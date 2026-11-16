"""Self-healing for the ``user_lexeme_srs.unreviewable_at`` hide flag.

A due lexeme that could not produce a review item is flagged so it stops
inflating due counts. The flag must never strand a word forever, so besides
the content/practice-template import reset it expires after
UNREVIEWABLE_RETRY_DAYS: the row is un-hidden and the next review-session
generation either serves it or re-flags it. Only the flag column is written;
no SRS scheduling data is touched and no rows are deleted.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import UserLexemeSRS

UNREVIEWABLE_RETRY_DAYS = 7


def expire_stale_unreviewable(
    db: Session, user_id: str | None = None, now: datetime | None = None
) -> int:
    """Clear unreviewable_at older than the retry window. Does not commit."""
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(
        days=UNREVIEWABLE_RETRY_DAYS
    )
    stmt = (
        update(UserLexemeSRS)
        .where(
            UserLexemeSRS.unreviewable_at.is_not(None),
            UserLexemeSRS.unreviewable_at <= cutoff,
        )
        .values(unreviewable_at=None)
        .execution_options(synchronize_session=False)
    )
    if user_id is not None:
        stmt = stmt.where(UserLexemeSRS.user_id == user_id)
    return db.execute(stmt).rowcount or 0
