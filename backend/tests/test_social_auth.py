import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import User, UserIdentity, UserStats
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
    monkeypatch.setenv("SOCIAL_SIGN_IN_ENABLED", "true")
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
    nonce: str | None = None,
    extra: dict | None = None,
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
    if nonce is not None:
        claims["nonce"] = hashlib.sha256(nonce.encode()).hexdigest()
    claims.update(extra or {})
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


APPLE_NONCE = "raw-nonce-0123456789abcdef"


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
        email="google-social@gmail.com",
    )

    response = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token, "display_name": "Google User"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["refresh_token"]
    assert body["user"]["email"] == "google-social@gmail.com"
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
        email="google-refresh@gmail.com",
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
    assert me.json()["email"] == "google-refresh@gmail.com"


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
        nonce=APPLE_NONCE,
    )

    response = client.post(
        "/auth/social",
        json={
            "provider": "apple",
            "id_token": token,
            "display_name": "Apple User",
            "nonce": APPLE_NONCE,
        },
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
            "email": "verified-link@gmail.com",
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
        email="VERIFIED-LINK@gmail.com",
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
        json={"email": "unverified-link@gmail.com", "password": "password123"},
    )
    assert registered.status_code == 201, registered.text
    existing_user_id = registered.json()["user"]["id"]
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-unverified",
        audience="google-web",
        email="unverified-link@gmail.com",
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
        email="reuse-first@gmail.com",
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
        email="reuse-second@gmail.com",
    )

    second = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": second_token},
    )

    assert second.status_code == 200, second.text
    assert second.json()["user"]["id"] == user_id
    assert second.json()["user"]["email"] == "reuse-first@gmail.com"
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
        email="null-password@gmail.com",
    )
    social = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token},
    )
    assert social.status_code == 200, social.text

    password_login = client.post(
        "/auth/login",
        json={"email": "null-password@gmail.com", "password": "password123"},
    )

    assert password_login.status_code == 401
    assert password_login.json()["error"]["code"] == "invalid_credentials"
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "null-password@gmail.com"))
        assert user.password_hash is None


def test_social_login_returns_503_when_provider_unconfigured(
    client,
    monkeypatch,
    social_keys,
):
    monkeypatch.setenv("SOCIAL_SIGN_IN_ENABLED", "true")
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
        email="me-social@gmail.com",
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


# --- Feature flag, nonce and issuer checks --------------------------------


def test_social_login_is_off_unless_the_flag_is_set(client, monkeypatch, social_keys):
    monkeypatch.delenv("SOCIAL_SIGN_IN_ENABLED", raising=False)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_IDS", "google-web")
    get_settings.cache_clear()
    try:
        token = make_id_token(
            social_keys,
            provider="google",
            subject="google-flag-off",
            audience="google-web",
            email="flag-off@gmail.com",
        )
        response = client.post("/auth/social", json={"provider": "google", "id_token": token})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "social_login_unavailable"
    finally:
        get_settings.cache_clear()


def test_apple_requires_a_nonce(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-no-nonce",
        audience="apple-service",
        email="apple-no-nonce@example.com",
        nonce=APPLE_NONCE,
    )
    response = client.post("/auth/social", json={"provider": "apple", "id_token": token})
    assert response.status_code == 401
    assert identity_count("apple", "apple-no-nonce") == 0


def test_apple_rejects_a_mismatched_nonce(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-bad-nonce",
        audience="apple-service",
        email="apple-bad-nonce@example.com",
        nonce=APPLE_NONCE,
    )
    response = client.post(
        "/auth/social",
        json={"provider": "apple", "id_token": token, "nonce": "some-other-nonce-value"},
    )
    assert response.status_code == 401


def test_apple_rejects_a_token_without_a_nonce_claim(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-unbound",
        audience="apple-service",
        email="apple-unbound@example.com",
    )
    response = client.post(
        "/auth/social",
        json={"provider": "apple", "id_token": token, "nonce": APPLE_NONCE},
    )
    assert response.status_code == 401


def test_google_nonce_is_checked_when_present(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-nonce",
        audience="google-web",
        email="google-nonce@gmail.com",
        nonce=APPLE_NONCE,
    )
    missing = client.post("/auth/social", json={"provider": "google", "id_token": token})
    assert missing.status_code == 401
    ok = client.post(
        "/auth/social",
        json={"provider": "google", "id_token": token, "nonce": APPLE_NONCE},
    )
    assert ok.status_code == 200, ok.text


