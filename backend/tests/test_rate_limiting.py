"""Rate limiting on the highest-value endpoints, 2026-07-06 security
hardening item — both of tonight's security passes (see
`docs/BUILD_LOG.md`) flagged "no rate limiting anywhere" as acceptable
for a small invite-only beta but worth having before wider exposure.

Covers: `/auth/login` (brute-force protection, per-IP), `/auth/register`
(registration-abuse prevention, per-IP), and the three answer-submission
endpoints (`/exercises/{id}/answer`, `/reviews/{id}/answer`,
`/practice/items/{id}/answer` — the same resource-exhaustion-adjacent
surface `test_security_payload_bounds.py` already bounds payload size
on), keyed per-account since those are already authenticated.

The "actually trips" tests monkeypatch each limiter's `.limit` down to a
small number rather than depending on (or needing hundreds of real HTTP
round-trips to reach) the real configured limits in `app/api/router.py`
- this proves the mechanism works independent of exactly how the real
limits get tuned. The `reset_rate_limits` autouse fixture in conftest.py
clears all limiters' state before every test, so none of this leaks
between tests (or interferes with the many register/login/answer calls
the rest of the existing suite already makes).
"""
from sqlalchemy import select

from app.api import router as router_module
from app.db.session import SessionLocal
from app.models import Exercise, ExerciseType


def seeded_exercise_id():
    # Must be a "translation"-type exercise specifically: these tests only
    # care about rate-limit behavior, not answer correctness, and submit a
    # fixed plain-string response ("some answer") regardless of what the
    # exercise actually is - unlike `.order_by(Exercise.id)` alone (picking
    # whichever real exercise happens to sort first by its random UUID),
    # which can and did pick a `flashcard` exercise, whose handler 422s on
    # anything other than exactly "known"/"unknown" - a real, observed
    # flake (2026-07-07), not hypothetical: adding one more exercise
    # elsewhere in the suite shifted which UUID sorts first and tripped
    # it. `translation` accepts any string response with no shape
    # requirements, so it's always compatible here.
    with SessionLocal() as db:
        return db.scalar(
            select(Exercise.id)
            .where(Exercise.type == ExerciseType.translation)
            .order_by(Exercise.id)
        )


# --- /auth/login ---

def test_login_rate_limit_returns_429_after_limit_exceeded(client, monkeypatch):
    monkeypatch.setattr(router_module.LOGIN_RATE_LIMIT, "limit", 3)
    email = "ratelimit-login@example.com"
    assert client.post("/auth/register", json={"email": email, "password": "password123"}).status_code == 201

    for _ in range(3):
        r = client.post("/auth/login", json={"email": email, "password": "password123"})
        assert r.status_code == 200

    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "login_rate_limited"
    assert r.json()["error"]["retry_after_seconds"] >= 1


def test_login_rate_limit_also_counts_failed_attempts(client, monkeypatch):
    # Brute-force protection specifically means WRONG-password guesses
    # must count against the limit too, not just successful logins.
    monkeypatch.setattr(router_module.LOGIN_RATE_LIMIT, "limit", 3)
    email = "ratelimit-brute@example.com"
    assert client.post("/auth/register", json={"email": email, "password": "password123"}).status_code == 201

    for _ in range(3):
        r = client.post("/auth/login", json={"email": email, "password": "wrong-password"})
        assert r.status_code == 401

    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "login_rate_limited"


def test_normal_login_usage_unaffected(client):
    email = "ratelimit-normal-login@example.com"
    assert client.post("/auth/register", json={"email": email, "password": "password123"}).status_code == 201
    for _ in range(3):
        r = client.post("/auth/login", json={"email": email, "password": "password123"})
        assert r.status_code == 200


# --- /auth/register ---

def test_register_rate_limit_returns_429_after_limit_exceeded(client, monkeypatch):
    monkeypatch.setattr(router_module.REGISTER_RATE_LIMIT, "limit", 2)

    for i in range(2):
        r = client.post("/auth/register", json={"email": f"ratelimit-reg-{i}@example.com", "password": "password123"})
        assert r.status_code == 201

    r = client.post("/auth/register", json={"email": "ratelimit-reg-overflow@example.com", "password": "password123"})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "register_rate_limited"
    assert r.json()["error"]["retry_after_seconds"] >= 1


def test_normal_registration_usage_unaffected(client):
    for i in range(2):
        r = client.post("/auth/register", json={"email": f"ratelimit-reg-normal-{i}@example.com", "password": "password123"})
        assert r.status_code == 201


# --- answer-submission endpoints ---

def test_exercise_answer_rate_limit_returns_429_after_limit_exceeded(client, auth, monkeypatch):
    monkeypatch.setattr(router_module.ANSWER_RATE_LIMIT, "limit", 2)
    exercise_id = seeded_exercise_id()

    for _ in range(2):
        r = client.post(f"/exercises/{exercise_id}/answer", headers=auth, json={"response": "some answer"})
        assert r.status_code == 200

    r = client.post(f"/exercises/{exercise_id}/answer", headers=auth, json={"response": "some answer"})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "answer_rate_limited"
    assert r.json()["error"]["retry_after_seconds"] >= 1


def test_answer_rate_limit_is_per_account_not_global(client, auth, monkeypatch):
    # A second, distinct account must not be affected by another
    # account already having hit its own limit - this is a per-account
    # bucket, not one shared across every user.
    monkeypatch.setattr(router_module.ANSWER_RATE_LIMIT, "limit", 1)
    exercise_id = seeded_exercise_id()

    assert client.post(f"/exercises/{exercise_id}/answer", headers=auth, json={"response": "some answer"}).status_code == 200
    assert client.post(f"/exercises/{exercise_id}/answer", headers=auth, json={"response": "some answer"}).status_code == 429

    reg = client.post("/auth/register", json={"email": "ratelimit-other-account@example.com", "password": "password123"})
    assert reg.status_code == 201
    other_auth = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    r = client.post(f"/exercises/{exercise_id}/answer", headers=other_auth, json={"response": "some answer"})
    assert r.status_code == 200


def test_normal_answer_submission_usage_unaffected(client, auth):
    exercise_id = seeded_exercise_id()
    for _ in range(3):
        r = client.post(f"/exercises/{exercise_id}/answer", headers=auth, json={"response": "some answer"})
        assert r.status_code == 200


# --- content reports / general feedback ---

def test_anonymous_feedback_rate_limit_returns_429_after_limit_exceeded(client, monkeypatch):
    monkeypatch.setattr(router_module.REPORT_RATE_LIMIT, "limit", 2)

    for i in range(2):
        r = client.post(
            "/feedback",
            json={"category": "app_bug", "description": f"Feedback {i}", "page_path": "/home"},
        )
        assert r.status_code == 201

    r = client.post(
        "/feedback",
        json={"category": "app_bug", "description": "overflow", "page_path": "/home"},
    )
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "report_rate_limited"
    assert r.json()["error"]["retry_after_seconds"] >= 1
