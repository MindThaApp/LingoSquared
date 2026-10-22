#!/usr/bin/env python3
"""Idempotently backfill prs-en lexemes (English target) from the shared en
realization, across all four prs-en course rows (A1/A2/B1/B2).

Scope as of 2026-07-22: A1 units 01-24 + 30-68, A2 units 25-34, B1 units
01-19, B2 units 01-08 -- i.e. every unit in scripts/content_manifest.txt's
four `prs-en*` lines. The 52 units a1 49-68 / a2 30-34 / b1 01-19 / b2 01-08
were added on 2026-07-22 to unblock unit checkpoints: `generate_checkpoint()`
needs BOTH practice templates AND lexemes and hard-fails below 12 items, so
those 52 units could not produce the checkpoint the publish gate requires.

REGISTER (2026-07-22): every Dari gloss in this file is colloquial Dari per
this lane's register pin in docs/content/CLAUDE.md, and was audited against
scripts/check_dari_register.py's marker inventory. That checker deliberately
scopes .py files out (see its "NOT COVERED" section, which names this file),
so the audit was run by importing its DIALECT_MARKERS/AUDIT_MARKERS/
FORMAL_3SG/IRANIAN_COPULA/METALANGUAGE tables and applying them to
EN_TARGET_TO_PRS_GLOSS's values directly. 21 pre-existing Iranian-Persian
glosses were repaired in that pass (آموزگار->معلم, بیایید->بیایین,
هستی->استی, formal است->استه x15, می‌شود->می‌شه x2, می‌کند->می‌کنه) --
these were the SRS-surface twin of registry class 1.28, and would have kept
showing Farsi-register words even after the overlays were repaired.

Written directly (not via Codex -- Codex was rate-limited at authoring
time) mirroring scripts/backfill_lexemes.py's structure and rigor.
Target-side English POS/semantic-tag classification is shared with
backfill_lexemes_nl_en.py/backfill_lexemes_fa_en.py via
scripts/_en_target_lexeme_common.py; the Dari gloss for each token is
this script's own -- and is NOT a find-replace of the fa-en script's
Farsi glosses. Verified against the actual prs-en overlay text
(docs/content/overlays/prs-en/a1_unit01.yaml, a1_unit02.yaml), which
uses genuinely distinct Dari vocabulary for several core content words
(student, teacher, engineer, and yes/no all use different words than
the fa-en script's Farsi equivalents -- see the dict below), plus the
Afghan verb-ending forms throughout. Per docs/content/AUTHORING_GUIDE.md
and this project's own established finding, Dari and Farsi share a
script but are not interchangeable content.

Deliberately scoped to TARGET-side (English) lexemes only, matching
backfill_lexemes_fa_en.py's scope cut (verified: no slot_preset in the
existing en-fa pilot pack ever uses a source-language slot).

Run via docker compose from backend/, mounting the full repo:
    cd backend
    docker compose run --rm \
      -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_prs_en.py
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
    EN_TOKEN_BOUNDARY_PUNCTUATION,
    EN_POS,
    en_token_display,
    en_agreement_tags,
    iter_taught_phrase_lexemes,
    normalize_en_token,
)

UNIT_FILES = (
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit01_greetings.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit02_introductions.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit03_numbers.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit04_dates.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit05_time.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit06_family.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit07_food.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit08_shopping.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit08.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit09_places.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit10_directions.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit10.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit11_weather.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit11.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit12_clothing.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit13_emotions.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit14_communication.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit14.yaml",
    ),
    # Units 15-20 (money/routines/plans/past events/preferences/
    # comparisons), added 2026-07-06 by this lane's own worker (a
    # separate concurrent worker owns units 21-26 -- appended
    # independently, not touched here).
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit15_money.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit15.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit16_routines.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit16.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit17_plans.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit17.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit18_past_events.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit18.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit19_preferences.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit19.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit20_comparisons.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit20.yaml",
    ),
    # Units 21-24 (A1: travel, health, work, housing) + 25-26 (A2:
    # bureaucracy, opinions), added 2026-07-06 by this lane's own worker
    # (a separate concurrent worker owns units 9-14, another owns 15-20
    # -- appended independently, not touched here), completing prs-en's
    # coverage of all 24 A1 + first 2 A2 spine outcomes for the shared
    # English realization, matching nl-en/fa-en's already-full 26-unit
    # coverage. EN_POS/en_agreement_tags for all six units' vocabulary
    # (including travel_noun, symptom_noun, occupation_noun/occupation_a,
    # room_noun, bureaucracy_noun, dogpark_noun) were already present in
    # _en_target_lexeme_common.py before this change (added earlier this
    # session alongside nl-en's own unit21-26 work) -- verified with a
    # standalone script diffing every introduced_token across these six
    # realization files against EN_POS's keys: zero missing. Only this
    # script's own Dari gloss dict needed extending (107 new tokens),
    # cross-checked against the actual prs-en overlay text for these
    # units, same division of labor as every other unit added here. One
    # deliberate homograph avoidance carried over from the shared
    # module's own documented limitation: "close" already has a gloss/
    # POS entry from unit05 (the store-hours "بند کردن"/verb sense);
    # unit26 reintroduces "close" as an adjective (proximity: "very
    # close to the playground"), but no new entry was added here and no
    # practice template in this pass uses "close" as a fillable slot for
    # that sense -- consistent with the shared module's own instruction
    # not to force a second, conflicting entry onto an existing bare-
    # token classification.
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit21_travel.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit21.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit22_health.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit22.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit23_work.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit23.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit24_housing.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit24.yaml",
    ),
    # Units 30-42 (hobbies through personality), added 2026-07-11 by the
    # prs-en depth-extension worker (a fresh-context worker extending
    # Endless Practice coverage from unit29 to unit42, per a depth audit
    # finding prs-en had only ~7.2hrs vs the >=10hr publish bar, with
    # existing practice packs stopping at unit29). Appended in the SAME
    # order these units are imported in scripts/content_manifest.txt's
    # prs-en line (...a1_unit24...a1_unit30...a1_unit42...) -- units
    # 25-29 are NOT in this tuple (they belong to the separate "انگلیسی
    # A2" course, UNIT_FILES_A2 below), so position 25 in THIS tuple
    # correctly corresponds to the real "انگلیسی A1" course's unit_order
    # 25, i.e. a1_unit30 (the A1 course's units are 1-24 then 30-58,
    # contiguous by import order, not by the on-disk unit NUMBER).
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit30_hobbies.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit30.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit31_appearance.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit31.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit32_animals.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit32.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit33_transportation.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit33.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit34_sports.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit34.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit35_technology.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit35.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit36_education.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit36.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit37_celebrations.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit37.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit38_household.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit38.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit39_neighborhood.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit39.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit40_post.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit40.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit41_cooking.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit41.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit42_personality.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit42.yaml",
    ),
    # Units 43-48 (colors / seasons / emergencies / lost items /
    # appointments / library), added 2026-07-12 for the Endless Practice
    # coverage-extension batch. Kept in the A1 tuple because these files
    # import into the same "انگلیسی A1" course row as units 30-42.
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit43_colors.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit43.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit44_seasons.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit44.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit45_emergencies.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit45.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit46_lost_items.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit46.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit47_appointments.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit47.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit48_library.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit48.yaml",
    ),
    # Units 49-68 (waste disposal ... borrowing/lending), added 2026-07-22 by
    # the checkpoint-coverage pass. WHY: `generate_checkpoint()`
    # (backend/app/practice/service.py) hard-fails below 12 items and needs
    # BOTH practice templates AND lexemes -- prs-en had ZERO lexemes for 52
    # units (a1 49-68, a2 30-34, b1 01-19, b2 01-08), so none of them could
    # generate the unit checkpoint that the publish gate requires. Appended in
    # the SAME order as scripts/content_manifest.txt's `prs-en` line
    # (...a1_unit48 a1_unit49 ... a1_unit68), so this tuple's positional index
    # keeps matching the imported course's unit_order (the A1 course's units
    # are 1-24 then 30-68, contiguous by IMPORT order, not by on-disk number).
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit49_waste_disposal.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit49.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit50_accommodation.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit50.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit51_pharmacy.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit51.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit52_personal_care.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit52.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit53_bike_rental.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit53.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit54_laundry.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit54.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit55_swimming_pool.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit55.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit56_restaurant.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit56.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit57_cinema.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit57.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit58_museum.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit58.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit59_banking_basics.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit59.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit60_invitations.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit60.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit61_apologies_excuses.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit61.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit62_phone_calls.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit62.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit63_asking_for_help.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit63.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit64_compliments.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit64.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit65_returns_exchanges.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit65.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit66_pharmacy_symptoms.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit66.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit67_family_news.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit67.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit68_borrowing_lending.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a1_unit68.yaml",
    ),
)

# A2 units live in a SEPARATE course row ("انگلیسی A2", not "انگلیسی
# A1") -- `POST /admin/content/import` matches/creates courses by
# (source_language, target_language, title), and the A2 overlay
# declares `course.title: انگلیسی A2`, distinct from A1's `انگلیسی A1`.
# Real bug found live 2026-07-06/07 (Dari Endless Practice QA pass,
# same root cause independently confirmed in the sibling
# backfill_lexemes_en_prs.py): this used to be a single UNIT_FILES
# tuple with a2 units 25-26 appended at continuous positions 25/26,
# backfilled against ONE lookup of the "انگلیسی A1" course (24 units).
# Position 25/26 don't exist in that course, so `main()` hard-failed
# with "imported course is missing en.a2.unit25...." on every run --
# A2 lexemes for this direction have never actually been backfillable
# against a real database. Kept as its own tuple with LOCAL 1-based
# ordering (looked up against the "انگلیسی A2" course separately in
# main(), never mixed with UNIT_FILES' indices).
UNIT_FILES_A2 = (
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit25_bureaucracy.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit25.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit26_opinions.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit26.yaml",
    ),
    # Unit 27 (A2: opening a bank account), added 2026-07-07 (practice-
    # pool-sync lane extending prs-en to this new unit, in parallel with the
    # equivalent fa-en pass). EN_POS/en_agreement_tags for this unit's
    # vocabulary (including the new banking_noun/banking_adjective
    # semantic tags) were already present in _en_target_lexeme_common.py
    # before this change (added earlier this session alongside nl-en's own
    # unit27 course-routing fix) -- verified every introduced_token across
    # this realization file against EN_POS's keys: zero missing. Only this
    # script's own Dari gloss dict needed extending (18 new tokens, cross-
    # checked against docs/content/overlays/prs-en/a2_unit27.yaml's own
    # real text, not a find-replace of the fa-en script's Farsi).
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit27_banking.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit27.yaml",
    ),
    # Unit 28 (A2: attending a doctor's appointment), added 2026-07-07
    # (practice-pool-sync lane extending prs-en to this new unit, in
    # parallel with the equivalent fa-en pass; nl-en's own unit28 pass is
    # a separate concurrent worker, not touched here). EN_POS/
    # en_agreement_tags for this unit's vocabulary (including the new
    # health_followup_noun/condition_adjective semantic tags) were
    # already present in _en_target_lexeme_common.py before this change
    # (added by the concurrent nl-en lane's own unit28 pass) -- verified
    # every introduced_token across this realization file against
    # EN_POS's keys: zero missing. Only this script's own Dari gloss
    # dict needed extending (16 new tokens, cross-checked against
    # docs/content/overlays/prs-en/a2_unit28.yaml's own real text, not a
    # find-replace of the fa-en script's Farsi).
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit28_doctor.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit28.yaml",
    ),
    # Unit 29 (A2: reporting a maintenance problem), added 2026-07-07 --
    # closing the practice-pool gap for the newest A2 unit (units 25-28
    # already had fa-en/nl-en/prs-en packs; unit29 had none). EN_POS/
    # en_agreement_tags for this unit's vocabulary (including the new
    # 3-member maintenance_noun tag [sink, plumber, repair]) were added to
    # _en_target_lexeme_common.py as part of this same pass -- verified
    # every introduced_token across this realization file against EN_POS's
    # keys: zero missing. Only this script's own Dari gloss dict needed
    # extending (18 new tokens, cross-checked against docs/content/
    # overlays/prs-en/a2_unit29.yaml's own real text, not a find-replace of
    # the fa-en script's Farsi).
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit29_maintenance.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit29.yaml",
    ),
    # Units 30-34 (job interview / travel disruption / online habits / weekly
    # schedule / shopping complaint), added 2026-07-22 by the same
    # checkpoint-coverage pass as a1 units 49-68 above. Order matches
    # scripts/content_manifest.txt's `prs-en-a2` line exactly.
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit30_job_interview.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit30.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit31_travel_disruption.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit31.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit32_online_habits.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit32.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit33_weekly_schedule.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit33.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit34_shopping_complaint.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit34.yaml",
    ),
    # Added 2026-08-05 (fa/prs native-gloss backlog): units 35-40 unblock the
    # last 6 prs-en A2 checkpoints. English POS ported from the already-shipped
    # nl-en EN_EXTRA (commit 304c029e); Dari glosses below are DRAFTS pending
    # Ramin's native audit.
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit35_prescription.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit35.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit36_document_correction.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit36.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit37_video_calls.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit37.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit38_repair_visit.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit38.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit39_after_the_interview.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit39.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit40_online_order_problem.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/a2_unit40.yaml",
    ),
)

# B1 and B2 each live in their OWN course row again ("انگلیسی B1" /
# "انگلیسی B2" -- the overlays declare those titles, and
# `POST /admin/content/import` matches/creates courses by
# (source_language, target_language, title)). Same LOCAL 1-based ordering
# discipline as UNIT_FILES_A2: these indices are looked up against their own
# course in main(), never mixed with another tuple's. Order matches
# scripts/content_manifest.txt's `prs-en-b1` / `prs-en-b2` lines.
UNIT_FILES_B1 = (
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit01_necessity.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit02_abilities.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit03_hypotheticals.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit04_debate.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit05_workplace.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit06_narrative.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit07_conditions.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit08_sequencing.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit08.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit09_reported_speech.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit10_purpose.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit10.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit11_unreal_hypotheticals.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit11.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit12_concession.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit13_relative_clauses.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit14_professional_communication.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit14.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit15_complaints.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit15.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit16_advice.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit16.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit17_regret.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit17.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit18_future_plans.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit18.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b1_unit19_summarizing.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b1_unit19.yaml",
    ),
)

UNIT_FILES_B2 = (
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit01_argumentation.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b2_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit02_speculation.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b2_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit03_hedging_emphasis.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b2_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit04_narrative_time.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b2_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit05_register.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b2_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit06_abstraction.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b2_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit07_negotiation.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b2_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/b2_unit08_synthesis.yaml",
        REPO_ROOT / "docs/content/overlays/prs-en/b2_unit08.yaml",
    ),
)

# Dari gloss for each shared English target token -- hand-written for
# this course specifically, cross-checked against the prs-en overlay's
# own real Dari phrasing (not derived from the fa-en script's Farsi
# glosses). Persian-range codepoints throughout (Persian keheh/yeh, not
# the Arabic-range look-alikes), described in prose only above, never
# pasted as literal forbidden characters.
EN_TARGET_TO_PRS_GLOSS: dict[str, str] = {
    "hello": "سلام", "hi": "سلام (خودمانی)", "good": "خوب", "morning": "صبح",
    "afternoon": "بعد از چاشت", "evening": "شام", "goodbye": "خداحافظ",
    "bye": "خداحافظ (خودمانی)", "how": "چطور", "are": "استین",
    "you": "شما", "i'm": "من استم", "fine": "خوب", "thanks": "تشکر",
    "not": "نی", "bad": "بد", "and": "و", "okay": "خوب",
    "nice": "خوش", "to": "به", "meet": "آشنا شدن", "too": "هم",
    "see": "دیدن", "later": "بعداً", "have": "داشتن", "a": "(حرف تعریف نامعین)",
    "day": "روز", "what": "چه", "is": "استه", "what's": "چیست",
    # "your"/"my" were previously glossed as bare Dari possessive SUFFIX
    # morphemes ("تان"/"م" -- how Dari actually attaches possession to
    # the noun, e.g. نظرم "opinion-my"), not standalone words. Real bug
    # found live 2026-07-06/07 (Dari Endless Practice QA pass): the
    # word_order generator substitutes this gloss into an English hint
    # frame as if it were a free-standing word (e.g. practice pack
    # prs-en/a2_unit26.yaml's `possessive_order` template, frame "In
    # {item} opinion, ..."), which rendered as the genuinely confusing
    # "In *م* opinion, the dog park is a good idea" -- a bound suffix
    # floating alone mid-English-sentence with no word it's attached to.
    # Fixed to match this same dict's own established, correct pattern
    # for the identical grammatical category ("his": "مالِ او (مذکر)",
    # "her": "مالِ او (مؤنث)" a few lines below) -- a natural standalone
    # explanatory phrase, not the bound suffix.
    "your": "مالِ شما", "name": "نام", "my": "مالِ من", "leila": "لیلا",
    "i": "من", "am": "استم", "student": "محصل", "teacher": "معلم",
    "yes": "بلی", "no": "نخیر", "new": "جدید", "member": "عضو",
    "he": "او (مذکر)", "she": "او (مؤنث)", "an": "(حرف تعریف نامعین)",
    "engineer": "انجنیر", "library": "کتابخانه", "assistant": "دستیار",
    "daniel": "دنیل", "work": "کار کردن", "at": "در", "the": "(حرف تعریف معین)",
    "welcome": "خوشامد", "thank": "تشکر کردن",
    # Unit 3 (numbers/ages/prices/phones/market), added 2026-07-06. Some
    # real Dari-specific vocabulary here vs the fa-en script's Farsi
    # (dollars/phone/number use the Afghan Dari borrowings دالر/تیلفون/
    # نمبر, not Farsi's دلار/تلفن/شماره).
    "zero": "صفر", "one": "یک", "two": "دو", "three": "سه", "four": "چهار",
    "five": "پنج", "six": "شش", "seven": "هفت", "eight": "هشت",
    "nine": "نه (عدد)", "ten": "ده", "eleven": "یازده", "twelve": "دوازده",
    "thirteen": "سیزده", "fifteen": "پانزده", "twenty": "بیست",
    "twenty-one": "بیست و یک", "thirty": "سی", "forty": "چهل",
    "fifty": "پنجاه", "hundred": "صد", "twenty-five": "بیست و پنج",
    "old": "سال قدمت‌داشتن (در بیان سن)", "years": "سال (جمع)",
    "it's": "این ... استه (مخفف)", "dollars": "دالر (جمع)",
    "phone": "تیلفون", "number": "نمبر", "market": "بازار",
    "apples": "سیب‌ها", "they're": "دوی ... استند (مخفف)",
    "ok": "خیر استه؛ باشه", "this": "این", "shop": "دکان",
    "much": "چقدر",
    # Unit 4 (days/months/calendar dates), added 2026-07-06. POS/tags
    # already shared from _en_target_lexeme_common.py (nl-en's own unit04
    # work) -- only these Dari glosses were needed. Month names use the
    # English-derived borrowings common in Afghan Dari (جنوری/مارچ/جولای/
    # سپتمبر/دسمبر), genuinely distinct from Farsi's French-derived forms
    # (ژانویه/مارس/ژوئیه/سپتامبر/دسامبر) -- not a copy of the fa-en dict.
    "monday": "دوشنبه", "tuesday": "سه‌شنبه", "wednesday": "چهارشنبه",
    "thursday": "پنجشنبه", "friday": "جمعه", "saturday": "شنبه",
    "sunday": "یکشنبه", "it": "آن", "today": "امروز", "january": "جنوری",
    "march": "مارچ", "july": "جولای", "september": "سپتمبر",
    "december": "دسمبر", "which": "کدام", "month": "ماه",
    "today's": "امروزِ ... (مالکیت)", "date": "تاریخ", "7th": "هفتم",
    "can": "می‌تانم؛ می‌تانه (تانستن، فعل کمکی دری)", "also": "هم",
    "write": "نوشتن", "as": "به حیث", "when's": "کی استه (مخفف)",
    "birthday": "سالگره", "3rd": "سوم", "opens": "باز می‌شه", "again": "دوباره",
    "open": "باز", "on": "در؛ روی", "9th": "نهم", "great": "خوب استه",
    "then": "بعد",
    # Unit 5 (telling the time), added 2026-07-06.
    "time": "وخت", "o'clock": "بجه (ساعتِ تمام)", "half": "نیم",
    "past": "گذشته", "quarter": "ربع", "night": "شب",
    "store": "دکان", "in": "در", "closes": "بند می‌شه",
    "does": "(فعل کمکی پرسشی)", "close": "بند کردن",
    # Unit 6 (family members and relationships), added 2026-07-06.
    "mother": "مادر", "father": "پدر", "brother": "برادر", "sister": "خواهر",
    "parents": "والدین", "siblings": "خواهر و برادرها",
    "grandmother": "بی‌بی", "grandfather": "بابه", "aunt": "عمه؛ خاله",
    "uncle": "کاکا؛ ماما", "cousin": "پسرکاکا؛ دخترکاکا (و مشابه)",
    "his": "مالِ او (مذکر)", "her": "مالِ او (مؤنث)",
    "she's": "او ... استه (مخفف)", "brothers": "برادران",
    "do": "(فعل کمکی پرسشی)", "any": "هیچ", "don't": "(منفیِ فعل کمکی، زمان حال)",
    "only": "فقط", "child": "بچه", "photo": "عکس", "family": "فامیل",
    "who": "کیا", "just": "فقط؛ همینحالا",
    # Unit 7 (food, drink, and ordering), added 2026-07-06.
    "coffee": "قهوه", "tea": "چای", "water": "آب", "bread": "نان",
    "soup": "شوروا", "salad": "سالاد", "sandwich": "ساندویچ",
    "i'd": "من می‌خواهم (مخفف)", "like": "خواستن؛ خوش داشتن",
    "please": "لطفاً", "anything": "چیزی", "else": "دیگه",
    "that's": "دا ... استه (مخفف)", "all": "بس", "for": "به خاطر",
    "here": "اینجا", "or": "یا", "go": "رفتن؛ بردن (بیرون‌بر)",
    "menu": "مینو", "price": "قیمت", "cafe": "کیفی", "3": "سه",
    "2": "دو", "5": "پنج", "6": "شش", "sure": "البته",
    # Unit 8 (shopping: prices and quantities), added 2026-07-06.
    "pound": "پوند (واحد وزن)", "of": "ازِ/متعلق به", "dozen": "درجن",
    "eggs": "تخم‌ها", "bottle": "بوتل", "bag": "کیسه", "rice": "برنج",
    "kilo": "کیلو", "tomatoes": "بادنجان رومی‌ها", "pounds": "پوندها",
    "fresh": "تازه", "per": "هر",
    "4": "چهار",
    # Unit 9 (common places and locations), added 2026-07-06. Glosses
    # cross-checked against the prs-en overlay's own real Dari phrasing
    # (docs/content/overlays/prs-en/a1_unit09.yaml), e.g. hospital=
    # شفاخانه and pharmacy=دواخانه (both genuinely distinct Dari lexemes
    # from Farsi's بیمارستان/داروخانه).
    "bank": "بانک", "hospital": "شفاخانه", "pharmacy": "دواخانه",
    "park": "پارک", "restaurant": "رستورانت", "next": "پهلوی",
    "across": "مقابل", "from": "از مبدأ",
    "between": "بین", "behind": "عقب", "front": "پیشروی",
    "where": "کجا", "far": "دور", "excuse": "ببخشین",
    "me": "مره (من را)",
    # Unit 10 (asking for and following directions), added 2026-07-06.
    "turn": "پیچیدن", "left": "چپ", "right": "راست", "straight": "مستقیم",
    "stop": "توقف کردن", "corner": "کنج سرک؛ چوک", "get": "رسیدن",
    "minutes": "دقیقه‌ها", "can't": "نمی‌تانم؛ نمی‌تانه (نی‌تانستن)",
    "miss": "گم کردن", "take": "گرفتن",
    "first": "اول", "street": "سرک", "second": "دوم",
    "directions": "مسیر؛ آدرس‌دهی",
    # Unit 11 (talking about the weather), added 2026-07-06. Overlay
    # renders both "hot" and "warm" as گرم -- kept as the overlay's own
    # literal Dari (not a script error), since Dari doesn't lexically
    # split hot/warm the way English does in this register.
    "sunny": "آفتابی", "rainy": "بارانی", "cloudy": "ابری", "cold": "سرد",
    "hot": "گرم", "windy": "بادی", "weather": "هوا", "warm": "گرم",
    "raining": "باران باریدن", "should": "باید", "umbrella": "چتر",
    "tomorrow": "فردا", "will": "(نشانهٔ فعل آینده)", "be": "بودن",
    "rain": "باران", "saturday": "شنبه", "let's": "بیایین (پیشنهاد مشترک)",
    "idea": "فکر؛ نظر", "but": "اما", "going": "می‌خواهد (آیندهٔ نزدیک)",
    "so": "پس",
    # Unit 12 (clothing: sizes and colors), added 2026-07-06.
    "shirt": "شرت؛ پیراهن", "pants": "پطلون", "shoes": "بوت",
    "jacket": "جاکت", "dress": "لباس زنانهٔ یک‌تکه", "small": "خورد",
    # Real mistranslation fix, found live 2026-07-06/07 (Dari Endless
    # Practice QA pass): "medium" was glossed "منجم؛ متوسط" -- منجم means
    # "astronomer" in Dari, unrelated to clothing size, apparently a
    # copy/mixup with متوسط ("medium/average"), the actually-correct word
    # already present after the semicolon. Fixed to drop the wrong term.
    "medium": "متوسط", "large": "کلان", "blue": "آبی", "black": "سیاه",
    "size": "سایز", "color": "رنگ", "20": "بیست",
    "i'll": "من ... خواهم (مخفف)", "we": "ما",
    # Unit 13 (talking about feelings), added 2026-07-06.
    "happy": "خوش", "sad": "خفه؛ غمگین", "tired": "خسته",
    "excited": "شوق‌مند؛ هیجان‌زده", "worried": "خفه؛ پریشان",
    "feeling": "احساس", "little": "کمی", "because": "چون",
    "big": "مهم؛ کلان", "test": "امتحان", "class": "صنف",
    "almost": "تقریباً", "over": "ختم شدن", "year": "سال",
    "last": "آخرین", "writer": "نویسنده", "oh": "آه", "understand": "فهمیدن",
    # Unit 14 (phone calls and messages), added 2026-07-06.
    "free": "وقت‌دار؛ آزاد", "tonight": "امشب", "sorry": "ببخشین",
    "repeat": "تکرار کردن", "that": "آن؛ دا", "speak": "گپ زدن",
    "more": "بیشتر", "slowly": "آهسته", "hear": "شنیدن",
    "well": "خوب", "6pm": "ساعت شش شام",
    "message": "پیام", "suggest": "پیشنهاد کردن", "meeting": "دیدار؛ ملاقات",
    "place": "جای", "about": "دربارهٔ",
    # Unit 15 (handling money and payments), added 2026-07-06. Glosses
    # cross-checked against docs/content/overlays/prs-en/a1_unit15.yaml's
    # own real Dari phrasing (cash=پیسهٔ نقد، credit card=کارت اعتباری،
    # debit card=کارت بانکی -- genuinely distinct Afghan Dari usage, not
    # a copy of the fa-en script's Farsi).
    "cash": "پیسهٔ نقد", "card": "کارت", "credit": "اعتباری",
    "debit": "بانکی؛ مستقیم", "total": "جمع کل",
    "cards": "کارت‌ها", "pay": "پرداخت کردن", "tax": "مالیه",
    "10": "ده", "by": "با", "1": "یک",
    # Unit 16 (describing a daily routine), added 2026-07-06. Overlay
    # renders "wake up"/"get dressed"/"go to bed" as multi-word Dari
    # phrases (بیدار شدن/کالا پوشیدن/به بستر رفتن) -- each single-token
    # gloss below reflects only that token's own contribution.
    "wake": "بیدار شدن", "up": "(جزء فعل دوبخشی)",
    "dressed": "کالا پوشیدن", "dinner": "شب چاشت",
    "bed": "بستر", "every": "هر", "usually": "معمولاً",
    "breakfast": "صبح‌چاشت", "after": "بعد از",
    # Unit 17 (making simple plans), added 2026-07-06.
    "want": "خواستن", "movie": "فلم",
    "weekend": "آخر هفته", "would": "میل داشتن",
    "walk": "قدم زدن", "love": "خیلی خوش شدن",
    "busy": "مصروف", "maybe": "شاید", "another": "دیگه",
    "lunch": "چاشت", "1pm": "ساعت یک بعد از چاشت",
    "works": "مناسب/خوب بودن",
    # Unit 18 (describing a recent event), added 2026-07-06.
    "went": "رفت (زمان گذشته)", "saw": "دید (زمان گذشته)",
    "ate": "خورد (زمان گذشته)",
    "visited": "به دیدن رفت (زمان گذشته)",
    "worked": "کار کرد (زمان گذشته)",
    "did": "(فعل کمکی پرسشی، زمان گذشته)",
    "yesterday": "دیروز", "together": "با هم",
    "watched": "تماشا کرد (زمان گذشته)",
    "writer's": "مالِ نویسنده", "s": "(علامت مالکیت)",
    "was": "بود (زمان گذشته)", "week": "هفته",
    # Unit 19 (expressing likes and preferences), added 2026-07-06. "hate"
    # confirmed against the overlay's own corrected Dari (نفرت داشتن، not
    # a Farsi-style بدبین بودن).
    "prefer": "ترجیح دادن", "hate": "نفرت داشتن", "milder": "ملایم‌تر",
    "very": "خیلی", "strong": "تُند",
    "why": "چرا", "think": "فکر کردن",
    "prefers": "ترجیح می‌ته (سوم شخص مفرد)",
    "thinks": "فکر می‌کنه (سوم شخص مفرد)",
    # Unit 20 (making basic comparisons), added 2026-07-06.
    "bigger": "کلان‌تر", "smaller": "خُرد‌تر", "cheaper": "ارزان‌تر",
    "expensive": "قیمت؛ گران", "faster": "تیزتر",
    "than": "از (در مقایسه)", "nicer": "قشنگ‌تر",
    "cheapest": "ارزان‌ترین", "red": "سرخ", "car": "موتر", "white": "سفید",
    # Units 21-24 (A1: travel, health, work, housing) + 25-26 (A2:
    # bureaucracy, opinions), added 2026-07-06. Atomic per-token
    # glosses -- cross-checked against, but not copy-pasted from, each
    # unit's own (phrase-level) Dari overlay glosses
    # (docs/content/overlays/prs-en/a1_unit21.yaml through a2_unit26.yaml).
    "ticket": "تکت", "platform": "سکو", "train": "ریل",
    "departure": "حرکت", "arrival": "رسیدن", "boston": "بوستون",
    "way": "طرف",
    "round": "دوطرفه", "trip": "سفر",
    "leaves": "حرکت می‌کنه (فعل، سوم‌شخص مفرد)", "9:15": "۹:۱۵",
    "arrives": "می‌رسه (فعل، سوم‌شخص مفرد)", "11:30": "۱۱:۳۰",
    "arrive": "رسیدن (فعل)",
    "headache": "سردردی", "stomachache": "معده‌درد", "fever": "تب",
    "cough": "سرفه", "sore": "دردناک",
    "throat": "گلو", "wrong": "تکلیف",
    "feel": "احساس کردن", "rest": "استراحت کردن",
    "need": "ضرورت داشتن", "doctor": "داکتر",
    "look": "معلوم شدن", "drink": "نوشیدن", "if": "اگه",
    "doesn't": "(منفیِ فعل کمکی، سوم‌شخص مفرد)", "better": "بهتر",
    "nurse": "نرس", "cook": "آشپز", "driver": "دریور",
    "patients": "مریض‌ها", "help": "کمک کردن", "reports": "راپورها",
    "interesting": "جالب", "company": "شرکت", "downtown": "مرکز شهر",
    "answer": "جواب دادن", "emails": "ایمیل‌ها",
    "sometimes": "بعضی وقت‌ها", "with": "با", "clients": "مشتری‌ها",
    "job": "وظیفه",
    "bedroom": "اتاق خواب", "kitchen": "آشپزخانه", "bathroom": "تشناب",
    "living": "نشیمن", "room": "اتاق",
    "garden": "باغچه", "many": "چند", "rooms": "اتاق‌ها",
    "there": "آنجا",
    "there's": "... استه (مخفف)", "apartment": "آپارتمان",
    "has": "داره", "bedrooms": "اتاق‌خواب‌ها", "favorite": "پسندیده",
    "tell": "گفتن", "isn't": "نیست (مخفف)", "balcony": "بالکن",
    "upstairs": "منزل بالا", "near": "نزدیک", "easy": "آسان",
    "eat": "خوردن",
    "appointment": "ملاقات", "document": "سند",
    "proof": "سند؛ ثبوت", "residency": "اقامت",
    "form": "فورم", "confirmation": "تأیید",
    "wondering": "می‌خواستم بدانم", "whether": "آیا",
    "could": "می‌تانستم/می‌تانین", "make": "گرفتن",
    "possible": "ممکن", "come": "آمدن", "update": "به‌روز کردن",
    "address": "آدرس", "moved": "کوچ کرد (زمان گذشته)",
    "id": "تذکره؛ کارت شناسایی",
    "utility": "خدمات شهری", "bill": "بل",
    "bring": "آوردن", "such": "مثل",
    "lived": "زندگی کده‌ام (زمان گذشته)",
    "since": "از (زمان مشخص)", "lease": "قرارداد کرایه",
    "when": "کِی", "10am": "ساعت ۱۰ صبح", "4471": "۴۴۷۱",
    "opinion": "نظر", "other": "دیگه",
    "hand": "دست",
    "agree": "موافق بودن", "dog": "سگ", "dogs": "سگ‌ها", "space": "فضا",
    "run": "دویدن", "playground": "زمین بازی",
    "fair": "منصفانه", "point": "نکته", "they": "آنها",
    "move": "جابه‌جا کردن", "farther": "دورتر",
    "away": "دور",
    # Unit 27 (A2: opening a bank account), added 2026-07-07. Atomic per-
    # token glosses -- cross-checked against, but not a find-replace of,
    # docs/content/overlays/prs-en/a2_unit27.yaml's own (phrase-level)
    # Dari glosses. "debit"/"card"/"i'll"-style contraction pattern reuse
    # their existing Unit 15/12 senses unchanged. Some genuinely distinct
    # Afghan Dari vocabulary here vs the fa-en script's Farsi (fee=معاش
    # not کارمزد, DMV=ادارهٔ ترافیک not ادارهٔ راهنمایی و رانندگی, 500=
    # پنجصد not پانصد -- all cross-checked against the actual prs-en
    # overlay text, not copied from the fa-en dict).
    "checking": "جاری", "account": "حساب",
    "monthly": "ماهانه", "fee": "فیس؛ کارمزد", "minimum": "حداقل",
    "balance": "مانده", "direct": "مستقیم",
    "deposit": "واریز", "documents": "اسناد (جمع)",
    "you'll": "شما ... ضرورت دارین (مخفف)",
    "dmv": "ادارهٔ ترافیک",
    "business": "کاری",
    "days": "روزها", "keep": "نگه داشتن", "500": "پنجصد",
    "sounds": "به‌نظر می‌رسه",
    "teller": "کارمند بانک", "both": "هر دو",
    # Unit 28 (A2: attending a doctor's appointment), added 2026-07-07.
    # Atomic per-token glosses -- cross-checked against, but not a find-
    # replace of, docs/content/overlays/prs-en/a2_unit28.yaml's own
    # (phrase-level) Dari glosses. Some genuinely distinct Afghan Dari
    # vocabulary here vs the fa-en script's Farsi (medicine=دوا not
    # دارو, worse=خرابتر not بدتر, twice=دو مرتبه not دو بار, within=تا
    # not ظرف -- all cross-checked against the actual prs-en overlay
    # text). "appointment"/"confirmation"/"card"/"arrive"/"headache"/
    # "sore"/"throat"/"fever"/"if"/"doesn't"/"better"/"drink"/"doctor"/
    # "any"/"should"/"take"/"get"/"come"/"this"/"water"/"day"/"minutes"/
    # "ten"/"five"/"number"/"today" reuse their existing senses unchanged.
    "medicine": "دوا", "prescription": "نسخهٔ داکتر",
    "follow": "پیگیری (در وقت بعدی)",
    "getting": "شدن (فعل، در خرابتر شدن)",
    "worse": "خرابتر", "insurance": "بیمه",
    "i've": "... دارم (مخفف)",
    "had": "داشت (زمان گذشته)", "early": "زودتر",
    "confirmed": "تأیید شده (استه)", "3pm": "ساعت سه بعد از چاشت",
    "7724": "۷۷۲۴", "twice": "دو مرتبه",
    "plenty": "زیاد",
    "back": "باز (باز آمدن)",
    "within": "تا (تا یک هفته)",
    # Unit 29 (A2: reporting a maintenance problem), added 2026-07-07.
    # Atomic per-token glosses -- cross-checked against, but not a find-
    # replace of, docs/content/overlays/prs-en/a2_unit29.yaml's own
    # (phrase-level) Dari glosses. Genuinely distinct Afghan Dari
    # vocabulary vs the fa-en script's Farsi (repair=ترمیم not تعمیر,
    # report=خبر دادن not گزارش دادن, someone=یک کس not یک نفر, afternoon-
    # hour phrasing follows this script's own established "بعد از چاشت"
    # convention rather than the overlay's Farsi-influenced "بعد از ظهر").
    # "kitchen"/"apartment"/"bathroom" reuse their existing unit24 senses
    # unchanged (recapped, not retaught).
    "leaking": "چکیدن", "sink": "ظرفشویی", "building": "بلاک", "manager": "مدیر",
    "plumber": "پایپ‌کار", "repair": "ترمیم", "report": "خبر دادن",
    "problem": "مشکل", "been": "بوده (در ساختار ماضی نقلی)",
    "someone": "یک کس؛ کسی", "fix": "ترمیم کردن",
    "2pm": "ساعت ۲ بعد از چاشت", "4pm": "ساعت ۴ بعد از چاشت",
    "received": "دریافت شده (استه)", "6180": "۶۱۸۰", "send": "فرستادن",
    "home": "خانه", "here's": "همینه (این استه، در معرفی چیزی)",
    # Units 30-42 (hobbies through personality), added 2026-07-11 by
    # the prs-en depth-extension worker. Atomic per-token glosses --
    # authored fresh in Afghan Dari register for each unit's real
    # taught vocabulary (checked against docs/content/overlays/
    # prs-en/a1_unit30.yaml through a1_unit42.yaml's own real Dari
    # phrasing where a matching gloss existed), NOT a copy of any
    # sibling script's Farsi. Afghan-Dari-specific vocabulary used
    # deliberately here where it differs from Iranian Farsi: کدن
    # (rather than the Farsi-only کردن) in several light-verb glosses,
    # مکتب-register informal forms, and the existing dictionary's own
    # established third-person "می‌کنه" spoken-register ending
    # (rather than Farsi's written می‌کند) for every new present-tense
    # third-person verb form below, matching this file's own
    # precedent throughout units 1-29.
    # Unit 30
    "reading": "کتاب خواندن", "cooking": "آشپزی",
    "painting": "نقاشی", "running": "دویدن",
    "goes": "می‌ره (سوم‌شخص مفرد)", "video": "ویدیو", "games": "بازی‌ها",
    "always": "همیشه", "often": "اکثراً",
    "cooks": "آشپزی می‌کنه (سوم‌شخص مفرد)", "rarely": "به ندرت",
    "never": "هیچ‌وقت", "paint": "رنگ‌مالی کردن",
    "ever": "هیچ‌وقت (در سوال)", "play": "بازی کردن", "book": "کتاب",
    "different": "مختلف", "hobbies": "سرگرمی‌ها", "mornings": "صبح‌ها",
    "friends": "رفقا", "paints": "رنگ‌مالی می‌کنه (سوم‌شخص مفرد)",
    # Unit 31
    "tall": "قد بلند", "short": "قد کوتاه", "hair": "موی سر", "long": "دراز",
    "blond": "موی طلایی", "curly": "چوقی (موی)", "eyes": "چشم‌ها",
    "brown": "قهوه‌یی", "green": "سبز", "glasses": "عینک",
    "wears": "می‌پوشه (سوم‌شخص مفرد)", "coworker": "همکارِ هم‌دفتر",
    "starting": "شروع کدن", "mia": "میا",
    "does.": "(فعل کمکی، سوم‌شخص مفرد do)", "door": "دروازه", "now": "حالا",
    "same": "همرنگ؛ یکسان", "laugh": "خندیدن", "lot": "خیلی",
    # Unit 32
    "cat": "پیشک", "sister's": "مالِ خواهر", "fish": "ماهی", "bird": "مرغک",
    "pet": "حیوان خانگی", "pets": "حیوانات خانگی",
    "luna.": "لونا", "likes": "خوش داره (سوم‌شخص مفرد)",
    "friendly": "خوش‌رفتار", "mia,": "میا،", "yes,": "بلی،",
    "nice!": "قشنگ!", "loves": "خیلی خوش داره (سوم‌شخص مفرد)",
    "ball.": "توپ.", "named": "نام‌دار؛ به نام", "max.": "مکس",
    "morning.": "صبح.", "walks,": "قدم‌ زدن‌ها،", "still": "بازهم",
    "watch": "تماشا کردن", "swim.": "شنا کردن.",
    # Unit 33
    "bus": "بس", "drive": "موتر راندن", "bike": "بایسکل", "ride": "سوار شدن",
    "work?": "کار؟", "takes": "طول می‌کشه (سوم‌شخص مفرد)",
    "late": "دیر", "daniel?": "دنیل؟", "it?": "آن؟", "okay,": "خیر استه،",
    "parking": "پارکینگ", "difficult.": "مشکل.",
    "drives": "موتر می‌رانه (سوم‌شخص مفرد)", "office.": "دفتر.",
    "worry": "پریشان بودن",
    # Unit 34
    "soccer": "فوتبال", "saturdays": "روزهای شنبه", "tennis": "تنیس",
    "plays": "بازی می‌کنه (سوم‌شخص مفرد)", "basketball": "بسکتبال",
    "swimming": "شنا کردن", "yoga": "یوگا", "exercise": "ورزش",
    "times": "دفعه‌ها", "swims": "شنا می‌کنه (سوم‌شخص مفرد)",
    "weekends": "آخر هفته‌ها", "gym": "جیم؛ باشگاه ورزشی", "pool": "حوض شنا",
    "us": "ما را", "really": "واقعاً", "house": "خانه", "stay": "ماندن",
    "active": "فعال", "ways": "طریقه‌ها", "before": "پیش از", "team": "تیم",
    "already": "قبلاً", "neighbor": "همسایه", "even": "حتی",
    "though": "اگرچه", "anyone's": "مالِ هیچ‌کس", "sport": "ورزش",
    # Unit 35
    "call": "زنگ زدن", "mom": "مادر (خودمانی)", "laptop": "لپ‌تاپ",
    "uses": "استفاده می‌کنه (سوم‌شخص مفرد)", "tablet": "تبلت",
    "reads": "می‌خوانه (سوم‌شخص مفرد)", "books": "کتاب‌ها",
    "computer": "کمپیوتر", "app": "اپلیکیشن", "camera": "کمره",
    "photos": "عکس‌ها", "text": "پیامک فرستادن",
    "sends": "می‌فرستد (سوم‌شخص مفرد)", "friend": "رفیق",
    "download": "دانلود کردن", "downloads": "دانلود می‌کنه (سوم‌شخص مفرد)",
    "wifi": "وایفای", "fast": "تیز", "battery": "بتری", "low": "کم",
    "use": "استفاده کردن", "slow": "آهسته", "most": "بیشتر",
    "mostly": "بیشترینه", "apps": "اپلیکیشن‌ها", "map": "نقشه",
    "them": "آنها را", "names": "نام‌ها", "their": "مالِ آنها",
    "phones": "تیلفون‌ها", "differently": "به طور مختلف", "people": "مردم",
    "instead": "به‌عوض", "maps": "نقشه‌ها",
    "tries": "کوشش می‌کنه (سوم‌شخص مفرد)", "recipes": "رسپی‌ها",
    "laptops": "لپ‌تاپ‌ها", "chat": "گپ زدن (آنلاین)",
    # Unit 36
    "course": "کورس", "taking": "گرفتن (کورس)",
    "community": "اجتماعی", "college": "کالج",
    "homework": "کار خانگی", "subject": "مضمون", "math": "ریاضی",
    "study": "درس خواندن", "studies": "درس می‌خانه (سوم‌شخص مفرد)",
    "studying": "درس‌خواندن", "doing": "انجام دادن", "photography": "عکاسی",
    "how's": "چطوره (مخفف)", "learning": "یادگرفتن",
    "teach": "درس دادن", "sometime": "یک وقتی", "something": "یک چیزی",
    "outside": "بیرون از", "nights": "شب‌ها", "learn": "یاد گرفتن",
    "skills": "مهارت‌ها", "spanish": "زبان هسپانوی",
    "wants": "می‌خواهه (سوم‌شخص مفرد)", "travel": "سفر کردن",
    "mexico": "مکسیکو", "someday": "یک روزی", "talk": "گپ زدن",
    "classes": "صنف‌ها", "october": "اکتوبر",
    # Unit 37
    "party": "محفل؛ مهمانی", "having": "داشتن",
    "gift": "تحفه", "bought": "خرید (زمان گذشته)",
    "invite": "دعوت کردن", "celebrate": "جشن گرفتن",
    "congratulations": "مبارک باشه", "coworkers": "همکاران",
    "congratulate": "تبریک گفتن", "him": "او را (مذکر)",
    "promotion": "ترفیع", "wish": "آرزو کردن", "surprise": "غافلگیرکننده",
    "planning": "پلان کدن", "know": "دانستن", "daniel's": "مالِ دنیل",
    "12th": "دوازدهم", "didn't": "(منفیِ فعل کمکی، زمان گذشته)", "office": "دفتر",
    "perfect": "عالی", "buy": "خریدن", "cake": "کیک", "definitely": "قطعاً",
    "we'll": "ما ... خواهیم (مخفف)",
    "were": "بودند (زمان گذشته)",
    "arrived": "رسید (زمان گذشته)",
    "found": "پیدا کرد (زمان گذشته)", "balloons": "بلون‌ها",
    "break": "وقفه", "everyone": "همه", "said": "گفت (زمان گذشته)",
    "congratulated": "تبریک گفت (زمان گذشته)",
    "gave": "داد (زمان گذشته)", "pair": "یک جوره", "framed": "قاب‌شده",
    "took": "گرفت (زمان گذشته)", "herself": "خودش (مؤنث)",
    "thanked": "تشکر کرد (زمان گذشته)", "wonderful": "عالی؛ فوق‌العاده",
    # Unit 38
    "chore": "کار خانه", "washing": "شستن", "dishes": "ظرف‌ها",
    "least": "کمترین", "laundry": "لباس‌شویی", "sundays": "روزهای یکشنبه",
    "vacuum": "جاروبرقی کدن", "vacuums": "جاروبرقی می‌کنه (سوم‌شخص مفرد)",
    "trash": "زباله", "out": "بیرون", "clean": "پاک کردن", "wash": "شستن",
    "cleans": "پاک می‌کنه (سوم‌شخص مفرد)", "mess": "شلوغی", "coming": "آمدن",
    "some": "بعضی", "cleaning": "پاک‌کاری", "leave": "رفتن (ترک کردن)",
    "own": "خودِ", "habits": "عادت‌ها", "washes": "می‌شویه (سوم‌شخص مفرد)",
    "mind": "چیزی نگفتن",
    "hates": "نفرت داره (سوم‌شخص مفرد)", "mia's": "مالِ میا",
    "luna": "لونا", "fur": "پشم حیوان", "everywhere": "همه‌جا",
    "guests": "میهمانان", "asked": "پرسید (زمان گذشته)",
    "vacuumed": "جاروبرقی کرد (زمان گذشته)", "thankful": "سپاسگزار",
    # Unit 39
    "neighborhood": "همسایگی؛ ساحه", "helpful": "کمک‌کننده",
    "nearby": "نزدیک", "quiet": "آرام", "noisy": "پرسروصدا",
    "mine": "مالِ من", "neighbors": "همسایه‌ها", "live": "زندگی کردن",
    "along": "خوب رفتار کدن", "grocery": "مواد خوراکی",
    "five-minute": "پنج‌دقیقه‌یی", "say": "گفتن", "might": "شاید (فعل کمکی)",
    "soon": "زود", "mr": "آقای", "lopez": "لوپیز",
    "waters": "آب می‌ته (سوم‌شخص مفرد)", "plants": "نباتات",
    "neighborhoods": "ساحه‌ها", "restaurants": "رستورانت‌ها",
    "shops": "دکان‌ها", "knows": "می‌شناسه (سوم‌شخص مفرد)",
    "several": "چند تا", "says": "می‌گه", "hallway": "دهلیز",
    "lives": "زندگی می‌کنه (سوم‌شخص مفرد)",
    "barks": "پارس می‌کنه (سوم‌شخص مفرد)", "talking": "گپ زدن",
    "decided": "تصمیم گرفت (زمان گذشته)",
    # Unit 40
    "post office": "پوستخانه", "letters": "خط‌ها (نامه‌ها)",
    "letter": "خط (نامه)", "package": "پارسل", "stamp": "تمبر",
    "envelope": "پاکت خط", "put": "گذاشتن", "mailbox": "صندوق پستی",
    "postcard": "کارت پستال", "express": "بیان کردن", "mail": "پُست (خط و پارسل)",
    "regular": "معمولی", "cost": "قیمت داشتن", "chicago": "شیکاگو",
    "receipt": "رسید", "around": "دور و بر", "post": "پُست کردن",
    "sent": "فرستاد (زمان گذشته)",
    "paid": "پرداخت کرد (زمان گذشته)",
    "wanted": "خواست (زمان گذشته)", "quickly": "زود", "ready": "آماده",
    "clerk": "کارمند", "weighed": "وزن کرد (زمان گذشته)",
    "chose": "انتخاب کرد (زمان گذشته)", "packages": "پارسل‌ها",
    "buys": "می‌خره (سوم‌شخص مفرد)",
    "writes": "می‌نویسه (سوم‌شخص مفرد)",
    "feels": "احساس می‌کنه (سوم‌شخص مفرد)", "personal": "شخصی",
    # Unit 41
    "recipe": "رسپی", "grandmother's": "مالِ بی‌بی",
    "ingredient": "مواد اولیه", "onions": "پیاز", "chop": "خرد کردن",
    "boil": "جوش دادن", "pasta": "پاستا", "taste": "چشیدن", "sauce": "سُس",
    "needs": "ضرورت داره (سوم‌شخص مفرد)", "salt": "نمک",
    "bake": "پختن (در تنور/فِر)", "forget": "فراموش کردن",
    "add": "اضافه کردن", "making": "ساختن", "show": "نشان دادن",
    "these": "این‌ها", "pieces": "قطعه‌ها", "delicious": "خوش‌مزه",
    "makes": "می‌سازه (سوم‌شخص مفرد)", "using": "استفاده کدن",
    "mother's": "مالِ مادر", "taught": "یاد داد (زمان گذشته)",
    "without": "بدون", "cutting": "بریدن", "fingers": "انگشت‌ها",
    "yet": "هنوز", "he's": "او ... استه (مخفف)",
    "chopped": "خرد کرد (زمان گذشته)", "while": "در حالی که",
    "boiled": "جوش داد (زمان گذشته)", "made": "ساخت (زمان گذشته)",
    "tasted": "چشید (زمان گذشته)",
    # Unit 42
    "funny": "بذله‌گو", "hardworking": "زحمتکش", "employee": "کارمند",
    "shy": "شرمگین", "calm": "آرام", "talkative": "پرگپ",
    "warms": "گرم می‌شه", "sense": "حس",
    "humor": "مزاح", "gets": "می‌گیره (سوم‌شخص مفرد)", "once": "یک‌بار",
    "project": "پروژه", "finishes": "ختم می‌کنه (سوم‌شخص مفرد)",
    "tasks": "وظیفه‌ها", "meetings": "ملاقات‌ها", "comfortable": "راحت",
    "relaxed": "آرام‌شده", "personalities": "شخصیت‌ها",
    "meets": "ملاقات می‌کنه (سوم‌شخص مفرد)", "creative": "خلاق",
    "helps": "کمک می‌کنه (سوم‌شخص مفرد)", "relax": "آرام گرفتن",
    "upset": "ناراحت", "outgoing": "اجتماعی", "organized": "منظم",
    "plans": "پلان‌ها", "group": "گروه", "patient": "صابر",
    "teaches": "درس می‌ته (سوم‌شخص مفرد)", "enjoy": "لذت بردن",
    "spending": "سپری کدن (وخت)",
}

EN_TARGET_TO_PRS_GLOSS.update({
    "sky": "آسمان", "grass": "چمن", "yellow": "زرد", "sun": "آفتاب",
    "dark": "تاریک", "wearing": "پوشیده استه", "light": "روشن",
    "painted": "رنگ‌شده", "bright": "روشن؛ درخشان", "fun": "جالب",
    "our": "از ما", "presentation": "ارائه", "choose": "انتخاب کردن",
    "colors": "رنگ‌ها", "looks": "معلوم می‌شه", "professional": "مسلکی",
    "choice": "انتخاب", "everything": "همه‌چیز", "gardens": "باغ‌ها",
    "especially": "به‌خصوص", "beautiful": "مقبول؛ زیبا", "reminds": "یادآوری می‌کنه",
    "everyday": "روزمره", "conversations": "گپ‌ها؛ گفت‌وگوها",
    "spring": "بهار", "flowers": "گل‌ها", "bloom": "شکوفه کردن",
    "summer": "تابستان", "beach": "ساحل", "fall": "خزان",
    "change": "تغییر کردن", "winter": "زمستان", "snows": "برف می‌بارد",
    "season": "فصل", "walking": "پیاده‌روی", "seasons": "فصل‌ها",
    "playing": "بازی کردن", "find": "پیدا کردن؛ دانستن", "outdoors": "بیرون",
    "emergency": "حالت اضطراری", "police": "پولیس", "ambulance": "امبولانس",
    "fire": "آتش", "department": "اداره؛ بخش", "911": "۹۱۱",
    "burning": "در حال سوختن", "smell": "بو", "smoke": "دود", "pan": "دیگ؛ تابه",
    "caught": "گرفت", "off": "خاموش؛ دور", "stove": "داش؛ اجاق",
    "hurry": "عجله کردن", "friend's": "از دوست", "goodness": "وای؛ خوبی",
    "wait": "صبر کردن", "case": "مورد", "safer": "امن‌تر",
    "until": "تا", "elevator": "لفت؛ آسانسور", "stairs": "زینه‌ها",
    "third": "سوم", "give": "دادن", "finally": "بالاخره",
    "waited": "صبر کرد", "notice": "اطلاعیه", "safe": "امن",
    "came": "آمد", "check": "چک کردن", "relieved": "آرام؛ آسوده",
    "hurt": "زخمی؛ آسیب‌دیده", "lost": "گم‌شده", "keys": "کلیدها",
    "wallet": "بکس پول", "backpack": "بکس پشتی", "seen": "دیده",
    "anyone": "کسی", "strap": "بند", "where's": "کجاست",
    "fountain": "فواره", "you're": "شما استین", "inside": "داخل",
    "ask": "پرسیدن", "holding": "گرفته استه", "desk": "میز پذیرش",
    "lose": "گم کردن", "item": "چیز؛ وسیله", "main": "عمده/اساسی", "gate": "دروازه",
    "describe": "توصیف کردن", "its": "از آن", "special": "خاص",
    "details": "جزئیات", "staff": "کارمندان اداره", "called": "زنگ زد؛ صدا کرد",
    "told": "گفت", "whole": "تمام", "story": "قصه", "track": "رد؛ پیگیری",
    "things": "چیزها", "available": "دسترس؛ موجود", "confirm": "تأیید کردن",
    "reschedule": "وقت را تغییر دادن", "max": "مکس", "seems": "معلوم می‌شه",
    "lately": "این اواخر", "due": "وقتش رسیده", "yearly": "سالانه",
    "checkup": "معاینه", "vet": "داکتر حیوانات", "dog's": "از سگ",
    "max's": "از مکس", "dentist": "داکتر دندان", "service": "خدمات",
    "you'd": "شما ... می‌کردین", "receptionist": "کارمند پذیرش",
    "changes": "تغییرات", "nervous": "وارخطا؛ مضطرب", "borrow": "قرض گرفتن",
    "return": "پس آوردن؛ برگرداندن", "borrowed": "قرض گرفته", "weeks": "هفته‌ها",
    "cookbook": "کتاب آشپزی", "fill": "پر کردن", "visiting": "دیدن؛ بازدید کردن",
    "libraries": "کتابخانه‌ها", "let": "اجازه دادن", "items": "چیزها؛ وسایل",
    "few": "چند", "librarian": "کتابدار", "finished": "ختم کرد",
    "used": "استفاده کرد", "started": "شروع کرد", "borrowing": "قرض گرفتن",
    "returned": "پس آورد؛ برگرداند", "picked": "گرفت؛ برداشت", "got": "گرفت",
    "checked": "چک کرد", "practice": "تمرین", "teaching": "درس دادن؛ آموزش",
    "reminded": "یادآوری کرد",
})


# Dari glosses for the 52 newly-covered units (a1 49-68, a2 30-34, b1 01-19,
# b2 01-08), added 2026-07-22. Two sources, both Dari-register by
# construction:
#   * where the unit's prs-en overlay has a single-word vocabulary teaching
#     card for exactly this token, the overlay's OWN `gloss` string is reused
#     verbatim (that text is the Dari a learner already sees for this word --
#     any other wording here would teach two different translations of one
#     word in one course);
#   * everything else is written here against the token's real sentence in
#     docs/content/realizations/en/, in the colloquial-Dari register this lane
#     is pinned to (docs/content/CLAUDE.md: "prs-en overlay lane: colloquial
#     Dari, می‌تانین/استه style") -- استه/استم/استین for the copula, the -ه 3sg
#     clitic (می‌کنه/می‌شه/می‌ته), 2pl -ین, and Afghan lexis (دالر، بس، سرک،
#     دوکان، فلم، معلم، کلکین، چوکی، تکت، چوک) rather than the Iranian
#     equivalents. scripts/check_dari_register.py's marker inventory was run
#     over every value below (it deliberately scopes out .py files, so the
#     check was applied to this dict directly): zero tier-1 markers, zero
#     tier-2 formal 3sg, zero Iranian copula, zero Iranian metalanguage.
EN_TARGET_TO_PRS_GLOSS.update({
    # -- a1 unit49 (sorting household waste)
    "sort": "دسته‌بندی کردن", "bin": "سطل", "recycle": "بازیافت کردن",
    "waste": "زباله", "glass": "شیشه", "paper": "کاغذ",
    "collection": "جمع‌آوری", "recycling": "بازیافت", "food": "غذا",
    "jar": "مرتبان", "bins": "سطل‌ها", "tuesdays": "سه‌شنبه‌ها",
    "fridays": "جمعه‌ها", "correctly": "به‌شکل درست",
    "buildings": "تعمیرها", "kinds": "قسم‌ها",
    "practicing": "تمرین کرده (شکل استمراری)",
    "afterward": "بعد از آن", "stopped": "جلوش را گرفت",
    "showed": "نشان داد", "sorts": "دسته‌بندی می‌کنه",
    "explained": "توضیح داد",
    # -- a1 unit50 (staying in accommodation)
    "hotel": "هوتل", "reservation": "رزرو", "check-out": "خروج (تخلیهٔ اتاق)",
    "staying": "ماندن (شکل استمراری)", "beds": "بسترها",
    "included": "شامل (در قیمت)", "key": "کلید",
    "under": "زیر؛ به نام", "downstairs": "در منزل پایین",
    "guesthouse": "مهمان‌خانه", "mountains": "کوه‌ها", "november": "نومبر",
    "14th": "چهاردهم", "16th": "شانزدهم", "picture": "تصویر",
    "view": "منظره", "window": "کلکین", "stayed": "ماند", "cooked": "پخت",
    "himself": "خودش (مذکر)", "loved": "بسیار خوشش آمد",
    # -- a1 unit51 (at the pharmacy)
    "pharmacist": "دواساز", "syrup": "شربت (دوای سرفه)",
    "runny": "آب‌ریزشی (بینی)", "nose": "بینی", "hours": "ساعت‌ها",
    "tablets": "گولی‌ها", "felt": "احساس کرد", "walked": "پیاده رفت",
    "listened": "گوش داد", "symptoms": "علامت‌ها", "recommended": "سفارش کرد",
    "box": "قطی", "tissues": "دستمال کاغذی",
    # -- a1 unit52 (personal care / the hairdresser)
    "haircut": "اصلاح", "hairdresser": "آرایشگر", "trim": "کمی کوتاه کردن",
    "shorter": "کوتاه‌تر", "style": "مدل", "visit": "به دیدن آمدن",
    "salon": "سالون آرایش", "washed": "شست",
    "looked": "معلوم می‌شد", "met": "ملاقات کرد",
    # -- a1 unit53 (renting a bike)
    "rent": "کرایه گرفتن", "hour": "ساعت", "helmet": "کلاه ایمنی",
    "costs": "قیمتش می‌شه", "we'd": "ما می‌خواهیم (مخفف)",
    "bikes": "بایسکل‌ها", "river": "دریا", "invited": "دعوت کرد",
    "neither": "هیچ‌کدام (از دو نفر)", "owned": "صاحبش بود",
    "rental": "کرایه‌دهی", "needed": "ضرورت داشت",
    "enjoying": "لذت بردن (شکل استمراری)", "join": "یکجا شدن",
    # -- a1 unit54 (the laundromat)
    "laundromat": "رخت‌شویی", "dryer": "خشک‌کن",
    "quarters": "سکهٔ بیست‌وپنج‌سنتی", "detergent": "پودر رخت‌شویی",
    "load": "نوبت", "machine": "ماشین (رخت‌شویی)", "broken": "خراب",
    "clothes": "کالی‌ها", "machines": "ماشین‌ها", "cycle": "دور (شستشو)",
    "pick": "گرفتن (پس گرفتن)", "broke": "خراب شد",
    "down": "پایین‌تر (در امتداد سرک)", "attendant": "مسئول دوکان",
    "talked": "گپ زد", "kept": "نگه کرد",
    "probably": "احتمالاً", "fixed": "درست شد",
    # -- a1 unit55 (the swimming pool)
    "locker": "کمد", "rules": "قوانین", "lifeguard": "نجات‌غریق",
    "enter": "داخل شدن", "swim": "آب‌بازی کردن", "cap": "کلاه (آب‌بازی)",
    "wear": "پوشیدن", "read": "خواندن", "watches": "نگاه می‌کنه",
    "lockers": "کمدها", "tickets": "تکت‌ها", "caps": "کلاه‌ها",
    "required": "ضروری", "entrance": "دروازهٔ ورودی", "dollar": "دالر",
    "coin": "سکه", "cool": "خنک شدن", "sign": "لوحه",
    "listed": "فهرست کرده بود", "bags": "بکس‌ها", "swam": "آب‌بازی کرد",
    "try": "کوشش کردن", "diving": "شیرجه", "board": "تخته (شیرجه)",
    # -- a1 unit56 (ordering in a restaurant)
    "waiter": "گارسون", "table": "میز", "order": "فرمایش دادن",
    "chicken": "گوشت مرغ", "meal": "غذا (وعدهٔ غذا)", "sit": "نشستن",
    "nineteen": "نزده", "pizza": "پیتزا", "juice": "شربت میوه",
    "brought": "آورد", "ordered": "فرمایش داد", "excellent": "بسیار عالی",
    # -- a1 unit57 (at the cinema)
    "cinema": "سینما", "showtime": "وخت نمایش", "seat": "چوکی",
    "screen": "پرده", "popcorn": "پاپ‌کورن", "popular": "مشهور",
    "film": "فلم", "start": "شروع شدن", "liked": "خوش داشت",
    "sixteen": "شانزده", "schedule": "جدول وخت",
    "star": "ستاره",
    "journey": "سفر (بخشی از نام یک فلم)",
    "7:00": "ساعت هفت", "$8": "هشت دالر",
    "race": "مسابقه",
    "5:00": "ساعت پنج", "$10": "ده دالر", "9:00": "ساعت نه", "$6": "شش دالر",
    "cashier": "کارمند صندوق", "explorers": "کاشفان",
    # -- a1 unit58 (visiting a museum)
    "museum": "موزیم", "exhibition": "نمایشگاه", "sculpture": "مجسمه",
    "guide": "راهنما", "enjoyed": "لذت برد", "paintings": "نقاشی‌ها",
    "city": "شهر", "adult": "کلان‌سال (تکت کلان‌سالان)", "current": "فعلی",
    "town": "شهر قدیمی", "square": "چوک", "sunset": "غروب آفتاب",
    # -- a1 unit59 (basic banking / the ATM)
    "atm": "ای‌تی‌ام", "pin": "پین (کود رمز)", "4:00": "ساعت چهار",
    "limit": "حد؛ محدودیت", "$100": "یکصد دالر", "accepted": "قبول می‌شه",
    "quick": "کوتاه؛ سریع", "entered": "داخل کرد (پین را)",
    # -- a1 unit60 (invitations)
    "invitation": "دعوت", "picnic": "پیک‌نیک", "6:00": "ساعت شش",
    "18": "هجده (نمبر خانه)", "wrote": "نوشت",
    # -- a1 unit61 (apologies and excuses)
    "traffic": "ترافیک", "mistake": "اشتباه", "starts": "شروع می‌شه",
    "waiting": "انتظار کشیدن (شکل استمراری)", "note": "یادداشت",
    "3:00": "ساعت سه", "apology": "معذرت‌خواهی", "classroom": "صنف",
    # -- a1 unit62 (phone calls)
    "voicemail": "پیام صوتی", "sound": "صدا", "clear": "واضح",
    # -- a1 unit63 (asking for help)
    "carry": "بردن / حمل کردن", "heavy": "سنگین", "shelf": "رف",
    "carried": "برد؛ حمل کرد",
    # -- a1 unit64 (compliments)
    "lovely": "بسیار مقبول / دل‌پسند", "kind": "مهربان", "smile": "لبخند",
    "being": "بودن (شکل استمراری)", "compliment": "تعریف؛ گپ خوش",
    # -- a1 unit65 (returns and exchanges)
    "exchange": "بدل کردن", "refund": "پس‌گرفتن پول", "larger": "کلان‌تر",
    "offered": "پیشنهاد کرد", "exchanged": "بدل کرد",
    # -- a1 unit66 (describing symptoms)
    "symptom": "علامت", "hurts": "درد می‌کنه",
    # -- a1 unit67 (family news)
    "news": "خبر", "baby": "طفل نوزاد", "proud": "افتخارکننده",
    "must": "باید (حتماً)", "shared": "شریک ساخت",
    # -- a1 unit68 (borrowing and lending)
    "lend": "امانت دادن", "charger": "چارجر",
    "lending": "امانت دادن (شکل استمراری)", "leila's": "مالِ لیلا",
    "share": "شریک ساختن", "lent": "امانت داد", "remember": "به یاد داشتن",
    # -- a2 unit30 (a job interview)
    "experience": "تجربه", "position": "پُست", "availability": "آمادگی وقت",
    "strength": "نقطهٔ قوت", "requirement": "شرط", "resume": "خلاصهٔ سوانح",
    "deadline": "میعاد", "social": "اجتماعی", "media": "رسانه",
    "marketing": "مارکیتنگ", "strengths": "نقطه‌های قوت",
    "path": "راه (بخشی از نام یک شرکت)",
    "looking": "در جستجو", "coordinator": "هماهنگ‌کننده",
    "requirements": "شرط‌ها", "writing": "نوشتن (مهارت نوشتن)",
    "immediately": "فوراً", "interview": "مصاحبه", "deadlines": "میعادها",
    "managed": "موفق شد؛ اداره کرد", "questions": "سوال‌ها", "role": "وظیفه؛ نقش کاری",
    "typical": "معمولی",
    # -- a2 unit31 (a travel disruption)
    "delay": "تأخیر", "cancelled": "لغو شده", "alternative": "بدیل",
    "signal": "سگنال (علامت خط ریل)", "delayed": "به تأخیر افتاده",
    "5:15": "ساعت پنج و ربع", "5:30": "ساعت پنج و نیم", "station": "ایستگاه",
    "tracks": "خط‌های ریل",
    # -- a2 unit32 (online habits)
    "notification": "اطلاعیهٔ اپ", "messaging": "پیام‌رسان (اپ پیام‌رسان)",
    "useful": "مفید", "touch": "تماس",
    "notifications": "اطلاعیه‌ها", "sharing": "شریک ساختن (شکل استمراری)",
    "spend": "صرف کردن (وخت)", "thing": "چیز",
    # -- a2 unit33 (a weekly schedule)
    "weekday": "روز کاری", "weekdays": "روزهای کاری", "email": "ایمیل",
    "online": "آنلاین", "mondays": "دوشنبه‌ها", "wednesdays": "چهارشنبه‌ها",
    # -- a2 unit34 (a shopping complaint)
    "defective": "خراب", "policy": "پالیسی؛ قاعده", "blender": "بلندر",
    "working": "کار کردن (شکل استمراری)", "30": "سی",
    "refunded": "پولش پس داده شد", "thirty-five": "سی‌وپنج",
    # -- a2 unit35 (at the pharmacy: a prescription) --- DRAFT Dari glosses
    # (2026-08-05), Kabuli register, pending Ramin's native audit.
    "dose": "دوز؛ اندازهٔ هر بار خوردن دوا", "refill": "تکرار نسخه",
    "refills": "تکرار نسخه", "side": "جانبی",
    "effects": "عوارض جانبی", "shouldn't": "نباید (مخفف)",
    # -- a2 unit36 (correcting a document)
    "certificate": "تصدیق؛ سند رسمی", "spelled": "هجی کرد؛ حرف‌حرف گفت",
    "copy": "کاپی؛ نقل", "passport": "پاسپورت", "mistakes": "غلطی‌ها",
    "registration": "راجستر؛ ثبت‌نام", "correction": "اصلاح؛ درست‌سازی",
    "corrected": "اصلاح کرد؛ درست کرد", "reference": "مرجع؛ نمبر پیگیری",
    "3092": "۳۰۹۲",
    # -- a2 unit37 (video calls)
    "microphone": "مایکروفون", "connection": "اتصال؛ کنکشن انترنت",
    "mute": "بی‌آواز کردن", "face": "چهره (روبه‌رو)",
    "calls": "تماس‌ها؛ کال‌ها", "headphones": "هدفون", "asks": "می‌پرسه",
    "question": "سوال", "classmates": "هم‌صنفی‌ها",
    "speaking": "گپ زدن (شکل استمراری)",
    # -- a2 unit38 (a repair visit)
    "leak": "چکک؛ آب‌آمدن", "won't": "نخواهد (مخفف)",
    "rescheduled": "وختش را تغییر داد؛ به وخت دیگه ماند", "9am": "۹ بجهٔ صبح",
    "11am": "۱۱ بجهٔ صبح",
    # -- a2 unit39 (after the interview)
    "contract": "قرارداد؛ کنترکت", "salary": "معاش", "accept": "قبول کردن",
    "interested": "علاقه‌مند",
    # -- a2 unit40 (an online order problem)
    "delivery": "تحویل‌دهی؛ رسانیدن", "parcel": "بسته؛ پارسل",
    "lamp": "لمپ؛ چراغ", "8154": "۸۱۵۴",
    # -- b1 unit01 (necessity and obligation)
    "task": "کار، وظیفه", "finish": "تمام کردن", "earlier": "زودتر",
    "forgot": "فراموش کرد", "renew": "تمدید کردن", "membership": "عضویت",
    "set": "گذاشتن", "reminder": "یادآور",
    "done": "کرده (شکل سوم فعل)",
    # -- b1 unit02 (past and present ability)
    "license": "جواز", "system": "سیستم",
    "able": "توانا",
    "manage": "موفق شدن", "person": "شخص",
    "licenses": "جوازها", "changed": "تغییر کرد", "hers": "مالِ او (مؤنث)",
    "wasn't": "نبود (مخفف)", "save": "صرفه‌جویی کردن",
    # -- b1 unit03 (real and past hypotheticals)
    "rains": "باران می‌باره", "known": "دانسته (شکل سوم فعل)",
    "signed": "نام‌نویسی کرد", "checks": "سر می‌زنه",
    # -- b1 unit04 (agreeing and disagreeing)
    "disagree": "مخالف بودن", "believe": "باور داشتن", "reason": "دلیل",
    "focus": "تمرکز کردن", "respect": "احترام گذاشتن", "easily": "به‌آسانی",
    "disagrees": "مخالفت می‌کنه", "believes": "باور داره",
    "seeing": "دیدن (شکل استمراری)", "each": "هر",
    "other's": "مالِ همدیگر", "important": "مهم",
    "saves": "صرفه‌جویی می‌کنه",
    # -- b1 unit05 (workplace updates)
    "responsible": "مسئول", "technical": "تخنیکی", "sales": "فروشات",
    "gives": "می‌ته", "expects": "توقع داره", "tells": "می‌گه",
    "truth": "راستی؛ حقیقت", "delays": "تأخیرها", "review": "بازبینی کردن",
    "numbers": "ارقام", "correct": "درست", "notes": "یادداشت‌ها",
    "appreciate": "قدردانی کردن",
    # -- b1 unit06 (telling a past story)
    "stranger": "یک کس ناشناس", "mechanic": "میخانیک", "flat": "پنچر (تایر)",
    "tire": "تایر", "pull": "کنار کردن",
    "driving": "موتر راندن (شکل استمراری)",
    "pulled": "کنار سرک ایستاد کرد", "helped": "کمک کرد",
    "word": "گپ", "suddenly": "ناگهان",
    "happened": "اتفاق افتاد",
    # -- b1 unit07 (real future conditions)
    "unless": "مگر این‌که، اگه نه", "condition": "شرط، حالت لازم",
    "result": "نتیجه", "present": "حال (زمان حال)", "tense": "زمان (دستوری)",
    "real": "واقعی", "future": "آینده", "backup": "بدیل (پلان بدیل)",
    "plan": "پلان", "conference": "کنفرانس (اتاق جلسه)",
    "joins": "یکجا می‌شه", "cannot": "نمی‌تانه (مخفف)",
    # -- b1 unit08 (sequencing future events)
    "lock": "قفل کردن", "clause": "جملهٔ فرعی",
    "locks": "قفل می‌کنه", "careful": "با دقت", "routine": "روال روزمره",
    "hands": "دست‌ها", "clears": "میز را جمع می‌کنه",
    # -- b1 unit09 (reported speech)
    "speech": "گفتار (نقل قول)", "reported": "نقل‌شده (نقل قول غیرمستقیم)",
    "summary": "خلاصه", "enough": "کافی", "full": "مکمل",
    "reply": "جواب دادن",
    # -- b1 unit10 (expressing purpose)
    "goal": "هدف", "improve": "بهتر ساختن، بهتر شدن",
    "prepare": "آماده شدن، آماده کدن", "design": "دیزاین", "money": "پیسه",
    "english": "انگلیسی (زبان)", "vocabulary": "ذخیرهٔ کلمه‌ها",
    "verb": "فعل", "goals": "هدف‌ها", "practices": "تمرین می‌کنه",
    "updates": "گزارش‌های کوتاه", "descriptions": "توضیح‌های کورس",
    "program": "برنامهٔ تحصیلی", "saving": "پس‌انداز کردن (شکل استمراری)",
    # -- b1 unit11 (unreal hypotheticals and regret)
    "opportunity": "فرصت", "regret": "پشیمانی", "sooner": "زودتر",
    "confident": "بااعتمادبه‌نفس، مطمئن",
    "rather": "ترجیحاً",
    "chance": "فرصت؛ شانس", "unreal": "غیرواقعی",
    "situation": "حالت؛ وضعیت", "joined": "پیوست؛ شامل شد", "timing": "وخت‌بندی",
    "saved": "پس‌انداز کرد",
    # -- b1 unit12 (concession)
    "although": "گرچه، با اینکه (با یک جملهٔ کامل)",
    "despite": "باوجود (+ اسم یا مصدر)",
    "however": "اما، بازهم (در آغاز یک جملهٔ جدا)",
    "convince": "قناعت دادن، راضی کدن", "flexibility": "انعطاف‌پذیری",
    "teamwork": "کارِ تیمی", "distractions": "چیزهای حواس‌پرت‌کن",
    "valid": "معتبر؛ درست", "followed": "دنبال می‌شه",
    "noun": "اسم", "sentence": "جمله", "period": "نقطه (علامت)",
    "semicolon": "نقطه‌ویرگول", "builds": "می‌سازه", "misses": "دلش تنگ می‌شه",
    "colleagues": "همکاران", "during": "در جریان", "breaks": "وقفه‌ها",
    "noise": "سروصدا", "alone": "تنها", "matters": "مهم استه",
    "preferences": "ترجیح‌ها",
    # -- b1 unit13 (relative clauses)
    "whose": "که مالِ او (نشان‌دهندهٔ مالکیت)", "approve": "تأیید کدن",
    "approved": "تأیید کرد", "colleague": "همکارِ کاری", "sits": "می‌شینه",
    "leads": "رهبری می‌کنه", "projects": "پروژه‌ها",
    "defining": "تعیین‌کننده (جملهٔ وصفی تعیین‌کننده)",
    "relative": "وصفی (جملهٔ وصفی)", "commas": "کامه‌ها", "exactly": "دقیقاً",
    "mean": "منظور داشتن", "non-defining": "غیرتعیین‌کننده",
    "extra": "اضافی", "information": "معلومات", "identified": "معرفی‌شده",
    "easier": "آسان‌تر", "fifth": "پنجم", "floor": "منزل", "eats": "می‌خوره",
    "finishing": "تمام کردن (شکل استمراری)",
    "has already": "قبلاً ... کرده (زمان حال کامل)", "woman": "زن",
    "designer": "دیزاینر", "logo": "لوگو", "won": "برنده شد",
    "award": "جایزه", "ours": "مالِ ما", "explains": "توضیح می‌ته",
    # -- b1 unit14 (professional communication)
    "agenda": "اجندا", "possibly": "احتمالاً (در درخواست مؤدبانه)",
    "formal": "رسمی", "workplace": "محل کار", "requests": "درخواست‌ها",
    "softened": "نرم‌شده", "conditional": "شرطی", "command": "امر",
    "forms": "شکل‌ها", "polite": "مؤدبانه", "budget": "بودجه",
    "hope": "امید داشتن", "tomorrow's": "مالِ فردا", "latest": "تازه‌ترین",
    "client": "مشتری", "best": "بهترین کوشش",
    "advance": "پیش", "request": "درخواست",
    "updated": "تازه‌شده",
    # -- b1 unit15 (making a complaint)
    "complain": "شکایت کدن", "damaged": "خراب، آسیب‌دیده",
    "replacement": "تعویض (چیزِ نو به‌جای خراب)", "resolve": "حل کدن",
    "issue": "موضوع/ایراد", "product": "جنس؛ محصول", "written": "نوشتاری",
    "complaint": "شکایت", "parts": "بخش‌ها", "specific": "مشخص",
    "resolution": "راه حل", "chair": "چوکی",
    "dear": "محترم (در آغاز نامه)", "wheel": "چرخ",
    "proceed": "پیش رفتن؛ اقدام کردن",
    "calling": "زنگ زدن (شکل استمراری)",
    # -- b1 unit16 (giving advice)
    "advice": "نصیحت، مشوره",
    "overwhelmed": "خسته و تحتِ فشار", "prioritize": "اولویت دادن",
    "workload": "مقدارِ کار", "decline": "به شکل مؤدبانه رد کدن",
    "closer": "نزدیک‌تر", "asking": "خواستن (شکل استمراری)",
    "suggestions": "پیشنهادها", "hypothetical": "حالت فرضی",
    "recommendation": "سفارش", "softer": "نرم‌تر", "suggestion": "پیشنهاد",
    "stronger": "قوی‌تر", "depending": "بسته به",
    "top": "بالا",
    "leading": "رهبری کردن (شکل استمراری)", "seem": "معلوم شدن",
    "handle": "از عهده برآمدن", "solid": "محکم؛ پخته",
    # -- b1 unit17 (expressing regret)
    "hindsight": "درکِ بعد از واقع شدن",
    "procrastinate": "به تعویق انداختن", "participle": "اسم مفعول",
    "happen": "اتفاق افتادن", "missed": "از دست داد",
    "end": "آخر", "true": "راست",
    # -- b1 unit18 (future plans)
    "arrangement": "قرارِ از پیش تعیین‌شده", "intention": "نیت",
    "prediction": "پیش‌بینی", "months": "ماه‌ها", "continuous": "استمراری",
    "agreed": "توافق‌شده", "decision": "تصمیم", "steps": "قدم‌ها",
    "completely": "کاملاً", "predicts": "پیش‌بینی می‌کنه",
    "agrees": "موافقت می‌کنه", "exciting": "دلچسپ",
    # -- b1 unit19 (summarizing)
    "detail": "جزئیات", "condensed": "فشرده", "words": "کلمه‌ها",
    "covered": "شامل بود", "phrase": "عبارت", "points": "نکته‌ها",
    "keeping": "نگه داشتن (شکل استمراری)", "highlight": "برجسته ساختن",
    "single": "یگانه", "separately": "جداگانه", "original": "نسخهٔ اصلی",
    "article": "مقاله", "communication": "ارتباط", "examples": "مثال‌ها",
    "background": "پس‌زمینه", "messages": "پیام‌ها",
    "guessing": "حدس زدن (شکل استمراری)", "ideas": "فکرها؛ نظرها",
    # -- b2 unit01 (argumentation)
    "claim": "ادعا، موقفی که دفاع می‌کنین",
    "evidence": "شواهد، دلیل قابل دید", "counterargument": "دلیل مخالف",
    "rebut": "جواب دادن به دلیل مخالف",
    "concede": "قبول کدن یک بخش از گپ مخالف",
    "outweigh": "سنگین‌تر بودن، مهم‌تر بودن",
    "retention": "ماندن کارمندان، نگهداشت", "collaboration": "همکاری",
    "risks": "خطرها", "supports": "پشتیبانی می‌کنه",
    "moving": "پیش رفتن (شکل استمراری)", "forward": "به پیش",
    "strongest": "قوی‌ترین", "survey": "سروی", "results": "نتیجه‌ها",
    "consistent": "یکسان", "concern": "نگرانی", "data": "معلومات",
    "direction": "جهت", "defended": "دفاع‌شده", "moves": "حرکت‌ها",
    "state": "بیان کردن", "acknowledge": "قبول کردن (یک نگرانی)",
    "opposing": "مخالف", "phrases": "عبارت‌ها", "reasonable": "معقول",
    "conceding": "واگذار کردن (شکل استمراری)",
    "argues": "استدلال می‌کنه", "hybrid": "ترکیبی", "improves": "بهتر می‌سازه",
    "lowering": "پایین آوردن (شکل استمراری)", "performance": "کارکرد",
    "employees": "کارمندان شرکت", "teams": "تیم‌ها", "less": "کمتر",
    "likely": "محتمل", "may": "شاید (فعل کمکی احتمال)", "suffer": "آسیب دیدن",
    "acknowledges": "قبول می‌کنه", "delivered": "تحویل داد",
    "scores": "نمره‌ها", "slightly": "کمی", "higher": "بلندتر",
    "concludes": "نتیجه می‌گیره", "benefits": "فایده‌ها", "managers": "مدیران",
    "weaker": "ضعیف‌تر", "support": "پشتیبانی کردن",
    "routines": "روش‌های همیشگی", "abandon": "رها کردن",
    # -- b2 unit02 (speculation and deduction)
    "deduction": "نتیجه‌گیری از شواهد", "guesswork": "حدس بی‌پایه",
    "outage": "از کار افتادن سیستم، قطعی", "consequence": "نتیجه، پیامد",
    "overlap": "هم‌پوشانی داشتن", "explanation": "توضیح",
    "tentative": "احتیاطی؛ غیرقطعی", "server": "سرور",
    "gone": "رفته",
    "overnight": "در جریان شب", "generated": "تولید شد", "failed": "ناکام شد",
    "permission": "اجازه (دسترسی)", "possibility": "احتمال",
    "uncertain": "نامطمئن", "monitoring": "نظارتی (صفحهٔ نظارت)",
    "page": "صفحه", "blank": "خالی", "suggests": "می‌گه؛ پیشنهاد می‌کنه",
    "explain": "توضیح دادن", "finance": "مالی (تیم مالی)",
    "missing": "نداشتن (شکل استمراری)", "dashboard": "داشبورد",
    "rebuilt": "از نو ساخته شد", "certain": "مطمئن",
    "pure": "محض", "none": "هیچ‌کدام",
    "consequences": "پیامدها", "expect": "توقع داشتن", "guess": "حدس",
    "limited": "محدود",
    # -- b2 unit03 (hedging and emphasis)
    "hedge": "نرم ساختن ادعا", "qualify": "محدود یا شرط‌دار ساختن",
    "emphasize": "تاکید کدن، برجسته ساختن", "broadly": "در کل، به طور عمومی",
    "provided": "به شرط این‌که", "overall": "در کل",
    "extent": "اندازه",
    "create": "ایجاد کردن", "worries": "نگران می‌سازه", "timeline": "جدول زمانی",
    "adjusted": "تنظیم شد", "attention": "توجه", "feedback": "بازخورد",
    "positive": "مثبت", "carefully": "با احتیاط", "qualified": "شرط‌دار",
    "avoids": "خودداری می‌کنه", "sounding": "معلوم شدن (شکل استمراری)",
    "absolute": "قطعی", "limits": "محدود می‌سازه",
    "accepting": "قبول کردن (شکل استمراری)", "construction": "ساختار جمله",
    "speakers": "گوینده‌ها", "principle": "اصل",
    "language": "زبان", "shows": "نشان می‌ته", "levels": "سطح‌ها",
    "commitment": "تعهد", "cautious": "محتاط",
    "saying": "گفتن (شکل استمراری)", "fully": "به‌طور مکمل",
    "workable": "قابل اجرا", "clearer": "واضح‌تر", "quality": "کیفیت",
    "adds": "علاوه می‌کنه", "approval": "تأیید", "step": "مرحله",
    "conditions": "شرط‌ها", "creates": "ایجاد می‌کنه",
    # -- b2 unit04 (narrative time)
    "foreground": "رویداد اصلی که قصه به طرفش می‌ره",
    "prior": "قبلی، پیش از یک لحظهٔ گذشته",
    "interrupt": "قطع کدن یک کار در جریان", "ongoing": "در جریان، ادامه‌دار",
    "chronology": "ترتیب واقعی اتفاق‌ها", "venue": "محل برگزاری برنامه",
    "interrupted": "قطع کرد", "equipment": "وسایل", "power": "برق",
    "volunteers": "داوطلبان", "setting": "آماده کردن",
    "chairs": "چوکی‌ها", "simple": "ساده (گذشتهٔ ساده)", "events": "رویدادها",
    "moment": "لحظه", "simon": "سایمن", "strict": "دقیق؛ سخت‌گیرانه",
    "chronological": "به ترتیب زمانی", "expected": "توقع داشت",
    "crew": "گروه کاری", "lights": "چراغ‌ها",
    "through": "از میان",
    "event": "برنامه؛ رویداد",
    # -- b2 unit05 (register)
    "register": "درجهٔ رسمی یا خودمانی بودن گپ",
    "casual": "خودمانی، مناسب دوست نزدیک",
    # NOTE: the overlay's own card for `audience` glosses it with مخاطب. That
    # word is on check_dari_register.py's Iranian-instructional-metalanguage
    # list (this lane's norm is طرف مقابل), so it is rewritten here rather
    # than harvested verbatim -- the only harvested gloss in this whole block
    # that was NOT taken as-is. Flagged for the overlay lane to fix at source.
    "audience": "شنونده یا خواننده، کسی که پیام را می‌گیره",
    "institution": "نهاد یا اداره مثل کلینیک، بانک، پوهنتون",
    "stiff": "خشک و بیش از حد رسمی", "appropriate": "مناسب برای موقعیت",
    "grateful": "سپاسگزار", "scheduling": "وقت‌بندی (تیم وقت‌بندی)",
    "content": "محتوا", "shift": "تغییر دادن", "nina": "نینا",
    "clinic": "کلینیک", "texts": "متن‌ها", "stays": "همان می‌مانه",
    "level": "سطح", "formality": "رسمی بودن",
    # -- b2 unit06 (abstract opinions and values)
    "value": "ارزش یا اصل مهم",
    "fairness": "انصاف، برخورد معقول با مردم",
    "convenience": "آسانی و عملی بودن",
    "transparent": "شفاف، قابل فهم برای همه",
    "commercial": "وابسته به کاروبار و فروش", "public": "عمومی",
    "spaces": "فضاها", "qualification": "شرط‌گذاری بر ادعا",
    "weight": "وزن",
    "arguing": "استدلال کردن (شکل استمراری)", "silence": "خاموشی",
    "businesses": "کاروبارها", "response": "جواب (به نظر مقابل)",
    "directly": "مستقیماً", "person's": "مالِ یک نفر", "amara": "امارا",
    "protected": "محافظت شود", "activity": "فعالیت", "accepts": "قبول می‌کنه",
    "leo's": "مالِ لیو", "harder": "سخت‌تر", "survive": "دوام آوردن",
    "belongs": "تعلق داره", "stance": "موقف", "unlimited": "بی‌حد",
    "restrictions": "محدودیت‌ها", "protect": "محافظت کردن",
    "shaped": "شکل‌گرفته", "profit": "مفاد", "comfort": "راحتی",
    # -- b2 unit07 (negotiation)
    "term": "یک بند یا بخش توافق", "proposal": "پیشنهاد شرط‌های ممکن",
    "refusal": "رد کردن یک شرط",
    "concession": "امتیاز دادن، کوتاه آمدن از یک بخش موقف",
    "scope": "حجم یا محدودهٔ کار شامل‌شده",
    "charts": "نمودارها، نمایش تصویری معلومات", "agreement": "توافق",
    "reduced": "کم شد", "appendix": "ضمیمه", "follows": "بعداً می‌آیه",
    "push": "پس زدن", "clearly": "به‌روشنی",
    "offer": "پیشنهاد کردن", "executive": "اجرایی (خلاصهٔ اجرایی)",
    "priya": "پریا", "proposed": "طرح کرد", "marcus": "مارکوس",
    "outcome": "نتیجهٔ نهایی", "deliver": "تحویل دادن", "planned": "پلان شده",
    "risk": "به خطر انداختن",
    # -- b2 unit08 (synthesizing sources)
    "source": "منبع معلومات",
    "synthesize": "معلومات چند منبع را یکجا ساختن",
    "evaluate": "ارزیابی کدن، قوت چیزی را سنجیدن",
    "conflict": "تضاد یا اختلاف بین منبع‌ها",
    "judgment": "قضاوت دلیل‌دار دربارهٔ پشتوانه", "sources": "منبع‌ها",
    "demand": "تقاضا", "increased": "زیاد شد", "cause": "سبب",
    "operator": "شرکت ترانسپورتی", "includes": "شامل می‌کنه",
    "staffing": "کارمندیابی (کمبود کارمند)", "records": "سوابق",
    "supported": "پشتیبانی‌شده", "passenger": "مسافر (سروی مسافران)",
    "buses": "بس‌ها", "became": "شد", "common": "عام", "opened": "باز شد",
    "passengers": "مسافران", "route": "مسیر", "crowded": "پُر ازدحام",
    "b": "ب", "identifies": "مشخص می‌کنه",
    "shortages": "کمبودها", "caused": "سبب شد", "tessa": "تسا",
    "accounts": "روایت‌ها", "comments": "نظرها",
    "showing": "نشان دادن (شکل استمراری)",
})


# Local English POS classification for the 765 tokens the 52 newly-covered
# units introduce (a1 49-68, a2 30-34, b1 01-19, b2 01-08).
#
# WHY THIS IS HERE AND NOT IN _en_target_lexeme_common.py: that module is the
# SHARED classification surface for nl-en/fa-en/prs-en and is owned by the
# concurrent sibling lanes -- this pass was scoped to this file only, so the
# entries live here as a FALLBACK. `_classify()` below resolves the shared
# EN_POS FIRST and only consults this dict for tokens the shared module does
# not know yet, so the moment the shared module gains a token, its
# classification wins and the two can never diverge in the DB (`Lexeme`'s
# natural key is (course, language_code, token, part_of_speech) -- two
# different POS values for one token would create a duplicate row, which is
# exactly what deferring to the shared module prevents).
#
# The token SET is not a judgement call: it is exactly the union of
# `introduced_tokens` across the 52 realization files, so it is identical to
# what the nl-en/fa-en lanes must cover for the same shared English units.
# Only the Dari gloss below is this lane's own.
EN_POS_EXTRA: dict[str, str] = {
    # -- a1 unit49 (sorting household waste)
    "waste": "noun", "glass": "noun", "paper": "noun", "collection": "noun",
    "recycling": "noun", "food": "noun", "jar": "noun", "bins": "noun",
    "tuesdays": "noun", "fridays": "noun", "correctly": "adverb",
    "buildings": "noun", "kinds": "noun", "practicing": "verb",
    "afterward": "adverb", "stopped": "verb", "showed": "verb",
    "sorts": "verb", "explained": "verb",
    # -- a1 unit50 (staying in accommodation)
    "staying": "verb", "beds": "noun", "included": "adjective", "key": "noun",
    "under": "preposition", "downstairs": "adverb", "guesthouse": "noun",
    "mountains": "noun", "november": "noun", "14th": "adjective",
    "16th": "adjective", "picture": "noun", "view": "noun", "window": "noun",
    "stayed": "verb", "cooked": "verb", "himself": "pronoun", "loved": "verb",
    # -- a1 unit51 (at the pharmacy)
    "syrup": "noun", "runny": "adjective", "nose": "noun", "hours": "noun",
    "tablets": "noun", "felt": "verb", "walked": "verb", "listened": "verb",
    "symptoms": "noun", "recommended": "verb", "box": "noun",
    "tissues": "noun",
    # -- a1 unit52 (personal care / the hairdresser)
    "visit": "verb", "salon": "noun", "washed": "verb", "looked": "verb",
    "met": "verb",
    # -- a1 unit53 (renting a bike)
    "costs": "verb", "we'd": "pronoun", "bikes": "noun", "river": "noun",
    "invited": "verb", "neither": "pronoun", "owned": "verb",
    "rental": "noun", "needed": "verb", "enjoying": "verb", "join": "verb",
    # -- a1 unit54 (the laundromat)
    "machine": "noun", "broken": "adjective", "clothes": "noun",
    "machines": "noun", "cycle": "noun", "pick": "verb", "broke": "verb",
    "down": "particle", "attendant": "noun", "talked": "verb", "kept": "verb",
    "probably": "adverb", "fixed": "verb",
    # -- a1 unit55 (the swimming pool)
    "enter": "verb", "swim": "verb", "cap": "noun", "wear": "verb",
    "read": "verb", "watches": "verb", "lockers": "noun", "tickets": "noun",
    "caps": "noun", "required": "adjective", "entrance": "noun",
    "dollar": "noun", "coin": "noun", "cool": "verb", "sign": "noun",
    "listed": "verb", "bags": "noun", "swam": "verb", "try": "verb",
    "diving": "noun", "board": "noun",
    # -- a1 unit56 (ordering in a restaurant)
    "chicken": "noun", "meal": "noun", "sit": "verb", "nineteen": "noun",
    "pizza": "noun", "juice": "noun", "brought": "verb", "ordered": "verb",
    "excellent": "adjective",
    # -- a1 unit57 (at the cinema)
    "popular": "adjective", "film": "noun", "start": "verb", "liked": "verb",
    "sixteen": "noun", "schedule": "noun", "star": "noun",
    "journey": "noun", "7:00": "symbol", "$8": "symbol", "race": "noun",
    "5:00": "symbol", "$10": "symbol", "9:00": "symbol", "$6": "symbol",
    "cashier": "noun", "explorers": "noun",
    # -- a1 unit58 (visiting a museum)
    "enjoyed": "verb", "paintings": "noun", "city": "noun",
    "adult": "adjective", "current": "adjective", "town": "noun",
    "square": "noun", "sunset": "noun",
    # -- a1 unit59 (basic banking / the ATM)
    "pin": "noun", "4:00": "symbol", "limit": "noun", "$100": "symbol",
    "accepted": "verb", "quick": "adjective", "entered": "verb",
    # -- a1 unit60 (invitations)
    "6:00": "symbol", "18": "symbol", "wrote": "verb",
    # -- a1 unit61 (apologies and excuses)
    "starts": "verb", "waiting": "verb", "note": "noun", "3:00": "symbol",
    "apology": "noun", "classroom": "noun",
    # -- a1 unit62 (phone calls)
    "sound": "noun", "clear": "adjective",
    # -- a1 unit63 (asking for help)
    "carried": "verb",
    # -- a1 unit64 (compliments)
    "being": "verb", "compliment": "noun",
    # -- a1 unit65 (returns and exchanges)
    "larger": "adjective", "offered": "verb", "exchanged": "verb",
    # -- a1 unit66 (describing symptoms)
    "hurts": "verb",
    # -- a1 unit67 (family news)
    "must": "verb", "shared": "verb",
    # -- a1 unit68 (borrowing and lending)
    "lending": "noun", "leila's": "pronoun", "share": "verb", "lent": "verb",
    "remember": "verb",
    # -- a2 unit30 (a job interview)
    "social": "adjective", "media": "noun", "marketing": "noun",
    "strengths": "noun", "path": "proper_noun", "looking": "verb",
    "coordinator": "noun", "requirements": "noun", "writing": "noun",
    "immediately": "adverb", "interview": "noun", "deadlines": "noun",
    "managed": "verb", "questions": "noun", "role": "noun",
    "typical": "adjective",
    # -- a2 unit31 (a travel disruption)
    "signal": "noun", "delayed": "adjective", "5:15": "symbol",
    "5:30": "symbol", "station": "noun", "tracks": "noun",
    # -- a2 unit32 (online habits)
    "messaging": "adjective", "useful": "adjective", "touch": "noun",
    "notifications": "noun", "sharing": "verb", "spend": "verb",
    "thing": "noun",
    # -- a2 unit33 (a weekly schedule)
    "weekdays": "noun", "email": "noun", "online": "adjective",
    "mondays": "noun", "wednesdays": "noun",
    # -- a2 unit34 (a shopping complaint)
    "policy": "noun", "blender": "noun", "working": "verb", "30": "symbol",
    "refunded": "verb", "thirty-five": "noun",
    # -- a2 unit35 (a prescription) --- POS ported from nl-en EN_EXTRA
    "dose": "noun", "refill": "noun", "refills": "noun", "side": "noun",
    "effects": "noun", "shouldn't": "verb",
    # -- a2 unit36 (correcting a document)
    "certificate": "noun", "spelled": "verb", "copy": "noun",
    "passport": "noun", "mistakes": "noun", "registration": "noun",
    "correction": "noun", "corrected": "verb", "reference": "noun",
    "3092": "symbol",
    # -- a2 unit37 (video calls)
    "microphone": "noun", "connection": "noun", "mute": "verb",
    "face": "noun", "calls": "noun", "headphones": "noun", "asks": "verb",
    "question": "noun", "classmates": "noun", "speaking": "verb",
    # -- a2 unit38 (a repair visit)
    "leak": "noun", "won't": "verb", "rescheduled": "verb", "9am": "symbol",
    "11am": "symbol",
    # -- a2 unit39 (after the interview)
    "contract": "noun", "salary": "noun", "accept": "verb",
    "interested": "adjective",
    # -- a2 unit40 (an online order problem)
    "delivery": "noun", "parcel": "noun", "lamp": "noun", "8154": "symbol",
    # -- b1 unit01 (necessity and obligation)
    "finish": "verb", "earlier": "adverb", "forgot": "verb", "renew": "verb",
    "membership": "noun", "set": "verb", "reminder": "noun", "done": "verb",
    # -- b1 unit02 (past and present ability)
    "able": "adjective", "manage": "verb", "person": "noun",
    "licenses": "noun", "changed": "verb", "hers": "pronoun",
    "wasn't": "verb", "save": "verb",
    # -- b1 unit03 (real and past hypotheticals)
    "rains": "verb", "known": "verb", "signed": "verb", "checks": "verb",
    # -- b1 unit04 (agreeing and disagreeing)
    "easily": "adverb", "disagrees": "verb", "believes": "verb",
    "seeing": "verb", "each": "adjective", "other's": "pronoun",
    "important": "adjective", "saves": "verb",
    # -- b1 unit05 (workplace updates)
    "responsible": "adjective", "technical": "adjective", "sales": "noun",
    "gives": "verb", "expects": "verb", "tells": "verb", "truth": "noun",
    "delays": "noun", "review": "verb", "numbers": "noun",
    "correct": "adjective", "notes": "noun", "appreciate": "verb",
    # -- b1 unit06 (telling a past story)
    "flat": "adjective", "tire": "noun", "pull": "verb", "driving": "verb",
    "pulled": "verb", "helped": "verb", "word": "noun", "suddenly": "adverb",
    "happened": "verb",
    # -- b1 unit07 (real future conditions)
    "present": "adjective", "tense": "noun", "real": "adjective",
    "future": "noun", "backup": "adjective", "plan": "noun",
    "conference": "noun", "joins": "verb", "cannot": "verb",
    # -- b1 unit08 (sequencing future events)
    "lock": "verb", "clause": "noun", "locks": "verb",
    "careful": "adjective", "routine": "noun", "hands": "noun",
    "clears": "verb",
    # -- b1 unit09 (reported speech)
    "speech": "noun", "reported": "adjective", "summary": "noun",
    "enough": "adjective", "full": "adjective", "reply": "verb",
    # -- b1 unit10 (expressing purpose)
    "design": "noun", "money": "noun", "english": "noun",
    "vocabulary": "noun", "verb": "noun", "goals": "noun",
    "practices": "verb", "updates": "noun", "descriptions": "noun",
    "program": "noun", "saving": "verb",
    # -- b1 unit11 (unreal hypotheticals and regret)
    "rather": "adverb", "chance": "noun", "unreal": "adjective",
    "situation": "noun", "joined": "verb", "timing": "noun", "saved": "verb",
    # -- b1 unit12 (concession)
    "distractions": "noun", "valid": "adjective", "followed": "verb",
    "noun": "noun", "sentence": "noun", "period": "noun",
    "semicolon": "noun", "builds": "verb", "misses": "verb",
    "colleagues": "noun", "during": "preposition", "breaks": "noun",
    "noise": "noun", "alone": "adverb", "matters": "verb",
    "preferences": "noun",
    # -- b1 unit13 (relative clauses)
    "approved": "verb", "colleague": "noun", "sits": "verb", "leads": "verb",
    "projects": "noun", "defining": "adjective", "relative": "adjective",
    "commas": "noun", "exactly": "adverb", "mean": "verb",
    "non-defining": "adjective", "extra": "adjective", "information": "noun",
    "identified": "verb", "easier": "adjective", "fifth": "adjective",
    "floor": "noun", "eats": "verb", "finishing": "verb",
    "has already": "verb", "woman": "noun", "designer": "noun",
    "logo": "noun", "won": "verb", "award": "noun", "ours": "pronoun",
    "explains": "verb",
    # -- b1 unit14 (professional communication)
    "possibly": "adverb", "formal": "adjective", "workplace": "noun",
    "requests": "noun", "softened": "adjective", "conditional": "adjective",
    "command": "noun", "forms": "noun", "polite": "adjective",
    "budget": "noun", "hope": "verb", "tomorrow's": "pronoun",
    "latest": "adjective", "client": "noun", "best": "noun",
    "advance": "noun", "request": "noun", "updated": "adjective",
    # -- b1 unit15 (making a complaint)
    "product": "noun", "written": "adjective", "complaint": "noun",
    "parts": "noun", "specific": "adjective", "resolution": "noun",
    "chair": "noun", "dear": "adjective", "wheel": "noun", "proceed": "verb",
    "calling": "verb",
    # -- b1 unit16 (giving advice)
    "closer": "adjective", "asking": "verb", "suggestions": "noun",
    "hypothetical": "noun", "recommendation": "noun", "softer": "adjective",
    "suggestion": "noun", "stronger": "adjective", "depending": "verb",
    "top": "noun", "leading": "verb", "seem": "verb", "handle": "verb",
    "solid": "adjective",
    # -- b1 unit17 (expressing regret)
    "participle": "noun", "happen": "verb", "missed": "verb", "end": "noun",
    "true": "adjective",
    # -- b1 unit18 (future plans)
    "months": "noun", "continuous": "adjective", "agreed": "adjective",
    "decision": "noun", "steps": "noun", "completely": "adverb",
    "predicts": "verb", "agrees": "verb", "exciting": "adjective",
    # -- b1 unit19 (summarizing)
    "words": "noun", "covered": "verb", "phrase": "noun", "points": "noun",
    "keeping": "verb", "highlight": "verb", "single": "adjective",
    "separately": "adverb", "original": "adjective", "article": "noun",
    "communication": "noun", "examples": "noun", "background": "noun",
    "messages": "noun", "guessing": "verb", "ideas": "noun",
    # -- b2 unit01 (argumentation)
    "risks": "noun", "supports": "verb", "moving": "verb",
    "forward": "adverb", "strongest": "adjective", "survey": "noun",
    "results": "noun", "consistent": "adjective", "concern": "noun",
    "data": "noun", "direction": "noun", "defended": "adjective",
    "moves": "noun", "state": "verb", "acknowledge": "verb",
    "opposing": "adjective", "phrases": "noun", "reasonable": "adjective",
    "conceding": "verb", "argues": "verb", "hybrid": "adjective",
    "improves": "verb", "lowering": "verb", "performance": "noun",
    "employees": "noun", "teams": "noun", "less": "adverb",
    "likely": "adjective", "may": "verb", "suffer": "verb",
    "acknowledges": "verb", "delivered": "verb", "scores": "noun",
    "slightly": "adverb", "higher": "adjective", "concludes": "verb",
    "benefits": "noun", "managers": "noun", "weaker": "adjective",
    "support": "verb", "routines": "noun", "abandon": "verb",
    # -- b2 unit02 (speculation and deduction)
    "overlap": "verb", "explanation": "noun", "tentative": "adjective",
    "server": "noun", "gone": "verb", "overnight": "adverb",
    "generated": "verb", "failed": "verb", "permission": "noun",
    "possibility": "noun", "uncertain": "adjective",
    "monitoring": "adjective", "page": "noun", "blank": "adjective",
    "suggests": "verb", "explain": "verb", "finance": "noun",
    "missing": "verb", "dashboard": "noun", "rebuilt": "verb",
    "certain": "adjective", "pure": "adjective", "none": "pronoun",
    "consequences": "noun", "expect": "verb", "guess": "noun",
    "limited": "adjective",
    # -- b2 unit03 (hedging and emphasis)
    "extent": "noun", "create": "verb", "worries": "verb",
    "timeline": "noun", "adjusted": "verb", "attention": "noun",
    "feedback": "noun", "positive": "adjective", "carefully": "adverb",
    "qualified": "adjective", "avoids": "verb", "sounding": "verb",
    "absolute": "adjective", "limits": "verb", "accepting": "verb",
    "construction": "noun", "speakers": "noun", "principle": "noun",
    "language": "noun", "shows": "verb", "levels": "noun",
    "commitment": "noun", "cautious": "adjective", "saying": "verb",
    "fully": "adverb", "workable": "adjective", "clearer": "adjective",
    "quality": "noun", "adds": "verb", "approval": "noun", "step": "noun",
    "conditions": "noun", "creates": "verb",
    # -- b2 unit04 (narrative time)
    "interrupted": "verb", "equipment": "noun", "power": "noun",
    "volunteers": "noun", "setting": "verb", "chairs": "noun",
    "simple": "adjective", "events": "noun", "moment": "noun",
    "simon": "proper_noun", "strict": "adjective",
    "chronological": "adjective", "expected": "verb", "crew": "noun",
    "lights": "noun", "through": "preposition", "event": "noun",
    # -- b2 unit05 (register)
    "grateful": "adjective", "scheduling": "adjective", "content": "noun",
    "shift": "verb", "nina": "proper_noun", "clinic": "noun",
    "texts": "noun", "stays": "verb", "level": "noun", "formality": "noun",
    # -- b2 unit06 (abstract opinions and values)
    "public": "adjective", "spaces": "noun", "qualification": "noun",
    "weight": "noun", "arguing": "verb", "silence": "noun",
    "businesses": "noun", "response": "noun", "directly": "adverb",
    "person's": "pronoun", "amara": "proper_noun", "protected": "verb",
    "activity": "noun", "accepts": "verb", "leo's": "pronoun",
    "harder": "adjective", "survive": "verb", "belongs": "verb",
    "stance": "noun", "unlimited": "adjective", "restrictions": "noun",
    "protect": "verb", "shaped": "verb", "profit": "noun",
    "comfort": "noun",
    # -- b2 unit07 (negotiation)
    "agreement": "noun", "reduced": "verb", "appendix": "noun",
    "follows": "verb", "push": "verb", "clearly": "adverb", "offer": "verb",
    "executive": "adjective", "priya": "proper_noun", "proposed": "verb",
    "marcus": "proper_noun", "outcome": "noun", "deliver": "verb",
    "planned": "verb", "risk": "verb",
    # -- b2 unit08 (synthesizing sources)
    "sources": "noun", "demand": "noun", "increased": "verb",
    "cause": "noun", "operator": "noun", "includes": "verb",
    "staffing": "noun", "records": "noun", "supported": "adjective",
    "passenger": "adjective", "buses": "noun", "became": "verb",
    "common": "adjective", "opened": "verb", "passengers": "noun",
    "route": "noun", "crowded": "adjective", "b": "symbol",
    "identifies": "verb", "shortages": "noun", "caused": "verb",
    "tessa": "proper_noun", "accounts": "noun", "comments": "noun",
    "showing": "verb",
    # -- vocabulary teaching cards whose Dari gloss was harvested verbatim from
    # the prs-en overlay's own `teaching.<key>.gloss` (see the gloss block
    # below); their POS still has to be classified here.
    "sort": "verb", "bin": "noun", "recycle": "verb", "hotel": "noun",
    "reservation": "noun", "check-out": "noun", "pharmacist": "noun",
    "haircut": "noun", "hairdresser": "noun", "trim": "verb",
    "shorter": "adjective", "style": "noun", "rent": "verb", "hour": "noun",
    "helmet": "noun", "laundromat": "noun", "dryer": "noun",
    "quarters": "noun", "detergent": "noun", "load": "noun",
    "locker": "noun", "rules": "noun", "lifeguard": "noun",
    "waiter": "noun", "table": "noun", "order": "verb", "cinema": "noun",
    "showtime": "noun", "seat": "noun", "screen": "noun", "popcorn": "noun",
    "museum": "noun", "exhibition": "noun", "sculpture": "noun",
    "guide": "noun", "atm": "noun", "invitation": "noun", "picnic": "noun",
    "traffic": "noun", "mistake": "noun", "voicemail": "noun",
    "carry": "verb", "heavy": "adjective", "shelf": "noun",
    "lovely": "adjective", "kind": "adjective", "smile": "noun",
    "exchange": "verb", "refund": "noun", "symptom": "noun", "news": "noun",
    "baby": "noun", "proud": "adjective", "lend": "verb", "charger": "noun",
    "experience": "noun", "position": "noun", "availability": "noun",
    "strength": "noun", "requirement": "noun", "resume": "noun",
    "deadline": "noun", "delay": "noun", "cancelled": "adjective",
    "alternative": "noun", "notification": "noun", "weekday": "noun",
    "defective": "adjective", "task": "noun", "license": "noun",
    "system": "noun", "disagree": "verb", "believe": "verb",
    "reason": "noun", "focus": "verb", "respect": "verb",
    "stranger": "noun", "mechanic": "noun", "unless": "particle",
    "condition": "noun", "result": "noun", "goal": "noun",
    "improve": "verb", "prepare": "verb", "opportunity": "noun",
    "regret": "noun", "sooner": "adverb", "confident": "adjective",
    "although": "particle", "despite": "preposition", "however": "adverb",
    "convince": "verb", "flexibility": "noun", "teamwork": "noun",
    "whose": "pronoun", "approve": "verb", "agenda": "noun",
    "complain": "verb", "damaged": "adjective", "replacement": "noun",
    "resolve": "verb", "issue": "noun", "advice": "noun",
    "overwhelmed": "adjective", "prioritize": "verb", "workload": "noun",
    "decline": "verb", "hindsight": "noun", "procrastinate": "verb",
    "arrangement": "noun", "intention": "noun", "prediction": "noun",
    "detail": "noun", "condensed": "adjective", "claim": "noun",
    "evidence": "noun", "counterargument": "noun", "rebut": "verb",
    "concede": "verb", "outweigh": "verb", "retention": "noun",
    "collaboration": "noun", "deduction": "noun", "guesswork": "noun",
    "outage": "noun", "consequence": "noun", "hedge": "verb",
    "qualify": "verb", "emphasize": "verb", "broadly": "adverb",
    "provided": "particle", "overall": "adverb", "foreground": "noun",
    "prior": "adjective", "interrupt": "verb", "ongoing": "adjective",
    "chronology": "noun", "venue": "noun", "register": "noun",
    "casual": "adjective", "audience": "noun", "institution": "noun",
    "stiff": "adjective", "appropriate": "adjective", "value": "noun",
    "fairness": "noun", "convenience": "noun", "transparent": "adjective",
    "commercial": "adjective", "term": "noun", "proposal": "noun",
    "refusal": "noun", "concession": "noun", "scope": "noun",
    "charts": "noun", "source": "noun", "synthesize": "verb",
    "evaluate": "verb", "conflict": "noun", "judgment": "noun",
}


PRS_UNIT_GLOSS_OVERRIDES: dict[tuple[str, str], str] = {
    # a2_unit36 teaches the VERB ("Could you correct it?"); bare `correct`
    # otherwise resolves to the adjective ("درست"). Added 2026-08-05.
    ("a2_unit36_document_correction", "correct"): "اصلاح کردن؛ درست کردن",
    # a2_unit35 (prescription): pill sense, matching the plural گولی‌ها (not
    # the computer تبلت). Added 2026-08-05 (native-gloss review).
    ("a2_unit35_prescription", "tablet"): "گولی",
    # a2_unit38 (repair visit): "leave the key with my neighbor" = entrust;
    # Dari ماندن (to put/leave with someone) + سپردن, not رفتن (to depart).
    ("a2_unit38_repair_visit", "leave"): "ماندن؛ سپردن",
    ("b1_unit05_workplace", "short"): "کوتاه/خلاصه",
    ("b1_unit10_purpose", "sound"): "نمودن/معلوم شدن",
    ("b1_unit10_purpose", "order"): "ترتیب",
    ("b2_unit01_argumentation", "sound"): "نمودن/معلوم شدن",
    ("b2_unit01_argumentation", "position"): "موقف",
    ("b2_unit01_argumentation", "like"): "مثل",
    ("b2_unit02_speculation", "run"): "اجرا شدن",
    ("b2_unit03_hedging_emphasis", "as"): "طوری که",
    ("b2_unit04_narrative_time", "order"): "ترتیب",
    ("b2_unit06_abstraction", "view"): "نظر",
    ("b2_unit08_synthesis", "period"): "مدت",
    # Wrong-sense per-unit glosses from the session9 prs-en practice review
    # (2026-10-19). The A1 first-introduction senses stay as they are
    # (next to = پهلوی, strong tea = تُند, how much = چقدر, that's all = بس).
    ("a2_unit30_job_interview", "next"): "بعدی؛ آینده",
    ("b1_unit01_necessity", "next"): "بعدی؛ آینده",
    ("b2_unit01_argumentation", "next"): "بعدی؛ آینده",
    ("a2_unit30_job_interview", "strong"): "قوی",
    ("b2_unit02_speculation", "strong"): "قوی",
    ("a2_unit29_maintenance", "much"): "زیاد؛ خیلی",
    ("b1_unit03_hypotheticals", "much"): "زیاد",
    ("b1_unit17_regret", "all"): "همه",
    ("b2_unit05_register", "all"): "همه",
    # "Of course" (البته): کورس (a study course) is the wrong sense here.
    ("a2_unit35_prescription", "course"): "البته (جزء یک عبارت)",
    ("b1_unit05_workplace", "course"): "البته (جزء یک عبارت)",
    # Added 2026-10-22 (fa-en/prs-en practice review rest)
    ("a1_unit07_food", "that's"): "این ... استه (مخفف)",
    ("a1_unit30_hobbies", "paint"): "نقاشی کردن",
    ("a1_unit30_hobbies", "paints"): "نقاشی می‌کنه (سوم‌شخص مفرد)",
    ("a1_unit43_colors", "bright"): "درخشان",
    ("a1_unit44_seasons", "find"): "پیدا کردن",
    ("a1_unit58_museum", "town"): "شهرک",
    ("a1_unit59_banking_basics", "balance"): "بیلانس حساب",
    ("a2_unit26_opinions", "idea"): "فکر",
    ("a2_unit31_travel_disruption", "train"): "قطار",
    ("a2_unit31_travel_disruption", "way"): "راه",
    ("a2_unit32_online_habits", "waste"): "ضایع کردن",
    ("a2_unit32_online_habits", "screen"): "صفحهٔ نمایش",
    ("a2_unit32_online_habits", "lot"): "مقدار زیاد",
    ("a2_unit34_shopping_complaint", "stopped"): "از کار افتاد",
}

PRS_UNIT_POS_OVERRIDES: dict[tuple[str, str], str] = {
    ("a2_unit36_document_correction", "correct"): "verb",
    ("b1_unit10_purpose", "sound"): "verb",
    ("b1_unit10_purpose", "order"): "noun",
    ("b2_unit01_argumentation", "sound"): "verb",
    ("b2_unit01_argumentation", "like"): "preposition",
    ("b2_unit04_narrative_time", "order"): "noun",
}


# Generated per-unit and per-lesson semantic tags, ported 2026-07-25 from
# backfill_lexemes_fa_en.py's identical mechanism after the polish wave
# measured that prs-en lexemes from ~a1_43 onward (and virtually all of
# B1/B2) carry no semantic tags at all — leaving every matching_pairs
# there stuck on bare part_of_speech pools (checkpoint-safe but
# course-wide off-theme in Endless Practice, unfixable pack-side). Two
# tags per token, e.g. `prs_en_a1_unit50_words` +
# `prs_en_a1_unit50_lesson03_words`; emitted ONLY on a token's first
# introduction (a re-used token must never receive a later unit's tag —
# its provenance lesson belongs to the earlier unit, which is exactly the
# silent checkpoint_unavailable cause the recipe calls defect #2). Purely
# additive: no shipped pack references these names, so no existing pool
# changes until a pack opts in.

# Grammar metalanguage taught as real tokens by B1/B2 grammar cards; they
# stay lexemes but are kept out of the generated tags so a pack can never
# build a vocabulary drill whose options are "noun"/"verb"/"clause".
METALANGUAGE_TOKENS = frozenset({
    "clause", "commas", "command", "conditional", "continuous", "defining",
    "direct", "form", "forms", "hypothetical", "noun", "non-defining",
    "participle", "past", "perfect", "period", "phrase", "present",
    "relative", "reported", "semicolon", "sentence", "simple", "speech",
    "tense", "unreal", "verb",
})

# Function words and proper nouns are excluded: a slot_gloss MC over proper
# nouns self-glosses, and matching over particles is not a vocabulary check.
TAGGABLE_POS = frozenset({"noun", "verb", "adjective", "adverb", "phrase"})


# Function words get their own per-lesson tag (2026-10-19, session9 prs-en
# practice review): lessons whose only new tokens are pronouns/prepositions/
# particles (a1_unit14 lesson04, a2_unit38 lesson04, b1_unit01 lesson01's
# "to") had no lesson tag at all, so their slots could only fall back to the
# whole level's function words. Kept separate from *_words so no vocabulary
# drill pool changes; a pack opts in by naming the new tag.
FUNCTION_POS = frozenset({"pronoun", "preposition", "particle"})


def _unit_semantic_tags(unit_stem, lesson_order, token, part_of_speech):
    if part_of_speech in FUNCTION_POS and all(
        character.isalpha() or character == "'" for character in token
    ):
        return [f"prs_en_{unit_stem}_lesson{lesson_order:02d}_function_words"]
    if part_of_speech not in TAGGABLE_POS or token in METALANGUAGE_TOKENS:
        return []
    if part_of_speech != "phrase" and not all(
        character.isalpha() or character in "-'" for character in token
    ):
        # Digits, currency marks, clock colons or attached punctuation:
        # real lexemes, poor slot candidates.
        return []
    return [
        f"prs_en_{unit_stem}_words",
        f"prs_en_{unit_stem}_lesson{lesson_order:02d}_words",
    ]


def _classify(files, level, specs):
    for unit_order, (realization_path, overlay_path) in enumerate(files, 1):
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
        overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
        teaching_overlays = overlay["teaching"]
        # "a1_unit49_waste_disposal" -> "a1_unit49": the stable per-unit
        # key the generated semantic tags are named after.
        unit_stem = "_".join(realization_path.stem.split("_")[:2])
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson["teaching"]:
                content_key = item["content_key"]
                for raw_token in item.get("introduced_tokens", []):
                    raw_key = raw_token.casefold().replace("’", "'")
                    token_key = normalize_en_token(raw_token)
                    lookup_key = raw_key if (
                        raw_key in EN_POS or raw_key in EN_POS_EXTRA
                    ) else token_key
                    # Shared classification WINS; EN_POS_EXTRA is only the
                    # local fallback for tokens the shared module has not
                    # taken over yet (see its comment above). Never the other
                    # way around: a token classified in both must resolve to
                    # ONE part_of_speech, or the (course, language_code,
                    # token, part_of_speech) lookup in main() misses and
                    # writes a duplicate Lexeme row.
                    part_of_speech = (
                        EN_POS.get(lookup_key) or EN_POS_EXTRA.get(lookup_key)
                    )
                    if part_of_speech is None:
                        raise ValueError(
                            f"missing English classification for {token_key!r} "
                            f"in _en_target_lexeme_common.py or EN_POS_EXTRA "
                            f"(lesson {lesson_key})"
                        )
                    token = en_token_display(raw_token, part_of_speech)
                    tags = en_agreement_tags(token_key)
                    # Keyed by (level, token) -- A1 and A2 are separate
                    # courses, so a bare token key would wrongly merge
                    # an A2 occurrence into an A1 spec already seen.
                    key = (level, token)
                    existing = specs.get(key)
                    if existing is None:
                        resolved_pos = PRS_UNIT_POS_OVERRIDES.get(
                            (realization_path.stem, lookup_key), part_of_speech
                        )
                        # ONLY on first introduction — see
                        # _unit_semantic_tags() above.
                        unit_tags = _unit_semantic_tags(
                            unit_stem, lesson_order, token, resolved_pos
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
                            "part_of_speech": resolved_pos,
                            "english_gloss": PRS_UNIT_GLOSS_OVERRIDES.get(
                                (realization_path.stem, lookup_key),
                                EN_TARGET_TO_PRS_GLOSS[lookup_key],
                            ).strip(EN_TOKEN_BOUNDARY_PUNCTUATION),
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
                realization_path.stem, lesson, teaching_overlays
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


def iter_specs():
    specs: dict[tuple[str, str], dict] = {}
    _classify(UNIT_FILES, "a1", specs)
    _classify(UNIT_FILES_A2, "a2", specs)
    _classify(UNIT_FILES_B1, "b1", specs)
    _classify(UNIT_FILES_B2, "b2", specs)
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
                    Course.source_language == "prs",
                    Course.target_language == "en",
                    Course.title == title,
                )
            )
            if course is None:
                if needed:
                    print(f"ERROR: prs-en {title!r} course must be imported first", file=sys.stderr)
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
