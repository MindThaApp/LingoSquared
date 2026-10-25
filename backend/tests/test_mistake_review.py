from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import Exercise, ReviewItem
from test_endless_practice import create_course_with_lexemes


def _user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def _exercise(client, auth):
    _course_id, lesson_id = create_course_with_lexemes()
    response = client.get(f"/lessons/{lesson_id}")
    assert response.status_code == 200
    return response.json()["exercises"][0]["id"]


def _answer(client, auth, exercise_id, response, **extra):
    return client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": response, **extra},
    )


def _review(auth, exercise_id):
    with SessionLocal() as db:
        return db.scalar(
            select(ReviewItem).where(
                ReviewItem.user_id == _user_id(auth),
                ReviewItem.exercise_id == exercise_id,
            )
        )


def test_wrong_answer_creates_one_review_due_in_ten_minutes(client, auth):
    exercise_id = _exercise(client, auth)
    before = datetime.now(timezone.utc)
    response = _answer(client, auth, exercise_id, "__wrong__")
    assert response.status_code == 200
    item = _review(auth, exercise_id)
    assert item is not None
    assert item.interval_days == 0 and item.ease_factor == 2.3 and item.repetitions == 0
    assert before + timedelta(minutes=9) < item.due_at < before + timedelta(minutes=11)
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ReviewItem.id)).where(
            ReviewItem.user_id == _user_id(auth), ReviewItem.exercise_id == exercise_id
        )) == 1


def test_operation_retry_and_correct_answer_do_not_create_reviews(client, auth):
    exercise_id = _exercise(client, auth)
    wrong = _answer(client, auth, exercise_id, "__wrong__", client_operation_id="retry-1")
    assert wrong.status_code == 200
    repeated = _answer(client, auth, exercise_id, "__wrong__", client_operation_id="retry-1")
    assert repeated.status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ReviewItem.id)).where(
            ReviewItem.user_id == _user_id(auth), ReviewItem.exercise_id == exercise_id
        )) == 1

    other_id = _exercise(client, auth)
    with SessionLocal() as db:
        correct = db.get(Exercise, other_id).correct_response
    answered = _answer(client, auth, other_id, correct)
    assert answered.status_code == 200 and answered.json()["result"] == "correct"
    assert _review(auth, other_id) is None


def test_second_wrong_answer_does_not_reset_review(client, auth):
    exercise_id = _exercise(client, auth)
    assert _answer(client, auth, exercise_id, "__wrong__").status_code == 200
    with SessionLocal() as db:
        item = db.scalar(select(ReviewItem).where(ReviewItem.exercise_id == exercise_id))
        item.ease_factor = 1.9
        item.interval_days = 2
        item.repetitions = 3
        item.due_at = datetime.now(timezone.utc) + timedelta(days=4)
        due_at = item.due_at
        db.commit()
    assert _answer(client, auth, exercise_id, "__wrong__").status_code == 200
    item = _review(auth, exercise_id)
    assert (item.ease_factor, item.interval_days, item.repetitions, item.due_at) == (1.9, 2, 3, due_at)


def test_almost_answer_creates_review(client, auth):
    exercise_id = _exercise(client, auth)
    almost = _answer(client, auth, exercise_id, "tset", input_mode="spoken")
    # Spoken grading recognizes a bounded one-word transcription typo.
    assert almost.status_code == 200
    assert almost.json()["result"] == "almost"
    assert _review(auth, exercise_id) is not None


def test_due_reviews_and_review_answer_schedule(client, auth):
    exercise_id = _exercise(client, auth)
    assert _answer(client, auth, exercise_id, "__wrong__").status_code == 200
    with SessionLocal() as db:
        item = db.scalar(select(ReviewItem).where(ReviewItem.exercise_id == exercise_id))
        item.due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    due = client.get("/me/reviews", headers=auth)
    assert due.status_code == 200
    assert sum(row["exercise_id"] == exercise_id for row in due.json()["items"]) == 1
    with SessionLocal() as db:
        correct = db.get(Exercise, exercise_id).correct_response
    before = datetime.now(timezone.utc)
    response = client.post(
        f"/reviews/{_review(auth, exercise_id).id}/answer",
        headers=auth,
        json={"response": correct},
    )
    assert response.status_code == 200 and response.json()["result"] == "correct"
    next_due_at = datetime.fromisoformat(response.json()["next_due_at"])
    # Due times land on 04:00 of the learner's local day (UTC when no
    # timezone is stored), so a 1-day interval is the next such morning.
    assert before < next_due_at <= before + timedelta(hours=24 + 4)
    assert (next_due_at.hour, next_due_at.minute) == (4, 0)


def test_retired_exercise_is_excluded_from_due_reviews(client, auth):
    exercise_id = _exercise(client, auth)
    assert _answer(client, auth, exercise_id, "__wrong__").status_code == 200
    with SessionLocal() as db:
        item = db.scalar(select(ReviewItem).where(ReviewItem.exercise_id == exercise_id))
        item.due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.get(Exercise, exercise_id).retired_at = datetime.now(timezone.utc)
        db.commit()
    response = client.get("/me/reviews", headers=auth)
    assert response.status_code == 200
    assert all(row["exercise_id"] != exercise_id for row in response.json()["items"])


def test_missing_review_answer_uses_error_envelope(client, auth):
    response = client.post(
        "/reviews/00000000-0000-0000-0000-000000000000/answer",
        headers=auth,
        json={"response": "answer"},
    )
    assert response.status_code == 404
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message"}
