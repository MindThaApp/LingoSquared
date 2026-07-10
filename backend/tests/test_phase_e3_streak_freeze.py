from datetime import datetime, timedelta, timezone

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import UserStats
from app.services.progress import STREAK_FREEZE_MILESTONE, record_activity


def _today():
    # record_activity(..., user_timezone=None) resolves to UTC.
    return datetime.now(timezone.utc).date()


def _register(client, email="freeze-user@example.com"):
    response = client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 201
    return decode_token(response.json()["access_token"])


def test_freeze_earned_at_seven_day_milestone(client):
    uid = _register(client, "freeze-earn@example.com")
    with SessionLocal() as db:
        for day in range(STREAK_FREEZE_MILESTONE):
            s = db.get(UserStats, uid)
            if s.last_activity_date:
                s.last_activity_date -= timedelta(days=1)
                db.commit()
            record_activity(db, uid, 10)
            db.commit()
        s = db.get(UserStats, uid)
        assert s.streak_days == STREAK_FREEZE_MILESTONE
        assert s.streak_freezes_available == 1


def test_freeze_not_re_earned_before_next_milestone(client):
    uid = _register(client, "freeze-no-double@example.com")
    with SessionLocal() as db:
        for day in range(STREAK_FREEZE_MILESTONE + 1):
            s = db.get(UserStats, uid)
            if s.last_activity_date:
                s.last_activity_date -= timedelta(days=1)
                db.commit()
            record_activity(db, uid, 10)
            db.commit()
        s = db.get(UserStats, uid)
        assert s.streak_days == STREAK_FREEZE_MILESTONE + 1
        # Already has a freeze from day 7 and hasn't hit day 14 yet.
        assert s.streak_freezes_available == 1


def test_freeze_auto_consumed_on_single_missed_day(client):
    uid = _register(client, "freeze-consume@example.com")
    # Seed state directly (bypassing record_activity) to represent "already
    # on a 7-day streak, one freeze available, last active 2 days ago" -
    # exactly one missed day.
    with SessionLocal() as db:
        s = db.get(UserStats, uid)
        s.streak_days = STREAK_FREEZE_MILESTONE
        s.streak_freezes_available = 1
        s.last_activity_date = _today() - timedelta(days=2)
        db.commit()

    with SessionLocal() as db:
        record_activity(db, uid, 10)
        db.commit()
        s = db.get(UserStats, uid)
        assert s.streak_freezes_available == 0
        assert s.last_freeze_used_date == s.last_activity_date == _today()
        # Streak kept growing instead of resetting to 1.
        assert s.streak_days == STREAK_FREEZE_MILESTONE + 1


def test_streak_resets_without_available_freeze_after_gap(client):
    uid = _register(client, "freeze-reset@example.com")
    with SessionLocal() as db:
        s = db.get(UserStats, uid)
        s.streak_days = 5
        s.streak_freezes_available = 0
        s.last_activity_date = _today() - timedelta(days=2)
        db.commit()

    with SessionLocal() as db:
        record_activity(db, uid, 10)
        db.commit()
        s = db.get(UserStats, uid)
        assert s.streak_days == 1


def test_streak_endpoint_reports_freeze_status(client):
    uid = _register(client, "freeze-endpoint@example.com")
    login = client.post(
        "/auth/login",
        json={"email": "freeze-endpoint@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    with SessionLocal() as db:
        s = db.get(UserStats, uid)
        s.streak_freezes_available = 1
        db.commit()

    response = client.get("/me/streak", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["streak_freezes_available"] == 1
    assert body["freeze_used_today"] is False


def test_streak_endpoint_reports_active_today(client):
    uid = _register(client, "active-today@example.com")
    login = client.post(
        "/auth/login",
        json={"email": "active-today@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Fresh account, no activity recorded yet.
    body = client.get("/me/streak", headers=headers).json()
    assert body["active_today"] is False

    # Yesterday's activity still isn't "today".
    with SessionLocal() as db:
        s = db.get(UserStats, uid)
        s.streak_days = 3
        s.last_activity_date = _today() - timedelta(days=1)
        db.commit()
    body = client.get("/me/streak", headers=headers).json()
    assert body["streak_days"] == 3
    assert body["active_today"] is False

    # Real activity today flips it (through record_activity, the same path
    # every answer endpoint uses — not a direct last_activity_date write).
    with SessionLocal() as db:
        record_activity(db, uid, 10)
        db.commit()
    body = client.get("/me/streak", headers=headers).json()
    assert body["active_today"] is True
