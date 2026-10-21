#!/usr/bin/env python3
"""Idempotently backfill reviewed en-fa A1 lexemes from units 1 and 2.

Needs both the app's DB settings/imports (in backend/) and this repo's
docs/content/ (at the repo root), which the backend Docker image alone
doesn't have — it only contains backend/. Run via docker compose from
backend/, mounting the full repo on top of the existing image/network/env:

    cd backend
    docker compose run --rm \
      -v "$(cd .. && pwd):/repo" \
      -e PYTHONPATH=/repo/backend \
      --entrypoint python \
      api /repo/scripts/backfill_lexemes.py

Add --dry-run to classify without touching the database. Running directly
on the host (`python ../scripts/backfill_lexemes.py` from backend/) only
works if your host Python has the backend's dependencies installed AND can
reach the DATABASE_URL in backend/.env — the docker compose form above is
the one that reliably matches how this actually gets deployed.

The realization's introduced_tokens are authoritative for Farsi. English
source lexemes are extracted from the corresponding reviewed teaching gloss,
then classified with the explicit POS sets below (no NLP dependency).
"""

from __future__ import annotations

import re
import sys
import argparse
import unicodedata
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

UNIT_FILES = (
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit01_greetings.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit02_introductions.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit03_numbers.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit04_family.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit05_places.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit06_food.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit07_weather.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit08_shopping.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit08.yaml",
    ),
    # Units 09-11 (Time / Dates / Routines), added 2026-07-07 by the
    # practice-content-gap-closing pass -- see docs/BUILD_LOG.md. This
    # closes the gap the A2-tuple comment above flagged ("the real
    # a1_unit09-12 content ... has NO lexeme classifier coverage in this
    # script at all"). Units 12-15 are a separate, parallel pass's lane
    # (not added here) -- re-read this file fresh before adding them so
    # the two passes don't clobber each other's tuple entries.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit09_time.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit10_dates.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit10.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit11_routines.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit11.yaml",
    ),
    # Units 12-15 (Plans / Past Events / Preferences / Comparisons), added
    # 2026-07-07 by the parallel practice-content-gap-closing pass (this
    # is the OTHER lane, appended after the 09-11 lane above landed first
    # -- re-read fresh immediately before any further edit here).
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit12_plans.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit13_past_events.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit14_preferences.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit14.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit15_comparisons.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit15.yaml",
    ),
    # Units 16-17 (Travel / Health), added 2026-07-07 by the en-fa
    # units-16-17 practice-authoring pass (this pack's own units grew from
    # 15 to 17 with zero prior Endless Practice coverage). Appended after
    # every prior lane's own tuple entries, per this file's own standing
    # re-read-fresh-before-editing convention.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit16_travel.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit16.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit17_health.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit17.yaml",
    ),
    # Units 18-19 (Work / Housing), added 2026-07-07 -- en-fa's own A1 pack
    # grew from 17 to 19 units with zero prior Endless Practice coverage.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit18_work.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit18.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit19_housing.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit19.yaml",
    ),
    # Unit 20 (Clothing), added 2026-07-09 by the en-fa overnight
    # units-20+ practice-authoring pass (real lesson content had grown to
    # a1_unit43+ with zero Endless Practice coverage past unit19 -- this
    # pass closes part of that gap). Re-read this file fresh before
    # appending any further unit here, per this file's own standing
    # convention -- other lanes may extend this same tuple concurrently.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit20_clothing.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit20.yaml",
    ),
    # Unit 21 (Money), added 2026-07-09, same overnight pass as unit20
    # above. Re-read this file fresh before appending any further unit
    # here, per this file's own standing convention.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit21_money.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit21.yaml",
    ),
    # Unit 22 (Phone), added 2026-07-09, same overnight pass as units
    # 20-21 above. Re-read this file fresh before appending any further
    # unit here, per this file's own standing convention.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit22_phone.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit22.yaml",
    ),
    # Unit 23 (Emotions), added 2026-07-09, same overnight pass as units
    # 20-22 above. Re-read this file fresh before appending any further
    # unit here, per this file's own standing convention.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit23_emotions.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit23.yaml",
    ),
    # Unit 24 (Hobbies), added 2026-07-09, same overnight pass as units
    # 20-23 above. Re-read this file fresh before appending any further
    # unit here, per this file's own standing convention.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit24_hobbies.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit24.yaml",
    ),
    # Units 25-30 (appearance / animals / sports / transportation /
    # technology / education), added 2026-07-22. THESE ARE INSERTED AT
    # THEIR REAL COURSE POSITIONS, NOT APPENDED -- read this before ever
    # appending to this tuple again:
    #
    # main() maps a tuple ENTRY'S 1-BASED INDEX onto the imported course's
    # `Unit.order`. The 2026-07-12 pass appended units 31-36 directly after
    # unit24, so they occupied INDEXES 25-30 and every lexeme they created
    # was written with `provenance_lesson_id` pointing at the real
    # a1_unit25-30 (appearance/animals/sports/transportation/technology/
    # education) lessons while its `provenance_lesson_content_key` string
    # correctly said "fa.a1.unit31...."-"fa.a1.unit36....". This is the
    # exact bug already documented for A2 units 09/10 in UNIT_FILES_A2
    # below, repeated three tuples later. Confirmed against the dev DB
    # 2026-07-22: Farsi A1 units 25-30 held 32-64 lexemes AND all 5-per-unit
    # practice templates belonging to units 31-36 (the practice importer
    # resolves its lesson via Lexeme.provenance_lesson_content_key, so the
    # templates followed the lexemes onto the wrong lessons), while units
    # 31-36 held zero of both -- i.e. unit checkpoints for 31-36 were dead
    # (`checkpoint_unavailable`) and checkpoints for 25-30 silently tested
    # the WRONG unit's vocabulary. Inserting 25-30 here restores the
    # index<->Unit.order identity for every A1 unit at once; main()'s
    # provenance refresh (see the comment there) repairs the already-written
    # rows on the next run.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit25_appearance.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit25.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit26_animals.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit26.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit27_sports.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit27.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit28_transportation.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit28.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit29_technology.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit29.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit30_education.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit30.yaml",
    ),
    # Units 31-36 (celebrations / household / neighborhood / post /
    # cooking / personality), added 2026-07-12 for the Endless Practice
    # coverage-extension batch. (Originally appended straight after unit24
    # -- see the units 25-30 block above for the index-misalignment bug that
    # caused and how it was fixed.)
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit31_celebrations.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit31.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit32_household.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit32.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit33_neighborhood.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit33.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit34_post.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit34.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit35_cooking.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit35.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit36_personality.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit36.yaml",
    ),
    # Units 37-57 (colors / seasons / emergencies / lost items /
    # appointments / library / waste disposal / accommodation / pharmacy /
    # personal care / bike rental / laundry / swimming pool / restaurant /
    # cinema / museum / concert / park / gym / beach / zoo), added
    # 2026-07-22 by the en-fa checkpoint-coverage pass. These 21 units
    # existed on disk and were already imported into the DB (Farsi A1 has 57
    # real units) but had zero lexeme classifier coverage in this script at
    # all, so `generate_checkpoint()` returned `checkpoint_unavailable` for
    # every one of them regardless of practice packs. Appended in strict
    # unit order immediately after unit36, keeping the tuple index ==
    # Unit.order identity the units 25-30 block above restored -- re-read
    # this tuple fresh before appending any further unit, per this file's
    # own standing convention, and NEVER append out of unit order.
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit37_colors.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit37.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit38_seasons.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit38.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit39_emergencies.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit39.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit40_lost_items.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit40.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit41_appointments.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit41.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit42_library.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit42.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit43_waste_disposal.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit43.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit44_accommodation.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit44.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit45_pharmacy.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit45.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit46_personal_care.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit46.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit47_bike_rental.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit47.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit48_laundry.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit48.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit49_swimming_pool.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit49.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit50_restaurant.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit50.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit51_cinema.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit51.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit52_museum.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit52.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit53_concert.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit53.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit54_park.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit54.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit55_gym.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit55.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit56_beach.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit56.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a1_unit57_zoo.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a1_unit57.yaml",
    ),
)

# A2 units live in a SEPARATE course row ("Farsi A2", not "Farsi A1") --
# `POST /admin/content/import` matches/creates courses by
# (source_language, target_language, title), and the A2 overlay declares
# `course.title: Farsi A2`, distinct from A1's `Farsi A1`. Real bug found
# live 2026-07-06/07 (Farsi Endless Practice QA pass, same root cause
# independently confirmed and already fixed in the sibling
# backfill_lexemes_en_prs.py/backfill_lexemes_prs_en.py pair): this used
# to be a single UNIT_FILES tuple with a2 units 9/10 appended at
# continuous positions 9/10, backfilled against ONE lookup of the
# "Farsi A1" course. Positions 9/10 in the real imported "Farsi A1"
# course are actually the native a1_unit09 (Time)/a1_unit10 (Dates)
# lessons (that course has grown to 12 real A1 units on disk since this
# script was last touched) -- so the lookup didn't crash, it silently
# resolved to the WRONG lesson: every A2 bureaucracy/opinions lexeme
# this session created had its `provenance_lesson_id` FK pointing at the
# Time/Dates lessons while its `provenance_lesson_content_key` STRING
# correctly said "fa.a2.unit09...."/"fa.a2.unit10....". Confirmed via a
# direct query against a genuinely fresh isolated DB. Net effect: the
# real "Farsi A2" course has zero Lexeme rows at all (`Lexeme.course_id`
# was always the A1 course's id), so its already-authored practice
# templates can never generate a single item -- Endless Practice for
# en-fa's A2 unit was completely dead, not degraded. Kept as its own
# tuple with LOCAL 1-based ordering (looked up against the "Farsi A2"
# course separately in main(), never mixed with UNIT_FILES' indices).
# NOTE: this only fixes A2 (units 9-10 of this tuple, i.e. bureaucracy/
# opinions). The real a1_unit09-12 (Time/Dates/Routines/Plans) content
# now shipped inside the actual "Farsi A1" course has NO lexeme
# classifier coverage in this script at all (added to lesson content
# after this script was last extended) -- a separate, larger
# content-authoring gap (new POS/register/agreement-tag data for ~4
# units of vocabulary), flagged in docs/BUILD_LOG.md rather than
# freehanded here.
UNIT_FILES_A2 = (
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit09_bureaucracy.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit10_opinions.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit10.yaml",
    ),
    # Units 11-18 (banking / doctor / maintenance / job interview / travel
    # disruption / online habits / weekly schedule / shopping complaint),
    # added 2026-07-11 -- these 8 units existed on disk and were already
    # imported into the DB but had zero lexeme classifier coverage in this
    # script at all, so Endless Practice for en-fa's A2 course beyond
    # unit10 was completely dead (same root cause already documented above
    # for units 9-10 before THEY were added). Re-read this tuple fresh
    # before appending any further unit here, per this file's own standing
    # convention -- other lanes may extend it concurrently.
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit11_banking.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit11.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit12_doctor.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit13_maintenance.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit14_job_interview.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit14.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit15_travel_disruption.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit15.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit16_online_habits.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit16.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit17_weekly_schedule.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit17.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/a2_unit18_shopping_complaint.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/a2_unit18.yaml",
    ),
)

# B1 units live in a THIRD, separate course row ("Farsi B1", confirmed by
# reading this pack's own en-fa/b1_unit0N.yaml `course.title` front-matter
# rather than assuming the "Farsi A1"/"Farsi A2" naming pattern continues),
# added 2026-07-11. These 6 units (necessity/abilities/hypotheticals/
# debate/workplace/narrative) existed on disk and were already imported
# into the DB but had zero lexeme classifier coverage in this script at
# all -- same root cause already documented above for A2 units 9-10/11-18
# before THEY were added: Endless Practice for en-fa's entire B1 course was
# completely dead (zero Lexeme rows, so its practice templates, if any, can
# never generate an item). Kept as its own tuple with LOCAL 1-based
# ordering, looked up against the "Farsi B1" course separately in main(),
# never mixed with UNIT_FILES/UNIT_FILES_A2's indices -- same pattern as
# UNIT_FILES_A2 itself.
UNIT_FILES_B1 = (
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit01_necessity.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit02_abilities.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit03_hypotheticals.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit04_debate.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit05_workplace.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit06_narrative.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit06.yaml",
    ),
    # Units 07-11 ("second wave": wishes and regret / nuanced debate /
    # professional meetings / relative clauses / reported speech), added
    # 2026-07-11 (B1 units 07-11 backfill pass) -- these 5 units existed on
    # disk and were already imported into the DB but had zero lexeme
    # classifier coverage in this script at all, same root cause already
    # documented above for units 01-06 before THEY were added. Re-read this
    # tuple fresh before appending any further unit here, per this file's
    # own standing convention -- other lanes may extend it concurrently.
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit07_wishes_and_regret.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit08_nuanced_debate.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit08.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit09_professional_meetings.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit10_relative_clauses.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit10.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit11_reported_speech.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit11.yaml",
    ),
    # Units 12-16 (real conditions / time clauses / reported messages /
    # purpose clauses / goals and plans), added 2026-07-22 by the en-fa
    # checkpoint-coverage pass -- confirmed at zero lexemes against the dev
    # DB (Farsi B1 units 12-16 held 0 rows), same root cause already
    # documented for units 01-06 and 07-11 before THEY were added. Appended
    # in strict unit order; the tuple index must stay == Unit.order.
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit12_real_conditions.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit13_time_clauses.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit14_reported_messages.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit14.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit15_purpose_clauses.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit15.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b1_unit16_goals_and_plans.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b1_unit16.yaml",
    ),
)
# B2 units 01-08 (argumentation / speculation / nuance / narrative /
# register / abstraction / negotiation / synthesis) live in a FOURTH,
# separate course row ("Farsi B2", confirmed from every en-fa/b2_unit0N.yaml
# overlay's own `course.title`). Same pattern as UNIT_FILES_A2/_B1: indices
# are this tuple's own 1-based ordering, looked up against the "Farsi B2"
# course separately in main(). Added 2026-10-19 to give the B2 checkpoints
# lexemes at all (before this, en-fa B2 had zero lexeme rows, so every B2
# unit checkpoint returned checkpoint_unavailable regardless of packs).
UNIT_FILES_B2 = (
    (
        REPO_ROOT / "docs/content/realizations/fa/b2_unit01_argumentation.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b2_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b2_unit02_speculation.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b2_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b2_unit03_nuance.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b2_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b2_unit04_narrative.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b2_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b2_unit05_register.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b2_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b2_unit06_abstraction.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b2_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b2_unit07_negotiation.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b2_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/fa/b2_unit08_synthesis.yaml",
        REPO_ROOT / "docs/content/overlays/en-fa/b2_unit08.yaml",
    ),
)
EN_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’/-][A-Za-z]+)*")

