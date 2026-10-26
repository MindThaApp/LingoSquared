#!/usr/bin/env python3
"""Derive units of a new TARGET language from a rich source target course.

derive_direction.py reuses one target course across LEARNER languages (same
target sentences, translated overlays).  This tool does the other axis: the
learner language stays (en) and the TARGET language changes.  It takes A1 units
of a deep course (en-nl: Dutch targets, English overlay) and rebuilds them for a
thin one (en-es: Spanish targets, English overlay) by *translating* the target
side instead of hand-authoring YAML:

    extract  nl units -> flat JSON to translate / author     (.local/derive-target/<new>/)
    (translate atoms.src.json -> atoms.tr.json, author.src.json -> author.tr.json)
    lexemes  list new target tokens that still need a gloss + part of speech
    (write lexemes.tr.json)
    inject   realizations + overlays + manifest line + backfill gloss block
    check    compiler validate/compile of the course + backfill dry run

What is translated, what is derived, what is authored (docs/content/DIRECTION_PIPELINE.md):

* atoms (atoms.*.json): every distinct source-target string (teaching targets,
  examples, titles, media texts, pair left sides, prompts).  Translated once,
  reused everywhere the exact text occurs, including inside English feedback.
* derived, never sent: introduced_tokens, tested_text (when it is a sentence atom or the
  answer), word_bank tiles (from the translated answer), punctuation variants of
  accepted answers, content keys (slugs re-derived from the translation),
  pair right sides, all English glosses/titles/options.
* authored (author.*.json): things that must be rewritten for the new language and
  not translated: distractors, fill-in-blank frames and answers, free-production
  answers with their variants, tested spans of comprehension items, grammar notes
  and feedback/instructions that talk about the source language, tile distractors.
  Every such slot is flagged AUTHOR in the report.
* flagged (report.json, lint): gender, formal/informal register, obligatory
  contractions, word-order variants that the tile bank cannot build, leftover
  source-language words, cast names.  Errors block inject unless acknowledged in
  ack.json ({"<id>:<FLAG>": "reason"}) or forced.

Not derived: practice packs (hand-authored per language, PRACTICE_PACK_RECIPE.md),
audio (media assets stay pending_generation), native review.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import unicodedata
from collections import OrderedDict, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import derive_direction as dd  # noqa: E402  (load/dump/manifest helpers)

ROOT = HERE.parent
CONTENT = ROOT / "docs/content"
MANIFEST = ROOT / "scripts/manifest.d/content"
DEFAULT_WORK = ROOT / ".local/derive-target"

# ---------------------------------------------------------------------------
# Per-language configuration (formal / informal markers, gender, contractions)
# ---------------------------------------------------------------------------
CFG = {
    # code: formal marker, informal marker (regexes over lowercase text)
    "nl": dict(name="Dutch", formal=r"\b(u|uw)\b", informal=r"\b(je|jij|jou|jouw|jullie)\b"),
    "de": dict(
        name="German",
        case_sensitive=True,                 # nouns are capitalised: never casefold tested_text / tiles; slugs transliterate umlauts
        translit=True,
        rekey_exercises=True,
        strict_residual=True,                # source-language words inside English fields are found by vocabulary, not by "occurs in an English field"
        per_card_keys=True,                  # a reading card's gloss keys translate per card (the same source word is another token in another text)
        rewrite_gloss=True,                  # rewritten grammar cards must also get an authored English title + gloss
        formal=r"\bIhnen\b|\bIhr(?:e|en|em|er|es)?\b|(?<=[\w,]) Sie\b",    # matched on the original case: sentence-initial Sie is ambiguous (she/they)
        informal=r"(?i:\b(?:du|dich|dir|dein\w*)\b)",
        gender=dict(mode="agent"),           # learner speaks as themselves: Ich bin Student / Studentin
        contractions=[(r"\b[iI]n dem\b", "im"), (r"\b[aA]n dem\b", "am"), (r"\b[zZ]u dem\b", "zum"), (r"\b[zZ]u der\b", "zur"),
                      (r"\b[vV]on dem\b", "vom"), (r"\b[bB]ei dem\b", "beim")],
        note=("Natural standard German. Nouns capitalised (Hund, not hund); real spelling (ä ö ü ß, no ae/ue). Informal source roles -> du, formal -> Sie "
              "(capital Sie/Ihnen/Ihr). Verb second in main clauses, verb-first questions, separable verbs split (Ich stehe um sieben Uhr auf), "
              "cases marked (accusative: Ich habe einen Hund; dative after mit/bei/zu). "
              "Contract in dem/an dem/zu dem/zu der/von dem/bei dem -> im/am/zum/zur/vom/beim."),
    ),
    "es": dict(
        name="Spanish",
        formal=r"\busted(es)?\b",
        informal=r"\b(tú|tu|te|ti|contigo|vosotros)\b|\b(tienes|puedes|quieres|eres|estás|vives|necesitas|hablas|haces|vas|sabes|dices|prefieres|llamas)\b",
        gender=dict(
            copula=r"\b(estoy|soy|estás|eres|estamos|somos|me siento|te sientes)\b",
            skip="de en a aquí ahí allí ahora bien mal ya con sin por para un una el la los las mi tu su casa muy tan mucho poco".split(),
            swap=(("o", "a"), ("os", "as")),
        ),
        contractions=[(r"\b[dD]e el\b", "del"), (r"\b[aA] el\b", "al")],
    ),
    "it": dict(
        name="Italian",
        formal=r"\blei\b",
        informal=r"\b(tu|ti|te|tuo|tua)\b",
        gender=dict(copula=r"\b(sono|sei|siamo|mi sento|ti senti)\b", skip="di in a qui lì ora bene male già con senza per un una il la i le mio tua molto".split(), swap=(("o", "a"), ("i", "e"))),
        contractions=[(r"\b[dD]i il\b", "del"), (r"\b[aA] il\b", "al"), (r"\b[iI]n il\b", "nel"), (r"\b[dD]a il\b", "dal")],
    ),
    "fr": dict(
        name="French",
        formal=r"\bvous\b",
        informal=r"\b(tu|toi|ton|ta|tes)\b",
        contractions=[(r"\b[dD]e le\b", "du"), (r"\b[àÀ] le\b", "au"), (r"\b[dD]e les\b", "des"), (r"\b[àÀ] les\b", "aux")],
    ),
    "pt": dict(name="Portuguese", formal=r"\bo senhor|a senhora\b", informal=r"\btu\b"),
}
TARGET_ANSWER_TYPES = {
    "word_order", "listen_order", "fill_in_blank", "translation", "writing_prompt",
    "dictation", "listen_type", "dialogue_response", "speak_response",
}
GERMAN_FREE_TEXT_TYPES = {"writing_prompt", "dialogue_response", "listen_type", "translation", "reverse_translation", "grammar_check"}   # compile_content.py
SEP = " || "
BLANK = "___"
PUNCT_CHARS = re.compile(r"[^\w\s'’\-‌]", re.U)
TOKEN_RE = re.compile(r"[\w'’\-‌]+", re.U)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
_EN_VOCAB: set[str] | None = None


def strip_punct(s: str) -> str:
    return " ".join(PUNCT_CHARS.sub(" ", s).split()) if "\n" in s else " ".join(PUNCT_CHARS.sub("", s).split())


def boundary_strip(s: str) -> str:
    """Only the punctuation at both ends (the dictation compiler check ignores just that)."""
    return re.sub(r"^[\s.!?¿¡;:,\"“”„]+|[\s.!?¿¡;:,\"“”„]+$", "", s)


def norm(s: str) -> str:
    """Same folding as compile_content.normalize_dialogue_option."""
    return " ".join(re.sub(r"[^\w‌]+", " ", s, flags=re.U).casefold().split())


def tokens(s: str) -> list[str]:
    return [t for t in (x.strip("-") for x in TOKEN_RE.findall(strip_punct(s))) if t]       # a bare "-e" ending is not a word


TRANSLIT_DE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})


def slug(s: str, words: int = 4, translit: bool = False) -> str:
    if translit:
        s = s.translate(TRANSLIT_DE)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    parts = re.findall(r"[a-z0-9]+", s.lower())[:words]
    return "_".join(parts)[:36] or "x"


def atom_id(text: str) -> str:
    return "a_" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:7]


def shuffled(tiles: list[str]) -> list[str]:
    """Deterministic scramble that never equals the answer order."""
    out = sorted(tiles, key=lambda t: hashlib.sha1((t + str(tiles.index(t))).encode()).hexdigest())
    if out == tiles and len(set(tiles)) > 1:
        out = tiles[1:] + tiles[:1]
    return out


def register_of(text: str, src: str) -> str | None:
    cfg = CFG.get(src)
    if not cfg:
        return None
    low = text if cfg.get("case_sensitive") else text.casefold()
    f = bool(re.search(cfg["formal"], low))
    i = bool(re.search(cfg["informal"], low))
    return "formal" if f and not i else "informal" if i and not f else None


AGENT_UMLAUT = {"Arzt": "Ärztin", "Koch": "Köchin", "Anwalt": "Anwältin"}
AGENT_UNDO = {v: k for k, v in AGENT_UMLAUT.items()}
AGENT_RE = re.compile(r"\b(Ich bin|bin ich)\s+(?:(ein|eine)\s+)?([A-ZÄÖÜ][\wäöüß]+)")


def agent_gender_alt(text: str) -> str | None:
    """German 'Ich bin Student' -> 'Ich bin Studentin' (and back); None when the noun is not an agent noun."""
    m = AGENT_RE.search(text)
    if not m:
        return None
    art, noun = m.group(2), m.group(3)
    if noun in AGENT_UNDO:
        other = AGENT_UNDO[noun]
    elif noun.endswith("in") and len(noun) > 5 and noun[:-2].endswith(("er", "ent", "ist", "or", "eur", "ler", "ner", "ger", "ter")):
        other = noun[:-2]
    elif noun.endswith(("er", "ent", "ist", "or", "eur", "arzt", "Arzt")) and len(noun) > 4:
        other = AGENT_UMLAUT.get(noun, noun + "in")
    else:
        return None
    new_art = {"ein": "eine", "eine": "ein"}.get(art, art)
    head = text[:m.start(2) if art else m.start(3)]
    return head + (new_art + " " if art else "") + other + text[m.end():]


class Unresolved(Exception):
    pass


# ---------------------------------------------------------------------------
# One unit
# ---------------------------------------------------------------------------
class UnitDeriver:
    def __init__(self, plan: "Plan", src_stem: str, new_no: int):
        self.p = plan
        self.stem = src_stem                         # a1_unit23_money
        m = re.match(r"^(a1)_unit(\d+)_(.+)$", src_stem)
        if not m:
            raise SystemExit(f"{src_stem}: expected a1_unitNN_name (only A1 is supported)")
        self.level, self.src_no, self.suffix = m.group(1), int(m.group(2)), m.group(3)
        self.new_no = new_no
        self.new_suffix = plan.suffixes.get(self.suffix, self.suffix)       # --suffixes: file / topic name in the new language
        self.new_stem = f"{self.level}_unit{new_no:02d}_{self.new_suffix}"
        self.real = dd.load(CONTENT / f"realizations/{plan.src}/{src_stem}.yaml")
        self.ovl = dd.load(CONTENT / f"overlays/{plan.src_pair}/{self.level}_unit{self.src_no:02d}.yaml")
        self.keymap: dict[str, str] = {}
        self.atom_texts: dict[str, str] = {}         # exact src text -> atom id (this unit)
        self.atom_norms: dict[str, str] = {}         # norm -> atom id
        self.used_slugs: dict[str, set[str]] = defaultdict(set)
        self.compose: dict[str, tuple[list[str], bool]] = {}
        self.id_text: dict[str, str] = {}
        self.rewrite_cks: set[str] = set()           # grammar_note cards whose explanation is rewritten (title + gloss are authored too)
        self.card_tr: dict[str, str] = {}            # card content key -> translated target text

    def compose_for(self, text: str):
        """([line, ...], strip_speaker) when `text` is built from teaching lines (gaps between lines allowed)."""
        for ln in self.lines:
            m = re.match(r"^[^\W\d_]+:\s+", ln)
            if m and ln[m.end():] == text:
                return [ln], True
        pos, used = 0, []
        for ln in self.lines:
            if text.startswith(ln, pos):
                used.append(ln)
                pos += len(ln)
                while pos < len(text) and text[pos] == " ":
                    pos += 1
                if pos >= len(text):
                    return (used, False) if len(used) > 1 else None
        return None

    # -- registry helpers --------------------------------------------------
    def T(self, text: str, kind: str, en: str | None = None, where: str | None = None) -> str:
        # gloss keys must be single tokens of the card text, so they translate separately
        if kind == "media":
            comps = self.compose_for(text)
            if comps:
                parts = [self.T(c, "teach", None, where) for c in comps[0]]
                joined = " ".join(parts)
                if comps[1]:
                    joined = re.sub(r"^[^\W\d_]+:\s*", "", joined)
                known = self.atom_texts.get(text)
                if known and known.startswith("d_"):
                    return self.p.derived[known]
                if known:                        # already a plain teaching atom: keep it
                    return self.T(text, "teach", None, where)
                aid = "d_" + hashlib.sha1(text.encode()).hexdigest()[:7]
                self.atom_texts[text] = aid
                self.id_text[aid] = text
                self.atom_norms.setdefault(norm(text), aid)
                self.p.derived[aid] = joined
                return joined
        aid = atom_id((("gk\0" + (where + "\0" if self.p.per_card_keys and where else "")) if kind == "gloss-key" else "") + text)
        self.p.add_atom(aid, text, kind, en, where, self.stem)
        if kind != "gloss-key":
            self.id_text[aid] = text
            self.atom_texts[text] = aid
            if kind != "title":                      # titles lose their punctuation; prefer sentence atoms
                self.atom_norms.setdefault(norm(text), aid)
        tr = self.p.tr_atoms.get(aid)
        if tr is None:
            self.p.missing.add(aid)
            return f"<<{aid}>>"
        return self.p.names(tr)

    def T_by_norm(self, text: str) -> str | None:
        aid = self.atom_norms.get(norm(text))
        if aid is None:
            return None
        if aid in self.p.derived:
            return self.p.derived[aid]
        tr = self.p.tr_atoms.get(aid)
        if tr is None:
            self.p.missing.add(aid)
            return f"<<{aid}>>"
        return self.p.names(tr)

    def A(self, slot: str, src: str, kind: str, ctx: dict | None = None, required: bool = True) -> str | None:
        """Authored slot.  Returns the translator's text or a placeholder."""
        self.p.add_author(slot, src, kind, ctx or {}, self.stem)
        v = self.p.tr_author.get(slot)
        if v is None:
            if required:
                self.p.missing.add(slot)
                return f"<<{slot}>>"
            return None
        return self.p.names(v)

    def flag(self, key: str, code: str, msg: str, level: str = "error") -> None:
        self.p.flags.append(dict(id=key, code=code, level=level, msg=msg, unit=self.stem))

    def en(self, s: str) -> str:
        """English text: cast names and language name swapped."""
        s = self.p.names(s)
        return s.replace(self.p.src_name, self.p.new_name)

    def en_checked(self, s: str, slot: str, kind: str, ctx: dict | None = None) -> str:
        """English text that may quote or discuss the source language.  Quoted atoms are
        substituted; anything still source-language needs authoring."""
        out = s
        for text, aid in sorted(self.atom_texts.items(), key=lambda kv: -len(kv[0])):
            if len(text) >= 3 and text in out:
                out = out.replace(text, self.T(text, "quote"))
        out = self.en(out)
        if "*" in s or re.search(r"\bunits?\s+\d+", s, re.I) or self.residual(out):
            v = self.A(slot, s, kind, dict(ctx or {}, why=",".join(self.residual(out)) or "italic span / unit cross-reference"))
            return v
        return out

    def residual(self, s: str) -> list[str]:
        toks = set(re.findall(r"[^\W\d_]{3,}", s.casefold()))
        return sorted(toks & self.src_only)

    # -- build ---------------------------------------------------------------
    def prepass(self) -> None:
        """Register every atom first so quoting can be substituted, and compute vocab sets."""
        R, O = self.real, self.ovl
        # media texts that are concatenations / speaker-stripped copies of teaching lines need no translation of their own
        self.lines = [t["target"]["text"] for u in R["units"] for l in u["lessons"] for t in l.get("teaching") or []]
        gl = lambda sect, k, f: ((O.get(sect) or {}).get(k) or {}).get(f)
        for a in R.get("media_assets") or []:
            self.T(a["text"], "media")
        for u in R["units"]:
            self.T(u["title"], "title", gl("units", u["content_key"], "title"))
            for l in u["lessons"]:
                self.T(l["title"], "title", gl("lessons", l["content_key"], "title"))
                for t in l.get("teaching") or []:
                    ck = t["content_key"]
                    en = gl("teaching", ck, "gloss")
                    self.T(t["target"]["text"], "teach", en if isinstance(en, str) else None, ck)
                    if t.get("kind") == "grammar_note" and len(t["target"]["text"].split()) > 8:
                        self.rewrite_cks.add(ck)
                        self.p.atom_ctx[atom_id(t["target"]["text"])]["rewrite"] = (
                            f"grammar explanation written in {self.p.src_name}: REWRITE it for {self.p.new_name} grammar, do not translate")
                        self.flag(ck, "GRAMMAR_REWRITE", "grammar_note card explains source-language grammar; rewrite per language", "warn")
                    exs = t.get("example")
                    exs = [exs] if isinstance(exs, dict) else (exs or [])
                    egl = gl("teaching", ck, "example_gloss")
                    egl = [egl] if isinstance(egl, str) else (egl or [])
                    for i, e in enumerate(exs):
                        self.T(e["text"], "example", egl[i] if i < len(egl) else None, ck)
                    for k, v in (gl("teaching", ck, "glosses") or {}).items():
                        self.T(k, "gloss-key", v, ck)
                for e in l["exercises"]:
                    for b in (e.get("prompt") or {}).get("target_blocks") or []:
                        if b.get("language_code") == self.p.src and BLANK not in b["text"]:
                            self.T(b["text"], "prompt", gl("exercises", e["content_key"], "instruction"), e["content_key"])
        # vocab sets
        srclex = set()
        for text in self.atom_texts:
            srclex |= set(re.findall(r"[^\W\d_]{3,}", text.casefold()))
        srclex = set()
        for text in self.atom_texts:
            srclex |= set(re.findall(r"[^\W\d_]{3,}", text.casefold()))
        env: set[str] = set()
        def add_en(s):
            if isinstance(s, str):
                env.update(re.findall(r"[^\W\d_]{3,}", s.casefold()))
        for sect in ("units", "lessons"):
            for v in (O.get(sect) or {}).values():
                add_en(v.get("title"))
        for v in (O.get("teaching") or {}).values():
            for f in ("title", "gloss", "example_gloss"):
                x = v.get(f)
                for s in ([x] if isinstance(x, str) else x or []):
                    add_en(s)
            for s in (v.get("glosses") or {}).values():
                add_en(s)
        for ck, v in (O.get("exercises") or {}).items():
            add_en(v.get("instruction"))
            co = v.get("correct_option")
            if isinstance(co, str) and norm(co) in self.atom_norms:
                continue          # source-language options (also word_order answers) are not English vocabulary
            add_en(co)
            for d in v.get("distractors") or []:
                add_en(d)
        for u in R["units"]:
            for l in u["lessons"]:
                for e in l["exercises"]:
                    for b in (e.get("prompt") or {}).get("target_blocks") or []:
                        if b.get("language_code") != self.p.src:
                            add_en(b["text"])

        # Pair sides.  Default: left is source-language text, right is English.  A right side that
        # consists only of source-language words (field -> value pairs) is source text too, and a
        # pair whose right side is a teaching atom and whose left is not is reversed (English left).
        allsrc = set(self.p.src_lexicon)             # inflected forms that occur on a pair side only (leest, luistert) are source text too
        teach_norms = set(self.atom_norms)
        for text in self.atom_texts:
            allsrc |= set(re.findall(r"[^\W\d_]{2,}", text.casefold()))
        self.pair_target: set[str] = set()
        self.right_target: set[str] = set()
        for u in R["units"]:
            for l in u["lessons"]:
                for e in l["exercises"]:
                    ck = e["content_key"]
                    for pr in e.get("pairs") or []:
                        L, Rt = pr["left"], pr["right"]
                        if norm(Rt) in teach_norms and norm(L) not in teach_norms:
                            self.pair_target.add(Rt)
                            self.right_target.add(Rt)
                            continue
                        self.pair_target.add(L)
                        tk = re.findall(r"[^\W\d_]{2,}", Rt.casefold())
                        if tk and all(t in allsrc for t in tk) and not all(t in env for t in tk):
                            self.pair_target.add(Rt)
                            if Rt not in self.atom_texts:
                                self.right_target.add(Rt)
                                self.flag(ck, "PAIR_RIGHT_TARGET",
                                          f"pair right side {Rt!r} was treated as {self.p.src_name} text; check it is not English", "warn")
        for u in R["units"]:
            for l in u["lessons"]:
                for e in l["exercises"]:
                    for pr in e.get("pairs") or []:
                        for side, other in ((pr["left"], pr["right"]), (pr["right"], pr["left"])):
                            if side in self.pair_target:
                                self.T(side, "pair", other, e["content_key"])
        for u in R["units"]:
            for l in u["lessons"]:
                for e in l["exercises"]:
                    for pr in e.get("pairs") or []:
                        for side in (pr["left"], pr["right"]):
                            if side not in self.pair_target:
                                add_en(side)
        srclex = set()
        for text in self.atom_texts:
            srclex |= set(re.findall(r"[^\W\d_]{3,}", text.casefold()))
        self.src_only = srclex - env
        if self.p.strict_residual:
            # `env` is built from the English fields themselves, so a source word quoted inside an English instruction or option
            # (*sporten*, doen aan) counted as English.  Strict mode: every word of the source course that no other English overlay uses.
            self.src_only = ({w for w in self.p.src_lexicon if len(w) >= 4} | srclex) - self.p.en_vocab - self.p.cast_words

    def options_are_target(self, ov: dict) -> bool:
        co = ov.get("correct_option")
        return isinstance(co, str) and norm(co) in self.atom_norms and "distractors" in ov

    def build(self) -> tuple[dict, dict]:
        self.prepass()
        R, O = copy.deepcopy(self.real), copy.deepcopy(self.ovl)
        sp, tp = self.p.src, self.p.tgt
        # -- keys -----------------------------------------------------------
        old_unit = R["units"][0]["content_key"]
        unit_tail = old_unit.split(".", 3)[3]
        prefix_old = f"{sp}.a1.unit{self.src_no:02d}."
        prefix_new = f"{tp}.a1.unit{self.new_no:02d}."
        self.keymap[old_unit] = prefix_new + (self.new_suffix if unit_tail == self.suffix else unit_tail)
        media_slugs: set[str] = set()
        for a in R.get("media_assets") or []:
            parts = a["content_key"].split(".")
            idx = max((i for i, s in enumerate(parts) if re.fullmatch(r"\d+", s)), default=len(parts) - 1)
            si = idx - 1
            while si > 2 and parts[si] in ("formal", "informal"):
                si -= 1
            base = slug(self.T(a["text"], "media"), 5, self.p.translit)
            s = base
            n = 2
            while s in media_slugs or s in self.p.media_slugs:
                s = f"{base}_{n}"
                n += 1
            media_slugs.add(s)
            self.p.media_slugs.add(s)
            parts[si] = s
            if len(parts) > 3 and parts[3] == self.suffix:
                parts[3] = self.new_suffix
            parts[0] = tp
            self.keymap[a["content_key"]] = ".".join(parts)
        for u in R["units"]:
            for l in u["lessons"]:
                lk = l["content_key"]
                m = re.match(r"^(.*\.lesson\d+)\.(.+)$", lk)
                nl = prefix_new + m.group(1)[len(prefix_old):] + "." + slug(self.T(l["title"], "title"), 4, self.p.translit)
                self.keymap[lk] = nl
                seen: set[str] = set()
                for t in l.get("teaching") or []:
                    ck = t["content_key"]
                    mm = re.match(r"^(.*\.teach)\.(.+)$", ck)
                    base = slug(self.T(t["target"]["text"], "teach"), 3, self.p.translit)
                    s, n = base, 2
                    while s in seen:
                        s = f"{base}_{n}"
                        n += 1
                    seen.add(s)
                    self.keymap[ck] = prefix_new + mm.group(1)[len(prefix_old):] + "." + s
                for e in l["exercises"]:
                    ck = e["content_key"]
                    self.keymap[ck] = prefix_new + ck[len(prefix_old):]
        for k in list(self.keymap):
            if not (k.startswith(sp + ".a1.")):
                raise SystemExit(f"unexpected key {k}")
        # -- realization ---------------------------------------------------------
        for a in R.get("media_assets") or []:
            a["text"] = self.T(a["text"], "media")
            a["language"] = tp
        self.media_tr = {a["content_key"]: a["text"] for a in R.get("media_assets") or []}
        O_ex = O.setdefault("exercises", {})
        O_te = O.setdefault("teaching", {})
        for u in R["units"]:
            u["title"] = self.T(u["title"], "title")
            for l in u["lessons"]:
                l["title"] = self.T(l["title"], "title")
                for t in l.get("teaching") or []:
                    self.teach(t, O_te.get(t["content_key"]))
                for i, e in enumerate(l["exercises"]):
                    self.exercise(e, O_ex.get(e["content_key"]), l)
        if self.p.rekey:
            self.rekey_exercises(R)
        # -- overlay English passthroughs -----------------------------------------
        for sect in ("units", "lessons"):
            for v in (O.get(sect) or {}).values():
                v["title"] = self.en(v["title"])
        for ck, v in (O_te).items():
            for f in ("title", "gloss"):
                if isinstance(v.get(f), str):
                    left = self.residual(self.en(v[f]))
                    if ck in self.rewrite_cks or left:
                        # a rewritten grammar card needs its own English title/gloss; leftover source words can be authored away too
                        got = self.A(f"{ck}#{f}", v[f], f, dict(en=v[f], card=self.card_tr.get(ck), why=",".join(left) or "grammar card rewritten"),
                                     required=ck in self.rewrite_cks and self.p.rewrite_gloss)
                        if got is not None:
                            v[f] = got
                            continue
                    if left:
                        self.flag(ck, "LEFTOVER", f"{f} {v[f]!r} still contains {self.p.src_name} words {left}")
                    v[f] = self.en(v[f])
            eg = v.get("example_gloss")
            if isinstance(eg, str):
                v["example_gloss"] = self.en(eg)
            elif isinstance(eg, list):
                v["example_gloss"] = [self.en(x) for x in eg]
            if "note" in v:
                v["note"] = self.en_checked(v["note"], ck + "#note", "note", dict(en=v.get("gloss")))
            if isinstance(v.get("glosses"), dict):
                v["glosses"] = OrderedDict((self.T(k, "gloss-key", None, ck), self.en(val)) for k, val in v["glosses"].items())
                card = next((t for u in R["units"] for l in u["lessons"] for t in l.get("teaching") or [] if t["content_key"] == ck), None)
                for k in v["glosses"]:
                    if card and not k.startswith("<<") and not re.search(rf"(?<![\w]){re.escape(k)}(?![\w])", card["target"]["text"], re.I):
                        self.flag(ck, "GLOSS_KEY", f"gloss key {k!r} is not a whole-word token of the card text (keys must be single words that occur in it)")
        # -- header ---------------------------------------------------------------
        R, O = self.finish(R, O)
        return R, O

    def rekey_exercises(self, R: dict) -> None:
        """Exercise key tails carry source-language words and cast names (choose_ik_sport): rebuild them from the translated tested text."""
        for u in R["units"]:
            for l in u["lessons"]:
                seen: set[str] = set()
                for e in l["exercises"]:
                    old = e["content_key"]
                    verb = self.keymap[old].rsplit(".", 1)[1].split("_", 1)[0]
                    txt = e.get("tested_text") or ""
                    if not txt or txt.startswith("<<"):
                        continue
                    base = f"{verb}_{slug(txt, 3, self.p.translit)}"
                    tail, n = base, 2
                    while tail in seen:
                        tail, n = f"{base}_{n}", n + 1
                    seen.add(tail)
                    head = self.keymap[old].rsplit(".", 1)[0]
                    self.keymap[old] = f"{head}.{tail}"

    # -- teaching ---------------------------------------------------------------
    def teach(self, t: dict, ov: dict | None) -> None:
        tgt = t["target"]
        tgt["text"] = self.T(tgt["text"], "teach")
        self.card_tr[t["content_key"]] = tgt["text"]
        tgt["language_code"] = self.p.tgt
        if t["target"].get("speaker"):
            tgt["speaker"] = self.p.names(tgt["speaker"])
        exs = t.get("example")
        for e in ([exs] if isinstance(exs, dict) else (exs or [])):
            e["text"] = self.T(e["text"], "example")
            e["language_code"] = self.p.tgt
        # target tokens plus the tokens of the card's examples (the source course introduces example words on the card too)
        ex_toks = [w for e in ([exs] if isinstance(exs, dict) else (exs or [])) for w in tokens(e["text"])]
        t["introduced_tokens"] = list(OrderedDict.fromkeys(tokens(tgt["text"]) + ex_toks))
        for atom_txt in [tgt["text"]] + ([e["text"] for e in ([exs] if isinstance(exs, dict) else (exs or []))] if self.p.cs else []):
            self.lints(t["content_key"], atom_txt, kind="teach")

    # -- exercises ---------------------------------------------------------------
    def exercise(self, e: dict, ov: dict | None, lesson: dict) -> None:
        sp, tp = self.p.src, self.p.tgt
        ck, ty = e["content_key"], e["type"]
        ov = ov if ov is not None else {}
        if ov is not None and ck not in (self.ovl.get("exercises") or {}):
            self.flag(ck, "NO_OVERLAY", "exercise has no overlay entry; copied as is", "warn")
        en_inst = ov.get("instruction")
        ctx = dict(type=ty, instruction=en_inst)
        mk = e.get("media_asset_key")
        if mk and getattr(self, "media_tr", None) and mk in self.media_tr:
            ctx["media"] = self.media_tr[mk]                      # translated audio text: the context a tested span / feedback refers to
        # prompt blocks
        frame_src = None
        for b in (e.get("prompt") or {}).get("target_blocks") or []:
            if b.get("language_code") == sp:
                if BLANK in b["text"]:
                    frame_src = b["text"]
                    b["text"] = self.A(ck + "#frame", frame_src, "frame", dict(ctx, en=en_inst))
                else:
                    b["text"] = self.T(b["text"], "prompt")
                b["language_code"] = tp
            else:
                b["text"] = self.en(b["text"])
        pr_tr = [b["text"] for b in (e.get("prompt") or {}).get("target_blocks") or [] if b.get("language_code") == tp]
        if pr_tr:
            ctx["prompt"] = " ".join(pr_tr)
        # overlay fields
        if "instruction" in ov:
            ov["instruction"] = self.en_checked(ov["instruction"], ck + "#instruction", "instruction", ctx)
        has_opts = "correct_option" in ov and "distractors" in ov
        old_accepted = copy.deepcopy(ov.get("accepted_answers") or [])
        acc_vals = [a.get("value") for a in old_accepted]
        canon_src = (acc_vals[0] if acc_vals and isinstance(acc_vals[0], str) else ov.get("correct_option"))
        ans_target = (self.options_are_target(ov) if has_opts else (ty in TARGET_ANSWER_TYPES and isinstance(canon_src, str)))
        if ty == "translation" and e.get("prompt"):
            bl = (self.real_prompt_langs(e))
            if sp in bl:
                self.flag(ck, "REVERSE_TRANSLATION", "translation prompt is in the source language; answers are English. Not derived automatically")
        tested_src = e.get("tested_text", "")
        alts: list[str] = []
        canon_tr: str | None = None
        if ty == "matching_pairs":
            for p_ in e.get("pairs") or []:
                p_["left"] = self.pr(p_["left"])
                p_["right"] = self.pr(p_["right"])
            for a in ov.get("accepted_answers") or []:
                if isinstance(a.get("value"), list):
                    for pr in a["value"]:
                        pr["left"] = self.pr(pr["left"])
                        pr["right"] = self.pr(pr["right"])
        elif has_opts and ans_target:
            canon_tr = self.T_by_norm(ov["correct_option"])
            ov["correct_option"] = canon_tr
            dist = self.A(ck + "#dist", SEP.join(ov["distractors"]), "distractors",
                          dict(ctx, correct_src=canon_src, correct_tr=canon_tr, n=len(ov["distractors"])))
            ov["distractors"] = [x for x in re.split(r"\s*\|\|\s*", dist) if x] if not dist.startswith("<<") else ov["distractors"]
            if not dist.startswith("<<") and len(ov["distractors"]) != len(self.ovl["exercises"][ck]["distractors"]):
                self.flag(ck, "DIST_COUNT", f"expected {len(self.ovl['exercises'][ck]['distractors'])} distractors", "warn")
            ov["accepted_answers"] = [dict(a, value=canon_tr) if isinstance(a.get("value"), str) else a for a in old_accepted[:1]]
            alts = [canon_tr]
        elif has_opts:
            left = self.residual(self.en(SEP.join([ov["correct_option"]] + list(ov["distractors"]))))
            got = None
            if left:                                   # options quote or discuss the source language: authored (correct || distractor || ...)
                got = self.A(ck + "#opts", SEP.join([ov["correct_option"]] + list(ov["distractors"])), "options",
                             dict(ctx, why=",".join(left), n=len(ov["distractors"]) + 1), required=self.p.strict_residual)
            if got and not got.startswith("<<"):
                parts = [x for x in re.split(r"\s*\|\|\s*", got) if x]
                ov["correct_option"], ov["distractors"] = self.en(parts[0]), [self.en(d) for d in parts[1:]]
                ov["accepted_answers"] = [dict(a, value=ov["correct_option"]) if isinstance(a.get("value"), str) else a
                                          for a in ov.get("accepted_answers") or []]
            else:
                ov["correct_option"] = self.en(ov["correct_option"])
                ov["distractors"] = [self.en(d) for d in ov["distractors"]]
            for a in ov.get("accepted_answers") or []:
                if isinstance(a.get("value"), str):
                    a["value"] = self.en(a["value"])
        elif ans_target:
            canon_tr, alts = self.answers(ck, ty, ov, canon_src, acc_vals, frame_src, ctx)
        else:
            for a in ov.get("accepted_answers") or []:
                if isinstance(a.get("value"), str):
                    a["value"] = self.en(a["value"])
        # tested text
        if "tested_text" in e:
            e["tested_text"] = self.tested(e, ck, tested_src, canon_src, canon_tr, ctx)
        # word bank
        if "word_bank" in e:
            self.bank(e, ck, tested_src, e["tested_text"], alts, ctx)
        if "feedback" in ov:
            ov["feedback"] = self.en_checked(ov["feedback"], ck + "#feedback", "feedback",
                                             dict(ctx, correct=canon_tr, tested=e.get("tested_text")))
        # lints on learner-produced alternates
        if ans_target and ty in TARGET_ANSWER_TYPES:
            produced = ty in ("translation", "writing_prompt", "dialogue_response", "speak_response", "fill_in_blank")
            for a in alts:      # transcription types (dictation, listen_*) copy someone else's sentence: no gender/register lint
                self.lints(ck, a, kind="answer" if produced else "transcribe", answers=alts, src_text=canon_src)
        if "media_asset_key" in e:
            pass

    def pr(self, right: str) -> str:
        return self.T(right, "pair") if right in self.pair_target else self.en(right)

    def real_prompt_langs(self, e: dict) -> set[str]:
        return {b.get("language_code") for b in (e.get("prompt") or {}).get("target_blocks") or []}

    # -- answers / variants --------------------------------------------------------
    def answers(self, ck, ty, ov, canon_src, acc_vals, frame_src, ctx):
        strs = [v for v in acc_vals if isinstance(v, str)]
        src_punct = any(re.search(r"[.!?,;:]", v) for v in strs)
        src_plain = any(not re.search(r"[.!?,;:]", v) for v in strs) or not strs
        classes = list(OrderedDict.fromkeys(norm(v) for v in strs))
        by_class = OrderedDict()
        for v in strs:
            by_class.setdefault(norm(v), v)
        if ty != "fill_in_blank" and norm(canon_src) in self.atom_norms:
            base = self.T_by_norm(canon_src)
            alts = [base]
        else:
            src_show = SEP.join(by_class.values())
            got = self.A(ck + "#ans", src_show, "answer",
                         dict(ctx, source_forms=list(by_class.values()), frame=frame_src))
            alts = [x for x in re.split(r"\s*\|\|\s*", got) if x]
            base = alts[0]
        extra = self.p.tr_author.get(ck + "#alt")
        extra = self.p.names(extra) if extra else None
        if extra:
            alts += [x for x in re.split(r"\s*\|\|\s*", extra) if x]
        if len(classes) > len(alts) and ty not in ("fill_in_blank",) and not any(x.startswith("<<") for x in alts):
            self.flag(ck, "VARIANTS", f"source accepted {len(classes)} distinct forms ({list(by_class.values())}); "
                      f"{len(alts)} given. Add `{ck}#alt` if the target language has real alternatives", "warn")
        out: list[str] = []
        for x in alts:
            if src_punct:
                out.append(x)
            if src_plain:
                out.append(strip_punct(x) if ty != "fill_in_blank" else x)
        out = list(OrderedDict.fromkeys(out))
        if self.p.translit and ty in GERMAN_FREE_TEXT_TYPES:
            # the German compiler wants the full ASCII transliteration (ä->ae ...) of every typed answer with umlauts
            out = list(OrderedDict.fromkeys(out + [x.translate(TRANSLIT_DE) for x in out if x.translate(TRANSLIT_DE) != x]))
        canon_form = out[0]
        if "correct_option" in ov:
            ov["correct_option"] = base if re.search(r"[.!?]", canon_src) else strip_punct(base)
        new_acc = []
        proto = ov.get("accepted_answers") or [{"status": "correct"}]
        for v in out:
            new_acc.append(dict(proto[0], value=v))
        ov["accepted_answers"] = new_acc
        if ty == "fill_in_blank" and frame_src:
            frame_tr = self.p.tr_author.get(ck + "#frame")
            if frame_tr and not any(x.startswith("<<") for x in alts):
                full = frame_tr.replace(BLANK, alts[0])
                if self.p.tr_atoms and norm(full) not in {norm(self.p.tr_atoms.get(a, "")) for a in self.p.atoms}:
                    self.flag(ck, "FILL_CHECK", f"frame filled with the answer ({full!r}) is not a translated sentence of this unit", "warn")
                if frame_tr.count(BLANK) != frame_src.count(BLANK):
                    self.flag(ck, "BLANK_COUNT", "frame must keep the same number of ___ blanks")
        return base, alts

    def tested(self, e, ck, tested_src, canon_src, canon_tr, ctx):
        """tested_text: sentence atom, the answer, or an authored span."""
        if canon_tr is not None and canon_src and norm(tested_src) == norm(canon_src):
            if canon_tr.startswith("<<"):
                return canon_tr
            if tested_src != strip_punct(canon_src) and tested_src == boundary_strip(canon_src):
                return boundary_strip(canon_tr)          # dictation: the compiler compares with the audio text, inner commas included
            body = strip_punct(canon_tr)
            if self.p.cs:
                return body
            return body if tested_src == strip_punct(canon_src) else body.lower() if tested_src == tested_src.lower() else body
        aid = self.atom_norms.get(norm(tested_src))
        if aid is not None:
            atom_tr = self.T_by_norm(tested_src)
            if atom_tr.startswith("<<"):
                return atom_tr
            body = strip_punct(atom_tr)
            keep_case = tested_src == strip_punct(self.id_text[aid])
            return body if keep_case or self.p.cs else body.casefold()
        v = self.A(ck + "#tested", tested_src, "tested", dict(ctx, canon=canon_tr))
        return v

    def bank(self, e, ck, tested_src, tested_tr, alts, ctx):
        src_tokens = [t.casefold() for t in tokens(tested_src)]
        bank_src = [t.casefold() for t in e["word_bank"]]
        if sorted(src_tokens) != sorted(bank_src):
            got = self.A(ck + "#bank", " | ".join(e["word_bank"]), "bank", dict(ctx, tested=tested_tr))
            e["word_bank"] = [x.strip() for x in got.split("|") if x.strip()]
            return
        if tested_tr.startswith("<<"):
            e["word_bank"] = ["<<bank>>"]
            return
        tiles = tokens(tested_tr)
        e["word_bank"] = shuffled(tiles)
        # every accepted alternate must be buildable from the tiles
        for a in alts:
            if sorted(t.casefold() for t in tokens(a)) != sorted(t.casefold() for t in tiles):
                self.flag(ck, "TILES", f"accepted variant {a!r} cannot be built from tiles {tiles}: word-order variants need their own tile set")

    # -- lints -------------------------------------------------------------------
    def lints(self, key: str, text: str, kind: str, answers: list[str] | None = None, src_text: str | None = None):
        if text.startswith("<<"):
            return
        tp, sp = self.p.tgt, self.p.src
        cfg = CFG.get(tp, {})
        for pat, fix in cfg.get("contractions", []):
            if re.search(pat, text):
                self.flag(key, "CONTRACTION", f"{text!r}: obligatory contraction not applied (use {fix!r}); never accept the uncontracted form as a variant")
        if src_text:
            src_reg = register_of(src_text, sp)
            tr_reg = register_of(text, tp) if cfg else None
            if src_reg and tr_reg and src_reg != tr_reg:
                self.flag(key, "REGISTER", f"source is {src_reg} ({src_text!r}) but translation reads {tr_reg} ({text!r})")
        g = cfg.get("gender")
        if g and kind == "answer" and g.get("mode") == "agent":
            alt = agent_gender_alt(text)
            if alt and norm(alt) not in {norm(x) for x in (answers or [])}:
                self.flag(key, "GENDER", f"speaker-gendered noun in {text!r}; add the other gender ({alt!r}) via `{key}#alt`")
        elif g and kind == "answer":
            m = re.search(g["copula"] + r"\s+(?:(?:muy|tan|un poco|bastante|molto|più)\s+)?(\w{3,}?)(os|as|o|a|i|e)\b", text, re.I)
            if m:
                stem, end = m.group(2), m.group(3)
                if (stem + end).lower() not in g["skip"]:
                    flip = dict(g["swap"])
                    flip.update({b: a for a, b in g["swap"]})
                    other = flip.get(end.lower())
                    if other:
                        alt = text[:m.start(2)] + stem + other + text[m.end():]
                        if norm(alt) not in {norm(x) for x in (answers or [])}:
                            self.flag(key, "GENDER", f"speaker-gendered form in {text!r}; add the other gender ({alt!r}) via `{key}#alt`")
        if self.p.cs:
            self.case_lint(key, text)

    def case_lint(self, key: str, text: str) -> None:
        """Case-sensitive targets (German): a known common noun written lowercase, or a known non-noun capitalised mid-sentence.
        Sentence starts, quoted phrases (*Was machst du?*) and cast names are skipped; nominalised verbs/adjectives (Kochen, etwas Neues)
        are legitimate exceptions to acknowledge in ack.json."""
        up, low = self.p.lexicon
        start = True
        for m in re.finditer(r"[^\W\d_][\w'’\-]*|[.!?:\n*\"“„]", text):
            t = m.group(0)
            if t in (".", "!", "?", ":", "\n", "*", '"', "“", "„"):
                start = True
                continue
            first, start = start, False
            if first or t in up or t in low or t in self.p.case_ok or t in self.p.names_map.values():
                continue
            cap = t[0].upper() + t[1:]
            if t[0].islower() and cap in up and cap not in self.p.case_ok and cap not in self.p.proper_nouns:
                self.flag(key, "CASE", f"{t!r} in {text!r}: German nouns are capitalised ({cap!r})")
            elif t[0].isupper() and (t[0].lower() + t[1:]) in low:
                self.flag(key, "CASE", f"{t!r} in {text!r}: capitalised mid-sentence, but {t[0].lower() + t[1:]!r} is a known non-noun")

    # -- header -----------------------------------------------------------------
    def finish(self, R: dict, O: dict) -> tuple[dict, dict]:
        tp, sp = self.p.tgt, self.p.src
        base_r = dd.load(self.p.base_real)
        base_o = dd.load(self.p.base_ovl)
        note = (f"Derived by scripts/derive_target.py from {sp}/{self.stem}.yaml ({self.p.src_pair} overlay): target text "
                f"translated, distractors/notes/feedback authored, tiles and tokens derived. Needs native {self.p.new_name} review "
                f"(register, naturalness, distractor plausibility). No sibling-file consultation was done for the authored parts "
                f"beyond the source ctx shown in author.src.json.")
        R["target_language"] = tp
        R["cefr_level"] = "A1"
        R["status"] = "complete_draft"
        R["generation_provenance"] = {
            "method": "ai_generated", "authoring_system": "claude", "human_reviewed": False,
            "source_material": f"Translated from {sp} A1 unit {self.src_no:02d} ({self.stem}) by scripts/derive_target.py.",
        }
        R["review"] = {"status": "unreviewed", "required_next_reviewer": "native_speaker_review", "notes": note}
        R["course"] = copy.deepcopy(base_r["course"])
        R["realization_version"] = base_r.get("realization_version", R.get("realization_version"))
        for u in R["units"]:
            u.pop("planned_lesson_count", None) if False else None
        newO = OrderedDict()
        for k in ("schema_version", "overlay_version"):
            newO[k] = base_o.get(k, O.get(k))
        newO["overlay_key"] = f"{self.p.new_pair}.a1.unit{self.new_no:02d}"
        newO["source_language"] = base_o["source_language"]
        newO["target_language"] = tp
        newO["status"] = "complete_draft"
        newO["generation_provenance"] = {"method": "ai_generated", "authoring_system": "claude", "human_reviewed": False}
        newO["review"] = {"status": "unreviewed", "required_next_reviewer": "native_speaker_review", "notes": note}
        if "answer_policy" in base_o:
            newO["answer_policy"] = copy.deepcopy(base_o["answer_policy"])
        newO["course"] = {"title": base_o["course"]["title"],
                          "description": self.en(O["course"]["description"])}
        for k in ("units", "lessons", "teaching", "exercises"):
            if k in O:
                newO[k] = O[k]
        R = self.remap(R)
        newO = self.remap(newO)
        return R, newO

    def remap(self, o):
        if isinstance(o, dict):
            return OrderedDict((self.keymap.get(k, k) if isinstance(k, str) else k, self.remap(v)) for k, v in o.items())
        if isinstance(o, list):
            return [self.remap(v) for v in o]
        if isinstance(o, str):
            return self.keymap.get(o, o)
        return o


