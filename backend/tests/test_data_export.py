"""GET /me/export — GDPR-style data-portability export.

Builds real user data through the actual API flows (lesson start/answer/
complete, practice batch/answer, quest award), plus a directly-inserted
CheckpointAttempt (generating a real 12-15 item checkpoint needs far more
content than this minimal test course has; the export only needs a row to
read back), then asserts the export document contains real values from each
user-scoped table — and that a second account's export contains none of it.
"""
import os
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    CheckpointAttempt,
    ContentIssueReport,
    Exercise,
    Lesson,
    PracticeItem,
    PushSubscription,
)
from test_endless_practice import (
    artifact,
    create_course_with_lexemes,
    import_templates,
)


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def test_export_requires_auth(client):
    assert client.get("/me/export").status_code == 401


def test_export_contains_real_values_from_each_table(client, admin, auth):
    uid = user_id(auth)
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))

    # Real lesson flow: LessonProgress + ExerciseAttempt + SkillProgress +
    # UserLexemeSRS + UserStats XP + (via record_activity) the seeded
    # threshold-1 "first_steps" achievement.
    assert client.post(f"/lessons/{lesson_id}/start", headers=auth).status_code == 200
    with SessionLocal() as db:
        exercise = db.scalar(select(Exercise).where(Exercise.lesson_id == lesson_id))
        exercise_id = exercise.id
        correct_response = exercise.correct_response
        unit_id = db.scalar(select(Lesson.unit_id).where(Lesson.id == lesson_id))
    answered = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": correct_response},
    )
    assert answered.status_code == 200, answered.text
    completed = client.post(f"/lessons/{lesson_id}/complete", headers=auth)
    assert completed.status_code == 200, completed.text

    # Real practice flow: PracticeItem + PracticeAttempt.
    batch = client.post(f"/practice/{course_id}/batch", headers=auth, json={"size": 1})
    assert batch.status_code == 200, batch.text
    practice_item_id = batch.json()["items"][0]["id"]
    with SessionLocal() as db:
        practice_response = db.get(PracticeItem, practice_item_id).correct_response
    practice_answer = client.post(
        f"/practice/items/{practice_item_id}/answer",
        headers=auth,
        json={"response": practice_response},
    )
    assert practice_answer.status_code == 200, practice_answer.text

    # Real quest award: the lesson completed above completes the
    # "Complete a lesson" daily quest, persisting a QuestCompletion row.
    assert client.get("/me/quests", headers=auth).status_code == 200

    # Real user-filed report (reporter_user_id-scoped in the export).
    report = client.post(
        f"/exercises/{exercise_id}/report",
        headers=auth,
        json={"category": "other", "description": "export-test report"},
    )
    assert report.status_code == 201, report.text

    with SessionLocal() as db:
        db.add(
            CheckpointAttempt(
                user_id=uid,
                unit_id=unit_id,
                total_items=12,
                passed=True,
                score=0.9,
                weak_outcomes=["greetings"],
                scored_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            PushSubscription(
                user_id=uid,
                endpoint=f"https://push.example.test/export-{uid}",
                p256dh="p256dh-key",
                auth="auth-key",
            )
        )
        db.commit()

    res = client.get("/me/export", headers=auth)
    assert res.status_code == 200, res.text
    assert "attachment" in res.headers.get("content-disposition", "")
    data = res.json()

    assert data["format_version"] == 1
    assert data["exported_at"]

    assert data["profile"]["id"] == uid
    assert data["profile"]["email"].endswith("@example.com")
    assert data["profile"]["display_name"] == "Test User"
    assert data["profile"]["created_at"]

    assert data["stats"]["total_xp"] > 0
    assert data["stats"]["daily_goal"] == 20

    assert any(
        sp["course_id"] == course_id and sp["completed_lessons"] >= 1
        for sp in data["skill_progress"]
    )

    lesson_rows = [x for x in data["lesson_progress"] if x["lesson_id"] == lesson_id]
    assert lesson_rows
    assert lesson_rows[0]["completed_at"]
    assert lesson_rows[0]["answer_count"] >= 1
    assert lesson_rows[0]["xp_earned"] > 0

    attempt_rows = [x for x in data["exercise_attempts"] if x["exercise_id"] == exercise_id]
    assert attempt_rows
    assert attempt_rows[0]["correct"] is True
    assert attempt_rows[0]["response"] == correct_response
    assert attempt_rows[0]["created_at"]

    practice_rows = [
        x for x in data["practice_attempts"] if x["practice_item_id"] == practice_item_id
    ]
    assert practice_rows
    assert practice_rows[0]["correct"] is True
    assert practice_rows[0]["course_id"] == course_id
    assert practice_rows[0]["prompt"]

    checkpoint_rows = [x for x in data["checkpoint_attempts"] if x["unit_id"] == unit_id]
    assert checkpoint_rows
    assert checkpoint_rows[0]["passed"] is True
    assert checkpoint_rows[0]["score"] == 0.9
    assert checkpoint_rows[0]["weak_outcomes"] == ["greetings"]

    assert data["lexeme_srs"], "completing the lesson should introduce SRS rows"
    srs = data["lexeme_srs"][0]
    assert srs["token"] and srs["english_gloss"] and srs["language_code"]
    assert srs["course_id"] == course_id
    assert srs["due_at"] and srs["introduced_at"]

    assert any(
        a["code"] == "first_steps" and a["earned_at"] for a in data["achievements"]
    )
    assert any(q["quest_code"] and q["awarded_at"] for q in data["quest_completions"])

    subs = [
        x
        for x in data["push_subscriptions"]
        if x["endpoint"] == f"https://push.example.test/export-{uid}"
    ]
    assert subs and subs[0]["created_at"]
    # Channel crypto keys are credentials, not personal data — never exported.
    assert "p256dh" not in subs[0] and "auth" not in subs[0]

    reports = [
        x for x in data["content_issue_reports"] if x["exercise_id"] == exercise_id
    ]
    assert reports
    assert reports[0]["description"] == "export-test report"
    assert reports[0]["category"] == "other"

    with SessionLocal() as db:
        # The export itself must be read-only: the user-filed report is
        # still there and still belongs to this user.
        assert (
            db.scalar(
                select(ContentIssueReport).where(
                    ContentIssueReport.reporter_user_id == uid
                )
            )
            is not None
        )


def test_export_is_scoped_to_own_account(client, auth):
    # `auth` has (or will accumulate) data from other tests in this module's
    # session; a brand-new account's export must be empty of everything.
    email = f"export-empty-{os.urandom(4).hex()}@example.com"
    registered = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Empty"},
    )
    assert registered.status_code == 201
    fresh = {"Authorization": f"Bearer {registered.json()['access_token']}"}

    res = client.get("/me/export", headers=fresh)
    assert res.status_code == 200
    data = res.json()
    assert data["profile"]["email"] == email
    assert data["stats"]["total_xp"] == 0
    for key in (
        "skill_progress",
        "lesson_progress",
        "exercise_attempts",
        "practice_attempts",
        "checkpoint_attempts",
        "lexeme_srs",
        "review_items",
        "achievements",
        "quest_completions",
        "vocabulary_progress",
        "grammar_progress",
        "push_subscriptions",
        "content_issue_reports",
    ):
        assert data[key] == [], f"fresh account's {key} should be empty"