# Atomic glosses are intentionally explicit. A teaching-card gloss often
# describes a whole phrase or dialogue and must never be copied onto each
# introduced token (e.g. خواهش is not independently "you're welcome").
FA_GLOSSES = {
    "س": "s", "ل": "l", "ا": "a / ā", "م": "m", "ن": "n", "ت": "t",
    "ش": "sh", "چ": "ch", "ی": "y / long i", "ه": "h", "ک": "k",
    "گ": "g", "ج": "j", "د": "d", "ر": "r", "ف": "f", "و": "v / o / u",
    "ب": "b", "خ": "kh", "ز": "z", "سلام": "hello", "صبح": "morning",
    "بخیر": "good; well", "عصر": "afternoon / evening", "خداحافظ": "goodbye",
    "ممنون": "thank you", "خواهش": "request; kindness", "می‌کنم": "I do",
    "حالتون": "your condition (polite)", "چطوره": "how is it?", "خوبم": "I'm well",
    "روز": "day", "شب": "night", "خوش": "pleasant; happy", "آمدید": "you came (polite)",
    "به": "to", "امید": "hope", "دیدار": "meeting", "فعلاً": "bye for now",
    "خوبی": "good", "داشته": "having", "باشید": "be (polite)", "چطوری": "how are you? (informal)",
    "تو": "you (informal singular)", "خیلی": "very", "بد": "bad", "نیستم": "I am not",
    "شما": "you (polite / plural)", "چطور": "how", "چای": "tea", "بفرمایید": "please; go ahead",
    "لطف": "kindness", "دارید": "you have (polite)", "زحمت": "trouble", "نکشید": "do not take (polite)",
    "از": "from; of", "تعارف": "Iranian politeness convention", "علی": "Ali", "نرگس": "Narges",
    "من": "I", "هستم": "I am", "آشنایی": "acquaintance; meeting", "با": "with",
    "خوشوقتم": "I am pleased", "هم": "also", "همین‌طور": "likewise", "داخل": "inside",
    "ولی": "but", "باید": "must", "بروم": "I go", "اسم": "name", "سارا": "Sara",
    "است": "is", "اسمم": "my name", "ساراست": "is Sara", "چیه": "what is it?",
    "اسمت": "your name (informal)", "او": "he / she", "هستی": "you are (informal)",
    "هست": "is; exists", "ایرانی": "Iranian", "ایرانیه": "is Iranian (spoken)",
    "ایران": "Iran", "انگلیس": "England", "انگلیسی": "English", "فرانسه": "France",
    "فرانسوی": "French", "کشور": "country", "ملیت": "nationality", "اهل": "from; originally of",
    "کجا": "where", "هستید": "you are (polite standard)", "هستین": "you are (polite spoken)",
    "کجایی": "where are you from? (informal)", "ایرانی‌ام": "I am Iranian", "ببخشید": "excuse me",
    "اینجا": "here", "کلاس": "class", "فارسیه": "is Farsi (spoken)", "بله": "yes",
    "مینا": "Mina",
    # Unit 3 (numbers)
    "عدد": "number", "صفر": "zero", "یک": "one", "دو": "two", "سه": "three",
    "چهار": "four", "پنج": "five", "شش": "six", "هفت": "seven", "هشت": "eight",
    "نه": "nine", "ده": "ten", "یازده": "eleven", "دوازده": "twelve",
    "سیزده": "thirteen", "چهارده": "fourteen", "پانزده": "fifteen",
    "شانزده": "sixteen", "هفده": "seventeen", "هجده": "eighteen",
    "نوزده": "nineteen", "بیست": "twenty", "سی": "thirty", "چهل": "forty",
    "پنجاه": "fifty", "شصت": "sixty", "هفتاد": "seventy", "هشتاد": "eighty",
    "نود": "ninety", "و": "and (links tens + units)", "شماره": "number (serial/phone)",
    "تلفن": "telephone", "تلفنتون": "your telephone (polite)", "چنده": "how much is it? (spoken)",
    "سال": "year", "چند": "how many", "سالته": "how old are you? (informal, lit. 'your-year-is')",
    "سالمه": "I am ... years old (lit. 'my-year-is')", "تا": "counting classifier (between a number and a noun)",
    "سیب": "apple", "کتاب": "book", "می‌خوام": "I want", "قیمت": "price",
    "تومن": "toman (currency unit)", "هزار": "thousand", "این": "this",
    "تومنه": "is ... toman (spoken)", "باهم": "together", "فارسی": "Farsi / Persian",
    "تمرین": "practice", "کنیم": "let's do (subjunctive, we)", "تلفنت": "your telephone (informal)",
    "باشه": "okay", "حتماً": "certainly", "شماره‌ام": "my number", "هشته": "is eight (spoken)",
    "صبر": "wait (noun)", "کن": "do (imperative)", "بنویسم": "let me write it down (subjunctive)",
    "درسته": "that's right", "آره": "yeah", "یکه": "is one (spoken)", "فردا": "tomorrow",
    "زنگ": "call / ring (noun)", "می‌زنم": "I make (a call)", "بهت": "to you (informal)",
    # Unit 4 (family)
    "مادر": "mother", "مامان": "mom", "پدر": "father", "بابا": "dad",
    "برادر": "brother", "خواهر": "sister", "مثل": "like; similar to",
    "خودمونی": "casual; informal", "دارم": "I have", "ندارم": "I don't have",
    "بزرگه": "is big (spoken)", "خانواده‌ی": "family of (with ezafe connector)",
    "ما": "we / us", "کوچیکه": "is small (spoken)", "پدربزرگ": "grandfather",
    "مادربزرگ": "grandmother", "عمو": "uncle (father's brother)", "عمه": "aunt (father's sister)",
    "دایی": "uncle (mother's brother)", "خاله": "aunt (mother's sister)", "طرف": "side (of family)",
    "پدرن": "are on the father's side (spoken)", "مادرن": "are on the mother's side (spoken)",
    "دارید": "you have (polite)", "داری": "you have (informal)",
    "نفرن": "are ... people (spoken)", "نفریم": "we are ... people (spoken)",
    "چهار": "four", "شوهر": "husband", "زن": "wife / woman", "متأهل": "married",
    "متأهلین": "are you married? (polite, spoken contraction)", "مجرد": "single (unmarried)",
    "مجردم": "I am single", "متأهلم": "I am married", "نوه": "grandchild", "برادرم": "my brother",
    "متأهله": "is married (spoken)", "پسر": "son", "داره": "he/she has (spoken)",
    "عکس": "photo", "خانواده‌ته": "is your family('s) (spoken)", "مامانمه": "is my mom (spoken)",
    "باباهم": "is my dad too (spoken)", "آقا": "man / mister", "کیه": "who is it? (spoken)",
    "داداشمه": "he's my brother (spoken)", "داداش": "brother (affectionate/everyday)",
    "برعکسه": "is the opposite (spoken)", "پس": "so; then", "شلوغه": "is crowded/lively (spoken)",
    "دارد": "he/she has (formal)", "ندارد": "he/she doesn't have (formal)",
    "نداره": "he/she doesn't have (spoken)", "است": "is (formal)",
    "مامانم": "my mom", "بابام": "my dad", "داداشم": "my brother",
    # Unit 5 (places and directions), added 2026-07-06.
    "هتل": "hotel", "رستوران": "restaurant", "دستشویی": "restroom",
    "اونجا": "there", "کجاست": "where is (it)?", "سمت": "side",
    "راست": "right", "چپ": "left", "راسته": "it's on the right (spoken)",
    "چپه": "it's on the left (spoken)", "مستقیم": "straight ahead",
    "برید": "go (polite)", "بعد": "after that; then", "یه": "a; an (spoken)",
    "کنار": "next to; beside", "آزادی": "Azadi (freedom; hotel name)",
    "همون": "that same one (spoken)", "رهگذر": "passer-by",
    "رستورانه": "it's the restaurant (spoken)",
    # Unit 6 (food and ordering a meal), added 2026-07-06 by the
    # practice-pool-sync lane.
    "نان": "bread", "برنج": "rice", "مرغ": "chicken", "آب": "water",
    "قهوه": "coffee", "میوه": "fruit", "یا": "or",
    "می‌خواستم": "I'd like (polite, lit. 'I was wanting')",
    "لطفاً": "please", "غریبه": "stranger", "گارسون": "waiter",
    "دوست": "friend", "نزدیک": "close; near", "منو": "menu",
    "چی": "what", "توصیه": "recommendation",
    "می‌کنید": "you do (polite)", "میل": "desire (in 'what would you like')",
    "جوجه‌کباب": "chicken kebab", "امروز": "today",
    "خوبه": "is good (spoken)", "لیوان": "glass", "بشقاب": "plate",
    "صورت‌حساب": "the bill / check", "رو": "(informal object marker)",
    "خوشمزه": "delicious", "بود": "was",
    "نوش": "(part of the phrase 'enjoy your meal')",
    "جان": "(part of the phrase 'enjoy your meal'; lit. 'dear / soul')",
    "چشم": "right away (polite acknowledgment)",
    "الان": "now; right away",
    "میارم": "I bring (spoken contraction)",
    "اومدید": "you came (spoken variant)",
    "مشتری": "customer", "خب": "well; okay", "البته": "of course",
    # Unit 7 (weather and making plans), added 2026-07-06.
    "آفتابی": "sunny", "بارونی": "rainy", "ابری": "cloudy",
    "برفی": "snowy", "گرم": "hot", "سرد": "cold", "خنک": "cool",
    "هوا": "weather", "آفتابیه": "it's sunny (spoken)",
    "سرده": "it's cold (spoken)", "بارونیه": "it's rainy (spoken)",
    "چون": "because; since",
    "بهتره": "it's better (spoken, \"we'd better\")",
    "چتر": "umbrella", "ببریم": "let's bring; we bring (subjunctive)",
    "کت": "coat", "بپوشیم": "let's wear (subjunctive)",
    "فکر": "thought (as in 'I think')",
    "کنم": "I do (subjunctive)", "رضا": "Reza (name)",
    "موافقم": "I agree", "گرمه": "it's hot (spoken)",
    "عالیه": "great; excellent (spoken)", "بریم": "let's go (subjunctive)",
    "پارک": "park", "می‌بینمت": "I'll see you",
    # Unit 8 (shopping: prices, quantities, and paying), added 2026-07-06.
    "مغازه": "shop", "تخفیف": "discount", "کیلویی": "per kilo",
    "کیلو": "kilo", "نصف": "half", "می‌دید": "you give (polite)",
    "برات": "for you (informal)",
    "حساب": "account; bill (as in 'to settle up')",
    "نقدی": "in cash", "کارت": "card",
    "می‌گیرید": "you take; you accept",
    "قابلی": "(part of the phrase 'no trouble at all')",
    "فروشنده": "shopkeeper; seller", "سیب‌ها": "the apples (plural)",
    # Unit 9 (A2: administrative errands / bureaucracy), added 2026-07-06.
    # Widened 2026-07-11 (B1 units 01/03/06 backfill pass): B1's own
    # "وقت ندارم"/"وقت دارم" ("I don't/do have time") and "وقت"
    # (b1_unit03.lesson06) use the plain, general "time" sense, not the
    # narrower A2-bureaucracy "appointment/time slot" sense this entry
    # originally covered -- widened rather than split, since both senses
    # are the same word and the DB rows for A2/B1 are already separate
    # (different course_id) regardless.
    "وقت": "appointment; time slot; time (in general)", "مدرک": "document",
    "آدرس": "address", "قبض": "utility bill", "ملی": "national",
    "برای": "for", "تغییر": "change",
    "بگیرم": "let me take/get (subjunctive)",
    "خونه‌مو": "my house (object marker)",
    "عوض": "change; exchange", "کردم": "I did",
    "آدرسمو": "my address (object marker)",
    # Widened 2026-07-11 (B1 unit01 reading_passage): "امسال بهتر می‌شه"
    # ("this year will turn out better") uses شدن's plain "becomes/turns
    # out" sense, not the polite-request-opener idiom this entry
    # originally covered -- widened, same reasoning as وقت above.
    "می‌شه": "would it be possible; becomes / turns out (to be)",
    "بگید": "tell (polite imperative)",
    "بیارم": "let me bring (subjunctive)",
    "اجاره‌نامه": "lease agreement", "مهلت": "deadline",
    "قدیم": "old", "برق": "electricity",
    "بیارید": "bring (polite imperative)", "ثبت‌نام": "registration",
    "آخر": "end", "همین": "this same", "ماه": "month",
    "چه": "what; which", "کمکی": "help",
    "دستم": "my hand (as in 'I can help')",
    "برمیاد": "comes; is possible (idiom part)",
    "کارمند": "clerk; employee", "کی": "when; who", "جدید": "new",
    "زندگی": "life; living", "پیش": "ago; before",
    "کافیه": "is enough (spoken)", "می‌تونم": "I can",
    "سه‌شنبه": "Tuesday", "بیام": "let me come (subjunctive)",
    "ساعت": "hour; o'clock", "کد": "code",
    "پیگیریتون": "your tracking (code)", "۲۲۱۴": "2214 (tracking code)",
    # Unit 10 (A2: opinions -- remote work vs. office debate), added 2026-07-06.
    "نظر": "opinion", "دلیل": "reason", "دورکاری": "remote work",
    "ترافیک": "traffic", "تمرکز": "concentration", "دفتر": "office",
    "تهران": "Tehran", "زیادی": "a lot; excessive",
    "تلف": "wasted", "پیام": "message",
    "خانواده": "family", "بیشتر": "more", "خانواده‌م": "my family",
    "باشم": "that I be (subjunctive)",
    "موافق": "agree(ing) (as in \"I don't agree\")",
    "نگار": "Negar (name)", "آرش": "Arash (name)", "چرا": "why",
    "خونه": "house; home", "همکارامو": "my colleagues (object marker)",
    "ببینم": "let me see (subjunctive)", "می‌گیره": "it takes",
    "عادت": "habit (as in \"I'm used to it\")",
    # Unit 09 (A1: time), added 2026-07-07 (practice-content-gap-closing pass).
    "دقیقه": "minute", "نیم": "half (of an hour)", "ربع": "quarter (of an hour)",
    "نیمه": "is half (spoken contraction)", "ظهر": "noon",
    "قرار": "appointment", "یکم": "a little (spoken)", "دیر": "late",
    "میشه": "becomes; happens (spoken)",
    "چهاره": "is four (spoken contraction)",
    "سر": "head; top (as in 'to/at work')", "کار": "work; job",
    "میام": "I come; I'll come (spoken)",
    "مشکلی": "a problem (as in 'no problem')",
    "نیست": "is not (negative copula)",
    # Unit 10 (A1: dates), added 2026-07-07.
    "شنبه": "Saturday", "یکشنبه": "Sunday", "دوشنبه": "Monday",
    "چهارشنبه": "Wednesday", "پنجشنبه": "Thursday", "جمعه": "Friday",
    "تعطیل": "off; closed (holiday)", "هفتگیه": "is weekly (spoken)",
    "فروردین": "Farvardin (1st Persian solar month)",
    "اردیبهشت": "Ordibehesht (2nd Persian solar month)",
    "خرداد": "Khordad (3rd Persian solar month)", "تقویم": "calendar",
    "هجری": "Hijri (calendar era)", "شمسی": "solar (calendar)",
    "استفاده": "use (as in 'uses')",
    "می‌کنه": "does; uses (spoken, 3rd person)",
    "چندشنبه‌ست": "is which day of the week? (spoken contraction)",
    "دهم": "10th", "اردیبهشته": "is Ordibehesht (spoken contraction)",
    "تاریخ": "date", "جلسه": "meeting", "کدوم": "which",
    "روزه": "is (the) day (spoken contraction)",
    "چندم": "what date/number (ordinal question)", "هشتم": "8th",
    "مریم": "Maryam (name)", "سه‌شنبه‌ست": "is Tuesday (spoken contraction)",
    "سرم": "my head (as in \"I'm busy\")",
    # Unit 11 (A1: routines), added 2026-07-07.
    "بیدار": "awake", "می‌شم": "I become (spoken)", "صبحونه": "breakfast",
    "می‌خورم": "I eat", "میرم": "I go (spoken)", "می‌خوابم": "I go to sleep",
    "می‌شی": "you become (spoken, informal 2nd person)",
    "هر": "every", "بعدش": "after that", "شب‌ها": "at night(s)",
    "یه‌کم": "a little (spoken)", "دیرتر": "later", "نیما": "Nima (name)",
    "شدن": "to become; to happen (infinitive)",
    "چیکار": "what (activity/doing)",
    "می‌کنی": "you do (spoken, informal 2nd person)",
    "معمولاً": "usually", "می‌خوابه": "he/she goes to sleep (spoken, 3rd person)",
    # Units 12-15 (A1: plans, past events, preferences, comparisons),
    # added 2026-07-07 by the parallel practice-content-gap-closing pass.
    # نیما/کار/چیکار/پنجشنبه/کدوم are already covered by the 09-11 lane's
    # own additions above -- not re-declared here.
    "برنامه": "plan", "سینما": "cinema / movies", "چطوره؟": "How about it? / How's that?",
    "می‌خوای": "do you want", "قبوله": "it's a deal / agreed",
    "متأسفم": "I'm sorry", "نمی‌تونم": "I can't",
    "دعوت": "invitation", "منتظرم": "I'm waiting",
    "ساعتی؟": "time? (o'clock, question form)",
    "دیروز": "yesterday", "رفتم": "I went", "خوردم": "I ate", "دیدم": "I saw",
    "کردی": "you did", "فیلم": "movie", "خوب": "good",
    "ناهار": "lunch", "خوندم": "I read", "موندم": "I stayed",
    "چی؟": "what?", "رفت": "he/she went", "دید": "he/she saw", "کرد": "he/she did",
    "موند": "he/she stayed", "خوند": "he/she read",
    "موسیقی": "music", "خوشمزه‌ست": "it's delicious", "جالبه": "it's interesting",
    "اون": "that", "بزرگ‌تره": "it's bigger", "کوچیک‌تره": "it's smaller",
    "گرون‌تره": "it's more expensive", "ارزون‌تره": "it's cheaper", "قد": "height",
    "بلندتره": "it's/he's taller", "جوون‌تره": "he's/she's younger", "بدتره": "it's worse",
    # Unit 16 (A1: travel), added 2026-07-07.
    "بلیط": "ticket", "قطار": "train", "اتوبوس": "bus", "فرودگاه": "airport",
    "سکو": "platform",
    "سکوی": "platform (ezafe-linked form, as in 'platform two')",
    "حرکت": "departure; movement (as in 'it departs')",
    "مسافر": "traveler; passenger",
    "می‌خواید": "you want (polite)",
    # Unit 17 (A1: health), added 2026-07-07.
    "حالم": "my state/condition (as in \"I don't feel well\")",
    "سردرد": "headache", "تب": "fever",
    "دلم": "my stomach (as in 'my stomach hurts')",
    "درد": "pain", "خسته‌ام": "I'm tired",
    "کمک": "help", "می‌تونی": "you can (informal)",
    "کمکم": "help me (object)", "کنی": "you do",
    "دکتر": "doctor", "دارو": "medicine",
    "استراحت": "rest (noun, as in 'rest!')",
    "بخور": "drink (imperative, as in 'drink water!')",
    # Unit 18 (A1: work), added 2026-07-07 (en-fa units-18-19
    # practice-authoring pass -- the pack grew 17->19 units this session
    # with zero prior practice coverage).
    "شغل": "job",
    "مهندسم": "I'm an engineer (colloquial contraction)",
    "معلمم": "I'm a teacher (colloquial contraction)",
    "دکترم": "I'm a doctor (colloquial contraction)",
    "شغلت": "your job",
    "شرکت": "company", "مدرسه": "school", "بیمارستان": "hospital",
    "در": "in / at",
    "مهندسه": "he's/she's an engineer (colloquial, third person)",
    "معلمه": "he's/she's a teacher (colloquial, third person)",
    # Unit 19 (A1: housing), added 2026-07-07, same pass as unit18 above.
    "اتاق": "room", "خواب": "sleep (as in 'bedroom')",
    "آشپزخانه": "kitchen", "حموم": "bathroom (colloquial)",
    "تخت": "bed", "میز": "table", "صندلی": "chair",
    "بالای": "above / on top of",
    "تخته": "it's the bed (colloquial contraction)",
    "آشپزخانه‌س": "it's the kitchen (colloquial contraction)",
    "خونه‌ی": "house of / my house (ezafe form)",
    "خونه‌ت": "your house (colloquial)",
    # Added 2026-07-23: introduced+glossed "his house" in
    # realizations/fa/a1_unit33_neighborhood.yaml (teach card, introduced_tokens)
    # but was missing here, which raised ValueError in _classify_fa and crashed
    # _practice_content_integrity_check.py / the fill_in_blank ambiguity gate for
    # the entire fa direction. Sibling of خونه‌ی/خونه‌ت above.
    "خونه‌اش": "his house (colloquial)",
    # Unit 20 (A1: clothing), added 2026-07-09 (en-fa units-20+ overnight
    # practice-depth pass, closing the gap where real lesson content ran
    # ahead of Endless Practice coverage). کت/می‌تونم/کنم already existed
    # (کت "coat" from unit07's weather content -- same referent as this
    # unit's "jacket," reused not re-glossed; می‌تونم/کنم from units
    # 12/17 -- reused verbatim, not redeclared here).
    "پیراهن": "shirt", "شلوار": "pants", "کفش": "shoes",
    "قشنگ": "nice / pretty",
    "رنگ": "color", "قرمز": "red", "آبی": "blue", "سیاه": "black", "سفید": "white",
    "سایز": "size", "بزرگ": "big", "کوچیک": "small", "متوسط": "medium",
    "امتحانش": "try it (on)",
    "سایزی": "what size (indefinite/interrogative form)",
    "قشنگه": "it's nice (colloquial contraction)",
    # Unit 21 (A1: money), added 2026-07-09, same overnight pass as unit20
    # above. تومن/هزار already existed (established unit03/unit08, "price"
    # semantic) -- reused verbatim, not redeclared here.
    "پول": "money", "بانک": "bank", "دلار": "dollar",
    "تبدیل": "exchange / convert",
    "چقدر": "how much / how many",
    "خودپرداز": "ATM (literally 'self-payer')",
    "بردارم": "I withdraw / take out",
    "خرد": "change / small (money)",
    "نرخ": "rate",
    "صد": "hundred",
    "کنید": "you do (polite/plural, subjunctive)",
    # Unit 22 (A1: phone), added 2026-07-09, same overnight pass as units
    # 20-21 above. تلفن/پیام/زنگ/میشه/برات/چهار/چطوری/بهتره/آره/حتماً/میام/
    # الان already existed (established across units 02/03/07/A2unit10/12/
    # 15/16/etc.) -- reused verbatim, not redeclared here.
    "زدن": "to ring / to hit (as in 'to call')",
    "صدا": "voice",
    "الو": "hello (answering the phone)",
    "منم": "it's me (colloquial contraction)",
    "تکرار": "repeat / repetition",
    "آهسته‌تر": "more slowly",
    "صحبت": "talk / speech (as in 'to talk')",
    "بیا": "come (imperative)",
    "کافه": "cafe",
    "قطع": "cut off / disconnected",
    "وصل": "connected",
    "بعداً": "later",
    "بهتر": "better",
    "شد": "became / happened (past)",
    "می‌کنیم": "we do (as in \"we'll talk\")",
    "میرن": "they go (informal/colloquial)",
    # Unit 23 (A1: emotions), added 2026-07-09, same overnight pass as
    # units 20-22 above. خسته‌ام/خوب/نیستم/چطوری/خوبم/من/یکم/چرا/هستی/کار/
    # کردم/چون/امروز/سارا/چه/نیما/تو/نیست already existed (established
    # across many earlier units) -- reused verbatim, not redeclared here.
    "خوشحال": "happy", "ناراحت": "sad",
    "خوشحالم": "I'm happy (colloquial contraction)",
    "ناراحتم": "I'm sad (colloquial contraction)",
    "خسته": "tired",
    "گشنه": "hungry",
    "گشنه‌ام": "I'm hungry (colloquial contraction)",
    "عصبانی": "angry",
    "عصبانی‌ام": "I'm angry (colloquial contraction)",
    "نگران": "worried",
    "نگرانی": "you're worried (colloquial contraction)",
    "تعطیله": "it's a holiday (colloquial contraction)",
    "زیاد": "a lot / much",
    "خسته‌ست": "is tired (colloquial contraction)",
    "کرده": "has done (past perfect)",
    "فقط": "only",
    "خوشحاله": "he's/she's happy (colloquial contraction)",
    # Unit 24 (A1: hobbies), added 2026-07-09, same overnight pass as
    # units 20-23 above. وقت/کتاب/من/دوست/دارم/موسیقی/فیلم/می‌کنم/هر/تو/
    # چیکار/می‌کنی/نیما/داره/چند/تا/هم/می‌کنه/سارا/سینما/چی/و/چه/خوب
    # already existed (established across many earlier units) -- reused
    # verbatim, not redeclared here.
    "آزاد": "free (as in 'free time')",
    "سرگرمی": "hobby",
    "خوندن": "to read / reading",
    "گوش": "ear (as in 'to listen')",
    "می‌دم": "I give / I do (as in 'I listen')",
    "می‌بینم": "I watch / I see",
    "ورزش": "sport / exercise",
    "فوتبال": "football",
    "بازی": "play / game",
    "هفته": "week",
    "گاهی": "sometimes",
    "می‌خونه": "he/she reads",
    "می‌رم": "I go",
    "دیدن": "to watch / to see",
    # Unit 11 (A2: banking), added 2026-07-11 (A2 units 11-18 backfill
    # pass -- these 8 units existed on disk and were already imported
    # into the DB but had zero lexeme classifier coverage in this script
    # at all; see UNIT_FILES_A2's own comment above).
    "کارت بانکی": "bank card", "رمز": "PIN code / password",
    "موجودی": "balance", "باز": "open",
    "کردن": "to do (infinitive)",
    "کارت ملی": "national ID card", "مدرک آدرس": "proof-of-address document",
    "بانکی": "banking / bank (adjective)",
    "اگر": "if", "مدارکتون": "your documents (polite)",
    "می‌تونید": "you can (polite)",
    "لازم": "necessary / needed", "لازمه": "necessary / needed (colloquial contraction)",
    "ساعت کاری": "working hours", "بعدازظهر": "afternoon",
    "۸": "8 (eight, numeral)", "۲": "2 (two, numeral)",
    "بکنم": "let me do (subjunctive, formal variant)",
    "ملیم": "my national ID (colloquial)",
    "جدیدم": "my new (colloquial possessive form)",
    "آوردم": "I brought (past)",
    "دیگه": "another; more; next",
    "آماده": "ready", "رمزش": "its PIN code (colloquial)",
    "می‌گیرم": "I get / I take (spoken)",
    "روزی": "day (indefinite form, e.g. 'the day that ...'/'what day')",
    "که": "that / which / so that",
    "تحویل": "delivery / handover (as in 'to receive/pick up')",
    # Unit 12 (A2: doctor), added 2026-07-11, same pass as unit11 above.
    "علائم": "symptoms", "مدت": "duration / length of time",
    "نسخه": "prescription", "شدیدی": "severe (indefinite form)",
    "گفت": "he/she said (past)", "بخورم": "let me drink / I drink (subjunctive)",
    "نوبت": "appointment; turn", "نوبتم": "my appointment (colloquial)",
    "۱۱": "11 (eleven, numeral)",
    "صبحه": "is morning / a.m. (colloquial contraction)",
    "زودتر": "earlier; sooner", "۱۵": "15 (fifteen, numeral)",
    "بیایید": "come (polite imperative)",
    "نشد": "didn't happen / didn't become (negative past)",
    "دوباره": "again", "تماس": "contact / call",
    "بگیرید": "take / get (polite imperative)",
    "شده": "become; happened (past participle)",
    "دکتر رضایی": "Dr. Rezaei",
    "سردرده": "it's a headache (colloquial contraction)",
    "شدیده": "it's severe (colloquial contraction)",
    "شدید": "severe", "داشت": "he/she had (past)",
    "کند": "he/she does (formal subjunctive of 'to do')",
    # Unit 13 (A2: maintenance), added 2026-07-11, same pass as unit11
    # above.
    "لوله": "pipe", "لوله‌ی": "pipe of (ezafe-linked form)",
    "حمام": "bathroom", "چکه": "leak / drip",
    "شوفاژ": "radiator / heater", "خراب": "broken",
    "سرایدار": "building superintendent / custodian",
    "تعمیر": "repair", "زدم": "I hit / I called (past)",
    "زد": "he/she hit / called (past)",
    "بیاید": "come (formal, 'can you come')",
    "تعمیرش": "repair it / its repair (object suffix)",
    "درخواست": "request", "ثبت": "registration / logging",
    "تعمیرکار": "repairman",
    "میاد": "he/she comes (spoken, 3rd person)",
    "۱۰": "10 (ten, numeral)",
    "این‌طوریه": "is like this (colloquial contraction)",
    "میره": "it goes (spoken, 3rd person)",
    "روی": "on top of; onto", "زمین": "ground; floor",
    "خونه‌ام": "I'm home (colloquial contraction)",
    "می‌بینمتون": "I'll see you (polite)",
    # Unit 14 (A2: job interview), added 2026-07-11, same pass as unit11
    # above.
    "مصاحبه": "interview", "تجربه": "experience",
    "تجربه‌ی": "experience of (ezafe-linked form)",
    "مهارت": "skill", "حقوق": "salary",
    "فرصت شغلی": "job opportunity", "رزومه": "résumé / CV",
    "هفته‌ی": "week of (ezafe-linked form)",
    "شروع": "start; beginning",
    "حداقل": "at least; minimum",
    "فروشگاه": "store; shop", "نیاز": "need",
    "مناسب": "suitable; good (fitting)",
    "مصاحبه‌ها": "interviews (plural)",
    "انجام": "carrying out; performing",
    "کاریتون": "your work (possessive form, polite)",
    "مصاحبه‌کننده": "interviewer",
    "مهارت‌هایی": "skills (indefinite/plural form)",
    "تیمی": "team-related; of the team (as in 'teamwork')",
    "حل": "solving; solution (as in 'problem-solving')",
    "مسئله": "problem; issue",
    "خوبم": "I'm good (at) (colloquial contraction)",
    # Unit 15 (A2: travel disruption), added 2026-07-11, same pass as
    # unit11 above.
    "قطار": "train", "تاخیر": "delay", "سکو": "platform",
    "سکوی": "platform of (ezafe-linked form)",
    "لغو": "cancelled", "لغو شدن": "to be cancelled",
    "اعلامیه": "announcement", "مسیر جایگزین": "alternative route",
    "مسیر": "route", "جایگزین": "alternative; substitute",
    "جایگزینی": "alternative; substitute (indefinite form)",
    "نُه": "nine (vocalized spelling, not 'no')",
    # Widened 2026-07-11 (B1 unit05 workplace, e.g. "او مسئول این پروژه
    # هست"): B1 uses هست as a plain predicate copula ("he/she/it is"),
    # not just the existential "there is" sense this entry originally
    # covered -- same core 3rd-singular "to be" verb, widened rather than
    # split (same reasoning as وقت/می‌شه above).
    "هست": "there is / exists; he/she/it is (copula)",
    "برسم": "let me arrive / I arrive (subjunctive)",
    "به خاطر": "because of",
    "مشکل فنی": "technical problem", "مشکل": "problem",
    "فنی": "technical", "توجه": "attention",
    "اصفهان": "Isfahan", "منتظر": "waiting",
    "می‌مونم": "I stay / I wait (spoken)",
    "قطارم": "my train (colloquial)",
    "متاسفانه": "unfortunately",
    "بخرید": "buy (polite imperative)",
    # Unit 16 (A2: online habits), added 2026-07-11, same pass as unit11
    # above.
    "شبکه‌ی اجتماعی": "social media", "شبکه": "network",
    "اجتماعی": "social", "اپلیکیشن": "app", "صفحه": "screen",
    "مفید": "useful",
    "مفیده": "is useful (colloquial contraction)",
    "خبر": "news", "سرگرم‌کننده": "entertaining; fun",
    "حدود": "about; approximately", "استفاده": "use",
    "دنیا": "world", "می‌خونم": "I read (spoken, 1st person)",
    "مورد علاقه": "favorite", "مورد": "case; item",
    "علاقه": "interest; liking",
    "علاقه‌ام": "my interest / liking (possessive form)",
    "می‌کند": "he/she does (formal, written register)",
    "اینستاگرامه": "is Instagram (colloquial contraction)",
    "نظرت": "your opinion (as in 'in your opinion')",
    # Unit 17 (A2: weekly schedule), added 2026-07-11, same pass as
    # unit11 above.
    "هفته‌ات": "your week (colloquial possessive)",
    "آخر هفته": "weekend", "آخر": "end",
    "استراحت کردن": "to rest", "اول": "first",
    "در آخر": "finally; at the end",
    "پنجشنبه‌ها": "on Thursdays (habitual plural)",
    "جمعه‌ها": "on Fridays (habitual plural)",
    "در طول هفته": "during the week", "طول": "duration; length",
    "تمیز کردن": "to clean", "تمیز": "clean",
    "برنامه‌ی": "schedule of (ezafe-linked form)",
    "خرید": "shopping; purchase",
    "دوستامو": "my friends (object marker, colloquial)",
    "برنامه‌ت": "your schedule (colloquial possessive)",
    "سر کار": "at/to work",
    # Unit 18 (A2: shopping complaint), added 2026-07-11, same pass as
    # unit11 above.
    "خرابه": "is broken (colloquial contraction)",
    "رسید": "receipt", "دادن": "to give (infinitive)",
    "بدم": "let me give / I give (subjunctive)",
    "تعویض": "exchange", "تعویض کردن": "to exchange",
    "بازپرداخت": "refund", "هدفون": "headphones",
    "خریدم": "I bought (past)",
    "صدا نداره": "has no sound",
    "پولم": "my money", "پس بگیرم": "let me get back / get my money back",
    "تعویضش": "exchange it (object suffix)",
    "تاریخ خرید": "purchase date", "کالا": "goods; merchandise",
    "را": "(marks a definite direct object, formal)",
    "داد": "he/she gave (past)",
    "خریدینش": "you bought it (polite/formal past)",
    "خریدمش": "I bought it (past)",
    "پولتون": "your money (polite)",
    "بدیم": "let's give / we give (subjunctive)",
    "بهتون": "to you (polite)",
    # B1 units 01-06 (necessity / abilities / hypotheticals / debate /
    # workplace / narrative), added 2026-07-11. This is the FIRST time
    # this script has covered any B1-level content -- see UNIT_FILES_B1's
    # own comment above for why it's a separate course/tuple, same
    # pattern as UNIT_FILES_A2. B1 reuses many A1/A2 tokens verbatim
    # (باید/کار/چون/خیلی/etc.) -- only genuinely new tokens are declared
    # below, one comment block per unit. Two real homograph collisions
    # were found and fixed via the existing scoped-discriminator pattern
    # (see BASHE_SUBJUNCTIVE_LESSONS/NO_NEGATION_LESSONS below); two more
    # reused tokens (برید/باشید) turned out to be compatible reuse, not
    # true homographs -- both existing sub/imperative-adjacent glosses
    # ("go (polite)"/"be (polite)") already read naturally for this
    # course's own subjunctive-complement usage too ("you must go"/"if
    # you have"), so they're deliberately left unchanged rather than
    # forcing an unnecessary split. سه existing entries ARE widened below
    # (وقت/هست/می‌شه) where the B1 sense is genuinely broader than what
    # was on file, not just a compatible restatement.
    #
    # Unit 01 (necessity: باید + subjunctive, present/past, dialogue about
    # a work deadline, reading about two years' obligations).
    "برم": "(that) I go", "بری": "(that) you go", "دانشگاه": "university",
    "بره": "(that) he/she go", "برن": "(that) they go", "اونا": "they",
    "می‌رفتم": "I was going / I used to go (imperfect past)",
    "نباید": "must not", "شلوغ": "busy; crowded",
    "نرفتم": "I didn't go", "گزارش": "report",
    "تموم": "finished; done", "کنه": "(that) he/she do",
    "امشب": "tonight", "بمونم": "(that) I stay",
    "وقت دارم": "I have time", "امسال": "this year", "پارسال": "last year",
    "مهم": "important", "به‌موقع": "on time",
    "نتونست": "couldn't / wasn't able to (simple past)",
    "کمتر": "less", "قبول": "acceptance (as in 'to accept')",
    "حالا": "now",
    # Unit 02 (abilities: می‌تونم + subjunctive, present/past, dialogue
    # about a car needing a repair, reading about getting a license).
    "رانندگی": "driving", "ماشین": "car", "می‌تونه": "he/she can",
    "می‌تونیم": "we can", "می‌تونن": "they can",
    "کنن": "(that) they do", "می‌تونستم": "I could / was able to",
    "نمی‌تونستم": "I couldn't / wasn't able to",
    "گواهینامه": "driver's license",
    "درستش": "fix it / repair it (object-suffixed)",
    "قطعه": "part (mechanical)", "بخرم": "(that I) buy",
    "حاضره": "is ready (colloquial contraction)",
    "نمی‌تونست": "he/she couldn't / wasn't able to",
    "نداشت": "he/she didn't have (past)", "گرفت": "got / received (past)",
    "ماشینش": "his/her car", "ماشینم": "my car",
    "امتحان": "test / exam",
    # Unit 03 (hypotheticals: اگه + subjunctive real conditions, plus
    # counterfactual past, dialogue about weekend shopping plans).
    "اگه": "if", "باشی": "(if) you be", "می‌خرم": "I buy / I'll buy",
    "می‌خری": "you buy / you'll buy", "باشیم": "(if) we be",
    "باشن": "(if) they be", "می‌خره": "he/she buys",
    "می‌خریم": "we buy", "می‌خرید": "you (pl.) buy",
    "می‌خرن": "they buy", "داشتم": "I had", "نداشتم": "I didn't have",
    "می‌خریدم": "I would buy / I would have bought",
    "نداشته": "not having (negative participle)",
    "نمی‌خرم": "I won't buy", "چیز": "thing",
    "امیدوارم": "I hope (contraction)",
    "شاید": "maybe", "همینطور": "likewise",
    # Unit 04 (debate: agreeing/disagreeing with an opinion, plus a
    # reason clause, dialogue about remote work).
    "موافقی": "you agree (informal)", "موافقه": "he/she agrees",
    "موافقیم": "we agree", "موافقید": "you (pl.) agree",
    "موافقن": "they agree", "مخالفم": "I disagree",
    "مخالفه": "he/she disagrees", "سخته": "it's hard (colloquial)",
    "تنهام": "I'm lonely (colloquial contraction)",
    "تنهاست": "he/she is lonely (colloquial contraction)",
    # Unit 05 (workplace: stating responsibility for a project, status
    # updates, dialogue about a status meeting).
    "مسئول": "responsible", "پروژه": "project", "هستیم": "we are",
    "هستن": "they are", "حسین": "Hossein",
    "تمومه": "it's done (colloquial contraction)",
    "هنوز": "still / yet", "چه‌وقت": "when",
    # Unit 06 (narrative: past-continuous background + simple-past event,
    # reported speech, dialogue retelling a story about a broken-down car).
    "وقتی": "when (temporal conjunction)",
    "گفتم": "I said", "گفتی": "you said", "می‌رسم": "I'll arrive",
    "می‌رسه": "he/she'll arrive", "نگفت": "he/she didn't say",
    "هیچی": "anything / nothing", "می‌رفت": "he/she was going",
    # B1 units 07-11 ("second wave": wishes and regret / nuanced debate /
    # professional meetings / relative clauses / reported speech), added
    # 2026-07-11 (B1 units 07-11 backfill pass). Same convention as units
    # 01-06 above: B1 reuses many earlier tokens verbatim -- only
    # genuinely new tokens are declared below, one comment block per unit.
    # Unit 07 (wishes and regret: کاش-wish + imperfect بودن, past counterfactual).
    "کاش": "if only / I wish", "بودم": "I was", "بودی": "you were",
    "دیشب": "last night", "جشن": "party; celebration", "تولد": "birth; birthday (as in 'birthday party')",
    "بودیم": "we were", "بودید": "you (pl.) were", "بودن": "they were",
    "رفته": "gone (past participle, as in 'I had gone')", "می‌دیدم": "I would see / I would have seen", "نرفته": "not gone (negative past participle)",
    "نمی‌دیدم": "I wouldn't see / I wouldn't have seen", "نیومد": "he/she didn't come (colloquial)", "نیومدم": "I didn't come (colloquial)",
    "اشکالی": "a problem; a flaw (indefinite, as in 'no problem')", "جات": "your place (colloquial)", "خالی": "empty",
    "بپرسم": "(that) I ask / let me ask (subjunctive)", "همدیگه": "each other", "ببینیم": "(that) we see (subjunctive)",
    "نتونستم": "I couldn't / wasn't able to", "می‌دونم": "I know (colloquial)", "خوشحال می‌شم": "I'd be happy (to) (colloquial, lit. 'I'll become happy')",
    "دست": "hand (as in 'was lost', lit. 'went from hand')", "کمی": "a little", "گذاشتن": "to put; to place (infinitive, as in 'to make plans')",
    "نرفت": "he/she didn't go", "دلتنگ": "homesick; longing (for someone)", "ببینن": "(that) they see (subjunctive)",
    # Unit 08 (nuanced debate: concessive هرچند/با اینکه + stronger contrastives).
    "هرچند": "although", "اما": "but (contrastive)", "اینکه": "that (complementizer, as in 'even though')",
    "تنها": "alone", "عین": "(part of the phrase 'nevertheless / at the same time')", "حال": "state; condition; mood (bare form)",
    "کارم": "my work (possessive form)", "ارتباط": "communication; connection", "تیم": "team",
    "سخت‌تر": "harder (comparative)", "بعضی": "some", "روزا": "days (colloquial plural)",
    "بازم": "still; also (colloquial)", "درباره‌ی": "about (preposition, ezafe-linked)", "فکری": "thought; idea (indefinite form)",
    "حرفت": "your point / your words (possessive form)", "بعضی وقتا": "sometimes (colloquial)", "فرق": "difference (as in 'is different')",
    "هیچ‌کدوم": "neither one; none of them", "نظرشون": "their opinion (possessive form)", "چیزی": "thing; something (indefinite form)",
    "آیا": "whether (yes-no question particle)", "بحث می‌کنن": "they discuss / debate", "می‌گه": "he/she says (colloquial, 3rd person)",
    "حرف": "talk; word; speech", "می‌مونه": "he/she stays / remains (colloquial, 3rd person)", "کارش": "his/her work (possessive form)",
    "می‌ده": "he/she gives / does (colloquial, 3rd person)", "احترام": "respect", "گفتن": "to say (infinitive)",
    "نکردن": "they didn't do (negative past, 3rd plural)",
    # Unit 09 (professional meetings: formal softened requests/suggestions).
    "بیایم": "(that) we come (subjunctive)", "موکول": "postponed (participial adjective, as in 'we postpone')", "امکانش": "possibility (of it) (as in 'is it possible')",
    "بفرستید": "you (formal) send", "پیشنهاد": "suggestion", "تصمیم": "decision",
    "بگیریم": "(that) we take/decide (subjunctive)", "بودجه": "budget", "می‌خواد": "he/she wants (colloquial, 3rd person)",
    "جلسه‌ی": "meeting of (ezafe-linked form)", "کردید": "you (formal) did", "بعدی": "next",
    "برگزار": "held; organized (participial adjective, as in 'is held')", "تشکر": "thanks; gratitude (as in 'with thanks')", "روزیه": "is (which) day (colloquial contraction)",
    "بفرسته": "he/she sends (subjunctive, 3rd person)", "همچنین": "also; likewise", "گرفتیم": "we took / decided (past, as in 'we decided')",
    "سوالی": "a question (indefinite form)",
    # Unit 10 (relative clauses: subject/object/oblique که-clauses).
    "کسی": "someone; the person (indefinite, as in 'the person who')", "سارا‌ست": "is Sara (colloquial contraction)", "دوستی": "a friend (indefinite form)",
    "درس می‌خونه": "he/she studies (lit. 'reads lesson')", "کتابی": "a book (indefinite form)", "کاری": "a job/task (indefinite form)",
    "واقعاً": "really", "باهاش": "with him/her (colloquial)", "شهری": "a city (indefinite form)",
    "توش": "in it (colloquial)", "شدم": "I became", "صمیمی": "close; intimate",
    "بگم": "(that) I say / let me say (subjunctive)", "دوستم": "my friend", "درباره‌ش": "about him/her/it (colloquial)",
    "همونه": "that's the one (colloquial contraction)", "با هم": "together", "می‌رفتیم": "we were going / used to go (imperfect)",
    "بزرگ شده": "has grown up (present perfect)", "شهر": "city (bare form)", "فرق داره": "is different (lit. 'has difference')",
    "همیشه": "always", "برگردم": "let me go back / (that) I return (subjunctive)", "خیابونی": "a street (indefinite form)",
    "می‌کردم": "I was doing / used to do (imperfect)", "همسایه‌ها": "neighbors (plural)", "همسایه‌هایی": "neighbors (indefinite/relative plural form)",
    "باهاشون": "with them (colloquial)", "مهربون": "kind", "می‌کرد": "he/she was doing / used to do (imperfect)",
    "کوچیکی": "small; little (indefinite adjective form)", "به دنیا اومد": "was born (lit. 'came to the world')", "آروم": "calm; quiet",
    "کمکش": "help him/her (object suffix)", "می‌کردن": "they were doing / used to do (imperfect, 3rd plural)", "برگرده": "(that) he/she return (subjunctive)",
    # Unit 11 (reported speech: reported questions, pronoun shift, plural گفتن).
    "پرسید": "he/she asked", "کِی": "when (explicit kasre diacritic, not 'who')", "میای": "you're coming (colloquial, 2nd person)",
    "میری": "you're going (colloquial, 2nd person)", "خودش": "himself / herself", "می‌ره": "he/she goes (colloquial, 3rd person)",
    "گفتیم": "we said", "داریم": "we have", "گفتید": "you (pl./formal) said",
    "میاید": "you (pl./formal) are coming", "بهم": "to me (colloquial)", "من و": "... and I (lit. 'I and', as in 'Maryam and I')",
    "تعریف": "recounting; telling (as in 'to recount/tell about')", "موافقت": "agreement (as in 'to agree')", "کیا": "who (plural, colloquial, as in 'who else')",
    "بهشون": "to them (colloquial)", "گفته": "said (past participle, as in 'had said')",
    # A1 units 31-36 (celebrations, household, neighborhood, post, cooking,
    # personality), added 2026-07-12 after those realization files were
    # added to the en-fa backfill file list. Keep these atomic: card-level
    # phrase glosses are intentionally not copied onto individual tokens.
    "مهمونی": "party / gathering", "کیک": "cake", "هدیه": "gift",
    "تولدمه": "it's my birthday", "تولدت": "your birthday",
    "کِیه": "when is it?", "تولدم": "my birthday", "مبارک": "happy; blessed",
    "براش": "for him/her", "نیماست": "is Nima", "جشن‌ها": "celebrations",
    "تولدها": "birthdays", "ظرف": "dish", "شستن": "washing; to wash",
    "لباس": "clothes", "جارو": "broom; sweeping", "خانه": "home / house",
    "می‌شورم": "I wash", "ظرف‌ها": "dishes", "لباس‌ها": "clothes",
    "می‌شوره": "he/she washes", "کارها": "tasks / chores",
    "می‌کنن": "they do", "کارهای": "tasks of / kinds of work",
    "محله": "neighborhood", "همسایه": "neighbor", "خیابان": "street",
    "محله‌ام": "my neighborhood", "آرومه": "is quiet / calm",
    "محله‌ات": "your neighborhood", "ماست": "is our / belongs to us",
    "پارکه": "is a park", "همسایه‌ات": "your neighbor",
    "همسایه‌ام": "my neighbor", "خانه‌اش": "his/her house",
    "نزدیکه": "is near", "پستخانه": "post office", "تمبر": "stamp",
    "نامه": "letter", "بسته": "package", "بفرستم": "I send (subjunctive)",
    "می‌فرستم": "I send / I am sending", "فرستادن": "to send",
    "گرفتن": "to receive / to take", "می‌فرستمش": "I send it",
    "زود": "soon / early", "می‌فرسته": "he/she sends",
    "آشپزی": "cooking", "پیاز": "onion", "نمک": "salt", "روغن": "oil",
    "خرد می‌کنم": "I chop", "می‌ریزم": "I pour / add",
    "سرخ می‌کنم": "I fry", "خرد کردن": "to chop",
    "سرخ کردن": "to fry", "ریختن": "to pour", "سرخش": "fry it",
    "غذا": "food / meal", "می‌پزه": "he/she cooks", "تقریباً": "almost",
    "آماده‌ست": "is ready", "مرسی": "thanks", "قرمه‌سبزی": "ghormeh sabzi",
    "می‌پزی": "you cook", "می‌پزم": "I cook",
    "آشپزخانه‌ست": "is the kitchen", "می‌ریزه": "he/she pours / adds",
    "دوست دارم": "I like", "وقت ندارم": "I don't have time",
    "بپز": "cook! (imperative)", "بامزه": "funny", "خجالتی": "shy",
    "جدی": "serious", "مهربونه": "he/she is kind",
    "بامزه‌ست": "he/she is funny", "خجالتیه": "he/she is shy",
    "جدیه": "he/she is serious", "زرنگ": "smart / clever",
    "تنبل": "lazy", "زحمت‌کش": "hardworking", "صبور": "patient",
    "تنبل نیست": "he/she is not lazy", "صبوره": "he/she is patient",
    "معلم": "teacher", "زحمت‌کشه": "he/she is hardworking",
    "شخصیت": "personality", "چه جوریه": "what is he/she like?",
    "شخصیتش": "his/her personality", "زرنگه": "he/she is smart",
    "اصلاً": "at all", "باحال": "cool", "آشنا بشم": "I get acquainted",
    "باحاله": "is cool", "هیچ‌وقت": "never", "برای همین": "for this reason",
    "جمع‌های": "groups of / plural gatherings of",
    "حرف نمی‌زنه": "he/she doesn't talk", "فکر می‌کنم": "I think",
    "زحمت‌کشم": "I am hardworking", "شخصیتت": "your personality",
    # ---------------------------------------------------------------
    # A1 units 25-30 (appearance, animals, sports, transportation,
    # technology, education), added 2026-07-22 by the en-fa
    # checkpoint-coverage pass. Atomic word glosses only -- a teaching
    # card's own phrase gloss is never copied onto its individual tokens.
    # Unit 25 (appearance).
    "قدش": "his/her height", "بلند": "tall", "بلنده": "is tall (spoken)",
    "کوتاه": "short", "کوتاهه": "is short (spoken)", "مو": "hair",
    "موی": "hair of (ezafe-linked form)", "موهاش": "his/her hair",
    "مشکی": "black (of hair/eyes)", "مشکیه": "is black (spoken)",
    "بلوند": "blond", "بلونده": "is blond (spoken)",
    "چشمای": "eyes of (ezafe-linked plural)", "چشماش": "his/her eyes",
    "قهوه‌ای": "brown", "قهوه‌ایه": "is brown (spoken)", "سبز": "green",
    "سبزه": "is green (spoken)", "آبیه": "is blue (spoken)",
    "عینک": "glasses", "می‌زنه": "he/she wears (glasses); he/she hits",
    "شکلیه": "does he/she look (as in 'what does he/she look like?')",
    "رنگیه": "is (what) color (as in 'what color is it?')",
    # Unit 26 (animals).
    "حیوان": "animal", "خونگی": "domestic (as in 'pet')",
    "سگ": "dog", "گربه": "cat", "پرنده": "bird", "ماهی": "fish",
    "اسمش": "its/his/her name", "سگم": "my dog", "سفیده": "is white (spoken)",
    "گربه‌ی": "cat of (ezafe-linked form)", "پشمک": "Pashmak (cat's name)",
    "پشمکه": "is Pashmak (spoken)", "منه": "is mine (spoken)",
    "سگمه": "is my dog (spoken)", "خوشگل": "cute; pretty",
    "خوشگله": "is cute (spoken)",
    # Unit 27 (sports).
    "بسکتبال": "basketball", "والیبال": "volleyball", "شنا": "swimming",
    "ورزشی": "a sport (indefinite form)",
    "باشگاه": "gym", "استخر": "swimming pool",
    "بار": "time(s); occurrence (as in 'twice')", "می‌ری": "you go (spoken)",
    # Unit 28 (transportation).
    "مترو": "metro; subway", "دوچرخه": "bicycle", "پیاده": "on foot",
    "تاکسی": "taxi", "چقدره": "how much is it? (spoken)",
    "ورزشه": "is exercise (spoken)",
    # Unit 29 (technology).
    "تکنولوژی": "technology", "گوشی": "mobile phone", "کامپیوتر": "computer",
    "اینترنت": "internet", "دانلود": "download",
    "گوشیت": "your phone (informal)",
    # Unit 30 (education).
    "دانشجو": "university student", "درس": "lesson; subject", "زبان": "language",
    "ریاضی": "math", "رشته": "major; field of study",
    "یاد": "learning (as in 'to learn')",
    "می‌خونی": "you study / you read (spoken)",
    "رشته‌ی": "major of (ezafe-linked form)",
    "ریاضیه": "is math (spoken)",
    # ---------------------------------------------------------------
    # A1 units 37-57, added 2026-07-22, same pass.
    # Unit 37 (colors).
    "زرد": "yellow", "نارنجی": "orange (color)", "صورتی": "pink",
    "سیاهه": "is black (spoken)", "قرمزه": "is red (spoken)", "موز": "banana",
    "گربه‌ی من": "my cat", "پیراهنم": "my shirt", "زرده": "is yellow (spoken)",
    "نارنجیه": "is orange (spoken)", "صورتیه": "is pink (spoken)",
    "بنفش": "purple", "خاکستری": "gray", "کتابم": "my book",
    "بنفشه": "is purple (spoken)", "خاکستریه": "is gray (spoken)",
    "رنگش": "its color", "چه رنگیه": "what color is it?",
    "کتابت": "your book (informal)", "ماشینت": "your car (informal)",
    "دوست دارد": "he/she likes (formal)", "تو خونه": "in the house",
    "اونجاست": "is there (spoken)", "چه رنگی": "what color",
    # Unit 38 (seasons).
    "فصل": "season", "بهار": "spring", "تابستان": "summer",
    "چهار فصل": "four seasons", "پاییز": "autumn", "زمستان": "winter",
    "برفیه": "is snowy (spoken)", "سرد نیست": "is not cold",
    "اسکی": "skiing", "برف": "snow", "کدوم فصل": "which season",
    "دوست داری": "you like (informal)", "تو چی؟": "what about you? (informal)",
    # Unit 39 (emergencies).
    "پلیس": "police", "آمبولانس": "ambulance", "آتش‌نشانی": "fire department",
    "آتش": "fire", "خطر": "danger", "تصادف": "accident",
    "اورژانس": "emergency; emergency room", "اورژانسه": "is an emergency (spoken)",
    "بزنید": "call / hit (polite imperative, as in 'call!')",
    # Unit 40 (lost items).
    "کیف": "bag", "کلید": "key", "گم": "lost (as in 'to lose')",
    "گذرنامه": "passport", "پیدا": "found (as in 'to find')",
    "دیدید": "did you see? (polite)", "آقای": "Mr. (ezafe-linked form)",
    "کریمی": "Karimi (surname)", "گمشده": "lost (item)", "پیداشده": "found (item)",
    # Unit 41 (appointments).
    "دندانپزشک": "dentist", "مطب": "doctor's office", "آزادم": "I am free",
    "آزادید": "are you free? (polite)", "خانم": "Ms.; madam",
    "احمدی": "Ahmadi (surname)", "رضایی": "Rezaei (surname)",
    # Unit 42 (library).
    "کتابخونه": "library", "امانت": "loan (as in 'to borrow')",
    "صادقی": "Sadeghi (surname)",
    # Unit 43 (waste disposal).
    "زباله": "trash; garbage", "سطل": "bin; bucket", "کاغذ": "paper",
    "پلاستیک": "plastic", "پلاستیکه": "is plastic (spoken)", "شیشه": "glass",
    "بازیافت": "recycling", "بازیافته": "is for recycling (spoken)",
    "می‌ندازم": "I put / I throw",
    "می‌ندازی": "you put / you throw (informal)", "جمع‌آوری": "collection; pickup",
    "شنبه‌ست": "is Saturday (spoken)",
    # Unit 44 (accommodation).
    "رزرو": "reservation; booking", "صبحانه": "breakfast",
    "صبحانه‌ست": "is breakfast (spoken)", "وای‌فای": "wifi",
    "وای‌فایه": "is the wifi (spoken)", "خروج": "checkout; departure",
    "رستمی": "Rostami (surname)", "ظهره": "is noon (spoken)", "مهمان": "guest",
    "مهمانه": "is a guest (spoken)",
    # Unit 45 (pharmacy).
    "داروخانه": "pharmacy", "قرص": "pill; tablet",
    "قبل": "before (as in 'before food')", "صالحی": "Salehi (surname)",
    # Unit 46 (personal care).
    "سلمانی": "barbershop", "موهام": "my hair", "کوتاه‌تر": "shorter",
    "مثل قبل": "like before", "نوری": "Nouri (surname)",
    # Unit 47 (bike rental).
    "کرایه": "rent; rental fee", "ودیعه": "deposit",
    "کوچیک می‌خوای یا بزرگ؟": "Do you want small or big?",
    "کی پس می‌دم؟": "When do I give it back?", "مرادی": "Moradi (surname)",
    "دوچرخه‌ی": "bicycle of (ezafe-linked form)",
    # Unit 48 (laundry).
    "خشکشویی": "dry cleaner's; laundry shop", "فوری": "express; urgent",
    "فردا ظهر خوبه؟": "Is tomorrow noon good?",
    "کِی می‌گیرم؟": "When do I pick it up?", "کاظمی": "Kazemi (surname)",
    # Unit 49 (swimming pool).
    "بازه": "is open (spoken)", "کمد": "locker",
    "استخر بازه؟": "Is the pool open?", "جعفری": "Jafari (surname)",
    # Unit 50 (restaurant).
    "سفارش": "order (as in 'to order')", "چلوکباب": "chelo kabab",
    "دوغ": "doogh (yogurt drink)", "رحیمی": "Rahimi (surname)",
    # Unit 51 (cinema).
    "سانس": "showtime; screening", "موسوی": "Mousavi (surname)",
    # Unit 52 (museum).
    "موزه": "museum", "نمایشگاه": "exhibition", "قدیمی": "old; historic",
    "فرهادی": "Farhadi (surname)",
    # Unit 53 (concert).
    "کنسرت": "concert", "چه ساعتی؟": "at what time?", "خواننده": "singer",
    "حسینی": "Hosseini (surname)", "شاهین": "Shahin (singer's name)",
    # Unit 54 (park).
    "پیک‌نیک": "picnic", "قدم": "step (as in 'to stroll')",
    "بزنیم": "let's take/hit (subjunctive, as in \"let's stroll\")",
    "درخت": "tree", "ملت": "Mellat (park name; lit. 'nation')",
    # Unit 55 (gym).
    "روزانه": "daily", "وزنه": "weight; weights", "شریفی": "Sharifi (surname)",
    # Unit 56 (beach).
    "ساحل": "beach; shore", "دریا": "sea", "ماسه": "sand",
    "نور": "Noor (beach name; lit. 'light')",
    # Unit 57 (zoo).
    "باغ‌وحش": "zoo", "شیر": "lion", "فیل": "elephant",
    "ارم": "Eram (zoo name)",
    # ---------------------------------------------------------------
    # B1 units 12-16 (real conditions, time clauses, reported messages,
    # purpose clauses, goals and plans), added 2026-07-22, same pass.
    # Unit 12 (real conditions).
    "بارون": "rain (colloquial)", "بیاد": "(that) it come / fall (subjunctive)",
    "داشتی": "you had (informal past)",
    "بده": "give (informal imperative, as in 'send a message')",
    "نتونستی": "you couldn't (informal past)",
    "بیای": "(that) you come (subjunctive, informal)", "می‌رن": "they go",
    "می‌ریم": "we go", "پیامت": "your message (informal)",
    "نتونه": "(that) he/she can't (subjunctive)", "دارن": "they have",
    "پیامش": "his/her message", "بزن": "hit / call (informal imperative)",
    # Unit 13 (time clauses).
    "بشه": "(that) it become / be done (subjunctive)", "رسیدم": "I arrived",
    "دادم": "I gave (as in 'I sent a message')",
    "زدید": "you (polite) called / hit (past)",
    "بدید": "give / let know (polite imperative)",
    "زمان‌بندی": "timing; scheduling", "روشنه": "is clear (spoken)",
    "بزنه": "(that) he/she call / hit (subjunctive)",
    "ساکت": "quiet; silent",
    # Unit 14 (reported messages).
    "عقب": "behind (as in 'to be delayed')",
    "افتاده": "has fallen / has been (as in 'has been delayed')",
    "ازم": "from me (colloquial)", "خواست": "he/she wanted / asked",
    "بزنم": "(that) I call / hit (subjunctive)",
    "بهش": "to him/her (colloquial)", "ازت": "from you (colloquial)",
    "خلاصه": "summary", "پیامی": "a message (indefinite form)",
    "منتقل": "passed on; transferred",
    "خبری": "a piece of news (indefinite form)",
    "داده": "has given (past participle, as in 'has reported')",
    "خواسته": "has asked (past participle)", "آخرش": "in the end; finally",
    "پیام‌ها": "the messages (plural)", "ازش": "from him/her (colloquial)",
    "فرداست": "is tomorrow (spoken)",
    # Unit 15 (purpose clauses).
    "فارسی‌ام": "my Farsi", "جمع": "gathering; saving (as in 'to save up')",
    "بیرون": "outside; out (as in 'to eat out')",
    "اومد": "he/she came (spoken past)", "هدف": "goal; aim", "دوم": "second",
    "یادداشت‌ها": "the notes (plural)",
    "پولی": "financial (indefinite/adjectival form)",
    "اینه": "is this (spoken contraction)", "فارسی‌اش": "his/her Farsi",
    "می‌خوره": "he/she eats", "بتونه": "(that) he/she can (subjunctive)",
    "بتونن": "(that) they can (subjunctive)", "راحت‌تر": "easier; more comfortably",
    "بشم": "(that) I become (subjunctive, as in 'that I pass')",
    # Unit 16 (goals and plans).
    "بتونم": "(that) I can (subjunctive)", "خرج": "spending (as in 'to spend')",
    "بتونیم": "(that) we can (subjunctive)",
    "تقسیم": "division (as in 'to divide up')",
}


