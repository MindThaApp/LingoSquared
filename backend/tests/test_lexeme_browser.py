from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    Lexeme,
    PracticeAttempt,
    PracticeItem,
    PracticeTemplate,
    UserLexemeSRS,
)
from test_endless_practice import artifact, create_course_with_lexemes, import_templates
from test_phase_a_srs import complete_via_api


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def test_lexeme_browser_filters_sorts_paginates_and_excludes_untracked(client, auth):
    course_id, lesson_id = create_course_with_lexemes()
    complete_via_api(client, auth, lesson_id)
    uid = user_id(auth)

    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(UserLexemeSRS)
                .where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
                .order_by(UserLexemeSRS.lexeme_id)
            )
        )
        for index, row in enumerate(rows):
            row.mastery = index / 10
            row.introduced_at = datetime.now(timezone.utc) - timedelta(days=index)

        lesson = db.get(Lexeme, rows[0].lexeme_id).provenance_lesson_id
        db.add(
            Lexeme(
                course_id=course_id,
                token="never-seen",
                language_code="es",
                part_of_speech="noun",
                english_gloss="never seen",
                agreement_tags={},
                provenance_lesson_id=lesson,
                provenance_lesson_content_key="test.practice.lesson.001",
                provenance_content_key="test.lexeme.never_seen",
            )
        )
        db.commit()

    response = client.get(
        f"/me/lexemes?course_id={course_id}&part_of_speech=noun&search=e&sort=mastery_desc&limit=2&offset=0",
        headers=auth,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["total_count"] >= 2
    assert len(body["items"]) == 2
    assert body["items"][0]["mastery"] >= body["items"][1]["mastery"]
    assert all(item["part_of_speech"] == "noun" for item in body["items"])
    assert "never-seen" not in {item["token"] for item in body["items"]}


def test_lexeme_browser_invalid_course_returns_404(client, auth):
    response = client.get("/me/lexemes?course_id=missing", headers=auth)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "course_not_found"


def test_lexeme_summary_counts_bands_due_today_and_suspended(client, auth):
    course_id, lesson_id = create_course_with_lexemes()
    complete_via_api(client, auth, lesson_id)
    uid = user_id(auth)
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(UserLexemeSRS)
                .where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
                .order_by(UserLexemeSRS.lexeme_id)
            )
        )
        rows[0].mastery = 0.1
        rows[0].due_at = now - timedelta(minutes=5)
        rows[1].mastery = 0.5
        rows[1].due_at = now - timedelta(minutes=1)
        rows[2].mastery = 0.9
        rows[2].due_at = now + timedelta(days=3)
        rows[3].suspended = True
        rows[3].due_at = now - timedelta(minutes=5)
        db.commit()

    response = client.get(f"/me/lexemes/summary?course_id={course_id}", headers=auth)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_tracked"] >= 4
    assert body["mastery_bands"]["new"] >= 1
    assert body["mastery_bands"]["learning"] >= 1
    assert body["mastery_bands"]["strong"] >= 1
    assert body["due_today"] >= 2
    assert body["suspended"] == 1


def test_lexeme_summary_empty_course_returns_zeroes(client, auth):
    course_id, _ = create_course_with_lexemes()
    response = client.get(f"/me/lexemes/summary?course_id={course_id}", headers=auth)
    assert response.status_code == 200
    assert response.json() == {
        "total_tracked": 0,
        "mastery_bands": {"new": 0, "learning": 0, "strong": 0},
        "due_today": 0,
        "suspended": 0,
    }


def test_mistakes_uses_lexeme_attempt_history_worst_first(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    uid = user_id(auth)

    with SessionLocal() as db:
        template = db.scalar(
            select(PracticeTemplate).where(PracticeTemplate.course_id == course_id)
        )
        rows = list(
            db.scalars(
                select(UserLexemeSRS)
                .where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
                .order_by(UserLexemeSRS.lexeme_id)
            )
        )
        rows[0].mastery = 0.2
        rows[0].repetitions = 3
        rows[1].mastery = 0.4
        rows[1].repetitions = 2
        now = datetime.now(timezone.utc)
        for target, outcomes in (
            (rows[0].lexeme_id, [False, False, True]),
            (rows[1].lexeme_id, [False]),
        ):
            for index, correct in enumerate(outcomes):
                item = PracticeItem(
                    user_id=uid,
                    course_id=course_id,
                    template_id=template.id,
                    filled_slots={},
                    prompt={},
                    correct_response="ok",
                    xp_value=5,
                    source="practice",
                    target_lexeme_id=target,
                    created_at=now,
                    expires_at=now + timedelta(hours=1),
                    answered_at=now,
                )
                db.add(item)
                db.flush()
                db.add(
                    PracticeAttempt(
                        user_id=uid,
                        practice_item_id=item.id,
                        response="x",
                        correct=correct,
                        xp_awarded=5 if correct else 0,
                        created_at=now + timedelta(seconds=index),
                    )
                )
        db.commit()

    response = client.get(f"/me/mistakes?course_id={course_id}", headers=auth)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_count"] == 2
    assert body["items"][0]["wrong_attempt_count"] == 2
    assert body["items"][0]["total_attempt_count"] == 3
    assert body["items"][0]["recent_accuracy"] == 1 / 3
    assert body["items"][0]["repetitions"] == 3
    assert body["items"][1]["wrong_attempt_count"] == 1


def test_mistakes_empty_when_no_wrong_attempts(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    uid = user_id(auth)

    with SessionLocal() as db:
        template = db.scalar(
            select(PracticeTemplate).where(PracticeTemplate.course_id == course_id)
        )
        srs = db.scalar(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.course_id == course_id,
            )
        )
        now = datetime.now(timezone.utc)
        item = PracticeItem(
            user_id=uid,
            course_id=course_id,
            template_id=template.id,
            filled_slots={},
            prompt={},
            correct_response="ok",
            xp_value=5,
            source="practice",
            target_lexeme_id=srs.lexeme_id,
            created_at=now,
            expires_at=now + timedelta(hours=1),
            answered_at=now,
        )
        db.add(item)
        db.flush()
        db.add(
            PracticeAttempt(
                user_id=uid,
                practice_item_id=item.id,
                response="ok",
                correct=True,
                xp_awarded=5,
                created_at=now,
            )
        )
        db.commit()

    response = client.get(f"/me/mistakes?course_id={course_id}", headers=auth)
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total_count": 0,
        "limit": 50,
        "offset": 0,
    }
