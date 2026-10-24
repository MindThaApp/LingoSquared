#!/usr/bin/env python3
"""Corpus-wide audit for 2 specific Endless Practice template bug classes,
dispatched 2026-07-07 after both surfaced by accident, independently, in
different directions' ad-hoc authoring passes the same night -- strongly
suggesting a systemic sweep would find more instances nobody happened to
notice yet. See docs/BUILD_LOG.md's "Cross-language content-integrity
sweep, 2026-07-06" entry (bug classes (2) and (5)) for the original
methodology this generalizes and formalizes into a reusable script.

BUG CLASS A -- self-reference in generative practice slots: a template's
`frame` (or its `answer_derivation.frame`, when of kind `render_frame`)
contains literal, non-placeholder text that collides with one of the SAME
placeholder slot's own real candidate values (via the exact
`lexeme_matches()`/`iter_specs()` machinery `backend/app/practice/
service.py` uses at runtime), so a generated instance can render a
nonsensical self-referencing sentence (e.g. "The hospital is next to the
hospital.") when generation happens to sample that specific candidate.
This is the same bug class as the project's known, deliberately-avoided
station/hospital and sandwich/market_quantity self-reference cases
(see AUTHORING_GUIDE.md and the practice packs' own review notes).

Checking logic mirrors REAL runtime rendering exactly (not just a naive
text scan), replicating `render_frame()`/`build_prompt()`'s field-
selection rules byte-for-byte:
  - `template.frame` renders with `default_field="token"` for every type
    EXCEPT `word_order`, which renders its (only) visible hint with
    `default_field="english_gloss"` (`build_prompt()`'s word_order
    branch) -- any `slot_rendering` override on the frame always wins
    regardless of type.
  - `answer_derivation.frame` (only present when `kind: render_frame`)
    is rendered separately, always with `default_field="token"` (no
    override kwarg at that call site), and is the literal word list
    used to build the word_order word bank / grade the answer, even
    though it's rarely displayed verbatim -- so a duplicate-token
    collision there is a real (if lower-visibility) instance of the
    same bug class, not exercise-type noise.

BUG CLASS B -- a practice template's `lesson_content_key` anchors to a
lesson that introduces ZERO new vocabulary (summed `introduced_tokens`
across every teaching card in that lesson) -- the backfill/import
pipeline requires >=1 introduced lexeme to resolve `PracticeTemplate.
lesson_id` at import time, so such a template can never actually import/
generate. `introduced_tokens` lives ONLY in `docs/content/realizations/
{en,nl,fa,prs,...}/*.yaml` teaching cards (confirmed: no overlay in this
repo ever declares a real `introduced_tokens` field -- the few grep hits
inside overlay files are prose *inside* long `notes:` strings, not actual
YAML keys) -- the lesson_content_key's own language-code prefix says
which realizations/ subdirectory to look in for every direction.

Usage:
    .content-venv/bin/python3 scripts/_practice_content_integrity_check.py
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

PRACTICE_DIRS = ["nl-en", "en-nl", "fa-en", "prs-en", "en-fa", "en-prs"]

# Matches scripts/_practice_slot_check.py's mapping of direction -> the
# backfill script whose iter_specs() produces that direction's real
# lexeme pool (en-fa/en-prs use different backfill scripts than their
# reverse direction; en-fa's is the un-suffixed base script).
DIRECTION_BACKFILL_MODULE = {
    "nl-en": "backfill_lexemes_nl_en",
    "en-nl": "backfill_lexemes_en_nl",
    "fa-en": "backfill_lexemes_fa_en",
    "prs-en": "backfill_lexemes_prs_en",
    "en-fa": "backfill_lexemes",
    "en-prs": "backfill_lexemes_en_prs",
}

# Session 10 (2026-10-24): any further practice direction whose backfill
# follows the backfill_lexemes_<src>_<tgt>.py naming convention (en-es,
# en-de, ...) is discovered automatically, so a new direction never needs
# a hand edit here.
for _dir in sorted(p.name for p in (Path(__file__).resolve().parent.parent / "docs/content/practice").iterdir() if p.is_dir()):
    _mod = "backfill_lexemes_" + _dir.replace("-", "_")
    if (Path(__file__).resolve().parent / (_mod + ".py")).exists() and _dir not in DIRECTION_BACKFILL_MODULE:
        DIRECTION_BACKFILL_MODULE[_dir] = _mod
        PRACTICE_DIRS.append(_dir)

SLOT_RE = re.compile(r"\{(\w+)\}")


# --------------------------------------------------------------------------
# Shared: byte-for-byte port of app/practice/service.py's lexeme_matches()
# (same port already used/verified by scripts/_practice_slot_check.py).
# --------------------------------------------------------------------------
def _as_values(value: Any) -> set:
    if isinstance(value, list):
        return set(value)
    return {value}


def _requested_matches(requested: Any, actual: Any) -> bool:
    return bool(_as_values(requested) & _as_values(actual))


def lexeme_matches(lexeme: dict, constraints: dict) -> bool:
    if lexeme["language_code"] != constraints.get("language_code"):
        return False
    if not _requested_matches(constraints.get("part_of_speech"), lexeme["part_of_speech"]):
        return False
    actual_tags = lexeme.get("agreement_tags") or {}
    return all(
        tag in actual_tags and _requested_matches(requested, actual_tags[tag])
        for tag, requested in constraints.get("agreement_tags", {}).items()
    )


def load_all_specs() -> dict[str, list[dict]]:
    """direction -> list of real lexeme spec dicts from that direction's
    own backfill script, exactly like _practice_slot_check.py loads them."""
    import importlib

    pools: dict[str, list[dict]] = {}
    for direction, module_name in DIRECTION_BACKFILL_MODULE.items():
        mod = importlib.import_module(module_name)
        pools[direction] = list(mod.iter_specs())
    return pools


# --------------------------------------------------------------------------
# BUG CLASS B: lesson_content_key anchored to a zero-vocabulary lesson
# --------------------------------------------------------------------------
def build_lesson_token_counts() -> dict[str, int]:
    """lesson_content_key -> total introduced_tokens count, summed across
    every teaching card in that lesson, scanning EVERY realization file
    under docs/content/realizations/*/*.yaml (all languages present)."""
    counts: dict[str, int] = {}
    realization_files = sorted(glob.glob(str(REPO_ROOT / "docs/content/realizations/*/*.yaml")))
    for path in realization_files:
        doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not doc:
            continue
        for unit in doc.get("units", []) or []:
            for lesson in unit.get("lessons", []) or []:
                key = lesson.get("content_key")
                if not key:
                    continue
                total = 0
                for card in lesson.get("teaching", []) or []:
                    tokens = card.get("introduced_tokens")
                    if isinstance(tokens, list):
                        total += len(tokens)
                # A lesson_content_key should be unique across the whole
                # corpus (it's the real DB anchor) -- if it recurs, keep
                # the max just in case of any legitimate duplication, but
                # this would itself be worth a second look.
                if key in counts and counts[key] != total:
                    print(f"  ! NOTE: lesson_content_key {key!r} declared with DIFFERING "
                          f"introduced_tokens totals across files ({counts[key]} vs {total}) "
                          f"-- keeping the max", file=sys.stderr)
                    counts[key] = max(counts[key], total)
                else:
                    counts[key] = total
    return counts


