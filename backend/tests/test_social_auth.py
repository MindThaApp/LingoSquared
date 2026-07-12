import base64
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import User, UserIdentity
from app.services import social_auth


def _b64url_int(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.fixture
def social_keys(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": "test-key",
        "alg": "RS256",
        "n": _b64url_int(public_numbers.n),
        "e": _b64url_int(public_numbers.e),
    }

    def fake_fetch(provider):
        return {"keys": [jwk]}

    monkeypatch.setattr(social_auth, "fetch_jwks", fake_fetch)
    social_auth.clear_jwks_cache()
    yield private_key
    social_auth.clear_jwks_cache()


@pytest.fixture
def configured_social(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_IDS", "google-web,google-ios")
    monkeypatch.setenv("APPLE_AUDIENCE_IDS", "apple-service,apple-bundle")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def make_id_token(
    private_key,
    *,
    provider: str,
    subject: str,
    audience: str,
    email: str,
    email_verified=True,
    expires_delta: timedelta = timedelta(minutes=10),
):
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "https://accounts.google.com"
        if provider == "google"
        else "https://appleid.apple.com",
        "sub": subject,
        "aud": audience,
        "iat": now,
        "exp": now + expires_delta,
        "email": email,
    }
    if provider == "google":
        claims["email_verified"] = email_verified
    else:
        claims["email_verified"] = "true" if email_verified else "false"
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def identity_count(provider: str, subject: str) -> int:
    with SessionLocal() as db:
        return db.scalar(
            select(func.count())
            .select_from(UserIdentity)
            .where(
                UserIdentity.provider == provider,
                UserIdentity.provider_subject == subject,
            )
        )


def auth_header(access_token: str):
    return {"Authorization": f"Bearer {access_token}"}


def test_google_social_login_happy_path(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-sub-1",
        audience="google-web",
        email="google-social@example.com",
    )

    response = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token, "display_name": "Google User"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["refresh_token"]
    assert body["user"]["email"] == "google-social@example.com"
    assert body["user"]["display_name"] == "Google User"
    assert identity_count("google", "google-sub-1") == 1


def test_social_refresh_token_rotates_through_existing_refresh_endpoint(
    client,
    configured_social,
    social_keys,
):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-refresh",
        audience="google-web",
        email="google-refresh@example.com",
    )
    social = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token},
    )
    assert social.status_code == 200, social.text

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": social.json()["refresh_token"]},
    )

    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["refresh_token"] != social.json()["refresh_token"]
    me = client.get("/auth/me", headers=auth_header(refreshed.json()["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "google-refresh@example.com"


def test_apple_social_login_happy_path_with_string_email_verified(
    client,
    configured_social,
    social_keys,
):
    token = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-sub-1",
        audience="apple-service",
        email="apple-social@example.com",
        email_verified=True,
    )

    response = client.post(
        "/auth/social",
        json={"provider": "apple", "id_token": token, "display_name": "Apple User"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["email"] == "apple-social@example.com"
    assert body["user"]["display_name"] == "Apple User"
    assert identity_count("apple", "apple-sub-1") == 1


def test_social_login_rejects_unallowed_audience(
    client,
    configured_social,
    social_keys,
):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-bad-aud",
        audience="not-configured",
        email="bad-aud@example.com",
    )

    response = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_social_login_rejects_expired_token(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-expired",
        audience="google-web",
        email="expired@example.com",
        expires_delta=timedelta(minutes=-1),
    )

    response = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_verified_email_links_existing_password_account(
    client,
    configured_social,
    social_keys,
):
    registered = client.post(
        "/auth/register",
        json={
            "email": "verified-link@example.com",
            "password": "password123",
            "display_name": "Existing User",
        },
    )
    assert registered.status_code == 201, registered.text
    existing_user_id = registered.json()["user"]["id"]
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-verified-link",
        audience="google-web",
        email="VERIFIED-LINK@example.com",
        email_verified=True,
    )

    response = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token},
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["id"] == existing_user_id
    assert response.json()["user"]["display_name"] == "Existing User"
    with SessionLocal() as db:
        identity = db.get(UserIdentity, ("google", "google-verified-link"))
        assert identity.user_id == existing_user_id


def test_unverified_email_creates_instead_of_linking(
    client,
    configured_social,
    social_keys,
):
    registered = client.post(
        "/auth/register",
        json={"email": "unverified-link@example.com", "password": "password123"},
    )
    assert registered.status_code == 201, registered.text
    existing_user_id = registered.json()["user"]["id"]
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-unverified",
        audience="google-web",
        email="unverified-link@example.com",
        email_verified=False,
    )

    response = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token},
    )

    assert response.status_code == 200, response.text
    new_user_id = response.json()["user"]["id"]
    assert new_user_id != existing_user_id
    with SessionLocal() as db:
        identity = db.get(UserIdentity, ("google", "google-unverified"))
        assert identity.user_id == new_user_id


def test_existing_identity_row_is_reused(client, configured_social, social_keys):
    first_token = make_id_token(
        social_keys,
        provider="google",
        subject="google-reuse",
        audience="google-web",
        email="reuse-first@example.com",
    )
    first = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": first_token},
    )
    assert first.status_code == 200, first.text
    user_id = first.json()["user"]["id"]
    second_token = make_id_token(
        social_keys,
        provider="google",
        subject="google-reuse",
        audience="google-web",
        email="reuse-second@example.com",
    )

    second = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": second_token},
    )

    assert second.status_code == 200, second.text
    assert second.json()["user"]["id"] == user_id
    assert second.json()["user"]["email"] == "reuse-first@example.com"
    assert identity_count("google", "google-reuse") == 1


def test_null_password_hash_login_returns_invalid_credentials(
    client,
    configured_social,
    social_keys,
):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-null-password",
        audience="google-web",
        email="null-password@example.com",
    )
    social = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token},
    )
    assert social.status_code == 200, social.text

    password_login = client.post(
        "/auth/login",
        json={"email": "null-password@example.com", "password": "password123"},
    )

    assert password_login.status_code == 401
    assert password_login.json()["error"]["code"] == "invalid_credentials"
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "null-password@example.com"))
        assert user.password_hash is None


def test_social_login_returns_503_when_provider_unconfigured(
    client,
    monkeypatch,
    social_keys,
):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_IDS", "")
    monkeypatch.setenv("APPLE_AUDIENCE_IDS", "apple-service")
    get_settings.cache_clear()
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-unconfigured",
        audience="google-web",
        email="unconfigured@example.com",
    )

    response = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "social_login_unavailable"
    get_settings.cache_clear()


def test_auth_me_includes_public_identities(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-me",
        audience="google-web",
        email="me-social@example.com",
    )
    social = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token},
    )
    assert social.status_code == 200, social.text
    access_token = social.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert me.status_code == 200, me.text
    body = me.json()
    assert body["identities"][0]["provider"] == "google"
    assert "created_at" in body["identities"][0]
    assert "provider_subject" not in body["identities"][0]
    assert "email" not in body["identities"][0]
