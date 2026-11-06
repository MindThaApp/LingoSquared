from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import (
    Exercise,
    Lexeme,
    PracticeItem,
    PracticeTemplate,
    UserLexemeSRS,
)
from app.review import fsrs
from app.review.scheduler import schedule
from test_endless_practice import (
    artifact,
    create_course_with_lexemes,
    import_templates,
)


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def complete_via_api(client, auth, lesson_id):
    started = client.post(
        f"/lessons/{lesson_id}/start",
        headers=auth,
    )
    assert started.status_code == 200
    detail = client.get(f"/lessons/{lesson_id}").json()
    if detail["exercises"]:
        exercise_id = detail["exercises"][0]["id"]
        with SessionLocal() as db:
            response = db.get(Exercise, exercise_id).correct_response
        answered = client.post(
            f"/exercises/{exercise_id}/answer",
            headers=auth,
            json={"response": response},
        )
        assert answered.status_code == 200 and answered.json()["correct"] is True
    completed = client.post(
        f"/lessons/{lesson_id}/complete",
        headers=auth,
    )
    assert completed.status_code == 200
    return completed


def answer_from_db(client, auth, item_id):
    with SessionLocal() as db:
        item = db.get(PracticeItem, item_id)
        response = item.correct_response
    result = client.post(
        f"/practice/items/{item_id}/answer",
        headers=auth,
        json={"response": response},
    )
    assert result.status_code == 200, result.text
    return result


class _ScheduleItem:
    def __init__(
        self,
        *,
        repetitions=2,
        interval_days=10,
        ease_factor=2.5,
        mastery=0.4,
        due_at=None,
        last_reviewed_at=None,
    ):
        self.repetitions = repetitions
        self.interval_days = interval_days
        self.ease_factor = ease_factor
        self.mastery = mastery
        self.due_at = due_at
        self.last_reviewed_at = last_reviewed_at


def test_schedule_on_time_review_grows_interval_per_fsrs():
    now = datetime.now(timezone.utc)
    item = _ScheduleItem(
        due_at=now - timedelta(minutes=1),
        last_reviewed_at=now - timedelta(days=10),
    )

    schedule(item, "correct", now=now)

    # SM-2 state (interval 10, ease 2.5) migrates to S=10, D=5.
    r = fsrs.retrievability(10, 10.0)
    expected = fsrs.next_stability(5.0, 10.0, r, fsrs.GOOD)
    assert item.stability == expected
    assert item.interval_days == fsrs.next_interval(expected)
    assert 20 <= item.interval_days <= 40
    assert item.repetitions == 3
    assert 0.54 < item.mastery < 0.56
    assert item.due_at > now + timedelta(days=item.interval_days - 1)


def test_schedule_early_review_grows_less_than_on_time():
    now = datetime.now(timezone.utc)
    early = _ScheduleItem(
        due_at=now + timedelta(days=8),
        last_reviewed_at=now - timedelta(days=2),
    )
    on_time = _ScheduleItem(
        due_at=now - timedelta(minutes=1),
        last_reviewed_at=now - timedelta(days=10),
    )

    schedule(early, "correct", now=now)
    schedule(on_time, "correct", now=now)

    assert 10 <= early.interval_days < on_time.interval_days
    assert early.repetitions == 3


def test_schedule_first_ever_review_uses_initial_stability():
    now = datetime.now(timezone.utc)
    item = _ScheduleItem(
        repetitions=0,
        interval_days=0,
        due_at=now + timedelta(minutes=5),
        last_reviewed_at=None,
    )

    schedule(item, "correct", now=now)

    assert item.stability == fsrs.DEFAULT_W[2]
    assert item.interval_days == 4
    assert item.repetitions == 1