# --- 2026-10-19: Farsi B2 tier (units 01-08) ---------------------------------
# Every B2 introduced token absent from FA_GLOSSES above (364 of the 573
# distinct B2 tokens). Each gloss is the atomic English meaning of the sense
# the B2 card actually teaches (read from the card's example sentence and the
# en-fa b2 overlay's teaching glosses), with a form cue where the unit pools
# several forms of one lemma (indefinite -i, ezafe/linked form, person).
# Glosses are English-only (no Persian script), so a multiple_choice option
# never quotes its own answer. None of these tokens occurs at A1-B1 (the
# script would have raised on it), so adding them is purely additive there.
# DRAFT pending native-Persian review, like the B2 units themselves.
FA_GLOSSES.update({
    "شواهد": "evidence",
    "روشنی": "clear (indefinite form, 'some clear ...')",
    "طرح": "plan; scheme",
    "ادامه": "continuation (part of 'to continue')",
    "بدهیم": "(that) we give; let's give (subjunctive)",
    "معتقدم": "I believe",
    "عجولانه": "hasty; rushed",
    "ادعا": "claim",
    "روشن": "clear",
    "قابل": "-able; worthy of (before a noun: 'defensible', 'acceptable')",
    "دفاع": "defense",
    "هزینه‌اش": "its cost",
    "باشد": "(that) it be (subjunctive)",
    "کافی": "enough; sufficient",
    "نداریم": "we don't have",
    "نشان": "showing (part of 'to show')",
    "می‌دهد": "gives (he/she/it)",
    "آمار": "statistics",
    "مطالعه": "study (reading, as in 'study room')",
    "پر": "full; heavily",
    "فضای": "space (linked form, before an adjective)",
    "آرام": "quiet; calm",
    "دانشجوها": "university students",
    "اصلی": "main",
    "امنیت": "safety; security",
    "شبانه": "nighttime; nightly",
    "مثال": "example",
    "هزینه": "cost",
    "نگهبان": "guard",
    "می‌توانیم": "we can",
    "طرفی": "a side (in 'on the one hand; moreover')",
    "کتابخانه": "library",
    "بالاتر": "higher",
    "ورودی": "entrance",
    "می‌ماند": "stays; remains (he/she/it)",
    "ضرر": "harm; loss",
    "تعطیلی": "closing; closure",
    "زودهنگام": "premature; early",
    "دسترسی": "access",
    "خانواده‌ها": "families",
    "طور": "manner; way (in 'specifically')",
    "مشخص": "specific; definite",
    "دانشجوهای": "university students (linked form, before an adjective)",
    "شاغل": "employed; working",
    "می‌کنند": "they do; they make",
    "درست": "true; right",
    "بالاست": "is high",
    "می‌شود": "it is possible; it becomes (he/she/it)",
    "راه‌حل": "solution",
    "کنترل": "control",
    "اعتراض": "objection",
    "درباره": "about; concerning",
    "پاسخ": "response; reply",
    "نتیجه": "result; conclusion",
    "ارزش": "worth; value",
    "بچه‌ها": "children; kids",
    "جایی": "a place; somewhere",
    "باشند": "(that) they be (subjunctive)",
    "شود": "(that) it become; (that) it be done (subjunctive)",
    "نمی‌توانیم": "we cannot",
    "نادیده": "unseen (part of 'to ignore')",
    "مجموع": "total (in 'overall')",
    "ماندن": "staying; remaining (infinitive)",
    "پمپ": "pump",
    "خاطر": "sake (in 'because of')",
    "فرسودگی": "wear and tear",
    "احتمالا": "probably",
    "مدیر": "manager",
    "ساختمان": "building",
    "احتمال": "chance; probability",
    "طبقه": "floor; storey",
    "پایین": "down; lower (in position)",
    "حتما": "surely; definitely",
    "وجود": "existence (in 'there is')",
    "علت": "cause",
    "بو": "smell",
    "معلوم": "known; evident",
    "نشانه": "sign; indication",
    "خرابی": "breakdown; failure",
    "فشار": "pressure",
    "صبح‌ها": "in the mornings",
    "می‌آید": "comes (he/she/it)",
    "می‌آیید": "you come (plural/formal)",
    "بنویسید": "write (plural/formal imperative)",
    "پراستفاده": "widely used; heavily used",
    "مطمئن": "sure; certain",
    "تمام": "finished; over",
    "آسانسور": "elevator; lift",
    "نمی‌تواند": "cannot (he/she/it)",
    "تصادفی": "accidental; by chance",
    "شدن‌ها": "occurrences (plural of 'becoming', in 'outages')",
    "دیوار": "wall",
    "دیده": "seen (past participle)",
    "نشتی": "leak",
    "کوچک": "small",
    "می‌تواند": "can (he/she/it)",
    "خطرناک": "dangerous",
    "بس": "so much (in 'because ... so much')",
    "بالا": "high; up",
    "بوده": "has been (past participle)",
    "آسیب": "damage; injury",
    "بعید": "unlikely",
    "کارشناس": "specialist; expert",
    "حدس": "guess",
    "ممکن": "possible",
    "ضعیف": "weak",
    "پیامد": "consequence",
    "همه": "everyone; all",
    "می‌کشد": "pulls; takes (time, in 'it takes two hours')",
    "بماند": "(that) it remain (subjunctive)",
    "ناراضی‌اند": "they are dissatisfied",
    "قطعی": "outage (in 'power outage')",
    "کم": "low (in amount)",
    "موقت": "temporary",
    "جمله": "sentence",
    "بنویسیم": "(that) we write; let's write",
    "می‌رسد": "reaches; arrives (he/she/it; in 'it seems')",
    "متن": "text",
    "تند": "sharp; harsh (in tone)",
    "نرم‌تر": "softer",
    "لحن": "tone",
    "تاثیر": "effect; impact",
    "بیشتری": "more (indefinite form, 'more of a ...')",
    "بدون": "without",
    "سند": "document (proof)",
    "حدی": "an extent (in 'to some extent')",
    "محترمانه": "respectful",
    "جای": "place; room (linked form, in 'is debatable')",
    "بحث": "debate; discussion",
    "محتاطانه": "cautiously",
    "جواب": "answer",
    "مخالف": "opposed; against",
    "نیستند": "they are not",
    "مگر": "unless (with 'that'); except if",
    "نمی‌اندازیم": "we don't throw (in 'we won't postpone')",
    "باران": "rain",
    "شرطی": "a condition (in 'provided that')",
    "منتشر": "published (part of 'to publish')",
    "دقیق‌تر": "more precise",
    "واژه": "word (formal)",
    "سوءتفاهم": "misunderstanding",
    "مطلق": "absolute",
    "حکم": "ruling; verdict",
    "کاملا": "completely",
    "استثنا": "exception",
    "قانون": "rule; law",
    "موارد": "cases; instances",
    "محدود": "limited",
    "عملی": "practical",
    "دقیقا": "exactly",
    "مشکل‌ساز": "problematic; troublesome",
    "نکته": "point (a detail)",
    "پایان": "end",
    "باعث": "the cause (in 'causes; is the reason for')",
    "ابهام": "ambiguity; uncertainty",
    "زمان": "time",
    "تاکید": "emphasis",
    "خشن": "rough; aggressive",
    "دیگر": "else; other",
    "بگوییم": "(that) we say",
    "تغییری": "a change (indefinite form)",
    "می‌خواهیم": "we want",
    "ساکنان": "residents",
    "واقع": "reality (in 'in fact')",
    "قبلی": "previous",
    "مبهم": "vague; ambiguous",
    "می‌بارید": "was falling (of rain: 'was raining')",
    "خلوت": "quiet; empty (not crowded)",
    "تازه": "just (recently)",
    "نبود": "was not",
    "زمینه": "background",
    "داستان": "story",
    "توضیح": "explanation",
    "رویداد": "event",
    "رخ": "occurrence (part of 'to happen')",
    "همان": "that same; the same",
    "لحظه": "moment",
    "چراغ‌ها": "lights; lamps",
    "خاموش": "off; out (of a light)",
    "صدای": "sound (linked form, 'the sound of')",
    "پشت": "behind",
    "بودند": "they were",
    "مهمان‌ها": "guests",
    "ماندند": "they stayed; they remained",
    "رسیدن": "arriving (infinitive)",
    "سالن": "hall",
    "گذاشته": "put; placed (past participle)",
    "ناگهان": "suddenly",
    "راهرو": "corridor",
    "پیش‌تر": "earlier; previously",
    "زده": "struck (past participle; in 'had talked')",
    "نرسیده": "not arrived (past participle)",
    "گرفتند": "they took; they got (in 'they called')",
    "خیس": "wet",
    "کف": "floor (surface)",
    "داشتیم": "we were (in the middle of)",
    "عکس‌ها": "photos",
    "نصب": "installation (part of 'to install')",
    "می‌کردیم": "we were doing; we used to do",
    "بلندی": "loud (indefinite form, 'a loud ...')",
    "آمد": "came (he/she/it)",
    "گفت‌وگو": "conversation; dialogue",
    "ترتیب": "order; sequence",
    "رویدادها": "events",
    "نوشتم": "I wrote",
    "فهمیدیم": "we realized; we understood",
    "پنجره": "window",
    "مانده": "left; remained (past participle)",
    "پشتی": "back; rear",
    "وسط": "middle",
    "رها": "Raha (name)",
    "قرارمان": "our appointment (our plan to meet)",
    "جایش": "its place (in 'as planned')",
    "بیندازی": "(that) you throw (informal; in 'postpone')",
    "خودمانی": "informal; familiar",
    "اداره": "office (public administration)",
    "ممکنه": "it's possible (spoken)",
    "می‌زنیم": "we strike (in 'we talk')",
    "لطفا": "please",
    "پیامم": "my message",
    "ببین": "see; look (informal imperative)",
    "همکار": "colleague",
    "همکارم": "my colleague",
    "محترمانه‌ای": "respectful (indefinite form, 'a respectful ...')",
    "نوشت": "wrote (he/she)",
    "همکاری": "cooperation",
    "آسان‌تر": "easier",
    "جابه‌جا": "moved; rescheduled (part of 'to move')",
    "دستور": "order; command",
    "بنویس": "write (informal imperative)",
    "سپاسگزارم": "I am grateful",
    "پیگیری": "follow-up",
    "امکان": "possibility",
    "مدارک": "documents",
    "بدهم": "(that) I give; (that) I hand in (subjunctive)",
    "ملاقات": "visit; appointment (official)",
    "سامانه": "system (online portal)",
    "تعویق": "delay (in 'to postpone')",
    "بیندازید": "(that) you throw (formal; in 'postpone')",
    "بررسی": "review; examination",
    "پرونده": "file; case file",
    "نیندازید": "don't throw (formal; in 'don't postpone')",
    "رسمی": "formal; official",
    "رسمی‌تر": "more formal",
    "خواهشمندم": "I kindly request (formal)",
    "اعلام": "announcement (part of 'to announce')",
    "کامل": "complete",
    "صورت": "case (in 'if possible')",
    "ایمیل": "email",
    "خود": "own; oneself",
    "آسیب‌پذیر": "vulnerable",
    "مسئولیت": "responsibility",
    "وظیفه": "duty",
    "دولت": "government",
    "پایدار": "stable; lasting",
    "نمی‌ماند": "does not remain; does not last",
    "اعتماد": "trust",
    "شفافیت": "transparency",
    "جامعه": "society",
    "فرهنگ": "culture",
    "ساخته": "built; made (past participle)",
    "تنهایی": "being alone (in 'by itself')",
    "می‌خواهد": "wants; takes (he/she/it; 'it takes time')",
    "می‌فهمم": "I understand",
    "دیگری": "another; a different (one)",
    "حریم": "boundary; sphere (in 'privacy')",
    "خصوصی": "private",
    "کاربران": "users",
    "نمی‌شود": "one cannot; it is not possible",
    "ساده": "simple; lightly",
    "بخش": "part; section",
    "پرسش": "question (formal)",
    "دیدگاه": "viewpoint",
    "شخصی": "personal",
    "کاربر": "user",
    "انتخاب": "choice",
    "واقعی": "real; genuine",
    "آن": "it; that",
    "گذشت": "passed (in 'pass over')",
    "مردم": "people (the public)",
    "تفاوت": "difference",
    "افراد": "individuals",
    "سرعت": "speed",
    "مهم‌تر": "more important",
    "طولانی": "long; lengthy",
    "معنی": "meaning",
    "تعمیم": "generalization (part of 'to generalize')",
    "هویت": "identity",
    "بخشی": "a part (indefinite form)",
    "فرهنگی": "cultural",
    "رفتار": "behavior",
    "اختلاف": "disagreement; dispute",
    "همزمان": "at the same time",
    "نگاه": "view; way of looking",
    "مرحله‌ای": "in stages; stage by stage",
    "دهیم": "(that) we do; (that) we give (subjunctive, formal)",
    "اجاره": "rent",
    "استودیو": "studio",
    "ماهانه": "monthly",
    "پرداخت": "payment (in 'is paid')",
    "برابر": "equal; equally",
    "شیفت‌ها": "shifts",
    "منصفانه": "fair; fairly",
    "شرایط": "terms (of an agreement)",
    "قرارداد": "contract",
    "متراژ": "floor area (in square metres)",
    "سهم": "share",
    "نفر": "person (counting people)",
    "جدا": "separately",
    "طبیعی": "natural",
    "نامشخص": "not yet determined; unspecified",
    "مبلغ": "amount (of money)",
    "پیش‌پرداخت": "deposit; down payment",
    "شرط": "condition",
    "راه": "way; road",
    "راضی": "satisfied",
    "رابطه": "relationship",
    "مذاکره": "negotiation",
    "ریسک": "risk",
    "مالک": "owner; landlord",
    "امتیاز": "concession; advantage",
    "ضمانت": "guarantee",
    "وسایل": "equipment; belongings",
    "گران": "expensive",
    "می‌خواهم": "I want",
    "ساعت‌ها": "hours",
    "توافق": "agreement",
    "دقیق": "exact; precise",
    "فعلا": "for now",
    "دهد": "(that) he/she do; (that) he/she give (subjunctive, formal)",
    "باغ": "garden",
    "اشاره": "reference (part of 'to refer to')",
    "منبع": "source",
    "محلی": "local",
    "بازسازی": "restoration; renovation",
    "دارند": "they have",
    "نویسنده": "writer; author",
    "منابع": "sources",
    "اجرا": "implementation; carrying out",
    "حالی": "a state (in 'whereas; while')",
    "خوش‌بین": "optimistic",
    "دومی": "the second one",
    "محتاط‌تر": "more cautious",
    "دیوارها": "walls",
    "کشید": "took (time); pulled (he/she/it)",
    "قانع‌کننده‌تر": "more convincing",
    "ادعایش": "his/her claim; its claim",
    "داوری": "judgement; evaluation",
    "پشتیبانی": "support (in 'supported')",
    "ادعای": "claim (linked form, before an adjective)",
    "منبعش": "its source",
    "نام": "name (in 'names; mentions')",
    "می‌برد": "takes; carries (in 'names, mentions')",
    "واقعیت": "reality; the facts",
    "می‌گویند": "they say; they tell",
    "جمع‌بندی": "summing-up; synthesis",
    "بی‌طرف": "impartial; balanced",
    "نقطه": "point (as in 'common ground')",
    "مشترک": "shared; common",
    "اهمیت": "importance",
    "تضاد": "conflict; contradiction",
    "مفیدند": "they are useful",
    "محتاط": "cautious",
    "اطلاعات": "information",
    "تصویر": "picture; image",
    "کامل‌تری": "fuller; more complete (indefinite form)",
    "خواندن": "reading (infinitive)",
})

# Part of speech for the B2 tokens above that are not nouns (fa_part_of_speech
# falls back to "noun"), plus per-B2 POS overrides where an earlier level's
# class is the wrong one for the B2 sense (applied only to level == "b2").
FA_B2_PART_OF_SPEECH = {
    "روشنی": "adjective",
    "بدهیم": "verb",
    "معتقدم": "verb",
    "عجولانه": "adjective",
    "روشن": "adjective",
    "قابل": "adjective",
    "باشد": "verb",
    "کافی": "adjective",
    "نداریم": "verb",
    "می‌دهد": "verb",
    "پر": "adjective",
    "آرام": "adjective",
    "اصلی": "adjective",
    "شبانه": "adjective",
    "می‌توانیم": "verb",
    "بالاتر": "adjective",
    "می‌ماند": "verb",
    "زودهنگام": "adjective",
    "مشخص": "adjective",
    "شاغل": "adjective",
    "می‌کنند": "verb",
    "درست": "adjective",
    "بالاست": "verb",
    "می‌شود": "verb",
    "درباره": "preposition",
    "باشند": "verb",
    "شود": "verb",
    "نمی‌توانیم": "verb",
    "نادیده": "adjective",
    "ماندن": "verb",
    "احتمالا": "adverb",
    "پایین": "adjective",
    "حتما": "adverb",
    "معلوم": "adjective",
    "صبح‌ها": "adverb",
    "می‌آید": "verb",
    "مطمئن": "adjective",
    "تمام": "adjective",
    "نمی‌تواند": "verb",
    "تصادفی": "adjective",
    "دیده": "verb",
    "کوچک": "adjective",
    "می‌تواند": "verb",
    "خطرناک": "adjective",
    "بس": "adverb",
    "بالا": "adjective",
    "بوده": "verb",
    "بعید": "adjective",
    "ممکن": "adjective",
    "ضعیف": "adjective",
    "همه": "pronoun",
    "می‌کشد": "verb",
    "بماند": "verb",
    "ناراضی‌اند": "verb",
    "کم": "adjective",
    "موقت": "adjective",
    "بنویسیم": "verb",
    "می‌رسد": "verb",
    "تند": "adjective",
    "نرم‌تر": "adjective",
    "بیشتری": "adjective",
    "بدون": "preposition",
    "محترمانه": "adjective",
    "محتاطانه": "adverb",
    "مخالف": "adjective",
    "نیستند": "verb",
    "مگر": "particle",
    "نمی‌اندازیم": "verb",
    "منتشر": "adjective",
    "دقیق‌تر": "adjective",
    "مطلق": "adjective",
    "کاملا": "adverb",
    "محدود": "adjective",
    "عملی": "adjective",
    "دقیقا": "adverb",
    "مشکل‌ساز": "adjective",
    "خشن": "adjective",
    "دیگر": "adjective",
    "بگوییم": "verb",
    "می‌خواهیم": "verb",
    "قبلی": "adjective",
    "مبهم": "adjective",
    "می‌بارید": "verb",
    "خلوت": "adjective",
    "تازه": "adverb",
    "نبود": "verb",
    "همان": "pronoun",
    "خاموش": "adjective",
    "پشت": "preposition",
    "بودند": "verb",
    "ماندند": "verb",
    "رسیدن": "verb",
    "گذاشته": "verb",
    "ناگهان": "adverb",
    "پیش‌تر": "adverb",
    "زده": "verb",
    "نرسیده": "verb",
    "گرفتند": "verb",
    "خیس": "adjective",
    "داشتیم": "verb",
    "می‌کردیم": "verb",
    "بلندی": "adjective",
    "آمد": "verb",
    "نوشتم": "verb",
    "فهمیدیم": "verb",
    "مانده": "verb",
    "پشتی": "adjective",
    "رها": "proper_noun",
    "بیندازی": "verb",
    "خودمانی": "adjective",
    "ممکنه": "verb",
    "می‌زنیم": "verb",
    "لطفا": "adverb",
    "ببین": "verb",
    "محترمانه‌ای": "adjective",
    "نوشت": "verb",
    "آسان‌تر": "adjective",
    "جابه‌جا": "adjective",
    "بنویس": "verb",
    "سپاسگزارم": "verb",
    "بدهم": "verb",
    "بیندازید": "verb",
    "نیندازید": "verb",
    "رسمی": "adjective",
    "رسمی‌تر": "adjective",
    "خواهشمندم": "verb",
    "کامل": "adjective",
    "خود": "pronoun",
    "آسیب‌پذیر": "adjective",
    "پایدار": "adjective",
    "نمی‌ماند": "verb",
    "ساخته": "verb",
    "می‌خواهد": "verb",
    "می‌فهمم": "verb",
    "دیگری": "adjective",
    "خصوصی": "adjective",
    "نمی‌شود": "verb",
    "ساده": "adjective",
    "شخصی": "adjective",
    "واقعی": "adjective",
    "آن": "pronoun",
    "گذشت": "verb",
    "مهم‌تر": "adjective",
    "طولانی": "adjective",
    "فرهنگی": "adjective",
    "همزمان": "adverb",
    "مرحله‌ای": "adverb",
    "دهیم": "verb",
    "ماهانه": "adverb",
    "برابر": "adjective",
    "منصفانه": "adjective",
    "جدا": "adverb",
    "طبیعی": "adjective",
    "نامشخص": "adjective",
    "راضی": "adjective",
    "گران": "adjective",
    "می‌خواهم": "verb",
    "دقیق": "adjective",
    "فعلا": "adverb",
    "دهد": "verb",
    "محلی": "adjective",
    "دارند": "verb",
    "خوش‌بین": "adjective",
    "محتاط‌تر": "adjective",
    "کشید": "verb",
    "قانع‌کننده‌تر": "adjective",
    "می‌برد": "verb",
    "می‌گویند": "verb",
    "بی‌طرف": "adjective",
    "مشترک": "adjective",
    "مفیدند": "verb",
    "محتاط": "adjective",
    "کامل‌تری": "adjective",
    "خواندن": "verb",
    # Overrides of earlier-level classes (evidence in FA_B2_GLOSS_OVERRIDES).
    "شیر": "noun",
    "بیاید": "verb",
    "بسته": "adjective",
    "و": "particle",
    "تا": "preposition",
    "اینکه": "particle",
    "البته": "adverb",
    "عقب": "adverb",
    "نه": "particle",
    "نگرانی": "noun",
    "آزادی": "noun",
    "نور": "noun",
    "کاری": "adjective",
}

# Per-B2 gloss overrides: the B2 row of these tokens is keyed (b2, token) and
# its FIRST B2 introduction teaches a different sense than the gloss an
# earlier level registered (e.g. شیر "lion" -> the tap/valve of b2_unit02,
# نه "nine" -> the negation of b2_unit03, خواننده "singer" -> "reader" in
# b2_unit08, آزادی/نور proper nouns -> the common nouns "freedom"/"light").
# Applied only when level == "b2", so no A1-B1 row changes.
FA_B2_GLOSS_OVERRIDES = {
    # English-only re-glosses of earlier-level glosses that quoted Persian
    # script (an MC option must never show its own answer's Persian).
    "تقسیم": "division (part of 'to divide up; to split')",
    "رفته": "gone (past participle)",
    "پیدا": "found (part of 'to find')",
    "شده": "become; happened (past participle)",
    "فکر": "thought (in 'I think')",
    "عوض": "change (part of 'to change; to replace')",
    "می‌کنیم": "we do; we will do",
    "موافق": "in agreement; in favour",
    "وقتی": "when (conjunction)",
    "قبل": "before (in 'before ...ing')",
    "کسی": "someone",
    "بده": "give (informal imperative; in 'let me know')",
    "امکانش": "its possibility (in 'is it possible')",
    "تحویل": "handover (part of 'to submit; to hand in')",
    "حرفت": "your point; what you say (informal)",
    "موافقت": "agreement (consent)",
    "قبول": "acceptance (part of 'to accept')",
    "برنامه": "schedule; programme",
    "حال": "state (in 'however; even so')",
    "بگیریم": "(that) we take (subjunctive; in 'to ignore')",
    "خبر": "news; word (in 'knows about it')",
    "صدا": "sound; noise",
    "شیر": "tap; valve",
    "بیاید": "(that) he/she come (subjunctive)",
    "زد": "struck (he/she, past; in 'guess')",
    "بسته": "closed; shut",
    "سر": "head (in 'noise': head and sound)",
    "و": "and",
    "تا": "to (in 'to some extent'); until",
    "اینکه": "that (in 'unless')",
    "البته": "of course",
    "عقب": "back (in 'to postpone')",
    "شدید": "heavy; severe",
    "نه": "no; not; neither ... nor",
    "نگرانی": "concern; worry",
    "بلند": "long; tall; loud",
    "داد": "gave (he/she, past; also in 'explained', 'happened')",
    "آزادی": "freedom",
    "طرف": "side (in 'on one hand / on the other hand')",
    "چند": "several; how many",
    "گرفت": "took; got (he/she, past)",
    "نور": "light (illumination)",
    "کاری": "work (as an adjective: 'working relationship')",
    "خواننده": "reader",
    "پیشنهاد": "proposal; suggestion",
    # Distinct-gloss refinements (2026-10-19, with the B2 practice tags):
    # keep every typed-translation prompt answerable by ONE B2 token across
    # the whole B2 course (vaght vs zaman/zamanbandi, masaleh vs moshkel,
    # rahat-tar vs asan-tar, zang vs tamas).
    "وقت": "time (slot)",
    "مسئله": "issue; matter",
    "زمان‌بندی": "scheduling",
    "راحت‌تر": "more comfortably; more at ease",
    "زنگ": "ring; ringing (of a bell or phone)",
}

