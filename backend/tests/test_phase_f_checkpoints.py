import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    CheckpointAttempt,
    Lesson,
    Lexeme,
    PracticeItem,
    PracticeTemplate,
    Unit,
    UserLexemeSRS,
)
from app.review.grading import (
    grade_answer,
    FREE_TEXT_EXERCISE_TYPES,
    MIN_ANSWER_LENGTH_FOR_TYPO_TOLERANCE,
)
from test_endless_practice import (
    artifact,
    create_course_with_lexemes,
    import_templates,
)


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def start_checkpoint(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(
        client,
        admin,
        course_id,
        artifact(include_listen=False),
    )
    with SessionLocal() as db:
        unit_id = db.scalar(
            select(Unit.id).where(Unit.course_id == course_id)
        )

    response = client.post(
        f"/units/{unit_id}/checkpoint",
        headers=auth,
    )
    assert response.status_code == 200, response.text
    return course_id, lesson_id, unit_id, response.json()["items"]


def answer_item(client, auth, item_id, correct):
    with SessionLocal() as db:
        item = db.get(PracticeItem, item_id)
        response = item.correct_response if correct else "__wrong__"

    result = client.post(
        f"/practice/items/{item_id}/answer",
        headers=auth,
        json={"response": response},
    )
    assert result.status_code == 200, result.text
    return result


def answer_all(client, auth, items, correct_count):
    for index, item in enumerate(items):
        answer_item(
            client,
            auth,
            item["id"],
            correct=index < correct_count,
        )


def test_checkpoint_generation_has_expected_count_and_session(
    client,
    admin,
    auth,
):
    _, _, _, items = start_checkpoint(client, admin, auth)

    assert 12 <= len(items) <= 15

    with SessionLocal() as db:
        rows = [
            db.get(PracticeItem, item["id"])
            for item in items
        ]
        assert all(row.source == "checkpoint" for row in rows)
        assert all(row.session_id is not None for row in rows)
        assert len({row.session_id for row in rows}) == 1

        checkpoint = db.get(CheckpointAttempt, rows[0].session_id)
        assert checkpoint is not None
        assert checkpoint.total_items == len(items)
        assert checkpoint.passed is None
        assert checkpoint.scored_at is None


def test_checkpoint_answer_never_updates_srs_per_item(
    client,
    admin,
    auth,
):
    course_id, _, _, items = start_checkpoint(client, admin, auth)
    uid = user_id(auth)

    with SessionLocal() as db:
        before = db.scalar(
            select(func.count(UserLexemeSRS.id)).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.course_id == course_id,
            )
        )
        assert before == 0

    answer_item(client, auth, items[0]["id"], correct=True)

    with SessionLocal() as db:
        after = db.scalar(
            select(func.count(UserLexemeSRS.id)).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.course_id == course_id,
            )
        )
        assert after == 0


