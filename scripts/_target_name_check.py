#!/usr/bin/env python3
"""Wrong-language-name check for cross pairs (X->Y, neither side English).

A generic instruction such as "Put the words in order to say '...'" can pick up "in Spanish" / "in German" from the
translation memory of an earlier target and then ends up in a pair whose target is French.  This check flags, in every
cross pair's overlays and practice packs, a language name (English, or written in the learner's own language) that is
not the pair's target language.

Not flagged: the learner language X itself (contrast notes), and any language the en->Y sibling file of the same name
mentions in English on 3+ lines (a unit that is about that language; for English itself on any line, since
'Do you speak English?' is ordinary A1 content).  Lines copied verbatim from the sibling are ignored.  Everything else needs an entry in
scripts/_target_name_allowlist.tsv (path <TAB> language <TAB> needle <TAB> reason; needle = substring of the line, or * for the whole file).

Usage: python3 scripts/_target_name_check.py [--pairs hi-nl,ar-ru]   Exit 1 when anything is found."""
from __future__ import annotations

import argparse
import functools
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "docs/content"
ALLOWLIST = Path(__file__).resolve().parent / "_target_name_allowlist.tsv"

LANGS = ["en", "nl", "fr", "de", "it", "es", "ru", "pl", "ro", "zh", "ja", "ko", "ar", "fa", "prs", "hi"]

# English names; a lowercase-insensitive whole-word match.
EN = {
    "en": r"English", "nl": r"Dutch", "fr": r"French", "de": r"German", "it": r"Italian", "es": r"Spanish",
    "ru": r"Russian", "pl": r"Polish", "ro": r"Romanian", "zh": r"Chinese", "ja": r"Japanese",
    "ko": r"Korean", "ar": r"Arabic", "fa": r"Persian", "prs": r"Dari", "hi": r"Hindi",
}
# Names in the learner's own language: LOCAL[learner][language] = regex.  Latin-script learners use word
# boundaries; the check lower-cases nothing, so each pattern lists its capitalised form where it matters.
LOCAL = {
    "de": {"en": r"Englisch", "nl": r"Niederländisch|Holländisch", "fr": r"Französisch", "it": r"Italienisch", "es": r"Spanisch",
           "ru": r"Russisch", "pl": r"Polnisch", "ro": r"Rumänisch"},
    "es": {"en": r"inglés", "nl": r"neerlandés|holandés", "fr": r"francés", "de": r"alemán", "it": r"italiano",
           "ru": r"ruso", "pl": r"polaco", "ro": r"rumano"},
    "fr": {"en": r"anglais", "nl": r"néerlandais|hollandais", "de": r"allemand", "it": r"italien", "es": r"espagnol",
           "ru": r"russe", "pl": r"polonais", "ro": r"roumain"},
    "it": {"en": r"inglese", "nl": r"olandese", "fr": r"francese", "de": r"tedesco", "es": r"spagnolo",
           "ru": r"russo", "pl": r"polacco", "ro": r"romeno"},
    "nl": {"en": r"Engels", "fr": r"Frans", "de": r"Duits", "it": r"Italiaans", "es": r"Spaans", "ru": r"Russisch",
           "pl": r"Pools", "ro": r"Roemeens"},
    "pl": {"en": r"angielski\w*", "nl": r"holender\w*|niderlandzk\w*", "fr": r"francusk\w*", "de": r"niemieck\w*", "it": r"włosk\w*",
           "es": r"hiszpańsk\w*", "ru": r"rosyjsk\w*", "ro": r"rumuńsk\w*"},
    "ro": {"en": r"engle[zj]\w*", "nl": r"olandez\w*", "fr": r"francez\w*", "de": r"german[ăa]\b|germane\b", "it": r"italian[ăa]\b|italiene\b",
           "es": r"spaniol\w*", "ru": r"rusă\b|rusesc\w*", "pl": r"polonez\w*"},
    "ru": {"en": r"[Аа]нглийск\w*", "nl": r"[Нн]идерландск\w*|[Гг]олландск\w*", "fr": r"[Фф]ранцузск\w*", "de": r"[Нн]емецк\w*",
           "it": r"[Ии]тальянск\w*", "es": r"[Ии]спанск\w*", "pl": r"[Пп]ольск\w*", "ro": r"[Рр]умынск\w*"},
    "ar": {"en": r"الإنجليزية|الانجليزية|إنجليزي|انجليزي", "nl": r"الهولندية|هولندي(?!ا)", "fr": r"الفرنسية|فرنسي(?!ا)", "de": r"الألمانية|ألماني(?!ا)|الالمانية",
           "it": r"الإيطالية|إيطالي(?!ا)|الايطالية", "es": r"الإسبانية|الاسبانية|الأسبانية|إسباني(?!ا)|اسباني(?!ا)|أسباني(?!ا)", "ru": r"الروسية|روسي(?!ا)", "pl": r"البولندية|بولندي(?!ا)",
           "ro": r"الرومانية|روماني(?!ا)"},
    "fa": {"en": r"انگلیسی", "nl": r"هلندی", "fr": r"فرانسوی|فرانسه‌ای|فرانسیسی", "de": r"آلمانی", "it": r"ایتالیایی", "es": r"اسپانیایی|اسپانوی|اسپانیولی",
           "ru": r"روسی(?!ه)", "pl": r"لهستانی", "ro": r"رومانیایی"},
    "prs": {"en": r"انگلیسی|انګلیسی", "nl": r"هالندی|هلندی", "fr": r"فرانسوی|فرانسه‌ای|فرانسیسی", "de": r"آلمانی|جرمن|المانی|جرمنی(?!ا)", "it": r"ایتالیایی|ایتالوی|ایتالیوی|اطالوی|ایتالیایی",
            "es": r"هسپانوی|اسپانیایی|اسپانوی|اسپانیولی|هسپانیایی", "ru": r"روسی(?!ه)", "pl": r"لهستانی|پولندی", "ro": r"رومانیایی|رومانوی"},
    "hi": {"en": r"अंग्रेज़ी|अंग्रेजी|इंग्लिश", "nl": r"डच", "fr": r"फ़्रेंच|फ्रेंच|फ़्रांसीसी|फ्रांसीसी", "de": r"जर्मन(?!ी)",
           "it": r"इतालवी|इटैलियन|इटालियन", "es": r"स्पेनिश|स्पैनिश|स्पेनी", "ru": r"रूसी", "pl": r"पोलिश", "ro": r"रोमानियाई|रोमेनियाई"},
}


