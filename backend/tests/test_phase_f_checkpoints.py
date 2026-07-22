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
from app.review.grading import (
    grade_answer,
    FREE_TEXT_EXERCISE_TYPES,
    MIN_ANSWER_LENGTH_FOR_TYPO_TOLERANCE,
)
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


# --- Checkpoint lexeme SCOPE (2026-07-22 fix) ------------------------------
#
# generate_checkpoint() passed ONLY the unit's own lesson ids to _material(),
# which filters both templates AND lexemes by provenance_lesson_id -- while
# generate_batch() passes every completed lesson. A unit template whose
# supporting slot is constrained to vocabulary taught in an EARLIER unit
# therefore had zero candidates for that slot at checkpoint scope, so
# fill_slots() returned None for every target and the unit could not reach
# the 12-item floor -- even though the identical template works in Endless
# Practice. Measured over the six launch directions, only ~48% of units
# could generate a checkpoint.
#
# The fix widens the pool ONLY as a fallback, and never lets the widening
# change what is actually being tested:
#   * templates stay unit-scoped, targets stay unit lexemes;
#   * pass 1 uses unit vocabulary alone (unchanged behavior);
#   * pass 2 widens to the course prefix purely to fill supporting slots,
#     and requires each item's GRADED answer to touch unit material;
#   * repeats are never used to reach 12 within one checkpoint.
# The tests below pin all four.

SCOPE_PRIOR_LESSON_KEY = "test.ckpt.scope.prior.lesson"
SCOPE_UNIT_LESSON_KEY = "test.ckpt.scope.unit.lesson"

SCOPE_WORD_SLOT = {
    "language_code": "es",
    "part_of_speech": "noun",
    "agreement_tags": {"semantic": "word"},
}
SCOPE_PLACE_SLOT = {
    "language_code": "es",
    "part_of_speech": "adverb",
    "agreement_tags": {"semantic": "place"},
}


