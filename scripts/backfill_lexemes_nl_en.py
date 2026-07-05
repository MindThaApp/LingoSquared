#!/usr/bin/env python3
"""Idempotently backfill reviewed nl-en A1 lexemes (English target,
Dutch source) from the shared en realization units 1 and 2.

Written directly (not via Codex -- Codex was rate-limited at authoring
time) mirroring scripts/backfill_lexemes.py's structure and rigor.
Target-side English classification lives in
scripts/_en_target_lexeme_common.py (shared with backfill_lexemes_fa_en.py
and backfill_lexemes_prs_en.py, since all three teach the identical
English realization to different source-language speakers -- only the
Dutch/Farsi/Dari source-side classification differs per script).

Needs both the app's DB settings/imports (in backend/) and this repo's
docs/content/ (at the repo root). Run via docker compose from backend/,
mounting the full repo on top of the existing image/network/env:

    cd backend
    docker compose run --rm \
      -v "$(cd .. && pwd):/repo" \
      -e PYTHONPATH=/repo/backend \
      --entrypoint python \
      api /repo/scripts/backfill_lexemes_nl_en.py

Add --dry-run to classify without touching the database.

Dutch source-side words are extracted from the nl-en overlay's `gloss:`
fields (the Dutch translation shown for each taught English item),
mirroring exactly how the reference script extracts English words from
the en-fa overlay's English gloss text.
"""
from __future__ import annotations

import re
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

# Dutch gloss for each shared English target token -- this is
# course-specific (source_language=nl), NOT shared with the fa-en/prs-en
# backfill scripts, unlike EN_POS/en_agreement_tags above. Found via live
# verification that a naive shared "english_gloss" would have made
# slot_gloss-derived multiple_choice exercises match an English word
# against itself instead of its actual Dutch meaning -- see the
# IMPORTANT note in _en_target_lexeme_common.py.
EN_TARGET_TO_NL_GLOSS: dict[str, str] = {
    "hello": "hallo", "hi": "hoi", "good": "goed", "morning": "ochtend",
    "afternoon": "middag", "evening": "avond", "goodbye": "tot ziens",
    "bye": "doei", "how": "hoe", "are": "bent (2e persoon)",
    "you": "jij / u", "i'm": "ik ben", "fine": "goed", "thanks": "bedankt",
    "not": "niet", "bad": "slecht", "and": "en", "okay": "oké",
    "nice": "leuk", "to": "te", "meet": "ontmoeten", "too": "ook",
    "see": "zien", "later": "later", "have": "hebben", "a": "een",
    "day": "dag", "what": "wat", "is": "is", "what's": "wat is",
    "your": "jouw / uw", "name": "naam", "my": "mijn", "leila": "Leila",
    "i": "ik", "am": "ben", "student": "student", "teacher": "leraar",
    "yes": "ja", "no": "nee", "new": "nieuw", "member": "lid",
    "he": "hij", "she": "zij", "an": "een", "engineer": "ingenieur",
    "library": "bibliotheek", "assistant": "medewerker", "daniel": "Daniel",
    "work": "werken", "at": "bij", "the": "de", "welcome": "welkom",
    "thank": "danken",
}

UNIT_FILES = (
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit01_greetings.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit02_introductions.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit02.yaml",
    ),
)

