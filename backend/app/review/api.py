"""Read-only review endpoints: due forecast and leeches."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models import Lexeme, UserLexemeSRS
from app.review.sm2 import LEECH_THRESHOLD, due_at_for

router = APIRouter()


class ReviewForecastOut(BaseModel):
    today: int
    tomorrow: int
    this_week: int


class LeechOut(BaseModel):
    lexeme_id: str
    course_id: str
    token: str
    english_gloss: str
    lapses: int


class LeechesOut(BaseModel):
    threshold: int
    items: list[LeechOut]


@router.get("/me/reviews/forecast", response_model=ReviewForecastOut)
def review_forecast(
    course_id: str | None = Query(default=None),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """Reviews due by the end of today (overdue included), during tomorrow,
    and during the following five days, on the learner's own study day."""
    now = datetime.now(timezone.utc)
    tz = user.timezone
    edges = [due_at_for(now, d, tz) for d in (1, 2, 7)]
    conds = [
        UserLexemeSRS.user_id == user.id,
        UserLexemeSRS.suspended.is_(False),
    ]
    if course_id:
        conds.append(UserLexemeSRS.course_id == course_id)

    def count(*extra):
        return db.scalar(
            select(func.count(UserLexemeSRS.id)).where(*conds, *extra)
        ) or 0

    return {
        "today": count(UserLexemeSRS.due_at < edges[0]),
        "tomorrow": count(
            UserLexemeSRS.due_at >= edges[0], UserLexemeSRS.due_at < edges[1]
        ),
        "this_week": count(
            UserLexemeSRS.due_at >= edges[1], UserLexemeSRS.due_at < edges[2]
        ),
    }


@router.get("/me/reviews/leeches", response_model=LeechesOut)
def review_leeches(
    course_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """Words lapsed LEECH_THRESHOLD+ times. Surfaced, never removed."""
    q = (
        select(UserLexemeSRS, Lexeme)
        .join(Lexeme, Lexeme.id == UserLexemeSRS.lexeme_id)
        .where(UserLexemeSRS.user_id == user.id, UserLexemeSRS.leech.is_(True))
        .order_by(UserLexemeSRS.lapses.desc(), Lexeme.token, Lexeme.id)
        .limit(limit)
    )
    if course_id:
        q = q.where(UserLexemeSRS.course_id == course_id)
    return {
        "threshold": LEECH_THRESHOLD,
        "items": [
            {
                "lexeme_id": lex.id,
                "course_id": srs.course_id,
                "token": lex.token,
                "english_gloss": lex.english_gloss,
                "lapses": srs.lapses,
            }
            for srs, lex in db.execute(q)
        ],
    }
