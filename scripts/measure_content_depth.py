#!/usr/bin/env python3
"""Estimate real content-depth hours per launch pair (Phase I, per
docs/NEXT_PHASE_ARCHITECTURE_SPEC.md section 3).

The publish-gate bar is >=10hr teaching + >=10hr practice per launch
pair, but neither number has ever actually been measured -- CLAUDE.md
and the spec both say so in as many words. This is the ruler.

Two halves, deliberately different data sources:

1. TEACHING MINUTES -- read directly from the realization/overlay YAML
   files (same corpus scripts/audio_manifest.py already reads), no DB
   needed. Estimated as card-count x a calibrated seconds-per-card,
   split by kind, because a dialogue turn takes longer to read/listen
   to than a single vocabulary card. The per-kind second estimates
   below are a first calibration, not measured against real user
   session data -- tune them once real analytics exist; they are
   isolated in SECONDS_PER_CARD so that's a one-line change later.

2. PRACTICE DEPTH -- this is the one the spec's own thesis is about:
   template COUNT overstates real depth, because each template's real
   variety is bounded by how many lexemes the course's reviewed pool
   has for each of that template's typed slots, not by how many
   templates exist. A course with 240 templates but a thin lexeme pool
   can still run out of fresh combinations fast. Needs the real DB
   (Lexeme + PracticeTemplate tables) -- YAML alone doesn't have
   per-lexeme agreement_tags/part_of_speech, that's backfilled data.
   Run via docker compose exactly like scripts/backfill_lexemes.py
   (see that script's own docstring for why: the backend Docker image
   only contains backend/, and this needs both app.models and the DB):

       cd backend
       docker compose run --rm \\
         -v "$(cd .. && pwd):/repo" \\
         -e PYTHONPATH=/repo/backend \\
         --entrypoint python \\
         api /repo/scripts/measure_content_depth.py --practice-only

Usage:
    python scripts/measure_content_depth.py                # teaching only (no DB needed)
    python scripts/measure_content_depth.py --practice-only # practice only (needs DB, see above)
    python scripts/measure_content_depth.py --both          # both (needs DB)
"""
from __future__ import annotations

import argparse
import sys
from itertools import product
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REALIZATIONS_DIR = REPO_ROOT / "docs" / "content" / "realizations"
MANIFEST = REPO_ROOT / "scripts" / "manifest.d" / "content"

# First-pass calibration, seconds of real learner time per card, by
# teaching card `kind`. Not measured against real session telemetry yet
# (no analytics pipeline exists) -- a reasoned estimate: a bare
# vocabulary card is a few seconds' glance, a dialogue turn or reading
# passage is read/listened to and re-read, a grammar note is the
# slowest (real comprehension, not recognition).
SECONDS_PER_CARD = {
    "vocabulary": 12,
    "phrase": 15,
    "dialogue": 20,
    "grammar_note": 35,
    "reading": 45,
    "listening": 25,
}
DEFAULT_SECONDS_PER_CARD = 15  # any kind not listed above


def load_manifest_courses() -> dict[str, list[str]]:
    """course_name -> list of realization file paths, from scripts/manifest.d/content."""
    courses: dict[str, list[str]] = {}
    lines = [l for fp in sorted(MANIFEST.glob("*.txt")) for l in fp.read_text(encoding="utf-8").splitlines()]
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, realizations, _overlays = line.split("|")
        courses[name] = [REPO_ROOT / p for p in realizations.split()]
    return courses


def count_teaching_seconds(realization_path: Path) -> tuple[int, int]:
    """Returns (total_seconds, card_count) for one realization file."""
    with realization_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    total_seconds = 0
    card_count = 0
    for unit in data.get("units", []):
        for lesson in unit.get("lessons", []):
            for card in lesson.get("teaching", []):
                kind = card.get("kind", "")
                total_seconds += SECONDS_PER_CARD.get(kind, DEFAULT_SECONDS_PER_CARD)
                card_count += 1
    return total_seconds, card_count


def teaching_report() -> dict[str, dict[str, Any]]:
    courses = load_manifest_courses()
    report: dict[str, dict[str, Any]] = {}
    for name, realizations in courses.items():
        # de-dup: fa-en/nl-en/prs-en all point at the SAME shared
        # docs/content/realizations/en/*.yaml files -- count each
        # underlying file once, not once per course that reuses it.
        seen: set[Path] = set()
        total_seconds = 0
        total_cards = 0
        for path in realizations:
            if path in seen:
                continue
            seen.add(path)
            if not path.exists():
                # Uncommitted/in-flight content from a concurrent session
                # isn't necessarily present in every checkout (e.g. an
                # isolated worktree snapshot) -- skip rather than crash,
                # this is a real corpus-state gap, not a script bug.
                print(f"  (skipping missing file, not in this checkout: {path})", file=sys.stderr)
                continue
            seconds, cards = count_teaching_seconds(path)
            total_seconds += seconds
            total_cards += cards
        report[name] = {
            "teaching_cards": total_cards,
            "teaching_hours": round(total_seconds / 3600, 2),
        }
    return report


