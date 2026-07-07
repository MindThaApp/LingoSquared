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
    "وقت": "appointment; time slot", "مدرک": "document",
    "آدرس": "address", "قبض": "utility bill", "ملی": "national",
    "برای": "for", "تغییر": "change",
    "بگیرم": "let me take/get (subjunctive)",
    "خونه‌مو": "my house (object marker)",
    "عوض": "change; exchange (in عوض کردن)", "کردم": "I did",
    "آدرسمو": "my address (object marker)",
    "می‌شه": "would it be possible", "بگید": "tell (polite imperative)",
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
}

FA_SYMBOLS = set("س ل ا م ن ت ش چ ی ه ک گ ج د ر ف و ب خ ز".split())
FA_PROPER_NOUNS = set(
    "علی نرگس سارا مینا ایران انگلیس فرانسه آزادی رضا تهران نگار آرش".split()
)
FA_PRONOUNS = set("من تو شما او ما این همون چی چه کی همین".split())
FA_PREPOSITIONS = set("به از با اهل بهت مثل کنار برای برات پیش".split())
FA_PARTICLES = set("هم ولی بله و آره پس تا یه یا چون رو خب چشم".split())
FA_ADVERBS = set(
    "فعلاً خیلی چطور کجا اینجا همین‌طور کجایی باهم فردا حتماً خودمونی چند "
    "اونجا مستقیم بعد لطفاً امروز الان کیلویی نقدی زیادی بیشتر چرا".split()
)
FA_ADJECTIVES = set(
    "خوبی بد ایرانی انگلیسی فرانسوی بزرگه کوچیکه متأهل مجرد برعکسه شلوغه "
    "آفتابی بارونی ابری برفی گرم سرد خنک نزدیک خوشمزه ملی قدیم جدید موافق".split()
)
FA_NUMBERS = set(
    "صفر یک دو سه چهار پنج شش هفت هشت نه ده یازده دوازده سیزده چهارده "
    "پانزده شانزده هفده هجده نوزده بیست سی چهل پنجاه شصت هفتاد هشتاد نود"
    .split()
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
}
FA_PHRASE_PARTS = {"بخیر", "خواهش"}

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


def fa_agreement_tags(token: str, lesson_key: str) -> dict[str, object]:
    semantics: list[str] = []
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
    if token in FA_PRONOUNS:
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
    if token in FA_NUMBERS or token in {"چنده", "شماره", "تلفن", "تلفنتون", "تلفنت", "شماره‌ام"}:
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
    if semantics:
        tags["semantic"] = list(dict.fromkeys(semantics))
    person = {
        "من": "first", "هستم": "first", "ایرانی‌ام": "first",
        "تو": "second", "شما": "second", "هستی": "second",
        "هستید": "second", "هستین": "second", "او": "third",
        "هست": "third", "است": "third", "ایرانیه": "third",
    }.get(token)
    if person:
        tags["person"] = person
    if token in {"من", "تو", "او"}:
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
                gloss = teaching_overlays[content_key].get("gloss", "")
                for token in item.get("introduced_tokens", []):
                    if token not in FA_GLOSSES:
                        raise ValueError(f"missing explicit Farsi gloss for {token!r}")
                    tags = fa_agreement_tags(token, lesson_key)
                    key = (level, token)
                    existing = fa_specs.get(key)
                    if existing is None:
                        fa_specs[key] = {
                            "level": level,
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "fa",
                            "part_of_speech": fa_part_of_speech(token),
                            "english_gloss": FA_GLOSSES[token], "agreement_tags": tags,
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
                if len(introduced) > 1 and target_text and "\n" not in target_text:
                    tags = fa_agreement_tags(target_text, lesson_key)
                    fa_specs.setdefault(
                        (level, target_text),
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
        for level, title in (("a1", "Farsi A1"), ("a2", "Farsi A2")):
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
