#!/usr/bin/env python3
"""Warn about matching exercises whose left and right sides are identical.

A pair such as had/had or water/water gives the answer away. Comparison is
case-, diacritic- and punctuation-insensitive. Warning-level only: the corpus
contains known instances, so this never fails (exit code is always 0).

Usage:
    .content-venv/bin/python3 scripts/_matching_pairs_identical_check.py [--summary]
"""
from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
OVERLAYS_DIR = REPO_ROOT / "docs/content/overlays"
WORD_RE = re.compile(r"\w+", re.UNICODE)
_Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
# Courses between closely related languages sharing a script legitimately
# contain identical words (Persian/Dari/Arabic); they are reported separately.
RELATED = {"ar", "fa", "prs"}


def is_related_course(course: str) -> bool:
    parts = course.split("-")
    return len(parts) == 2 and parts[0] in RELATED and parts[1] in RELATED


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value)).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(WORD_RE.findall(value))


def is_identical(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    n = normalize(left)
    return bool(n) and n == normalize(right)


def find_identical_pairs(overlays_dir: Path = OVERLAYS_DIR) -> list[tuple[str, str, str, str]]:
    """Return (course, file, content_key, word) for every identical pair."""
    found: list[tuple[str, str, str, str]] = []
    for path in sorted(overlays_dir.glob("*/*.yaml")):
        if is_related_course(path.parent.name):
            continue
        doc = yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)
        exercises = doc.get("exercises") if isinstance(doc, dict) else None
        if not isinstance(exercises, dict):
            continue
        for key, ex in exercises.items():
            if not isinstance(ex, dict):
                continue
            for answer in ex.get("accepted_answers") or []:
                value = answer.get("value") if isinstance(answer, dict) else None
                if not isinstance(value, dict):
                    continue
                for left, right in value.items():
                    if is_identical(left, right):
                        found.append((path.parent.name, path.name, str(key), str(left)))
    return found


def main() -> int:
    found = find_identical_pairs()
    summary = "--summary" in sys.argv
    if not summary:
        for course, name, key, word in found:
            print(f"WARN: {course}/{name}: {key} identical pair {word!r}")
    counts = Counter(course for course, *_ in found)
    for course, n in counts.most_common():
        print(f"  {course}: {n}")
    print(f"Matching-pairs identical check: {len(found)} identical pair(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
