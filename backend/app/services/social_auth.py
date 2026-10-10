import hashlib
import hmac
import time
from typing import Any, Literal

import httpx
import jwt


Provider = Literal["google", "apple"]

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
JWKS_CACHE_SECONDS = 300
# A token signed with a key id we have not seen may follow a provider key
# rotation, so it triggers a refetch, but at most this often per provider:
# anyone can send a made-up key id.
JWKS_REFETCH_MIN_SECONDS = 60
ACCEPTED_ALGORITHMS = {"RS256", "ES256"}
# Tolerated clock skew between this server and the provider, in seconds.
CLOCK_SKEW_SECONDS = 60
# Gmail addresses are owned by Google; for any other domain Google's
# email_verified only means the address was verified at some point, so it
# is trusted for account linking only when the token carries a Workspace
# hosted-domain (hd) claim for that same domain.
GOOGLE_OWNED_EMAIL_DOMAINS = {"gmail.com", "googlemail.com"}

_JWKS_CACHE: dict[Provider, tuple[float, dict[str, Any]]] = {}
_JWKS_LAST_FETCH: dict[Provider, float] = {}


class SocialTokenError(Exception):
    pass


class ProviderUnavailable(Exception):
    """The provider's signing keys could not be fetched (not the caller's fault)."""


def clear_jwks_cache() -> None:
    _JWKS_CACHE.clear()
    _JWKS_LAST_FETCH.clear()


def fetch_jwks(provider: Provider) -> dict[str, Any]:
    url = GOOGLE_JWKS_URL if provider == "google" else APPLE_JWKS_URL
    response = httpx.get(url, timeout=3.0)
    response.raise_for_status()
    return response.json()


def _refetch_jwks(provider: Provider) -> dict[str, Any]:
    now = time.monotonic()
    _JWKS_LAST_FETCH[provider] = now
    try:
        jwks = fetch_jwks(provider)
        if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
            raise ValueError("malformed JWKS")
    except Exception as exc:
        cached = _JWKS_CACHE.get(provider)
        if cached:
            # Keep using the last good key set rather than failing every
            # sign-in while the provider endpoint is briefly unreachable.
            return cached[1]
        raise ProviderUnavailable(f"Could not fetch {provider} signing keys") from exc
    _JWKS_CACHE[provider] = (now + JWKS_CACHE_SECONDS, jwks)
    return jwks


def _jwks_for(provider: Provider) -> dict[str, Any]:
    cached = _JWKS_CACHE.get(provider)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    return _refetch_jwks(provider)


def _signing_key(provider: Provider, kid: str) -> dict[str, Any]:
    try:
        return _find_jwk(_jwks_for(provider), kid)
    except SocialTokenError:
        last = _JWKS_LAST_FETCH.get(provider)
        if last is not None and time.monotonic() - last < JWKS_REFETCH_MIN_SECONDS:
            raise
        return _find_jwk(_refetch_jwks(provider), kid)


def _issuer_allowed(provider: Provider, issuer: str) -> bool:
    if provider == "google":
        return issuer in {"accounts.google.com", "https://accounts.google.com"}
    return issuer == "https://appleid.apple.com"


def _find_jwk(jwks: dict[str, Any], kid: str) -> dict[str, Any]:
    for jwk in jwks.get("keys", []):
        if jwk.get("kid") == kid:
            return jwk
    raise SocialTokenError("No matching signing key")


def nonce_digest(raw_nonce: str) -> str:
    return hashlib.sha256(raw_nonce.encode("utf-8")).hexdigest()


def _check_nonce(provider: Provider, claims: dict[str, Any], raw_nonce: str | None) -> None:
    """The client gets a raw nonce from POST /auth/social/nonce, sends its
    SHA-256 hex digest to the provider, which embeds it in the ID token, and
    sends the raw nonce here. Required for both providers. That it was
    issued by this server and is used only once is checked by the caller
    (app.api.router.consume_social_nonce)."""
    claimed = claims.get("nonce")
    if not raw_nonce:
        raise SocialTokenError("Missing nonce")
    if not isinstance(claimed, str):
        raise SocialTokenError("Nonce mismatch")
    if not hmac.compare_digest(claimed, nonce_digest(raw_nonce)):
        raise SocialTokenError("Nonce mismatch")


def verify_id_token(
    provider: Provider,
    id_token: str,
    audiences: set[str],
    nonce: str | None = None,
) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(id_token)
        kid = header.get("kid")
        alg = header.get("alg")
        if not kid or alg not in ACCEPTED_ALGORITHMS:
            raise SocialTokenError("Unsupported token header")
        jwk = _signing_key(provider, kid)
        key = jwt.PyJWK.from_dict(jwk).key
        claims = jwt.decode(
            id_token,
            key=key,
            algorithms=[alg],
            audience=list(audiences),
            leeway=CLOCK_SKEW_SECONDS,
            options={"require": ["aud", "exp", "iat", "iss", "sub"]},
        )
    except (SocialTokenError, ProviderUnavailable):
        raise
    except Exception as exc:
        raise SocialTokenError("Invalid social token") from exc

    issuer = claims.get("iss")
    subject = claims.get("sub")
    if not isinstance(issuer, str) or not _issuer_allowed(provider, issuer):
        raise SocialTokenError("Invalid issuer")
    if not isinstance(subject, str) or not subject:
        raise SocialTokenError("Missing subject")
    # A token issued to several audiences must name us as the party it was
    # issued to (Google's guidance); a present azp must always be one of us.
    authorized_party = claims.get("azp")
    token_audience = claims.get("aud")
    if authorized_party is not None and authorized_party not in audiences:
        raise SocialTokenError("Invalid authorized party")
    if isinstance(token_audience, list) and len(token_audience) > 1 and authorized_party is None:
        raise SocialTokenError("Missing authorized party")
    _check_nonce(provider, claims, nonce)
    return claims


def email_is_verified(provider: Provider, claims: dict[str, Any]) -> bool:
    value = claims.get("email_verified")
    if provider == "google":
        return value is True
    if isinstance(value, str):
        return value.lower() == "true"
    return value is True


APPLE_PRIVATE_RELAY_DOMAIN = "privaterelay.appleid.com"


def is_apple_private_relay(email: str) -> bool:
    return email.rsplit("@", 1)[-1].lower() == APPLE_PRIVATE_RELAY_DOMAIN


def email_is_trusted_for_linking(provider: Provider, claims: dict[str, Any], email: str) -> bool:
    """Whether this provider vouches for the user owning `email` today.

    It is necessary, not sufficient, for linking to an existing account by
    email: the router also never links into an account that has a password
    (registration does not verify email ownership).

    Apple: a private relay address is unique to this app and the Apple ID.
    Any other address Apple only verified when the Apple ID was set up, and
    may have changed hands since (a former employee's work address), which
    is why the password-account rule matters most for Apple.
    """
    if not email_is_verified(provider, claims):
        return False
    if provider == "apple":
        return True
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in GOOGLE_OWNED_EMAIL_DOMAINS:
        return True
    hosted_domain = claims.get("hd")
    return isinstance(hosted_domain, str) and hosted_domain.lower() == domain
