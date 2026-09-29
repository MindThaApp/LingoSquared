from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import Exercise, ExerciseAttempt, Lesson, LessonProgress, SkillProgress, Unit, UserStats


def _lesson(client):
    course = client.get("/courses?source=en&target=fa").json()[0]
    unit = client.get(f"/courses/{course['id']}/units").json()[0]
    lesson = client.get(f"/units/{unit['id']}/lessons").json()[0]
    detail = client.get(f"/lessons/{lesson['id']}").json()
    return lesson, detail


def _user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def test_completion_requires_answer_but_allows_empty_lesson(client, auth):
    lesson, detail = _lesson(client)
    assert client.post(f"/lessons/{lesson['id']}/start", headers=auth).status_code == 200

    blocked = client.post(f"/lessons/{lesson['id']}/complete", headers=auth)
    assert blocked.status_code == 409
    assert blocked.json()["error"] == {
        "code": "lesson_not_attempted",
        "message": "Answer at least one lesson exercise before completing it",
    }
    with SessionLocal() as db:
        assert db.scalar(select(SkillProgress).where(SkillProgress.user_id == _user_id(auth))) is None
        progress = db.scalar(select(LessonProgress).where(
            LessonProgress.user_id == _user_id(auth), LessonProgress.lesson_id == lesson["id"]
        ))
        assert progress.completed_at is None

        unit = db.get(Unit, detail["unit_id"])
        empty = Lesson(unit_id=unit.id, title=f"Empty {uuid4()}", order=999)
        db.add(empty)
        db.commit()
        empty_id = empty.id

    assert client.post(f"/lessons/{empty_id}/start", headers=auth).status_code == 200
    completed = client.post(f"/lessons/{empty_id}/complete", headers=auth)
    assert completed.status_code == 200, completed.text
    assert completed.json()["accuracy"] == 0

    exercise = detail["exercises"][0]
    with SessionLocal() as db:
        response = db.get(Exercise, exercise["id"]).correct_response
    answered = client.post(
        f"/exercises/{exercise['id']}/answer", headers=auth, json={"response": response}
    )
    assert answered.status_code == 200
    assert client.post(f"/lessons/{lesson['id']}/complete", headers=auth).status_code == 200


def test_answer_operation_id_is_idempotent(client, auth):
    lesson, detail = _lesson(client)
    assert client.post(f"/lessons/{lesson['id']}/start", headers=auth).status_code == 200
    exercise = detail["exercises"][0]
    with SessionLocal() as db:
        response = db.get(Exercise, exercise["id"]).correct_response
    payload = {"response": response, "client_operation_id": str(uuid4())}
    first = client.post(f"/exercises/{exercise['id']}/answer", headers=auth, json=payload)
    retry = client.post(f"/exercises/{exercise['id']}/answer", headers=auth, json=payload)
    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ExerciseAttempt.id)).where(
            ExerciseAttempt.user_id == _user_id(auth),
            ExerciseAttempt.client_operation_id == payload["client_operation_id"],
        )) == 1
        stats = db.get(UserStats, _user_id(auth))
        assert stats.total_xp == first.json()["xp_awarded"]


def test_concurrent_same_operation_id_creates_one_attempt(client, auth):
    lesson, detail = _lesson(client)
    assert client.post(f"/lessons/{lesson['id']}/start", headers=auth).status_code == 200
    exercise = detail["exercises"][0]
    with SessionLocal() as db:
        response = db.get(Exercise, exercise["id"]).correct_response
    payload = {"response": response, "client_operation_id": str(uuid4())}

    def submit(_):
        return client.post(f"/exercises/{exercise['id']}/answer", headers=auth, json=payload)

    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(submit, range(2)))
    assert all(answer.status_code == 200 for answer in answers)
    assert answers[0].json() == answers[1].json()
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ExerciseAttempt.id)).where(
            ExerciseAttempt.user_id == _user_id(auth),
            ExerciseAttempt.client_operation_id == payload["client_operation_id"],
        )) == 1


def test_concurrent_first_correct_answers_award_first_and_replay_xp_once(client, auth):
    lesson, detail = _lesson(client)
    assert client.post(f"/lessons/{lesson['id']}/start", headers=auth).status_code == 200
    exercise = detail["exercises"][0]
    with SessionLocal() as db:
        row = db.get(Exercise, exercise["id"])
        response = row.correct_response
        full_xp = row.xp

    def submit(_):
        return client.post(
            f"/exercises/{exercise['id']}/answer",
            headers=auth,
            json={"response": response, "client_operation_id": str(uuid4())},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(submit, range(2)))
    assert all(answer.status_code == 200 for answer in answers)
    assert sorted(answer.json()["xp_awarded"] for answer in answers) == [1, full_xp]
    with SessionLocal() as db:
        assert db.get(UserStats, _user_id(auth)).total_xp == full_xp + 1


def test_replay_xp_daily_cap_and_wrong_replay_does_not_extend_streak(client, auth):
    lesson, detail = _lesson(client)
    exercise = detail["exercises"][0]
    with SessionLocal() as db:
        row = db.get(Exercise, exercise["id"])
        correct_response = row.correct_response
        uid = _user_id(auth)
        stats = db.get(UserStats, uid)
        today = datetime.now(timezone.utc).date()
        stats.streak_days = 4
        stats.last_activity_date = today - timedelta(days=1)
        # Represent an exercise that was answered correctly before today.
        db.add(ExerciseAttempt(
            user_id=uid,
            exercise_id=row.id,
            response=correct_response,
            correct=True,
            outcome="correct",
            xp_awarded=0,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        ))
        # 20 correct answers already used today's replay allowance.
        for _ in range(20):
            db.add(ExerciseAttempt(
                user_id=uid,
                exercise_id=row.id,
                response=correct_response,
                correct=True,
                outcome="correct",
                xp_awarded=0,
                created_at=datetime.now(timezone.utc),
            ))
        db.commit()

    wrong = client.post(
        f"/exercises/{exercise['id']}/answer",
        headers=auth,
        json={"response": "definitely-wrong", "client_operation_id": str(uuid4())},
    )
    assert wrong.status_code == 200 and wrong.json()["correct"] is False
    with SessionLocal() as db:
        stats = db.get(UserStats, _user_id(auth))
        assert stats.streak_days == 4
        assert stats.last_activity_date == today - timedelta(days=1)

    replay = client.post(
        f"/exercises/{exercise['id']}/answer",
        headers=auth,
        json={"response": correct_response, "client_operation_id": str(uuid4())},
    )
    assert replay.status_code == 200
    assert replay.json()["xp_awarded"] == 0
