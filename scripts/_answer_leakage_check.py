#!/usr/bin/env python3
"""Answer-leakage lint (read-only): exercise text that contains its own answer.

Joins each overlay exercise (docs/content/overlays/<src>-<tgt>/*.yaml: instruction,
accepted_answers, correct_option) with its realization entry (docs/content/
realizations/<tgt>/*.yaml: type, prompt.target_blocks) by content_key, then flags
items where a correct answer appears, as a whole-token sequence, inside text shown
to the learner:
  - instruction (overlay)            -> multi-word answers (>=2 tokens) for any type;
                                        single-token answers (>=3 chars) for
                                        fill_in_blank only
  - prompt.target_blocks[].text      -> multi-word answers for any type except reading/
                                        listening comprehension (answer lives in the
                                        passage); for multiple_choice / listen_select only
                                        when the block text EQUALS the answer (the en-pl
                                        "prompt printed its own answer" class)
matching_pairs and answers/prompts in a different language never match by design
(the target-language answer string itself must appear). Practice packs are templated
and are not scanned.

Output: TSV on stdout (or --out): course, file, item_id, field, matched_answer.
Exit code is always 0 (WARN-only tool); counts per course go to stderr.

Reviewed false positives live in scripts/_answer_leakage_allowlist.tsv
(content_key <TAB> matched_answer (as printed here) <TAB> reason); they match in
every field and course and are counted on stderr, not reported.

Usage: .content-venv/bin/python3 scripts/_answer_leakage_check.py [--strip-accents] [--out FILE]
"""
from __future__ import annotations
import argparse
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT = REPO_ROOT / "docs" / "content"
CHOICE_TYPES = {"multiple_choice", "listen_select"}
SKIP_TYPES = {"matching_pairs"}
PASSAGE_TYPES = {"reading_comprehension", "listening_comprehension"}


def norm(s: str, strip_accents: bool = False) -> str:
    s = unicodedata.normalize("NFKC", s).casefold()
    if strip_accents:
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = "".join(" " if unicodedata.category(c)[0] in "PSZC" else c for c in s)
    return " ".join(s.split())


def contains(haystack: str, needle: str) -> bool:
    return bool(needle) and f" {needle} " in f" {haystack} "


def _load(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:  # noqa: BLE001
        print(f"WARN: cannot parse {path}: {e}", file=sys.stderr)
        return {}


def walk_exercises(node):
    if isinstance(node, dict):
        if "content_key" in node and "type" in node:
            yield node
        for v in node.values():
            yield from walk_exercises(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_exercises(v)


def realization_index() -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for f in sorted((CONTENT / "realizations").glob("*/*.yaml")):
        for ex in walk_exercises(_load(f).get("units")):
            idx.setdefault(ex["content_key"], ex)
    return idx


def answer_strings(ex: dict) -> list[str]:
    out = []
    for a in ex.get("accepted_answers") or []:
        if not isinstance(a, dict) or a.get("status", "correct") != "correct":
            continue
        v = a.get("value")
        if isinstance(v, list):
            v = " ".join(str(x) for x in v)
        if isinstance(v, str):
            out.append(v)
    for k in ("correct_option", "correct_response"):
        if isinstance(ex.get(k), str):
            out.append(ex[k])
    return out


def check_item(ex: dict, real: dict, strip: bool):
    """Yield (field, matched_answer) for one exercise."""
    typ = real.get("type")
    if typ in SKIP_TYPES:
        return
    answers = {norm(a, strip) for a in answer_strings(ex)}
    answers.discard("")
    fields = []
    if isinstance(ex.get("instruction"), str):
        fields.append(("instruction", norm(ex["instruction"], strip), False))
    blocks = (real.get("prompt") or {}).get("target_blocks") or []
    for i, b in enumerate(blocks):
        if isinstance(b, dict) and isinstance(b.get("text"), str):
            fields.append((f"prompt.target_blocks[{i}]", norm(b["text"], strip), True))
    for field, text, is_block in fields:
        for ans in sorted(answers):
            multi = len(ans.split()) >= 2
            if is_block and typ in PASSAGE_TYPES:
                continue  # the answer legitimately lives in the shown passage
            if is_block and typ in CHOICE_TYPES:
                # en-pl class: prompt text IS the correct option. Containment is
                # allowed to pass (e.g. "which part is the negated clause?").
                ok = text == ans
            elif multi:
                ok = True
            elif is_block:
                ok = False
            else:
                ok = typ == "fill_in_blank" and len(ans) >= 3
            if ok and contains(text, ans):
                yield field, ans


ALLOWLIST = Path(__file__).resolve().parent / "_answer_leakage_allowlist.tsv"


def load_allowlist() -> set[tuple[str, str]]:
    out = set()
    if ALLOWLIST.exists():
        for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 2:
                    out.add((parts[0], parts[1]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strip-accents", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    ridx = realization_index()
    rows = []
    allow = load_allowlist()
    skipped = 0
    for f in sorted((CONTENT / "overlays").glob("*/*.yaml")):
        course = f.parent.name
        for key, ex in (_load(f).get("exercises") or {}).items():
            real = ridx.get(key)
            if not real or not isinstance(ex, dict):
                continue
            for field, ans in check_item(ex, real, args.strip_accents):
                if (key, ans) in allow:
                    skipped += 1
                    continue
                rows.append((course, str(f.relative_to(REPO_ROOT)), key, field, ans))
    lines = ["course\tfile\titem_id\tfield\tmatched_answer"] + ["\t".join(r) for r in rows]
    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    c = Counter(r[0] for r in rows)
    print(f"answer-leakage: {len(rows)} hit(s) ({skipped} allowlisted)", file=sys.stderr)
    for k, v in sorted(c.items()):
        print(f"  {k}\t{v}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