def test_schedule_lapse_on_established_word_keeps_partial_credit():
    # A lapse lowers stability (never to zero) and difficulty rises; the
    # mastery penalty and repetitions reset apply.
    now = datetime.now(timezone.utc)
    item = _ScheduleItem(
        repetitions=8,
        interval_days=100,
        ease_factor=2.5,
        mastery=0.9,
        due_at=now - timedelta(minutes=1),
        last_reviewed_at=now - timedelta(days=100),
    )

    schedule(item, "incorrect", now=now)

    assert 1 <= item.interval_days < 100
    assert item.stability < 100 and item.stability > 0
    assert item.difficulty > 5.0
    assert item.ease_factor < 2.5
    assert item.repetitions == 0
    assert abs(item.mastery - 0.7) < 1e-9
    assert item.due_at > now + timedelta(days=item.interval_days - 1)


def test_schedule_success_after_lapse_regrows():
    now = datetime.now(timezone.utc)
    item = _ScheduleItem(
        repetitions=8,
        interval_days=100,
        ease_factor=2.5,
        mastery=0.9,
        due_at=now - timedelta(minutes=1),
        last_reviewed_at=now - timedelta(days=100),
    )
    schedule(item, "incorrect", now=now)
    lapsed = item.interval_days

    item.due_at = now - timedelta(minutes=1)
    item.last_reviewed_at = now - timedelta(days=lapsed)
    schedule(item, "correct", now=now)

    assert item.interval_days > lapsed
    assert item.repetitions == 1


def test_schedule_consecutive_lapses_converge_to_floor_never_negative():
    now = datetime.now(timezone.utc)
    item = _ScheduleItem(
        repetitions=8,
        interval_days=100,
        ease_factor=2.5,
        mastery=0.9,
        due_at=now - timedelta(minutes=1),
        last_reviewed_at=now - timedelta(days=100),
    )

    for _ in range(8):
        schedule(item, "incorrect", now=now)
        item.last_reviewed_at = now - timedelta(days=1)
        assert item.interval_days >= 1
        assert item.repetitions >= 0
        assert 1.3 <= item.ease_factor
        assert item.stability >= fsrs.MIN_STABILITY
        assert 1.0 <= item.difficulty <= 10.0
        assert item.mastery >= 0.0

    assert item.interval_days == 1
    assert item.repetitions == 0


def test_lesson_completion_populates_srs_idempotently(client, auth):
    course_id, lesson_id = create_course_with_lexemes()
    uid = user_id(auth)

    first = complete_via_api(client, auth, lesson_id)
    assert first.json()["xp_awarded"] > 0

    with SessionLocal() as db:
        count_before = db.scalar(
            select(func.count(UserLexemeSRS.id)).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.course_id == course_id,
            )
        )
        assert count_before > 0
        rows = list(
            db.scalars(
                select(UserLexemeSRS).where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
            )
        )
        assert all(row.introduced_at is not None for row in rows)
        assert all(row.due_at > row.introduced_at for row in rows)

    second = client.post(
        f"/lessons/{lesson_id}/complete",
        headers=auth,
    )
    assert second.status_code == 200
    assert second.json()["xp_awarded"] == 0

    with SessionLocal() as db:
        count_after = db.scalar(
            select(func.count(UserLexemeSRS.id)).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.course_id == course_id,
            )
        )
        assert count_after == count_before


