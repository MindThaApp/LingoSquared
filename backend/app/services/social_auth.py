import time
from typing import Any, Literal

import httpx
import jwt


Provider = Literal["google", "apple"]

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
JWKS_CACHE_SECONDS = 300
ACCEPTED_ALGORITHMS = {"RS256", "ES256"}

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


def verify_id_token(
    provider: Provider,
    id_token: str,
    audiences: set[str],
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
            options={"require": ["aud", "exp", "iss", "sub"]},
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
    return claims


def email_is_verified(provider: Provider, claims: dict[str, Any]) -> bool:
    value = claims.get("email_verified")
    if provider == "google":
        return value is True
    if isinstance(value, str):
        return value.lower() == "true"
    return value is True
