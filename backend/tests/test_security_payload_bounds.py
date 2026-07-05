"""Security pass, 2026-07-05: a pathologically large `response` on any
answer-submission endpoint (exercise/review/practice, all reachable by any
authenticated non-admin user, no rate limiting) used to reach
grade_answer()'s Damerau-Levenshtein comparison unbounded -
damerau_levenshtein() allocates an O(len(a) * len(b)) table with no length
check of its own, so a multi-megabyte `response` string was a trivial
resource-exhaustion vector. Fixed with a serialized-size bound in
AnswerIn/ContentIssueReportIn (app/schemas/api.py) and a max_length on
LoginIn.password (previously unbounded, unlike RegisterIn's). These tests
confirm the guard actually rejects an oversized payload via the real HTTP
API (not just at the schema layer) and that ordinary, legitimate answers
are completely unaffected.
"""
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Exercise


def seeded_exercise_id():
    with SessionLocal() as db:
        return db.scalar(select(Exercise.id).order_by(Exercise.id))


def test_oversized_string_answer_rejected_before_grading(client, auth):
    exercise_id = seeded_exercise_id()
    huge = "a" * 200_000  # far past any real answer, well past the 5000-char bound
    response = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": huge},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_oversized_list_answer_rejected(client, auth):
    exercise_id = seeded_exercise_id()
    response = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": ["word"] * 50_000},
    )
    assert response.status_code == 422


def test_ordinary_short_answer_still_works(client, auth):
    exercise_id = seeded_exercise_id()
    response = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": "a perfectly normal short answer"},
    )
    assert response.status_code == 200


def test_oversized_login_password_rejected_without_touching_db(client):
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "x" * 100_000},
    )
    assert response.status_code == 422


def test_oversized_learner_response_on_content_issue_report_rejected(client, auth):
    exercise_id = seeded_exercise_id()
    response = client.post(
        f"/exercises/{exercise_id}/report",
        headers=auth,
        json={
            "category": "wrong_answer_key",
            "learner_response": {"response": "x" * 200_000},
        },
    )
    assert response.status_code == 422
