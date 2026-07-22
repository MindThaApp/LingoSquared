"""Persian ZWNJ / Arabic-harakat invisible-formatting grading (2026-07-22).

Regression suite for the highest-severity correctness bug found by the
2026-07-22 audit: fa resolves to script='arabic', so grade_answer() runs
fully strict (no distance-1 tolerance at all), and _normalize() only
casefolded + collapsed whitespace. A ZERO WIDTH NON-JOINER (U+200C) - the
character Persian writes می‌کنم / لباس‌ها / درباره‌ی with, which is
invisible and which no mainstream Persian keyboard and no speech-to-text
engine emits - therefore decided correct-vs-incorrect. 296 of 912 (32%)
en-fa free-text-graded exercises had a ZWNJ-bearing accepted answer with
no ZWNJ-free variant; the 49 speak_response ones among them were
impossible to pass at all. Defect class 1.30 (harakat with no
undiacritized accepted variant) is the same bug on the same shape and is
covered here too.

Every Persian/Arabic string below is copied from the live corpus -
docs/content/realizations/fa/ and docs/content/overlays/en-fa|en-ar/ -
with the source cited, so these tests fail if the fix stops matching what
the content actually contains.
"""
from app.review.grading import (
    ZWNJ,
    answers_equivalent,
    grade,
    grade_answer,
    is_invisible_formatting_only_difference,
    is_script_confusion,
    strip_invisible_formatting,
)

# --- real corpus strings ---------------------------------------------------
# docs/content/overlays/en-fa/a1_unit01.yaml:311
#   accepted_answers: [{value: [خواهش, می‌کنم], status: correct}]
KHAHESH_MIKONAM = "خواهش می‌کنم"
KHAHESH_MIKONAM_JOINED = "خواهش میکنم"
KHAHESH_MIKONAM_SPACED = "خواهش می کنم"

# docs/content/overlays/en-fa/a1_unit22.yaml:242
#   - {value: "لطفاً آهسته‌تر صحبت کنید", status: correct}
# carries BOTH a fathatan (U+064B, لطفاً) and a ZWNJ (آهسته‌تر).
LOTFAN_AHESTETAR = "لطفاً آهسته‌تر صحبت کنید"

# docs/content/overlays/en-fa/a1_unit04.yaml:549 - speak_response, the
# category that was outright impossible (STT never emits U+200C).
SPEAK_FAMILY = "خانواده‌ی من کوچیکه یک برادر دارم خواهر ندارم"

# docs/content/overlays/en-fa/a1_unit08.yaml:329 - speak_response with two
# accepted variants, i.e. the multi-answer wrapper that never reaches
# grade_answer() at all.
SPEAK_DISCOUNT_ACCEPTED = ["تخفیف می‌دید؟", "تخفیف می‌دید"]

# docs/content/overlays/en-ar/b1_unit50.yaml:59 - Arabic kasratan (U+064D).
AR_SECOND_OFFICE = "على الرغم من أن الأمر يحمل مخاطرة أنا أؤيد فتح مكتب ثانٍ"

ARABIC = dict(exercise_type="translation", script="arabic")


# --- ZWNJ: present-expected / absent-given ---------------------------------
def test_zwnj_expected_joined_response_is_correct():
    assert grade_answer(KHAHESH_MIKONAM_JOINED, KHAHESH_MIKONAM, **ARABIC) == "correct"


def test_zwnj_expected_space_response_is_correct():
    # Persian mobile keyboards commonly produce a plain space where the
    # orthography wants a ZWNJ.
    assert grade_answer(KHAHESH_MIKONAM_SPACED, KHAHESH_MIKONAM, **ARABIC) == "correct"


def test_zwnj_on_both_sides_is_correct():
    assert grade_answer(KHAHESH_MIKONAM, KHAHESH_MIKONAM, **ARABIC) == "correct"


# --- ZWNJ: the reverse direction (learner types it, content lacks it) ------
def test_zwnj_response_against_joined_expected_is_correct():
    assert grade_answer(KHAHESH_MIKONAM, KHAHESH_MIKONAM_JOINED, **ARABIC) == "correct"


def test_zwnj_response_against_spaced_expected_is_correct():
    assert grade_answer(KHAHESH_MIKONAM, KHAHESH_MIKONAM_SPACED, **ARABIC) == "correct"


def test_mixed_zwnj_usage_within_one_sentence_is_correct():
    # One ZWNJ dropped, one typed as a space, in the same answer - the case
    # a "strip all ZWNJ" or "ZWNJ -> space" single canonical form misses.
    mixed = "امروز ظرف‌ها رو می شورم"
    expected = "امروز ظرف‌ها رو می‌شورم"  # docs/content/overlays/en-fa/a1_unit32.yaml
    assert grade_answer(mixed, expected, **ARABIC) == "correct"
    assert grade_answer("امروز ظرفها رو می‌شورم", expected, **ARABIC) == "correct"


