#!/usr/bin/env python3
"""One Devanagari spelling per person name in everything Hindi (hi realization, every X-hi / hi-X overlay and practice pack, lexicon, TM).

Names are transliterated from several source languages (Elena, Mihai, Omar, Mathieu ...); without a rule the same name drifts into
two or three spellings (नीना / निना, ओमर / ओमार / उमर).  scripts/_hindi_names.tsv lists the standard spelling per name
(Latin <TAB> standard <TAB> rejected spellings).  This check flags

  1. a rejected spelling used as a whole Devanagari word, and
  2. any other word that has the same sound skeleton as a standard spelling but is spelled differently (vowel length, nukta,
     chandrabindu/anusvara, long/short matra), unless it is a known ordinary Hindi word (SAME_SOUND_OK), and
  3. a Latin-script person name sitting inside Hindi text ("Mihai कहता है", "मेरा नाम Ana है") -- in Hindi text every name is
     written in Devanagari.  A name counts as "inside Hindi text" when its nearest non-name neighbour is a Devanagari word and
     neither side is a Latin word (so "Ik heet Noor सीधे ..." and *Ich heiße Anna* stay: those are target-language text).
     Lines where Hindi is the TARGET language (realizations/hi, X-hi overlays/packs) are English/German/... prose around Hindi
     quotes; there the check only looks at lines that are mostly Devanagari.  Intended exceptions (a brand, an explicit
     transliteration exercise) go in scripts/_hindi_latin_name_allowlist.tsv (path <TAB> needle <TAB> reason; needle = substring
     of the line, * = whole file) or carry the marker "hindi-latin-name-ok" on the same line.

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
SAME_SOUND_OK = {"आना", "लें", "लेन", "प्रिय", "जुली", "याँ", "जोश", "सार"}  # आना/लें = verbs, प्रिय = dear, मिली-जुली = mixed, सार = summary, जोश = enthusiasm, याँ = plural-ending fragment

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


LATIN_WORD = re.compile(r"[A-Za-z\u00c0-\u00ff]")
TOKEN = re.compile(r"\S+")
NAME_TOKEN = re.compile(r"[\W_]*([A-Z\u00c0-\u00dd][A-Za-z\u00c0-\u00ff]+)(?:['\u2019]s)?[\W_]*")
SENT_END = re.compile(r"[.?!][\"'\u2019\u201d*)]*:?$")
FLOW_TEXT = re.compile(r"\s*-?\s*\{[^\"]*?\btext:\s*(?=\")")
YAML_KEY = re.compile(r"\s*(?:-\s+)?[a-z_][a-z0-9_]*:(?=\s)")
ALLOWLIST = Path(__file__).resolve().parent / "_hindi_latin_name_allowlist.tsv"
OK_MARKER = "hindi-latin-name-ok"


def latin_names(line: str, names, *, target: bool = False, key_line_skip: bool = False):
    """Spans (start, end, name) of Latin-script person names that sit inside Hindi text on this line.

    target=True: Hindi is the course's target language, so the surrounding prose is English/German/...; only mostly-Devanagari
    lines are considered.  key_line_skip: a mapping key at the start of the line (`Elena: 31 साल की`) is target-language data."""
    if OK_MARKER in line or not DEV.search(line):
        return []
    if target:
        body = line.split('text: "', 1)[-1]  # flow-style `{content_key: ..., text: "..."}`: judge the quoted text only
        dev = len(re.findall(r"[\u0900-\u097F]", body))
        lat = len(re.findall(r"[A-Za-z]", body))
        if dev < 2 * lat or line.lstrip().startswith("#"):
            return []
    toks = [(m.start(), m.end(), m.group()) for m in TOKEN.finditer(line)]
    kind = ["D" if DEV.search(t) else ("L" if LATIN_WORD.search(t) else "P") for _, _, t in toks]
    flow = FLOW_TEXT.match(line)  # `- {content_key: x, language: hi, text: "...` -- the keys before the quoted text are syntax
    if flow:
        kind = ["P" if toks[i][0] < flow.end() else k for i, k in enumerate(kind)]
    pre = YAML_KEY.match(line)  # a leading `title:` / `- gloss:` is YAML syntax, not a Latin word
    if pre:
        kind = ["P" if toks[i][0] < pre.end() else k for i, k in enumerate(kind)]

    def is_name(t):
        m = NAME_TOKEN.fullmatch(t.strip("*\"'\u2018\u2019\u201c\u201d\u201e()[]{}:;,\u2014\u2013-"))
        return bool(m) and m.group(1) in names

    def side(i, step):
        if step == 1 and SENT_END.search(toks[i][2]):
            return "none"
        j = i + step
        while 0 <= j < len(toks):
            if kind[j] == "D":
                return "D"
            if kind[j] == "P":
                j += step
                continue
            if step == -1 and SENT_END.search(toks[j][2]):
                return "none"
            if is_name(toks[j][2]):
                if step == 1 and SENT_END.search(toks[j][2]):
                    return "none"
                j += step
                continue
            return "L"
        return "none"

    out = []
    for i, (s0, _e0, t) in enumerate(toks):
        if kind[i] != "L":
            continue
        m = NAME_TOKEN.fullmatch(t)
        if not m or m.group(1) not in names:
            continue
        if key_line_skip and i == 0 and t.endswith(":") or (key_line_skip and i == 1 and toks[0][2] == "-" and t.endswith(":")):
            continue
        if target and i == len(toks) - 1 and i > 0 and kind[i - 1] == "D" and toks[i - 1][2].endswith(":"):
            continue  # `अर्जुन: Arjun` -- a Hindi word glossed by its Latin form (the answer side of an English-learner pair)
        left, right = side(i, -1), side(i, 1)
        if "L" in (left, right) or "D" not in (left, right):
            continue
        a = s0 + t.index(m.group(1))
        out.append((a, a + len(m.group(1)), m.group(1)))
    return out


def load_allow():
    rules = []
    if ALLOWLIST.exists():
        for line in ALLOWLIST.read_text(encoding="utf8").splitlines():
            if line.strip() and not line.startswith("#"):
                p = line.split("\t")
                rules.append((p[0], p[1] if len(p) > 1 else "*"))
    return rules


def allowed(rel: str, line: str, rules) -> bool:
    return any(rel == r and (n == "*" or n in line) for r, n in rules)


def is_target_file(rel: str) -> bool:
    """Hindi is the target language: realizations/hi, *-hi overlays and practice packs (X-hi)."""
    parts = rel.split("/")
    return parts[0] == "realizations" or (len(parts) > 1 and parts[1].endswith("-hi"))


def latin_name_set():
    return {l.split("\t")[0] for l in NAMES.read_text(encoding="utf8").splitlines() if l.strip() and not l.startswith("#")}


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


def json_strings(o, path=""):
    """Yield every string VALUE of a parsed JSON document (keys are source-language text)."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from json_strings(v, f"{path}/{k}")
    elif isinstance(o, list):
        for v in o:
            yield from json_strings(v, path)
    elif isinstance(o, str):
        yield o


