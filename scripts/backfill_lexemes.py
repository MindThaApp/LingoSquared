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
}

FA_SYMBOLS = set("س ل ا م ن ت ش چ ی ه ک گ ج د ر ف و ب خ ز".split())
FA_PROPER_NOUNS = set("علی نرگس سارا مینا ایران انگلیس فرانسه".split())
FA_PRONOUNS = set("من تو شما او ما این".split())
FA_PREPOSITIONS = set("به از با اهل بهت مثل".split())
FA_PARTICLES = set("هم ولی بله و آره پس تا".split())
FA_ADVERBS = set(
    "فعلاً خیلی چطور کجا اینجا همین‌طور کجایی باهم فردا حتماً خودمونی چند".split()
)
FA_ADJECTIVES = set(
    "خوبی بد ایرانی انگلیسی فرانسوی بزرگه کوچیکه متأهل مجرد برعکسه شلوغه".split()
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


def iter_specs():
    fa_specs: dict[str, dict] = {}
    seen_en: set[str] = set()
    for unit_order, (realization_path, overlay_path) in enumerate(UNIT_FILES, 1):
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
                    existing = fa_specs.get(token)
                    if existing is None:
                        fa_specs[token] = {
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "fa",
                            "part_of_speech": fa_part_of_speech(token),
                            "english_gloss": FA_GLOSSES[token], "agreement_tags": tags,
                        }
                    else:
                        for key, value in tags.items():
                            if key == "semantic":
                                prior = existing["agreement_tags"].setdefault(key, [])
                                prior.extend(item for item in value if item not in prior)
                            else:
                                existing["agreement_tags"].setdefault(key, value)

                target_text = item.get("target", {}).get("text", "").strip()
                introduced = item.get("introduced_tokens", [])
                if len(introduced) > 1 and target_text and "\n" not in target_text:
                    tags = fa_agreement_tags(target_text, lesson_key)
                    fa_specs.setdefault(
                        target_text,
                        {
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": target_text, "language_code": "fa",
                            "part_of_speech": "phrase", "english_gloss": gloss,
                            "agreement_tags": tags,
                        },
                    )
                for match in EN_TOKEN_RE.findall(gloss):
                    token = match.casefold().replace("’", "'")
                    if token in seen_en:
                        continue
                    seen_en.add(token)
                    yield {
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
        course = db.scalar(
            select(Course).where(
                Course.source_language == "en",
                Course.target_language == "fa",
                Course.title == "Farsi A1",
            )
        )
        if course is None:
            print("ERROR: en-fa Farsi A1 course must be imported first", file=sys.stderr)
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