# Dutch word tokenizer -- Latin script plus Dutch diacritics (ë, ï, etc.)
NL_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ]+(?:['’-][A-Za-zÀ-ÿ]+)*")

# Hand-classified from every unique word appearing in the nl-en overlay's
# `gloss:` fields across both units (confirmed by reading both files).
NL_POS: dict[str, str] = {
    "hallo": "noun", "hoi": "noun", "goedemorgen": "noun", "goedemiddag": "noun",
    "goedenavond": "noun", "tot": "preposition", "ziens": "noun", "doei": "noun",
    "hoe": "adverb", "gaat": "verb", "het": "pronoun", "met": "preposition",
    "je": "pronoun", "u": "pronoun", "en": "particle", "jij": "pronoun",
    "bedankt": "noun", "niet": "particle", "slecht": "adjective", "ben": "verb",
    "oké": "adjective", "leuk": "adjective", "te": "preposition",
    "ontmoeten": "verb", "jou": "pronoun", "ook": "adverb", "later": "adverb",
    "fijne": "adjective", "dag": "noun", "heet": "verb", "mijn": "pronoun",
    "naam": "noun", "is": "verb", "leila": "proper_noun", "ik": "pronoun",
    "student": "noun", "leraar": "noun", "ja": "particle", "dat": "pronoun",
    "nee": "particle", "een": "particle", "nieuw": "adjective", "lid": "noun",
    "hij": "pronoun", "zij": "pronoun", "ingenieur": "noun", "bibliotheek": "noun",
    "bibliotheekmedewerker": "noun", "daniel": "proper_noun", "werk": "verb",
    "bij": "preposition", "welkom": "adjective", "in": "preposition", "dank": "noun",
    "de": "particle", "goed": "adjective",
}

NL_GLOSSES: dict[str, str] = {
    "hallo": "hello", "hoi": "hi (informal)", "goedemorgen": "good morning",
    "goedemiddag": "good afternoon", "goedenavond": "good evening",
    "tot": "until; to", "ziens": "seeing (fixed expression 'tot ziens')",
    "doei": "bye (informal)", "hoe": "how", "gaat": "goes (3rd person 'gaan')",
    "het": "it", "met": "with", "je": "you (informal)", "u": "you (formal)",
    "en": "and", "jij": "you (informal, emphatic)", "bedankt": "thanks",
    "niet": "not", "slecht": "bad", "ben": "am (1st person 'zijn')",
    "oké": "okay", "leuk": "nice; fun", "te": "to",
    "ontmoeten": "to meet", "jou": "you (informal, object form)",
    "ook": "also; too", "later": "later", "fijne": "nice; pleasant",
    "dag": "day", "heet": "is called/named (3rd person 'heten')",
    "mijn": "my", "naam": "name", "is": "is (3rd person 'zijn')",
    "leila": "Leila (name)", "ik": "I", "student": "student", "leraar": "teacher",
    "ja": "yes", "dat": "that", "nee": "no", "een": "a; an", "nieuw": "new",
    "lid": "member", "hij": "he", "zij": "she", "ingenieur": "engineer",
    "bibliotheek": "library", "bibliotheekmedewerker": "library assistant",
    "daniel": "Daniel (name)", "werk": "work (1st person 'werken')",
    "bij": "at; by", "welkom": "welcome", "in": "in", "dank": "thanks (short form)",
    "de": "the (common gender)", "goed": "good; well",
}


def nl_agreement_tags(token: str) -> dict[str, object]:
    semantics: list[str] = []
    if token in {"hallo", "hoi", "goedemorgen", "goedemiddag", "goedenavond", "welkom"}:
        semantics.append("greeting")
    if token in {"goedemorgen", "goedemiddag", "goedenavond", "dag"}:
        semantics.append("time_period")
    if token in {"tot", "ziens", "doei", "later"}:
        semantics.append("farewell")
    if token in {"hoe", "gaat"}:
        semantics.append("wellbeing_question")
    if token in {"slecht", "oké", "niet", "goed"}:
        semantics.append("wellbeing_answer")
    if token in {"bedankt", "dank", "leuk", "welkom"}:
        semantics.append("politeness")
    if token in {"ja", "nee"}:
        semantics.append("politeness")
    if token in {"naam", "mijn", "heet", "ik", "ben", "is", "je", "u", "jij"}:
        semantics.append("identity")
    if token in {"leila", "daniel"}:
        semantics.append("person_name")
    if token in {"bibliotheek", "bibliotheekmedewerker", "lid", "student", "leraar", "ingenieur", "nieuw", "werk"}:
        semantics.append("dialogue_word")

    tags: dict[str, object] = {}
    if semantics:
        tags["semantic"] = semantics

    person = {
        "ik": "first", "ben": "first",
        "je": "second", "u": "second", "jij": "second", "jou": "second", "mijn": "first",
        "hij": "third", "zij": "third", "het": "third", "is": "third", "heet": "third",
    }.get(token)
    if person:
        tags["person"] = person
    if token in {"je", "jij", "jou"}:
        tags["register"] = "informal"
    elif token == "u":
        tags["register"] = "formal"
    return tags


def iter_specs():
    en_specs: dict[str, dict] = {}
    nl_specs: dict[str, dict] = {}
    for unit_order, (realization_path, overlay_path) in enumerate(UNIT_FILES, 1):
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
        overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
        teaching_overlays = overlay["teaching"]
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson["teaching"]:
                content_key = item["content_key"]
                gloss = teaching_overlays.get(content_key, {}).get("gloss", "")

                for token in item.get("introduced_tokens", []):
                    token = token.casefold().replace("’", "'")
                    if token not in EN_POS:
                        raise ValueError(
                            f"missing English classification for {token!r} "
                            f"in _en_target_lexeme_common.py (lesson {lesson_key})"
                        )
                    existing = en_specs.get(token)
                    tags = en_agreement_tags(token)
                    if existing is None:
                        en_specs[token] = {
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "en",
                            "part_of_speech": EN_POS[token],
                            "english_gloss": EN_TARGET_TO_NL_GLOSS[token], "agreement_tags": tags,
                        }
                    else:
                        for key, value in tags.items():
                            if key == "semantic":
                                prior = existing["agreement_tags"].setdefault(key, [])
                                prior.extend(v for v in value if v not in prior)
                            else:
                                existing["agreement_tags"].setdefault(key, value)

                for match in NL_TOKEN_RE.findall(gloss):
                    token = match.casefold()
                    if token not in NL_POS:
                        raise ValueError(
                            f"missing explicit Dutch gloss for {token!r} "
                            f"(from gloss text {gloss!r}, lesson {lesson_key})"
                        )
                    tags = nl_agreement_tags(token)
                    existing = nl_specs.get(token)
                    if existing is None:
                        nl_specs[token] = {
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "nl",
                            "part_of_speech": NL_POS[token],
                            "english_gloss": NL_GLOSSES[token], "agreement_tags": tags,
                        }
                    else:
                        for key, value in tags.items():
                            if key == "semantic":
                                prior = existing["agreement_tags"].setdefault(key, [])
                                prior.extend(v for v in value if v not in prior)
                            else:
                                existing["agreement_tags"].setdefault(key, value)
    yield from en_specs.values()
    yield from nl_specs.values()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    specs = list(iter_specs())
    if args.dry_run:
        en_count = sum(spec["language_code"] == "en" for spec in specs)
        nl_count = sum(spec["language_code"] == "nl" for spec in specs)
        print(f"Lexeme backfill dry run: {en_count} en, {nl_count} nl.")
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        course = db.scalar(
            select(Course).where(
                Course.source_language == "nl",
                Course.target_language == "en",
                Course.title == "Engels A1",
            )
        )
        if course is None:
            print("ERROR: nl-en 'Engels A1' course must be imported first", file=sys.stderr)
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