def test_same_review_session_retry_schedules_only_first_answer(
    client,
    admin,
    auth,
):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    uid = user_id(auth)

    with SessionLocal() as db:
        srs = db.scalar(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.course_id == course_id,
            )
        )
        srs.due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        target_id = srs.lexeme_id
        db.commit()

    session = client.post(
        "/reviews/session",
        headers=auth,
        json={"course_id": course_id, "size": 1},
    )
    assert session.status_code == 200, session.text
    original_id = session.json()["items"][0]["id"]

    with SessionLocal() as db:
        original = db.get(PracticeItem, original_id)
        assert original.target_lexeme_id == target_id

    wrong = client.post(
        f"/practice/items/{original_id}/answer",
        headers=auth,
        json={"response": "__wrong__"},
    )
    assert wrong.status_code == 200
    assert wrong.json()["correct"] is False

    with SessionLocal() as db:
        first_state = db.scalar(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.lexeme_id == target_id,
            )
        )
        due_after_first = first_state.due_at
        repetitions_after_first = first_state.repetitions
        mastery_after_first = first_state.mastery
        assert repetitions_after_first == 0
        assert first_state.interval_days == 1

    retry = client.post(
        f"/reviews/items/{original_id}/retry",
        headers=auth,
    )
    assert retry.status_code == 200, retry.text
    assert len(retry.json()["items"]) == 1
    retry_id = retry.json()["items"][0]["id"]
    answer_from_db(client, auth, retry_id)

    with SessionLocal() as db:
        final_state = db.scalar(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == uid,
                UserLexemeSRS.lexeme_id == target_id,
            )
        )
        assert final_state.due_at == due_after_first
        assert final_state.repetitions == repetitions_after_first
        assert final_state.mastery == mastery_after_first


def test_review_sampler_prioritizes_due_lexeme(client, admin, auth):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
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
        # artifact()'s templates only match part_of_speech="noun" lexemes
        # (the number words) - the "right"/adverb and good_wish/phrase
        # lexemes created by create_course_with_lexemes() have no matching
        # template, so picking one of those as "due" would correctly fall
        # through to a different lexeme rather than reveal a real bug.
        noun_lexeme_ids = set(
            db.scalars(
                select(Lexeme.id).where(
                    Lexeme.course_id == course_id,
                    Lexeme.part_of_speech == "noun",
                )
            )
        )
        due = next(row for row in rows if row.lexeme_id in noun_lexeme_ids)
        for row in rows:
            row.due_at = datetime.now(timezone.utc) + timedelta(days=5)
            row.mastery = 0.0
        due.due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        due.mastery = 0.9
        due_id = due.lexeme_id
        db.commit()

    response = client.post(
        "/reviews/session",
        headers=auth,
        json={"course_id": course_id, "size": 1},
    )
    assert response.status_code == 200, response.text
    item_id = response.json()["items"][0]["id"]

    with SessionLocal() as db:
        item = db.get(PracticeItem, item_id)
        assert item.target_lexeme_id == due_id


def test_ladder_falls_back_when_production_template_unavailable(
    client,
    admin,
    auth,
):
    course_id, lesson_id = create_course_with_lexemes()
    import_templates(client, admin, course_id, artifact(include_listen=False))
    complete_via_api(client, auth, lesson_id)
    uid = user_id(auth)

    with SessionLocal() as db:
        for template in db.scalars(
            select(PracticeTemplate).where(
                PracticeTemplate.course_id == course_id,
                PracticeTemplate.type == "translation",
            )
        ):
            template.active = False

        rows = list(
            db.scalars(
                select(UserLexemeSRS).where(
                    UserLexemeSRS.user_id == uid,
                    UserLexemeSRS.course_id == course_id,
                )
            )
        )
        # Same constraint as test_review_sampler_prioritizes_due_lexeme:
        # only part_of_speech="noun" lexemes have any matching template at
        # all in artifact(), so the fallback target must be one of those.
        noun_lexeme_ids = set(
            db.scalars(
                select(Lexeme.id).where(
                    Lexeme.course_id == course_id,
                    Lexeme.part_of_speech == "noun",
                )
            )
        )
        target = next(
            row for row in rows if row.lexeme_id in noun_lexeme_ids
        )
        for row in rows:
            row.due_at = datetime.now(timezone.utc) + timedelta(days=5)
        target.due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        target.mastery = 0.9
        db.commit()

    response = client.post(
        "/reviews/session",
        headers=auth,
        json={"course_id": course_id, "size": 1},
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["type"] in {
        "word_order",
        "matching_pairs",
        "fill_in_blank",
    }
