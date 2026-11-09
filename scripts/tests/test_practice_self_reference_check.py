"""Tests for practice-template self-reference checks."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _practice_self_reference_check as chk  # noqa: E402


def test_match_handles_pos_lists_and_overlapping_agreement_tags():
    lexeme = {
        "language_code": "nl", "part_of_speech": "noun",
        "agreement_tags": {"number": ["singular", "plural"]},
    }
    assert chk._match(lexeme, {
        "language_code": "nl", "part_of_speech": ["noun", "proper_noun"],
        "agreement_tags": {"number": "plural"},
    })
    assert not chk._match(lexeme, {
        "language_code": "nl", "agreement_tags": {"gender": "common"},
    })


def test_frame_text_collects_nested_text():
    assert chk._frame_text({
        "text": "main", "nested": [{"text": "ignored because direct text wins"}],
    }) == "main"
    assert chk._frame_text([{"text": "first"}, {"feedback": "second"}]) == "first second"


def test_slot_reuse_hits_reports_duplicate_and_cross_language_slot(tmp_path, monkeypatch, capsys):
    practice = tmp_path / "docs/content/practice/en-nl"
    practice.mkdir(parents=True)
    (practice / "a1_unit01.yaml").write_text(yaml.safe_dump({"templates": [{
        "content_key": "template",
        "frame": {
            "text": "Choose {item}, then {item}",
            "language_code": "en",
        },
        "slots": {"item": {"language_code": "nl", "part_of_speech": "noun"}},
    }]}), encoding="utf-8")
    monkeypatch.setattr(chk, "REPO_ROOT", tmp_path)

    assert chk.slot_reuse_hits() == 2
    output = capsys.readouterr().out
    assert "SLOT-REUSE" in output
    assert "SLOT-LANG" in output


def test_slot_reuse_accepts_explicit_gloss_rendering(tmp_path, monkeypatch):
    practice = tmp_path / "docs/content/practice/en-nl"
    practice.mkdir(parents=True)
    (practice / "a1_unit01.yaml").write_text(yaml.safe_dump({"templates": [{
        "frame": {
            "text": "Choose {item}", "language_code": "en",
            "slot_rendering": {"item": "english_gloss"},
        },
        "slots": {"item": {"language_code": "nl", "part_of_speech": "noun"}},
    }]}), encoding="utf-8")
    monkeypatch.setattr(chk, "REPO_ROOT", tmp_path)
    assert chk.slot_reuse_hits() == 0
