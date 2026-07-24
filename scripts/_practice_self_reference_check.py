#!/usr/bin/env python3
"""Self-reference check for word_order practice templates (recipe defect 1.14 / §6.4).

A word_order frame's literal (non-placeholder) text must not contain a word that is
also a UNIT-scoped candidate for one of that frame's own slots. Two failure modes:
  - genuine self-reference: "It's ten past {item}" with 'ten' in item's pool -> the
    word bank shows two identical tiles and the answer is ambiguous;
  - invariant-answer: a frame with NO {slot} placeholder but a declared multi-member
    slot -> every render is the same fixed string, so the learner is credited toward
    a lexeme that never actually varied (SRS mis-attribution).

Candidates are scoped to the pack's own unit (matching generate_checkpoint). Single-
character candidate pools (letter-ordering spelling exercises, where the letters ARE
the content) are excluded -- they are legitimately made of their own tiles.

Usage: .content-venv/bin/python3 scripts/_practice_self_reference_check.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

MODULES = {
    "en-fa": "backfill_lexemes", "en-prs": "backfill_lexemes_en_prs",
    "en-nl": "backfill_lexemes_en_nl", "fa-en": "backfill_lexemes_fa_en",
    "prs-en": "backfill_lexemes_prs_en", "nl-en": "backfill_lexemes_nl_en",
}
_UNIT_RE = re.compile(r"(a1|a2|b1|b2)_unit(\d+)")
_WORD_RE = re.compile(r"[^\s{}.,،؟?!:;\"'()]+")
_specs: dict[str, list] = {}


def specs(direction: str) -> list:
    if direction not in _specs:
        import importlib
        _specs[direction] = list(importlib.import_module(MODULES[direction]).iter_specs())
    return _specs[direction]


def _match(lx: dict, c: dict) -> bool:
    if lx["language_code"] != c.get("language_code"):
        return False
    pos = c.get("part_of_speech")
    if pos and not ({lx["part_of_speech"]} & (set(pos) if isinstance(pos, list) else {pos})):
        return False
    tags = lx.get("agreement_tags") or {}
    for t, req in (c.get("agreement_tags") or {}).items():
        if t not in tags:
            return False
        rv = set(req) if isinstance(req, list) else {req}
        av = tags[t]
        av = set(av) if isinstance(av, list) else {av}
        if not (rv & av):
            return False
    return True


def _frame_text(fr) -> str:
    if isinstance(fr, dict):
        if isinstance(fr.get("text"), str):
            return fr["text"]
        return " ".join(_frame_text(v) for v in fr.values())
    if isinstance(fr, list):
        return " ".join(_frame_text(x) for x in fr)
    return fr if isinstance(fr, str) else ""


def main() -> int:
    hits = 0
    scanned = 0
    for f in sorted(REPO_ROOT.glob("docs/content/practice/*/*.yaml")):
        direction = f.parent.name
        if direction not in MODULES:
            continue
        m = _UNIT_RE.search(f.stem)
        if not m:
            continue
        unit_key = f".{m.group(1)}.unit{m.group(2)}."
        try:
            pack = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(pack, dict):
            continue
        unit_lex = [s for s in specs(direction) if unit_key in s["lesson_content_key"]]
        for t in pack.get("templates", []):
            if t.get("type") != "word_order":
                continue
            scanned += 1
            txt = _frame_text(t.get("frame"))
            literals = set(_WORD_RE.findall(re.sub(r"\{[^}]*\}", " ", txt)))
            for sn, c in (t.get("slots") or {}).items():
                cands = {lx["token"] for lx in unit_lex if _match(lx, c)}
                if cands and max(len(x) for x in cands) <= 1:
                    continue  # letter-ordering spelling task -- tiles ARE the content
                bad = cands & literals
                if bad:
                    hits += 1
                    print(f"SELF-REF {direction}/{f.name} {t.get('content_key', '')[-44:]}: "
                          f"slot {sn!r} candidate(s) {bad} appear as literal frame words | frame={txt[:70]!r}")
    print(f"\nscanned {scanned} word_order frames; {hits} self-reference/invariant-answer hit(s).")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
