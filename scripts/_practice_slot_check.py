#!/usr/bin/env python3
"""Standalone slot-matching verification harness for Endless Practice
template packs -- no database, no backend import, just the exact same
matching semantics as backend/app/practice/service.py's lexeme_matches()
(copied deliberately, not imported, so this can run with only PyYAML
installed; the two are cross-checked against each other's source by eye
whenever this harness is touched).

Why this exists: scripts/compile_content.py practice-validate is PURELY
static YAML schema/reference checking -- it never touches the database
or any real Lexeme row, so a pack can validate 0 errors/0 warnings and
still be completely inert (or, worse, silently generate a grammatically
wrong sentence) at runtime if the real backfilled Lexeme data doesn't
actually satisfy what a template's slots ask for. This was the load-
bearing discovery the nl-en practice-pool-sync work made first; this
script is the general-purpose version of the one-off check that lane
wrote, reused here for the fa/prs bundle (en-fa, fa-en, en-prs) so the
same class of bug (too few candidates for multiple_choice/matching_pairs,
or a slot whose real candidate pool can render a grammatically wrong
sentence) gets caught before shipping, not after.

Usage:
    .content-venv/bin/python3 scripts/_practice_slot_check.py

Add new (pack_path, spec_source) pairs to PACKS below whenever a new
practice pack + backfill script pair is authored.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

MIN_MULTI_OPTION_CANDIDATES = 3  # mirrors build_prompt()'s `len(options) < 3` reject


def _as_values(value: Any) -> set[Any]:
    if isinstance(value, list):
        return set(value)
    return {value}


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


def check_pack(pack_path: Path, lexemes: list[dict]) -> list[str]:
    """Returns a list of human-readable problems found (empty = clean)."""
    problems: list[str] = []
    pack = yaml.safe_load(pack_path.read_text(encoding="utf-8"))
    for template in pack.get("templates", []):
        key = template.get("content_key", "<no content_key>")
        ttype = template.get("type")
        slots = template.get("slots", {})
        for slot_name, constraints in slots.items():
            candidates = [lx for lx in lexemes if lexeme_matches(lx, constraints)]
            if not candidates:
                problems.append(f"{key}: slot {slot_name!r} has ZERO candidate lexemes -- template can never generate")
                continue
            if ttype in {"multiple_choice", "listen_select"}:
                derivation = template.get("answer_derivation", {})
                if derivation.get("kind") in {"slot_gloss", "slot_text"} and derivation.get("slot") == slot_name:
                    distinct = len({
                        (lx["english_gloss"] if derivation["kind"] == "slot_gloss" else lx["token"])
                        for lx in candidates
                    })
                    if distinct < MIN_MULTI_OPTION_CANDIDATES:
                        problems.append(
                            f"{key}: slot {slot_name!r} (type={ttype}) has only {distinct} distinct "
                            f"answer-derivation value(s), need >={MIN_MULTI_OPTION_CANDIDATES} for a "
                            "well-formed multiple_choice/listen_select item"
                        )
            if ttype == "matching_pairs":
                distinct_tokens = len({lx["token"] for lx in candidates})
                if distinct_tokens < 2:
                    problems.append(
                        f"{key}: slot {slot_name!r} (type=matching_pairs) has only {distinct_tokens} "
                        "distinct token(s), need >=2 to ever satisfy a distinct slot_relation"
                    )
    return problems


def main() -> int:
    total_problems = 0

    def run(label: str, pack_paths: list[Path], specs_fn) -> None:
        nonlocal total_problems
        try:
            lexemes = [
                {
                    "language_code": s["language_code"],
                    "part_of_speech": s["part_of_speech"],
                    "token": s["token"],
                    "english_gloss": s["english_gloss"],
                    "agreement_tags": s["agreement_tags"],
                }
                for s in specs_fn()
            ]
        except Exception as exc:
            # Don't let one broken direction hide every other direction's
            # results -- found live 2026-07-06: backfill_lexemes_en_prs.py's
            # own UNIT_FILES references docs/content/realizations/prs/
            # a1_unit02_introductions.yaml, which does not exist on disk
            # (the prs realization only has units 01 and 03) -- a real,
            # pre-existing content/script mismatch unrelated to this run,
            # not something a practice-pool-sync pass can fix without prs
            # unit02 content actually being authored.
            total_problems += 1
            print(f"=== {label}: SPEC LOADING FAILED ===")
            print(f"  {exc!r}")
            return
        print(f"=== {label}: {len(lexemes)} lexemes available ===")
        for pack_path in pack_paths:
            problems = check_pack(pack_path, lexemes)
            if problems:
                total_problems += len(problems)
                print(f"  FAIL {pack_path}")
                for p in problems:
                    print(f"    - {p}")
            else:
                print(f"  OK   {pack_path}")

    from backfill_lexemes import iter_specs as en_fa_specs
    from backfill_lexemes_fa_en import iter_specs as fa_en_specs
    from backfill_lexemes_en_prs import iter_specs as en_prs_specs
    from backfill_lexemes_prs_en import iter_specs as prs_en_specs

    run(
        "en-fa (target=fa)",
        sorted((REPO_ROOT / "docs/content/practice/en-fa").glob("a*_unit*.yaml")),
        en_fa_specs,
    )
    run(
        "fa-en (target=en)",
        [
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit01.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit02.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit03.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit04.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit05.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit06.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit07.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit08.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit09.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit10.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit11.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit12.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit13.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit14.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit15.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit16.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit17.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit18.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit19.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit20.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit21.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit22.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit23.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a1_unit24.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a2_unit25.yaml",
            REPO_ROOT / "docs/content/practice/fa-en/a2_unit26.yaml",
        ],
        fa_en_specs,
    )
    run(
        "en-prs (target=prs)",
        sorted((REPO_ROOT / "docs/content/practice/en-prs").glob("a*_unit*.yaml")),
        en_prs_specs,
    )
    run(
        "prs-en (target=en)",
        sorted((REPO_ROOT / "docs/content/practice/prs-en").glob("a1_unit*.yaml")),
        prs_en_specs,
    )

    print()
    if total_problems:
        print(f"TOTAL PROBLEMS: {total_problems}")
        return 1
    print("All packs: every slot has >=1 candidate; every multiple_choice/"
          "listen_select/matching_pairs slot has enough distinct candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
