#!/usr/bin/env python3
"""Unit-scope satisfiability check for practice packs.

WHY THIS EXISTS
---------------
`scripts/_practice_slot_check.py` verifies each template's slots against the
*whole direction's* lexeme pool. But `generate_checkpoint()` only loads the
lexemes belonging to the pack's OWN unit (its lesson_ids). So a template whose
slot reuses a semantic tag introduced by an *earlier* unit passes the
whole-direction check yet has ZERO candidates at checkpoint time -- it silently
never generates. This is recipe DO-NOT #2 / SS1.1, and a 2026-07-23 pack review
found it is systemic across every pre-recipe (pre-2026-07-22) a1_unit01-24 pack.

This script is the missing check: it scopes each pack's candidate pool to that
pack's own unit (matching generate_checkpoint) and flags:
  - DEAD: a slot with 0 unit-scoped candidates -> template can never generate.
  - MC/listen_select below the >=3 distinct-answer floor.
  - matching_pairs whose distinct unit-scoped token pool < the number of
    `distinct`-related slots it declares (can't fill) or < the recipe's 6-pair
    floor (SS16 / DO-NOT #5).

lexeme_matches() is a byte-for-byte port of app/practice/service.py's, kept in
sync with _practice_slot_check.py (copied deliberately, not imported).

Usage: .content-venv/bin/python3 scripts/_practice_unit_scope_check.py
Exit 1 if any DEAD template exists (informational floors do not fail the run).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

MIN_MULTI_OPTION_CANDIDATES = 3      # build_prompt() rejects < 3 options
MATCHING_PAIRS_FLOOR = 6             # AUTHORING_GUIDE SS16 / recipe DO-NOT #5

_UNIT_RE = re.compile(r"(a1|a2|b1|b2)_unit(\d+)")


def _as_values(value: Any) -> set[Any]:
    return set(value) if isinstance(value, list) else {value}


def _requested_matches(requested: Any, actual: Any) -> bool:
    return bool(_as_values(requested) & _as_values(actual))


def lexeme_matches(lexeme: dict, constraints: dict) -> bool:
    """Byte-for-byte port of app/practice/service.py's lexeme_matches()."""
    if lexeme["language_code"] != constraints.get("language_code"):
        return False
    if not _requested_matches(constraints.get("part_of_speech"), lexeme["part_of_speech"]):
        return False
    actual_tags = lexeme.get("agreement_tags") or {}
    return all(
        tag in actual_tags and _requested_matches(requested, actual_tags[tag])
        for tag, requested in constraints.get("agreement_tags", {}).items()
    )


def _unit_key_from_path(pack_path: Path) -> str | None:
    """`.../a1_unit05.yaml` -> the substring `.a1.unit05.` that a lesson_content_key
    for that unit must contain (matches generate_checkpoint's unit scoping)."""
    m = _UNIT_RE.search(pack_path.stem)
    if not m:
        return None
    return f".{m.group(1)}.unit{m.group(2)}."


def _distinct_slot_count(template: dict) -> int:
    """Number of slots a matching_pairs template needs distinct fills for."""
    relations = template.get("slot_relations") or []
    counts = [len(r.get("slots", [])) for r in relations if r.get("kind") == "distinct"]
    if counts:
        return max(counts)
    return len(template.get("slots", {}))