def test_speak_response_zwnj_free_transcript_is_correct():
    # The 49 impossible items: an STT transcript never contains U+200C.
    transcript = "خانواده ی من کوچیکه یک برادر دارم خواهر ندارم"
    assert (
        grade_answer(
            transcript, SPEAK_FAMILY, exercise_type="speak_response", script="arabic"
        )
        == "correct"
    )


def test_zwnj_difference_grades_correct_not_almost():
    # "almost" would still deny full XP/SRS credit on some paths - a
    # missing invisible character must land on "correct".
    assert grade_answer(KHAHESH_MIKONAM_JOINED, KHAHESH_MIKONAM, **ARABIC) != "almost"


# --- harakat (defect class 1.30), both directions --------------------------
def test_harakat_absent_in_response_is_correct():
    assert grade_answer("لطفا آهسته تر صحبت کنید", LOTFAN_AHESTETAR, **ARABIC) == "correct"


def test_harakat_present_in_response_absent_in_expected_is_correct():
    assert grade_answer("لطفاً", "لطفا", **ARABIC) == "correct"


def test_persian_kasra_and_damma_are_ignored():
    # docs/content/overlays/en-fa/a1_unit31.yaml (کِی) and the fa nine (نُه).
    assert grade_answer("کی", "کِی", **ARABIC) == "correct"
    assert grade_answer("نه", "نُه", **ARABIC) == "correct"


def test_arabic_kasratan_is_ignored():
    undiacritized = AR_SECOND_OFFICE.replace("ثانٍ", "ثان")
    assert grade_answer(undiacritized, AR_SECOND_OFFICE, **ARABIC) == "correct"


def test_tatweel_is_ignored():
    assert grade_answer("سـلام", "سلام", **ARABIC) == "correct"
    assert grade_answer("سلام", "سـلام", **ARABIC) == "correct"


def test_bidi_and_zero_width_marks_are_ignored():
    # RLM/LRM ride along on copy-paste out of RTL text.
    assert grade_answer("‏سلام‎", "سلام", **ARABIC) == "correct"


# --- NEGATIVE: script confusion must still never be forgiven ---------------
def test_arabic_kaf_vs_persian_keheh_still_incorrect():
    assert grade_answer("كتاب", "کتاب", **ARABIC) == "incorrect"
    # ...and also when the author opted into typo tolerance.
    assert (
        grade_answer(
            "كتاب", "کتاب", exercise_type="translation", orthography_strict=False
        )
        == "incorrect"
    )


def test_arabic_yeh_vs_persian_yeh_still_incorrect():
    assert grade_answer("مي‌کنم", "می‌کنم", **ARABIC) == "incorrect"
    assert (
        grade_answer(
            "مي‌کنم", "می‌کنم", exercise_type="translation", orthography_strict=False
        )
        == "incorrect"
    )


def test_script_confusion_is_not_hidden_by_a_missing_zwnj():
    # Arabic kaf AND no ZWNJ: the length mismatch used to make
    # _single_substitution_pair() return None, so the wrong-script letter
    # would have slipped past the hard block on a tolerant exercise.
    assert is_script_confusion("میكنم", "می‌کنم") is True
    assert (
        grade_answer(
            "میكنم", "می‌کنم", exercise_type="translation", orthography_strict=False
        )
        == "incorrect"
    )


def test_script_confusion_is_not_hidden_by_a_missing_harakat():
    assert is_script_confusion("كتاب", "کِتاب") is True


def test_teh_marbuta_and_alef_maksura_still_incorrect():
    assert grade_answer("خانة", "خانه", **ARABIC) == "incorrect"
    assert grade_answer("على", "علی", **ARABIC) == "incorrect"


def test_heh_goal_is_not_treated_as_invisible_formatting():
    # ۀ is a visible letter in ARABIC_PERSIAN_SCRIPT_PAIRS, and the
    # combining hamza that composes it is deliberately NOT stripped.
    assert grade_answer("خانۀ", "خانه", **ARABIC) == "incorrect"
    assert is_invisible_formatting_only_difference("خانۀ", "خانه") is False


# --- NEGATIVE: real errors must still be incorrect -------------------------
def test_wrong_persian_word_still_incorrect():
    assert grade_answer("سلام", KHAHESH_MIKONAM, **ARABIC) == "incorrect"


