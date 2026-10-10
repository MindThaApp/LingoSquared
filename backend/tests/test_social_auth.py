import base64
import hashlib
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import func, select

from app.api.router import issue_social_nonce
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import SocialLoginNonce, User, UserIdentity, UserStats
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
    nonce: str | None = "issue",
    extra: dict | None = None,
    kid: str = "test-key",
):
    """Sign an ID token. By default it embeds a nonce freshly issued by the
    server (as POST /auth/social/nonce would); nonce=None leaves the claim
    out, any other string embeds that value."""
    if nonce == "issue":
        with SessionLocal() as db:
            nonce = issue_social_nonce(db)[0]
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
    signed = SignedToken(jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    ))
    signed.provider = provider
    signed.nonce = nonce
    return signed


class SignedToken(str):
    provider: str
    nonce: str | None


def request_body(token: SignedToken, **extra):
    """The request body a client sends for this token."""
    payload = {"provider": token.provider, "id_token": str(token)}
    if token.nonce is not None:
        payload["nonce"] = token.nonce
    payload.update(extra)
    return payload


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
        json=request_body(token, display_name="Google User"),
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
        json=request_body(token),
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
    )

    response = client.post(
        "/auth/social",
        json=request_body(token, display_name="Apple User"),
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
        json=request_body(token),
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
        json=request_body(token),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_verified_email_never_signs_in_to_a_password_account(
    client,
    configured_social,
    social_keys,
):
    # Pre-account hijacking: an attacker registers the victim's address
    # with a password of their choosing (registration does not verify
    # email). When the victim later continues with Google, their identity
    # must not be attached to the attacker's account.
    registered = client.post(
        "/auth/register",
        json={
            "email": "verified-link@gmail.com",
            "password": "attacker-pass-1",
            "display_name": "Attacker",
        },
    )
    assert registered.status_code == 201, registered.text
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-verified-link",
        audience="google-web",
        email="VERIFIED-LINK@gmail.com",
        email_verified=True,
    )

    response = client.post("/auth/social", json=request_body(token))

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "account_exists"
    assert "access_token" not in response.json()
    assert identity_count("google", "google-verified-link") == 0
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User).where(User.email == "verified-link@gmail.com")) == 1


def test_password_account_owner_links_from_inside_the_account(
    client,
    configured_social,
    social_keys,
):
    registered = client.post(
        "/auth/register",
        json={"email": "owner-links@gmail.com", "password": "password123"},
    )
    assert registered.status_code == 201, registered.text
    user_id = registered.json()["user"]["id"]
    link_token = make_id_token(
        social_keys,
        provider="google",
        subject="google-owner-links",
        audience="google-web",
        email="owner-links@gmail.com",
    )
    linked = client.post(
        "/auth/social/link",
        json=request_body(link_token, current_password="password123"),
        headers=auth_header(registered.json()["access_token"]),
    )
    assert linked.status_code == 200, linked.text

    # From then on Google signs in to that account.
    sign_in = make_id_token(
        social_keys,
        provider="google",
        subject="google-owner-links",
        audience="google-web",
        email="owner-links@gmail.com",
    )
    response = client.post("/auth/social", json=request_body(sign_in))
    assert response.status_code == 200, response.text
    assert response.json()["user"]["id"] == user_id


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
        json=request_body(token),
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
        json=request_body(first_token),
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
        json=request_body(second_token),
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
        json=request_body(token),
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
        json=request_body(token),
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
        json=request_body(token),
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
        response = client.post("/auth/social", json=request_body(token))
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "social_login_unavailable"
    finally:
        get_settings.cache_clear()


def test_social_login_requires_a_nonce(client, configured_social, social_keys):
    for provider, audience in (("apple", "apple-service"), ("google", "google-web")):
        token = make_id_token(
            social_keys,
            provider=provider,
            subject=f"{provider}-no-nonce",
            audience=audience,
            email=f"{provider}-no-nonce@gmail.com",
        )
        payload = request_body(token)
        del payload["nonce"]
        response = client.post("/auth/social", json=payload)
        assert response.status_code == 401, provider
        assert identity_count(provider, f"{provider}-no-nonce") == 0


def test_social_login_rejects_a_mismatched_nonce(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-bad-nonce",
        audience="apple-service",
        email="apple-bad-nonce@example.com",
    )
    with SessionLocal() as db:
        other_nonce = issue_social_nonce(db)[0]
    response = client.post("/auth/social", json=request_body(token, nonce=other_nonce))
    assert response.status_code == 401


