from datetime import datetime, timedelta, timezone


def quality_for_result(result: bool | str) -> int:
    """Single seam for SM-2 quality mapping.

    Accepts either the legacy plain bool (True/False -> 5/2) or Phase C's
    3-state grading result ("correct"/"almost"/"incorrect" -> 5/4/2).
    """
    if isinstance(result, bool):
        return 5 if result else 2
    if result == "correct":
        return 5
    if result == "almost":
        return 4
    return 2


def schedule(item, correct: bool | str):
    # SQLAlchemy column defaults are applied during INSERT, not necessarily
    # when a mapped object is constructed. Normalize before scheduling so
    # new unflushed items and legacy rows with null state are both safe.
    item.repetitions = item.repetitions if item.repetitions is not None else 0
    item.interval_days = (
        item.interval_days if item.interval_days is not None else 0
    )
    item.ease_factor = item.ease_factor if item.ease_factor is not None else 2.5
    item.mastery = item.mastery if item.mastery is not None else 0.0

    now = datetime.now(timezone.utc)
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

    quality = quality_for_result(correct)
    success = quality >= 3
    if not success:
        item.repetitions = 0
        item.interval_days = 1
    else:
        next_interval_days = (
            1
            if item.repetitions == 0
            else 6
            if item.repetitions == 1
            else max(1, round(item.interval_days * item.ease_factor))
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
    item.due_at = now + timedelta(days=item.interval_days)
    return item
