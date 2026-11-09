"""Tests for unit-scoped practice-template satisfiability checks."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _practice_unit_scope_check as chk  # noqa: E402


def _spec(token: str, unit: str = "01") -> dict:
    return {
        "lesson_content_key": f"nl.a1.unit{unit}.lesson1",
        "language_code": "nl",
        "part_of_speech": "noun",
        "token": token,
        "english_gloss": token,
        "agreement_tags": {"topic": "place"},
    }


def _constraints() -> dict:
    return {
        "language_code": "nl",
        "part_of_speech": "noun",
        "agreement_tags": {"topic": "place"},
    }


def test_flags_dead_slot_using_only_pack_unit_lexemes(tmp_path):
    pack = tmp_path / "a1_unit01.yaml"
    pack.write_text(yaml.safe_dump({"templates": [{
        "content_key": "k.dead",
        "type": "translation",
        "slots": {"item": _constraints()},
    }]}), encoding="utf-8")
    problems = chk.check_pack(pack, [_spec("station", unit="02")])
    assert any(severity == "DEAD" and "k.dead" in message for severity, message in problems)


def test_reports_multiple_choice_floor_without_marking_it_dead(tmp_path):
    pack = tmp_path / "a1_unit01.yaml"
    pack.write_text(yaml.safe_dump({"templates": [{
        "content_key": "k.mc",
        "type": "multiple_choice",
        "slots": {"item": _constraints()},
        "answer_derivation": {"kind": "slot_text", "slot": "item"},
    }]}), encoding="utf-8")
    problems = chk.check_pack(pack, [_spec("station")])
    keyed = [(severity, message) for severity, message in problems if "k.mc" in message]
    assert [severity for severity, _ in keyed] == ["FLOOR"]


def test_invalid_yaml_is_skipped(tmp_path):
    pack = tmp_path / "a1_unit01.yaml"
    pack.write_text("templates: [\n", encoding="utf-8")
    assert chk.check_pack(pack, []) == [
        ("SKIP", "a1_unit01.yaml: could not parse (ParserError) -- skipped")
    ]