def test_checkpoint_forces_strict_orthography(
    client,
    admin,
    auth,
):
    _, _, _, items = start_checkpoint(client, admin, auth)

    # Real, previously-flaky bug (found live 2026-07-06, root-caused
    # here): this used to accept `fill_in_blank` as an interchangeable
    # candidate alongside `translation`, but grade_answer()/
    # FREE_TEXT_EXERCISE_TYPES deliberately excludes fill_in_blank from
    # typo tolerance (its correct_response shape isn't reliably plain
    # free text by exercise-type name alone - see grading.py's own
    # comment) - grade_answer(..., exercise_type="fill_in_blank", ...)
    # always returns "incorrect" regardless of edit distance. Whenever
    # checkpoint generation happened to sample a fill_in_blank item
    # before a translation item, this test picked the wrong kind of
    # candidate and failed despite nothing being broken. Restricting to
    # an actual FREE_TEXT_EXERCISE_TYPES member fixes it at the root
    # instead of by chance of sampling order.
    selected = None
    with SessionLocal() as db:
        for output_item in items:
            item = db.get(PracticeItem, output_item["id"])
            template = db.get(PracticeTemplate, item.template_id)
            if (
                template.type in FREE_TEXT_EXERCISE_TYPES
                and isinstance(item.correct_response, str)
                # Must be long enough that typo tolerance applies at all:
                # answers under MIN_ANSWER_LENGTH_FOR_TYPO_TOLERANCE
                # (2026-07-10 short-answer exact-match floor, see
                # grading.is_too_short_for_typo_tolerance()) grade
                # "incorrect" on ANY mismatch, which would break this
                # test's "almost" precondition whenever sampling happened
                # to pick a 2-3 character answer - same flakiness class as
                # the fill_in_blank sampling bug described above.
                and len(item.correct_response.strip())
                >= MIN_ANSWER_LENGTH_FOR_TYPO_TOLERANCE
            ):
                selected = (
                    item.id,
                    template.type,
                    item.correct_response,
                )
                break

    assert selected is not None
    item_id, exercise_type, correct_response = selected
    typo = (
        correct_response[1]
        + correct_response[0]
        + correct_response[2:]
    )
    assert typo != correct_response
    assert (
        grade_answer(
            typo,
            correct_response,
            exercise_type=exercise_type,
            script="latin",
        )
        == "almost"
    )

    response = client.post(
        f"/practice/items/{item_id}/answer",
        headers=auth,
        json={"response": typo},
    )
    assert response.status_code == 200, response.text
    assert response.json()["correct"] is False
    assert response.json()["result"] == "incorrect"


def test_passing_checkpoint_consolidates_all_untracked_unit_lexemes(
    client,
    admin,
    auth,
):
    course_id, _, unit_id, items = start_checkpoint(
        client,
        admin,
        auth,
    )
    uid = user_id(auth)

    with SessionLocal() as db:
        checkpoint_items = list(
            db.scalars(
                select(PracticeItem).where(
                    PracticeItem.id.in_(
                        [item["id"] for item in items]
                    )
                )
            )
        )
        covered = {
            item.target_lexeme_id
            for item in checkpoint_items
            if item.target_lexeme_id is not None
        }
        assert covered
        all_unit_lexeme_ids = set(
            db.scalars(
                select(Lexeme.id)
                .join(Lesson, Lesson.id == Lexeme.provenance_lesson_id)
                .where(Lesson.unit_id == unit_id)
            )
        )
        assert covered < all_unit_lexeme_ids

        existing_lexeme_id = sorted(covered)[0]
        existing_due_at = datetime.now(timezone.utc) + timedelta(days=11)
        existing = UserLexemeSRS(
            user_id=uid,
            lexeme_id=existing_lexeme_id,
            course_id=course_id,
            ease_factor=2.1,
            interval_days=11,
            repetitions=4,
            mastery=0.73,
            due_at=existing_due_at,
            last_reviewed_at=None,
            introduced_at=datetime.now(timezone.utc) - timedelta(days=20),
            suspended=False,
            last_session_id=None,
        )
        db.add(existing)
        db.commit()
        existing_id = existing.id

    correct_count = math.ceil(len(items) * 0.8)
    answer_all(client, auth, items, correct_count)
    before_result = datetime.now(timezone.utc)

    result = client.get(
        f"/units/{unit_id}/checkpoint/result",
        headers=auth,
    )
    after_result = datetime.now(timezone.utc)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "complete"
    assert body["passed"] is True
    assert body["score"] >= 0.8
    assert body["checkpoint_passed"] is True

    with SessionLocal() as db:
        existing = db.get(UserLexemeSRS, existing_id)
        assert existing.mastery == 0.73
        assert existing.due_at == existing_due_at
        assert existing.interval_days == 11
        assert existing.repetitions == 4
        assert existing.last_reviewed_at is None

        rows = list(
            db.scalars(
                select(UserLexemeSRS).where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.lexeme_id.in_(all_unit_lexeme_ids),
                )
            )
        )
        assert {row.lexeme_id for row in rows} == all_unit_lexeme_ids

        covered_new_rows = [
            row
            for row in rows
            if (
                row.lexeme_id in covered
                and row.lexeme_id != existing_lexeme_id
            )
        ]
        assert covered_new_rows
        assert all(row.mastery >= 0.5 for row in covered_new_rows)
        assert all(row.interval_days == 3 for row in covered_new_rows)
        assert all(row.repetitions == 1 for row in covered_new_rows)
        assert all(
            before_result + timedelta(days=3)
            <= row.due_at
            <= after_result + timedelta(days=3)
            for row in covered_new_rows
        )

        uncovered_rows = [
            row for row in rows if row.lexeme_id not in covered
        ]
        assert uncovered_rows
        assert all(row.mastery == 0.3 for row in uncovered_rows)
        assert all(row.interval_days == 1 for row in uncovered_rows)
        assert all(row.repetitions == 0 for row in uncovered_rows)
        assert all(row.last_reviewed_at is None for row in uncovered_rows)
        assert all(
            before_result + timedelta(days=1)
            <= row.due_at
            <= after_result + timedelta(days=1)
            for row in uncovered_rows
        )

    units = client.get(
        f"/courses/{course_id}/units",
        headers=auth,
    )
    assert units.status_code == 200, units.text
    unit = next(row for row in units.json() if row["id"] == unit_id)
    assert unit["checkpoint_passed"] is True


