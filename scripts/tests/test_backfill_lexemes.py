import importlib.util
from pathlib import Path


def load_backfill():
    path = Path(__file__).resolve().parents[1] / "backfill_lexemes.py"
    spec = importlib.util.spec_from_file_location("lingosquared_backfill", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backfill_specs_cover_both_languages_with_unique_identities():
    backfill = load_backfill()
    specs = list(backfill.iter_specs())
    identities = {
        (spec["language_code"], spec["token"], spec["part_of_speech"])
        for spec in specs
    }

    assert len(identities) == len(specs)
    assert sum(spec["language_code"] == "fa" for spec in specs) > 101
    assert sum(spec["language_code"] == "en" for spec in specs) > 100


def test_backfill_specs_expose_tags_used_by_pilot_templates():
    backfill = load_backfill()
    specs = list(backfill.iter_specs())
    tags = {
        tag
        for spec in specs
        if spec["language_code"] == "fa"
        for tag in spec["agreement_tags"].get("semantic", [])
    }

    assert {
        "letter",
        "greeting",
        "time_period",
        "farewell",
        "wellbeing_question",
        "person_name",
        "country",
        "nationality",
        "origin_marker",
        "class_word",
        "dialogue_word",
    } <= tags
