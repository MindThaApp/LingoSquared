from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    Course,
    Lesson,
    LessonProgress,
    Lexeme,
    PracticeAttempt,
    PracticeItem,
    PracticeTemplate,
    QuestCompletion,
    Unit,
    UserLexemeSRS,
    UserStats,
)
from app.services.progress import activity_day_bounds


def _register(client, email, timezone_name=None):
    body = {
        "email": email,
        "password": "password123",
    }
    if timezone_name is not None:
        body["timezone"] = timezone_name

    response = client.post("/auth/register", json=body)
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return (
        decode_token(token),
        {"Authorization": f"Bearer {token}"},
    )


def _quests(client, headers):
    response = client.get("/me/quests", headers=headers)
    assert response.status_code == 200, response.text
    return {
        quest["code"]: quest
        for quest in response.json()["quests"]
    }


def _course_and_lesson(db):
    course = db.scalar(select(Course).order_by(Course.id))
    assert course is not None
    lesson = db.scalar(
        select(Lesson)
        .join(Unit)
        .where(Unit.course_id == course.id)
        .order_by(Lesson.id)
    )
    assert lesson is not None
    return course, lesson


def _add_correct_practice_attempts(user_id, count):
    with SessionLocal() as db:
        course, lesson = _course_and_lesson(db)
        template = PracticeTemplate(
            course_id=course.id,
            content_key=f"quest-test-{uuid4()}",
            provenance_lesson_id=lesson.id,
            type="translation",
            frame={},
            slots={},
            slot_relations=[],
            answer_derivation={},
            feedback_frame={},
            active=True,
        )
        db.add(template)
        db.flush()

        for _ in range(count):
            item = PracticeItem(
                user_id=user_id,
                course_id=course.id,
                template_id=template.id,
                filled_slots={},
                prompt={},
                correct_response="correct",
                xp_value=5,
                source="practice",
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
            db.add(item)
            db.flush()
            db.add(
                PracticeAttempt(
                    user_id=user_id,
                    practice_item_id=item.id,
                    response="correct",
                    correct=True,
                    xp_awarded=5,
                    created_at=datetime.now(timezone.utc),
                )
            )

        db.commit()


def test_new_account_has_three_incomplete_quests(client):
    _, headers = _register(
        client,
        f"quests-initial-{uuid4()}@example.com",
    )

    quests = _quests(client, headers)

    assert set(quests) == {
        "clear_reviews",
        "complete_lesson",
        "practice_correct_5",
    }
    assert all(quest["completed"] is False for quest in quests.values())
    assert quests["clear_reviews"]["progress"] == 0
    assert quests["complete_lesson"]["progress"] == 0
    assert quests["practice_correct_5"]["progress"] == 0


def test_clear_reviews_completes_only_after_existing_reviews_are_clear(client):
    user_id, headers = _register(
        client,
        f"quests-reviews-{uuid4()}@example.com",
    )

    assert _quests(client, headers)["clear_reviews"]["completed"] is False

    with SessionLocal() as db:
        course, lesson = _course_and_lesson(db)
        lexeme = Lexeme(
            course_id=course.id,
            token=f"quest-{uuid4()}",
            language_code=course.target_language,
            part_of_speech="noun",
            english_gloss="quest test",
            agreement_tags={},
            provenance_lesson_id=lesson.id,
            provenance_lesson_content_key=f"lesson-{uuid4()}",
            provenance_content_key=f"content-{uuid4()}",
        )
        db.add(lexeme)
        db.flush()

        review = UserLexemeSRS(
            user_id=user_id,
            lexeme_id=lexeme.id,
            course_id=course.id,
            ease_factor=2.5,
            interval_days=0,
            repetitions=0,
            mastery=0.0,
            due_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            last_reviewed_at=None,
            introduced_at=datetime.now(timezone.utc),
            suspended=False,
            last_session_id=None,
        )
        db.add(review)
        db.commit()
        review_id = review.id

    due = _quests(client, headers)["clear_reviews"]
    assert due["completed"] is False
    assert due["progress"] == 0
    assert due["target"] == 1

    with SessionLocal() as db:
        review = db.get(UserLexemeSRS, review_id)
        review.due_at = datetime.now(timezone.utc) + timedelta(days=1)
        db.commit()

    cleared = _quests(client, headers)["clear_reviews"]
    assert cleared["completed"] is True
    assert cleared["progress"] == 1


def test_complete_lesson_reports_complete_and_awards_xp_once(client):
    user_id, headers = _register(
        client,
        f"quests-lesson-{uuid4()}@example.com",
    )

    assert _quests(client, headers)["complete_lesson"]["completed"] is False

    with SessionLocal() as db:
        _, lesson = _course_and_lesson(db)
        db.add(
            LessonProgress(
                user_id=user_id,
                lesson_id=lesson.id,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                completed_at=datetime.now(timezone.utc),
                correct_count=1,
                answer_count=1,
                xp_earned=0,
            )
        )
        db.commit()
        xp_before = db.get(UserStats, user_id).total_xp

    first = _quests(client, headers)["complete_lesson"]
    assert first["completed"] is True
    assert first["progress"] == 1
    assert first["target"] == 1

    with SessionLocal() as db:
        xp_after_first = db.get(UserStats, user_id).total_xp
        completions_after_first = db.scalar(
            select(func.count(QuestCompletion.id)).where(
                QuestCompletion.user_id == user_id,
                QuestCompletion.quest_code == "complete_lesson",
            )
        )

    second = _quests(client, headers)["complete_lesson"]
    assert second["completed"] is True

    with SessionLocal() as db:
        xp_after_second = db.get(UserStats, user_id).total_xp
        completions_after_second = db.scalar(
            select(func.count(QuestCompletion.id)).where(
                QuestCompletion.user_id == user_id,
                QuestCompletion.quest_code == "complete_lesson",
            )
        )

    assert xp_after_first == xp_before + first["xp_reward"]
    assert xp_after_second == xp_after_first
    assert completions_after_first == 1
    assert completions_after_second == 1


def test_practice_quest_reports_capped_live_progress(client):
    user_id, headers = _register(
        client,
        f"quests-practice-{uuid4()}@example.com",
    )

    initial = _quests(client, headers)["practice_correct_5"]
    assert initial["completed"] is False
    assert initial["progress"] == 0
    assert initial["target"] == 5

    _add_correct_practice_attempts(user_id, 3)

    partial = _quests(client, headers)["practice_correct_5"]
    assert partial["completed"] is False
    assert partial["progress"] == 3

    _add_correct_practice_attempts(user_id, 2)

    complete = _quests(client, headers)["practice_correct_5"]
    assert complete["completed"] is True
    assert complete["progress"] == 5

    _add_correct_practice_attempts(user_id, 2)

    capped = _quests(client, headers)["practice_correct_5"]
    assert capped["completed"] is True
    assert capped["progress"] == 5


def test_yesterdays_completion_does_not_complete_todays_quest(client):
    timezone_name = "Pacific/Kiritimati"
    user_id, headers = _register(
        client,
        f"quests-yesterday-{uuid4()}@example.com",
        timezone_name,
    )
    today_start, _ = activity_day_bounds(timezone_name)
    yesterday = today_start.date() - timedelta(days=1)

    with SessionLocal() as db:
        _, lesson = _course_and_lesson(db)
        db.add(
            LessonProgress(
                user_id=user_id,
                lesson_id=lesson.id,
                started_at=today_start - timedelta(hours=2),
                completed_at=today_start - timedelta(hours=1),
                correct_count=1,
                answer_count=1,
                xp_earned=0,
            )
        )
        db.add(
            QuestCompletion(
                user_id=user_id,
                quest_code="complete_lesson",
                date=yesterday,
                awarded_at=today_start - timedelta(hours=1),
            )
        )
        db.commit()
        xp_before = db.get(UserStats, user_id).total_xp

    quest = _quests(client, headers)["complete_lesson"]

    assert quest["completed"] is False
    assert quest["progress"] == 0

    with SessionLocal() as db:
        assert db.get(UserStats, user_id).total_xp == xp_before
        today_completion = db.scalar(
            select(QuestCompletion).where(
                QuestCompletion.user_id == user_id,
                QuestCompletion.quest_code == "complete_lesson",
                QuestCompletion.date == today_start.date(),
            )
        )
        assert today_completion is None
