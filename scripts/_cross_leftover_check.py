#!/usr/bin/env python3
"""English-leftover / structure check for cross-language directions X->Y (X and Y both not English).

For every overlays/<X>-<Y> directory with X != en and Y != en, compare each overlay and practice pack with the sibling
en-<Y> file of the same name: same structure, and no learner-language string that is still English prose.
Exit 1 when anything is found.  Usage: .content-venv/bin/python3 scripts/_cross_leftover_check.py [--pairs es-fr] [--quiet]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_cross as dc  # noqa: E402


def cross_pairs() -> list[str]:
    return sorted(d.name for d in (dc.CONTENT / "overlays").iterdir()
                  if d.is_dir() and "en" not in d.name.split("-") and (dc.CONTENT / "overlays" / f"en-{d.name.split('-')[1]}").is_dir())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=lambda s: s.split(","))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    total = 0
    for pair in a.pairs or cross_pairs():
        hits = dc.learner_leftovers(pair)
        total += len(hits)
        print(f"cross-leftover {pair}: {len(hits)}")
        if not a.quiet:
            for h in hits[:100]:
                print("  " + h)
    print(f"cross-leftover total: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
