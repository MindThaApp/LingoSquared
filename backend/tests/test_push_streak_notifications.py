"""POST /admin/push/notify-streaks-at-risk — the evening "your streak
ends tonight" trigger an external cron fires (see
scripts/trigger_streak_notifications.sh).

Web push isn't configured in the test environment (no VAPID keys), so
push delivery itself is faked at the app.services.push module boundary —
the router imports that module (not the individual functions), so
monkeypatching module attributes is exactly what the endpoint calls.
These tests exercise the real selection logic: who gets notified, who
doesn't, and that "today" is the user's own timezone's today.

The endpoint scans ALL user_stats rows and the test DB is shared across
the session's test files, so assertions check membership of this file's
own users in the captured send list, never exact totals.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import app.services.push as push_service
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import UserStats


def _register(client, email):
    response = client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 201
    return decode_token(response.json()["access_token"])


def _set_stats(uid, streak_days, last_activity_date, user_timezone=None):
    with SessionLocal() as db:
        s = db.get(UserStats, uid)
        s.streak_days = streak_days
        s.last_activity_date = last_activity_date
        if user_timezone is not None:
            from app.models import User

            db.get(User, uid).timezone = user_timezone
        db.commit()


def _fake_push(monkeypatch):
    """Pretend push is configured and capture every send instead of
    hitting a real push service. Returns the capture list of
    (user_id, title, body) tuples."""
    sends = []

    def fake_send(db, user_id, title, body, url="/"):
        sends.append((user_id, title, body))
        return 1  # one subscription "delivered"

    monkeypatch.setattr(push_service, "push_configured", lambda: True)
    monkeypatch.setattr(push_service, "send_push_to_user", fake_send)
    return sends


def _utc_today():
    # A user with no stored timezone resolves to UTC (resolve_user_tz).
    return datetime.now(timezone.utc).date()


def test_inactive_user_with_streak_is_notified(client, admin, monkeypatch):
    uid = _register(client, "streak-push-inactive@example.com")
    _set_stats(uid, streak_days=3, last_activity_date=_utc_today() - timedelta(days=1))
    sends = _fake_push(monkeypatch)

    response = client.post("/admin/push/notify-streaks-at-risk", headers=admin)
    assert response.status_code == 200
    data = response.json()
    assert data["notified_users"] >= 1
    assert data["notifications_sent"] >= data["notified_users"]

    mine = [s for s in sends if s[0] == uid]
    assert len(mine) == 1
    _, title, body = mine[0]
    assert title == "Your streak is at risk"
    # The copy names the actual streak length.
    assert "3-day streak" in body
    assert "ends tonight" in body


def test_user_already_active_today_is_not_notified(client, admin, monkeypatch):
    uid = _register(client, "streak-push-active@example.com")
    _set_stats(uid, streak_days=5, last_activity_date=_utc_today())
    sends = _fake_push(monkeypatch)

    response = client.post("/admin/push/notify-streaks-at-risk", headers=admin)
    assert response.status_code == 200
    assert [s for s in sends if s[0] == uid] == []


def test_user_with_zero_streak_is_not_notified(client, admin, monkeypatch):
    # Nothing worth protecting: streak_days == 0, regardless of activity.
    uid = _register(client, "streak-push-zero@example.com")
    _set_stats(uid, streak_days=0, last_activity_date=_utc_today() - timedelta(days=1))
    sends = _fake_push(monkeypatch)

    response = client.post("/admin/push/notify-streaks-at-risk", headers=admin)
    assert response.status_code == 200
    assert [s for s in sends if s[0] == uid] == []


def test_lapsed_streak_is_not_notified(client, admin, monkeypatch):
    uid = _register(client, "streak-push-lapsed@example.com")
    _set_stats(uid, streak_days=8, last_activity_date=_utc_today() - timedelta(days=3))
    sends = _fake_push(monkeypatch)

    response = client.post("/admin/push/notify-streaks-at-risk", headers=admin)
    assert response.status_code == 200
    assert [s for s in sends if s[0] == uid] == []


def test_today_is_the_users_own_timezone_today(client, admin, monkeypatch):
    # "Active today" must be judged in the USER's timezone, not the
    # server's/UTC (same day boundary record_activity() uses).
    # Pacific/Kiritimati (UTC+14) is the timezone most often on a
    # different calendar date from UTC; a user whose last activity is
    # their own local today is safe and must NOT be notified — even at
    # moments when that local date isn't UTC's date.
    tz = "Pacific/Kiritimati"
    uid = _register(client, "streak-push-kiritimati@example.com")
    local_today = datetime.now(ZoneInfo(tz)).date()
    _set_stats(uid, streak_days=7, last_activity_date=local_today, user_timezone=tz)
    sends = _fake_push(monkeypatch)

    response = client.post("/admin/push/notify-streaks-at-risk", headers=admin)
    assert response.status_code == 200
    assert [s for s in sends if s[0] == uid] == []


def test_503_when_push_not_configured(client, admin):
    # No VAPID keys in the test env and nothing monkeypatched: the
    # endpoint must refuse honestly, same as notify-due-reviews.
    response = client.post("/admin/push/notify-streaks-at-risk", headers=admin)
    assert response.status_code == 503
    # This app's global HTTPException handler wraps detail under "error",
    # not FastAPI's default "detail" key — see app/main.py.
    assert response.json()["error"]["code"] == "push_not_configured"


def test_requires_admin(client, auth):
    response = client.post("/admin/push/notify-streaks-at-risk", headers=auth)
    assert response.status_code == 403
