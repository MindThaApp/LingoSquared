#!/usr/bin/env python3
"""en-fa lexeme classification under the per-direction name used by the cross-pair tooling.

The en-fa (Farsi target, English learner) backfill predates the backfill_lexemes_en_<Y>.py naming and lives in
scripts/backfill_lexemes.py.  derive_cross.py / _cross_lexeme_backfill.py import backfill_lexemes_en_<target>, so this
module re-exports that script's `iter_specs` (and everything else it defines) unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backfill_lexemes import *  # noqa: E402,F401,F403
from backfill_lexemes import iter_specs, main  # noqa: E402,F401

if __name__ == "__main__":
    raise SystemExit(main())
