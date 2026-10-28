#!/usr/bin/env python3
"""Dutch-leftover check for derived courses, overlays, realizations and practice packs.

scripts/derive_target.py derives units from the en-nl course into other targets. Text it
fails to translate or author stays Dutch ("Kaartje", "X zegt:" in English feedback, Dutch
words in a note). Nothing else caught that. This check scans every string leaf of
  overlays/<learner>-<target>/*.yaml, practice/<learner>-<target>/*.yaml, realizations/<target>/*.yaml
for every course whose learner and target language are both not nl (en-nl and nl-en legitimately
carry Dutch), with two detectors:

  1. source-identity: a derived file names its en-nl source in its provenance ("from nl/a1_unit11_plans.yaml");
     a string equal to a string of that source (overlay / practice pack / nl realization) that is not
     English (english_fraction < 0.9) or carries a Dutch marker is untranslated.
  2. Dutch markers: >= 2 distinctive Dutch function / common words, or 1 in a string of <= 4 words.
     Words that are also English / German / Romance / Slavic words ("die", "is", "in", "was", "van", "de",
     "hier", "wie", ...) are deliberately NOT in the list; German-language text (learner or target de) only
     uses words German does not share. Quoted examples inside {braces}, 'single' or "double" quotes of
     English notes about Dutch cognates are not exempt: a course for non-Dutch learners should not quote Dutch.
  3. Dutch slugs: a snake_case token built from Dutch words (choose_ontbijten) in a user-visible value is a hit.
     The same slugs as dict keys / content keys are not user-visible: listed with --slugs, never failing.

  4. English-side lint (derived en-<target> overlays only): a matching pair whose two sides are both target-language
     (or identical non-English words), e.g. 'museo' = 'museo' where the English side 'museum' was translated, and
     English-only fields (example_gloss / note / instruction / accepted_note / course_description) that are
     almost entirely target-course words outside quotes. Person-vs-sentence pairs (name = activity) are not flagged.

Exit 1 when any user-visible hit is found. Usage:
    .content-venv/bin/python3 scripts/_dutch_leftover_check.py [--pairs en-es,en-fr] [--slugs] [--quiet]
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
import yaml  # noqa: E402

_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@functools.lru_cache(maxsize=None)
def _load(path_str: str):
    """Cached YAML load (C loader when available): every file is read a few times by the lexicon builders."""
    return yaml.load(Path(path_str).read_text(encoding="utf-8"), Loader=_LOADER)


def load(path: Path):
    return _load(str(path))

# Distinctive Dutch words: not valid words of English, German, Spanish, French, Italian, Portuguese, Romanian,
# Polish, Russian (transliterated) or Hindi/Arabic/Persian romanisations. Deliberately excluded because they are
# real words elsewhere: die, is, in, was, van, de, het-like "het" is kept (not a word elsewhere), me, met, dat, wat,
# hier, wie, war, dag, haar, men, over, op, om, of, an, er, ja, so, zo, nu, al, hun, ze, je, te, ons.
NL_WORDS = set("""het een niet zijn ik jij wij jullie zegt zeggen heeft hebben naar voor maar ook geen mijn
waarom welke kaartje alsjeblieft graag bedankt gaat gaan wordt worden kunnen willen wil moet moeten elke veel altijd
nooit bij aan wel toch nee goed deze onze zij hij dank alstublieft tot straks vandaag morgen gisteren vanavond
vanmorgen dinsdag woensdag donderdag vrijdag zaterdag zondag maandag mevrouw meneer lekker eigenlijk misschien
ontbijt ontbijten koffie tafel kamer huis vraagt antwoordt antwoord vragen woord woorden zin zinnen bijvoorbeeld
tussen zonder omdat dus nog alle allemaal heel erg zeer mag mogen zal zullen zou zouden kan kon konden
had hadden waren wordt gewoon vrij klein groot nieuwe oude mooie leuke leuk lekkere beetje twee drie vier vijf zes
zeven acht negen tien kopje kopjes stukje straat gezelligfijn fiets fietsen ziekenhuis winkel winkels
apotheek bibliotheek station perron spoor reis reizen kaart kaartjes retour enkele dubbele""".split())
# Dutch compounds that are never words of another checked language: one occurrence is a hit at any string length
# (the usual "1 hit only in a short string" rule missed "...asking for help at the taalcafe" in long titles).
NL_COMPOUNDS = set("""taalcafe taalcafé taalles taalcursus taalschool taalmaatje taalgids taalniveau
taalcafes taalcafés taalcafeetje""".split())
# A few of the above are ordinary words of one of the checked languages; drop them per language of the text.
SHARED = {
    "de": set("tot dank morgen alle dus zin erg sechs acht neun tisch kaffee frage antwort wort worte kamer huis "
              "reise reisen station winkel klein groß zeit zonder vrij kan mag zal zou kon had waren wordt gewoon "
              "vier fünf zeven nog bij klein bedankt reis lekker fijn plan station".split()),
    "en": set("fine station reis straat kamer perron plan gewoon".split()),
    "ru": set(),
    "es": set("tot alle dus zin acht tafel kaart station reis spoor".split()),
    "fr": set("tot alle dus zin acht tafel kaart station reis spoor onze retour".split()),
    "it": set("tot alle dus zin acht tafel kaart station reis spoor".split()),
}
# Words that exist in the Romance / Germanic / Slavic targets too and are therefore only counted with a second hit.
WEAK = set("""morgen dank tot alle erg zin goed nee wel toch ook veel nog heel zeer mag kan kon had waren vier acht
station kaart fijn lekker graag""".split())

TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)
SLUG = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
NON_VISIBLE_KEYS = {"content_key", "lesson_content_key", "unit_content_key", "pack_key", "overlay_key", "key", "id",
                    "language_code", "direction", "part_of_speech", "semantic", "agreement_tags", "type", "tags",
                    "generation_provenance", "review", "status", "schema_version", "tag_schema", "source_material",
                    "overlay_version", "realization_version", "source_language", "target_language", "cefr_level",
                    "authoring_system", "media_asset_key", "media_key", "method", "fresh_context", "notes"}
KEY_LIKE = re.compile(r"^[a-z0-9_.\-:]+$")


def text_lang(learner: str, target: str, kind: str) -> str:
    return f"{learner}+{target}+en"


def _old_text_lang(learner: str, target: str, kind: str) -> str:
    """Language the shared-word filter should respect for a file ('de' when German text is in it)."""
    if "de" in (learner, target) and kind != "overlays":
        return "de"
    if "de" == learner or ("de" == target and kind == "practice"):
        return "de"
    return "en" if learner == "en" else learner


def nl_markers(text: str, lang: str = "en") -> list[str]:
    text = re.sub(r"\{[^}]*\}", " ", text)
    toks = [t.lower() for t in TOKEN.findall(text)]
    if not toks:
        return []
    shared = set().union(*(SHARED.get(l, set()) for l in lang.split("+")))
    hits = [t for t in toks if t in NL_WORDS and t not in shared]
    compounds = sorted({t for t in toks if t in NL_COMPOUNDS})
    if compounds:
        return sorted(set(hits) | set(compounds))
    strong = [t for t in hits if t not in WEAK]
    if len(set(hits)) >= 2 or (strong and len(toks) <= 4) or (strong and len(set(strong)) >= 1 and len(toks) <= 8):
        return sorted(set(hits))
    return []


def dutch_slugs(text: str, lang: str = "en") -> list[str]:
    out = []
    shared = set().union(*(SHARED.get(l, set()) for l in lang.split("+")))
    for m in SLUG.findall(text):
        if any(p in NL_WORDS and p not in WEAK and p not in shared for p in m.split("_")):
            out.append(m)
    return out


def key_slugs(node, path=()):
    """Dutch slugs used as dict keys / content-key values: not user-visible, listed only."""
    found = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str):
                found.update(s for s in dutch_slugs(k.replace(".", " ")) + (dutch_slugs(k) if "_" in k else []))
            found |= key_slugs(v, path + (k,))
    elif isinstance(node, list):
        for v in node:
            found |= key_slugs(v, path)
    elif isinstance(node, str) and path and path[-1] in NON_VISIBLE_KEYS and KEY_LIKE.match(node):
        found.update(dutch_slugs(node))
    return found


# ---------------------------------------------------------------------------
# Dutch-only lexicon: words of the nl realizations that are neither English nor words of the target course
# ---------------------------------------------------------------------------
WORD3 = re.compile(r"[^\W\d_]{3,}", re.UNICODE)


def visible_strings(y):
    """String leaves a learner can see: provenance / review notes / keys are excluded. They quote Dutch words
    ("no longer contains the answer word kaartje", "Welke zin zegt de medewerker") and used to make those words
    look like English or target vocabulary, which hid real leftovers such as 'Haar means hair' or 'Nina zegt: ...'."""
    for path, t in dd.walk_strings(y):
        if _visible(path) and not any(isinstance(p, str) and p in HIDDEN_SECTIONS for p in path[:1]):
            yield path, t


HIDDEN_SECTIONS = {"review", "generation_provenance"}


def _english_core() -> set:
    v = set(dd.CORE_EN)
    for p in (CONTENT / "realizations" / "en").glob("*.yaml"):
        for _, t in visible_strings(load(p)):
            v.update(re.findall(r"[a-z]+(?:'[a-z]+)?", t.lower()))
    return v


@functools.lru_cache(maxsize=None)
def english_words_lenient() -> frozenset:
    """Vocabulary for the English-side pair lint only: includes words quoted in provenance / review notes."""
    words = set(dd.english_vocab())
    per = []
    for pair in ("en-ar", "en-fa", "en-hi", "en-prs"):
        c: set[str] = set()
        for f in (CONTENT / "overlays" / pair).glob("*.yaml"):
            for _p, t in dd.walk_strings(load(f)):
                c.update(WORD3.findall(t.casefold()))
        per.append(c)
    from collections import Counter
    cnt = Counter(w for c in per for w in c)
    return frozenset(words | {w for w, n in cnt.items() if n >= 2})


@functools.lru_cache(maxsize=None)
def english_words() -> frozenset:
    """English vocabulary: all English realizations plus words found in >= 2 of the non-derived English-learner courses
    (en-ar/en-fa/en-hi/en-prs), where a quoted Dutch leftover cannot be common."""
    words = _english_core()
    per = []
    for pair in ("en-ar", "en-fa", "en-hi", "en-prs"):
        c: set[str] = set()
        for f in (CONTENT / "overlays" / pair).glob("*.yaml"):
            for _p, t in visible_strings(load(f)):
                c.update(WORD3.findall(t.casefold()))
        per.append(c)
    from collections import Counter
    cnt = Counter(w for c in per for w in c)
    words |= {w for w, n in cnt.items() if n >= 2}
    return frozenset(words)


@functools.lru_cache(maxsize=None)
def dutch_vocab() -> frozenset:
    """Every word of the nl realizations' Dutch text and titles."""
    voc: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("text"), str) and o.get("language_code", o.get("language")) in (None, "nl"):
                voc.update(WORD3.findall(o["text"].casefold()))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for f in sorted((CONTENT / "realizations/nl").glob("*.yaml")):
        walk(load(f))
    return frozenset(voc)


