import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "check_lexeme_lengths.py"
    spec = importlib.util.spec_from_file_location("check_lexeme_lengths", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ok_specs_pass():
    mod = _load()
    spec = {"token": "x", "part_of_speech": "noun", "english_gloss": "a" * 255, "content_key": "k"}
    assert mod.check_specs([spec]) == []


def test_overlong_gloss_and_pos_are_flagged():
    mod = _load()
    spec = {"token": "x", "part_of_speech": "p" * 41, "english_gloss": "a" * 256, "content_key": "k"}
    problems = mod.check_specs([spec], "src.py")
    assert len(problems) == 2
    assert any("english_gloss" in p and "256" in p for p in problems)


def test_limits_match_model_columns():
    import re

    src = (Path(__file__).resolve().parents[2] / "backend/app/models/entities.py").read_text()
    block = src.split("class Lexeme", 1)[1].split("\nclass ", 1)[0]
    for field, limit in _load().LIMITS.items():
        field = {"lesson_content_key": "provenance_lesson_content_key", "content_key": "provenance_content_key"}.get(field, field)
        m = re.search(rf"{field}: Mapped\[str\] = mapped_column\(String\((\d+)\)", block)
        assert m, field
    for field, limit in _load().LIMITS.items():
        f = {"lesson_content_key": "provenance_lesson_content_key", "content_key": "provenance_content_key"}.get(field, field)
        assert int(re.search(rf"{f}: Mapped\[str\] = mapped_column\(String\((\d+)\)", block).group(1)) == limit
