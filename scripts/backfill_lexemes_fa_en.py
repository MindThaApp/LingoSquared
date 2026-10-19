#!/usr/bin/env python3
"""Idempotently backfill reviewed fa-en A1 lexemes (English target) from
the shared en realization units 1, 2, and 3 (numbers/ages/prices/phones/
market -- added 2026-07-05 by the practice-pool-sync lane, reusing the
EN_POS/en_agreement_tags additions the nl-en lane already made to
_en_target_lexeme_common.py for this same unit; only the Farsi gloss
dict needed extending here, no new POS/tag classification work).

Written directly (not via Codex -- Codex was rate-limited at authoring
time) mirroring scripts/backfill_lexemes.py's structure and rigor.
Target-side English POS/semantic-tag classification is shared with
backfill_lexemes_nl_en.py/backfill_lexemes_prs_en.py via
scripts/_en_target_lexeme_common.py; the Farsi gloss for each token is
this script's own (glosses are course/source-language-specific, see
the IMPORTANT note in that shared module -- a real bug where an
earlier version of this pattern glossed English words with themselves
was caught and fixed during nl-en's live verification).

Deliberately scoped to TARGET-side (English) lexemes only, not also a
parallel Farsi "source-side" lexeme pool: verified by grepping the
existing en-fa pilot pack that no slot_preset there ever uses a
source-language slot (every slot_preset in production is
target-language only) -- the source-side classification the reference
script builds is not consumed by any template. Skipping it here is a
deliberate scope cut given time constraints, not an oversight; it can
be added later if a template pattern is designed that needs it.

EXTENDED 2026-07-22 (unit-checkpoint unblocking lane) from 48 A1 + 5 A2
units to the full authored fa-en corpus: A1 units 1-24/30-68, A2 units
25-34, B1 units 1-19 and B2 units 1-8 -- four separate course rows
("انگلیسی A1"/"A2"/"B1"/"B2"), four separate UNIT_FILES* tuples, each with
its own LOCAL 1-based unit ordering. The 52 units added in that pass had
ZERO lexemes, which made a unit checkpoint impossible for every one of them
regardless of practice-pack authoring: `generate_checkpoint()`
(backend/app/practice/service.py) calls `_material()` with only the unit's
own lesson ids and 409s `checkpoint_unavailable` below 12 items, and
lexemes -- not packs -- are what `_material()` needs. See
FA_EN_EXTRA_LEXEMES below for that pass's own POS/gloss table and why it is
file-private rather than in _en_target_lexeme_common.py.

Run via docker compose from backend/, mounting the full repo:
    cd backend
    docker compose run --rm \
      -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_fa_en.py
Add --dry-run to classify without touching the database.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from _en_target_lexeme_common import (  # noqa: E402
    EN_POS,
    en_token_display,
    en_agreement_tags,
    iter_taught_phrase_lexemes,
    normalize_en_token,
    strip_en_sentence_punctuation,
)

UNIT_FILES = (
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit01_greetings.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit02_introductions.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit03_numbers.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit04_dates.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit05_time.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit06_family.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit07_food.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit08_shopping.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit08.yaml",
    ),
    # Units 9-14 added 2026-07-06 (practice-pool-sync lane, extending fa-en
    # to match nl-en's already-full 26-unit coverage). EN_POS/en_agreement_tags
    # for all six units' vocabulary were already present in
    # _en_target_lexeme_common.py before this change (added earlier this
    # session alongside nl-en's own unit09-26 work) -- verified by diffing
    # every introduced_token across these six realization files against
    # EN_POS's keys with a standalone script; zero missing. Only this
    # script's own Farsi gloss dict needed extending, same division of labor
    # as every other unit added here.
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit09_places.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit10_directions.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit10.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit11_weather.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit11.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit12_clothing.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit13_emotions.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit14_communication.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit14.yaml",
    ),
    # Units 15-20 added 2026-07-06 (practice-pool-sync lane, continuing fa-en
    # coverage past the parallel 9-14 lane, matching nl-en's already-full
    # 26-unit coverage). EN_POS/en_agreement_tags for all six units'
    # vocabulary (money, routines, plans, past events, preferences,
    # comparisons) -- including every semantic tag needed for the practice
    # templates authored alongside this change (payment_method, card_type,
    # meal, hour_number, weekday, past_verb, past_verb_intransitive,
    # preference_verb, preference_verb_full, comparative_adj,
    # superlative_adj, color) -- were ALREADY present in
    # _en_target_lexeme_common.py before this change (added earlier this
    # session alongside nl-en's own unit15-20 work). Verified by a standalone
    # script diffing every introduced_token across these six realization
    # files against EN_POS's keys: zero missing. Only this script's own
    # Farsi gloss dict needed extending, same division of labor as every
    # other unit added here. One deliberate homograph avoidance: "get" (Unit
    # 10's "رسیدن (در get to)" sense, reach a place) is reused in unit16's
    # "get dressed" with a different sense (become/put on) -- but neither
    # this nor unit20's "get" ("I'll get the small one") is ever used as a
    # fillable slot in this pass's templates (following nl-en's own
    # lesson01-of-unit16 precedent of giving zero templates to routine
    # verbs with no same-lesson synonym set), so the existing single gloss
    # is never shown against the wrong sense and was deliberately left
    # untouched rather than forced into a second, conflicting entry.
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit15_money.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit15.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit16_routines.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit16.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit17_plans.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit17.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit18_past_events.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit18.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit19_preferences.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit19.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit20_comparisons.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit20.yaml",
    ),
    # Units 21-24 (A1: travel, health, work, housing) + 25-26 (A2:
    # bureaucracy, opinions) added 2026-07-06 (practice-pool-sync lane),
    # completing fa-en's coverage of all 24 A1 + first 2 A2 spine outcomes
    # for the shared English realization, matching nl-en's already-full
    # 26-unit coverage. EN_POS/en_agreement_tags for all six units'
    # vocabulary (including travel_noun, symptom_noun, occupation_noun/
    # occupation_a, room_noun, bureaucracy_noun, dogpark_noun) were already
    # present in _en_target_lexeme_common.py before this change (added
    # earlier this session alongside nl-en's own unit21-26 work) --
    # verified with a standalone script diffing every introduced_token
    # across these six realization files against EN_POS's keys: zero
    # missing. Only this script's own Farsi gloss dict needed extending
    # (107 new tokens), same division of labor as every other unit added
    # here. One deliberate homograph avoidance carried over from the
    # shared module's own documented limitation: "close" already has a
    # gloss/POS entry from unit05 (the store-hours "بستن"/verb sense);
    # unit26 reintroduces "close" as an adjective (proximity: "very close
    # to the playground"), but no new entry was added and no practice
    # template here uses "close" as a fillable slot for that sense --
    # consistent with the shared module's own instruction not to force a
    # second, conflicting entry onto an existing bare-token classification.
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit21_travel.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit21.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit22_health.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit22.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit23_work.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit23.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit24_housing.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit24.yaml",
    ),
    # Units 30-42 (A1: hobbies, appearance, animals, transportation, sports,
    # technology, education, celebrations, household, neighborhood, post
    # office, cooking, personality), added 2026-07-11 (fa-en depth-audit
    # lane -- a real content-depth audit found fa-en's Endless Practice pool
    # only covered units 1-29 of the 69 authored units, well under the
    # >=10hr publish-gate bar). These are all still A1-level; the shared
    # English realization's on-disk unit numbering skips 25-29 for the A1
    # track (those are the SEPARATE A2 course's own units 25-29, see
    # UNIT_FILES_A2 below, and content_manifest.txt/practice_manifest.txt
    # both order fa-en's realization/overlay files exactly this way: 1-24,
    # then 30-42-and-beyond) -- appended here CONTINUOUS with units 1-24 so
    # `_classify()`'s enumerate(..., 1) unit_order matches the real Unit.
    # order values the "انگلیسی A1" course was imported with (25 for
    # unit30, 26 for unit31, ... 37 for unit42). EN_POS/en_agreement_tags
    # for all thirteen units' vocabulary (including the new hobby_noun/
    # frequency_adverb/eye_color/pet_noun/transport_noun/sport_noun/
    # ball_sport/device_noun/class_noun/celebration_noun/chore_noun/
    # neighborhood_noun/mail_noun/cooking_verb/personality_adjective
    # semantic tags) were added to _en_target_lexeme_common.py as part of
    # this same pass -- verified every introduced_token across these
    # thirteen realization files against EN_POS's keys: zero missing after
    # the addition. This script's own Farsi gloss dict was extended to
    # match (364 new tokens, cross-checked against, but not copy-pasted
    # from, each unit's own fa-en overlay Farsi text).
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit30_hobbies.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit30.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit31_appearance.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit31.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit32_animals.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit32.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit33_transportation.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit33.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit34_sports.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit34.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit35_technology.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit35.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit36_education.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit36.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit37_celebrations.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit37.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit38_household.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit38.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit39_neighborhood.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit39.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit40_post.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit40.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit41_cooking.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit41.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit42_personality.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit42.yaml",
    ),
    # Units 43-48 (colors / seasons / emergencies / lost items /
    # appointments / library), added 2026-07-12 for the Endless Practice
    # coverage-extension batch. Kept in the A1 tuple because these files
    # import into the same "انگلیسی A1" course row as units 30-42.
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit43_colors.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit43.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit44_seasons.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit44.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit45_emergencies.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit45.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit46_lost_items.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit46.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit47_appointments.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit47.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit48_library.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit48.yaml",
    ),
    # Units 49-68 (waste disposal, accommodation, pharmacy, personal care,
    # bike rental, laundry, swimming pool, restaurant, cinema, museum,
    # banking basics, invitations, apologies, phone calls, asking for help,
    # compliments, returns/exchanges, pharmacy symptoms, family news,
    # borrowing/lending), added 2026-07-22 by the unit-checkpoint
    # unblocking lane. These 20 units had ZERO lexemes, so
    # `generate_checkpoint()` could never assemble 12 items for any of them
    # (a hard publish-gate requirement -- see
    # docs/content/PRACTICE_PACK_RECIPE.md section 0). Still A1-level, still the
    # same "انگلیسی A1" course row, so they stay CONTINUOUS with units
    # 1-24/30-48 here -- `_classify()`'s enumerate(..., 1) unit_order must
    # match the real Unit.order values the course was imported with, and
    # scripts/content_manifest.txt's fa-en line orders the realization files
    # in exactly this sequence (1-24, then 30-68).
    #
    # POS/semantic classification for the ~765 tokens these units (plus the
    # A2/B1/B2 tuples below) introduce is NOT in
    # _en_target_lexeme_common.py -- see FA_EN_EXTRA_LEXEMES below for why
    # this script carries its own table rather than editing the shared
    # module (three sibling backfills were extending the same 52 units
    # concurrently).
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit49_waste_disposal.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit49.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit50_accommodation.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit50.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit51_pharmacy.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit51.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit52_personal_care.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit52.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit53_bike_rental.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit53.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit54_laundry.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit54.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit55_swimming_pool.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit55.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit56_restaurant.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit56.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit57_cinema.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit57.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit58_museum.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit58.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit59_banking_basics.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit59.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit60_invitations.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit60.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit61_apologies_excuses.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit61.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit62_phone_calls.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit62.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit63_asking_for_help.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit63.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit64_compliments.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit64.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit65_returns_exchanges.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit65.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit66_pharmacy_symptoms.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit66.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit67_family_news.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit67.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit68_borrowing_lending.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a1_unit68.yaml",
    ),
)

# A2 units live in a SEPARATE course row ("انگلیسی A2", not "انگلیسی A1")
# -- `POST /admin/content/import` matches/creates courses by
# (source_language, target_language, title), and the A2 overlay declares
# `course.title: انگلیسی A2`, distinct from A1's `انگلیسی A1`. Real bug
# found live 2026-07-06/07 (Farsi Endless Practice QA pass, same root
# cause independently confirmed and already fixed in the sibling
# backfill_lexemes_en_prs.py/backfill_lexemes_prs_en.py pair): this used
# to be a single UNIT_FILES tuple with a2 units 25-26 appended at
# continuous positions 25/26, backfilled against ONE lookup of the
# "انگلیسی A1" course (24 real units) -- position 25/26 don't exist in
# that course, so `main()` hard-failed with "imported course is missing
# en.a2.unit25...." on every run. A2 lexemes for this direction have
# never actually been backfillable against a real database. Kept as its
# own tuple with LOCAL 1-based ordering (looked up against the "انگلیسی
# A2" course separately in main(), never mixed with UNIT_FILES' indices).
UNIT_FILES_A2 = (
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit25_bureaucracy.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit25.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit26_opinions.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit26.yaml",
    ),
    # Unit 27 (A2: opening a bank account), added 2026-07-07 (practice-
    # pool-sync lane extending fa-en to this new unit, in parallel with the
    # equivalent prs-en pass). EN_POS/en_agreement_tags for this unit's
    # vocabulary (including the new banking_noun/banking_adjective
    # semantic tags) were already present in _en_target_lexeme_common.py
    # before this change (added earlier this session alongside nl-en's own
    # unit27 course-routing fix) -- verified every introduced_token across
    # this realization file against EN_POS's keys: zero missing. Only this
    # script's own Farsi gloss dict needed extending (18 new tokens, cross-
    # checked against docs/content/overlays/fa-en/a2_unit27.yaml's own real
    # text, not copy-pasted from it).
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit27_banking.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit27.yaml",
    ),
    # Unit 28 (A2: attending a doctor's appointment), added 2026-07-07
    # (practice-pool-sync lane extending fa-en to this new unit, in
    # parallel with the equivalent prs-en pass; nl-en's own unit28 pass is
    # a separate concurrent worker, not touched here). EN_POS/
    # en_agreement_tags for this unit's vocabulary (including the new
    # health_followup_noun/condition_adjective semantic tags) were already
    # present in _en_target_lexeme_common.py before this change (added by
    # the concurrent nl-en lane's own unit28 pass) -- verified every
    # introduced_token across this realization file against EN_POS's keys:
    # zero missing. Only this script's own Farsi gloss dict needed
    # extending (16 new tokens, cross-checked against
    # docs/content/overlays/fa-en/a2_unit28.yaml's own real text, not
    # copy-pasted from it).
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit28_doctor.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit28.yaml",
    ),
    # Unit 29 (A2: reporting a maintenance problem), added 2026-07-07 --
    # closing the practice-pool gap for the newest A2 unit (units 25-28
    # already had fa-en/nl-en/prs-en packs; unit29 had none). EN_POS/
    # en_agreement_tags for this unit's vocabulary (including the new
    # 3-member maintenance_noun tag [sink, plumber, repair]) were added to
    # _en_target_lexeme_common.py as part of this same pass (not a
    # concurrent lane this time) -- verified every introduced_token across
    # this realization file against EN_POS's keys: zero missing. Only this
    # script's own Farsi gloss dict needed extending (18 new tokens,
    # cross-checked against docs/content/overlays/fa-en/a2_unit29.yaml's
    # own real text, not copy-pasted from it).
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit29_maintenance.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit29.yaml",
    ),
    # Units 30-34 (job interview, travel disruption, online habits, weekly
    # schedule, shopping complaint), added 2026-07-22 by the unit-checkpoint
    # unblocking lane -- all five had zero lexemes. Order here matches
    # scripts/content_manifest.txt's fa-en-a2 line (25, 26, 27, 28, 29, 30,
    # 31, 32, 33, 34), i.e. LOCAL 1-based positions 6-10 inside the
    # "انگلیسی A2" course.
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit30_job_interview.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit30.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit31_travel_disruption.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit31.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit32_online_habits.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit32.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit33_weekly_schedule.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit33.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit34_shopping_complaint.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit34.yaml",
    ),
    # Added 2026-08-05 (fa/prs native-gloss backlog): units 35-40 unblock the
    # last 6 fa-en A2 checkpoints. English POS ported from the already-shipped
    # nl-en EN_EXTRA (commit 304c029e); Farsi glosses below are DRAFTS pending
    # Ramin's native audit.
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit35_prescription.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit35.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit36_document_correction.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit36.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit37_video_calls.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit37.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit38_repair_visit.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit38.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit39_after_the_interview.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit39.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit40_online_order_problem.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit40.yaml",
    ),
)

# B1 and B2 live in their own course rows again ("انگلیسی B1" / "انگلیسی
# B2", declared by docs/content/overlays/fa-en/b1_unit01.yaml and
# b2_unit01.yaml) -- same per-level course split as A1 vs A2, and lexemes
# never cross a course boundary (AUTHORING_GUIDE section 18). Both tuples use
# LOCAL 1-based ordering, matched against their own course in main(),
# never mixed with UNIT_FILES'/UNIT_FILES_A2's indices. Order matches
# scripts/content_manifest.txt's fa-en-b1 / fa-en-b2 lines.
#
# Added 2026-07-22: all 19 B1 + all 8 B2 units had zero lexemes, so every
# one of them returned `checkpoint_unavailable` regardless of practice
# packs.
UNIT_FILES_B1 = (
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit01_necessity.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit02_abilities.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit03_hypotheticals.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit04_debate.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit05_workplace.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit06_narrative.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit07_conditions.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit08_sequencing.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit08.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit09_reported_speech.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit10_purpose.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit10.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit11_unreal_hypotheticals.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit11.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit12_concession.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit13_relative_clauses.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit14_professional_communication.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit14.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit15_complaints.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit15.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit16_advice.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit16.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit17_regret.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit17.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit18_future_plans.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit18.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit19_summarizing.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b1_unit19.yaml",
    ),
)

UNIT_FILES_B2 = (
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit01_argumentation.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b2_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit02_speculation.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b2_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit03_hedging_emphasis.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b2_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit04_narrative_time.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b2_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit05_register.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b2_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit06_abstraction.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b2_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit07_negotiation.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b2_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit08_synthesis.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/b2_unit08.yaml",
    ),
)

# Farsi gloss for each shared English target token -- hand-written for
# this course specifically. Must use Persian-range codepoints
# throughout (U+06A9 keheh, U+06CC Persian yeh), never the Arabic kaf/
# yeh codepoints -- described here in prose only, not pasted, per the
# project's own standing rule against literally including forbidden
# characters even as a "don't use this" example.
EN_TARGET_TO_FA_GLOSS: dict[str, str] = {
    "hello": "سلام", "hi": "سلام (خودمانی)", "good": "خوب", "morning": "صبح",
    "afternoon": "بعدازظهر", "evening": "عصر", "goodbye": "خداحافظ",
    "bye": "خداحافظ (خودمانی)", "how": "چطور", "are": "هستی/هستید",
    "you": "تو/شما", "i'm": "من هستم", "fine": "خوب", "thanks": "ممنون",
    "not": "نه", "bad": "بد", "and": "و", "okay": "خوب",
    "nice": "خوشایند", "to": "به", "meet": "ملاقات کردن", "too": "هم",
    "see": "دیدن", "later": "بعداً", "have": "داشتن", "a": "(حرف تعریف نامعین)",
    "day": "روز", "what": "چه", "is": "است", "what's": "چیست",
    "your": "ات/تان", "name": "اسم", "my": "ام", "leila": "لیلا",
    "i": "من", "am": "هستم", "student": "دانشجو", "teacher": "معلم",
    "yes": "بله", "no": "نه", "new": "جدید", "member": "عضو",
    "he": "او (مذکر)", "she": "او (مؤنث)", "an": "(حرف تعریف نامعین)",
    "engineer": "مهندس", "library": "کتابخانه", "assistant": "دستیار",
    "daniel": "دنیل", "work": "کار کردن", "at": "در", "the": "(حرف تعریف معین)",
    "welcome": "خوش آمدید", "thank": "تشکر کردن",
    # Unit 3 (numbers/ages/prices/phones/market), added 2026-07-05. Atomic
    # per-token glosses -- cross-checked against, but not copy-pasted from,
    # the fa-en unit03 overlay's own (phrase-level) Farsi glosses.
    "zero": "صفر", "one": "یک", "two": "دو", "three": "سه", "four": "چهار",
    "five": "پنج", "six": "شش", "seven": "هفت", "eight": "هشت",
    "nine": "نه (عدد)", "ten": "ده", "eleven": "یازده", "twelve": "دوازده",
    "thirteen": "سیزده", "fifteen": "پانزده", "twenty": "بیست",
    "twenty-one": "بیست و یک", "thirty": "سی", "forty": "چهل",
    "fifty": "پنجاه", "hundred": "صد", "twenty-five": "بیست و پنج",
    "old": "سال قدمت‌داشتن (در بیان سن یا قدمت)", "years": "سال (جمع)",
    "it's": "این ... است (مخفف it is)", "dollars": "دلار (جمع)",
    "phone": "تلفن", "number": "شماره", "market": "بازار",
    "apples": "سیب‌ها", "they're": "آنها ... هستند (مخفف they are)",
    "ok": "باشه؛ خب", "this": "این", "shop": "مغازه",
    "much": "چقدر",
    # Unit 4 (days/months/calendar dates), added 2026-07-06. POS/tags
    # already shared from _en_target_lexeme_common.py (nl-en's own unit04
    # work) -- only these Farsi glosses were needed.
    "monday": "دوشنبه", "tuesday": "سه‌شنبه", "wednesday": "چهارشنبه",
    "thursday": "پنجشنبه", "friday": "جمعه", "saturday": "شنبه",
    "sunday": "یکشنبه", "it": "آن", "today": "امروز", "january": "ژانویه",
    "march": "مارس", "july": "ژوئیه", "september": "سپتامبر",
    "december": "دسامبر", "which": "کدام", "month": "ماه",
    "today's": "امروزِ ... (مالکیت)", "date": "تاریخ", "7th": "هفتم",
    "can": "می‌تواند؛ می‌توان", "also": "همچنین", "write": "نوشتن",
    "as": "به عنوان", "when's": "کی است (مخفف when is)", "birthday": "تولد",
    "3rd": "سوم", "opens": "باز می‌شود", "again": "دوباره", "open": "باز",
    "on": "در؛ روی", "9th": "نهم", "great": "عالی", "then": "سپس",
    # Unit 5 (telling the time), added 2026-07-06.
    "time": "زمان", "o'clock": "ساعت (تمام)",
    "half": "نیم", "past": "و ... (در بیان زمان، مثلاً ربع گذشته از)",
    "quarter": "ربع", "night": "شب", "store": "مغازه",
    "in": "در", "closes": "بسته می‌شود", "does": "(فعل کمکی پرسشی)",
    "close": "بستن",
    # Unit 6 (family members and relationships), added 2026-07-06.
    "mother": "مادر", "father": "پدر", "brother": "برادر", "sister": "خواهر",
    "parents": "والدین", "siblings": "خواهر و برادرها",
    "grandmother": "مادربزرگ", "grandfather": "پدربزرگ",
    "aunt": "عمه؛ خاله", "uncle": "عمو؛ دایی",
    "cousin": "پسرعمو؛ دخترعمو (و مشابه)", "his": "مالِ او (مذکر)",
    "her": "مالِ او (مؤنث)", "she's": "او ... است (مخفف she is)",
    "brothers": "برادرها", "do": "(فعل کمکی پرسشی)", "any": "هیچ",
    "don't": "(منفیِ فعل کمکی do)", "only": "فقط", "child": "بچه",
    "photo": "عکس", "family": "خانواده", "who": "چه کسی",
    "just": "فقط؛ تازه",
    # Unit 7 (food, drink, and ordering), added 2026-07-06.
    "coffee": "قهوه", "tea": "چای", "water": "آب", "bread": "نان",
    "soup": "سوپ", "salad": "سالاد", "sandwich": "ساندویچ",
    "i'd": "من می‌خواهم (مخفف I would)", "like": "خواستن؛ دوست داشتن",
    "please": "لطفاً", "anything": "چیزی", "else": "دیگر",
    "that's": "آن ... است (مخفف that is)", "all": "همه؛ همین",
    "for": "برای", "here": "اینجا", "or": "یا",
    "go": "رفتن؛ بردن (بیرون‌بر)", "menu": "منو", "price": "قیمت",
    "cafe": "کافه", "3": "سه", "2": "دو", "5": "پنج", "6": "شش",
    "sure": "البته",
    # Unit 8 (shopping: prices and quantities), added 2026-07-06.
    "pound": "پوند (واحد وزن)", "of": "از", "dozen": "دوجین",
    "eggs": "تخم‌مرغ‌ها", "bottle": "بطری", "bag": "کیسه", "rice": "برنج",
    "kilo": "کیلو", "tomatoes": "گوجه‌فرنگی‌ها", "pounds": "پوندها",
    "fresh": "تازه", "per": "هر",
    "4": "چهار",
    # Unit 9 (common places and locations), added 2026-07-06. Atomic
    # per-token glosses -- cross-checked against, but not copy-pasted from,
    # the fa-en unit09 overlay's own (phrase-level) Farsi glosses.
    "bank": "بانک", "hospital": "بیمارستان", "pharmacy": "داروخانه",
    "park": "پارک", "restaurant": "رستوران", "next": "کنار",
    "across": "روبه‌رو", "from": "از", "between": "بین",
    "behind": "پشت", "front": "جلو", "where": "کجا",
    "far": "دور", "excuse": "ببخشید", "me": "من (حالت مفعولی)",
    # Unit 10 (asking for and following directions), added 2026-07-06.
    "turn": "پیچیدن", "left": "چپ", "right": "راست", "straight": "مستقیم",
    "stop": "ایستادن", "corner": "نبش؛ گوشهٔ خیابان", "get": "رسیدن",
    "minutes": "دقیقه‌ها", "can't": "نمی‌توانی/نمی‌تواند (منفیِ can)",
    "miss": "از دست‌دادن؛ گم‌کردن", "take": "بردن؛ گرفتن", "first": "اول",
    "street": "خیابان", "second": "دوم", "directions": "مسیر؛ آدرس",
    # Unit 11 (talking about the weather), added 2026-07-06.
    "sunny": "آفتابی", "rainy": "بارانی", "cloudy": "ابری", "cold": "سرد",
    "hot": "گرم", "windy": "بادی", "weather": "آب‌وهوا",
    "warm": "گرم و ملایم", "raining": "بارون‌آمدن", "should": "باید",
    "umbrella": "چتر", "tomorrow": "فردا",
    "will": "(فعل کمکی زمان آینده)", "be": "بودن", "rain": "باران؛ باریدن",
    "let's": "بیا (پیشنهاد انجام کاری با هم)", "idea": "فکر؛ ایده",
    "but": "اما", "going": "قرار است", "so": "پس",
    # Unit 12 (clothing: sizes and colors), added 2026-07-06.
    "shirt": "پیراهن", "pants": "شلوار", "shoes": "کفش",
    "jacket": "ژاکت؛ کاپشن", "dress": "پیراهن زنانه", "small": "کوچک",
    "medium": "متوسط", "large": "بزرگ", "blue": "آبی", "black": "مشکی",
    "size": "سایز", "color": "رنگ", "20": "بیست",
    "i'll": "من ... خواهم (مخفف I will)", "we": "ما",
    # Unit 13 (talking about feelings), added 2026-07-06.
    "happy": "خوشحال", "sad": "ناراحت", "tired": "خسته",
    "excited": "هیجان‌زده", "worried": "نگران",
    "feeling": "احساس؛ حس‌کردن", "little": "کمی (در a little)",
    "because": "چون", "big": "بزرگ", "test": "امتحان", "class": "کلاس",
    "almost": "تقریباً", "over": "تمام (در be over)", "last": "آخرین",
    "year": "سال", "writer": "نویسنده", "oh": "آه", "understand": "فهمیدن",
    # Unit 14 (phone calls and messages), added 2026-07-06.
    "free": "آزاد؛ وقت‌داشتن", "tonight": "امشب",
    "sorry": "ببخشید؛ متأسفم", "repeat": "تکرار کردن", "that": "آن",
    "speak": "صحبت‌کردن", "more": "بیشتر", "slowly": "آهسته",
    "hear": "شنیدن", "well": "خوب", "6pm": "ساعت شش عصر",
    "message": "پیام", "suggest": "پیشنهاد دادن", "meeting": "قرار ملاقات",
    "place": "مکان", "about": "دربارهٔ",
    # Unit 15 (handling money and payments), added 2026-07-06. Atomic
    # per-token glosses -- cross-checked against, but not copy-pasted from,
    # the fa-en unit15 overlay's own (phrase-level) Farsi glosses. "take"/
    # "sorry"/"i'll"/"we" reuse their existing Unit 10/14/12/12 senses
    # unchanged (same meaning here, no new entry needed).
    "cash": "پول نقد", "card": "کارت", "credit": "اعتباری",
    "debit": "برداشت مستقیم (از حساب بانکی)", "total": "جمع کل",
    "cards": "کارت‌ها", "pay": "پرداخت کردن",
    "by": "با (روش انجام کار؛ مثلاً pay by card)", "tax": "مالیات",
    "1": "یک", "10": "ده",
    # Unit 16 (describing a daily routine), added 2026-07-06. "get"/"that"
    # reuse their existing Unit 10/14 senses unchanged -- see the UNIT_FILES
    # comment above for why "get" is deliberately never used as a fillable
    # slot in this pass's templates despite the sense mismatch.
    "wake": "بیدار شدن",
    "up": "بالا (در wake up: بیدار شدن)",
    "dressed": "پوشیده", "dinner": "شام",
    "bed": "رختخواب", "every": "هر", "usually": "معمولاً",
    "breakfast": "صبحانه", "after": "بعد از",
    # Unit 17 (making simple plans), added 2026-07-06. "sorry"/"can't"/
    # "about"/"me" reuse their existing Unit 14/10/14/9 senses unchanged.
    "want": "خواستن", "movie": "فیلم", "weekend": "آخر هفته",
    "would": "(فعل کمکی مؤدبانه؛ در Would you like)", "walk": "قدم زدن",
    "love": "خیلی دوست داشتن؛ عاشق بودن", "busy": "شلوغ (سرم شلوغه)",
    "maybe": "شاید", "another": "یک ... دیگر", "lunch": "ناهار",
    "1pm": "ساعت یک بعدازظهر", "works": "خوب/مناسب است",
    # Unit 18 (describing a recent event), added 2026-07-06. "last"/"we"
    # reuse their existing Unit 13/12 senses unchanged.
    "went": "رفت (زمان گذشتهٔ go)", "saw": "دید (زمان گذشتهٔ see)",
    "ate": "خورد (زمان گذشتهٔ eat)",
    "visited": "دیدار کرد (زمان گذشتهٔ visit)",
    "worked": "کار کرد (زمان گذشتهٔ work)",
    "did": "(فعل کمکی پرسشی گذشته)", "yesterday": "دیروز", "week": "هفته",
    "together": "با هم", "watched": "تماشا کرد (زمان گذشتهٔ watch)",
    "writer's": "مالِ نویسنده", "writer": "نویسنده",
    "s": "(علامت مالکیت 's)", "was": "بود (زمان گذشتهٔ is/am)",
    # Unit 19 (expressing likes and preferences), added 2026-07-06. "love"
    # (added above, unit17)/"because"/"but" reuse their existing senses
    # unchanged.
    "prefer": "ترجیح دادن", "hate": "متنفر بودن", "calmer": "آرام‌بخش‌تر",
    "very": "خیلی", "strong": "قوی؛ غلیظ", "why": "چرا",
    "think": "فکر کردن", "prefers": "ترجیح می‌دهد (سوم‌شخص مفرد)",
    "thinks": "فکر می‌کند (سوم‌شخص مفرد)",
    # Unit 20 (making basic comparisons), added 2026-07-06. "small"/"big"/
    # "but"/"by" (added above, unit15)/"i'll"/"get" reuse their existing
    # senses unchanged.
    "bigger": "بزرگ‌تر", "smaller": "کوچک‌تر", "cheaper": "ارزان‌تر",
    "more": "بیشتر (در more expensive)", "expensive": "گران",
    "faster": "سریع‌تر", "than": "از (در مقایسه)", "nicer": "قشنگ‌تر",
    "cheapest": "ارزان‌ترین", "red": "قرمز", "car": "ماشین", "blue": "آبی",
    "white": "سفید",
    # Units 21-24 (A1: travel, health, work, housing) + 25-26 (A2:
    # bureaucracy, opinions), added 2026-07-06. Atomic per-token glosses --
    # cross-checked against, but not copy-pasted from, each unit's own
    # (phrase-level) Farsi overlay glosses. Reused-sense tokens that
    # already have an entry above are deliberately NOT repeated here (e.g.
    # "from"/"where"/"hospital"/"next"/"small"/"every"/"like"/"meet"/
    # "teacher"/"engineer" from units 1-20; "should"/"would"/"will"/"be"/
    # "maybe"/"very"/"think"/"little"/"but"/"about"/"so"/"me"/"dinner"/
    # "friday"/"photo"/"because"/"last"/"works"/"good"/"idea"/"park" --
    # same meaning in every reuse here, no new entry needed).
    "ticket": "بلیت", "platform": "سکو", "train": "قطار",
    "departure": "حرکت؛ عزیمت", "arrival": "رسیدن؛ ورود", "boston": "بوستون",
    "way": "طرف",
    "round": "دوره‌ای", "trip": "سفر",
    "leaves": "حرکت می‌کنه (فعل، سوم‌شخص مفرد leave)", "9:15": "۹:۱۵",
    "arrives": "می‌رسه (فعل، سوم‌شخص مفرد arrive)", "11:30": "۱۱:۳۰",
    "arrive": "رسیدن (فعل)",
    "headache": "سردرد", "stomachache": "دل‌درد", "fever": "تب",
    "cough": "سرفه", "sore": "دردناک",
    "throat": "گلو", "wrong": "اشتباه؛ خراب",
    "feel": "احساس کردن", "rest": "استراحت کردن", "need": "نیاز داشتن",
    "doctor": "دکتر", "look": "به‌نظر رسیدن",
    "doesn't": "(منفیِ فعل کمکی does)", "better": "بهتر", "if": "اگر",
    "drink": "نوشیدن",
    "nurse": "پرستار", "cook": "آشپز", "driver": "راننده",
    "patients": "بیماران", "help": "کمک کردن", "reports": "گزارش‌ها",
    "interesting": "جالب", "company": "شرکت", "downtown": "مرکز شهر",
    "answer": "جواب دادن (در answer emails)", "emails": "ایمیل‌ها",
    "sometimes": "بعضی وقت‌ها", "with": "با", "clients": "مشتری‌ها",
    "job": "شغل",
    "bedroom": "اتاق خواب", "kitchen": "آشپزخانه", "bathroom": "حمام",
    "living": "نشیمن", "room": "اتاق",
    "garden": "باغچه؛ حیاط", "many": "چند تا (در how many)",
    "rooms": "اتاق‌ها", "there": "آنجا",
    "there's": "... هست (مخفف there is)", "apartment": "آپارتمان",
    "has": "دارد", "bedrooms": "اتاق‌خواب‌ها", "favorite": "موردعلاقه",
    "tell": "گفتن", "isn't": "نیست (مخفف is not)", "balcony": "بالکن",
    "upstairs": "طبقهٔ بالا", "near": "نزدیک", "easy": "راحت؛ آسان",
    "eat": "خوردن",
    "appointment": "قرار ملاقات", "document": "مدرک",
    "proof": "مدرک؛ سند", "residency": "اقامت",
    "form": "فرم", "confirmation": "تأیید", "was": "بود",
    "wondering": "می‌خواستم بدونم", "whether": "آیا",
    "could": "می‌تونستم/می‌تونین", "make": "گرفتن",
    "possible": "ممکن", "come": "آمدن", "update": "به‌روز کردن",
    "address": "آدرس", "moved": "نقل مکان کردم (زمان گذشتهٔ move)",
    "month": "ماه", "id": "کارت شناسایی",
    "utility": "خدمات شهری", "bill": "قبض",
    "bring": "آوردن", "such": "مثل",
    "lived": "زندگی کرده‌ام (زمان گذشتهٔ live)",
    "since": "از (زمان مشخص)", "lease": "قرارداد اجاره",
    "when": "چه وقت", "10am": "ساعت ۱۰ صبح", "4471": "۴۴۷۱",
    "dog": "سگ", "opinion": "نظر", "other": "دیگر (در on the other hand)",
    "hand": "دست",
    "agree": "موافق بودن", "dogs": "سگ‌ها", "space": "فضا", "run": "دویدن",
    "playground": "زمین بازی", "fair": "منصفانه",
    "point": "نکته", "they": "آنها",
    "move": "جابه‌جا کردن؛ منتقل کردن", "farther": "دورتر",
    "away": "دور (در move away)",
    # Unit 27 (A2: opening a bank account), added 2026-07-07. Atomic per-
    # token glosses -- cross-checked against, but not copy-pasted from,
    # docs/content/overlays/fa-en/a2_unit27.yaml's own (phrase-level)
    # Farsi glosses. "debit"/"card"/"i'll"-style contraction pattern reuse
    # their existing Unit 15/12 senses unchanged.
    "checking": "جاری", "account": "حساب",
    "monthly": "ماهانه", "fee": "کارمزد", "minimum": "حداقل",
    "balance": "موجودی", "direct": "مستقیم (در direct deposit)",
    "deposit": "واریز", "documents": "مدارک (جمع)",
    "you'll": "شما ... خواهید (مخفف you will)",
    "dmv": "ادارهٔ راهنمایی و رانندگی",
    "business": "کاری",
    "days": "روزها", "keep": "نگه داشتن", "500": "پانصد",
    "sounds": "به‌نظر می‌رسد (در that sounds good)",
    "teller": "کارمند بانک", "both": "هر دو",
    # Unit 28 (A2: attending a doctor's appointment), added 2026-07-07.
    # Atomic per-token glosses -- cross-checked against, but not copy-
    # pasted from, docs/content/overlays/fa-en/a2_unit28.yaml's own
    # (phrase-level) Farsi glosses. "appointment"/"confirmation"/"card"/
    # "arrive"/"headache"/"sore"/"throat"/"fever"/"if"/"doesn't"/"better"/
    # "drink"/"doctor"/"any"/"should"/"take"/"get"/"come"/"this"/"water"/
    # "day"/"minutes"/"ten"/"five"/"number"/"today" reuse their existing
    # senses unchanged.
    "medicine": "دارو", "prescription": "نسخه",
    "follow": "پیگیری",
    "getting": "در حال ... شدن",
    "worse": "بدتر", "insurance": "بیمه",
    "i've": "من ... داشته‌ام (مخفف I have)",
    "had": "داشتم (زمان گذشتهٔ have)", "early": "زودتر",
    "confirmed": "تأیید شده (است)", "3pm": "ساعت سهٔ بعدازظهر",
    "7724": "۷۷۲۴", "twice": "دو بار",
    "plenty": "به مقدار زیاد",
    "back": "برگشتن",
    "within": "ظرف",
    # Unit 29 (A2: reporting a maintenance problem), added 2026-07-07.
    # Atomic per-token glosses -- cross-checked against, but not copy-
    # pasted from, docs/content/overlays/fa-en/a2_unit29.yaml's own
    # (phrase-level) Farsi glosses. "kitchen"/"apartment"/"bathroom" reuse
    # their existing unit24 senses unchanged (recapped, not retaught).
    "leaking": "چکه کردن", "sink": "سینک", "building": "ساختمان",
    "manager": "مدیر", "plumber": "لوله‌کش", "repair": "تعمیر",
    "report": "گزارش دادن", "problem": "مشکل",
    "been": "بوده",
    "someone": "یک نفر؛ کسی", "fix": "درست کردن",
    "2pm": "ساعت ۲ بعدازظهر", "4pm": "ساعت ۴ بعدازظهر",
    "received": "دریافت شده", "6180": "۶۱۸۰", "send": "فرستادن",
    "home": "خونه", "here's": "اینه (مخفف this is، در معرفی چیزی)",
    # Units 30-42 (A1: hobbies, appearance, animals, transportation,
    # sports, technology, education, celebrations, household,
    # neighborhood, post office, cooking, personality), added 2026-07-11
    # (fa-en depth-audit lane, extending Endless Practice coverage past
    # the shared English realization's unit24 ceiling -- these are all
    # still A1-level, in the SAME "انگلیسی A1" course, continuous with
    # units 1-24 in UNIT_FILES below; the shared English realization's
    # on-disk numbering skips 25-29 for the A1 track (those are the A2
    # course's own units, see UNIT_FILES_A2). Atomic per-token glosses --
    # cross-checked against, but not copy-pasted from, each unit's own
    # (phrase-level) Farsi overlay glosses. Includes tokens with attached
    # punctuation exactly as introduced_tokens declares them (e.g.
    # "ball.", "mia,"), matching EN_POS's own keying convention for the
    # same tokens.
    "12th": "دوازدهم", "active": "فعال", "add": "اضافه کردن",
    "along": "کنار آمدن", "already": "قبلاً",
    "always": "همیشه", "anyone's": "مالِ هیچ‌کس", "app": "اپلیکیشن",
    "apps": "اپلیکیشن‌ها", "around": "دور و بر", "arrived": "رسید",
    "asked": "درخواست کرد", "bake": "پختن (در فر)", "ball.": "توپ",
    "balloons": "بادکنک‌ها", "barks": "پارس می‌کند", "basketball": "بسکتبال",
    "battery": "باتری", "before": "قبل از", "bike": "دوچرخه",
    "bird": "پرنده", "blond": "بلوند (رنگ مو)", "boil": "جوشاندن",
    "boiled": "جوشاند", "book": "کتاب", "books": "کتاب‌ها", "bought": "خرید",
    "break": "اتاق استراحت", "brown": "قهوه‌ای",
    "bus": "اتوبوس", "buy": "خریدن", "buys": "می‌خرد", "cake": "کیک",
    "call": "تماس گرفتن", "calm": "آرام", "camera": "دوربین", "cat": "گربه",
    "celebrate": "جشن گرفتن", "chat": "چت کردن", "chicago": "شیکاگو",
    "chop": "خرد کردن", "chopped": "خرد کرد", "chore": "کار خانه",
    "chose": "انتخاب کرد", "classes": "کلاس‌ها", "clean": "تمیز کردن",
    "cleaning": "تمیزکردن (اسم مصدر)", "cleans": "تمیز می‌کند",
    "clerk": "کارمند", "college": "دانشکده", "comfortable": "راحت",
    "coming": "آمدن (میهمان‌ها می‌آیند)",
    "community": "اجتماع", "computer": "کامپیوتر",
    "congratulate": "تبریک گفتن", "congratulated": "تبریک گفت",
    "congratulations": "تبریک", "cooking": "آشپزی", "cooks": "آشپزی می‌کند",
    "cost": "هزینه داشتن", "course": "دوره", "coworker": "همکار",
    "coworkers": "همکاران", "creative": "خلاق", "curly": "فرفری",
    "cutting": "در حال بریدن", "daniel's": "مالِ دنیل", "daniel?": "دنیل؟",
    "decided": "تصمیم گرفت", "definitely": "قطعاً", "delicious": "خوشمزه",
    "didn't": "(منفیِ فعل کمکی گذشته did)", "different": "متفاوت",
    "differently": "به‌طور متفاوت", "difficult.": "سخت", "dishes": "ظرف‌ها",
    "does.": "بله (فعل کمکی does، در پاسخ کوتاه)", "doing": "انجام دادن",
    "door": "در", "download": "دانلود کردن", "downloads": "دانلود می‌کند",
    "drive": "رانندگی کردن", "drives": "رانندگی می‌کند",
    "employee": "کارمند", "enjoy": "لذت بردن", "envelope": "پاکت‌نامه",
    "even": "حتی", "ever": "هیچ‌وقت (در سؤال)", "everyone": "همه",
    "everywhere": "همه‌جا", "exercise": "ورزش کردن",
    "express": "بیان کردن", "eyes": "چشم‌ها", "fast": "سریع",
    "feels": "احساس می‌شود", "fingers": "انگشت‌ها",
    "finishes": "تمام می‌کند", "fish": "ماهی", "five-minute": "پنج‌دقیقه‌ای",
    "forget": "فراموش کردن", "found": "پیدا کرد", "framed": "قاب‌شده",
    "friend": "دوست", "friendly": "مهربان",
    "friends": "دوستان", "funny": "بامزه", "fur": "پشم (حیوان)",
    "games": "بازی‌ها", "gave": "داد",
    "gets": "می‌شود", "gift": "هدیه",
    "glasses": "عینک", "goes": "می‌رود", "grandmother's": "مالِ مادربزرگ",
    "green": "سبز", "grocery": "خواربارفروشی",
    "group": "گروه", "guests": "میهمان‌ها", "gym": "باشگاه",
    "habits": "عادت‌ها", "hair": "مو", "hallway": "راهرو",
    "hardworking": "زحمت‌کش", "hates": "متنفر است",
    "having": "برگزار کردن",
    "he's": "او ... است (مخفف he is)", "helpful": "کمک‌کننده",
    "helps": "کمک می‌کند", "herself": "خودش (مؤنث)", "him": "او را (مذکر)",
    "hobbies": "سرگرمی‌ها", "homework": "تکلیف", "house": "خانه",
    "how's": "چطوره (مخفف how is)", "humor": "شوخ‌طبعی",
    "ingredient": "مواد اولیه", "instead": "در عوض", "invite": "دعوت کردن",
    "it?": "آن؟", "know": "دانستن", "knows": "می‌شناسد", "laptop": "لپ‌تاپ",
    "laptops": "لپ‌تاپ‌ها", "late": "دیر", "laugh": "خندیدن",
    "laundry": "لباسشویی", "learn": "یاد گرفتن",
    "learning": "در حال یادگیری", "least": "کمترین",
    "leave": "وقت گذاشتن", "letter": "نامه",
    "letters": "نامه‌ها", "likes": "دوست دارد", "live": "زندگی کردن",
    "lives": "زندگی می‌کند", "long": "بلند", "lopez": "لوپز",
    "lot": "خیلی (در a lot)", "loves": "خیلی دوست دارد",
    "low": "کم (باتری کم)", "luna": "لونا", "luna.": "لونا",
    "made": "درست کرد", "mail": "پست", "mailbox": "صندوق پستی",
    "makes": "درست می‌کند", "making": "درست کردن", "map": "نقشه",
    "maps": "نقشه‌ها", "math": "ریاضی", "max.": "مکس", "meetings": "جلسات",
    "meets": "ملاقات می‌کند", "mess": "به‌هم‌ریختگی", "mexico": "مکزیک",
    "mia": "میا", "mia's": "مالِ میا", "mia,": "میا،", "might": "ممکن است",
    "mind": "اهمیت دادن", "mine": "مالِ من", "mom": "مامان",
    "morning.": "صبح", "mornings": "صبح‌ها", "most": "بیشتر",
    "mostly": "بیشترِ اوقات", "mother's": "مالِ مادر", "mr": "آقای",
    "named": "به نام", "names": "اسم‌ها", "nearby": "نزدیک",
    "needs": "نیاز دارد", "neighbor": "همسایه", "neighborhood": "محله",
    "neighborhoods": "محله‌ها", "neighbors": "همسایه‌ها", "never": "هرگز",
    "nice!": "قشنگ!", "nights": "شب‌ها", "noisy": "پرسروصدا", "now": "حالا",
    "october": "اکتبر", "office": "دفتر کار", "office.": "دفتر کار",
    "often": "اغلب", "okay,": "خب،", "once": "وقتی که",
    "onions": "پیازها", "organized": "منظم", "out": "بیرون (در take out)",
    "outgoing": "اجتماعی", "outside": "بیرون از",
    "own": "خودش", "package": "بسته",
    "packages": "بسته‌ها", "paid": "پرداخت کرد", "paint": "نقاشی کردن",
    "painting": "نقاشی", "paints": "نقاشی می‌کند", "pair": "جفت",
    "parking": "پارکینگ", "party": "مهمانی", "pasta": "پاستا",
    "patient": "صبور", "people": "آدم‌ها", "perfect": "عالی",
    "personal": "شخصی", "personalities": "شخصیت‌ها", "pet": "حیوان خانگی",
    "pets": "حیوانات خانگی", "phones": "گوشی‌ها", "photography": "عکاسی",
    "photos": "عکس‌ها", "pieces": "تکه‌ها", "planning": "در حال برنامه‌ریزی",
    "plans": "برنامه‌ها", "plants": "گیاهان", "play": "بازی کردن",
    "plays": "بازی می‌کند", "pool": "استخر", "post": "پست",
    "post office": "اداره پست", "postcard": "کارت‌پستال", "project": "پروژه",
    "promotion": "ترفیع", "put": "گذاشتن", "quickly": "سریع",
    "quiet": "آرام", "rarely": "به‌ندرت", "reading": "کتاب‌خوانی",
    "reads": "می‌خواند", "ready": "آماده", "really": "واقعاً",
    "receipt": "رسید", "recipe": "دستور پخت", "recipes": "دستور پخت‌ها",
    "regular": "معمولی", "relax": "آرام شدن", "relaxed": "آرام (احساس)",
    "restaurants": "رستوران‌ها", "ride": "دوچرخه‌سواری کردن",
    "running": "دویدن", "said": "گفت", "salt": "نمک", "same": "مثل هم",
    "saturdays": "شنبه‌ها", "sauce": "سس", "say": "گفتن", "says": "می‌گوید",
    "sends": "می‌فرستد", "sense": "حس", "sent": "فرستاد",
    "several": "چند تا", "shops": "مغازه‌ها", "short": "کوتاه",
    "show": "نشان دادن", "shy": "خجالتی", "sister's": "مالِ خواهرم",
    "skills": "مهارت‌ها", "slow": "کند", "soccer": "فوتبال",
    "some": "مقداری", "someday": "یک روزی", "something": "چیزی",
    "sometime": "یک وقتی", "soon": "به‌زودی", "spanish": "اسپانیایی",
    "spending": "گذراندن (وقت)", "sport": "ورزش", "stamp": "تمبر",
    "starting": "شروع می‌کند", "stay": "ماندن",
    "still": "هنوز", "studies": "درس می‌خواند", "study": "درس خواندن",
    "studying": "در حال درس‌خواندن", "subject": "درس (موضوع تحصیلی)",
    "sundays": "یکشنبه‌ها", "surprise": "غافلگیری", "swim.": "شنا کردن",
    "swimming": "شنا", "swims": "شنا می‌کند", "tablet": "تبلت",
    "takes": "طول می‌کشد", "taking": "گرفتن (کلاس گرفتن)",
    "talk": "صحبت کردن", "talkative": "پرحرف", "talking": "در حال صحبت کردن",
    "tall": "قدبلند", "tasks": "وظایف", "taste": "چشیدن", "tasted": "چشید",
    "taught": "یاد داد", "teach": "یاد دادن", "teaches": "یاد می‌دهد",
    "team": "تیم", "tennis": "تنیس", "text": "پیامک فرستادن",
    "thanked": "تشکر کرد", "thankful": "قدردان", "their": "مالِ آنها",
    "them": "آنها را", "these": "این‌ها", "though": "هرچند",
    "times": "بار (تعداد دفعات)", "took": "گرفت (زمان گذشتهٔ take)",
    "trash": "زباله", "travel": "سفر کردن", "tries": "امتحان می‌کند",
    "upset": "ناراحت", "us": "ما (حالت مفعولی)", "use": "استفاده کردن",
    "uses": "استفاده می‌کند", "using": "با استفاده از",
    "vacuum": "جارو کردن", "vacuumed": "جارو کرد", "vacuums": "جارو می‌کند",
    # walks: gloss comma dropped 2026-07-25 -- unlike the mirrored-comma
    # style on pure display tokens (میا،/خب،/بله،), this one surfaces as a
    # standalone option in POS-noun practice pools, where the dangling
    # comma reads as a typo (flagged by the polish wave).
    "video": "ویدیویی", "walks,": "پیاده‌روی‌ها",
    "wanted": "می‌خواست", "wants": "می‌خواهد",
    "warms": "گرم می‌شود", "wash": "شستن",
    "washes": "می‌شوید", "washing": "شستن (اسم مصدر)", "watch": "تماشا کردن",
    "waters": "آب می‌دهد", "ways": "راه‌ها",
    "we'll": "ما ... خواهیم (مخفف we will)", "wears": "می‌پوشد",
    "weekends": "آخر هفته‌ها", "weighed": "وزن کرد", "were": "بودند",
    "while": "درحالی‌که", "wifi": "وای‌فای", "wish": "آرزو کردن",
    "without": "بدون", "wonderful": "فوق‌العاده", "work?": "کار؟ (محل کار)",
    "worry": "نگران بودن", "writes": "می‌نویسد", "yes,": "بله،",
    "yet": "هنوز", "yoga": "یوگا",
}

EN_TARGET_TO_FA_GLOSS.update({
    "sky": "آسمان", "grass": "چمن", "yellow": "زرد", "sun": "خورشید",
    "dark": "تیره", "wearing": "پوشیده است", "light": "روشن",
    "painted": "رنگ‌شده", "bright": "روشن؛ درخشان", "fun": "جالب؛ سرگرم‌کننده",
    "our": "مالِ ما", "presentation": "ارائه", "choose": "انتخاب کردن",
    "colors": "رنگ‌ها", "looks": "به‌نظر می‌رسد", "professional": "حرفه‌ای",
    "choice": "انتخاب", "everything": "همه‌چیز", "gardens": "باغ‌ها",
    "especially": "به‌خصوص", "beautiful": "زیبا", "reminds": "یادآوری می‌کند",
    "everyday": "روزمره", "conversations": "گفت‌وگوها",
    "spring": "بهار", "flowers": "گل‌ها", "bloom": "شکوفه دادن",
    "summer": "تابستان", "beach": "ساحل", "fall": "پاییز",
    "change": "تغییر کردن", "winter": "زمستان", "snows": "برف می‌بارد",
    "season": "فصل", "walking": "پیاده‌روی", "seasons": "فصل‌ها",
    "playing": "بازی کردن", "find": "پیدا کردن؛ دانستن", "outdoors": "بیرون",
    "emergency": "وضعیت اضطراری", "police": "پلیس", "ambulance": "آمبولانس",
    "fire": "آتش", "department": "اداره؛ بخش", "911": "۹۱۱",
    "burning": "در حال سوختن", "smell": "بو", "smoke": "دود", "pan": "تابه",
    "caught": "گرفت (در catch fire)", "off": "خاموش؛ دور", "stove": "اجاق",
    "hurry": "عجله کردن", "friend's": "مالِ دوست", "goodness": "خوبی؛ وای",
    "wait": "صبر کردن", "case": "مورد", "safer": "امن‌تر",
    "until": "تا", "elevator": "آسانسور", "stairs": "پله‌ها",
    "third": "سوم", "give": "دادن", "finally": "بالاخره",
    "waited": "صبر کرد", "notice": "اطلاعیه", "safe": "امن",
    "came": "آمد", "check": "بررسی کردن", "relieved": "آسوده",
    "hurt": "آسیب‌دیده", "lost": "گم‌شده", "keys": "کلیدها",
    "wallet": "کیف پول", "backpack": "کوله‌پشتی", "seen": "دیده",
    "anyone": "کسی", "strap": "بند", "where's": "کجاست",
    "fountain": "فواره", "you're": "تو/شما هستی", "inside": "داخل",
    "ask": "پرسیدن", "holding": "در دست داشتن", "desk": "میز پذیرش",
    "lose": "گم کردن", "item": "وسیله", "main": "اصلی", "gate": "دروازه",
    "describe": "توصیف کردن", "its": "مالِ آن", "special": "خاص",
    "details": "جزئیات", "staff": "کارکنان", "called": "زنگ زد؛ صدا کرد",
    "told": "گفت", "whole": "تمام", "story": "داستان", "track": "رد؛ پیگیری",
    "things": "چیزها", "available": "در دسترس؛ موجود", "confirm": "تأیید کردن",
    "reschedule": "زمان را تغییر دادن", "max": "مکس", "seems": "به‌نظر می‌رسد",
    "lately": "اخیراً", "due": "موعدش رسیده", "yearly": "سالانه",
    "checkup": "معاینه", "vet": "دامپزشک", "dog's": "مالِ سگ",
    "max's": "مالِ مکس", "dentist": "دندان‌پزشک", "service": "خدمات",
    "you'd": "تو/شما ... می‌کردی", "receptionist": "مسئول پذیرش",
    "changes": "تغییرات", "nervous": "عصبی؛ مضطرب", "borrow": "قرض گرفتن",
    "return": "برگرداندن", "borrowed": "قرض گرفته", "weeks": "هفته‌ها",
    "cookbook": "کتاب آشپزی", "fill": "پر کردن", "visiting": "بازدید کردن",
    "libraries": "کتابخانه‌ها", "let": "اجازه دادن", "items": "وسایل",
    "few": "چند", "librarian": "کتابدار", "finished": "تمام کرد",
    "used": "استفاده کرد", "started": "شروع کرد", "borrowing": "قرض گرفتن",
    "returned": "برگرداند", "picked": "برداشت", "got": "گرفت",
    "checked": "بررسی کرد", "practice": "تمرین", "teaching": "آموزش",
    "reminded": "یادآوری کرد",
})


# ---------------------------------------------------------------------------
# 2026-07-22 extension: a1 units 49-68, a2 units 30-34, ALL of b1 (1-19) and
# ALL of b2 (1-8) -- the 52 units that had ZERO lexemes and therefore could
# never produce a unit checkpoint (`generate_checkpoint()` hard-fails with
# `checkpoint_unavailable` below 12 items, and `_material()` only sees
# lexemes whose provenance lesson belongs to the unit itself).
#
# WHY THIS TABLE LIVES HERE INSTEAD OF _en_target_lexeme_common.py:
# the shared module is consumed by nl-en/prs-en/de-en as well, and those
# lanes' backfills were being extended over the SAME 52 units concurrently
# by other agents. Editing one shared dict from four workers at once is the
# `content_manifest.txt`-class concurrency hazard root CLAUDE.md forbids, so
# this pass keeps its classification local and file-private. The ~443
# already-classified tokens these units re-use are still served from the
# shared module, so they stay byte-identical to nl-en/prs-en; only the ~765
# tokens the shared module has never seen are served from here. When the
# shared module eventually absorbs them, delete the duplicate keys here
# rather than the shared ones.
#
# Shape: token -> (part_of_speech, Iranian-Persian gloss). One combined dict
# (not two parallel ones) so a POS can never drift out of sync with the
# gloss that was written for that sense. Iranian Persian throughout -- NOT
# Dari; copying between fa and prs is defect class 1.28 in
# docs/CONTENT_DEFECT_REGISTRY.md. Persian-range codepoints only (U+06CC
# Persian yeh, U+06A9 keheh). Glosses are hand-written against each unit's
# realization text and cross-checked against -- not copy-pasted from -- that
# unit's own docs/content/overlays/fa-en/*.yaml teaching-card glosses (the
# overlay glosses are phrase-level; Lexeme.english_gloss must be atomic
# because it is shown as the literal answer text of a `slot_gloss`
# multiple_choice/translation item).
FA_EN_EXTRA_LEXEMES: dict[str, tuple[str, str]] = {
    # --- a1 unit49: sorting household waste -------------------------------
    "sort": ("verb", "دسته‌بندی کردن"),
    "waste": ("noun", "زباله"),
    "bin": ("noun", "سطل زباله"),
    "recycle": ("verb", "بازیافت کردن"),
    "glass": ("noun", "شیشه"),
    "paper": ("noun", "کاغذ"),
    "collection": ("noun", "جمع‌آوری (در collection day)"),
    "recycling": ("noun", "بازیافت"),
    "food": ("noun", "غذا"),
    "jar": ("noun", "شیشهٔ ظرف"),
    "bins": ("noun", "سطل‌ها"),
    "tuesdays": ("noun", "سه‌شنبه‌ها"),
    "fridays": ("noun", "جمعه‌ها"),
    "correctly": ("adverb", "به‌درستی"),
    "buildings": ("noun", "ساختمان‌ها"),
    "kinds": ("noun", "انواع"),
    "practicing": ("verb", "در حال تمرین کردن"),
    "afterward": ("adverb", "بعد از آن"),
    "stopped": ("verb", "متوقف کرد؛ جلوی کاری را گرفت"),
    "showed": ("verb", "نشان داد"),
    "sorts": ("verb", "دسته‌بندی می‌کند"),
    "explained": ("verb", "توضیح داد"),
    # --- a1 unit50: booking and using accommodation -----------------------
    "hotel": ("noun", "هتل"),
    "staying": ("verb", "اقامت داشتن"),
    "beds": ("noun", "تخت‌ها"),
    "reservation": ("noun", "رزرو"),
    "included": ("adjective", "شامل قیمت"),
    "check-out": ("noun", "تسویه و ترک هتل"),
    "key": ("noun", "کلید"),
    "under": ("preposition", "به نام (در under the name)"),
    "downstairs": ("adverb", "طبقهٔ پایین"),
    "guesthouse": ("noun", "مهمان‌پذیر"),
    "mountains": ("noun", "کوه‌ها"),
    "november": ("noun", "نوامبر"),
    "14th": ("noun", "چهاردهم"),
    "16th": ("noun", "شانزدهم"),
    "picture": ("noun", "عکس"),
    "view": ("noun", "منظره"),
    "window": ("noun", "پنجره"),
    "stayed": ("verb", "ماند"),
    "cooked": ("verb", "آشپزی کرد"),
    "himself": ("pronoun", "خودش (مذکر)"),
    "loved": ("verb", "خیلی دوست داشت"),
    # --- a1 unit51: buying medicine at the pharmacy -----------------------
    "pharmacist": ("noun", "داروساز"),
    "syrup": ("noun", "شربت"),
    "runny": ("adjective", "آبریزش‌دار (در runny nose)"),
    "nose": ("noun", "بینی"),
    "hours": ("noun", "ساعت‌های کاری"),
    "tablets": ("noun", "قرص‌ها"),
    "felt": ("verb", "احساس کرد"),
    "walked": ("verb", "پیاده رفت"),
    "listened": ("verb", "گوش داد"),
    "symptoms": ("noun", "علائم بیماری"),
    "recommended": ("verb", "توصیه کرد"),
    "box": ("noun", "جعبه"),
    "tissues": ("noun", "دستمال کاغذی"),
    # --- a1 unit52: a haircut and personal care ---------------------------
    "haircut": ("noun", "کوتاه کردن مو"),
    "hairdresser": ("noun", "آرایشگر"),
    "trim": ("noun", "کمی کوتاه کردن مو"),
    "shorter": ("adjective", "کوتاه‌تر"),
    "style": ("noun", "مدل مو"),
    "visit": ("noun", "مراجعه"),
    "salon": ("noun", "آرایشگاه"),
    "washed": ("verb", "شست"),
    "looked": ("verb", "نگاه کرد"),
    "met": ("verb", "ملاقات کرد"),
    # --- a1 unit53: renting a bike ----------------------------------------
    "rent": ("verb", "کرایه کردن"),
    "hour": ("noun", "ساعت (واحد زمان)"),
    "costs": ("verb", "قیمتش چقدر است"),
    "helmet": ("noun", "کلاه ایمنی"),
    "we'd": ("pronoun", "ما می‌خواهیم (مخفف we would)"),
    "bikes": ("noun", "دوچرخه‌ها"),
    "river": ("noun", "رودخانه"),
    "invited": ("verb", "دعوت کرد"),
    "neither": ("particle", "هیچ‌کدام"),
    "owned": ("verb", "مالکش بود"),
    "rental": ("noun", "کرایه"),
    "needed": ("verb", "لازم داشت"),
    "enjoying": ("verb", "در حال لذت بردن"),
    "join": ("verb", "ملحق شدن"),
    # --- a1 unit54: using a laundromat ------------------------------------
    "laundromat": ("noun", "لباس‌شویی عمومی"),
    "machine": ("noun", "ماشین لباسشویی"),
    "broken": ("adjective", "خراب"),
    "dryer": ("noun", "خشک‌کن"),
    "clothes": ("noun", "لباس‌ها"),
    "quarters": ("noun", "سکه‌های بیست‌وپنج‌سنتی"),
    "machines": ("noun", "ماشین‌ها"),
    "detergent": ("noun", "پودر لباسشویی"),
    "load": ("noun", "یک نوبت لباس"),
    "cycle": ("noun", "دور شست‌وشو"),
    "pick": ("verb", "برداشتن (در pick up)"),
    "broke": ("verb", "خراب شد (در broke down)"),
    "down": ("particle", "از کار افتادن (در break down)"),
    "attendant": ("noun", "مسئول"),
    "talked": ("verb", "صحبت کرد"),
    "kept": ("verb", "نگه داشت"),
    "probably": ("adverb", "احتمالاً"),
    "fixed": ("verb", "درست کرد"),
    # --- a1 unit55: a trip to the swimming pool ---------------------------
    "enter": ("verb", "وارد شدن"),
    "locker": ("noun", "کمد قفل‌دار"),
    "swim": ("verb", "شنا کردن"),
    "cap": ("noun", "کلاه شنا"),
    "wear": ("verb", "پوشیدن"),
    "rules": ("noun", "قوانین"),
    "read": ("verb", "خواندن"),
    "lifeguard": ("noun", "غریق‌نجات"),
    "watches": ("verb", "مراقب است"),
    "lockers": ("noun", "کمدها"),
    "tickets": ("noun", "بلیت‌ها"),
    "caps": ("noun", "کلاه‌های شنا"),
    "required": ("adjective", "الزامی"),
    "entrance": ("noun", "ورودی"),
    "dollar": ("noun", "دلار"),
    "coin": ("noun", "سکه"),
    "cool": ("adjective", "خنک"),
    "sign": ("noun", "تابلو"),
    "listed": ("verb", "نوشته بود"),
    "bags": ("noun", "کیف‌ها"),
    "swam": ("verb", "شنا کرد"),
    "try": ("verb", "امتحان کردن"),
    "diving": ("noun", "شیرجه (در diving board)"),
    "board": ("noun", "تخته (در diving board)"),
    # --- a1 unit56: eating at a restaurant --------------------------------
    "waiter": ("noun", "گارسون"),
    "table": ("noun", "میز"),
    "order": ("verb", "سفارش دادن"),
    "chicken": ("noun", "مرغ"),
    "meal": ("noun", "وعدهٔ غذا"),
    "sit": ("verb", "نشستن"),
    "nineteen": ("noun", "نوزده"),
    "pizza": ("noun", "پیتزا"),
    "juice": ("noun", "آبمیوه"),
    "brought": ("verb", "آورد"),
    "ordered": ("verb", "سفارش داد"),
    "excellent": ("adjective", "عالی"),
    # --- a1 unit57: an evening at the cinema ------------------------------
    "cinema": ("noun", "سینما"),
    "popular": ("adjective", "پرطرفدار"),
    "showtime": ("noun", "زمان اکران"),
    "film": ("noun", "فیلم"),
    "seat": ("noun", "صندلی"),
    "screen": ("noun", "صفحهٔ نمایش"),
    "popcorn": ("noun", "پاپ‌کورن"),
    "start": ("verb", "شروع شدن"),
    "liked": ("verb", "دوست داشت"),
    "sixteen": ("noun", "شانزده"),
    "schedule": ("noun", "برنامهٔ زمانی"),
    "star": ("noun", "ستاره"),
    "journey": ("noun", "سفر"),
    "7:00": ("symbol", "۷:۰۰"),
    "$8": ("symbol", "۸ دلار"),
    "race": ("noun", "مسابقه"),
    "5:00": ("symbol", "۵:۰۰"),
    "$10": ("symbol", "۱۰ دلار"),
    "9:00": ("symbol", "۹:۰۰"),
    "$6": ("symbol", "۶ دلار"),
    "cashier": ("noun", "باجه‌دار"),
    "explorers": ("noun", "کاشفان"),
    # --- a1 unit58: an afternoon at the museum ----------------------------
    "museum": ("noun", "موزه"),
    "exhibition": ("noun", "نمایشگاه"),
    "sculpture": ("noun", "مجسمه"),
    "guide": ("noun", "راهنما"),
    "enjoyed": ("verb", "لذت برد"),
    "paintings": ("noun", "نقاشی‌ها"),
    "city": ("noun", "شهر"),
    "adult": ("noun", "بزرگسال"),
    "current": ("adjective", "فعلی"),
    "town": ("noun", "شهر کوچک"),
    "square": ("noun", "میدان"),
    "sunset": ("noun", "غروب"),
    # --- a1 unit59: basic banking -----------------------------------------
    "atm": ("noun", "دستگاه خودپرداز"),
    "pin": ("noun", "رمز کارت"),
    "4:00": ("symbol", "۴:۰۰"),
    "limit": ("noun", "سقف برداشت"),
    "$100": ("symbol", "۱۰۰ دلار"),
    "accepted": ("adjective", "پذیرفته‌شده"),
    "quick": ("adjective", "کوتاه؛ سریع"),
    "entered": ("verb", "وارد کرد"),
    # --- a1 unit60: inviting someone --------------------------------------
    "invitation": ("noun", "دعوت‌نامه"),
    "picnic": ("noun", "پیک‌نیک"),
    "6:00": ("symbol", "۶:۰۰"),
    "18": ("symbol", "۱۸"),
    "wrote": ("verb", "نوشت"),
    # --- a1 unit61: apologising and giving an excuse ----------------------
    "traffic": ("noun", "ترافیک"),
    "mistake": ("noun", "اشتباه"),
    "starts": ("verb", "شروع می‌شود"),
    "waiting": ("verb", "در حال صبر کردن"),
    "note": ("noun", "یادداشت"),
    "3:00": ("symbol", "۳:۰۰"),
    "apology": ("noun", "عذرخواهی"),
    "classroom": ("noun", "کلاس درس"),
    # --- a1 unit62: short phone calls -------------------------------------
    "voicemail": ("noun", "پیام صوتی"),
    "sound": ("noun", "صدا"),
    "clear": ("adjective", "واضح"),
    # --- a1 unit63: asking a neighbour for help ---------------------------
    "carry": ("verb", "حمل کردن"),
    "heavy": ("adjective", "سنگین"),
    "shelf": ("noun", "قفسه"),
    "carried": ("verb", "حمل کرد"),
    # --- a1 unit64: paying a compliment -----------------------------------
    "lovely": ("adjective", "خیلی قشنگ"),
    "kind": ("adjective", "مهربان"),
    "smile": ("noun", "لبخند"),
    "being": ("verb", "بودن (در Thanks for being kind)"),
    "compliment": ("noun", "تعریف"),
    # --- a1 unit65: returns and exchanges ---------------------------------
    "exchange": ("verb", "تعویض کردن"),
    "larger": ("adjective", "بزرگ‌تر"),
    "refund": ("noun", "بازپرداخت"),
    "offered": ("verb", "پیشنهاد داد"),
    "exchanged": ("verb", "تعویض کرد"),
    # --- a1 unit66: describing a symptom at the pharmacy ------------------
    "symptom": ("noun", "علامت بیماری"),
    "hurts": ("verb", "درد می‌کند"),
    # --- a1 unit67: sharing family news -----------------------------------
    "news": ("noun", "خبر"),
    "baby": ("noun", "نوزاد"),
    "proud": ("adjective", "مفتخر"),
    "must": ("verb", "حتماً (نتیجه‌گیری از شواهد)"),
    "shared": ("verb", "به اشتراک گذاشت"),
    # --- a1 unit68: borrowing and lending ---------------------------------
    "lend": ("verb", "قرض دادن"),
    "charger": ("noun", "شارژر"),
    "lending": ("noun", "قرض‌دهی"),
    "leila's": ("pronoun", "مالِ لیلا"),
    "share": ("verb", "شریک شدن"),
    "lent": ("verb", "قرض داد"),
    "remember": ("verb", "به یاد آوردن"),
    # --- a2 unit30: a job interview ---------------------------------------
    "experience": ("noun", "سابقهٔ کار"),
    "position": ("noun", "موقعیت شغلی"),
    "availability": ("noun", "زمان در دسترس بودن"),
    "strength": ("noun", "نقطهٔ قوت"),
    "requirement": ("noun", "شرط لازم"),
    "social": ("adjective", "اجتماعی (در social media)"),
    "media": ("noun", "رسانه (در social media)"),
    "marketing": ("noun", "بازاریابی"),
    "strengths": ("noun", "نقاط قوت"),
    "resume": ("noun", "رزومه"),
    "deadline": ("noun", "مهلت انجام کار"),
    "path": ("noun", "مسیر"),
    "looking": ("verb", "دنبال چیزی گشتن"),
    "coordinator": ("noun", "هماهنگ‌کننده"),
    "requirements": ("noun", "شرایط لازم"),
    "writing": ("noun", "نوشتن"),
    "immediately": ("adverb", "فوراً"),
    "interview": ("noun", "مصاحبه"),
    "deadlines": ("noun", "مهلت‌ها"),
    "managed": ("verb", "مدیریت کرد"),
    "questions": ("noun", "سؤال‌ها"),
    "role": ("noun", "نقش شغلی"),
    "typical": ("adjective", "معمولی"),
    # --- a2 unit31: a travel disruption -----------------------------------
    "delay": ("noun", "تأخیر"),
    "cancelled": ("adjective", "لغو شده"),
    "alternative": ("noun", "گزینهٔ جایگزین"),
    "signal": ("noun", "سیگنال"),
    "delayed": ("adjective", "با تأخیر"),
    "5:15": ("symbol", "۵:۱۵"),
    "5:30": ("symbol", "۵:۳۰"),
    "station": ("noun", "ایستگاه"),
    "tracks": ("noun", "ریل‌ها"),
    # --- a2 unit32: talking about online habits ---------------------------
    "messaging": ("adjective", "پیام‌رسان"),
    "notification": ("noun", "اعلان"),
    "useful": ("adjective", "مفید"),
    "touch": ("noun", "تماس (در in touch)"),
    "notifications": ("noun", "اعلان‌ها"),
    "sharing": ("noun", "به اشتراک گذاشتن"),
    "spend": ("verb", "صرف کردن وقت"),
    "thing": ("noun", "چیز"),
    # --- a2 unit33: describing a weekly schedule --------------------------
    "weekday": ("noun", "روز کاری هفته"),
    "weekdays": ("noun", "روزهای کاری هفته"),
    "email": ("noun", "ایمیل"),
    "online": ("adjective", "آنلاین"),
    "mondays": ("noun", "دوشنبه‌ها"),
    "wednesdays": ("noun", "چهارشنبه‌ها"),
    # --- a2 unit34: making a shopping complaint ---------------------------
    "policy": ("noun", "قوانین بازگشت کالا"),
    "defective": ("adjective", "معیوب"),
    "blender": ("noun", "مخلوط‌کن"),
    "working": ("verb", "کار کردن"),
    "30": ("symbol", "۳۰"),
    "refunded": ("verb", "بازپرداخت شد"),
    "thirty-five": ("noun", "سی و پنج"),
    # --- a2 unit35: at the pharmacy (a prescription) ----------------------
    # DRAFT Farsi glosses (2026-08-05), pending Ramin's native audit. POS
    # ported from nl-en EN_EXTRA. Colloquial Iranian register; senses pinned
    # to the a2_unit35 overlay's own glossary (دوز/تکرار نسخه/عوارض جانبی).
    "dose": ("noun", "دوز؛ مقدار هر بار مصرف دارو"),
    "refill": ("noun", "تکرار نسخه"),
    "refills": ("noun", "تکرار نسخه"),
    "side": ("noun", "جانبی (در side effects)"),
    "effects": ("noun", "عوارض جانبی"),
    "shouldn't": ("verb", "نباید (مخفف should not)"),
    # --- a2 unit36: correcting a document ---------------------------------
    "certificate": ("noun", "گواهی؛ مدرک رسمی"),
    "spelled": ("verb", "هجی کرد؛ حروفش را گفت"),
    "copy": ("noun", "کپی؛ رونوشت"),
    "passport": ("noun", "پاسپورت؛ گذرنامه"),
    "mistakes": ("noun", "اشتباه‌ها"),
    "registration": ("noun", "ثبت‌نام"),
    "correction": ("noun", "اصلاح؛ تصحیح"),
    "corrected": ("verb", "اصلاح کرد؛ تصحیح کرد"),
    "reference": ("noun", "مرجع؛ شمارهٔ پیگیری"),
    "3092": ("symbol", "۳۰۹۲"),
    # --- a2 unit37: video calls -------------------------------------------
    "microphone": ("noun", "میکروفون"),
    "connection": ("noun", "اتصال؛ ارتباط اینترنتی"),
    "mute": ("verb", "بی‌صدا کردن"),
    "face": ("noun", "چهره (در face to face: رو در رو)"),
    "calls": ("noun", "تماس‌ها"),
    "headphones": ("noun", "هدفون"),
    "asks": ("verb", "می‌پرسه"),
    "question": ("noun", "سؤال"),
    "classmates": ("noun", "هم‌کلاسی‌ها"),
    "speaking": ("verb", "صحبت کردن (شکل ing فعل speak)"),
    # --- a2 unit38: a repair visit ----------------------------------------
    "leak": ("noun", "نشتی"),
    "won't": ("verb", "نخواهد (مخفف will not)"),
    "rescheduled": ("verb", "زمانش را عوض کرد؛ موکول کرد"),
    "9am": ("symbol", "۹ صبح"),
    "11am": ("symbol", "۱۱ صبح"),
    # --- a2 unit39: after the interview -----------------------------------
    "contract": ("noun", "قرارداد"),
    "salary": ("noun", "حقوق"),
    "accept": ("verb", "قبول کردن"),
    "interested": ("adjective", "علاقه‌مند"),
    # --- a2 unit40: an online order problem -------------------------------
    "delivery": ("noun", "تحویل؛ ارسال"),
    "parcel": ("noun", "بسته؛ مرسوله"),
    "lamp": ("noun", "چراغ"),
    "8154": ("symbol", "۸۱۵۴"),
    # --- b1 unit01: expressing necessity ----------------------------------
    "task": ("noun", "کار؛ وظیفه"),
    "finish": ("verb", "تمام کردن"),
    "earlier": ("adverb", "زودتر"),
    "forgot": ("verb", "فراموش کرد"),
    "renew": ("verb", "تمدید کردن"),
    "membership": ("noun", "عضویت"),
    "set": ("verb", "تنظیم کردن"),
    "reminder": ("noun", "یادآور"),
    "done": ("verb", "انجام‌داده (قسمت سوم do)"),
    # --- b1 unit02: present and past ability ------------------------------
    "able": ("adjective", "توانا (در be able to)"),
    "manage": ("verb", "موفق شدن"),
    "license": ("noun", "گواهینامه"),
    "person": ("noun", "شخص (در in person: حضوری)"),
    "system": ("noun", "سیستم"),
    "licenses": ("noun", "گواهینامه‌ها"),
    "changed": ("verb", "تغییر کرد"),
    "hers": ("pronoun", "مالِ او (مؤنث)"),
    "wasn't": ("verb", "نبود (مخفف was not)"),
    "save": ("verb", "صرفه‌جویی کردن"),
    # --- b1 unit03: real conditionals -------------------------------------
    "rains": ("verb", "باران می‌بارد"),
    "known": ("verb", "دانسته (قسمت سوم know)"),
    "signed": ("verb", "ثبت‌نام کرد (در sign up)"),
    "checks": ("verb", "دنبال چیزی می‌گردد"),
    # --- b1 unit04: agreeing and disagreeing ------------------------------
    "disagree": ("verb", "مخالف بودن"),
    "believe": ("verb", "باور داشتن"),
    "reason": ("noun", "دلیل"),
    "focus": ("verb", "تمرکز کردن"),
    "respect": ("verb", "احترام گذاشتن"),
    "easily": ("adverb", "به‌راحتی"),
    "disagrees": ("verb", "مخالف است"),
    "believes": ("verb", "باور دارد"),
    "seeing": ("verb", "دیدن"),
    "each": ("adjective", "هر (در each other)"),
    "other's": ("pronoun", "همدیگر (در each other's)"),
    "important": ("adjective", "مهم"),
    "saves": ("verb", "صرفه‌جویی می‌کند"),
    # --- b1 unit05: workplace status updates ------------------------------
    "responsible": ("adjective", "مسئول"),
    "technical": ("adjective", "فنی"),
    "sales": ("noun", "فروش"),
    "gives": ("verb", "می‌دهد"),
    "expects": ("verb", "انتظار دارد"),
    "tells": ("verb", "می‌گوید"),
    "truth": ("noun", "حقیقت"),
    "delays": ("noun", "تأخیرها"),
    "review": ("verb", "مرور کردن"),
    "numbers": ("noun", "اعداد"),
    "correct": ("adjective", "درست"),
    "notes": ("noun", "یادداشت‌ها"),
    "appreciate": ("verb", "قدردانی کردن"),
    # --- b1 unit06: narrating a past event --------------------------------
    "flat": ("adjective", "پنچر"),
    "tire": ("noun", "لاستیک"),
    "pull": ("verb", "کنار زدن (در pull over)"),
    "stranger": ("noun", "غریبه"),
    "mechanic": ("noun", "مکانیک"),
    "driving": ("verb", "در حال رانندگی"),
    "pulled": ("verb", "کنار زد"),
    "helped": ("verb", "کمک کرد"),
    "word": ("noun", "قول (در keep one's word)"),
    "suddenly": ("adverb", "ناگهان"),
    "happened": ("verb", "اتفاق افتاد"),
    # --- b1 unit07: conditions and consequences ---------------------------
    "unless": ("particle", "مگر این که"),
    "condition": ("noun", "شرط"),
    "result": ("noun", "نتیجه"),
    "present": ("adjective", "حال (زمان دستوری)"),
    "tense": ("noun", "زمان دستوری"),
    "real": ("adjective", "واقعی"),
    "future": ("noun", "آینده"),
    "backup": ("adjective", "جایگزین"),
    "plan": ("noun", "برنامه"),
    "conference": ("noun", "کنفرانس (در conference room)"),
    "joins": ("verb", "وارد جلسه می‌شود"),
    "cannot": ("verb", "نمی‌تواند"),
    # --- b1 unit08: sequencing an evening routine -------------------------
    "lock": ("verb", "قفل کردن"),
    "clause": ("noun", "جمله‌واره"),
    "locks": ("verb", "قفل می‌کند"),
    "careful": ("adjective", "دقیق؛ منظم"),
    "routine": ("noun", "روال"),
    "hands": ("noun", "دست‌ها"),
    "clears": ("verb", "خالی می‌کند"),
    # --- b1 unit09: reported speech ---------------------------------------
    "speech": ("noun", "گفتار (در reported speech)"),
    "reported": ("adjective", "نقل‌شده"),
    "summary": ("noun", "خلاصه"),
    "enough": ("adjective", "کافی"),
    "full": ("adjective", "کامل"),
    "reply": ("verb", "جواب دادن"),
    # --- b1 unit10: expressing purpose ------------------------------------
    "goal": ("noun", "هدف"),
    "design": ("noun", "طراحی"),
    "improve": ("verb", "بهتر کردن"),
    "money": ("noun", "پول"),
    "prepare": ("verb", "آماده شدن"),
    "english": ("noun", "انگلیسی"),
    "vocabulary": ("noun", "واژگان"),
    "verb": ("noun", "فعل"),
    "goals": ("noun", "هدف‌ها"),
    "practices": ("verb", "تمرین می‌کند"),
    "updates": ("noun", "گزارش‌های پیشرفت"),
    "descriptions": ("noun", "توضیحات"),
    "program": ("noun", "برنامهٔ آموزشی"),
    "saving": ("verb", "در حال پس‌انداز کردن"),
    # --- b1 unit11: unreal hypotheticals ----------------------------------
    "rather": ("adverb", "ترجیحاً (در would rather)"),
    "opportunity": ("noun", "فرصت"),
    "regret": ("noun", "حسرت"),
    "chance": ("noun", "شانس"),
    "unreal": ("adjective", "غیرواقعی"),
    "situation": ("noun", "موقعیت"),
    "sooner": ("adverb", "زودتر"),
    "confident": ("adjective", "بااعتمادبه‌نفس"),
    "joined": ("verb", "ملحق شد"),
    "timing": ("noun", "زمان‌بندی"),
    "saved": ("verb", "پس‌انداز کرد"),
    # --- b1 unit12: concession --------------------------------------------
    "although": ("particle", "با این که"),
    "despite": ("preposition", "با وجود"),
    "distractions": ("noun", "حواس‌پرتی‌ها"),
    "however": ("adverb", "با این حال"),
    "valid": ("adjective", "درست؛ منطقی"),
    "convince": ("verb", "متقاعد کردن"),
    "followed": ("verb", "دنبال می‌شود (در followed by)"),
    "noun": ("noun", "اسم (دستور زبان)"),
    "sentence": ("noun", "جمله"),
    "period": ("noun", "نقطه (نشانهٔ نگارشی)"),
    "semicolon": ("noun", "نقطه‌ویرگول"),
    "flexibility": ("noun", "انعطاف‌پذیری"),
    "teamwork": ("noun", "کار تیمی"),
    "builds": ("verb", "می‌سازد"),
    "misses": ("verb", "دلش تنگ می‌شود"),
    "colleagues": ("noun", "همکاران"),
    "during": ("preposition", "در طول"),
    "breaks": ("noun", "وقت استراحت"),
    "noise": ("noun", "سروصدا"),
    "alone": ("adverb", "تنها"),
    "matters": ("verb", "مهم است"),
    "preferences": ("noun", "ترجیح‌ها"),
    # --- b1 unit13: relative clauses --------------------------------------
    "whose": ("pronoun", "که ... او (نشان‌دهندهٔ مالکیت)"),
    "approved": ("verb", "تأیید کرد"),
    "colleague": ("noun", "همکار (رسمی)"),
    "sits": ("verb", "می‌نشیند"),
    "leads": ("verb", "اداره می‌کند"),
    "projects": ("noun", "پروژه‌ها"),
    "defining": ("adjective", "تعیین‌کننده (جملهٔ موصولی)"),
    "relative": ("adjective", "موصولی"),
    "commas": ("noun", "ویرگول‌ها"),
    "exactly": ("adverb", "دقیقاً"),
    "mean": ("verb", "معنی دادن"),
    "non-defining": ("adjective", "غیرتعیین‌کننده"),
    "extra": ("adjective", "اضافی"),
    "information": ("noun", "اطلاعات"),
    "identified": ("verb", "شناسایی‌شده"),
    "approve": ("verb", "تأیید کردن"),
    "easier": ("adjective", "راحت‌تر"),
    "fifth": ("adjective", "پنجم"),
    "floor": ("noun", "طبقه"),
    "eats": ("verb", "غذا می‌خورد"),
    "finishing": ("verb", "در حال تمام کردن"),
    "has already": ("phrase", "قبلاً کاری را کرده است"),
    "woman": ("noun", "زن"),
    "designer": ("noun", "طراح"),
    "logo": ("noun", "لوگو"),
    "won": ("verb", "برنده شد"),
    "award": ("noun", "جایزه"),
    "ours": ("pronoun", "مالِ ما"),
    "explains": ("verb", "توضیح می‌دهد"),
    # --- b1 unit14: professional communication ----------------------------
    "possibly": ("adverb", "احتمالاً (در could we possibly)"),
    "agenda": ("noun", "دستور جلسه"),
    "formal": ("adjective", "رسمی"),
    "workplace": ("noun", "محیط کار"),
    "requests": ("noun", "درخواست‌ها"),
    "softened": ("adjective", "نرم‌شده"),
    "conditional": ("adjective", "شرطی"),
    "command": ("noun", "دستور"),
    "forms": ("noun", "ساختارها"),
    "polite": ("adjective", "مؤدبانه"),
    "budget": ("noun", "بودجه"),
    "hope": ("verb", "امیدوار بودن"),
    "tomorrow's": ("pronoun", "مالِ فردا"),
    "latest": ("adjective", "آخرین"),
    "client": ("noun", "مشتری"),
    "best": ("adjective", "بهترین (در do my best)"),
    "advance": ("noun", "پیش (در in advance)"),
    "request": ("noun", "درخواست"),
    "updated": ("adjective", "به‌روزشده"),
    # --- b1 unit15: making a complaint ------------------------------------
    "complain": ("verb", "شکایت کردن"),
    "damaged": ("adjective", "آسیب‌دیده"),
    "replacement": ("noun", "کالای جایگزین"),
    "resolve": ("verb", "حل کردن"),
    "issue": ("noun", "ایراد"),
    "product": ("noun", "کالا"),
    "written": ("adjective", "کتبی"),
    "complaint": ("noun", "شکایت"),
    "parts": ("noun", "بخش‌ها"),
    "specific": ("adjective", "مشخص"),
    "resolution": ("noun", "راه‌حل"),
    "chair": ("noun", "صندلی میز کار"),
    "dear": ("adjective", "عزیز"),
    "wheel": ("noun", "چرخ"),
    "proceed": ("verb", "ادامه دادن"),
    "calling": ("verb", "در حال تماس گرفتن"),
    # --- b1 unit16: giving advice -----------------------------------------
    "advice": ("noun", "نصیحت"),
    "overwhelmed": ("adjective", "غرق کار"),
    "prioritize": ("verb", "در اولویت قرار دادن"),
    "workload": ("noun", "حجم کاری"),
    "decline": ("verb", "مؤدبانه رد کردن"),
    "closer": ("adjective", "نزدیک‌تر"),
    "asking": ("verb", "درخواست کردن"),
    "suggestions": ("noun", "پیشنهادها"),
    "hypothetical": ("noun", "فرض غیرواقعی"),
    "recommendation": ("noun", "توصیه"),
    "softer": ("adjective", "نرم‌تر"),
    "suggestion": ("noun", "پیشنهاد"),
    "stronger": ("adjective", "قوی‌تر"),
    "depending": ("verb", "بستگی داشتن (در depending on)"),
    "top": ("noun", "بالا (در on top of that: علاوه بر این)"),
    "leading": ("verb", "رهبری کردن"),
    "seem": ("verb", "به نظر رسیدن"),
    "handle": ("verb", "از پس کاری برآمدن"),
    "solid": ("adjective", "محکم"),
    # --- b1 unit17: expressing regret -------------------------------------
    "hindsight": ("noun", "درک پس از وقوع"),
    "procrastinate": ("verb", "کار را عقب انداختن"),
    "participle": ("noun", "قسمت سوم فعل"),
    "happen": ("verb", "اتفاق افتادن"),
    "missed": ("adjective", "ازدست‌رفته"),
    "end": ("noun", "آخر (در in the end)"),
    "true": ("adjective", "درست"),
    # --- b1 unit18: future plans ------------------------------------------
    "arrangement": ("noun", "قرار از پیش تعیین‌شده"),
    "intention": ("noun", "قصد"),
    "prediction": ("noun", "پیش‌بینی"),
    "months": ("noun", "ماه‌ها"),
    "continuous": ("adjective", "استمراری"),
    "agreed": ("verb", "هماهنگ‌شده"),
    "decision": ("noun", "تصمیم"),
    "steps": ("noun", "قدم‌ها"),
    "completely": ("adverb", "کاملاً"),
    "predicts": ("verb", "پیش‌بینی می‌کند"),
    "agrees": ("verb", "قبول می‌کند"),
    "exciting": ("adjective", "هیجان‌انگیز"),
    # --- b1 unit19: summarising -------------------------------------------
    "detail": ("noun", "نکتهٔ جزئی"),
    "words": ("noun", "کلمات"),
    "covered": ("verb", "به چیزی پرداخت"),
    "phrase": ("noun", "عبارت"),
    "points": ("noun", "نکته‌ها"),
    "keeping": ("verb", "نگه داشتن"),
    "highlight": ("verb", "برجسته کردن"),
    "single": ("adjective", "تکی"),
    "separately": ("adverb", "جداگانه"),
    "condensed": ("adjective", "خلاصه‌شده"),
    "original": ("adjective", "اولیه"),
    "article": ("noun", "مقاله"),
    "communication": ("noun", "ارتباطات"),
    "examples": ("noun", "مثال‌ها"),
    "background": ("noun", "پس‌زمینه"),
    "messages": ("noun", "پیام‌ها"),
    "guessing": ("verb", "حدس زدن"),
    "ideas": ("noun", "ایده‌ها"),
    # --- b2 unit01: building an argument ----------------------------------
    "claim": ("noun", "ادعا"),
    "evidence": ("noun", "شواهد"),
    "counterargument": ("noun", "استدلال مخالف"),
    "rebut": ("verb", "جواب دادن به مخالفت"),
    "concede": ("verb", "پذیرفتن بخشی از حرف طرف مقابل"),
    "outweigh": ("verb", "مهم‌تر بودن"),
    "risks": ("noun", "ریسک‌ها"),
    "supports": ("verb", "تأیید می‌کند"),
    "moving": ("verb", "پیش رفتن (در moving forward)"),
    "forward": ("adverb", "به جلو"),
    "strongest": ("adjective", "قوی‌ترین"),
    "survey": ("noun", "نظرسنجی"),
    "results": ("noun", "نتایج"),
    "consistent": ("adjective", "یکدست"),
    "concern": ("noun", "نگرانی"),
    "data": ("noun", "داده‌ها"),
    "direction": ("noun", "جهت"),
    "defended": ("adjective", "دفاع‌شده"),
    "moves": ("noun", "مرحله‌های استدلال"),
    "state": ("verb", "بیان کردن"),
    "acknowledge": ("verb", "پذیرفتن"),
    "opposing": ("adjective", "مخالف"),
    "phrases": ("noun", "عبارت‌ها"),
    "reasonable": ("adjective", "منطقی"),
    "conceding": ("verb", "واگذار کردن"),
    "retention": ("noun", "حفظ کارکنان"),
    "collaboration": ("noun", "همکاری"),
    "argues": ("verb", "استدلال می‌کند"),
    "hybrid": ("adjective", "ترکیبی"),
    "improves": ("verb", "بهتر می‌کند"),
    "lowering": ("verb", "پایین آوردن"),
    "performance": ("noun", "عملکرد"),
    "employees": ("noun", "کارمندان"),
    "teams": ("noun", "تیم‌ها"),
    "less": ("adverb", "کمتر"),
    "likely": ("adjective", "محتمل"),
    "may": ("verb", "ممکن است"),
    "suffer": ("verb", "آسیب دیدن"),
    "acknowledges": ("verb", "می‌پذیرد"),
    "delivered": ("verb", "تحویل داد"),
    "scores": ("noun", "امتیازها"),
    "slightly": ("adverb", "کمی"),
    "higher": ("adjective", "بالاتر"),
    "concludes": ("verb", "نتیجه می‌گیرد"),
    "benefits": ("noun", "مزایا"),
    "managers": ("noun", "مدیرها"),
    "weaker": ("adjective", "ضعیف‌تر"),
    "support": ("verb", "تأیید کردن"),
    "routines": ("noun", "روال‌ها"),
    "abandon": ("verb", "کنار گذاشتن"),
    # --- b2 unit02: speculation and deduction -----------------------------
    "deduction": ("noun", "نتیجه‌گیری از شواهد"),
    "guesswork": ("noun", "حدس بی‌پایه"),
    "overlap": ("verb", "هم‌پوشانی داشتن"),
    "explanation": ("noun", "توضیح"),
    "tentative": ("adjective", "محتاطانه"),
    "server": ("noun", "سرور"),
    "gone": ("verb", "رفته (قسمت سوم go)"),
    "overnight": ("adverb", "در طول شب"),
    "generated": ("verb", "ساخته شد"),
    "failed": ("verb", "اجرا نشد"),
    "permission": ("noun", "دسترسی"),
    "possibility": ("noun", "احتمال"),
    "uncertain": ("adjective", "نامطمئن"),
    "outage": ("noun", "قطعی سیستم"),
    "consequence": ("noun", "پیامد"),
    "monitoring": ("adjective", "مانیتورینگ"),
    "page": ("noun", "صفحه"),
    "blank": ("adjective", "خالی"),
    "suggests": ("verb", "احتمال می‌دهد"),
    "explain": ("verb", "توضیح دادن"),
    "finance": ("noun", "مالی"),
    "missing": ("adjective", "ناموجود"),
    "dashboard": ("noun", "داشبورد"),
    "rebuilt": ("verb", "دوباره ساخته شد"),
    "certain": ("adjective", "مطمئن"),
    "pure": ("adjective", "کاملاً بی‌پایه"),
    "none": ("pronoun", "هیچ‌کدام"),
    "consequences": ("noun", "پیامدها"),
    "expect": ("verb", "انتظار داشتن"),
    "guess": ("noun", "حدس"),
    "limited": ("adjective", "محدود"),
    # --- b2 unit03: hedging and emphasis ----------------------------------
    "hedge": ("verb", "محتاط‌تر گفتن"),
    "qualify": ("verb", "محدود کردن ادعا"),
    "emphasize": ("verb", "تأکید کردن"),
    "extent": ("noun", "حد (در to some extent)"),
    "broadly": ("adverb", "در کل"),
    "provided": ("particle", "به شرطی که"),
    "create": ("verb", "ایجاد کردن"),
    "worries": ("verb", "نگران می‌کند"),
    "timeline": ("noun", "زمان‌بندی"),
    "adjusted": ("adjective", "تنظیم‌شده"),
    "attention": ("noun", "توجه"),
    "overall": ("adverb", "در مجموع"),
    "feedback": ("noun", "بازخورد"),
    "positive": ("adjective", "مثبت"),
    "carefully": ("adverb", "با دقت"),
    "qualified": ("adjective", "مشروط‌شده"),
    "avoids": ("verb", "جلوگیری می‌کند"),
    "sounding": ("verb", "به نظر رسیدن"),
    "absolute": ("adjective", "مطلق"),
    "limits": ("verb", "محدود می‌کند"),
    "accepting": ("verb", "پذیرفتن"),
    "construction": ("noun", "ساختار"),
    "speakers": ("noun", "گویندگان"),
    "principle": ("noun", "اصل"),
    "language": ("noun", "زبان"),
    "shows": ("verb", "نشان می‌دهد"),
    "levels": ("noun", "سطح‌ها"),
    "commitment": ("noun", "تعهد"),
    "cautious": ("adjective", "محتاطانه"),
    "saying": ("verb", "گفتن"),
    "fully": ("adverb", "کاملاً"),
    "workable": ("adjective", "قابل اجرا"),
    "clearer": ("adjective", "روشن‌تر"),
    "quality": ("noun", "کیفیت"),
    "adds": ("verb", "اضافه می‌کند"),
    "approval": ("noun", "تأیید"),
    "step": ("noun", "مرحله"),
    "conditions": ("noun", "شرط‌ها"),
    "creates": ("verb", "ایجاد می‌کند"),
    # --- b2 unit04: narrative time ----------------------------------------
    "foreground": ("noun", "رویداد اصلی"),
    "prior": ("adjective", "پیشین"),
    "interrupt": ("verb", "قطع کردن"),
    "interrupted": ("verb", "قطع کرد"),
    "ongoing": ("adjective", "ادامه‌دار"),
    "chronology": ("noun", "ترتیب زمانی"),
    "equipment": ("noun", "تجهیزات"),
    "power": ("noun", "برق"),
    "volunteers": ("noun", "داوطلب‌ها"),
    "setting": ("verb", "در حال چیدن (در setting up)"),
    "chairs": ("noun", "صندلی‌ها"),
    "simple": ("adjective", "ساده"),
    "events": ("noun", "رویدادها"),
    "moment": ("noun", "لحظه"),
    "venue": ("noun", "محل برگزاری"),
    "simon": ("proper_noun", "سایمون"),
    "strict": ("adjective", "دقیق"),
    "chronological": ("adjective", "زمانی"),
    "expected": ("adjective", "پیش‌بینی‌شده"),
    "crew": ("noun", "گروه کاری"),
    "lights": ("noun", "چراغ‌ها"),
    "through": ("preposition", "از ابتدا تا انتها (در walk through)"),
    "event": ("noun", "برنامه؛ رویداد"),
    # --- b2 unit05: register and formality --------------------------------
    "register": ("noun", "لحن و درجهٔ رسمی بودن"),
    "casual": ("adjective", "خودمانی"),
    "audience": ("noun", "مخاطب"),
    "institution": ("noun", "نهاد"),
    "grateful": ("adjective", "ممنون"),
    "scheduling": ("adjective", "زمان‌بندی (در Scheduling Team)"),
    "content": ("noun", "محتوا"),
    "shift": ("verb", "تغییر کردن"),
    "stiff": ("adjective", "خشک و زیادی رسمی"),
    "appropriate": ("adjective", "مناسب"),
    "nina": ("proper_noun", "نینا"),
    "clinic": ("noun", "کلینیک"),
    "texts": ("noun", "متن‌ها"),
    "stays": ("verb", "ثابت می‌ماند"),
    "level": ("noun", "سطح"),
    "formality": ("noun", "رسمی بودن"),
    # --- b2 unit06: abstract values ---------------------------------------
    "value": ("noun", "ارزش"),
    "public": ("adjective", "عمومی"),
    "spaces": ("noun", "فضاها"),
    "fairness": ("noun", "انصاف"),
    "convenience": ("noun", "راحتی"),
    "qualification": ("noun", "محدود کردن ادعا"),
    "weight": ("noun", "وزن"),
    "arguing": ("verb", "استدلال کردن"),
    "silence": ("noun", "سکوت"),
    "businesses": ("noun", "کسب‌وکارها"),
    "response": ("noun", "پاسخ"),
    "directly": ("adverb", "مستقیم"),
    "person's": ("pronoun", "مالِ شخص"),
    "transparent": ("adjective", "شفاف"),
    "commercial": ("adjective", "تجاری"),
    "amara": ("proper_noun", "آمارا"),
    "protected": ("verb", "محافظت شود"),
    "activity": ("noun", "فعالیت"),
    "accepts": ("verb", "قبول دارد"),
    "leo's": ("pronoun", "مالِ لئو"),
    "harder": ("adjective", "سخت‌تر"),
    "survive": ("verb", "دوام آوردن"),
    "belongs": ("verb", "متعلق است"),
    "stance": ("noun", "موضع"),
    "unlimited": ("adjective", "بی‌حد"),
    "restrictions": ("noun", "محدودیت‌ها"),
    "protect": ("verb", "محافظت کردن"),
    "shaped": ("verb", "شکل گرفتن"),
    "profit": ("noun", "سود"),
    "comfort": ("noun", "آسایش"),
    # --- b2 unit07: negotiating terms -------------------------------------
    "term": ("noun", "بند توافق"),
    "agreement": ("noun", "توافق"),
    "proposal": ("noun", "پیشنهاد"),
    "refusal": ("noun", "رد کردن"),
    "concession": ("noun", "امتیاز مشروط"),
    "scope": ("noun", "محدودهٔ کار"),
    "reduced": ("adjective", "کاهش‌یافته"),
    "appendix": ("noun", "پیوست"),
    "follows": ("verb", "بعداً می‌آید"),
    "push": ("verb", "فشار آوردن"),
    "clearly": ("adverb", "روشن"),
    "offer": ("verb", "پیشنهاد دادن"),
    "executive": ("adjective", "مدیریتی"),
    "charts": ("noun", "نمودارها"),
    "priya": ("proper_noun", "پریا"),
    "proposed": ("verb", "مطرح کرد"),
    "marcus": ("proper_noun", "مارکوس"),
    "outcome": ("noun", "نتیجه"),
    "deliver": ("verb", "تحویل دادن"),
    "planned": ("adjective", "برنامه‌ریزی‌شده"),
    "risk": ("verb", "به خطر انداختن"),
    # --- b2 unit08: synthesising sources ----------------------------------
    "source": ("noun", "منبع"),
    "synthesize": ("verb", "ترکیب کردن اطلاعات منابع"),
    "evaluate": ("verb", "ارزیابی کردن"),
    "conflict": ("noun", "اختلاف"),
    "judgment": ("noun", "قضاوت مستدل"),
    "sources": ("noun", "منابع"),
    "demand": ("noun", "تقاضا"),
    "increased": ("verb", "بیشتر شد"),
    "cause": ("noun", "علت"),
    "operator": ("noun", "اپراتور"),
    "includes": ("verb", "شامل می‌شود"),
    "staffing": ("adjective", "مربوط به کارکنان"),
    "records": ("noun", "سوابق"),
    "supported": ("adjective", "پشتوانه‌دار"),
    "passenger": ("adjective", "مسافر (در passenger survey)"),
    "buses": ("noun", "اتوبوس‌ها"),
    "became": ("verb", "شد"),
    "common": ("adjective", "رایج"),
    "opened": ("verb", "افتتاح شد"),
    "passengers": ("noun", "مسافرها"),
    "route": ("noun", "مسیر"),
    "crowded": ("adjective", "شلوغ"),
    "b": ("symbol", "ب (نشانهٔ منبع B)"),
    "identifies": ("verb", "معرفی می‌کند"),
    "shortages": ("noun", "کمبود"),
    "caused": ("verb", "باعث شد"),
    "tessa": ("proper_noun", "تسا"),
    "accounts": ("noun", "روایت‌ها"),
    "comments": ("noun", "نظرها"),
    "showing": ("verb", "نشان دادن"),
}

# Per-LEVEL sense overrides, applied FIRST and winning over both
# FA_EN_EXTRA_LEXEMES and the shared EN_POS/EN_TARGET_TO_FA_GLOSS.
#
# The shared module can only hold ONE (POS, sense) per bare token string --
# its own documented "close"/"get" homograph limitation. Because A1/A2/B1/B2
# are four SEPARATE courses with four separate Lexeme rows, a token whose
# B2 sense differs from its A1 sense can simply be given a different entry
# per level here, without breaking any already-shipped A1 pack. Every entry
# below is a real sense divergence found while reading the 52 realizations,
# not a stylistic preference.
LEVEL_SENSE_OVERRIDES: dict[tuple[str, str], tuple[str, str]] = {
    # "visit": a1 unit52 teaches the noun ("A visit to the hairdresser"),
    # a2 unit33 uses the verb ("On the weekend, I visit my parents").
    ("a2", "visit"): ("verb", "سر زدن به"),
    # "screen": a1 unit57 is the cinema screen, a2 unit32 is screen time.
    ("a1", "screen"): ("noun", "پردهٔ سینما"),
    # "staying": a1 unit50 is staying AT a hotel, a2 unit32 staying in touch.
    ("a2", "staying"): ("verb", "در ارتباط ماندن (در staying in touch)"),
    # "waste": a1 unit49 is the noun (household waste), a2 unit32 the verb
    # ("it can waste a lot of time").
    ("a2", "waste"): ("verb", "تلف کردن"),
    # "exchange": a1 unit65 teaches the verb, a2 unit34 the noun ("a refund
    # or an exchange").
    ("a2", "exchange"): ("noun", "تعویض کالا"),
    # "start": verb everywhere except b2 unit04, where it is the noun ("we
    # pushed the start back twenty minutes").
    ("b2", "start"): ("noun", "شروع"),
    # "rent": a1 unit53 teaches the verb (renting a bike), b1 unit01 the
    # noun (monthly rent).
    ("b1", "rent"): ("noun", "اجاره"),
    # "sign": a1 unit55 is the noun (a sign at the pool), b1 unit03 the verb
    # ("I'll sign up immediately").
    ("b1", "sign"): ("verb", "ثبت‌نام کردن (در sign up)"),
    # "sound": a1 unit62 is the noun (the sound was not clear), b1/b2 the
    # linking verb ("sound professional"/"sound reasonable").
    ("b1", "sound"): ("verb", "به نظر رسیدن"),
    ("b2", "sound"): ("verb", "به نظر رسیدن"),
    # "order": a1 unit56 teaches ordering food, b1 unit10 is "in order to",
    # b2 unit04 is chronological order.
    ("b1", "order"): ("noun", "منظور (در in order to: برای این که)"),
    ("b2", "order"): ("noun", "ترتیب"),
    # "online": a2 unit33 is attributive (an online class), b1 unit02 is
    # adverbial (renew my license online).
    ("b1", "online"): ("adverb", "آنلاین"),
    # "managed": a2 unit30 is "managed a team", b1 unit02 "managed to
    # finish".
    ("b1", "managed"): ("verb", "موفق شد"),
    # "period": b1 unit12 is the punctuation mark, b2 unit08 a span of time.
    ("b2", "period"): ("noun", "دوره زمانی"),
    # "points": b1 unit19 is the noun (main points), b2 unit01 the verb
    # ("the data points in the other direction").
    ("b2", "points"): ("verb", "اشاره می‌کند"),
    # "position": a2 unit30 is a job position, b2 unit01 an argued stance.
    ("b2", "position"): ("noun", "موضع"),
    # "policy": a2 unit34 is a store return policy, b2 unit03 an
    # organisational policy.
    ("b2", "policy"): ("noun", "سیاست"),
    # "review": b1 unit05 is the verb, b2 unit01 an attributive noun
    # ("review scores").
    ("b2", "review"): ("noun", "بررسی"),
    # "focus": b1 unit04 is the verb, b2 unit03 the noun (a focus
    # construction).
    ("b2", "focus"): ("noun", "تمرکز"),
    # "checks": b1 unit03 is the verb, b2 unit03 the noun (quality checks).
    ("b2", "checks"): ("noun", "بررسی‌ها"),
    # "carry": a1 unit63 is physical carrying, b2 unit06 "carry more
    # weight".
    ("b2", "carry"): ("verb", "وزن داشتن (در carry weight)"),
    # "shared": a1 unit67 is the past verb, b2 unit06 the adjective ("shared
    # spaces").
    ("b2", "shared"): ("adjective", "مشترک"),
    # "view": a1 unit50 is a hotel-window view, b2 unit06 an opinion.
    ("b2", "view"): ("noun", "دیدگاه"),
    # "delayed": a2 unit31 is the adjective ("the train is delayed"), b2
    # unit04 the past verb ("we delayed the start").
    ("b2", "delayed"): ("verb", "عقب انداخت"),
    # "entered": a1 unit59 is entering a PIN, b2 unit04 guests entering a
    # room.
    ("b2", "entered"): ("verb", "وارد شدند"),
    # "rules": a1 unit55 is the noun (pool rules), b2 unit02 the verb
    # ("cannot ... rules out an explanation").
    ("b2", "rules"): ("verb", "رد می‌کند (در rule out)"),
    # Shared-module senses that are wrong for B1/B2. These three tokens ARE
    # in EN_POS, so without an override the B-level lexeme would ship the A1
    # gloss against a completely different sense.
    # "left": EN_POS has the unit10 direction noun; b1 unit19 uses "left out
    # most of the examples".
    ("b1", "left"): ("verb", "حذف کرد (در leave out)"),
    # "run": EN_POS has unit39's "dogs need space to run"; b2 unit02 uses
    # "the reports did not run".
    ("b2", "run"): ("verb", "اجرا شدن"),
    # "account": EN_POS has unit27's bank account; b2 unit08 uses "which
    # account is better supported" (a version of events).
    ("b2", "account"): ("noun", "روایت؛ گزارش"),
}

# The 52 units this pass added. `_classify()` only synthesises the
# per-unit/per-lesson semantic tags below for these -- deliberately NOT for
# units 1-48/25-29, whose lexemes are already live and whose agreement_tags
# should not churn under an unrelated backfill run.
# Widened 2026-07-25 from the original a1_49-68/a2_30-34/B1/B2 scoping to
# EVERY unit: the polish wave measured that the untagged bands (a1_30-48
# especially) leave matching_pairs stuck on bare part_of_speech pools —
# fine at checkpoint scope, but course-wide off-theme at Endless-Practice
# scope, with no pack-side fix possible. Widening is purely ADDITIVE: no
# shipped pack references the new tag names, so no existing candidate pool
# changes, and the first-introduction-only rule (_unit_semantic_tags
# docstring) still keeps every generated tag checkpoint-safe. Built from
# the actual realization stems instead of numeric ranges so it can never
# drift from the file list.
AUTO_TAG_UNIT_STEMS = frozenset(
    "_".join(realization.stem.split("_")[:2])
    for realization, _overlay in (
        UNIT_FILES + UNIT_FILES_A2 + UNIT_FILES_B1 + UNIT_FILES_B2
    )
)

# Grammar metalanguage that the B1/B2 realizations introduce as real tokens
# (they appear inside those units' own grammar-explanation cards). They
# still become lexemes -- `_classify()` hard-fails on any unclassified token
# and the learner genuinely sees them -- but they are kept OUT of the
# generated semantic tags, so a practice pack can never build a vocabulary
# multiple_choice whose options are "فعل"/"اسم"/"جمله‌واره".
METALANGUAGE_TOKENS = frozenset({
    "clause", "commas", "command", "conditional", "continuous", "defining",
    "direct", "form", "forms", "hypothetical", "noun", "non-defining",
    "participle", "past", "perfect", "period", "phrase", "present",
    "relative", "reported", "semicolon", "sentence", "simple", "speech",
    "tense", "unreal", "verb",
})

# Parts of speech that may appear in a generated semantic tag. Function
# words and proper nouns are excluded: a `slot_gloss` multiple_choice over
# proper nouns self-glosses ("Simon" -> "Simon"), and a matching_pairs over
# particles/prepositions is not a vocabulary check.
TAGGABLE_POS = frozenset({"noun", "verb", "adjective", "adverb", "phrase"})


UNIT_SENSE_OVERRIDES: dict[tuple[str, str], tuple[str, str]] = {
    # a2_unit36 teaches the VERB ("Could you correct it?"); the shared table
    # resolves bare `correct` to the adjective ("درست"), which would emit a
    # wrong-sense vocab card here. Added 2026-08-05 (native-gloss backlog fix).
    ("a2_unit36_document_correction", "correct"): ("verb", "اصلاح کردن؛ تصحیح کردن"),
    # a2_unit35 (prescription): the shared/EXTRA tables carry the wrong sense
    # for these three in a pharmacy context. Added 2026-08-05 (native-gloss
    # review). tablet = pill (not the computer), matching the plural قرص‌ها;
    # hours = the dosing interval "every eight hours" (not office hours);
    # stop = cease "do not stop taking" (not physically halt/stand).
    ("a2_unit35_prescription", "tablet"): ("noun", "قرص"),
    ("a2_unit35_prescription", "hours"): ("noun", "ساعت"),
    ("a2_unit35_prescription", "stop"): ("verb", "قطع کردن؛ متوقف کردن"),
    # a2_unit38 (repair visit): "leave the key with my neighbor" = entrust,
    # not spend-time (وقت گذاشتن).
    ("a2_unit38_repair_visit", "leave"): ("verb", "گذاشتن؛ سپردن"),
    ("b1_unit01_necessity", "must"): ("verb", "باید"),
    ("b1_unit01_necessity", "next"): ("adjective", "بعدی"),
    ("b1_unit01_necessity", "right"): ("adjective", "درست"),
    ("b1_unit02_abilities", "would"): ("verb", "می‌شد/می‌بود"),
    ("b1_unit13_relative_clauses", "used"): ("verb", "عادت داشت (used to)"),
    ("b2_unit01_argumentation", "next"): ("adjective", "بعدی"),
    ("b2_unit03_hedging_emphasis", "would"): ("verb", "می‌شد/می‌بود"),
    ("b2_unit07_negotiation", "make"): ("verb", "باعث شدن"),
    # a1_unit35 (technology): "make a call" -- bare گرفتن collides with taking and call=تماس گرفتن.
    ("a1_unit35_technology", "make"): ("verb", "برقرار کردن (تماس)"),
    # a1_unit43 (colors): light green / too bright / a fun color -- split the overlapping روشن glosses.
    ("a1_unit43_colors", "light"): ("adjective", "کم‌رنگ؛ روشن"),
    ("a1_unit43_colors", "bright"): ("adjective", "پررنگ؛ درخشان"),
    ("a1_unit43_colors", "fun"): ("adjective", "شاد؛ سرگرم‌کننده"),
    # a1_unit44 (seasons): playing (noun, "loves playing soccer") collided with play; outdoors collided with out.
    ("a1_unit44_seasons", "playing"): ("noun", "بازی (فعالیت)"),
    ("a1_unit44_seasons", "outdoors"): ("adverb", "در فضای باز"),
    # a1_unit45 (emergencies): "caught fire" -- the gloss embedded English and shared گرفت with got/took.
    ("a1_unit45_emergencies", "caught"): ("verb", "آتش گرفت"),
    # a1_unit48 (library): borrow/borrowing shared one gloss; "checked out a cookbook" is not "examined";
    # other carried English ("on the other hand") in its gloss.
    ("a1_unit48_library", "borrow"): ("verb", "قرض گرفتن؛ امانت گرفتن"),
    ("a1_unit48_library", "borrowing"): ("noun", "امانت‌گیری"),
    ("a1_unit48_library", "checked"): ("verb", "امانت گرفت"),
    ("a1_unit48_library", "other"): ("adjective", "دیگر؛ سایر"),
}


def _lexeme_pos_and_gloss(
    level: str, unit_stem: str, token: str
) -> tuple[str, str]:
    """Resolve (part_of_speech, Farsi gloss) for one token at one level.

    Resolution order, most specific first: UNIT_SENSE_OVERRIDES ->
    LEVEL_SENSE_OVERRIDES -> this script's own FA_EN_EXTRA_LEXEMES -> the shared
    _en_target_lexeme_common.EN_POS plus this script's own
    EN_TARGET_TO_FA_GLOSS. The local table deliberately wins over the
    shared module for the tokens it owns: its glosses and semantic tags
    were authored against ITS part-of-speech choice, so a concurrent
    sibling lane adding the same token to EN_POS under a different POS must
    not silently repoint a Farsi gloss at a sense it was not written for.
    """
    override = UNIT_SENSE_OVERRIDES.get((unit_stem, token))
    if override is not None:
        return override
    override = LEVEL_SENSE_OVERRIDES.get((level, token))
    if override is not None:
        return override
    local = FA_EN_EXTRA_LEXEMES.get(token)
    if local is not None:
        return local
    if token not in EN_POS:
        raise ValueError(
            f"missing English classification for {token!r} -- add it to "
            f"FA_EN_EXTRA_LEXEMES in this file (or to EN_POS + "
            f"EN_TARGET_TO_FA_GLOSS if it belongs to the shared A1 corpus)"
        )
    if token not in EN_TARGET_TO_FA_GLOSS:
        raise ValueError(f"missing Farsi gloss for {token!r}")
    return EN_POS[token], EN_TARGET_TO_FA_GLOSS[token]


def _unit_semantic_tags(unit_stem, lesson_order, token, part_of_speech):
    """Unit- and lesson-scoped semantic tags for a newly-introduced token.

    THE load-bearing property (docs/content/PRACTICE_PACK_RECIPE.md, section
    1): `generate_checkpoint()` calls `_material()` with ONLY the unit's own
    lesson ids, so a practice slot is satisfiable at checkpoint scope only
    if its tag's members are lexemes THIS unit introduces. These tags are
    therefore emitted ONLY on a token's first introduction (see
    `_classify()`), never when a later unit re-uses it -- a tag that reached
    a re-used token would name a lexeme whose provenance lesson belongs to
    an earlier unit, which is exactly the silent `checkpoint_unavailable`
    cause the recipe calls defect #2.

    Two tags per token: one unit-wide (enough distinct members for a 6-slot
    matching_pairs) and one per lesson (so a pack can anchor at least one
    template on every lesson, which the checkpoint's lesson stratification
    needs).
    """
    if part_of_speech not in TAGGABLE_POS or token in METALANGUAGE_TOKENS:
        return []
    if part_of_speech == "phrase":
        return [
            f"fa_en_{unit_stem}_words",
            f"fa_en_{unit_stem}_lesson{lesson_order:02d}_words",
        ]
    # Tokens carrying digits, currency marks, clock colons or attached
    # punctuation are real lexemes but make poor slot candidates.
    if not all(character.isalpha() or character in "-'" for character in token):
        return []
    return [
        f"fa_en_{unit_stem}_words",
        f"fa_en_{unit_stem}_lesson{lesson_order:02d}_words",
    ]

def _classify(files, level, specs):
    for unit_order, (realization_path, overlay_path) in enumerate(files, 1):
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
        overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
        teaching_overlays = overlay["teaching"]
        # "a1_unit49_waste_disposal" -> "a1_unit49": the stable per-unit key
        # the generated semantic tags are named after (and the gate for
        # whether this unit gets them at all).
        stem = realization_path.stem
        unit_stem = "_".join(stem.split("_")[:2])
        auto_tag = unit_stem in AUTO_TAG_UNIT_STEMS
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson["teaching"]:
                content_key = item["content_key"]
                for raw_token in item.get("introduced_tokens", []):
                    raw_key = raw_token.casefold().replace("’", "'")
                    token_key = normalize_en_token(raw_token)
                    lookup_key = raw_key if (
                        raw_key in EN_POS or raw_key in FA_EN_EXTRA_LEXEMES
                    ) else token_key
                    part_of_speech, gloss = _lexeme_pos_and_gloss(
                        level, stem, lookup_key
                    )
                    token = en_token_display(raw_token, part_of_speech)
                    gloss = strip_en_sentence_punctuation(gloss)
                    tags = en_agreement_tags(token_key)
                    # Keyed by (level, token) -- A1/A2/B1/B2 are separate
                    # courses (separate Lexeme rows are fine/expected even
                    # for a token spelled the same in more than one), so a
                    # bare token key would wrongly merge/skip a B1
                    # occurrence into an A1 spec already seen.
                    key = (level, token)
                    existing = specs.get(key)
                    if existing is None:
                        if auto_tag:
                            # ONLY on first introduction -- see
                            # _unit_semantic_tags()'s docstring for why a
                            # re-used token must never receive a later
                            # unit's tag.
                            unit_tags = _unit_semantic_tags(
                                unit_stem, lesson_order, token, part_of_speech
                            )
                            if unit_tags:
                                semantic = tags.setdefault("semantic", [])
                                semantic.extend(
                                    tag for tag in unit_tags if tag not in semantic
                                )
                        specs[key] = {
                            "level": level,
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "en",
                            "part_of_speech": part_of_speech,
                            "english_gloss": gloss,
                            "agreement_tags": tags,
                        }
                    else:
                        for tag_key, value in tags.items():
                            if tag_key == "semantic":
                                prior = existing["agreement_tags"].setdefault(tag_key, [])
                                prior.extend(v for v in value if v not in prior)
                            else:
                                existing["agreement_tags"].setdefault(tag_key, value)
            for content_key, token, gloss in iter_taught_phrase_lexemes(
                stem, lesson, teaching_overlays
            ):
                key = (level, token)
                if key in specs:
                    continue
                semantic = _unit_semantic_tags(
                    unit_stem, lesson_order, token, "phrase"
                )
                specs[key] = {
                    "level": level,
                    "unit_order": unit_order,
                    "lesson_order": lesson_order,
                    "lesson_content_key": lesson_key,
                    "content_key": content_key,
                    "token": token,
                    "language_code": "en",
                    "part_of_speech": "phrase",
                    "english_gloss": gloss,
                    "agreement_tags": {"semantic": semantic} if semantic else {},
                }


# Column widths on backend/app/models/entities.py::Lexeme. There is no
# validator for these anywhere yet, and an over-length value 500s the whole
# import rather than failing one row, so iter_specs() asserts them itself.
_COLUMN_LIMITS = {
    "token": 255,
    "part_of_speech": 40,
    "english_gloss": 255,
    "lesson_content_key": 255,
    "content_key": 255,
}


def iter_specs():
    specs: dict[tuple[str, str], dict] = {}
    _classify(UNIT_FILES, "a1", specs)
    _classify(UNIT_FILES_A2, "a2", specs)
    _classify(UNIT_FILES_B1, "b1", specs)
    _classify(UNIT_FILES_B2, "b2", specs)
    for spec in specs.values():
        for field, limit in _COLUMN_LIMITS.items():
            if len(spec[field]) > limit:
                raise ValueError(
                    f"{field} {spec[field]!r} is {len(spec[field])} chars, "
                    f"over the Lexeme.{field} String({limit}) limit"
                )
    yield from specs.values()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    specs = list(iter_specs())
    if args.dry_run:
        print(f"Lexeme backfill dry run: {len(specs)} en.")
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        courses_by_level = {}
        for level, title in (
            ("a1", "انگلیسی A1"),
            ("a2", "انگلیسی A2"),
            ("b1", "انگلیسی B1"),
            ("b2", "انگلیسی B2"),
        ):
            needed = any(spec["level"] == level for spec in specs)
            course = db.scalar(
                select(Course).where(
                    Course.source_language == "fa",
                    Course.target_language == "en",
                    Course.title == title,
                )
            )
            if course is None:
                if needed:
                    print(f"ERROR: fa-en {title!r} course must be imported first", file=sys.stderr)
                    return 1
                continue
            courses_by_level[level] = course

        lessons_by_level = {
            level: {
                (unit.order, lesson.order): lesson
                for unit in db.scalars(select(Unit).where(Unit.course_id == course.id))
                for lesson in db.scalars(select(Lesson).where(Lesson.unit_id == unit.id))
            }
            for level, course in courses_by_level.items()
        }
        created = 0
        updated = 0
        for spec in specs:
            level = spec.pop("level")
            course = courses_by_level[level]
            lesson = lessons_by_level[level].get(
                (spec.pop("unit_order"), spec.pop("lesson_order"))
            )
            if lesson is None:
                print(f"ERROR: imported course is missing {spec['lesson_content_key']}", file=sys.stderr)
                db.rollback()
                return 1
            existing = db.scalar(
                select(Lexeme).where(
                    Lexeme.course_id == course.id,
                    Lexeme.language_code == spec["language_code"],
                    Lexeme.token == spec["token"],
                    Lexeme.part_of_speech == spec["part_of_speech"],
                )
            )
            if existing:
                existing.english_gloss = spec["english_gloss"]
                existing.agreement_tags = spec["agreement_tags"]
                updated += 1
                continue
            db.add(
                Lexeme(
                    course_id=course.id,
                    provenance_lesson_id=lesson.id,
                    provenance_lesson_content_key=spec.pop("lesson_content_key"),
                    provenance_content_key=spec.pop("content_key"),
                    **spec,
                )
            )
            created += 1
        db.commit()
    print(f"Lexeme backfill complete: {created} created, {updated} updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
