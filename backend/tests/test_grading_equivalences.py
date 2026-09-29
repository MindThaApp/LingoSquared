from app.review.grading import grade, grade_answer


def test_fa_optional_leading_pronoun_is_correct_for_typed_and_spoken():
    accepted = "جمعه خونه موندم"
    learner = "من جمعه خونه موندم"
    assert grade(
        learner, accepted, "translation", script="arabic", language_code="fa"
    ) == "correct"
    assert grade(
        learner,
        accepted,
        "translation",
        script="arabic",
        language_code="fa",
        input_mode="spoken",
    ) == "correct"


def test_prs_optional_pronoun_after_clause_boundary():
    accepted = "من کتاب دارم ولی کتاب دارد"
    learner = "من کتاب دارم ولی او کتاب دارد"
    assert grade(
        learner, accepted, "translation", script="arabic", language_code="prs"
    ) == "correct"


def test_es_optional_subject_pronoun_is_correct_for_typed_and_spoken():
    assert grade(
        "Yo voy al cine", "Voy al cine", "translation", script="latin", language_code="es"
    ) == "correct"
    assert grade(
        "Yo voy al cine",
        "Voy al cine",
        "translation",
        script="latin",
        language_code="es",
        input_mode="spoken",
    ) == "correct"


def test_optional_pronoun_is_allowed_at_a_new_sentence_start():
    assert grade(
        "Voy al cine. Yo duermo",
        "Voy al cine. Duermo",
        "translation",
        script="latin",
        language_code="es",
    ) == "correct"


def test_non_pro_drop_language_does_not_get_pronoun_equivalence():
    assert grade("Ga", "Ik ga", "translation", script="latin", language_code="nl") == "incorrect"


def test_pronoun_must_be_added_or_dropped_not_changed():
    assert grade(
        "تو جمعه خونه موندم",
        "من جمعه خونه موندم",
        "translation",
        script="arabic",
        language_code="fa",
    ) == "incorrect"


def test_optional_pronoun_does_not_allow_other_word_changes():
    assert grade(
        "من جمعه بیرون موندم",
        "جمعه خونه موندم",
        "translation",
        script="arabic",
        language_code="fa",
    ) == "incorrect"


def test_persian_arabic_joining_variants_are_correct_for_typed_and_spoken():
    for learner in ("پنج‌شنبه", "پنج شنبه"):
        assert grade(
            learner, "پنجشنبه", "translation", script="arabic", language_code="fa"
        ) == "correct"
        assert grade(
            learner,
            "پنجشنبه",
            "translation",
            script="arabic",
            language_code="fa",
            input_mode="spoken",
        ) == "correct"


def test_joining_equivalence_is_limited_to_arabic_script_runs():
    assert grade(
        "سلام world", "سلامworld", "translation", script="arabic", language_code="fa"
    ) == "incorrect"


def test_new_equivalences_do_not_apply_to_dictation():
    assert grade_answer(
        "من جمعه خونه موندم",
        "جمعه خونه موندم",
        exercise_type="dictation",
        language_code="fa",
    ) == "incorrect"
    assert grade_answer(
        "پنج شنبه",
        "پنجشنبه",
        exercise_type="dictation",
        language_code="fa",
    ) == "incorrect"


def test_new_equivalences_respect_strictness_metadata():
    assert grade(
        "من جمعه خونه موندم",
        "جمعه خونه موندم",
        "translation",
        script="arabic",
        language_code="fa",
        orthography_strict=True,
    ) == "incorrect"
    assert grade(
        "پنج شنبه",
        "پنجشنبه",
        "translation",
        script="arabic",
        language_code="fa",
        orthography_strict=True,
    ) == "incorrect"
    assert grade(
        "Yo voy al cine",
        "Voy al cine",
        "translation",
        script="latin",
        language_code="es",
        case_sensitive=True,
    ) == "incorrect"
