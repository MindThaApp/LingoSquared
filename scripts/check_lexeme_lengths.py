#!/usr/bin/env python3
"""Fail if any lexeme spec emitted by a scripts/backfill_lexemes*.py source
exceeds its DB column length (lexemes.* String(N) in backend/app/models/entities.py).

Postgres rejects the whole backfill transaction on overflow (StringDataRightTruncation),
so this must be caught before deploy. Pure Python, no DB needed.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parent / "backend"))

LIMITS = {
    "token": 255,
    "part_of_speech": 40,
    "english_gloss": 255,
    "lesson_content_key": 255,
    "content_key": 255,
}


def check_specs(specs, source="specs"):
    problems = []
    for spec in specs:
        for field, limit in LIMITS.items():
            value = spec.get(field)
            if isinstance(value, str) and len(value) > limit:
                key = spec.get("content_key") or spec.get("token")
                problems.append(f"{source}: {field} is {len(value)} chars (max {limit}) in {key}")
    return problems


def main() -> int:
    problems = []
    n = 0
    for path in sorted(SCRIPTS.glob("backfill_lexemes*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "iter_specs"):
            continue
        n += 1
        problems += check_specs(module.iter_specs(), path.name)
    for p in problems:
        print("ERROR:", p)
    print(f"check_lexeme_lengths: {n} backfill sources, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
