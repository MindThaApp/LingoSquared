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
        item.interval_days = max(1, round(item.interval_days * 0.3))
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
