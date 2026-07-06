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
    "وعلیکم": "and upon you", "خوش": "pleasant; happy", "آمدید": "you came (polite)",
    "تشکر": "thanks", "خواهش": "request; kindness", "می‌کنم": "I do",
    "خدا": "God", "حافظ": "protector", "صبح": "morning", "بخیر": "well; good",
    "روز": "day", "عصر": "afternoon/evening", "شب": "night", "به": "to",
    "امید": "hope", "دیدار": "meeting", "شما": "you (polite)", "چطور": "how",
    "استین": "you are (polite)", "تو": "you (informal)", "استی": "you are (informal)",
    "خوب": "good", "استم": "I am", "جور": "well; fine", "بد": "bad",
    "نیستم": "I am not", "و": "and", "همه": "everyone; all", "استند": "they are",
    "فامیل‌تان": "your family", "است": "is", "اهل": "from; originally of",
    "خانه": "house", "شکر": "thank God; thanks", "زنده": "alive; long (may you live)",
    "باشین": "may you be (polite)", "خانهٔ": "house of", "خودتان": "yourself",
    "بالا": "up; upstairs", "بفرمایید": "please, go ahead", "اول": "first",
    "بزرگ‌ترها": "elders", "می‌کنیم": "we do", "دفتر": "office", "کابل": "Kabul",
    "حامد": "Hamed (name)", "من": "I", "همکار": "colleague", "نو": "new",
    "نجیب": "Najib (name)", "آمدین": "you came (informal, contracted)",
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
    "بدهید": "give (polite imperative, in the 'allow me to...' construction)",
    "اجازه": "permission", "همکارم": "my colleague",
    "فریدون": "Faridun (name)", "نامت": "your name (informal)",
    "هرات": "Herat (city)", "مزار": "Mazar (part of Mazar-i-Sharif)",
    "شریف": "Sharif (part of Mazar-i-Sharif)", "افغانستان": "Afghanistan",
    "شهر": "city", "کار": "work; job", "داکتر": "doctor",
    "معلم": "teacher", "مهندس": "engineer", "دوکاندار": "shopkeeper",
    "آرزو": "Arezoo (name)", "دوست": "friend", "جناب": "Mr.; sir",
    "خانم": "Ms.; Mrs.", "نزدیک": "close; near",
    "می‌توانید": "you can (polite)", "دوباره": "again",
    "بگویید": "say (polite imperative)", "مهمانی": "party; gathering",
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
    "کجاست": "where is (it)?", "ببخشید": "excuse me", "دور": "far",
    "این‌جا": "here", "آن‌جا": "there", "در": "at (preposition)",
    "کنار": "side; beside", "پشت": "behind", "مقابل": "opposite",
    "زیاد": "much; a lot", "نیست": "is not", "مستقیم": "straight",
    "بروید": "go (polite imperative)", "بعد": "after; then",
    "رهگذر": "passerby", "زرمینه": "Zarmina (name)",
    "قابلی": "worth (in \"don't mention it\")", "نداره": "doesn't have (spoken)",
    # Unit 6 (giving directions and finding your way), added 2026-07-06.
    "چپ": "left", "راست": "right", "بپیچید": "turn (polite imperative)",
    "به": "to / toward", "بروم": "I go (subjunctive)",
    "فهمیدم": "I understood", "از": "from", "روبه‌رو": "opposite / across",
    "روبه‌روی": "across from (construct form)", "شماست": "is yours (polite)",
    "بسیار": "very", "خوب": "good", "سهیلا": "Sohaila (name)",
    "دکاندار": "shopkeeper", "سفر": "trip; journey", "خوش": "happy; pleasant",
    # Unit 7 (talking on the phone), added 2026-07-06.
    "الو": "hello (on the phone)", "کی": "who", "صحبت": "talk; speech",
    "می‌کند": "does / is doing", "فرید": "Farid (name)", "لطفاً": "please",
    "آهسته": "slowly", "کنید": "do (polite imperative)", "پیام": "message",
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
    "آمدین": "you came (informal)", "میل": "desire / preference",
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
    "بیاورید": "bring (polite imperative)", "ثبت": "registration",
    "آخر": "end", "ماه": "month", "می‌آورم": "I bring",
    "خدمتی": "service", "می‌توانم": "I can / may I",
    "برایتان": "for you (polite)", "انجام": "performance; carrying out",
    "بدهم": "let me give / do", "کارمند": "clerk; employee",
    "کریم": "Karim (name)", "خانهٔ": "house of (construct form)",
    "جدید": "new", "زندگی": "life; living", "می‌کنید": "you do",
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
}