FA_SYMBOLS = set("س ل ا م ن ت ش چ ی ه ک گ ج د ر ف و ب خ ز".split())
FA_PROPER_NOUNS = set(
    "علی نرگس سارا مینا ایران انگلیس فرانسه آزادی رضا تهران نگار آرش "
    "مریم نیما".split()
    # A2 units 11-18, added 2026-07-11.
    + ["دکتر رضایی", "اصفهان"]
    # B1 unit05 (workplace), added 2026-07-11: حسین (Hossein), a colleague
    # named in the responsibility/status-update dialogue.
    + ["حسین"]
    # A1 units 26/40-57, added 2026-07-22: the pet name پشمک, the surnames
    # of the service-counter characters units 40-55 each introduce (Karimi,
    # Ahmadi, Rezaei, Sadeghi, Rostami, Salehi, Nouri, Moradi, Kazemi,
    # Jafari, Rahimi, Mousavi, Farhadi, Hosseini), the singer شاهین, and the
    # three real Tehran place names used on this pack's signs (پارک ملت,
    # ساحل نور, باغ‌وحش ارم). رضایی is the bare surname; the multi-word
    # "دکتر رضایی" already above stays as its own established entry.
    + ["پشمک", "کریمی", "احمدی", "رضایی", "صادقی", "رستمی", "صالحی",
       "نوری", "مرادی", "کاظمی", "جعفری", "رحیمی", "موسوی", "فرهادی",
       "حسینی", "شریفی", "شاهین", "ملت", "نور", "ارم"]
)
FA_PRONOUNS = set(
    "من تو شما او ما این همون چی چه کی همین کدوم اون چقدر".split()
    + ["چی؟"]
    # B1 units 01/06 (necessity/narrative), added 2026-07-11: اونا (they,
    # informal plural, sibling of او/اونا already established), هیچی
    # (anything/nothing, indefinite pronoun), چه‌وقت (when, interrogative
    # pronoun, same class as the already-established کی).
    + ["اونا", "هیچی", "چه‌وقت"]
    # B1 units 07-11 ("second wave"), added 2026-07-11: همدیگه
    # ("each other", reciprocal pronoun), هیچ‌کدوم ("neither one", same
    # class as the already-established کدوم), کسی ("someone/the person",
    # indefinite relative antecedent), خودش ("himself/herself", reflexive
    # pronoun), کِی ("when", explicit-kasre variant of the already-
    # established کی, disambiguating "when" from "who"), کیا ("who",
    # colloquial plural interrogative).
    + ["همدیگه", "هیچ‌کدوم", "کسی", "کِی", "خودش", "کیا"]
)
FA_PREPOSITIONS = set(
    "به از با اهل بهت مثل کنار برای برات پیش در بالای".split()
    # A2 units 11-18, added 2026-07-11: به خاطر (because of, + noun,
    # distinct from چون which takes a full clause), روی (on top of/onto),
    # بهتون (to you, polite -- same class as the already-established
    # informal بهت).
    + ["به خاطر", "روی", "بهتون"]
    # B1 units 07-11 ("second wave"), added 2026-07-11: درباره‌ی
    # ("about", ezafe-linked), باهاش/باهاشون ("with him-her"/"with them",
    # colloquial pronoun-incorporated forms of با), توش ("in it",
    # colloquial pronoun-incorporated تو), درباره‌ش ("about him/her/it",
    # colloquial pronoun-incorporated درباره‌ی), بهم/بهشون ("to me"/"to
    # them", colloquial pronoun-incorporated به, sibling of the already-
    # established بهت/بهتون).
    + ["درباره‌ی", "باهاش", "توش", "درباره‌ش", "باهاشون", "بهم", "بهشون"]
    # B1 unit14 (reported messages), added 2026-07-22: ازم/ازت/ازش ("from
    # me / from you / from him-her") and بهش ("to him/her") are the same
    # colloquial pronoun-incorporated class as the already-established
    # بهم/بهت/بهتون/باهاش above.
    + ["ازم", "ازت", "ازش", "بهش"]
    # A1 unit31 (celebrations), added 2026-07-12: براش is the third-person
    # sibling of the already-established برات ("for you").
    + ["براش"]
)
FA_PARTICLES = set(
    "هم ولی بله و آره پس تا یه یا چون رو خب چشم "
    # Unit 22 (A1: phone), added 2026-07-09: الو is the phone-answering
    # interjection ("hello?"), same class as other interjection-like
    # particles already in this set.
    "الو".split()
    # A2 units 11-18, added 2026-07-11: اگر (if, conditional conjunction),
    # که (that/which/so that, subordinating conjunction), را (formal
    # object marker, same class as the already-established colloquial رو).
    + ["اگر", "که", "را"]
    # B1 units 03/06 (hypotheticals/narrative), added 2026-07-11: اگه
    # (if, colloquial spoken variant of the already-established formal
    # اگر), وقتی (when, temporal subordinating conjunction, same class
    # as the already-established چون).
    + ["اگه", "وقتی"]
    # B1 units 07-11 ("second wave"), added 2026-07-11: کاش ("if
    # only / I wish", wish particle), هرچند ("although", concessive
    # subordinator), اما ("but", contrastive, sibling of the already-
    # established ولی), اینکه ("that", complementizer in با اینکه, "even
    # though"), آیا (yes-no question particle).
    + ["کاش", "هرچند", "اما", "اینکه", "آیا"]
)
FA_ADVERBS = set(
    "فعلاً خیلی چطور کجا اینجا همین‌طور کجایی باهم فردا حتماً خودمونی چند "
    "اونجا مستقیم بعد لطفاً امروز الان کیلویی نقدی زیادی بیشتر چرا "
    "یکم دیر چندم بعدش یه‌کم دیرتر چیکار معمولاً شب‌ها دیروز "
    # Unit 22 (A1: phone), added 2026-07-09.
    "آهسته‌تر بعداً "
    # Unit 23 (A1: emotions), added 2026-07-09.
    "زیاد فقط "
    # Unit 24 (A1: hobbies), added 2026-07-09.
    "گاهی".split()
    # A2 units 11-18, added 2026-07-11: دیگه (another/more/next), حداقل
    # (at least/minimum), زودتر (earlier/sooner), دوباره (again), متاسفانه
    # (unfortunately), حدود (about/approximately), اول (first), در آخر
    # (finally/at the end), در طول هفته (during the week) -- all function
    # as sentence-level adverbial modifiers, same class as بیشتر/چند
    # already in this set.
    + ["دیگه", "حداقل", "زودتر", "دوباره", "متاسفانه", "حدود", "اول",
       "در آخر", "در طول هفته"]
    # B1 units 01-05, added 2026-07-11: امشب (tonight), امسال (this
    # year), پارسال (last year), به‌موقع (on time), کمتر (less, sibling
    # of the already-established comparative بیشتر), حالا (now, sibling
    # of the already-established الان), شاید (maybe), همینطور
    # (likewise -- a genuinely distinct string from the already-
    # established همین‌طور, which has a ZWNJ; not a duplicate), هنوز
    # (still/yet).
    + ["امشب", "امسال", "پارسال", "به‌موقع", "کمتر", "حالا", "شاید",
       "همینطور", "هنوز"]
    # B1 units 07-11 ("second wave"), added 2026-07-11: دیشب ("last
    # night"), تنها ("alone"), بعضی/بعضی وقتا ("some"/"sometimes",
    # quantifier-adverbs, same class as the already-established چند),
    # بازم ("still/also", colloquial), همچنین ("also/likewise", sibling
    # of the already-established هم/همینطور), واقعاً ("really"), با هم
    # ("together"), همیشه ("always"), کمی ("a little").
    + ["دیشب", "کمی", "تنها", "بعضی", "بازم", "بعضی وقتا", "همچنین", "واقعاً", "با هم", "همیشه"]
    # A1 units 34-36, added 2026-07-12.
    + ["زود", "تقریباً", "اصلاً", "هیچ‌وقت", "برای همین"]
    # A1 units 28/45 and B1 units 14/15, added 2026-07-22: پیاده ("on
    # foot", manner adverb), قبل ("before", same temporal class as the
    # already-established بعد), عقب ("behind", in عقب افتادن), آخرش ("in
    # the end", sentence adverb like the already-established بعدش) and
    # بیرون ("outside/out", in بیرون غذا می‌خورم).
    + ["پیاده", "قبل", "عقب", "آخرش", "بیرون"]
)
FA_ADJECTIVES = set(
    "خوبی بد ایرانی انگلیسی فرانسوی بزرگه کوچیکه متأهل مجرد برعکسه شلوغه "
    "آفتابی بارونی ابری برفی گرم سرد خنک نزدیک خوشمزه ملی قدیم جدید موافق "
    "تعطیل هجری شمسی دهم هشتم بیدار هر خوب "
    # Unit 20 (A1: clothing), added 2026-07-09: colors and sizes function
    # attributively (پیراهن قرمز, سایز بزرگ), same class as the weather
    # adjectives (آفتابی/بارونی/...) already in this set.
    "قشنگ قرمز آبی سیاه سفید بزرگ کوچیک متوسط "
    # Unit 21 (A1: money), added 2026-07-09: خرد modifies پول attributively
    # (پول خرد, "small/change money"), same attributive-adjective class.
    "خرد "
    # Unit 22 (A1: phone), added 2026-07-09: قطع/وصل are predicate
    # adjectives with میشه ("cuts in and out"); بهتر is the plain
    # (non-contracted) form of the already-established بهتره.
    "قطع وصل بهتر "
    # Unit 23 (A1: emotions), added 2026-07-09: the 6 core feeling words,
    # all attributive/predicate adjectives (من خوشحالم, تو نگرانی, etc.).
    "خوشحال ناراحت خسته گشنه عصبانی نگران "
    # Unit 24 (A1: hobbies), added 2026-07-09: آزاد modifies وقت
    # attributively (وقت آزاد, "free time").
    "آزاد".split()
    # A2 units 11-18, added 2026-07-11: باز (open), جدیدم (colloquial
    # possessive of جدید), لازم (necessary), آماده (ready), شدیدی/شدید
    # (severe), خراب (broken), لغو (cancelled), جایگزین/جایگزینی
    # (alternative), فنی (technical), منتظر (waiting), اجتماعی (social),
    # مفید (useful), سرگرم‌کننده (entertaining), تمیز (clean), مناسب
    # (suitable), تیمی (team-related), بانکی (banking/bank, adjectival
    # form of بانک).
    + ["باز", "جدیدم", "لازم", "آماده", "شدیدی", "شدید", "خراب", "لغو",
       "جایگزین", "جایگزینی", "فنی", "منتظر", "اجتماعی", "مفید",
       "سرگرم‌کننده", "تمیز", "مناسب", "تیمی", "بانکی"]
    # B1 units 01/05, added 2026-07-11: شلوغ (busy/crowded, bare form of
    # the already-established colloquial contraction شلوغه), تموم
    # (finished/done, participial adjective -- combines with کنم/کنه to
    # form "finish"), مهم (important), مسئول (responsible).
    + ["شلوغ", "تموم", "مهم", "مسئول"]
    # B1 units 07-11 ("second wave"), added 2026-07-11: خالی ("empty"),
    # دلتنگ ("homesick/longing"), سخت‌تر ("harder", bare comparative,
    # distinct from the already-established -e-copula-contracted
    # comparatives like بزرگ‌تره), موکول ("postponed", participial
    # adjective, same class as the already-established لغو) and برگزار
    # ("held/organized", same class), بعدی ("next"), صمیمی
    # ("close/intimate"), مهربون ("kind"), کوچیکی (indefinite adjective
    # form of the already-established کوچیک), آروم ("calm/quiet").
    + ["خالی", "دلتنگ", "سخت‌تر", "موکول", "بعدی", "برگزار", "صمیمی", "مهربون", "کوچیکی", "آروم"]
    # A1 units 31/36, added 2026-07-12: celebration/personality
    # adjectives in bare attributive form. Their fused copula forms are
    # classified as verbs below, following the existing course precedent.
    + ["مبارک", "بامزه", "خجالتی", "جدی", "زرنگ", "تنبل", "زحمت‌کش", "صبور", "باحال"]
    # A1 units 25-57 and B1 units 13-15, added 2026-07-22. Attributive/
    # predicate adjectives: the appearance words (بلند/کوتاه/مشکی/بلوند/
    # قهوه‌ای/سبز, unit25 -- same attributive class as unit20's own color
    # adjectives) and unit37's five new colors (زرد/نارنجی/صورتی/بنفش/
    # خاکستری); خونگی (in حیوان خونگی, 'pet') and خوشگل (unit26); گم/پیدا
    # (participial adjectives completing گم کردن/پیدا کردن, same class as
    # the already-established تموم) plus the sign forms گمشده/پیداشده
    # (unit40); کوتاه‌تر (unit46) and راحت‌تر (B1 unit15), bare comparatives
    # like the already-established سخت‌تر; فوری (unit48); قدیمی (unit52);
    # روزانه (unit55, in کارت روزانه); دوم (B1 unit15) -- ordinal, same
    # class as the already-established دهم/هشتم; ساکت (B1 unit13); منتقل
    # (B1 unit14), participial like the already-established موکول; پولی
    # (B1 unit15, in هدف پولی, 'a financial goal'). Their fused copula
    # forms are classified as verbs below, following course precedent.
    + ["بلند", "کوتاه", "مشکی", "بلوند", "قهوه‌ای", "سبز", "خونگی",
       "خوشگل", "زرد", "نارنجی", "صورتی", "بنفش", "خاکستری", "گم",
       "پیدا", "گمشده", "پیداشده", "کوتاه‌تر", "فوری", "قدیمی",
       "روزانه", "ساکت", "منتقل", "پولی", "راحت‌تر", "دوم"]
)
FA_NUMBERS = set(
    "صفر یک دو سه چهار پنج شش هفت هشت نه ده یازده دوازده سیزده چهارده "
    "پانزده شانزده هفده هجده نوزده بیست سی چهل پنجاه شصت هفتاد هشتاد نود "
    # Unit 21 (A1: money), added 2026-07-09.
    "صد"
    .split()
    # A2 unit 15 (travel disruption), added 2026-07-11: نُه is the
    # vocalized spelling of "nine" this unit deliberately uses to avoid
    # colliding with the plain, unvocalized نه ("no") -- see
    # NO_NEGATION_LESSONS below for the reverse collision this unit's own
    # spelling choice avoids.
    + ["نُه"]
)
FA_VERBS = {
    "می‌کنم", "حالتون", "چطوره", "خوبم", "آمدید", "داشته", "باشید",
    "چطوری", "نیستم", "بفرمایید", "دارید", "نکشید", "هستم", "خوشوقتم",
    "باید", "بروم", "است", "ساراست", "چیه", "هستی", "هست",
    "ایرانیه", "هستید", "هستین", "ایرانی‌ام", "ببخشید", "فارسیه",
    "چنده", "سالته", "سالمه", "می‌خوام", "تومنه", "کنیم", "باشه",
    "شماره‌ام", "هشته", "بنویسم", "درسته", "یکه", "می‌زنم", "کن",
    "دارم", "ندارم", "دارد", "ندارد", "نداره", "داره", "متأهله",
    "متأهلین", "مجردم", "متأهلم", "خانواده‌ته", "مامانمه", "باباهم", "کیه",
    "داداشمه", "پدرن", "مادرن", "نفرن", "نفریم", "داری",
    "کجاست", "راسته", "چپه", "برید", "رستورانه",
    # Units 6-8, added 2026-07-06.
    "می‌خواستم", "می‌کنید", "خوبه", "بود", "میارم", "اومدید",
    "آفتابیه", "سرده", "بارونیه", "بهتره", "ببریم", "بپوشیم", "کنم",
    "موافقم", "گرمه", "عالیه", "بریم", "می‌بینمت", "می‌دید", "می‌گیرید",
    # Units 9-10 (A2), added 2026-07-06.
    "بگیرم", "کردم", "می‌شه", "بگید", "بیارم", "بیارید", "برمیاد",
    "می‌تونم", "بیام", "کافیه", "باشم", "ببینم", "می‌گیره",
    # Unit 09 (A1: time), added 2026-07-07.
    "نیمه", "میشه", "چهاره", "میام", "نیست",
    # Unit 10 (A1: dates), added 2026-07-07.
    "هفتگیه", "می‌کنه", "چندشنبه‌ست", "اردیبهشته", "روزه", "سه‌شنبه‌ست",
    # Unit 11 (A1: routines), added 2026-07-07.
    "می‌شم", "می‌خورم", "میرم", "می‌خوابم", "می‌شی", "شدن", "می‌کنی",
    "می‌خوابه",
    # Units 12-15 (A1: plans, past events, preferences, comparisons),
    # added 2026-07-07 by the parallel practice-content-gap-closing pass.
    # Colloquial -e/-ست copula-contraction predicates (خوشمزه‌ست/جالبه/
    # the 8 comparative forms) are classified verb here, matching the
    # already-established precedent for this exact contraction class
    # (آفتابیه/سرده/بارونیه/گرمه/بهتره, unit07's own review notes: "part
    # of speech verb, not adjective, matching how the realization/
    # overlay's own review notes classify these as spoken copula
    # contractions").
    "چطوره؟", "می‌خوای", "قبوله", "متأسفم", "نمی‌تونم", "منتظرم",
    "رفتم", "خوردم", "دیدم", "کردی", "خوندم", "موندم",
    "رفت", "دید", "کرد", "موند", "خوند",
    "خوشمزه‌ست", "جالبه",
    "بزرگ‌تره", "کوچیک‌تره", "گرون‌تره", "ارزون‌تره", "بلندتره", "جوون‌تره",
    "بدتره",
    # Unit 16 (A1: travel), added 2026-07-07.
    "می‌خواید",
    # Unit 17 (A1: health), added 2026-07-07.
    "خسته‌ام", "می‌تونی", "کنی", "بخور",
    # Unit 18 (A1: work), added 2026-07-07. مهندسم/معلمم/دکترم/مهندسه/معلمه
    # are colloquial copula contractions (X + هستم/است), matching this
    # course's own established precedent that such contractions are
    # classified verb, not noun/adjective (see the آفتابیه/سرده/بارونیه/
    # گرمه precedent noted above).
    "مهندسم", "معلمم", "دکترم", "مهندسه", "معلمه",
    # Unit 19 (A1: housing), added 2026-07-07, same precedent as above.
    "تخته", "آشپزخانه‌س",
    # Unit 20 (A1: clothing), added 2026-07-09, same colloquial -e-copula-
    # contraction precedent as آفتابیه/سرده/بارونیه/گرمه above.
    "قشنگه",
    # Unit 21 (A1: money), added 2026-07-09. بردارم (I withdraw, 1st
    # person subjunctive) and کنید (you do, polite/plural subjunctive --
    # additive on top of کنم/کنی's already-established precedent).
    "بردارم", "کنید",
    # Unit 22 (A1: phone), added 2026-07-09. منم (colloquial "it's me"
    # copula contraction), زدن (infinitive, "to ring/hit" -- part of
    # زنگ زدن), بیا (imperative "come"), شد (past "became/happened"),
    # می‌کنیم (we do, 1st person plural), میرن (they go, informal --
    # from this unit's own grammar_note card, explicitly labeled
    # colloquial there).
    "منم", "زدن", "بیا", "شد", "می‌کنیم", "میرن",
    # Unit 23 (A1: emotions), added 2026-07-09. Colloquial -am/-i/-e
    # copula contractions (خوشحالم/ناراحتم/گشنه‌ام/عصبانی‌ام/نگرانی/
    # تعطیله/خسته‌ست/خوشحاله), same established precedent as خسته‌ام/
    # آفتابیه/سرده/بارونیه/گرمه above. کرده is the past-perfect "has done."
    "خوشحالم", "ناراحتم", "گشنه‌ام", "عصبانی‌ام", "نگرانی",
    "تعطیله", "خسته‌ست", "خوشحاله", "کرده",
    # Unit 24 (A1: hobbies), added 2026-07-09. خوندن/دیدن (infinitives,
    # same class as unit22's already-established زدن precedent), می‌دم/
    # می‌بینم/می‌خونه/می‌رم (conjugated verb forms).
    "خوندن", "دیدن", "می‌دم", "می‌بینم", "می‌خونه", "می‌رم",
    # A2 unit 11 (banking), added 2026-07-11 (A2 units 11-18 backfill
    # pass). کردن (infinitive "to do", same class as the already-
    # established شدن precedent); لازمه/صبحه are colloquial -e-copula-
    # contraction predicates, same precedent as آفتابیه/سرده/بارونیه/
    # گرمه above.
    "کردن", "می‌تونید", "لازمه", "بکنم", "آوردم", "می‌گیرم",
    # A2 unit 12 (doctor), added 2026-07-11.
    "گفت", "بخورم", "صبحه", "بیایید", "نشد", "بگیرید", "شده", "سردرده",
    "شدیده", "داشت", "کند",
    # A2 unit 13 (maintenance), added 2026-07-11.
    "زدم", "زد", "بیاید", "میاد", "این‌طوریه", "میره", "خونه‌ام",
    "می‌بینمتون",
    # A2 unit 14 (job interview), added 2026-07-11. خوبم is the colloquial
    # "I'm good (at)" copula contraction, same precedent as خسته‌ام above.
    "خوبم",
    # A2 unit 15 (travel disruption), added 2026-07-11. هست is the plain
    # existential copula ("there is/exists").
    "هست", "برسم", "بخرید", "می‌مونم",
    # A2 unit 16 (online habits), added 2026-07-11. مفیده/اینستاگرامه are
    # colloquial -e-copula-contraction predicates, same precedent as
    # آفتابیه/سرده/بارونیه/گرمه above.
    "مفیده", "می‌خونم", "می‌کند", "اینستاگرامه",
    # A2 unit 18 (shopping complaint), added 2026-07-11. خرابه is the
    # same colloquial -e-copula-contraction precedent as خراب above's
    # sibling unit13 قشنگه/etc.
    "خرابه", "دادن", "بدم", "خریدم", "داد", "خریدینش", "خریدمش", "بدیم",
    # B1 unit01 (necessity), added 2026-07-11. برم/بری/بره/برن (subjunctive
    # "go" paradigm, sibling of the already-established formal بروم and
    # subjunctive بریم/برید), نباید (must not, sibling of the already-
    # established باید), نرفتم (didn't go), کنه (subjunctive "that he/she
    # do", sibling of the already-established کنم/کنی/کنید/کنیم), بمونم
    # (subjunctive "that I stay").
    "برم", "بری", "بره", "برن", "نباید", "نرفتم", "کنه", "بمونم",
    # B1 unit02 (abilities), added 2026-07-11. می‌تونه/می‌تونیم/می‌تونن
    # (ability paradigm, sibling of the already-established می‌تونم/
    # می‌تونی/می‌تونید), کنن (subjunctive "that they do", completing the
    # کنم/کنی/کنه/کنیم/کنید paradigm), می‌تونستم/نمی‌تونستم/نمی‌تونست
    # (past-ability forms), درستش (object-suffixed subjunctive "fix it"),
    # بخرم (subjunctive "that I buy"), حاضره (colloquial -e-copula-
    # contraction predicate, same precedent as آفتابیه/سرده/بارونیه/گرمه
    # above), نداشت (he/she didn't have, past), گرفت (got/received,
    # past).
    "می‌تونه", "می‌تونیم", "می‌تونن", "کنن", "می‌تونستم", "نمی‌تونستم",
    "درستش", "بخرم", "حاضره", "نمی‌تونست", "نداشت", "گرفت",
    # B1 unit03 (hypotheticals), added 2026-07-11. باشی/باشیم/باشن
    # (subjunctive "be" paradigm, sibling of the already-established
    # داشته/باشید), می‌خرم/می‌خری/می‌خره/می‌خریم/می‌خرید/می‌خرن (indicative
    # "buy" paradigm), داشتم/نداشتم (I had / I didn't have, past),
    # می‌خریدم (I would buy / would have bought), نداشته (negative
    # participle "not having", sibling of the already-established
    # داشته), نمی‌خرم (I won't buy), امیدوارم (I hope, colloquial -am
    # copula contraction, same precedent as خوشحالم/تنهام).
    "باشی", "باشیم", "باشن", "می‌خرم", "می‌خری", "می‌خره", "می‌خریم",
    "می‌خرید", "می‌خرن", "داشتم", "نداشتم", "می‌خریدم", "نداشته",
    "نمی‌خرم", "امیدوارم",
    # B1 unit04 (debate), added 2026-07-11. موافقی/موافقه/موافقیم/
    # موافقید/موافقن (agreement paradigm, sibling of the already-
    # established موافقم), مخالفم/مخالفه (disagreement, same paradigm),
    # سخته/تنهام/تنهاست (colloquial copula-contraction predicates, same
    # precedent as آفتابیه/سرده/بارونیه/گرمه/ساراست above).
    "موافقی", "موافقه", "موافقیم", "موافقید", "موافقن", "مخالفم",
    "مخالفه", "سخته", "تنهام", "تنهاست",
    # B1 unit05 (workplace), added 2026-07-11. هستیم/هستن (be paradigm,
    # sibling of the already-established هستم/هستی/هستید/هستین), تمومه
    # (colloquial -e-copula-contraction predicate, same precedent as
    # تخته/آشپزخانه‌س above).
    "هستیم", "هستن", "تمومه",
    # B1 unit06 (narrative), added 2026-07-11. گفتم/گفتی (I/you said,
    # sibling of the already-established گفت), می‌رسم/می‌رسه (will
    # arrive), نگفت (he/she didn't say), می‌رفت (he/she was going,
    # sibling of the already-established می‌رفتم).
    "گفتم", "گفتی", "می‌رسم", "می‌رسه", "نگفت", "می‌رفت",
    # B1 units 07-11 ("second wave"), added 2026-07-11: the بودم/بودی/
    # بود/بودیم/بودید/بودن past-tense "to be" paradigm (unit07, used
    # bare with an atomic "I was"/"you were"/etc. gloss -- the کاش-wish
    # meaning comes from the grammar construction, not baked into the
    # token gloss, same discipline as the already-established
    # داشتم/می‌خریدم precedent); رفته/نرفته (pluperfect participles);
    # می‌دیدم/نمی‌دیدم (imperfect "would see"); the rest are ordinary
    # conjugated verb forms, colloquial copula contractions (سارا‌ست/
    # همونه/روزیه, same precedent as آفتابیه/سرده/بارونیه/گرمه), or
    # subjunctive forms following the established کنم/کنی/... paradigm
    # pattern.
    "بودم", "بودی", "بودیم", "بودید", "بودن", "رفته", "می‌دیدم", "نرفته", "نمی‌دیدم", "نیومد", "نیومدم", "بپرسم", "ببینیم", "نتونستم", "می‌دونم", "گذاشتن", "نرفت", "ببینن", "می‌گه", "می‌مونه", "می‌ده", "گفتن", "نکردن", "بیایم", "بفرستید", "بگیریم", "می‌خواد", "کردید", "روزیه", "بفرسته", "گرفتیم", "سارا‌ست", "شدم", "بگم", "همونه", "می‌رفتیم", "برگردم", "می‌کردم", "می‌کرد", "می‌کردن", "برگرده", "پرسید", "میای", "میری", "می‌ره", "گفتیم", "داریم", "گفتید", "میاید", "گفته",
    # A1 units 31-36, added 2026-07-12. Includes ordinary conjugated
    # verbs, infinitives, light-verb compounds, and colloquial fused
    # copula predicates, matching the existing precedent for earlier A1
    # units' -ه/-ست contractions.
    "تولدمه", "کِیه", "نیماست", "می‌شورم", "می‌شوره", "می‌کنن",
    "آرومه", "ماست", "پارکه", "نزدیکه", "بفرستم", "می‌فرستم",
    "فرستادن", "گرفتن", "می‌فرستمش", "می‌فرسته", "خرد می‌کنم",
    "می‌ریزم", "سرخ می‌کنم", "خرد کردن", "سرخ کردن", "ریختن",
    "سرخش", "می‌پزه", "آماده‌ست", "می‌پزی", "می‌پزم",
    "آشپزخانه‌ست", "می‌ریزه", "دوست دارم", "وقت ندارم", "بپز",
    "مهربونه", "بامزه‌ست", "خجالتیه", "جدیه", "تنبل نیست",
    "صبوره", "زحمت‌کشه", "چه جوریه", "زرنگه", "آشنا بشم",
    "باحاله", "حرف نمی‌زنه", "فکر می‌کنم", "زحمت‌کشم",
    # A1 units 25-30, added 2026-07-22. Mostly colloquial -e/-ست copula
    # contractions (بلنده/کوتاهه/مشکیه/بلونده/قهوه‌ایه/سبزه/آبیه/سفیده/
    # پشمکه/منه/سگمه/خوشگله/ورزشه/ریاضیه/چقدره), same long-established
    # precedent as آفتابیه/سرده/بارونیه/گرمه; the rest are ordinary
    # conjugated forms.
    "بلنده", "کوتاهه", "مشکیه", "بلونده", "قهوه‌ایه", "سبزه", "آبیه",
    "می‌زنه", "شکلیه", "رنگیه", "سفیده", "پشمکه", "منه", "سگمه",
    "خوشگله", "می‌ری", "چقدره", "ورزشه", "می‌خونی", "ریاضیه",
    # A1 units 37-57, added 2026-07-22, same contraction precedent
    # (سیاهه/قرمزه/زرده/نارنجیه/صورتیه/بنفشه/خاکستریه/اونجاست/برفیه/
    # اورژانسه/پلاستیکه/بازیافته/شنبه‌ست/صبحانه‌ست/وای‌فایه/مهمانه/ظهره/
    # بازه/آزادم/آزادید) plus ordinary verbs and the two multi-word light
    # verbs دوست داری/دوست دارد (siblings of the established دوست دارم)
    # and the negated predicate سرد نیست (sibling of تنبل نیست).
    "سیاهه", "قرمزه", "زرده", "نارنجیه", "صورتیه", "بنفشه", "خاکستریه",
    "دوست دارد", "دوست داری", "سرد نیست", "اونجاست", "برفیه",
    "اورژانسه", "بزنید", "دیدید", "آزادم", "آزادید", "پلاستیکه",
    "بازیافته", "می‌ندازم", "می‌ندازی", "شنبه‌ست", "صبحانه‌ست",
    "وای‌فایه", "مهمانه", "ظهره", "بازه", "بزنیم",
    # B1 units 12-16, added 2026-07-22: the conditional/temporal
    # subjunctive paradigm (بیاد/بیای/بشه/بشم/بزنه/بزنم/نتونه/نتونستی/
    # بتونم/بتونیم/بتونه/بتونن), colloquial imperatives (بده/بزن/بدید),
    # ordinary past/present forms, and the copula contractions
    # فرداست/اینه/روشنه (same precedent as ساراست/همونه).
    "بیاد", "داشتی", "بده", "نتونستی", "بیای", "می‌رن", "می‌ریم",
    "نتونه", "دارن", "بزن", "بشه", "رسیدم", "دادم", "زدید", "بدید",
    "روشنه", "بزنه", "افتاده", "خواست", "بزنم", "داده", "خواسته",
    "فرداست", "اومد", "اینه", "می‌خوره", "بتونه", "بتونن", "بشم",
    "بتونم", "بتونیم",
}
FA_PHRASE_PARTS = {"بخیر", "خواهش"}
# Multi-word tokens a realization introduces as ONE vocabulary item that
# are not verb phrases (those go in FA_VERBS above, e.g. دوست دارم) --
# question frames, noun phrases and whole set phrases. Classified "phrase"
# so a word-level practice slot (noun/adjective/verb) can never draw a
# whole sentence into a single-word frame. Added 2026-07-22 with A1 units
# 25-57; earlier multi-word entries are deliberately left at their
# established classification (changing one would orphan its existing DB
# row, which main() matches on token+part_of_speech).
FA_MULTIWORD_PHRASES = {
    "گربه‌ی من", "چه رنگیه", "چه رنگی", "تو خونه", "چهار فصل",
    "کدوم فصل", "تو چی؟", "مثل قبل", "کوچیک می‌خوای یا بزرگ؟",
    "کی پس می‌دم؟", "فردا ظهر خوبه؟", "کِی می‌گیرم؟", "استخر بازه؟",
    "چه ساعتی؟",
}
# B1 units 07-11 ("second wave"), added 2026-07-11: عین (only ever
# appears here as part of در عین حال, "nevertheless" -- meaningless
# alone in this corpus, same class as بخیر/خواهش) and من و (an
# incomplete fragment, "... and I", that only makes sense followed by
# a name, e.g. من و مریم, "Maryam and I").
FA_PHRASE_PARTS |= {"عین", "من و"}

