from app.review.grading import grade, grade_answer


def test_multi_answer_free_text_gets_typo_tolerance():
    correct = {"canonical": "correct", "accepted": ["correct", "right"]}
    assert grade("corret", correct, "translation", script="latin") == "almost"


def test_non_dictation_trailing_period_is_ignored():
    assert grade("hello.", "hello", "translation", script="latin") == "correct"
    assert grade("hello", "hello.", "translation", script="latin") == "correct"


def test_smart_apostrophe_is_equivalent():
    assert grade("I’m ready", "I'm ready", "translation", script="latin") == "correct"


def test_nfd_text_is_equivalent_to_nfc():
    assert grade("cafe\u0301", "café", "translation", script="latin") == "correct"


def test_persian_question_mark_variant_is_ignored():
    assert grade("چطوری؟", "چطوری?", "translation", script="arabic") == "correct"


def test_dictation_keeps_internal_punctuation_strict():
    assert grade_answer(
        "Sí quiero aprender.",
        "Sí, quiero aprender.",
        exercise_type="dictation",
    ) == "incorrect"


def test_punctuation_strict_disables_punctuation_normalization():
    assert grade(
        "hello.", "hello", "translation", script="latin", punctuation_strict=True
    ) == "almost"


def test_fill_in_blank_uses_typo_tolerance_for_long_words():
    assert grade("bannana", "banana", "fill_in_blank", script="latin") == "almost"
