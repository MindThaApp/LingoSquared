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
    # Units 31-36 (celebrations / household / neighborhood / post /
    # cooking / personality), added 2026-07-12 for the Endless Practice
    # coverage-extension batch. Units 25-30 are not in this tuple in the
    # current practice manifest; this additive pass follows the requested
    # en-fa units 31+ range and keeps A2/B1 course routing separate below.
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
    "سالمه": "I am ... years old (lit. 'my-year-is')", "تا": "counting classifier (number + تا + noun)",
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
    "نوش": "(part of نوش جان, 'enjoy your meal')",
    "جان": "(part of نوش جان, lit. 'dear / soul')",
    "چشم": "right away (polite acknowledgment)",
    "الان": "now; right away",
    "میارم": "I bring (spoken contraction of می‌آورم)",
    "اومدید": "you came (spoken variant of آمدید)",
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
    "فکر": "thought (in فکر کنم, 'I think')",
    "کنم": "I do (subjunctive)", "رضا": "Reza (name)",
    "موافقم": "I agree", "گرمه": "it's hot (spoken)",
    "عالیه": "great; excellent (spoken)", "بریم": "let's go (subjunctive)",
    "پارک": "park", "می‌بینمت": "I'll see you",
    # Unit 8 (shopping: prices, quantities, and paying), added 2026-07-06.
    "مغازه": "shop", "تخفیف": "discount", "کیلویی": "per kilo",
    "کیلو": "kilo", "نصف": "half", "می‌دید": "you give (polite)",
    "برات": "for you (informal)",
    "حساب": "account; bill (in حساب کردن, 'to settle up')",
    "نقدی": "in cash", "کارت": "card",
    "می‌گیرید": "you take; you accept",
    "قابلی": "(part of قابلی نداره, 'no trouble at all')",
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
    "عوض": "change; exchange (in عوض کردن)", "کردم": "I did",
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
    "دستم": "my hand (in از دستم برمیاد, 'I can help')",
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
    "تلف": "wasted (in تلف می‌شه)", "پیام": "message",
    "خانواده": "family", "بیشتر": "more", "خانواده‌م": "my family",
    "باشم": "that I be (subjunctive)",
    "موافق": "agree(ing) (in موافق نیستم, \"I don't agree\")",
    "نگار": "Negar (name)", "آرش": "Arash (name)", "چرا": "why",
    "خونه": "house; home", "همکارامو": "my colleagues (object marker)",
    "ببینم": "let me see (subjunctive)", "می‌گیره": "it takes",
    "عادت": "habit (in عادت دارم, \"I'm used to it\")",
    # Unit 09 (A1: time), added 2026-07-07 (practice-content-gap-closing pass).
    "دقیقه": "minute", "نیم": "half (of an hour)", "ربع": "quarter (of an hour)",
    "نیمه": "is half (spoken contraction of نیم است)", "ظهر": "noon",
    "قرار": "appointment", "یکم": "a little (spoken)", "دیر": "late",
    "میشه": "becomes; happens (spoken)",
    "چهاره": "is four (spoken contraction of چهار است)",
    "سر": "head; top (in سر کار, 'to/at work')", "کار": "work; job",
    "میام": "I come; I'll come (spoken)",
    "مشکلی": "a problem (in مشکلی نیست, 'no problem')",
    "نیست": "is not (negative copula)",
    # Unit 10 (A1: dates), added 2026-07-07.
    "شنبه": "Saturday", "یکشنبه": "Sunday", "دوشنبه": "Monday",
    "چهارشنبه": "Wednesday", "پنجشنبه": "Thursday", "جمعه": "Friday",
    "تعطیل": "off; closed (holiday)", "هفتگیه": "is weekly (spoken)",
    "فروردین": "Farvardin (1st Persian solar month)",
    "اردیبهشت": "Ordibehesht (2nd Persian solar month)",
    "خرداد": "Khordad (3rd Persian solar month)", "تقویم": "calendar",
    "هجری": "Hijri (calendar era)", "شمسی": "solar (calendar)",
    "استفاده": "use (in استفاده می‌کنه, 'uses')",
    "می‌کنه": "does; uses (spoken, 3rd person)",
    "چندشنبه‌ست": "is which day of the week? (spoken contraction)",
    "دهم": "10th", "اردیبهشته": "is Ordibehesht (spoken contraction)",
    "تاریخ": "date", "جلسه": "meeting", "کدوم": "which",
    "روزه": "is (the) day (spoken contraction)",
    "چندم": "what date/number (ordinal question)", "هشتم": "8th",
    "مریم": "Maryam (name)", "سه‌شنبه‌ست": "is Tuesday (spoken contraction)",
    "سرم": "my head (in سرم شلوغه, 'I'm busy')",
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
    "بلند‌تره": "it's/he's taller", "جوون‌تره": "he's/she's younger", "بد‌تره": "it's worse",
    # Unit 16 (A1: travel), added 2026-07-07.
    "بلیط": "ticket", "قطار": "train", "اتوبوس": "bus", "فرودگاه": "airport",
    "سکو": "platform",
    "سکوی": "platform (ezafe-linked form, as in سکوی دو 'platform two')",
    "حرکت": "departure; movement (in حرکت می‌کنه, 'it departs')",
    "مسافر": "traveler; passenger",
    "می‌خواید": "you want (polite)",
    # Unit 17 (A1: health), added 2026-07-07.
    "حالم": "my state/condition (in حالم خوب نیست, 'I don't feel well')",
    "سردرد": "headache", "تب": "fever",
    "دلم": "my stomach (in دلم درد می‌کنه, 'my stomach hurts')",
    "درد": "pain", "خسته‌ام": "I'm tired",
    "کمک": "help", "می‌تونی": "you can (informal)",
    "کمکم": "help me (object)", "کنی": "you do",
    "دکتر": "doctor", "دارو": "medicine",
    "استراحت": "rest (noun, in استراحت کن, 'rest!')",
    "بخور": "drink (imperative, in آب بخور, 'drink water!')",
    # Unit 18 (A1: work), added 2026-07-07 (en-fa units-18-19
    # practice-authoring pass -- the pack grew 17->19 units this session
    # with zero prior practice coverage).
    "شغل": "job",
    "مهندسم": "I'm an engineer (colloquial contraction of مهندس هستم)",
    "معلمم": "I'm a teacher (colloquial contraction of معلم هستم)",
    "دکترم": "I'm a doctor (colloquial contraction of دکتر هستم)",
    "شغلت": "your job",
    "شرکت": "company", "مدرسه": "school", "بیمارستان": "hospital",
    "در": "in / at",
    "مهندسه": "he's/she's an engineer (colloquial, third person)",
    "معلمه": "he's/she's a teacher (colloquial, third person)",
    # Unit 19 (A1: housing), added 2026-07-07, same pass as unit18 above.
    "اتاق": "room", "خواب": "sleep (in اتاق خواب, 'bedroom')",
    "آشپزخانه": "kitchen", "حموم": "bathroom (colloquial)",
    "تخت": "bed", "میز": "table", "صندلی": "chair",
    "بالای": "above / on top of",
    "تخته": "it's the bed (colloquial contraction of تخت است)",
    "آشپزخانه‌س": "it's the kitchen (colloquial contraction of آشپزخانه است)",
    "خونه‌ی": "house of / my house (ezafe form of خونه)",
    "خونه‌ت": "your house (colloquial)",
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
    "سایزی": "what size (indefinite/interrogative form of سایز)",
    "قشنگه": "it's nice (colloquial contraction of قشنگ است)",
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
    "زدن": "to ring / to hit (in زنگ زدن, 'to call')",
    "صدا": "voice",
    "الو": "hello (answering the phone)",
    "منم": "it's me (colloquial contraction of من هم / من است)",
    "تکرار": "repeat / repetition",
    "آهسته‌تر": "more slowly",
    "صحبت": "talk / speech (in صحبت کردن, 'to talk')",
    "بیا": "come (imperative)",
    "کافه": "cafe",
    "قطع": "cut off / disconnected",
    "وصل": "connected",
    "بعداً": "later",
    "بهتر": "better",
    "شد": "became / happened (past)",
    "می‌کنیم": "we do (in صحبت می‌کنیم, 'we'll talk')",
    "میرن": "they go (informal/colloquial)",
    # Unit 23 (A1: emotions), added 2026-07-09, same overnight pass as
    # units 20-22 above. خسته‌ام/خوب/نیستم/چطوری/خوبم/من/یکم/چرا/هستی/کار/
    # کردم/چون/امروز/سارا/چه/نیما/تو/نیست already existed (established
    # across many earlier units) -- reused verbatim, not redeclared here.
    "خوشحال": "happy", "ناراحت": "sad",
    "خوشحالم": "I'm happy (colloquial contraction of خوشحال هستم)",
    "ناراحتم": "I'm sad (colloquial contraction of ناراحت هستم)",
    "خسته": "tired",
    "گشنه": "hungry",
    "گشنه‌ام": "I'm hungry (colloquial contraction of گشنه هستم)",
    "عصبانی": "angry",
    "عصبانی‌ام": "I'm angry (colloquial contraction of عصبانی هستم)",
    "نگران": "worried",
    "نگرانی": "you're worried (colloquial contraction of نگران هستی)",
    "تعطیله": "it's a holiday (colloquial contraction of تعطیل است)",
    "زیاد": "a lot / much",
    "خسته‌ست": "is tired (colloquial contraction of خسته است)",
    "کرده": "has done (past perfect)",
    "فقط": "only",
    "خوشحاله": "he's/she's happy (colloquial contraction of خوشحال است)",
    # Unit 24 (A1: hobbies), added 2026-07-09, same overnight pass as
    # units 20-23 above. وقت/کتاب/من/دوست/دارم/موسیقی/فیلم/می‌کنم/هر/تو/
    # چیکار/می‌کنی/نیما/داره/چند/تا/هم/می‌کنه/سارا/سینما/چی/و/چه/خوب
    # already existed (established across many earlier units) -- reused
    # verbatim, not redeclared here.
    "آزاد": "free (in وقت آزاد, 'free time')",
    "سرگرمی": "hobby",
    "خوندن": "to read / reading",
    "گوش": "ear (in گوش دادن, 'to listen')",
    "می‌دم": "I give / I do (in گوش می‌دم, 'I listen')",
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
    "بانکی": "banking / bank (adjective, from بانک)",
    "اگر": "if", "مدارکتون": "your documents (polite)",
    "می‌تونید": "you can (polite)",
    "لازم": "necessary / needed", "لازمه": "necessary / needed (colloquial contraction of لازم است)",
    "ساعت کاری": "working hours", "بعدازظهر": "afternoon",
    "۸": "8 (eight, numeral)", "۲": "2 (two, numeral)",
    "بکنم": "let me do (subjunctive, formal variant of کنم)",
    "ملیم": "my national ID (colloquial, short for کارت ملیم)",
    "جدیدم": "my new (colloquial possessive form of جدید)",
    "آوردم": "I brought (past)",
    "دیگه": "another; more; next",
    "آماده": "ready", "رمزش": "its PIN code (colloquial)",
    "می‌گیرم": "I get / I take (spoken)",
    "روزی": "day (indefinite form of روز, e.g. 'the day that ...'/'what day')",
    "که": "that / which / so that",
    "تحویل": "delivery / handover (in تحویل گرفتن/می‌گیرید, 'to receive/pick up')",
    # Unit 12 (A2: doctor), added 2026-07-11, same pass as unit11 above.
    "علائم": "symptoms", "مدت": "duration / length of time",
    "نسخه": "prescription", "شدیدی": "severe (indefinite form of شدید)",
    "گفت": "he/she said (past)", "بخورم": "let me drink / I drink (subjunctive)",
    "نوبت": "appointment; turn", "نوبتم": "my appointment (colloquial)",
    "۱۱": "11 (eleven, numeral)",
    "صبحه": "is morning / a.m. (colloquial contraction of صبح است)",
    "زودتر": "earlier; sooner", "۱۵": "15 (fifteen, numeral)",
    "بیایید": "come (polite imperative)",
    "نشد": "didn't happen / didn't become (negative past of شدن)",
    "دوباره": "again", "تماس": "contact / call",
    "بگیرید": "take / get (polite imperative)",
    "شده": "become; happened (past participle of شدن)",
    "دکتر رضایی": "Dr. Rezaei",
    "سردرده": "it's a headache (colloquial contraction of سردرد است)",
    "شدیده": "it's severe (colloquial contraction of شدید است)",
    "شدید": "severe", "داشت": "he/she had (past)",
    "کند": "he/she does (formal subjunctive of کردن)",
    # Unit 13 (A2: maintenance), added 2026-07-11, same pass as unit11
    # above.
    "لوله": "pipe", "لوله‌ی": "pipe of (ezafe-linked form of لوله)",
    "حمام": "bathroom", "چکه": "leak / drip",
    "شوفاژ": "radiator / heater", "خراب": "broken",
    "سرایدار": "building superintendent / custodian",
    "تعمیر": "repair", "زدم": "I hit / I called (past)",
    "زد": "he/she hit / called (past)",
    "بیاید": "come (polite imperative)",
    "تعمیرش": "repair it / its repair (object suffix on تعمیر)",
    "درخواست": "request", "ثبت": "registration / logging",
    "تعمیرکار": "repairman",
    "میاد": "he/she comes (spoken, 3rd person)",
    "۱۰": "10 (ten, numeral)",
    "این‌طوریه": "is like this (colloquial contraction)",
    "میره": "it goes (spoken, 3rd person of رفتن)",
    "روی": "on top of; onto", "زمین": "ground; floor",
    "خونه‌ام": "I'm home (colloquial contraction of خونه + هستم)",
    "می‌بینمتون": "I'll see you (polite)",
    # Unit 14 (A2: job interview), added 2026-07-11, same pass as unit11
    # above.
    "مصاحبه": "interview", "تجربه": "experience",
    "تجربه‌ی": "experience of (ezafe-linked form of تجربه)",
    "مهارت": "skill", "حقوق": "salary",
    "فرصت شغلی": "job opportunity", "رزومه": "résumé / CV",
    "هفته‌ی": "week of (ezafe-linked form of هفته)",
    "شروع": "start; beginning",
    "حداقل": "at least; minimum",
    "فروشگاه": "store; shop", "نیاز": "need",
    "مناسب": "suitable; good (fitting)",
    "مصاحبه‌ها": "interviews (plural of مصاحبه)",
    "انجام": "carrying out; performing",
    "کاریتون": "your work (possessive form of کار, polite)",
    "مصاحبه‌کننده": "interviewer",
    "مهارت‌هایی": "skills (indefinite/plural form of مهارت)",
    "تیمی": "team-related; of the team (in کار تیمی, 'teamwork')",
    "حل": "solving; solution (in حل مسئله, 'problem-solving')",
    "مسئله": "problem; issue",
    "خوبم": "I'm good (at) (colloquial contraction of خوب + ام)",
    # Unit 15 (A2: travel disruption), added 2026-07-11, same pass as
    # unit11 above.
    "قطار": "train", "تاخیر": "delay", "سکو": "platform",
    "سکوی": "platform of (ezafe-linked form of سکو)",
    "لغو": "cancelled", "لغو شدن": "to be cancelled",
    "اعلامیه": "announcement", "مسیر جایگزین": "alternative route",
    "مسیر": "route", "جایگزین": "alternative; substitute",
    "جایگزینی": "alternative; substitute (indefinite form)",
    "نُه": "nine (vocalized spelling, distinct from نه 'no')",
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
    "مفیده": "is useful (colloquial contraction of مفید است)",
    "خبر": "news", "سرگرم‌کننده": "entertaining; fun",
    "حدود": "about; approximately", "استفاده": "use",
    "دنیا": "world", "می‌خونم": "I read (spoken, 1st person)",
    "مورد علاقه": "favorite", "مورد": "case; item",
    "علاقه": "interest; liking",
    "علاقه‌ام": "my interest / liking (possessive form of علاقه)",
    "می‌کند": "he/she does (formal, written register)",
    "اینستاگرامه": "is Instagram (colloquial contraction of اینستاگرام + است)",
    "نظرت": "your opinion (in به نظرت, 'in your opinion')",
    # Unit 17 (A2: weekly schedule), added 2026-07-11, same pass as
    # unit11 above.
    "هفته‌ات": "your week (colloquial possessive)",
    "آخر هفته": "weekend", "آخر": "end",
    "استراحت کردن": "to rest", "اول": "first",
    "در آخر": "finally; at the end",
    "پنجشنبه‌ها": "on Thursdays (habitual plural of پنجشنبه)",
    "جمعه‌ها": "on Fridays (habitual plural of جمعه)",
    "در طول هفته": "during the week", "طول": "duration; length",
    "تمیز کردن": "to clean", "تمیز": "clean",
    "برنامه‌ی": "schedule of (ezafe-linked form of برنامه)",
    "خرید": "shopping; purchase",
    "دوستامو": "my friends (object marker, colloquial)",
    "برنامه‌ت": "your schedule (colloquial possessive)",
    "سر کار": "at/to work",
    # Unit 18 (A2: shopping complaint), added 2026-07-11, same pass as
    # unit11 above.
    "خرابه": "is broken (colloquial contraction of خراب است)",
    "رسید": "receipt", "دادن": "to give (infinitive)",
    "بدم": "let me give / I give (subjunctive)",
    "تعویض": "exchange", "تعویض کردن": "to exchange",
    "بازپرداخت": "refund", "هدفون": "headphones",
    "خریدم": "I bought (past)",
    "صدا نداره": "has no sound",
    "پولم": "my money", "پس بگیرم": "let me get back / get my money back",
    "تعویضش": "exchange it (object suffix on تعویض)",
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
    "کمتر": "less", "قبول": "acceptance (in قبول کردن, 'to accept')",
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
    "حاضره": "is ready (colloquial contraction of حاضر است)",
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
    "امیدوارم": "I hope (contraction of امیدوار + ام)",
    "شاید": "maybe", "همینطور": "likewise",
    # Unit 04 (debate: agreeing/disagreeing with an opinion, plus a
    # reason clause, dialogue about remote work).
    "موافقی": "you agree (informal)", "موافقه": "he/she agrees",
    "موافقیم": "we agree", "موافقید": "you (pl.) agree",
    "موافقن": "they agree", "مخالفم": "I disagree",
    "مخالفه": "he/she disagrees", "سخته": "it's hard (colloquial)",
    "تنهام": "I'm lonely (colloquial contraction of تنها + ام)",
    "تنهاست": "he/she is lonely (colloquial contraction of تنها + است)",
    # Unit 05 (workplace: stating responsibility for a project, status
    # updates, dialogue about a status meeting).
    "مسئول": "responsible", "پروژه": "project", "هستیم": "we are",
    "هستن": "they are", "حسین": "Hossein",
    "تمومه": "it's done (colloquial contraction of تموم + است)",
    "هنوز": "still / yet", "چه‌وقت": "when",
    # Unit 06 (narrative: past-continuous background + simple-past event,
    # reported speech, dialogue retelling a story about a broken-down car).
    "وقتی": "when (temporal conjunction, in وقتی که)",
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
    "دیشب": "last night", "جشن": "party; celebration", "تولد": "birth; birthday (in جشن تولد, 'birthday party')",
    "بودیم": "we were", "بودید": "you (pl.) were", "بودن": "they were",
    "رفته": "gone (past participle, used in رفته بودم, 'I had gone')", "می‌دیدم": "I would see / I would have seen", "نرفته": "not gone (negative past participle)",
    "نمی‌دیدم": "I wouldn't see / I wouldn't have seen", "نیومد": "he/she didn't come (colloquial)", "نیومدم": "I didn't come (colloquial)",
    "اشکالی": "a problem; a flaw (indefinite, in اشکالی نداره, 'no problem')", "جات": "your place (colloquial جا+ت, in جات خالی بود, 'we missed you')", "خالی": "empty",
    "بپرسم": "(that) I ask / let me ask (subjunctive)", "همدیگه": "each other", "ببینیم": "(that) we see (subjunctive)",
    "نتونستم": "I couldn't / wasn't able to", "می‌دونم": "I know (colloquial)", "خوشحال می‌شم": "I'd be happy (to) (خوشحال + colloquial می‌شم, 'I'll become happy')",
    "دست": "hand (in از دست رفت, 'was lost', lit. 'went from hand')", "کمی": "a little", "گذاشتن": "to put; to place (infinitive, in قرار گذاشتن, 'to make plans')",
    "نرفت": "he/she didn't go", "دلتنگ": "homesick; longing (for someone)", "ببینن": "(that) they see (subjunctive)",
    # Unit 08 (nuanced debate: concessive هرچند/با اینکه + stronger contrastives).
    "هرچند": "although", "اما": "but (contrastive)", "اینکه": "that (complementizer, in با اینکه, 'even though')",
    "تنها": "alone", "عین": "(part of در عین حال, 'nevertheless / at the same time')", "حال": "state; condition; mood (bare form of the already-established حالم)",
    "کارم": "my work (possessive form of کار)", "ارتباط": "communication; connection", "تیم": "team",
    "سخت‌تر": "harder (comparative of سخت)", "بعضی": "some", "روزا": "days (colloquial plural of روز)",
    "بازم": "still; also (colloquial)", "درباره‌ی": "about (preposition, ezafe-linked)", "فکری": "thought; idea (indefinite form of فکر, in چه فکری می‌کنه؟)",
    "حرفت": "your point / your words (possessive form of حرف)", "بعضی وقتا": "sometimes (colloquial)", "فرق": "difference (in فرق داره, 'is different')",
    "هیچ‌کدوم": "neither one; none of them", "نظرشون": "their opinion (possessive form of نظر)", "چیزی": "thing; something (indefinite form of چیز)",
    "آیا": "whether (yes-no question particle)", "بحث می‌کنن": "they discuss / debate", "می‌گه": "he/she says (colloquial, 3rd person of گفتن)",
    "حرف": "talk; word; speech", "می‌مونه": "he/she stays / remains (colloquial, 3rd person)", "کارش": "his/her work (possessive form of کار)",
    "می‌ده": "he/she gives / does (colloquial, 3rd person, in انجام می‌ده)", "احترام": "respect", "گفتن": "to say (infinitive)",
    "نکردن": "they didn't do (negative past, 3rd plural)",
    # Unit 09 (professional meetings: formal softened requests/suggestions).
    "بیایم": "(that) we come (subjunctive)", "موکول": "postponed (participial adjective, in موکول کنیم, 'we postpone')", "امکانش": "possibility (of it) (in امکانش هست, 'is it possible')",
    "بفرستید": "you (formal) send", "پیشنهاد": "suggestion", "تصمیم": "decision",
    "بگیریم": "(that) we take/decide (subjunctive, in تصمیم بگیریم)", "بودجه": "budget", "می‌خواد": "he/she wants (colloquial, 3rd person)",
    "جلسه‌ی": "meeting of (ezafe-linked form of جلسه)", "کردید": "you (formal) did", "بعدی": "next",
    "برگزار": "held; organized (participial adjective, in برگزار می‌شه, 'is held')", "تشکر": "thanks; gratitude (in با تشکر, 'with thanks')", "روزیه": "is (which) day (colloquial contraction, in چه روزیه؟)",
    "بفرسته": "he/she sends (subjunctive, 3rd person)", "همچنین": "also; likewise", "گرفتیم": "we took / decided (past, in تصمیم گرفتیم, 'we decided')",
    "سوالی": "a question (indefinite form of سوال)",
    # Unit 10 (relative clauses: subject/object/oblique که-clauses).
    "کسی": "someone; the person (indefinite, in کسی که, 'the person who')", "سارا‌ست": "is Sara (colloquial contraction of سارا+است)", "دوستی": "a friend (indefinite form of دوست, in دوستی که, 'the friend who')",
    "درس می‌خونه": "he/she studies (lit. 'reads lesson')", "کتابی": "a book (indefinite form of کتاب, in کتابی که, 'the book that')", "کاری": "a job/task (indefinite form of کار, in کاری که می‌کنه)",
    "واقعاً": "really", "باهاش": "with him/her (colloquial با+هاش)", "شهری": "a city (indefinite form of شهر, in شهری که, 'the city that')",
    "توش": "in it (colloquial تو+ش)", "شدم": "I became", "صمیمی": "close; intimate",
    "بگم": "(that) I say / let me say (subjunctive)", "دوستم": "my friend", "درباره‌ش": "about him/her/it (colloquial درباره+ش)",
    "همونه": "that's the one (colloquial contraction of همون+است)", "با هم": "together", "می‌رفتیم": "we were going / used to go (imperfect)",
    "بزرگ شده": "has grown up (present perfect, in شهری که توش بزرگ شده)", "شهر": "city (bare form)", "فرق داره": "is different (lit. 'has difference')",
    "همیشه": "always", "برگردم": "let me go back / (that) I return (subjunctive)", "خیابونی": "a street (indefinite form of خیابون, in خیابونی که)",
    "می‌کردم": "I was doing / used to do (imperfect)", "همسایه‌ها": "neighbors (plural)", "همسایه‌هایی": "neighbors (indefinite/relative plural form)",
    "باهاشون": "with them (colloquial با+هاشون)", "مهربون": "kind", "می‌کرد": "he/she was doing / used to do (imperfect)",
    "کوچیکی": "small; little (indefinite adjective form of کوچیک, in شهر کوچیکی)", "به دنیا اومد": "was born (lit. 'came to the world')", "آروم": "calm; quiet",
    "کمکش": "help him/her (object suffix on کمک)", "می‌کردن": "they were doing / used to do (imperfect, 3rd plural)", "برگرده": "(that) he/she return (subjunctive)",
    # Unit 11 (reported speech: reported questions, pronoun shift, plural گفتن).
    "پرسید": "he/she asked", "کِی": "when (explicit kasre diacritic, disambiguating from کی 'who')", "میای": "you're coming (colloquial, 2nd person)",
    "میری": "you're going (colloquial, 2nd person)", "خودش": "himself / herself", "می‌ره": "he/she goes (colloquial, 3rd person)",
    "گفتیم": "we said", "داریم": "we have", "گفتید": "you (pl./formal) said",
    "میاید": "you (pl./formal) are coming", "بهم": "to me (colloquial به+م)", "من و": "... and I (lit. 'I and', in من و مریم, 'Maryam and I')",
    "تعریف": "recounting; telling (in تعریف کردن, 'to recount/tell about')", "موافقت": "agreement (in موافقت کردن, 'to agree')", "کیا": "who (plural, colloquial, in کیا دیگه, 'who else')",
    "بهشون": "to them (colloquial به+شون)", "گفته": "said (past participle, in گفته بود, 'had said')",
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
    "بزرگ‌تره", "کوچیک‌تره", "گرون‌تره", "ارزون‌تره", "بلند‌تره", "جوون‌تره",
    "بد‌تره",
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
}
FA_PHRASE_PARTS = {"بخیر", "خواهش"}
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
    if token in FA_PHRASE_PARTS:
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
    if token in {"تا", "سیب", "کتاب"}:
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
    # (بزرگ‌تره/کوچیک‌تره/گرون‌تره/ارزون‌تره/بلند‌تره/جوون‌تره/بهتره/
    # بد‌تره) into one set rather than fragmenting into per-lesson
    # subgroups, since they all share the exact same "-تره/-ه" contracted
    # comparative form and this gives a much richer >=3-candidate pool for
    # every one of multiple_choice/matching_pairs/translation (بهتره
    # already existed from unit07 with no semantic tag of its own -- this
    # is a clean additive tag, no conflict). "demonstrative_word"
    # (این/اون, 2 members, matching/translation-only -- این already
    # exists from unit03 with unrelated tags, additive here too).
    if token in {
        "بزرگ‌تره", "کوچیک‌تره", "گرون‌تره", "ارزون‌تره",
        "بلند‌تره", "جوون‌تره", "بهتره", "بد‌تره",
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
                    existing = fa_specs.get(key)
                    if existing is None:
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
                # No phrase-derivation at B1: its multi-token teaching cards
                # are grammar-note paragraphs and full reading passages, not
                # the short natural phrases this path was built for (same
                # policy the en-prs script chose for its B1 wiring). The
                # length guard is a hard backstop for every level: Lexeme.
                # token is VARCHAR(255), and a newline-free reading passage
                # slipped through here on 2026-07-11 and crashed the real
                # backfill run with StringDataRightTruncation.
                if (
                    len(introduced) > 1
                    and target_text
                    and "\n" not in target_text
                    and level != "b1"
                    and len(target_text) <= 255
                ):
                    tags = fa_agreement_tags(target_text, lesson_key)
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
                            "part_of_speech": "phrase", "english_gloss": gloss,
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
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        courses_by_level = {}
        for level, title in (("a1", "Farsi A1"), ("a2", "Farsi A2"), ("b1", "Farsi B1")):
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
                # Preserve first-introduction provenance, but refresh reviewed
                # lexical metadata so reruns safely repair earlier backfills.
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