def test_social_login_rejects_wrong_issuer(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-bad-iss",
        audience="google-web",
        email="bad-iss@gmail.com",
        extra={"iss": "https://evil.example.com"},
    )
    response = client.post("/auth/social", json={"provider": "google", "id_token": token})
    assert response.status_code == 401


def test_social_login_rejects_token_signed_by_another_key(client, configured_social, social_keys):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_id_token(
        other_key,
        provider="google",
        subject="google-forged",
        audience="google-web",
        email="forged@gmail.com",
    )
    response = client.post("/auth/social", json={"provider": "google", "id_token": token})
    assert response.status_code == 401
    assert identity_count("google", "google-forged") == 0


# --- Linking by email ------------------------------------------------------


def test_google_non_gmail_address_without_hosted_domain_does_not_link(
    client, configured_social, social_keys
):
    registered = client.post(
        "/auth/register",
        json={"email": "corp-user@example.org", "password": "password123"},
    )
    assert registered.status_code == 201, registered.text
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-corp-nohd",
        audience="google-web",
        email="corp-user@example.org",
    )
    response = client.post("/auth/social", json={"provider": "google", "id_token": token})
    assert response.status_code == 200, response.text
    assert response.json()["user"]["id"] != registered.json()["user"]["id"]
    assert response.json()["user"]["email"].endswith("@social.lingosquared.example")


def test_google_hosted_domain_address_links(client, configured_social, social_keys):
    registered = client.post(
        "/auth/register",
        json={"email": "ws-user@example.net", "password": "password123"},
    )
    assert registered.status_code == 201, registered.text
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-ws-hd",
        audience="google-web",
        email="ws-user@example.net",
        extra={"hd": "example.net"},
    )
    response = client.post("/auth/social", json={"provider": "google", "id_token": token})
    assert response.status_code == 200, response.text
    assert response.json()["user"]["id"] == registered.json()["user"]["id"]


def test_email_link_refuses_a_second_identity_of_the_same_provider(
    client, configured_social, social_keys
):
    first = make_id_token(
        social_keys,
        provider="google",
        subject="google-dup-1",
        audience="google-web",
        email="dup-provider@gmail.com",
    )
    assert client.post("/auth/social", json={"provider": "google", "id_token": first}).status_code == 200
    second = make_id_token(
        social_keys,
        provider="google",
        subject="google-dup-2",
        audience="google-web",
        email="dup-provider@gmail.com",
    )
    response = client.post("/auth/social", json={"provider": "google", "id_token": second})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_already_linked"


# --- Linking to the signed-in account / guest conversion ------------------


def register_guest(client):
    email = f"guest-{uuid.uuid4()}@example.com"
    response = client.post(
        "/auth/register",
        json={"email": email, "password": str(uuid.uuid4()), "display_name": "Guesty"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def give_progress(user_id, xp):
    with SessionLocal() as db:
        stats = db.get(UserStats, user_id)
        stats.total_xp = xp
        stats.streak_days = 3
        db.commit()


def test_guest_converts_to_google_account_and_keeps_progress(
    client, configured_social, social_keys
):
    guest = register_guest(client)
    guest_id = guest["user"]["id"]
    give_progress(guest_id, 420)
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-guest-convert",
        audience="google-web",
        email="Converted.Guest@gmail.com",
    )

    linked = client.post(
        "/auth/social/link",
        json={"provider": "google", "id_token": token},
        headers=auth_header(guest["access_token"]),
    )

    assert linked.status_code == 200, linked.text
    body = linked.json()
    assert body["id"] == guest_id
    assert body["email"] == "converted.guest@gmail.com"
    assert body["display_name"] == "Guesty"
    assert [identity["provider"] for identity in body["identities"]] == ["google"]
    with SessionLocal() as db:
        user = db.get(User, guest_id)
        assert user.password_hash is None
        assert db.get(UserStats, guest_id).total_xp == 420

    # A later Google sign-in on another device lands in the same account.
    again = client.post("/auth/social", json={"provider": "google", "id_token": token})
    assert again.status_code == 200, again.text
    assert again.json()["user"]["id"] == guest_id
    xp = client.get("/me/xp", headers=auth_header(again.json()["access_token"]))
    assert xp.status_code == 200, xp.text
    assert xp.json()["total_xp"] == 420


def test_guest_converts_to_apple_private_relay_account(client, configured_social, social_keys):
    guest = register_guest(client)
    token = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-guest-convert",
        audience="apple-service",
        email="abc123@privaterelay.appleid.com",
        nonce=APPLE_NONCE,
    )
    linked = client.post(
        "/auth/social/link",
        json={"provider": "apple", "id_token": token, "nonce": APPLE_NONCE, "display_name": "Jo"},
        headers=auth_header(guest["access_token"]),
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["email"] == "abc123@privaterelay.appleid.com"
    assert linked.json()["display_name"] == "Jo"


def test_guest_with_unverified_email_gets_a_synthetic_address(client, configured_social, social_keys):
    guest = register_guest(client)
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-guest-unverified",
        audience="google-web",
        email="not-verified@gmail.com",
        email_verified=False,
    )
    linked = client.post(
        "/auth/social/link",
        json={"provider": "google", "id_token": token},
        headers=auth_header(guest["access_token"]),
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["email"].endswith("@social.lingosquared.example")
    assert not linked.json()["email"].startswith("guest-")


def test_guest_conversion_refuses_an_email_owned_by_another_account(
    client, configured_social, social_keys
):
    owner = client.post(
        "/auth/register",
        json={"email": "taken-by-owner@gmail.com", "password": "password123"},
    )
    assert owner.status_code == 201, owner.text
    guest = register_guest(client)
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-guest-taken",
        audience="google-web",
        email="taken-by-owner@gmail.com",
    )
    linked = client.post(
        "/auth/social/link",
        json={"provider": "google", "id_token": token},
        headers=auth_header(guest["access_token"]),
    )
    assert linked.status_code == 409
    assert linked.json()["error"]["code"] == "email_exists"
    assert identity_count("google", "google-guest-taken") == 0
    with SessionLocal() as db:
        user = db.get(User, guest["user"]["id"])
        assert user.email.startswith("guest-")
        assert user.password_hash is not None


