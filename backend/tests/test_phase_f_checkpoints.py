import math
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select

from app.content.service import import_content
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    CheckpointAttempt,
    Course,
    Lesson,
    Lexeme,
    PracticeItem,
    PracticeTemplate,
    Unit,
    UserLexemeSRS,
)
from app.practice.service import (
    PRODUCTION_TYPES,
    RECOGNITION_TYPES,
    STRUCTURED_TYPES,
)
from app.review.grading import grade_answer, FREE_TEXT_EXERCISE_TYPES
from app.schemas.api import ImportRequest
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
                and len(item.correct_response) >= 2
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


# --- Checkpoint calibration (2026-07-10 pedagogy-review fix) ---------------
#
# generate_checkpoint() used to delegate to _generate_prioritized(), which
# (a) sampled the learner's due/weakest lexemes first (so two learners or
# two attempts could face materially different samples, with whole lessons
# unrepresented) and (b) picked exercise-format difficulty from live
# per-lexeme mastery via _tier_order() (so weak learners got easier
# recognition-heavy formats against the same fixed 80% pass bar). The tests
# below pin the fixed behavior: stratified lesson coverage, and a fixed
# CHECKPOINT_MASTERY_BANDS difficulty mix that ignores SRS state entirely.

CKPT_LESSON_KEYS = (
    "test.ckpt.lesson.001",
    "test.ckpt.lesson.002",
    "test.ckpt.lesson.003",
)


def create_multi_lesson_course(lexemes_per_lesson=6):
    """One unit whose material is spread across THREE lessons.

    Unlike test_endless_practice.create_course_with_lexemes() (a single
    lesson, useless for coverage assertions), every lexeme here matches
    the shared noun/"word" slot the artifact() templates use, so any
    lexeme is a viable target for every template -- the only thing that
    distinguishes lessons is provenance, which is exactly what the
    stratification test needs to observe.
    """
    title = f"Checkpoint stratification test {uuid4()}"
    payload = {
        "courses": [
            {
                "source_language": "en",
                "target_language": "es",
                "title": title,
                "units": [
                    {
                        "title": "Unit",
                        "order": 1,
                        "lessons": [
                            {
                                "title": f"Lesson {index + 1}",
                                "order": index + 1,
                                "exercises": [
                                    {
                                        "type": "translation",
                                        "order": 1,
                                        "prompt": {
                                            "text_blocks": [
                                                {
                                                    "text": "test",
                                                    "language_code": "en",
                                                    "direction": "ltr",
                                                }
                                            ]
                                        },
                                        "correct_response": "test",
                                    }
                                ],
                            }
                            for index in range(len(CKPT_LESSON_KEYS))
                        ],
                    }
                ],
            }
        ]
    }
    with SessionLocal() as db:
        count, errors, _ = import_content(
            db, ImportRequest.model_validate(payload)
        )
        assert count == 1 and not errors
        course = db.scalar(select(Course).where(Course.title == title))
        lessons = list(
            db.scalars(
                select(Lesson)
                .join(Unit)
                .where(Unit.course_id == course.id)
                .order_by(Lesson.order)
            )
        )
        assert len(lessons) == len(CKPT_LESSON_KEYS)
        token_index = 0
        for lesson, lesson_key in zip(lessons, CKPT_LESSON_KEYS):
            for _ in range(lexemes_per_lesson):
                token_index += 1
                db.add(
                    Lexeme(
                        course_id=course.id,
                        token=f"palabra{token_index}",
                        language_code="es",
                        part_of_speech="noun",
                        english_gloss=f"word{token_index}",
                        agreement_tags={"semantic": "word"},
                        provenance_lesson_id=lesson.id,
                        provenance_lesson_content_key=lesson_key,
                        provenance_content_key=(
                            f"test.ckpt.lexeme.{token_index}"
                        ),
                    )
                )
        db.commit()
        unit_id = db.scalar(
            select(Unit.id).where(Unit.course_id == course.id)
        )
        return course.id, unit_id, [lesson.id for lesson in lessons]


def multi_lesson_checkpoint_setup(client, admin):
    course_id, unit_id, lesson_ids = create_multi_lesson_course()
    body = artifact(include_listen=False)
    for template in body["packs"][0]["templates"]:
        # Template->lesson resolution goes through
        # Lexeme.provenance_lesson_content_key; any one lesson in the
        # unit works, since _material() gathers templates unit-wide.
        template["lesson_content_key"] = CKPT_LESSON_KEYS[0]
    import_templates(client, admin, course_id, body)
    return course_id, unit_id, lesson_ids


