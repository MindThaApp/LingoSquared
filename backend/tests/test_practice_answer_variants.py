"""Practice items accept shared Dari/Persian variants, authored
answer_derivation.accepted_variants, and English contraction expansions."""
import random
from types import SimpleNamespace

from app.practice.service import build_prompt
from app.review.grading import grade

SLOT = {"language_code": "prs", "part_of_speech": "noun", "agreement_tags": {"semantic": "x"}}


def lex(token, gloss="ticket"):
    return SimpleNamespace(
        id=token, token=token, english_gloss=gloss, language_code="prs",
        part_of_speech="noun", agreement_tags={"semantic": "x"},
    )


def ok(resp, correct, lang="prs", t="translation"):
    return grade(resp, correct, t, script="arabic", language_code=lang) == "correct"


def test_ticket_variants_accepted_both_ways():
    for resp in ("تکت", "بلیط", "بلیت"):
        assert ok(resp, "تکت")
    assert ok("یک بلیط به هرات", "یک تکت به هرات")
    assert ok("یک تکت به هرات", "یک بلیت به هرات")
    assert ok("بلیت", "بلیط", lang="fa")
    assert not ok("قطار", "تکت")


def test_register_pairs():
    assert ok("نام من احمد است", "نامم احمد است")
    assert ok("نامم احمد است", "نام من احمد است")
    assert ok("من استم", "من هستم")
    assert not ok("نام تو احمد است", "نامم احمد است")


def test_variants_do_not_leak_to_other_languages_or_partial_words():
    assert not ok("بلیط", "تکت", lang="en")
    assert not ok("استمرار", "هستمرار")


def test_english_contractions_in_practice_answers():
    assert ok("I am here", "I'm here", lang="en")
    assert ok("he is a doctor", "he's a doctor", lang="en")
    assert ok("I'm here", "I am here", lang="en")
    assert grade("I am here", {"canonical": "I'm here", "accepted": ["I'm here"]}, "translation", script="latin", language_code="en") == "correct"


def test_authored_accepted_variants_on_translation_and_fill():
    template = SimpleNamespace(
        type="translation",
        slots={"item": SLOT},
        frame={"text": "ticket {item}", "language_code": "en", "direction": "ltr"},
        answer_derivation={
            "kind": "render_frame",
            "frame": {"text": "تکت {item}", "language_code": "prs", "direction": "rtl"},
            "accepted_variants": ["ٹکٹ {item}"],
        },
    )
    course = SimpleNamespace(source_language="en", target_language="prs")
    _, answer = build_prompt(template, course, {"item": lex("هرات")}, [lex("هرات")], random.Random(1))
    assert answer == {"canonical": "تکت هرات", "accepted": ["تکت هرات", "ٹکٹ هرات"]}
    assert grade("ٹکٹ هرات", answer, "translation", script="arabic", language_code="prs") == "correct"
    assert grade("بلیط هرات", answer, "translation", script="arabic", language_code="prs") == "correct"
