"""Tests for Endless Practice content-integrity checks."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _practice_content_integrity_check as chk  # noqa: E402


def _constraints() -> dict:
    return {
        "language_code": "nl",
        "part_of_speech": "noun",
        "agreement_tags": {"topic": "place"},
    }


def _spec(token: str, gloss: str) -> dict:
    return {
        **_constraints(),
        "token": token,
        "english_gloss": gloss,
    }


def test_frame_collision_uses_runtime_rendered_field():
    template = {
        "frame": {"text": "The hospital is next to {place}."},
        "slots": {"place": _constraints()},
    }
    findings = chk._check_one_frame(
        template,
        "frame",
        template["frame"],
        template["slots"],
        [_spec("ziekenhuis", "hospital"), _spec("station", "station")],
        "english_gloss",
    )
    assert len(findings) == 1
    assert findings[0]["matched_candidate_values"] == ["hospital"]
    assert findings[0]["rendered_field"] == "english_gloss"


def test_collision_respects_word_boundaries_and_zwnj():
    assert chk._collides("hospital", "near the hospital")
    assert not chk._collides("hospital", "hospitality")
    assert not chk._collides("رفتم", "می‌رفتم")


def test_zero_and_unresolved_lesson_anchors_are_flagged(tmp_path, monkeypatch):
    pack_dir = tmp_path / "docs/content/practice/nl-en"
    pack_dir.mkdir(parents=True)
    (pack_dir / "a1_unit01.yaml").write_text(
        "templates:\n"
        "  - content_key: k.zero\n"
        "    lesson_content_key: nl.zero\n"
        "  - content_key: k.missing\n"
        "    lesson_content_key: nl.missing\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(chk, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(chk, "PRACTICE_DIRS", ["nl-en"])
    violations = chk.check_bug_class_b({"nl.zero": 0})
    assert {item["content_key"] for item in violations} == {"k.zero", "k.missing"}
    assert {item["issue"] for item in violations} == {
        "ZERO introduced_tokens -- lesson can never anchor a real lexeme",
        "UNRESOLVED -- no lesson in any realization file has this content_key",
    }