def latin_findings(f: Path, names, rules):
    """(line number, name, text) for each Latin person name inside Hindi text of one content file."""
    rel = f.relative_to(CONTENT).as_posix()
    if rel.startswith("lexicon/") or rel.startswith("tm/"):
        import json
        src = (s for s in json_strings(json.loads(f.read_text(encoding="utf8"))))
        items = enumerate(src, 1)
        key_skip = False
    else:
        items = enumerate(f.read_text(encoding="utf8").splitlines(), 1)
        key_skip = rel.startswith("overlays/hi-")
    target = is_target_file(rel)
    for n, text in items:
        for _a, _b, w in latin_names(text, names, target=target, key_line_skip=key_skip):
            if not allowed(rel, text, rules):
                yield n, w, text


def main() -> int:
    std, rejected = load()
    names = latin_name_set()
    rules = load_allow()
    sk = {}
    for good in std:
        sk.setdefault(skeleton(good), set()).add(good)
    ok_words = set(std) | SAME_SOUND_OK
    found = 0
    for f in files():
        rel = f.relative_to(CONTENT)
        for n, w, text in latin_findings(f, names, rules):
            print(f"{rel}:{n}: Latin name '{w}' inside Hindi text -> write it in Devanagari ({'/'.join(sorted(d for d, l in std.items() if l == w)) or w})")
            found += 1
        for n, line in enumerate(f.read_text(encoding="utf8").splitlines(), 1):
            for w in DEV.findall(line):
                if w in ok_words or len(w) < 3 or "\u093e" <= w[0] <= "\u094f":  # a word never starts with a vowel sign (plural-suffix fragments)
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
