"""Tests for Endless Practice slot candidate validation."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _practice_slot_check as chk  # noqa: E402


def _lexeme(token: str, gloss: str, *, pos: str = "noun", **tags):
    return {
        "language_code": "nl",
        "part_of_speech": pos,
        "token": token,
        "english_gloss": gloss,
        "agreement_tags": tags,
    }


def test_lexeme_matches_language_pos_and_overlapping_tags():
    lexeme = _lexeme("kat", "cat", number=["singular", "plural"])
    assert chk.lexeme_matches(lexeme, {
        "language_code": "nl", "part_of_speech": ["noun", "verb"],
        "agreement_tags": {"number": "singular"},
    })
    assert not chk.lexeme_matches(lexeme, {
        "language_code": "en", "part_of_speech": "noun",
    })
    assert not chk.lexeme_matches(lexeme, {
        "language_code": "nl", "part_of_speech": "noun",
        "agreement_tags": {"gender": "common"},
    })


def test_check_pack_reports_empty_and_undersized_candidate_pools(tmp_path):
    pack = tmp_path / "pack.yaml"
    pack.write_text(yaml.safe_dump({"templates": [
        {
            "content_key": "missing", "type": "word_order",
            "slots": {"verb": {"language_code": "nl", "part_of_speech": "verb"}},
        },
        {
            "content_key": "choices", "type": "multiple_choice",
            "slots": {"item": {"language_code": "nl", "part_of_speech": "noun"}},
            "answer_derivation": {"kind": "slot_gloss", "slot": "item"},
        },
        {
            "content_key": "pairs", "type": "matching_pairs",
            "slots": {"item": {"language_code": "nl", "part_of_speech": "noun"}},
        },
    ]}), encoding="utf-8")

    problems = chk.check_pack(pack, [
        _lexeme("kat", "cat"),
        _lexeme("kat", "kitty"),
    ])

    assert len(problems) == 3
    assert "ZERO candidate lexemes" in problems[0]
    assert "only 2 distinct answer-derivation value(s)" in problems[1]
    assert "only 1 distinct token(s)" in problems[2]


def test_check_pack_accepts_sufficient_distinct_candidates(tmp_path):
    pack = tmp_path / "pack.yaml"
    pack.write_text(yaml.safe_dump({"templates": [{
        "content_key": "choices", "type": "listen_select",
        "slots": {"item": {"language_code": "nl", "part_of_speech": "noun"}},
        "answer_derivation": {"kind": "slot_text", "slot": "item"},
    }]}), encoding="utf-8")
    assert chk.check_pack(pack, [
        _lexeme("kat", "cat"), _lexeme("hond", "dog"), _lexeme("vis", "fish"),
    ]) == []
