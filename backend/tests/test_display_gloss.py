"""Bracketed authoring notes in glosses are hidden in practice items only."""

import random

from app.models import Lexeme, PracticeTemplate
from app.practice.service import (
    _distractor_values,
    derive_answer,
    display_gloss,
    render_frame,
)


def _lex(token: str, gloss: str) -> Lexeme:
    return Lexeme(
        token=token,
        language_code="nl",
        part_of_speech="verb",
        english_gloss=gloss,
        course_id="c",
    )


def test_display_gloss_strips_notes():
    assert display_gloss("call (with ik)") == "call"
    assert display_gloss("(inflected) call") == "call"
    assert display_gloss("you; your (informal)") == "you; your"
    assert display_gloss("a (b (c)) d") == "a d"
    assert display_gloss("call (x), phone") == "call, phone"


def test_display_gloss_keeps_meaning_and_never_empty():
    assert display_gloss("and/or; also") == "and/or; also"
    assert display_gloss("(inflected)") == "(inflected)"
    assert display_gloss("plain") == "plain"
    assert display_gloss(None) == ""


def test_render_frame_strips_only_english_gloss_field():
    filled = {"v": _lex("bel", "call (with ik)")}
    frame = {"text": "Ik {v} je", "slot_rendering": {"v": "english_gloss"}}
    assert render_frame(frame, filled) == "Ik call je"
    assert render_frame({"text": "Ik {v} je"}, filled) == "Ik bel je"


def test_matching_pairs_keep_notes_only_for_clashes():
    filled = {
        "a": _lex("eet", "eat (with ik)"),
        "b": _lex("eten", "eat"),
        "c": _lex("bel", "call (with ik)"),
    }
    pairs = derive_answer({"kind": "matching_pairs", "slots": ["a", "b", "c"]}, filled)
    assert pairs == {"eet": "eat (with ik)", "eten": "eat", "bel": "call"}


def test_distractor_clash_with_answer_is_skipped():
    slot = {"language_code": "nl", "part_of_speech": "verb"}
    template = PracticeTemplate(
        slots={"v": slot},
        answer_derivation={"kind": "slot_gloss", "slot": "v"},
    )
    lexemes = [
        _lex("eten", "eat"),
        _lex("eet", "eat (with ik)"),
        _lex("bel", "call (with ik)"),
        _lex("loop", "walk (inflected)"),
        _lex("loopt", "walk"),
    ]
    values = _distractor_values(template, "eat", lexemes, random.Random(1))
    assert sorted(values) == ["call", "walk"]