ABOUT_LANG_LINES = 3
ID_LINE = re.compile(r"^\s*(- )?[a-z]{2}\.[a-z]\d")


def _wb(pat: str) -> str:
    return rf"(?<![A-Za-z]){pat}(?![A-Za-z])"


@functools.lru_cache(maxsize=None)
def compile_names(learner: str) -> dict[str, re.Pattern]:
    """language -> regex matching its English name or its name in the learner's language."""
    out = {}
    for lang in LANGS:
        parts = [_wb(EN[lang])]
        loc = LOCAL.get(learner, {}).get(lang)
        if loc:
            parts.append(_wb(loc) if re.match(r"[A-Za-z\\\[]", loc) and learner not in ("ar", "fa", "prs", "hi", "ru") else loc)
        out[lang] = re.compile("|".join(parts))
    return out


def names_in(learner: str, text: str) -> set[str]:
    """Languages whose English name or `learner`-language name occurs in `text`."""
    return {lang for lang, rx in compile_names(learner).items() if rx.search(text)}


def tm_entry_ok(learner: str, english: str, translation: str) -> bool:
    """False when the translation names a language the English source does not (a target name that leaked into the
    translation memory and would be reused for a pair with another target)."""
    return not (names_in(learner, translation) - names_in("en", english))


@functools.lru_cache(maxsize=None)
def compile_any(learner: str) -> re.Pattern:
    return re.compile("|".join(f"(?:{rx.pattern})" for rx in compile_names(learner).values()))


def load_allowlist(path: Path = ALLOWLIST) -> list[tuple[str, str, str]]:
    rows = []
    if path.exists():
        for ln in path.read_text(encoding="utf-8").splitlines():
            if not ln.strip() or ln.startswith("#"):
                continue
            f = ln.split("\t")
            if len(f) >= 4 and not ln.startswith("#"):
                rows.append((f[0], f[1], f[2]))
    return rows


def check_text(learner: str, target: str, text: str, sibling_text: str = "") -> list[tuple[int, str, str]]:
    """(line number, language, line) for every wrong-language name in `text`."""
    names = compile_names(learner)
    anyname = compile_any(learner)
    # a unit about language L (the en->Y sibling names L on >= ABOUT_LANG_LINES lines) may name L freely; one or two
    # mentions in the sibling (a register note) do not license the cross file to name L anywhere else.
    skip = {learner, target} | {lang for lang in LANGS
                                if len(re.findall(rf"^.*{_wb(EN[lang])}.*$", sibling_text, re.M)) >= (1 if lang == "en" else ABOUT_LANG_LINES)}
    sib_lines = {ln.strip() for ln in sibling_text.split("\n")}
    hits = []
    for i, line in enumerate(text.split("\n"), 1):
        if line.lstrip().startswith("register:") or ID_LINE.match(line):   # content key / slug line, e.g. "de.a1.unit02.lesson03.teach.italien:"
            continue
        if line.lstrip().startswith("notes: 'Derived from en-"):   # generated header ("Derived from en-Y ... every French string was translated")
            continue
        if line.strip() in sib_lines:   # copied verbatim from the en->Y sibling (register notes, target-language text)
            continue
        if not anyname.search(line):
            continue
        for lang in LANGS:
            if lang not in skip and names[lang].search(line):
                hits.append((i, lang, line.strip()))
    return hits


def cross_pairs() -> list[str]:
    seen = set()
    for kind in ("overlays", "practice"):
        for d in (CONTENT / kind).iterdir():
            a, _, b = d.name.partition("-")
            if d.is_dir() and b and a != "en" and b != "en" and a in LANGS and b in LANGS:
                seen.add(d.name)
    return sorted(seen)


def scan(pairs: list[str], allow: list[tuple[str, str, str]] | None = None, content: Path = CONTENT) -> list[str]:
    allow = load_allowlist() if allow is None else allow
    out = []
    for pair in pairs:
        learner, target = pair.split("-", 1)
        for kind in ("overlays", "practice"):
            for f in sorted((content / kind / pair).glob("*.yaml")):
                sib = content / kind / f"en-{target}" / f.name
                sib_text = sib.read_text(encoding="utf-8") if sib.exists() else ""
                rel = f"{kind}/{pair}/{f.name}"
                for ln, lang, line in check_text(learner, target, f.read_text(encoding="utf-8"), sib_text):
                    if any(p == rel and l == lang and (n == "*" or n in line) for p, l, n in allow):
                        continue
                    out.append(f"{rel}:{ln}: [{lang}] {line[:160]}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=lambda s: s.split(","))
    a = ap.parse_args()
    hits = scan(a.pairs or cross_pairs())
    for h in hits:
        print(h)
    print(f"target-name check: {len(hits)} hit(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