def test_wrong_verb_person_still_incorrect():
    # می‌کنی (you do) vs می‌کنم (I do) - a real one-letter contrast.
    assert grade_answer("خواهش می‌کنی", KHAHESH_MIKONAM, **ARABIC) == "incorrect"


def test_dropped_word_space_is_still_incorrect():
    # Only a ZWNJ may vanish; an authored word space may not.
    assert grade_answer("خواهشمیکنم", KHAHESH_MIKONAM, **ARABIC) == "incorrect"


def test_missing_word_still_incorrect():
    assert grade_answer("خواهش", KHAHESH_MIKONAM, **ARABIC) == "incorrect"


# --- strictness / other-script behaviour must be unchanged -----------------
def test_orthography_strict_still_forgives_only_invisible_formatting():
    assert (
        grade_answer(
            KHAHESH_MIKONAM_JOINED, KHAHESH_MIKONAM, **ARABIC, orthography_strict=True
        )
        == "correct"
    )
    # A checkpoint (which forces orthography_strict=True) still refuses a
    # genuine distance-1 error.
    assert (
        grade_answer(
            "خواهش می‌کنی", KHAHESH_MIKONAM, **ARABIC, orthography_strict=True
        )
        == "incorrect"
    )


def test_latin_grading_is_untouched():
    assert grade_answer("hola", "hola", exercise_type="translation", script="latin") == "correct"
    assert grade_answer("hoal", "hola", exercise_type="translation", script="latin") == "almost"
    assert grade_answer("xyz", "hola", exercise_type="translation", script="latin") == "incorrect"


def test_case_sensitive_exercises_are_untouched():
    assert (
        grade_answer(
            "sie", "Sie", exercise_type="translation", script="latin", case_sensitive=True
        )
        == "incorrect"
    )


# --- the paths that never reach grade_answer() -----------------------------
def test_multi_answer_wrapper_forgives_zwnj():
    correct = {"canonical": SPEAK_DISCOUNT_ACCEPTED[0], "accepted": SPEAK_DISCOUNT_ACCEPTED}
    assert grade("تخفیف میدید", correct, "speak_response", script="arabic") == "correct"
    assert grade("تخفیف می دید؟", correct, "speak_response", script="arabic") == "correct"
    assert grade("تخفیف نمیدید", correct, "speak_response", script="arabic") == "incorrect"


def test_word_order_tokens_forgive_zwnj():
    assert grade(["خواهش", "میکنم"], "خواهش می‌کنم", "word_order", script="arabic") == "correct"
    assert (
        grade(
            ["خواهش", "میکنم"],
            {"canonical": ["خواهش", "می‌کنم"], "accepted": [["خواهش", "می‌کنم"]]},
            "word_order",
            script="arabic",
        )
        == "correct"
    )
    assert grade(["میکنم", "خواهش"], "خواهش می‌کنم", "word_order", script="arabic") == "incorrect"


# --- helper-level unit tests ----------------------------------------------
def test_strip_invisible_formatting():
    assert strip_invisible_formatting("لطفاً") == "لطفا"
    assert strip_invisible_formatting("سـلام") == "سلام"
    # ZWNJ deliberately survives - it may have to line up with a space.
    assert ZWNJ in strip_invisible_formatting(KHAHESH_MIKONAM)
    assert strip_invisible_formatting("hola") == "hola"


def test_is_invisible_formatting_only_difference():
    assert is_invisible_formatting_only_difference(KHAHESH_MIKONAM, KHAHESH_MIKONAM_JOINED)
    assert is_invisible_formatting_only_difference(KHAHESH_MIKONAM, KHAHESH_MIKONAM_SPACED)
    assert is_invisible_formatting_only_difference("لطفاً", "لطفا")
    assert not is_invisible_formatting_only_difference("کتاب", "كتاب")
    assert not is_invisible_formatting_only_difference("خواهشمیکنم", KHAHESH_MIKONAM)
    assert not is_invisible_formatting_only_difference("hola", "hoal")


def test_answers_equivalent_recurses_into_token_lists():
    assert answers_equivalent(["خواهش", "میکنم"], ["خواهش", "می‌کنم"])
    assert not answers_equivalent(["خواهش"], ["خواهش", "می‌کنم"])
    assert not answers_equivalent(["خواهش", "میكنم"], ["خواهش", "می‌کنم"])


def test_zwnj_flood_response_is_not_a_dos():
    # The learner side is attacker-controlled; the matcher is linear-DP
    # behind an O(n) gate, not a backtracking regex.
    assert grade_answer(ZWNJ * 4000 + "سلام", "سلام", **ARABIC) == "correct"
    assert grade_answer(ZWNJ.join("ا" * 2000), "سلام", **ARABIC) == "incorrect"
