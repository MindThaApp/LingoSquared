"""Review event log writes and the scheduler wrapper that feeds it."""

from sqlalchemy.orm import Session

from app.models import ReviewEvent
from app.review.sm2 import schedule


def schedule_and_log(
    db: Session,
    item,
    result: bool | str,
    *,
    user,
    source: str,
    lexeme_id: str | None = None,
    exercise_id: str | None = None,
    course_id: str | None = None,
    self_grade: str | None = None,
    latency_ms: int | None = None,
    now=None,
):
    """Run the scheduler on `item` and append one ReviewEvent row.

    The row is added to the caller's session and committed with it, so a
    review that is rolled back leaves no log entry."""
    schedule(
        item,
        result,
        now=now,
        tz=getattr(user, "timezone", None),
        fuzz_key=str(getattr(item, "id", None) or lexeme_id or exercise_id),
        self_grade=self_grade,
    )
    info = item.last_schedule
    db.add(
        ReviewEvent(
            user_id=user.id,
            lexeme_id=lexeme_id,
            exercise_id=exercise_id,
            course_id=course_id,
            source=source,
            reviewed_at=info["reviewed_at"],
            result=result if isinstance(result, str) else (
                "correct" if result else "incorrect"
            ),
            self_grade=info["self_grade"],
            quality=info["quality"],
            correct=info["success"],
            previous_interval_days=info["previous_interval_days"],
            new_interval_days=item.interval_days,
            previous_ease=info["previous_ease"],
            new_ease=item.ease_factor,
            previous_due_at=info["previous_due_at"],
            new_due_at=item.due_at,
            latency_ms=latency_ms,
        )
    )
    return item


def schedule_practice_srs(db: Session, srs, result, *, user, item, body):
    """Schedule a UserLexemeSRS row from a practice-item answer and log it."""
    return schedule_and_log(
        db,
        srs,
        result,
        user=user,
        source=item.source,
        lexeme_id=srs.lexeme_id,
        course_id=srs.course_id,
        self_grade=getattr(body, "self_grade", None),
        latency_ms=getattr(body, "latency_ms", None),
    )


def apply_self_grade(result: str, item_type, body) -> str:
    """Flashcards are self-graded: an explicit rating overrides the
    known/unknown verdict ("again" is a miss, anything else a pass). Other
    item types keep automatic grading and ignore a stray rating."""
    grade = getattr(body, "self_grade", None)
    if grade is None or str(getattr(item_type, "value", item_type)) != "flashcard":
        return result
    return "incorrect" if grade == "again" else "correct"
