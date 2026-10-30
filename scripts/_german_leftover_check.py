#!/usr/bin/env python3
"""German-leftover check for derived learner-language overlays and practice packs.

A direction X-Y is learner-language X, target Y. Every overlay / practice pack of
a direction with X != de must not carry German text: derive_direction.py copies the
de-en overlay and translates only strings it classifies as learner-language, so
anything misclassified (historically: teaching-card titles, which were assumed to be
English target text) survives untranslated and is shown to learners.

Two detectors, both applied to every string leaf of overlays/<X>-<Y>/*.yaml and
practice/<X>-<Y>/*.yaml (X != de, X != en):
  1. sibling-equal: the string is byte-identical to the string at the same path in
     the de-en overlay of the same unit, and is not English (english_fraction < 0.9
     against the English realizations' vocabulary);
  2. German markers: >= 2 distinctive German function words, a single one in a
     string of <= 4 words, or an umlaut/eszett plus one function word.
     Detector 2 skips X in {nl} for the shared words (Dutch overlaps German).

Exit 1 when anything is found. Usage:
    .content-venv/bin/python3 scripts/_german_leftover_check.py [--pairs es-en,fr-en] [--quiet]
"""
from __future__ import annotations

import argparse
import functools
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import derive_direction as dd  # noqa: E402

CONTENT = dd.CONTENT
# Distinctive German function words (not valid in es/fr/it/pt/ro/pl/ru/hi/ar/ko/ja/zh/en).
DE_WORDS = set("""und nicht ich ist sind ein eine einen einem einer mit für zu zum zur von wird werden wir sie
auch nach dem den dass oder aber wenn weil über wie noch nur sehr bitte danke habe haben bist
fragt sagt gibt kann muss möchte möchtest ihr ihre ihren sich mir mich dir dich uns euch beim aufs
soll sollen kein keine Gespräch Frage Antwort Beispiel Wort Wörter Satz Sätze Grundform Partizip Zahl Zahlen""".lower().split())
UMLAUT = re.compile(r"[äöüßÄÖÜ]")
TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)
# Dutch shares many tokens with German; only the strongest signals apply there.
DUTCH_SAFE = set("und ich ist ein eine mit für zu zum zur von wir auch nach dass oder aber wenn weil über noch nur sehr".split()) - {"ik"}


def german_markers(text: str, learner: str, target: str = "") -> bool:
    toks = [t.lower() for t in TOKEN.findall(re.sub(r"\{[^}]*\}", " ", text))]
    if not toks:
        return False
    words = DUTCH_SAFE if learner == "nl" else DE_WORDS
    if target == "nl":
        words = words - {"wie"}          # Dutch "Met wie spreek ik?" is target text of X-nl pairs
    if learner == "fr":
        words = words - {"uns"}          # "quelques-uns", "les uns"
    hits = [t for t in toks if t in words]
    if len(hits) >= 2:
        return True
    if len(hits) == 1 and (len(toks) <= 4 or UMLAUT.search(text)):
        return True
    return False


REAL = {re.match(r"(\w+?_unit\d+)", q.name).group(1): q for q in (CONTENT / "realizations" / "en").glob("*.yaml")}


@functools.lru_cache(maxsize=None)
def _ridx(stem: str) -> dict:
    return dd.realization_index(REAL[stem]) if stem in REAL else {}


@functools.lru_cache(maxsize=None)
def _sib(kind: str, name: str) -> dict:
    sib = CONTENT / kind / "de-en" / name
    return dict(dd.walk_strings(dd.load(sib))) if sib.exists() else {}


def _walk(node, path=()):
    yield from dd.walk_strings(node, path)


def scan_pair(pair: str, quiet: bool = False) -> list[str]:
    learner = pair.split("-")[0]
    if pair.endswith("-de") and learner not in ("de", "en"):
        # German is the TARGET of a cross pair (es-de ...): overlays and packs legitimately carry German options,
        # answers and quoted examples, so a German-marker scan cannot tell leftovers from target text. The English
        # learner-language residue of such pairs is gated by scripts/_cross_leftover_check.py instead.
        return []
    out: list[str] = []
    for kind in ("overlays", "practice"):
        d = CONTENT / kind / pair
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.yaml")):
            y = dd.load(p)
            sib_vals: dict[tuple, str] = {}
            ridx = _ridx(p.stem)
            sib_vals = _sib(kind, p.name)
            for path, v in _walk(y):
                if not dd.has_words(v) or path[0] in ("generation_provenance", "review", "status"):
                    continue
                if kind == "overlays" and dd.overlay_role(path) is None:
                    continue
                sibling_equal = False
                if kind == "overlays" and sib_vals.get(path) == v and learner != "nl":
                    role = dd.overlay_role(path)
                    if path[0] == "teaching" and role == "title":
                        tgt = ridx.get(path[1], {}).get("target", "")
                        sibling_equal = not dd.teaching_title_is_english(v, tgt)
                    elif role == "title" or role in dd.ALWAYS_LEARNER:
                        sibling_equal = dd.english_fraction(v) < 0.9
                if sibling_equal or german_markers(v, learner, pair.split("-")[1]):
                    out.append(f"{pair} {kind}/{p.name}: {'/'.join(map(str, path))[:90]}: {v[:90]!r}")
    return out


def derived_pairs() -> list[str]:
    ps = []
    for d in sorted((CONTENT / "overlays").iterdir()):
        if d.is_dir() and d.name.split("-")[0] not in ("de", "en"):
            ps.append(d.name)
    return ps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=lambda s: s.split(","))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    total = 0
    for pair in a.pairs or derived_pairs():
        hits = scan_pair(pair)
        total += len(hits)
        print(f"german-leftover {pair}: {len(hits)}")
        if not a.quiet:
            for h in hits[:200]:
                print("  " + h)
    print(f"german-leftover total: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