PRS_POS: dict[str, str] = {
    "ا": "symbol", "ب": "symbol", "ت": "symbol", "د": "symbol", "ر": "symbol",
    "ز": "symbol", "س": "symbol", "ش": "symbol", "ص": "symbol", "ج": "symbol",
    "چ": "symbol", "ح": "symbol", "خ": "symbol", "ع": "symbol", "غ": "symbol",
    "ف": "symbol", "ق": "symbol", "ک": "symbol", "گ": "symbol", "ل": "symbol",
    "م": "symbol", "ن": "symbol", "و": "particle", "ه": "symbol", "ی": "symbol",
    "سلام": "noun", "علیکم": "particle", "وعلیکم": "particle", "خوش": "adjective",
    "آمدید": "verb", "تشکر": "noun", "خواهش": "noun", "می‌کنم": "verb",
    "خدا": "noun", "حافظ": "noun", "صبح": "noun", "بخیر": "adjective",
    "روز": "noun", "عصر": "noun", "شب": "noun", "به": "preposition",
    "امید": "noun", "دیدار": "noun", "شما": "pronoun", "چطور": "adverb",
    "استین": "verb", "تو": "pronoun", "استی": "verb", "خوب": "adjective",
    "استم": "verb", "جور": "adjective", "بد": "adjective", "نیستم": "verb",
    "همه": "pronoun", "استند": "verb", "فامیل‌تان": "noun", "است": "verb",
    "اهل": "preposition", "خانه": "noun", "شکر": "noun", "زنده": "adjective",
    "باشین": "verb", "خانهٔ": "noun", "خودتان": "pronoun", "بالا": "adverb",
    "بفرمایید": "verb", "اول": "adverb", "بزرگ‌ترها": "noun", "می‌کنیم": "verb",
    "دفتر": "noun", "کابل": "proper_noun", "حامد": "proper_noun", "من": "pronoun",
    "همکار": "noun", "نو": "adjective", "نجیب": "proper_noun", "آمدین": "verb",
    "نام‌تان": "noun", "چیست": "verb", "نام": "noun", "از": "preposition",
    "آشنایی": "noun", "با": "preposition", "شدم": "verb", "هم": "particle",
    "همکاران": "noun", "را": "particle", "معرفی": "noun", "بسیار": "adverb",
    "این": "pronoun", "میز": "noun",
    # Unit 2 additions, added 2026-07-05.
    "بدهید": "verb", "اجازه": "noun", "همکارم": "noun",
    "فریدون": "proper_noun", "نامت": "noun", "هرات": "proper_noun",
    "مزار": "proper_noun", "شریف": "proper_noun", "افغانستان": "proper_noun",
    "شهر": "noun", "کار": "noun", "داکتر": "noun", "معلم": "noun",
    "مهندس": "noun", "دوکاندار": "noun", "آرزو": "proper_noun",
    "دوست": "noun", "جناب": "noun", "خانم": "noun", "نزدیک": "adjective",
    "می‌توانید": "verb", "دوباره": "adverb", "بگویید": "verb",
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
    "کجاست": "verb", "ببخشید": "verb", "دور": "adjective",
    "این‌جا": "adverb", "آن‌جا": "adverb", "در": "preposition",
    "کنار": "noun", "پشت": "preposition", "مقابل": "preposition",
    "زیاد": "adjective", "نیست": "verb", "مستقیم": "adjective",
    "بروید": "verb", "بعد": "adverb", "رهگذر": "noun",
    "زرمینه": "proper_noun", "قابلی": "noun", "نداره": "verb",
    # Unit 6 (directions), added 2026-07-06.
    "چپ": "noun", "راست": "noun", "بپیچید": "verb", "به": "preposition",
    "بروم": "verb", "فهمیدم": "verb", "از": "preposition",
    "روبه‌رو": "adverb", "روبه‌روی": "preposition", "شماست": "verb",
    "بسیار": "adverb", "خوب": "adjective", "سهیلا": "proper_noun",
    "دکاندار": "noun", "سفر": "noun", "خوش": "adjective",
    # Unit 7 (communication), added 2026-07-06.
    "الو": "particle", "کی": "pronoun", "صحبت": "noun", "می‌کند": "verb",
    "فرید": "proper_noun", "لطفاً": "adverb", "آهسته": "adverb",
    "کنید": "verb", "پیام": "noun", "می‌خواهم": "verb", "بگذارم": "verb",
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
    "رسید": "noun", "کرایه": "noun", "مهلت": "noun", "بیاورید": "verb",
    "ثبت": "noun", "آخر": "noun", "ماه": "noun", "می‌آورم": "verb",
    "خدمتی": "noun", "می‌توانم": "verb", "برایتان": "preposition",
    "انجام": "noun", "بدهم": "verb", "کارمند": "noun",
    "کریم": "proper_noun", "خانهٔ": "noun", "جدید": "adjective",
    "زندگی": "noun", "می‌کنید": "verb", "گذشته": "adjective",
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
}


