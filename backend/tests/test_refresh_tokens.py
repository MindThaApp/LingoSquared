from datetime import timedelta

from sqlalchemy import func, select

from app.api.router import utc_now
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import RefreshToken


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