# تو is a genuine homograph across this whole course: the informal
# second-person PRONOUN "you" everywhere else, but a spatial/abstract
# PREPOSITION "in / inside / within" in these specific lessons --
# unit19's own "تو آشپزخانه" locational sense (the original case this
# split was built for), plus two more instances found while adding A2
# units 11-18 (2026-07-11): unit14's "تو کار تیمی ... خوبم" ("good AT
# teamwork") and unit18's "تو مهلت هفت روزه هستید" ("within the seven-
# day window") -- both abstract, non-locational uses of the same
# preposition sense, and both introduce تو itself as a real vocabulary
# item in this sense (present in introduced_tokens), not the pronoun.
# Listed by LESSON, not a single content_key, since a lesson can reuse
# the preposition sense across more than one card (unit14's turn02 AND
# turn04 both use it).
TOO_PREPOSITION_LESSONS = {
    "fa.a1.unit19.lesson04.location_in_home",
    "fa.a2.unit14.lesson04.interview_dialogue",
    "fa.a2.unit18.lesson04.shop_return_counter_dialogue",
    # B1 units 07-11 ("second wave"), added 2026-07-11: two more instances
    # found while adding this pass, both confirmed by the units' own
    # fresh-context review notes -- unit09's "تو جلسه شرکت کردید" ("you
    # participated IN the meeting," paired with the formal شرکت کردید, NOT
    # an informal-pronoun slip per the review's own explicit check) and
    # unit10's "دوستی که تو دانشگاه درس می‌خونه" ("the friend who studies
    # AT university"). Both are the same abstract/locational preposition
    # sense as the existing entries, not the informal "you" pronoun.
    "fa.b1.unit09.lesson04.dialogue_meeting",
    "fa.b1.unit10.lesson01.subject_relative",
}

# نه is a genuine homograph too: "nine" (FA_NUMBERS, established since
# a1_unit03) versus the negation "no / not" used in these three A2
# dialogue lessons -- a real, previously-latent bug found while adding
# units 12/15/16 (2026-07-11 A2 units 11-18 backfill pass). None of
# these three lessons mention the number nine at all; unit15's own
# "nine o'clock" is deliberately spelled "نُه" (with the vocalization
# mark, see FA_NUMBERS above) specifically to avoid this exact
# collision, but these three lessons' negation still collides with the
# long-established plain "نه" = "nine" entry without this split.
NO_NEGATION_LESSONS = {
    # B2 (added 2026-10-19): "نه کاملا ... نه کاملا" (neither ... nor),
    # "نه چیز دیگر" (nothing else), "نه سرد است نه خودمانی".
    "fa.b2.unit03.nuance.lesson02.qualification",
    "fa.b2.unit03.nuance.lesson03.emphasis",
    "fa.b2.unit05.register.lesson02.colleague",
    "fa.a2.unit12.lesson04.doctor_visit_dialogue",
    "fa.a2.unit15.lesson04.station_counter_dialogue",
    "fa.a2.unit16.lesson04.habits_conversation",
    # B1 unit04 (debate), added 2026-07-11 (B1 units 01-06 backfill
    # pass): the same نه = "no" (not "nine") collision, found while
    # adding this unit's remote-work-disagreement dialogue -- B1 doesn't
    # teach numbers at all, so this is the only نه occurrence at the b1
    # level, but the fix is the same regardless of level since this set
    # isn't itself level-scoped.
    "fa.b1.unit04.lesson04.dialogue_remote_work",
    # A1 units 10/33/36/45, added 2026-07-22 (en-fa checkpoint-coverage
    # pass): four more occurrences of the same collision, three of them
    # PRE-EXISTING (units 10/33/36 were already in UNIT_FILES and had been
    # silently inheriting the "nine" gloss/POS/number-tag for a plain "no")
    # and one in this pass's own new range (unit45's "نه، فقط ..." dosage
    # answer, whose overlay gloss says "no" outright). None of the four
    # lessons mentions the number nine; unit49/52/57's own "ساعت نه"
    # ("nine o'clock") lessons are deliberately NOT listed here, so the
    # number sense keeps its long-established a1_unit03 anchor.
    "fa.a1.unit10.lesson06.meeting_date_dialogue",
    "fa.a1.unit33.lesson04.neighborhood_dialogue",
    "fa.a1.unit36.lesson04.personality_dialogue",
    "fa.a1.unit45.lesson03.dosage_timing",
}

# چشم is a genuine homograph in this course, found 2026-07-22 while adding
# A1 units 25-57: the polite acknowledgment "right away / certainly"
# (FA_PARTICLES, established since a1_unit06's restaurant etiquette card
# and reused in unit46/a2_unit12) versus the plain body-part NOUN "eye"
# that a1_unit25 introduces and drills. Without this split, unit25's whole
# eye-colour lesson would inherit "right away (polite acknowledgment)" as
# its gloss and "particle" as its part of speech -- a learner flashcard
# reading "چشم: right away" while the exercise is about eye colour. Given
# its own key-tuple discriminator AND a distinct part_of_speech (so the two
# senses land as separate Lexeme rows -- main() matches on
# token+part_of_speech), same pattern as تو's location_prep split.
CHESHM_EYE_LESSONS = {
    "fa.a1.unit25.lesson03.eyes",
}

# پس is a genuine homograph too, same pass: the discourse particle "so;
# then" (established since a1_unit04/unit07, e.g. "پس بریم پارک") versus
# the "back" of پس دادن ("to give back / return an item"), which units
# 42/47 introduce as a real vocabulary item in that sense. Classified
# adverb there so the two senses land as separate Lexeme rows.
# NOTE (not fixed here, flagged for the coordinator): a2_unit18's own
# "پس دادن" note has the same "back" sense but its a2-level row already
# exists with the discourse gloss; it is left untouched rather than
# silently re-pointing an already-shipped A2 unit's lexeme.
PAS_RETURN_LESSONS = {
    "fa.a1.unit42.lesson03.when_giving_back",
    "fa.a1.unit47.lesson03.size_and_return",
}

# تا is a genuine homograph too, same pass, with THREE senses in this
# corpus: the counting classifier ("دو تا سیب", established a1_unit03 --
# the sense the plain FA_GLOSSES/FA_PARTICLES entry covers), the
# preposition "until / up to / by" (the opening-hours and deadline lessons
# listed below), and B1's purpose conjunction "so that" (units 15/16).
# The latter two are grouped here as one preposition-classified lexeme
# ("until; up to; so that"), because they are the same non-classifier تا
# and never contrast within a lesson. b1_unit09's own "تا فردا" ("by
# tomorrow") is included deliberately: it is a PRE-EXISTING mis-gloss --
# B1 teaches no counting classifier at all, so today the only b1 تا row
# carries the classifier gloss.
TA_UNTIL_LESSONS = {
    # B2 (added 2026-10-19): "تا حدی" = "to some extent" -- no counting
    # classifier anywhere in B2.
    "fa.b2.unit03.nuance.lesson01.hedging",
    "fa.a1.unit42.lesson03.when_giving_back",
    "fa.a1.unit44.lesson04.checkin_dialogue",
    "fa.a1.unit47.lesson03.size_and_return",
    "fa.a1.unit49.lesson03.locker_and_hours",
    "fa.a1.unit52.lesson02.new_museum_two",
    "fa.a1.unit54.lesson05.reading_park_sign",
    "fa.a1.unit55.lesson03.class_and_hours",
    "fa.a1.unit56.lesson05.reading_beach_sign",
    "fa.a1.unit57.lesson05.reading_zoo_sign",
    "fa.b1.unit09.lesson04.dialogue_meeting",
    "fa.b1.unit15.lesson02.saving_goal",
    "fa.b1.unit15.lesson03.work_goal",
    "fa.b1.unit15.lesson05.reading_goals",
    "fa.b1.unit15.lesson06.wrapup_production",
    "fa.b1.unit16.lesson01.study_goal",
    "fa.b1.unit16.lesson02.saving_goal",
    "fa.b1.unit16.lesson04.dialogue_goals",
    "fa.b1.unit16.lesson05.reading_goals",
    "fa.b1.unit16.lesson06.wrapup_production",
}

# جدی is a genuine homograph too, same pass: the personality ADJECTIVE
# "serious" (a1_unit36) versus B1 unit14's conversational reaction
# "really?!". Unlike چشم/پس/تا above no key-tuple or part_of_speech
# discriminator is needed -- the two senses are in different courses
# (a1 vs b1) so fa_specs's (level, token) key already separates them and
# their DB rows have different course_id -- only the gloss needs
# overriding, same as the باشه precedent.
JADI_REALLY_LESSONS = {
    "fa.b1.unit14.lesson04.dialogue_messages",
}

# باشه is a genuine homograph too, found while adding B1 unit03
# (hypotheticals), 2026-07-11: the informal affirmation "okay"
# (FA_VERBS, established since a1_unit12's accept_word group) versus the
# 3rd-person-singular SUBJUNCTIVE copula "(if) he/she be/has" that
# completes this unit's "داشته باشم/باشی/باشه/باشیم/باشید/باشن"
# conditional paradigm -- a real, confusable difference (a learner
# flashcard reading "باشه: okay" while the actual sentence is "اگه پول
# داشته باشه می‌خره", "if he/she has money, he/she buys it," would be
# genuinely misled), unlike برید/باشید's compatible-reuse cases
# documented in FA_GLOSSES' own B1 comment block above. Both senses
# already land as separate Lexeme rows regardless (the "okay" sense is
# level="a1", this sense is level="b1", and fa_specs's key already
# includes level) -- so unlike تو/نه above, no third key-tuple
# discriminator is needed here, just the english_gloss/semantic-tag
# override in fa_agreement_tags()/_classify_fa() below. part_of_speech
# stays "verb" either way (already true for both senses via the
# existing FA_VERBS membership), so no override needed there either.
BASHE_SUBJUNCTIVE_LESSONS = {
    "fa.b1.unit03.lesson02.real_condition_all_persons",
    # B1 unit09 (professional meetings), added 2026-07-11 (B1 units 07-11
    # backfill pass): the same subjunctive-copula sense recurs in this
    # unit's own reading passage -- "تصمیم گرفتیم که جلسه‌ی بعدی سه‌شنبه
    # باشه" ("we decided the next meeting should be [on] Tuesday"), a
    # 3rd-person "(that it) be" completing a formal decision/suggestion
    # clause, not the informal "okay" affirmation.
    "fa.b1.unit09.lesson05.reading_the_professional_message",
    # B1 units 12/15, added 2026-07-22: the same subjunctive-copula sense
    # completes this pass's own conditional/purpose paradigms -- "اگه هوا
    # خوب باشه" ("if the weather is good") and "تا جلسه آماده باشه" ("so
    # that the meeting is ready"). Listing them also stops these lessons
    # re-merging the unrelated A1 "okay" tags (accept_word/
    # travel_confirmation_word) onto the b1 row.
    # KNOWN LIMITATION, flagged rather than papered over: b1 unit12
    # lesson04 contains BOTH senses (its dialogue opens with a plain
    # "باشه." = "okay"), and the whole b1 level shares one باشه row, which
    # carries the subjunctive gloss. Splitting it would need a
    # content_key-level discriminator, not a lesson-level one.
    "fa.b1.unit12.lesson04.dialogue_plan_b",
    "fa.b1.unit12.lesson05.reading_plan",
    "fa.b1.unit15.lesson03.work_goal",
    "fa.b1.unit15.lesson05.reading_goals",
    "fa.b1.unit15.lesson06.wrapup_production",
}

EN_PRONOUNS = {
    "i", "you", "we", "she", "he", "him", "her", "they", "this",
    "herself", "who", "he/she", "you're", "i'm", "what's", "sara's",
}
EN_PREPOSITIONS = {"from", "to", "for", "of", "inside", "until"}
EN_PARTICLES = {"and", "but", "or", "not", "yes", "that", "whether", "the", "a", "my", "your", "so", "then"}
EN_ADVERBS = {"right", "left", "again", "now", "very", "here", "politely", "too", "originally", "ahead", "how", "where", "together", "tomorrow", "certainly", "casual", "informal"}
EN_ADJECTIVES = {
    "good", "bad", "kind", "context-sensitive", "iranian", "english", "french",
    "persian", "pleased", "present", "written", "married", "single", "big",
    "small", "zero", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
    "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
}
EN_VERBS = {
    "is", "are", "am", "be", "see", "meet", "have", "go", "don't",
    "welcomes", "greets", "thanks", "state", "says", "returns", "asks",
    "answers", "invites", "explains", "must", "leave", "acknowledges",
    "hopes", "confirms", "introduces", "learns", "want", "has",
}


# Extra B2-only semantic tags the en-fa B2 practice packs slot on, keyed by
# token and applied ONLY to a token's first B2 introduction (the lexeme row
# whose provenance is that unit), never to an A1-B1 row:
# - b2u<NN>_core: CURATED content words (noun/verb/adjective/adverb) of unit
#   NN for multiple_choice and matching_pairs. Leaves out linked (ezafe),
#   indefinite -i and possessive forms whose base word is also in the unit
#   (فضای, روشنی, ادعایش, منبعش, همکارم ...), fragments whose gloss only
#   makes sense inside a fixed expression (خاطر, طور, رخ, وجود, واقع ...),
#   numerals/determiners, and one of each near-paraphrase pair (حرف beside
#   واژه, نگاه beside دیدگاه), so no MC/matching item offers two
#   interchangeable English answers.
# - b2u<NN>_vert_l<L>: the bare-word translation pool of lesson L: core
#   nouns/adjectives/adverbs first taught in that lesson, minus every token
#   whose English prompt is just as well answered by another common Persian
#   word or a colloquial variant (جواب/پاسخ, واژه, پرسش, آرام, لطفا ...) or
#   whose gloss names only part of a compound verb (نصب, تعویق, اعلام ...).
#   Verbs are never in it (formal/colloquial variants of the same form).
# - b2u<NN>_<slug>_single: one single-member anchor per word_order frame,
#   carried by exactly one token in the whole direction.
FA_B2_EXTRA_TAGS: dict[str, list[str]] = {
    "نظر": ["b2u01_core", "b2u01_vert_l1"],
    "شواهد": ["b2u01_core", "b2u01_vert_l1", "b2u01_shavahed_single"],
    "داریم": ["b2u01_core"],
    "باید": ["b2u01_core"],
    "طرح": ["b2u01_core", "b2u01_vert_l1"],
    "ادامه": ["b2u01_core"],
    "بدهیم": ["b2u01_core"],
    "معتقدم": ["b2u01_core"],
    "تصمیم": ["b2u01_core", "b2u01_vert_l1"],
    "عجولانه": ["b2u01_core", "b2u01_vert_l1"],
    "نیست": ["b2u01_core"],
    "ادعا": ["b2u01_core", "b2u01_vert_l1"],
    "دلیل": ["b2u01_core", "b2u01_vert_l1"],
    "روشن": ["b2u01_core", "b2u01_vert_l1"],
    "نیاز": ["b2u01_core", "b2u01_vert_l1"],
    "دارد": ["b2u01_core"],
    "محله": ["b2u01_core", "b2u01_vert_l1"],
    "مفید": ["b2u01_core", "b2u01_vert_l1"],
    "است": ["b2u01_core"],
    "دفاع": ["b2u01_core", "b2u01_vert_l1"],
    "پیشنهاد": ["b2u01_core", "b2u01_vert_l1"],
    "باشد": ["b2u01_core"],
    "کافی": ["b2u01_core", "b2u01_vert_l1"],
    "تغییر": ["b2u01_core", "b2u01_vert_l1"],
    "برنامه": ["b2u01_core", "b2u01_vert_l1"],
    "نداریم": ["b2u01_core"],
    "می‌دهد": ["b2u01_core"],
    "آمار": ["b2u01_core", "b2u01_vert_l1"],
    "اتاق": ["b2u01_core", "b2u01_vert_l1"],
    "مطالعه": ["b2u01_core", "b2u01_vert_l1"],
    "پر": ["b2u01_core", "b2u01_vert_l1"],
    "استفاده": ["b2u01_core", "b2u01_vert_l1"],
    "آرام": ["b2u01_core"],
    "دانشجوها": ["b2u01_core", "b2u01_vert_l1"],
    "اصلی": ["b2u01_core", "b2u01_vert_l1"],
    "امنیت": ["b2u01_core", "b2u01_vert_l1", "b2u01_amniyat_single"],
    "شبانه": ["b2u01_core", "b2u01_vert_l1"],
    "مثال": ["b2u01_core", "b2u01_vert_l2"],
    "هزینه": ["b2u01_core", "b2u01_vert_l2"],
    "نگهبان": ["b2u01_core", "b2u01_vert_l2"],
    "می‌توانیم": ["b2u01_core"],
    "تقسیم": ["b2u01_core"],
    "کنیم": ["b2u01_core"],
    "کتابخانه": ["b2u01_core", "b2u01_vert_l2"],
    "بعد": ["b2u01_core"],
    "کار": ["b2u01_core", "b2u01_vert_l2"],
    "لازم": ["b2u01_core", "b2u01_vert_l2"],
    "برق": ["b2u01_core", "b2u01_vert_l2"],
    "امسال": ["b2u01_core", "b2u01_vert_l2"],
    "بالاتر": ["b2u01_core", "b2u01_vert_l2"],
    "رفته": ["b2u01_core"],
    "شب": ["b2u01_core", "b2u01_vert_l2"],
    "ورودی": ["b2u01_core", "b2u01_vert_l2", "b2u01_vorudi_single"],
    "می‌ماند": ["b2u01_core"],
    "کمتر": ["b2u01_core", "b2u01_vert_l2"],
    "ضرر": ["b2u01_core", "b2u01_vert_l2", "b2u01_zarar_single"],
    "تعطیلی": ["b2u01_core", "b2u01_vert_l2"],
    "زودهنگام": ["b2u01_core", "b2u01_vert_l2"],
    "موافقم": ["b2u01_core"],
    "دسترسی": ["b2u01_core", "b2u01_vert_l2"],
    "خانواده‌ها": ["b2u01_core", "b2u01_vert_l2"],
    "مهم": ["b2u01_core", "b2u01_vert_l2"],
    "مشخص": ["b2u01_core", "b2u01_vert_l2"],
    "شاغل": ["b2u01_core", "b2u01_vert_l2"],
    "ساعت": ["b2u01_core", "b2u01_vert_l2"],
    "می‌کنند": ["b2u01_core"],
    "درست": ["b2u01_core", "b2u01_vert_l3"],
    "بالاست": ["b2u01_core"],
    "هنوز": ["b2u01_core", "b2u01_vert_l3"],
    "می‌شود": ["b2u01_core"],
    "راه‌حل": ["b2u01_core", "b2u01_vert_l3", "b2u01_rahhal_single"],
    "پیدا": ["b2u01_core"],
    "کرد": ["b2u01_core"],
    "کنترل": ["b2u01_core", "b2u01_vert_l3"],
    "اعتراض": ["b2u01_core", "b2u01_vert_l3"],
    "جدی": ["b2u01_core", "b2u01_vert_l3"],
    "پاسخ": ["b2u01_core", "b2u01_vert_l3"],
    "کوتاه": ["b2u01_core", "b2u01_vert_l3"],
    "همیشه": ["b2u01_core", "b2u01_vert_l3"],
    "نتیجه": ["b2u01_core", "b2u01_vert_l3"],
    "ارزش": ["b2u01_core", "b2u01_vert_l3"],
    "بچه‌ها": ["b2u01_core", "b2u01_vert_l3"],
    "درس": ["b2u01_core", "b2u01_vert_l3"],
    "داشته": ["b2u01_core"],
    "باشند": ["b2u01_core"],
    "بهتر": ["b2u01_core", "b2u01_vert_l3"],
    "شود": ["b2u01_core"],
    "نمی‌توانیم": ["b2u01_core"],
    "نادیده": ["b2u01_core", "b2u01_nadideh_single"],
    "بگیریم": ["b2u01_core"],
    "باز": ["b2u01_core", "b2u01_vert_l3"],
    "ماندن": ["b2u01_core"],
    "می‌کنم": ["b2u01_core"],
    "شاید": ["b2u02_core", "b2u02_vert_l1"],
    "پمپ": ["b2u02_core", "b2u02_vert_l1"],
    "فرسودگی": ["b2u02_core", "b2u02_vert_l1"],
    "خراب": ["b2u02_core", "b2u02_vert_l1"],
    "شده": ["b2u02_core"],
    "احتمالا": ["b2u02_core", "b2u02_vert_l1"],
    "مدیر": ["b2u02_core", "b2u02_vert_l1"],
    "ساختمان": ["b2u02_core", "b2u02_vert_l1"],
    "خبر": ["b2u02_core"],
    "احتمال": ["b2u02_core", "b2u02_vert_l1"],
    "زیاد": ["b2u02_core", "b2u02_vert_l1"],
    "مشکل": ["b2u02_core", "b2u02_vert_l1"],
    "طبقه": ["b2u02_core", "b2u02_vert_l1"],
    "پایین": ["b2u02_core", "b2u02_vert_l1"],
    "شروع": ["b2u02_core", "b2u02_vert_l1"],
    "حتما": ["b2u02_core", "b2u02_vert_l1"],
    "فنی": ["b2u02_core", "b2u02_vert_l1"],
    "علت": ["b2u02_core", "b2u02_vert_l1", "b2u02_ellat_single"],
    "بو": ["b2u02_core", "b2u02_vert_l1"],
    "معلوم": ["b2u02_core", "b2u02_vert_l1"],
    "نشانه": ["b2u02_core", "b2u02_vert_l1"],
    "صدا": ["b2u02_core", "b2u02_vert_l1"],
    "خرابی": ["b2u02_core", "b2u02_vert_l1"],
    "فکر": ["b2u02_core"],
    "کنم": ["b2u02_core"],
    "فشار": ["b2u02_core", "b2u02_vert_l1", "b2u02_feshar_single"],
    "آب": ["b2u02_core", "b2u02_vert_l1"],
    "صبح‌ها": ["b2u02_core", "b2u02_vert_l1"],
    "می‌آید": ["b2u02_core"],
    "مطمئن": ["b2u02_core", "b2u02_vert_l1"],
    "نیستم": ["b2u02_core"],
    "تعمیر": ["b2u02_core", "b2u02_vert_l1"],
    "امروز": ["b2u02_core", "b2u02_vert_l1"],
    "تمام": ["b2u02_core", "b2u02_vert_l1"],
    "آسانسور": ["b2u02_core", "b2u02_vert_l2"],
    "نمی‌تواند": ["b2u02_core"],
    "تصادفی": ["b2u02_core", "b2u02_vert_l2"],
    "قطع": ["b2u02_core", "b2u02_vert_l2"],
    "دیوار": ["b2u02_core", "b2u02_vert_l2"],
    "دیده": ["b2u02_core"],
    "نشتی": ["b2u02_core", "b2u02_vert_l2", "b2u02_nashti_single"],
    "کوچک": ["b2u02_core", "b2u02_vert_l2"],
    "می‌تواند": ["b2u02_core"],
    "خطرناک": ["b2u02_core", "b2u02_vert_l2"],
    "بالا": ["b2u02_core", "b2u02_vert_l2"],
    "بوده": ["b2u02_core"],
    "لوله": ["b2u02_core", "b2u02_vert_l2"],
    "آسیب": ["b2u02_core", "b2u02_vert_l2", "b2u02_asib_single"],
    "قدیمی": ["b2u02_core", "b2u02_vert_l2"],
    "عوض": ["b2u02_core"],
    "بعید": ["b2u02_core", "b2u02_vert_l2"],
    "شیر": ["b2u02_core", "b2u02_vert_l2"],
    "کارشناس": ["b2u02_core", "b2u02_vert_l2"],
    "بیاید": ["b2u02_core"],
    "حدس": ["b2u02_core", "b2u02_vert_l2"],
    "زد": ["b2u02_core"],
    "ممکن": ["b2u02_core", "b2u02_vert_l3", "b2u02_momken_single"],
    "امشب": ["b2u02_core", "b2u02_vert_l3"],
    "ضعیف": ["b2u02_core", "b2u02_vert_l3"],
    "پیامد": ["b2u02_core", "b2u02_vert_l3", "b2u02_payamad_single"],
    "تاخیر": ["b2u02_core", "b2u02_vert_l3"],
    "طول": ["b2u02_core", "b2u02_vert_l3"],
    "می‌کشد": ["b2u02_core"],
    "بماند": ["b2u02_core"],
    "بسته": ["b2u02_core", "b2u02_vert_l3"],
    "همسایه‌ها": ["b2u02_core", "b2u02_vert_l3"],
    "ناراضی‌اند": ["b2u02_core"],
    "دیر": ["b2u02_core", "b2u02_vert_l3"],
    "قطعی": ["b2u02_core", "b2u02_vert_l3"],
    "کم": ["b2u02_core", "b2u02_vert_l3"],
    "آماده": ["b2u02_core", "b2u02_vert_l3"],
    "باشیم": ["b2u02_core"],
    "موقت": ["b2u02_core", "b2u02_vert_l3"],
    "جمله": ["b2u03_core", "b2u03_vert_l1"],
    "فردا": ["b2u03_core", "b2u03_vert_l1"],
    "دوباره": ["b2u03_core", "b2u03_vert_l1"],
    "بنویسیم": ["b2u03_core"],
    "می‌رسد": ["b2u03_core"],
    "متن": ["b2u03_core", "b2u03_vert_l1"],
    "کمی": ["b2u03_core"],
    "تند": ["b2u03_core", "b2u03_vert_l1"],
    "صبر": ["b2u03_core", "b2u03_vert_l1"],
    "نرم‌تر": ["b2u03_core", "b2u03_vert_l1", "b2u03_narmtar_single"],
    "لحن": ["b2u03_core", "b2u03_vert_l1", "b2u03_lahn_single"],
    "تاثیر": ["b2u03_core", "b2u03_vert_l1"],
    "سند": ["b2u03_core", "b2u03_vert_l1"],
    "نامه": ["b2u03_core", "b2u03_vert_l1"],
    "محترمانه": ["b2u03_core", "b2u03_vert_l1"],
    "بحث": ["b2u03_core", "b2u03_vert_l1"],
    "محتاطانه": ["b2u03_core", "b2u03_vert_l1"],
    "جواب": ["b2u03_core"],
    "دادن": ["b2u03_core"],
    "گاهی": ["b2u03_core", "b2u03_vert_l1"],
    "البته": ["b2u03_core", "b2u03_vert_l2"],
    "مخالف": ["b2u03_core", "b2u03_vert_l2"],
    "نیستند": ["b2u03_core"],
    "جلسه": ["b2u03_core", "b2u03_vert_l2"],
    "عقب": ["b2u03_core"],
    "نمی‌اندازیم": ["b2u03_core"],
    "باران": ["b2u03_core", "b2u03_vert_l2"],
    "شدید": ["b2u03_core", "b2u03_vert_l2"],
    "منتشر": ["b2u03_core", "b2u03_montasher_single"],
    "می‌کنیم": ["b2u03_core"],
    "دقیق‌تر": ["b2u03_core", "b2u03_vert_l2"],
    "واژه": ["b2u03_core"],
    "سوءتفاهم": ["b2u03_core", "b2u03_vert_l2"],
    "می‌کند": ["b2u03_core"],
    "مطلق": ["b2u03_core", "b2u03_vert_l2"],
    "حکم": ["b2u03_core", "b2u03_vert_l2"],
    "کاملا": ["b2u03_core", "b2u03_vert_l2"],
    "مخالفم": ["b2u03_core"],
    "موافق": ["b2u03_core", "b2u03_vert_l2"],
    "استثنا": ["b2u03_core", "b2u03_vert_l2"],
    "قانون": ["b2u03_core", "b2u03_vert_l2"],
    "هست": ["b2u03_core"],
    "بیشتر": ["b2u03_core", "b2u03_vert_l2"],
    "موارد": ["b2u03_core", "b2u03_vert_l2"],
    "محدود": ["b2u03_core", "b2u03_vert_l2"],
    "عملی": ["b2u03_core", "b2u03_vert_l2", "b2u03_amali_single"],
    "دقیقا": ["b2u03_core", "b2u03_vert_l3"],
    "مشکل‌ساز": ["b2u03_core", "b2u03_vert_l3"],
    "نکته": ["b2u03_core", "b2u03_vert_l3"],
    "پایان": ["b2u03_core", "b2u03_vert_l3"],
    "تکرار": ["b2u03_core", "b2u03_vert_l3"],
    "کن": ["b2u03_core"],
    "نگرانی": ["b2u03_core", "b2u03_vert_l3"],
    "ابهام": ["b2u03_core", "b2u03_vert_l3", "b2u03_ebham_single"],
    "زمان": ["b2u03_core", "b2u03_vert_l3"],
    "تاکید": ["b2u03_core", "b2u03_vert_l3"],
    "خشن": ["b2u03_core", "b2u03_vert_l3"],
    "چیز": ["b2u03_core", "b2u03_vert_l3"],
    "دیگر": ["b2u03_core", "b2u03_vert_l3"],
    "بلند": ["b2u03_core", "b2u03_vert_l3"],
    "بگوییم": ["b2u03_core"],
    "می‌خواهیم": ["b2u03_core"],
    "ساکنان": ["b2u03_core", "b2u03_vert_l3"],
    "قبلی": ["b2u03_core", "b2u03_vert_l3"],
    "خیلی": ["b2u03_core", "b2u03_vert_l3"],
    "مبهم": ["b2u03_core", "b2u03_vert_l3", "b2u03_mobham_single"],
    "بود": ["b2u03_core"],
    "می‌بارید": ["b2u04_core"],
    "خیابان": ["b2u04_core", "b2u04_vert_l1"],
    "خلوت": ["b2u04_core", "b2u04_vert_l1"],
    "نمایشگاه": ["b2u04_core", "b2u04_vert_l1"],
    "عکس": ["b2u04_core", "b2u04_vert_l1"],
    "عصر": ["b2u04_core", "b2u04_vert_l1"],
    "تازه": ["b2u04_core", "b2u04_tazeh_single"],
    "کافه": ["b2u04_core", "b2u04_vert_l1"],
    "شلوغ": ["b2u04_core", "b2u04_vert_l1"],
    "نبود": ["b2u04_core"],
    "زمینه": ["b2u04_core", "b2u04_vert_l1"],
    "داستان": ["b2u04_core", "b2u04_vert_l1"],
    "توضیح": ["b2u04_core", "b2u04_vert_l1"],
    "داد": ["b2u04_core"],
    "رویداد": ["b2u04_core", "b2u04_vert_l1"],
    "تماس": ["b2u04_core", "b2u04_vert_l1"],
    "لحظه": ["b2u04_core", "b2u04_vert_l1", "b2u04_lahzeh_single"],
    "چراغ‌ها": ["b2u04_core", "b2u04_vert_l1"],
    "خاموش": ["b2u04_core", "b2u04_vert_l1"],
    "شد": ["b2u04_core"],
    "بودند": ["b2u04_core"],
    "مهمان‌ها": ["b2u04_core", "b2u04_vert_l1"],
    "منتظر": ["b2u04_core", "b2u04_vert_l1"],
    "ماندند": ["b2u04_core"],
    "قبل": ["b2u04_core"],
    "رسیدن": ["b2u04_core"],
    "سالن": ["b2u04_core", "b2u04_vert_l2", "b2u04_salon_single"],
    "تمیز": ["b2u04_core", "b2u04_vert_l2"],
    "کرده": ["b2u04_core"],
    "کلید": ["b2u04_core", "b2u04_vert_l2"],
    "میز": ["b2u04_core", "b2u04_vert_l2"],
    "گذاشته": ["b2u04_core"],
    "ناگهان": ["b2u04_core", "b2u04_vert_l2"],
    "رفت": ["b2u04_core"],
    "راهرو": ["b2u04_core", "b2u04_vert_l2"],
    "پیش‌تر": ["b2u04_core"],
    "زده": ["b2u04_core"],
    "بودیم": ["b2u04_core"],
    "نرسیده": ["b2u04_core"],
    "گرفتند": ["b2u04_core"],
    "خیس": ["b2u04_core", "b2u04_vert_l2", "b2u04_khis_single"],
    "کف": ["b2u04_core", "b2u04_vert_l2"],
    "عکس‌ها": ["b2u04_core", "b2u04_vert_l3"],
    "نصب": ["b2u04_core", "b2u04_nasb_single"],
    "می‌کردیم": ["b2u04_core"],
    "آمد": ["b2u04_core"],
    "گفت‌وگو": ["b2u04_core", "b2u04_vert_l3"],
    "زنگ": ["b2u04_core", "b2u04_vert_l3"],
    "تلفن": ["b2u04_core", "b2u04_vert_l3"],
    "ترتیب": ["b2u04_core", "b2u04_vert_l3"],
    "رویدادها": ["b2u04_core", "b2u04_vert_l3"],
    "نوشتم": ["b2u04_core"],
    "فهمیدیم": ["b2u04_core"],
    "پنجره": ["b2u04_core", "b2u04_vert_l3", "b2u04_panjereh_single"],
    "مانده": ["b2u04_core"],
    "پشتی": ["b2u04_core", "b2u04_vert_l3"],
    "وسط": ["b2u04_core", "b2u04_vert_l3"],
    "زودتر": ["b2u05_core", "b2u05_vert_l1"],
    "می‌تونی": ["b2u05_core"],
    "دقیقه": ["b2u05_core", "b2u05_vert_l1", "b2u05_daghigheh_single"],
    "کنی": ["b2u05_core"],
    "بیندازی": ["b2u05_core"],
    "خودمانی": ["b2u05_core", "b2u05_vert_l1", "b2u05_khodemani_single"],
    "پیام": ["b2u05_core", "b2u05_vert_l1"],
    "اداره": ["b2u05_core", "b2u05_vert_l1"],
    "زیادی": ["b2u05_core"],
    "ممکنه": ["b2u05_core"],
    "بده": ["b2u05_core"],
    "دوست": ["b2u05_core", "b2u05_vert_l1"],
    "نزدیک": ["b2u05_core", "b2u05_vert_l1"],
    "راحت‌تر": ["b2u05_core", "b2u05_vert_l1"],
    "می‌زنیم": ["b2u05_core"],
    "دیرتر": ["b2u05_core", "b2u05_vert_l1"],
    "می‌رسم": ["b2u05_core"],
    "لطفا": ["b2u05_core"],
    "ببین": ["b2u05_core"],
    "گزارش": ["b2u05_core", "b2u05_vert_l2"],
    "بفرستید": ["b2u05_core"],
    "همکار": ["b2u05_core", "b2u05_vert_l2"],
    "نوشت": ["b2u05_core"],
    "مناسب": ["b2u05_core", "b2u05_vert_l2", "b2u05_monaseb_single"],
    "همکاری": ["b2u05_core", "b2u05_vert_l2", "b2u05_hamkari_single"],
    "آسان‌تر": ["b2u05_core", "b2u05_vert_l2"],
    "جابه‌جا": ["b2u05_core"],
    "دستور": ["b2u05_core", "b2u05_vert_l2"],
    "درخواست": ["b2u05_core", "b2u05_vert_l2"],
    "بنویس": ["b2u05_core"],
    "سرد": ["b2u05_core", "b2u05_vert_l2"],
    "سپاسگزارم": ["b2u05_core"],
    "پیگیری": ["b2u05_core", "b2u05_vert_l2"],
    "امکان": ["b2u05_core", "b2u05_vert_l3"],
    "مدارک": ["b2u05_core", "b2u05_vert_l3", "b2u05_madarek_single"],
    "تحویل": ["b2u05_core"],
    "بدهم": ["b2u05_core"],
    "وقت": ["b2u05_core"],
    "ملاقات": ["b2u05_core", "b2u05_vert_l3"],
    "سامانه": ["b2u05_core", "b2u05_vert_l3"],
    "ثبت": ["b2u05_core", "b2u05_vert_l3"],
    "تعویق": ["b2u05_core"],
    "بیندازید": ["b2u05_core"],
    "بررسی": ["b2u05_core", "b2u05_vert_l3"],
    "پرونده": ["b2u05_core", "b2u05_vert_l3", "b2u05_parvandeh_single"],
    "نیندازید": ["b2u05_core"],
    "رسمی": ["b2u05_core", "b2u05_vert_l3"],
    "رسمی‌تر": ["b2u05_core", "b2u05_vert_l3"],
    "خواهشمندم": ["b2u05_core"],
    "جدید": ["b2u05_core", "b2u05_vert_l3"],
    "اعلام": ["b2u05_core"],
    "کنید": ["b2u05_core"],
    "کامل": ["b2u05_core", "b2u05_vert_l3"],
    "ایمیل": ["b2u05_core", "b2u05_vert_l3"],
    "احترام": ["b2u05_core", "b2u05_vert_l3"],
    "می‌فرستم": ["b2u05_core"],
    "آزادی": ["b2u06_core", "b2u06_vert_l1"],
    "آسیب‌پذیر": ["b2u06_core", "b2u06_vert_l1", "b2u06_asibpazir_single"],
    "مسئولیت": ["b2u06_core", "b2u06_vert_l1"],
    "فقط": ["b2u06_core", "b2u06_vert_l1"],
    "وظیفه": ["b2u06_core", "b2u06_vert_l1"],
    "دولت": ["b2u06_core", "b2u06_vert_l1"],
    "پایدار": ["b2u06_core", "b2u06_vert_l1"],
    "نمی‌ماند": ["b2u06_core"],
    "اعتماد": ["b2u06_core", "b2u06_vert_l1"],
    "شفافیت": ["b2u06_core", "b2u06_vert_l1", "b2u06_shafafiyat_single"],
    "جامعه": ["b2u06_core", "b2u06_vert_l1"],
    "طرف": ["b2u06_core"],
    "فرهنگ": ["b2u06_core", "b2u06_vert_l1"],
    "ساخته": ["b2u06_core"],
    "تنهایی": ["b2u06_core"],
    "می‌خواهد": ["b2u06_core"],
    "می‌فهمم": ["b2u06_core"],
    "می‌گیرم": ["b2u06_core"],
    "حریم": ["b2u06_core"],
    "خصوصی": ["b2u06_core", "b2u06_vert_l2"],
    "کاربران": ["b2u06_core", "b2u06_vert_l2"],
    "مسئله": ["b2u06_core", "b2u06_vert_l2", "b2u06_masaleh_single"],
    "نمی‌شود": ["b2u06_core"],
    "ساده": ["b2u06_core", "b2u06_vert_l2"],
    "گرفت": ["b2u06_core"],
    "بخش": ["b2u06_core", "b2u06_vert_l2"],
    "پرسش": ["b2u06_core"],
    "دارم": ["b2u06_core"],
    "دیدگاه": ["b2u06_core", "b2u06_vert_l2", "b2u06_didgah_single"],
    "تجربه": ["b2u06_core", "b2u06_vert_l2"],
    "شخصی": ["b2u06_core", "b2u06_vert_l2"],
    "کاربر": ["b2u06_core", "b2u06_vert_l2"],
    "انتخاب": ["b2u06_core", "b2u06_vert_l2"],
    "واقعی": ["b2u06_core", "b2u06_vert_l2"],
    "نباید": ["b2u06_core"],
    "گذشت": ["b2u06_core"],
    "مردم": ["b2u06_core", "b2u06_vert_l2"],
    "تفاوت": ["b2u06_core", "b2u06_vert_l3"],
    "افراد": ["b2u06_core", "b2u06_vert_l3"],
    "سرعت": ["b2u06_core", "b2u06_vert_l3", "b2u06_sorat_single"],
    "مهم‌تر": ["b2u06_core", "b2u06_vert_l3"],
    "طولانی": ["b2u06_core", "b2u06_vert_l3"],
    "معنی": ["b2u06_core", "b2u06_vert_l3"],
    "موافقت": ["b2u06_core"],
    "تعمیم": ["b2u06_core"],
    "هویت": ["b2u06_core", "b2u06_vert_l3", "b2u06_hoviyat_single"],
    "زبان": ["b2u06_core", "b2u06_vert_l3"],
    "فرهنگی": ["b2u06_core", "b2u06_vert_l3"],
    "رفتار": ["b2u06_core", "b2u06_vert_l3"],
    "اختلاف": ["b2u06_core", "b2u06_vert_l3"],
    "همزمان": ["b2u06_core", "b2u06_vert_l3"],
    "مرحله‌ای": ["b2u07_core", "b2u07_vert_l1"],
    "انجام": ["b2u07_core"],
    "دهیم": ["b2u07_core"],
    "اجاره": ["b2u07_core", "b2u07_vert_l1", "b2u07_ejareh_single"],
    "استودیو": ["b2u07_core", "b2u07_vert_l1"],
    "ماهانه": ["b2u07_core", "b2u07_vert_l1"],
    "پرداخت": ["b2u07_core"],
    "برابر": ["b2u07_core", "b2u07_vert_l1"],
    "نور": ["b2u07_core", "b2u07_vert_l1"],
    "شیفت‌ها": ["b2u07_core", "b2u07_vert_l1"],
    "منصفانه": ["b2u07_core", "b2u07_vert_l1"],
    "شرایط": ["b2u07_core", "b2u07_vert_l1"],
    "قرارداد": ["b2u07_core", "b2u07_vert_l1"],
    "متراژ": ["b2u07_core", "b2u07_vert_l1"],
    "سهم": ["b2u07_core", "b2u07_vert_l1", "b2u07_sahm_single"],
    "نفر": ["b2u07_core", "b2u07_vert_l1"],
    "جدا": ["b2u07_core", "b2u07_vert_l1"],
    "طبیعی": ["b2u07_core", "b2u07_vert_l1"],
    "نامشخص": ["b2u07_core", "b2u07_vert_l2"],
    "مبلغ": ["b2u07_core", "b2u07_vert_l2", "b2u07_mablagh_single"],
    "پیش‌پرداخت": ["b2u07_core", "b2u07_vert_l2"],
    "قبول": ["b2u07_core"],
    "شرط": ["b2u07_core", "b2u07_vert_l2"],
    "دوم": ["b2u07_core"],
    "راه": ["b2u07_core", "b2u07_vert_l2"],
    "راضی": ["b2u07_core", "b2u07_vert_l2"],
    "رابطه": ["b2u07_core", "b2u07_vert_l2", "b2u07_rabeteh_single"],
    "مذاکره": ["b2u07_core", "b2u07_vert_l2"],
    "کوتاه‌تر": ["b2u07_core", "b2u07_vert_l2"],
    "ریسک": ["b2u07_core", "b2u07_vert_l3", "b2u07_risk_single"],
    "تاریخ": ["b2u07_core", "b2u07_vert_l3"],
    "مالک": ["b2u07_core", "b2u07_vert_l3"],
    "امتیاز": ["b2u07_core", "b2u07_vert_l3"],
    "ضمانت": ["b2u07_core", "b2u07_vert_l3", "b2u07_zemanat_single"],
    "وسایل": ["b2u07_core", "b2u07_vert_l3"],
    "گران": ["b2u07_core", "b2u07_vert_l3"],
    "می‌خواهم": ["b2u07_core"],
    "ساعت‌ها": ["b2u07_core", "b2u07_vert_l3"],
    "توافق": ["b2u07_core", "b2u07_vert_l3"],
    "دقیق": ["b2u07_core", "b2u07_vert_l3"],
    "فعلا": ["b2u07_core", "b2u07_vert_l3"],
    "ماه": ["b2u07_core", "b2u07_vert_l3"],
    "دهد": ["b2u07_core"],
    "باغ": ["b2u08_core", "b2u08_vert_l1", "b2u08_bagh_single"],
    "اشاره": ["b2u08_core"],
    "منبع": ["b2u08_core", "b2u08_vert_l1"],
    "اول": ["b2u08_core"],
    "مصاحبه": ["b2u08_core", "b2u08_vert_l1"],
    "محلی": ["b2u08_core", "b2u08_vert_l1"],
    "بازسازی": ["b2u08_core", "b2u08_vert_l1"],
    "دارند": ["b2u08_core"],
    "نویسنده": ["b2u08_core", "b2u08_vert_l1"],
    "پروژه": ["b2u08_core", "b2u08_vert_l1"],
    "منابع": ["b2u08_core", "b2u08_vert_l1", "b2u08_manabe_single"],
    "اجرا": ["b2u08_core", "b2u08_vert_l1"],
    "خوش‌بین": ["b2u08_core", "b2u08_vert_l1"],
    "دومی": ["b2u08_core"],
    "محتاط‌تر": ["b2u08_core", "b2u08_vert_l1"],
    "دیوارها": ["b2u08_core", "b2u08_vert_l1"],
    "کشید": ["b2u08_core"],
    "قانع‌کننده‌تر": ["b2u08_core", "b2u08_vert_l2", "b2u08_ghanekonandehtar_single"],
    "عدد": ["b2u08_core", "b2u08_vert_l2"],
    "خواننده": ["b2u08_core", "b2u08_vert_l2"],
    "کمک": ["b2u08_core", "b2u08_vert_l2"],
    "داوری": ["b2u08_core", "b2u08_vert_l2", "b2u08_davari_single"],
    "پشتیبانی": ["b2u08_core"],
    "نام": ["b2u08_core"],
    "می‌برد": ["b2u08_core"],
    "واقعیت": ["b2u08_core", "b2u08_vert_l3"],
    "می‌گویند": ["b2u08_core"],
    "جمع‌بندی": ["b2u08_core", "b2u08_vert_l3"],
    "بی‌طرف": ["b2u08_core", "b2u08_vert_l3"],
    "نقطه": ["b2u08_core"],
    "مشترک": ["b2u08_core", "b2u08_vert_l3", "b2u08_moshtarak_single"],
    "اهمیت": ["b2u08_core", "b2u08_vert_l3"],
    "تضاد": ["b2u08_core", "b2u08_vert_l3"],
    "زمان‌بندی": ["b2u08_core", "b2u08_vert_l3"],
    "مفیدند": ["b2u08_core"],
    "محتاط": ["b2u08_core", "b2u08_vert_l3"],
    "اطلاعات": ["b2u08_core", "b2u08_vert_l3", "b2u08_etelaat_single"],
    "تصویر": ["b2u08_core", "b2u08_vert_l3"],
    "خواندن": ["b2u08_core"],
}


