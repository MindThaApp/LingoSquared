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


def course_payload_with_second_unit(title, target="nl"):
    payload = course_payload(title, target=target)
    payload["units"].append(
        {
            "title": "Second unit",
            "order": 2,
            "lessons": [
                {
                    "title": "Second lesson",
                    "order": 1,
                    "teaching": [
                        {
                            "kind": "vocabulary",
                            "title": "Farewell",
                            "text_blocks": [
                                {
                                    "text": "bye",
                                    "language_code": "en",
                                    "direction": "ltr",
                                },
                                {
                                    "text": "dag",
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
                                        "text": "bye",
                                        "language_code": "en",
                                        "direction": "ltr",
                                    }
                                ]
                            },
                            "correct_response": "dag",
                            "feedback": "dag means bye.",
                            "xp": 10,
                        }
                    ],
                }
            ],
        }
    )
    return payload


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
        created, errors, counters = import_content(db, request)
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

        created, errors, counters = import_content(db, request)
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


def test_unit_track_import_create_and_content_key_update_in_place():
    title = f"Track import {uuid4()}"
    payload = course_payload(title)
    payload["units"][0]["content_key"] = "test.track.unit"
    payload["units"][0]["track"] = "situation"
    request = ImportRequest.model_validate({"courses": [payload]})
    with SessionLocal() as db:
        created, errors, _ = import_content(db, request)
        assert created == 1 and errors == []
        original = db.scalar(select(Unit).where(Unit.content_key == "test.track.unit"))
        assert original.track == "situation"
        original_id = original.id
        payload["units"][0].pop("track")
        created, errors, _ = import_content(
            db, ImportRequest.model_validate({"courses": [payload]})
        )
        assert created == 0 and errors == []
        updated = db.get(Unit, original_id)
        assert updated.track == "core"
        assert updated.id == original_id


def test_new_course_is_created_alongside_skipped_existing_course():
    existing_title = f"Existing mixed import {uuid4()}"
    new_title = f"New mixed import {uuid4()}"

    existing_request = ImportRequest.model_validate(
        {"courses": [course_payload(existing_title, target="fr")]}
    )

    with SessionLocal() as db:
        created, errors, counters = import_content(db, existing_request)
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

        created, errors, counters = import_content(db, mixed_request)
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


def test_new_units_are_appended_to_existing_course():
    """Real bug found 2026-07-05: POST /admin/content/import used to
    skip an already-imported course entirely, so any unit authored
    AFTER a course's initial seed could never go live no matter how
    many times it was reimported. Fixed by detecting units whose
    `order` isn't already present under the existing course (units are
    unique per (course_id, order)) and appending only those, while
    every already-present unit/lesson/exercise/progress row stays
    byte-for-byte untouched -- the same non-destructive guarantee as
    `test_existing_course_import_is_non_destructive` above, just for
    the append path instead of the no-op path.
    """
    title = f"Growing course {uuid4()}"

    with SessionLocal() as db:
        created, errors, counters = import_content(
            db, ImportRequest.model_validate({"courses": [course_payload(title)]})
        )
        assert created == 1
        assert errors == []

        original_ids = course_tree_ids(db, title)

        user = User(
            email=f"append-units-{uuid4()}@example.com",
            password_hash="test-only",
            display_name="Append Units Test",
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

        # Reimport the SAME course, now with a second unit included --
        # this is exactly the "unit 2/3 authored after unit 1 already
        # shipped" scenario that was silently dropped before the fix.
        created, errors, counters = import_content(
            db,
            ImportRequest.model_validate(
                {"courses": [course_payload_with_second_unit(title)]}
            ),
        )
        assert created == 0  # not a NEW course -- existing one, appended to
        assert errors == []

        # Unit 1's ids and the real progress pinned to it are untouched.
        assert course_tree_ids(db, title) == original_ids
        surviving_progress = db.get(LessonProgress, progress_id)
        assert surviving_progress is not None
        assert surviving_progress.correct_count == 3
        assert surviving_progress.answer_count == 4
        assert surviving_progress.xp_earned == 30

        # Unit 2 now genuinely exists.
        course = db.scalar(select(Course).where(Course.title == title))
        units = list(
            db.scalars(
                select(Unit)
                .where(Unit.course_id == course.id)
                .order_by(Unit.order)
            )
        )
        assert [u.order for u in units] == [1, 2]
        second_unit = units[1]
        assert second_unit.title == "Second unit"
        second_lesson = db.scalar(
            select(Lesson).where(Lesson.unit_id == second_unit.id)
        )
        assert second_lesson is not None
        second_exercise = db.scalar(
            select(Exercise).where(Exercise.lesson_id == second_lesson.id)
        )
        assert second_exercise is not None
        assert second_exercise.correct_response == "dag"

        # Reimporting again with the SAME two units is a true no-op --
        # nothing new to append, no duplicate units created.
        created, errors, counters = import_content(
            db,
            ImportRequest.model_validate(
                {"courses": [course_payload_with_second_unit(title)]}
            ),
        )
        assert created == 0
        assert errors == []
        units_after_repeat = list(
            db.scalars(select(Unit).where(Unit.course_id == course.id))
        )
        assert len(units_after_repeat) == 2