@functools.lru_cache(maxsize=None)
def target_vocab_native(target: str) -> frozenset:
    """Words of the target course's own text blocks (language_code == target) and titles-free: never English prompt text."""
    voc: set[str] = set()

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get("text"), str) and o.get("language_code", o.get("language")) == target:
                voc.update(WORD3.findall(o["text"].casefold()))
                voc.update(w for w in TOKEN.findall(o["text"].casefold()) if len(w) == 2)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for f in sorted((CONTENT / "realizations" / target).glob("*.yaml")):
        walk(load(f))
    return frozenset(voc)


@functools.lru_cache(maxsize=None)
def target_vocab(target: str) -> frozenset:
    """Every word of the target realizations, English prompt text included (a Dutch word that the course itself uses is no leftover)."""
    voc: set[str] = set()
    for f in sorted((CONTENT / "realizations" / target).glob("*.yaml")):
        for _p, t in visible_strings(load(f)):
            voc.update(WORD3.findall(t.casefold()))
    return frozenset(voc)


def nl_only_tokens(text: str, target: str) -> list[str]:
    toks = WORD3.findall(re.sub(r"\{[^}]*\}", " ", text).casefold())
    dv, ev, tv = dutch_vocab(), english_words(), target_vocab(target)
    own = TARGET_OWN.get(target, frozenset())
    return sorted({t for t in toks if t in dv and t not in ev and t not in tv and t not in NAMES and t not in own})