def test_social_login_rejects_a_token_without_a_nonce_claim(client, configured_social, social_keys):
    for provider, audience in (("apple", "apple-service"), ("google", "google-web")):
        token = make_id_token(
            social_keys,
            provider=provider,
            subject=f"{provider}-unbound",
            audience=audience,
            email=f"{provider}-unbound@example.com",
            nonce=None,
        )
        with SessionLocal() as db:
            issued = issue_social_nonce(db)[0]
        response = client.post("/auth/social", json=request_body(token, nonce=issued))
        assert response.status_code == 401, provider


def test_social_login_rejects_a_nonce_the_server_never_issued(client, configured_social, social_keys):
    # The nonce matches the token, but this server never handed it out.
    for provider, audience in (("apple", "apple-service"), ("google", "google-web")):
        token = make_id_token(
            social_keys,
            provider=provider,
            subject=f"{provider}-self-made-nonce",
            audience=audience,
            email=f"{provider}-self-made@gmail.com",
            nonce=APPLE_NONCE,
        )
        response = client.post("/auth/social", json=request_body(token))
        assert response.status_code == 401, provider
        assert identity_count(provider, f"{provider}-self-made-nonce") == 0


def test_a_captured_sign_in_cannot_be_replayed(client, configured_social, social_keys):
    for provider, audience in (("apple", "apple-service"), ("google", "google-web")):
        token = make_id_token(
            social_keys,
            provider=provider,
            subject=f"{provider}-replayed",
            audience=audience,
            email=f"{provider}-replayed@gmail.com",
        )
        first = client.post("/auth/social", json=request_body(token))
        assert first.status_code == 200, first.text
        replayed = client.post("/auth/social", json=request_body(token))
        assert replayed.status_code == 401, provider
        assert replayed.json()["error"]["code"] == "invalid_credentials"


def test_an_expired_nonce_is_refused(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-stale-nonce",
        audience="google-web",
        email="stale-nonce@gmail.com",
    )
    with SessionLocal() as db:
        row = db.get(SocialLoginNonce, social_auth.nonce_digest(token.nonce))
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    response = client.post("/auth/social", json=request_body(token))
    assert response.status_code == 401


def test_nonce_endpoint_issues_single_use_nonces(client, configured_social):
    first = client.post("/auth/social/nonce")
    second = client.post("/auth/social/nonce")
    assert first.status_code == 200, first.text
    assert first.json()["expires_in"] == get_settings().social_nonce_ttl_seconds
    assert len(first.json()["nonce"]) >= 43
    assert first.json()["nonce"] != second.json()["nonce"]
    with SessionLocal() as db:
        stored = db.get(SocialLoginNonce, social_auth.nonce_digest(first.json()["nonce"]))
        assert stored is not None
        # Only the digest is stored.
        assert db.get(SocialLoginNonce, first.json()["nonce"]) is None


def test_nonce_rate_limit_has_its_own_ceiling(client, configured_social):
    from app.api.router import SOCIAL_NONCE_RATE_LIMIT

    settings = get_settings()
    assert SOCIAL_NONCE_RATE_LIMIT.limit == settings.social_nonce_rate_limit_max
    assert settings.social_nonce_rate_limit_max > settings.refresh_rate_limit_max
    for _ in range(settings.social_nonce_rate_limit_max):
        assert client.post("/auth/social/nonce").status_code == 200
    limited = client.post("/auth/social/nonce")
    assert limited.status_code == 429


def test_prune_removes_expired_nonces_only(client, configured_social):
    from app.scripts.prune_refresh_tokens import prune_social_nonces

    fresh = client.post("/auth/social/nonce").json()["nonce"]
    stale = client.post("/auth/social/nonce").json()["nonce"]
    with SessionLocal() as db:
        row = db.get(SocialLoginNonce, social_auth.nonce_digest(stale))
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
        assert prune_social_nonces(db) >= 1
        assert db.get(SocialLoginNonce, social_auth.nonce_digest(stale)) is None
        assert db.get(SocialLoginNonce, social_auth.nonce_digest(fresh)) is not None


def test_nonce_endpoint_is_off_with_the_flag(client, monkeypatch):
    monkeypatch.delenv("SOCIAL_SIGN_IN_ENABLED", raising=False)
    get_settings.cache_clear()
    try:
        response = client.post("/auth/social/nonce")
        assert response.status_code == 503
    finally:
        get_settings.cache_clear()


