from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import PracticeItem, Unit, User
from app.scripts.checkpoint_coverage import (
    CHECKPOINT_MIN_ITEMS,
    PROBE_USER_ID,
    UnitCoverage,
    format_report,
    measure,
    parse_direction,
    summarize,
)
from test_endless_practice import (
    artifact,
    create_course_with_lexemes,
    import_templates,
)


def _key_units(course_id):
    # Authored courses carry unit content keys; the bootstrap demo courses
    # do not, and the probe skips those by default.
    with SessionLocal() as db:
        for unit in db.scalars(select(Unit).where(Unit.course_id == course_id)):
            unit.content_key = f"test.coverage.{uuid4().hex[:12]}"
        db.commit()


def _practice_item_count(course_id):
    with SessionLocal() as db:
        return db.scalar(
            select(func.count(PracticeItem.id)).where(
                PracticeItem.course_id == course_id
            )
        )


def test_unit_with_practice_pack_is_available_and_nothing_persists(client, admin):
    course_id, _ = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    _key_units(course_id)

    with SessionLocal() as db:
        results = measure(db, directions=None, course_ids=[course_id])

    assert len(results) == 1
    assert results[0].direction == "en-es"
    assert results[0].items >= CHECKPOINT_MIN_ITEMS
    assert results[0].available

    # The probe runs inside a rolled-back transaction: no practice items,
    # no probe user left behind.
    assert _practice_item_count(course_id) == 0
    with SessionLocal() as db:
        assert db.get(User, PROBE_USER_ID) is None


def test_unit_without_practice_pack_is_unavailable():
    course_id, _ = create_course_with_lexemes()
    _key_units(course_id)

    with SessionLocal() as db:
        results = measure(db, directions=None, course_ids=[course_id])

    assert [result.items for result in results] == [0]
    assert not results[0].available
    assert "unavailable" in format_report(results)


def test_unkeyed_courses_are_skipped_unless_requested(client, admin):
    course_id, _ = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))

    with SessionLocal() as db:
        assert measure(db, directions=None, course_ids=[course_id]) == []
    with SessionLocal() as db:
        results = measure(
            db, directions=None, course_ids=[course_id], include_unkeyed=True
        )
    assert len(results) == 1 and results[0].available


def test_direction_filter_matches_source_and_target():
    course_id, _ = create_course_with_lexemes(source="en", target="es")
    _key_units(course_id)

    with SessionLocal() as db:
        assert measure(db, directions=["es-en"], course_ids=[course_id]) == []
    with SessionLocal() as db:
        assert len(measure(db, directions=["en-es"], course_ids=[course_id])) == 1


def test_parse_direction_rejects_malformed_values():
    assert parse_direction("prs-en") == ("prs", "en")
    for bad in ("en", "-en", "en-", ""):
        with pytest.raises(ValueError):
            parse_direction(bad)


def test_summary_counts_per_direction_and_overall():
    def unit(direction, items):
        return UnitCoverage(direction, "A1", "Course", 1, None, "Unit", items)

    results = [unit("en-nl", 15), unit("en-nl", 11), unit("fa-en", 12)]
    summary = summarize(results)

    assert summary["en-nl"] == {"available": 1, "total": 2}
    assert summary["fa-en"] == {"available": 1, "total": 1}
    assert summary["overall"] == {"available": 2, "total": 3}
    report = format_report(results)
    assert "overall    2/3 (66.7%)" in report
    assert "en-nl A1 Course #1: 11" in report