def test_link_refuses_an_identity_owned_by_another_account(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-owned-elsewhere",
        audience="google-web",
        email="owned-elsewhere@gmail.com",
    )
    assert client.post("/auth/social", json={"provider": "google", "id_token": token}).status_code == 200
    guest = register_guest(client)
    linked = client.post(
        "/auth/social/link",
        json={"provider": "google", "id_token": token},
        headers=auth_header(guest["access_token"]),
    )
    assert linked.status_code == 409
    assert linked.json()["error"]["code"] == "identity_in_use"


def test_link_is_idempotent_for_the_same_account(client, configured_social, social_keys):
    guest = register_guest(client)
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-idempotent-link",
        audience="google-web",
        email="idempotent-link@gmail.com",
    )
    headers = auth_header(guest["access_token"])
    first = client.post("/auth/social/link", json={"provider": "google", "id_token": token}, headers=headers)
    second = client.post("/auth/social/link", json={"provider": "google", "id_token": token}, headers=headers)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert identity_count("google", "google-idempotent-link") == 1


def test_password_account_can_link_and_keeps_its_email_and_password(
    client, configured_social, social_keys
):
    registered = client.post(
        "/auth/register",
        json={"email": "keeps-password@example.com", "password": "password123"},
    )
    assert registered.status_code == 201, registered.text
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-keeps-password",
        audience="google-web",
        email="other-address@gmail.com",
    )
    linked = client.post(
        "/auth/social/link",
        json={"provider": "google", "id_token": token},
        headers=auth_header(registered.json()["access_token"]),
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["email"] == "keeps-password@example.com"
    login = client.post(
        "/auth/login",
        json={"email": "keeps-password@example.com", "password": "password123"},
    )
    assert login.status_code == 200


def test_link_refuses_a_second_identity_of_the_same_provider(client, configured_social, social_keys):
    guest = register_guest(client)
    headers = auth_header(guest["access_token"])
    first = make_id_token(
        social_keys,
        provider="google",
        subject="google-link-one",
        audience="google-web",
        email="link-one@gmail.com",
    )
    assert client.post("/auth/social/link", json={"provider": "google", "id_token": first}, headers=headers).status_code == 200
    second = make_id_token(
        social_keys,
        provider="google",
        subject="google-link-two",
        audience="google-web",
        email="link-two@gmail.com",
    )
    response = client.post("/auth/social/link", json={"provider": "google", "id_token": second}, headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_already_linked"


def test_link_requires_a_signed_in_account(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-anon-link",
        audience="google-web",
        email="anon-link@gmail.com",
    )
    response = client.post("/auth/social/link", json={"provider": "google", "id_token": token})
    assert response.status_code == 401
