"""Romanized-input nudge: a Latin answer matching the stored romanization of a correct
target-script answer is "almost" (partial credit), never "correct", never for Latin answers."""
import json

import pytest

from app.review import translit_nudge
from app.review.grading import grade, grade_answer
from app.review.translit_nudge import NUDGE_MESSAGE, normalize_key, romanized_input_nudge
from app.schemas.api import TeachingCard, TextBlock


def test_ru_romanization_is_almost():
    assert grade_answer("privet", "Привет", exercise_type="translation", script="cyrillic", language_code="ru") == "almost"
    assert grade_answer("Privet!", "Привет", exercise_type="translation", script="cyrillic", language_code="ru") == "almost"


def test_hi_romanization_is_almost_and_folds_spelling():
    assert grade_answer("Namaste", "नमस्ते", exercise_type="writing_prompt", script="devanagari", language_code="hi") == "almost"
    assert grade_answer("dhanyavaad", "धन्यवाद", exercise_type="translation", script="devanagari", language_code="hi") == "almost"


def test_native_script_still_correct_and_wrong_latin_still_incorrect():
    assert grade_answer("Привет", "Привет", exercise_type="translation", script="cyrillic", language_code="ru") == "correct"
    assert grade_answer("zdravstvuyte", "Привет", exercise_type="translation", script="cyrillic", language_code="ru") == "incorrect"
    assert grade_answer("hello", "Привет", exercise_type="translation", script="cyrillic", language_code="ru") == "incorrect"


def test_latin_correct_answers_unaffected():
    # romanize_* exercises have a Latin answer: graded as before
    assert grade_answer("salam", "salam", exercise_type="translation", script="arabic", language_code="fa") == "correct"
    assert grade_answer("salam", "Salam", exercise_type="translation", script="latin", language_code="fa") == "correct"


def test_multi_answer_and_grade_entrypoint():
    correct = {"canonical": "Привет", "accepted": ["Привет", "Спасибо"]}
    assert grade("privet", correct, "translation", script="cyrillic", language_code="ru") == "almost"
    assert grade("spasibo", correct, "translation", script="cyrillic", language_code="ru") == "almost"
    assert grade("privet", "Привет", "multiple_choice", script="cyrillic", language_code="ru") == "incorrect"


def test_other_languages_and_missing_store_are_untouched():
    assert not translit_nudge.romanized_input_matches("hallo", "Hallo", "de")
    assert not translit_nudge.romanized_input_matches("privet", "Привет", None)


def test_nudge_message():
    assert romanized_input_nudge("privet", "Привет", "ru") == NUDGE_MESSAGE == "Right — now write it in script"
    assert romanized_input_nudge("Привет", "Привет", "ru") is None


def test_fa_with_mock_store(monkeypatch):
    key = normalize_key("خداحافظ", "fa")
    monkeypatch.setattr(translit_nudge, "_entries", lambda lang: {key: "khodâ hâfez"} if lang == "fa" else {})
    assert grade_answer("khoda hafez", "خداحافظ", exercise_type="translation", script="arabic", language_code="fa") == "almost"
    assert grade_answer("khodahafez", "خداحافظ", exercise_type="translation", script="arabic", language_code="fa") == "almost"
    assert grade_answer("salam", "خداحافظ", exercise_type="translation", script="arabic", language_code="fa") == "incorrect"
    # Arabic yeh/kaf and harakat fold into the same key
    assert normalize_key("خُدا", "fa") == normalize_key("خدا", "fa")


def test_text_block_translit_is_additive():
    plain = TextBlock(text="hi", language_code="en", direction="ltr")
    assert "translit" not in plain.model_dump()
    rich = TextBlock(text="Привет", language_code="ru", direction="ltr", translit="Privet")
    assert rich.model_dump()["translit"] == "Privet"
    card = TeachingCard(kind="vocabulary", text_blocks=[rich, plain])
    dumped = card.model_dump()
    assert dumped["text_blocks"][0]["translit"] == "Privet"
    assert "translit" not in dumped["text_blocks"][1]
    assert "translit" not in json.dumps(plain.model_dump())


def test_mirror_in_sync_with_store_keys_are_normalised():
    for lang in ("ru", "hi"):
        for key in list(translit_nudge._entries(lang))[:500]:
            assert normalize_key(key, lang) == key


def test_strict_and_choice_types_never_get_romanization_credit():
    assert grade_answer("privet", "Привет", exercise_type="translation", script="cyrillic", language_code="ru", orthography_strict=True) == "incorrect"
    assert grade_answer("privet", "Привет", exercise_type="multiple_choice", script="cyrillic", language_code="ru") == "incorrect"


def test_single_letter_drills_not_credited():
    assert grade_answer("a", "а", exercise_type="writing_prompt", script="cyrillic", language_code="ru") == "incorrect"


def test_conversation_romanized_reply_is_not_credited_and_flagged():
    from app.api.router import conversation_reply_result

    node = {"accepted_variants": ["Привет"], "answer_language_code": "ru"}
    kw = dict(node=node, script="cyrillic", language_code="ru")
    assert conversation_reply_result(response="privet", **kw) == ("incorrect", None, True)
    assert conversation_reply_result(response="Привет", **kw) == ("correct", "Привет", False)
    assert conversation_reply_result(response="zzz", **kw) == ("incorrect", None, False)