def test_failing_checkpoint_does_not_touch_srs_and_reports_weak_outcomes(
    client,
    admin,
    auth,
):
    course_id, _, unit_id, items = start_checkpoint(
        client,
        admin,
        auth,
    )
    uid = user_id(auth)

    answer_all(client, auth, items, correct_count=0)

    result = client.get(
        f"/units/{unit_id}/checkpoint/result",
        headers=auth,
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "complete"
    assert body["passed"] is False
    assert body["score"] == 0
    assert body["weak_outcomes"]
    assert body["checkpoint_passed"] is False

    with SessionLocal() as db:
        count = db.scalar(
            select(func.count(UserLexemeSRS.id)).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.course_id == course_id,
            )
        )
        assert count == 0


def test_checkpoint_retake_delay_and_expiry(
    client,
    admin,
    auth,
):
    _, _, unit_id, items = start_checkpoint(client, admin, auth)
    uid = user_id(auth)

    answer_all(client, auth, items, correct_count=0)
    result = client.get(
        f"/units/{unit_id}/checkpoint/result",
        headers=auth,
    )
    assert result.status_code == 200, result.text
    assert result.json()["passed"] is False

    blocked = client.post(
        f"/units/{unit_id}/checkpoint",
        headers=auth,
    )
    assert blocked.status_code == 429, blocked.text
    # This app's global HTTPException handler wraps detail under "error",
    # not FastAPI's default "detail" key - see app/main.py.
    detail = blocked.json()["error"]
    assert detail["code"] == "checkpoint_retake_delayed"
    assert detail["retry_after_seconds"] > 0

    with SessionLocal() as db:
        latest = db.scalar(
            select(CheckpointAttempt)
            .where(
                CheckpointAttempt.user_id == uid,
                CheckpointAttempt.unit_id == unit_id,
            )
            .order_by(
                CheckpointAttempt.created_at.desc(),
                CheckpointAttempt.id.desc(),
            )
            .limit(1)
        )
        latest.created_at = (
            datetime.now(timezone.utc)
            - timedelta(hours=1, seconds=1)
        )
        db.commit()

    allowed = client.post(
        f"/units/{unit_id}/checkpoint",
        headers=auth,
    )
    assert allowed.status_code == 200, allowed.text
    assert 12 <= len(allowed.json()["items"]) <= 15
