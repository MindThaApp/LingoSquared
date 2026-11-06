import hashlib
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.review import fsrs

# Lapses before a word is flagged as a leech. The flag only surfaces the word
# to the learner; it never suspends or removes it.
LEECH_THRESHOLD = 8
# Intervals at or below this many days are not fuzzed (short steps stay exact).
FUZZ_MIN_INTERVAL_DAYS = 7
FUZZ_FRACTION = 0.05
# The study day rolls over at this local hour, so a late-night review still
# counts toward "today" and new reviews become due in the learner's morning.
DAY_ROLLOVER_HOUR = 4

# Self-graded buttons (flashcards) -> FSRS rating. The legacy SM-2 quality
# values are still written to review_events.quality (again 2 .. easy 5).
SELF_GRADES = ("again", "hard", "good", "easy")
_GRADE_RATING = {
    "again": fsrs.AGAIN,
    "hard": fsrs.HARD,
    "good": fsrs.GOOD,
    "easy": fsrs.EASY,
}
_RATING_QUALITY = {fsrs.AGAIN: 2, fsrs.HARD: 3, fsrs.GOOD: 4, fsrs.EASY: 5}


def _tz(name: str | None):
    if name:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return ZoneInfo("UTC")


def fuzz_factor(key: str, local_day) -> float:
    """Deterministic factor in [-FUZZ_FRACTION, +FUZZ_FRACTION], stable for
    one (item, local day) pair so the same review always lands on the same
    date and tests need no random seed."""
    digest = hashlib.sha256(f"{key}|{local_day.isoformat()}".encode()).digest()
    unit = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF  # 0..1
    return (unit * 2 - 1) * FUZZ_FRACTION


def fuzzed_days(interval_days: int, key: str | None, local_day) -> int:
    if key is None or interval_days <= FUZZ_MIN_INTERVAL_DAYS:
        return interval_days
    return max(1, round(interval_days * (1 + fuzz_factor(key, local_day))))


def study_day(now: datetime, tz_name: str | None):
    """The learner's current study day (local date, rolling over at 04:00)."""
    local = now.astimezone(_tz(tz_name))
    return (local - timedelta(hours=DAY_ROLLOVER_HOUR)).date()


def due_at_for(
    now: datetime, days: int, tz_name: str | None = None
) -> datetime:
    """Start (04:00 local) of the study day `days` after today, in UTC."""
    tz = _tz(tz_name)
    day = study_day(now, tz_name) + timedelta(days=days)
    local = datetime.combine(day, time(DAY_ROLLOVER_HOUR), tzinfo=tz)
    return local.astimezone(timezone.utc)


def rating_for_result(result: bool | str) -> int:
    """Single seam mapping an answer outcome to an FSRS rating.

    Accepts the legacy plain bool (True/False -> Good/Again) or the 3-state
    grading result ("correct"/"almost"/"incorrect" -> Good/Hard/Again) or a
    self-grade word. Hints and retries are not recorded by the app, so they
    cannot feed in; "almost" (a near-miss) is the Hard signal.
    """
    if isinstance(result, bool):
        return fsrs.GOOD if result else fsrs.AGAIN
    if result in _GRADE_RATING:
        return _GRADE_RATING[result]
    if result == "correct":
        return fsrs.GOOD
    if result == "almost":
        return fsrs.HARD
    return fsrs.AGAIN


def legacy_state(item) -> tuple[float, float] | None:
    """(stability, difficulty) for a card that has SM-2 history but no FSRS
    state yet, or None for a card that has never been reviewed. Mirrors the
    alembic 0037 backfill: stability = interval, difficulty from ease; a
    history-less review item starts as a failed card."""
    reviewed = getattr(item, "last_reviewed_at", None) is not None
    interval = item.interval_days or 0
    if not (reviewed or (item.repetitions or 0) > 0 or interval > 1):
        if hasattr(item, "last_reviewed_at"):
            return None  # genuinely new lexeme card
        # A legacy review item is created by a wrong answer: it starts as a
        # card that was just failed.
        return (
            fsrs.initial_stability(fsrs.AGAIN),
            fsrs.initial_difficulty(fsrs.AGAIN),
        )
    return (
        float(max(1, interval)),
        fsrs.difficulty_from_ease(
            item.ease_factor if item.ease_factor is not None else 2.5
        ),
    )


