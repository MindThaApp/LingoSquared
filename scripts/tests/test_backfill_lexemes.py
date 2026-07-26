import importlib.util
from pathlib import Path


def _load(filename, module_name):
    path = Path(__file__).resolve().parents[1] / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_backfill():
    return _load("backfill_lexemes.py", "lingosquared_backfill")


def load_backfill_en_prs():
    return _load("backfill_lexemes_en_prs.py", "lingosquared_backfill_en_prs")


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


# --- Generated per-unit/per-lesson tags (_unit_semantic_tags) ------------
# Guard the Persian-aware behavior added 2026-07-26 (wave 4). These pin the
# alpha-guard (ZWNJ + combining diacritics allowed, digits/punctuation/spaces
# rejected), the POS gate, the metalanguage exclusion, and the two-tag shape,
# so a later refactor of the guard cannot silently change tag emission.


def test_en_fa_unit_semantic_tags_shape_and_alpha_guard():
    tags = load_backfill()._unit_semantic_tags

    # a plain Farsi noun -> unit-wide + zero-padded per-lesson tag
    assert tags("a1_unit33", 2, "نان", "noun") == [
        "en_fa_a1_unit33_words",
        "en_fa_a1_unit33_lesson02_words",
    ]
    # ZWNJ compound and a combining tanwin stay taggable
    assert tags("a1_unit33", 1, "می‌کنم", "verb")
    assert tags("a1_unit01", 1, "فعلاً", "adverb")
    # digits (Persian or ASCII), embedded spaces, attached punctuation: rejected
    assert tags("a1_unit33", 1, "۱۲۳", "noun") == []
    assert tags("a1_unit33", 1, "123", "adjective") == []
    assert tags("a1_unit33", 1, "the house", "noun") == []
    # non-content POS: not a vocabulary drill
    assert tags("a1_unit33", 1, "خونه", "pronoun") == []
    assert tags("a1_unit33", 1, "به", "preposition") == []
    # phrase POS skips the single-token alpha-guard (spaces allowed)
    assert tags("a1_unit33", 1, "قد کوتاه", "phrase")


def test_en_prs_unit_semantic_tags_excludes_metalanguage():
    prs = load_backfill_en_prs()
    tags = prs._unit_semantic_tags

    # ordinary Dari vocabulary is tagged...
    assert tags("a1_unit06", 1, "چپ", "noun") == [
        "en_prs_a1_unit06_words",
        "en_prs_a1_unit06_lesson01_words",
    ]
    # ...but the two grammar-term tokens are held out even though POS=noun
    assert prs.METALANGUAGE_TOKENS == {"فعل", "فاعل"}
    assert tags("b1_unit01", 1, "فعل", "noun") == []
    assert tags("b1_unit01", 1, "فاعل", "noun") == []


def test_en_prs_metalanguage_tokens_carry_no_generated_tag_in_specs():
    # Integration guard: whatever unit فعل/فاعل are introduced in, no spec for
    # them ends up carrying an en_prs_ generated tag.
    specs = list(load_backfill_en_prs().iter_specs())
    for spec in specs:
        if spec["token"] in {"فعل", "فاعل"}:
            generated = [
                t
                for t in (spec.get("agreement_tags") or {}).get("semantic", [])
                if str(t).startswith("en_prs_")
            ]
            assert generated == [], (spec["token"], generated)
