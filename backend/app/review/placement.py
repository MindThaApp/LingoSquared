"""Pure (DB-free) helpers for the course placement test.

The placement test samples a course's own existing recognition exercises
(``multiple_choice`` / ``matching_pairs``), ladders them by the CEFR level
of their owning unit, and maps per-level accuracy to a recommended
starting level. Everything in this module is pure so it can be unit-tested
without a database or HTTP layer -- the DB-touching ``build_placement_set``
and the endpoints live in ``app/api/router.py``.

Design authority: ``docs/PLACEMENT_TEST_SPEC.md`` (CEO-approved 2026-08-05)
and the placement section of ``docs/CONTRACT.md``.
"""

# CEFR sublevels in ascending difficulty order (mirrors the frontend's
# levelPreferences.ts CEFR_ORDER). Used both to validate a parsed level and
# to walk answered blocks lowest-first.
CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

# The placement ladder proper: only A1..B2 are ever administered (see
# spec 2.1). A course reaching B1 yields 12 items; through B2, 16.
PLACEMENT_LEVELS = ["A1", "A2", "B1", "B2"]

# Items sampled per level block, and the correct-per-block count that
# counts as passing that level (>= 3 of 4 == >= 75%).
PLACEMENT_BLOCK_SIZE = 4
PLACEMENT_PASS_THRESHOLD = 3

# The only exercise types placement ever probes with: self-contained,
# choice-graded (correct/incorrect, never "almost"), no audio, no free
# text -> script-agnostic and RTL / prs-no-TTS safe. Do NOT add free-text
# types here without revisiting grading.py strictness (see spec 4).
PLACEMENT_PROBE_TYPES = ("multiple_choice", "matching_pairs")


def parse_cefr_level(content_key):
    """Parse the CEFR sublevel out of a unit's ``content_key``.

    ``"nl.a1.unit72.dierenwinkel"`` -> ``"A1"``; ``"fa.b1.unit01.x"`` ->
    ``"B1"``. Returns ``None`` for a missing/unparseable key (legacy units
    imported before content_key tracking) so callers can drop such units
    from the ladder rather than misclassify them. Mirrors the frontend
    ``parseCefrLevel`` in ``levelPreferences.ts``.

    Level is ALWAYS derived from ``content_key`` here, never from
    ``Course.level`` -- the latter is a single fixed value set at course
    creation and never updated as higher content is appended (spec 4,
    footgun 5).
    """
    if not content_key:
        return None
    parts = str(content_key).split(".")
    if len(parts) < 2:
        return None
    segment = parts[1].upper()
    return segment if segment in CEFR_ORDER else None


def _level_sort_key(level):
    return CEFR_ORDER.index(level) if level in CEFR_ORDER else len(CEFR_ORDER)


def summarize_per_level(graded, *, pass_threshold=PLACEMENT_PASS_THRESHOLD):
    """Aggregate ``[(level, correct_bool), ...]`` into
    ``{level: {"correct": n, "total": t}}``. Probes with a ``None`` level
    are ignored."""
    per_level = {}
    for level, correct in graded:
        if level is None:
            continue
        bucket = per_level.setdefault(level, {"correct": 0, "total": 0})
        bucket["total"] += 1
        if correct:
            bucket["correct"] += 1
    return per_level


def recommend_from_answers(graded, *, pass_threshold=PLACEMENT_PASS_THRESHOLD):
    """Map graded placement answers to a recommended starting level.

    ``graded`` is a list of ``(cefr_level, correct_bool)`` -- one entry per
    answered probe. Returns ``(recommended_level, per_level_summary)``.

    Walking answered levels lowest-first, the recommendation is the first
    level the learner FAILS (correct < ``pass_threshold``); if every
    answered level passes, it is the highest answered level. Returns
    ``(None, {})`` for no gradeable answers (caller then recommends the
    course start). This realizes the spec 2.1 table:

    - fail A1                -> A1 (course start)
    - pass A1, fail A2       -> A2
    - pass A1+A2, fail B1    -> B1
    - pass all present       -> highest level present
    """
    per_level = summarize_per_level(graded, pass_threshold=pass_threshold)
    levels = sorted(per_level, key=_level_sort_key)
    recommended = None
    for level in levels:
        recommended = level
        if per_level[level]["correct"] < pass_threshold:
            break
    return recommended, per_level
