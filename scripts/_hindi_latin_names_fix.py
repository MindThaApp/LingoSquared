#!/usr/bin/env python3
"""Rewrite Latin-script person names inside Hindi text to their standard Devanagari spelling (scripts/_hindi_names.tsv) and
replace rejected Devanagari spellings.  Uses the same detector as scripts/_hindi_name_check.py, so what this script fixes is
exactly what the check flags.  Run it on new hi-X / X-hi content before opening a PR; idempotent.

Usage: python3 scripts/_hindi_latin_names_fix.py [--dry-run] [paths...]   (default: every file the check covers)"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _hindi_name_check as hn  # noqa: E402


def standard_by_latin():
    out = {}
    for line in hn.NAMES.read_text(encoding="utf8").splitlines():
        if line.strip() and not line.startswith("#"):
            p = line.split("\t")
            out.setdefault(p[0], p[1])
    return out


def fix_text(text, names, std, rules, rel, *, target, key_skip):
    """Return text with Latin names inside Hindi text converted (non-overlapping spans, applied right to left)."""
    if hn.allowed(rel, text, rules):
        return text
    spans = hn.latin_names(text, names, target=target, key_line_skip=key_skip)
    for a, b, w in sorted(spans, reverse=True):
        text = text[:a] + std[w] + text[b:]
    return text


def fix_file(f: Path, std, names, rules, rejected_rx, rejected):
    rel = f.relative_to(hn.CONTENT).as_posix()
    target = hn.is_target_file(rel)
    raw = f.read_text(encoding="utf8")
    out = []
    is_json = rel.startswith(("lexicon/", "tm/"))
    for line in raw.split("\n"):
        new = line
        if is_json:
            m = re.fullmatch(r'(\s*)("(?:[^"\\]|\\.)*")(\s*:\s*)("(?:[^"\\]|\\.)*")(,?)', line)
            if m:
                val = json.loads(m.group(4))
                nv = fix_text(val, names, std, rules, rel, target=target, key_skip=False)
                if nv != val:
                    new = m.group(1) + m.group(2) + m.group(3) + json.dumps(nv, ensure_ascii=False) + m.group(5)
        else:
            new = fix_text(line, names, std, rules, rel, target=target, key_skip=rel.startswith("overlays/hi-"))
        out.append(new)
    res = "\n".join(out)
    res = rejected_rx.sub(lambda m: rejected[m.group(0)], res)
    return raw, res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args()
    std = standard_by_latin()
    names = hn.latin_name_set()
    rules = hn.load_allow()
    _, rejected = hn.load()
    rejected_rx = re.compile(r"(?<![ऀ-ॿ])(" + "|".join(sorted(map(re.escape, rejected), key=len, reverse=True)) + r")(?![ऀ-ॿ])")
    targets = [Path(p).resolve() for p in a.paths] if a.paths else list(hn.files())
    changed = 0
    for f in targets:
        for _ in range(3):  # fixpoint: a converted name can make a neighbouring name "adjacent to Devanagari"
            raw, res = fix_file(f, std, names, rules, rejected_rx, rejected)
            if raw == res:
                break
            changed += raw != res
            if not a.dry_run:
                f.write_text(res, encoding="utf8")
            else:
                break
    print(f"hindi-latin-names fix: {changed} file pass(es) changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
