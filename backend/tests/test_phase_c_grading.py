from app.review.grading import (
    damerau_levenshtein,
    grade_answer,
    is_case_only_difference,
    is_latin_script_text,
    is_script_confusion,
)
from app.review.sm2 import quality_for_result, schedule


def test_damerau_levenshtein_distance_1_variants():
    assert damerau_levenshtein("hola", "hola") == 0
    assert damerau_levenshtein("hola", "holaa") == 1  # insertion
    assert damerau_levenshtein("hola", "hol") == 1  # deletion
    assert damerau_levenshtein("hola", "hala") == 1  # substitution
    assert damerau_levenshtein("hola", "hloa") == 1  # adjacent transposition


def test_damerau_levenshtein_distance_2_plus_rejected():
    assert damerau_levenshtein("hola", "adios") > 1
    assert damerau_levenshtein("gracias", "gracis") == 1
    assert damerau_levenshtein("gracias", "graci") == 2


def test_grade_answer_latin_tolerant_by_default():
    assert grade_answer("hola", "hola", exercise_type="translation") == "correct"
    assert grade_answer("hoal", "hola", exercise_type="translation") == "almost"
    assert grade_answer("xyz", "hola", exercise_type="translation") == "incorrect"


def test_grade_answer_non_latin_strict_by_default():
    # سلام vs a distance-1 typo - strict by default (script defaults to
    # non-latin heuristic when no explicit script/orthography_strict given)
    result = grade_answer("سلا", "سلام", exercise_type="translation")
    assert result == "incorrect"


def test_grade_answer_explicit_script_param():
    assert (
        grade_answer("hoal", "hola", exercise_type="translation", script="latin")
        == "almost"
    )
    assert (
        grade_answer("hoal", "hola", exercise_type="translation", script="arabic")
        == "incorrect"
    )


def test_grade_answer_orthography_strict_overrides_script_default():
    # Latin-script correct answer, but author forced strict mode.
    assert (
        grade_answer(
            "hoal",
            "hola",
            exercise_type="translation",
            script="latin",
            orthography_strict=True,
        )
        == "incorrect"
    )
    # Non-latin correct answer, but author explicitly allows tolerance.
    result = grade_answer(
        "سلا",
        "سلام",
        exercise_type="translation",
        script="arabic",
        orthography_strict=False,
    )
    # "سلا" vs "سلام" is a deletion (distance 1), not a script-pair swap,
    # so tolerant mode should accept it as almost.
    assert result == "almost"


def test_script_confusion_never_forgiven_even_when_tolerant():
    # Arabic kaf ك vs Persian keheh ک - same word otherwise, distance 1.
    a = "کتاب"  # Persian keheh
    b = "كتاب"  # Arabic kaf
    assert is_script_confusion(a, b) is True
    result = grade_answer(
        a,
        b,
        exercise_type="translation",
        script="latin",  # even if caller wrongly thought this was tolerant
        orthography_strict=False,
    )
    assert result == "incorrect"


def test_script_confusion_helper_false_for_unrelated_chars():
    assert is_script_confusion("hola", "hala") is False
    assert is_script_confusion("ab", "abc") is False  # different lengths


def test_choice_type_exercises_never_produce_almost():
    assert grade_answer("goodbye", "hello", exercise_type="multiple_choice") in {
        "incorrect",
        "correct",
    }
    # even a distance-1 wrong option must not become "almost"
    assert (
        grade_answer("hell", "hello", exercise_type="multiple_choice") == "incorrect"
    )


def test_is_latin_script_text():
    assert is_latin_script_text("hola") is True
    assert is_latin_script_text("سلام") is False
    assert is_latin_script_text("") is False


def test_is_case_only_difference_helper():
    assert is_case_only_difference("sie", "Sie") is True
    assert is_case_only_difference("Sie", "Sie") is False  # identical, not "different"
    assert is_case_only_difference("sie", "sei") is False  # different letters, not case


