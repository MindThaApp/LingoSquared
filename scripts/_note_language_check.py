#!/usr/bin/env python3
"""Grammar-note language check: English prose must not sit inside target-language (or learner-language) note text.

Two detectors, both over `kind: grammar_note` teaching cards:

  1. realization: the `target` text of a grammar_note in realizations/<target>/ is pl/es/fr/... -coded (cards whose block
     is coded in a learner language are skipped: overlays localize them via target_text) and is shared by
     every learner pair, so English words in it ("Gdzie (where) plus jest (is) ...", a whole English sentence) show up
     as English inside the target-language span in every X-<target> course. Flagged when it holds one STRONG English
     marker or two WEAK ones (see below). Learner-language explanations belong in the overlay (title/gloss/note).
     Parenthesised-gloss cards (see localized_gloss_card) that every non-English overlay localizes are not flagged.
  2. overlay title: for every learner language X other than English, a grammar_note `title` in X-<target> overlays
     identical to the en-<target> title (i.e. never translated) and containing English words is flagged.

Existing violations in other targets / levels are recorded in scripts/_note_language_baseline.tsv (kind<TAB>key). The
check fails on any hit not in the baseline, and on any baseline entry that no longer hits (remove it when fixed), so
the list can only shrink.

Usage: .content-venv/bin/python3 scripts/_note_language_check.py [--list] [--write-baseline]   Exit 1 on new/stale hits."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "docs" / "content"
BASELINE = ROOT / "scripts" / "_note_language_baseline.tsv"
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# STRONG: English words that are not words of any target language we ship (pl/es/fr/it/de/nl/ro/ru/hi/ar/fa/prs, Latin
# transliterations included). WEAK: English function words; two of them in one text mean English prose.
STRONG = set("""the with means where how then please infinitive imperative genitive locative good but prefer hurt feel
because while whose which should would could shall usually always never whenever instead between before after again
those these there their they them been being does doing someone something cheapest afterward nevertheless however
believe think recommend seems""".split())
WEAK = set("""are and for you your it this that from when will have has used use going get not can plus is""".split())
# Learner-language titles are short, so a single English word identical to the en-<target> title is enough.
TITLE_EN = STRONG | WEAK | set("to go by of at or if be the".split())
# WEAK words that are also ordinary words of a target language: never counted for that target.
WEAK_SHARED = {
    "pl": {"plus"},
    "nl": {"is", "plus"},
    "de": {"is", "plus"},
    "es": {"plus"},
    "fr": {"plus"},
    "ro": {"plus"},
    "it": {"plus"},
}
# STRONG words that are also ordinary words of a target language (Romanian "prefer" = "I prefer"): never counted there.
STRONG_SHARED = {"ro": {"prefer"}}

WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")


def load(path: Path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER)


def english_hits(text: str, target: str | None) -> list[str]:
    words = [w.lower() for w in WORD.findall(re.sub(r"[*_]", "", text))]
    strong = [w for w in words if w in STRONG and w not in STRONG_SHARED.get(target or "", set())]
    weak = [w for w in words if w in WEAK and w not in WEAK_SHARED.get(target or "", set())]
    if strong or len(weak) >= 2:
        return strong + weak
    return []


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


# Parenthesised-gloss cards (session 20 group 3): a Arabic/Devanagari-script word list such as 'کجا (where)' whose only
# English sits inside parentheses. For English learners the parenthesis is the learner gloss; the compiler lets every other
# X-<target> overlay replace the whole body with `target_text` (compile_content._target_block_with_learner_gloss). Such a card
# is not English prose in a target span as long as every existing non-English overlay of that unit does localize it.
GLOSS_SCRIPT_TARGETS = {"ar", "fa", "prs", "hi"}
_NONLATIN = re.compile(r"[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff\u0900-\u097f]")
_PAREN_GLOSS = re.compile(r"\([^()]*[A-Za-z]{2}[^()]*\)")
_overlay_cache: dict[Path, dict] = {}


def _teaching_overlay(path: Path, key: str):
    if path not in _overlay_cache:
        found: dict = {}
        for node in walk(load(path)):
            for k, v in node.items():
                if isinstance(k, str) and k.count(".") >= 4 and isinstance(v, dict):
                    found[k] = v
        _overlay_cache[path] = found
    return _overlay_cache[path].get(key)


def localized_gloss_card(target: str, key: str, text: str) -> bool:
    """True for a parenthesised-gloss card whose English is only the parenthesised gloss and which every existing
    non-English X-<target> overlay of its unit replaces with `target_text`."""
    if target not in GLOSS_SCRIPT_TARGETS or not _NONLATIN.search(text) or not _PAREN_GLOSS.search(text):
        return False
    if english_hits(_PAREN_GLOSS.sub("", text), target):
        return False
    parts = key.split(".")  # <target>.<level>.<unit>...
    fname = f"{parts[1]}_{parts[2]}.yaml"
    for pair in sorted((CONTENT / "overlays").glob(f"*-{target}")):
        if pair.name.startswith("en-") or not (pair / fname).exists():
            continue
        entry = _teaching_overlay(pair / fname, key)
        if not (entry and entry.get("target_text")):
            return False
    return True


def realization_hits() -> dict[str, str]:
    hits: dict[str, str] = {}
    for f in sorted((CONTENT / "realizations").glob("*/*.yaml")):
        target = f.parent.name
        if target == "en":
            continue
        for node in walk(load(f)):
            if node.get("kind") == "grammar_note" and "content_key" in node:
                block = node.get("target") or {}
                # A block coded in a learner language (language_code != target, e.g. es notes written in English) is
                # not target-coded prose: the compiler requires every X-<target> overlay to localize it via target_text.
                if block.get("language_code") not in (None, target):
                    continue
                text = block.get("text", "")
                if text and english_hits(text, target) and not localized_gloss_card(target, node["content_key"], text):
                    hits[f"realization\t{node['content_key']}"] = text
    return hits


def title_hits() -> dict[str, str]:
    notes: dict[str, set[str]] = {}
    for f in sorted((CONTENT / "realizations").glob("*/*.yaml")):
        keys = {n["content_key"] for n in walk(load(f)) if n.get("kind") == "grammar_note" and "content_key" in n}
        notes.setdefault(f.parent.name, set()).update(keys)

    def titles(pair_dir: Path, target: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for f in sorted(pair_dir.glob("*.yaml")):
            for node in walk(load(f)):
                for key, val in node.items():
                    if key in notes.get(target, ()) and isinstance(val, dict) and isinstance(val.get("title"), str):
                        out[key] = val["title"]
        return out

    hits: dict[str, str] = {}
    for en_dir in sorted((CONTENT / "overlays").glob("en-*")):
        target = en_dir.name.split("-", 1)[1]
        en_titles = titles(en_dir, target)
        for pair_dir in sorted((CONTENT / "overlays").glob(f"*-{target}")):
            if pair_dir == en_dir:
                continue
            for key, title in titles(pair_dir, target).items():
                if title == en_titles.get(key) and any(w.lower() in TITLE_EN for w in WORD.findall(title)):
                    hits[f"title:{pair_dir.name}\t{key}"] = title
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print every hit, baselined or not")
    ap.add_argument("--write-baseline", action="store_true")
    a = ap.parse_args()
    hits = {**realization_hits(), **title_hits()}
    if a.write_baseline:
        BASELINE.write_text("".join(f"{k}\n" for k in sorted(hits)), encoding="utf-8")
        print(f"wrote {len(hits)} baseline entries")
        return 0
    baseline = {l.rstrip("\n") for l in BASELINE.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")} if BASELINE.exists() else set()
    new = sorted(set(hits) - baseline)
    stale = sorted(baseline - set(hits))
    if a.list:
        for k in sorted(hits):
            print(("  " if k in baseline else "NEW ") + k + "  |  " + hits[k][:100])
    for k in new:
        print(f"note-language: English prose in grammar note: {k}  |  {hits[k][:120]}")
    for k in stale:
        print(f"note-language: baseline entry no longer hits (remove it): {k}")
    print(f"note-language: {len(hits)} hit(s), {len(baseline)} baselined, {len(new)} new, {len(stale)} stale")
    return 1 if new or stale else 0


if __name__ == "__main__":
    sys.exit(main())
