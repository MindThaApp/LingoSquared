"""Sentry crash reporting for backend server errors.

Server errors are not learner-personal, so they are reported whenever
SENTRY_DSN is set -- but nothing identifying may leave the box. The
``scrub_event`` hook below is the single place that guarantees that: it
drops request bodies, cookies and auth headers, masks emails / tokens /
password-like fields, and removes learner free-text answers. Without a
DSN (tests, local runs) ``init_sentry`` does nothing at all.
"""
from __future__ import annotations

import re
from typing import Any

REDACTED = "[Filtered]"

# Keys whose values are never sent, matched case-insensitively as a
# substring of the key (so "x-auth-token" and "refreshToken" both hit).
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "email",
    "credential",
    "jwt",
    "session",
    # Learner free-text: exercise answers and typed/spoken responses,
    # feedback descriptions.
    "answer",
    "response_text",
    "transcript",
    "description",
    "free_text",
    "freetext",
    "user_input",
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]*")
_BEARER_RE = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=\-]{8,}")
_KV_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|token|secret|access_token|refresh_token|api_key)(=|:\s*)[^\s&,;\"']+"
)
_UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_DIGITS_RE = re.compile(r"\d+")


def _is_sensitive_key(key: Any) -> bool:
    k = str(key).lower()
    return any(part in k for part in _SENSITIVE_KEY_PARTS)


def scrub_string(value: str) -> str:
    value = _JWT_RE.sub(REDACTED, value)
    value = _BEARER_RE.sub(lambda m: f"{m.group(1)} {REDACTED}", value)
    value = _KV_SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", value)
    value = _EMAIL_RE.sub("[email]", value)
    return value


def scrub_value(value: Any, _depth: int = 0) -> Any:
    if _depth > 12:
        return REDACTED
    if isinstance(value, str):
        return scrub_string(value)
    if isinstance(value, dict):
        return {
            k: (REDACTED if _is_sensitive_key(k) else scrub_value(v, _depth + 1))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [scrub_value(v, _depth + 1) for v in value]
    return value


def _fingerprint_message(message: str) -> str:
    """Strip volatile ids/numbers so the same bug groups together."""
    return _DIGITS_RE.sub("N", _UUID_RE.sub("UUID", message))[:200]


def scrub_event(event: dict, hint: dict | None = None) -> dict | None:
    """Sentry ``before_send``: scrub in place-ish and set a stable fingerprint."""
    request = event.get("request")
    if isinstance(request, dict):
        # Bodies hold learner answers and credentials; cookies and query
        # strings can hold tokens. Keep method/url/route only.
        for key in ("data", "cookies", "query_string", "env"):
            request.pop(key, None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {
                k: (REDACTED if _is_sensitive_key(k) else scrub_value(v))
                for k, v in headers.items()
                if str(k).lower() not in {"x-forwarded-for", "x-real-ip"}
            }
        if isinstance(request.get("url"), str):
            request["url"] = scrub_string(request["url"])

    # Never identify the learner: keep at most an opaque id.
    user = event.get("user")
    if isinstance(user, dict):
        event["user"] = {"id": user["id"]} if "id" in user else {}

    event.pop("server_name", None)

    for section in ("extra", "contexts", "tags", "breadcrumbs", "exception", "logentry", "message", "threads"):
        if section in event:
            event[section] = scrub_value(event[section])

    # Stable grouping: exception type + route template, with ids/numbers
    # in the message normalised away, instead of whatever frames shifted.
    values = (event.get("exception") or {}).get("values") or []
    if values and not event.get("fingerprint"):
        last = values[-1]
        event["fingerprint"] = [
            str(last.get("type") or "Error"),
            _fingerprint_message(str(last.get("value") or "")),
            str(event.get("transaction") or ""),
        ]
    return event


def init_sentry(settings) -> bool:
    """Initialise the SDK iff a DSN is configured. Returns whether it did."""
    dsn = (getattr(settings, "sentry_dsn", "") or "").strip()
    if not dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        release=(settings.sentry_release or None),
        environment=settings.sentry_environment_name,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=0.0,
        before_send=scrub_event,
    )
    return True
