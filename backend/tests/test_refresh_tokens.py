import hashlib
from datetime import timedelta

from sqlalchemy import func, select

from app.api.router import utc_now
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import RefreshToken
from app.scripts.prune_refresh_tokens import main as prune_refresh_tokens_main


def register(client, email):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Refresh"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_header(access_token):
    return {"Authorization": f"Bearer {access_token}"}


def test_refresh_issues_new_working_access_token(client):
    first = register(client, "refresh-success@example.com")

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )

    assert refreshed.status_code == 200, refreshed.text
    body = refreshed.json()
    assert body["expires_in"] == 1800
    assert body["access_token"] != first["access_token"]
    assert body["refresh_token"] != first["refresh_token"]

    me = client.get("/auth/me", headers=auth_header(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "refresh-success@example.com"


def test_refresh_uses_digest_lookup_and_rejects_legacy_row(client):
    first = register(client, "refresh-digest@example.com")
    user_id = decode_token(first["access_token"])

    with SessionLocal() as db:
        token = db.scalar(select(RefreshToken).where(RefreshToken.user_id == user_id))
        assert token.token_sha256 == hashlib.sha256(first["refresh_token"].encode()).hexdigest()
        token.token_sha256 = None
        db.commit()

    refreshed = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert refreshed.status_code == 401
    assert refreshed.json()["error"]["code"] == "invalid_refresh_token"


def test_refresh_rotation_invalidates_old_refresh_token(client):
    first = register(client, "refresh-rotation@example.com")
    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text

    reused = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )

    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "refresh_token_reused"


def test_refresh_reuse_detection_revokes_all_user_refresh_tokens(client):
    first = register(client, "refresh-reuse@example.com")
    login = client.post(
        "/auth/login",
        json={"email": "refresh-reuse@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text

    rotated = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert rotated.status_code == 200, rotated.text
    user_id = decode_token(rotated.json()["access_token"])

    reused = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "refresh_token_reused"

    with SessionLocal() as db:
        unrevoked = db.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    assert unrevoked == 0

    second_session = client.post(
        "/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert second_session.status_code == 401
    assert second_session.json()["error"]["code"] == "refresh_token_reused"

    rotated_session = client.post(
        "/auth/refresh",
        json={"refresh_token": rotated.json()["refresh_token"]},
    )
    assert rotated_session.status_code == 401
    assert rotated_session.json()["error"]["code"] == "refresh_token_reused"


def test_expired_refresh_token_is_rejected(client):
    first = register(client, "refresh-expired@example.com")
    user_id = decode_token(first["access_token"])

    with SessionLocal() as db:
        token = db.scalar(
            select(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        token.expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )

    assert refreshed.status_code == 401
    assert refreshed.json()["error"]["code"] == "invalid_refresh_token"


def test_logout_revokes_presented_refresh_token(client):
    first = register(client, "refresh-logout@example.com")

    logout = client.post(
        "/auth/logout",
        json={"refresh_token": first["refresh_token"]},
    )
    assert logout.status_code == 204
    assert logout.content == b""

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert refreshed.status_code == 401
    assert refreshed.json()["error"]["code"] == "refresh_token_reused"


def _add_refresh_token(db, user_id, token_id, expires_at, revoked_at=None):
    db.add(
        RefreshToken(
            id=token_id,
            token_hash=f"not-used-{token_id}",
            token_sha256=None,
            user_id=user_id,
            issued_at=utc_now() - timedelta(days=20),
            expires_at=expires_at,
            revoked_at=revoked_at,
        )
    )


def test_login_and_refresh_prune_same_users_expired_and_old_revoked_rows(client):
    first = register(client, "refresh-prune-login@example.com")
    user_id = decode_token(first["access_token"])
    now = utc_now()
    with SessionLocal() as db:
        _add_refresh_token(db, user_id, "expired-login", now - timedelta(seconds=1))
        _add_refresh_token(
            db,
            user_id,
            "old-revoked-login",
            now + timedelta(days=30),
            now - timedelta(days=8),
        )
        _add_refresh_token(
            db,
            user_id,
            "recent-revoked-login",
            now + timedelta(days=30),
            now - timedelta(days=2),
        )
        db.commit()

    logged_in = client.post(
        "/auth/login",
        json={"email": "refresh-prune-login@example.com", "password": "password123"},
    )
    assert logged_in.status_code == 200, logged_in.text
    with SessionLocal() as db:
        rows = set(db.scalars(select(RefreshToken.id).where(RefreshToken.user_id == user_id)))
    assert "expired-login" not in rows
    assert "old-revoked-login" not in rows
    assert "recent-revoked-login" in rows

    new_token = logged_in.json()["refresh_token"]
    now = utc_now()
    with SessionLocal() as db:
        _add_refresh_token(db, user_id, "expired-refresh", now - timedelta(seconds=1))
        _add_refresh_token(
            db,
            user_id,
            "old-revoked-refresh",
            now + timedelta(days=30),
            now - timedelta(days=9),
        )
        db.commit()

    refreshed = client.post("/auth/refresh", json={"refresh_token": new_token})
    assert refreshed.status_code == 200, refreshed.text
    with SessionLocal() as db:
        rows = set(db.scalars(select(RefreshToken.id).where(RefreshToken.user_id == user_id)))
    assert "expired-refresh" not in rows
    assert "old-revoked-refresh" not in rows


def test_global_refresh_token_pruner_removes_only_expired_or_old_revoked(client, capsys):
    registered = register(client, "refresh-prune-global@example.com")
    user_id = decode_token(registered["access_token"])
    now = utc_now()
    with SessionLocal() as db:
        _add_refresh_token(db, user_id, "global-expired", now - timedelta(seconds=1))
        _add_refresh_token(
            db,
            user_id,
            "global-old-revoked",
            now + timedelta(days=10),
            now - timedelta(days=8),
        )
        _add_refresh_token(
            db,
            user_id,
            "global-recent-revoked",
            now + timedelta(days=10),
            now - timedelta(days=1),
        )
        db.commit()

    prune_refresh_tokens_main()
    assert capsys.readouterr().out == "Pruned 2 refresh token rows.\n"
    with SessionLocal() as db:
        remaining = set(db.scalars(select(RefreshToken.id).where(RefreshToken.user_id == user_id)))
    assert "global-expired" not in remaining
    assert "global-old-revoked" not in remaining
    assert "global-recent-revoked" in remaining