def create_two_unit_course(unit_nouns=8, prior_adverbs=4, unit_tags=None):
    """Unit 2 is the unit under test; unit 1 holds the PRIOR vocabulary.

    Unit 2's own lexemes are all nouns tagged semantic=word; the adverbs
    tagged semantic=place exist ONLY in unit 1. A unit-2 template with a
    `place` slot is therefore unbuildable from unit-2 material alone --
    exactly the shape that used to make a checkpoint impossible.
    """
    title = f"Checkpoint scope test {uuid4()}"
    exercise = {
        "type": "translation",
        "order": 1,
        "prompt": {
            "text_blocks": [
                {"text": "test", "language_code": "en", "direction": "ltr"}
            ]
        },
        "correct_response": "test",
    }
    payload = {
        "courses": [
            {
                "source_language": "en",
                "target_language": "es",
                "title": title,
                "units": [
                    {
                        "title": "Prior unit",
                        "order": 1,
                        "lessons": [
                            {
                                "title": "Prior lesson",
                                "order": 1,
                                "exercises": [exercise],
                            }
                        ],
                    },
                    {
                        "title": "Unit under test",
                        "order": 2,
                        "lessons": [
                            {
                                "title": "Unit lesson",
                                "order": 1,
                                "exercises": [exercise],
                            }
                        ],
                    },
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
        units = list(
            db.scalars(
                select(Unit)
                .where(Unit.course_id == course.id)
                .order_by(Unit.order)
            )
        )
        assert len(units) == 2
        prior_unit, unit = units
        prior_lesson_id = db.scalar(
            select(Lesson.id).where(Lesson.unit_id == prior_unit.id)
        )
        unit_lesson_id = db.scalar(
            select(Lesson.id).where(Lesson.unit_id == unit.id)
        )
        marker = uuid4().hex[:8]
        for index in range(prior_adverbs):
            db.add(
                Lexeme(
                    course_id=course.id,
                    token=f"lugar{index}",
                    language_code="es",
                    part_of_speech="adverb",
                    english_gloss=f"place{index}",
                    agreement_tags={"semantic": "place"},
                    provenance_lesson_id=prior_lesson_id,
                    provenance_lesson_content_key=SCOPE_PRIOR_LESSON_KEY,
                    provenance_content_key=(
                        f"test.ckpt.scope.prior.{marker}.{index}"
                    ),
                )
            )
        for index in range(unit_nouns):
            db.add(
                Lexeme(
                    course_id=course.id,
                    token=f"cosa{index}",
                    language_code="es",
                    part_of_speech="noun",
                    english_gloss=f"thing{index}",
                    agreement_tags=(
                        {"semantic": "word"} if unit_tags is None else unit_tags
                    ),
                    provenance_lesson_id=unit_lesson_id,
                    provenance_lesson_content_key=SCOPE_UNIT_LESSON_KEY,
                    provenance_content_key=(
                        f"test.ckpt.scope.unit.{marker}.{index}"
                    ),
                )
            )
        db.commit()
        return {
            "course_id": course.id,
            "unit_id": unit.id,
            "prior_unit_id": prior_unit.id,
            "unit_lesson_id": unit_lesson_id,
            "prior_lesson_id": prior_lesson_id,
        }


def scope_artifact(templates):
    return {
        "artifact_type": "lingosquared.practice_templates",
        "artifact_version": 1,
        "source_language": "en",
        "target_language": "es",
        "packs": [
            {
                "pack_key": f"test.ckpt.scope.pack.{uuid4().hex[:8]}",
                "unit_content_key": "test.ckpt.scope.unit",
                "tag_schema": {},
                "templates": templates,
            }
        ],
    }


def cross_unit_templates():
    """Unit-2 templates that all reference unit-1 vocabulary in a slot.

    Every answer derivation is anchored on `word` (a unit-2 noun); the
    `place` slot is supporting context only.
    """
    es_frame = {
        "text": "{word} {place}",
        "language_code": "es",
        "direction": "ltr",
    }
    return [
        {
            "content_key": "test.ckpt.scope.multiple_choice",
            "lesson_content_key": SCOPE_UNIT_LESSON_KEY,
            "type": "multiple_choice",
            "frame": dict(es_frame),
            "slots": {"word": SCOPE_WORD_SLOT, "place": SCOPE_PLACE_SLOT},
            "answer_derivation": {"kind": "slot_gloss", "slot": "word"},
            "feedback_frame": {
                "text": "Correct.",
                "language_code": "en",
                "direction": "ltr",
            },
        },
        {
            "content_key": "test.ckpt.scope.fill_in_blank",
            "lesson_content_key": SCOPE_UNIT_LESSON_KEY,
            "type": "fill_in_blank",
            "frame": {
                "text": "aqui {place} {word}",
                "language_code": "es",
                "direction": "ltr",
            },
            "slots": {"word": SCOPE_WORD_SLOT, "place": SCOPE_PLACE_SLOT},
            "answer_derivation": {"kind": "slot_text", "slot": "word"},
            "feedback_frame": {
                "text": "Correct.",
                "language_code": "en",
                "direction": "ltr",
            },
        },
        {
            "content_key": "test.ckpt.scope.word_order",
            "lesson_content_key": SCOPE_UNIT_LESSON_KEY,
            "type": "word_order",
            "frame": dict(es_frame),
            "slots": {"word": SCOPE_WORD_SLOT, "place": SCOPE_PLACE_SLOT},
            "answer_derivation": {
                "kind": "render_frame",
                "frame": dict(es_frame),
            },
            "feedback_frame": {
                "text": "Correct.",
                "language_code": "en",
                "direction": "ltr",
            },
        },
        {
            "content_key": "test.ckpt.scope.translation",
            "lesson_content_key": SCOPE_UNIT_LESSON_KEY,
            "type": "translation",
            "frame": {
                "text": "{word} {place}",
                "language_code": "en",
                "direction": "ltr",
                "slot_rendering": {
                    "word": "english_gloss",
                    "place": "english_gloss",
                },
            },
            "slots": {"word": SCOPE_WORD_SLOT, "place": SCOPE_PLACE_SLOT},
            "answer_derivation": {
                "kind": "render_frame",
                "frame": dict(es_frame),
            },
            "feedback_frame": {
                "text": "Correct.",
                "language_code": "en",
                "direction": "ltr",
            },
        },
    ]


def frame_teaching_templates():
    """The real fa-en `en.a1.unit14.communication` shape.

    A unit-2 template whose ONLY slot is constrained to unit-1
    vocabulary: the unit's own contribution is the frame text, and the
    slot recycles earlier-taught words. Reproduced here because that is
    the shape behind every one of the seven guaranteed-409 packs.
    """
    es_frame = {
        "text": "vamos {place}",
        "language_code": "es",
        "direction": "ltr",
    }
    return [
        {
            "content_key": "test.ckpt.scope.frame.word_order",
            "lesson_content_key": SCOPE_UNIT_LESSON_KEY,
            "type": "word_order",
            "frame": dict(es_frame),
            "slots": {"place": SCOPE_PLACE_SLOT},
            "answer_derivation": {
                "kind": "render_frame",
                "frame": dict(es_frame),
            },
            "feedback_frame": {
                "text": "Correct.",
                "language_code": "en",
                "direction": "ltr",
            },
        },
        {
            "content_key": "test.ckpt.scope.frame.translation",
            "lesson_content_key": SCOPE_UNIT_LESSON_KEY,
            "type": "translation",
            "frame": {
                "text": "we go {place}",
                "language_code": "en",
                "direction": "ltr",
                "slot_rendering": {"place": "english_gloss"},
            },
            "slots": {"place": SCOPE_PLACE_SLOT},
            "answer_derivation": {
                "kind": "render_frame",
                "frame": dict(es_frame),
            },
            "feedback_frame": {
                "text": "Correct.",
                "language_code": "en",
                "direction": "ltr",
            },
        },
        {
            "content_key": "test.ckpt.scope.frame.multiple_choice",
            "lesson_content_key": SCOPE_UNIT_LESSON_KEY,
            "type": "multiple_choice",
            "frame": dict(es_frame),
            "slots": {"place": SCOPE_PLACE_SLOT},
            "answer_derivation": {"kind": "slot_gloss", "slot": "place"},
            "feedback_frame": {
                "text": "Correct.",
                "language_code": "en",
                "direction": "ltr",
            },
        },
    ]


def prior_answer_templates():
    """Unit templates whose GRADED answer is prior vocabulary.

    A unit-2 noun can be forced into the `word` slot, so the item could
    claim to "target" unit material -- but the learner is graded purely
    on a unit-1 adverb. These must never be attributed to a unit lexeme.
    """
    es_frame = {
        "text": "{word} {place}",
        "language_code": "es",
        "direction": "ltr",
    }
    return [
        {
            "content_key": "test.ckpt.scope.prior_answer.multiple_choice",
            "lesson_content_key": SCOPE_UNIT_LESSON_KEY,
            "type": "multiple_choice",
            "frame": dict(es_frame),
            "slots": {"word": SCOPE_WORD_SLOT, "place": SCOPE_PLACE_SLOT},
            "answer_derivation": {"kind": "slot_gloss", "slot": "place"},
            "feedback_frame": {
                "text": "Correct.",
                "language_code": "en",
                "direction": "ltr",
            },
        },
        {
            "content_key": "test.ckpt.scope.prior_answer.fill_in_blank",
            "lesson_content_key": SCOPE_UNIT_LESSON_KEY,
            "type": "fill_in_blank",
            "frame": {
                "text": "aqui {word} {place}",
                "language_code": "es",
                "direction": "ltr",
            },
            "slots": {"word": SCOPE_WORD_SLOT, "place": SCOPE_PLACE_SLOT},
            "answer_derivation": {"kind": "slot_text", "slot": "place"},
            "feedback_frame": {
                "text": "Correct.",
                "language_code": "en",
                "direction": "ltr",
            },
        },
    ]


def scope_setup(client, admin, templates, **kwargs):
    ids = create_two_unit_course(**kwargs)
    import_templates(
        client,
        admin,
        ids["course_id"],
        scope_artifact(templates),
    )
    return ids


def unit_lexeme_ids(unit_id):
    with SessionLocal() as db:
        return set(
            db.scalars(
                select(Lexeme.id)
                .join(Lesson, Lesson.id == Lexeme.provenance_lesson_id)
                .where(Lesson.unit_id == unit_id)
            )
        )


def error_code(response):
    # app/main.py reshapes every HTTPException to {"error": {code, ...}}.
    return response.json()["error"]["code"]


def test_checkpoint_builds_when_template_needs_prior_unit_vocabulary(
    client,
    admin,
    auth,
):
    ids = scope_setup(client, admin, cross_unit_templates())
    unit_id = ids["unit_id"]

    # Precondition: unit-2 material ALONE cannot satisfy these templates.
    # Every `place` candidate lives in unit 1, so _base_slot_candidates()
    # is empty for that slot at the old unit-only scope -- this is the
    # exact 409 the fix targets.
    from app.practice.service import _base_slot_candidates

    with SessionLocal() as db:
        own_lexemes = list(
            db.scalars(
                select(Lexeme)
                .join(Lesson, Lesson.id == Lexeme.provenance_lesson_id)
                .where(Lesson.unit_id == unit_id)
            )
        )
        for template in db.scalars(
            select(PracticeTemplate).where(
                PracticeTemplate.course_id == ids["course_id"]
            )
        ):
            candidates = _base_slot_candidates(template, own_lexemes)
            assert not candidates["place"], template.content_key

    response = client.post(f"/units/{unit_id}/checkpoint", headers=auth)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert 12 <= len(items) <= 15

    own_ids = unit_lexeme_ids(unit_id)
    prior_ids = unit_lexeme_ids(ids["prior_unit_id"])
    assert own_ids and prior_ids and not (own_ids & prior_ids)

    with SessionLocal() as db:
        rows = [db.get(PracticeItem, item["id"]) for item in items]
        # Every item is TARGETED on the unit under test, never on the
        # earlier unit's vocabulary.
        assert all(row.target_lexeme_id in own_ids for row in rows)
        # ...and the earlier unit's vocabulary really was used, only as
        # supporting slot fill (otherwise this test would pass even with
        # the bug still present).
        prior_tokens = set(
            db.scalars(
                select(Lexeme.token).where(Lexeme.id.in_(prior_ids))
            )
        )
        assert any(
            set(row.filled_slots.values()) & prior_tokens for row in rows
        )
        assert all(row.source == "checkpoint" for row in rows)
        assert len({row.session_id for row in rows}) == 1


def test_checkpoint_target_attribution_implies_unit_material_in_answer(
    client,
    admin,
    auth,
):
    """The invariant the answer-scope guard buys.

    An item may only CLAIM a unit lexeme as its target_lexeme_id if that
    lexeme reaches the graded answer -- checkpoint_result() turns
    target_lexeme_id into SRS consolidation credit and into
    weak_outcomes, so attributing an item to a word the learner was never
    asked to produce would both mis-credit and mis-blame.
    """
    ids = scope_setup(client, admin, cross_unit_templates())
    response = client.post(
        f"/units/{ids['unit_id']}/checkpoint", headers=auth
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]

    from app.practice.service import _answer_slot_names

    own_ids = unit_lexeme_ids(ids["unit_id"])
    with SessionLocal() as db:
        own_tokens = set(
            db.scalars(select(Lexeme.token).where(Lexeme.id.in_(own_ids)))
        )
        attributed = 0
        for output_item in items:
            item = db.get(PracticeItem, output_item["id"])
            if item.target_lexeme_id is None:
                continue
            attributed += 1
            assert item.target_lexeme_id in own_ids
            template = db.get(PracticeTemplate, item.template_id)
            graded_tokens = {
                item.filled_slots[name]
                for name in _answer_slot_names(template)
                if name in item.filled_slots
            }
            assert graded_tokens & own_tokens, (
                template.content_key,
                item.filled_slots,
            )
    assert attributed == len(items)


def test_checkpoint_prefers_templates_that_grade_unit_material(
    client,
    admin,
    auth,
):
    # Both template families are the unit's own and both are buildable
    # once the pool is widened, but only one grades the learner on unit-2
    # vocabulary. The unit-material pass runs first, so the whole
    # checkpoint should come from that family and none from the family
    # that would grade a unit-1 adverb.
    ids = scope_setup(
        client,
        admin,
        cross_unit_templates() + prior_answer_templates(),
    )
    response = client.post(
        f"/units/{ids['unit_id']}/checkpoint", headers=auth
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert 12 <= len(items) <= 15

    with SessionLocal() as db:
        used = {
            db.get(
                PracticeTemplate,
                db.get(PracticeItem, item["id"]).template_id,
            ).content_key
            for item in items
        }
    assert used
    assert not any("prior_answer" in key for key in used), used


def test_frame_teaching_unit_generates_with_unattributed_targets(
    client,
    admin,
    auth,
):
    """The seven guaranteed-409 packs' actual shape.

    fa-en/prs-en/nl-en `en.a1.unit14.communication` (and unit17, and
    fa-en unit39) teach sentence frames; every slot in their unit-authored
    templates is constrained to a semantic tag whose vocabulary came from
    an earlier unit, and their own lexemes carry no agreement tags at all,
    so they match no slot and cannot even be generation targets. A
    checkpoint must still be possible -- the unit's own templates are what
    is being tested -- but nothing prior may be credited to the unit, so
    every such item stores a NULL target_lexeme_id.
    """
    ids = create_two_unit_course(unit_nouns=6, prior_adverbs=6, unit_tags={})
    import_templates(
        client,
        admin,
        ids["course_id"],
        scope_artifact(frame_teaching_templates()),
    )
    unit_id = ids["unit_id"]

    own_ids = unit_lexeme_ids(unit_id)
    with SessionLocal() as db:
        # Precondition: no unit lexeme matches any slot of any of the
        # unit's own templates, so it cannot be a target at all.
        from app.practice.service import lexeme_matches

        own = list(
            db.scalars(select(Lexeme).where(Lexeme.id.in_(own_ids)))
        )
        templates = list(
            db.scalars(
                select(PracticeTemplate).where(
                    PracticeTemplate.course_id == ids["course_id"]
                )
            )
        )
        assert own and templates
        assert not any(
            lexeme_matches(lexeme, constraints)
            for lexeme in own
            for template in templates
            for constraints in template.slots.values()
        )

    response = client.post(f"/units/{unit_id}/checkpoint", headers=auth)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert 12 <= len(items) <= 15

    with SessionLocal() as db:
        rows = [db.get(PracticeItem, item["id"]) for item in items]
        # Nothing prior is credited to this unit.
        assert all(row.target_lexeme_id is None for row in rows)
        # ...and every item is still built from the UNIT's own templates,
        # which is what makes it a test of this unit.
        unit_template_ids = set(
            db.scalars(
                select(PracticeTemplate.id)
                .join(
                    Lesson,
                    Lesson.id == PracticeTemplate.provenance_lesson_id,
                )
                .where(Lesson.unit_id == unit_id)
            )
        )
        assert unit_template_ids
        assert all(row.template_id in unit_template_ids for row in rows)


def test_frame_teaching_checkpoint_can_still_be_passed_and_scored(
    client,
    admin,
    auth,
):
    # A NULL target_lexeme_id must not break scoring or consolidation:
    # the pass still records, and every unit lexeme is seeded as
    # "uncovered" rather than credited as directly tested.
    ids = create_two_unit_course(unit_nouns=6, prior_adverbs=6, unit_tags={})
    import_templates(
        client,
        admin,
        ids["course_id"],
        scope_artifact(frame_teaching_templates()),
    )
    unit_id = ids["unit_id"]
    uid = user_id(auth)

    response = client.post(f"/units/{unit_id}/checkpoint", headers=auth)
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    answer_all(client, auth, items, math.ceil(len(items) * 0.8))

    result = client.get(
        f"/units/{unit_id}/checkpoint/result", headers=auth
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "complete"
    assert body["passed"] is True
    assert body["checkpoint_passed"] is True

    own_ids = unit_lexeme_ids(unit_id)
    prior_ids = unit_lexeme_ids(ids["prior_unit_id"])
    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(UserLexemeSRS).where(UserLexemeSRS.user_id == uid)
            )
        )
        seeded = {row.lexeme_id for row in rows}
        assert seeded == own_ids
        # Nothing from the earlier unit was credited by passing this one.
        assert not (seeded & prior_ids)
        assert all(row.mastery == 0.3 for row in rows)


def test_checkpoint_refuses_a_unit_whose_material_is_unusable(
    client,
    admin,
    auth,
):
    # Templates exist and are the unit's own, but NO lexeme anywhere in
    # the course prefix satisfies their slot: nothing can be built, and
    # the endpoint must fail cleanly rather than emit a short checkpoint.
    ids = create_two_unit_course(unit_nouns=4, prior_adverbs=0)
    import_templates(
        client,
        admin,
        ids["course_id"],
        scope_artifact(frame_teaching_templates()),
    )
    response = client.post(
        f"/units/{ids['unit_id']}/checkpoint", headers=auth
    )
    assert response.status_code == 409, response.text
    assert error_code(response) == "checkpoint_unavailable"

    uid = user_id(auth)
    with SessionLocal() as db:
        # Clean failure: the rolled-back attempt leaves nothing behind.
        assert (
            db.scalar(
                select(func.count(CheckpointAttempt.id)).where(
                    CheckpointAttempt.user_id == uid,
                    CheckpointAttempt.unit_id == ids["unit_id"],
                )
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count(PracticeItem.id)).where(
                    PracticeItem.user_id == uid,
                    PracticeItem.course_id == ids["course_id"],
                )
            )
            == 0
        )


def test_checkpoint_refuses_a_unit_with_no_material_at_all(
    client,
    admin,
    auth,
):
    # No practice templates imported for this course whatsoever.
    ids = create_two_unit_course()
    response = client.post(
        f"/units/{ids['unit_id']}/checkpoint", headers=auth
    )
    assert response.status_code == 409, response.text
    assert error_code(response) == "checkpoint_unavailable"


def test_checkpoint_does_not_pad_a_thin_unit_with_duplicates(
    client,
    admin,
    auth,
):
    # Two unit nouns and one buildable single-slot template: at most two
    # genuinely distinct items exist. multiple_choice needs >=3 options so
    # it cannot build at all here, leaving fill_in_blank's two fillings.
    # The old per-attempt escape hatch padded that to twelve visible
    # duplicates and passed the 409 gate; a 12-item floor met by repeating
    # the same two questions six times is not a gate at all.
    ids = create_two_unit_course(unit_nouns=2, prior_adverbs=2)
    import_templates(
        client,
        admin,
        ids["course_id"],
        scope_artifact(cross_unit_templates()[:2]),
    )
    response = client.post(
        f"/units/{ids['unit_id']}/checkpoint", headers=auth
    )
    assert response.status_code == 409, response.text
    assert error_code(response) == "checkpoint_unavailable"


def test_checkpoint_items_are_all_distinct(client, admin, auth):
    ids = scope_setup(client, admin, cross_unit_templates())
    response = client.post(
        f"/units/{ids['unit_id']}/checkpoint", headers=auth
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]

    from app.practice.service import _prompt_signature, _signature

    with SessionLocal() as db:
        rows = [db.get(PracticeItem, item["id"]) for item in items]
        slot_signatures = {
            _signature(row.template_id, row.filled_slots) for row in rows
        }
        visible_signatures = {
            _prompt_signature(row.prompt) for row in rows
        }
    assert len(slot_signatures) == len(items)
    assert len(visible_signatures) == len(items)


def test_widened_checkpoint_keeps_phase_f_invariants(
    client,
    admin,
    auth,
):
    """SRS untouched per item, strict orthography, idempotent attempt."""
    ids = scope_setup(client, admin, cross_unit_templates())
    course_id = ids["course_id"]
    unit_id = ids["unit_id"]
    uid = user_id(auth)

    response = client.post(f"/units/{unit_id}/checkpoint", headers=auth)
    assert response.status_code == 200, response.text
    items = response.json()["items"]

    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count(UserLexemeSRS.id)).where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
            )
            == 0
        )

    # Invariant 1: answering a checkpoint item never touches per-item SRS.
    answer_item(client, auth, items[0]["id"], correct=True)
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count(UserLexemeSRS.id)).where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
            )
            == 0
        )

    # Invariant 2: orthography_strict is forced, so a near-miss that
    # grade_answer() would call "almost" is still scored incorrect.
    selected = None
    with SessionLocal() as db:
        for output_item in items[1:]:
            item = db.get(PracticeItem, output_item["id"])
            template = db.get(PracticeTemplate, item.template_id)
            if (
                template.type in FREE_TEXT_EXERCISE_TYPES
                and isinstance(item.correct_response, str)
                and len(item.correct_response.strip())
                >= MIN_ANSWER_LENGTH_FOR_TYPO_TOLERANCE
            ):
                selected = (item.id, template.type, item.correct_response)
                break
    assert selected is not None
    item_id, exercise_type, correct_response = selected
    typo = correct_response[1] + correct_response[0] + correct_response[2:]
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
    strict = client.post(
        f"/practice/items/{item_id}/answer",
        headers=auth,
        json={"response": typo},
    )
    assert strict.status_code == 200, strict.text
    assert strict.json()["correct"] is False
    assert strict.json()["result"] == "incorrect"

    # Invariant 3: idempotent -- a second POST while the first attempt is
    # unscored returns the SAME attempt's items, never a second attempt
    # row, and a scored attempt is rate-limited instead of re-rolled.
    answered = {items[0]["id"], item_id}
    answer_all(
        client,
        auth,
        [item for item in items if item["id"] not in answered],
        correct_count=0,
    )
    result = client.get(
        f"/units/{unit_id}/checkpoint/result", headers=auth
    )
    assert result.status_code == 200, result.text
    again = client.post(f"/units/{unit_id}/checkpoint", headers=auth)
    assert again.status_code == 429, again.text
    assert error_code(again) == "checkpoint_retake_delayed"
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count(CheckpointAttempt.id)).where(
                    CheckpointAttempt.user_id == uid,
                    CheckpointAttempt.unit_id == unit_id,
                )
            )
            == 1
        )


