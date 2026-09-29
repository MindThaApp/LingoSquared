"""Opt-in in-process scheduler for local-time daily push reminders."""

from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import PushNotificationGuard, PushSubscription, User, UserLexemeSRS, UserStats
from app.services import push as push_service
from app.services.progress import effective_streak_days, resolve_user_tz


def in_local_window(user_timezone: str | None, now: datetime, start_hour: int, end_hour: int) -> bool:
    """Whether an instant falls in a local half-open [start, end) hour window."""
    local_now = now.astimezone(resolve_user_tz(user_timezone))
    return time(start_hour) <= local_now.timetz().replace(tzinfo=None) < time(end_hour)


def local_date_for(user_timezone: str | None, now: datetime) -> date:
    return now.astimezone(resolve_user_tz(user_timezone)).date()


def claim_notification(db: Session, user_id: str, trigger_code: str, local_date: date) -> bool:
    """Atomically claim one send attempt across processes/workers."""
    result = db.execute(
        pg_insert(PushNotificationGuard)
        .values(
            user_id=user_id,
            trigger_code=trigger_code,
            local_date=local_date,
            attempted_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_nothing(
            constraint="uq_push_notification_guards_user_trigger_date"
        )
        .returning(PushNotificationGuard.id)
    )
    claimed = result.scalar_one_or_none() is not None
    if claimed:
        # Commit the guard before sending so a second worker cannot deliver
        # the same daily trigger while this worker is talking to Web Push.
        db.commit()
    return claimed


def run_push_scheduler_once(now: datetime | None = None, db: Session | None = None) -> dict[str, int]:
    """Evaluate reminders once; `now` is injectable for deterministic tests."""
    if not push_service.push_configured():
        return {"notified_users": 0, "notifications_sent": 0}
    instant = now or datetime.now(timezone.utc)
    own_session = db is None
    db = db or SessionLocal()
    notified_users = 0
    notifications_sent = 0
    try:
        users = db.scalars(
            select(User)
            .join(PushSubscription, PushSubscription.user_id == User.id)
            .distinct()
        ).all()
        for user in users:
            local_day = local_date_for(user.timezone, instant)
            stats = db.get(UserStats, user.id)
            has_due_reviews = db.scalar(
                select(UserLexemeSRS.id).where(
                    UserLexemeSRS.user_id == user.id,
                    UserLexemeSRS.due_at <= instant,
                    UserLexemeSRS.suspended.is_(False),
                ).limit(1)
            ) is not None
            if in_local_window(user.timezone, instant, 18, 19) and has_due_reviews:
                if claim_notification(db, user.id, "daily_reminder", local_day):
                    sent = push_service.send_push_to_user(
                        db, user.id, "Reviews are waiting",
                        "You have words due for review — keep your streak going.", "/review",
                    )
                    if sent:
                        notified_users += 1
                        notifications_sent += sent

            if stats and stats.streak_days > 0 and in_local_window(user.timezone, instant, 19, 20):
                effective_days = effective_streak_days(
                    stats.streak_days,
                    stats.last_activity_date,
                    user.timezone,
                    today=local_day,
                    freezes_available=stats.streak_freezes_available,
                )
                if effective_days > 0 and stats.last_activity_date != local_day:
                    if claim_notification(db, user.id, "streak_at_risk", local_day):
                        sent = push_service.send_push_to_user(
                            db, user.id, "Your streak is at risk",
                            f"Your {effective_days}-day streak ends tonight — come back before midnight!", "/",
                        )
                        if sent:
                            notified_users += 1
                            notifications_sent += sent
        return {"notified_users": notified_users, "notifications_sent": notifications_sent}
    finally:
        if own_session:
            db.close()


def push_scheduler_enabled() -> bool:
    return get_settings().enable_push_scheduler
