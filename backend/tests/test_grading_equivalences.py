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


def test_comma_after_leading_no_changes_meaning_in_es_pl_ro():
    cases = [
        ("es", "No, está cerca.", "No está cerca"),
        ("pl", "Nie, zgadzam się.", "Nie zgadzam się"),
        ("ro", "Nu, mi-e frică.", "Nu mi-e frică"),
    ]
    for language, with_pause, without_pause in cases:
        for correct, learner in ((with_pause, without_pause), (without_pause, with_pause)):
            assert grade(
                learner, correct, "translation", script="latin", language_code=language
            ) == "incorrect", (language, correct, learner)
    # Other pause marks count as the same pause; accents still fold as before.
    assert grade(
        "¡No! Está cerca", "No, está cerca.", "translation", script="latin", language_code="es"
    ) == "correct"
    assert grade(
        "No esta cerca", "No está cerca", "translation", script="latin", language_code="es"
    ) == "almost"


def test_leading_no_comma_rule_is_narrow():
    # A doubled "no" keeps the negation either way.
    assert grade(
        "Nie nie, kawa jest lepsza", "Nie, nie, kawa jest lepsza", "translation",
        script="latin", language_code="pl",
    ) == "correct"
    # Languages with a distinct negator keep ignoring the comma.
    assert grade("Nee dank je", "Nee, dank je.", "translation", script="latin", language_code="nl") == "correct"
    assert grade("No thanks", "No, thanks.", "translation", script="latin", language_code="en") == "correct"
    # Other commas stay ignored in es.
    assert grade(
        "Sí está lejos", "Sí, está lejos.", "translation", script="latin", language_code="es"
    ) == "correct"
    # Spoken transcripts keep ignoring punctuation.
    assert grade(
        "No está cerca", "No, está cerca.", "dialogue_response", script="latin",
        language_code="es", input_mode="spoken",
    ) == "correct"
    # Multi-answer content still accepts any listed variant.
    accepted = {"canonical": "No, gracias.", "accepted": ["No, gracias.", "No gracias."]}
    assert grade("No gracias", accepted, "translation", script="latin", language_code="es") == "correct"


def test_romanian_cedilla_folds_to_comma_below():
    for strict in (None, True):
        assert grade(
            "Şi ţara e frumoasă", "Și țara e frumoasă", "translation",
            script="latin", language_code="ro", orthography_strict=strict,
        ) == "correct"
        assert grade(
            "ŞI ŢARA", "și țara", "translation", script="latin", language_code="ro",
            orthography_strict=strict,
        ) == "correct"
    # A genuinely missing diacritic is still a spelling difference.
    assert grade(
        "Si tara e frumoasa", "Și țara e frumoasă", "translation",
        script="latin", language_code="ro",
    ) == "incorrect"
    # Dictation stays byte-strict on visible diacritics.
    assert grade("Şi ţara", "Și țara", "dictation", language_code="ro") == "incorrect"


def test_hindi_nukta_and_chandrabindu_fold():
    pairs = [
        ("निश्चित रूप से वजह ट्रैफिक है", "निश्चित रूप से वजह ट्रैफ़िक है"),
        ("मुझे जरूर आना है", "मुझे ज़रूर आना है"),
        ("खराब", "ख़राब"),
        ("यह महंगा है", "यह महँगा है"),
        # precomposed क़ (U+0958) vs क + nukta
        ("क़लम", "क़लम"),
        ("कलम", "क़लम"),
    ]
    for learner, correct in pairs:
        for strict in (None, True):
            assert grade(
                learner, correct, "translation", script="devanagari",
                language_code="hi", orthography_strict=strict,
            ) == "correct", (learner, correct)
            assert grade(
                correct, learner, "translation", script="devanagari",
                language_code="hi", orthography_strict=strict,
            ) == "correct", (learner, correct)
    # ड़/ढ़ are distinct letters and keep their nukta.
    assert grade("पडना", "पढ़ना", "translation", script="devanagari", language_code="hi") == "incorrect"
    assert grade("लडका", "लड़का", "translation", script="devanagari", language_code="hi") == "incorrect"
    # Dictation is unchanged (variants there must be authored).
    assert grade("ट्रैफिक है", "ट्रैफ़िक है", "dictation", language_code="hi") == "incorrect"


def test_arabic_detached_waw_is_forgiven_even_when_strict():
    for strict in (None, True):
        for learner, correct in (
            ("أريد ماء و قهوة", "أريد ماء وقهوة"),
            ("أريد ماء وقهوة", "أريد ماء و قهوة"),
            ("و أنا أيضا", "وأنا أيضا"),
        ):
            assert grade(
                learner, correct, "translation", script="arabic",
                language_code="ar", orthography_strict=strict,
            ) == "correct"
    # Only a standalone و: a word ending in و keeps its space.
    assert grade(
        "هوذهب", "هو ذهب", "translation", script="arabic", language_code="ar",
        orthography_strict=True,
    ) == "incorrect"
    # fa/prs write و detached; no new rule there on strict paths.
    assert grade(
        "من وتو", "من و تو", "translation", script="arabic", language_code="fa",
        orthography_strict=True,
    ) == "incorrect"
    # Dictation is unchanged.
    assert grade("ماء و قهوة", "ماء وقهوة", "dictation", language_code="ar") == "incorrect"


# --- session 9 grader review fixes (2026-10-20) ---------------------------


