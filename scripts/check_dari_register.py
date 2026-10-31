#!/usr/bin/env python3
"""Dialect/register checker for Dari (prs) content -- closes registry class 1.28.

WHY THIS EXISTS
---------------
`docs/CONTENT_DEFECT_REGISTRY.md` class **1.28 "Dari (prs) dialect
split-brain"** has been UNPREVENTED at the tooling layer since 2026-07-07:
Dari and Iranian Persian share a script and most of their lexicon, so a
Farsi-register string inside a Dari file is invisible to every existing
validator (the compiler validates structure, not dialect) *and* to a
casual read. The class recurred on 2026-07-22, when `overlays/prs-en/`
A1 units 01-24 turned out to be written in Iranian Persian register and
partly byte-copied from `overlays/fa-en/` -- on the first two units a
Dari learner ever sees.

DESIGN: WHY A CURATED LIST, NOT A CORPUS DIFF
---------------------------------------------
A purely data-driven "token absent from known-good Dari" rule was tried
first and produces garbage: A1 Dari content has no occasion to use
شواهد / بودجه / ادعا / منبع, so a frequency diff flags ordinary B1/B2
topic vocabulary as a dialect defect. That is precisely the noisy-
validator failure this project has been burned by before (a Codex
validator once emitted 360 false positives and taught everyone to ignore
validators). So the marker inventory below is *linguistically* curated --
each entry is a form where Dari and Iranian Persian genuinely diverge --
and then *empirically* validated to fire zero times on the known-good
Dari corpus.

Equally important is what is NOT flagged. Dari and Iranian Persian
overlap enormously; an over-broad find/replace would corrupt correct
content. These are deliberately NOT markers:

  * shared core vocabulary (days, numbers, family, colours, food);
  * the colloquial 3sg `-ه` clitic copula and verb endings
    (می‌کنه/می‌شه/می‌گه/خوبه/بازه) -- Kabuli Dari does this too;
  * `اگه`, `باشه`, `بریم`, `برم`, `همدیگه`, `دیگه` -- all attested in the
    known-good Dari corpus;
  * `می‌خواهم`/`می‌خواهد`/`می‌تواند` -- full uncontracted forms are the
    Dari norm, not a Farsi import (only the *Tehrani contractions*
    می‌خوام/می‌تونم are flagged);
  * `چتر`, `قطار`, `کیف`, `بلیط`, `دوچرخه`, `مهندس`, `معلم` -- used as
    taught target-language words in `realizations/prs/`, so they cannot
    be hard errors even though a more Afghan alternative exists.

TIERS
-----
1. `dialect_marker` -- forms that occur ZERO times in the entire
   known-good Dari corpus and are unambiguously Iranian Persian.
   Scanned in EVERY prs lane (realizations, both overlay directions,
   both practice packs).
2. `overlay_register` -- forms that are CORRECT in the formal-written
   register of `realizations/prs/` but violate the `prs-en` overlay
   lane's register pin (`docs/content/CLAUDE.md`: "prs-en overlay lane:
   colloquial Dari, می‌تانین/استه style"). Scanned in `overlays/prs-en/`
   ONLY, with per-file thresholds calibrated so the known-good band
   (A1 units 30-68) is clean.
3. `fa_transplant` -- long prose strings byte-identical to a string in
   `overlays/fa-en/` that ALSO carry an Iranian register marker. Short
   identical strings are expected and fine (a two-word vocabulary gloss
   is legitimately the same in both languages); a full copied *sentence*
   carrying Farsi register is not.

SUPPRESSIONS (why a hit can be legitimate)
------------------------------------------
`overlays/en-prs/` teaches Dari to English speakers and deliberately
names the Iranian word it is contrasting against ("دواخانه ... distinct
from the Iranian Farsi داروخانه"). Two suppressions handle this without
weakening the check:
  * majority-Latin-script strings (English explanatory prose), and
  * any string containing an explicit contrast cue (see CONTRAST_CUES).
Metadata fields (`review.notes`, `generation_provenance.*`,
`register_policy`, `source_material`, `introduced_tokens`) are never
scanned -- they are prose about the content, not content.

NOT COVERED (deliberate scope cuts -- check these by hand)
----------------------------------------------------------
  * `scripts/backfill_lexemes_prs_en.py` -- a .py file, not YAML, but it
    carries hand-written Dari glosses derived from `prs-en` A1 units
    01/02 and therefore inherits their register (it currently contains
    آموزگار, دلار and formal است/می‌کند/می‌شود). Repair it in the same
    wave as those units or the SRS lexeme glosses stay Farsi-register.
  * `frontend/src/i18n/*.json` app-chrome locales.
  * Anything a marker inventory cannot see: word order, idiom choice,
    pragmatics. This closes a bug CLASS, not the need for review.

Usage:
    .content-venv/bin/python3 scripts/check_dari_register.py
    .content-venv/bin/python3 scripts/check_dari_register.py --known-good
    .content-venv/bin/python3 scripts/check_dari_register.py --details
    .content-venv/bin/python3 scripts/check_dari_register.py --audit

Exit code 1 if any gated finding is reported, else 0.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT = REPO_ROOT / "docs" / "content"

# --------------------------------------------------------------------------
# Corpora
# --------------------------------------------------------------------------

# Every lane that must be Dari. `known_good` marks the bands that are
# verified-correct and therefore double as the validator's own regression
# suite: --known-good must report zero findings there.
PRS_LANES: list[tuple[str, str]] = [
    ("realizations/prs", "realization"),
    ("overlays/en-prs", "overlay_en_prs"),
    ("overlays/prs-en", "overlay_prs_en"),
    ("practice/en-prs", "practice"),
    ("practice/prs-en", "practice"),
]
FA_OVERLAY = "overlays/fa-en"


def _cross_prs_lanes() -> list[tuple[str, str]]:
    """Cross pairs with Dari as the LEARNER language (prs-es, prs-de ...): their overlays and packs must be Dari too."""
    out: list[tuple[str, str]] = []
    for kind, label in (("overlays", "overlay_prs_cross"), ("practice", "practice")):
        base = CONTENT / kind
        if base.is_dir():
            out += [(f"{kind}/{d.name}", label) for d in sorted(base.glob("prs-*"))
                    if d.is_dir() and d.name != "prs-en"]
    return out


PRS_LANES += _cross_prs_lanes()

PERSO_ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
LATIN = re.compile(r"[A-Za-z]")
TOKEN = re.compile(r"[ء-يٰ-ۓ‌پچژکگی]+")

META_TOP_LEVEL = {"review", "generation_provenance"}
META_LEAVES = {"notes", "register_policy", "source_material", "introduced_tokens"}

CONTRAST_CUES = (
    "not the Iranian",
    "not Iranian",
    "Iranian Farsi",
    "Iranian-colloquial",
    "Iranian colloquial",
    "distinct from",
    "rather than",
    "as opposed to",
    "unlike Iranian",
    "Iranian Persian",
    "in Iran",
)

# --------------------------------------------------------------------------
# Tier 1 -- hard dialect markers. Iranian form -> Dari form used in this corpus.
# Every key below occurs ZERO times in the known-good Dari corpus
# (realizations/prs + overlays/en-prs + both practice packs + prs-en A1 u30-68),
# outside metadata and contrast notes.
# --------------------------------------------------------------------------
DIALECT_MARKERS: dict[str, tuple[str, str]] = {
    # -- copula: Iranian هست- paradigm vs Dari است- paradigm (class 1.28 core)
    "هستی": ("استی", "copula"),
    "هستید": ("استین", "copula"),
    "هستین": ("استین", "copula"),
    "هستیم": ("استیم", "copula"),
    "هستند": ("استند", "copula"),
    "نیستی": ("نیستین/نی", "copula"),
    "نیستید": ("نیستین", "copula"),
    "نیستیم": ("نیستیم", "copula"),
    # -- 2pl verb ending: Iranian -ید vs Afghan -ین (the original class 1.28)
    "بکنید": ("بکنین", "2pl_ending"),
    "نکنید": ("نکنین", "2pl_ending"),
    "بنویسید": ("بنویسین", "2pl_ending"),
    "بگویید": ("بگویین", "2pl_ending"),
    "بگیرید": ("بگیرین", "2pl_ending"),
    "بدهید": ("بتین", "2pl_ending"),
    "دهید": ("بتین", "2pl_ending"),
    "ندارید": ("ندارین", "2pl_ending"),
    "ببخشید": ("معذرت می‌خواهم", "2pl_ending"),
    "بیایید": ("بیایین", "2pl_ending"),
    "باشید": ("باشین", "2pl_ending"),
    "نباشید": ("نباشین", "2pl_ending"),
    "شوید": ("شوین", "2pl_ending"),
    "بخوانید": ("بخوانین", "2pl_ending"),
    "بپرسید": ("بپرسین", "2pl_ending"),
    "بگذارید": ("بگذارین", "2pl_ending"),
    "بدانید": ("بدانین", "2pl_ending"),
    "ببینید": ("ببینین", "2pl_ending"),
    "بشنوید": ("بشنوین", "2pl_ending"),
    "بخرید": ("بخرین", "2pl_ending"),
    "می‌کنید": ("می‌کنین", "2pl_ending"),
    "می‌روید": ("می‌رین", "2pl_ending"),
    "می‌گیرید": ("می‌گیرین", "2pl_ending"),
    "می‌دانید": ("می‌دانین", "2pl_ending"),
    "می‌توانید": ("می‌توانین", "2pl_ending"),
    "می‌خواهید": ("می‌خواهین", "2pl_ending"),
    "می‌دهید": ("می‌تین", "2pl_ending"),
    "می‌بینید": ("می‌بینین", "2pl_ending"),
    # -- Tehrani contractions with no Dari counterpart
    "یه": ("یک", "tehrani"),
    "اون": ("او/آن", "tehrani"),
    "اونا": ("آن‌ها", "tehrani"),
    "اونها": ("آن‌ها", "tehrani"),
    "اونجا": ("همانجه/آنجا", "tehrani"),
    "اینا": ("این‌ها", "tehrani"),
    "کدوم": ("کدام", "tehrani"),
    "همون": ("همو/همان", "tehrani"),
    "خونه": ("خانه", "tehrani"),
    "کتابخونه": ("کتابخانه", "tehrani"),
    "نشون": ("نشان", "tehrani"),
    "تموم": ("تمام", "tehrani"),
    "می‌تونم": ("می‌توانم", "tehrani"),
    "می‌تونی": ("می‌توانی", "tehrani"),
    "می‌تونه": ("می‌تواند", "tehrani"),
    "می‌تونیم": ("می‌توانیم", "tehrani"),
    "می‌تونید": ("می‌توانین", "tehrani"),
    "می‌تونین": ("می‌توانین", "tehrani"),
    "نمی‌تونم": ("نمی‌توانم", "tehrani"),
    "می‌خوام": ("می‌خواهم", "tehrani"),
    "می‌خوای": ("می‌خواهی", "tehrani"),
    "می‌خوایم": ("می‌خواهیم", "tehrani"),
    "می‌دونم": ("می‌دانم", "tehrani"),
    "می‌دونی": ("می‌دانی", "tehrani"),
    "می‌دونه": ("می‌دانه", "tehrani"),
    "نمی‌دونم": ("نمی‌دانم", "tehrani"),
    "میاد": ("می‌آیه", "tehrani"),
    "چیه": ("چیست/چی اس", "tehrani"),
    "کیه": ("کی اس", "tehrani"),
    "بهت": ("برایت", "tehrani"),
    "بهم": ("برایم", "tehrani"),
    "ازش": ("از او/از آن", "tehrani"),
    "توش": ("در آن", "tehrani"),
    "باهاش": ("با او", "tehrani"),
    "آره": ("بلی", "tehrani"),
    "بهتره": ("بهتر اس/بهتر استه", "tehrani"),
    "بله": ("بلی", "tehrani"),
    "مرسی": ("تشکر", "tehrani"),
    # -- Iranian lexemes with an established, in-corpus Dari counterpart
    "دانش‌آموز": ("شاگرد/محصل", "lexeme"),
    "آموزگار": ("معلم", "lexeme"),
    "خیابان": ("سرک", "lexeme"),
    "اتوبوس": ("بس", "lexeme"),
    "دلار": ("دالر", "lexeme"),
    "ریال": ("افغانی", "lexeme"),
    "تومن": ("افغانی", "lexeme"),
    "تومان": ("افغانی", "lexeme"),
    "خشکشویی": ("رخت‌شویی", "lexeme"),
    "فروشگاه": ("دوکان", "lexeme"),
    "فیلم": ("فلم", "lexeme"),
    "مسواک": ("برس دندان", "lexeme"),
}

# --------------------------------------------------------------------------
# Tier 1b -- AUDIT markers: same class-1.28 shape, but each has a handful of
# occurrences inside `realizations/prs/` that a human must adjudicate rather
# than a validator auto-fail (unit36 deliberately *teaches* هستم as a
# vocabulary item, for instance). Reported only under --audit, never counted
# toward the exit code or the --known-good gate, following the "REVIEW, not
# auto-flagged" convention of scripts/_fill_in_blank_ambiguity_check.py.
# A noisy hard error trains everyone to ignore the validator; these belong in
# a human queue instead.
# --------------------------------------------------------------------------
AUDIT_MARKERS: dict[str, tuple[str, str]] = {
    "هستم": ("استم", "copula"),
    "کنید": ("کنین", "2pl_ending"),
    "دارید": ("دارین", "2pl_ending"),
    "بفرمایید": ("بفرمایین", "2pl_ending"),
    "بروید": ("برین", "2pl_ending"),
}

# --------------------------------------------------------------------------
# Tier 2 -- prs-en overlay register (correct elsewhere, wrong in THIS lane)
# --------------------------------------------------------------------------
IRANIAN_COPULA = {"است", "هست"}
DARI_COPULA = {"استه", "استم", "استین", "استیم", "استند"}

# Formal written 3sg `-د`. Correct in realizations/prs (formal register),
# wrong in the colloquial-Dari prs-en overlay lane. می‌خواهد / می‌تواند are
# deliberately absent: the uncontracted forms are the Dari norm.
FORMAL_3SG: dict[str, str] = {
    "می‌کند": "می‌کنه",
    "می‌شود": "می‌شه",
    "می‌گوید": "می‌گه",
    "می‌پرسد": "می‌پرسه",
    "می‌دهد": "می‌ده",
    "می‌رود": "می‌ره",
    "می‌آید": "می‌آیه",
    "می‌گیرد": "می‌گیره",
    "می‌بیند": "می‌بینه",
    "می‌داند": "می‌دانه",
    "می‌نویسد": "می‌نویسه",
}
COLLOQUIAL_3SG = set(FORMAL_3SG.values()) | {"می‌ته", "می‌خوره"}

# Iranian instructional metalanguage. The prs-en lane's own norm (A1 u30-68)
# is جواب / سوال / کلمه; the fa-en lane's is پاسخ / پرسش / واژه.
METALANGUAGE: dict[str, str] = {
    "پاسخ": "جواب",
    "پرسش": "سوال",
    "واژه‌ها": "کلمه‌ها",
    "مخاطب": "طرف مقابل",
}

# Thresholds calibrated against the known-good band (prs-en A1 units 30-68),
# whose observed maxima are: iranian copula 6 (never exceeding Dari copula in
# the same file), formal 3sg 3, metalanguage 0, fa transplants 1.
COPULA_MIN = 5
FORMAL_3SG_MIN = 4
METALANGUAGE_MIN = 3
TRANSPLANT_MIN_WORDS = 5
TRANSPLANT_MIN_COUNT = 2


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def _walk(node: Any, path: list[str], out: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _walk(value, path + [str(key)], out)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk(value, path + [f"[{index}]"], out)
    elif isinstance(node, str) and PERSO_ARABIC.search(node):
        out.append((".".join(path), node))


def is_learner_facing(path: str) -> bool:
    parts = [p for p in path.split(".") if not p.startswith("[")]
    if not parts:
        return False
    if parts[0] in META_TOP_LEVEL:
        return False
    return parts[-1] not in META_LEAVES


def load_lane(rel: str) -> dict[Path, list[tuple[str, str]]]:
    directory = CONTENT / rel
    result: dict[Path, list[tuple[str, str]]] = {}
    if not directory.is_dir():
        return result
    for path in sorted(directory.glob("*.yaml")):
        with path.open(encoding="utf-8") as handle:
            document = yaml.safe_load(handle)
        strings: list[tuple[str, str]] = []
        _walk(document, [], strings)
        result[path] = [(p, s) for p, s in strings if is_learner_facing(p)]
    return result


def is_suppressed(text: str) -> bool:
    """A string that explicitly contrasts against the Iranian form, or is
    English explanatory prose, may legitimately contain Iranian words."""
    if any(cue in text for cue in CONTRAST_CUES):
        return True
    latin = len(LATIN.findall(text))
    perso = len(PERSO_ARABIC.findall(text))
    return latin > perso


# --------------------------------------------------------------------------
# Bands
# --------------------------------------------------------------------------
def unit_number(name: str) -> int:
    match = re.search(r"unit(\d+)", name)
    return int(match.group(1)) if match else -1


def prs_en_band(name: str) -> str:
    number = unit_number(name)
    if name.startswith("a1_unit"):
        return "a1_u01-24" if number <= 24 else "a1_u30-68"
    return name.split("_")[0]


def is_known_good(rel: str, filename: str) -> bool:
    """The bands independently verified as authentic Dari (2026-07-22 audit).
    --known-good asserts the validator reports nothing here."""
    if rel == "overlays/prs-en":
        return prs_en_band(filename) == "a1_u30-68"
    return rel in {"realizations/prs", "overlays/en-prs", "practice/en-prs", "practice/prs-en"}


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
class Finding:
    __slots__ = ("path", "check", "message", "detail")

    def __init__(self, path: Path, check: str, message: str, detail: list[str] | None = None):
        self.path = path
        self.check = check
        self.message = message
        self.detail = detail or []


def check_dialect_markers(
    path: Path,
    strings: list[tuple[str, str]],
    markers: dict[str, tuple[str, str]] = DIALECT_MARKERS,
    check: str = "dialect_marker",
) -> list[Finding]:
    hits: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for field, text in strings:
        if is_suppressed(text):
            continue
        for token in TOKEN.findall(text):
            if token in markers:
                hits[token].append((field, text))
    findings = []
    for token, occurrences in sorted(hits.items(), key=lambda kv: -len(kv[1])):
        dari, kind = markers[token]
        findings.append(
            Finding(
                path,
                check,
                f"[{kind}] Iranian '{token}' x{len(occurrences)} -- Dari: '{dari}'",
                [f"{field}: {text}" for field, text in occurrences[:6]],
            )
        )
    return findings


def check_overlay_register(path: Path, strings: list[tuple[str, str]]) -> list[Finding]:
    counts: Counter[str] = Counter()
    where: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for field, text in strings:
        if is_suppressed(text):
            continue
        for token in TOKEN.findall(text):
            counts[token] += 1
            where[token].append((field, text))

    findings: list[Finding] = []

    iranian = sum(counts[t] for t in IRANIAN_COPULA)
    dari = sum(counts[t] for t in DARI_COPULA)
    if iranian >= COPULA_MIN and iranian > dari:
        sample = [f"{f}: {t}" for token in IRANIAN_COPULA for f, t in where[token][:3]]
        findings.append(
            Finding(
                path,
                "overlay_register",
                f"[copula] formal/Iranian است|هست x{iranian} vs Dari استه|استم|استین x{dari} "
                f"-- this lane's register pin is colloquial Dari (استه style)",
                sample[:6],
            )
        )

    formal = sum(counts[t] for t in FORMAL_3SG)
    colloquial = sum(counts[t] for t in COLLOQUIAL_3SG)
    if formal >= FORMAL_3SG_MIN:
        breakdown = ", ".join(
            f"{t}x{counts[t]}->{FORMAL_3SG[t]}" for t in FORMAL_3SG if counts[t]
        )
        sample = [f"{f}: {t}" for token in FORMAL_3SG if counts[token] for f, t in where[token][:2]]
        findings.append(
            Finding(
                path,
                "overlay_register",
                f"[formal_3sg] formal written -د x{formal} vs colloquial -ه x{colloquial} ({breakdown})",
                sample[:6],
            )
        )

    meta = sum(counts[t] for t in METALANGUAGE)
    if meta >= METALANGUAGE_MIN:
        breakdown = ", ".join(f"{t}x{counts[t]}->{METALANGUAGE[t]}" for t in METALANGUAGE if counts[t])
        sample = [f"{f}: {t}" for token in METALANGUAGE if counts[token] for f, t in where[token][:2]]
        findings.append(
            Finding(
                path,
                "overlay_register",
                f"[metalanguage] Iranian instructional metalanguage x{meta} ({breakdown})",
                sample[:6],
            )
        )
    return findings


def check_fa_transplant(
    path: Path, strings: list[tuple[str, str]], fa_strings: set[str]
) -> list[Finding]:
    transplants: list[tuple[str, str]] = []
    for field, text in strings:
        if text not in fa_strings or len(text.split()) < TRANSPLANT_MIN_WORDS:
            continue
        tokens = set(TOKEN.findall(text))
        if tokens & (IRANIAN_COPULA | set(FORMAL_3SG) | set(METALANGUAGE) | set(DIALECT_MARKERS)):
            transplants.append((field, text))
    if len(transplants) < TRANSPLANT_MIN_COUNT:
        return []
    return [
        Finding(
            path,
            "fa_transplant",
            f"{len(transplants)} prose strings (>={TRANSPLANT_MIN_WORDS} words) are byte-identical "
            f"to overlays/fa-en AND carry Iranian register",
            [f"{field}: {text}" for field, text in transplants[:8]],
        )
    ]


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--known-good",
        action="store_true",
        help="scan ONLY the verified-authentic Dari bands; this is the "
        "validator's own zero-false-positive regression suite",
    )
    parser.add_argument("--details", action="store_true", help="print offending strings")
    parser.add_argument(
        "--audit",
        action="store_true",
        help="additionally report AUDIT_MARKERS as 'dialect_review' findings "
        "(human call required; never affects the exit code)",
    )
    args = parser.parse_args()

    fa_strings = {text for strings in load_lane(FA_OVERLAY).values() for _, text in strings}

    findings: list[Finding] = []
    review: list[Finding] = []
    scanned = 0
    for rel, _kind in PRS_LANES:
        for path, strings in load_lane(rel).items():
            good = is_known_good(rel, path.name)
            if args.known_good and not good:
                continue
            scanned += 1
            findings.extend(check_dialect_markers(path, strings))
            if args.audit:
                review.extend(
                    check_dialect_markers(path, strings, AUDIT_MARKERS, "dialect_review")
                )
            if rel == "overlays/prs-en":
                findings.extend(check_overlay_register(path, strings))
                findings.extend(check_fa_transplant(path, strings, fa_strings))

    by_file: dict[Path, list[Finding]] = defaultdict(list)
    for finding in findings + review:
        by_file[finding.path].append(finding)

    for path in sorted(by_file):
        print(f"{path.relative_to(REPO_ROOT)}")
        for finding in by_file[path]:
            print(f"  {finding.check:18s} {finding.message}")
            if args.details:
                for line in finding.detail:
                    print(f"      | {line}")

    by_check = Counter(f.check for f in findings + review)
    print()
    print(f"scanned {scanned} files"
          f"{' (known-good bands only)' if args.known_good else ''}"
          f"; {len(by_file)} with findings")
    for check, count in sorted(by_check.items()):
        print(f"  {check}: {count}")
    print(f"TOTAL FINDINGS: {len(findings)}"
          + (f"  (+{len(review)} dialect_review, human call, not gated)" if args.audit else ""))
    if args.known_good:
        print(
            "ACCEPTANCE: --known-good must report 0 gated findings."
            f" -> {'PASS' if not findings else 'FAIL'}"
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
