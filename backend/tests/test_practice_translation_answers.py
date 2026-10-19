"""Practice translation items accept every same-gloss synonym, and English
answers treat contractions as their full forms (session9 review findings)."""
import random
from types import SimpleNamespace

from app.practice.service import build_prompt, translation_accepted_answers
from app.review.grading import grade


def lexeme(token, gloss, language="prs", pos="noun", **tags):
    return SimpleNamespace(
        id=token,
        token=token,
        english_gloss=gloss,
        language_code=language,
        part_of_speech=pos,
        agreement_tags={"semantic": "family", **tags},
    )


SLOT = {"language_code": "prs", "part_of_speech": "noun", "agreement_tags": {"semantic": "family"}}
BRADARAM = lexeme("برادرم", "my brother")
DADASHAM = lexeme("داداشم", "My  Brother")
KHAHARAM = lexeme("خواهرم", "my sister")
OTHER_POS = lexeme("برادرانه", "my brother", pos="adjective")
POOL = [BRADARAM, DADASHAM, KHAHARAM, OTHER_POS]


def slot_text_template():
    return SimpleNamespace(
        type="translation",
        slots={"item": SLOT},
        frame={"text": "{item}", "language_code": "prs", "direction": "rtl", "slot_rendering": {"item": "english_gloss"}},
        answer_derivation={"kind": "slot_text", "slot": "item"},
    )


def test_slot_text_translation_accepts_same_gloss_synonyms():
    answer = translation_accepted_answers(slot_text_template(), {"item": BRADARAM}, POOL, "برادرم")
    assert answer == {"canonical": "برادرم", "accepted": ["برادرم", "داداشم"]}
    for learner in ("برادرم", "داداشم"):
        assert grade(learner, answer, "translation", script="arabic", language_code="prs") == "correct"
    assert grade("خواهرم", answer, "translation", script="arabic", language_code="prs") == "incorrect"


def test_slot_text_translation_without_synonyms_keeps_plain_answer():
    answer = translation_accepted_answers(slot_text_template(), {"item": KHAHARAM}, POOL, "خواهرم")
    assert answer == "خواهرم"


def test_render_frame_translation_expands_synonyms_in_the_frame():
    template = SimpleNamespace(
        type="translation",
        slots={"item": SLOT},
        frame={"text": "This is {item}", "language_code": "en", "direction": "ltr", "slot_rendering": {"item": "english_gloss"}},
        answer_derivation={"kind": "render_frame", "frame": {"text": "این {item} است", "language_code": "prs", "direction": "rtl"}},
    )
    course = SimpleNamespace(source_language="en", target_language="prs")
    prompt, answer = build_prompt(template, course, {"item": DADASHAM}, POOL, random.Random(1))
    assert prompt["text_blocks"][1]["text"] == "This is My  Brother"
    assert answer == {"canonical": "این داداشم است", "accepted": ["این داداشم است", "این برادرم است"]}
    assert grade("این برادرم است", answer, "translation", script="arabic", language_code="prs") == "correct"


def test_english_contractions_are_equivalent_to_full_forms():
    pairs = [
        ("I'm a student", "I am a student"),
        ("I don't know", "I do not know"),
        ("It's cold today", "It is cold today"),
        ("She can't come", "She cannot come"),
        ("She can not come", "She can't come"),
        ("We won't be late", "We will not be late"),
        ("They've already eaten", "They have already eaten"),
        ("I'd like a coffee", "I would like a coffee"),
        ("He's been there", "He has been there"),
        ("I’m ready.", "I am ready"),
    ]
    for learner, correct in pairs:
        assert grade(learner, correct, "translation", script="latin", language_code="en") == "correct", learner
        assert grade(correct, learner, "translation", script="latin", language_code="en") == "correct", learner
    assert grade("I'm ready", "I am ready", "speak_response", script="latin", language_code="en", input_mode="spoken") == "correct"
    accepted = {"canonical": "I am fine", "accepted": ["I am fine", "I am okay"]}
    assert grade("I'm okay", accepted, "translation", script="latin", language_code="en") == "correct"


def test_english_contraction_rule_is_conservative():
    # Possessive 's is not expanded.
    assert grade("John is car", "John's car", "translation", script="latin", language_code="en") == "incorrect"
    # A wrong expansion stays wrong.
    assert grade("I'm not hungry", "I am hungry", "translation", script="latin", language_code="en") == "incorrect"
    assert grade("It's", "It was", "translation", script="latin", language_code="en") == "incorrect"
    # Only English answers.
    assert grade("I am", "I'm", "translation", script="latin", language_code="nl") == "incorrect"
    # A typo on top of a contraction is still only "almost".
    assert grade("I'm reddy to go", "I am ready to go", "translation", script="latin", language_code="en") == "almost"
    # Dictation stays byte-strict.
    assert grade("I am ready", "I'm ready", "dictation", script="latin", language_code="en") == "incorrect"
