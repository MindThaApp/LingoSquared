from app.review.grading import grade
from app.schemas.api import AnswerIn


def test_spoken_long_word_allows_two_edits_but_typed_does_not():
    assert grade(
        "elefant", "elephant", "translation", input_mode="spoken", language_code="en"
    ) == "almost"
    assert grade("elefant", "elephant", "translation", input_mode="typed") == "incorrect"


def test_spoken_persian_allows_one_edit_but_typed_remains_strict():
    assert grade(
        "کتاب", "کتابا", "translation", input_mode="spoken", language_code="fa"
    ) == "almost"
    assert grade("کتاب", "کتابا", "translation", input_mode="typed", language_code="fa") == "incorrect"


def test_spoken_digit_matches_target_language_number_word():
    assert grade("7", "zeven", "translation", input_mode="spoken", language_code="nl") == "almost"
    assert grade("2:30", "half drie", "translation", input_mode="spoken", language_code="nl") == "almost"
    assert grade("۷", "7", "translation", input_mode="spoken", language_code="fa") == "almost"
    assert grade("7", "zeven", "translation", input_mode="typed", language_code="nl") == "incorrect"


def test_spoken_allows_one_extra_short_function_word():
    assert grade(
        "ik ga de naar school",
        "ik ga naar school",
        "translation",
        input_mode="spoken",
        language_code="nl",
    ) == "almost"


def test_spoken_still_rejects_a_wrong_word():
    assert grade("the red car", "the blue car", "translation", input_mode="spoken") == "incorrect"
    assert grade("the a in and car", "the and car", "translation", input_mode="spoken", language_code="en") == "incorrect"


def test_speaking_exercise_defaults_to_spoken_tolerance():
    assert grade("elefant", "elephant", "speak_repeat", language_code="en") == "almost"


def test_answer_input_mode_defaults_to_typed_and_accepts_spoken():
    assert AnswerIn(response="answer").input_mode == "typed"
    assert AnswerIn(response="answer", input_mode="spoken").input_mode == "spoken"