def test_social_login_rejects_wrong_issuer(client, configured_social, social_keys):
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-bad-iss",
        audience="google-web",
        email="bad-iss@gmail.com",
        extra={"iss": "https://evil.example.com"},
    )
    response = client.post("/auth/social", json=request_body(token))
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
    response = client.post("/auth/social", json=request_body(token))
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
    response = client.post("/auth/social", json=request_body(token))
    assert response.status_code == 200, response.text
    assert response.json()["user"]["id"] != registered.json()["user"]["id"]
    assert response.json()["user"]["email"].endswith("@social.lingosquared.example")


def test_google_hosted_domain_address_does_not_join_a_passwordless_account(client, configured_social, social_keys):
    # An account created through Apple (no password) with a verified
    # address; Google vouches for the same Workspace address via hd. Still
    # not linked: a new provider is connected only from inside the account.
    apple = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-ws-first",
        audience="apple-service",
        email="ws-user@example.net",
    )
    created = client.post("/auth/social", json=request_body(apple))
    assert created.status_code == 200, created.text
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-ws-hd",
        audience="google-web",
        email="ws-user@example.net",
        extra={"hd": "example.net"},
    )
    response = client.post("/auth/social", json=request_body(token))
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "account_exists"
    assert identity_count("google", "google-ws-hd") == 0


def test_google_hosted_domain_address_does_not_sign_in_to_a_password_account(client, configured_social, social_keys):
    registered = client.post(
        "/auth/register",
        json={"email": "ws-password@example.net", "password": "password123"},
    )
    assert registered.status_code == 201, registered.text
    token = make_id_token(
        social_keys,
        provider="google",
        subject="google-ws-password",
        audience="google-web",
        email="ws-password@example.net",
        extra={"hd": "example.net"},
    )
    response = client.post("/auth/social", json=request_body(token))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "account_exists"


@pytest.mark.parametrize(
    "email",
    ["former-staff@example.com", "relay-user@privaterelay.appleid.com"],
)
def test_apple_email_never_signs_in_to_a_password_account(client, configured_social, social_keys, email):
    # Apple verified a non-relay address only when the Apple ID was set up;
    # it may belong to someone else by now. Neither kind of Apple address
    # is enough to enter an account that has a password.
    registered = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert registered.status_code == 201, registered.text
    token = make_id_token(
        social_keys,
        provider="apple",
        subject=f"apple-pw-{email}",
        audience="apple-service",
        email=email,
    )
    response = client.post("/auth/social", json=request_body(token))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "account_exists"
    assert identity_count("apple", f"apple-pw-{email}") == 0


def test_email_never_joins_an_account_that_has_the_same_provider(
    client, configured_social, social_keys
):
    first = make_id_token(
        social_keys,
        provider="google",
        subject="google-dup-1",
        audience="google-web",
        email="dup-provider@gmail.com",
    )
    assert client.post("/auth/social", json=request_body(first)).status_code == 200
    second = make_id_token(
        social_keys,
        provider="google",
        subject="google-dup-2",
        audience="google-web",
        email="dup-provider@gmail.com",
    )
    response = client.post("/auth/social", json=request_body(second))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "account_exists"
    assert identity_count("google", "google-dup-2") == 0


def test_apple_email_never_joins_an_account_created_through_google(
    client, configured_social, social_keys
):
    # Probe from the R25 review: an account created through Google for
    # x@gmail.com, then an Apple sign-in carrying the same non-relay
    # address. The Apple ID's address may have changed hands since it was
    # set up, so it must not land in the Google user's account.
    google = make_id_token(
        social_keys,
        provider="google",
        subject="google-cross-provider-owner",
        audience="google-web",
        email="cross-provider@gmail.com",
    )
    created = client.post("/auth/social", json=request_body(google))
    assert created.status_code == 200, created.text
    apple = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-cross-provider-intruder",
        audience="apple-service",
        email="cross-provider@gmail.com",
    )
    response = client.post("/auth/social", json=request_body(apple))
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "account_exists"
    assert identity_count("apple", "apple-cross-provider-intruder") == 0
    with SessionLocal() as db:
        owners = db.scalar(
            select(func.count()).select_from(User).where(User.email == "cross-provider@gmail.com")
        )
    assert owners == 1


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
        json=request_body(token),
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
    later = make_id_token(
        social_keys,
        provider="google",
        subject="google-guest-convert",
        audience="google-web",
        email="Converted.Guest@gmail.com",
    )
    again = client.post("/auth/social", json=request_body(later))
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
    )
    linked = client.post(
        "/auth/social/link",
        json=request_body(token, display_name="Jo"),
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
        json=request_body(token),
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
        json=request_body(token),
        headers=auth_header(guest["access_token"]),
    )
    assert linked.status_code == 409
    assert linked.json()["error"]["code"] == "email_exists"
    assert identity_count("google", "google-guest-taken") == 0
    with SessionLocal() as db:
        user = db.get(User, guest["user"]["id"])
        assert user.email.startswith("guest-")
        assert user.password_hash is not None


