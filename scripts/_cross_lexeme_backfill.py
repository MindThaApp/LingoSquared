#!/usr/bin/env python3
"""Shared runner for cross-language lexeme backfills (X->Y, neither English).

Deliberately NOT named ``backfill_lexemes*.py`` (sync_dev_db.sh runs that glob).  A cross pair reuses the en->Y
classification (tokens, parts of speech, tags, unit/lesson provenance) from scripts/backfill_lexemes_en_<Y>.py and
replaces only the gloss text with the learner-language glosses of docs/content/lexicon/<X>-<Y>.json
(written by scripts/derive_cross.py).  Unit order is positional, so the X->Y manifest group of every derived level
must list the same realizations, in the same order, as the en->Y group.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _target_lexeme_backfill_common import REPO_ROOT, manifest_group, run  # noqa: E402


def build(learner: str, target: str):
    """(levels, iter_specs) of a cross pair: the en-<target> specs with the learner-language glosses swapped in."""
    pair = f"{learner}-{target}"
    lex = json.loads((REPO_ROOT / f"docs/content/lexicon/{pair}.json").read_text(encoding="utf-8"))
    sibling = importlib.import_module(f"backfill_lexemes_en_{target}")
    levels = {}
    sib_levels = getattr(sibling, "LEVELS", None) or {"a1": f"en-{target}"}   # en-nl has no LEVELS table (one a1 group)
    for level in lex:
        sib_group = sib_levels[level]
        group = sib_group.replace("en-", f"{learner}-", 1)
        if manifest_group(group)[0] != manifest_group(sib_group)[0]:
            raise SystemExit(f"{group} does not list the same realizations as {sib_group}; derive all units of the level first")
        levels[level] = group

    def iter_specs():
        for spec in sibling.iter_specs():
            level = spec["level"]
            if level not in lex:
                continue
            gloss = lex[level].get(spec["token"])
            if not gloss:
                raise ValueError(f"missing {learner} gloss for {spec['token']!r} ({level}) in docs/content/lexicon/{pair}.json")
            yield {**spec, "english_gloss": gloss}

    return levels, iter_specs


def main(learner: str, target: str, argv: list[str] | None = None) -> int:
    levels, iter_specs = build(learner, target)
    return run(description=__doc__, source_language=learner, target_language=target,
               levels=levels, iter_specs=iter_specs, argv=argv)