def practice_depth_report(db_url: str | None = None) -> dict[str, dict[str, Any]]:
    """Needs the real DB -- see module docstring for the docker compose
    invocation this must run under. Estimates, per course, the real
    combinatorial item space per template (product of per-slot
    candidate counts, the same base_candidates a real generation
    request computes in backend/app/practice/service.py's
    _base_slot_candidates()) rather than trusting template count."""
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.core.config import get_settings
    from app.db.session import engine as default_engine
    from app.models import Course, Lexeme, PracticeTemplate
    from app.practice.service import _base_slot_candidates

    engine = default_engine
    if db_url:
        from sqlalchemy import create_engine
        engine = create_engine(db_url)

    # Average seconds per practice item, same order of magnitude as a
    # teaching card but slightly longer (answering, not just reading) --
    # matches this project's own diminishing-XP pacing assumption of
    # roughly one item per 15-20s of real attention.
    SECONDS_PER_ITEM = 18
    # A template with an astronomically large product (e.g. 5 open
    # slots x 50 candidates each) doesn't mean 50^5 DISTINCT questions
    # feel different to a learner -- cap each template's contribution
    # at this many items, which is already far more than
    # RECENT_ITEM_LIMIT=50 (the anti-repeat window) would ever need to
    # avoid a felt repeat, so it doesn't distort the sum while still
    # correctly showing which templates are thin (below the cap).
    PER_TEMPLATE_CAP = 500

    # Aggregated by bare "{source}-{target}" direction, NOT by course id --
    # multiple Course rows can share one direction (e.g. an A1 course and
    # an A2 course both realizing "fa-en"), and their stats must be SUMMED
    # here, not overwrite each other (a real bug found live 2026-07-09:
    # fa-en/nl-en/prs-en each have both an A1 and an A2 course now, and an
    # earlier version of this function kept only whichever course's stats
    # were processed last). estimated_practice_hours is recomputed from
    # the summed estimated_unique_items at the end, not summed itself, so
    # per-course rounding doesn't compound across courses.
    raw: dict[str, dict[str, int]] = {}
    with Session(engine) as db:
        for course in db.scalars(select(Course)):
            templates = list(
                db.scalars(
                    select(PracticeTemplate).where(
                        PracticeTemplate.course_id == course.id
                    )
                )
            )
            lexemes = list(
                db.scalars(select(Lexeme).where(Lexeme.course_id == course.id))
            )
            if not templates:
                continue
            total_items = 0
            thin_templates = 0
            for template in templates:
                candidates = _base_slot_candidates(template, lexemes)
                if any(not v for v in candidates.values()):
                    continue  # ungenerable right now, contributes 0
                space = 1
                for values in candidates.values():
                    space *= len(values)
                    if space >= PER_TEMPLATE_CAP:
                        space = PER_TEMPLATE_CAP
                        break
                if space < 20:  # arbitrary "thin" threshold for the report
                    thin_templates += 1
                total_items += space
            key = f"{course.source_language}-{course.target_language}"
            agg = raw.setdefault(
                key,
                {
                    "templates": 0,
                    "thin_templates_under_20_variants": 0,
                    "estimated_unique_items": 0,
                },
            )
            agg["templates"] += len(templates)
            agg["thin_templates_under_20_variants"] += thin_templates
            agg["estimated_unique_items"] += total_items

    report: dict[str, dict[str, Any]] = {
        key: {
            **stats,
            "estimated_practice_hours": round(
                stats["estimated_unique_items"] * SECONDS_PER_ITEM / 3600, 2
            ),
        }
        for key, stats in raw.items()
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--practice-only", action="store_true")
    parser.add_argument("--both", action="store_true")
    parser.add_argument("--db-url", help="Override DATABASE_URL (default: backend/.env's)")
    args = parser.parse_args()

    do_teaching = not args.practice_only
    do_practice = args.practice_only or args.both

    if do_teaching:
        print("=== Teaching content (from YAML, no DB) ===")
        for name, stats in sorted(teaching_report().items()):
            gate = "OK" if stats["teaching_hours"] >= 10 else "SHORT"
            print(
                f"  {name:12s}  {stats['teaching_cards']:4d} cards  "
                f"~{stats['teaching_hours']:6.2f}h  [{gate} vs >=10hr gate]"
            )

    if do_practice:
        print("\n=== Practice depth (from DB, real lexeme pool) ===")
        try:
            for name, stats in sorted(practice_depth_report(args.db_url).items()):
                gate = "OK" if stats["estimated_practice_hours"] >= 10 else "SHORT"
                print(
                    f"  {name:12s}  {stats['templates']:4d} templates  "
                    f"{stats['thin_templates_under_20_variants']:3d} thin  "
                    f"~{stats['estimated_unique_items']:6d} items  "
                    f"~{stats['estimated_practice_hours']:6.2f}h  [{gate} vs >=10hr gate]"
                )
        except Exception as exc:  # pragma: no cover - reported to caller, not swallowed
            print(f"  Could not reach the DB: {exc}", file=sys.stderr)
            print(
                "  Run this half via docker compose with the repo mounted -- "
                "see this script's module docstring for the exact command "
                "(same pattern as scripts/backfill_lexemes.py).",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
