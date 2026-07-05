from app.review.grading import (
    damerau_levenshtein,
    grade_answer,
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


def test_schedule_incorrect_resets_repetitions():
    item = _FakeSRSRow()
    schedule(item, "correct")
    schedule(item, "incorrect")
    assert item.repetitions == 0
    assert item.interval_days == 1