def check_pack(pack_path: Path, all_specs: list[dict]) -> list[tuple[str, str]]:
    """Return [(severity, message)]; severity in {'DEAD','FLOOR'}."""
    unit_key = _unit_key_from_path(pack_path)
    if unit_key is None:
        return []
    unit_lexemes = [s for s in all_specs if unit_key in s["lesson_content_key"]]
    problems: list[tuple[str, str]] = []
    try:
        pack = yaml.safe_load(pack_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        # A pack being mid-written by a concurrent editor can parse-fail
        # transiently; skip it rather than crash the whole run.
        return [("SKIP", f"{pack_path.name}: could not parse ({exc.__class__.__name__}) -- skipped")]
    if not isinstance(pack, dict):
        return [("SKIP", f"{pack_path.name}: not a mapping -- skipped")]
    for template in pack.get("templates", []):
        key = template.get("content_key", "<no content_key>")
        ttype = template.get("type")
        slots = template.get("slots", {})
        dead = False
        for slot_name, constraints in slots.items():
            candidates = [lx for lx in unit_lexemes if lexeme_matches(lx, constraints)]
            if not candidates:
                problems.append(("DEAD", f"{key}: slot {slot_name!r} has 0 unit-scoped candidates -> template never generates at checkpoint"))
                dead = True
        if dead:
            continue  # already can't generate; floor checks are moot
        # floor checks (template can generate at least one item)
        if ttype in {"multiple_choice", "listen_select"}:
            deriv = template.get("answer_derivation", {})
            if deriv.get("kind") in {"slot_gloss", "slot_text"}:
                slot_name = deriv.get("slot")
                constraints = slots.get(slot_name, {})
                cands = [lx for lx in unit_lexemes if lexeme_matches(lx, constraints)]
                field = "english_gloss" if deriv["kind"] == "slot_gloss" else "token"
                distinct = len({lx[field] for lx in cands})
                if distinct < MIN_MULTI_OPTION_CANDIDATES:
                    problems.append(("FLOOR", f"{key}: {ttype} has only {distinct} distinct unit-scoped answer value(s) (<{MIN_MULTI_OPTION_CANDIDATES})"))
        if ttype == "matching_pairs":
            need = _distinct_slot_count(template)
            # tokens across all matching slots (all share the same pool here)
            first_slot = next(iter(slots.values()), {})
            cands = [lx for lx in unit_lexemes if lexeme_matches(lx, first_slot)]
            distinct_tokens = len({lx["token"] for lx in cands})
            if distinct_tokens < need:
                problems.append(("DEAD", f"{key}: matching_pairs needs {need} distinct fills but unit-scoped pool has {distinct_tokens} -> never generates"))
            elif need < MATCHING_PAIRS_FLOOR:
                problems.append(("FLOOR", f"{key}: matching_pairs declares only {need} slots (<{MATCHING_PAIRS_FLOOR}-pair floor)"))
    return problems


DIRECTIONS: list[tuple[str, str, str]] = [
    # (label, practice subdir, backfill module)
    ("en-fa", "en-fa", "backfill_lexemes"),
    ("fa-en", "fa-en", "backfill_lexemes_fa_en"),
    ("en-prs", "en-prs", "backfill_lexemes_en_prs"),
    ("prs-en", "prs-en", "backfill_lexemes_prs_en"),
    ("en-nl", "en-nl", "backfill_lexemes_en_nl"),
    ("nl-en", "nl-en", "backfill_lexemes_nl_en"),
]


def main() -> int:
    import importlib
    total_dead = 0
    total_floor = 0
    dead_packs: dict[str, int] = {}
    for label, subdir, module_name in DIRECTIONS:
        try:
            mod = importlib.import_module(module_name)
            specs = list(mod.iter_specs())
        except Exception as exc:  # a broken direction shouldn't hide the rest
            print(f"=== {label}: SPEC LOADING FAILED: {exc!r} ===")
            continue
        packs = sorted((REPO_ROOT / "docs/content/practice" / subdir).glob("*_unit*.yaml"))
        print(f"=== {label}: {len(specs)} specs, {len(packs)} packs ===")
        for pack_path in packs:
            problems = check_pack(pack_path, specs)
            dead = [m for sev, m in problems if sev == "DEAD"]
            floor = [m for sev, m in problems if sev == "FLOOR"]
            skip = [m for sev, m in problems if sev == "SKIP"]
            if dead:
                dead_packs[label] = dead_packs.get(label, 0) + 1
            total_dead += len(dead)
            total_floor += len(floor)
            if problems:
                print(f"  {pack_path.name}: {len(dead)} DEAD, {len(floor)} below-floor"
                      + (", SKIPPED" if skip else ""))
                for m in dead:
                    print(f"      DEAD  {m}")
                for m in floor:
                    print(f"      FLOOR {m}")
                for m in skip:
                    print(f"      SKIP  {m}")
    print()
    print(f"TOTAL: {total_dead} DEAD template-slots, {total_floor} below-floor "
          f"({sum(dead_packs.values())} packs with >=1 dead template: "
          f"{', '.join(f'{k}={v}' for k, v in sorted(dead_packs.items()))})")
    return 1 if total_dead else 0


if __name__ == "__main__":
    raise SystemExit(main())