def _en(learner, correct, **kwargs):
    return grade(learner, correct, "translation", script="latin", language_code="en", **kwargs)


def test_ambiguous_contractions_reject_wrong_expansions():
    assert _en("He is eaten", "He's eaten") == "incorrect"
    assert _en("It is been a while", "It's been a while") == "incorrect"
    assert _en("If I would known", "If I'd known") == "incorrect"
    assert _en("I had like a coffee", "I'd like a coffee") == "incorrect"
    assert _en("Everyone is book", "Everyone's book") == "incorrect"
    # The right expansions still pass, both directions.
    for learner, correct in [
        ("He has eaten", "He's eaten"),
        ("It has been a while", "It's been a while"),
        ("If I had known", "If I'd known"),
        ("You had better go", "You'd better go"),
        ("It is done", "It's done"),
        ("It has done", "It's done"),
        ("She is tired", "She's tired"),
    ]:
        assert _en(learner, correct) == "correct", learner
        assert _en(correct, learner) == "correct", learner


def test_its_and_it_s_are_not_contraction_equivalents():
    assert _en("its cold", "it is cold") == "incorrect"
    assert _en("it is cold", "its cold") == "incorrect"
    assert _en("Its color", "It is color") == "incorrect"
    # A missing apostrophe is at most a typo, never a full match.
    assert _en("its cold", "it's cold") != "correct"
    assert _en("it's color", "its color") != "correct"


def test_strict_exercises_accept_correct_expansions_only():
    for learner, correct in [
        ("I am ready", "I'm ready"),
        ("He has eaten", "He's eaten"),
        ("I can not", "I can't"),
        ("If I had known", "If I'd known"),
    ]:
        assert _en(learner, correct, orthography_strict=True) == "correct", learner
        assert _en(correct, learner, orthography_strict=True) == "correct", learner
    assert grade(
        "I am ready", "I'm ready", "speak_response", script="latin",
        language_code="en", input_mode="spoken", orthography_strict=True,
    ) == "correct"
    for learner, correct in [
        ("He is eaten", "He's eaten"),
        ("If I would known", "If I'd known"),
        ("Everyone is book", "Everyone's book"),
        ("It is been a while", "It's been a while"),
    ]:
        assert _en(learner, correct, orthography_strict=True) == "incorrect", learner


def test_romanian_hyphenated_clitics_are_not_a_pause():
    for learner, correct in [("Nu mi place", "Nu-mi place"), ("Nu i așa", "Nu-i așa?")]:
        assert grade(
            learner, correct, "translation", script="latin", language_code="ro"
        ) in {"correct", "almost"}, learner
    assert grade(
        "Nu-mi place", "Nu-mi place", "translation", script="latin", language_code="ro"
    ) == "correct"
    # A real pause after Nu still has to match.
    assert grade(
        "Nu e aproape", "Nu, e aproape", "translation", script="latin", language_code="ro"
    ) == "incorrect"


def test_politeness_follow_up_does_not_need_its_comma():
    assert grade(
        "No gracias", "No, gracias", "translation", script="latin", language_code="es"
    ) == "correct"
    assert grade(
        "Nie dziękuję", "Nie, dziękuję", "translation", script="latin", language_code="pl"
    ) == "correct"
    assert grade(
        "Nu mulțumesc", "Nu, mulțumesc", "translation", script="latin", language_code="ro"
    ) == "correct"
    # The negator case is unchanged.
    assert grade(
        "No está cerca", "No, está cerca", "translation", script="latin", language_code="es"
    ) == "incorrect"


def test_hindi_nukta_folding_is_a_documented_decision():
    # Deliberate: minimal pairs differing only by nukta/chandrabindu merge,
    # strict paths included; dictation stays byte-strict.
    for learner, correct in [("खाना", "ख़ाना"), ("सजा", "सज़ा"), ("हंस", "हँस")]:
        assert grade(
            learner, correct, "translation", script="devanagari", language_code="hi",
            orthography_strict=True,
        ) == "correct", learner
    # Precomposed क़ (U+0958) input folds like the decomposed form.
    assert grade(
        "क़ाली", "काली", "translation",
        script="devanagari", language_code="hi",
    ) == "correct"
    assert grade("सजा", "सज़ा", "dictation", script="devanagari", language_code="hi") == "incorrect"


def test_adjectival_participles_accept_is_and_has_where_both_read():
    # 's + adjectival participle means "is"; accept it.
    for learner, correct in [
        ("She is married", "She's married"),
        ("He is tired", "He's tired"),
        ("It is closed", "It's closed"),
        ("I am done", "I'm done"),
        ("He is finished", "He's finished"),
        ("He is gone", "He's gone"),
        ("He is drunk", "He's drunk"),
        ("It is done", "It's done"),
    ]:
        for strict in (None, True):
            assert _en(learner, correct, orthography_strict=strict) == "correct", learner
            assert _en(correct, learner, orthography_strict=strict) == "correct", learner
    # Genuinely ambiguous: both readings are accepted.
    for learner, correct in [
        ("He has gone", "He's gone"),
        ("He has finished", "He's finished"),
        ("She has grown", "She's grown"),
    ]:
        assert _en(learner, correct) == "correct", learner
        assert _en(correct, learner) == "correct", learner
    # Clear errors stay rejected.
    for learner, correct in [
        ("He is eaten", "He's eaten"),
        ("It is been", "It's been"),
        ("If I would known", "If I'd known"),
    ]:
        assert _en(learner, correct) == "incorrect", learner
