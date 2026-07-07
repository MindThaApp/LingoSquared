#!/usr/bin/env python3
"""Idempotently backfill Unit.content_key for units imported before
content_key tracking existed on the units endpoint (2026-07-07).

Why this exists: `POST /admin/content/import`'s content_key-based
update-in-place matching (see docs/CONTRACT.md, "content_key-based
update-in-place, 2026-07-06") only updates a row that ALREADY has a
matching content_key — a pre-existing row with content_key=NULL can
never be matched by content_key (see `_match_by_content_key`'s own
docstring in backend/app/content/service.py: "pre-content_key rows are
structurally unmatchable"), so a plain re-import leaves every
already-shipped unit's content_key NULL forever. This script instead
matches existing NULL-content_key Unit rows to their real content_key
directly by TITLE, using each course direction's own overlay files
(docs/content/overlays/{source}-{target}/*.yaml) — the exact same
title text `import_content()` used when it first created that row, so
the match is exact, not a guess, and is safely skipped (never guessed)
whenever a title isn't uniquely recoverable.

Needs both the app's DB settings/imports (in backend/) and this repo's
docs/content/ (at the repo root), which the backend Docker image alone
doesn't have — it only contains backend/. Run via docker compose from
backend/, mounting the full repo on top of the existing image/network/env
(same recipe as backfill_lexemes.py):

    cd backend
    docker compose run --rm \\
      -v "$(cd .. && pwd):/repo" \\
      -e PYTHONPATH=/repo/backend \\
      --entrypoint python \\
      api /repo/scripts/backfill_unit_content_keys.py

Add --dry-run to report what WOULD change without touching the database.

Only ever writes Unit.content_key (an additive nullable column) — never
touches order/title/section, never creates/deletes rows, and only ever
updates rows that are currently NULL. Safe to re-run any number of times
(a unit that already has a content_key is left untouched, matched or not).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

OVERLAYS_ROOT = REPO_ROOT / "docs/content/overlays"
REALIZATIONS_ROOT = REPO_ROOT / "docs/content/realizations"


def _title_to_content_key_for_direction(source: str, target: str) -> dict[str, str]:
    """Build {unit_title: content_key} for one (source, target) course
    direction from its overlay files, falling back to the realization's
    own raw title for any unit an overlay doesn't override. Titles that
    map to more than one content_key within this direction are dropped
    (reported separately) rather than matched ambiguously."""
    overlay_dir = OVERLAYS_ROOT / f"{source}-{target}"
    by_title: dict[str, set[str]] = {}
    if not overlay_dir.is_dir():
        return {}
    for overlay_file in sorted(overlay_dir.glob("*.yaml")):
        data = yaml.safe_load(overlay_file.read_text()) or {}
        units = data.get("units") or {}
        for content_key, override in units.items():
            title = (override or {}).get("title")
            if not title:
                # Overlay didn't override this unit's title -- fall back
                # to the realization file's own raw title for the same
                # content_key. target_language of the realization is
                # always `target` (a course teaches `target`, and every
                # X-en direction realizes the SAME en/*.yaml content).
                title = _realization_title(target, content_key)
            if not title:
                continue
            by_title.setdefault(title, set()).add(content_key)
    return {
        title: next(iter(keys))
        for title, keys in by_title.items()
        if len(keys) == 1
    }


_REALIZATION_CACHE: dict[str, dict[str, str]] = {}


def _realization_title(target: str, content_key: str) -> str | None:
    """Look up a unit's raw title directly from its realization file by
    content_key, scanning every a1/a2_unit*.yaml under
    docs/content/realizations/{target}/ once per target language."""
    if target not in _REALIZATION_CACHE:
        cache: dict[str, str] = {}
        lang_dir = REALIZATIONS_ROOT / target
        if lang_dir.is_dir():
            for f in sorted(lang_dir.glob("a*_unit*.yaml")):
                data = yaml.safe_load(f.read_text()) or {}
                for unit in data.get("units") or []:
                    key = unit.get("content_key")
                    title = unit.get("title")
                    if key and title:
                        cache[key] = title
        _REALIZATION_CACHE[target] = cache
    return _REALIZATION_CACHE[target].get(content_key)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without touching the database.",
    )
    args = parser.parse_args()

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Unit

    direction_cache: dict[tuple[str, str], dict[str, str]] = {}
    matched = 0
    ambiguous_or_missing = 0

    with SessionLocal() as db:
        courses = list(db.scalars(select(Course)))
        for course in courses:
            direction = (course.source_language, course.target_language)
            if direction not in direction_cache:
                direction_cache[direction] = _title_to_content_key_for_direction(*direction)
            title_map = direction_cache[direction]
            if not title_map:
                continue
            units = list(
                db.scalars(
                    select(Unit).where(
                        Unit.course_id == course.id,
                        Unit.content_key.is_(None),
                    )
                )
            )
            for unit in units:
                content_key = title_map.get(unit.title)
                if content_key is None:
                    ambiguous_or_missing += 1
                    continue
                matched += 1
                print(
                    f"{'[dry-run] ' if args.dry_run else ''}"
                    f"{course.source_language}-{course.target_language} "
                    f"{course.title!r} unit {unit.order} {unit.title!r} "
                    f"-> content_key={content_key!r}"
                )
                if not args.dry_run:
                    unit.content_key = content_key
        if not args.dry_run:
            db.commit()

    print(
        f"\nUnit content_key backfill {'(dry run) ' if args.dry_run else ''}"
        f"complete: {matched} matched, {ambiguous_or_missing} left NULL "
        "(no unique title match — expected for synthetic/test courses "
        "and any unit whose title has since diverged from its content "
        "file)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