def fa_part_of_speech(token: str) -> str:
    if token in FA_SYMBOLS:
        return "symbol"
    if token in FA_NUMBERS:
        return "adjective"
    if token in FA_PROPER_NOUNS:
        return "proper_noun"
    if token in FA_PRONOUNS:
        return "pronoun"
    if token in FA_PREPOSITIONS:
        return "preposition"
    if token in FA_PARTICLES:
        return "particle"
    if token in FA_ADVERBS:
        return "adverb"
    if token in FA_ADJECTIVES:
        return "adjective"
    if token in FA_VERBS:
        return "verb"
    if token in FA_PHRASE_PARTS or token in FA_MULTIWORD_PHRASES:
        return "phrase"
    return "noun"


def en_part_of_speech(token: str) -> str:
    if token in EN_PRONOUNS:
        return "pronoun"
    if token in EN_PREPOSITIONS:
        return "preposition"
    if token in EN_PARTICLES:
        return "particle"
    if token in EN_ADVERBS:
        return "adverb"
    if token in EN_ADJECTIVES:
        return "adjective"
    if token in EN_VERBS:
        return "verb"
    if len(token) <= 3 and token not in {"day", "bye", "tea", "mom", "dad", "son", "her", "him"}:
        return "symbol"
    return "noun"


# BEGIN volume practice singleton tags (generated 2026-07-13)
VOLUME_PRACTICE_SINGLETON_TAGS = {'آبی': ['volume_en_fa_a1_unit20_color_word_12_single'], 'آرش': ['volume_en_fa_a1_unit01_person_name_11_single'], 'بخیر': ['volume_en_fa_a1_unit01_good_wish_04_single'], 'بزرگ': ['volume_en_fa_a1_unit20_size_word_10_single'], 'خسته': ['volume_en_fa_a1_unit23_feeling_a_03_single', 'volume_en_fa_a1_unit23_feeling_b_01_single'], 'ده': ['volume_en_fa_a1_unit21_number_word_07_single', 'volume_en_fa_a1_unit21_number_word_09_single'], 'شب': ['volume_en_fa_a1_unit01_time_period_02_single'], 'صدا': ['volume_en_fa_a1_unit22_phone_word_a_06_single', 'volume_en_fa_a1_unit22_phone_word_b_05_single'], 'چای': ['volume_en_fa_a1_unit01_offered_item_08_single']}
# END volume practice singleton tags

