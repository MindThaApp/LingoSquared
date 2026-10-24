"""Sentry wiring: off without a DSN, and nothing identifying survives scrubbing."""
from types import SimpleNamespace
from unittest import mock

from app.core import sentry as sentry_mod
from app.core.config import Settings
from app.core.sentry import REDACTED, init_sentry, scrub_event


def _settings(**kw):
    return Settings(_env_file=None, **kw)


def test_no_dsn_means_sdk_never_initialised():
    # The test environment must never be able to send events.
    assert Settings(_env_file=None).sentry_dsn == ""
    with mock.patch("sentry_sdk.init") as init:
        assert init_sentry(_settings()) is False
        assert init_sentry(SimpleNamespace(sentry_dsn="   ")) is False
    init.assert_not_called()


def test_dsn_enables_sdk_with_pii_off_and_scrubber():
    s = _settings(sentry_dsn="https://key@example.invalid/1", sentry_release="abc123")
    with mock.patch("sentry_sdk.init") as init:
        assert init_sentry(s) is True
    kw = init.call_args.kwargs
    assert kw["send_default_pii"] is False
    assert kw["before_send"] is scrub_event
    assert kw["release"] == "abc123"
    assert kw["environment"] == "production.lan"
    assert kw["include_local_variables"] is False


def test_environment_defaults_from_app_env():
    assert _settings(app_env="dev").sentry_environment_name == "development"
    assert _settings(app_env="production").sentry_environment_name == "production.lan"
    assert _settings(sentry_environment="staging").sentry_environment_name == "staging"


def test_scrub_removes_credentials_bodies_and_free_text():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abcDEF123"
    event = {
        "request": {
            "url": "http://x/v1/auth/login?token=abc",
            "method": "POST",
            "data": {"email": "a@b.co", "password": "hunter2"},
            "cookies": {"sid": "1"},
            "query_string": "token=abc",
            "headers": {
                "Authorization": f"Bearer {jwt}",
                "Cookie": "sid=1",
                "Set-Cookie": "sid=2",
                "User-Agent": "UA",
                "X-Forwarded-For": "10.0.0.1",
            },
        },
        "user": {"id": 7, "email": "learner@example.com", "ip_address": "1.2.3.4", "username": "bob"},
        "extra": {"answer": "de kat", "user_answer": "x", "refresh_token": "r", "note": "ok"},
        "exception": {"values": [{"type": "ValueError", "value": f"bad mail learner@example.com token={jwt}"}]},
        "transaction": "/v1/lessons/{lesson_id}",
    }
    out = scrub_event(event)
    blob = repr(out)
    for leak in ("a@b.co", "hunter2", "learner@example.com", jwt, "1.2.3.4", "bob", "de kat", "sid=1", "10.0.0.1"):
        assert leak not in blob, leak
    assert out["request"]["headers"]["Authorization"] == REDACTED
    assert out["request"]["headers"]["Cookie"] == REDACTED
    assert out["request"]["headers"]["User-Agent"] == "UA"
    assert "data" not in out["request"] and "cookies" not in out["request"]
    assert out["user"] == {"id": 7}
    assert out["extra"]["note"] == "ok"
    assert "[email]" in out["exception"]["values"][0]["value"]


def test_fingerprint_is_stable_across_ids():
    def ev(n):
        return {
            "exception": {"values": [{"type": "KeyError", "value": f"item {n} missing"}]},
            "transaction": "/v1/items/{id}",
        }

    a, b = scrub_event(ev(12)), scrub_event(ev(9999))
    assert a["fingerprint"] == b["fingerprint"]
    assert a["fingerprint"][0] == "KeyError"
    assert a["fingerprint"][2] == "/v1/items/{id}"


def test_fingerprint_respects_existing():
    e = scrub_event({"exception": {"values": [{"type": "E", "value": "x"}]}, "fingerprint": ["custom"]})
    assert e["fingerprint"] == ["custom"]


def test_scrub_handles_odd_shapes():
    assert scrub_event({}) == {}
    assert sentry_mod.scrub_value(None) is None
