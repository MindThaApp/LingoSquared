from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Course, Exercise, Lesson, Unit


def keyed_payload(title, exercises, retire_missing=True):
    return {
        "retire_missing": retire_missing,
        "courses": [
            {
                "source_language": "en",
                "target_language": "es",
                "title": title,
                "units": [
                    {
                        "title": "Unit",
                        "order": 1,
                        "content_key": "unit.1",
                        "lessons": [
                            {
                                "title": "Lesson",
                                "order": 1,
                                "content_key": "lesson.1",
                                "exercises": exercises,
                            }
                        ],
                    }
                ],
            }
        ],
    }


def exercise(order, text, content_key=None):
    row = {
        "type": "translation",
        "order": order,
        "prompt": {
            "text_blocks": [
                {"text": text, "language_code": "en", "direction": "ltr"}
            ]
        },
        "correct_response": "respuesta",
    }
    if content_key is not None:
        row["content_key"] = content_key
    return row


def import_payload(client, admin, payload):
    response = client.post("/admin/content/import", headers=admin, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_import_retires_keyed_exercise_preserves_unkeyed_and_reactivates(client, admin, auth):
    title = "Exercise retirement lifecycle"
    first = keyed_payload(
        title,
        [
            exercise(1, "one", "exercise.one"),
            exercise(2, "two", "exercise.two"),
            exercise(3, "legacy"),
        ],
    )
    import_payload(client, admin, first)

    with SessionLocal() as db:
        course = db.scalar(select(Course).where(Course.title == title))
        unit = db.scalar(select(Unit).where(Unit.course_id == course.id))
        lesson_row = db.scalar(select(Lesson).where(Lesson.unit_id == unit.id))
        removed = db.scalar(
            select(Exercise).where(Exercise.content_key == "exercise.two")
        )
        legacy = db.scalar(
            select(Exercise).where(
                Exercise.lesson_id == lesson_row.id,
                Exercise.content_key.is_(None),
            )
        )
        removed_id, legacy_id, lesson_id, unit_id = (
            removed.id,
            legacy.id,
            lesson_row.id,
            unit.id,
        )

    retired = import_payload(
        client,
        admin,
        keyed_payload(title, [exercise(1, "one updated", "exercise.one")]),
    )
    assert retired["retired_exercises"] == 1
    assert retired["unretired_exercises"] == 0

    with SessionLocal() as db:
        removed = db.get(Exercise, removed_id)
        legacy = db.get(Exercise, legacy_id)
        assert removed.retired_at is not None
        assert legacy.retired_at is None

    lesson_list = client.get(f"/units/{unit_id}/lessons").json()
    assert lesson_list[0]["exercise_count"] == 2
    detail = client.get(f"/lessons/{lesson_id}").json()
    assert removed_id not in {item["id"] for item in detail["exercises"]}

    answer = client.post(
        f"/exercises/{removed_id}/answer",
        headers=auth,
        json={"response": "respuesta"},
    )
    assert answer.status_code == 200, answer.text

    restored = import_payload(
        client,
        admin,
        keyed_payload(
            title,
            [
                exercise(1, "one updated", "exercise.one"),
                exercise(2, "two restored", "exercise.two"),
            ],
        ),
    )
    assert restored["unretired_exercises"] == 1
    with SessionLocal() as db:
        assert db.get(Exercise, removed_id).retired_at is None


def test_retire_missing_false_preserves_old_behavior_and_zero_counters(client, admin):
    title = "Exercise retirement opt out"
    import_payload(
        client,
        admin,
        keyed_payload(
            title,
            [exercise(1, "one", "exercise.one"), exercise(2, "two", "exercise.two")],
        ),
    )
    result = import_payload(
        client,
        admin,
        keyed_payload(
            title,
            [exercise(1, "one changed", "exercise.one")],
            retire_missing=False,
        ),
    )
    assert result["retired_exercises"] == 0
    assert result["unretired_exercises"] == 0
    with SessionLocal() as db:
        remaining = db.scalar(
            select(Exercise).where(Exercise.content_key == "exercise.two")
        )
        assert remaining.retired_at is None