def fa_agreement_tags(token: str, lesson_key: str) -> dict[str, object]:
    semantics: list[str] = []

    for semantic in VOLUME_PRACTICE_SINGLETON_TAGS.get(token, ()):
        semantics.append(semantic)
    if token in FA_SYMBOLS:
        semantics.append("letter")
    if token == "سلام":
        semantics.append("greeting")
    if token in {"صبح", "عصر", "روز", "شب"}:
        semantics.append("time_period")
    if token in {"بخیر", "خوش"}:
        semantics.append("good_wish")
    if token in {"خداحافظ", "فعلاً"}:
        semantics.append("farewell")
    if token in {"چطوره", "چطوری", "چطور"}:
        semantics.append("wellbeing_question")
    if token in {"خوبم", "نیستم", "بد"}:
        semantics.append("wellbeing_answer")
    if token in {"ممنون", "خواهش", "می‌کنم", "بفرمایید", "لطف", "زحمت", "نکشید", "تعارف", "خوشوقتم"}:
        semantics.append("politeness")
    if token == "چای":
        semantics.append("offered_item")
    if token in {"علی", "نرگس", "سارا", "مینا"}:
        semantics.append("person_name")
    if token == "اسم":
        semantics.append("name_word")
    # تو's PREPOSITION sense ("in/inside/within", see TOO_PREPOSITION_
    # LESSONS above) is excluded here so that sense never picks up the
    # pronoun tag (and, below, the pronoun's person/number metadata),
    # matching _classify_fa's own separate-Lexeme handling for this same
    # homograph.
    is_too_location = token == "تو" and lesson_key in TOO_PREPOSITION_LESSONS
    # نه's negation sense ("no/not", see NO_NEGATION_LESSONS above) is
    # excluded from the "number" tag below the same way.
    is_no_negation = token == "نه" and lesson_key in NO_NEGATION_LESSONS
    # باشه's B1 subjunctive-copula sense (see BASHE_SUBJUNCTIVE_LESSONS
    # above) is excluded from the "accept_word"/"travel_confirmation_
    # word" tags below the same way, so this unrelated A1 "okay"
    # semantic grouping never sweeps in the b1-level conditional-
    # paradigm occurrence.
    is_bashe_subjunctive = token == "باشه" and lesson_key in BASHE_SUBJUNCTIVE_LESSONS
    # تا's non-classifier sense ("until / up to / so that", see
    # TA_UNTIL_LESSONS above) is excluded from the "quantity" tag below the
    # same way -- an opening-hours "تا" must never be drawn into a
    # counting-classifier practice slot. Added 2026-07-22.
    is_ta_until = token == "تا" and lesson_key in TA_UNTIL_LESSONS
    if token in FA_PRONOUNS and not is_too_location:
        semantics.append("pronoun")
    if token in {"هستم", "هستی", "هست", "است", "هستید", "هستین", "ساراست", "ایرانیه", "ایرانی‌ام"}:
        semantics.append("copula")
    countries = {"ایران": "iran", "انگلیس": "england", "فرانسه": "france"}
    nationalities = {"ایرانی": "iran", "انگلیسی": "england", "فرانسوی": "france"}
    tags: dict[str, object] = {}
    if token in countries:
        semantics.append("country")
        tags["country_key"] = countries[token]
    if token in nationalities:
        semantics.append("nationality")
        tags["country_key"] = nationalities[token]
    if token == "اهل":
        semantics.append("origin_marker")
    if token in {"کجا", "کجایی"}:
        semantics.append("place_question")
    if token == "کلاس":
        semantics.append("class_word")
    if lesson_key.endswith("lesson06.first_meeting_dialogue") or lesson_key.endswith("lesson06.language_class_dialogue"):
        semantics.append("dialogue_word")
    if " " in token or "،" in token or "؟" in token:
        semantics.append("reviewed_phrase")
    if token in {"حالتون چطوره؟", "چطوری؟"}:
        semantics.extend(["wellbeing_question", "wellbeing_question_phrase"])
    if token in {"خوبم", "خیلی خوبم", "بد نیستم، ممنون"}:
        semantics.extend(["wellbeing_answer", "wellbeing_answer_phrase"])
    if token in {"خواهش می‌کنم", "لطف دارید", "زحمت نکشید", "ممنون از لطف شما"}:
        semantics.extend(["politeness", "politeness_phrase"])
    if (token in FA_NUMBERS or token in {"چنده", "شماره", "تلفن", "تلفنتون", "تلفنت", "شماره‌ام"}) and not is_no_negation:
        semantics.append("number")
    if token in {"شماره", "تلفن", "تلفنتون", "تلفنت", "شماره‌ام"}:
        semantics.append("phone_number")
    if token in {"سال", "سالته", "سالمه"}:
        semantics.append("age")
    if token in {"تا", "سیب", "کتاب"} and not is_ta_until:
        semantics.append("quantity")
    if token in {"قیمت", "تومن", "هزار", "تومنه"}:
        semantics.append("price")
    if token in {
        "مادر", "مامان", "پدر", "بابا", "برادر", "خواهر", "پدربزرگ",
        "مادربزرگ", "عمو", "عمه", "دایی", "خاله", "شوهر", "زن", "نوه",
        "پسر", "برادرم", "داداش", "داداشمه", "مامانم", "بابام", "داداشم",
    }:
        semantics.append("kinship_term")
    if token in {"عمو", "عمه"}:
        semantics.append("paternal_side")
    if token in {"دایی", "خاله", "پدرن", "مادرن"}:
        semantics.append("maternal_side" if token != "پدرن" else "paternal_side")
    if token in {"دارم", "ندارم", "دارد", "ندارد", "نداره", "داره", "دارید", "داری"}:
        semantics.append("possession_verb")
    if token in {"متأهل", "مجرد", "متأهله", "متأهلین", "مجردم", "متأهلم"}:
        semantics.append("marital_status")
    if token in {"خانواده‌ی", "بزرگه", "کوچیکه", "نفرن", "نفریم", "شلوغه"}:
        semantics.append("family_description")
    # "confirm_word" (درسته alone, added 2026-07-24): anchors a1_unit03's
    # confirm_order.002 word_order slot "آره {dialogue_word}" to the one
    # word that grammatically completes the confirmation. آره stays out on
    # purpose -- it is the frame's own literal, and including it would put
    # a duplicate tile in the word bank. Single-member tag precedent:
    # نیما's "person_name" (unit 11).
    if token in {"درسته"}:
        semantics.append("confirm_word")
    if lesson_key.endswith("lesson06.dialogue_phone_numbers") or lesson_key.endswith("lesson06.family_photo_dialogue"):
        semantics.append("dialogue_word")
    # Unit 5 (places and directions): 3-member bare-word recognition tags,
    # exactly meeting this bundle's >=3-distinct-value multiple_choice/
    # matching_pairs rule. Kept recognition-only (no shared generative
    # frame): the real content's own "X {is on side}" phrasing uses
    # colloquial contractions (راسته/چپه = "is on the right/left") that
    # differ per word rather than a uniform "{item} است" pattern, so
    # forcing one shared frame here would risk an unnatural sentence.
    if token in {"هتل", "رستوران", "دستشویی"}:
        semantics.append("place_word")
    if token in {"سمت", "راست", "چپ"}:
        semantics.append("direction_side")
    if token in {"مستقیم", "بعد", "کنار"}:
        semantics.append("direction_connector")
    # Only 2 candidates (colloquial "است" contractions) -- kept out of
    # multiple_choice/matching_pairs, translation-only.
    if token in {"راسته", "چپه"}:
        semantics.append("is_on_side")
    # Unit 6 (food and ordering), added 2026-07-06. 4/3/3-member recognition
    # groups meeting the >=3-distinct-value rule for multiple_choice/
    # matching_pairs; smaller/dialogue-specific phrases left translation-only.
    if token in {"نان", "برنج", "مرغ", "میوه"}:
        semantics.append("food_item")
    if token in {"چای", "قهوه", "آب"}:
        semantics.append("drink_item")
    if token in {"لیوان", "بشقاب", "کیلو", "نصف"}:
        semantics.append("quantity_unit_word")
    if token in {"مغازه", "فروشنده"}:
        semantics.append("shop_word")
    if token in {"نقدی", "کارت", "حساب"}:
        semantics.append("payment_word")
    if lesson_key.endswith("lesson06.restaurant_dialogue"):
        semantics.append("dialogue_word")
    # Practice-pool-depth pass, added 2026-07-06 (closing the units 06-10
    # practice-template-depth gap): "ordering_register" is the same
    # polite-vs-informal contrast unit06's own realization already drills
    # in its lesson02.exercise04 match_register exercise (2 members, kept
    # translation/matching_pairs-only, below the >=3 multiple_choice
    # threshold, same class of narrow register pair as unit05's
    # is_on_side).
    if token in {"می‌خواستم", "می‌خوام"}:
        semantics.append("ordering_register")
    # Unit 7 (weather and making plans), added 2026-07-06.
    if token in {"آفتابی", "بارونی", "ابری", "برفی"}:
        semantics.append("weather_condition")
    if token in {"گرم", "سرد", "خنک"}:
        semantics.append("temperature_word")
    if token in {"آفتابیه", "سرده", "بارونیه", "گرمه"}:
        semantics.append("weather_state_verb")
    if lesson_key.endswith("lesson06.weather_plan_dialogue"):
        semantics.append("dialogue_word")
    # Practice-pool-depth pass, added 2026-07-06: "weather_time_word"
    # (امروز/فردا, both genuinely taught/reinforced in this unit's
    # lesson03/04/06, real content -- 2 members, matching/translation only).
    if token in {"امروز", "فردا"}:
        semantics.append("weather_time_word")
    # Unit 8 (shopping), added 2026-07-06.
    if lesson_key.endswith("lesson06.market_dialogue"):
        semantics.append("dialogue_word")
    # Practice-pool-depth pass, added 2026-07-06: "service_role_word"
    # groups the three service-interaction role nouns that recur across
    # this course's two "ordering/paying" units (گارسون/مشتری first taught
    # unit06, فروشنده taught here in unit08) -- anchored at unit08 (this
    # unit) since that's where all three are genuinely available,
    # mirroring quantity_unit_word's own already-established
    # anchor-at-the-completing-unit precedent below. "price_number"
    # groups the three number words unit08's own dialogue reuses for
    # prices/discounts (سی/بیست/هشت, first taught unit03, reinforced here
    # in lesson02/lesson04's real price/discount phrases) -- scoped
    # narrowly to the numbers this unit's own content actually reuses,
    # not the whole course-wide "number" pool, so the generated item
    # stays genuinely tied to this unit's shopping scenario.
    if token in {"گارسون", "مشتری", "فروشنده"}:
        semantics.append("service_role_word")
    if token in {"سی", "بیست", "هشت"}:
        semantics.append("price_number")
    # Unit 9 (A2: bureaucracy), added 2026-07-06.
    if token in {"وقت", "مدرک", "آدرس", "قبض"}:
        semantics.append("bureaucracy_word")
    if lesson_key.startswith("fa.a2.unit09.lesson04"):
        semantics.append("dialogue_word")
    # Practice-pool-depth pass, added 2026-07-06: "paperwork_word"
    # (اجاره‌نامه/مهلت, 2 members, matching/translation only -- same
    # below-threshold precedent as ordering_register/is_on_side).
    # "bureaucracy_phrase" pools every genuine whole-sentence/whole-phrase
    # lexeme this unit's own four lessons introduce (the same
    # space-containing tokens iter_specs() already auto-derives and tags
    # "reviewed_phrase" below, scoped here to just this unit's own
    # lessons via lesson_key) -- 11 real members by lesson04, anchored
    # there since that's where the pool completes.
    if token in {"اجاره‌نامه", "مهلت"}:
        semantics.append("paperwork_word")
    if lesson_key.startswith("fa.a2.unit09") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("bureaucracy_phrase")
    # Unit 10 (A2: opinions), added 2026-07-06.
    if token in {"نظر", "دلیل", "دورکاری", "ترافیک", "تمرکز", "دفتر"}:
        semantics.append("opinion_word")
    if token in {"رضا", "نگار", "آرش"}:
        semantics.append("person_name")
    if token == "تهران":
        semantics.append("city_name")
    if lesson_key.startswith("fa.a2.unit10.lesson04"):
        semantics.append("dialogue_word")
    # Practice-pool-depth pass, added 2026-07-06: "family_message_word"
    # (پیام/خانواده, 2 members, matching/translation only). "opinion_phrase"
    # mirrors unit09's own "bureaucracy_phrase" pattern -- every genuine
    # whole-sentence/whole-phrase lexeme this unit's own four lessons
    # introduce, scoped via lesson_key, 7 real members by lesson04.
    if token in {"پیام", "خانواده"}:
        semantics.append("family_message_word")
    if lesson_key.startswith("fa.a2.unit10") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("opinion_phrase")
    # Unit 09 (A1: time), added 2026-07-07 (practice-content-gap-closing
    # pass). "time_unit_word" (ساعت/دقیقه/نیم/ربع, 4 members, anchored
    # lesson01) is the basic time-telling vocabulary. "day_part_word"
    # (صبح/ظهر/عصر/شب, 4 members, anchored lesson04) is deliberately a
    # NEW additive tag rather than widening the existing "time_period"
    # tag (already used by en-fa's own a1_unit01.yaml pack for greeting
    # phrases pooling صبح/عصر/شب/روز) -- adding ظهر there or pooling روز
    # here would risk an odd combination (روز/day mixed with a specific
    # time-of-day set), so this unit gets its own clean 4-member set
    # instead. "appointment_word" (قرار, 1 member, translation-only,
    # same below-multiple_choice-threshold class as other units' narrow
    # single-word tags). "time_phrase" pools this unit's own genuine
    # taught full-question/full-statement phrases (auto-derived by
    # iter_specs() from multi-token teaching cards) -- kept as an
    # explicit allow-list rather than a lesson_key-prefix+shape scope
    # (unlike bureaucracy_phrase/opinion_phrase above) because this
    # unit's grammar_note cards would otherwise sweep in an awkward
    # parenthetical-laden phrase not fit for a clean practice item.
    if token in {"ساعت", "دقیقه", "نیم", "ربع"}:
        semantics.append("time_unit_word")
    if token in {"صبح", "ظهر", "عصر", "شب"}:
        semantics.append("day_part_word")
    if token == "قرار":
        semantics.append("appointment_word")
    if token in {
        "ساعت چنده؟", "ساعت سه و نیمه", "قرار ساعت چنده؟", "ساعت چهار عصر",
    }:
        semantics.append("time_phrase")
    if lesson_key.startswith("fa.a1.unit09.lesson06"):
        semantics.append("dialogue_word")
    # Unit 10 (A1: dates), added 2026-07-07. "weekday" (7 members,
    # anchored lesson01), "month_name" (فروردین/اردیبهشت/خرداد, 3
    # members, anchored lesson02), "ordinal_date_word" (دهم/هشتم, 2
    # members, matching/translation-only, same below-threshold class as
    # a1_unit07's weather_time_word), "calendar_word" (تاریخ/جلسه, 2
    # members, matching/translation-only), "date_phrase" (this unit's
    # own genuine taught full-question/full-statement phrases, same
    # explicit-allow-list approach as unit09's time_phrase above).
    if token in {
        "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه",
    }:
        semantics.append("weekday")
    if token in {"فروردین", "اردیبهشت", "خرداد"}:
        semantics.append("month_name")
    if token in {"دهم", "هشتم"}:
        semantics.append("ordinal_date_word")
    if token in {"تاریخ", "جلسه"}:
        semantics.append("calendar_word")
    if token in {
        "امروز چندشنبه‌ست؟", "امروز پنجشنبه، دهم اردیبهشته",
        "جلسه کدوم روزه؟", "سه‌شنبه چندم اردیبهشته؟",
    }:
        semantics.append("date_phrase")
    if token in {"مریم"}:
        semantics.append("person_name")
    if lesson_key.startswith("fa.a1.unit10.lesson06"):
        semantics.append("dialogue_word")
    # Unit 11 (A1: routines), added 2026-07-07. "routine_verb_phrase"
    # (the 4 core routine verbs, all auto-derived multi-token phrases
    # except می‌خوابم which is a single introduced_token but still a
    # genuine member of the same closed set, anchored lesson01).
    # "routine_connector" (هر/بعدش/یه‌کم/معمولاً/دیرتر, 5 members, the
    # sequencing/comparison adverbs used to describe a routine --
    # anchored lesson06, the "completing" lesson, since معمولاً isn't
    # taught until then). "routine_phrase" pools this unit's own genuine
    # taught full-question/full-statement phrases, same explicit-allow-
    # list approach as units 09/10 above.
    if token in {
        "بیدار می‌شم", "صبحونه می‌خورم", "میرم سر کار", "می‌خوابم",
    }:
        semantics.append("routine_verb_phrase")
    if token in {"هر", "بعدش", "یه‌کم", "دیرتر", "معمولاً"}:
        semantics.append("routine_connector")
    if token in {
        "ساعت چند بیدار می‌شی؟", "هر روز", "شب‌ها ساعت یازده می‌خوابم",
        "تو چی؟", "یه‌کم دیرتر",
    }:
        semantics.append("routine_phrase")
    if token in {"نیما"}:
        semantics.append("person_name")
    if lesson_key.startswith("fa.a1.unit11.lesson06"):
        semantics.append("dialogue_word")
    # Unit 12 (A1: plans), added 2026-07-07 by the parallel practice-
    # content-gap-closing pass. "plan_core_word" (برنامه/سینما/بریم, 3
    # members, mixed noun/verb, anchored lesson01). "accept_word"
    # (باشه/عالیه/قبوله, 3 members, anchored lesson03). "decline_word"
    # (متأسفم/نمی‌تونم, 2 members, matching/translation-only, same
    # below-multiple_choice-threshold class as other units' narrow
    # pairs). "invitation_word" (دعوت/منتظرم/می‌بینمت, 3 members, mixed
    # noun/verb, anchored lesson05).
    if token in {"برنامه", "سینما", "بریم"}:
        semantics.append("plan_core_word")
    if token in {"باشه", "عالیه", "قبوله"} and not is_bashe_subjunctive:
        semantics.append("accept_word")
    if token in {"متأسفم", "نمی‌تونم"}:
        semantics.append("decline_word")
    if token in {"دعوت", "منتظرم", "می‌بینمت"}:
        semantics.append("invitation_word")
    if lesson_key.endswith("lesson06.making_a_plan_dialogue"):
        semantics.append("dialogue_word")
    # Unit 13 (A1: past events), added 2026-07-07. "past_verb_first_
    # person" (رفتم/خوردم/دیدم/خوندم, 4 members, anchored lesson05 where
    # the pool completes). "past_verb_third_person" (رفت/دید/کرد/موند/
    # خوند, 5 members, anchored lesson06's third_person_past grammar
    # note). "recent_event_word" (فیلم/ناهار/خوب, 3 members, mixed noun/
    # adjective, anchored lesson04). "recent_event_question_word"
    # (دیروز/چیکار/کردی, 3 members, mixed adverb/pronoun/verb, anchored
    # lesson03). "weekend_misc_word" (موندم/چی؟, 2 members, matching/
    # translation-only).
    if token in {"رفتم", "خوردم", "دیدم", "خوندم"}:
        semantics.append("past_verb_first_person")
    if token in {"رفت", "دید", "کرد", "موند", "خوند"}:
        semantics.append("past_verb_third_person")
    if token in {"فیلم", "ناهار", "خوب"}:
        semantics.append("recent_event_word")
    if token in {"دیروز", "چیکار", "کردی"}:
        semantics.append("recent_event_question_word")
    if token in {"موندم", "چی؟"}:
        semantics.append("weekend_misc_word")
    if lesson_key.endswith("lesson06.weekend_recap_dialogue"):
        semantics.append("dialogue_word")
    # Unit 14 (A1: preferences), added 2026-07-07. "preference_word"
    # (قهوه/چای/موسیقی, 3 members, anchored lesson02 where موسیقی
    # completes the pool). "preference_verb" (داره/نداره, 2 members,
    # matching/translation-only -- the colloquial 3rd-person forms,
    # additive to the existing broader "possession_verb" tag those two
    # tokens already carry). "preference_reason" (خوشمزه‌ست/جالبه, 2
    # members, matching/translation-only; گرمه deliberately excluded even
    # though it also appears as a reason in this unit's reading, since it
    # already belongs to unit07's own weather_state_verb set and adding
    # it here would risk a pragmatically odd generated combination like
    # "music is warm"). "asking_word" (کدوم/بیشتر/یا, 3 members, mixed
    # pronoun/adverb/particle, anchored lesson03).
    if token in {"قهوه", "چای", "موسیقی"}:
        semantics.append("preference_word")
    if token in {"داره", "نداره"}:
        semantics.append("preference_verb")
    if token in {"خوشمزه‌ست", "جالبه"}:
        semantics.append("preference_reason")
    if token in {"کدوم", "بیشتر", "یا"}:
        semantics.append("asking_word")
    if lesson_key.endswith("lesson06.preferences_dialogue"):
        semantics.append("dialogue_word")
    # Unit 15 (A1: comparisons), added 2026-07-07. "comparative_word"
    # pools ALL 8 colloquial comparative forms taught across this unit
    # (بزرگ‌تره/کوچیک‌تره/گرون‌تره/ارزون‌تره/بلندتره/جوون‌تره/بهتره/
    # بدتره) into one set rather than fragmenting into per-lesson
    # subgroups, since they all share the exact same "-تره/-ه" contracted
    # comparative form and this gives a much richer >=3-candidate pool for
    # every one of multiple_choice/matching_pairs/translation (بهتره
    # already existed from unit07 with no semantic tag of its own -- this
    # is a clean additive tag, no conflict). "demonstrative_word"
    # (این/اون, 2 members, matching/translation-only -- این already
    # exists from unit03 with unrelated tags, additive here too).
    if token in {
        "بزرگ‌تره", "کوچیک‌تره", "گرون‌تره", "ارزون‌تره",
        "بلندتره", "جوون‌تره", "بهتره", "بدتره",
    }:
        semantics.append("comparative_word")
    if token in {"این", "اون"}:
        semantics.append("demonstrative_word")
    if lesson_key.endswith("lesson06.comparisons_dialogue"):
        semantics.append("dialogue_word")
    # Unit 16 (A1: travel), added 2026-07-07. "travel_vocab_word" pools this
    # unit's 4 core lesson01 nouns (ticket/train/bus/airport), anchored
    # lesson01. "transport_mode" is a narrower additive subset of just the
    # two actual vehicles (train/bus, 2 members) -- used by this unit's own
    # generative word_order templates below, since "ticket"/"airport" can't
    # grammatically fill a "{X} departs..." sentence the same way.
    # "ticket_request_word" (تهران/می‌خوام/به, 3 members, mixed proper_noun/
    # verb/preposition, anchored lesson02) and "departure_detail_word"
    # (سکو/حرکت/کی, 3 members, mixed noun/pronoun, anchored lesson03) are
    # recognition-only groups, matching the established mixed-POS pattern
    # already used by e.g. a1_unit12's own invitation_word/asking_word.
    # "travel_confirmation_word" (فردا/باشه, 2 members, mixed adverb/verb,
    # anchored lesson05, matching/translation-only -- below the
    # multiple_choice threshold) and "dialogue_role_word" (مسافر/فروشنده,
    # 2 members, both nouns naming the two dialogue participants, anchored
    # lesson05, matching/translation-only) round out this unit's real
    # vocabulary.
    if token in {"بلیط", "قطار", "اتوبوس", "فرودگاه"}:
        semantics.append("travel_vocab_word")
    if token in {"قطار", "اتوبوس"}:
        semantics.append("transport_mode")
    if token in {"تهران", "می‌خوام", "به"}:
        semantics.append("ticket_request_word")
    if token in {"سکو", "حرکت", "کی"}:
        semantics.append("departure_detail_word")
    if token in {"فردا", "باشه"} and not is_bashe_subjunctive:
        semantics.append("travel_confirmation_word")
    if token in {"مسافر", "فروشنده"}:
        semantics.append("dialogue_role_word")
    # Unit 17 (A1: health), added 2026-07-07. "symptom_word" pools every
    # genuine symptom noun/phrase this unit's first two lessons teach
    # (سردرد/تب plus the three auto-derived/single-token symptom phrases
    # حالم خوب نیست/دلم درد می‌کنه/خسته‌ام, 5 members, mixed noun/phrase/
    # verb, anchored lesson02 where خسته‌ام completes the pool) -- mirrors
    # the real realization's own combined match_more_symptoms exercise,
    # which pairs exactly this same mixed word/phrase set. "symptom_noun_
    # word" is a narrower additive subset of just the 2 single-word
    # physical symptoms (سردرد/تب) -- used by this unit's own generative
    # "{symptom} دارم"/"{name} {symptom} داره" word_order templates below,
    # since the 3 phrase-level members can't grammatically follow دارم/داره
    # the same way. "help_word" (کمک/می‌تونی plus the auto-derived
    # می‌تونی کمکم کنی؟ phrase, 3 members, mixed noun/verb/phrase, anchored
    # lesson03) and "advice_word" (دکتر/دارو, 2 members noun, anchored
    # lesson04, matching/translation-only) are recognition groups.
    # "advice_phrase" (the 2 auto-derived imperative-advice phrases
    # استراحت کن/آب بخور, anchored lesson04) is also generative: this
    # unit's own word_order template below combines two distinct members
    # with و, directly mirroring lesson04's own taught "استراحت کن و آب
    # بخور" sentence (both orders read equally naturally as advice).
    if token in {"سردرد", "تب", "حالم خوب نیست", "دلم درد می‌کنه", "خسته‌ام"}:
        semantics.append("symptom_word")
    if token in {"سردرد", "تب"}:
        semantics.append("symptom_noun_word")
    if token in {"کمک", "می‌تونی", "می‌تونی کمکم کنی؟"}:
        semantics.append("help_word")
    if token in {"دکتر", "دارو"}:
        semantics.append("advice_word")
    if token in {"استراحت کن", "آب بخور"}:
        semantics.append("advice_phrase")
    # Unit 18 (A1: work), added 2026-07-07 (en-fa units-18-19
    # practice-authoring pass). "job_asking_word" (شغل/شغلت/چیه, 3
    # members, mixed noun/noun/verb, anchored lesson02 where the pool
    # completes) mirrors the realization's own match_asking_vocab base.
    # "occupation_self_phrase" (مهندسم/معلمم/دکترم, 3 members, all verb
    # per the copula-contraction precedent, anchored lesson01).
    # "workplace_word" (شرکت/مدرسه/بیمارستان, 3 members, anchored
    # lesson03). "workplace_grammar_word" (در/کجا, 2 members, mixed
    # preposition/adverb, translation/matching-only -- below the
    # multiple_choice floor, anchored lesson03). "occupation_third_
    # person" (مهندسه/معلمه, 2 members, translation/matching-only,
    # anchored lesson06 where معلمه completes the pair). "work_verb_form"
    # (می‌کنم/می‌کنی/می‌کنه, 3 members -- additive on top of whatever other
    # tags these very common tokens already carry from earlier units,
    # since combining any of them with the fixed noun کار is always a
    # grammatically valid "I/you/he-she work[s]," anchored lesson05
    # where می‌کنه completes the set).
    if token in {"شغل", "شغلت", "چیه"}:
        semantics.append("job_asking_word")
    if token in {"مهندسم", "معلمم", "دکترم"}:
        semantics.append("occupation_self_phrase")
    if token in {"شرکت", "مدرسه", "بیمارستان"}:
        semantics.append("workplace_word")
    if token in {"در", "کجا"} and lesson_key.startswith("fa.a1.unit18"):
        semantics.append("workplace_grammar_word")
    if token in {"مهندسه", "معلمه"}:
        semantics.append("occupation_third_person")
    if token in {"می‌کنم", "می‌کنی", "می‌کنه"}:
        semantics.append("work_verb_form")
    if lesson_key.endswith("lesson06.jobs_dialogue"):
        semantics.append("dialogue_word")
    # Unit 19 (A1: housing), added 2026-07-07, same pass as unit18 above.
    # "room_word" (خونه/آشپزخانه/حموم/"اتاق خواب", 4 members -- the last
    # is the auto-derived two-token phrase lexeme from lesson01's own
    # otagh_khab_word card -- anchored lesson01) is the unit's core
    # recognition vocabulary. "home_room_word" is a narrower additive
    # subset EXCLUDING خونه (آشپزخانه/حموم/"اتاق خواب", 3 members) -- used
    # by this unit's own generative "خونه‌ی من یه {home_room_word} داره"
    # word_order template, since a خونه candidate there would render the
    # nonsensical "my house has a house." "object_word" (تخت/میز/صندلی,
    # 3 members, anchored lesson03). "is_location_verb" (تخته/آشپزخانه‌س,
    # 2 members, translation/matching-only, anchored lesson04) are the
    # colloquial copula-contracted forms naming what's at a location --
    # deliberately NOT combined generatively with location_word below,
    # since the correct -ه/-س suffix depends on the specific noun's own
    # ending and can't be derived generically per candidate.
    # "house_possessive_word" (خونه‌ی/خونه‌ت, 2 members, translation/
    # matching-only, anchored lesson06 where خونه‌ت completes the pair).
    if token in {"خونه", "آشپزخانه", "حموم", "اتاق خواب"}:
        semantics.append("room_word")
    if token in {"آشپزخانه", "حموم", "اتاق خواب"}:
        semantics.append("home_room_word")
    if token in {"تخت", "میز", "صندلی"}:
        semantics.append("object_word")
    if token in {"تخته", "آشپزخانه‌س"}:
        semantics.append("is_location_verb")
    if token in {"خونه‌ی", "خونه‌ت"}:
        semantics.append("house_possessive_word")
    # تو's spatial-preposition sense (unit19 lesson04, "in/inside") is
    # given its own home_location_word tag alongside کنار/بالای, the 3
    # real location words this lesson teaches together -- scoped to this
    # lesson_key so the PRONOUN sense of تو (used throughout the course,
    # e.g. unit18's تو چی؟) never picks this tag up. کنار/بالای get the
    # same tag layered additively on top of whatever tags they already
    # carry from earlier units (کنار: preposition, already established
    # unit05; بالای: brand new this unit).
    if token in {"تو", "کنار", "بالای"} and lesson_key == "fa.a1.unit19.lesson04.location_in_home":
        semantics.append("home_location_word")
    if lesson_key.endswith("lesson06.housing_dialogue"):
        semantics.append("dialogue_word")
    # Unit 20 (A1: clothing), added 2026-07-09 (en-fa overnight
    # practice-depth pass, units 20+). "clothing_word" pools the 4
    # clothing-item nouns plus قشنگ (mixed noun/adjective, 5 members,
    # anchored lesson01, mirrors the realization's own 5-pair
    # match_clothing_words exercise). "clothing_item_word" is the
    # narrower additive noun-only subset (4 members) used for this pack's
    # generative "{X} می‌خوام"/"این {X} چنده؟" word_order templates,
    # since قشنگ can't grammatically fill either frame. کت is additive
    # here on top of its existing unit07 "coat" entry -- same referent,
    # reused not re-glossed. "color_full_word" pools رنگ with the 4 color
    # adjectives (5 members, anchored lesson02, mirrors the realization's
    # own 5-pair match_colors exercise); "color_word" is the narrower
    # additive adjective-only subset (4 members) for the generative
    # "یه {item} {color} می‌خوام" template mirroring lesson06's own real
    # dialogue line "یه پیراهن آبی می‌خوام". "size_full_word" pools سایز
    # with the 3 size adjectives (4 members, anchored lesson03, mirrors
    # the realization's own 4-pair match_sizes exercise); "size_word" is
    # the narrower additive adjective-only subset (3 members) for the
    # generative "سایز {size}" template mirroring lesson03's own real
    # "سایز بزرگ" exercise. "try_on_phrase" pools the one non-colliding
    # auto-derived lesson04 phrase lexeme with the two individual review
    # tokens بله/بفرمایید (translation/matching-only, below the
    # multiple_choice floor, same mixed-type class as e.g. unit17's own
    # help_word). Deliberately NOT using the auto-derived phrase
    # "بله، بفرمایید." itself as a pack slot member: it's a real
    # dead-anchor homograph with unit06's restaurant dialogue, which
    # already introduces the byte-identical phrase text for an unrelated
    # "waiter confirms the order" meaning. This pack's phrase-derivation
    # discriminator-key fix in _classify_fa (see the "trying_on_clothes"
    # key below) keeps iter_specs() itself correct for either sense, but
    # both senses still share one physical Lexeme row at DB-persistence
    # time (main()'s existing-row lookup matches on token+part_of_speech
    # only, not on this Python-side dict key) -- so relying on that
    # specific phrase text for a generated practice item risks drawing
    # whichever sense's gloss happened to be written to the DB last.
    # Reusing بله/بفرمایید as plain review tokens instead sidesteps this
    # entirely (each is its own long-established, non-colliding Lexeme).
    if token in {"پیراهن", "شلوار", "کفش", "کت", "قشنگ"}:
        semantics.append("clothing_word")
    if token in {"پیراهن", "شلوار", "کفش", "کت"}:
        semantics.append("clothing_item_word")
    if token in {"رنگ", "قرمز", "آبی", "سیاه", "سفید"}:
        semantics.append("color_full_word")
    if token in {"قرمز", "آبی", "سیاه", "سفید"}:
        semantics.append("color_word")
    if token in {"سایز", "بزرگ", "کوچیک", "متوسط"}:
        semantics.append("size_full_word")
    if token in {"بزرگ", "کوچیک", "متوسط"}:
        semantics.append("size_word")
    if token == "می‌تونم امتحانش کنم؟" and lesson_key == "fa.a1.unit20.lesson04.trying_on":
        semantics.append("try_on_phrase")
    if token in {"بله", "بفرمایید"} and lesson_key == "fa.a1.unit20.lesson04.trying_on":
        semantics.append("try_on_phrase")
    if lesson_key.endswith("lesson06.store_dialogue"):
        semantics.append("dialogue_word")
    # Unit 21 (A1: money), added 2026-07-09 (en-fa overnight
    # practice-depth pass, units 20+). "money_word" pools the 4 core
    # nouns (پول/بانک/دلار/تبدیل, anchored lesson01, mirrors the
    # realization's own 4-pair match_money_words exercise).
    # "exchange_word" pools the 4 review/new words lesson02 teaches
    # alongside its two phrases (به/تومن/چقدر/دارید, mixed preposition/
    # noun/pronoun/verb, anchored lesson02, mirrors the realization's own
    # match_exchange_phrases exercise's word-level pairs). "atm_word"
    # pools خودپرداز with از/بردارم (mixed noun/preposition/verb, 3
    # members, anchored lesson03, mirrors match_atm_phrases). "change_
    # word" pools خرد with بفرمایید (mixed adjective/verb, 2 members,
    # translation/matching-only, below the multiple_choice floor, same
    # class as other units' narrow pairs -- بفرمایید is additive here on
    # top of its long-established unit01 entry). "rate_word" pools نرخ
    # with هر (mixed noun/adjective, 2 members, translation/matching-
    # only, anchored lesson05).
    if token in {"پول", "بانک", "دلار", "تبدیل"}:
        semantics.append("money_word")
    if token in {"به", "تومن", "چقدر", "دارید"} and lesson_key == "fa.a1.unit21.lesson02.exchanging_currency":
        semantics.append("exchange_word")
    if token in {"خودپرداز", "از", "بردارم"} and lesson_key == "fa.a1.unit21.lesson03.atm_withdrawal":
        semantics.append("atm_word")
    if token in {"خرد", "بفرمایید"} and lesson_key == "fa.a1.unit21.lesson04.asking_for_change":
        semantics.append("change_word")
    if token in {"نرخ", "هر"} and lesson_key == "fa.a1.unit21.lesson05.asking_the_rate":
        semantics.append("rate_word")
    if lesson_key.endswith("lesson06.bank_dialogue"):
        semantics.append("dialogue_word")
    # Unit 22 (A1: phone), added 2026-07-09 (en-fa overnight
    # practice-depth pass, units 20+). "phone_word" pools the 4 core
    # lesson01 items -- تلفن/پیام/صدا plus the auto-derived "زنگ زدن"
    # phrase lexeme (mixed noun/phrase, anchored lesson01, mirrors
    # match_phone_words). تلفن/پیام already carry unrelated tags from
    # earlier units (unit02's phone_number, a2_unit10's family_message_
    # word) -- additive here, same meaning throughout, not a homograph.
    # "phone_answer_word" pools الو/منم (2 members, translation/
    # matching-only, anchored lesson02). "repeat_word" pools تکرار/
    # آهسته‌تر/صحبت (3 members, anchored lesson03, mirrors
    # match_repeat_phrases' word-level pairs); "repeat_phrase" pools the
    # 2 auto-derived lesson03 sentence-level phrases (translation/
    # matching-only). "message_word" pools برات/بیا/کافه (3 members,
    # anchored lesson04 -- برات is additive on top of its existing
    # unit12-ish preposition entry, same meaning throughout);
    # "message_phrase" pools the 2 auto-derived lesson04 sentence-level
    # phrases. "call_ending_word" pools بعداً/بهتر/شد/الان (4 members,
    # anchored lesson05 -- الان additive on top of its existing entry);
    # "ending_phrase" pools the 2 auto-derived lesson05 sentence-level
    # phrases.
    if token in {"تلفن", "پیام", "صدا", "زنگ زدن"}:
        semantics.append("phone_word")
    if token in {"الو", "منم"} and lesson_key == "fa.a1.unit22.lesson02.answering_the_phone":
        semantics.append("phone_answer_word")
    if token in {"تکرار", "آهسته‌تر", "صحبت"} and lesson_key == "fa.a1.unit22.lesson03.asking_to_repeat":
        semantics.append("repeat_word")
    if token in {"میشه تکرار کنید؟", "لطفاً آهسته‌تر صحبت کنید"} and lesson_key == "fa.a1.unit22.lesson03.asking_to_repeat":
        semantics.append("repeat_phrase")
    if token in {"برات", "بیا", "کافه"} and lesson_key == "fa.a1.unit22.lesson04.reading_a_text_message":
        semantics.append("message_word")
    if token in {"یه پیام برات دارم", "فردا ساعت چهار بیا کافه"} and lesson_key == "fa.a1.unit22.lesson04.reading_a_text_message":
        semantics.append("message_phrase")
    if token in {"بعداً", "بهتر", "شد", "الان"} and lesson_key == "fa.a1.unit22.lesson05.ending_a_call":
        semantics.append("call_ending_word")
    if token in {"خداحافظ، بعداً صحبت می‌کنیم", "الان بهتر شد؟"} and lesson_key == "fa.a1.unit22.lesson05.ending_a_call":
        semantics.append("ending_phrase")
    if lesson_key.endswith("lesson06.phone_dialogue"):
        semantics.append("dialogue_word")
    # Unit 23 (A1: emotions), added 2026-07-09 (en-fa overnight
    # practice-depth pass, units 20+). "basic_feeling_word" pools the 3
    # core lesson01 adjectives (خوشحال/ناراحت/خسته, anchored lesson01,
    # all 3 genuinely available there). "feeling_word" is the FULL
    # growing 6-member superset (adds گشنه at lesson02, عصبانی/نگران at
    # lesson03) -- anchored lesson03, the completing lesson, same
    # growing-pool precedent already established by a1_unit17's own
    # symptom_word (anchored at ITS completing lesson, not lesson01
    # despite 2 of 5 members being taught there). "hunger_word" pools
    # گشنه with یکم (2 members, mixed adjective/adverb, translation/
    # matching-only, anchored lesson02 -- یکم additive on top of its
    # existing adverb entry). "feeling_1st_person_word" pools the 5
    # colloquial "I am X" contractions (anchored lesson03, where
    # عصبانی‌ام completes the set) -- deliberately NOT built as a
    # generative "{feeling_word}م" word_order frame, since the correct
    # contraction suffix genuinely varies by word ending (خوشحالم has no
    # inserted vowel, گشنه‌ام/عصبانی‌ام do) and can't be derived
    # generically per candidate, the same caution already applied to
    # a1_unit19's is_location_verb. "asking_state_word" pools چرا/نگرانی
    # (2 members, anchored lesson03, translation/matching-only).
    # "reason_word" pools تعطیله/امروز/زیاد (3 members, anchored lesson04
    # -- امروز additive on top of its existing adverb entry).
    # "reading_word" pools فقط/خسته‌ست/کرده/نیست (4 members, anchored
    # lesson05 -- نیست additive on top of its existing copula entry).
    # "reaction_word" pools چه/خوشحاله (2 members, anchored lesson06,
    # translation/matching-only -- چه additive on top of its existing
    # pronoun entry). One generative template reuses feeling_word:
    # "{feeling_a} و {feeling_b}" (distinct pair joined by و) is always
    # grammatical regardless of which two feelings are picked, same
    # "join any two words with و" pattern already used by units 20-22.
    if token in {"خوشحال", "ناراحت", "خسته"}:
        semantics.append("basic_feeling_word")
    if token in {"خوشحال", "ناراحت", "خسته", "گشنه", "عصبانی", "نگران"}:
        semantics.append("feeling_word")
    if token in {"گشنه", "یکم"} and lesson_key == "fa.a1.unit23.lesson02.asking_how_someone_is":
        semantics.append("hunger_word")
    if token in {"خوشحالم", "ناراحتم", "خسته‌ام", "گشنه‌ام", "عصبانی‌ام"}:
        semantics.append("feeling_1st_person_word")
    if token in {"چرا", "نگرانی"} and lesson_key == "fa.a1.unit23.lesson03.more_feelings":
        semantics.append("asking_state_word")
    if token in {"تعطیله", "امروز", "زیاد"} and lesson_key == "fa.a1.unit23.lesson04.giving_a_reason":
        semantics.append("reason_word")
    if token in {"فقط", "خسته‌ست", "کرده", "نیست"} and lesson_key == "fa.a1.unit23.lesson05.reading_about_feelings":
        semantics.append("reading_word")
    if token in {"چه", "خوشحاله"} and lesson_key == "fa.a1.unit23.lesson06.feelings_dialogue":
        semantics.append("reaction_word")
    if lesson_key.endswith("lesson06.feelings_dialogue"):
        semantics.append("dialogue_word")
    # Unit 24 (A1: hobbies), added 2026-07-09 (en-fa overnight
    # practice-depth pass, units 20+). "hobby_word" pools سرگرمی with the
    # 2 auto-derived lesson01 phrase lexemes "وقت آزاد"/"کتاب خوندن" (3
    # members, mixed noun/phrase, anchored lesson01, mirrors
    # match_basic_hobbies_vocab). "music_movie_word" pools موسیقی/فیلم/
    # می‌بینم with the auto-derived "گوش می‌دم" phrase (4 members, mixed
    # noun/verb/phrase, anchored lesson02, mirrors match_music_movies_
    # vocab). "sport_word" pools ورزش/فوتبال/بازی (3 members, anchored
    # lesson03, mirrors match_sport_vocab's new-word subset).
    # "frequency_word" pools هفته/گاهی (2 members, translation/matching-
    # only, anchored lesson04). "reading_hobby_word" pools می‌خونه/
    # می‌کنه/هم (3 members, anchored lesson05) -- deliberately excludes
    # "چند تا" despite this lesson's own teach.chand_ta_phrase card: that
    # exact phrase text is a real dead-anchor collision with unit04's own
    # "چند تا" (narrower "how many"-only sense/gloss there vs. this
    # unit's broader "a few / how many"), given its own discriminator key
    # below for iter_specs() correctness, but still not used as an actual
    # slot member here, same DB-persistence-collapse caution already
    # documented for unit20's بله، بفرمایید. "closing_word" pools دیدن
    # with the auto-derived "می‌رم سینما" phrase (2 members, translation/
    # matching-only, anchored lesson06).
    if token in {"سرگرمی", "وقت آزاد", "کتاب خوندن"}:
        semantics.append("hobby_word")
    if token in {"موسیقی", "فیلم", "می‌بینم", "گوش می‌دم"} and lesson_key == "fa.a1.unit24.lesson02.music_and_movies":
        semantics.append("music_movie_word")
    if token in {"ورزش", "فوتبال", "بازی"} and lesson_key == "fa.a1.unit24.lesson03.sport":
        semantics.append("sport_word")
    if token in {"هفته", "گاهی"} and lesson_key == "fa.a1.unit24.lesson04.how_often":
        semantics.append("frequency_word")
    if token in {"می‌خونه", "می‌کنه", "هم"} and lesson_key == "fa.a1.unit24.lesson05.reading_about_a_hobby":
        semantics.append("reading_hobby_word")
    if token in {"دیدن", "می‌رم سینما"} and lesson_key == "fa.a1.unit24.lesson06.hobbies_dialogue":
        semantics.append("closing_word")
    if lesson_key.endswith("lesson06.hobbies_dialogue"):
        semantics.append("dialogue_word")
    # -----------------------------------------------------------------
    # A1 units 25-30 and 37-57 + B1 units 12-16, added 2026-07-22 by the
    # en-fa checkpoint-coverage pass.
    #
    # ONE RULE governs every group below and it is not obvious, so it is
    # written out once here instead of per unit: `generate_checkpoint()`
    # only sees lexemes whose provenance lesson belongs to THAT unit, and
    # a lexeme's provenance is its FIRST introduction anywhere in the
    # course (iter_specs keys on (level, token), first occurrence wins).
    # So every group below contains only tokens this unit itself
    # introduces first -- never a review word it merely reuses. Tagging a
    # reused word here would attach the tag to the EARLIER unit's lexeme
    # and silently contribute nothing to this unit's checkpoint. That is
    # also why several of these groups are small: units 42/45/49-53/55-57
    # and B1 unit16 are review-heavy by construction (see this pass's
    # report for the per-unit hostable counts).
    # Unit 25 (appearance).
    if token in {"قدش", "بلند", "بلنده", "کوتاه", "کوتاهه"}:
        semantics.append("height_word")
    if token in {"مو", "موی", "موهاش", "مشکی", "مشکیه", "بلوند", "بلونده"}:
        semantics.append("hair_word")
    if token in {"چشمای", "چشماش", "قهوه‌ای", "قهوه‌ایه", "سبز", "سبزه", "آبیه"}:
        semantics.append("eye_word")
    if token == "چشم" and lesson_key in CHESHM_EYE_LESSONS:
        semantics.append("eye_word")
    if token in {"بلند", "کوتاه", "مشکی", "بلوند", "قهوه‌ای", "سبز"}:
        semantics.append("appearance_adjective")
    if token in {"عینک", "می‌زنه", "شکلیه", "رنگیه"}:
        semantics.append("appearance_question_word")
    # Unit 26 (animals).
    if token in {"حیوان", "سگ", "گربه", "پرنده", "ماهی"}:
        semantics.append("animal_word")
    if token in {"خونگی", "حیوان"}:
        semantics.append("pet_word")
    if token in {"اسمش", "سگم", "پشمک", "پشمکه"}:
        semantics.append("pet_name_word")
    if token in {"سفیده", "گربه‌ی", "خوشگل", "خوشگله"}:
        semantics.append("pet_description_word")
    if token in {"منه", "سگمه"}:
        semantics.append("ownership_word")
    # Unit 27 (sports).
    if token in {"بسکتبال", "والیبال", "شنا"}:
        semantics.append("sport_name_word")
    if token in {"باشگاه", "استخر"}:
        semantics.append("sport_place_word")
    if token in {"ورزشی", "می‌ری", "بار"}:
        semantics.append("sport_question_word")
    if token == "می‌ره" and lesson_key.startswith("fa.a1.unit27"):
        semantics.append("sport_question_word")
    # Unit 28 (transportation).
    if token in {"مترو", "دوچرخه", "تاکسی", "پیاده"}:
        semantics.append("transport_mode_word")
    if token in {"چقدره", "ورزشه"}:
        semantics.append("transport_comment_word")
    # Unit 29 (technology).
    if token in {"تکنولوژی", "گوشی", "کامپیوتر", "اینترنت"}:
        semantics.append("device_word")
    if token in {"دانلود", "گوشیت"}:
        semantics.append("phone_use_word")
    # Unit 30 (education).
    if token in {"دانشجو", "درس", "زبان"}:
        semantics.append("study_word")
    if token in {"ریاضی", "رشته", "رشته‌ی", "ریاضیه"}:
        semantics.append("subject_word")
    if token in {"یاد", "می‌خونی"}:
        semantics.append("learning_verb_word")
    # Unit 37 (colors).
    if token in {"زرد", "نارنجی", "صورتی", "بنفش", "خاکستری"}:
        semantics.append("new_color_word")
    if token in {
        "زرده", "نارنجیه", "صورتیه", "بنفشه", "خاکستریه", "سیاهه", "قرمزه",
    }:
        semantics.append("color_state_verb")
    if token in {"موز", "پیراهنم", "کتابم", "کتابت", "ماشینت", "گربه‌ی من"}:
        semantics.append("colored_object_word")
    if token in {"رنگش", "چه رنگیه", "چه رنگی"}:
        semantics.append("color_question_word")
    if token in {"تو خونه", "اونجاست", "دوست دارد"}:
        semantics.append("color_reading_word")
    # Unit 38 (seasons).
    if token in {"بهار", "تابستان", "پاییز", "زمستان", "فصل", "چهار فصل"}:
        semantics.append("season_word")
    if token in {"اسکی", "برف"}:
        semantics.append("season_activity_word")
    if token in {"برفیه", "سرد نیست"}:
        semantics.append("season_state_verb")
    # "تو چی؟" is deliberately NOT a member: unit38 reuses it but it is
    # first introduced (and therefore anchored) back in unit11, so tagging
    # it here would only widen unit11's pool, never unit38's checkpoint.
    if token in {"کدوم فصل", "دوست داری"} and lesson_key.startswith("fa.a1.unit38"):
        semantics.append("season_choice_word")
    # Unit 39 (emergencies).
    if token in {"پلیس", "آمبولانس", "آتش‌نشانی"}:
        semantics.append("emergency_service_word")
    if token in {"آتش", "خطر", "تصادف"}:
        semantics.append("danger_word")
    if token in {"اورژانس", "اورژانسه", "بزنید"}:
        semantics.append("emergency_call_word")
    # Unit 40 (lost items).
    if token in {"کیف", "کلید", "گذرنامه"}:
        semantics.append("lost_item_word")
    if token in {"گم", "پیدا", "دیدید"}:
        semantics.append("lost_found_verb_word")
    if token in {"گمشده", "پیداشده"}:
        semantics.append("notice_status_word")
    # Unit 41 (appointments).
    if token in {"دندانپزشک", "مطب"}:
        semantics.append("appointment_place_word")
    if token in {"آزادم", "آزادید"}:
        semantics.append("availability_word")
    # Units 40/41 both introduce a courtesy title; grouped once so a
    # title slot has two members course-wide while each row stays
    # anchored in its own unit.
    if token in {"آقای", "خانم"}:
        semantics.append("courtesy_title_word")
    # Unit 42 (library).
    if token in {"کتابخونه", "امانت"}:
        semantics.append("library_word")
    # Unit 43 (waste disposal).
    if token in {"زباله", "سطل", "کاغذ", "پلاستیک", "شیشه", "بازیافت"}:
        semantics.append("waste_word")
    if token in {"می‌ندازم", "می‌ندازی"}:
        semantics.append("waste_verb_word")
    if token in {"پلاستیکه", "بازیافته"}:
        semantics.append("waste_state_verb")
    if token in {"جمع‌آوری", "شنبه‌ست"}:
        semantics.append("collection_word")
    # Unit 44 (accommodation).
    if token in {"رزرو", "صبحانه", "وای‌فای", "خروج", "مهمان"}:
        semantics.append("hotel_word")
    if token in {"صبحانه‌ست", "وای‌فایه", "مهمانه", "ظهره"}:
        semantics.append("hotel_state_verb")
    # Unit 45 (pharmacy).
    if token in {"داروخانه", "قرص", "قبل"}:
        semantics.append("pharmacy_word")
    # Unit 46 (personal care).
    if token in {"سلمانی", "موهام", "کوتاه‌تر", "مثل قبل"}:
        semantics.append("salon_word")
    # Unit 47 (bike rental).
    if token in {"کرایه", "ودیعه", "دوچرخه‌ی"}:
        semantics.append("rental_word")
    if token in {"کوچیک می‌خوای یا بزرگ؟", "کی پس می‌دم؟"}:
        semantics.append("rental_question_phrase")
    if token == "پس" and lesson_key in PAS_RETURN_LESSONS:
        semantics.append("return_word")
    # Unit 48 (laundry).
    if token in {"خشکشویی", "فوری"}:
        semantics.append("laundry_word")
    if token in {"فردا ظهر خوبه؟", "کِی می‌گیرم؟"}:
        semantics.append("laundry_question_phrase")
    # Unit 49 (swimming pool).
    if token in {"کمد", "بازه", "استخر بازه؟"}:
        semantics.append("pool_facility_word")
    # Unit 50 (restaurant).
    if token in {"سفارش", "چلوکباب", "دوغ"}:
        semantics.append("restaurant_order_word")
    # Unit 51 (cinema).
    if token == "سانس":
        semantics.append("cinema_word")
    # Unit 52 (museum).
    if token in {"موزه", "نمایشگاه", "قدیمی"}:
        semantics.append("museum_word")
    # Unit 53 (concert).
    # "چه ساعتی؟" excluded for the same reason as unit38's "تو چی؟"
    # above -- it is anchored in unit12.
    if token in {"کنسرت", "خواننده"} and lesson_key.startswith("fa.a1.unit53"):
        semantics.append("concert_word")
    # Unit 54 (park).
    if token in {"پیک‌نیک", "درخت", "قدم", "بزنیم"}:
        semantics.append("park_word")
    # Unit 55 (gym).
    if token in {"روزانه", "وزنه"}:
        semantics.append("gym_word")
    # Unit 56 (beach).
    if token in {"ساحل", "دریا", "ماسه"}:
        semantics.append("beach_word")
    # Unit 57 (zoo).
    if token in {"باغ‌وحش", "شیر", "فیل"}:
        semantics.append("zoo_word")
    # Every surname/place name units 40-57 introduce joins the existing
    # course-wide "person_name" pool (each anchored in its own unit, so a
    # unit checkpoint still only ever sees its own).
    if token in {
        "کریمی", "احمدی", "رضایی", "صادقی", "رستمی", "صالحی", "نوری",
        "مرادی", "کاظمی", "جعفری", "رحیمی", "موسوی", "فرهادی", "حسینی",
        "شریفی", "شاهین",
    }:
        semantics.append("person_name")
    if token in {"ملت", "نور", "ارم", "پشمک"}:
        semantics.append("proper_name_word")
    # B1 unit12 (real conditions).
    if token in {"بیاد", "داشتی", "نتونستی", "بیای", "نتونه"}:
        semantics.append("conditional_verb_word")
    if token in {"بارون", "می‌رن", "می‌ریم", "پیامت", "پیامش", "دارن"}:
        semantics.append("plan_b_word")
    if token in {"بده", "بزن"}:
        semantics.append("conditional_imperative_word")
    # B1 unit13 (time clauses).
    if token in {"بشه", "رسیدم", "دادم", "بزنه"}:
        semantics.append("time_clause_verb")
    if token in {"زمان‌بندی", "روشنه", "ساکت"}:
        semantics.append("schedule_word")
    if token in {"زدید", "بدید"}:
        semantics.append("polite_request_verb")
    # B1 unit14 (reported messages).
    if token in {"خواست", "خواسته", "داده", "افتاده", "بزنم", "عقب"}:
        semantics.append("reported_speech_verb")
    if token in {"ازم", "ازت", "ازش", "بهش"}:
        semantics.append("pronoun_incorporated_prep")
    if token in {"خلاصه", "پیامی", "خبری", "پیام‌ها", "منتقل", "آخرش", "فرداست"}:
        semantics.append("message_summary_word")
    # B1 unit15 (purpose clauses).
    if token in {"هدف", "دوم", "پولی", "اینه"}:
        semantics.append("purpose_goal_word")
    if token in {"جمع", "بیرون", "می‌خوره"}:
        semantics.append("saving_action_word")
    if token in {"بتونه", "بتونن", "بشم"}:
        semantics.append("ability_subjunctive_verb")
    if token in {"فارسی‌ام", "فارسی‌اش", "راحت‌تر", "اومد", "یادداشت‌ها"}:
        semantics.append("personal_progress_word")
    # B1 unit16 (goals and plans).
    if token in {"بتونم", "بتونیم"}:
        semantics.append("ability_purpose_verb")
    if token in {"خرج", "تقسیم", "صحبت", "کارها"} and lesson_key.startswith(
        "fa.b1.unit16"
    ):
        semantics.append("teamwork_word")
    # Second sweep over the same 32 units: tokens these units introduce
    # first but that no topical group above happened to name -- mostly
    # review vocabulary reaching a NEW course level (a1 words appearing at
    # b1 for the first time) and the conjugated siblings of a group's own
    # verbs. Folded into the nearest existing group rather than left
    # untagged, since an untagged lexeme is un-hostable by any semantic
    # slot and therefore dead weight in its unit's checkpoint.
    if token == "اپلیکیشن" and lesson_key.startswith("fa.a1.unit29"):
        semantics.append("device_word")
    if token in {"می‌فرستم", "می‌گیرم", "می‌گیره", "می‌فرسته"} and lesson_key.startswith(
        "fa.a1.unit29"
    ):
        semantics.append("phone_use_word")
    if token in {"غذا", "می‌ده"} and lesson_key.startswith("fa.a1.unit26"):
        semantics.append("pet_food_word")
    if token == "ماشین" and lesson_key.startswith("fa.a1.unit28"):
        semantics.append("transport_mode_word")
    if token == "دانشگاه" and lesson_key.startswith("fa.a1.unit30"):
        semantics.append("study_word")
    if token == "می‌خونم" and lesson_key.startswith("fa.a1.unit30"):
        semantics.append("learning_verb_word")
    if token in {"ماشینم", "روی"} and lesson_key.startswith("fa.a1.unit37"):
        semantics.append("colored_object_word")
    if token == "داریم" and lesson_key.startswith("fa.a1.unit38"):
        semantics.append("season_state_verb")
    if token == "لازمه" and lesson_key.startswith("fa.a1.unit39"):
        semantics.append("emergency_call_word")
    if token == "روزی" and lesson_key.startswith("fa.a1.unit45"):
        semantics.append("pharmacy_word")
    if token == "باز" and lesson_key.startswith("fa.a1.unit49"):
        semantics.append("pool_facility_word")
    if token == "شروع" and lesson_key.startswith("fa.a1.unit51"):
        semantics.append("cinema_word")
    if token == "ببینیم" and lesson_key.startswith("fa.a1.unit57"):
        semantics.append("zoo_word")
    if token in {"می‌کنیم", "خبر"} and lesson_key.startswith("fa.b1.unit12"):
        semantics.append("plan_b_word")
    if token in {"می‌زنم", "می‌شم"} and lesson_key.startswith("fa.b1.unit13"):
        semantics.append("time_clause_verb")
    if token == "شروع" and lesson_key.startswith("fa.b1.unit13"):
        semantics.append("schedule_word")
    if token in {"داد", "آماده‌ست"} and lesson_key.startswith("fa.b1.unit14"):
        semantics.append("reported_speech_verb")
    if token == "اول" and lesson_key.startswith("fa.b1.unit14"):
        semantics.append("message_summary_word")
    if token in {"تمرین", "غذا", "می‌خورم"} and lesson_key.startswith("fa.b1.unit15"):
        semantics.append("saving_action_word")
    if token in {"چند", "پیش", "می‌خونم"} and lesson_key.startswith("fa.b1.unit15"):
        semantics.append("personal_progress_word")
    # The remaining dialogue-lesson tokens, listed by TOKEN rather than
    # swept up by a lesson-only "any dialogue lesson in this range" rule.
    # That sweep was written first and reverted the same day: because
    # _classify_fa MERGES semantic tags into a token's existing (earlier)
    # spec, a lesson-only rule tags every review word the dialogue reuses
    # -- it put "dialogue_word" on 73 lexemes anchored in units 01-24,
    # silently widening those already-shipped units' own practice pools.
    # Any tag added here must therefore be keyed on tokens THIS unit
    # introduces first.
    if token in {"سخته"} and lesson_key.startswith("fa.a1.unit30"):
        semantics.append("learning_verb_word")
    if token in {"باحاله!"} and lesson_key.startswith("fa.a1.unit37"):
        semantics.append("color_reading_word")
    if token in {"بیایید"} and lesson_key.startswith("fa.a1.unit39"):
        semantics.append("emergency_call_word")
    if token in {"هوا", "می‌کنن", "پارک", "کافه", "منتظر"} and lesson_key.startswith(
        "fa.b1.unit12"
    ):
        semantics.append("plan_b_word")
    if token in {"می‌فرسته", "می‌فرستم", "بهتون"} and lesson_key.startswith(
        "fa.b1.unit13"
    ):
        semantics.append("polite_request_verb")
    if token == "جدی" and lesson_key in JADI_REALLY_LESSONS:
        semantics.append("message_summary_word")
    if semantics:
        tags["semantic"] = list(dict.fromkeys(semantics))
    person = {
        "من": "first", "هستم": "first", "ایرانی‌ام": "first",
        "تو": "second", "شما": "second", "هستی": "second",
        "هستید": "second", "هستین": "second", "او": "third",
        "هست": "third", "است": "third", "ایرانیه": "third",
    }.get(token) if not is_too_location else None
    if person:
        tags["person"] = person
    if token in {"من", "تو", "او"} and not is_too_location:
        tags["number"] = "singular"
    elif token == "شما":
        tags["number"] = "polite_or_plural"
    if token == "کجا":
        tags["register"] = "neutral"
    elif token == "کجایی":
        tags["register"] = "informal"
    return tags