def _elapsed_days(item, now: datetime) -> float:
    last = getattr(item, "last_reviewed_at", None)
    if last is None and item.due_at is not None:
        # No review timestamp (legacy review items, seeds): assume the last
        # review happened one interval before the due date.
        last = item.due_at - timedelta(days=item.interval_days or 0)
    if last is None:
        return float(item.interval_days or 0)  # no timestamps: assume on time
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return max(0.0, (now - last).total_seconds() / 86400)


def schedule(
    item,
    correct: bool | str,
    *,
    now: datetime | None = None,
    tz: str | None = None,
    fuzz_key: str | None = None,
    self_grade: str | None = None,
):
    """Advance one item's FSRS state.

    `correct` is the grading result. `self_grade` (again/hard/good/easy),
    when given, replaces it for scheduling. `tz` is the learner's IANA
    timezone (UTC when unset): due times land on 04:00 local. `fuzz_key`
    (e.g. the item id) enables deterministic +/-5% spread on intervals over
    a week; the stored interval stays exact, only due_at is spread.

    The legacy columns stay populated so the API is unchanged:
    interval_days is the scheduled interval, ease_factor a function of
    difficulty, repetitions the run of successful reviews.
    Returns the item; `item.last_schedule` carries details for the log."""
    item.repetitions = item.repetitions if item.repetitions is not None else 0
    item.interval_days = (
        item.interval_days if item.interval_days is not None else 0
    )
    item.ease_factor = item.ease_factor if item.ease_factor is not None else 2.5
    item.mastery = item.mastery if item.mastery is not None else 0.0

    now = now or datetime.now(timezone.utc)
    previous_due_at = getattr(item, "due_at", None)
    previous_ease = item.ease_factor
    previous_interval_days = item.interval_days

    if self_grade in _GRADE_RATING:
        rating = _GRADE_RATING[self_grade]
    else:
        rating = rating_for_result(correct)
        self_grade = None
    quality = _RATING_QUALITY[rating]
    success = rating != fsrs.AGAIN

    stability = getattr(item, "stability", None)
    difficulty = getattr(item, "difficulty", None)
    if stability is None or difficulty is None:
        legacy = legacy_state(item)
        stability, difficulty = legacy if legacy else (None, None)
    previous_stability = stability
    stability, difficulty = fsrs.review(
        stability, difficulty, _elapsed_days(item, now), rating
    )

    if not success:
        if hasattr(item, "lapses"):
            item.lapses = (item.lapses or 0) + 1
            if item.lapses >= LEECH_THRESHOLD:
                item.leech = True
        item.repetitions = 0
    else:
        item.repetitions += 1
    item.stability = stability
    item.difficulty = difficulty
    item.interval_days = fsrs.next_interval(stability)
    item.ease_factor = fsrs.ease_from_difficulty(difficulty)
    item.mastery = min(
        1.0,
        max(0.0, item.mastery + (0.15 if success else -0.2)),
    )
    local_day = study_day(now, tz)
    item.due_at = due_at_for(
        now, fuzzed_days(item.interval_days, fuzz_key, local_day), tz
    )
    item.last_schedule = {
        "rating": rating,
        "quality": quality,
        "success": success,
        "self_grade": self_grade,
        "previous_interval_days": previous_interval_days,
        "previous_ease": previous_ease,
        "previous_stability": previous_stability,
        "previous_due_at": previous_due_at,
        "reviewed_at": now,
    }
    return item
