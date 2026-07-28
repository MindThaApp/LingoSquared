"""Regression tests for casefold de-duplication of multiple_choice /
listen_select distractors (`_distractor_values`).

Background: several semantic-tag pools carry the same word twice as separate
Lexeme rows — a lowercase form and a capitalized sentence-initial/label form
whose gloss differs only by case ("apples"/"Apples", "library"/"Library").
Exact-string dedup let both survive, so a recognition item could show two
options meaning the identical thing with only one graded correct — a real
"more than one defensible answer" defect (2026-07-27 en-nl native review:
produce / place / direction_word pools). `_distractor_values` now dedupes by
casefold and folds the answer's own case-variant out.

These tests exercise the pure distractor-selection function directly with
in-memory ORM objects (no DB rows are persisted). NOTE: article-reworded
capitalized variants ("the hospital"/"Hospital") are intentionally NOT merged
here — that is the blanket-tagger contamination fixed content-side via the
`_pure` / route_word narrow-tag wave, and is asserted as a known boundary below.
"""

import random

from app.models import Lexeme, PracticeTemplate
from app.practice.service import _distractor_values

SLOT = {"language_code": "en", "part_of_speech": "noun"}


def _lex(gloss: str) -> Lexeme:
    return Lexeme(
        token=gloss,
        language_code="en",
        part_of_speech="noun",
        english_gloss=gloss,
        agreement_tags={},
    )


def _template() -> PracticeTemplate:
    return PracticeTemplate(
        type="multiple_choice",
        frame={"text": "{item}"},
        slots={"item": SLOT},
        answer_derivation={"kind": "slot_gloss", "slot": "item"},
    )


def _options(glosses, answer, seed):
    """Mirror build_prompt's multiple_choice option assembly."""
    rng = random.Random(seed)
    lexemes = [_lex(g) for g in glosses]
    distractors = _distractor_values(_template(), answer, lexemes, rng)
    options = [answer, *distractors]
    return list(dict.fromkeys(options))


PRODUCE = ["apples", "Apples", "pears", "Pears", "tomatoes", "Tomatoes",
           "bell peppers", "Bell peppers"]


def test_answer_case_variant_is_never_a_distractor():
    for seed in range(200):
        opts = _options(PRODUCE, "apples", seed)
        assert "Apples" not in opts, f"seed {seed}: capitalized answer-variant leaked"


def test_no_two_options_are_casefold_equal():
    for seed in range(200):
        opts = _options(PRODUCE, "apples", seed)
        folds = [o.casefold() for o in opts]
        assert len(folds) == len(set(folds)), f"seed {seed}: duplicate meaning in {opts}"


def test_lowercase_representative_preferred_over_capitalized():
    # With both cases present, the surviving distractor for each meaning is the
    # lowercase-initial form, so no odd capitalized option appears mid-list.
    rng = random.Random(1)
    lexemes = [_lex(g) for g in PRODUCE]
    distractors = _distractor_values(_template(), "apples", lexemes, rng)
    assert distractors, "expected at least one distractor"
    assert all(not d[:1].isupper() for d in distractors), distractors


def test_all_caps_label_with_no_lowercase_variant_is_kept():
    # Legitimate all-caps labels (START/DOEL) have no lowercase sibling to
    # prefer, so they must survive as valid distractors.
    glosses = ["the route", "START", "DOEL", "the station"]
    rng = random.Random(0)
    lexemes = [_lex(g) for g in glosses]
    distractors = _distractor_values(_template(), "the route", lexemes, rng)
    assert "START" in distractors and "DOEL" in distractors, distractors


def test_pool_padded_only_by_case_dups_starves_below_option_floor():
    # yes/Yes + no/No is two real meanings; after casefold-dedup the answer
    # "yes" yields a single distractor "no" -> [answer, "no"] has < 3 options,
    # so the caller (build_prompt) rejects the instance and falls back. This is
    # the intended safe degradation, not a crash.
    rng = random.Random(5)
    lexemes = [_lex(g) for g in ["yes", "Yes", "no", "No"]]
    distractors = _distractor_values(_template(), "yes", lexemes, rng)
    assert distractors == ["no"], distractors
    assert len(["yes", *distractors]) < 3


def test_deterministic_for_fixed_seed():
    a = _distractor_values(_template(), "apples", [_lex(g) for g in PRODUCE], random.Random(7))
    b = _distractor_values(_template(), "apples", [_lex(g) for g in PRODUCE], random.Random(7))
    assert a == b


def test_known_boundary_article_reworded_variant_is_not_merged():
    # Documents the scope limit: "the hospital"/"Hospital" differ by wording,
    # not just case, so gloss-casefold does NOT merge them. Fixing this pair is
    # the content-side `_pure`/route_word narrow-tag wave's job, not this
    # function's. If a future token-identity dedup lands, update this test.
    glosses = ["library", "Library", "the hospital", "Hospital", "the bank", "Bank"]
    rng = random.Random(3)
    lexemes = [_lex(g) for g in glosses]
    # For answer "the hospital", "Hospital" remains a candidate distractor.
    all_distractors = set()
    for seed in range(50):
        all_distractors.update(
            _distractor_values(_template(), "the hospital", [_lex(g) for g in glosses], random.Random(seed))
        )
    assert "Hospital" in all_distractors  # known, documented gap