# ---------------------------------------------------------------------------
# Plan (all units of one run)
# ---------------------------------------------------------------------------
class Plan:
    def __init__(self, args, work: Path):
        self.src_pair, self.new_pair = args.source, args.new
        self.src, self.tgt = self.src_pair.split("-")[1], self.new_pair.split("-")[1]
        self.src_name = CFG.get(self.src, {}).get("name", self.src)
        self.new_name = CFG.get(self.tgt, {}).get("name", self.tgt)
        self.cs = bool(CFG.get(self.tgt, {}).get("case_sensitive"))      # case carries meaning (German nouns)
        self.translit = bool(CFG.get(self.tgt, {}).get("translit"))
        self.strict_residual = bool(CFG.get(self.tgt, {}).get("strict_residual"))
        self.per_card_keys = bool(CFG.get(self.tgt, {}).get("per_card_keys"))
        self.rewrite_gloss = bool(CFG.get(self.tgt, {}).get("rewrite_gloss"))
        self.rekey = bool(CFG.get(self.tgt, {}).get("rekey_exercises"))     # exercise key tails re-derived from the translation
        self.suffixes = dict(kv.split("=", 1) for kv in (getattr(args, "suffixes", None) or "").split(",") if "=" in kv)
        self._lex = None
        self.work = work
        self.names_map = dict(kv.split("=", 1) for kv in (args.names or "").split(",") if "=" in kv)
        self.units = args.units
        self.atoms: OrderedDict[str, str] = OrderedDict()
        self.atom_ctx: dict[str, dict] = {}
        self.author: OrderedDict[str, str] = OrderedDict()
        self.author_ctx: dict[str, dict] = {}
        self.missing: set[str] = set()
        self.flags: list[dict] = []
        self.media_slugs: set[str] = set()
        self.derived: dict[str, str] = {}
        self.tr_atoms = load_json(work / "atoms.tr.json")
        self.tr_author = load_json(work / "author.tr.json")
        self.acks = load_json(work / "ack.json")
        # base files of the target course: header/answer policy come from them
        group = args.group or self.new_pair
        real, ovl = manifest_group(group)
        self.group = group
        self.base_real, self.base_ovl = real[0], ovl[0]
        first = args.first_unit or next_unit_number(self.tgt)
        self.derivers = [UnitDeriver(self, s, first + i) for i, s in enumerate(self.units)]

    @property
    def en_vocab(self) -> set[str]:
        """Words used in the English fields of the other courses' overlays (anything the source course quotes is not in here)."""
        global _EN_VOCAB
        if _EN_VOCAB is None:
            v: set[str] = set()
            for pair in ("en-de", "en-es", "en-fr", "en-it", "en-pl", "en-ro"):
                if pair in (self.src_pair,):
                    continue
                for fp in (CONTENT / f"overlays/{pair}").glob("*.yaml"):
                    v.update(re.findall(r"[^\W\d_]{3,}", fp.read_text(encoding="utf-8").casefold()))
            _EN_VOCAB = v
        return _EN_VOCAB

    @property
    def cast_words(self) -> set[str]:
        self.src_lexicon                                      # loads _src_names / _gloss_words
        return ({w.casefold() for kv in list(self.names_map.items()) for w in kv} | self._src_names | self._gloss_words
                | {"opa", "taalcafé", "taalcafe"})

    @property
    def src_lexicon(self) -> set[str]:
        """Lowercase words of the source target course (every introduced token of its realizations): recognises
        source-language pair sides whose inflected forms occur nowhere else (leest, luistert)."""
        if getattr(self, "_src_lex", None) is None:
            raw: set[str] = set()
            for fp in (CONTENT / f"realizations/{self.src}").glob("*.yaml"):
                for m in re.finditer(r"introduced_tokens:\s*\[([^\]]*)\]", fp.read_text(encoding="utf-8")):
                    raw.update(re.findall(r"[^\W\d_]{2,}", m.group(1)))
            low = {w for w in raw if w[0].islower()}
            self._src_names = {w.casefold() for w in raw if w[0].isupper() and w.casefold() not in low}    # Marieke, Pico: never lowercase
            self._src_lex = {w.casefold() for w in raw}
            # English glosses of the source lexemes are English words even when spelled like a source word (blond)
            self._gloss_words: set[str] = set()
            try:
                spec = importlib.util.spec_from_file_location("bf_src_" + self.src, ROOT / f"scripts/backfill_lexemes_{self.src_pair.split('-')[0]}_{self.src}.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for name in dir(mod):
                    d = getattr(mod, name)
                    if name.endswith("GLOSSES") and isinstance(d, dict):
                        for v in d.values():
                            if isinstance(v, str):
                                self._gloss_words.update(re.findall(r"[^\W\d_]{3,}", v.casefold()))
            except Exception:
                pass
        return self._src_lex

    @property
    def lexicon(self) -> tuple[set[str], set[str]]:
        """(capitalised, lowercase) lexemes already known to the target backfill."""
        if self._lex is None:
            try:
                g = load_backfill(self).GLOSSES
            except (OSError, SystemExit, AttributeError):
                g = {}
            self._lex = ({k for k in g if k[:1].isupper()}, {k for k in g if k[:1].islower()})
        return self._lex

    @property
    def proper_nouns(self) -> set[str]:
        try:
            mod = load_backfill(self)
            return set(getattr(mod, "PROPER_NOUNS", ())) | set(getattr(mod, "POS_SETS", {}).get("proper_noun", ()))
        except (OSError, SystemExit, AttributeError):
            return set()

    case_ok = frozenset({"Sie", "Ihnen", "Ihr", "Ihre", "Ihren", "Ihrem", "Ihrer", "Ihres"})   # formal address: capital is correct mid-sentence

    def names(self, s: str) -> str:
        for a, b in self.names_map.items():
            s = re.sub(rf"\b{re.escape(a)}\b", b, s)
        return s

    def add_atom(self, aid, text, kind, en, where, unit):
        self.atoms.setdefault(aid, text)
        c = self.atom_ctx.setdefault(aid, dict(kind=kind, en=[], where=[]))
        if en and en not in c["en"] and len(c["en"]) < 3:
            c["en"].append(en)
        if where and where not in c["where"] and len(c["where"]) < 2:
            c["where"].append(where)
        if kind in ("teach", "title") and c["kind"] in ("media", "prompt", "pair", "quote"):
            c["kind"] = kind
        reg = register_of(text, self.src)
        if reg:
            c["register"] = reg

    def add_author(self, slot, src, kind, ctx, unit):
        self.author.setdefault(slot, src)
        self.author_ctx.setdefault(slot, dict(ctx, kind=kind))

    def build_all(self):
        out = []
        for d in self.derivers:
            out.append((d,) + d.build())
        return out


def plain(o):
    if isinstance(o, dict):
        return {k: plain(v) for k, v in o.items()}
    if isinstance(o, list):
        return [plain(v) for v in o]
    return o


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def dump_json(p: Path, o) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def manifest_group(group: str):
    fp = MANIFEST / f"{group}.txt"
    for line in fp.read_text(encoding="utf-8").splitlines():
        if line.startswith(group + "|"):
            parts = line.split("|")
            return [ROOT / x for x in parts[1].split()], [ROOT / x for x in parts[2].split()]
    raise SystemExit(f"{group!r} missing in {fp}")


def next_unit_number(tgt: str) -> int:
    nums = [int(m.group(1)) for p in (CONTENT / f"realizations/{tgt}").glob("*.yaml")
            if (m := re.match(r"^[ab][12]_unit(\d+)_", p.name))]
    return max(nums, default=0) + 1


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def make_plan(args) -> Plan:
    work = Path(args.work) if args.work else DEFAULT_WORK / (args.new or "en-es")
    work.mkdir(parents=True, exist_ok=True)
    saved = load_json(work / "plan.json")
    args.source = args.source or saved.get("source") or "en-nl"          # without flags the saved plan decides, never the en-es default
    args.new = args.new or saved.get("new") or "en-es"
    if saved.get("new") == args.new:
        args.group = args.group or saved.get("group")
    if not args.units:
        args.units = saved.get("units")
        args.first_unit = args.first_unit or saved.get("first_unit")
        args.names = args.names or saved.get("names")
        args.suffixes = getattr(args, "suffixes", None) or saved.get("suffixes")
        if not args.units:
            raise SystemExit("--units a1_unitNN_name ... required on first run")
    return Plan(args, work)


def guide(plan: Plan) -> str:
    return f"""# Translator guide: {plan.src_name} -> {plan.new_name} (derive_target)

Files in this folder
  atoms.src.json     {{id: {plan.src_name} text}}  -> write atoms.tr.json {{id: {plan.new_name} text}}   (TRANSLATE)
  atoms.ctx.json     English meaning, kind, register, where used (read only)
  author.src.json    {{slot: text}}  -> write author.tr.json {{slot: ...}}                  (AUTHOR, not translate)
  author.ctx.json    what the slot is for, what the expected answer is
  lexemes.src.json   (after `lexemes`) token needs "gloss | pos"                             (AUTHOR)
  ack.json           {{"<id>:<FLAG>": "why this lint is a false positive"}}

Rules
* Natural {plan.new_name} for the English meaning in atoms.ctx.json, not a calque of the {plan.src_name} wording.
  Keep the cast: write the {plan.src_name} names as they are; --names maps them ({plan.names_map or 'none'}) after translation.
* Register: ctx.register=formal -> usted-style address of the {plan.new_name} formal form; informal -> tu-style.  Match the sibling units.
* Tiles/word order: answers are cut into tiles from the translated sentence; give word-order alternatives (`#alt`)
  ONLY if they use exactly the same words.
* Slots (all values plain strings):
    <ck>#ans   canonical answer || alternative || ...   (fill_in_blank: the blank filler(s))
    <ck>#alt   extra accepted answers || ...  (gender, formal/informal, regional); may be added to ANY answer exercise
    <ck>#dist  wrong {plan.new_name} options || ...      (same count as the source; plausible learner errors in {plan.new_name}, never English)
    <ck>#frame sentence with ___ for the blank (same number of blanks)
    <ck>#tested the short {plan.new_name} span the item tests; must occur in the (translated) audio text
    <ck>#bank  tile1 | tile2 | ...                       (only when the source tiles included distractors)
    <ck>#note / #feedback / #instruction  rewrite in English about {plan.new_name} (the source text discusses {plan.src_name})
* Obligatory contractions are always applied (es del/al, fr du/au, it nel/del...); never list the uncontracted form as a variant.
* Gender: when the learner speaks as themselves with a gendered adjective, add the other gender via `#alt`.
* Lexemes (`lexemes.tr.json`): {{token: "english gloss | pos"}}; for a case-sensitive target a sentence-initial capital of a non-noun
  is written as {{"Hast": "=hast"}} (citation-form alias) next to its own entry {{"hast": "you have (informal) | verb"}}.
{CFG.get(plan.tgt, {}).get("note", "")}
"""


def cmd_extract(args):
    plan = make_plan(args)
    built = plan.build_all()
    w = plan.work
    # keep earlier translations for unchanged text (ids are text hashes)
    dump_json(w / "plan.json", dict(source=plan.src_pair, new=plan.new_pair, units=plan.units,
                                    first_unit=plan.derivers[0].new_no, names=args.names, group=plan.group,
                                    suffixes=getattr(args, "suffixes", None)))
    atoms = OrderedDict(sorted(plan.atoms.items(), key=lambda kv: kv[0]))
    dump_json(w / "atoms.src.json", plan.atoms)
    dump_json(w / "atoms.ctx.json", plan.atom_ctx)
    dump_json(w / "author.src.json", plan.author)
    dump_json(w / "author.ctx.json", plan.author_ctx)
    (w / "GUIDE.md").write_text(guide(plan), encoding="utf-8")
    view = []
    for aid, text in plan.atoms.items():
        c = plan.atom_ctx[aid]
        view.append(f"{aid}\t{c['kind']}\t{c.get('register','')}\t{text!r}\t{' / '.join(c['en'])}")
    (w / "atoms.view.tsv").write_text("\n".join(view) + "\n", encoding="utf-8")
    by_kind = defaultdict(int)
    for s, c in plan.author_ctx.items():
        by_kind[c["kind"]] += 1
    todo_a = [a for a in plan.atoms if a not in plan.tr_atoms]
    todo_s = [s for s in plan.author if s not in plan.tr_author and plan.author_ctx[s]["kind"] != "alt"]
    print(f"units: {', '.join(d.new_stem for d in plan.derivers)}")
    print(f"atoms to translate: {len(todo_a)} of {len(plan.atoms)}")
    print(f"author slots: {len(todo_s)} of {len(plan.author) - by_kind.get('alt', 0)}  {dict(by_kind)}")
    print(f"work dir: {w}")


def active_flags(plan: Plan) -> list[dict]:
    out = []
    for f in plan.flags:
        if f"{f['id']}:{f['code']}" in plan.acks:
            continue
        out.append(f)
    return out


def cmd_status(args):
    plan = make_plan(args)
    plan.build_all()
    missing = sorted(plan.missing)
    print(f"missing translations/slots: {len(missing)}")
    for m in missing[:40]:
        print("  ", m)
    fl = active_flags(plan)
    errs = [f for f in fl if f["level"] == "error"]
    print(f"flags: {len(errs)} errors, {len(fl) - len(errs)} warnings")
    for f in fl[:60]:
        print(f"  [{f['level']}] {f['code']} {f['id']}: {f['msg'][:160]}")
    dump_json(plan.work / "report.json", dict(missing=missing, flags=fl))


def new_tokens(plan: Plan, built) -> tuple[dict, object]:
    """Tokens of the derived units that the target backfill has no gloss for.

    Case-sensitive targets (German): a sentence-initial capital of a non-noun (`Hast`) is its own raw token. Give it
    the value `=hast` in lexemes.tr.json to map it to its citation form instead of glossing it as a noun."""
    mod = load_backfill(plan)
    tr = load_json(plan.work / "lexemes.tr.json")
    out: dict[str, dict] = {}
    for d, R, O in built:
        for u in R["units"]:
            for l in u["lessons"]:
                for t in l.get("teaching") or []:
                    for raw in t.get("introduced_tokens") or []:
                        raw = str(raw)
                        alias = tr.get(raw, "")
                        tok = alias[1:].strip() if alias.startswith("=") else mod.normalize(raw)
                        if tok in mod.GLOSSES or tok in out:
                            continue
                        info = dict(example=t["target"]["text"], en=(O["teaching"].get(t["content_key"]) or {}).get("gloss"),
                                    unit=d.new_stem)
                        if plan.cs and tok[:1].isupper() and tok[:1].lower() + tok[1:] in mod.GLOSSES:
                            info["hint"] = f"capitalised: gloss as a NEW noun, or write '={tok[:1].lower() + tok[1:]}' if it is only a sentence-initial form"
                        elif plan.cs and tok[:1].isupper():
                            info["hint"] = "capitalised: a noun/proper noun, or '=lowercase' (and gloss that) for a sentence-initial verb/adjective/pronoun"
                        out[tok] = info
    return out, mod


def load_backfill(plan: Plan):
    path = ROOT / f"scripts/backfill_lexemes_{plan.src_pair.split('-')[0]}_{plan.tgt}.py"
    spec = importlib.util.spec_from_file_location("bf_" + plan.tgt, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_lexemes(args):
    plan = make_plan(args)
    built = plan.build_all()
    if plan.missing & set(plan.atoms):
        raise SystemExit("translate atoms.src.json first (atoms missing: %d)" % len(plan.missing & set(plan.atoms)))
    toks, _mod = new_tokens(plan, built)
    tr = load_json(plan.work / "lexemes.tr.json")
    dump_json(plan.work / "lexemes.src.json", {t: "" for t in toks})
    dump_json(plan.work / "lexemes.ctx.json", toks)
    todo = [t for t in toks if t not in tr]
    print(f"new tokens needing a gloss: {len(toks)} ({len(todo)} not yet in lexemes.tr.json)")
    print("format: {token: 'english gloss | pos'}   pos in noun verb adjective adverb pronoun preposition particle phrase proper_noun (noun is the default)")


GEN_BEGIN = "# --- derive_target.py: derived units (generated; keep markers) ---"
GEN_END = "# --- end derive_target.py ---"


def write_backfill_block(plan: Plan, lex: dict[str, str]) -> Path:
    path = ROOT / f"scripts/backfill_lexemes_{plan.src_pair.split('-')[0]}_{plan.tgt}.py"
    text = path.read_text(encoding="utf-8")
    existing: dict[str, tuple[str, str]] = {}
    cites: dict[str, str] = {}
    if GEN_BEGIN in text:
        block = text[text.index(GEN_BEGIN):text.index(GEN_END)]
        m = re.search(r"DERIVED_TARGET_GLOSSES: dict\[str, str\] = (\{.*?\n\})\nDERIVED_TARGET_POS", block, re.S)
        g = eval(m.group(1)) if m else {}  # literal dict written by this tool
        m2 = re.search(r"DERIVED_TARGET_POS: dict\[str, str\] = (\{.*?\n\})\n", block, re.S)
        p = eval(m2.group(1)) if m2 else {}
        m3 = re.search(r"DERIVED_TARGET_CITATION: dict\[str, str\] = (\{.*?\n\})\n", block, re.S)
        cites = eval(m3.group(1)) if m3 else {}
        for k, v in g.items():
            existing[k] = (v, p.get(k, "noun"))
    for tok, val in lex.items():
        if val.strip().startswith("="):                      # sentence-initial form -> citation form
            cites[tok] = val.strip()[1:].strip()
            continue
        parts = [x.strip() for x in val.split("|")]          # "gloss | pos" (the pilot read the 3rd field and lost every pos)
        existing[tok] = (parts[0], (parts[1] if len(parts) > 1 else "") or "noun")
    gl = "{\n" + "".join(f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v[0], ensure_ascii=False)},\n" for k, v in sorted(existing.items())) + "}"
    ps = "{\n" + "".join(f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v[1])},\n" for k, v in sorted(existing.items()) if v[1] != "noun") + "}"
    cs = "{\n" + "".join(f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in sorted(cites.items())) + "}"
    cite_code = ("if DERIVED_TARGET_CITATION and \"CITATION_FORMS\" in globals():\n    CITATION_FORMS.update(DERIVED_TARGET_CITATION)\n"
                 if cites else "")
    block = (f"{GEN_BEGIN}\n"
             f"DERIVED_TARGET_GLOSSES: dict[str, str] = {gl}\nDERIVED_TARGET_POS: dict[str, str] = {ps}\n"
             f"DERIVED_TARGET_CITATION: dict[str, str] = {cs}\n" + cite_code +
             "for _tok, _gloss in DERIVED_TARGET_GLOSSES.items():\n    GLOSSES.setdefault(_tok, _gloss)\n"
             "for _tok, _pos in DERIVED_TARGET_POS.items():\n    POS_SETS.setdefault(_pos, set()).add(_tok)\n"
             f"{GEN_END}\n")
    if GEN_BEGIN in text:
        text = text[:text.index(GEN_BEGIN)] + block + text[text.index(GEN_END) + len(GEN_END) + 1:]
    else:
        anchor = 'POS_SETS["noun"] = set(GLOSSES)'
        if anchor not in text:
            raise SystemExit(f"{path.name}: anchor {anchor!r} not found")
        text = text.replace(anchor, block + "\n" + anchor, 1)
    path.write_text(text, encoding="utf-8")
    return path


