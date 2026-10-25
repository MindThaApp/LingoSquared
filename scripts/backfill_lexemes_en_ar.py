#!/usr/bin/env python3
"""Idempotently backfill en-ar (Arabic target) lexemes for the "Arabic A1"
course, so en-ar practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: en->X backfill for Arabic (Modern Standard Arabic).
All plumbing lives in scripts/_target_lexeme_backfill_common.py (see its
docstring for the tag scheme); this file is data only: one hand-written
English gloss and one part of speech per citation form.

Scope: A1 (the "en-ar-a1" manifest group, units 01-24) and A2 (the
"en-ar-a2" group, units 25-34, added 2026-10-24 in session 11) and B1 (the
"en-ar-b1" group, units 35-53, added 2026-10-25 in session 12). A2 and B1 are
separate Course rows, so their lexemes are first-sight per course and carry
their own gloss and part-of-speech tables (GLOSSES_A2, POS_SETS_A2,
B1_ENTRIES). The B1 course must be imported before this script runs;
otherwise it exits with a clear error (see run()). B2+ is not classified yet;
extend LEVELS and the tables together.

Normalization: Arabic has no case, so normalize() is the identity. The
A1 realizations are written without harakat (short-vowel marks) and the
introduced_tokens contain no word spelled both with and without harakat or
with variant hamza/alef forms (checked: stripping harakat and folding
hamza/alef/yeh/teh-marbuta variants produces no collisions among the 240
tokens), so no citation-form mapping is needed. If a later unit mixes
spellings, map them to ONE undiacritized form in CITATION_FORMS below
(grading strips harakat anyway; display stays undiacritized). Genuinely
different words that merely look alike (e.g. the verb تفضل "you prefer" vs
the phrase تفضلي "here you are") are NOT unified.

Glossing rules followed here (PRACTICE_PACK_RECIPE.md §0.1, §6.6):
* the gloss is the sense the unit actually teaches at first sight,
* second-person forms that differ by gender say "(masc.)"/"(fem.)" where
  the written word is gender-specific, so a bare-word translation prompt
  names one form,
* no Arabic text and no transliteration in a gloss,
* the five letters of the unit 01 script ramp are glossed as letters.

Run (after the en-ar course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_ar.py

Add --dry-run to classify without touching the database.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _target_lexeme_backfill_common import (  # noqa: E402
    classify,
    manifest_group,
    pos_lookup,
    run,
    split_words,
)

LANG = "ar"
LEVELS = {"a1": "en-ar-a1", "a2": "en-ar-a2", "b1": "en-ar-b1"}

# token as written in the realization -> single undiacritized citation form.
# Empty: no A1 word is spelled two ways (see module docstring).
CITATION_FORMS: dict[str, str] = {}


def normalize(token: str) -> str:
    return CITATION_FORMS.get(token, token)


GLOSSES: dict[str, str] = {
    # unit01 greetings
    "م": "the letter m", "ر": "the letter r", "ح": "the letter h (breathy)",
    "ب": "the letter b", "ا": "the letter a (long)",
    "مرحبا": "hello", "صباح": "morning", "الخير": "the good",
    "مساء": "evening; afternoon", "مع": "with", "السلامة": "safety",
    "شكرا": "thank you", "عفوا": "you're welcome",
    "تصبح": "you wake up (masc.)", "على": "on; to", "خير": "good; goodness",
    "أهلا": "welcome", "وسهلا": "and ease", "بك": "with you; to you",
    "إلى": "to; until", "اللقاء": "the meeting", "النور": "the light",
    "يوما": "day (in a wish)", "سعيدا": "happy (in a wish)",
    "كيف": "how", "حالك": "your condition", "بخير": "fine; well",
    "الحمد": "the praise", "لله": "for God", "وأنت": "and you",
    "ممتاز": "excellent (masc.)", "لا": "no; not", "بأس": "harm",
    # unit02 introductions
    "ما": "what", "اسمك": "your name", "اسمي": "my name", "كريم": "Karim",
    "أنا": "I", "سارة": "Sara", "تشرفنا": "nice to meet you",
    "من": "from; of", "أين": "where", "أنت": "you",
    "لبنان": "Lebanon", "مصر": "Egypt", "الأردن": "Jordan",
    "المغرب": "Morocco", "سوريا": "Syria", "العراق": "Iraq",
    "هل": "(starts a yes-or-no question)", "نعم": "yes",
    "سعدت": "I was pleased", "بلقائك": "at meeting you",
    "يوسف": "Yusuf", "ليلى": "Layla", "دائما": "always",
    # unit03 numbers
    "واحد": "one (masc.)", "اثنان": "two", "ثلاثة": "three", "أربعة": "four",
    "خمسة": "five", "ستة": "six", "سبعة": "seven", "ثمانية": "eight",
    "تسعة": "nine", "عشرة": "ten", "كم": "how much; how many",
    "هذا": "this (masc.)", "رقم": "number", "بخمسة": "for five",
    "وهذا": "and this (masc.)", "بعشرة": "for ten",
    # unit04 dates
    "تاريخ": "date", "اليوم": "today", "مايو": "May", "يونيو": "June",
    "الخامس": "the fifth (masc.)", "السادس": "the sixth (masc.)",
    "درس": "lesson", "الدرس": "the lesson", "في": "in; on",
    # unit05 time
    "الساعة": "the hour; the time", "الثالثة": "the third (fem.)",
    "الخامسة": "the fifth (fem.)", "صباحا": "in the morning",
    "متى": "when", "ومتى": "and when",
    # unit06 family
    "عائلة": "family", "أب": "father", "أم": "mother", "أخ": "brother",
    "أخت": "sister", "وأخت": "and sister", "عندي": "I have",
    "عائلتك": "your family", "اسمها": "her name", "نور": "Nour",
    "يا": "O (calls a person by name)", "وأم": "and mother", "اسم": "name",
    "أختك": "your sister",
    # unit07 food
    "ماء": "water", "قهوة": "coffee", "وقهوة": "and coffee", "خبز": "bread",
    "أريد": "I want", "فضلك": "your favor (in a polite request)",
    "تريدين": "you want (fem.)", "خبزا": "bread (as something wanted)",
    "قطعة": "piece", "واحدة": "one (fem.)", "تفضلي": "here you are (to a woman)",
    # unit08 shopping
    "سعر": "price", "تفاح": "apples", "دراهم": "dirhams",
    "التفاح": "the apples", "تفاحتين": "two apples",
    # unit09 places
    "مكان": "place", "مكتبة": "library", "المكتبة": "the library",
    "سوق": "market", "السوق": "the market", "مقهى": "cafe",
    "المقهى": "the cafe", "هنا": "here", "قرب": "near", "وأين": "and where",
    # unit10 directions
    "يمين": "right (direction)", "يسار": "left (direction)",
    "اليسار": "the left", "الأمام": "the front", "اليمين": "the right",
    "امش": "walk (to a man)", "ثم": "then",
    # unit11 routines
    "كل": "every", "يوم": "day", "أستيقظ": "I wake up",
    "السابعة": "the seventh (fem.)", "أدرس": "I study",
    "التاسعة": "the ninth (fem.)", "أنام": "I sleep",
    "العاشرة": "the tenth (fem.)", "ماذا": "what", "تفعل": "you do (masc.)",
    # unit12 plans
    "غدا": "tomorrow", "نذهب": "we go", "جيد": "good",
    # unit13 past events
    "ذهبت": "I went", "أمس": "yesterday", "اشتريت": "I bought",
    "تفاحا": "apples (as something bought)", "فعلت": "you did",
    "شربت": "I drank",
    # unit14 preferences
    "أحب": "I like", "القهوة": "the coffee", "شاي": "tea", "الشاي": "the tea",
    "الماء": "the water", "ولا": "and not", "أفضل": "I prefer",
    "تفضل": "you prefer (masc.)",
    # unit15 comparisons
    "أكبر": "bigger", "أصغر": "smaller", "أقرب": "closer", "أرخص": "cheaper",
    "والسوق": "and the market",
    # unit16 travel
    "تذكرة": "ticket", "القطار": "the train", "القاهرة": "Cairo",
    "الرصيف": "the platform", "الثاني": "the second (masc.)", "أي": "which",
    "رصيف": "platform",
    # unit17 health
    "ألم": "pain", "الرأس": "the head", "البطن": "the stomach",
    "المشكلة": "the problem", "اشربي": "drink (to a woman)",
    "استريحي": "rest (to a woman)", "أحتاج": "I need", "مساعدة": "help",
    "واستريحي": "and rest (to a woman)",
    # unit18 work
    "عمل": "work", "عملك": "your work", "مهندس": "engineer (masc.)",
    "مكتب": "office", "أعمل": "I work", "أكتب": "I write", "أقرأ": "I read",
    "العمل": "the work", "عملا": "work (object ending)", "وأقرأ": "and I read",
    # unit19 housing
    "بيت": "house", "بيتي": "my house", "غرفة": "room", "مطبخ": "kitchen",
    "طاولة": "table", "الغرفة": "the room", "بيتك": "your house",
    "ومطبخ": "and a kitchen", "عندك": "you have",
    # unit20 weather
    "الجو": "the weather", "مشمس": "sunny", "بارد": "cold", "حار": "hot",
    "هيا": "let's", "نشرب": "we drink", "وحار": "and hot",
    # unit21 clothing
    "ملابس": "clothes", "قميص": "shirt", "قميصا": "shirt (as something wanted)",
    "القميص": "the shirt", "أزرق": "blue (masc.)", "المقاس": "the size",
    "مقاس": "size", "متوسط": "medium", "بمقاس": "in a size",
    # unit22 emotions
    "شعور": "feeling", "سعيد": "happy (masc.)", "سعيدة": "happy (fem.)",
    "حزين": "sad (masc.)", "حزينة": "sad (fem.)", "لأن": "because",
    "تشعر": "you feel (masc.)", "متعب": "tired (masc.)", "متعبة": "tired (fem.)",
    # unit23 communication
    "هاتف": "phone", "أسمعك": "I hear you", "أعد": "repeat (to a man)",
    "تكلم": "speak (to a man)", "ببطء": "slowly", "رسالة": "message",
    "الموعد": "the appointment",
    # unit24 money
    "مال": "money", "أدفع": "I pay", "بطاقة": "card", "بالبطاقة": "by card",
    "سأدفع": "I will pay", "نقدا": "cash", "المبلغ": "the amount",
    "أستطيع": "I can", "الدفع": "paying",
}

POS_SETS = {
    "symbol": split_words("م ر ح ب ا"),
    "proper_noun": split_words(
        "كريم سارة يوسف ليلى نور لبنان مصر الأردن المغرب سوريا العراق القاهرة"
    ),
    "pronoun": split_words("أنا أنت وأنت هذا وهذا ما"),
    "preposition": split_words("مع على إلى بك من في قرب لله"),
    "particle": split_words("لا هل نعم يا ولا ثم لأن هيا"),
    "adjective": split_words(
        "ممتاز سعيدا واحد واحدة الخامس السادس الثالثة الخامسة السابعة التاسعة "
        "العاشرة الثاني أكبر أصغر أقرب أرخص جيد بارد حار مشمس وحار أزرق متوسط "
        "سعيد سعيدة حزين حزينة متعب متعبة بخير أي"
    ),
    "adverb": split_words(
        "كيف أين متى ومتى وأين كم ماذا دائما صباحا هنا غدا أمس ببطء نقدا "
        "اليوم كل"
    ),
    "verb": split_words(
        "تصبح سعدت أريد تريدين امش أستيقظ أدرس أنام تفعل نذهب ذهبت اشتريت "
        "فعلت شربت أحب أفضل تفضل اشربي استريحي واستريحي أحتاج أعمل أكتب أقرأ "
        "وأقرأ نشرب تشعر أسمعك أعد تكلم أدفع سأدفع أستطيع عندي عندك"
    ),
    "phrase": split_words(
        "مرحبا شكرا عفوا أهلا وسهلا تشرفنا تفضلي بلقائك بخمسة بعشرة بمقاس بالبطاقة "
        "اسمي اسمك اسمها"
    ),
}
POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())

CATEGORY_TAGS: dict[str, list[str]] = {}
for _tag, _words in {
    "ar_number": "واحد اثنان ثلاثة أربعة خمسة ستة سبعة ثمانية تسعة عشرة",
    "ar_month": "مايو يونيو",
    "ar_family": "عائلة أب أم أخ أخت وأخت عائلتك وأم أختك",
}.items():
    for _w in _words.split():
        CATEGORY_TAGS.setdefault(_w, []).append(_tag)

part_of_speech = pos_lookup(POS_SETS)


# ---------------------------------------------------------------------------
# A2 (course "Arabic A2", manifest group en-ar-a2, units 25-34). Separate
# tables: A2 is its own Course, so every token is first-sight again and is
# glossed for the sense the A2 unit teaches. Same rules as the A1 table
# above: no Arabic and no transliteration inside a gloss, "(masc.)"/"(fem.)"
# where the written word is gender-specific, the sense taught at first sight.
# The A2 realizations are written without harakat, like A1.
# ---------------------------------------------------------------------------
GLOSSES_A2: dict[str, str] = {
    # unit25 registering an address
    "تسجيل": "registration", "السلطات": "the authorities",
    "التسجيل": "the registration", "استمارة": "form",
    "جواز": "passport (first of two words)", "سفر": "travel (in 'passport')",
    "أحتاج": "I need", "إلى": "to", "موعد": "appointment",
    "يوم": "day", "الثلاثاء": "Tuesday", "الساعة": "the hour; the time",
    "العاشرة": "the tenth (fem.)",
    "صباح": "morning", "الخير": "the good", "كيف": "how",
    "أساعدك": "I help you", "أريد": "I want", "عنواني": "my address",
    "الجديد": "the new (masc.)", "اسمي": "my name", "ليلى": "Layla",
    "حسن": "Hassan (a surname)", "العنوان": "the address",
    "ورقم": "and the number of", "الهاتف": "the phone", "شارع": "street",
    "النور": "the light (in a street name)", "بناية": "building",
    "خمسة": "five", "والعنوان": "and the address", "رقم": "number",
    "صفر": "zero", "سبعة": "seven",
    "هل": "(starts a yes-or-no question)", "الموظف": "the employee (masc.)",
    "ما": "what", "اسمك": "your name", "الكامل": "the full (masc.)",
    "نعم": "yes", "تحتاجين": "you need (fem.)", "وجواز": "and passport",
    "الموعد": "the appointment",
    # unit26 opinions
    "رأي": "opinion", "رأيك": "your opinion", "أعتقد": "I think; I believe",
    "أن": "that (joins a statement to what was said)", "لأن": "because",
    "لأنه": "because it (masc.)", "لأنها": "because it (fem.)",
    "الدرس": "the lesson", "مفيد": "useful (masc.)", "سهل": "easy (masc.)",
    "الحصة": "the class (session)", "هادئ": "quiet; calm (masc.)",
    "هادئة": "quiet; calm (fem.)",
    "الصباحية": "the morning one (fem.)", "الصباح": "the morning",
    "المسائية": "the evening one (fem.)", "أفضل": "better",
    "لا": "no; not", "أوافقك": "I agree with you", "الرأي": "the opinion",
    "أرى": "I think; I see", "تناسب": "it suits (fem.)", "عملي": "my work",
    "أفهم": "I understand", "لكن": "but", "أسهل": "easier", "لي": "for me",
    "في": "in", "أنا": "I",
    # unit27 opening a bank account
    "بنك": "bank", "حساب": "account", "بنكي": "bank (adj., masc.)",
    "بنكية": "bank (adj., fem.)", "فتح": "opening", "إثبات": "proof",
    "وإثبات": "and proof", "عنوان": "address", "عندي": "I have", "و": "and",
    "أهلا": "welcome", "وسهلا": "and ease (in a welcome)", "يوسف": "Yusuf",
    "خوري": "Khoury (a surname)", "بطاقة": "card",
    "مصرفية": "banking (fem.)", "رسوم": "fees", "شهرية": "monthly (fem.)",
    "وهل": "and (starts a question)", "الحساب": "the account",
    "الأساسي": "the basic (masc.)", "أساسي": "basic (masc.)",
    "توجد": "there is (fem.)", "الموظفة": "the employee (fem.)",
    "عندك": "you have", "وعنوانك": "and your address", "يشمل": "includes",
    "ولا": "and not; and no", "للحساب": "for the account",
    # unit28 at the doctor
    "الحلق": "the throat", "ألم": "pain", "منذ": "since; for",
    "ثلاثة": "three", "أيام": "days", "شديد": "severe (masc.)",
    "والألم": "and the pain", "بسيط": "mild (masc.)", "حمى": "fever",
    "وحمى": "and fever", "أيضا": "also", "مشكلتك": "your problem",
    "دواء": "medicine", "الدواء": "the medicine", "مرتين": "twice",
    "اليوم": "the day; today", "كثيرا": "a lot", "ماء": "water",
    "اشربي": "drink (to a woman)", "آخر": "another (masc.)", "بعد": "after",
    "أسبوع": "week", "إذا": "if", "لم": "did not; do not (with a verb)",
    "تتحسني": "you get better (fem.)", "الطبيبة": "the doctor (fem.)",
    "أم": "or (between two options)", "خذي": "take (to a woman)",
    "هذا": "this (masc.)", "واشربي": "and drink (to a woman)",
    "عودي": "come back (to a woman)",
    # unit29 a problem at home
    "تسرب": "leak", "مشكلة": "problem", "المطبخ": "the kitchen",
    "هناك": "there is; there", "متى": "when", "يومين": "two days",
    "تزداد": "it increases (fem.)", "سوءا": "worse",
    "والمشكلة": "and the problem", "فني": "technician",
    "فنيا": "technician (as something sent)", "إصلاح": "repair",
    "المشكلة": "the problem",
    "سنرسل": "we will send", "غدا": "tomorrow", "صباحا": "in the morning",
    "أكون": "I am; I will be", "البيت": "the house; the home",
    "كن": "be (to a man)", "التاسعة": "the ninth (fem.)", "من": "from; of",
    "فضلك": "your favor (in a polite request)", "الإصلاح": "the repair",
    "موجود": "present; there (masc.)", "لإصلاح": "to repair; for the repair of",
    # unit30 a job interview
    "خبرة": "experience", "مجال": "field", "المجال": "the field",
    "عملت": "I worked", "لمدة": "for a period of", "سنتين": "two years",
    "متاحة": "available (fem.)", "وأنا": "and I", "عطلة": "holiday; break",
    "نهاية": "end", "الأسبوع": "the week",
    "لديك": "you have", "أي": "any", "سؤال": "question", "عن": "about",
    "الوظيفة": "the job", "ساعات": "hours", "العمل": "the work",
    "الثامنة": "the eighth (fem.)", "حتى": "until", "الرابعة": "the fourth (fem.)",
    "مساء": "in the evening", "أخبريني": "tell me (to a woman)",
    "خبرتك": "your experience", "المديرة": "the manager (fem.)",
    "نور": "Nour", "للعمل": "for work", "أنت": "you",
    # unit31 a delayed train
    "متأخر": "late; delayed (masc.)", "القطار": "the train", "نصف": "half",
    "ساعة": "hour", "فنية": "technical (fem.)", "بسبب": "because of",
    "قطار": "train", "بديل": "alternative (masc.)", "يوجد": "there is (masc.)",
    "الرصيف": "the platform", "اثنين": "two (in a number)",
    "عشر": "ten (before a plural noun)", "دقائق": "minutes",
    "سيصل": "it will arrive (masc.)", "نفس": "same", "الوقت": "the time",
    "تقريبا": "approximately", "سيتأخر": "it will be late (masc.)",
    "فقط": "only", "عذرا": "sorry; excuse me",
    # unit32 digital life
    "الذكي": "the smart (masc.)", "أستخدم": "I use", "هاتفي": "my phone",
    "يوميا": "daily", "وسائل": "means; media", "التواصل": "communication",
    "الاجتماعي": "the social (masc.)", "لوسائل": "for the media of",
    "ساعتين": "two hours", "حوالي": "about; around", "خاصة": "especially",
    "كم": "how many; how much", "تستخدمين": "you use (fem.)",
    "هاتفك": "your phone", "مفيدة": "useful (fem.)",
    "للتواصل": "for communication", "مع": "with", "الأصدقاء": "the friends",
    "أنها": "that it (fem.)", "تأخذ": "it takes (fem.)",
    "وقتا": "time (as something taken)", "لكنها": "but it (fem.)",
    # unit33 a busy week
    "صالة": "hall", "الرياضة": "the sport", "السادسة": "the sixth (fem.)",
    "أولا": "first", "أذهب": "I go", "ثم": "then", "أطبخ": "I cook",
    "العشاء": "the dinner",
    "ألتقي": "I meet", "بأصدقائي": "with my friends", "وفي": "and in",
    "أزور": "I visit", "عائلتي": "my family", "وأزور": "and I visit",
    "كل": "every",
    # unit34 a complaint
    "إرجاع": "returning (an item)", "القميص": "the shirt", "فيه": "it has; in it",
    "عيب": "defect", "الحجم": "the size", "غير": "not; non-",
    "صحيح": "correct; right (masc.)", "ممزق": "torn (masc.)",
    "قليلا": "a little", "وممزق": "and torn (masc.)",
    "معك": "you have (with you)", "الإيصال": "the receipt",
    "معي": "I have (with me)", "استرداد": "refund", "المال": "the money",
    "استبدال": "exchange", "تريد": "you want (masc.)",
    "البائعة": "the shop assistant (fem.)",
}

POS_SETS_A2 = {
    "proper_noun": split_words("ليلى حسن يوسف خوري نور"),
    "pronoun": split_words("أنا أنت ما هذا"),
    "preposition": split_words(
        "إلى في من منذ عن حتى مع بعد بسبب لمدة لي فيه معك معي لديك عندي عندك "
        "للحساب للعمل للتواصل لوسائل لإصلاح"
    ),
    "particle": split_words(
        "هل وهل أن أنها لأن لأنه لأنها لكن لكنها إذا لم أم و ولا لا نعم أي غير"
    ),
    "adjective": split_words(
        "الجديد الكامل مفيد سهل هادئ هادئة مفيدة بنكي بنكية مصرفية شهرية "
        "الأساسي أساسي شديد بسيط آخر موجود متاحة متأخر فنية بديل الذكي "
        "الاجتماعي صحيح ممزق وممزق العاشرة التاسعة الثامنة الرابعة السادسة "
        "الصباحية المسائية أفضل أسهل"
    ),
    "adverb": split_words(
        "كيف كم متى هناك أيضا كثيرا مرتين يوميا غدا صباحا مساء تقريبا فقط "
        "أولا ثم خاصة حوالي قليلا سوءا عذرا اليوم"
    ),
    "verb": split_words(
        "أساعدك أريد أحتاج تحتاجين أعتقد أرى أوافقك أفهم تناسب توجد يشمل "
        "اشربي واشربي خذي عودي تتحسني تزداد سنرسل أكون كن عملت أخبريني "
        "سيصل سيتأخر أستخدم تستخدمين تأخذ أذهب أطبخ ألتقي أزور وأزور تريد "
        "يوجد"
    ),
    "phrase": split_words("أهلا وسهلا"),
}
POS_SETS_A2["noun"] = set(GLOSSES_A2) - set().union(*POS_SETS_A2.values())

CATEGORY_TAGS_A2: dict[str, list[str]] = {}
for _tag, _words in {
    "ar_number": "خمسة سبعة صفر ثلاثة اثنين عشر",
}.items():
    for _w in _words.split():
        CATEGORY_TAGS_A2.setdefault(_w, []).append(_tag)

part_of_speech_a2 = pos_lookup(POS_SETS_A2)

# B1 (session 12): every token the Arabic B1 course introduces, with its own
# gloss (B1 is a separate Course row, so tokens seen in A1/A2 are re-glossed
# for the sense B1 teaches). Format: token: (part-of-speech code, gloss).
# Codes: n noun, v verb, a adjective, d adverb, r pronoun, p preposition,
# t particle, N proper noun, h phrase. Verb forms say who does the action;
# second-person forms say (masc.)/(fem.); forms that only occur after a
# conditional or negative particle say so.
_B1_POS_CODES = {
    "n": "noun", "v": "verb", "a": "adjective", "d": "adverb",
    "r": "pronoun", "p": "preposition", "t": "particle",
    "N": "proper_noun", "h": "phrase",
}
B1_ENTRIES: dict[str, tuple[str, str]] = {
    'أهلا': ('h', 'hello'),
    'التقرير': ('n', 'the report'),
    'أستطيع': ('v', 'I can'),
    'أن': ('t', 'that; to (links two verbs)'),
    'أكتب': ('v', 'I write'),
    'اليوم': ('d', 'today'),
    'لا': ('t', 'no; not'),
    'هل': ('t', '(starts a yes-or-no question)'),
    'تستطيع': ('v', 'you can (masc.)'),
    'تكتب': ('v', 'you write (masc.)'),
    'غدا': ('d', 'tomorrow'),
    'استطعت': ('v', 'I was able'),
    'أمس': ('d', 'yesterday'),
    'لم': ('t', 'did not (with a verb)'),
    'أستطع': ('v', 'I be able (form used after did not)'),
    'لو': ('t', 'if (unreal condition)'),
    'اتصلت': ('v', 'I called; you called (masc.)'),
    'بي': ('p', 'me (after a preposition)'),
    'لاستطعت': ('v', 'I would be able'),
    'أساعدك': ('v', 'I help you (masc.)'),
    'أكتبه': ('v', 'I write it'),
    'لكن': ('t', 'but'),
    'جزءا': ('n', 'a part'),
    'منه': ('p', 'from it; of it'),
    'نعم': ('t', 'yes'),
    'أنهيه': ('v', 'I finish it'),
    'من': ('p', 'from; of'),
    'فضلك': ('n', 'your favor (in a polite request)'),
    'البلدية': ('n', 'the town hall'),
    'يجب': ('v', 'it is necessary; must'),
    'أذهب': ('v', 'I go'),
    'إلى': ('p', 'to'),
    'تحضري': ('v', 'you bring (fem.)'),
    'كل': ('n', 'all; every'),
    'الأوراق': ('n', 'the papers'),
    'ألا': ('t', 'that not (before a verb)'),
    'تنسي': ('v', 'you forget (fem.)'),
    'جواز': ('n', 'passport (first of two words)'),
    'سفرك': ('n', 'your travel (as in your passport)'),
    'كان': ('v', 'was'),
    'أحضر': ('v', 'I bring'),
    'حسنا': ('d', 'okay; fine'),
    'وأحضر': ('v', 'and I bring'),
    'أيضا': ('d', 'also'),
    'نسيت': ('v', 'I forgot'),
    'المقابلة': ('n', 'the interview'),
    'إذا': ('t', 'if (a real possibility)'),
    'نجحت': ('v', 'I succeed (after if)'),
    'في': ('p', 'in'),
    'فسأسافر': ('v', 'then I will travel'),
    'سأسافر': ('v', 'I will travel'),
    'دبي': ('N', 'Dubai'),
    'ماذا': ('r', 'what'),
    'ستفعلين': ('v', 'you will do (fem.)'),
    'كنت': ('v', 'I was'),
    'غنية': ('a', 'rich (fem.)'),
    'لسافرت': ('v', 'I would travel'),
    'حول': ('p', 'around'),
    'العالم': ('n', 'the world'),
    'الامتحان': ('n', 'the exam'),
    'ذاكرت': ('v', 'I studied (for an exam)'),
    'أكثر': ('d', 'more'),
    'لكنت': ('v', 'I would be'),
    'عندك': ('p', 'you have (masc.)'),
    'مقابلة': ('n', 'interview'),
    'عمل': ('n', 'work'),
    'للعمل': ('p', 'for work'),
    'وماذا': ('r', 'and what'),
    'تنجحي': ('v', 'you succeed (fem.)'),
    'أنجح': ('v', 'I succeed'),
    'لبحثت': ('v', 'I would look'),
    'عن': ('p', 'about; for'),
    'وظيفة': ('n', 'job (position)'),
    'أخرى': ('a', 'another (fem.)'),
    'هنا': ('d', 'here'),
    'أعتقد': ('v', 'I think; I believe'),
    'أفضل': ('a', 'better'),
    'العمل': ('n', 'the work'),
    'المنزل': ('n', 'the home'),
    'المكتب': ('n', 'the office'),
    'أوافقك': ('v', 'I agree with you'),
    'الرأي': ('n', 'the opinion'),
    'لأن': ('t', 'because'),
    'أسهل': ('a', 'easier'),
    'التركيز': ('n', 'the focus'),
    'الاجتماعات': ('n', 'the meetings'),
    'القصيرة': ('a', 'the short (fem.)'),
    'الطويلة': ('a', 'the long (fem.)'),
    'المواضيع': ('n', 'the topics'),
    'المهمة': ('a', 'the important (fem.)'),
    'تحتاج': ('v', 'it needs (fem.)'),
    'وقتا': ('n', 'time (as something needed)'),
    'أطول': ('a', 'longer'),
    'أنا': ('r', 'I'),
    'مسؤول': ('a', 'responsible (masc.)'),
    'أنت': ('r', 'you (masc.)'),
    'مسؤولة': ('a', 'responsible (fem.)'),
    'هذا': ('r', 'this (masc.)'),
    'انتهيت': ('v', 'I finished'),
    'الجزء': ('n', 'the part'),
    'الأول': ('a', 'the first (masc.)'),
    'ما': ('t', '(in the phrase for still) not'),
    'زلت': ('v', 'I still am (after the word for not)'),
    'أعمل': ('v', 'I work'),
    'على': ('p', 'on; at'),
    'الثاني': ('a', 'the second (masc.)'),
    'يمكنك': ('v', 'you are able to (masc.)'),
    'مساعدتي': ('n', 'helping me'),
    'بينما': ('t', 'while'),
    'أنتظر': ('v', 'I wait'),
    'الحافلة': ('n', 'the bus'),
    'قابلت': ('v', 'I met'),
    'صديقتي': ('n', 'my friend (fem.)'),
    'القديمة': ('a', 'the old (fem.)'),
    'ثم': ('d', 'then'),
    'ذهبنا': ('v', 'we went'),
    'مقهى': ('n', 'cafe'),
    'تحدثنا': ('v', 'we talked'),
    'كثيرا': ('d', 'a lot'),
    'هناك': ('d', 'there'),
    'حدث': ('v', 'it happened'),
    'قالت': ('v', 'she said'),
    'لي': ('p', 'to me'),
    'إن': ('t', 'that (after said)'),
    'إنها': ('t', 'that she (after said)'),
    'ستنتقل': ('v', 'she will move'),
    'مدينة': ('n', 'city'),
    'أمطرت': ('v', 'it rains (after if)'),
    'سنبقى': ('v', 'we will stay'),
    'البيت': ('n', 'the house'),
    'فسنبقى': ('v', 'then we will stay'),
    'تمطر': ('v', 'it rains (after did not)'),
    'سنذهب': ('v', 'we will go'),
    'الحديقة': ('n', 'the park'),
    'فسنذهب': ('v', 'then we will go'),
    'نهاية': ('n', 'end'),
    'الأسبوع': ('n', 'the week'),
    'أستيقظ': ('v', 'I wake up'),
    'عندما': ('t', 'when'),
    'أشرب': ('v', 'I drink'),
    'القهوة': ('n', 'the coffee'),
    'استيقظت': ('v', 'I woke up'),
    'نور': ('N', 'Nour'),
    'بنور': ('p', 'to Nour'),
    'بعد': ('p', 'after'),
    'أنام': ('v', 'I sleep'),
    'قبل': ('p', 'before'),
    'قرأت': ('v', 'I read'),
    'كتابا': ('n', 'a book'),
    'تفعل': ('v', 'you do (masc.)'),
    'تستيقظ': ('v', 'you wake up (masc.)'),
    'فعلت': ('v', 'you did (masc.)'),
    'بك': ('p', 'to you (masc.)'),
    'عملت': ('v', 'she worked'),
    'المجال': ('n', 'the field'),
    'لمدة': ('p', 'for a period of'),
    'سنتين': ('n', 'two years'),
    'عطلة': ('n', 'holiday'),
    'المديرة': ('n', 'the manager (fem.)'),
    'سألت': ('v', 'she asked'),
    'كانت': ('v', 'she was'),
    'متاحة': ('a', 'available (fem.)'),
    'سألتها': ('v', 'she asked her'),
    'أدرس': ('v', 'I study'),
    'الإنجليزية': ('n', 'English'),
    'لكي': ('t', 'in order to'),
    'أسافر': ('v', 'I travel'),
    'الخارج': ('n', 'abroad'),
    'يوم': ('n', 'day'),
    'أذاكر': ('v', 'I study (for exams)'),
    'حتى': ('t', 'until; so that'),
    'تدرس': ('v', 'you study (masc.)'),
    'لماذا': ('d', 'why'),
    'تذاكر': ('v', 'you study for exams (masc.)'),
    'ولماذا': ('d', 'and why'),
    'متعبة': ('a', 'tired (fem.)'),
    'جدا': ('d', 'very'),
    'هذه': ('r', 'this (fem.)'),
    'الأيام': ('n', 'the days'),
    'مكانك': ('n', 'your place'),
    'لأخذت': ('v', 'I would take'),
    'إجازة': ('n', 'leave; time off'),
    'قصيرة': ('a', 'short (fem.)'),
    'أخذ': ('n', 'taking'),
    'الآن': ('d', 'now'),
    'تنامين': ('v', 'you sleep (fem.)'),
    'مبكرا': ('d', 'early'),
    'فكرة': ('n', 'idea'),
    'جيدة': ('a', 'good (fem.)'),
    'أتوقف': ('v', 'I stop'),
    'شرب': ('n', 'drinking'),
    'إذن': ('d', 'then; so'),
    'تقديم': ('n', 'submitting'),
    'شكوى': ('n', 'complaint'),
    'الإنترنت': ('n', 'the internet'),
    'مقطوع': ('a', 'cut off (masc.)'),
    'منذ': ('p', 'since'),
    'بيتي': ('n', 'my house'),
    'ولم': ('t', 'and did not'),
    'يحل': ('v', 'he or she solves'),
    'أحد': ('r', 'anyone'),
    'زيارة': ('n', 'visit'),
    'فنية': ('a', 'technical (fem.)'),
    'لإصلاح': ('p', 'to fix'),
    'بنا': ('p', 'to us'),
    'المشكلة': ('n', 'the problem'),
    'ليتني': ('t', 'if only I'),
    'حضرت': ('v', 'I attended'),
    'حفلة': ('n', 'party'),
    'عيد': ('n', 'festival'),
    'ميلادك': ('n', 'your birth'),
    'الشهر': ('n', 'the month'),
    'الماضي': ('a', 'last; past'),
    'مريضة': ('a', 'sick (fem.)'),
    'تلك': ('r', 'that (fem.)'),
    'الليلة': ('n', 'the night'),
    'أخبرك': ('v', 'I tell you'),
    'بذلك': ('p', 'about that'),
    'سيكون': ('v', 'it will be'),
    'اجتماع': ('n', 'meeting'),
    'الاثنين': ('n', 'Monday'),
    'أنوي': ('v', 'I intend'),
    'تعلم': ('n', 'learning'),
    'اللغة': ('n', 'the language'),
    'الألمانية': ('a', 'the German (fem.)'),
    'العام': ('n', 'the year'),
    'برنامجك': ('n', 'your schedule'),
    'المشروع': ('n', 'the project'),
    'قد': ('t', 'may; might'),
    'ينتهي': ('v', 'it ends'),
    'متأخرا': ('d', 'late'),
    'لست': ('v', 'I am not'),
    'متأكدا': ('a', 'sure (masc.)'),
    'باختصار': ('d', 'in short'),
    'ستبني': ('v', 'she will build'),
    'الحكومة': ('n', 'the government'),
    'جسرا': ('n', 'a bridge'),
    'جديدا': ('a', 'new (describing a bridge)'),
    'القادم': ('a', 'the next; coming'),
    'بالإضافة': ('d', 'in addition (first of two words)'),
    'ذلك': ('r', 'that (masc.)'),
    'سيقلل': ('v', 'it will reduce'),
    'الجسر': ('n', 'the bridge'),
    'وقت': ('n', 'time'),
    'السفر': ('n', 'the travel'),
    'بين': ('p', 'between'),
    'المدينتين': ('n', 'the two cities'),
    'شيئا': ('n', 'something'),
    'مثيرا': ('a', 'exciting (masc.)'),
    'للاهتمام': ('p', 'of interest'),
    'مقالا': ('n', 'an article'),
    'مشروع': ('n', 'project'),
    'جديد': ('a', 'new (masc.)'),
    'الرغم': ('n', 'despite (in the phrase for although)'),
    'الأمر': ('n', 'the matter'),
    'يحمل': ('v', 'he or it carries'),
    'مخاطرة': ('n', 'risk'),
    'أؤيد': ('v', 'I support'),
    'فتح': ('n', 'opening'),
    'مكتب': ('n', 'office'),
    'ثان': ('a', 'second (masc.)'),
    'غير': ('t', 'however (in the phrase for however)'),
    'علينا': ('p', 'we must (literally: on us)'),
    'نضع': ('v', 'we put'),
    'خطة': ('n', 'plan'),
    'دقيقة': ('a', 'precise (fem.)'),
    'أولا': ('d', 'first'),
    'رأيك': ('n', 'your opinion'),
    'لدينا': ('p', 'we have'),
    'لكنا': ('v', 'we would be'),
    'أنهينا': ('v', 'we finished'),
    'ركزنا': ('v', 'we focused'),
    'الميزانية': ('n', 'the budget'),
    'كنا': ('v', 'we were'),
    'سننهي': ('v', 'we will finish'),
    'الوقت': ('n', 'the time'),
    'المحدد': ('a', 'the set; the specified'),
    'تكرمتم': ('v', 'you were kind enough (formal)'),
    'بمراجعة': ('n', 'by reviewing'),
    'الاجتماع': ('n', 'the meeting'),
    'يمكننا': ('v', 'we are able to'),
    'الانتقال': ('n', 'moving on'),
    'النقطة': ('n', 'the point'),
    'التالية': ('a', 'the next (fem.)'),
    'أي': ('r', 'any'),
    'ملاحظات': ('n', 'comments'),
    'بالطبع': ('d', 'of course'),
    'الزميل': ('n', 'the colleague (masc.)'),
    'الذي': ('r', 'who; which (masc.)'),
    'يعمل': ('v', 'he works'),
    'اسمه': ('n', 'his name'),
    'كريم': ('N', 'Karim'),
    'المبنى': ('n', 'the building'),
    'عنه': ('p', 'about him'),
    'قريب': ('a', 'close; near (masc.)'),
    'الشركة': ('n', 'the company'),
    'التي': ('r', 'who; which (fem.)'),
    'عملنا': ('v', 'we worked'),
    'معها': ('p', 'with her'),
    'قريبة': ('a', 'close; near (fem.)'),
    'هو': ('r', 'he'),
    'الجديد': ('a', 'the new (masc.)'),
    'أريد': ('v', 'I want'),
}
GLOSSES_B1 = {tok: gloss for tok, (_code, gloss) in B1_ENTRIES.items()}
POS_SETS_B1: dict[str, set[str]] = {}
for _tok, (_code, _gloss) in B1_ENTRIES.items():
    POS_SETS_B1.setdefault(_B1_POS_CODES[_code], set()).add(_tok)
part_of_speech_b1 = pos_lookup(POS_SETS_B1)


def iter_specs():
    for level, group in LEVELS.items():
        realizations, _ = manifest_group(group)
        tables = {
            "a1": (GLOSSES, part_of_speech, CATEGORY_TAGS),
            "a2": (GLOSSES_A2, part_of_speech_a2, CATEGORY_TAGS_A2),
            "b1": (GLOSSES_B1, part_of_speech_b1, {}),
        }
        glosses, pos, tags = tables[level]
        yield from classify(
            lang=LANG,
            level=level,
            unit_files=realizations,
            glosses=glosses,
            part_of_speech=pos,
            normalize=normalize,
            category_tags=tags,
        )


def main() -> int:
    return run(
        description=__doc__,
        source_language="en",
        target_language=LANG,
        levels=LEVELS,
        iter_specs=iter_specs,
    )


if __name__ == "__main__":
    raise SystemExit(main())