# Generated per-unit and per-lesson semantic tags, ported 2026-07-26 from
# the X-en scripts' identical mechanism (backfill_lexemes_fa_en.py /
# _prs_en.py, commit 05af7ace) to close the LAST remaining semantic-tag
# deserts -- the Persian-TARGET direction. The polish wave measured that
# en-fa's a1_31-36, a2_12-16 and b1_01-11 matching_pairs were stuck on bare
# part_of_speech pools (checkpoint-safe, but course-wide off-theme in
# Endless Practice and unfixable pack-side, because those units carry no
# hand-authored agreement_tags.semantic). Two tags per first-introduced
# taggable Farsi token, e.g. `en_fa_a1_unit33_words` +
# `en_fa_a1_unit33_lesson02_words`; emitted ONLY on a token's first
# introduction (a re-used token must never receive a later unit's tag --
# that provenance belongs to the earlier unit, exactly the silent
# checkpoint_unavailable cause the recipe calls defect #2). Purely
# additive: no shipped pack references these names, so no existing pool
# changes until a pack opts in.

# Persian-aware metalanguage guard. The English-TARGET directions must keep
# English grammar terms (noun/verb/clause) out of the generated tags,
# because their B1/B2 grammar cards teach those words as real English
# tokens a vocabulary drill could then wrongly quiz. This course is the
# mirror image: every grammar term is taught in the ENGLISH gloss /
# grammar_note, never as a Farsi token. An audit of FA_GLOSSES confirmed
# ZERO Farsi grammar-metalanguage lexemes (اسم is "name", حرف is
# "talk/word", حال is "mood", جمع is "gathering" -- all vocabulary), so the
# set is empty. It exists for parity and as the hook if a grammar-term
# Farsi token is ever introduced.
METALANGUAGE_TOKENS: frozenset[str] = frozenset()

# noun/verb/adjective/adverb/phrase are drillable vocabulary; pronouns,
# prepositions, particles, symbols and proper nouns are excluded (matching
# over particles is not a vocabulary check; a slot_gloss MC over proper
# nouns self-glosses).
TAGGABLE_POS = frozenset({"noun", "verb", "adjective", "adverb", "phrase"})


def _unit_semantic_tags(unit_stem, lesson_order, token, part_of_speech):
    if part_of_speech not in TAGGABLE_POS or token in METALANGUAGE_TOKENS:
        return []
    if part_of_speech != "phrase" and not all(
        character.isalpha()
        or unicodedata.combining(character)
        or character in "‌-'"  # ZWNJ (Persian compounds) + hyphen + apostrophe
        for character in token
    ):
        # Digits (ASCII or Persian), currency marks, clock colons, Persian
        # punctuation (، ؟ ؛) or spaces: real lexemes, poor slot candidates.
        return []
    return [
        f"en_fa_{unit_stem}_words",
        f"en_fa_{unit_stem}_lesson{lesson_order:02d}_words",
    ]


# Direct-speech glosses for A2 lesson04 dialogue lines (and one reading
# passage), keyed by teaching content_key. The teaching overlays gloss these
# cards as third-person stage narration ("<name> says ..."), sometimes with
# the Persian-script character name inside the English. That reads wrongly
# as a translation in practice (MC options / translate prompts) and leaks
# target-script words. Only the derived PHRASE lexeme's english_gloss uses
# these; the overlay card text and the English source-token extraction are
# unchanged. Added 2026-10-19 (session9 backfill-gloss leakage pass).
PHRASE_GLOSS_OVERRIDES: dict[str, str] = {
    # Teaching-note glosses come from the overlay and quote the Persian
    # token; the gloss is English-only so no translate item shows its answer.
    'fa.a1.unit06.lesson01.teach.va_ya': 'and; or',
    'fa.a1.unit06.lesson02.teach.register_note': 'Use the past-tense form with a stranger or waiter; use the present form only with a close friend.',
    'fa.a1.unit08.lesson02.teach.contraction_note': 'The everyday spoken contraction of the price word plus "is" (it is ... toman).',
    'fa.a1.unit09.lesson02.teach.contraction_note': 'The everyday spoken contraction of "how many" plus "is" (what number is it?).',
    'fa.a2.unit09.lesson04.teach.turn01': 'Please, how can I help you?',
    'fa.a2.unit09.lesson04.teach.turn03': 'Since when have you lived at the new address?',
    'fa.a2.unit09.lesson04.teach.turn04': 'Since last month. Could you tell me what I should bring?',
    'fa.a2.unit09.lesson04.teach.turn06': 'Can I come on Tuesday?',
    'fa.a2.unit09.lesson04.teach.turn07': 'Yes, Tuesday at ten is fine. Your tracking code is 2214.',
    'fa.a2.unit10.lesson04.teach.turn04': "Because I can't concentrate at home, and I like seeing my colleagues.",
    'fa.a2.unit10.lesson04.teach.turn05': 'Okay, but in my opinion traffic takes a lot of time.',
    'fa.a2.unit10.lesson04.teach.turn06': "That's true, but I'm used to it.",
    'fa.a2.unit11.lesson04.teach.turn04': 'Yes, I brought my national ID card and the electricity bill for my new home.',
    'fa.a2.unit11.lesson04.teach.turn05': 'Great. Your bank card will be ready in three days.',
    'fa.a2.unit11.lesson04.teach.turn06': 'When do I get its PIN?',
    'fa.a2.unit11.lesson04.teach.turn07': 'The same day you pick up the card.',
    'fa.a2.unit12.lesson04.teach.turn04': "No, it's just a headache, but it's severe.",
    'fa.a2.unit12.lesson04.teach.turn05': 'Okay, take this prescription and rest for a few days.',
    'fa.a2.unit13.lesson04.teach.turn01': 'Hello, my bathroom pipe is leaking.',
    'fa.a2.unit13.lesson04.teach.turn03': 'Since yesterday. Water is getting onto the floor.',
    'fa.a2.unit13.lesson04.teach.turn04': "Okay, I'll come tomorrow morning and repair it.",
    'fa.a2.unit13.lesson04.teach.turn05': "Thanks, I'm home until 11 o'clock.",
    'fa.a2.unit13.lesson04.teach.turn06': 'All right, see you then.',
    'fa.a2.unit14.lesson04.teach.turn02': 'I worked in an office for three years.',
    'fa.a2.unit14.lesson04.teach.turn03': 'What skills do you have?',
    'fa.a2.unit14.lesson04.teach.turn04': "I'm good at teamwork and problem-solving.",
    'fa.a2.unit14.lesson04.teach.turn05': 'Can you start next week?',
    'fa.a2.unit15.lesson04.teach.turn02': "Unfortunately, because of a technical problem, it's an hour late. It leaves at ten from platform three.",
    'fa.a2.unit15.lesson04.teach.turn04': 'Yes, a bus leaves at nine thirty from platform five, but you have to buy a new ticket.',
    'fa.a2.unit15.lesson04.teach.turn05': "No, it's fine. I'll wait for the train.",
    'fa.a2.unit15.lesson04.teach.turn06': 'Okay, then wait at platform three at ten.',
    'fa.a2.unit16.lesson04.teach.turn01': 'Sara, how much do you use social media every day?',
    'fa.a2.unit16.lesson04.teach.turn04': "In my opinion it's entertaining, but sometimes I also waste time.",
    'fa.a2.unit16.lesson04.teach.turn05': 'I mostly read the news, not social media.',
    'fa.a2.unit16.lesson04.teach.turn06': 'How nice!',
    'fa.a2.unit17.lesson04.teach.turn01': "Sara, how's your week? What's your schedule?",
    'fa.a2.unit17.lesson04.teach.turn02': 'First, I go to work Saturday to Wednesday.',
    'fa.a2.unit18.lesson04.teach.turn01': 'Excuse me, I bought these headphones but they have no sound.',
    'fa.a2.unit18.lesson04.teach.turn02': 'Do you have the receipt? What day did you buy them?',
    'fa.a2.unit18.lesson04.teach.turn03': 'Yes, here you are. I bought them three days ago.',
    'fa.a2.unit18.lesson04.teach.turn04': "No problem, you're within the seven-day window. Do you want us to exchange them or refund your money?",
    'fa.a2.unit18.lesson04.teach.turn06': "Okay, I'll give you a new pair of headphones right now.",
}


def _classify_fa(files, level, fa_specs, seen_en):
    # Keyed by (level, token) -- A1 and A2 are separate courses (separate
    # Lexeme rows are fine/expected even for a token spelled the same in
    # both), so a bare token key would wrongly merge/skip an A2
    # occurrence into an A1 spec already seen (same fix as the sibling
    # backfill_lexemes_en_prs.py).
    for unit_order, (realization_path, overlay_path) in enumerate(files, 1):
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
        overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
        teaching_overlays = overlay["teaching"]
        # "a1_unit33_neighborhood" -> "a1_unit33": the stable per-unit key
        # the generated semantic tags (_unit_semantic_tags) are named after.
        unit_stem = "_".join(realization_path.stem.split("_")[:2])
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson["teaching"]:
                content_key = item["content_key"]
                # B1 unit01's own overlay omits the teaching-card entry
                # entirely (not just a blank gloss) for 9 pure-review
                # content_keys (e.g. teach.unja/teach.kone/teach.ro --
                # tokens already established/glossed elsewhere, found
                # while adding the B1 units 01-06 backfill pass,
                # 2026-07-11) -- .get(content_key, {}) tolerates that
                # gap the same way the existing .get("gloss", "") already
                # tolerates a present-but-blank gloss field, without
                # touching the content itself (out of scope for this
                # script). A1/A2 overlays have always had a complete
                # entry per content_key, so this is a no-op for them.
                gloss = teaching_overlays.get(content_key, {}).get("gloss", "")
                for token in item.get("introduced_tokens", []):
                    if token not in FA_GLOSSES:
                        raise ValueError(f"missing explicit Farsi gloss for {token!r}")
                    tags = fa_agreement_tags(token, lesson_key)
                    key = (level, token)
                    part_of_speech = fa_part_of_speech(token)
                    english_gloss = FA_GLOSSES[token]
                    # تو is genuinely two different lexemes in this course:
                    # the informal second-person PRONOUN "you" (taught
                    # early, used throughout, e.g. "تو چی؟" in units
                    # 11/13/18) versus a spatial/abstract PREPOSITION
                    # sense "in/inside/within" (تو آشپزخانه, "in the
                    # kitchen"; unit14's "تو کار تیمی ... خوبم"; unit18's
                    # "تو مهلت هفت روزه هستید") in TOO_PREPOSITION_LESSONS
                    # above. Same collision class as the en-prs sibling
                    # script's already-established و/می‌شود/کی special
                    # cases -- given its own key/POS/gloss here instead of
                    # letting the second sense silently share the
                    # pronoun's classification (which would make a
                    # preposition-constrained practice slot draw "you," or
                    # a pronoun-constrained slot draw "in/inside").
                    if token == "تو" and lesson_key in TOO_PREPOSITION_LESSONS:
                        key = (level, token, "location_prep")
                        part_of_speech = "preposition"
                        english_gloss = "in / inside / within"
                    # نه is genuinely two different lexemes too: "nine"
                    # (FA_NUMBERS, established since a1_unit03) versus the
                    # negation "no / not" in NO_NEGATION_LESSONS above --
                    # a real, previously-latent bug found while adding A2
                    # units 12/15/16 (2026-07-11). Without this split,
                    # every "no"/"not" occurrence in these three dialogue
                    # lessons would silently inherit the long-established
                    # "nine" gloss/POS/number-tag instead.
                    if token == "نه" and lesson_key in NO_NEGATION_LESSONS:
                        key = (level, token, "negation")
                        part_of_speech = "particle"
                        english_gloss = "no / not"
                    # باشه is genuinely two different lexemes too: the
                    # informal affirmation "okay" (level="a1", established
                    # since a1_unit12) versus the 3rd-singular SUBJUNCTIVE
                    # copula "(if) he/she be/has" that completes B1
                    # unit03's own conditional paradigm, in
                    # BASHE_SUBJUNCTIVE_LESSONS above -- a real, previously
                    # -latent bug class found while adding B1 units 01-06
                    # (2026-07-11). Unlike تو/نه above, NO key-tuple
                    # discriminator is needed here: `key = (level, token)`
                    # already differs (a1 vs b1), since these two senses
                    # never occur within the SAME course/level. Only the
                    # gloss needs overriding here (part_of_speech is
                    # already "verb" for both senses via the shared
                    # FA_VERBS membership, so no override needed there).
                    if token == "باشه" and lesson_key in BASHE_SUBJUNCTIVE_LESSONS:
                        english_gloss = "(if) he/she is / be (subjunctive copula)"
                    # باشید: FA_GLOSSES glosses it "be (polite)" -- the
                    # a1_unit01 farewell-imperative sense (e.g. موفق باشید).
                    # In b1_unit03's داشته باشید real-conditional paradigm it
                    # is the 2nd-plural subjunctive "(if) you (pl.) be",
                    # consistent with its siblings باشی/باشیم/باشن ("(if)
                    # [person] be"); the inherited "be (polite)" gloss shown
                    # as the MC/matching answer there hid the subjunctive
                    # sense the unit teaches. Gloss-only override (a1 vs b1
                    # already separate the two rows). Native review 2026-07-27.
                    if token == "باشید" and lesson_key == "fa.b1.unit03.lesson02.real_condition_all_persons":
                        english_gloss = "(if) you (pl.) be"
                    # چشم / پس / تا: three more genuine homographs, split
                    # 2026-07-22 -- see CHESHM_EYE_LESSONS,
                    # PAS_RETURN_LESSONS and TA_UNTIL_LESSONS above for
                    # each one's evidence. All three get BOTH a key-tuple
                    # discriminator and a distinct part_of_speech, so the
                    # two senses persist as separate Lexeme rows (main()'s
                    # existing-row lookup matches on token+part_of_speech).
                    if token == "چشم" and lesson_key in CHESHM_EYE_LESSONS:
                        key = (level, token, "body_part")
                        part_of_speech = "noun"
                        english_gloss = "eye"
                    if token == "پس" and lesson_key in PAS_RETURN_LESSONS:
                        key = (level, token, "return_back")
                        part_of_speech = "adverb"
                        english_gloss = "back (as in 'to give back')"
                    # Wrong-sense B1 glosses (session9 practice review,
                    # 2026-10-19). Both tokens are keyed per level, so the
                    # A1 senses ("you give (polite)" in تخفیف می‌دید؟,
                    # "company") are untouched. B1 unit07's reading uses
                    # می‌دید as the counterfactual "would have seen"; B1
                    # unit09 uses شرکت only in شرکت کردید ("took part").
                    if level == "b1" and token == "می‌دید":
                        english_gloss = "he/she would see / would have seen"
                    # A1 unit30 (education): می‌خونم means "I study" here
                    # (دانشگاه ... می‌خونم), not "I read".
                    if token == "می‌خونم" and lesson_key.startswith("fa.a1.unit30"):
                        english_gloss = "I study (spoken, 1st person)"
                    if level == "b1" and token == "شرکت":
                        english_gloss = "participation (as in 'to take part')"
                    if token == "تا" and lesson_key in TA_UNTIL_LESSONS:
                        key = (level, token, "until_prep")
                        part_of_speech = "preposition"
                        english_gloss = "until; up to; so that (purpose)"
                    # جدی: gloss-only override, same reasoning as باشه
                    # above (a1 vs b1 already separates the two rows).
                    if token == "جدی" and lesson_key in JADI_REALLY_LESSONS:
                        english_gloss = "really?! (surprised reaction)"
                    # B2 (2026-10-19): per-tier POS / gloss for the sense
                    # the B2 card teaches -- see FA_B2_PART_OF_SPEECH and
                    # FA_B2_GLOSS_OVERRIDES. Level-scoped, so A1-B1 rows
                    # are untouched.
                    if level == "b2":
                        part_of_speech = FA_B2_PART_OF_SPEECH.get(token, part_of_speech)
                        english_gloss = FA_B2_GLOSS_OVERRIDES.get(token, english_gloss)
                    existing = fa_specs.get(key)
                    if existing is None:
                        # ONLY on first introduction -- see
                        # _unit_semantic_tags() above. Uses the RESOLVED
                        # part_of_speech (after the homograph overrides
                        # above), so e.g. تو's location-prep sense is
                        # excluded exactly like its pronoun sense is.
                        unit_tags = _unit_semantic_tags(
                            unit_stem, lesson_order, token, part_of_speech
                        )
                        if level == "b2":
                            unit_tags = unit_tags + FA_B2_EXTRA_TAGS.get(token, [])
                        if unit_tags:
                            semantic = tags.setdefault("semantic", [])
                            semantic.extend(t for t in unit_tags if t not in semantic)
                        fa_specs[key] = {
                            "level": level,
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "fa",
                            "part_of_speech": part_of_speech,
                            "english_gloss": english_gloss, "agreement_tags": tags,
                        }
                    else:
                        for tag_key, value in tags.items():
                            if tag_key == "semantic":
                                prior = existing["agreement_tags"].setdefault(tag_key, [])
                                prior.extend(v for v in value if v not in prior)
                            else:
                                existing["agreement_tags"].setdefault(tag_key, value)

                target_text = item.get("target", {}).get("text", "").strip()
                introduced = item.get("introduced_tokens", [])
                # No phrase-derivation at B1 or B2: its multi-token teaching cards
                # are grammar-note paragraphs and full reading passages, not
                # the short natural phrases this path was built for (same
                # policy the en-prs script chose for its B1 wiring). The
                # length guard is a hard backstop for every level: Lexeme.
                # token is VARCHAR(255), and a newline-free reading passage
                # slipped through here on 2026-07-11 and crashed the real
                # backfill run with StringDataRightTruncation.
                # The label-phrase guard was added 2026-07-22 with A1 units
                # 25-30/37-57. Many of this pack's realizations use review
                # cards whose target TEXT is an authoring LABEL rather than
                # a Persian phrase -- e.g. "رنگ (color) / سفید (white) /
                # ... -- already known from units 20 and 25", or "زندگی
                # می‌کنم = I live". Those satisfy every other condition
                # here and get persisted as real Persian "phrase" lexemes,
                # so a practice item can show a learner a Persian prompt
                # with English gloss text and an authoring note baked into
                # it. A genuine Persian phrase never contains an ASCII
                # letter, so the test rejects exactly that class.
                #
                # It is deliberately scoped to the units THIS pass adds
                # (a1 25-30 and 37-57) instead of applying corpus-wide.
                # 42 such rows are already persisted from earlier passes
                # (units 06/13/16/18/19/23/31-36, a2 11/15/16/18), and
                # _practice_lesson_id() in backend/app/content/service.py
                # resolves a pack's lesson key through
                # Lexeme.provenance_lesson_content_key -- so suppressing an
                # already-written row leaves it stranded on its old lesson
                # and the key then "maps to multiple lessons", which fails
                # the whole practice import. Verified for real against an
                # isolated copy of the dev DB (102 such errors on Farsi A1
                # before this scoping). Cleaning those 42 rows up is a
                # separate coordinator-side task; until then they keep
                # being emitted so they stay re-pointable.
                _guarded_unit = re.match(
                    r"fa\.a1\.unit(\d\d)\.", lesson_key
                )
                _label_guarded = bool(_guarded_unit) and (
                    25 <= int(_guarded_unit.group(1)) <= 30
                    or 37 <= int(_guarded_unit.group(1)) <= 57
                )
                if (
                    len(introduced) > 1
                    and target_text
                    and "\n" not in target_text
                    and level not in ("b1", "b2")
                    and len(target_text) <= 255
                    and not (_label_guarded and re.search(r"[A-Za-z]", target_text))
                ):
                    tags = fa_agreement_tags(target_text, lesson_key)
                    # Generated unit/lesson tags for the derived phrase too
                    # (POS "phrase"). setdefault() below only writes on the
                    # phrase's first occurrence, so a re-derived phrase keeps
                    # its earlier unit's tag -- same first-introduction rule
                    # as the introduced-token path. Single-token matchers
                    # narrow POS to [noun,verb,adjective,adverb], so a phrase
                    # carrying this tag is still excluded from them.
                    phrase_unit_tags = _unit_semantic_tags(
                        unit_stem, lesson_order, target_text, "phrase"
                    )
                    if phrase_unit_tags:
                        semantic = tags.setdefault("semantic", [])
                        semantic.extend(t for t in phrase_unit_tags if t not in semantic)
                    phrase_key = (level, target_text)
                    # Real dead-anchor collision caught 2026-07-09 while
                    # adding unit20 (clothing): unit06's own restaurant
                    # dialogue (lesson06.teach.turn03) already introduces
                    # the byte-identical phrase "بله، بفرمایید." (there,
                    # a waiter confirming an order) -- setdefault() below
                    # would otherwise silently keep unit06's OLD anchor/
                    # gloss ("The waiter confirms and hands over the
                    # menu.") for unit20's genuinely different "Yes, go
                    # ahead [and try it on]" sense. Given its own
                    # discriminator key here, same pattern as تو's
                    # location_prep homograph split above, so unit20's
                    # try_on_phrase group gets its own correctly-anchored,
                    # correctly-glossed entry instead of silently reusing
                    # unit06's.
                    if target_text == "بله، بفرمایید." and content_key.endswith(
                        "teach.yes_go_ahead"
                    ):
                        phrase_key = (level, target_text, "trying_on_clothes")
                    # Same dead-anchor class caught again 2026-07-09 while
                    # adding unit24 (hobbies): unit04's own family-asking
                    # content already introduces the byte-identical phrase
                    # "چند تا" (there, strictly interrogative "how many,"
                    # gloss "how many" only) -- unit24 reuses the same
                    # phrase in a genuinely different, broader sense ("a
                    # few," in a declarative sentence, gloss "a few / how
                    # many"). Without this, setdefault() below would
                    # silently keep unit04's narrower anchor/gloss for
                    # unit24's own occurrence. Given its own discriminator
                    # key, same pattern as بله، بفرمایید above -- note this
                    # pack still does NOT use "چند تا" as an actual slot
                    # member (same DB-persistence-collapse caution as
                    # unit20's own write-up), this fix is for iter_specs()
                    # correctness only.
                    if target_text == "چند تا" and content_key.endswith(
                        "teach.chand_ta_phrase"
                    ):
                        phrase_key = (level, target_text, "hobby_reading_frequency")
                    fa_specs.setdefault(
                        phrase_key,
                        {
                            "level": level,
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": target_text, "language_code": "fa",
                            "part_of_speech": "phrase",
                            "english_gloss": PHRASE_GLOSS_OVERRIDES.get(content_key, gloss),
                            "agreement_tags": tags,
                        },
                    )
                for match in EN_TOKEN_RE.findall(gloss):
                    token = match.casefold().replace("’", "'")
                    seen_key = (level, token)
                    if seen_key in seen_en:
                        continue
                    seen_en.add(seen_key)
                    yield {
                        "level": level,
                        "unit_order": unit_order,
                        "lesson_order": lesson_order,
                        "lesson_content_key": lesson_key,
                        "content_key": content_key,
                        "token": token,
                        "language_code": "en",
                        "part_of_speech": en_part_of_speech(token),
                        "english_gloss": token,
                        "agreement_tags": {"semantic": ["source_gloss"]},
                    }


def iter_specs():
    fa_specs: dict[tuple[str, str], dict] = {}
    seen_en: set[tuple[str, str]] = set()
    yield from _classify_fa(UNIT_FILES, "a1", fa_specs, seen_en)
    yield from _classify_fa(UNIT_FILES_A2, "a2", fa_specs, seen_en)
    yield from _classify_fa(UNIT_FILES_B1, "b1", fa_specs, seen_en)
    yield from _classify_fa(UNIT_FILES_B2, "b2", fa_specs, seen_en)
    yield from fa_specs.values()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and classify content without connecting to the database.",
    )
    args = parser.parse_args()
    specs = list(iter_specs())
    if args.dry_run:
        fa_count = sum(spec["language_code"] == "fa" for spec in specs)
        en_count = sum(spec["language_code"] == "en" for spec in specs)
        print(f"Lexeme backfill dry run: {fa_count} fa, {en_count} en.")
        for level in ("a1", "a2", "b1", "b2"):
            level_fa = sum(
                spec["language_code"] == "fa" and spec["level"] == level
                for spec in specs
            )
            level_en = sum(
                spec["language_code"] == "en" and spec["level"] == level
                for spec in specs
            )
            print(f"  {level}: {level_fa} fa, {level_en} en")
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        courses_by_level = {}
        for level, title in (("a1", "Farsi A1"), ("a2", "Farsi A2"), ("b1", "Farsi B1"), ("b2", "Farsi B2")):
            needed = any(spec["level"] == level for spec in specs)
            course = db.scalar(
                select(Course).where(
                    Course.source_language == "en",
                    Course.target_language == "fa",
                    Course.title == title,
                )
            )
            if course is None:
                if needed:
                    print(f"ERROR: en-fa {title!r} course must be imported first", file=sys.stderr)
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
        repointed = 0
        for spec in specs:
            level = spec.pop("level")
            course = courses_by_level[level]
            lesson = lessons_by_level[level].get(
                (spec.pop("unit_order"), spec.pop("lesson_order"))
            )
            if lesson is None:
                print(
                    f"ERROR: imported course is missing {spec['lesson_content_key']}",
                    file=sys.stderr,
                )
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
                # Refresh reviewed lexical metadata so reruns safely repair
                # earlier backfills.
                existing.english_gloss = spec["english_gloss"]
                existing.agreement_tags = spec["agreement_tags"]
                # Provenance is ALSO refreshed, added 2026-07-22. This used
                # to be pinned ("preserve first-introduction provenance"),
                # which is what a spec already carries anyway: iter_specs()
                # keys fa_specs on (level, token[, sense]) and keeps the
                # FIRST occurrence, so spec's lesson IS the first
                # introduction. Pinning it therefore preserved nothing real
                # -- it only made a wrong provenance permanent, and units
                # 31-36 had exactly that (their rows were written against
                # units 25-30's lessons; see the UNIT_FILES units 25-30
                # comment). Since `generate_checkpoint()` buckets a unit's
                # material strictly by provenance_lesson_id, a stale FK is
                # a dead checkpoint. Idempotent: after one run the values
                # already match and this is a no-op write.
                if existing.provenance_lesson_id != lesson.id:
                    repointed += 1
                existing.provenance_lesson_id = lesson.id
                existing.provenance_lesson_content_key = spec["lesson_content_key"]
                existing.provenance_content_key = spec["content_key"]
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
    print(
        f"Lexeme backfill complete: {created} created, {updated} updated "
        f"({repointed} re-pointed to their correct provenance lesson)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
