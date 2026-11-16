"""Hearts, gems and the weekly leaderboard.

Free app: gems are EARNED only (lesson completion, perfect lesson, streak
milestones) and can be spent only on in-app things (a heart refill or a streak
freeze). Nothing here involves purchases or money.

Every piece sits behind its own flag (ENABLE_HEARTS / ENABLE_GEMS /
ENABLE_LEADERBOARD, default off). The server is authoritative; the client only
displays what these functions compute.

Hearts are derived lazily from stored timestamps (no cron):
`hearts` + `hearts_anchor_at` (start of the current refill interval).
The gem ledger (`gem_transactions`) is append-only; each event carries a
per-user unique idempotency key so replays and retries cannot post twice.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, union_all
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    ExerciseAttempt,
    GemTransaction,
    PracticeAttempt,
    User,
    UserGameState,
    UserStats,
)

HEARTS_MAX = 5
HEART_REFILL_SECONDS = 4 * 60 * 60
# A practice/review session restores one heart once the learner has answered
# this many practice items since the last restore (server-counted, so the
# client cannot claim a restore without the work).
PRACTICE_RESTORE_MIN_ANSWERS = 5

GEMS_LESSON_COMPLETE = 5
GEMS_PERFECT_LESSON = 5
STREAK_MILESTONE_GEMS = {3: 5, 7: 10, 14: 15, 30: 30, 60: 50, 100: 100}
GEMS_STREAK_EVERY_100 = 100
SPEND_COSTS = {"heart_refill": 10, "streak_freeze": 20}
MAX_STREAK_FREEZES = 2

LEADERBOARD_TOP_N = 20


def hearts_enabled() -> bool:
    return get_settings().enable_hearts


def gems_enabled() -> bool:
    return get_settings().enable_gems


def leaderboard_enabled() -> bool:
    return get_settings().enable_leaderboard


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


# ---------------------------------------------------------------- hearts math


def refill_hearts(
    stored: int, anchor: datetime | None, now: datetime
) -> tuple[int, datetime | None]:
    """Pure lazy-refill: one heart per HEART_REFILL_SECONDS since `anchor`.

    Returns (hearts, new_anchor). The anchor advances by whole intervals only,
    so partial progress toward the next heart is kept. At full hearts the
    anchor is None.
    """
    stored = max(0, min(HEARTS_MAX, stored))
    if stored >= HEARTS_MAX:
        return HEARTS_MAX, None
    anchor = _aware(anchor) or now
    elapsed = (now - anchor).total_seconds()
    gained = int(elapsed // HEART_REFILL_SECONDS) if elapsed > 0 else 0
    hearts = min(HEARTS_MAX, stored + gained)
    if hearts >= HEARTS_MAX:
        return HEARTS_MAX, None
    return hearts, anchor + timedelta(seconds=gained * HEART_REFILL_SECONDS)


def next_heart_at(hearts: int, anchor: datetime | None) -> datetime | None:
    if hearts >= HEARTS_MAX or anchor is None:
        return None
    return anchor + timedelta(seconds=HEART_REFILL_SECONDS)


# ---------------------------------------------------------------------- state


def game_state(db: Session, user_id: str, *, for_update: bool = False) -> UserGameState:
    query = select(UserGameState).where(UserGameState.user_id == user_id)
    if for_update:
        query = query.with_for_update()
    state = db.scalar(query)
    if state is None:
        candidate = UserGameState(
            user_id=user_id, hearts=HEARTS_MAX, gem_balance=0, leaderboard_opt_out=False
        )
        try:
            with db.begin_nested():
                db.add(candidate)
                db.flush()
            state = candidate
        except IntegrityError:
            state = db.scalar(query)
            if state is None:
                raise
    return state


def _settle(state: UserGameState, now: datetime) -> None:
    """Apply the lazy refill to the stored columns (caller holds the lock)."""
    hearts, anchor = refill_hearts(state.hearts, state.hearts_anchor_at, now)
    state.hearts = hearts
    state.hearts_anchor_at = anchor


def hearts_now(db: Session, user_id: str, now: datetime | None = None) -> tuple[int, datetime | None]:
    """Current hearts and the time the next one arrives, without writing."""
    now = now or datetime.now(timezone.utc)
    state = db.get(UserGameState, user_id)
    if state is None:
        return HEARTS_MAX, None
    hearts, anchor = refill_hearts(state.hearts, state.hearts_anchor_at, now)
    return hearts, next_heart_at(hearts, anchor)


def lose_heart(db: Session, user_id: str, now: datetime | None = None) -> int:
    """A wrong answer in a new lesson costs one heart (never below zero)."""
    now = now or datetime.now(timezone.utc)
    state = game_state(db, user_id, for_update=True)
    _settle(state, now)
    if state.hearts > 0:
        if state.hearts >= HEARTS_MAX:
            state.hearts_anchor_at = now
        state.hearts -= 1
    return state.hearts


def restore_heart_for_practice(db: Session, user_id: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    state = game_state(db, user_id, for_update=True)
    _settle(state, now)
    if state.hearts >= HEARTS_MAX:
        return {"restored": False, "reason": "full"}
    since = _aware(state.last_practice_restore_at)
    q = select(func.count(PracticeAttempt.id)).where(PracticeAttempt.user_id == user_id)
    if since is not None:
        q = q.where(PracticeAttempt.created_at > since)
    answered = db.scalar(q) or 0
    if answered < PRACTICE_RESTORE_MIN_ANSWERS:
        return {"restored": False, "reason": "not_enough_practice"}
    state.hearts += 1
    if state.hearts >= HEARTS_MAX:
        state.hearts_anchor_at = None
    state.last_practice_restore_at = now
    return {"restored": True, "reason": None}


# ------------------------------------------------------------------ gem ledger


def _post(db: Session, state: UserGameState, amount: int, kind: str, key: str) -> bool:
    """Append one ledger row. Returns False if the key was already used.

    Caller must hold the state row lock. A negative amount can never take the
    balance below zero (checked by the caller and by a DB CHECK).
    """
    exists = db.scalar(
        select(GemTransaction.id).where(
            GemTransaction.user_id == state.user_id,
            GemTransaction.idempotency_key == key,
        )
    )
    if exists is not None:
        return False
    new_balance = state.gem_balance + amount
    if new_balance < 0:
        return False
    try:
        with db.begin_nested():
            db.add(
                GemTransaction(
                    user_id=state.user_id,
                    amount=amount,
                    kind=kind,
                    idempotency_key=key,
                    balance_after=new_balance,
                )
            )
            db.flush()
    except IntegrityError:
        return False
    state.gem_balance = new_balance
    return True


def award_gems(db: Session, user_id: str, amount: int, kind: str, key: str) -> int:
    """Earn gems once per idempotency key. Returns gems actually granted."""
    if not gems_enabled() or amount <= 0:
        return 0
    state = game_state(db, user_id, for_update=True)
    return amount if _post(db, state, amount, kind, key) else 0


def streak_milestone_gems(streak_days: int) -> int:
    if streak_days in STREAK_MILESTONE_GEMS:
        return STREAK_MILESTONE_GEMS[streak_days]
    if streak_days > 100 and streak_days % 100 == 0:
        return GEMS_STREAK_EVERY_100
    return 0


def on_streak_advanced(db: Session, user_id: str, streak_days: int, day) -> int:
    gems = streak_milestone_gems(streak_days)
    if not gems:
        return 0
    return award_gems(db, user_id, gems, "streak_milestone", f"streak:{streak_days}:{day.isoformat()}")


def award_lesson_gems(db: Session, user_id: str, lesson_id: str, perfect: bool) -> int:
    """Gems for the FIRST completion of a lesson (replays never reach here)."""
    total = award_gems(db, user_id, GEMS_LESSON_COMPLETE, "lesson_complete", f"lesson:{lesson_id}")
    if perfect:
        total += award_gems(db, user_id, GEMS_PERFECT_LESSON, "perfect_lesson", f"perfect:{lesson_id}")
    return total


class SpendError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def spend_gems(db: Session, user_id: str, item: str, operation_id: str) -> dict:
    """Spend earned gems on a heart refill or a streak freeze.

    Idempotent per (item, operation_id): a retry returns applied=False and
    charges nothing. Raises SpendError for invalid or unaffordable requests.
    """
    cost = SPEND_COSTS.get(item)
    if cost is None:
        raise SpendError("unknown_item", "Unknown item")
    now = datetime.now(timezone.utc)
    state = game_state(db, user_id, for_update=True)
    key = f"spend:{item}:{operation_id}"
    already = db.scalar(
        select(GemTransaction.id).where(
            GemTransaction.user_id == user_id, GemTransaction.idempotency_key == key
        )
    )
    if already is not None:
        return {"applied": False, "item": item, "cost": cost, "gem_balance": state.gem_balance}
    _settle(state, now)
    if item == "heart_refill" and state.hearts >= HEARTS_MAX:
        raise SpendError("hearts_full", "Your hearts are already full")
    stats = None
    if item == "streak_freeze":
        stats = db.scalar(
            select(UserStats).where(UserStats.user_id == user_id).with_for_update()
        )
        if stats is None:
            stats = UserStats(user_id=user_id, total_xp=0, streak_days=0, daily_goal=20, streak_freezes_available=0)
            db.add(stats)
            db.flush()
        if stats.streak_freezes_available >= MAX_STREAK_FREEZES:
            raise SpendError("freeze_limit", "You already have the maximum number of streak freezes")
    if state.gem_balance < cost:
        raise SpendError("insufficient_gems", "Not enough gems")
    if not _post(db, state, -cost, f"spend_{item}", key):
        raise SpendError("insufficient_gems", "Not enough gems")
    if item == "heart_refill":
        state.hearts = HEARTS_MAX
        state.hearts_anchor_at = None
    else:
        stats.streak_freezes_available += 1
    return {"applied": True, "item": item, "cost": cost, "gem_balance": state.gem_balance}


# ----------------------------------------------------------------- leaderboard


def week_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Monday 00:00 UTC to the next Monday 00:00 UTC containing `now`."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=now.weekday())
    return start, start + timedelta(days=7)


def _weekly_totals(start: datetime, end: datetime):
    ex = select(ExerciseAttempt.user_id.label("uid"), ExerciseAttempt.xp_awarded.label("xp")).where(
        ExerciseAttempt.created_at >= start, ExerciseAttempt.created_at < end
    )
    pr = select(PracticeAttempt.user_id.label("uid"), PracticeAttempt.xp_awarded.label("xp")).where(
        PracticeAttempt.created_at >= start, PracticeAttempt.created_at < end
    )
    both = union_all(ex, pr).subquery()
    return (
        select(both.c.uid.label("uid"), func.sum(both.c.xp).label("xp"))
        .group_by(both.c.uid)
        .subquery()
    )


def _eligible(totals):
    """Users with weekly XP > 0 who are active and have not opted out."""
    opted_out = func.coalesce(UserGameState.leaderboard_opt_out, False)
    return (
        select(User.id, User.display_name, totals.c.xp)
        .join(totals, totals.c.uid == User.id)
        .outerjoin(UserGameState, UserGameState.user_id == User.id)
        .where(User.is_active.is_(True), opted_out.is_(False), totals.c.xp > 0)
    )


def weekly_leaderboard(db: Session, user_id: str, now: datetime | None = None) -> dict:
    start, end = week_bounds(now)
    totals = _weekly_totals(start, end)
    base = _eligible(totals)
    rows = db.execute(base.order_by(totals.c.xp.desc(), User.id).limit(LEADERBOARD_TOP_N)).all()
    state = db.get(UserGameState, user_id)
    opted_out = bool(state.leaderboard_opt_out) if state else False
    entries = []
    previous_xp, rank = None, 0
    for index, (uid_, name, xp) in enumerate(rows, start=1):
        if xp != previous_xp:
            rank, previous_xp = index, xp
        entries.append(
            {
                "rank": rank,
                "display_name": (name or "").strip() or "Learner",
                "xp": int(xp),
                "is_me": uid_ == user_id,
            }
        )
    me = None
    if not opted_out:
        mine = db.scalar(select(totals.c.xp).where(totals.c.uid == user_id)) or 0
        if mine > 0:
            sub = base.subquery()
            ahead = db.scalar(select(func.count()).select_from(sub).where(sub.c.xp > mine)) or 0
            me = {"rank": int(ahead) + 1, "xp": int(mine)}
        else:
            me = {"rank": None, "xp": 0}
    return {
        "week_start": start,
        "week_end": end,
        "opted_out": opted_out,
        "entries": entries,
        "me": me,
    }