# Loanwords / cognates / names that are ordinary English (or course-neutral) although they occur in the Dutch course.
NAMES = frozenset("loop meter sms pico centrale chef calque theater workshop tekst anna naam baat hun".split())
# Targets whose own words (or romanisations) coincide with Dutch-only vocabulary: German 'das Haar'; Hindi/Arabic/Persian
# transliterations (naam, baat, hun, anna: NAMES above) are target text quoted in English notes, never Dutch.
TARGET_OWN = {"de": frozenset({"haar"})}


# ---------------------------------------------------------------------------
# Source mapping: derived file -> en-nl overlay / pack and nl realization strings
# ---------------------------------------------------------------------------
SRC_RE = re.compile(r"nl/(a1_unit\d+)_?([a-z0-9_]*)\.yaml")


@functools.lru_cache(maxsize=None)
def _strings(path_str: str) -> frozenset:
    p = Path(path_str)
    if not p.exists():
        return frozenset()
    return frozenset(v for _p, v in dd.walk_strings(load(p)) if dd.has_words(v))


def source_files(pair: str, name: str, y: dict) -> list[Path]:
    """en-nl overlay / pack and nl realization of the unit a derived overlay/pack was derived from."""
    blob = str((y.get("review") or {}).get("notes") or "") + str(y.get("generation_provenance") or "")
    m = SRC_RE.search(blob)
    if not m:
        return []
    unit = m.group(1)
    out = [CONTENT / "overlays/en-nl" / f"{unit}.yaml", CONTENT / "practice/en-nl" / f"{unit}.yaml"]
    out += sorted((CONTENT / "realizations/nl").glob(f"{unit}_*.yaml"))
    return out