def test_case_sensitive_defaults_off_existing_behavior_unchanged():
    # No case_sensitive kwarg at all - must behave exactly as before this
    # feature existed (the whole point of defaulting to False).
    assert grade_answer("HOLA", "hola", exercise_type="translation") == "correct"
    assert grade_answer("Sie", "sie", exercise_type="translation") == "correct"


def test_case_sensitive_german_sie_vs_capital_sie():
    # The actual reported scenario: German formal "Sie" (capital, "you"
    # formal) vs lowercase "sie" ("she"/"they") - a real grammatical
    # distinction. Once an exercise opts into case_sensitive, the two
    # must grade as genuinely different answers, not interchangeable.
    assert (
        grade_answer(
            "Sie", "Sie", exercise_type="translation", case_sensitive=True
        )
        == "correct"
    )
    assert (
        grade_answer(
            "sie", "Sie", exercise_type="translation", case_sensitive=True
        )
        == "incorrect"
    )
    assert (
        grade_answer(
            "Sie", "sie", exercise_type="translation", case_sensitive=True
        )
        == "incorrect"
    )
    assert (
        grade_answer(
            "sie", "sie", exercise_type="translation", case_sensitive=True
        )
        == "correct"
    )


def test_case_sensitive_case_only_mismatch_never_becomes_almost():
    # Without case_sensitive at all, "sie"/"Sie" casefold to the identical
    # string, so it's a perfect match ("correct") - the whole reason this
    # distinction was previously ungradeable. Once case_sensitive=True
    # stops casefolding, "sie" vs "Sie" becomes a genuine distance-1
    # substitution - without the is_case_only_difference guard, THAT would
    # fall straight into the existing typo-tolerance path and earn
    # "almost" (still counted as correct for XP/SRS), silently
    # reintroducing the exact bug case_sensitive exists to fix. Confirm it
    # is hard-blocked to "incorrect" instead.
    lenient = grade_answer("sie", "Sie", exercise_type="translation")
    assert lenient == "correct"
    assert damerau_levenshtein("sie", "Sie") == 1  # confirms it WOULD be
    # typo-tolerance-eligible once case_sensitive stops casefolding away
    # the difference - so the guard below is doing real work, not a no-op.
    strict = grade_answer(
        "sie", "Sie", exercise_type="translation", case_sensitive=True
    )
    assert strict == "incorrect"


def test_case_sensitive_real_typos_still_tolerated():
    # case_sensitive must not disable typo tolerance in general - only
    # case-only mismatches are hard-blocked. A genuine typo with the
    # correct case elsewhere should still earn "almost".
    result = grade_answer(
        "Sie geth", "Sie geht", exercise_type="translation", case_sensitive=True
    )
    assert result == "almost"


def test_quality_for_result_mapping():
    assert quality_for_result("correct") == 5
    assert quality_for_result("almost") == 4
    assert quality_for_result("incorrect") == 2
    assert quality_for_result(True) == 5
    assert quality_for_result(False) == 2


class _FakeSRSRow:
    def __init__(self):
        self.repetitions = None
        self.interval_days = None
        self.ease_factor = None
        self.mastery = None
        self.due_at = None


def test_schedule_almost_counts_as_success_not_failure():
    item = _FakeSRSRow()
    schedule(item, "almost")
    assert item.repetitions == 1
    assert item.mastery > 0.0  # success branch, not the -0.2 failure branch


def test_schedule_incorrect_on_young_word_still_restarts_it():
    # The 2026-07-10 lapse softening (proportional demotion instead of a
    # hard reset — see the comment in sm2.schedule()) only preserves
    # credit for ESTABLISHED words. A word with a single successful
    # review has nothing worth preserving: -2 repetitions floors at 0 and
    # 30% of a 1-day interval floors at 1, so the outcome for a young
    # word is identical to the old full reset.
    item = _FakeSRSRow()
    schedule(item, "correct")
    schedule(item, "incorrect")
    assert item.repetitions == 0
    assert item.interval_days == 1
