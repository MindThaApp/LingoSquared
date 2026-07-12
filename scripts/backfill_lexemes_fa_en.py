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

from _en_target_lexeme_common import EN_POS, en_agreement_tags  # noqa: E402

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
    "much": "چقدر (در how much)",
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
    "park": "پارک", "restaurant": "رستوران", "next": "کنار (در next to)",
    "across": "روبه‌رو (در across from)", "from": "از", "between": "بین",
    "behind": "پشت", "front": "جلو (در in front of)", "where": "کجا",
    "far": "دور", "excuse": "ببخشید (در excuse me)", "me": "من (حالت مفعولی)",
    # Unit 10 (asking for and following directions), added 2026-07-06.
    "turn": "پیچیدن", "left": "چپ", "right": "راست", "straight": "مستقیم",
    "stop": "ایستادن", "corner": "نبش؛ گوشهٔ خیابان", "get": "رسیدن (در get to)",
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
    "but": "اما", "going": "قرار است (در going to)", "so": "پس",
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
    "free": "آزاد؛ وقت‌داشتن (در are you free)", "tonight": "امشب",
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
    "wake": "بیدار شدن (در wake up)",
    "up": "بالا (در wake up: بیدار شدن)",
    "dressed": "پوشیده (در get dressed: لباس پوشیدن)", "dinner": "شام",
    "bed": "رختخواب (در go to bed)", "every": "هر", "usually": "معمولاً",
    "breakfast": "صبحانه", "after": "بعد از",
    # Unit 17 (making simple plans), added 2026-07-06. "sorry"/"can't"/
    # "about"/"me" reuse their existing Unit 14/10/14/9 senses unchanged.
    "want": "خواستن", "movie": "فیلم", "weekend": "آخر هفته",
    "would": "(فعل کمکی مؤدبانه؛ در Would you like)", "walk": "قدم زدن",
    "love": "خیلی دوست داشتن؛ عاشق بودن", "busy": "شلوغ (سرم شلوغه)",
    "maybe": "شاید", "another": "یک ... دیگر", "lunch": "ناهار",
    "1pm": "ساعت یک بعدازظهر", "works": "خوب/مناسب است (works for me)",
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
    "way": "طرف (در one way یعنی یک‌طرفه)",
    "round": "دوره‌ای (در round trip یعنی رفت‌وبرگشت)", "trip": "سفر",
    "leaves": "حرکت می‌کنه (فعل، سوم‌شخص مفرد leave)", "9:15": "۹:۱۵",
    "arrives": "می‌رسه (فعل، سوم‌شخص مفرد arrive)", "11:30": "۱۱:۳۰",
    "arrive": "رسیدن (فعل)",
    "headache": "سردرد", "stomachache": "دل‌درد", "fever": "تب",
    "cough": "سرفه", "sore": "دردناک (در sore throat یعنی گلودرد)",
    "throat": "گلو", "wrong": "اشتباه؛ خراب (در What's wrong یعنی چی شده)",
    "feel": "احساس کردن", "rest": "استراحت کردن", "need": "نیاز داشتن",
    "doctor": "دکتر", "look": "به‌نظر رسیدن (در look well)",
    "doesn't": "(منفیِ فعل کمکی does)", "better": "بهتر", "if": "اگر",
    "drink": "نوشیدن",
    "nurse": "پرستار", "cook": "آشپز", "driver": "راننده",
    "patients": "بیماران", "help": "کمک کردن", "reports": "گزارش‌ها",
    "interesting": "جالب", "company": "شرکت", "downtown": "مرکز شهر",
    "answer": "جواب دادن (در answer emails)", "emails": "ایمیل‌ها",
    "sometimes": "بعضی وقت‌ها", "with": "با", "clients": "مشتری‌ها",
    "job": "شغل",
    "bedroom": "اتاق خواب", "kitchen": "آشپزخانه", "bathroom": "حمام",
    "living": "نشیمن (در living room)", "room": "اتاق",
    "garden": "باغچه؛ حیاط", "many": "چند تا (در how many)",
    "rooms": "اتاق‌ها", "there": "آنجا (در there is/there are: وجود داشتن)",
    "there's": "... هست (مخفف there is)", "apartment": "آپارتمان",
    "has": "دارد", "bedrooms": "اتاق‌خواب‌ها", "favorite": "موردعلاقه",
    "tell": "گفتن", "isn't": "نیست (مخفف is not)", "balcony": "بالکن",
    "upstairs": "طبقهٔ بالا", "near": "نزدیک", "easy": "راحت؛ آسان",
    "eat": "خوردن",
    "appointment": "قرار ملاقات", "document": "مدرک",
    "proof": "مدرک؛ سند (در proof of residency)", "residency": "اقامت",
    "form": "فرم", "confirmation": "تأیید", "was": "بود",
    "wondering": "می‌خواستم بدونم (در I was wondering)", "whether": "آیا",
    "could": "می‌تونستم/می‌تونین", "make": "گرفتن (در make an appointment)",
    "possible": "ممکن", "come": "آمدن", "update": "به‌روز کردن",
    "address": "آدرس", "moved": "نقل مکان کردم (زمان گذشتهٔ move)",
    "month": "ماه", "id": "کارت شناسایی",
    "utility": "خدمات شهری (در utility bill)", "bill": "قبض",
    "bring": "آوردن", "such": "مثل (در such as)",
    "lived": "زندگی کرده‌ام (زمان گذشتهٔ live)",
    "since": "از (زمان مشخص)", "lease": "قرارداد اجاره",
    "when": "چه وقت", "10am": "ساعت ۱۰ صبح", "4471": "۴۴۷۱",
    "dog": "سگ", "opinion": "نظر", "other": "دیگر (در on the other hand)",
    "hand": "دست (در on the other hand یعنی از طرف دیگه)",
    "agree": "موافق بودن", "dogs": "سگ‌ها", "space": "فضا", "run": "دویدن",
    "playground": "زمین بازی", "fair": "منصفانه (در fair point)",
    "point": "نکته", "they": "آنها",
    "move": "جابه‌جا کردن؛ منتقل کردن", "farther": "دورتر",
    "away": "دور (در move away)",
    # Unit 27 (A2: opening a bank account), added 2026-07-07. Atomic per-
    # token glosses -- cross-checked against, but not copy-pasted from,
    # docs/content/overlays/fa-en/a2_unit27.yaml's own (phrase-level)
    # Farsi glosses. "debit"/"card"/"i'll"-style contraction pattern reuse
    # their existing Unit 15/12 senses unchanged.
    "checking": "جاری (در checking account)", "account": "حساب",
    "monthly": "ماهانه", "fee": "کارمزد", "minimum": "حداقل",
    "balance": "موجودی", "direct": "مستقیم (در direct deposit)",
    "deposit": "واریز", "documents": "مدارک (جمع)",
    "you'll": "شما ... خواهید (مخفف you will)",
    "dmv": "ادارهٔ راهنمایی و رانندگی",
    "business": "کاری (در business days یعنی روزهای کاری)",
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
    "follow": "پیگیری (در follow-up appointment)",
    "getting": "در حال ... شدن (فعل، در getting worse)",
    "worse": "بدتر", "insurance": "بیمه",
    "i've": "من ... داشته‌ام (مخفف I have)",
    "had": "داشتم (زمان گذشتهٔ have)", "early": "زودتر",
    "confirmed": "تأیید شده (است)", "3pm": "ساعت سهٔ بعدازظهر",
    "7724": "۷۷۲۴", "twice": "دو بار",
    "plenty": "به مقدار زیاد (در plenty of water)",
    "back": "برگشتن (در come back)",
    "within": "ظرف (در within a week یعنی ظرف یک هفته)",
    # Unit 29 (A2: reporting a maintenance problem), added 2026-07-07.
    # Atomic per-token glosses -- cross-checked against, but not copy-
    # pasted from, docs/content/overlays/fa-en/a2_unit29.yaml's own
    # (phrase-level) Farsi glosses. "kitchen"/"apartment"/"bathroom" reuse
    # their existing unit24 senses unchanged (recapped, not retaught).
    "leaking": "چکه کردن", "sink": "سینک", "building": "ساختمان",
    "manager": "مدیر", "plumber": "لوله‌کش", "repair": "تعمیر",
    "report": "گزارش دادن", "problem": "مشکل",
    "been": "بوده (فعل be در ساختار کامل، مثل has been)",
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
    "along": "کنار آمدن (در get along)", "already": "قبلاً",
    "always": "همیشه", "anyone's": "مالِ هیچ‌کس", "app": "اپلیکیشن",
    "apps": "اپلیکیشن‌ها", "around": "دور و بر", "arrived": "رسید",
    "asked": "درخواست کرد", "bake": "پختن (در فر)", "ball.": "توپ",
    "balloons": "بادکنک‌ها", "barks": "پارس می‌کند", "basketball": "بسکتبال",
    "battery": "باتری", "before": "قبل از", "bike": "دوچرخه",
    "bird": "پرنده", "blond": "بلوند (رنگ مو)", "boil": "جوشاندن",
    "boiled": "جوشاند", "book": "کتاب", "books": "کتاب‌ها", "bought": "خرید",
    "break": "اتاق استراحت (در break room)", "brown": "قهوه‌ای",
    "bus": "اتوبوس", "buy": "خریدن", "buys": "می‌خرد", "cake": "کیک",
    "call": "تماس گرفتن", "calm": "آرام", "camera": "دوربین", "cat": "گربه",
    "celebrate": "جشن گرفتن", "chat": "چت کردن", "chicago": "شیکاگو",
    "chop": "خرد کردن", "chopped": "خرد کرد", "chore": "کار خانه",
    "chose": "انتخاب کرد", "classes": "کلاس‌ها", "clean": "تمیز کردن",
    "cleaning": "تمیزکردن (اسم مصدر)", "cleans": "تمیز می‌کند",
    "clerk": "کارمند", "college": "دانشکده", "comfortable": "راحت",
    "coming": "آمدن (میهمان‌ها می‌آیند)",
    "community": "اجتماع (در community college)", "computer": "کامپیوتر",
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
    "express": "پیشتاز (پست پیشتاز)", "eyes": "چشم‌ها", "fast": "سریع",
    "feels": "احساس می‌شود", "fingers": "انگشت‌ها",
    "finishes": "تمام می‌کند", "fish": "ماهی", "five-minute": "پنج‌دقیقه‌ای",
    "forget": "فراموش کردن", "found": "پیدا کرد", "framed": "قاب‌شده",
    "friend": "دوست", "friendly": "مهربان",
    "friends": "دوستان", "funny": "بامزه", "fur": "پشم (حیوان)",
    "games": "بازی‌ها", "gave": "داد",
    "gets": "می‌شود (gets more comfortable)", "gift": "هدیه",
    "glasses": "عینک", "goes": "می‌رود", "grandmother's": "مالِ مادربزرگ",
    "green": "سبز", "grocery": "خواربارفروشی (در grocery store)",
    "group": "گروه", "guests": "میهمان‌ها", "gym": "باشگاه",
    "habits": "عادت‌ها", "hair": "مو", "hallway": "راهرو",
    "hardworking": "زحمت‌کش", "hates": "متنفر است",
    "having": "برگزار کردن (در having a party)",
    "he's": "او ... است (مخفف he is)", "helpful": "کمک‌کننده",
    "helps": "کمک می‌کند", "herself": "خودش (مؤنث)", "him": "او را (مذکر)",
    "hobbies": "سرگرمی‌ها", "homework": "تکلیف", "house": "خانه",
    "how's": "چطوره (مخفف how is)", "humor": "شوخ‌طبعی",
    "ingredient": "مواد اولیه", "instead": "در عوض", "invite": "دعوت کردن",
    "it?": "آن؟", "know": "دانستن", "knows": "می‌شناسد", "laptop": "لپ‌تاپ",
    "laptops": "لپ‌تاپ‌ها", "late": "دیر", "laugh": "خندیدن",
    "laundry": "لباسشویی", "learn": "یاد گرفتن",
    "learning": "در حال یادگیری", "least": "کمترین",
    "leave": "وقت گذاشتن (در leave for)", "letter": "نامه",
    "letters": "نامه‌ها", "likes": "دوست دارد", "live": "زندگی کردن",
    "lives": "زندگی می‌کند", "long": "بلند", "lopez": "لوپز",
    "lot": "خیلی (در a lot)", "loves": "خیلی دوست دارد",
    "low": "کم (باتری کم)", "luna": "لونا", "luna.": "لونا",
    "made": "درست کرد", "mail": "پست", "mailbox": "صندوق پستی",
    "makes": "درست می‌کند", "making": "درست کردن", "map": "نقشه",
    "maps": "نقشه‌ها", "math": "ریاضی", "max.": "مکس", "meetings": "جلسات",
    "meets": "ملاقات می‌کند", "mess": "به‌هم‌ریختگی", "mexico": "مکزیک",
    "mia": "میا", "mia's": "مالِ میا", "mia,": "میا،", "might": "ممکن است",
    "mind": "اهمیت دادن (I don't mind)", "mine": "مالِ من", "mom": "مامان",
    "morning.": "صبح", "mornings": "صبح‌ها", "most": "بیشتر",
    "mostly": "بیشترِ اوقات", "mother's": "مالِ مادر", "mr": "آقای",
    "named": "به نام", "names": "اسم‌ها", "nearby": "نزدیک",
    "needs": "نیاز دارد", "neighbor": "همسایه", "neighborhood": "محله",
    "neighborhoods": "محله‌ها", "neighbors": "همسایه‌ها", "never": "هرگز",
    "nice!": "قشنگ!", "nights": "شب‌ها", "noisy": "پرسروصدا", "now": "حالا",
    "october": "اکتبر", "office": "دفتر کار", "office.": "دفتر کار",
    "often": "اغلب", "okay,": "خب،", "once": "وقتی که (once you know)",
    "onions": "پیازها", "organized": "منظم", "out": "بیرون (در take out)",
    "outgoing": "اجتماعی", "outside": "بیرون از",
    "own": "خودش (own chore habits)", "package": "بسته",
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
    "sends": "می‌فرستد", "sense": "حس (sense of humor)", "sent": "فرستاد",
    "several": "چند تا", "shops": "مغازه‌ها", "short": "کوتاه",
    "show": "نشان دادن", "shy": "خجالتی", "sister's": "مالِ خواهرم",
    "skills": "مهارت‌ها", "slow": "کند", "soccer": "فوتبال",
    "some": "مقداری", "someday": "یک روزی", "something": "چیزی",
    "sometime": "یک وقتی", "soon": "به‌زودی", "spanish": "اسپانیایی",
    "spending": "گذراندن (وقت)", "sport": "ورزش", "stamp": "تمبر",
    "starting": "شروع می‌کند", "stay": "ماندن (در stay active)",
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
    "video": "ویدیویی (در video games)", "walks,": "پیاده‌روی‌ها،",
    "wanted": "می‌خواست", "wants": "می‌خواهد",
    "warms": "گرم می‌شود (warms up: راحت می‌شود)", "wash": "شستن",
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


