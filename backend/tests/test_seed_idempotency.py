from uuid import uuid4

from sqlalchemy import select

from app.content.service import import_content
from app.db.session import SessionLocal
from app.models import Course, Exercise, Lesson, LessonProgress, Unit, User
from app.schemas.api import ImportRequest


def course_payload(title, target="nl"):
    return {
        "source_language": "en",
        "target_language": target,
        "title": title,
        "description": "Idempotency test course.",
        "level": "A1",
        "units": [
            {
                "title": "Test unit",
                "order": 1,
                "lessons": [
                    {
                        "title": "Test lesson",
                        "order": 1,
                        "teaching": [
                            {
                                "kind": "vocabulary",
                                "title": "Greeting",
                                "text_blocks": [
                                    {
                                        "text": "hello",
                                        "language_code": "en",
                                        "direction": "ltr",
                                    },
                                    {
                                        "text": "hallo",
                                        "language_code": target,
                                        "direction": "ltr",
                                    },
                                ],
                            }
                        ],
                        "exercises": [
                            {
                                "type": "translation",
                                "order": 1,
                                "prompt": {
                                    "text_blocks": [
                                        {
                                            "text": "hello",
                                            "language_code": "en",
                                            "direction": "ltr",
                                        }
                                    ]
                                },
                                "correct_response": "hallo",
                                "feedback": "hallo means hello.",
                                "xp": 10,
                            }
                        ],
                    }
                ],
            }
        ],
        "content_items": [],
    }


def course_tree_ids(db, title):
    course = db.scalar(select(Course).where(Course.title == title))
    unit = db.scalar(select(Unit).where(Unit.course_id == course.id))
    lesson = db.scalar(select(Lesson).where(Lesson.unit_id == unit.id))
    exercise = db.scalar(
        select(Exercise).where(Exercise.lesson_id == lesson.id)
    )
    return {
        "course": course.id,
        "unit": unit.id,
        "lesson": lesson.id,
        "exercise": exercise.id,
    }


def test_existing_course_import_is_non_destructive():
    title = f"Idempotent course {uuid4()}"
    request = ImportRequest.model_validate(
        {"courses": [course_payload(title)]}
    )

    with SessionLocal() as db:
        created, errors = import_content(db, request)
        assert created == 1
        assert errors == []

        original_ids = course_tree_ids(db, title)

        user = User(
            email=f"seed-idempotency-{uuid4()}@example.com",
            password_hash="test-only",
            display_name="Seed Test",
        )
        db.add(user)
        db.flush()

        progress = LessonProgress(
            user_id=user.id,
            lesson_id=original_ids["lesson"],
            correct_count=3,
            answer_count=4,
            xp_earned=30,
        )
        db.add(progress)
        db.commit()

        progress_id = progress.id
        user_id = user.id

        created, errors = import_content(db, request)
        assert created == 0
        assert errors == []

        assert course_tree_ids(db, title) == original_ids

        surviving_progress = db.get(LessonProgress, progress_id)
        assert surviving_progress is not None
        assert surviving_progress.user_id == user_id
        assert surviving_progress.lesson_id == original_ids["lesson"]
        assert surviving_progress.correct_count == 3
        assert surviving_progress.answer_count == 4
        assert surviving_progress.xp_earned == 30


def test_new_course_is_created_alongside_skipped_existing_course():
    existing_title = f"Existing mixed import {uuid4()}"
    new_title = f"New mixed import {uuid4()}"

    existing_request = ImportRequest.model_validate(
        {"courses": [course_payload(existing_title, target="fr")]}
    )

    with SessionLocal() as db:
        created, errors = import_content(db, existing_request)
        assert created == 1
        assert errors == []

        existing_ids = course_tree_ids(db, existing_title)

        mixed_request = ImportRequest.model_validate(
            {
                "courses": [
                    course_payload(existing_title, target="fr"),
                    course_payload(new_title, target="de"),
                ]
            }
        )

        created, errors = import_content(db, mixed_request)
        assert created == 1
        assert errors == []

        assert course_tree_ids(db, existing_title) == existing_ids

        new_course = db.scalar(
            select(Course).where(Course.title == new_title)
        )
        assert new_course is not None
        assert new_course.source_language == "en"
        assert new_course.target_language == "de"

        new_unit = db.scalar(
            select(Unit).where(Unit.course_id == new_course.id)
        )
        new_lesson = db.scalar(
            select(Lesson).where(Lesson.unit_id == new_unit.id)
        )
        new_exercise = db.scalar(
            select(Exercise).where(Exercise.lesson_id == new_lesson.id)
        )

        assert new_unit is not None
        assert new_lesson is not None
        assert new_exercise is not None
