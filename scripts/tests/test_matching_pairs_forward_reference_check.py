"""Tests for the matching-pairs forward-reference detector."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _matching_pairs_forward_reference_check as chk  # noqa: E402


def _write_course(tmp_path, lessons, *, language="en"):
    root = tmp_path / "realizations"
    course = root / language
    course.mkdir(parents=True)
    (course / "a1_unit01.yaml").write_text(yaml.safe_dump({
        "target_language": language,
        "units": [{"content_key": "unit", "lessons": lessons}],
    }), encoding="utf-8")
    return root


def test_find_violations_flags_answer_first_taught_later(tmp_path, monkeypatch):
    root = _write_course(tmp_path, [
        {"content_key": "early", "exercises": [{
            "content_key": "match", "type": "matching_pairs",
            "pairs": [{"left": "went", "right": "Travelled!"}],
        }]},
        {"content_key": "later", "teaching": [{
            "target": {"text": "travelled"}, "introduced_tokens": ["travelled"],
        }]},
    ])
    monkeypatch.setattr(chk, "REALIZATIONS_DIR", root)
    monkeypatch.setattr(chk, "REPO_ROOT", tmp_path)

    found = chk.find_violations()

    assert len(found) == 1
    assert found[0].right == "Travelled!"
    assert found[0].taught_lesson_key == "later"
