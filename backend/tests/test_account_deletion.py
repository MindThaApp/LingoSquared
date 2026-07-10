from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    ContentIssueReport,
    Exercise,
    ExerciseAttempt,
    LessonProgress,
    PracticeAttempt,
    PracticeItem,
    PushSubscription,
    User,
    UserLexemeSRS,
    UserStats,
)
from test_endless_practice import (
    artifact,
    create_course_with_lexemes,
    import_templates,
)


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def count_for_user(db, model, user_column, uid):
    return db.scalar(select(func.count()).select_from(model).where(user_column == uid))


def test_delete_me_removes_user_and_linked_rows(client, admin, auth):
    uid = user_id(auth)
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))

    assert client.post(f"/lessons/{lesson_id}/start", headers=auth).status_code == 200

    with SessionLocal() as db:
        exercise = db.scalar(select(Exercise).where(Exercise.lesson_id == lesson_id))
        exercise_id = exercise.id
        correct_response = exercise.correct_response

    answered = client.post(
        f"/exercises/{exercise_id}/answer",
        headers=auth,
        json={"response": correct_response},
    )
    assert answered.status_code == 200, answered.text

    completed = client.post(f"/lessons/{lesson_id}/complete", headers=auth)
    assert completed.status_code == 200, completed.text

    batch = client.post(f"/practice/{course_id}/batch", headers=auth, json={"size": 1})
    assert batch.status_code == 200, batch.text
    practice_item_id = batch.json()["items"][0]["id"]

    with SessionLocal() as db:
        practice_item = db.get(PracticeItem, practice_item_id)
        practice_response = practice_item.correct_response

    practice_answer = client.post(
        f"/practice/items/{practice_item_id}/answer",
        headers=auth,
        json={"response": practice_response},
    )
    assert practice_answer.status_code == 200, practice_answer.text

    with SessionLocal() as db:
        db.add(
            PushSubscription(
                user_id=uid,
                endpoint=f"https://push.example.test/{uid}",
                p256dh="p256dh",
                auth="auth",
            )
        )
        db.add(
            ContentIssueReport(
                reporter_user_id=None,
                practice_item_id=practice_item_id,
                category="other",
                description="anonymous report against user-owned practice item",
                client_context={},
            )
        )
        db.commit()

        assert db.get(User, uid) is not None
        assert count_for_user(db, LessonProgress, LessonProgress.user_id, uid) > 0
        assert count_for_user(db, UserLexemeSRS, UserLexemeSRS.user_id, uid) > 0
        assert count_for_user(db, ExerciseAttempt, ExerciseAttempt.user_id, uid) > 0
        assert count_for_user(db, PracticeItem, PracticeItem.user_id, uid) > 0
        assert count_for_user(db, PracticeAttempt, PracticeAttempt.user_id, uid) > 0
        assert count_for_user(db, PushSubscription, PushSubscription.user_id, uid) > 0
        assert db.scalar(
            select(func.count())
            .select_from(ContentIssueReport)
            .where(ContentIssueReport.practice_item_id == practice_item_id)
        ) > 0

    deleted = client.delete("/me", headers=auth)
    assert deleted.status_code == 204
    assert deleted.content == b""

    with SessionLocal() as db:
        assert db.get(User, uid) is None
        assert db.get(UserStats, uid) is None
        assert count_for_user(db, LessonProgress, LessonProgress.user_id, uid) == 0
        assert count_for_user(db, UserLexemeSRS, UserLexemeSRS.user_id, uid) == 0
        assert count_for_user(db, ExerciseAttempt, ExerciseAttempt.user_id, uid) == 0
        assert count_for_user(db, PracticeItem, PracticeItem.user_id, uid) == 0
        assert count_for_user(db, PracticeAttempt, PracticeAttempt.user_id, uid) == 0
        assert count_for_user(db, PushSubscription, PushSubscription.user_id, uid) == 0
        assert db.scalar(
            select(func.count())
            .select_from(ContentIssueReport)
            .where(ContentIssueReport.practice_item_id == practice_item_id)
        ) == 0

    unauthorized = client.get("/auth/me", headers=auth)
    assert unauthorized.status_code == 401
