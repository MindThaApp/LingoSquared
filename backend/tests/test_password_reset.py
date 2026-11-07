import logging
import os
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.api import router as router_module
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import PasswordResetToken, User
from app.services import email as email_service


@pytest.fixture
def mail(monkeypatch):
    """Enable a fake provider and capture (to, token) instead of sending."""
    sent = []
    settings = get_settings()
    monkeypatch.setattr(settings, "email_provider", "log")
    monkeypatch.setattr(router_module, "send_password_reset", lambda s, to, token: sent.append((to, token)))
    return sent


def register(client, password="password123"):
    email = f"rs-{os.urandom(4).hex()}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": password, "display_name": "Rs"})
    assert r.status_code == 201, r.text
    return r.json()


def request(client, email):
    return client.post("/auth/password-reset/request", json={"email": email})


def confirm(client, token, pw="brandnewpass1"):
    return client.post("/auth/password-reset/confirm", json={"token": token, "new_password": pw})


def test_request_same_response_for_known_unknown_and_disabled(client, mail, monkeypatch):
    s = register(client)
    known = request(client, s["user"]["email"])
    unknown = request(client, "nobody-here@example.com")
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"status": "ok"}
    assert [to for to, _ in mail] == [s["user"]["email"]]
    monkeypatch.setattr(get_settings(), "email_provider", "")
    mail.clear()
    off = request(client, s["user"]["email"])
    assert off.json() == known.json()
    assert mail == []


def test_confirm_sets_password_revokes_sessions_and_is_single_use(client, mail):
    s = register(client)
    request(client, s["user"]["email"])
    token = mail[0][1]
    r = confirm(client, token)
    assert r.status_code == 200, r.text
    assert client.post("/auth/login", json={"email": s["user"]["email"], "password": "password123"}).status_code == 401
    assert client.post("/auth/login", json={"email": s["user"]["email"], "password": "brandnewpass1"}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": r.json()["refresh_token"]}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": s["refresh_token"]}).status_code == 401
    again = confirm(client, token, "anotherpass12")
    assert again.status_code == 400
    assert again.json()["error"]["code"] == "invalid_reset_token"


def test_token_stored_hashed_and_newer_request_voids_older(client, mail):
    s = register(client)
    request(client, s["user"]["email"])
    request(client, s["user"]["email"])
    old, new = mail[0][1], mail[1][1]
    with SessionLocal() as db:
        rows = db.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == s["user"]["id"])).all()
        assert len(rows) == 2
        assert all(old not in r.token_sha256 and new not in r.token_sha256 for r in rows)
    assert confirm(client, old).status_code == 400
    assert confirm(client, new).status_code == 200


def test_expired_and_garbage_tokens_rejected(client, mail):
    s = register(client)
    request(client, s["user"]["email"])
    token = mail[0][1]
    with SessionLocal() as db:
        row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == s["user"]["id"]))
        row.expires_at = row.expires_at - timedelta(days=1)
        db.commit()
    assert confirm(client, token).status_code == 400
    assert confirm(client, "garbage").status_code == 400
    assert client.post("/auth/login", json={"email": s["user"]["email"], "password": "password123"}).status_code == 200


def test_confirm_enforces_password_strength(client, mail):
    s = register(client)
    request(client, s["user"]["email"])
    assert confirm(client, mail[0][1], "short").status_code == 422
    assert confirm(client, mail[0][1]).status_code == 200


def test_guest_and_passwordless_accounts_get_no_token(client, mail):
    s = register(client)
    with SessionLocal() as db:
        u = db.get(User, s["user"]["id"])
        u.password_hash = None
        db.commit()
    assert request(client, s["user"]["email"]).status_code == 200
    assert mail == []


def test_request_rate_limited_per_ip_and_per_email(client, mail):
    s = register(client)
    for _ in range(5):
        assert request(client, s["user"]["email"]).status_code == 200
    # 4th+ request for the same address is silently dropped, not mailed.
    assert len(mail) == 3
    r = request(client, s["user"]["email"])
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "password_reset_rate_limited"


def test_log_provider_never_logs_token_in_production(caplog):
    class S:
        email_provider = "log"
        password_reset_base_url = "https://x.test"
        password_reset_ttl_seconds = 3600
    s = S()
    s.app_env = "production"
    with caplog.at_level(logging.INFO):
        email_service.send_password_reset(s, "a@example.com", "SECRETTOKEN")
    assert "SECRETTOKEN" not in caplog.text
    s.app_env = "test"
    with caplog.at_level(logging.INFO):
        email_service.send_password_reset(s, "a@example.com", "SECRETTOKEN")
    assert "SECRETTOKEN" in caplog.text
