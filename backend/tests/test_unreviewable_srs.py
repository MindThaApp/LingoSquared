from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Lexeme, PracticeItem, UserLexemeSRS
from test_endless_practice import (
    artifact,
    create_course_with_lexemes,
    import_templates,
)
from test_phase_a_srs import complete_via_api, user_id


def _prepare_review_course(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    return course_id, user_id(auth)


def _srs_for_token(db, uid, course_id, token):
    return db.scalar(
        select(UserLexemeSRS)
        .join(Lexeme, Lexeme.id == UserLexemeSRS.lexeme_id)
        .where(
            UserLexemeSRS.user_id == uid,
            UserLexemeSRS.course_id == course_id,
            Lexeme.token == token,
        )
    )


def test_due_ungeneratable_lexeme_is_flagged_without_schedule_change(
    client, admin, auth
):
    course_id, uid = _prepare_review_course(client, admin, auth)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(UserLexemeSRS).where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
            )
        )
        for row in rows:
            row.due_at = now + timedelta(days=30)
        target = _srs_for_token(db, uid, course_id, "derecha")
        target.due_at = now - timedelta(minutes=1)
        db.commit()
        db.refresh(target)
        unchanged = (
            target.due_at,
            target.stability,
            target.difficulty,
            target.interval_days,
            target.ease_factor,
            target.repetitions,
            target.mastery,
            target.last_reviewed_at,
        )

    before = client.get("/me/reviews/due", headers=auth)
    assert before.status_code == 200, before.text
    assert before.json()["due_count"] == 1

    session = client.post(
        "/reviews/session",
        headers=auth,
        json={"course_id": course_id, "size": 1},
    )
    assert session.status_code == 200, session.text

    with SessionLocal() as db:
        target = _srs_for_token(db, uid, course_id, "derecha")
        assert target.unreviewable_at is not None
        assert (
            target.due_at,
            target.stability,
            target.difficulty,
            target.interval_days,
            target.ease_factor,
            target.repetitions,
            target.mastery,
            target.last_reviewed_at,
        ) == unchanged

    after = client.get("/me/reviews/due", headers=auth)
    assert after.status_code == 200, after.text
    assert after.json()["due_count"] == 0


def test_due_generatable_lexeme_stays_due_and_is_served(client, admin, auth):
    course_id, uid = _prepare_review_course(client, admin, auth)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(UserLexemeSRS).where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
            )
        )
        for row in rows:
            row.due_at = now + timedelta(days=30)
        target = _srs_for_token(db, uid, course_id, "uno")
        target.due_at = now - timedelta(minutes=1)
        lexeme_id = target.lexeme_id
        db.commit()

    session = client.post(
        "/reviews/session",
        headers=auth,
        json={"course_id": course_id, "size": 1},
    )
    assert session.status_code == 200, session.text
    assert len(session.json()["items"]) == 1
    item_id = session.json()["items"][0]["id"]

    with SessionLocal() as db:
        item = db.get(PracticeItem, item_id)
        target = _srs_for_token(db, uid, course_id, "uno")
        assert item.target_lexeme_id == lexeme_id
        assert target.unreviewable_at is None

    due = client.get("/me/reviews/due", headers=auth)
    assert due.status_code == 200, due.text
    assert due.json()["due_count"] == 1


def test_practice_generation_miss_does_not_flag_lexeme_unreviewable(
    client, admin, auth
):
    course_id, uid = _prepare_review_course(client, admin, auth)
    with SessionLocal() as db:
        target = _srs_for_token(db, uid, course_id, "derecha")
        target.due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        lexeme_id = target.lexeme_id
        db.commit()

    batch = client.post(
        f"/practice/{course_id}/batch",
        headers=auth,
        json={"size": 1, "target_lexeme_ids": [lexeme_id]},
    )
    assert batch.status_code == 200, batch.text
    assert batch.json() == {"locked": False, "items": []}

    with SessionLocal() as db:
        target = _srs_for_token(db, uid, course_id, "derecha")
        assert target.unreviewable_at is None


def test_practice_reimport_resets_unreviewable_flag(client, admin, auth):
    course_id, uid = _prepare_review_course(client, admin, auth)
    with SessionLocal() as db:
        target = _srs_for_token(db, uid, course_id, "derecha")
        target.unreviewable_at = datetime.now(timezone.utc)
        db.commit()

    result = import_templates(
        client,
        admin,
        course_id,
        artifact(include_listen=False),
    )
    assert result == {"imported_templates": 0, "updated_templates": 5}

    with SessionLocal() as db:
        target = _srs_for_token(db, uid, course_id, "derecha")
        assert target.unreviewable_at is None