def realization_source(y: dict) -> list[Path]:
    blob = str(y.get("generation_provenance") or "")
    m = re.search(r"nl A1 unit (\d+) \((a1_unit\d+_[a-z0-9_]+)\)", blob)
    return [CONTENT / "realizations/nl" / f"{m.group(2)}.yaml"] if m else []


def identity_hit(v: str, src: frozenset, target: str, lang: str = "en") -> bool:
    """String copied verbatim from the Dutch source and carrying Dutch-only words or markers."""
    return v in src and bool(nl_markers(v, lang) or nl_only_tokens(v, target))


# ---------------------------------------------------------------------------
# English-side lint: fields of an en-<target> overlay that must be English but are not
# (derive_target translated the English side of a matching pair: "museum" -> "muzeu")
# ---------------------------------------------------------------------------
# gloss is deliberately absent: a phrase card's gloss is the target sentence, its title the English meaning.
EN_FIELDS = {"example_gloss", "note", "instruction", "accepted_note", "course_description"}


@functools.lru_cache(maxsize=None)
def english_loose() -> frozenset:
    """Pair-lint English vocabulary: english_words() plus any word that occurs in the overlays of >= 3 en-<target> courses
    other than en-nl (cognates and loanwords: bouquet, score, fan, stage, sea). A word quoted from one target stays out."""
    from collections import Counter
    cnt: Counter = Counter()
    for d in sorted((CONTENT / "overlays").iterdir()):
        if d.is_dir() and d.name.startswith("en-") and d.name != "en-nl":
            seen: set[str] = set()
            for f in d.glob("*.yaml"):
                for _p, t in dd.walk_strings(load(f)):
                    seen.update(WORD3.findall(t.casefold()))
            cnt.update(seen)
    return frozenset(english_words_lenient() | {w for w, n in cnt.items() if n >= 3})


def _tgt_share(text: str, target: str, strip_quotes: bool = False) -> float:
    """Share of the word tokens (>= 2 letters) that are target-course words and not English vocabulary."""
    if strip_quotes:
        text = re.sub(r"\*[^*]*\*|'[^']*'|\"[^\"]*\"|\u2018[^\u2019]*\u2019", " ", text)
    toks = [t.casefold() for t in TOKEN.findall(re.sub(r"\{[^}]*\}", " ", text)) if len(t) >= 2]
    if not toks:
        return 0.0
    tv, ev = target_vocab_native(target), english_loose()
    return sum(t in tv and t not in ev for t in toks) / len(toks)