def check_bug_class_b(lesson_token_counts: dict[str, int]) -> list[dict]:
    violations = []
    for direction in PRACTICE_DIRS:
        pack_dir = REPO_ROOT / "docs/content/practice" / direction
        for pack_path in sorted(pack_dir.glob("*_unit*.yaml")):
            doc = yaml.safe_load(pack_path.read_text(encoding="utf-8"))
            if not doc:
                continue
            for template in doc.get("templates", []) or []:
                key = template.get("content_key", "<no content_key>")
                lck = template.get("lesson_content_key")
                if not lck:
                    violations.append({
                        "direction": direction, "file": str(pack_path),
                        "content_key": key, "lesson_content_key": None,
                        "issue": "MISSING lesson_content_key entirely",
                    })
                    continue
                if lck not in lesson_token_counts:
                    violations.append({
                        "direction": direction, "file": str(pack_path),
                        "content_key": key, "lesson_content_key": lck,
                        "issue": "UNRESOLVED -- no lesson in any realization file has this content_key",
                    })
                elif lesson_token_counts[lck] == 0:
                    violations.append({
                        "direction": direction, "file": str(pack_path),
                        "content_key": key, "lesson_content_key": lck,
                        "issue": "ZERO introduced_tokens -- lesson can never anchor a real lexeme",
                    })
    return violations


# --------------------------------------------------------------------------
# BUG CLASS A: self-reference in generative practice slots
# --------------------------------------------------------------------------
def _boundary_pattern(value: str) -> "re.Pattern":
    escaped = re.escape(value.strip())
    escaped = escaped.replace(r"\ ", r"\s+")
    # U+200C (ZWNJ) joins Persian/Dari verb prefixes (می‌/نمی‌) to their stem;
    # \w does not include it, so a bare (?<!\w) boundary would wrongly match a
    # stem (e.g. رفتم) inside a ZWNJ-joined form (می‌رفتم). Treat ZWNJ as a
    # word-joiner so those are not flagged as self-reference collisions.
    return re.compile(r"(?<![\w‌])" + escaped + r"(?![\w‌])", re.UNICODE | re.IGNORECASE)