def cmd_inject(args):
    plan = make_plan(args)
    built = plan.build_all()
    if plan.missing and not args.allow_missing:
        raise SystemExit(f"{len(plan.missing)} translations/slots missing (run `status`): {sorted(plan.missing)[:8]}")
    fl = active_flags(plan)
    errs = [f for f in fl if f["level"] == "error"]
    for f in fl:
        print(f"[{f['level']}] {f['code']} {f['id']}: {f['msg'][:200]}")
    if errs and not args.force:
        raise SystemExit(f"{len(errs)} lint errors; fix them or acknowledge in ack.json (or --force)")
    # lexemes
    toks, _mod = new_tokens(plan, built)
    lex = load_json(plan.work / "lexemes.tr.json")
    missing_lex = [t for t in toks if t not in lex]
    if missing_lex and not args.skip_lexemes:
        raise SystemExit(f"{len(missing_lex)} tokens lack a gloss (run `lexemes`, fill lexemes.tr.json): {missing_lex[:10]}")
    written = []
    new_real, new_ovl = [], []
    for d, R, O in built:
        rp = CONTENT / f"realizations/{plan.tgt}/{d.new_stem}.yaml"
        op = CONTENT / f"overlays/{plan.new_pair}/{d.level}_unit{d.new_no:02d}.yaml"
        dd.dump(plain(R), rp)
        dd.dump(plain(O), op)
        written += [rp, op]
        new_real.append(rp.relative_to(ROOT).as_posix())
        new_ovl.append(op.relative_to(ROOT).as_posix())
    update_manifest(plan.group, new_real, new_ovl)
    if not args.skip_lexemes and lex:
        # all of lexemes.tr.json: gloss entries and `=citation` aliases (an alias target may not occur as a raw token itself)
        written.append(write_backfill_block(plan, dict(lex)))
    for p in written:
        print("wrote", p.relative_to(ROOT))


