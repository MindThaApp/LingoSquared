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
ACCEPTED_ALGORITHMS = {"RS256", "ES256"}
# Tolerated clock skew between this server and the provider, in seconds.
CLOCK_SKEW_SECONDS = 60
# Gmail addresses are owned by Google; for any other domain Google's
# email_verified only means the address was verified at some point, so it
# is trusted for account linking only when the token carries a Workspace
# hosted-domain (hd) claim for that same domain.
GOOGLE_OWNED_EMAIL_DOMAINS = {"gmail.com", "googlemail.com"}

_JWKS_CACHE: dict[Provider, tuple[float, dict[str, Any]]] = {}


class SocialTokenError(Exception):
    pass


def clear_jwks_cache() -> None:
    _JWKS_CACHE.clear()


def fetch_jwks(provider: Provider) -> dict[str, Any]:
    url = GOOGLE_JWKS_URL if provider == "google" else APPLE_JWKS_URL
    response = httpx.get(url, timeout=3.0)
    response.raise_for_status()
    return response.json()


def _jwks_for(provider: Provider) -> dict[str, Any]:
    now = time.monotonic()
    cached = _JWKS_CACHE.get(provider)
    if cached and cached[0] > now:
        return cached[1]
    jwks = fetch_jwks(provider)
    _JWKS_CACHE[provider] = (now + JWKS_CACHE_SECONDS, jwks)
    return jwks


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
    """The client sends SHA-256(raw nonce) to the provider, which embeds it
    in the ID token, and sends the raw nonce here. Required for Apple; for
    Google it is checked whenever either side carries one."""
    claimed = claims.get("nonce")
    if provider == "apple" and not raw_nonce:
        raise SocialTokenError("Missing nonce")
    if raw_nonce is None and claimed is None:
        return
    if not raw_nonce or not isinstance(claimed, str):
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
        jwk = _find_jwk(_jwks_for(provider), kid)
        key = jwt.PyJWK.from_dict(jwk).key
        claims = jwt.decode(
            id_token,
            key=key,
            algorithms=[alg],
            audience=list(audiences),
            leeway=CLOCK_SKEW_SECONDS,
            options={"require": ["aud", "exp", "iat", "iss", "sub"]},
        )
    except SocialTokenError:
        raise
    except Exception as exc:
        raise SocialTokenError("Invalid social token") from exc

    issuer = claims.get("iss")
    subject = claims.get("sub")
    if not isinstance(issuer, str) or not _issuer_allowed(provider, issuer):
        raise SocialTokenError("Invalid issuer")
    if not isinstance(subject, str) or not subject:
        raise SocialTokenError("Missing subject")
    _check_nonce(provider, claims, nonce)
    return claims


def email_is_verified(provider: Provider, claims: dict[str, Any]) -> bool:
    value = claims.get("email_verified")
    if provider == "google":
        return value is True
    if isinstance(value, str):
        return value.lower() == "true"
    return value is True


def email_is_trusted_for_linking(provider: Provider, claims: dict[str, Any], email: str) -> bool:
    """Whether this provider vouches for the user owning `email`, which is
    what linking to an existing account by email requires."""
    if not email_is_verified(provider, claims):
        return False
    if provider == "apple":
        return True
    domain = email.rsplit("@", 1)[-1].lower()
    if domain in GOOGLE_OWNED_EMAIL_DOMAINS:
        return True
    hosted_domain = claims.get("hd")
    return isinstance(hosted_domain, str) and hosted_domain.lower() == domain
