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

Third pass (bilingual slot reuse): in ANY frame text (prompt or feedback) a
{slot} must not appear twice -- slot_rendering is per frame, so a "target --
English" feedback frame prints the target token in both halves ("that is her
vader"). A PROMPT frame in a different language from its slot's must render the
slot via slot_rendering: english_gloss (or be a proper noun, or a quoted
"Translate using {slot}:" hint).

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
# Session 10 (2026-10-24): any further practice direction whose backfill
# follows the backfill_lexemes_<src>_<tgt>.py naming convention (en-es,
# en-de, ...) is discovered automatically, so a new direction never needs
# a hand edit here.
for _dir in sorted(p.name for p in (Path(__file__).resolve().parent.parent / "docs/content/practice").iterdir() if p.is_dir()):
    _mod = "backfill_lexemes_" + _dir.replace("-", "_")
    if (Path(__file__).resolve().parent / (_mod + ".py")).exists() and _dir not in MODULES:
        MODULES[_dir] = _mod
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


_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
# Directions whose lexeme gloss is English while the token is Persian: an
# Arabic-script character in english_gloss quotes the token (or a sibling)
# and gives translate/MC items their answer. (fa-en / prs-en glosses are
# Persian by design and are not scanned.)
ENGLISH_GLOSS_DIRECTIONS = ("en-fa", "en-prs")


def gloss_script_hits() -> int:
    """Gloss pass: english_gloss of every en-fa / en-prs spec must be English only."""
    hits = 0
    for direction in ENGLISH_GLOSS_DIRECTIONS:
        for s in specs(direction):
            g = s.get("english_gloss") or ""
            if _ARABIC_RE.search(g):
                hits += 1
                print(f"GLOSS-SCRIPT {direction} {s['content_key'][-60:]}: token={s['token'][:30]!r} "
                      f"gloss={g[:80]!r}")
    return hits


def _texts(o, path=""):
    """Yield (path, node) for every dict carrying a str `text` with a placeholder."""
    if isinstance(o, dict):
        if isinstance(o.get("text"), str) and "{" in o["text"]:
            yield path, o
        for k, v in o.items():
            yield from _texts(v, f"{path}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _texts(v, f"{path}/{i}")


def slot_reuse_hits() -> int:
    hits = 0
    for f in sorted(REPO_ROOT.glob("docs/content/practice/*/*.yaml")):
        try:
            pack = yaml.safe_load(f.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue
        for t in (pack or {}).get("templates", []) if isinstance(pack, dict) else []:
            slots = t.get("slots") or {}
            body = {k: v for k, v in t.items() if k != "slots"}
            for path, node in _texts(body):
                names = re.findall(r"\{(\w+)\}", node["text"])
                key = t.get("content_key", "")[-44:]
                dup = sorted({n for n in names if names.count(n) > 1})
                if dup:
                    hits += 1
                    print(f"SLOT-REUSE {f.parent.name}/{f.name} {key} {path}: {dup} repeated | {node['text'][:70]!r}")
                if path != "/frame":
                    continue
                rend = node.get("slot_rendering") or {}
                for n in set(names):
                    sl = slots.get(n) or {}
                    if (sl.get("language_code") in (None, node.get("language_code"))
                            or rend.get(n) in ("english_gloss", "token")
                            or sl.get("part_of_speech") == "proper_noun"
                            or node["text"].startswith("Translate using {")):
                        continue
                    hits += 1
                    print(f"SLOT-LANG {f.parent.name}/{f.name} {key}: {n!r} ({sl.get('language_code')}) "
                          f"in {node.get('language_code')} prompt without english_gloss | {node['text'][:70]!r}")
    return hits


def main() -> int:
    hits = gloss_script_hits() + slot_reuse_hits()
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