def update_manifest(group: str, real: list[str], ovl: list[str]) -> None:
    fp = MANIFEST / f"{group}.txt"
    lines = fp.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if line.startswith(group + "|"):
            parts = line.split("|")
            r, o = parts[1].split(), parts[2].split()
            r += [x for x in real if x not in r]
            o += [x for x in ovl if x not in o]
            if len(r) != len(o):
                raise SystemExit("manifest realization/overlay counts differ")
            line = "|".join([parts[0], " ".join(r), " ".join(o)])
        out.append(line)
    fp.write_text("\n".join(out) + "\n", encoding="utf-8")


def cmd_check(args):
    plan = make_plan(args)
    py = ROOT / ".content-venv/bin/python"
    py = str(py if py.exists() else sys.executable)
    real, ovl = manifest_group(plan.group)
    rc = 0
    for cmd in (
        [py, "scripts/compile_content.py", "validate", "--realization", *map(str, real), "--overlay", *map(str, ovl)],
        [py, "scripts/compile_content.py", "compile", "--realization", *map(str, real), "--overlay", *map(str, ovl), "--out", str(plan.work / "compiled.json")],
        [py, f"scripts/backfill_lexemes_{plan.src_pair.split('-')[0]}_{plan.tgt}.py", "--dry-run"],
    ):
        print("$", " ".join(cmd[:3]), "...")
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        print("\n".join(tail))
        rc |= r.returncode
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("extract", cmd_extract), ("status", cmd_status), ("lexemes", cmd_lexemes),
                     ("inject", cmd_inject), ("check", cmd_check)):
        p = sub.add_parser(name)
        p.add_argument("--source", help="source course pair (default: the saved plan, else en-nl)")
        p.add_argument("--new", help="new target course pair (default: the saved plan, else en-es)")
        p.add_argument("--group", help="manifest group receiving the units (default = --new)")
        p.add_argument("--units", nargs="*", help="source realization stems, e.g. a1_unit23_money")
        p.add_argument("--first-unit", type=int, help="unit number of the first derived unit (default: next free)")
        p.add_argument("--names", help="cast map, e.g. Lotte=Elena,Omar=Mateo")
        p.add_argument("--suffixes", help="topic name map for file names / unit keys, e.g. sporten=sport,vervoer=verkehr")
        p.add_argument("--work")
        p.add_argument("--allow-missing", action="store_true")
        p.add_argument("--skip-lexemes", action="store_true")
        p.add_argument("--force", action="store_true")
        p.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    return args.fn(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
