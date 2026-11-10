"""Dari->Farsi (prs-fa) lexemes whose word equals their gloss are not served."""

from app.models import Course, Lexeme
from app.practice.service import is_identical_pair_lexeme


def _course(source: str, target: str) -> Course:
    return Course(source_language=source, target_language=target, title="t")


def _lex(token: str, gloss: str) -> Lexeme:
    return Lexeme(
        token=token,
        language_code="fa",
        part_of_speech="noun",
        english_gloss=gloss,
        course_id="c",
    )


def test_identical_is_excluded():
    assert is_identical_pair_lexeme(_course("prs", "fa"), _lex("سلام", "سلام"))


def test_yeh_kaf_zwnj_difference_counts_as_identical():
    course = _course("prs", "fa")
    assert is_identical_pair_lexeme(course, _lex("کتاب", "كتاب"))
    assert is_identical_pair_lexeme(course, _lex("ایرانی", "ايرانى"))
    assert is_identical_pair_lexeme(course, _lex("می‌کنم", "می کنم"))
    assert is_identical_pair_lexeme(course, _lex("خوب", "خوب (note)"))


def test_different_words_are_kept():
    assert not is_identical_pair_lexeme(_course("prs", "fa"), _lex("مدرسه", "مکتب"))


def test_fa_prs_direction_is_unaffected():
    assert not is_identical_pair_lexeme(_course("fa", "prs"), _lex("سلام", "سلام"))
    assert not is_identical_pair_lexeme(_course("en", "fa"), _lex("سلام", "سلام"))
