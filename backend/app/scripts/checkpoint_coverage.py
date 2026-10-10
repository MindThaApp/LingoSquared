"""Measure which units can produce a scored unit checkpoint.

Runs the real ``generate_checkpoint()`` for every unit of the selected
courses, exactly as ``POST /units/{id}/checkpoint`` does, and counts the
items it returns. A unit is available when it yields at least
``CHECKPOINT_MIN_ITEMS`` (the floor below which the endpoint answers 409
``checkpoint_unavailable``).

Read-only by construction: everything runs inside one transaction that is
always rolled back, including the throwaway probe user that the
``practice_items.user_id`` foreign key needs. Each unit runs in its own
savepoint, so one unit's generated items never count as another unit's
"recent" history.

Run from ``backend/`` against a database that has content, lexeme backfills
and practice packs imported (``scripts/sync_dev_db.sh``)::

    python -m app.scripts.checkpoint_coverage                 # 6 launch directions
    python -m app.scripts.checkpoint_coverage --direction fa-en --direction prs-en
    python -m app.scripts.checkpoint_coverage --all --json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Iterable
from uuid import uuid4

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Course, Unit, User
from app.practice.service import generate_checkpoint

CHECKPOINT_MIN_ITEMS = 12
CHECKPOINT_SIZE = 15
LAUNCH_DIRECTIONS = ("en-nl", "en-fa", "en-prs", "nl-en", "fa-en", "prs-en")
LEVEL_ORDER = {level: index for index, level in enumerate(("A1", "A2", "B1", "B2", "C1", "C2"))}

# Fixed so repeated runs draw the same seeded sample (the checkpoint RNG is
# keyed on user id). The row only ever exists inside the rolled-back
# transaction.
PROBE_USER_ID = "00000000-0000-4000-8000-0000c0ffee12"
PROBE_USER_EMAIL = "checkpoint-coverage-probe@invalid.local"


@dataclass(frozen=True)
class UnitCoverage:
    direction: str
    level: str
    course_title: str
    unit_order: int
    unit_key: str | None
    unit_title: str
    items: int

    @property
    def available(self) -> bool:
        return self.items >= CHECKPOINT_MIN_ITEMS


def parse_direction(direction: str) -> tuple[str, str]:
    source, sep, target = direction.partition("-")
    if not sep or not source or not target:
        raise ValueError(f"direction must look like 'en-nl', got {direction!r}")
    return source, target


def _level(course: Course) -> str:
    level = course.level
    return getattr(level, "value", level) or "A1"


def _authored_course_ids(db: Session, course_ids: list[str]) -> set[str]:
    # Courses imported from the authored corpus carry unit content keys;
    # the bootstrap demo courses do not (same rule remove_demo_courses.sql
    # uses), so they are skipped unless asked for.
    if not course_ids:
        return set()
    return set(
        db.scalars(
            select(Unit.course_id)
            .where(Unit.course_id.in_(course_ids), Unit.content_key.is_not(None))
            .distinct()
        )
    )


def measure(
    db: Session,
    directions: Iterable[str] | None = LAUNCH_DIRECTIONS,
    include_unkeyed: bool = False,
    course_ids: Iterable[str] | None = None,
) -> list[UnitCoverage]:
    """Probe every unit of the matching courses. Leaves the session rolled back."""
    try:
        query = select(Course)
        if course_ids is not None:
            query = query.where(Course.id.in_(list(course_ids)))
        if directions is not None:
            pairs = [parse_direction(direction) for direction in directions]
            query = query.where(
                tuple_(Course.source_language, Course.target_language).in_(pairs)
            )
        courses = list(db.scalars(query))
        if not include_unkeyed:
            authored = _authored_course_ids(db, [course.id for course in courses])
            courses = [course for course in courses if course.id in authored]
        courses.sort(
            key=lambda course: (
                course.source_language,
                course.target_language,
                LEVEL_ORDER.get(_level(course), 99),
                course.title,
            )
        )

        db.add(
            User(
                id=PROBE_USER_ID,
                email=PROBE_USER_EMAIL,
                display_name="checkpoint coverage probe",
                is_active=False,
            )
        )
        db.flush()

        results: list[UnitCoverage] = []
        for course in courses:
            units = list(
                db.scalars(
                    select(Unit)
                    .where(Unit.course_id == course.id)
                    .order_by(Unit.order, Unit.id)
                )
            )
            for unit in units:
                savepoint = db.begin_nested()
                try:
                    items = generate_checkpoint(
                        db,
                        PROBE_USER_ID,
                        course,
                        unit.id,
                        CHECKPOINT_SIZE,
                        str(uuid4()),
                    )
                    count = len(items)
                finally:
                    savepoint.rollback()
                results.append(
                    UnitCoverage(
                        direction=f"{course.source_language}-{course.target_language}",
                        level=_level(course),
                        course_title=course.title,
                        unit_order=unit.order,
                        unit_key=unit.content_key,
                        unit_title=unit.title,
                        items=count,
                    )
                )
        return results
    finally:
        db.rollback()


def summarize(results: Iterable[UnitCoverage]) -> dict[str, dict[str, int]]:
    """Per direction (and overall): available / total units."""
    summary: dict[str, dict[str, int]] = defaultdict(lambda: {"available": 0, "total": 0})
    for result in results:
        for key in (result.direction, "overall"):
            summary[key]["total"] += 1
            summary[key]["available"] += int(result.available)
    return dict(summary)


def format_report(results: list[UnitCoverage]) -> str:
    summary = summarize(results)
    lines = ["direction  available/total"]
    for direction, counts in summary.items():
        if direction == "overall":
            continue
        lines.append(f"{direction:<10} {counts['available']}/{counts['total']}")
    overall = summary.get("overall", {"available": 0, "total": 0})
    percent = 100.0 * overall["available"] / overall["total"] if overall["total"] else 0.0
    lines.append(f"{'overall':<10} {overall['available']}/{overall['total']} ({percent:.1f}%)")
    missing = [result for result in results if not result.available]
    if missing:
        lines.append("")
        lines.append(f"unavailable (fewer than {CHECKPOINT_MIN_ITEMS} items):")
        for result in missing:
            label = result.unit_key or f"{result.course_title} #{result.unit_order}"
            lines.append(f"  {result.direction} {result.level} {label}: {result.items}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure unit checkpoint availability")
    parser.add_argument(
        "--direction",
        action="append",
        help="course direction such as en-nl (repeatable; default: the 6 launch directions)",
    )
    parser.add_argument("--all", action="store_true", help="every course, all directions")
    parser.add_argument(
        "--include-unkeyed",
        action="store_true",
        help="also probe courses without unit content keys (bootstrap demo courses)",
    )
    parser.add_argument("--json", action="store_true", help="print per-unit JSON instead of a report")
    args = parser.parse_args(argv)

    if args.all and args.direction:
        parser.error("--all and --direction are mutually exclusive")
    directions = None if args.all else (args.direction or list(LAUNCH_DIRECTIONS))
    try:
        for direction in directions or ():
            parse_direction(direction)
    except ValueError as exc:
        parser.error(str(exc))

    with SessionLocal() as db:
        results = measure(db, directions, include_unkeyed=args.include_unkeyed)

    if args.json:
        print(
            json.dumps(
                {
                    "min_items": CHECKPOINT_MIN_ITEMS,
                    "summary": summarize(results),
                    "units": [asdict(result) | {"available": result.available} for result in results],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(format_report(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
