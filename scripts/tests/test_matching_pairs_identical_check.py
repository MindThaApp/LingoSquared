"""Tests for the warn-level identical matching-pair detector."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _matching_pairs_identical_check as chk  # noqa: E402


def test_identical_ignores_case_diacritics_punctuation():
    assert chk.is_identical("had", "had")
    assert chk.is_identical("Café", "cafe")
    assert chk.is_identical("Meeting", "meeting.")
    assert not chk.is_identical("had moeten", "should have")
    assert not chk.is_identical("", "")


def test_find_identical_pairs(tmp_path):
    course = tmp_path / "en-nl"
    course.mkdir()
    (course / "b1_unit01.yaml").write_text(
        "exercises:\n"
        "  k.match:\n"
        "    accepted_answers:\n"
        "      - value: {had: had, eerder: earlier, Water: water}\n"
        "        status: correct\n"
        "  k.other:\n"
        "    accepted_answers:\n"
        "      - {value: 'plain text', status: correct}\n",
        encoding="utf-8",
    )
    related = tmp_path / "fa-prs"
    related.mkdir()
    (related / "a1_unit01.yaml").write_text(
        "exercises:\n  k.m:\n    accepted_answers:\n      - value: {x: x}\n",
        encoding="utf-8",
    )
    found = chk.find_identical_pairs(tmp_path)
    assert [(c, k, w) for c, _, k, w in found] == [
        ("en-nl", "k.match", "had"),
        ("en-nl", "k.match", "Water"),
    ]