def prs_agreement_tags(token: str, lesson_key: str) -> dict[str, object]:
    semantics: list[str] = []
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
    if token in {"صبح", "روز", "عصر", "شب"}:
        semantics.append("time_period")
    if token in {"بخیر", "خوش"}:
        semantics.append("good_wish")
    if token in {"خدا", "حافظ", "امید", "دیدار"}:
        semantics.append("farewell")
    if token in {"چطور", "استین", "استی"}:
        semantics.append("wellbeing_question")
    if token in {"خوب", "استم", "جور", "بد", "نیستم", "استند"}:
        semantics.append("wellbeing_answer")
    if token in {"تشکر", "خواهش", "می‌کنم", "بفرمایید", "شکر"}:
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
    if token in {"جناب", "خانم"}:
        semantics.append("title")
    if token in {"دوست", "همکار", "همکارم", "همکاران"}:
        semantics.append("relationship_word")
    if token in {"اجازه", "بدهید", "معرفی", "کنم", "این"} and lesson_key.startswith("prs.a1.unit02.lesson04"):
        semantics.append("introduction_phrase")
    if token in {"می‌توانید", "دوباره", "بگویید", "نزدیک"}:
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
    if token == "بپیچید":
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
    if token in {"بشقاب", "تا"}:
        semantics.append("counting_word")

    # A2 unit 09 (bureaucracy) semantic tags, added 2026-07-06.
    if token in {"وقت", "سند", "آدرس", "تذکره", "شاروالی"}:
        semantics.append("office_word")
    if token in {"رسید", "مهلت"}:
        semantics.append("paperwork_word")

    # A2 unit 10 (opinions) semantic tags, added 2026-07-06.
    if token in {"نظر", "دلیل", "تحصیل", "خارج", "وطن"}:
        semantics.append("opinion_word")
    if token in {"پروین", "احمد"}:
        semantics.append("person_name")

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


def _classify(files, level, specs):
    for unit_order, (realization_path, _overlay_path) in enumerate(files, 1):
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
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
        print(f"Lexeme backfill dry run: {len(specs)} prs.")
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        courses_by_level = {}
        for level, title in (("a1", "Dari A1"), ("a2", "Dari A2")):
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