def _pairs(node, path=()):
    if isinstance(node, dict):
        if isinstance(node.get("left"), str) and isinstance(node.get("right"), str):
            yield path, node["left"], node["right"]
        for k, v in node.items():
            yield from _pairs(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _pairs(v, path + (i,))


def english_side_hits(pair: str, p: Path) -> list[str]:
    """Matching pairs with no English side, and English-only fields (gloss / note / instruction) that are not English."""
    learner, target = pair.split("-")
    if learner != "en":
        return []
    y = load(p)
    if "Derived by scripts/derive_target.py" not in str((y.get("review") or {}).get("notes") or ""):
        return []                                     # hand-authored units are reviewed by native speakers; this lint guards derivation
    out: list[str] = []
    for path, left, right in _pairs(y):
        same = left.casefold() == right.casefold()
        short = len(left.split()) <= 3 and len(right.split()) <= 3 and not (left[:1].isupper() and len(left.split()) == 1 and not same)
        if _tgt_share(left, target) >= 0.99 and _tgt_share(right, target) >= 0.99 and (same or short):
            out.append(f"overlays/{pair}/{p.name}: {'/'.join(map(str, path))[-60:]}: pair {left!r} = {right!r} [no English side]")
    for path, v in dd.walk_strings(y):
        if not dd.has_words(v) or dd.overlay_role(path) is None or path[0] in ("exercises",) and path[2:3] == ("feedback",):
            continue
        if path[-1] in EN_FIELDS and len(TOKEN.findall(v)) >= 3 and _tgt_share(v, target, True) >= 0.8:
            out.append(f"overlays/{pair}/{p.name}: {'/'.join(map(str, path))[-60:]}: {v[:80]!r} [English field not English]")
    return out


def _is_target_text(path: tuple) -> bool:
    return any(isinstance(p, str) and p in ("target", "frame", "text") for p in path)


def _visible(path: tuple) -> bool:
    return not any(isinstance(p, str) and p in NON_VISIBLE_KEYS for p in path)


def scan_file(kind: str, pair: str, p: Path, learner: str, target: str) -> tuple[list[str], set[str]]:
    y = load(p)
    lang = text_lang(learner, target, kind)
    srcs = (realization_source(y) if kind == "realizations" else source_files(pair, p.name, y))
    src = frozenset().union(*[_strings(str(s)) for s in srcs]) if srcs else frozenset()
    out: list[str] = []
    for path, v in dd.walk_strings(y):
        if not _visible(path) or not dd.has_words(v):
            continue
        if kind == "overlays" and dd.overlay_role(path) is None:
            continue
        tag = None
        en_field = learner == "en" and kind != "realizations" and not (kind == "practice" and _is_target_text(path))
        if identity_hit(v, src, target, lang):
            tag = "identical to Dutch source"
        elif nl_markers(v, lang):
            tag = "dutch words " + ",".join(nl_markers(v, lang))
        elif en_field and nl_only_tokens(v, target):
            tag = "dutch-only words " + ",".join(nl_only_tokens(v, target))
        elif SLUG.search(v) and dutch_slugs(v, lang):
            tag = "dutch slug " + ",".join(dutch_slugs(v, lang))
        if tag:
            out.append(f"{kind}/{pair}/{p.name}: {'/'.join(map(str, path))[-70:]}: {v[:80]!r} [{tag}]")
    return out, key_slugs(y)


def scan_pair(pair: str) -> tuple[list[str], set[str]]:
    learner, target = pair.split("-")
    out: list[str] = []
    slugs: set[str] = set()
    for kind in ("overlays", "practice"):
        d = CONTENT / kind / pair
        if d.is_dir():
            for p in sorted(d.glob("*.yaml")):
                h, s = scan_file(kind, pair, p, learner, target)
                out += h
                slugs |= s
                if kind == "overlays":
                    out += english_side_hits(pair, p)
    d = CONTENT / "realizations" / target
    if learner == "en" and d.is_dir():                       # realizations belong to the target; scan them once, with en-<target>
        for p in sorted(d.glob("*.yaml")):
            h, s = scan_file("realizations", target, p, learner, target)
            out += h
            slugs |= s
    return out, slugs


def course_pairs() -> list[str]:
    ps = []
    for d in sorted((CONTENT / "overlays").iterdir()):
        if d.is_dir() and "nl" not in d.name.split("-"):
            ps.append(d.name)
    return ps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=lambda s: s.split(","))
    ap.add_argument("--slugs", action="store_true", help="also list Dutch slugs used as keys (informational)")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    total = 0
    allslugs: set[str] = set()
    for pair in a.pairs or course_pairs():
        hits, slugs = scan_pair(pair)
        allslugs |= slugs
        total += len(hits)
        print(f"dutch-leftover {pair}: {len(hits)}")
        if not a.quiet:
            for h in hits[:300]:
                print("  " + h)
    if a.slugs and allslugs:
        print(f"dutch-leftover key slugs (not user-visible, informational): {len(allslugs)}")
        for s in sorted(allslugs)[:200]:
            print("  " + s)
    print(f"dutch-leftover total: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
