#!/usr/bin/env python3
"""Idempotently backfill reviewed fa-en A1 lexemes (English target) from
the shared en realization units 1 and 2.

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