def register_second_user(client):
    email = f"user-{os.urandom(4).hex()}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "display_name": "Second Test User",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def seed_srs_for_all_course_lexemes(auth, course_id, mastery, due_in_days):
    with SessionLocal() as db:
        lexeme_ids = list(
            db.scalars(
                select(Lexeme.id).where(Lexeme.course_id == course_id)
            )
        )
        assert lexeme_ids
        for lexeme_id in lexeme_ids:
            db.add(
                UserLexemeSRS(
                    user_id=user_id(auth),
                    lexeme_id=lexeme_id,
                    course_id=course_id,
                    ease_factor=2.5,
                    interval_days=1,
                    repetitions=2,
                    mastery=mastery,
                    due_at=(
                        datetime.now(timezone.utc)
                        + timedelta(days=due_in_days)
                    ),
                    last_reviewed_at=None,
                    introduced_at=(
                        datetime.now(timezone.utc) - timedelta(days=5)
                    ),
                    suspended=False,
                    last_session_id=None,
                )
            )
        db.commit()


TIER_BY_TYPE = (
    {name: "recognition" for name in RECOGNITION_TYPES}
    | {name: "structured" for name in STRUCTURED_TYPES}
    | {name: "production" for name in PRODUCTION_TYPES}
)


def tier_distribution(items):
    counts = {"recognition": 0, "structured": 0, "production": 0}
    for item in items:
        counts[TIER_BY_TYPE[item["type"]]] += 1
    return counts


def test_checkpoint_items_are_stratified_across_unit_lessons(
    client,
    admin,
    auth,
):
    _, unit_id, lesson_ids = multi_lesson_checkpoint_setup(client, admin)

    response = client.post(f"/units/{unit_id}/checkpoint", headers=auth)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert 12 <= len(items) <= 15

    lesson_counts = {lesson_id: 0 for lesson_id in lesson_ids}
    with SessionLocal() as db:
        for output_item in items:
            item = db.get(PracticeItem, output_item["id"])
            lexeme = db.get(Lexeme, item.target_lexeme_id)
            lesson_counts[lexeme.provenance_lesson_id] += 1

    # Round-robin stratification: every lesson represented, no lesson
    # clustered on. With 12-15 items over 3 equally-sized lessons the
    # split is 4/4/4 to 5/5/5 when every generation attempt succeeds;
    # the small tolerance below only absorbs occasional per-attempt
    # generation retries (which advance the target cursor but not the
    # item count), not any real clustering.
    assert all(count > 0 for count in lesson_counts.values())
    floor_share = len(items) // len(lesson_ids)
    assert all(
        count >= floor_share - 1 for count in lesson_counts.values()
    ), lesson_counts
    assert (
        max(lesson_counts.values()) - min(lesson_counts.values()) <= 2
    ), lesson_counts


def test_checkpoint_format_mix_is_consistent_regardless_of_mastery(
    client,
    admin,
    auth,
):
    course_id, unit_id, _ = multi_lesson_checkpoint_setup(client, admin)

    weak_auth = auth
    strong_auth = register_second_user(client)

    # Weak learner: every unit lexeme tracked at rock-bottom mastery and
    # overdue -- under the old adaptive path this produced an all-
    # recognition (easiest) checkpoint. Strong learner: everything
    # tracked at near-max mastery, nothing due -- old path produced an
    # all-production checkpoint. Same course, same unit, same pass bar.
    seed_srs_for_all_course_lexemes(
        weak_auth, course_id, mastery=0.05, due_in_days=-1
    )
    seed_srs_for_all_course_lexemes(
        strong_auth, course_id, mastery=0.95, due_in_days=30
    )

    weak = client.post(f"/units/{unit_id}/checkpoint", headers=weak_auth)
    assert weak.status_code == 200, weak.text
    strong = client.post(
        f"/units/{unit_id}/checkpoint", headers=strong_auth
    )
    assert strong.status_code == 200, strong.text

    weak_counts = tier_distribution(weak.json()["items"])
    strong_counts = tier_distribution(strong.json()["items"])

    # Criterion-referenced: the difficulty mix comes from the fixed
    # CHECKPOINT_MASTERY_BANDS cycle, identical for every learner --
    # per-lexeme mastery state must not shift it in either direction.
    assert weak_counts == strong_counts, (weak_counts, strong_counts)
    # And that shared mix genuinely spans all three tiers (a 15-item
    # checkpoint cycling 3 bands puts 5 items in each; >=4 leaves room
    # only for per-attempt generation retries, not a skewed test).
    for counts in (weak_counts, strong_counts):
        assert all(count >= 4 for count in counts.values()), counts
