import importlib.util
from pathlib import Path

_p = Path(__file__).resolve().parents[1] / "_answer_leakage_check.py"
_s = importlib.util.spec_from_file_location("answer_leakage_check", _p)
m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(m)


def _ex(instruction, ans, **kw):
    return {"instruction": instruction, "accepted_answers": [{"value": ans, "status": "correct"}], **kw}


def _real(typ, text=None):
    blocks = [{"text": text}] if text else []
    return {"type": typ, "prompt": {"target_blocks": blocks}}


def run(ex, real):
    return list(m.check_item(ex, real, False))


def test_reply_exactly_flagged():
    assert run(_ex('Reply with exactly: "Да, именно так."', "Да, именно так."), _real("dialogue_response"))


def test_fill_blank_single_word_in_instruction():
    assert run(_ex("Complete the sentence with *tuttavia*", "tuttavia"), _real("fill_in_blank", "Sì, ___ costa."))


def test_clean_fill_blank_not_flagged():
    assert not run(_ex("Complete the sentence.", "tuttavia"), _real("fill_in_blank", "Sì, ___ costa."))


def test_partial_phrase_not_flagged():
    assert not run(_ex("Write using *Posso fare in modo che*", "Posso fare in modo che Sam riceva"), _real("writing_prompt"))


def test_choice_prompt_equals_option_flagged_but_substring_not():
    assert run(_ex("Pick", "kaufen"), _real("multiple_choice", "Kaufen"))
    assert not run(_ex("Which part?", "wenn er kommt"), _real("multiple_choice", "Wenn er kommt, gehe ich."))


def test_reading_passage_exempt():
    assert not run(_ex("Q?", "pâine și pui"), _real("reading_comprehension", "Aș dori pâine și pui."))


def test_accent_flag():
    ex, real = _ex("Write: perché no", "perche no"), _real("writing_prompt")
    assert not run(ex, real)
    assert list(m.check_item(ex, real, True))
