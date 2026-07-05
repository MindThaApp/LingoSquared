from datetime import time, timedelta
from zoneinfo import ZoneInfo

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import User
from app.services.progress import (
    activity_day_bounds,
    resolve_user_tz,
    valid_timezone_or_none,
)


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def test_valid_timezone_or_none_accepts_real_iana_zone():
    assert valid_timezone_or_none("Pacific/Kiritimati") == "Pacific/Kiritimati"


def test_valid_timezone_or_none_rejects_garbage():
    assert valid_timezone_or_none("not/a/real/zone") is None
    assert valid_timezone_or_none("") is None
    assert valid_timezone_or_none(None) is None


def test_resolve_user_tz_falls_back_to_utc():
    assert resolve_user_tz(None) == ZoneInfo("UTC")
    assert resolve_user_tz("garbage") == ZoneInfo("UTC")
    assert resolve_user_tz("Pacific/Kiritimati") == ZoneInfo("Pacific/Kiritimati")


def test_activity_day_bounds_respects_given_timezone():
    tz = ZoneInfo("Pacific/Kiritimati")
    start, end = activity_day_bounds("Pacific/Kiritimati")
    assert start.tzinfo == tz
    assert start.time() == time.min
    assert end - start == timedelta(days=1)


def test_activity_day_bounds_defaults_to_utc():
    start, _ = activity_day_bounds(None)
    assert start.tzinfo == ZoneInfo("UTC")


def test_register_persists_valid_client_timezone(client):
    email = "tz-user-1@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "timezone": "Pacific/Kiritimati",
        },
    )
    assert response.status_code == 201
    with SessionLocal() as db:
        u = db.get(User, decode_token(response.json()["access_token"]))
        assert u.timezone == "Pacific/Kiritimati"


def test_register_ignores_invalid_client_timezone(client):
    email = "tz-user-2@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "timezone": "not/a/real/zone",
        },
    )
    assert response.status_code == 201
    with SessionLocal() as db:
        u = db.get(User, decode_token(response.json()["access_token"]))
        assert u.timezone is None


def test_login_updates_timezone_when_it_changes(client):
    email = "tz-user-3@example.com"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "timezone": "Pacific/Kiritimati",
        },
    )
    login = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "password123",
            "timezone": "Etc/GMT+12",
        },
    )
    assert login.status_code == 200
    with SessionLocal() as db:
        u = db.get(User, decode_token(login.json()["access_token"]))
        assert u.timezone == "Etc/GMT+12"


def test_login_without_timezone_keeps_existing_value(client):
    email = "tz-user-4@example.com"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "timezone": "Pacific/Kiritimati",
        },
    )
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    with SessionLocal() as db:
        u = db.get(User, decode_token(login.json()["access_token"]))
        assert u.timezone == "Pacific/Kiritimati"
