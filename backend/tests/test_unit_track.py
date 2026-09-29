from uuid import uuid4

from sqlalchemy import inspect, select

from app.api.router import first_placement_unit, speaking_unlocked
from app.db.session import SessionLocal, engine
from app.models import Course, Lesson, LessonProgress, Unit, UnitSection, User
from app.schemas.api import UnitOut


def _course(db):
    course = Course(
        source_language="en",
        target_language="es",
        title=f"Unit track {uuid4()}",
    )
    db.add(course)
    db.flush()
    return course


def _unit(db, course, order, key, track="core", section=UnitSection.reading_writing):
    unit = Unit(
        course_id=course.id,
        title=key,
        order=order,
        content_key=key,
        track=track,
        section=section,
    )
    db.add(unit)
    db.flush()
    return unit


def test_unit_track_column_has_core_server_default():
    column = next(c for c in inspect(engine).get_columns("units") if c["name"] == "track")
    assert column["nullable"] is False
    assert "core" in column["default"]


def test_speaking_unlock_ignores_incomplete_situation_unit():
    with SessionLocal() as db:
        course = _course(db)
        core = _unit(db, course, 1, "en.a1.unit01.core")
        side = _unit(db, course, 2, "en.a1.unit02.side", "situation")
        speaking = _unit(db, course, 3, "en.a1.unit03.speaking", section=UnitSection.speaking)
        core_lesson = Lesson(unit_id=core.id, title="Core", order=1)
        Lesson(unit_id=side.id, title="Side", order=1)
        user = User(email=f"track-{uuid4()}@example.com", password_hash="test-only")
        db.add(user)
        db.add(core_lesson)
        db.flush()
        db.add(LessonProgress(user_id=user.id, lesson_id=core_lesson.id, completed_at=None))
        db.flush()
        # Set completion on the row to exercise the unlock query's real predicate.
        progress = db.scalar(select(LessonProgress).where(LessonProgress.lesson_id == core_lesson.id))
        from datetime import datetime, timezone
        progress.completed_at = datetime.now(timezone.utc)
        db.flush()
        assert speaking_unlocked(db, course.id, progress.user_id, speaking.order)


def test_first_placement_unit_skips_situation_units():
    with SessionLocal() as db:
        course = _course(db)
        _unit(db, course, 1, "en.a1.unit01.side", "situation")
        core = _unit(db, course, 2, "en.a1.unit02.core")
        assert first_placement_unit(db, course.id, "A1").id == core.id


def test_unit_out_includes_track():
    output = UnitOut.model_validate(
        {
            "id": "unit-id",
            "title": "Optional practice",
            "order": 1,
            "lesson_count": 0,
            "section": "reading_writing",
            "locked": False,
            "track": "situation",
        }
    )
    assert output.track == "situation"