def _classify(files, level, specs):
    for unit_order, (realization_path, _overlay_path) in enumerate(files, 1):
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson["teaching"]:
                content_key = item["content_key"]
                for token in item.get("introduced_tokens", []):
                    token = token.casefold().replace("’", "'")
                    if token not in EN_POS:
                        raise ValueError(
                            f"missing English classification for {token!r} "
                            f"in _en_target_lexeme_common.py (lesson {lesson_key})"
                        )
                    tags = en_agreement_tags(token)
                    # Keyed by (level, token) -- A1 and A2 are separate
                    # courses (separate Lexeme rows are fine/expected even
                    # for a token spelled the same in both), so a bare
                    # token key would wrongly merge/skip an A2 occurrence
                    # into an A1 spec already seen.
                    key = (level, token)
                    existing = specs.get(key)
                    if existing is None:
                        specs[key] = {
                            "level": level,
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "en",
                            "part_of_speech": EN_POS[token],
                            "english_gloss": EN_TARGET_TO_FA_GLOSS[token],
                            "agreement_tags": tags,
                        }
                    else:
                        for tag_key, value in tags.items():
                            if tag_key == "semantic":
                                prior = existing["agreement_tags"].setdefault(tag_key, [])
                                prior.extend(v for v in value if v not in prior)
                            else:
                                existing["agreement_tags"].setdefault(tag_key, value)


def iter_specs():
    specs: dict[tuple[str, str], dict] = {}
    _classify(UNIT_FILES, "a1", specs)
    _classify(UNIT_FILES_A2, "a2", specs)
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
        for level, title in (("a1", "انگلیسی A1"), ("a2", "انگلیسی A2")):
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