def _collides(value: str, literal_text: str) -> bool:
    if not value or not value.strip():
        return False
    return bool(_boundary_pattern(value).search(literal_text))


def _check_one_frame(
    template: dict,
    frame_field_label: str,
    frame_dict: dict,
    slots_defs: dict,
    spec_pool: list[dict],
    default_field: str,
) -> list[dict]:
    text = (frame_dict or {}).get("text") or ""
    placeholders = SLOT_RE.findall(text)
    if not placeholders:
        return []
    literal_residual = SLOT_RE.sub(" ", text)
    if not literal_residual.strip():
        return []  # bare-word recognition frame, e.g. "{item}" alone -- no literal text to collide with
    slot_rendering = (frame_dict or {}).get("slot_rendering") or {}
    findings = []
    for slot_name in dict.fromkeys(placeholders):  # de-dup, preserve order
        constraints = slots_defs.get(slot_name)
        if not constraints:
            continue
        field = slot_rendering.get(slot_name, default_field)
        candidates = [s for s in spec_pool if lexeme_matches(s, constraints)]
        matched_values = sorted({
            cand[field] for cand in candidates
            if cand.get(field) and _collides(cand[field], literal_residual)
        })
        if matched_values:
            findings.append({
                "frame_field": frame_field_label,
                "slot": slot_name,
                "rendered_field": field,
                "frame_text": text,
                "literal_residual": literal_residual.strip(),
                "matched_candidate_values": matched_values,
                "num_real_candidates": len(candidates),
            })
    return findings


def check_bug_class_a(spec_pools: dict[str, list[dict]]) -> list[dict]:
    violations = []
    for direction in PRACTICE_DIRS:
        spec_pool = spec_pools[direction]
        pack_dir = REPO_ROOT / "docs/content/practice" / direction
        for pack_path in sorted(pack_dir.glob("*_unit*.yaml")):
            doc = yaml.safe_load(pack_path.read_text(encoding="utf-8"))
            if not doc:
                continue
            for template in doc.get("templates", []) or []:
                key = template.get("content_key", "<no content_key>")
                ttype = template.get("type")
                slots_defs = template.get("slots", {}) or {}

                default_field = "english_gloss" if ttype == "word_order" else "token"
                findings = _check_one_frame(
                    template, "frame", template.get("frame"), slots_defs, spec_pool, default_field
                )

                ad = template.get("answer_derivation") or {}
                if ad.get("kind") == "render_frame":
                    findings += _check_one_frame(
                        template, "answer_derivation.frame", ad.get("frame"),
                        slots_defs, spec_pool, "token",
                    )

                for f in findings:
                    violations.append({
                        "direction": direction, "file": str(pack_path),
                        "content_key": key, "type": ttype, **f,
                    })
    return violations


def main() -> int:
    print("Loading real lexeme pools for all 6 directions (iter_specs())...")
    spec_pools = load_all_specs()
    for d, pool in spec_pools.items():
        print(f"  {d}: {len(pool)} lexeme specs")

    print("\nBuilding lesson_content_key -> introduced_tokens totals from every "
          "realization file...")
    lesson_token_counts = build_lesson_token_counts()
    print(f"  {len(lesson_token_counts)} distinct lesson_content_keys found")

    print("\n=== BUG CLASS B: zero-vocabulary lesson_content_key anchors ===")
    b_violations = check_bug_class_b(lesson_token_counts)
    if b_violations:
        for v in b_violations:
            print(f"  FLAG [{v['direction']}] {v['file']}")
            print(f"       content_key={v['content_key']}")
            print(f"       lesson_content_key={v['lesson_content_key']!r}: {v['issue']}")
    else:
        print("  none found")

    print("\n=== BUG CLASS A: self-reference in generative practice slots ===")
    a_violations = check_bug_class_a(spec_pools)
    if a_violations:
        for v in a_violations:
            print(f"  FLAG [{v['direction']}] {v['file']}")
            print(f"       content_key={v['content_key']} type={v['type']} "
                  f"frame_field={v['frame_field']} slot={v['slot']} rendered_field={v['rendered_field']}")
            print(f"       frame_text={v['frame_text']!r}")
            print(f"       matched_candidate_values={v['matched_candidate_values']} "
                  f"(of {v['num_real_candidates']} real candidates)")
    else:
        print("  none found")

    print(f"\nTOTAL: {len(b_violations)} class-B candidate(s), {len(a_violations)} class-A candidate(s)")
    print("(class-A list is a raw mechanical scan -- still needs human triage for "
          "genuine self-reference vs. incidental common-word overlap, same as this "
          "project's earlier passes.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
