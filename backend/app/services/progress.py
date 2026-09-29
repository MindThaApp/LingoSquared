from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import UserStats, Achievement, UserAchievement

def valid_timezone_or_none(user_timezone: str | None) -> str | None:
    """Validate a client-supplied IANA timezone string before persisting
    it on User.timezone - store nothing rather than a garbage value that
    would silently fall back to UTC forever at read time anyway."""
    if not user_timezone:
        return None
    try:
        ZoneInfo(user_timezone)
    except ZoneInfoNotFoundError:
        return None
    return user_timezone

def resolve_user_tz(user_timezone: str | None):
    """Resolve a user's IANA timezone string, falling back to UTC for a
    missing/invalid value rather than the old server-local behavior -
    every caller of "what day is it for this user" should go through
    this, not date.today()/datetime.now() directly."""
    if user_timezone:
        try:
            return ZoneInfo(user_timezone)
        except ZoneInfoNotFoundError:
            pass
    return ZoneInfo("UTC")

STREAK_FREEZE_MILESTONE = 7

def stats_for(db:Session,user_id:str):
    s=db.get(UserStats,user_id)
    if not s:
        s=UserStats(
            user_id=user_id,
            total_xp=0,
            streak_days=0,
            last_activity_date=None,
            daily_goal=20,
            streak_freezes_available=0,
            last_freeze_used_date=None,
        )
        db.add(s)
        db.flush()
    return s
def record_activity(db:Session,user_id:str,xp:int,user_timezone:str|None=None):
    s=stats_for(db,user_id); today=datetime.now(resolve_user_tz(user_timezone)).date()
    if s.last_activity_date != today:
        gap = (today - s.last_activity_date).days if s.last_activity_date else None
        if gap == 1:
            s.streak_days += 1
        elif gap == 2 and s.streak_freezes_available > 0:
            # Exactly one missed day, and a freeze is available: silently
            # cover the gap instead of resetting - "auto-consumed on the
            # first missed day" per the spec, no user action required.
            s.streak_freezes_available -= 1
            s.streak_days += 1
            s.last_freeze_used_date = today
        else:
            s.streak_days = 1
        s.last_activity_date = today
        if s.streak_freezes_available == 0 and s.streak_days % STREAK_FREEZE_MILESTONE == 0:
            s.streak_freezes_available = 1
    award_xp(db,user_id,xp,s)
    return s

def award_xp(db:Session,user_id:str,xp:int,stats:UserStats|None=None):
    """Add XP and unlock XP achievements without counting learning activity."""
    s=stats or stats_for(db,user_id)
    s.total_xp += xp
    for achievement in db.scalars(select(Achievement).where(Achievement.threshold<=s.total_xp)):
        if not db.scalar(select(UserAchievement).where(UserAchievement.user_id==user_id,UserAchievement.achievement_id==achievement.id)):
            db.add(UserAchievement(user_id=user_id,achievement_id=achievement.id))
    return s

def activity_day_bounds(user_timezone:str|None=None):
    """Bounds for the user's own local day (IANA timezone, UTC fallback)
    - used consistently for streaks and any other "once per day" window
    (e.g. practice's diminishing-returns XP cap, per-lexeme-per-day SRS
    gating) so they all agree on when a user's day starts."""
    tz=resolve_user_tz(user_timezone)
    start=datetime.combine(datetime.now(tz).date(),time.min,tzinfo=tz)
    return start,start+timedelta(days=1)
