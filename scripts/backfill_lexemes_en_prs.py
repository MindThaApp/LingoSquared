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
}


def prs_agreement_tags(token: str, lesson_key: str) -> dict[str, object]:
    semantics: list[str] = []
    letters = set("ابتدرزسشصجچحخعغفقکگلمنوهی")
    if token in letters:
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


def iter_specs():
    specs: dict[str, dict] = {}
    for unit_order, (realization_path, _overlay_path) in enumerate(UNIT_FILES, 1):
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
                    existing = specs.get(token)
                    if existing is None:
                        specs[token] = {
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "prs",
                            "part_of_speech": PRS_POS[token],
                            "english_gloss": PRS_GLOSSES[token], "agreement_tags": tags,
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
        print(f"Lexeme backfill dry run: {len(specs)} prs.")
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        course = db.scalar(
            select(Course).where(
                Course.source_language == "en",
                Course.target_language == "prs",
                Course.title == "Dari A1",
            )
        )
        if course is None:
            print("ERROR: en-prs 'Dari A1' course must be imported first", file=sys.stderr)
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
