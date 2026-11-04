import os

from app.api import router as router_module


def register(client, email=None, password="password123"):
    email = email or f"pw-{os.urandom(4).hex()}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": password, "display_name": "Pw"})
    assert r.status_code == 201, r.text
    return r.json()


def hdr(session):
    return {"Authorization": f"Bearer {session['access_token']}"}


def change(client, session, current, new):
    return client.post("/auth/password", headers=hdr(session), json={"current_password": current, "new_password": new})


def test_change_password_success_swaps_login_and_returns_session(client):
    s = register(client)
    r = change(client, s, "password123", "brandnewpass1")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["refresh_token"] and body["refresh_token"] != s["refresh_token"]
    assert client.post("/auth/login", json={"email": s["user"]["email"], "password": "password123"}).status_code == 401
    assert client.post("/auth/login", json={"email": s["user"]["email"], "password": "brandnewpass1"}).status_code == 200
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}).status_code == 200


def test_change_password_revokes_other_sessions_but_not_the_new_one(client):
    s = register(client)
    other = client.post("/auth/login", json={"email": s["user"]["email"], "password": "password123"}).json()
    r = change(client, s, "password123", "brandnewpass1")
    assert r.status_code == 200
    # New session first: presenting a revoked token afterwards trips reuse
    # detection, which would (correctly) revoke the whole family.
    assert client.post("/auth/refresh", json={"refresh_token": r.json()["refresh_token"]}).status_code == 200
    for old in (s, other):
        assert client.post("/auth/refresh", json={"refresh_token": old["refresh_token"]}).status_code == 401


def test_change_password_wrong_current_is_403_and_changes_nothing(client):
    s = register(client)
    r = change(client, s, "wrongpassword", "brandnewpass1")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "invalid_current_password"
    assert client.post("/auth/login", json={"email": s["user"]["email"], "password": "password123"}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": s["refresh_token"]}).status_code == 200


def test_change_password_enforces_signup_strength_rules(client):
    s = register(client)
    assert change(client, s, "password123", "short").status_code == 422
    assert change(client, s, "password123", "x" * 129).status_code == 422
    assert change(client, s, "password123", "password123").status_code == 400


def test_change_password_requires_authentication(client):
    r = client.post("/auth/password", json={"current_password": "a", "new_password": "brandnewpass1"})
    assert r.status_code == 401


def test_change_password_unavailable_for_guest_accounts(client):
    g = register(client, email="guest-abc123@example.com")
    r = change(client, g, "password123", "brandnewpass1")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "password_change_unavailable"


def test_change_password_unavailable_for_passwordless_accounts(client):
    s = register(client)
    from app.db.session import SessionLocal
    from app.models import User
    with SessionLocal() as db:
        u = db.get(User, s["user"]["id"])
        u.password_hash = None
        db.commit()
    r = change(client, s, "password123", "brandnewpass1")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "password_change_unavailable"


def test_change_password_is_rate_limited_and_counts_failures(client, monkeypatch):
    s = register(client)
    monkeypatch.setattr(router_module.LOGIN_RATE_LIMIT, "limit", 2)
    assert change(client, s, "bad-one-1", "brandnewpass1").status_code == 403
    assert change(client, s, "bad-two-2", "brandnewpass1").status_code == 403
    r = change(client, s, "password123", "brandnewpass1")
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "login_rate_limited"
