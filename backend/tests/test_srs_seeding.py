from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models import Exercise, Lesson, Lexeme, UserLexemeSRS
from test_endless_practice import create_course_with_lexemes


def _user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


def _make_lesson():
    course_id, lesson_id = create_course_with_lexemes()
    with SessionLocal() as db:
        source = db.scalar(select(Exercise).where(Exercise.lesson_id == lesson_id))
        for order in range(2, 6):
            db.add(Exercise(
                lesson_id=lesson_id,
                type=source.type,
                order=order,
                prompt=dict(source.prompt),
                correct_response=source.correct_response,
                feedback=source.feedback,
                xp=source.xp,
            ))
        db.commit()
    return course_id, lesson_id


def _answer_lesson(client, auth, lesson_id, mode):
    assert client.post(f"/lessons/{lesson_id}/start", headers=auth).status_code == 200
    exercises = client.get(f"/lessons/{lesson_id}").json()["exercises"]
    for index, exercise in enumerate(exercises):
        with SessionLocal() as db:
            correct = db.get(Exercise, exercise["id"]).correct_response
        if mode == "correct":
            response, input_mode = correct, "typed"
        elif mode == "almost":
            response, input_mode = "tset", "spoken"
        else:
            response, input_mode = "__wrong__", "typed"
        result = client.post(
            f"/exercises/{exercise['id']}/answer",
            headers=auth,
            json={"response": response, "input_mode": input_mode},
        )
        assert result.status_code == 200, result.text
        if mode == "almost":
            assert result.json()["result"] == "almost"
    completed = client.post(f"/lessons/{lesson_id}/complete", headers=auth)
    assert completed.status_code == 200, completed.text


def _rows(auth, lesson_id):
    with SessionLocal() as db:
        lexemes = list(db.scalars(select(Lexeme).where(Lexeme.provenance_lesson_id == lesson_id)))
        rows = list(db.scalars(select(UserLexemeSRS).where(
            UserLexemeSRS.user_id == _user_id(auth),
            UserLexemeSRS.lexeme_id.in_([lex.id for lex in lexemes]),
        )))
        return rows


def test_five_first_try_correct_seeds_three_day_interval(client, auth):
    _course_id, lesson_id = _make_lesson()
    before = datetime.now(timezone.utc)
    _answer_lesson(client, auth, lesson_id, "correct")
    rows = _rows(auth, lesson_id)
    assert rows and all(row.interval_days == 3 and row.repetitions == 1 for row in rows)
    assert all(row.mastery == 0.5 for row in rows)
    assert all(before + timedelta(days=2, hours=23) < row.due_at < before + timedelta(days=3, minutes=1) for row in rows)


def test_three_of_five_seeds_neutral_one_day_defaults(client, auth):
    _course_id, lesson_id = _make_lesson()
    # Answer three exercises correctly and two incorrectly: score 0.6.
    before = datetime.now(timezone.utc)
    assert client.post(f"/lessons/{lesson_id}/start", headers=auth).status_code == 200
    exercises = client.get(f"/lessons/{lesson_id}").json()["exercises"]
    for index, exercise in enumerate(exercises):
        with SessionLocal() as db:
            correct = db.get(Exercise, exercise["id"]).correct_response
        response = correct if index < 3 else "__wrong__"
        assert client.post(f"/exercises/{exercise['id']}/answer", headers=auth, json={"response": response}).status_code == 200
    assert client.post(f"/lessons/{lesson_id}/complete", headers=auth).status_code == 200
    rows = _rows(auth, lesson_id)
    assert rows and all(row.interval_days == 0 and row.repetitions == 0 and row.mastery == 0 for row in rows)
    assert all(row.ease_factor == 2.5 for row in rows)
    assert all(timedelta(hours=23, minutes=59) < row.due_at - before < timedelta(days=1, minutes=1) for row in rows)


def test_zero_of_five_seeds_four_hour_low_score_band(client, auth):
    _course_id, lesson_id = _make_lesson()
    before = datetime.now(timezone.utc)
    _answer_lesson(client, auth, lesson_id, "wrong")
    rows = _rows(auth, lesson_id)
    assert rows and all(row.ease_factor == 2.3 and row.interval_days == 0 and row.repetitions == 0 and row.mastery == 0 for row in rows)
    assert all(before + timedelta(hours=3, minutes=59) < row.due_at < before + timedelta(hours=4, minutes=1) for row in rows)


def test_almost_only_score_half_seeds_low_score_band(client, auth):
    _course_id, lesson_id = _make_lesson()
    before = datetime.now(timezone.utc)
    _answer_lesson(client, auth, lesson_id, "almost")
    rows = _rows(auth, lesson_id)
    assert rows and all(row.ease_factor == 2.3 and row.interval_days == 0 and row.repetitions == 0 for row in rows)
    assert all(before + timedelta(hours=3, minutes=59) < row.due_at < before + timedelta(hours=4, minutes=1) for row in rows)


def test_recompletion_does_not_reseed_and_existing_srs_is_untouched(client, auth):
    _course_id, lesson_id = _make_lesson()
    _answer_lesson(client, auth, lesson_id, "correct")
    with SessionLocal() as db:
        rows = list(db.scalars(select(UserLexemeSRS).where(UserLexemeSRS.user_id == _user_id(auth))))
        original_count = len(rows)
        row = rows[0]
        lexeme_id = row.lexeme_id
        row.mastery = 0.91
        row.interval_days = 17
        row.repetitions = 8
        original = (row.mastery, row.interval_days, row.repetitions, row.due_at)
        db.commit()
    result = client.post(f"/lessons/{lesson_id}/complete", headers=auth)
    assert result.status_code == 200
    with SessionLocal() as db:
        rows = list(db.scalars(select(UserLexemeSRS).where(UserLexemeSRS.user_id == _user_id(auth))))
        assert len(rows) == original_count
        row = db.scalar(select(UserLexemeSRS).where(
            UserLexemeSRS.user_id == _user_id(auth),
            UserLexemeSRS.lexeme_id == lexeme_id,
        ))
        assert (row.mastery, row.interval_days, row.repetitions, row.due_at) == original


def test_admin_completion_without_attempts_uses_neutral_defaults(client, admin, auth):
    _course_id, lesson_id = _make_lesson()
    before = datetime.now(timezone.utc)
    result = client.post(
        f"/admin/users/{_user_id(auth)}/unlock",
        headers=admin,
        json={"lesson_id": lesson_id},
    )
    assert result.status_code == 200, result.text
    rows = _rows(auth, lesson_id)
    assert rows and all(row.ease_factor == 2.5 and row.interval_days == 0 and row.repetitions == 0 and row.mastery == 0 for row in rows)
    assert all(before + timedelta(hours=23, minutes=59) < row.due_at < before + timedelta(days=1, minutes=1) for row in rows)
