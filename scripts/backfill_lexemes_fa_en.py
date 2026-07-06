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
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit25_bureaucracy.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit25.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit26_opinions.yaml",
        REPO_ROOT / "docs/content/overlays/fa-en/a2_unit26.yaml",
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
}


def iter_specs():
    specs: dict[str, dict] = {}
    for unit_order, (realization_path, _overlay_path) in enumerate(UNIT_FILES, 1):
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
                    existing = specs.get(token)
                    if existing is None:
                        specs[token] = {
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "en",
                            "part_of_speech": EN_POS[token],
                            "english_gloss": EN_TARGET_TO_FA_GLOSS[token],
                            "agreement_tags": tags,
                        }
                    else:
                        for key, value in tags.items():
                            if key == "semantic":
                                prior = existing["agreement_tags"].setdefault(key, [])
                                prior.extend(v for v in value if v not in prior)
                            else:
                                existing["agreement_tags"].setdefault(key, value)
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
        course = db.scalar(
            select(Course).where(
                Course.source_language == "fa",
                Course.target_language == "en",
                Course.title == "انگلیسی A1",
            )
        )
        if course is None:
            print("ERROR: fa-en 'انگلیسی A1' course must be imported first", file=sys.stderr)
            return 1

        lessons = {
            (unit.order, lesson.order): lesson
            for unit in db.scalars(select(Unit).where(Unit.course_id == course.id))
            for lesson in db.scalars(select(Lesson).where(Lesson.unit_id == unit.id))
        }
        created = 0
        updated = 0
        for spec in specs:
            lesson = lessons.get((spec.pop("unit_order"), spec.pop("lesson_order")))
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
