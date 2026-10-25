import hashlib
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Lapses before a word is flagged as a leech. The flag only surfaces the word
# to the learner; it never suspends or removes it.
LEECH_THRESHOLD = 8
# Intervals at or below this many days are not fuzzed (short steps stay exact).
FUZZ_MIN_INTERVAL_DAYS = 7
FUZZ_FRACTION = 0.05
# The study day rolls over at this local hour, so a late-night review still
# counts toward "today" and new reviews become due in the learner's morning.
DAY_ROLLOVER_HOUR = 4

# Self-graded buttons (flashcards) -> SM-2 quality.
SELF_GRADES = ("again", "hard", "good", "easy")
_GRADE_QUALITY = {"again": 2, "hard": 3, "good": 4, "easy": 5}
HARD_INTERVAL_FACTOR = 1.2
EASY_INTERVAL_BONUS = 1.3


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


def quality_for_result(result: bool | str) -> int:
    """Single seam for SM-2 quality mapping.

    Accepts either the legacy plain bool (True/False -> 5/2) or Phase C's
    3-state grading result ("correct"/"almost"/"incorrect" -> 5/4/2).
    """
    if isinstance(result, bool):
        return 5 if result else 2
    if result in _GRADE_QUALITY:
        return _GRADE_QUALITY[result]
    if result == "correct":
        return 5
    if result == "almost":
        return 4
    return 2


def schedule(
    item,
    correct: bool | str,
    *,
    now: datetime | None = None,
    tz: str | None = None,
    fuzz_key: str | None = None,
    self_grade: str | None = None,
):
    """Advance one item's SM-2 state.

    `correct` is the grading result. `self_grade` (again/hard/good/easy),
    when given, replaces it for scheduling. `tz` is the learner's IANA
    timezone (UTC when unset): due times land on 04:00 local. `fuzz_key`
    (e.g. the item id) enables deterministic +/-5% spread on intervals over
    a week; the stored interval stays exact, only due_at is spread.
    Returns the item; `item.last_schedule` carries details for the log."""
    # SQLAlchemy column defaults are applied during INSERT, not necessarily
    # when a mapped object is constructed. Normalize before scheduling so
    # new unflushed items and legacy rows with null state are both safe.
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
    early_review_ratio = 1.0
    last_reviewed_at = getattr(item, "last_reviewed_at", None)
    due_at = getattr(item, "due_at", None)
    if last_reviewed_at is not None and due_at is not None and due_at > now:
        scheduled_span = due_at - last_reviewed_at
        if scheduled_span.total_seconds() > 0:
            elapsed_span = now - last_reviewed_at
            early_review_ratio = max(
                0.0,
                min(1.0, elapsed_span / scheduled_span),
            )

    if self_grade in _GRADE_QUALITY:
        quality = _GRADE_QUALITY[self_grade]
    else:
        quality = quality_for_result(correct)
        self_grade = None
    success = quality >= 3
    if not success:
        # Lapse handling: proportional demotion, NOT a full reset.
        #
        # Textbook SM-2 (and this function's original form) resets
        # repetitions=0 / interval_days=1 on any failed review, discarding
        # all prior learning on the word in one wrong answer. For genuinely
        # hard vocabulary that produces the classic "ease hell" spiral:
        # every lapse restarts the word from scratch, its ease_factor keeps
        # dropping, and its growth rate converges toward zero — the word
        # feels endless. Real-world SRS implementations soften this:
        # Anki's "new interval" lapse setting is exactly a multiplier on
        # the pre-lapse interval (default 0%, but 20-30% is the widely
        # recommended anti-ease-hell setting), and FSRS models post-lapse
        # stability as a fraction of prior stability, never zero.
        #
        # Numbers chosen, and why:
        #
        # - interval_days keeps 30% of its pre-lapse value (floor 1 day).
        #   30% sits at the generous end of the Anki-recommended 20-30%
        #   range, deliberately: unlike stock Anki, a lapse here ALSO
        #   costs -0.32 ease_factor and -0.2 mastery (both below, both
        #   unchanged), so the word is already being demoted on two other
        #   axes and doesn't need a near-total interval reset on top.
        #
        # - repetitions drops by 2 (floor 0) rather than to 0. The value
        #   2 is chosen for how it composes with the success branch's
        #   bootstrap ladder (reps==0 -> 1 day, reps==1 -> 6 days, else
        #   interval * ease), which this fix must not touch:
        #     * established words (reps >= 4) stay at reps >= 2 after a
        #       lapse, so their NEXT success grows multiplicatively from
        #       the retained 30% interval — the partial credit is actually
        #       used, not overwritten by the 1/6-day bootstrap steps;
        #     * young words (reps <= 2) fall back into the bootstrap
        #       ladder, which is correct — one or two successful reviews
        #       is not established learning worth preserving;
        #     * consecutive lapses compound (-2 reps and x0.3 interval
        #       each time) and converge to the old full reset
        #       (reps=0, interval=1) — the right limit for a word the
        #       learner keeps failing, so this is strictly a softening
        #       of the single-lapse case, not unlimited credit.
        item.repetitions = max(0, item.repetitions - 2)
        if hasattr(item, "lapses"):
            item.lapses = (item.lapses or 0) + 1
            if item.lapses >= LEECH_THRESHOLD:
                item.leech = True
        item.interval_days = max(1, round(item.interval_days * 0.3))
    else:
        next_interval_days = (
            1
            if item.repetitions == 0
            else 6
            if item.repetitions == 1
            else max(1, round(item.interval_days * item.ease_factor))
        )
        if self_grade == "hard" and item.repetitions >= 2:
            next_interval_days = max(
                1, round(previous_interval_days * HARD_INTERVAL_FACTOR)
            )
        elif self_grade == "easy":
            next_interval_days = max(
                next_interval_days + 1,
                round(next_interval_days * EASY_INTERVAL_BONUS),
            )
        if early_review_ratio < 1.0:
            interval_growth = next_interval_days - previous_interval_days
            next_interval_days = max(
                1,
                round(
                    previous_interval_days
                    + (interval_growth * early_review_ratio)
                ),
            )
        item.interval_days = next_interval_days
        item.repetitions += 1

    item.ease_factor = max(
        1.3,
        item.ease_factor
        + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    item.mastery = min(
        1.0,
        max(0.0, item.mastery + (0.15 if success else -0.2)),
    )
    local_day = study_day(now, tz)
    item.due_at = due_at_for(
        now, fuzzed_days(item.interval_days, fuzz_key, local_day), tz
    )
    item.last_schedule = {
        "quality": quality,
        "success": success,
        "self_grade": self_grade,
        "previous_interval_days": previous_interval_days,
        "previous_ease": previous_ease,
        "previous_due_at": previous_due_at,
        "reviewed_at": now,
    }
    return item