def test_widened_checkpoint_retake_still_reaches_the_floor(
    client,
    admin,
    auth,
):
    # The recent-signature window holds the previous attempt's items, so
    # the "fresh material" passes come up short on a retake. The late
    # passes drop that history (but never allow a duplicate WITHIN one
    # checkpoint), which is what keeps a retake at full length.
    ids = scope_setup(
        client, admin, cross_unit_templates(), unit_nouns=4, prior_adverbs=2
    )
    unit_id = ids["unit_id"]

    first = client.post(f"/units/{unit_id}/checkpoint", headers=auth)
    assert first.status_code == 200, first.text
    answer_all(client, auth, first.json()["items"], correct_count=0)
    assert (
        client.get(
            f"/units/{unit_id}/checkpoint/result", headers=auth
        ).status_code
        == 200
    )

    with SessionLocal() as db:
        latest = db.scalar(
            select(CheckpointAttempt)
            .where(
                CheckpointAttempt.user_id == user_id(auth),
                CheckpointAttempt.unit_id == unit_id,
            )
            .order_by(
                CheckpointAttempt.created_at.desc(),
                CheckpointAttempt.id.desc(),
            )
            .limit(1)
        )
        latest.created_at = datetime.now(timezone.utc) - timedelta(
            hours=1, seconds=1
        )
        db.commit()

    retake = client.post(f"/units/{unit_id}/checkpoint", headers=auth)
    assert retake.status_code == 200, retake.text
    retake_items = retake.json()["items"]
    assert 12 <= len(retake_items) <= 15

    from app.practice.service import _prompt_signature

    with SessionLocal() as db:
        signatures = {
            _prompt_signature(db.get(PracticeItem, item["id"]).prompt)
            for item in retake_items
        }
    assert len(signatures) == len(retake_items)