def google_token(social_keys, subject, email):
    return make_id_token(
        social_keys,
        provider="google",
        subject=subject,
        audience="google-web",
        email=email,
    )


def register_password_account(client, email):
    response = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert response.status_code == 201, response.text
    return response.json()


def test_link_refuses_an_identity_owned_by_another_account(client, configured_social, social_keys):
    first = google_token(social_keys, "google-owned-elsewhere", "owned-elsewhere@gmail.com")
    assert client.post("/auth/social", json=request_body(first)).status_code == 200
    guest = register_guest(client)
    again = google_token(social_keys, "google-owned-elsewhere", "owned-elsewhere@gmail.com")
    linked = client.post(
        "/auth/social/link",
        json=request_body(again),
        headers=auth_header(guest["access_token"]),
    )
    assert linked.status_code == 409
    assert linked.json()["error"]["code"] == "identity_in_use"


def test_link_is_idempotent_for_the_same_account(client, configured_social, social_keys):
    guest = register_guest(client)
    headers = auth_header(guest["access_token"])
    first = client.post(
        "/auth/social/link",
        json=request_body(google_token(social_keys, "google-idempotent-link", "idempotent-link@gmail.com")),
        headers=headers,
    )
    second = client.post(
        "/auth/social/link",
        json=request_body(google_token(social_keys, "google-idempotent-link", "idempotent-link@gmail.com")),
        headers=headers,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert identity_count("google", "google-idempotent-link") == 1


def test_password_account_can_link_and_keeps_its_email_and_password(
    client, configured_social, social_keys
):
    registered = register_password_account(client, "keeps-password@example.com")
    token = google_token(social_keys, "google-keeps-password", "other-address@gmail.com")
    linked = client.post(
        "/auth/social/link",
        json=request_body(token, current_password="password123"),
        headers=auth_header(registered["access_token"]),
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["email"] == "keeps-password@example.com"
    login = client.post(
        "/auth/login",
        json={"email": "keeps-password@example.com", "password": "password123"},
    )
    assert login.status_code == 200


@pytest.mark.parametrize("current_password", [None, "wrong-password"])
def test_password_account_link_needs_the_current_password(
    client, configured_social, social_keys, current_password
):
    # A stolen access token alone must not be enough to attach the
    # thief's own Google account for permanent access.
    registered = register_password_account(client, f"link-needs-password-{current_password}@example.com")
    subject = f"google-thief-{current_password}"
    token = google_token(social_keys, subject, f"thief-{current_password}@gmail.com")
    extra = {} if current_password is None else {"current_password": current_password}
    linked = client.post(
        "/auth/social/link",
        json=request_body(token, **extra),
        headers=auth_header(registered["access_token"]),
    )
    assert linked.status_code == 403
    assert linked.json()["error"]["code"] == "reauthentication_required"
    assert identity_count("google", subject) == 0


def test_passwordless_account_cannot_link_with_an_access_token_alone(
    client, configured_social, social_keys
):
    created = client.post(
        "/auth/social",
        json=request_body(google_token(social_keys, "google-passwordless-owner", "passwordless-owner@gmail.com")),
    )
    assert created.status_code == 200, created.text
    apple = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-passwordless-thief",
        audience="apple-service",
        email="thief@privaterelay.appleid.com",
    )
    linked = client.post(
        "/auth/social/link",
        json=request_body(apple),
        headers=auth_header(created.json()["access_token"]),
    )
    assert linked.status_code == 403
    assert linked.json()["error"]["code"] == "reauthentication_required"
    assert identity_count("apple", "apple-passwordless-thief") == 0


def test_link_refuses_a_second_identity_of_the_same_provider(client, configured_social, social_keys):
    registered = register_password_account(client, "second-identity@example.com")
    headers = auth_header(registered["access_token"])
    first = google_token(social_keys, "google-link-one", "link-one@gmail.com")
    assert client.post(
        "/auth/social/link",
        json=request_body(first, current_password="password123"),
        headers=headers,
    ).status_code == 200
    second = google_token(social_keys, "google-link-two", "link-two@gmail.com")
    response = client.post(
        "/auth/social/link",
        json=request_body(second, current_password="password123"),
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_already_linked"


def test_link_requires_a_signed_in_account(client, configured_social, social_keys):
    token = google_token(social_keys, "google-anon-link", "anon-link@gmail.com")
    response = client.post("/auth/social/link", json=request_body(token))
    assert response.status_code == 401


def reauth_body(token: SignedToken):
    return {"provider": token.provider, "id_token": str(token), "nonce": token.nonce}


def apple_token(social_keys, subject, email):
    return make_id_token(
        social_keys,
        provider="apple",
        subject=subject,
        audience="apple-service",
        email=email,
    )


def test_wrong_password_does_not_use_up_the_link_nonce(client, configured_social, social_keys):
    registered = register_password_account(client, "typo-password@example.com")
    headers = auth_header(registered["access_token"])
    token = google_token(social_keys, "google-typo-password", "typo-password@gmail.com")

    typo = client.post(
        "/auth/social/link",
        json=request_body(token, current_password="password12"),
        headers=headers,
    )
    assert typo.status_code == 403
    assert typo.json()["error"]["code"] == "reauthentication_required"
    with SessionLocal() as db:
        assert db.get(SocialLoginNonce, social_auth.nonce_digest(token.nonce)) is not None

    # Same provider sign-in, corrected password: no second popup needed.
    linked = client.post(
        "/auth/social/link",
        json=request_body(token, current_password="password123"),
        headers=headers,
    )
    assert linked.status_code == 200, linked.text
    assert identity_count("google", "google-typo-password") == 1

    # The nonce is now used up, so the request cannot be replayed.
    with SessionLocal() as db:
        assert db.get(SocialLoginNonce, social_auth.nonce_digest(token.nonce)) is None
    replayed = client.post(
        "/auth/social/link",
        json=request_body(token, current_password="password123"),
        headers=headers,
    )
    assert replayed.status_code == 403
    assert replayed.json()["error"]["code"] == "invalid_credentials"


def test_link_with_an_invalid_token_is_403_not_401(client, configured_social, social_keys):
    # A 401 would make the client throw away a perfectly good session.
    registered = register_password_account(client, "bad-link-token@example.com")
    token = google_token(social_keys, "google-bad-link-token", "bad-link-token@gmail.com")
    response = client.post(
        "/auth/social/link",
        json=request_body(token, nonce="not-the-nonce-0123456789", current_password="password123"),
        headers=auth_header(registered["access_token"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_passwordless_account_links_a_second_provider_after_signing_in_again(
    client, configured_social, social_keys
):
    created = client.post(
        "/auth/social",
        json=request_body(google_token(social_keys, "google-reauth-owner", "reauth-owner@gmail.com")),
    )
    assert created.status_code == 200, created.text
    assert created.json()["user"]["id"]
    headers = auth_header(created.json()["access_token"])
    me = client.get("/auth/me", headers=headers)
    assert me.json()["has_password"] is False

    reauth = google_token(social_keys, "google-reauth-owner", "reauth-owner@gmail.com")
    apple = apple_token(social_keys, "apple-reauth-second", "reauth-second@privaterelay.appleid.com")
    linked = client.post(
        "/auth/social/link",
        json=request_body(apple, reauth=reauth_body(reauth)),
        headers=headers,
    )
    assert linked.status_code == 200, linked.text
    assert sorted(identity["provider"] for identity in linked.json()["identities"]) == ["apple", "google"]
    # Both nonces are used up.
    with SessionLocal() as db:
        assert db.get(SocialLoginNonce, social_auth.nonce_digest(apple.nonce)) is None
        assert db.get(SocialLoginNonce, social_auth.nonce_digest(reauth.nonce)) is None

    # The new provider now signs in to the same account.
    again = client.post(
        "/auth/social",
        json=request_body(apple_token(social_keys, "apple-reauth-second", "reauth-second@privaterelay.appleid.com")),
    )
    assert again.status_code == 200, again.text
    assert again.json()["user"]["id"] == created.json()["user"]["id"]


def test_reauth_must_be_a_provider_linked_to_this_account(client, configured_social, social_keys):
    victim = client.post(
        "/auth/social",
        json=request_body(google_token(social_keys, "google-reauth-victim", "reauth-victim@gmail.com")),
    )
    assert victim.status_code == 200, victim.text
    # The holder of the victim's access token signs in with their own
    # Google account, which is not linked to the victim's account.
    outsider = google_token(social_keys, "google-reauth-outsider", "reauth-outsider@gmail.com")
    apple = apple_token(social_keys, "apple-reauth-outsider", "reauth-outsider@privaterelay.appleid.com")
    response = client.post(
        "/auth/social/link",
        json=request_body(apple, reauth=reauth_body(outsider)),
        headers=auth_header(victim.json()["access_token"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "reauthentication_required"
    assert identity_count("apple", "apple-reauth-outsider") == 0
    # Nothing was used up by the refused attempt.
    with SessionLocal() as db:
        assert db.get(SocialLoginNonce, social_auth.nonce_digest(apple.nonce)) is not None


def test_reauth_with_an_invalid_token_is_refused(client, configured_social, social_keys):
    created = client.post(
        "/auth/social",
        json=request_body(google_token(social_keys, "google-reauth-bad", "reauth-bad@gmail.com")),
    )
    assert created.status_code == 200, created.text
    stale = google_token(social_keys, "google-reauth-bad", "reauth-bad@gmail.com")
    apple = apple_token(social_keys, "apple-reauth-bad", "reauth-bad@privaterelay.appleid.com")
    reauth = reauth_body(stale)
    reauth["nonce"] = "some-other-nonce-0123456789"
    response = client.post(
        "/auth/social/link",
        json=request_body(apple, reauth=reauth),
        headers=auth_header(created.json()["access_token"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert identity_count("apple", "apple-reauth-bad") == 0


def test_reauth_cannot_be_replayed(client, configured_social, social_keys):
    created = client.post(
        "/auth/social",
        json=request_body(google_token(social_keys, "google-reauth-replay", "reauth-replay@gmail.com")),
    )
    assert created.status_code == 200, created.text
    headers = auth_header(created.json()["access_token"])
    reauth = google_token(social_keys, "google-reauth-replay", "reauth-replay@gmail.com")
    first = client.post(
        "/auth/social/link",
        json=request_body(
            apple_token(social_keys, "apple-reauth-replay-1", "replay-1@privaterelay.appleid.com"),
            reauth=reauth_body(reauth),
        ),
        headers=headers,
    )
    assert first.status_code == 200, first.text
    unlinked = client.post("/auth/social/unlink", json={"provider": "apple"}, headers=headers)
    assert unlinked.status_code == 200, unlinked.text
    second = client.post(
        "/auth/social/link",
        json=request_body(
            apple_token(social_keys, "apple-reauth-replay-2", "replay-2@privaterelay.appleid.com"),
            reauth=reauth_body(reauth),
        ),
        headers=headers,
    )
    assert second.status_code == 403
    assert second.json()["error"]["code"] == "invalid_credentials"
    assert identity_count("apple", "apple-reauth-replay-2") == 0


def test_me_reports_whether_the_account_has_a_password(client, configured_social, social_keys):
    registered = register_password_account(client, "has-password@example.com")
    me = client.get("/auth/me", headers=auth_header(registered["access_token"]))
    assert me.json()["has_password"] is True
    guest = register_guest(client)
    me = client.get("/auth/me", headers=auth_header(guest["access_token"]))
    assert me.json()["has_password"] is False


# --- Client configuration ---------------------------------------------------


def test_social_config_lists_nothing_while_the_flag_is_off(client, monkeypatch):
    monkeypatch.delenv("SOCIAL_SIGN_IN_ENABLED", raising=False)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_IDS", "google-web")
    monkeypatch.setenv("APPLE_AUDIENCE_IDS", "apple-service")
    get_settings.cache_clear()
    try:
        response = client.get("/auth/social/config")
        assert response.status_code == 200
        assert response.json() == {"providers": []}
    finally:
        get_settings.cache_clear()


def test_social_config_lists_the_configured_providers(client, configured_social):
    response = client.get("/auth/social/config")
    assert response.status_code == 200
    assert response.json() == {"providers": ["google", "apple"]}


def test_social_config_leaves_out_a_provider_without_audiences(client, monkeypatch):
    monkeypatch.setenv("SOCIAL_SIGN_IN_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_IDS", "google-web")
    monkeypatch.setenv("APPLE_AUDIENCE_IDS", "")
    get_settings.cache_clear()
    try:
        assert client.get("/auth/social/config").json() == {"providers": ["google"]}
    finally:
        get_settings.cache_clear()


# --- Unlinking --------------------------------------------------------------


def test_unlink_is_off_with_the_flag(client, configured_social, social_keys, monkeypatch):
    registered = register_password_account(client, "unlink-flag-off@example.com")
    headers = auth_header(registered["access_token"])
    token = google_token(social_keys, "google-unlink-flag-off", "unlink-flag-off@gmail.com")
    assert client.post(
        "/auth/social/link",
        json=request_body(token, current_password="password123"),
        headers=headers,
    ).status_code == 200
    monkeypatch.setenv("SOCIAL_SIGN_IN_ENABLED", "false")
    get_settings.cache_clear()
    response = client.post(
        "/auth/social/unlink",
        json={"provider": "google", "current_password": "password123"},
        headers=headers,
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "social_login_unavailable"
    assert identity_count("google", "google-unlink-flag-off") == 1


def test_password_account_can_unlink_with_its_password(client, configured_social, social_keys):
    registered = register_password_account(client, "unlink-owner@example.com")
    headers = auth_header(registered["access_token"])
    token = google_token(social_keys, "google-unlink-me", "unlink-me@gmail.com")
    assert client.post(
        "/auth/social/link",
        json=request_body(token, current_password="password123"),
        headers=headers,
    ).status_code == 200

    refused = client.post("/auth/social/unlink", json={"provider": "google"}, headers=headers)
    assert refused.status_code == 403
    assert identity_count("google", "google-unlink-me") == 1

    unlinked = client.post(
        "/auth/social/unlink",
        json={"provider": "google", "current_password": "password123"},
        headers=headers,
    )
    assert unlinked.status_code == 200, unlinked.text
    assert unlinked.json()["identities"] == []
    assert identity_count("google", "google-unlink-me") == 0

    # The Google account no longer signs in to it.
    again = client.post(
        "/auth/social",
        json=request_body(google_token(social_keys, "google-unlink-me", "unlink-me@gmail.com")),
    )
    assert again.status_code == 200, again.text
    assert again.json()["user"]["id"] != registered["user"]["id"]


def test_unlink_never_removes_the_last_way_to_sign_in(client, configured_social, social_keys):
    created = client.post(
        "/auth/social",
        json=request_body(google_token(social_keys, "google-only-method", "only-method@gmail.com")),
    )
    assert created.status_code == 200, created.text
    headers = auth_header(created.json()["access_token"])
    response = client.post("/auth/social/unlink", json={"provider": "google"}, headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_login_method"
    assert identity_count("google", "google-only-method") == 1


def test_passwordless_account_with_two_providers_can_drop_one(client, configured_social, social_keys):
    apple = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-two-methods",
        audience="apple-service",
        email="two-methods@gmail.com",
    )
    created = client.post("/auth/social", json=request_body(apple))
    assert created.status_code == 200, created.text
    headers = auth_header(created.json()["access_token"])
    again = make_id_token(
        social_keys,
        provider="apple",
        subject="apple-two-methods",
        audience="apple-service",
        email="two-methods@gmail.com",
    )
    google = client.post(
        "/auth/social/link",
        json=request_body(
            google_token(social_keys, "google-two-methods", "two-methods@gmail.com"),
            reauth=reauth_body(again),
        ),
        headers=headers,
    )
    assert google.status_code == 200, google.text

    dropped = client.post("/auth/social/unlink", json={"provider": "apple"}, headers=headers)
    assert dropped.status_code == 200, dropped.text
    assert [identity["provider"] for identity in dropped.json()["identities"]] == ["google"]
    last = client.post("/auth/social/unlink", json={"provider": "google"}, headers=headers)
    assert last.status_code == 409


def test_unlink_of_a_provider_that_is_not_linked_is_404(client, configured_social, social_keys):
    registered = register_password_account(client, "unlink-none@example.com")
    response = client.post(
        "/auth/social/unlink",
        json={"provider": "apple", "current_password": "password123"},
        headers=auth_header(registered["access_token"]),
    )
    assert response.status_code == 404


# --- Provider keys, audiences and concurrency -------------------------------


def test_unknown_key_id_refetches_the_key_set_once(client, configured_social, social_keys, monkeypatch):
    rotated_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = rotated_key.public_key().public_numbers()
    rotated_jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": "rotated-key",
        "alg": "RS256",
        "n": _b64url_int(numbers.n),
        "e": _b64url_int(numbers.e),
    }
    published = {"keys": []}
    fetches = []

    def fake_fetch(provider):
        fetches.append(provider)
        return {"keys": list(published["keys"])}

    monkeypatch.setattr(social_auth, "fetch_jwks", fake_fetch)
    social_auth.clear_jwks_cache()

    # The key set is cached before the provider publishes the new key.
    early = make_id_token(
        rotated_key, provider="google", subject="google-rotated", audience="google-web",
        email="rotated@gmail.com", kid="rotated-key",
    )
    assert client.post("/auth/social", json=request_body(early)).status_code == 401
    assert len(fetches) == 1

    # Published now; a refetch inside the minimum interval is not allowed,
    # so an attacker cannot make us fetch on every request.
    published["keys"].append(rotated_jwk)
    blocked = make_id_token(
        rotated_key, provider="google", subject="google-rotated", audience="google-web",
        email="rotated@gmail.com", kid="rotated-key",
    )
    assert client.post("/auth/social", json=request_body(blocked)).status_code == 401
    assert len(fetches) == 1

    # Once the interval has passed, the unknown kid triggers one refetch.
    monkeypatch.setattr(social_auth, "JWKS_REFETCH_MIN_SECONDS", 0)
    token = make_id_token(
        rotated_key, provider="google", subject="google-rotated", audience="google-web",
        email="rotated@gmail.com", kid="rotated-key",
    )
    response = client.post("/auth/social", json=request_body(token))
    assert response.status_code == 200, response.text
    assert len(fetches) == 2


def test_provider_key_fetch_failure_is_503(client, configured_social, monkeypatch):
    def failing_fetch(provider):
        raise social_auth.httpx.ConnectError("unreachable")

    monkeypatch.setattr(social_auth, "fetch_jwks", failing_fetch)
    social_auth.clear_jwks_cache()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = make_id_token(
        key, provider="google", subject="google-offline", audience="google-web", email="offline@gmail.com",
    )
    response = client.post("/auth/social", json=request_body(token))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "social_provider_unavailable"
    social_auth.clear_jwks_cache()


def test_multiple_audiences_need_an_authorized_party_of_ours(client, configured_social, social_keys):
    def multi(subject, extra):
        return make_id_token(
            social_keys, provider="google", subject=subject, audience="google-web",
            email=f"{subject}@gmail.com", extra={"aud": ["google-web", "someone-else"], **extra},
        )

    missing = client.post("/auth/social", json=request_body(multi("google-azp-missing", {})))
    assert missing.status_code == 401
    foreign = client.post("/auth/social", json=request_body(multi("google-azp-foreign", {"azp": "someone-else"})))
    assert foreign.status_code == 401
    ours = client.post("/auth/social", json=request_body(multi("google-azp-ours", {"azp": "google-web"})))
    assert ours.status_code == 200, ours.text


def test_concurrent_first_sign_in_does_not_500(client, configured_social, social_keys):
    # Another request is creating the account for this identity right now
    # (inserted, not yet committed). Ours waits on the unique key, fails,
    # and must then return the account the other request created.
    with SessionLocal() as other:
        user = User(email="race-first@gmail.com", password_hash=None, display_name="Race", is_admin=False)
        other.add(user)
        other.flush()
        other.add(UserStats(user_id=user.id, total_xp=0, streak_days=0, last_activity_date=None, daily_goal=20))
        other.add(UserIdentity(user_id=user.id, provider="google", provider_subject="google-race"))
        other.flush()
        token = google_token(social_keys, "google-race", "race-first@gmail.com")
        result = {}

        def sign_in():
            result["response"] = client.post("/auth/social", json=request_body(token))

        racer = threading.Thread(target=sign_in)
        racer.start()
        time.sleep(1.0)
        assert "response" not in result
        other.commit()
        user_id = user.id
    racer.join(timeout=30)

    response = result["response"]
    assert response.status_code == 200, response.text
    assert response.json()["user"]["id"] == user_id
    assert identity_count("google", "google-race") == 1
