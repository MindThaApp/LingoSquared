#!/usr/bin/env python3
"""One Devanagari spelling per person name in everything Hindi (hi realization, every X-hi / hi-X overlay and practice pack, lexicon, TM).

Names are transliterated from several source languages (Elena, Mihai, Omar, Mathieu ...); without a rule the same name drifts into
two or three spellings (नीना / निना, ओमर / ओमार / उमर).  scripts/_hindi_names.tsv lists the standard spelling per name
(Latin <TAB> standard <TAB> rejected spellings).  This check flags

  1. a rejected spelling used as a whole Devanagari word, and
  2. any other word that has the same sound skeleton as a standard spelling but is spelled differently (vowel length, nukta,
     chandrabindu/anusvara, long/short matra), unless it is a known ordinary Hindi word (SAME_SOUND_OK).

Usage: python3 scripts/_hindi_name_check.py     Exit 1 when anything is found."""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "docs/content"
NAMES = Path(__file__).resolve().parent / "_hindi_names.tsv"

DEV = re.compile(r"[\u0900-\u0963\u0966-\u097F]+")  # Devanagari without the danda
# Ordinary Hindi words whose sound skeleton happens to equal a name's (not names).
SAME_SOUND_OK = {"आना", "लें", "लेन", "प्रिय", "जुली"}  # आना/लें = verbs, प्रिय = dear, मिली-जुली = mixed

_C = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "च": "c", "छ": "ch", "ज": "j", "झ": "jh", "ट": "t", "ठ": "th", "ड": "d",
      "ढ": "dh", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n", "ण": "n", "प": "p", "फ": "f", "ब": "b", "भ": "bh",
      "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "s", "ष": "s", "स": "s", "ह": "h", "ळ": "l"}
_I = {"अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o", "ऍ": "e"}
_M = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e", "ृ": "ri"}


def skeleton(word: str) -> str:
    """Rough sound key: ignores nukta, vowel length, ऑ/ओ, ं/ँ/न, final inherent 'a'."""
    w = unicodedata.normalize("NFC", word).replace("़", "")
    out, i = [], 0
    while i < len(w):
        c = w[i]
        if c in _C:
            out.append(_C[c])
            nxt = w[i + 1] if i + 1 < len(w) else ""
            if nxt == "्":
                i += 1
            elif nxt in _M:
                out.append(_M[nxt])
                i += 1
            else:
                out.append("a")
        elif c in _I:
            out.append(_I[c])
        elif c in "ंँ":
            out.append("n")
        i += 1
    s = "".join(out)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s.rstrip("a") if len(s) > 2 else s


def load():
    std, rejected = {}, {}
    for line in NAMES.read_text(encoding="utf8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split("\t")
        lat, good = p[0], p[1]
        bad = [b for b in (p[2].split(",") if len(p) > 2 and p[2] else [])]
        std[good] = lat
        for b in bad:
            rejected[b] = good
    return std, rejected


def files():
    pats = ["realizations/hi/*.yaml", "overlays/*-hi/*.yaml", "overlays/hi-*/*.yaml", "practice/*-hi/*.yaml", "practice/hi-*/*.yaml",
            "lexicon/*hi*.json", "tm/hi.json"]
    seen = set()
    for pat in pats:
        for f in sorted(CONTENT.glob(pat)):
            if f not in seen:
                seen.add(f)
                yield f


def main() -> int:
    std, rejected = load()
    sk = {}
    for good in std:
        sk.setdefault(skeleton(good), set()).add(good)
    ok_words = set(std) | SAME_SOUND_OK
    found = 0
    for f in files():
        rel = f.relative_to(CONTENT)
        for n, line in enumerate(f.read_text(encoding="utf8").splitlines(), 1):
            for w in DEV.findall(line):
                if w in ok_words or len(w) < 3:
                    continue
                if w in rejected:
                    print(f"{rel}:{n}: '{w}' -> use '{rejected[w]}' ({std[rejected[w]]})")
                    found += 1
                elif skeleton(w) in sk:
                    goods = "/".join(sorted(sk[skeleton(w)]))
                    print(f"{rel}:{n}: '{w}' sounds like name '{goods}' but is spelled differently (add to SAME_SOUND_OK if it is an ordinary word)")
                    found += 1
    print(f"hindi-name check: {found} finding(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
