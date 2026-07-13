#!/usr/bin/env python3
"""Idempotently backfill reviewed en-prs A1 lexemes (Dari target) from
units 1-2 (unit 1: script ramp through the Kabul workplace dialogue;
unit 2, added 2026-07-05 by the practice-pool-sync lane: name exchange,
origin/hometown, occupation, introducing a third person, polite titles,
and a gathering dialogue).

Written directly (not via Codex -- Codex was rate-limited at authoring
time) mirroring scripts/backfill_lexemes.py's structure and rigor.
Target-side Dari classification is NOT derived from the reference
script's Farsi classification -- verified against this course's own
realization text (docs/content/realizations/prs/a1_unit01_greetings.yaml),
which uses genuinely distinct Afghan forms (استم/استی/استند copulas,
تشکر, جور, شکر) per docs/content/AUTHORING_GUIDE.md's standing warning
that Dari and Farsi share a script but are not interchangeable content.

Note: the underlying en-prs overlay is `review: status: unreviewed` as
of this writing -- built correctly against current content, but a
later content review could still touch wording. Not this script's
problem to solve, flagged for whoever reviews next.

Extended 2026-07-11 to also cover A2 units 11-18 and the full B1 course
(units 01-06, its own separate "Dari B1" course/UNIT_FILES_B1 tuple) --
see UNIT_FILES_A2/UNIT_FILES_B1's own header comments for why each is
kept as a separate, locally-1-based-ordered tuple rather than appended
to UNIT_FILES.

Run via docker compose from backend/, mounting the full repo:
    cd backend
    docker compose run --rm \
      -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_prs.py
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

UNIT_FILES = (
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit01_greetings.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit02_introductions.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit02.yaml",
    ),
    # Units 03-08 (A1), added 2026-07-06 by the practice-pool-sync lane,
    # closing the en-prs practice-pool gap against prs's real A1
    # realization depth (previously only units 1-2 had any practice
    # coverage at all).
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit03_family.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit04_numbers.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit05_places.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit06_directions.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit07_communication.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit08_food.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit08.yaml",
    ),
    # Units 09-11 (A1: dates, shopping, time), added 2026-07-07 -- the
    # real A1 realization grew 8->15 units this same night; this closes
    # the practice-pool gap for units 09-11 specifically (a parallel
    # session is doing 12-15 separately -- re-read this file fresh
    # immediately before any further edit here to coordinate ordering).
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit09_dates.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit10_shopping.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit10.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit11_time.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit11.yaml",
    ),
    # Units 12-15 (A1: routines, plans, preferences, comparisons), added
    # 2026-07-07 by the parallel session mentioned in the unit 09-11
    # comment above -- closes the practice-pool gap for units 12-15
    # specifically (units 09-11 were done separately, same night).
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit12_routines.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit13_plans.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit14_preferences.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit14.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit15_comparisons.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit15.yaml",
    ),
    # Units 16-17 (A1: travel, health), added 2026-07-07 -- the real A1
    # realization grew 15->17 units this same night. Closes the
    # practice-pool gap for these two specifically-new units.
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit16_travel.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit16.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit17_health.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit17.yaml",
    ),
    # Units 18-19 (A1: work, housing), added 2026-07-07 -- the real A1
    # realization grew 17->19 units this session. Closes the practice-pool
    # gap for these two specifically-new units (same pass as the fa
    # sibling script's own units-18-19 extension, authored independently
    # per the sibling-isolation rule).
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit18_work.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit18.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit19_housing.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit19.yaml",
    ),
    # Units 20-24 (A1: past events, clothing, weather, money,
    # transportation), added 2026-07-09 -- practice-pool depth-extension
    # pass closing the gap between the practice manifest (previously
    # capped at unit19) and the real prs realization depth (now through
    # unit44+). Only units 20-24 are backfilled in this pass.
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit20_past_events.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit20.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit21_clothing.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit21.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit22_weather.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit22.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit23_money.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit23.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit24_transportation.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit24.yaml",
    ),
    # Units 25-30 (A1: emotions, hobbies, appearance, animals, sports,
    # technology), added 2026-07-11 -- practice-pool depth-extension pass
    # closing part of the gap between the practice manifest (previously
    # capped at unit24 for A1) and the real prs realization depth (now
    # through unit61). All six units are `status: reviewed` on disk.
    # Only units 25-30 are backfilled in this pass.
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit25_emotions.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit25.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit26_hobbies.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit26.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit27_appearance.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit27.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit28_animals.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit28.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit29_sports.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit29.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit30_technology.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit30.yaml",
    ),
    # Units 31-40 (A1: education, celebrations, household, neighborhood,
    # post, cooking, personality, colors, seasons, emergencies), added
    # 2026-07-11 -- second practice-pool depth-extension pass, continuing
    # directly from the units 25-30 pass. All ten are `status: reviewed`
    # on disk (both the prs realization and the en-prs overlay).
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit31_education.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit31.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit32_celebrations.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit32.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit33_household.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit33.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit34_neighborhood.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit34.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit35_post.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit35.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit36_cooking.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit36.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit37_personality.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit37.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit38_colors.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit38.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit39_seasons.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit39.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a1_unit40_emergencies.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a1_unit40.yaml",
    ),
)

# A2 units live in a SEPARATE course row ("Dari A2", not "Dari A1") --
# `POST /admin/content/import` matches/creates courses by
# (source_language, target_language, title), and every en-prs A2
# overlay declares `course.title: Dari A2`, distinct from A1's `Dari
# A1`. Real bug found live 2026-07-06/07 (Dari Endless Practice QA
# pass): this used to be a single UNIT_FILES tuple with a2 units 09-10
# appended at continuous positions 9/10, backfilled against ONE lookup
# of the "Dari A1" course only. Since the real A1 realization has since
# grown to 12 units, position 9/10 silently resolved to Dari A1's OWN
# real unit09/unit10 lessons instead of erroring -- every A2 lexeme got
# created with the correct token/gloss/tags but the WRONG
# `provenance_lesson_id` (pointing at unrelated A1 lesson content
# instead of the real A2 bureaucracy/opinions lessons, which live in
# the separate "Dari A2" course and got zero lexemes of their own).
# Kept as its own tuple with LOCAL 1-based ordering (looked up against
# the "Dari A2" course separately in main(), never mixed with UNIT_FILES'
# indices) so this can't recur as the A1 unit count keeps growing.
UNIT_FILES_A2 = (
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit09_bureaucracy.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit10_opinions.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit10.yaml",
    ),
    # Units 11-18 (banking, doctor, home maintenance, job interview, travel
    # disruption, online habits, weekly schedule, shopping complaint), added
    # 2026-07-11 -- these 8 A2 units exist on disk and are imported to the
    # DB but were missing from this script entirely, leaving them with zero
    # practice-pool lexeme coverage. Kept in this SAME UNIT_FILES_A2 tuple
    # (not a separate one) since they're all still the "Dari A2" course --
    # only the LOCAL 1-based position within this tuple matters (see the
    # comment above UNIT_FILES_A2's own declaration), and units 09/10
    # already occupy positions 1/2, so 11-18 correctly land at positions
    # 3-10 by simple append, matching the real unit.order values Dari A2's
    # own imported course rows will have.
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit11_banking.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit11.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit12_doctor.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit13_maintenance.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit14_job_interview.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit14.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit15_travel_disruption.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit15.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit16_online_habits.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit16.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit17_weekly_schedule.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit17.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/a2_unit18_shopping_complaint.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/a2_unit18.yaml",
    ),
)

# B1 units 01-06 (abilities, necessity, conditions, sequencing, reported
# speech, purpose), added 2026-07-11 -- these 6 units exist on disk and are
# imported to the DB (their own separate "Dari B1" course, confirmed via
# every b1_unitNN.yaml overlay's `course.title: Dari B1`) but were entirely
# missing from this script, leaving B1 lessons with zero practice-pool
# lexeme coverage. Kept as its OWN tuple with LOCAL 1-based ordering
# (looked up against the "Dari B1" course separately in main(), never
# mixed with UNIT_FILES/UNIT_FILES_A2's indices), same defensive pattern
# UNIT_FILES_A2's own header comment documents and for the identical
# reason: a bare positional index would silently resolve to the wrong
# course's unit/lesson if either course's real unit count ever diverges
# from this tuple's length.
UNIT_FILES_B1 = (
    (
        REPO_ROOT / "docs/content/realizations/prs/b1_unit01_abilities.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/b1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/b1_unit02_necessity.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/b1_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/b1_unit03_conditions.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/b1_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/b1_unit04_sequencing.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/b1_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/b1_unit05_reported_speech.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/b1_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/prs/b1_unit06_purpose.yaml",
        REPO_ROOT / "docs/content/overlays/en-prs/b1_unit06.yaml",
    ),
)

# Hand-classified from every introduced_token across all 6 lessons of
# unit 1 (confirmed by reading the realization file directly, not
# guessed). Persian-range codepoints throughout -- Persian keheh/yeh,
# never the Arabic-range look-alikes (described in prose only).
PRS_GLOSSES: dict[str, str] = {
    "ا": "a (letter)", "ب": "b (letter)", "ت": "t (letter)", "د": "d (letter)",
    "ر": "r (letter)", "ز": "z (letter)", "س": "s (letter)", "ش": "sh (letter)",
    "ص": "s, emphatic (letter)", "ج": "j (letter)", "چ": "ch (letter)",
    "ح": "h, emphatic (letter)", "خ": "kh (letter)", "ع": "a/e, glottal (letter)",
    "غ": "gh (letter)", "ف": "f (letter)", "ق": "q (letter)", "ک": "k (letter)",
    "گ": "g (letter)", "ل": "l (letter)", "م": "m (letter)", "ن": "n (letter)",
    "و": "v/o/u (letter)", "ه": "h (letter)", "ی": "y / long i (letter)",
    "سلام": "hello", "علیکم": "upon you (greeting particle)",
    "وعلیکم": "and upon you", "خوش": "pleasant; happy", "آمدین": "you came (polite)",
    "تشکر": "thanks", "خواهش": "request; kindness", "می‌کنم": "I do",
    "خدا": "God", "حافظ": "protector", "صبح": "morning", "بخیر": "well; good",
    "روز": "day", "عصر": "afternoon/evening", "شب": "night", "به": "to",
    "امید": "hope", "دیدار": "meeting", "شما": "you (polite)", "چطور": "how",
    "استین": "you are (polite)", "تو": "you (informal)", "استی": "you are (informal)",
    "خوب": "good", "استم": "I am", "جور": "well; fine", "بد": "bad",
    "نیستم": "I am not", "و": "and", "همه": "everyone; all", "استند": "they are",
    "فامیل‌تان": "your family", "است": "is", "اهل": "from; originally of",
    "خانه": "house", "شکر": "thank God; thanks", "زنده": "alive; long (may you live)",
    "باشین": "may you be / (if) you be (subjunctive, polite)", "خانهٔ": "house of", "خودتان": "yourself",
    "بالا": "up; upstairs", "بفرمایین": "please, go ahead / come in (polite)", "اول": "first",
    "بزرگ‌ترها": "elders", "می‌کنیم": "we do", "دفتر": "office", "کابل": "Kabul",
    "حامد": "Hamed (name)", "من": "I", "همکار": "colleague", "نو": "new",
    "نجیب": "Najib (name)", "آمدین": "you came (polite)",
    "نام‌تان": "your name", "چیست": "what is", "نام": "name", "از": "from",
    "آشنایی": "acquaintance", "با": "with", "شدم": "I became", "هم": "also",
    "همکاران": "colleagues", "را": "(object marker)", "معرفی": "introduction",
    "بسیار": "very", "این": "this", "میز": "desk; table",
    # Unit 2 (introductions: name exchange, origin, occupation,
    # introducing a third person, polite titles, gathering dialogue),
    # added 2026-07-05 by the practice-pool-sync lane. Confirmed by
    # reading docs/content/realizations/prs/a1_unit02_introductions.yaml
    # directly -- every token below is a genuinely new introduced_token
    # not already covered by unit 1's dict above (checked against the
    # full unit-1 key set first to avoid silently overwriting an
    # existing, already-reviewed gloss).
    "بدهین": "give (polite imperative)",
    "اجازه": "permission", "همکارم": "my colleague",
    "فریدون": "Faridun (name)", "نامت": "your name (informal)",
    "هرات": "Herat (city)", "مزار": "Mazar (part of Mazar-i-Sharif)",
    "شریف": "Sharif (part of Mazar-i-Sharif)", "افغانستان": "Afghanistan",
    "شهر": "city", "کار": "work; job", "داکتر": "doctor",
    "معلم": "teacher", "مهندس": "engineer", "دوکاندار": "shopkeeper",
    "آرزو": "Arezoo (name)", "دوست": "friend", "جناب": "Mr.; sir",
    "خانم": "Ms.; Mrs.", "نزدیک": "close; near",
    "می‌تانین": "you can (polite)", "دوباره": "again",
    "بگویین": "say (polite imperative)", "مهمانی": "party; gathering",
    "لیلا": "Leila (name)", "دیدن": "seeing; to see",
    "خوشحال": "happy; glad", "کجا": "where",
    "کنم": "let me do; I do (subjunctive)",
    # Unit 3 (family and relatives), added 2026-07-06 by the
    # practice-pool-sync lane.
    "مادر": "mother", "پدر": "father", "برادر": "brother", "خواهر": "sister",
    "و": "and", "این": "this", "من": "I", "او": "he / she",
    "مادرم": "my mother", "برادرم": "my brother", "خواهرم": "my sister",
    "است": "is", "پدرکلان": "grandfather", "مادرکلان": "grandmother",
    "کاکا": "paternal uncle", "عمه": "paternal aunt", "ماما": "maternal uncle",
    "خاله": "maternal aunt", "کاکایم": "my paternal uncle",
    "عمه‌ام": "my paternal aunt", "پدری": "paternal (side)",
    "پدرم": "my father", "مامایم": "my maternal uncle",
    "مادری": "maternal (side)", "فامیل": "family",
    "فامیل‌تان": "your family (polite)", "چند": "how many", "نفر": "people (counter)",
    "ما": "we", "چهار": "four", "پنج": "five", "شش": "six", "یک": "one",
    "دو": "two", "دارم": "I have", "تک‌فرزند": "only child", "استم": "I am",
    "داریم": "we have", "دارین": "you have (polite)",
    "مادر‌تان": "your mother (polite)", "جور": "well; fine",
    "استند": "they are", "بلی": "yes", "نخیر": "no", "ندارم": "I do not have",
    "پدر‌تان": "your father (polite)", "متأهل": "married", "مجرد": "single",
    "شوهر": "husband", "شوهرم": "my husband", "خانم": "Ms.; Mrs.; wife",
    "ازدواج": "marriage", "کردین": "you did (polite)", "اولاد": "children",
    "محصل": "university student", "فرشته": "Fereshteh (name)",
    "دارد": "he/she has", "هنوز": "yet; still", "نداریم": "we do not have",
    "ندارد": "he/she does not have",
    # Unit 4 (counting and numbers), added 2026-07-06.
    "سه": "three", "هفت": "seven", "هشت": "eight", "نه": "nine", "ده": "ten",
    "یازده": "eleven", "دوازده": "twelve", "سیزده": "thirteen",
    "چهارده": "fourteen", "پانزده": "fifteen", "شانزده": "sixteen",
    "هفده": "seventeen", "هجده": "eighteen", "نوزده": "nineteen",
    "بیست": "twenty", "سی": "thirty", "چهل": "forty", "پنجاه": "fifty",
    "شصت": "sixty", "هفتاد": "seventy", "هشتاد": "eighty", "نود": "ninety",
    "صد": "one hundred", "سال": "year", "ساله": "years old",
    "استین": "you are (polite)", "استی": "you are (informal)",
    "نمبر": "number", "تلفن": "telephone", "تلفن‌تان": "your telephone (polite)",
    "صفر": "zero", "تلفنم": "my telephone", "سلام": "hello",
    "همایون": "Homayoun (name)", "تشکر": "thanks", "تو": "you (informal)",
    "بشیر": "Bashir (name)", "تلفنت": "your telephone (informal)",
    "همین": "this very; right (now)", "حالا": "now",
    "سیف": "save (loanword, in سیف می‌کنم)", "می‌کنم": "I do",
    # Unit 5 (important places in the city), added 2026-07-06.
    "بازار": "market", "بانک": "bank", "مسجد": "mosque",
    "شفاخانه": "hospital", "مکتب": "school", "دواخانه": "pharmacy",
    "پوسته": "post (mail)", "خانه": "house", "سفارت": "embassy",
    "میدان": "field / square", "هوایی": "aerial",
    "کجاست": "where is (it)?", "ببخشین": "excuse me", "دور": "far",
    "این‌جا": "here", "آن‌جا": "there", "در": "at (preposition)",
    "کنار": "side; beside", "پشت": "behind", "مقابل": "opposite",
    "زیاد": "much; a lot", "نیست": "is not", "مستقیم": "straight",
    "بروین": "go (polite imperative)", "بعد": "after; then",
    "رهگذر": "passerby", "زرمینه": "Zarmina (name)",
    "قابلی": "worth (in \"don't mention it\")", "نداره": "doesn't have (spoken)",
    # Unit 6 (giving directions and finding your way), added 2026-07-06.
    "چپ": "left", "راست": "right", "بپیچین": "turn (polite imperative)",
    "به": "to / toward", "بروم": "I go (subjunctive)",
    "فهمیدم": "I understood", "از": "from", "روبه‌رو": "opposite / across",
    "روبه‌روی": "across from (construct form)", "شماست": "is yours (polite)",
    "بسیار": "very", "خوب": "good", "سهیلا": "Sohaila (name)",
    "دکاندار": "shopkeeper", "سفر": "trip; journey", "خوش": "happy; pleasant",
    # Unit 7 (talking on the phone), added 2026-07-06.
    "الو": "hello (on the phone)", "کی": "who", "صحبت": "talk; speech",
    "می‌کند": "does / is doing", "فرید": "Farid (name)", "لطفاً": "please",
    "آهسته": "slowly", "کنین": "do (polite imperative)", "پیام": "message",
    "می‌خواهم": "I want", "بگذارم": "let me leave / put",
    "زنگ": "call; ring (noun)", "می‌زنم": "I make (a call)",
    "کوتاه": "short", "فردا": "tomorrow", "جلسه": "meeting",
    "ساعت": "hour; o'clock", "می‌رسانم": "I'll pass it along / deliver",
    "لیمه": "Lima (name)", "برای": "for", "می‌نویسم": "I am writing",
    "گذاشت": "left (past tense, put / leave)",
    # Unit 8 (food and ordering a meal), added 2026-07-06.
    "نان": "bread", "پلو": "rice pilaf", "قورمه": "meat and vegetable stew",
    "چای": "tea", "آب": "water", "چی": "what", "تازه": "fresh", "بشقاب": "plate",
    "تا": "counter word (pieces)", "بل": "the bill",
    "می‌شه": "becomes / comes to (amount)", "خیلی": "very",
    "خوش‌مزه": "delicious", "بود": "was", "چایخانه": "teahouse",
    "آمدین": "you came (polite)", "میل": "desire / preference",
    "مشتری": "customer", "هردو": "both", "با": "with",
    "چشم": "of course (lit. eye, polite acknowledgment)",
    "می‌آرم": "I'll bring", "دوصد": "two hundred", "افغانی": "Afghani (currency)",
    # A2 unit 09 (administrative errands), added 2026-07-06.
    "وقت": "appointment / time", "سند": "document", "آدرس": "address",
    "تذکره": "national ID booklet", "شاروالی": "municipality",
    "می‌خواستم": "I wanted (polite request)", "تغییر": "change",
    "بگیرم": "let me take", "چون": "because", "خانه‌ام": "my house",
    "را": "(object marker)", "عوض": "change (noun/verb stem)",
    "کردم": "I did", "باید": "must", "آدرسم": "my address",
    "می‌شود": "would it be possible; is it okay", "چه": "what",
    "چیزی": "something / what thing", "بیاورم": "should I bring",
    "رسید": "receipt", "کرایه": "rent", "مهلت": "deadline",
    "بیارین": "bring (polite imperative)", "ثبت": "registration",
    "آخر": "end", "ماه": "month", "می‌آورم": "I bring",
    "خدمتی": "service", "می‌توانم": "I can / may I",
    "برایتان": "for you (polite)", "انجام": "performance; carrying out",
    "بدهم": "let me give / do", "کارمند": "clerk; employee",
    "کریم": "Karim (name)", "خانهٔ": "house of (construct form)",
    "جدید": "new", "زندگی": "life; living", "می‌کنین": "you do",
    "گذشته": "past; last", "کافی": "enough", "روز": "day",
    "سه‌شنبه": "Tuesday", "بیایم": "may I come", "پیگیری‌تان": "your tracking (number)",
    "هزار": "thousand",
    # A2 unit 10 (sharing opinions), added 2026-07-06.
    "نظر": "opinion", "دلیل": "reason", "تحصیل": "study; education",
    "خارج": "abroad", "وطن": "homeland", "بهتر": "better",
    "پوهنتون‌های": "universities", "فرصت": "opportunity", "بیشتر": "more",
    "تجربهٔ": "experience of (construct form)", "کسب": "gaining; acquiring",
    "فکر": "thought; think", "نمی‌کنم": "I don't (do)",
    "پروین": "Parwin (name)", "احمد": "Ahmad (name)", "چرا": "why",
    "فامیلم": "my family", "بمانم": "let me stay", "وطنم": "my homeland",
    "کمک": "help", "درست": "correct; true", "ولی": "but", "شاید": "maybe",
    "همین‌جا": "right here", "می‌مانم": "I stay",
    # Unit 9 (days and dates), added 2026-07-07. Confirmed by reading
    # docs/content/realizations/prs/a1_unit09_dates.yaml directly --
    # "بشیر" was already glossed under unit4 (reused as-is, only its
    # semantic tag needs extending below); every other token here is
    # genuinely new.
    "شنبه": "Saturday", "یکشنبه": "Sunday", "دوشنبه": "Monday",
    "چهارشنبه": "Wednesday", "پنجشنبه": "Thursday", "جمعه": "Friday",
    "تاریخ": "date", "رخصتی": "day off / holiday", "هفته": "week",
    "حمل": "Hamal (1st Hijri Shamsi month)",
    "ثور": "Sawr (2nd Hijri Shamsi month)",
    "جوزا": "Jawza (3rd Hijri Shamsi month)", "تقویم": "calendar",
    "هجری": "Hijri", "شمسی": "solar (calendar)", "استفاده": "use",
    "امروز": "today", "پانزدهم": "15th", "کدام": "which",
    "چندم": "what number / which day (of the month)", "نوزدهم": "19th",
    "مصروف": "busy", "می‌بینمت": "I'll see you",
    "داری": "you have (informal)", "مشکل": "problem",
    # Unit 10 (shopping and prices), added 2026-07-07. Confirmed by
    # reading docs/content/realizations/prs/a1_unit10_shopping.yaml
    # directly. HISTORY NOTE (2026-07-07 Dari 2pl fix): unit01/02/07
    # originally used Iranian -ید spellings (بفرمایید/می‌توانید/بدهید)
    # as separate lexemes from unit10's Afghan -ین forms; the corpus-
    # wide -ید -> -ین conversion (see BUILD_LOG) merged each pair into
    # the single correct Afghan form. The duplicate dict entries below
    # are therefore intentional last-wins repeats of the same token,
    # matching this file's per-unit-section layout convention.
    "دوکان": "shop", "قیمت": "price", "ارزان": "cheap", "گران": "expensive",
    "تخفیف": "discount", "قیمتش": "its price", "سیب": "apple(s)",
    "کیلو": "kilo", "می‌تانین": "you can (polite)",
    "بدهین": "give (polite imperative)",
    "بفرمایین": "please, go ahead / come in (polite)",
    "سیب‌ها": "the apples",
    # Unit 11 (time), added 2026-07-07. Confirmed by reading
    # docs/content/realizations/prs/a1_unit11_time.yaml directly --
    # "ساعت"/"نه"/"صبح"/"عصر"/"شب"/"هفت"/"هشت"/"چند"/"شما"/"من"/"است"
    # were all already glossed from earlier units, reused as-is.
    "دقیقه": "minute", "نیم": "half", "ربع": "quarter", "ظهر": "noon",
    "قرار": "appointment", "می‌آیم": "I'm coming / I come",
    "منتظر": "waiting",
    # Unit 12 (daily routines), added 2026-07-07. Confirmed by reading
    # docs/content/realizations/prs/a1_unit12_routines.yaml directly --
    # هفت/ده/شش/ساعت/صبح/ظهر/عصر/شب/هر/من/و/تو/بلی/چند/همایون were all
    # already glossed from earlier units, reused as-is. زرمینه was already
    # glossed (unit05, as a passerby character) but never given the
    # person_name semantic tag until this unit's own dialogue -- fixed
    # below alongside this unit's own additions.
    "خواب": "sleep (noun)", "بیدار": "awake",
    "می‌شوم": "I become / I wake up", "صبحانه": "breakfast",
    "می‌خورم": "I eat", "می‌روم": "I go", "می‌خوابم": "I sleep",
    "می‌شوی": "you wake up (informal)", "هر": "every", "زود": "early",
    "چطور؟": "how? (turning a question back, as in 'what about you?')",
    # می‌شود ALREADY EXISTS in this dict (A2 unit09: "would it be
    # possible; is it okay") -- a genuine homograph, not the same
    # lexeme: this unit's usage is the third-person indicative of
    # "to become/wake up" (بیدار می‌شود, he/she wakes up), completely
    # unrelated to unit09's polite-request sense. Same collision class
    # already solved for "و" (letter vs. conjunction) below in
    # _classify() -- given its own special-cased key/gloss/POS there
    # instead of overwriting the shared bare-token entry.
    # Unit 13 (making plans), added 2026-07-07. Confirmed by reading
    # docs/content/realizations/prs/a1_unit13_plans.yaml directly --
    # چطور/است/خوب/استم/کار/دارم/ساعت/پنج/بعد/از/ظهر/سلام/شما/را/فرید/چه
    # were all already glossed from earlier units (جمعه/کدام/منتظر too,
    # from the parallel session's units 09/11), reused as-is.
    "پلان": "plan", "پارک": "park", "برویم": "let's go (subjunctive, we)",
    "است؟": "is (it)? (question form of 'to be')",
    "می‌خواهین": "do you want (polite)", "عالی": "great; excellent",
    "قبول": "accepted; agreed", "متأسف": "sorry",
    "نمی‌توانم": "I can't", "دعوت": "invitation",
    "می‌بینم": "I see / I'll see", "نگار": "Negar (name)",
    # Unit 14 (preferences), added 2026-07-07. Confirmed by reading
    # docs/content/realizations/prs/a1_unit14_preferences.yaml directly --
    # دوست/دارم/چای/ندارم/من/را/بیشتر/چون/خوش‌مزه/است/و/دارد/ندارد/شما/
    # چطور/کریم were all already glossed from earlier units, reused as-is
    # (their literal "have"/"friend" glosses stand; the idiomatic "like"
    # meaning comes from the دوست دارم construction as a whole, not from
    # any single re-glossed token).
    # (کدام "which" already exists in this dict from the parallel
    # session's unit09 -- reused as-is, not re-added here.)
    "قهوه": "coffee", "موسیقی": "music",
    "دارین": "you have (polite)", "یا": "or", "جالب": "interesting",
    "گرم": "warm",
    # Unit 15 (comparisons), added 2026-07-07. Confirmed by reading
    # docs/content/realizations/prs/a1_unit15_comparisons.yaml directly --
    # این/است/از/چون/و/بلی/بهتر/کریم/نگار were all already glossed from
    # earlier units, reused as-is. ارزان/گران (base adjectives, unit10)
    # are distinct tokens from this unit's own ارزان‌تر/گران‌تر comparative
    # forms below -- not a collision, genuinely different strings.
    "آن": "that", "بزرگ‌تر": "bigger", "کوچک‌تر": "smaller",
    "گران‌تر": "more expensive", "ارزان‌تر": "cheaper", "قد": "height",
    "بلندتر": "taller / longer", "جوان‌تر": "younger", "بدتر": "worse",
    "اما": "but",
    # Unit 16 (travel), added 2026-07-07. Confirmed by reading
    # docs/content/realizations/prs/a1_unit16_travel.yaml directly --
    # هرات/یک/از/دو/به/می‌خواهم/صبح/ساعت/هشت/فردا/بسیار/خوب/تشکر/زیاد/
    # قابلی/نداره/سفر/خوش/و were all already glossed from earlier units,
    # reused as-is. "کی" (already glossed "who" from unit07) is a genuine
    # homograph here -- this unit's own sense ("when") is special-cased
    # in _classify() below rather than overwriting the existing entry.
    "بلیط": "ticket", "قطار": "train", "بس": "bus", "سکو": "platform",
    "سکوی": "platform (ezafe form of سکو, used before a following noun)",
    "حرکت": "departure; movement",
    "مسافر": "traveler; passenger", "فروشنده": "seller; vendor",
    # Unit 17 (health), added 2026-07-07. Confirmed by reading
    # docs/content/realizations/prs/a1_unit17_health.yaml directly --
    # دارم/استم/خوب/نیست/داکتر/می‌خواهم/کنین/آب/زیاد/سلام/و/تشکر/چطور/
    # استین were all already glossed from earlier units, reused as-is.
    # "بشیر" (already glossed "Bashir (name)" from unit04) gets its
    # person_name tag extended below -- a real pre-existing gap, same
    # class as زرمینه/کریم.
    "سردرد": "headache", "تب": "fever", "دل‌درد": "stomachache",
    "مریض": "sick; ill", "حالم": "my condition / how I feel (حال + م)",
    "دوا": "medicine", "استراحت": "rest",
    "بنوشین": "drink (polite imperative)",
    "صاحب": "sir (respectful honorific, appended after a title)",
    # Unit 18 (work), added 2026-07-07. Confirmed by reading
    # docs/content/realizations/prs/a1_unit18_work.yaml directly --
    # معلم/مهندس/داکتر/دوکاندار/کار/استم/دفتر/دوکان/شفاخانه/مکتب/در/
    # می‌کنم/کجا/می‌کنین/و/است/هر/روز/بشیر/شما/چیست/بلی were all already
    # glossed from earlier units, reused as-is. لیلا (already "Leila
    # (name)" from unit02) and می‌کند (already "does / is doing" from
    # unit07) are also reused as-is -- genuinely the same lexemes, not
    # collisions. درس/می‌دهد are the only genuinely new tokens.
    "درس": "lesson", "می‌دهد": "he/she gives (درس می‌دهد, 'teaches')",
    # Unit 19 (housing), added 2026-07-07, same pass as unit18 above.
    # Confirmed by reading
    # docs/content/realizations/prs/a1_unit19_housing.yaml directly --
    # خانه/دارم/دو/سه/نزدیک/است/این/دارد/یک/و/مقابل/شما/چند/بلی/لیلا/
    # فریدون were all already glossed from earlier units, reused as-is.
    "اتاق": "room", "آشپزخانه": "kitchen", "تشناب": "bathroom",
    "چوکی": "chair", "تخت": "bed", "کلکین": "window", "بزرگ": "big",
    # Unit 20 (past events), added 2026-07-09 (practice-pool depth-
    # extension pass, units 20-24). شدم ("I became") and کردم ("I did")
    # are REUSED existing lexemes (unit02 and A2 unit09 respectively,
    # genuinely the same words) -- not re-added here.
    "دیروز": "yesterday", "رفتم": "I went", "خوردم": "I ate",
    "خسته": "tired", "رفتی": "you went", "کردی": "you did / you worked",
    "رفت": "she/he went", "کرد": "she/he did / worked", "شد": "she/he became",
    # Unit 21 (clothing), added 2026-07-09. کنم/دارد/بود/رفت are REUSED
    # existing lexemes, not re-added here.
    "لباس": "clothes", "پیراهن": "shirt", "پطلون": "trousers",
    "کفش": "shoes", "رنگ": "color", "سیاه": "black", "سفید": "white",
    "سرخ": "red", "اندازه": "size", "کوچک": "small",
    "می‌تانم": "I can", "این‌را": "this (object marker)",
    "پرو": "try-on", "پرو کنین": "try it on (polite imperative)",
    "پنجصد": "five hundred", "اندازه‌اش": "its size",
    "می‌خرم": "I buy", "خرید": "bought",
    # Unit 22 (weather), added 2026-07-09. چطور/گرم/یا/فردا/می‌شود/پارک/
    # بهتر/برویم/اما are REUSED existing lexemes, not re-added here.
    # می‌شود gets a THIRD homograph sense here (weather "will become"),
    # special-cased in _classify() below -- same collision class as the
    # existing A2-unit09/unit12 split.
    "هوا": "weather", "آفتابی": "sunny", "ابری": "cloudy",
    "باران": "rain", "برف": "snow", "می‌بارد": "is falling (rain/snow)",
    "سرد": "cold", "بمانیم": "let's stay / we stay (subjunctive)",
    "پس": "so / then", "می‌مانیم": "we stay", "نمی‌توانیم": "we can't",
    "فلم": "film", "می‌بینیم": "we watch / we see", "می‌مانند": "they stay",
    # Unit 23 (money), added 2026-07-09. دارم/صد/می‌تانم/افغانی/است/
    # امروز/چند/به/را/می‌کنم/می‌خواهم/دارین/بفرمایین/هزار/زرمینه/بسیار/
    # هفتاد/تشکر/کرد/رفت/برای are REUSED existing lexemes.
    "پول": "money", "نقد": "cash", "کارت": "card", "دالر": "dollar",
    "می‌پردازم": "I pay", "نقدی": "in cash", "می‌پردازین": "you pay (polite)",
    "کارتی": "by card", "بپردازم": "let me pay / I pay (subjunctive)",
    "صرافی": "money exchanger", "تبدیل": "exchange", "کردن": "to do / to make",
    "نرخ": "exchange rate", "تبدیل کنین": "(please) exchange",
    "می‌گیرم": "I take / I receive", "گرفت": "he/she took / received",
    "گرفتم": "I took / I received",
    # Unit 24 (transportation), added 2026-07-09. بس/می‌روم/با/چطور/
    # می‌خرم/شهر/نزدیک/ارزان/اما/هر/روز/چون/می‌کند/او/نیست/من/یا are
    # REUSED existing lexemes.
    "تکسی": "taxi", "موتر": "car", "دوچرخه": "bicycle", "پیاده": "on foot",
    "می‌روی": "you go", "تکت": "ticket", "ایستگاه": "station",
    "تیز": "fast", "تیزتر": "faster", "خانه‌اش": "his house",
    "پس‌انداز": "savings", "می‌رود": "he/she goes",
    # Unit 25 (emotions), added 2026-07-11. خوشحال/خسته/نگران/چرا/چون/
    # امروز/هوا/خوب/است/کار/زیاد/کردم/خراب/دارم/من/تو/هم/کمی/بعد/از/او/
    # اما/استم/استین/استی/دارد are REUSED existing lexemes.
    "ناراحت": "sad", "عصبانی": "angry", "گاهی": "sometimes",
    # Unit 26 (hobbies), added 2026-07-11. کتاب/موسیقی/کردن/فلم/دیدن/
    # آشپزی/آزاد/وقت/چی/در/را/دوست/دارم/دارین/هر/روز/هفته/آخر/می‌کنم/من/
    # تو/می‌کنی/هم/و/می‌کند/دارد/او/اما/گاهی are REUSED existing lexemes.
    "سرگرمی": "hobby", "خواندن": "reading / to read",
    "گوش": "listening (as in gosh kardan, to listen)",
    "پیاده‌روی": "walking",
    # Unit 27 (appearance), added 2026-07-11. قد/کوتاه/است/دارد/او/چطور/
    # خوب/سیاه/رنگ/برادر/بلی/تشکر/هم/زرمینه/و/کریم/ندارد/اما/استم/دارم/
    # من are REUSED existing lexemes. چشم is a genuine homograph against
    # the existing polite particle sense ("of course") -- split by
    # content_key in _classify() below, same collision class as و/می‌شود.
    "بلند": "tall; high", "مو": "hair", "موی": "hair (linked form)",
    "ریش": "beard", "عینک": "glasses", "قیافه": "appearance / looks",
    "قیافه‌اش": "his/her appearance", "آبی": "blue", "قهوه‌ای": "brown",
    "برادرت": "your brother (informal)",
    # Unit 28 (animals), added 2026-07-11. دارم/دارین/است/من/یک/بلی/
    # نخیر/ندارم/رنگ/سیاه/سفید/کوچک/بزرگ/و/تو/داری/چه/هر/روز/زرمینه/به/
    # او/غذا/دارد/می‌دهد/اما/استم are REUSED existing lexemes.
    "حیوان": "animal", "سگ": "dog", "پشک": "cat", "پرنده": "bird",
    "ماهی": "fish", "خانگی": "domestic; household (as in pet)",
    "می‌دهی": "you give (informal)", "می‌دهم": "I give",
    # Unit 29 (sports), added 2026-07-11. ورزش/بازی/کردن/می‌کنم/یک/است/
    # خوب/هم/چند/بار/در/هفته/می‌کنین/من/دو/پارک/بزرگ/تو/می‌کنی/کجا/
    # می‌کند/زرمینه/هر/عالی/او/همایون/اما/دوست/دارم/را/وقت/ندارم are
    # REUSED existing lexemes.
    "فوتبال": "football", "والیبال": "volleyball", "کرکت": "cricket",
    "شنا": "swimming", "محبوب": "popular", "باشگاه": "gym",
    # Unit 30 (technology), added 2026-07-11. کمپیوتر/انترنت/من/دارم/در/
    # دفتر/است/آهسته/این/خوب/استفاده/کردن/می‌کنم/از/پیام/می‌فرستم/زنگ/
    # می‌زنم/می‌گیرم/دانلود/می‌خواهم/یک/کنم/چند/بار/روز/می‌کنین/هر/
    # می‌کند/تو/می‌کنی/کجا/زرمینه/زیاد/و/بلی/عالی/او/می‌گیرد/همایون/اما/
    # دوست/را/وقت/ندارم are REUSED existing lexemes.
    "تکنالوژی": "technology", "موبایل": "mobile phone",
    "اپلیکیشن": "app", "عکس": "photo", "می‌فرستد": "he/she sends",
    # A2 unit 11 (banking), added 2026-07-11. Confirmed by reading
    # docs/content/realizations/prs/a2_unit11_banking.yaml directly --
    # بانک/کارت/تذکره/باشین/کنین/کردن/و/می‌خواستم/یک/کنم/رسید/کرایه/خانه/
    # تا/سه/روز/می‌شود/برای/بیارین/پنجصد/افغانی/است/نیست/بفرمایین/چه/
    # خدمتی/می‌توانم/برایتان/انجام/بدهم/کارمند/همایون/دارین/بلی/خانه‌ام/
    # خوب/را/کی/می‌گیرم/تشکر/از were all already glossed from earlier
    # units, reused as-is.
    "حساب": "account", "بانکی": "banking (adjective)", "رمز": "PIN code",
    "موجودی": "balance (account)", "امضا": "signature", "اگر": "if",
    "داشته": "having (perfect participle stem)",
    "می‌توانین": "you can (polite)", "باز": "open",
    "بانکی‌تان": "your bank (possessive, polite)", "دیگر": "more; another",
    "آماده": "ready", "کارمزد": "fee", "حداقل": "minimum",
    "ماهانه": "monthly", "اینه": "here it is (colloquial)",
    "تذکره‌ام": "my ID booklet", "رمزش": "its PIN",
    "همان": "that very; the same", "روزی": "the day (indefinite/construct)",
    "که": "that (relative pronoun)",
    "تحویل": "handover; receipt of delivery",
    "می‌گیرین": "you take/receive (polite)", "وقت‌تان": "your time (polite)",
    # A2 unit 12 (doctor visit), added 2026-07-11. Confirmed by reading
    # docs/content/realizations/prs/a2_unit12_doctor.yaml directly --
    # از/دو/روز/خیلی/است/و/باید/بدهم/این/دوا/را/داکتر/شما/چهارشنبه/ساعت/
    # نه/صبح/لطفاً/تذکره/بیارین/اگر/یک/زنگ/سلام/بشیر/چطور/استین/چه/مشکل/
    # دارین/صاحب/کی/تب/هم/بلی/دارم/بهتر/دوباره/تشکر were all already
    # glossed from earlier units, reused as-is.
    "علامت": "symptom", "مدت": "duration", "شدید": "severe",
    "آزمایش": "medical test", "نسخه": "prescription",
    "تجویز": "to prescribe", "پیش": "ago; before", "سردردم": "my headache",
    "شروع": "start; beginning",
    "شده": "has become / has happened (past participle auxiliary)",
    "آیا": "(question particle)", "بار": "time(s) (counter, occurrence)",
    "بخورم": "let me take/eat (subjunctive)", "تاییدی": "confirmation",
    "معاینه": "checkup; examination", "نوبت": "appointment (turn)",
    "نتوانین": "you cannot (polite)", "بیایین": "come (polite imperative)",
    "بزنین": "make/do (polite imperative, e.g. of a phone call)",
    "یک‌کمی": "a little bit",
    "بخورین": "take/drink/eat (polite imperative)",
    "نشدین": "you don't get well/become (polite negative)",
    # A2 unit 13 (home maintenance), added 2026-07-11. Confirmed by
    # reading docs/content/realizations/prs/a2_unit13_maintenance.yaml
    # directly -- هر/چه/می‌کند/و/باید/کی/می‌توانین/اتاق/کار/روز/ساعت/ده/
    # است/اما/دارد/الو/بفرمایین/سلام/من/کریم/استم/از/شروع/شده/فردا/نه/را/
    # تشکر/هم/آن/به were all already glossed from earlier units, reused
    # as-is.
    "خرابی": "malfunction; breakdown", "لوله": "pipe", "برق": "electricity",
    "چکه": "leak", "تعمیر": "repair", "کارگر": "worker; repairman",
    "زودتر": "sooner; more quickly", "آشپزخانه‌ام": "my kitchen",
    "شود": "becomes / gets done (bare subjunctive)",
    "بفرستین": "send (polite imperative)", "خوابم": "my sleep (in 'اتاق خوابم', my bedroom)",
    "نمی‌کند": "does not work / is not working", "هزینه": "cost",
    "رایگان": "free (no cost)", "تعمیرات": "repairs (plural)",
    "پنج‌شنبه": "Thursday", "می‌آید": "comes / is coming",
    "صاحب خانه": "landlord", "دیشب": "last night", "باشه": "okay (colloquial)",
    "می‌فرستم": "I send", "می‌گویم": "I say / I tell",
    # A2 unit 14 (job interview), added 2026-07-11. Confirmed by reading
    # docs/content/realizations/prs/a2_unit14_job_interview.yaml directly
    # -- چند/سال/دارین/من/سه/در/این/دارم/از/می‌توانم/شروع/کنم/است/برای/
    # حداقل/دو/و/افغانی/ماه/لطفاً/تجربهٔ/بگویین/لیمه/شما/چیست/کی/
    # می‌توانین/کنین were all already glossed from earlier units, reused
    # as-is.
    "تجربه": "experience", "مهارت": "skill", "حقوق": "salary",
    "وظیفه": "position; duty; job", "رزومه": "resume; CV",
    "مصاحبه": "interview", "هفتهٔ": "week of (construct form)",
    "آینده": "next; coming; future", "چقدر": "how much",
    "بست": "job vacancy; position (Afghan bureaucratic term)",
    "شرایط": "requirements; conditions", "لازم": "necessary; required",
    "کمپیوتر": "computer", "زبان": "language", "انگلیسی": "English",
    "سی‌هزار": "thirty thousand", "خوش آمدین": "welcome (polite)",
    "خود": "self; own", "مصاحبه‌کننده": "interviewer",
    "مهارت‌های": "skills (of) (plural, construct form)",
    # A2 unit 15 (travel disruption), added 2026-07-11. Confirmed by
    # reading docs/content/realizations/prs/a2_unit15_travel_disruption.
    # yaml directly -- به/دلیل/شده/است/باید/تا/فردا/صبح/کنین/و/من/هم/کنم/
    # بس/کی/حرکت/می‌کند/دارد/ساعت/هشت/ایستگاه/امروز/نه/مزار/شریف/کابل/
    # بفرمایین/چه/می‌توانم/برایتان/همایون/آن/نخیر/چند/تشکر/از were all
    # already glossed from earlier units, reused as-is.
    "تاخیر": "delay", "لغو": "cancellation", "بسته": "closed",
    "راه": "road; way", "مسیر": "route", "بدیل": "alternative",
    "برفباری": "snowfall", "اطلاعیه": "notice; announcement",
    "صبر": "patience; waiting", "بعدی": "next", "وجود": "existence",
    "مسافران": "passengers", "کمکی": "some help",
    "بکنم": "let me do / may I do (subjunctive)",
    "کارمند ایستگاه": "station clerk", "متأسفم": "I'm sorry",
    "معلومات‌تان": "your information",
    # A2 unit 16 (online habits), added 2026-07-11. Confirmed by reading
    # docs/content/realizations/prs/a2_unit16_online_habits.yaml directly
    # -- کردن/وقت/من/در/را/می‌بینم/زیاد/و/هر/روز/تو/چقدر/به/نظر/است/ولی/
    # باید/خود/بیشتر/از/چند/ساعت/استفاده/تا/برای/زرمینه/همایون/یک/چطور/
    # شاید/دو/این/آن/درست/فردا/عالی were all already glossed from earlier
    # units, reused as-is.
    "شبکهٔ": "network of (construct form)", "اجتماعی": "social",
    "ویدیو": "video", "دانلود": "download", "پیام‌رسان": "messaging app",
    "بازی": "game", "کمپیوتری": "computer (adjective)",
    "آزاد": "free (available time)", "معمولاً": "usually",
    "شبکه‌های": "networks (plural, construct form)", "بعضی": "some",
    "اوقات": "times (plural of وقت)", "می‌گیرد": "takes (third person)",
    "می‌گذرانی": "you spend (time) (informal)", "انترنت": "internet",
    "مفید": "useful", "محدود": "limited", "کنیم": "let's do / we do (subjunctive)",
    "کاربر": "user", "بسیاری": "many (of)", "مردم": "people",
    "روزانه": "daily", "می‌کنند": "they do", "افراد": "individuals; people",
    "بیشتری": "more (comparative, indefinite)", "خانواده": "family",
    "دوستان": "friends", "باشند": "they may be (subjunctive)",
    "لذت": "pleasure; enjoyment", "می‌برم": "I take / I carry",
    "کمتر": "less",
    # A2 unit 17 (weekly schedule), added 2026-07-11. Confirmed by
    # reading docs/content/realizations/prs/a2_unit17_weekly_schedule.
    # yaml directly -- هفته/آخر/اول/بعد/در/به/دفتر/می‌روم/می‌کنم/و/هفتهٔ/
    # تو/چطور/است/بیدار/می‌شوم/با/فامیلم/وقت/استراحت/کردن/همایون/صبح/
    # زود/می‌شود/می‌رود/اما/او/می‌کند/زرمینه/چه/کار/من/خانه/می‌آیم/بازار/
    # داری were all already glossed from earlier units, reused as-is.
    "برنامه": "schedule; program", "روزهای": "days of (plural construct)",
    "ورزش": "exercise; sport", "کمی": "a little; a bit",
    "مطالعه": "study; reading", "برنامهٔ": "schedule of (construct form)",
    "دیر": "late", "می‌گذرانم": "I spend (time)", "تفاوت": "difference",
    "می‌کنی": "you do (informal)", "آشپزی": "cooking",
    "دوستانم": "my friends", "خوبی": "good (indefinite form)",
    # A2 unit 18 (shopping complaint), added 2026-07-11. Confirmed by
    # reading docs/content/realizations/prs/a2_unit18_shopping_complaint.
    # yaml directly -- کردن/رسید/آن/را/می‌کنم/گرم/و/این/که/دیروز/است/
    # می‌خواهم/کنم/یا/پس/بگیرم/کدام/مهلت/اگر/شده/هفت/روز/با/کنین/
    # بفرمایین/چه/کمکی/می‌توانم/بکنم/فروشنده/کریم/دارد/بلی/اینه/بدهم/
    # بهتر/تشکر were all already glossed from earlier units, reused
    # as-is.
    "خراب": "broken", "تعویض": "exchange", "بازپرداخت": "refund",
    "گارانتی": "warranty", "عیب": "defect", "وقتی": "when (temporal clause)",
    "روشن": "turned on; lit", "نمی‌شود": "does not become (negative)",
    "بخاری": "heater", "برقی": "electric (adjective)",
    "خریدم": "I bought", "پولم": "my money",
    "ترجیح": "preference", "می‌دهین": "you give (polite)",
    "اصلی": "original", "کالای": "item of; goods of (construct form)",
    "خریداری": "purchase; purchasing",
    "باشد": "may be / is (subjunctive, third person)",
    "می‌توانید": "you can (polite)", "ظرف": "within (a period of time)",
    "مشکلی": "a problem (indefinite)",
    "روشنش": "turning it on / its being turned on",
    "همراه‌تان": "with you (polite)", "رسیدم": "my receipt",
    "پول‌تان": "your money (polite)",
    # B1 unit 01 (abilities: می‌تانم/توانستن paradigm, present + past,
    # errands dialogue, appointment reading), added 2026-07-11. Confirmed
    # by reading docs/content/realizations/prs/b1_unit01_abilities.yaml
    # directly. This is the FIRST B1 unit backfilled by this script --
    # B1 is its own separate course ("Dari B1"), so these are all new
    # (level, token) keys regardless of any bare-string overlap with
    # A1/A2 (see UNIT_FILES_B1's own comment below for why that's safe).
    # می‌تانم/می‌تانین are REUSED existing A1 lexemes (same paradigm,
    # completed here with the missing persons), not re-added.
    "می‌تانی": "you can", "بخرم": "(that) I buy", "ببینم": "(that) I see",
    "بفرستم": "(that) I send", "کتاب": "book", "نامه": "letter",
    "بفرستی": "(that) you send", "می‌تانه": "he/she can",
    "می‌تانیم": "we can", "می‌تانن": "they can",
    "ببره": "(that) he/she take", "بکنین": "(that) you (polite) do",
    "بیایند": "(that) they come", "آنها": "they",
    "می‌تانستم": "I could / I was able to",
    "نتانستم": "I could not / I was not able to",
    "می‌تانستی": "you could / you were able to",
    "پسته خانه": "post office", "نرفت": "didn't go",
    "ببری": "(that) you take", "راستی": "by the way",
    "نداشتم": "I didn't have", "ملاقات": "appointment",
    "برود": "(that) he/she go", "نتانست": "he/she could not",
    "نزد": "near / at (someone's place)", "پارسال": "last year",
    "بگیره": "(that) he/she take", "امسال": "this year",
    # B1 unit 02 (necessity: باید paradigm, present + past + negation,
    # guests dialogue, reading), added 2026-07-11. Confirmed by reading
    # docs/content/realizations/prs/b1_unit02_necessity.yaml directly.
    # باید/نان/کار/کمک/تشکر/مریض/بود/استراحت/خوب/برای/می‌کند/او/هم were
    # all already glossed from earlier A1/A2 units, reused as-is.
    # بخرم (unit01 above) and نداشتم (unit01 above) are REUSED existing
    # B1 lexemes -- same meaning, not re-added.
    "بخری": "(that) you buy", "خودش": "itself",
    "همیشه": "always", "شکل": "form; shape",
    "فعل": "verb (grammar term)", "فاعل": "subject (grammar term)",
    "بخره": "he/she (should) buy", "بخریم": "(that) we buy",
    "بخرین": "(that) you (plural/polite) buy", "بخرن": "(that) they buy",
    "می‌خریدم": "I should have bought / I was supposed to buy",
    "نباید": "must not", "نخریدم": "I didn't buy",
    "مهمان": "guest(s)", "امشب": "tonight", "پاک": "clean",
    "غذا": "food", "بپزم": "(that) I cook", "گوشت": "meat",
    "می‌آیند": "they come / are coming", "نگران": "worried",
    "نباش": "don't be (negative imperative)",
    "می‌کرد": "he/she was doing / used to do",
    "داشت": "had", "حالش": "his/her condition",
    "بپزد": "(that) he/she cook",
    # B1 unit 03 (conditions: اگر paradigm, weather negation, Friday-plan
    # dialogue, park reading), added 2026-07-11. Confirmed by reading
    # docs/content/realizations/prs/b1_unit03_conditions.yaml directly.
    # داشته/باشد/باشند/می‌آیم/پارک/می‌روم/ما/باران/می‌مانیم/در/جمعه/
    # می‌کنی/شاید/آفتابی/چای/می‌مانم/روز/دیگر/دوباره/خوبی/هوا were all
    # already glossed from earlier A1/A2 units, reused as-is. می‌آیند
    # (unit02 above) is a REUSED existing B1 lexeme, not re-added.
    "باشم": "(if) I have", "باشی": "(if) you have",
    "می‌آیی": "you come", "باشیم": "(if) we have",
    "می‌آییم": "we come",
    "ببارد": "it rains (subjunctive)", "نبارد": "it doesn't rain",
    "می‌رویم": "we go", "نمی‌دانم": "I don't know",
    "می‌نوشیم": "we drink", "رفتند": "they went",
    "ماندند": "they stayed", "نوشیدند": "they drank",
    # آنجا is a genuine spelling variant of the already-existing "آن‌جا"
    # (unit05 places, with a ZWNJ between آن and جا) -- this realization
    # writes it WITHOUT the ZWNJ, a different literal string the
    # compiler/grader compares byte-for-byte, so it needs its own entry
    # rather than being silently treated as the same token. Flagged in
    # this pass's report as a genuinely uncertain spelling inconsistency,
    # not something this script should "fix" by rewriting content.
    "آنجا": "there (spelling variant of آن‌جا, no ZWNJ)",
    "می‌روند": "they go",
    # B1 unit 04 (sequencing: وقتی paradigm, present + past time clauses,
    # after-work dialogue, Homayoun's-day reading), added 2026-07-11.
    # Confirmed by reading
    # docs/content/realizations/prs/b1_unit04_sequencing.yaml directly.
    # وقتی/خسته/می‌شوم/می‌شوی/می‌کنیم/می‌کنند/کردی/کمی/می‌خورم/می‌بینم/
    # کرد/شد were all already glossed from earlier A1/A2 units, reused
    # as-is. غذا (unit02 above) and می‌آیی (unit03 above) are REUSED
    # existing B1 lexemes, not re-added. می‌شود/رسید/رسیدم are genuine
    # homographs against existing A1/A2 entries with unrelated meanings
    # (polite-request/receipt/receipt vs. this unit's become/arrive
    # senses) -- special-cased by lesson_key/content_key in _classify()
    # below instead of overwriting the shared dict entries, same
    # collision class as the existing و/کی/می‌شود splits.
    "می‌شویم": "we become",
    "می‌شین": "you (plural/polite) become", "می‌شوند": "they become",
    "پختم": "I cooked", "رسیدی": "you arrived",
    "تلویزیون": "television", "خورد": "he/she ate",
    "تمام": "complete; finished", "آمد": "he/she came",
    # B1 unit 05 (reported speech: گفت که paradigm, reported questions,
    # manager-news dialogue, reading), added 2026-07-11. Confirmed by
    # reading docs/content/realizations/prs/b1_unit05_reported_speech.yaml
    # directly. چیزی/صبح/بیایم/صحبت were all already glossed from earlier
    # A1/A2 units, reused as-is. مهمان (unit02 above) and می‌آیی/می‌آییم
    # (unit03 above) and می‌آیند (unit02 above) are REUSED existing B1
    # lexemes, not re-added.
    "گفتم": "I said", "گفتی": "you said", "گفت": "he/she said",
    "گفتیم": "we said", "گفتید": "you (plural/polite) said",
    "گفتند": "they said", "پرسید": "he/she asked",
    "پرسیدم": "I asked", "مدیر": "manager", "مهم": "important",
    "پرسیدی": "you asked", "شنید": "heard",
    # B1 unit 06 (purpose: تا/برای اینکه paradigm, negative purpose,
    # goals dialogue, reading), added 2026-07-11. Confirmed by reading
    # docs/content/realizations/prs/b1_unit06_purpose.yaml directly.
    # مکتب/انگلیسی/می‌رود/می‌خوابم/موتر/کنم/هر/دو were all already
    # glossed from earlier A1/A2 units, reused as-is. بخرم (unit01
    # above) and بگیرم (existing A2 lexeme, reused compositionally with
    # یاد to mean "learn") are REUSED, not re-added. تا is a genuine
    # homograph against the existing "counter word (pieces)" sense
    # (A1 unit08 food) -- this unit's sense is the purpose conjunction
    # "in order to / so that", special-cased by content_key in
    # _classify() below, same collision class as می‌شود/رسید above.
    "یاد": "memory (used with گرفتن: to learn)",
    "جمع": "total; gathering (used with کردن: to save/collect)",
    "کنی": "(that) you do", "بگیرد": "(that) he/she takes/gets",
    "کند": "(that) he/she does", "بگیری": "(that) you take/get",
    "بگیریم": "(that) we take/get",
    "بگیرین": "(that) you (plural/polite) take/get",
    "بگیرند": "(that) they take/get",
    "کنید": "(that) you (plural/polite) do", "کنند": "(that) they do",
    "نشوم": "(so that) I don't become",
    "نشوی": "(so that) you don't become", "می‌خوابی": "you sleep",
    "این‌قدر": "this much / so much",
    "پیدا": "found (used with کردن: to find)",
    "هدف": "goal; purpose", "می‌خواهد": "he/she wants",
    "تلاش": "effort (used with کردن: to try hard)",
    "بخرد": "(that) he/she buy",
    # Unit 31 (education), added 2026-07-11 (units 31-40 practice-pool
    # depth-extension pass). مکتب/محصل/کجا/دوست/دارم/را/وقت/ندارم/اما/
    # است/من/در/شما/تو/بلی/چطور/کابل/او/عالی/تحصیل/درس/جالب/پروین/کریم
    # are all REUSED existing lexemes (تحصیل/درس/جالب/پروین/کریم were
    # first introduced by A2 units 09/10, but specs are (level, token)
    # keyed, so unit31 -- level a1 -- still needs its own row; not
    # re-added here, the shared dict value already matches). حقوق is a
    # genuine homograph against the existing "salary" sense (A2 unit14)
    # -- this unit's sense is "law" (field of study), special-cased by
    # content_key in _classify() below instead of overwriting the
    # shared dict entry.
    "پوهنتون": "university", "رشته": "field of study; major",
    "می‌خوانم": "I study / I read", "طب": "medicine",
    "اقتصاد": "economics", "ادبیات": "literature",
    "می‌خوانین": "you study (polite)", "می‌خواند": "he/she studies",
    "می‌خوانی": "you study (informal)", "دشوار": "difficult",
    "رشته‌ی": "field of (construct form)",
    # Unit 32 (celebrations), added 2026-07-11. شما/من/است/چطور/او/یک/
    # اما/دوست/دارم/وقت/ندارم/تو/بلی/خوشحال/امروز/در/کدام are all REUSED
    # existing lexemes.
    "تولد": "birthday", "جشن": "celebration; party", "کیک": "cake",
    "هدیه": "gift", "تبریک": "congratulations",
    "تولدت": "your birthday (informal)", "مبارک": "blessed; happy",
    "می‌آیین": "will you come? (polite)", "بصیر": "Basir (name)",
    "مریم": "Maryam (name)", "می‌آورد": "he/she brings",
    # Unit 33 (household chores), added 2026-07-11. پاک ("clean") /
    # کمک ("help") / باید ("must") / لطفاً ("please") / کی ("who") /
    # چه ("what") / می‌کند / کنین are all REUSED existing lexemes with
    # matching meanings. ظرف is a genuine homograph against the
    # existing "within (a period of time)" preposition sense (A2
    # unit18) -- this unit's sense is the noun "dishes," special-cased
    # by content_key in _classify() below. می‌شویم is likewise a genuine
    # homograph against the existing "we become" sense (B1 unit04,
    # شدن paradigm) -- this unit's sense is "I wash" (شستن paradigm,
    # a coincidental shared conjugated form), also special-cased by
    # content_key below.
    "جاروب": "broom; to sweep", "شستن": "to wash",
    "وحید": "Wahid (name)", "شکریه": "Shukria (name)",
    "می‌شوید": "he/she washes",
    # Unit 34 (neighborhood), added 2026-07-11. نزدیک/دور/کدام/شما/بلی/
    # چطور/من/ما/خانه/خوب/است/نیست/کجاست/در/تو/او/هر/روز/خوشحال/دوست/
    # دارم/را/اما/وقت/ندارم/مکتب/لیلا/فرید are all REUSED existing
    # lexemes.
    "محله": "neighborhood", "همسایه": "neighbor", "سرک": "street; road",
    "دوکان": "shop; store", "کارته": "Karte (neighborhood-name element)",
    # Unit 35 (post office), added 2026-07-11. تکت/خانه/نزدیک/است/
    # می‌خواهم/یک/کجا/به/هرات/شما/چند/روز/دو/سه/امروز/فردا/سلام/برای/یا/
    # خوب/او/در/بسیار/دوست/دارم/را/اما/وقت/ندارم/لطفاً are all REUSED
    # existing lexemes.
    "پُسته": "post (as in پُسته خانه, post office)",
    "پُستی": "postal (as in تکت پُستی, postage stamp)",
    "پارسل": "parcel", "روان": "sent; dispatched (as in روان کردن, to send)",
    "می‌رسد": "it arrives", "روزه": "-day (duration marker, e.g. دو روزه, two-day)",
    "نادیا": "Nadia (name)", "رحیم": "Rahim (name)",
    # Unit 36 (cooking), added 2026-07-11. آشپزخانه/غذا/گوشت/یک/می‌خواهم/
    # در/اول/بعد/آب/گرم/سلام/بلی/لطفاً/چشم/تشکر/او/می‌کند/بسیار/خوشحال/
    # است/دوست/دارم/را/اما/وقت/ندارم/نادیا/فرید are all REUSED existing
    # lexemes.
    "پیاز": "onion", "هستم": "I am (spelling/register variant of استم)",
    "می‌پزم": "I cook", "نمک": "salt", "برنج": "rice",
    "خرد": "chopped (as in خرد کردن, to chop)",
    "می‌اندازم": "I add / I throw in",
    "می‌ریزم": "I pour", "می‌پزین": "you cook (polite)",
    "می‌پزد": "he/she cooks", "بپزین": "(please) cook",
    # Unit 37 (personality), added 2026-07-11. او/است/و/اما/چطور/چون/
    # کمک/بلی/کمی/همیشه/گاهی/همه/را/استم/استین are all REUSED existing
    # lexemes.
    "مهربان": "kind", "زحمتکش": "hardworking", "باهوش": "smart; intelligent",
    "تنبل": "lazy", "شوخ": "funny; playful", "کم‌حرف": "quiet; reserved",
    "راستگو": "honest", "آدم": "person",
    "دوست دارند": "they like",
    # Unit 38 (colors), added 2026-07-11. رنگ/است/سیاه/سفید/سرخ/این/
    # پیراهن/موتر/کتاب/من/و/اما/خانه/چه/کدام/شما/او/اتاق/میز are all
    # REUSED existing lexemes; آبی is a REUSED existing lexeme
    # (unit27 appearance) gaining an additive color_word tag here.
    "زرد": "yellow", "سبز": "green", "نارنجی": "orange",
    "خاکستری": "gray", "بنفش": "purple",
    "قهوه‌یی": "brown (spelling variant of قهوه‌ای, no dialect-meaning difference)",
    "دوست دارین": "you like (polite)", "دوست دارم": "I like",
    "دوست دارد": "he/she likes", "دوست ندارم": "I don't like",
    # Unit 39 (seasons), added 2026-07-11. چهار/است/سال/هوا/گرم/سرد/
    # خیلی/امروز/و/اما/در/می‌شود/می‌بارد/باران/برف/آفتابی/کدام/را/من/
    # شما/بلی/او/محبوب/دوست دارین/دوست دارم/دوست ندارم/دوست دارد are
    # all REUSED existing lexemes (the دوست دار* phrases were first
    # introduced by unit38 above, reused as-is here).
    "فصل": "season", "بهار": "spring", "تابستان": "summer",
    "خنک": "cool", "خزان": "autumn; fall", "زمستان": "winter",
    # Unit 40 (emergencies), added 2026-07-11. کمک/می‌خواهم/این/است/
    # می‌تانین/کنین/به/زود/بیایین/او/دارد/چه/می‌آید/تشکر/زیاد/یک/نفر/
    # شهر/می‌کند/در/تلفن/ندارم/اما/شما are all REUSED existing lexemes.
    "اضطراری": "emergency", "پولیس": "police", "امبولانس": "ambulance",
    "آتش": "fire", "اطفائیه": "fire brigade",
    "مه ره": "me (informal object pronoun)",
    "زنگ بزنین": "call! (polite imperative)",
    "زخمی": "injured", "خون‌ریزی": "bleeding",
    "زنگ می‌زنم": "I call (by phone)", "تشکر زیاد": "thanks a lot",
}

PRS_POS: dict[str, str] = {
    "ا": "symbol", "ب": "symbol", "ت": "symbol", "د": "symbol", "ر": "symbol",
    "ز": "symbol", "س": "symbol", "ش": "symbol", "ص": "symbol", "ج": "symbol",
    "چ": "symbol", "ح": "symbol", "خ": "symbol", "ع": "symbol", "غ": "symbol",
    "ف": "symbol", "ق": "symbol", "ک": "symbol", "گ": "symbol", "ل": "symbol",
    "م": "symbol", "ن": "symbol", "و": "particle", "ه": "symbol", "ی": "symbol",
    "سلام": "noun", "علیکم": "particle", "وعلیکم": "particle", "خوش": "adjective",
    "آمدین": "verb", "تشکر": "noun", "خواهش": "noun", "می‌کنم": "verb",
    "خدا": "noun", "حافظ": "noun", "صبح": "noun", "بخیر": "adjective",
    "روز": "noun", "عصر": "noun", "شب": "noun", "به": "preposition",
    "امید": "noun", "دیدار": "noun", "شما": "pronoun", "چطور": "adverb",
    "استین": "verb", "تو": "pronoun", "استی": "verb", "خوب": "adjective",
    "استم": "verb", "جور": "adjective", "بد": "adjective", "نیستم": "verb",
    "همه": "pronoun", "استند": "verb", "فامیل‌تان": "noun", "است": "verb",
    "اهل": "preposition", "خانه": "noun", "شکر": "noun", "زنده": "adjective",
    "باشین": "verb", "خانهٔ": "noun", "خودتان": "pronoun", "بالا": "adverb",
    "بفرمایین": "verb", "اول": "adverb", "بزرگ‌ترها": "noun", "می‌کنیم": "verb",
    "دفتر": "noun", "کابل": "proper_noun", "حامد": "proper_noun", "من": "pronoun",
    "همکار": "noun", "نو": "adjective", "نجیب": "proper_noun", "آمدین": "verb",
    "نام‌تان": "noun", "چیست": "verb", "نام": "noun", "از": "preposition",
    "آشنایی": "noun", "با": "preposition", "شدم": "verb", "هم": "particle",
    "همکاران": "noun", "را": "particle", "معرفی": "noun", "بسیار": "adverb",
    "این": "pronoun", "میز": "noun",
    # Unit 2 additions, added 2026-07-05.
    "بدهین": "verb", "اجازه": "noun", "همکارم": "noun",
    "فریدون": "proper_noun", "نامت": "noun", "هرات": "proper_noun",
    "مزار": "proper_noun", "شریف": "proper_noun", "افغانستان": "proper_noun",
    "شهر": "noun", "کار": "noun", "داکتر": "noun", "معلم": "noun",
    "مهندس": "noun", "دوکاندار": "noun", "آرزو": "proper_noun",
    "دوست": "noun", "جناب": "noun", "خانم": "noun", "نزدیک": "adjective",
    "می‌تانین": "verb", "دوباره": "adverb", "بگویین": "verb",
    "مهمانی": "noun", "لیلا": "proper_noun", "دیدن": "noun",
    "خوشحال": "adjective", "کجا": "adverb", "کنم": "verb",
    # Unit 3 (family), added 2026-07-06.
    "مادر": "noun", "پدر": "noun", "برادر": "noun", "خواهر": "noun",
    "و": "particle", "این": "pronoun", "من": "pronoun", "او": "pronoun",
    "مادرم": "noun", "برادرم": "noun", "خواهرم": "noun", "است": "verb",
    "پدرکلان": "noun", "مادرکلان": "noun", "کاکا": "noun", "عمه": "noun",
    "ماما": "noun", "خاله": "noun", "کاکایم": "noun", "عمه‌ام": "noun",
    "پدری": "adjective", "پدرم": "noun", "مامایم": "noun", "مادری": "adjective",
    "فامیل": "noun", "فامیل‌تان": "noun", "چند": "adverb", "نفر": "noun",
    "ما": "pronoun", "چهار": "adjective", "پنج": "adjective", "شش": "adjective",
    "یک": "adjective", "دو": "adjective", "دارم": "verb", "تک‌فرزند": "noun",
    "استم": "verb", "داریم": "verb", "دارین": "verb", "مادر‌تان": "noun",
    "جور": "adjective", "استند": "verb", "بلی": "particle", "نخیر": "particle",
    "ندارم": "verb", "پدر‌تان": "noun", "متأهل": "adjective",
    "مجرد": "adjective", "شوهر": "noun", "شوهرم": "noun", "خانم": "noun",
    "ازدواج": "noun", "کردین": "verb", "اولاد": "noun", "محصل": "noun",
    "فرشته": "proper_noun", "دارد": "verb", "هنوز": "adverb",
    "نداریم": "verb", "ندارد": "verb",
    # Unit 4 (numbers), added 2026-07-06.
    "سه": "adjective", "هفت": "adjective", "هشت": "adjective",
    "نه": "adjective", "ده": "adjective", "یازده": "adjective",
    "دوازده": "adjective", "سیزده": "adjective", "چهارده": "adjective",
    "پانزده": "adjective", "شانزده": "adjective", "هفده": "adjective",
    "هجده": "adjective", "نوزده": "adjective", "بیست": "adjective",
    "سی": "adjective", "چهل": "adjective", "پنجاه": "adjective",
    "شصت": "adjective", "هفتاد": "adjective", "هشتاد": "adjective",
    "نود": "adjective", "صد": "adjective", "سال": "noun", "ساله": "adjective",
    "استین": "verb", "استی": "verb", "نمبر": "noun", "تلفن": "noun",
    "تلفن‌تان": "noun", "صفر": "adjective", "تلفنم": "noun", "سلام": "noun",
    "همایون": "proper_noun", "تشکر": "noun", "تو": "pronoun",
    "بشیر": "proper_noun", "تلفنت": "noun", "همین": "adverb",
    "حالا": "adverb", "سیف": "noun", "می‌کنم": "verb",
    # Unit 5 (places), added 2026-07-06.
    "بازار": "noun", "بانک": "noun", "مسجد": "noun", "شفاخانه": "noun",
    "مکتب": "noun", "دواخانه": "noun", "پوسته": "noun", "خانه": "noun",
    "سفارت": "noun", "میدان": "noun", "هوایی": "adjective",
    "کجاست": "verb", "ببخشین": "verb", "دور": "adjective",
    "این‌جا": "adverb", "آن‌جا": "adverb", "در": "preposition",
    "کنار": "noun", "پشت": "preposition", "مقابل": "preposition",
    "زیاد": "adjective", "نیست": "verb", "مستقیم": "adjective",
    "بروین": "verb", "بعد": "adverb", "رهگذر": "noun",
    "زرمینه": "proper_noun", "قابلی": "noun", "نداره": "verb",
    # Unit 6 (directions), added 2026-07-06.
    "چپ": "noun", "راست": "noun", "بپیچین": "verb", "به": "preposition",
    "بروم": "verb", "فهمیدم": "verb", "از": "preposition",
    "روبه‌رو": "adverb", "روبه‌روی": "preposition", "شماست": "verb",
    "بسیار": "adverb", "خوب": "adjective", "سهیلا": "proper_noun",
    "دکاندار": "noun", "سفر": "noun", "خوش": "adjective",
    # Unit 7 (communication), added 2026-07-06.
    "الو": "particle", "کی": "pronoun", "صحبت": "noun", "می‌کند": "verb",
    "فرید": "proper_noun", "لطفاً": "adverb", "آهسته": "adverb",
    "کنین": "verb", "پیام": "noun", "می‌خواهم": "verb", "بگذارم": "verb",
    "زنگ": "noun", "می‌زنم": "verb", "کوتاه": "adjective", "فردا": "adverb",
    "جلسه": "noun", "ساعت": "noun", "می‌رسانم": "verb", "لیمه": "proper_noun",
    "برای": "preposition", "می‌نویسم": "verb", "گذاشت": "verb",
    # Unit 8 (food), added 2026-07-06.
    "نان": "noun", "پلو": "noun", "قورمه": "noun", "چای": "noun", "آب": "noun",
    "چی": "pronoun", "تازه": "adjective", "بشقاب": "noun", "تا": "particle",
    "بل": "noun", "می‌شه": "verb", "خیلی": "adverb", "خوش‌مزه": "adjective",
    "بود": "verb", "چایخانه": "noun", "آمدین": "verb", "میل": "noun",
    "مشتری": "noun", "هردو": "pronoun", "با": "preposition",
    "چشم": "particle", "می‌آرم": "verb", "دوصد": "adjective",
    "افغانی": "noun",
    # A2 unit 09 (bureaucracy), added 2026-07-06.
    "وقت": "noun", "سند": "noun", "آدرس": "noun", "تذکره": "noun",
    "شاروالی": "noun", "می‌خواستم": "verb", "تغییر": "noun",
    "بگیرم": "verb", "چون": "particle", "خانه‌ام": "noun", "را": "particle",
    "عوض": "noun", "کردم": "verb", "باید": "verb", "آدرسم": "noun",
    "می‌شود": "verb", "چه": "pronoun", "چیزی": "pronoun", "بیاورم": "verb",
    "رسید": "noun", "کرایه": "noun", "مهلت": "noun", "بیارین": "verb",
    "ثبت": "noun", "آخر": "noun", "ماه": "noun", "می‌آورم": "verb",
    "خدمتی": "noun", "می‌توانم": "verb", "برایتان": "preposition",
    "انجام": "noun", "بدهم": "verb", "کارمند": "noun",
    "کریم": "proper_noun", "خانهٔ": "noun", "جدید": "adjective",
    "زندگی": "noun", "می‌کنین": "verb", "گذشته": "adjective",
    "کافی": "adjective", "روز": "noun", "سه‌شنبه": "noun", "بیایم": "verb",
    "پیگیری‌تان": "noun", "هزار": "adjective",
    # A2 unit 10 (opinions), added 2026-07-06.
    "نظر": "noun", "دلیل": "noun", "تحصیل": "noun", "خارج": "noun",
    "وطن": "noun", "بهتر": "adjective", "پوهنتون‌های": "noun",
    "فرصت": "noun", "بیشتر": "adjective", "تجربهٔ": "noun", "کسب": "noun",
    "فکر": "noun", "نمی‌کنم": "verb", "پروین": "proper_noun",
    "احمد": "proper_noun", "چرا": "adverb", "فامیلم": "noun",
    "بمانم": "verb", "وطنم": "noun", "کمک": "noun", "درست": "adjective",
    "ولی": "particle", "شاید": "adverb", "همین‌جا": "adverb",
    "می‌مانم": "verb",
    # Unit 9 (days and dates), added 2026-07-07.
    "شنبه": "noun", "یکشنبه": "noun", "دوشنبه": "noun",
    "چهارشنبه": "noun", "پنجشنبه": "noun", "جمعه": "noun",
    "تاریخ": "noun", "رخصتی": "noun", "هفته": "noun",
    "حمل": "noun", "ثور": "noun", "جوزا": "noun", "تقویم": "noun",
    "هجری": "adjective", "شمسی": "adjective", "استفاده": "noun",
    "امروز": "adverb", "پانزدهم": "adjective", "کدام": "pronoun",
    "چندم": "adjective", "نوزدهم": "adjective", "مصروف": "adjective",
    "می‌بینمت": "verb", "داری": "verb", "مشکل": "noun",
    # Unit 10 (shopping and prices), added 2026-07-07.
    "دوکان": "noun", "قیمت": "noun", "ارزان": "adjective",
    "گران": "adjective", "تخفیف": "noun", "قیمتش": "noun",
    "سیب": "noun", "کیلو": "noun", "می‌تانین": "verb",
    "بدهین": "verb", "بفرمایین": "verb", "سیب‌ها": "noun",
    # Unit 11 (time), added 2026-07-07.
    "دقیقه": "noun", "نیم": "noun", "ربع": "noun", "ظهر": "noun",
    "قرار": "noun", "می‌آیم": "verb", "منتظر": "adjective",
    # Unit 12 (daily routines), added 2026-07-07.
    "خواب": "noun", "بیدار": "adjective", "می‌شوم": "verb",
    "صبحانه": "noun", "می‌خورم": "verb", "می‌روم": "verb",
    "می‌خوابم": "verb", "می‌شوی": "verb", "هر": "adverb", "زود": "adverb",
    "چطور؟": "adverb",
    # Unit 13 (making plans), added 2026-07-07.
    "پلان": "noun", "پارک": "noun", "برویم": "verb", "است؟": "verb",
    "می‌خواهین": "verb", "عالی": "adjective", "قبول": "adjective",
    "متأسف": "adjective", "نمی‌توانم": "verb", "دعوت": "noun",
    "می‌بینم": "verb", "نگار": "proper_noun",
    # Unit 14 (preferences), added 2026-07-07. (کدام already exists,
    # see the matching PRS_GLOSSES comment above.)
    "قهوه": "noun", "موسیقی": "noun",
    "دارین": "verb", "یا": "particle", "جالب": "adjective",
    "گرم": "adjective",
    # Unit 15 (comparisons), added 2026-07-07.
    "آن": "pronoun", "بزرگ‌تر": "adjective", "کوچک‌تر": "adjective",
    "گران‌تر": "adjective", "ارزان‌تر": "adjective", "قد": "noun",
    "بلندتر": "adjective", "جوان‌تر": "adjective", "بدتر": "adjective",
    "اما": "particle",
    # Unit 16 (travel), added 2026-07-07.
    "بلیط": "noun", "قطار": "noun", "بس": "noun", "سکو": "noun",
    "سکوی": "noun", "حرکت": "noun",
    "مسافر": "noun", "فروشنده": "noun",
    # Unit 17 (health), added 2026-07-07.
    "سردرد": "noun", "تب": "noun", "دل‌درد": "noun",
    "مریض": "adjective", "حالم": "noun",
    "دوا": "noun", "استراحت": "noun", "بنوشین": "verb", "صاحب": "noun",
    # Unit 18 (work), added 2026-07-07.
    "درس": "noun", "می‌دهد": "verb",
    # Unit 19 (housing), added 2026-07-07.
    "اتاق": "noun", "آشپزخانه": "noun", "تشناب": "noun",
    "چوکی": "noun", "تخت": "noun", "کلکین": "noun", "بزرگ": "adjective",
    # Unit 20 (past events), added 2026-07-09.
    "دیروز": "adverb", "رفتم": "verb", "خوردم": "verb", "خسته": "adjective",
    "رفتی": "verb", "کردی": "verb", "رفت": "verb", "کرد": "verb", "شد": "verb",
    # Unit 21 (clothing), added 2026-07-09.
    "لباس": "noun", "پیراهن": "noun", "پطلون": "noun", "کفش": "noun",
    "رنگ": "noun", "سیاه": "adjective", "سفید": "adjective",
    "سرخ": "adjective", "اندازه": "noun", "کوچک": "adjective",
    "می‌تانم": "verb", "این‌را": "pronoun", "پرو": "noun",
    "پرو کنین": "phrase", "پنجصد": "adjective", "اندازه‌اش": "noun",
    "می‌خرم": "verb", "خرید": "verb",
    # Unit 22 (weather), added 2026-07-09.
    "هوا": "noun", "آفتابی": "adjective", "ابری": "adjective",
    "باران": "noun", "برف": "noun", "می‌بارد": "verb", "سرد": "adjective",
    "بمانیم": "verb", "پس": "particle", "می‌مانیم": "verb",
    "نمی‌توانیم": "verb", "فلم": "noun", "می‌بینیم": "verb",
    "می‌مانند": "verb",
    # Unit 23 (money), added 2026-07-09.
    "پول": "noun", "نقد": "noun", "کارت": "noun", "دالر": "noun",
    "می‌پردازم": "verb", "نقدی": "adjective", "می‌پردازین": "verb",
    "کارتی": "adjective", "بپردازم": "verb", "صرافی": "noun",
    "تبدیل": "noun", "کردن": "verb", "نرخ": "noun",
    "تبدیل کنین": "phrase", "می‌گیرم": "verb", "گرفت": "verb",
    "گرفتم": "verb",
    # Unit 24 (transportation), added 2026-07-09.
    "تکسی": "noun", "موتر": "noun", "دوچرخه": "noun", "پیاده": "adverb",
    "می‌روی": "verb", "تکت": "noun", "ایستگاه": "noun", "تیز": "adjective",
    "تیزتر": "adjective", "خانه‌اش": "noun", "پس‌انداز": "noun",
    "می‌رود": "verb",
    # Unit 25 (emotions), added 2026-07-11.
    "ناراحت": "adjective", "عصبانی": "adjective", "گاهی": "adverb",
    # Unit 26 (hobbies), added 2026-07-11.
    "سرگرمی": "noun", "خواندن": "verb", "گوش": "noun",
    "پیاده‌روی": "noun",
    # Unit 27 (appearance), added 2026-07-11.
    "بلند": "adjective", "مو": "noun", "موی": "noun", "ریش": "noun",
    "عینک": "noun", "قیافه": "noun", "قیافه‌اش": "noun",
    "آبی": "adjective", "قهوه‌ای": "adjective", "برادرت": "noun",
    # Unit 28 (animals), added 2026-07-11.
    "حیوان": "noun", "سگ": "noun", "پشک": "noun", "پرنده": "noun",
    "ماهی": "noun", "خانگی": "adjective", "می‌دهی": "verb",
    "می‌دهم": "verb",
    # Unit 29 (sports), added 2026-07-11.
    "فوتبال": "noun", "والیبال": "noun", "کرکت": "noun", "شنا": "noun",
    "محبوب": "adjective", "باشگاه": "noun",
    # Unit 30 (technology), added 2026-07-11.
    "تکنالوژی": "noun", "موبایل": "noun", "اپلیکیشن": "noun",
    "عکس": "noun", "می‌فرستد": "verb",
    # A2 unit 11 (banking), added 2026-07-11.
    "حساب": "noun", "بانکی": "adjective", "رمز": "noun", "موجودی": "noun",
    "امضا": "noun", "اگر": "particle", "داشته": "verb",
    "می‌توانین": "verb", "باز": "adjective", "بانکی‌تان": "noun",
    "دیگر": "adjective", "آماده": "adjective", "کارمزد": "noun",
    "حداقل": "adjective", "ماهانه": "adjective", "اینه": "particle",
    "تذکره‌ام": "noun", "رمزش": "noun", "همان": "pronoun", "روزی": "noun",
    "که": "particle", "تحویل": "noun", "می‌گیرین": "verb",
    "وقت‌تان": "noun",
    # A2 unit 12 (doctor visit), added 2026-07-11.
    "علامت": "noun", "مدت": "noun", "شدید": "adjective",
    "آزمایش": "noun", "نسخه": "noun", "تجویز": "noun", "پیش": "adverb",
    "سردردم": "noun", "شروع": "noun", "شده": "verb", "آیا": "particle",
    "بار": "noun", "بخورم": "verb", "تاییدی": "noun", "معاینه": "noun",
    "نوبت": "noun", "نتوانین": "verb", "بیایین": "verb", "بزنین": "verb",
    "یک‌کمی": "adverb", "بخورین": "verb", "نشدین": "verb",
    # A2 unit 13 (home maintenance), added 2026-07-11.
    "خرابی": "noun", "لوله": "noun", "برق": "noun", "چکه": "noun",
    "تعمیر": "noun", "کارگر": "noun", "زودتر": "adverb",
    "آشپزخانه‌ام": "noun", "شود": "verb", "بفرستین": "verb",
    "خوابم": "noun", "نمی‌کند": "verb", "هزینه": "noun",
    "رایگان": "adjective", "تعمیرات": "noun", "پنج‌شنبه": "noun",
    "می‌آید": "verb", "صاحب خانه": "noun", "دیشب": "adverb",
    "باشه": "particle", "می‌فرستم": "verb", "می‌گویم": "verb",
    # A2 unit 14 (job interview), added 2026-07-11.
    "تجربه": "noun", "مهارت": "noun", "حقوق": "noun", "وظیفه": "noun",
    "رزومه": "noun", "مصاحبه": "noun", "هفتهٔ": "noun",
    "آینده": "adjective", "چقدر": "adverb", "بست": "noun",
    "شرایط": "noun", "لازم": "adjective", "کمپیوتر": "noun",
    "زبان": "noun", "انگلیسی": "adjective", "سی‌هزار": "adjective",
    "خوش آمدین": "phrase", "خود": "pronoun", "مصاحبه‌کننده": "noun",
    "مهارت‌های": "noun",
    # A2 unit 15 (travel disruption), added 2026-07-11.
    "تاخیر": "noun", "لغو": "noun", "بسته": "adjective", "راه": "noun",
    "مسیر": "noun", "بدیل": "adjective", "برفباری": "noun",
    "اطلاعیه": "noun", "صبر": "noun", "بعدی": "adjective",
    "وجود": "noun", "مسافران": "noun", "کمکی": "noun", "بکنم": "verb",
    "کارمند ایستگاه": "noun", "متأسفم": "verb", "معلومات‌تان": "noun",
    # A2 unit 16 (online habits), added 2026-07-11.
    "شبکهٔ": "noun", "اجتماعی": "adjective", "ویدیو": "noun",
    "دانلود": "noun", "پیام‌رسان": "noun", "بازی": "noun",
    "کمپیوتری": "adjective", "آزاد": "adjective", "معمولاً": "adverb",
    "شبکه‌های": "noun", "بعضی": "pronoun", "اوقات": "noun",
    "می‌گیرد": "verb", "می‌گذرانی": "verb", "انترنت": "noun",
    "مفید": "adjective", "محدود": "adjective", "کنیم": "verb",
    "کاربر": "noun", "بسیاری": "adjective", "مردم": "noun",
    "روزانه": "adverb", "می‌کنند": "verb", "افراد": "noun",
    "بیشتری": "adjective", "خانواده": "noun", "دوستان": "noun",
    "باشند": "verb", "لذت": "noun", "می‌برم": "verb", "کمتر": "adverb",
    # A2 unit 17 (weekly schedule), added 2026-07-11.
    "برنامه": "noun", "روزهای": "noun", "ورزش": "noun", "کمی": "adverb",
    "مطالعه": "noun", "برنامهٔ": "noun", "دیر": "adverb",
    "می‌گذرانم": "verb", "تفاوت": "noun", "می‌کنی": "verb",
    "آشپزی": "noun", "دوستانم": "noun", "خوبی": "adjective",
    # A2 unit 18 (shopping complaint), added 2026-07-11.
    "خراب": "adjective", "تعویض": "noun", "بازپرداخت": "noun",
    "گارانتی": "noun", "عیب": "noun", "وقتی": "particle",
    "روشن": "adjective", "نمی‌شود": "verb", "بخاری": "noun",
    "برقی": "adjective", "خریدم": "verb", "پولم": "noun",
    "ترجیح": "noun", "می‌دهین": "verb", "اصلی": "adjective",
    "کالای": "noun", "خریداری": "noun", "باشد": "verb",
    "می‌توانید": "verb", "ظرف": "preposition", "مشکلی": "noun",
    "روشنش": "noun", "همراه‌تان": "adjective", "رسیدم": "noun",
    "پول‌تان": "noun",
    # B1 unit 01 (abilities), added 2026-07-11.
    "می‌تانی": "verb", "بخرم": "verb", "ببینم": "verb", "بفرستم": "verb",
    "کتاب": "noun", "نامه": "noun", "بفرستی": "verb", "می‌تانه": "verb",
    "می‌تانیم": "verb", "می‌تانن": "verb", "ببره": "verb",
    "بکنین": "verb", "بیایند": "verb", "آنها": "pronoun",
    "می‌تانستم": "verb", "نتانستم": "verb", "می‌تانستی": "verb",
    "پسته خانه": "noun", "نرفت": "verb", "ببری": "verb",
    "راستی": "adverb", "نداشتم": "verb", "ملاقات": "noun",
    "برود": "verb", "نتانست": "verb", "نزد": "preposition",
    "پارسال": "adverb", "بگیره": "verb", "امسال": "adverb",
    # B1 unit 02 (necessity), added 2026-07-11.
    "بخری": "verb", "خودش": "pronoun", "همیشه": "adverb",
    "شکل": "noun", "فعل": "noun", "فاعل": "noun", "بخره": "verb",
    "بخریم": "verb", "بخرین": "verb", "بخرن": "verb",
    "می‌خریدم": "verb", "نباید": "verb", "نخریدم": "verb",
    "مهمان": "noun", "امشب": "adverb", "پاک": "adjective",
    "غذا": "noun", "بپزم": "verb", "گوشت": "noun",
    "می‌آیند": "verb", "نگران": "adjective", "نباش": "verb",
    "می‌کرد": "verb", "داشت": "verb", "حالش": "noun", "بپزد": "verb",
    # B1 unit 03 (conditions), added 2026-07-11.
    "باشم": "verb", "باشی": "verb", "می‌آیی": "verb", "باشیم": "verb",
    "می‌آییم": "verb", "ببارد": "verb",
    "نبارد": "verb", "می‌رویم": "verb", "نمی‌دانم": "verb",
    "می‌نوشیم": "verb", "رفتند": "verb", "ماندند": "verb",
    "نوشیدند": "verb", "آنجا": "adverb", "می‌روند": "verb",
    # B1 unit 04 (sequencing), added 2026-07-11.
    "می‌شویم": "verb", "می‌شین": "verb",
    "می‌شوند": "verb", "پختم": "verb", "رسیدی": "verb",
    "تلویزیون": "noun", "خورد": "verb", "تمام": "adjective",
    "آمد": "verb",
    # B1 unit 05 (reported speech), added 2026-07-11.
    "گفتم": "verb", "گفتی": "verb", "گفت": "verb", "گفتیم": "verb",
    "گفتید": "verb", "گفتند": "verb", "پرسید": "verb",
    "پرسیدم": "verb", "مدیر": "noun", "مهم": "adjective",
    "پرسیدی": "verb", "شنید": "verb",
    # B1 unit 06 (purpose), added 2026-07-11.
    "یاد": "noun", "جمع": "noun", "کنی": "verb", "بگیرد": "verb",
    "کند": "verb", "بگیری": "verb", "بگیریم": "verb",
    "بگیرین": "verb", "بگیرند": "verb", "کنید": "verb",
    "کنند": "verb", "نشوم": "verb", "نشوی": "verb",
    "می‌خوابی": "verb", "این‌قدر": "adverb", "پیدا": "adjective",
    "هدف": "noun", "می‌خواهد": "verb", "تلاش": "noun",
    "بخرد": "verb",
    # Unit 31 (education), added 2026-07-11.
    "پوهنتون": "noun", "رشته": "noun", "می‌خوانم": "verb", "طب": "noun",
    "اقتصاد": "noun", "ادبیات": "noun", "می‌خوانین": "verb",
    "می‌خواند": "verb", "می‌خوانی": "verb", "دشوار": "adjective",
    "رشته‌ی": "noun",
    # Unit 32 (celebrations), added 2026-07-11.
    "تولد": "noun", "جشن": "noun", "کیک": "noun", "هدیه": "noun",
    "تبریک": "noun", "تولدت": "noun", "مبارک": "adjective",
    "می‌آیین": "verb", "بصیر": "proper_noun", "مریم": "proper_noun",
    "می‌آورد": "verb",
    # Unit 33 (household chores), added 2026-07-11.
    "جاروب": "noun", "شستن": "verb", "وحید": "proper_noun",
    "شکریه": "proper_noun", "می‌شوید": "verb",
    # Unit 34 (neighborhood), added 2026-07-11.
    "محله": "noun", "همسایه": "noun", "سرک": "noun", "دوکان": "noun",
    "کارته": "proper_noun",
    # Unit 35 (post office), added 2026-07-11.
    "پُسته": "noun", "پُستی": "adjective", "پارسل": "noun",
    "روان": "adjective", "می‌رسد": "verb", "روزه": "adjective",
    "نادیا": "proper_noun", "رحیم": "proper_noun",
    # Unit 36 (cooking), added 2026-07-11.
    "پیاز": "noun", "هستم": "verb", "می‌پزم": "verb", "نمک": "noun",
    "برنج": "noun", "خرد": "adjective", "می‌اندازم": "verb",
    "می‌ریزم": "verb", "می‌پزین": "verb", "می‌پزد": "verb",
    "بپزین": "verb",
    # Unit 37 (personality), added 2026-07-11.
    "مهربان": "adjective", "زحمتکش": "adjective", "باهوش": "adjective",
    "تنبل": "adjective", "شوخ": "adjective", "کم‌حرف": "adjective",
    "راستگو": "adjective", "آدم": "noun", "دوست دارند": "phrase",
    # Unit 38 (colors), added 2026-07-11.
    "زرد": "adjective", "سبز": "adjective", "نارنجی": "adjective",
    "خاکستری": "adjective", "بنفش": "adjective", "قهوه‌یی": "adjective",
    "دوست دارین": "phrase", "دوست دارم": "phrase", "دوست دارد": "phrase",
    "دوست ندارم": "phrase",
    # Unit 39 (seasons), added 2026-07-11.
    "فصل": "noun", "بهار": "noun", "تابستان": "noun", "خنک": "adjective",
    "خزان": "noun", "زمستان": "noun",
    # Unit 40 (emergencies), added 2026-07-11.
    "اضطراری": "noun", "پولیس": "noun", "امبولانس": "noun", "آتش": "noun",
    "اطفائیه": "noun", "مه ره": "phrase", "زنگ بزنین": "phrase",
    "زخمی": "adjective", "خون‌ریزی": "noun", "زنگ می‌زنم": "phrase",
    "تشکر زیاد": "phrase",
}


# BEGIN volume practice singleton tags (generated 2026-07-13)
VOLUME_PRACTICE_SINGLETON_TAGS = {'آبی': ['volume_en_prs_a1_unit38_color_word_05_single'], 'آرزو': ['volume_en_prs_a1_unit02_person_name_04_single'], 'بانک': ['volume_en_prs_a1_unit05_city_place_06_single'], 'بهار': ['volume_en_prs_a1_unit39_specific_season_word_03_single'], 'جمعه': ['volume_en_prs_a1_unit09_weekday_name_10_single'], 'دور': ['volume_en_prs_a1_unit05_location_word_08_single'], 'سند': ['volume_en_prs_a2_unit09_office_word_12_single'], 'شریف': ['volume_en_prs_a1_unit02_city_name_02_single'], 'شوخ': ['volume_en_prs_a1_unit37_personality_word_07_single'], 'غذا': ['volume_en_prs_a1_unit36_cook_object_word_09_single'], 'نامه': ['volume_en_prs_a1_unit35_sendable_item_word_11_single'], 'پولیس': ['volume_en_prs_a1_unit40_emergency_service_word_01_single']}
# END volume practice singleton tags

def prs_agreement_tags(token: str, lesson_key: str) -> dict[str, object]:
    semantics: list[str] = []

    for semantic in VOLUME_PRACTICE_SINGLETON_TAGS.get(token, ()):
        semantics.append(semantic)
    letters = set("ابتدرزسشصجچحخعغفقکگلمنوهی")
    # "letter" tags every occurrence of these 25 characters unconditionally
    # -- harmless for the other 24 (no competing standalone-word meaning),
    # but و is also the extremely common conjunction "and" used in every
    # later lesson. `docs/content/practice/en-prs/a1_unit01.yaml`'s own
    # `letter` slot preset comment says this tag "keeps this preset
    # restricted to its script use" -- that assumption only holds if
    # "and"-sense occurrences of و don't ALSO get tagged "letter". Real gap
    # found live 2026-07-06/07 alongside the part_of_speech/gloss fix
    # above: restrict و's "letter" tag to its actual script-ramp teaching
    # occurrence so the "and" sense lexeme can't be drawn into a
    # letter-identification slot even though its `part_of_speech` matches.
    if token in letters and (
        token != "و" or lesson_key == "prs.a1.unit01.lesson01.script_ramp"
    ):
        semantics.append("letter")
    if token in {"سلام", "علیکم", "وعلیکم", "خوش"}:
        semantics.append("greeting")
    if token in {"صبح", "روز", "عصر", "شب", "ظهر"}:
        semantics.append("time_period")
    # Narrower than time_period above: excludes روز ("day," the generic
    # noun, not a genuine "part of the day") so a template can safely
    # generalize a taught frame like "ساعت نه {time_of_day} است" across
    # every candidate without producing "nine o'clock day is" nonsense.
    # Added 2026-07-07 for unit11 (time), part_of_day_word set below.
    if token in {"صبح", "عصر", "شب", "ظهر"}:
        semantics.append("time_of_day")
    if token in {"بخیر", "خوش"}:
        semantics.append("good_wish")
    if token in {"خدا", "حافظ", "امید", "دیدار"}:
        semantics.append("farewell")
    if token in {"چطور", "استین", "استی"}:
        semantics.append("wellbeing_question")
    if token in {"خوب", "استم", "جور", "بد", "نیستم", "استند"}:
        semantics.append("wellbeing_answer")
    if token in {"تشکر", "خواهش", "می‌کنم", "بفرمایین", "شکر"}:
        semantics.append("politeness")
    if token in {"نام", "نام‌تان", "چیست", "من", "شما", "تو", "است", "استم"}:
        semantics.append("identity")
    if token in {"حامد", "نجیب"}:
        semantics.append("person_name")
    if token in {"دفتر", "همکار", "همکاران", "نو", "میز", "معرفی"}:
        semantics.append("dialogue_word")
    if lesson_key.endswith("lesson06.first_meeting_dialogue"):
        semantics.append("dialogue_word")
    # Unit 2 additions, 2026-07-05. Also fixes a real pre-existing bug
    # found while extending this function: "کابل" (Kabul, a CITY) was
    # incorrectly tagged "person_name" above (now removed from that set)
    # -- it belongs here as a proper city_name instead.
    if token in {"فریدون", "آرزو", "لیلا"}:
        semantics.append("person_name")
    if token in {"کابل", "هرات", "مزار", "شریف"}:
        semantics.append("city_name")
    if token == "افغانستان":
        semantics.append("country")
    if token == "شهر":
        semantics.append("city_word")
    if token in {"نام", "نام‌تان", "نامت", "چیست"}:
        semantics.append("name_word")
    if token in {"کجا", "استین"} and lesson_key.startswith("prs.a1.unit02.lesson02"):
        semantics.append("origin_question")
    if token == "کار":
        semantics.append("occupation_question")
    if token in {"داکتر", "معلم", "مهندس", "دوکاندار"}:
        semantics.append("occupation")
    if token in {"جناب", "خانم", "صاحب"}:
        # صاحب (unit17 health, added 2026-07-07) is a genuine third member
        # of this same "polite address title" set -- extending the
        # existing tuple in place rather than adding a parallel tag,
        # since it's the identical semantic role جناب/خانم already fill.
        semantics.append("title")
    if token in {"دوست", "همکار", "همکارم", "همکاران"}:
        semantics.append("relationship_word")
    if token in {"اجازه", "بدهین", "معرفی", "کنم", "این"} and lesson_key.startswith("prs.a1.unit02.lesson04"):
        semantics.append("introduction_phrase")
    if token in {"می‌تانین", "دوباره", "بگویین", "نزدیک"}:
        semantics.append("politeness")
    if lesson_key.endswith("lesson06.gathering_dialogue"):
        semantics.append("dialogue_word")

    # Unit 3 (family) semantic tags, added 2026-07-06 -- used by the
    # en-prs practice pack's slot_presets, mirroring the >=3-distinct-
    # candidate rule scripts/_practice_slot_check.py enforces.
    if token in {"مادر", "پدر", "برادر", "خواهر"}:
        semantics.append("immediate_family")
    if token in {"کاکا", "عمه", "ماما", "خاله"}:
        semantics.append("uncle_aunt")
    if token in {"متأهل", "مجرد", "شوهر", "خانم"}:
        semantics.append("marital_word")
    if token in {"دارم", "داریم", "دارین"}:
        semantics.append("have_verb")

    # Unit 4 (numbers) semantic tags, added 2026-07-06.
    if token in {"یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه", "ده"}:
        semantics.append("ones_number")
    if token in {
        "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده",
        "هفده", "هجده", "نوزده",
    }:
        semantics.append("teens_number")
    if token in {"بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود", "صد"}:
        semantics.append("tens_number")
    if token in {"نمبر", "تلفن", "تلفنم"}:
        semantics.append("phone_word")

    # Unit 5 (places) semantic tags, added 2026-07-06.
    if token in {"بازار", "بانک", "مسجد", "شفاخانه", "مکتب", "دواخانه", "سفارت", "دفتر"}:
        semantics.append("city_place")
    if token in {"نزدیک", "دور", "این‌جا", "آن‌جا"}:
        semantics.append("location_word")

    # Unit 6 (directions) semantic tags, added 2026-07-06.
    if token in {"مستقیم", "چپ", "راست"}:
        semantics.append("direction_word")
    if token in {"اول", "بعد"}:
        semantics.append("sequence_word")
    if token == "بپیچین":
        semantics.append("turn_verb")

    # Unit 7 (communication) semantic tags, added 2026-07-06.
    if token in {"فرید", "همایون", "لیمه"}:
        semantics.append("person_name")
    if token in {"الو", "تلفن"}:
        semantics.append("phone_opening")
    if token in {"پیام", "کوتاه"}:
        semantics.append("message_word")

    # Unit 8 (food) semantic tags, added 2026-07-06.
    if token in {"نان", "پلو", "قورمه", "چای", "آب"}:
        semantics.append("food_item")
    if token in {"دکاندار", "مشتری"}:
        semantics.append("role_word")
    if token in {"مسافر", "فروشنده"}:
        # Unit 16 (travel)'s own dialogue-role pair (traveler/seller) --
        # a separate tag from role_word above (that's specifically
        # unit08's shopkeeper/customer pair); kept distinct since these
        # are genuinely different real vocabulary, not padded.
        semantics.append("travel_role_word")
    if token in {"بشقاب", "تا"}:
        semantics.append("counting_word")

    # A2 unit 09 (bureaucracy) semantic tags, added 2026-07-06.
    if token in {"وقت", "سند", "آدرس", "تذکره", "شاروالی"}:
        semantics.append("office_word")
    if token in {"رسید", "مهلت"}:
        semantics.append("paperwork_word")
    # Added 2026-07-07 (A2 tagging-depth pass): pools every genuine
    # whole-sentence/whole-phrase lexeme this unit's own four lessons
    # introduce -- these are auto-derived by _classify()'s new
    # derive_phrases=True path (only ever passed for UNIT_FILES_A2 below,
    # so this can never touch A1's pool) exactly the same way
    # backfill_lexemes.py's own _classify_fa() already does for fa, and
    # this tag mirrors that script's "bureaucracy_phrase" tag for the fa
    # sibling unit exactly -- scoped here via lesson_key prefix so it only
    # ever picks up this unit's own derived phrases, never unit10's or any
    # A1 unit's. This was the single biggest real gap between this script
    # and backfill_lexemes.py's own a2_unit09 section: zero phrase-level
    # lexemes existed here at all before this pass, versus fa's 11 real
    # "bureaucracy_phrase" members.
    if lesson_key.startswith("prs.a2.unit09") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("bureaucracy_phrase")

    # A2 unit 10 (opinions) semantic tags, added 2026-07-06.
    if token in {"نظر", "دلیل", "تحصیل", "خارج", "وطن"}:
        semantics.append("opinion_word")
    if token in {"پروین", "احمد"}:
        semantics.append("person_name")
    # Added 2026-07-07 (A2 tagging-depth pass): پیام (message) and فامیل
    # (family) are both genuinely taught in lesson03 but were never given
    # any semantic tag at all -- mirrors backfill_lexemes.py's own
    # "family_message_word" tag for the fa sibling unit's پیام/خانواده
    # pair exactly (2 real members, matching_pairs/translation only,
    # below the multiple_choice/listen_select 3-candidate floor).
    if token in {"پیام", "فامیل"}:
        semantics.append("family_message_word")
    # Same "bureaucracy_phrase" pattern as unit09 above, scoped to this
    # unit's own lesson_key prefix -- mirrors backfill_lexemes.py's own
    # "opinion_phrase" tag for the fa sibling unit exactly.
    if lesson_key.startswith("prs.a2.unit10") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("opinion_phrase")

    # Unit 9 (dates) semantic tags, added 2026-07-07.
    if token in {"شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"}:
        semantics.append("weekday_name")
    if token in {"حمل", "ثور", "جوزا"}:
        semantics.append("month_name")
    if token in {"پانزدهم", "نوزدهم"}:
        semantics.append("ordinal_date")
    if token in {"تاریخ", "تقویم", "هجری", "شمسی"}:
        semantics.append("calendar_word")
    if token == "بشیر":
        semantics.append("person_name")
    # Cross-unit pooling (unit09 + unit11, both genuine, real
    # vocabulary): مصروف/منتظر are the two "state of a person re: a
    # scheduled event" adjectives taught across these two units;
    # قرار/جلسه are the two "scheduled event" nouns; می‌آیم/می‌بینمت are
    # the two "meeting-arrangement" verbs. Each pair is real, not padded
    # -- kept as separate 2-member groups per AUTHORING_GUIDE.md #16's
    # documented precedent for genuine small closed sets (e.g. unit08's
    # role_word), not force-merged into one oversized bucket.
    if token in {"مصروف", "منتظر"}:
        semantics.append("state_adjective")
    if token in {"قرار", "جلسه"}:
        semantics.append("appointment_word")
    if token in {"می‌آیم", "می‌بینمت"}:
        semantics.append("meeting_verb")

    # Unit 10 (shopping and prices) semantic tags, added 2026-07-07.
    if token in {"دوکان", "قیمت", "ارزان", "گران", "تخفیف", "قیمتش"}:
        semantics.append("shop_word")
    if token in {"سیب", "سیب‌ها"}:
        semantics.append("food_item")
    if token == "کیلو":
        semantics.append("counting_word")
    if token in {"می‌تانین", "بدهین"}:
        semantics.append("polite_request_verb")

    # Unit 11 (time) semantic tags, added 2026-07-07.
    if token in {"ساعت", "دقیقه", "نیم", "ربع"}:
        semantics.append("time_unit")

    # Unit 12 (daily routines) semantic tags, added 2026-07-07.
    if token in {"می‌شوم", "می‌خورم", "می‌روم", "می‌خوابم", "می‌شوی"}:
        semantics.append("routine_verb")
    # می‌شود gets routine_verb ONLY for its unit12 lesson06 occurrence
    # (bare-token match would also wrongly tag A2 unit09's unrelated
    # "would it be possible" sense of the same string) -- same
    # lesson_key-scoped pattern already used above for "و"'s
    # letter-vs-conjunction split.
    if token == "می‌شود" and lesson_key == "prs.a1.unit12.lesson06.comparing_routines_dialogue":
        semantics.append("routine_verb")
    if token in {"خواب", "صبحانه", "دفتر", "شب"}:
        semantics.append("routine_word")
    if token == "هر":
        semantics.append("every_word")
    if token == "زود":
        semantics.append("early_word")
    if token == "زرمینه":
        # Real pre-existing gap fixed here: زرمینه was glossed (unit05,
        # as a passerby character) but never given the person_name tag
        # any earlier unit needed -- this unit's own dialogue (زرمینه و
        # همایون) is the first real practice-pool use of her as a named
        # dialogue speaker, so it's fixed here alongside this unit's own
        # additions rather than left dangling.
        semantics.append("person_name")

    # Unit 13 (making plans) semantic tags, added 2026-07-07.
    if token in {"پلان", "پارک", "دعوت"}:
        semantics.append("plan_noun")
    if token in {"برویم", "می‌خواهین", "نمی‌توانم", "می‌بینم"}:
        semantics.append("plan_verb")
    if token in {"عالی", "قبول", "متأسف", "منتظر"}:
        semantics.append("accept_decline_word")
    if token == "منتظر":
        # Private single-candidate tag (منتظر is the group's only
        # member), layered ON TOP of the shared accept_decline_word tag
        # above -- used by this unit's fill_in_blank template so the
        # slot resolves to exactly one real candidate project-wide
        # (AUTHORING_GUIDE.md #17), while accept_decline_word (4
        # members) still serves the multiple_choice/matching_pairs
        # templates that want the full pool.
        semantics.append("waiting_word")
    if token == "جمعه":
        semantics.append("weekday_name")
    if token == "نگار":
        semantics.append("person_name")

    # Unit 14 (preferences) semantic tags, added 2026-07-07.
    if token in {"دارم", "دارین", "دارد", "ندارم", "ندارد"}:
        semantics.append("preference_verb")
    if token in {"قهوه", "چای", "موسیقی"}:
        semantics.append("preference_topic")
    if token in {"خوش‌مزه", "جالب", "گرم"}:
        semantics.append("description_adjective")
    if token == "گرم":
        # Private single-candidate tag (this unit's fill_in_blank slot),
        # same pattern as منتظر above -- layered on top of the shared
        # description_adjective tag, not a replacement for it.
        semantics.append("warm_word")
    if token in {"کدام", "یا", "بیشتر"}:
        semantics.append("choice_word")
    if token == "کریم":
        # Real pre-existing gap fixed here: کریم was glossed (A2 unit09)
        # but never given the person_name tag -- this unit's dialogue is
        # the first practice-pool use of him as a named dialogue
        # speaker.
        semantics.append("person_name")

    # Unit 15 (comparisons) semantic tags, added 2026-07-07.
    if token in {"این", "آن"}:
        semantics.append("demonstrative_word")
    if token in {
        "بزرگ‌تر", "کوچک‌تر", "گران‌تر", "ارزان‌تر",
        "بلندتر", "جوان‌تر", "بهتر", "بدتر",
    }:
        semantics.append("comparative_adjective")
    # "و" excludes its lesson01 script-ramp (letter-name) occurrence --
    # same lesson_key-scoped guard already used for the "letter" tag
    # above, so the pure conjunction sense (and only that sense) pools
    # with چون/اما here.
    if token in {"چون", "اما"} or (
        token == "و" and lesson_key != "prs.a1.unit01.lesson01.script_ramp"
    ):
        semantics.append("connector_word")
    if token == "قد":
        semantics.append("height_word")

    # Unit 16 (travel) semantic tags, added 2026-07-07.
    if token in {"بلیط", "قطار", "بس"}:
        semantics.append("travel_noun_core")
    if token in {"بلیط", "قطار", "بس", "سکو"}:
        semantics.append("travel_noun")
    if token == "حرکت":
        semantics.append("depart_noun")
    if token == "می‌خواهم":
        semantics.append("want_verb")
    if token in {"تشکر", "زیاد", "قابلی", "نداره", "سفر", "خوش"}:
        semantics.append("travel_farewell_word")
    if token in {"بسیار", "خوب"}:
        semantics.append("confirmation_word")
    if token == "فردا":
        semantics.append("tomorrow_word")
    if token == "سکوی":
        semantics.append("platform_ezafe")
    # "کی" only gets its private when_word tag for THIS unit's own "when"
    # sense occurrence (lesson_key-scoped, mirroring the "letter"/
    # unit12 می‌شود homograph guards above) -- unit07's "who" sense (same
    # bare string, different meaning) must never be pulled into a
    # when_word-constrained slot. See the matching content_key-scoped
    # override in _classify() below, which also gives this sense its own
    # distinct part_of_speech ("adverb" vs. the "who" sense's "pronoun")
    # so the two senses are genuinely separate Lexeme rows.
    if token == "کی" and lesson_key == "prs.a1.unit16.lesson03.asking_departure_details":
        semantics.append("when_word")

    # Unit 17 (health) semantic tags, added 2026-07-07.
    if token in {"سردرد", "تب", "دل‌درد"}:
        semantics.append("symptom_word")
    if token in {"مریض", "خوب", "بد"}:
        semantics.append("health_feeling_word")
    if token in {"داکتر", "دوا"}:
        semantics.append("seek_help_noun")
    if token in {"استراحت", "کنین", "آب", "زیاد", "بنوشین"}:
        semantics.append("health_advice_word")
    if token == "حالم":
        semantics.append("condition_word")
    if token == "بشیر":
        # Real pre-existing gap fixed here: بشیر was glossed (unit04, as
        # a phone-number-exchange character) but never given the
        # person_name tag -- this unit's dialogue is the first
        # practice-pool use of him as a named dialogue speaker (the
        # doctor's patient), same class of gap already fixed for
        # زرمینه/کریم above.
        semantics.append("person_name")

    # Unit 18 (work) semantic tags, added 2026-07-07 (en-fa/en-prs
    # units-18-19 practice-authoring pass). "occupation_workplace"
    # (دفتر/دوکان/شفاخانه/مکتب, 4 members, each pairing with one of the
    # 4 already-established "occupation" members from unit02/unit10 --
    # معلم<->مکتب, داکتر<->شفاخانه, مهندس<->دفتر, دوکاندار<->دوکان) is
    # additive on top of each token's existing city_place/shop_word tags,
    # anchored lesson02 where the pool completes. "work_verb_form"
    # (می‌کنم/می‌کنین/می‌کند, 3 members -- deliberately excludes استم,
    # since کار استم is ungrammatical) is a genuine compositional reuse,
    # not a homograph: each token always literally means "does/do," and
    # combining any of them with the fixed noun کار is grammatically
    # valid regardless of which lesson first introduced them, so no
    # lesson_key scoping is needed here (unlike the real و/می‌شود/کی
    # homograph splits above). "teach_word" (درس/می‌دهد, 2 members,
    # translation/matching-only -- below the multiple_choice floor)
    # anchored lesson05.
    if token in {"دفتر", "دوکان", "شفاخانه", "مکتب"}:
        semantics.append("occupation_workplace")
    if token in {"می‌کنم", "می‌کنین", "می‌کند"}:
        semantics.append("work_verb_form")
    if token in {"درس", "می‌دهد"}:
        semantics.append("teach_word")
    if lesson_key.endswith("lesson06.job_dialogue"):
        semantics.append("dialogue_word")

    # Unit 19 (housing) semantic tags, added 2026-07-07, same pass as
    # unit18 above. "room_word" (خانه/اتاق/آشپزخانه/تشناب, 4 members,
    # anchored lesson01) is the unit's core recognition vocabulary.
    # "home_room_word" is a narrower additive subset EXCLUDING خانه
    # (اتاق/آشپزخانه/تشناب, 3 members) -- used by this unit's own
    # generative "این خانه یک {home_room_word} دارد"-style word_order
    # template, since a خانه candidate there would render the
    # nonsensical "this house has a house." "object_word"
    # (میز/چوکی/تخت/کلکین, 4 members, anchored lesson02).
    # "home_description_word" (بزرگ/مقابل, 2 members, mixed adjective/
    # preposition, translation/matching-only -- below the
    # multiple_choice floor) anchored lesson05.
    if token in {"خانه", "اتاق", "آشپزخانه", "تشناب"}:
        semantics.append("room_word")
    if token in {"اتاق", "آشپزخانه", "تشناب"}:
        semantics.append("home_room_word")
    if token in {"میز", "چوکی", "تخت", "کلکین"}:
        semantics.append("object_word")
    if token in {"بزرگ", "مقابل"}:
        semantics.append("home_description_word")
    if lesson_key.endswith("lesson06.home_dialogue"):
        semantics.append("dialogue_word")

    # Unit 20 (past events) semantic tags, added 2026-07-09 (practice-pool
    # depth-extension pass, units 20-24). "past_verb_first" (رفتم/خوردم/
    # کردم/شدم, 4 members -- شدم/کردم are REUSED existing lexemes from
    # unit02/A2-unit09 respectively, genuinely the same words) is the
    # unit's core first-person simple-past paradigm. "go_verb"/"eat_verb"/
    # "work_past_verb" are private single-candidate subsets layered on top
    # (same pattern as منتظر/گرم in units 13/14), used only where composing
    # with a fixed noun requires a SPECIFIC verb for grammaticality
    # (صبحانه [ate], کار [worked] -- any OTHER past_verb_first member there
    # would be ungrammatical, not just implausible). "past_verb_second"
    # (رفتی/کردی, 2) and "past_verb_third" (رفت/کرد/شد, 3) are the matching
    # 2nd/3rd-person forms, both completed in lesson06's dialogue.
    # "time_reference" pools this unit's new دیروز together with the
    # ALREADY-EXISTING امروز (unit09) and فردا (unit07/13) -- additive
    # extension of those two tokens' tags, not a new parallel group.
    if token in {"رفتم", "خوردم", "کردم", "شدم"}:
        semantics.append("past_verb_first")
    if token == "رفتم":
        semantics.append("go_verb")
    if token == "خوردم":
        semantics.append("eat_verb")
    if token == "کردم":
        semantics.append("work_past_verb")
    if token == "کار":
        semantics.append("work_noun_word")
    if token == "خسته":
        semantics.append("tired_word")
    if token in {"رفتی", "کردی"}:
        semantics.append("past_verb_second")
    if token in {"رفت", "کرد", "شد"}:
        semantics.append("past_verb_third")
    if token in {"دیروز", "امروز", "فردا"}:
        semantics.append("time_reference")
    if lesson_key.endswith("lesson06.yesterday_dialogue"):
        semantics.append("dialogue_word")

    # Unit 21 (clothing) semantic tags, added 2026-07-09. "clothing_word"
    # (لباس/پیراهن/پطلون/کفش, 4 members, anchored lesson01) is the unit's
    # core recognition vocabulary. "color_word" (سیاه/سفید/سرخ, 3,
    # anchored lesson02) are the taught colors; "color_noun" (رنگ, 1) is
    # the noun "color" itself, kept separate from the color ADJECTIVES.
    # "size_word" (اندازه, 1) and "clothing_size_adjective" (بزرگ/کوچک, 2
    # -- additive on top of whatever tags these already carry from the
    # comparisons unit) are this unit's size vocabulary. "can_verb"
    # (می‌تانم, 1) and "buy_verb" (می‌خرم, 1) are both later REUSED as-is
    # by unit23/unit24 (genuinely the same words). "try_on_phrase" (پرو
    # کنین, 1) is a real single-project-wide-candidate phrase-level token.
    if token in {"لباس", "پیراهن", "پطلون", "کفش"}:
        semantics.append("clothing_word")
    if token in {"سیاه", "سفید", "سرخ"}:
        semantics.append("color_word")
    if token == "رنگ":
        semantics.append("color_noun")
    if token == "اندازه":
        semantics.append("size_word")
    if token in {"بزرگ", "کوچک"}:
        semantics.append("clothing_size_adjective")
    if token == "می‌تانم":
        semantics.append("can_verb")
    if token == "می‌خرم":
        semantics.append("buy_verb")
    if token == "پرو کنین":
        semantics.append("try_on_phrase")
    if lesson_key.endswith("lesson05.clothing_shop_dialogue"):
        semantics.append("dialogue_word")

    # Unit 22 (weather) semantic tags, added 2026-07-09. "weather_
    # descriptor" (آفتابی/ابری/گرم/سرد, 4 members -- گرم is a REUSED
    # existing lexeme, additively tagged here alongside its existing
    # unit14 warm_word tag) combines grammatically with است ("هوا X
    # است") for all 4 sky-condition AND temperature adjectives.
    # "weather_precip_noun" (باران/برف, 2) are kept SEPARATE (nouns, not
    # adjectives) since they combine with می‌بارد ("X می‌بارد"), not است --
    # composing them with است instead would be ungrammatical, the same
    # class of constraint already documented for unit20's eat_verb/
    # work_past_verb above. "stay_verb" (بمانیم/می‌مانیم/می‌مانند, 3,
    # completes lesson06) is the "stay home" verb paradigm across
    # subjunctive/1pl/3pl forms -- all distinct glosses. "future_become_
    # verb" is a THIRD homograph sense of می‌شود (weather "will become"),
    # special-cased by content_key in _classify() below, same collision
    # class as the existing A2-unit09/unit12 splits.
    if token in {"آفتابی", "ابری", "گرم", "سرد"}:
        semantics.append("weather_descriptor")
    if token == "هوا":
        semantics.append("weather_noun")
    if token in {"باران", "برف"}:
        semantics.append("weather_precip_noun")
    if token == "می‌بارد":
        semantics.append("fall_verb")
    # Scoped by lesson_key (unambiguous -- this is the only می‌شود
    # occurrence in this lesson) rather than content_key, since this
    # function only receives lesson_key. Matches the resulting Lexeme
    # row created by the content_key-scoped key/gloss split in
    # _classify() above.
    if token == "می‌شود" and lesson_key == "prs.a1.unit22.lesson04.tomorrow_forecast":
        semantics.append("future_become_verb")
    if token in {"بمانیم", "می‌مانیم", "می‌مانند"}:
        semantics.append("stay_verb")
    if token == "بمانیم":
        semantics.append("stay_verb_subjunctive")
    if token == "می‌بینیم":
        semantics.append("watch_verb")
    if token == "نمی‌توانیم":
        semantics.append("cant_verb")
    if token == "فلم":
        semantics.append("film_word")
    if lesson_key.endswith("lesson05.weather_changes_a_plan"):
        semantics.append("dialogue_word")

    # Unit 23 (money) semantic tags, added 2026-07-09. "money_word"
    # (پول/نقد/کارت/دالر, 4, anchored lesson01) is the unit's core
    # recognition vocabulary. "countable_money_word" (کارت/دالر, 2 --
    # additive subset of money_word, excludes the mass nouns پول/نقد)
    # is used only where a "how many X" frame requires a genuinely
    # countable noun. "payment_verb" (می‌پردازم/می‌پردازین/بپردازم, 3,
    # completes lesson02) and "receive_verb" (می‌گیرم/گرفت/گرفتم, 3,
    # completes lesson05) are both real distinct-gloss paradigms.
    # "exchange_word" (صرافی/نرخ, 2) and "cash_or_card_adj"
    # (نقدی/کارتی, 2) are genuine small closed sets, matching_pairs/
    # translation only, per the established role_word/family_message_
    # word precedent. "currency_word" (دالر, 1 -- additive subset of
    # money_word) is used where a frame needs specifically "dollar," not
    # any money_word member (e.g. an exchange-rate question about a
    # generic "card" wouldn't make sense).
    if token in {"پول", "نقد", "کارت", "دالر"}:
        semantics.append("money_word")
    if token in {"کارت", "دالر"}:
        semantics.append("countable_money_word")
    if token == "دالر":
        semantics.append("currency_word")
    if token in {"می‌پردازم", "می‌پردازین", "بپردازم"}:
        semantics.append("payment_verb")
    if token in {"نقدی", "کارتی"}:
        semantics.append("cash_or_card_adj")
    if token in {"صرافی", "نرخ"}:
        semantics.append("exchange_word")
    if token == "تبدیل":
        semantics.append("exchange_noun")
    if token == "تبدیل کنین":
        semantics.append("exchange_imperative")
    if token == "رسید":
        # رسید already carries A2-unit09's "paperwork_word" tag --
        # additively layered here for this unit's own single-candidate
        # fill_in_blank use, same pattern as حالم/منتظر/گرم above.
        semantics.append("receipt_word")
    if token in {"می‌گیرم", "گرفت", "گرفتم"}:
        semantics.append("receive_verb")
    if lesson_key.endswith("lesson04.exchange_dialogue"):
        semantics.append("dialogue_word")

    # Unit 24 (transportation) semantic tags, added 2026-07-09.
    # "transport_mode_word" (بس/تکسی/موتر/دوچرخه, 4, completes lesson01
    # -- بس is a REUSED existing lexeme from unit16 travel) is the
    # unit's core vehicle vocabulary, all combining grammatically with
    # با ... می‌روم ("I go by X"). "on_foot_word" (پیاده, 1) is kept
    # SEPARATE from transport_mode_word since it's not a vehicle noun and
    # combines differently in a sentence (پیاده می‌روم, no با). "go_verb_
    # present" (می‌روم/می‌روی/می‌رود, 3, completes lesson05) is the "go"
    # verb paradigm across 1st/2nd/3rd person -- all distinct glosses.
    # "you_go_verb"/"go_verb_third" are private single-candidate subsets
    # layered on top, same pattern as unit20's go_verb/eat_verb. "speed_
    # adjective" (تیز/تیزتر, 2) is a genuine small closed set. "ticket_
    # word" (تکت/ایستگاه, 2) and "ticket_only" (تکت, 1 -- additive
    # subset, since "ایستگاه چند است؟" would be nonsensical, stations
    # don't have a price) round out the set.
    if token in {"بس", "تکسی", "موتر", "دوچرخه"}:
        semantics.append("transport_mode_word")
    if token == "پیاده":
        semantics.append("on_foot_word")
    if token in {"می‌روم", "می‌روی", "می‌رود"}:
        semantics.append("go_verb_present")
    if token == "می‌روی":
        semantics.append("you_go_verb")
    if token == "می‌رود":
        semantics.append("go_verb_third")
    if token in {"تیز", "تیزتر"}:
        semantics.append("speed_adjective")
    if token == "تیزتر":
        semantics.append("speed_comparative_only")
    if token in {"تکت", "ایستگاه"}:
        semantics.append("ticket_word")
    if token == "تکت":
        semantics.append("ticket_only")
    if lesson_key.endswith("lesson04.commute_dialogue"):
        semantics.append("dialogue_word")

    # Unit 25 (emotions) semantic tags, added 2026-07-11.
    # "emotion_word" (خوشحال/ناراحت/خسته/عصبانی/نگران, 5 members,
    # completes lesson01 -- خوشحال/خسته/نگران are REUSED existing
    # lexemes, additive on top of their existing tags) is the unit's
    # core feeling vocabulary; all five are adjectives that combine
    # grammatically with استم ("I am X") and with the taught
    # "چرا ... استین؟" question frame.
    if token in {"خوشحال", "ناراحت", "خسته", "عصبانی", "نگران"}:
        semantics.append("emotion_word")

    # Unit 26 (hobbies) semantic tags, added 2026-07-11.
    # "hobby_topic_word" (سرگرمی/پیاده‌روی/آشپزی/موسیقی/کتاب/فلم, 6 --
    # موسیقی/کتاب/فلم/آشپزی are REUSED existing lexemes re-taught in
    # this unit's lesson01 hobby compounds) is the unit's recognition
    # pool. "hobby_activity_word" (پیاده‌روی/آشپزی, 2) is the strict
    # subset that combines grammatically with می‌کنم ("I do X") -- the
    # other members would produce ungrammatical "کتاب می‌کنم"-style
    # sentences, same composition trap as unit24's پیاده/با split.
    if token in {"سرگرمی", "پیاده‌روی", "آشپزی", "موسیقی", "کتاب", "فلم"}:
        semantics.append("hobby_topic_word")
    if token in {"پیاده‌روی", "آشپزی"}:
        semantics.append("hobby_activity_word")

    # Unit 27 (appearance) semantic tags, added 2026-07-11.
    # "appearance_word" (قد/مو/چشم/ریش/عینک/قیافه, 6 -- قد is a REUSED
    # existing lexeme; چشم here is the unit27 EYE sense only, a genuine
    # homograph against the existing polite particle "of course," split
    # by content_key in _classify() below and scoped here by lesson_key
    # so the particle sense never gains this tag). "have_feature_word"
    # (ریش/عینک, 2) is the subset that combines with "او ... دارد"
    # (he has a beard / glasses) -- مو/چشم would read oddly there.
    # "eye_hair_color_word" (آبی/قهوه‌ای/سیاه, 3 -- سیاه REUSED,
    # additive on its existing color_word tag) generalizes the taught
    # "چشم او آبی است" frame; سفید deliberately excluded (blue/brown/
    # black are the eye colors this unit actually teaches or reads).
    if token in {"قد", "مو", "ریش", "عینک", "قیافه"}:
        semantics.append("appearance_word")
    if token == "چشم" and lesson_key.startswith("prs.a1.unit27"):
        semantics.append("appearance_word")
    if token in {"ریش", "عینک"}:
        semantics.append("have_feature_word")
    if token in {"آبی", "قهوه‌ای", "سیاه"}:
        semantics.append("eye_hair_color_word")

    # Unit 28 (animals) semantic tags, added 2026-07-11.
    # "animal_topic_word" (حیوان/سگ/پشک/پرنده/ماهی, 5, completes
    # lesson01) is the unit's recognition pool. "animal_word"
    # (سگ/پشک/پرنده/ماهی, 4) excludes the generic حیوان so the taught
    # "یک ... دارم" frame never renders the odd "یک حیوان دارم" as a
    # drilled sentence. "pet_color_word" (سیاه/سفید, 2, both REUSED)
    # is deliberately narrower than unit21's color_word (سرخ excluded
    # -- a red pet is not a sentence this unit teaches).
    if token in {"حیوان", "سگ", "پشک", "پرنده", "ماهی"}:
        semantics.append("animal_topic_word")
    if token in {"سگ", "پشک", "پرنده", "ماهی"}:
        semantics.append("animal_word")
    if token in {"سیاه", "سفید"}:
        semantics.append("pet_color_word")

    # Unit 29 (sports) semantic tags, added 2026-07-11.
    # "sport_topic_word" (ورزش/فوتبال/والیبال/کرکت/شنا/باشگاه, 6 --
    # ورزش REUSED) is the unit's recognition pool. "ball_sport_word"
    # (فوتبال/والیبال/کرکت, 3) is the strict subset that combines with
    # "بازی می‌کنم" ("I play X") -- شنا composes with شنا می‌کنم
    # instead, so drawing it into a بازی frame would be ungrammatical,
    # same composition trap as unit24's پیاده/با split.
    # "sport_place_word" (باشگاه/پارک, 2 -- پارک REUSED) generalizes
    # the taught "در ... بازی می‌کنم" location frame.
    if token in {"ورزش", "فوتبال", "والیبال", "کرکت", "شنا", "باشگاه"}:
        semantics.append("sport_topic_word")
    if token in {"فوتبال", "والیبال", "کرکت"}:
        semantics.append("ball_sport_word")
    if token in {"باشگاه", "پارک"}:
        semantics.append("sport_place_word")

    # Unit 30 (technology) semantic tags, added 2026-07-11.
    # "tech_topic_word" (تکنالوژی/موبایل/کمپیوتر/انترنت/اپلیکیشن/عکس,
    # 6 -- کمپیوتر/انترنت REUSED) is the unit's recognition pool.
    # "tech_use_word" (موبایل/کمپیوتر/انترنت, 3) is the subset the
    # taught "از ... استفاده می‌کنم" frame actually uses.
    # "phone_action_verb" (می‌فرستم/می‌زنم/می‌گیرم, 3, all REUSED with
    # genuinely distinct glosses: I send / I make a call / I take-
    # receive) covers lesson02's phone actions.
    if token in {"تکنالوژی", "موبایل", "کمپیوتر", "انترنت", "اپلیکیشن", "عکس"}:
        semantics.append("tech_topic_word")
    if token in {"موبایل", "کمپیوتر", "انترنت"}:
        semantics.append("tech_use_word")
    if token in {"می‌فرستم", "می‌زنم", "می‌گیرم"}:
        semantics.append("phone_action_verb")

    # Unit 31 (education) semantic tags, added 2026-07-11.
    # "study_vocab_word" (تحصیل/پوهنتون/مکتب/رشته/محصل/درس, 6 --
    # مکتب/محصل REUSED, additive tags) is the unit's recognition pool.
    # "field_word" (طب/حقوق/اقتصاد/ادبیات, 4) is the subset of academic
    # fields that combine grammatically with "من ... می‌خوانم" (I study
    # X), matching the taught "من طب می‌خوانم." pattern. حقوق here uses
    # the special-cased "law" sense (content_key-scoped in _classify()
    # below), never the existing "salary" sense.
    if token in {"تحصیل", "پوهنتون", "مکتب", "رشته", "محصل", "درس"}:
        semantics.append("study_vocab_word")
    if token in {"طب", "حقوق", "اقتصاد", "ادبیات"} and (
        token != "حقوق" or lesson_key.startswith("prs.a1.unit31")
    ):
        semantics.append("field_word")

    # Unit 32 (celebrations) semantic tags, added 2026-07-11.
    # "celebration_word" (تولد/جشن/کیک/هدیه/تبریک, 5) is the unit's
    # recognition pool. "celebration_liked_word" (تولد/جشن/کیک/هدیه, 4
    # -- excludes تبریک, since "I like congratulations" is not a
    # sentence this unit teaches or a natural generalization) is the
    # subset that combines grammatically with the taught "... را دوست
    # دارم" wrap-up frame.
    if token in {"تولد", "جشن", "کیک", "هدیه", "تبریک"}:
        semantics.append("celebration_word")
    if token in {"تولد", "جشن", "کیک", "هدیه"}:
        semantics.append("celebration_liked_word")

    # Unit 33 (household chores) semantic tags, added 2026-07-11.
    # "chore_word" (جاروب/ظرف/پاک/کمک, 4 -- "کار خانه" deliberately
    # excluded, since its own introduced_tokens are the two SEPARATE
    # already-existing words کار/خانه, not a combined "کار خانه"
    # lexeme; there is no single token to tag) is the unit's
    # recognition pool -- ظرف here uses the special-cased "dishes"
    # sense (content_key-scoped in _classify() below), never the
    # existing "within a period of time" sense. "sweep_clean_word"
    # (جاروب/پاک, 2) is the strict subset that combines with the taught
    # "باید ... کنم" light-verb frame (جاروب کردن/پاک کردن) -- ظرف uses
    # شستن instead, a different light verb, so drawing it into this
    # frame would be ungrammatical, same composition trap as unit24's
    # پیاده/با split.
    if token in {"جاروب", "ظرف", "پاک", "کمک"} and (
        token != "ظرف" or lesson_key.startswith("prs.a1.unit33")
    ):
        semantics.append("chore_word")
    if token in {"جاروب", "پاک"}:
        semantics.append("sweep_clean_word")

    # Unit 34 (neighborhood) semantic tags, added 2026-07-11.
    # "neighborhood_word" (محله/همسایه/سرک/دوکان/مکتب, 5 -- مکتب REUSED,
    # additive tag) is the unit's recognition pool. "place_proximity_word"
    # (دوکان/مکتب, 2) is the subset the taught "... نزدیک است"/"... دور
    # نیست" frames actually use.
    if token in {"محله", "همسایه", "سرک", "دوکان", "مکتب"}:
        semantics.append("neighborhood_word")
    if token in {"دوکان", "مکتب"}:
        semantics.append("place_proximity_word")

    # Unit 35 (post office) semantic tags, added 2026-07-11.
    # "post_word" (پُسته/پُستی/نامه/پارسل, 4 -- "پُسته خانه" and "تکت
    # پُستی" deliberately excluded: both are taught as vocabulary whose
    # own introduced_tokens split into two separate pieces (پُسته+خانه
    # reused; تکت reused+پُستی), not a combined single lexeme, so پُسته
    # and پُستی are drawn individually here, each with its own
    # standalone gloss) is the unit's recognition pool.
    # "sendable_item_word" (نامه/پارسل, 2) is the subset the taught
    # "... روان می‌کنم" (I send X) frame actually uses.
    if token in {"پُسته", "پُستی", "نامه", "پارسل"}:
        semantics.append("post_word")
    if token in {"نامه", "پارسل"}:
        semantics.append("sendable_item_word")

    # Unit 36 (cooking) semantic tags, added 2026-07-11.
    # "cooking_word" (آشپزخانه/غذا/پیاز/گوشت/نمک/برنج, 6, all nouns) is
    # the unit's recognition pool. "cook_object_word" (غذا/گوشت/برنج, 3)
    # is the subset that combines grammatically with the taught "...
    # می‌پزم" (I cook X) frame -- پیاز pairs with خرد می‌کنم (chop) and
    # نمک pairs with می‌اندازم (add) instead, so drawing either into a
    # می‌پزم frame would be a composition trap, same class as unit24's
    # پیاده/با split.
    if token in {"آشپزخانه", "غذا", "پیاز", "گوشت", "نمک", "برنج"}:
        semantics.append("cooking_word")
    if token in {"غذا", "گوشت", "برنج"}:
        semantics.append("cook_object_word")

    # Unit 37 (personality) semantic tags, added 2026-07-11.
    # "personality_word" (مهربان/زحمتکش/باهوش/تنبل/شوخ/کم‌حرف/راستگو, 7,
    # all adjectives) is the unit's recognition pool -- every member
    # combines grammatically with the taught "او ... است" predicate
    # frame, checked per candidate (all 7 are simple predicate
    # adjectives with no exceptions).
    if token in {
        "مهربان", "زحمتکش", "باهوش", "تنبل", "شوخ", "کم‌حرف", "راستگو",
    }:
        semantics.append("personality_word")

    # Unit 38 (colors) semantic tags, added 2026-07-11. Extends the
    # existing "color_word" tag (unit21: سیاه/سفید/سرخ) with this
    # unit's new colors plus آبی (REUSED existing lexeme from unit27
    # appearance, additive tag on top of its eye_hair_color_word tag)
    # -- every member combines grammatically with the taught "رنگ ...
    # را دوست دارم" (I like the color X) frame, checked per candidate.
    if token in {
        "آبی", "زرد", "سبز", "نارنجی", "خاکستری", "بنفش", "قهوه‌یی",
    }:
        semantics.append("color_word")

    # Unit 39 (seasons) semantic tags, added 2026-07-11. "season_word"
    # (فصل/بهار/تابستان/خزان/زمستان, 5, includes the generic "season"
    # noun) is the unit's recognition pool. "specific_season_word"
    # (بهار/تابستان/خزان/زمستان, 4 -- excludes the generic فصل) is the
    # subset that combines with the taught "... را دوست دارم" frame
    # (matching "بهار را دوست دارم.").
    if token in {"فصل", "بهار", "تابستان", "خزان", "زمستان"}:
        semantics.append("season_word")
    if token in {"بهار", "تابستان", "خزان", "زمستان"}:
        semantics.append("specific_season_word")

    # Unit 40 (emergencies) semantic tags, added 2026-07-11.
    # "emergency_topic_word" (اضطراری/پولیس/امبولانس/آتش/اطفائیه/زخمی/
    # خون‌ریزی, 7) is the unit's recognition pool. "emergency_service_word"
    # (پولیس/امبولانس/اطفائیه, 3) is the strict subset of callable
    # services that combine with the taught "... می‌خواهم" (I need X)
    # frame (matching "پولیس می‌خواهم!"/"امبولانس می‌خواهم!") -- اضطراری
    # is a description of the situation itself (not something you
    # "need"), and زخمی/خون‌ریزی describe a person's condition, not a
    # service, so both are excluded from this frame.
    if token in {
        "اضطراری", "پولیس", "امبولانس", "آتش", "اطفائیه", "زخمی", "خون‌ریزی",
    }:
        semantics.append("emergency_topic_word")
    if token in {"پولیس", "امبولانس", "اطفائیه"}:
        semantics.append("emergency_service_word")

    # A2 unit 11 (banking) semantic tags, added 2026-07-11. "bank_word"
    # (بانک/حساب/بانکی/کارت/رمز/موجودی/امضا, anchored lesson01) is the
    # unit's core recognition vocabulary. "bank_action_verb"
    # (باز/کنین/می‌توانین, completes the if-grammar note) covers "open an
    # account." "bank_notice_word" (کارمزد/حداقل/ماهانه, anchored
    # lesson03) is the reading-notice vocabulary.
    if token in {"بانک", "حساب", "بانکی", "کارت", "رمز", "موجودی", "امضا"}:
        semantics.append("bank_word")
    if token in {"کارمزد", "حداقل", "ماهانه"}:
        semantics.append("bank_notice_word")
    if lesson_key.startswith("prs.a2.unit11") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("banking_phrase")

    # A2 unit 12 (doctor visit) semantic tags, added 2026-07-11.
    # "symptom_report_word" (علامت/مدت/شدید, anchored lesson01) is the
    # unit's core recognition vocabulary. "appointment_word"
    # (تاییدی/معاینه/نوبت, anchored lesson03) is the appointment-notice
    # vocabulary.
    if token in {"علامت", "مدت", "شدید"}:
        semantics.append("symptom_report_word")
    if token in {"تاییدی", "معاینه", "نوبت"}:
        semantics.append("appointment_word")
    if lesson_key.startswith("prs.a2.unit12") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("doctor_phrase")

    # A2 unit 13 (home maintenance) semantic tags, added 2026-07-11.
    # "maintenance_word" (خرابی/لوله/برق/چکه/تعمیر/کارگر, anchored
    # lesson01) is the unit's core recognition vocabulary.
    if token in {"خرابی", "لوله", "برق", "چکه", "تعمیر", "کارگر"}:
        semantics.append("maintenance_word")
    if token in {"هزینه", "رایگان"}:
        semantics.append("repair_cost_word")
    if lesson_key.startswith("prs.a2.unit13") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("maintenance_phrase")

    # A2 unit 14 (job interview) semantic tags, added 2026-07-11.
    # "interview_word" (تجربه/مهارت/حقوق/وظیفه/رزومه/مصاحبه, anchored
    # lesson01) is the unit's core recognition vocabulary. "posting_word"
    # (بست/شرایط, anchored lesson03) is the job-posting reading
    # vocabulary.
    if token in {"تجربه", "مهارت", "حقوق", "وظیفه", "رزومه", "مصاحبه"}:
        semantics.append("interview_word")
    if token in {"بست", "شرایط"}:
        semantics.append("posting_word")
    if token in {"لیمه"}:
        semantics.append("person_name")
    if lesson_key.startswith("prs.a2.unit14") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("interview_phrase")

    # A2 unit 15 (travel disruption) semantic tags, added 2026-07-11.
    # "disruption_word" (تاخیر/لغو/بسته/مسیر/بدیل/برفباری/اطلاعیه,
    # anchored lesson01) is the unit's core recognition vocabulary.
    if token in {"تاخیر", "لغو", "بسته", "مسیر", "بدیل", "برفباری", "اطلاعیه"}:
        semantics.append("disruption_word")
    if token in {"ایستگاه", "مسافران"}:
        semantics.append("station_word")
    if lesson_key.startswith("prs.a2.unit15") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("travel_disruption_phrase")

    # A2 unit 16 (online habits) semantic tags, added 2026-07-11.
    # "online_habit_word" (ویدیو/دانلود/پیام‌رسان/بازی/کمپیوتری/انترنت,
    # anchored lesson01) is the unit's core recognition vocabulary.
    if token in {"ویدیو", "دانلود", "پیام‌رسان", "بازی", "کمپیوتری", "انترنت"}:
        semantics.append("online_habit_word")
    if token in {"معمولاً", "بعضی", "اوقات"}:
        semantics.append("frequency_word")
    if token == "کاربر":
        semantics.append("technology_role_word")
    if lesson_key.startswith("prs.a2.unit16") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("online_habit_phrase")

    # A2 unit 17 (weekly schedule) semantic tags, added 2026-07-11.
    # "schedule_word" (هفته/برنامه/ورزش/مطالعه, anchored lesson01) is the
    # unit's core recognition vocabulary. "sequence_connector"
    # (اول/بعد/در آخر) is this unit's own step-up connector set,
    # distinct from unit06's own directional اول/بعد "sequence_word" tag
    # (a different, narrower routine-sequencing sense reused here).
    if token in {"هفته", "برنامه", "ورزش", "مطالعه"}:
        semantics.append("schedule_word")
    if token in {"اول", "بعد"}:
        semantics.append("sequence_connector")
    if lesson_key.startswith("prs.a2.unit17") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("weekly_schedule_phrase")

    # A2 unit 18 (shopping complaint) semantic tags, added 2026-07-11.
    # "complaint_word" (خراب/تعویض/بازپرداخت/گارانتی/عیب, anchored
    # lesson01) is the unit's core recognition vocabulary.
    if token in {"خراب", "تعویض", "بازپرداخت", "گارانتی", "عیب"}:
        semantics.append("complaint_word")
    if token in {"مهلت", "اصلی"}:
        semantics.append("return_policy_word")
    if lesson_key.startswith("prs.a2.unit18") and (
        " " in token or "،" in token or "؟" in token
    ):
        semantics.append("shopping_complaint_phrase")

    # B1 unit 01 (abilities) semantic tags, added 2026-07-11. This is the
    # first B1 unit tagged by this function -- B1 is its own separate
    # course ("Dari B1"), so tag-name reuse against A1/A2 tag names
    # elsewhere in this function (e.g. "appointment_word", "location_word",
    # "time_reference" below) is harmless: practice-pool queries are
    # scoped by course_id, so there is no actual cross-course pooling even
    # when the same tag string is used. "ability_verb_present" completes
    # the می‌تانم paradigm across all 6 persons (می‌تانم/می‌تانین are
    # REUSED existing A1 lexemes, additively tagged here). "past_ability_
    # verb" is the past/negative paradigm. "ke_clause_subjunctive" pools
    # every subjunctive verb form this unit teaches after a که-clause
    # (می‌تانم که + subjunctive), spanning lessons 01-05.
    if token in {"می‌تانم", "می‌تانی", "می‌تانه", "می‌تانیم", "می‌تانین", "می‌تانن"}:
        semantics.append("ability_verb_present")
    if token in {"می‌تانستم", "می‌تانستی", "نتانستم", "نتانست"}:
        semantics.append("past_ability_verb")
    if token in {
        "بخرم", "ببینم", "بفرستم", "بفرستی", "ببره", "بکنین", "بیایند",
        "برود", "ببری", "بگیره",
    }:
        semantics.append("ke_clause_subjunctive")
    if token == "آنها":
        semantics.append("plural_pronoun")
    if token in {"کتاب", "نامه"}:
        semantics.append("correspondence_word")
    if token == "پسته خانه":
        semantics.append("errand_place_word")
    if token in {"نرفت", "نتانست", "نداشتم"}:
        semantics.append("past_negative_verb")
    if token == "ملاقات":
        # Reuses the "appointment_word" tag name already used for A1
        # unit11's قرار/جلسه and A2 unit12's تاییدی/معاینه/نوبت -- same
        # generic concept, different course, no real pool mixing (see
        # the module-level comment above).
        semantics.append("appointment_word")
    if token in {"پارسال", "امسال"}:
        # Additive extension of the existing "time_reference" tag
        # (A1 unit20: دیروز/امروز/فردا) -- both are genuine time-reference
        # adverbs, same semantic role.
        semantics.append("time_reference")
    if token == "راستی":
        semantics.append("byway_particle")
    if token == "نزد":
        # Additive extension of the existing "location_word" tag
        # (A1 unit05: نزدیک/دور/این‌جا/آن‌جا).
        semantics.append("location_word")
    if lesson_key.endswith("lesson04.dialogue_errands"):
        semantics.append("dialogue_word")

    # B1 unit 02 (necessity) semantic tags, added 2026-07-11.
    # "necessity_subjunctive_verb" is the باید + بخر- paradigm (بخرم is a
    # REUSED existing B1 lexeme from unit01 above, additively tagged).
    # "past_necessity_verb" (باید + imperfect stem, unfulfilled past
    # obligation) is a genuine small closed set. "grammar_term_word"
    # pools the metalanguage this unit's grammar note teaches (itself/
    # always/form/verb/subject) to explain that باید never conjugates.
    if token in {"بخرم", "بخری", "بخره", "بخریم", "بخرین", "بخرن"}:
        semantics.append("necessity_subjunctive_verb")
    if token in {"می‌خریدم", "می‌کرد"}:
        semantics.append("past_necessity_verb")
    if token in {"نباید", "نخریدم"}:
        semantics.append("necessity_negation_word")
    if token in {"خودش", "همیشه", "شکل", "فعل", "فاعل"}:
        semantics.append("grammar_term_word")
    if token in {"مهمان", "امشب"}:
        semantics.append("guest_word")
    if token in {"غذا", "گوشت"}:
        # Additive extension of the existing "food_item" tag (A1 unit08:
        # نان/پلو/قورمه/چای/آب; A1 unit10: سیب/سیب‌ها).
        semantics.append("food_item")
    if token in {"بپزم", "بپزد"}:
        semantics.append("cook_verb")
    if token in {"نگران", "نباش"}:
        semantics.append("worry_word")
    if token == "پاک":
        semantics.append("clean_word")
    if token == "داشت":
        semantics.append("past_have_verb")
    if token == "حالش":
        # Additive extension of the existing "condition_word" tag
        # (A1 unit17: حالم).
        semantics.append("condition_word")
    if lesson_key.endswith("lesson04.dialogue_guests"):
        semantics.append("dialogue_word")

    # B1 unit 03 (conditions) semantic tags, added 2026-07-11.
    # "subjunctive_be_verb" is the داشته باشم/باشی/باشیم/باشید compound
    # paradigm. "come_verb_present" is a cross-unit paradigm spanning
    # units 02 (می‌آیند), 03 (می‌آیی/می‌آییم), and 05 (reviewed again) --
    # all genuinely the same "come" verb, placed here since unit03 is
    # where most of the paradigm completes. "rain_verb" and
    # "past_verb_plural_third" (park reading) are real closed sets.
    if token in {"باشم", "باشی", "باشیم", "باشین"}:
        semantics.append("subjunctive_be_verb")
    if token in {"می‌آیی", "می‌آیند", "می‌آییم"}:
        semantics.append("come_verb_present")
    if token in {"ببارد", "نبارد"}:
        semantics.append("rain_verb")
    if token in {"می‌رویم", "می‌روند"}:
        semantics.append("go_verb_plural")
    if token == "نمی‌دانم":
        semantics.append("know_verb")
    if token == "می‌نوشیم":
        semantics.append("drink_verb_plural")
    if token in {"رفتند", "ماندند", "نوشیدند"}:
        semantics.append("past_verb_plural_third")
    if token == "آنجا":
        # Additive extension of the existing "location_word" tag, same
        # concept as آن‌جا (the ZWNJ-having spelling) -- see the dict
        # comment above about this being a genuine spelling variant.
        semantics.append("location_word")
    if lesson_key.endswith("lesson04.dialogue_friday_plan"):
        semantics.append("dialogue_word")

    # B1 unit 04 (sequencing) semantic tags, added 2026-07-11.
    # "become_verb_plural" completes the می‌شود paradigm's plural persons
    # (کار می‌کنین pairs with the existing می‌کنیم/می‌کنند members).
    # "past_verb_first_b1"/"past_verb_second_b1"/"past_verb_third_b1" are
    # this unit's own new simple-past forms (distinct from A1 unit20's
    # own past_verb_first/second/third sets, which cover a DIFFERENT verb
    # paradigm -- رفتم/خوردم/کردم/شدم -- kept separate rather than merged
    # in, since combining them would mix verbs across two different
    # courses' tag pools for no real benefit).
    if token in {"می‌شویم", "می‌شین", "می‌شوند"}:
        semantics.append("become_verb_plural")
    if token in {"پختم", "رسیدم"}:
        semantics.append("past_verb_first_b1")
    if token in {"رسیدی"}:
        semantics.append("past_verb_second_b1")
    if token in {"خورد", "آمد"}:
        semantics.append("past_verb_third_b1")
    if token == "تلویزیون":
        semantics.append("household_object_word")
    if token == "تمام":
        semantics.append("completion_word")
    if lesson_key.endswith("lesson04.dialogue_after_work"):
        semantics.append("dialogue_word")

    # B1 unit 05 (reported speech) semantic tags, added 2026-07-11.
    # "report_verb_present"/"report_verb_past" are the گفت/پرسید paradigms
    # (both completed across lessons 01-03).
    if token in {"گفتم", "گفتی", "گفت", "گفتیم", "گفتید", "گفتند"}:
        semantics.append("report_verb_say")
    if token in {"پرسید", "پرسیدم", "پرسیدی"}:
        semantics.append("report_verb_ask")
    if token == "مدیر":
        semantics.append("workplace_person_word")
    if token == "مهم":
        semantics.append("important_word")
    if token == "شنید":
        semantics.append("hear_verb")
    if lesson_key.endswith("lesson04.dialogue_manager_news"):
        semantics.append("dialogue_word")

    # B1 unit 06 (purpose) semantic tags, added 2026-07-11.
    # "purpose_subjunctive_verb" pools the یاد گرفتن/جمع کردن paradigms
    # taught together across lessons 01-02 (بخرم is a REUSED existing B1
    # lexeme from unit01, additively tagged). "negative_purpose_verb" is
    # the نشوم/نشوی pair (lesson03). "goal_word" is the reading/dialogue's
    # own vocabulary (هدف/تلاش).
    if token in {
        "کنی", "بگیرد", "کند", "بگیری", "بگیریم", "بگیرین", "بگیرند",
        "کنید", "کنند", "بخرم", "بخرد",
    }:
        semantics.append("purpose_subjunctive_verb")
    if token in {"نشوم", "نشوی"}:
        semantics.append("negative_purpose_verb")
    if token in {"یاد", "جمع"}:
        semantics.append("purpose_noun_stem")
    if token in {"هدف", "تلاش"}:
        semantics.append("goal_word")
    if token == "این‌قدر":
        semantics.append("degree_word")
    if token == "پیدا":
        semantics.append("find_word")
    if lesson_key.endswith("lesson04.dialogue_goals"):
        semantics.append("dialogue_word")

    tags: dict[str, object] = {}
    if semantics:
        tags["semantic"] = list(dict.fromkeys(semantics))
    person = {
        "من": "first", "استم": "first", "شدم": "first", "می‌کنم": "first",
        "شما": "second", "تو": "second", "استین": "second", "استی": "second",
        "می‌کنیم": "first",
    }.get(token)
    if person:
        tags["person"] = person
    if token in {"شما", "استین"}:
        tags["register"] = "formal"
    elif token in {"تو", "استی"}:
        tags["register"] = "informal"
    return tags


def _classify(files, level, specs, derive_phrases=False):
    # derive_phrases=True is only ever passed for UNIT_FILES_A2 (see
    # iter_specs() below) -- added 2026-07-07 (A2 tagging-depth pass) to
    # mirror backfill_lexemes.py's own _classify_fa() whole-phrase
    # auto-derivation exactly (see that function's matching block for the
    # fa sibling). Keeping this opt-in via a default-False parameter
    # (rather than making it unconditional) guarantees A1's existing
    # lexeme pool is byte-for-byte unchanged by this pass -- only A2 units
    # 09/10 gain the new phrase-level lexemes.
    for unit_order, (realization_path, overlay_path) in enumerate(files, 1):
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
        teaching_overlays = None
        if derive_phrases:
            overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
            teaching_overlays = overlay["teaching"]
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson["teaching"]:
                content_key = item["content_key"]
                for token in item.get("introduced_tokens", []):
                    if token not in PRS_GLOSSES:
                        raise ValueError(
                            f"missing explicit Dari gloss for {token!r} (lesson {lesson_key})"
                        )
                    tags = prs_agreement_tags(token, lesson_key)
                    # Keyed by (level, token) -- A1 and A2 are separate
                    # courses (separate Lexeme rows are fine/expected
                    # even for a token spelled the same in both), so a
                    # bare token key would wrongly merge/skip an A2
                    # occurrence into an A1 spec already seen.
                    key = (level, token)
                    part_of_speech = PRS_POS[token]
                    english_gloss = PRS_GLOSSES[token]
                    # "و" is genuinely two different lexemes in this
                    # course: the LETTER NAME (taught in lesson01's
                    # script-ramp, content_key ...teach.nun_vav_he_ye,
                    # alongside ن/ه/ی which are correctly "X (letter)")
                    # and the extremely common conjunction "and" (used
                    # everywhere else). PRS_POS/PRS_GLOSSES are flat
                    # dicts keyed by bare token, already collapsed to
                    # their LAST literal value ("particle"/"and") by
                    # the time this function runs, and the dedup key
                    # above was ALSO bare-token -- so و only ever
                    # produced one Lexeme, and any template drawing it
                    # (including the letter-ramp matching_pairs drill)
                    # showed "and" as the answer instead of "v/o/u
                    # (letter)", breaking the "every option reads X
                    # (letter)" pattern of that exercise. Real bug
                    # found live 2026-07-06/07 (Dari Endless Practice
                    # QA pass) -- confirmed via a live-generated
                    # matching_pairs item and its actual grading.
                    # Give the letter-ramp occurrence its own key/POS/
                    # gloss so it's a separate Lexeme instead of
                    # colliding with the "and" vocabulary sense.
                    if token == "و" and content_key.endswith("teach.nun_vav_he_ye"):
                        key = (level, token, "letter_symbol")
                        part_of_speech = "symbol"
                        english_gloss = "v/o/u (letter)"
                    # "می‌شود" is likewise genuinely two different
                    # lexemes: A2 unit09's polite-request sense ("would
                    # it be possible; is it okay," a fixed idiom head)
                    # versus this unit's plain third-person indicative
                    # of "to become/wake up" (بیدار می‌شود, he/she wakes
                    # up) introduced in prs.a1.unit12.lesson06's
                    # mishavad_word grammar_note. Same collision class
                    # as "و" above -- special-cased here instead of
                    # letting the second-classified occurrence silently
                    # overwrite the shared PRS_GLOSSES/PRS_POS entry for
                    # the other course's real usage.
                    if token == "می‌شود" and content_key.endswith("teach.mishavad_word"):
                        key = (level, token, "wakeup_third_person")
                        part_of_speech = "verb"
                        english_gloss = "he/she wakes up / becomes (third person)"
                    # "می‌شود" gets a THIRD genuinely distinct sense here:
                    # unit22 (weather)'s future "will become" sense
                    # (فردا هوا سرد می‌شود -- it will get cold tomorrow),
                    # unrelated to both A2-unit09's polite-request sense
                    # and unit12's present-tense "wakes up" sense above.
                    # Same collision class, given its own key/gloss so a
                    # template constrained to this sense never draws
                    # either of the other two.
                    if token == "می‌شود" and content_key.endswith("teach.mishawad"):
                        key = (level, token, "weather_future")
                        part_of_speech = "verb"
                        english_gloss = "will become"
                    # "کی" is likewise genuinely two different lexemes:
                    # unit07's interrogative pronoun sense ("who," content_key
                    # ...lesson02.teach.who_speaking, already the default
                    # PRS_GLOSSES/PRS_POS entry) versus unit16's interrogative
                    # adverb sense ("when," قطار کی حرکت می‌کند؟ -- when does
                    # the train depart?, content_key ...lesson03.teach.
                    # kay_word). Same collision class as و/می‌شود above --
                    # given its own key/POS/gloss here (POS "adverb" instead
                    # of the existing "pronoun") so a template constrained to
                    # part_of_speech: pronoun only ever draws the "who" sense
                    # and a template constrained to part_of_speech: adverb
                    # only ever draws the "when" sense; the bare string is
                    # otherwise identical, so without this split a
                    # multiple_choice/translation/fill_in_blank slot on
                    # either sense could non-deterministically show the
                    # wrong gloss for whichever Lexeme got sampled. Real gap
                    # found and fixed while authoring unit16's practice pool,
                    # 2026-07-07.
                    if token == "کی" and content_key.endswith("teach.kay_word"):
                        key = (level, token, "when_sense")
                        part_of_speech = "adverb"
                        english_gloss = "when"
                    # "چشم" is likewise genuinely two different lexemes:
                    # the polite acknowledgment particle ("of course,"
                    # lit. eye, already the default PRS_GLOSSES/PRS_POS
                    # entry from its earlier teaching occurrence) versus
                    # unit27 (appearance)'s literal body-part NOUN "eye"
                    # (چشم او آبی است -- his/her eyes are blue). Same
                    # collision class as و/می‌شود/کی above -- given its
                    # own key/POS/gloss here so unit27's appearance
                    # templates (part_of_speech: noun + the unit27-scoped
                    # appearance_word tag) only ever draw the "eye" sense
                    # and never show "of course" as the gloss for a
                    # body-part drill. Added 2026-07-11 (units 25-30
                    # practice-pool pass).
                    if token == "چشم" and content_key.endswith("unit27.lesson01.teach.eye_word"):
                        key = (level, token, "eye_noun")
                        part_of_speech = "noun"
                        english_gloss = "eye"
                    # B1 unit04 introduces THREE more genuine homographs
                    # against existing A1/A2 entries, found and fixed while
                    # backfilling the B1 course, 2026-07-11:
                    # "رسید" already exists as a NOUN ("receipt," A2
                    # unit10) -- b1_unit04.lesson05's reading passage
                    # teaches the bare token as the 3rd-person simple past
                    # VERB of رسیدن ("he/she arrived"), an unrelated word
                    # that happens to share the same spelling. Same
                    # collision class as و/می‌شود/کی above.
                    if token == "رسید" and content_key.endswith("teach.resid"):
                        key = (level, token, "arrived_third_person")
                        part_of_speech = "verb"
                        english_gloss = "he/she arrived"
                    # "رسیدم" likewise already exists as a NOUN ("my
                    # receipt," A2 unit18 shopping_complaint, رسید + م
                    # possessive) -- b1_unit04.lesson03 teaches the SAME
                    # bare string as the 1st-person simple past VERB of
                    # رسیدن ("I arrived"). Same collision class.
                    if token == "رسیدم" and content_key.endswith("teach.residam"):
                        key = (level, token, "arrived_first_person")
                        part_of_speech = "verb"
                        english_gloss = "I arrived"
                    # "می‌شود" gets a FOURTH genuinely distinct sense here
                    # (on top of the three A1/A2 senses already split
                    # above): b1_unit04.lesson02's grammar_agreement card
                    # teaches the plain 3rd-person-present indicative
                    # "becomes" as part of a full کار می‌کنم/... و
                    # می‌شوم/... paradigm table, unrelated to A2-unit09's
                    # polite-request idiom, A1-unit12's specific "wakes up"
                    # dialogue sense, and A1-unit22's weather "will become"
                    # sense. content_key.endswith("teach.grammar_agreement")
                    # is reused by MANY B1 lessons for their own unrelated
                    # grammar notes, so this one is scoped by the more
                    # specific lesson_key instead (unique to this card).
                    if token == "می‌شود" and lesson_key == "prs.b1.unit04.lesson02.present_time_clause_all_persons":
                        key = (level, token, "become_third_person_b1")
                        part_of_speech = "verb"
                        english_gloss = "he/she becomes (third person)"
                    # "تا" already exists as a counter word ("two pieces,"
                    # A1 unit08 food) -- b1_unit06.lesson01 teaches the
                    # bare token as the purpose conjunction "in order to /
                    # so that," an unrelated grammatical function that
                    # happens to share the same spelling. Same collision
                    # class as the others above.
                    if token == "تا" and content_key.endswith("teach.ta"):
                        key = (level, token, "purpose_conjunction")
                        part_of_speech = "particle"
                        english_gloss = "in order to / so that"
                    # Units 31-40 (2026-07-11 practice-pool pass) introduce
                    # three more genuine homographs against existing
                    # entries, same collision class as the others above:
                    # "حقوق" already exists as a NOUN meaning "salary" (A2
                    # unit14 job interview) -- unit31's education lesson02
                    # teaches the bare token as "law" (a field of study),
                    # an unrelated meaning that happens to share the same
                    # spelling.
                    if token == "حقوق" and content_key.endswith("teach.law_word"):
                        key = (level, token, "law_sense")
                        part_of_speech = "noun"
                        english_gloss = "law"
                    # "ظرف" already exists as a PREPOSITION meaning "within
                    # (a period of time)" (A2 unit18 shopping complaint) --
                    # unit33's household-chores lesson01 teaches the bare
                    # token as the NOUN "dishes," an unrelated meaning that
                    # happens to share the same spelling.
                    if token == "ظرف" and content_key.endswith("teach.dishes_word"):
                        key = (level, token, "dishes_sense")
                        part_of_speech = "noun"
                        english_gloss = "dishes"
                    # "می‌شویم" already exists meaning "we become" (B1
                    # unit04 sequencing, شدن paradigm) -- unit33's
                    # household-chores lesson01 teaches the bare token as
                    # "I wash" (شستن paradigm), a coincidentally identical
                    # conjugated form with an unrelated verb root.
                    if token == "می‌شویم" and content_key.endswith("teach.review_wash_do"):
                        key = (level, token, "wash_first_person")
                        part_of_speech = "verb"
                        english_gloss = "I wash"
                    existing = specs.get(key)
                    if existing is None:
                        specs[key] = {
                            "level": level,
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "prs",
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

                # Whole-phrase lexeme auto-derivation, added 2026-07-07
                # (A2 tagging-depth pass), A2-only via derive_phrases.
                # Mirrors backfill_lexemes.py's own _classify_fa(): any
                # teaching card that introduces MORE THAN ONE genuinely new
                # token at once (i.e. actually teaches a whole phrase or
                # sentence, not a bare word) also becomes its own separate
                # "phrase" lexeme, keyed on the full Dari target text and
                # glossed from the paired overlay's own teaching gloss (the
                # realization alone has no English text). A card whose
                # target_text spans multiple lines is skipped (never
                # happens in this content, but matches the fa sibling's own
                # defensive check). Real content only -- every phrase this
                # produces is a sentence the realization already teaches
                # verbatim; nothing is invented.
                if derive_phrases:
                    target_text = item.get("target", {}).get("text", "").strip()
                    introduced = item.get("introduced_tokens", [])
                    if len(introduced) > 1 and target_text and "\n" not in target_text:
                        phrase_tags = prs_agreement_tags(target_text, lesson_key)
                        phrase_gloss = teaching_overlays.get(content_key, {}).get("gloss", "")
                        specs.setdefault(
                            (level, target_text),
                            {
                                "level": level,
                                "unit_order": unit_order, "lesson_order": lesson_order,
                                "lesson_content_key": lesson_key, "content_key": content_key,
                                "token": target_text, "language_code": "prs",
                                "part_of_speech": "phrase", "english_gloss": phrase_gloss,
                                "agreement_tags": phrase_tags,
                            },
                        )


def iter_specs():
    specs: dict[tuple[str, str], dict] = {}
    _classify(UNIT_FILES, "a1", specs)
    _classify(UNIT_FILES_A2, "a2", specs, derive_phrases=True)
    # B1 is NOT passed derive_phrases=True, unlike A2 -- checked its
    # actual teaching-card shapes before deciding this, 2026-07-11: several
    # B1 cards introduce more than one token per card, but those are
    # GRAMMAR-NOTE cards whose `target.text` is a full explanatory
    # paragraph (e.g. the می‌تانم paradigm summary) or, in the reading
    # cards, a genuine multi-sentence passage -- neither shape is the
    # short, real, natural phrase/sentence A2's derive_phrases was built
    # for (see backfill_lexemes.py's own _classify_fa() precedent this
    # mirrors). Turning it on for B1 would create garbled "phrase" lexemes
    # keyed on entire grammar explanations or full reading passages, not
    # useful practice-pool material. B1's content shape (dialogue-driven,
    # like A1) is a closer match to A1's own convention, which also never
    # uses derive_phrases.
    _classify(UNIT_FILES_B1, "b1", specs)
    yield from specs.values()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    specs = list(iter_specs())
    if args.dry_run:
        print(f"Lexeme backfill dry run: {len(specs)} prs.")
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        courses_by_level = {}
        for level, title in (("a1", "Dari A1"), ("a2", "Dari A2"), ("b1", "Dari B1")):
            needed = any(spec["level"] == level for spec in specs)
            course = db.scalar(
                select(Course).where(
                    Course.source_language == "en",
                    Course.target_language == "prs",
                    Course.title == title,
                )
            )
            if course is None:
                if needed:
                    print(f"ERROR: en-prs {title!r} course must be imported first", file=sys.stderr)
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
