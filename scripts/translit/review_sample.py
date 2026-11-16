#!/usr/bin/env python3
"""Write a reproducible review sample (default 100 multi-word target strings) for a language:
  review_sample.py --lang fa --out ~/AI/Projects/LingoSquared/.local/logs/translit-review-sample-fa.md
Draws from realization/practice strings (what learners actually see), stratified by length."""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translit.common import collect_target_strings, load_store  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--lang", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--n", type=int, default=100)
ap.add_argument("--seed", type=int, default=20261116)
a = ap.parse_args()

store = load_store(a.lang)["entries"]
real = collect_target_strings(a.lang, ("realizations", "practice"))
pool = sorted(k for k in real if k in store and len(k.split()) >= 2 and 8 <= len(k) <= 70)
rng = random.Random(a.seed)
short = [k for k in pool if len(k.split()) <= 3]
long_ = [k for k in pool if len(k.split()) > 3]
pick = rng.sample(short, min(len(short), a.n // 2)) + rng.sample(long_, min(len(long_), a.n - a.n // 2))
pick = pick[: a.n]
rng.shuffle(pick)
src = {e["source"] for e in store.values()}
lines = [
    f"# Pronunciation review sample: {a.lang} ({len(pick)} strings)",
    "",
    f"Store: docs/content/translit/{a.lang}.json ({len(store)} entries, sources: {', '.join(sorted(src))}).",
    "Scheme: docs/content/translit/SCHEME.md. Mark each row OK or write the corrected romanization.",
    "Sampled at random (seed %d) from strings learners see in realization/practice content." % a.seed,
    "",
    "| # | Script | Proposed romanization | OK / correction |",
    "|---|---|---|---|",
]
for i, k in enumerate(pick, 1):
    lines.append(f"| {i} | {k} | {store[k]['romanization']} |  |")
Path(a.out).expanduser().write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {a.out}: {len(pick)} rows")
