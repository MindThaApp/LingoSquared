#!/usr/bin/env python3
"""Ambiguity check for `fill_in_blank` Endless Practice templates.

Companion to scripts/_practice_slot_check.py, which only verifies that a
slot has ENOUGH candidate lexemes (>=1, or >=3 for multiple_choice option
variety). It does NOT check whether a fill_in_blank slot's candidates are
actually DISTINGUISHABLE by the frame's remaining (non-blanked) text --
that's this script's job.

Why this matters: `_material()` in backend/app/practice/service.py scopes
a course's candidate lexeme pool to ALL lexemes from ALL of the user's
COMPLETED lessons so far (not just the one lesson a template is anchored
to). For a single-slot fill_in_blank template like

    frame: {text: "Ik heet {item}."}
    slots: {item: *person_name}
    answer_derivation: {kind: slot_text, slot: item}

the blanked prompt is just "Ik heet ___." with no other anchor. Early in
a course, when only 1-2 lexemes exist for `person_name`, this happens to
be answerable (there's only one name the learner could know). But as the
course grows and more lessons introduce more names, the *same* template
becomes genuinely ambiguous -- any taught name fits grammatically, and
the grader only accepts the one specific token that generation picked
for that instance. This is the subtler variant of AUTHORING_GUIDE.md#13's
bare-slot bug: not zero context, but insufficient (non-disambiguating)
context.

Method: for every single-slot fill_in_blank template, compute the real
distinct-candidate count for its blanked slot using the FULL course's
lexeme pool (the worst case that `_material()` converges to once a
learner has completed every lesson at or before this template's own
anchor lesson that shares its tag combination) via the same
`lexeme_matches()` port already used by `_practice_slot_check.py`. Flag
any template whose candidate count is > 1, since a single fixed-text
frame around one open slot gives the frontend/backend no mechanism to
narrow the answer beyond the tag (no picture, no earlier-established
fact, no audio) -- so >1 distinct candidate always means the learner
cannot determine the specific expected answer BY CONTEXT (they may
know it by luck/memory of the one true lesson sentence, but that's not
"determined by the given context").

Multi-slot templates (a handful, ~9 project-wide) are reported
separately and NOT auto-flagged -- other filled-but-visible slots in the
same frame may legitimately narrow the answer (e.g. "{city} is in
{country}." blanking city while country stays visible), which needs a
human read of the actual frame text, not a blind count.

Usage:
    .content-venv/bin/python3 scripts/_fill_in_blank_ambiguity_check.py
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


def _as_values(value: Any) -> set[Any]:
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


#: Maps a practice pack's (source_language, target_language) pair to the
#: backfill script module that has its real iter_specs() lexeme data. Shared
#: by this script's own main() and scripts/compile_content.py's permanent
#: practice-validate ambiguity check (AUTHORING_GUIDE.md #17) -- single
#: source of truth so a new launch-gate direction only needs updating here.
DIRECTION_SPEC_MODULES: dict[tuple[str, str], str] = {
    ("en", "fa"): "backfill_lexemes",
    ("fa", "en"): "backfill_lexemes_fa_en",
    ("en", "prs"): "backfill_lexemes_en_prs",
    ("prs", "en"): "backfill_lexemes_prs_en",
    ("en", "nl"): "backfill_lexemes_en_nl",
    ("nl", "en"): "backfill_lexemes_nl_en",
}

# Session 10 (2026-10-24): any further practice direction whose backfill
# follows the backfill_lexemes_<src>_<tgt>.py naming convention (en-es,
# en-de, ...) is discovered automatically, so a new direction never needs
# a hand edit here.
for _dir in sorted(p.name for p in (Path(__file__).resolve().parent.parent / "docs/content/practice").iterdir() if p.is_dir()):
    _mod = "backfill_lexemes_" + _dir.replace("-", "_")
    if (Path(__file__).resolve().parent / (_mod + ".py")).exists() and tuple(_dir.split("-")) not in DIRECTION_SPEC_MODULES:
        DIRECTION_SPEC_MODULES[tuple(_dir.split("-"))] = _mod


def load_lexemes_for_pair(source_language: str, target_language: str) -> list[dict] | None:
    """Returns the normalized lexeme list for a (source, target) pair via its
    real backfill_lexemes*.py iter_specs(), or None if the pair isn't one of
    the mapped launch-gate directions (caller should skip the ambiguity
    check gracefully in that case, not fail closed on unmapped/future
    language pairs)."""
    module_name = DIRECTION_SPEC_MODULES.get((source_language, target_language))
    if module_name is None:
        return None
    import importlib

    module = importlib.import_module(module_name)
    return [
        {
            "language_code": s["language_code"],
            "part_of_speech": s["part_of_speech"],
            "token": s["token"],
            "english_gloss": s["english_gloss"],
            "agreement_tags": s["agreement_tags"],
        }
        for s in module.iter_specs()
    ]


def check_pack_dict(pack: dict, lexemes: list[dict]) -> tuple[list[str], list[str]]:
    """Returns (ambiguous, multi_slot_flagged_for_review) for an already-
    loaded pack document. Shared by check_pack() (CLI path, loads YAML from
    disk) and scripts/compile_content.py's practice-validate (already has
    the pack loaded as a dict, no need to re-read the file)."""
    ambiguous: list[str] = []
    multi_slot: list[str] = []
    for template in pack.get("templates", []):
        if template.get("type") != "fill_in_blank":
            continue
        key = template.get("content_key", "<no content_key>")
        derivation = template.get("answer_derivation", {})
        if derivation.get("kind") != "slot_text":
            continue
        if derivation.get("interchangeable"):
            # AUTHORING_GUIDE.md #17: content-authored opt-in flag meaning
            # every one of the slot's own constraint-matching candidates is
            # accepted as correct (build_prompt()/grade() already handle
            # this generically) -- genuinely resolved, not a bug to flag.
            continue
        slots = template.get("slots", {})
        blanked_slot = derivation.get("slot")
        constraints = slots.get(blanked_slot)
        if constraints is None:
            continue
        candidates = [lx for lx in lexemes if lexeme_matches(lx, constraints)]
        distinct = len({lx["token"] for lx in candidates})
        frame_text = template.get("frame", {}).get("text", "")
        if len(slots) > 1:
            if distinct > 1:
                multi_slot.append(
                    f"{key}: slot {blanked_slot!r} has {distinct} distinct candidates, "
                    f"frame={frame_text!r}, other slots={sorted(s for s in slots if s != blanked_slot)} "
                    "-- needs a human read of whether the other visible slot(s) disambiguate"
                )
            continue
        if distinct > 1:
            ambiguous.append(
                f"{key}: slot {blanked_slot!r} has {distinct} distinct candidates "
                f"({sorted({lx['token'] for lx in candidates})[:8]}{'...' if distinct > 8 else ''}), "
                f"frame={frame_text!r} -- no other context to disambiguate which one is correct"
            )
    return ambiguous, multi_slot


def check_pack(pack_path: Path, lexemes: list[dict]) -> tuple[list[str], list[str]]:
    """CLI-path wrapper: loads the pack YAML from disk, then delegates to
    check_pack_dict()."""
    pack = yaml.safe_load(pack_path.read_text(encoding="utf-8"))
    return check_pack_dict(pack, lexemes)


#: (label, practice-pack directory name, (source_language, target_language))
#: for every launch-gate direction this script sweeps. Directory name and
#: language pair happen to differ only for the reverse directions' folder
#: naming, so kept explicit rather than derived.
DIRECTIONS: list[tuple[str, str, tuple[str, str]]] = [
    ("en-fa (target=fa)", "en-fa", ("en", "fa")),
    ("fa-en (target=en)", "fa-en", ("fa", "en")),
    ("en-prs (target=prs)", "en-prs", ("en", "prs")),
    ("prs-en (target=en)", "prs-en", ("prs", "en")),
    ("en-nl (target=nl)", "en-nl", ("en", "nl")),
    ("nl-en (target=en)", "nl-en", ("nl", "en")),
]
for (_src, _tgt), _mod in DIRECTION_SPEC_MODULES.items():
    if not any(d[2] == (_src, _tgt) for d in DIRECTIONS):
        DIRECTIONS.append((f"{_src}-{_tgt} (target={_tgt})", f"{_src}-{_tgt}", (_src, _tgt)))


def main() -> int:
    total_ambiguous = 0
    total_multi_slot = 0

    for label, dirname, (source_language, target_language) in DIRECTIONS:
        pack_paths = sorted((REPO_ROOT / "docs/content/practice" / dirname).glob("*_unit*.yaml"))
        try:
            lexemes = load_lexemes_for_pair(source_language, target_language)
        except Exception as exc:
            print(f"=== {label}: SPEC LOADING FAILED ===")
            print(f"  {exc!r}")
            continue
        if lexemes is None:
            print(f"=== {label}: SPEC LOADING FAILED (no DIRECTION_SPEC_MODULES entry) ===")
            continue
        print(f"=== {label}: {len(lexemes)} lexemes available ===")
        for pack_path in pack_paths:
            ambiguous, multi_slot = check_pack(pack_path, lexemes)
            total_ambiguous += len(ambiguous)
            total_multi_slot += len(multi_slot)
            if ambiguous or multi_slot:
                print(f"  {pack_path}")
                for a in ambiguous:
                    print(f"    AMBIGUOUS - {a}")
                for m in multi_slot:
                    print(f"    REVIEW    - {m}")

    print()
    print(f"TOTAL AMBIGUOUS (single-slot, auto-flagged): {total_ambiguous}")
    print(f"TOTAL MULTI-SLOT (needs human read): {total_multi_slot}")
    return 1 if (total_ambiguous or total_multi_slot) else 0


if __name__ == "__main__":
    raise SystemExit(main())
