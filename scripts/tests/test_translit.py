import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from translit import attach, rules  # noqa: E402
from translit.common import is_target_string, latin_ok, normalize_key, STORE_DIR  # noqa: E402


def test_ru_rules():
    assert rules.ru("Привет") == "Privet"
    assert rules.ru("Мне грустно") == "Mne grustno"
    assert rules.ru("Я учитель.") == "Ya uchitel."
    assert rules.ru("Здравствуйте") == "Zdravstvuyte"
    assert rules.ru("щи") == "shchi"


def test_hi_rules_schwa_deletion():
    assert rules.hi("घर") == "ghar"
    assert rules.hi("कमल") == "kamal"
    assert rules.hi("समझदार") == "samajhdaar"
    assert rules.hi("नमस्ते") == "namaste"
    assert rules.hi("मुझे सिर में दर्द है।") == "mujhe sir mein dard hai."
    assert rules.hi("मेरा नाम प्रिया है") == "mera naam priya hai"


def test_key_parity_with_backend():
    from app.review.translit_nudge import normalize_key as backend_key

    for lang, s in [
        ("fa", "كتاب  می‌روم‎"),
        ("fa", "خُدا"),
        ("ar", "مَال"),
        ("ar", "كتاب ي"),
        ("ru", "*Привет*  мир"),
        ("hi", "नमस्ते।"),
    ]:
        assert normalize_key(s, lang) == backend_key(s, lang)


def test_target_string_filter():
    assert is_target_string("Привет", "ru")
    assert not is_target_string("Dima mówi: Привет", "ru")
    assert not is_target_string("'Привет' का मतलब नमस्ते है", "ru")
    assert is_target_string("خداحافظ", "fa")
    assert not is_target_string("w_забыть", "ru")
    assert latin_ok("khodâ hâfez") and not latin_ok("хода")


def test_stores_are_well_formed():
    for p in STORE_DIR.glob("*.json"):
        st = json.loads(p.read_text(encoding="utf-8"))
        lang = st["lang"]
        for k, e in st["entries"].items():
            assert normalize_key(k, lang) == k
            assert set(e) == {"romanization", "scheme", "source", "reviewed"}
            assert e["source"] in {"rule", "llm", "human"} and isinstance(e["reviewed"], bool)
            assert latin_ok(e["romanization"])


def _ex(type_, key, prompt, correct):
    return {"type": type_, "content_key": key, "prompt": prompt, "correct_response": correct}


def test_attach_no_answer_leak(monkeypatch):
    monkeypatch.setitem(attach._STORES, "ru", {"Привет": {"romanization": "Privet"}, "Пока": {"romanization": "Poka"}})
    blk = lambda t: {"text": t, "language_code": "ru", "direction": "ltr"}
    # a prompt block equal to the correct answer is not romanized
    ex = _ex("writing_prompt", "ru.x", {"text_blocks": [blk("Привет")], "options": ["Привет", "Пока"]}, "Привет")
    attach.attach_exercise(ex, "ru")
    assert "translit" not in ex["prompt"]["text_blocks"][0]
    assert ex["prompt"]["translit_map"] == {"Привет": "Privet", "Пока": "Poka"}
    # romanize exercises and script_ramp lessons get nothing
    ex = _ex("translation", "ru.a1.romanize_hello", {"text_blocks": [blk("Привет")]}, "privet")
    attach.attach_exercise(ex, "ru")
    assert "translit" not in ex["prompt"]["text_blocks"][0]
    ex = _ex("multiple_choice", "ru.y", {"text_blocks": [], "options": ["Привет"]}, "Привет")
    attach.attach_exercise(ex, "ru", "script_ramp")
    assert "translit_map" not in ex["prompt"]
    # listening exercises: no prompt-block translit
    ex = _ex("listen_type", "ru.z", {"text_blocks": [blk("Пока")]}, "Привет")
    attach.attach_exercise(ex, "ru")
    assert "translit" not in ex["prompt"]["text_blocks"][0]
    # cards: blocks in the target language only
    card = {"text_blocks": [blk("Привет"), {"text": "Hi", "language_code": "en", "direction": "ltr"}]}
    attach.attach_card(card, "ru")
    assert card["text_blocks"][0]["translit"] == "Privet" and "translit" not in card["text_blocks"][1]


def test_attach_carries_reviewed_flag(monkeypatch):
    monkeypatch.setitem(
        attach._STORES, "ru",
        {"Привет": {"romanization": "Privet", "reviewed": True}, "Пока": {"romanization": "Poka", "reviewed": False}},
    )
    blk = lambda t: {"text": t, "language_code": "ru", "direction": "ltr"}
    card = {"text_blocks": [blk("Привет"), blk("Пока")]}
    attach.attach_card(card, "ru")
    assert card["text_blocks"][0]["translit_reviewed"] is True
    assert card["text_blocks"][1]["translit_reviewed"] is False
    ex = _ex("multiple_choice", "ru.q", {"text_blocks": [], "options": ["Привет", "Пока"]}, "Привет")
    attach.attach_exercise(ex, "ru")
    assert ex["prompt"]["translit_reviewed_list"] == ["Привет"]
