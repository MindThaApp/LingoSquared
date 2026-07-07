#!/usr/bin/env python3
"""Idempotently backfill reviewed prs-en A1 lexemes (English target) from
the shared en realization units 1 and 2.

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

from _en_target_lexeme_common import EN_POS, en_agreement_tags  # noqa: E402

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
    "day": "روز", "what": "چه", "is": "است", "what's": "چیست",
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
    "i": "من", "am": "استم", "student": "محصل", "teacher": "آموزگار",
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
    "it's": "این ... است (مخفف it is)", "dollars": "دالر (جمع)",
    "phone": "تیلفون", "number": "نمبر", "market": "بازار",
    "apples": "سیب‌ها", "they're": "دوی ... استند (مخفف they are)",
    "ok": "خیر است؛ باشه", "this": "این", "shop": "دکان",
    "much": "چقدر (در how much)",
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
    "write": "نوشتن", "as": "به حیث", "when's": "کی است (مخفف when is)",
    "birthday": "سالگره", "3rd": "سوم", "opens": "باز می‌شه", "again": "دوباره",
    "open": "باز", "on": "در؛ روی", "9th": "نهم", "great": "خوب است",
    "then": "بعد",
    # Unit 5 (telling the time), added 2026-07-06.
    "time": "وخت", "o'clock": "بجه (ساعتِ تمام)", "half": "نیم",
    "past": "و ... (در بیان وخت)", "quarter": "ربع", "night": "شب",
    "store": "دکان", "in": "در", "closes": "بند می‌شه",
    "does": "(فعل کمکی پرسشی)", "close": "بند کردن",
    # Unit 6 (family members and relationships), added 2026-07-06.
    "mother": "مادر", "father": "پدر", "brother": "برادر", "sister": "خواهر",
    "parents": "والدین", "siblings": "خواهر و برادرها",
    "grandmother": "بی‌بی", "grandfather": "بابه", "aunt": "عمه؛ خاله",
    "uncle": "کاکا؛ ماما", "cousin": "پسرکاکا؛ دخترکاکا (و مشابه)",
    "his": "مالِ او (مذکر)", "her": "مالِ او (مؤنث)",
    "she's": "او ... است (مخفف she is)", "brothers": "برادران",
    "do": "(فعل کمکی پرسشی)", "any": "هیچ", "don't": "(منفیِ فعل کمکی do)",
    "only": "فقط", "child": "بچه", "photo": "عکس", "family": "فامیل",
    "who": "کیا", "just": "فقط؛ همینحالا",
    # Unit 7 (food, drink, and ordering), added 2026-07-06.
    "coffee": "قهوه", "tea": "چای", "water": "آب", "bread": "نان",
    "soup": "شوروا", "salad": "سالاد", "sandwich": "ساندویچ",
    "i'd": "من می‌خواهم (مخفف I would)", "like": "خواستن؛ خوش داشتن (این معنای دوم در Unit 19 استعمال می‌شه)",
    "please": "لطفاً", "anything": "چیزی", "else": "دیگه",
    "that's": "دا ... است (مخفف that is)", "all": "بس", "for": "به خاطر",
    "here": "اینجا", "or": "یا", "go": "رفتن؛ بردن (بیرون‌بر)",
    "menu": "مینو", "price": "قیمت", "cafe": "کیفی", "3": "سه",
    "2": "دو", "5": "پنج", "6": "شش", "sure": "البته",
    # Unit 8 (shopping: prices and quantities), added 2026-07-06.
    "pound": "پوند (واحد وزن)", "of": "از", "dozen": "درجن",
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
    "park": "پارک", "restaurant": "رستورانت", "next": "پهلوی (در next to)",
    "across": "مقابل (در across from)", "from": "از",
    "between": "بین", "behind": "عقب", "front": "پیشروی (در in front of)",
    "where": "کجا", "far": "دور", "excuse": "ببخشین (در excuse me)",
    "me": "مره (من را)",
    # Unit 10 (asking for and following directions), added 2026-07-06.
    "turn": "پیچیدن", "left": "چپ", "right": "راست", "straight": "مستقیم",
    "stop": "توقف کردن", "corner": "کنج سرک؛ چوک", "get": "رسیدن (در get to)",
    "minutes": "دقیقه‌ها", "can't": "نمی‌تانم؛ نمی‌تانه (نی‌تانستن)",
    "miss": "گم کردن (در can't miss it)", "take": "گرفتن (در take the street)",
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
    "rain": "باران", "saturday": "شنبه", "let's": "بیایید (پیشنهاد مشترک)",
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
    "i'll": "من ... خواهم (مخفف I will)", "we": "ما",
    # Unit 13 (talking about feelings), added 2026-07-06.
    "happy": "خوش", "sad": "خفه؛ غمگین", "tired": "خسته",
    "excited": "شوق‌مند؛ هیجان‌زده", "worried": "خفه؛ پریشان",
    "feeling": "احساس", "little": "کمی (در a little)", "because": "چون",
    "big": "مهم؛ کلان", "test": "امتحان", "class": "صنف",
    "almost": "تقریباً", "over": "ختم شدن (در almost over)", "year": "سال",
    "last": "آخرین", "writer": "نویسنده", "oh": "آه", "understand": "فهمیدن",
    # Unit 14 (phone calls and messages), added 2026-07-06.
    "free": "وقت‌دار؛ آزاد", "tonight": "امشب", "sorry": "ببخشین",
    "repeat": "تکرار کردن", "that": "آن؛ دا", "speak": "گپ زدن",
    "more": "بیشتر", "slowly": "آهسته", "hear": "شنیدن",
    "well": "خوب (در hear well)", "6pm": "ساعت شش شام",
    "message": "پیام", "suggest": "پیشنهاد کردن", "meeting": "دیدار؛ ملاقات",
    "place": "جای", "about": "دربارهٔ",
    # Unit 15 (handling money and payments), added 2026-07-06. Glosses
    # cross-checked against docs/content/overlays/prs-en/a1_unit15.yaml's
    # own real Dari phrasing (cash=پیسهٔ نقد، credit card=کارت اعتباری،
    # debit card=کارت بانکی -- genuinely distinct Afghan Dari usage, not
    # a copy of the fa-en script's Farsi).
    "cash": "پیسهٔ نقد", "card": "کارت", "credit": "اعتباری (در credit card)",
    "debit": "بانکی؛ مستقیم (در debit card)", "total": "جمع کل",
    "cards": "کارت‌ها", "pay": "پرداخت کردن", "tax": "مالیه",
    "10": "ده", "by": "با (در pay by card)", "1": "یک",
    # Unit 16 (describing a daily routine), added 2026-07-06. Overlay
    # renders "wake up"/"get dressed"/"go to bed" as multi-word Dari
    # phrases (بیدار شدن/کالا پوشیدن/به بستر رفتن) -- each single-token
    # gloss below reflects only that token's own contribution.
    "wake": "بیدار شدن (در wake up)", "up": "بیدار شدن (جزء wake up)",
    "dressed": "کالا پوشیدن (در get dressed)", "dinner": "شب چاشت",
    "bed": "بستر (در go to bed)", "every": "هر", "usually": "معمولاً",
    "breakfast": "صبح‌چاشت", "after": "بعد از",
    # Unit 17 (making simple plans), added 2026-07-06.
    "want": "خواستن (در Do you want to)", "movie": "فلم",
    "weekend": "آخر هفته", "would": "میل داشتن (در Would you like to)",
    "walk": "قدم زدن", "love": "خیلی خوش شدن (در I'd love to)",
    "busy": "مصروف", "maybe": "شاید", "another": "دیگه",
    "lunch": "چاشت", "1pm": "ساعت یک بعد از چاشت",
    "works": "مناسب/خوب بودن (در {day} works for me)",
    # Unit 18 (describing a recent event), added 2026-07-06.
    "went": "رفت (زمان گذشتهٔ go)", "saw": "دید (زمان گذشتهٔ see)",
    "ate": "خورد (زمان گذشتهٔ eat)",
    "visited": "به دیدن رفت (زمان گذشتهٔ visit)",
    "worked": "کار کرد (زمان گذشتهٔ work)",
    "did": "(فعل کمکی پرسشی گذشته، در What did you do)",
    "yesterday": "دیروز", "together": "با هم",
    "watched": "تماشا کرد (زمان گذشتهٔ watch)",
    "writer's": "مالِ نویسنده", "s": "(علامت مالکیت 's)",
    "was": "بود (زمان گذشتهٔ is/am)", "week": "هفته",
    # Unit 19 (expressing likes and preferences), added 2026-07-06. "hate"
    # confirmed against the overlay's own corrected Dari (نفرت داشتن، not
    # a Farsi-style بدبین بودن).
    "prefer": "ترجیح دادن", "hate": "نفرت داشتن", "calmer": "آرام‌تر",
    "very": "خیلی (در very much)", "strong": "تُند (در too strong)",
    "why": "چرا", "think": "فکر کردن",
    "prefers": "ترجیح می‌ته (سوم شخص مفرد)",
    "thinks": "فکر می‌کنه (سوم شخص مفرد)",
    # Unit 20 (making basic comparisons), added 2026-07-06.
    "bigger": "کلان‌تر", "smaller": "خُرد‌تر", "cheaper": "ارزان‌تر",
    "expensive": "قیمتی (در more expensive: قیمتی‌تر)", "faster": "تیزتر",
    "than": "از (در مقایسه، مثلاً X از Y ...تره)", "nicer": "قشنگ‌تر",
    "cheapest": "ارزان‌ترین", "red": "سرخ", "car": "موتر", "white": "سفید",
    # Units 21-24 (A1: travel, health, work, housing) + 25-26 (A2:
    # bureaucracy, opinions), added 2026-07-06. Atomic per-token
    # glosses -- cross-checked against, but not copy-pasted from, each
    # unit's own (phrase-level) Dari overlay glosses
    # (docs/content/overlays/prs-en/a1_unit21.yaml through a2_unit26.yaml).
    "ticket": "تکت", "platform": "سکو", "train": "ریل",
    "departure": "حرکت", "arrival": "رسیدن", "boston": "بوستون",
    "way": "طرف (در one way یعنی یک‌طرفه)",
    "round": "دوطرفه (در round trip)", "trip": "سفر",
    "leaves": "حرکت می‌کنه (فعل، سوم‌شخص مفرد leave)", "9:15": "۹:۱۵",
    "arrives": "می‌رسه (فعل، سوم‌شخص مفرد arrive)", "11:30": "۱۱:۳۰",
    "arrive": "رسیدن (فعل)",
    "headache": "سردردی", "stomachache": "معده‌درد", "fever": "تب",
    "cough": "سرفه", "sore": "دردناک (در sore throat یعنی گلودردی)",
    "throat": "گلو", "wrong": "تکلیف (در What's wrong)",
    "feel": "احساس کردن", "rest": "استراحت کردن",
    "need": "ضرورت داشتن", "doctor": "داکتر",
    "look": "معلوم شدن (در look well)", "drink": "نوشیدن", "if": "اگه",
    "doesn't": "(منفیِ فعل کمکی does)", "better": "بهتر",
    "nurse": "نرس", "cook": "آشپز", "driver": "دریور",
    "patients": "مریض‌ها", "help": "کمک کردن", "reports": "راپورها",
    "interesting": "جالب", "company": "شرکت", "downtown": "مرکز شهر",
    "answer": "جواب دادن (در answer emails)", "emails": "ایمیل‌ها",
    "sometimes": "بعضی وقت‌ها", "with": "با", "clients": "مشتری‌ها",
    "job": "وظیفه",
    "bedroom": "اتاق خواب", "kitchen": "آشپزخانه", "bathroom": "تشناب",
    "living": "نشیمن (در living room)", "room": "اتاق",
    "garden": "باغچه", "many": "چند (در how many)", "rooms": "اتاق‌ها",
    "there": "آنجا (در there is/there are: موجود بودن)",
    "there's": "... هست (مخفف there is)", "apartment": "آپارتمان",
    "has": "داره", "bedrooms": "اتاق‌خواب‌ها", "favorite": "پسندیده",
    "tell": "گفتن", "isn't": "نیست (مخفف is not)", "balcony": "بالکن",
    "upstairs": "منزل بالا", "near": "نزدیک", "easy": "آسان",
    "eat": "خوردن",
    "appointment": "ملاقات", "document": "سند",
    "proof": "سند؛ ثبوت (در proof of residency)", "residency": "اقامت",
    "form": "فورم", "confirmation": "تأیید",
    "wondering": "می‌خواستم بدانم (در I was wondering)", "whether": "آیا",
    "could": "می‌تانستم/می‌تانین", "make": "گرفتن (در make an appointment)",
    "possible": "ممکن", "come": "آمدن", "update": "به‌روز کردن",
    "address": "آدرس", "moved": "کوچ کدم (زمان گذشتهٔ move)",
    "id": "تذکره؛ کارت شناسایی",
    "utility": "خدمات شهری (در utility bill)", "bill": "بل",
    "bring": "آوردن", "such": "مثل (در such as)",
    "lived": "زندگی کده‌ام (زمان گذشتهٔ live)",
    "since": "از (زمان مشخص)", "lease": "قرارداد کرایه",
    "when": "کِی", "10am": "ساعت ۱۰ صبح", "4471": "۴۴۷۱",
    "opinion": "نظر", "other": "دیگه (در on the other hand)",
    "hand": "دست (در on the other hand یعنی از طرف دیگه)",
    "agree": "موافق بودن", "dog": "سگ", "dogs": "سگ‌ها", "space": "فضا",
    "run": "دویدن", "playground": "زمین بازی",
    "fair": "منصفانه (در fair point)", "point": "نکته", "they": "آنها",
    "move": "جابه‌جا کردن", "farther": "دورتر",
    "away": "دور (در move away)",
    # Unit 27 (A2: opening a bank account), added 2026-07-07. Atomic per-
    # token glosses -- cross-checked against, but not a find-replace of,
    # docs/content/overlays/prs-en/a2_unit27.yaml's own (phrase-level)
    # Dari glosses. "debit"/"card"/"i'll"-style contraction pattern reuse
    # their existing Unit 15/12 senses unchanged. Some genuinely distinct
    # Afghan Dari vocabulary here vs the fa-en script's Farsi (fee=معاش
    # not کارمزد, DMV=ادارهٔ ترافیک not ادارهٔ راهنمایی و رانندگی, 500=
    # پنجصد not پانصد -- all cross-checked against the actual prs-en
    # overlay text, not copied from the fa-en dict).
    "checking": "جاری (در checking account)", "account": "حساب",
    "monthly": "ماهانه", "fee": "معاش (کارمزد بانک)", "minimum": "حداقل",
    "balance": "مانده", "direct": "مستقیم (در direct deposit)",
    "deposit": "واریز", "documents": "اسناد (جمع)",
    "you'll": "شما ... ضرورت دارین (مخفف you will)",
    "dmv": "ادارهٔ ترافیک",
    "business": "کاری (در business days یعنی روزهای کاری)",
    "days": "روزها", "keep": "نگه داشتن", "500": "پنجصد",
    "sounds": "به‌نظر می‌رسه (در that sounds good)",
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
    "i've": "... دارم (مخفف I have، همرنگ سه ورز می‌شه که ... دارم)",
    "had": "داشتم (زمان گذشتهٔ have)", "early": "زودتر",
    "confirmed": "تأیید شده (است)", "3pm": "ساعت سه بعد از چاشت",
    "7724": "۷۷۲۴", "twice": "دو مرتبه",
    "plenty": "زیاد (در plenty of water: آب زیاد)",
    "back": "باز (در come back: باز آمدن)",
    "within": "تا (در within a week: تا یک هفته)",
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
    "leaking": "چکیدن", "sink": "نل", "building": "بلاک", "manager": "مدیر",
    "plumber": "پایپ‌کار", "repair": "ترمیم", "report": "خبر دادن",
    "problem": "مشکل", "been": "بوده (در ساختار ماضی نقلی)",
    "someone": "یک کس؛ کسی", "fix": "ترمیم کدن",
    "2pm": "ساعت ۲ بعد از چاشت", "4pm": "ساعت ۴ بعد از چاشت",
    "received": "دریافت شده (است)", "6180": "۶۱۸۰", "send": "فرستادن",
    "home": "خانه", "here's": "همینه (این است، در معرفی چیزی)",
}


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
                    # courses, so a bare token key would wrongly merge
                    # an A2 occurrence into an A1 spec already seen.
                    key = (level, token)
                    existing = specs.get(key)
                    if existing is None:
                        specs[key] = {
                            "level": level,
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "en",
                            "part_of_speech": EN_POS[token],
                            "english_gloss": EN_TARGET_TO_PRS_GLOSS[token],
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
