#!/usr/bin/env python3
"""Latin-script leftovers in Cyrillic (ru) target blocks of every compiled <learner>-ru course.
Usage: .content-venv/bin/python3 scripts/_cyrillic_latin_check.py [--pairs de-ru,en-ru]   Exit 1 when anything is found."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_cross as dc  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=lambda s: s.split(","))
    a = ap.parse_args()
    cm = dc.dd.read_manifest(dc.dd.MANIFEST)
    pairs = a.pairs or sorted(d.name for d in (dc.CONTENT / "overlays").iterdir() if d.is_dir() and d.name.endswith("-ru"))
    total = 0
    for pair in pairs:
        for g in (g for g in cm if g == pair or g.startswith(pair + "-")):
            reals, ovs = cm[g]
            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "c.json"
                r = subprocess.run([sys.executable, str(dc.ROOT / "scripts/compile_content.py"), "compile", "--realization", *reals,
                                    "--overlay", *ovs, "--out", str(out)], cwd=dc.ROOT, capture_output=True, text=True)
                if r.returncode:
                    print(f"{g}: compile failed")
                    total += 1
                    continue
                hits = dc.latin_in_cyrillic(out, "ru")
            total += len(hits)
            print(f"cyrillic-latin {g}: {len(hits)}")
            for h in hits[:50]:
                print("  " + h)
    print(f"cyrillic-latin total: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
