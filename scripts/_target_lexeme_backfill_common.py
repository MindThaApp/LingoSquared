#!/usr/bin/env python3
"""Shared runner for the per-direction en->X lexeme backfills added in
session 10 (backfill_lexemes_en_es.py and its siblings).

Deliberately NOT named ``backfill_lexemes*.py``: scripts/sync_dev_db.sh runs
every file matching that glob, and this module is a library, not a backfill.

It mirrors scripts/backfill_lexemes_en_nl.py's structure and invariants, but
keeps the per-direction scripts down to DATA (one hand-written gloss and part
of speech per token, plus optional category tags), so a reviewer reads
glosses instead of plumbing:

* Unit files come from the direction's ``scripts/manifest.d/content/*.txt`` line,
  in manifest order. ``unit_order`` is positional and must equal the imported
  ``Unit.order``; reading the manifest line itself (instead of a glob) keeps
  that invariant by construction (see the long comment above
  backfill_lexemes_en_nl.py's UNIT_FILES for the data-corruption bug that a
  glob drifting from the manifest caused).
* The course title is read from the group's first overlay (``course.title``),
  the same value ``POST /admin/content/import`` deduplicates courses by.
* One spec per (course, token); first sight wins, exactly like en-nl. A token
  first taught in an earlier unit keeps that unit's provenance lesson.
* Every token gets three automatic semantic tags, so practice packs can build
  PER-UNIT pools without touching this file:
    ``<lang>_<level>_u<NN>``        every lexeme first taught in unit NN
    ``<lang>_<level>_u<NN>_l<LL>``  ... in lesson LL of unit NN
    ``w_<token>``                   a single-member anchor for that token
  ``NN`` is the realization FILE's unit number (``a1_unit07_x`` -> ``u07``),
  not the manifest position, so tags read the same as the file names.
* A missing gloss or part of speech is a hard error (ValueError), never a
  guess. A new realization unit therefore crashes the backfill until someone
  glosses its tokens, by design.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Callable, Iterable, Iterator

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

MANIFEST = REPO_ROOT / "scripts/manifest.d/content"
POS_ORDER = (
    "symbol", "proper_noun", "pronoun", "preposition", "particle",
    "adjective", "adverb", "verb", "phrase", "noun",
)
_UNIT_NUM_RE = re.compile(r"^[a-c][12]_unit(\d+)_")


def manifest_group(group: str) -> tuple[list[Path], list[Path]]:
    """(realization paths, overlay paths) of one manifest.d/content group file,
    in manifest order."""
    fp = MANIFEST / f"{group}.txt"
    for line in (fp.read_text(encoding="utf-8").splitlines() if fp.exists() else []):
        if line.startswith(group + "|"):
            parts = line.split("|")
            return (
                [REPO_ROOT / p for p in parts[1].split()],
                [REPO_ROOT / p for p in parts[2].split()],
            )
    raise SystemExit(f"{group!r} group missing from {MANIFEST}")


def course_title(group: str) -> str:
    _, overlays = manifest_group(group)
    overlay = yaml.safe_load(overlays[0].read_text(encoding="utf-8"))
    return overlay["course"]["title"]


def pos_lookup(pos_sets: dict[str, Iterable[str]]) -> Callable[[str], str]:
    """Build a token -> part_of_speech function from {pos: tokens}. A token
    listed under two parts of speech is an authoring error."""
    table: dict[str, str] = {}
    for pos in POS_ORDER:
        for token in pos_sets.get(pos, ()):
            if token in table and table[token] != pos:
                raise ValueError(f"{token!r} listed as both {table[token]} and {pos}")
            table[token] = pos
    unknown = set(pos_sets) - set(POS_ORDER)
    if unknown:
        raise ValueError(f"unknown part-of-speech sets: {sorted(unknown)}")

    def lookup(token: str) -> str:
        try:
            return table[token]
        except KeyError:
            raise ValueError(f"missing explicit part of speech for {token!r}") from None

    return lookup


def split_words(text: str) -> set[str]:
    """Whitespace-split helper for writing POS sets as one string."""
    return set(text.split())


def classify(
    *,
    lang: str,
    level: str,
    unit_files: list[Path],
    glosses: dict[str, str],
    part_of_speech: Callable[[str], str],
    normalize: Callable[[str], str],
    category_tags: dict[str, list[str]] | None = None,
    gloss_overrides: dict[tuple[str, str], str] | None = None,
    pos_overrides: dict[tuple[str, str], str] | None = None,
) -> Iterator[dict]:
    """Yield one lexeme spec per token, first sight wins (fresh per course).

    ``normalize`` maps an introduced token to its citation form (e.g. fold a
    sentence-initial capital). ``category_tags`` adds hand-chosen semantic
    tags per citation form (weekday, family_member, ...). The overrides are
    keyed by (realization stem, token), like en-nl's NL_UNIT_*_OVERRIDES.
    """
    category_tags = category_tags or {}
    gloss_overrides = gloss_overrides or {}
    pos_overrides = pos_overrides or {}
    specs: dict[str, dict] = {}
    for unit_order, path in enumerate(unit_files, 1):
        stem = path.stem
        match = _UNIT_NUM_RE.match(stem)
        if not match:
            raise ValueError(f"unexpected realization filename {path.name}")
        unit_tag = f"{lang}_{level}_u{int(match.group(1)):02d}"
        realization = yaml.safe_load(path.read_text(encoding="utf-8"))
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson.get("teaching") or []:
                for raw in item.get("introduced_tokens") or []:
                    token = normalize(str(raw))
                    if token in specs:
                        continue
                    if token not in glosses:
                        raise ValueError(
                            f"missing explicit {lang} gloss for {token!r} ({lesson_key})"
                        )
                    semantic = [unit_tag, f"{unit_tag}_l{lesson_order:02d}", f"w_{token}"]
                    semantic.extend(
                        t for t in category_tags.get(token, ()) if t not in semantic
                    )
                    specs[token] = {
                        "level": level,
                        "unit_order": unit_order,
                        "lesson_order": lesson_order,
                        "lesson_content_key": lesson_key,
                        "content_key": item["content_key"],
                        "token": token,
                        "language_code": lang,
                        "part_of_speech": pos_overrides.get(
                            (stem, token), part_of_speech(token)
                        ),
                        "english_gloss": gloss_overrides.get((stem, token), glosses[token]),
                        "agreement_tags": {"semantic": semantic},
                    }
    yield from specs.values()


def run(
    *,
    description: str,
    source_language: str,
    target_language: str,
    levels: dict[str, str],
    iter_specs: Callable[[], Iterable[dict]],
    argv: list[str] | None = None,
) -> int:
    """CLI + DB writer shared by the per-direction scripts.

    ``levels`` maps level -> manifest.d/content group (e.g. {"a1": "en-es"}).
    Same DB semantics as backfill_lexemes_en_nl.py's main(): update an
    existing (course, language, token, pos) row in place; migrate a single
    other-POS row for the same token in place (keeps FK references valid);
    otherwise insert.
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    specs = list(iter_specs())
    direction = f"{source_language}-{target_language}"
    if args.dry_run:
        per_level = ", ".join(
            f"{sum(s['level'] == lvl for s in specs)} {lvl}" for lvl in levels
        )
        identities = {(s["level"], s["token"], s["part_of_speech"]) for s in specs}
        print(f"Lexeme backfill dry run ({direction}): {len(specs)} {target_language} ({per_level}).")
        if len(identities) != len(specs):
            print("ERROR: duplicate lexeme identities in specs", file=sys.stderr)
            return 1
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        courses_by_level = {}
        for level, group in levels.items():
            title = course_title(group)
            course = db.scalar(
                select(Course).where(
                    Course.source_language == source_language,
                    Course.target_language == target_language,
                    Course.title == title,
                )
            )
            if course is None:
                if any(s["level"] == level for s in specs):
                    print(f"ERROR: {direction} {title!r} course must be imported first", file=sys.stderr)
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
        created = updated = 0
        for raw_spec in specs:
            spec = dict(raw_spec)
            level = spec.pop("level")
            course = courses_by_level[level]
            lesson = lessons_by_level[level].get((spec.pop("unit_order"), spec.pop("lesson_order")))
            if lesson is None:
                print(f"ERROR: imported course is missing {spec['lesson_content_key']}", file=sys.stderr)
                db.rollback()
                return 1
            existing = db.scalar(
                select(Lexeme).where(
                    Lexeme.course_id == course.id,
                    Lexeme.language_code == target_language,
                    Lexeme.token == spec["token"],
                    Lexeme.part_of_speech == spec["part_of_speech"],
                )
            )
            if existing:
                existing.english_gloss = spec["english_gloss"]
                existing.agreement_tags = spec["agreement_tags"]
                updated += 1
                continue
            others = db.scalars(
                select(Lexeme).where(
                    Lexeme.course_id == course.id,
                    Lexeme.language_code == target_language,
                    Lexeme.token == spec["token"],
                )
            ).all()
            if len(others) == 1:
                row = others[0]
                row.part_of_speech = spec["part_of_speech"]
                row.english_gloss = spec["english_gloss"]
                row.agreement_tags = spec["agreement_tags"]
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
    print(f"Lexeme backfill complete ({direction}): {created} created, {updated} updated.")
    return 0
