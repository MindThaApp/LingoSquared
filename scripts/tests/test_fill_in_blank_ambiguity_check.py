"""Tests for the fill-in-blank ambiguity detector."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _fill_in_blank_ambiguity_check as chk  # noqa: E402


def _lexeme(token: str) -> dict:
    return {
        "language_code": "nl",
        "part_of_speech": "noun",
        "token": token,
        "english_gloss": token,
        "agreement_tags": {"topic": "place"},
    }


def _template(key: str, *, interchangeable: bool = False, second_slot: bool = False) -> dict:
    slots = {
        "item": {
            "language_code": "nl",
            "part_of_speech": "noun",
            "agreement_tags": {"topic": "place"},
        }
    }
    if second_slot:
        slots["other"] = {"language_code": "nl", "part_of_speech": "verb"}
    return {
        "content_key": key,
        "type": "fill_in_blank",
        "frame": {"text": "Ik zie {item}."},
        "slots": slots,
        "answer_derivation": {
            "kind": "slot_text",
            "slot": "item",
            "interchangeable": interchangeable,
        },
    }


def test_single_slot_multiple_candidates_is_ambiguous(tmp_path):
    pack = tmp_path / "a1_unit01.yaml"
    pack.write_text("templates: []\n", encoding="utf-8")
    # Exercise the YAML-loading wrapper with a tiny replacement document.
    import yaml

    pack.write_text(yaml.safe_dump({"templates": [_template("k.ambiguous")]}), encoding="utf-8")
    ambiguous, review = chk.check_pack(pack, [_lexeme("station"), _lexeme("school")])
    assert len(ambiguous) == 1
    assert "k.ambiguous" in ambiguous[0]
    assert review == []


def test_interchangeable_and_multi_slot_are_handled_separately():
    pack = {
        "templates": [
            _template("k.accept-all", interchangeable=True),
            _template("k.review", second_slot=True),
        ]
    }
    ambiguous, review = chk.check_pack_dict(pack, [_lexeme("station"), _lexeme("school")])
    assert ambiguous == []
    assert len(review) == 1
    assert "k.review" in review[0]

