"""Placement test backend (course-level), 2026-08-05.

Covers the spec 5 test plan: deterministic laddered set, per-item live
grading with NO side effects (no ExerciseAttempt/LessonProgress/
UserLexemeSRS rows), table-driven recommend_from_answers, 409 when the
course can't fill one block, and 400 for an exercise not in the course.

The MVP writes nothing, so these run against directly-seeded courses via
SessionLocal (no content-import/lexeme machinery needed).
"""

from uuid import uuid4

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.core.security import decode_token
from app.models import (
    Course,
    Exercise,
    ExerciseAttempt,
    ExerciseType,
    Lesson,
    LessonProgress,
    Unit,
    UnitSection,
    UserLexemeSRS,
)
from app.review.placement import recommend_from_answers


def user_id(auth):
    return decode_token(auth["Authorization"].split()[1])


# --- direct seeding ----------------------------------------------------

def make_course(level_counts, *, section=UnitSection.reading_writing):
    """Create an en->nl course with, for each (level, n) in level_counts,
    one reading/writing unit whose lesson holds ``n`` multiple_choice
    exercises. Correct answer of exercise k is ``"correct-<id>"``. Returns
    (course_id, {level: [exercise_id, ...]} in stable authored order).

    Good-citizen note (shared session DB): every course is uniquely tagged
    (uuid ``tag`` in title/content_key/answers) so these rows never collide
    with each other or the seed course. Crucially they are ALWAYS
    multiple_choice (never a free-text/translation type), so the
    type-filtered ``seeded_exercise_id()`` helpers in other suites
    (test_rate_limiting / test_security_payload_bounds select
    ``Exercise.type == translation``) can never pick a placement row - the
    coupling that first surfaced when this suite began seeding rows."""
    tag = uuid4().hex[:8]
    exercise_ids: dict[str, list[str]] = {}
    with SessionLocal() as db:
        course = Course(
            source_language="en",
            target_language="nl",
            title=f"Placement {tag}",
        )
        db.add(course)
        db.flush()
        for unit_order, (level, count) in enumerate(level_counts, start=1):
            unit = Unit(
                course_id=course.id,
                title=f"{level} unit {tag}",
                order=unit_order,
                section=section,
                content_key=f"nl.{level.lower()}.unit{unit_order:02d}.{tag}",
            )
            db.add(unit)
            db.flush()
            lesson = Lesson(unit_id=unit.id, title="L1", order=1)
            db.add(lesson)
            db.flush()
            ids = []
            for ex_order in range(1, count + 1):
                key = f"{level}-{ex_order}-{tag}"
                ex = Exercise(
                    lesson_id=lesson.id,
                    type=ExerciseType.multiple_choice,
                    order=ex_order,
                    prompt={"question": f"q {key}", "options": ["a", "b", f"correct-{key}"]},
                    correct_response=f"correct-{key}",
                )
                db.add(ex)
                db.flush()
                ids.append(ex.id)
            exercise_ids[level] = ids
        db.commit()
        return course.id, exercise_ids


def correct_answer(exercise_id):
    with SessionLocal() as db:
        return db.get(Exercise, exercise_id).correct_response


# --- pure recommend logic (table-driven) -------------------------------

def test_recommend_fail_a1_recommends_a1():
    graded = [("A1", False), ("A1", False), ("A1", True), ("A1", True)]
    level, per_level = recommend_from_answers(graded)
    assert level == "A1"
    assert per_level["A1"] == {"correct": 2, "total": 4}


def test_recommend_pass_a1_fail_a2_recommends_a2():
    graded = [("A1", True)] * 4 + [("A2", True), ("A2", False), ("A2", False), ("A2", False)]
    level, _ = recommend_from_answers(graded)
    assert level == "A2"


def test_recommend_pass_all_recommends_highest():
    graded = [("A1", True)] * 4 + [("A2", True)] * 4 + [("B1", True)] * 4
    level, _ = recommend_from_answers(graded)
    assert level == "B1"


def test_recommend_empty_answers():
    assert recommend_from_answers([]) == (None, {})


# --- GET /placement : deterministic set --------------------------------

def test_placement_set_ladder_and_ordering(client, auth):
    # A1 has 6 probes (only first 4 in the block), A2 has 4, B1 has 3 (dropped).
    course_id, ids = make_course([("A1", 6), ("A2", 4), ("B1", 3)])
    r = client.get(f"/courses/{course_id}/placement", headers=auth)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["course_id"] == course_id
    assert body["levels"] == ["A1", "A2"]  # B1 dropped (< 4)
    assert body["block_size"] == 4
    assert body["pass_threshold"] == 3
    assert len(body["items"]) == 8  # 4 A1 + 4 A2
    # Deterministic: first 4 authored A1 exercises, in order, then A2's 4.
    got = [(it["id"], it["level"]) for it in body["items"]]
    expected = [(eid, "A1") for eid in ids["A1"][:4]] + [(eid, "A2") for eid in ids["A2"][:4]]
    assert got == expected
    # Correct answers are NEVER serialized in the set payload: each item
    # carries only the withheld-answer shape {id, level, type, order, prompt}.
    for it in body["items"]:
        assert set(it.keys()) == {"id", "level", "type", "order", "prompt"}
    # Reproducible across calls.
    r2 = client.get(f"/courses/{course_id}/placement", headers=auth)
    assert [it["id"] for it in r2.json()["items"]] == [it["id"] for it in body["items"]]


def test_placement_set_unknown_course_404(client, auth):
    r = client.get(f"/courses/{uuid4().hex}/placement", headers=auth)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "course_not_found"


def test_placement_unavailable_under_one_block_409(client, auth):
    course_id, _ = make_course([("A1", 3)])  # can't fill one A1 block
    r = client.get(f"/courses/{course_id}/placement", headers=auth)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "placement_unavailable"


def test_placement_requires_auth(client):
    course_id, _ = make_course([("A1", 4)])
    r = client.get(f"/courses/{course_id}/placement")
    assert r.status_code == 401


# --- POST /placement/answer : live grade, no side effects --------------

def test_placement_answer_grades_and_writes_nothing(client, auth):
    course_id, ids = make_course([("A1", 4), ("A2", 4)])
    a1 = ids["A1"][0]
    # correct
    r = client.post(
        f"/courses/{course_id}/placement/answer",
        headers=auth,
        json={"exercise_id": a1, "response": correct_answer(a1)},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["correct"] is True
    assert body["result"] == "correct"
    assert body["correct_response"] == correct_answer(a1)
    # incorrect
    r = client.post(
        f"/courses/{course_id}/placement/answer",
        headers=auth,
        json={"exercise_id": a1, "response": "definitely-wrong"},
    )
    assert r.status_code == 200
    assert r.json()["correct"] is False
    assert r.json()["result"] == "incorrect"
    # No rows written by placement for this user.
    uid = user_id(auth)
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ExerciseAttempt.id)).where(ExerciseAttempt.user_id == uid)) == 0
        assert db.scalar(select(func.count(LessonProgress.id)).where(LessonProgress.user_id == uid)) == 0
        assert db.scalar(select(func.count(UserLexemeSRS.id)).where(UserLexemeSRS.user_id == uid)) == 0


def test_placement_answer_exercise_not_in_course_400(client, auth):
    course_id, _ = make_course([("A1", 4)])
    other_course_id, other_ids = make_course([("A1", 4)])
    foreign = other_ids["A1"][0]
    r = client.post(
        f"/courses/{course_id}/placement/answer",
        headers=auth,
        json={"exercise_id": foreign, "response": "a"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "exercise_not_in_placement"


def test_placement_answer_unknown_exercise_400(client, auth):
    course_id, _ = make_course([("A1", 4)])
    r = client.post(
        f"/courses/{course_id}/placement/answer",
        headers=auth,
        json={"exercise_id": uuid4().hex, "response": "a"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "exercise_not_in_placement"


# --- POST /placement/result : authoritative recommendation -------------

def _ans(exercise_id, correct):
    return {"exercise_id": exercise_id, "response": correct_answer(exercise_id) if correct else "wrong"}


def test_placement_result_pass_a1_fail_a2(client, auth):
    course_id, ids = make_course([("A1", 4), ("A2", 4), ("B1", 4)])
    answers = [_ans(e, True) for e in ids["A1"]] + [
        _ans(ids["A2"][0], True),
        _ans(ids["A2"][1], False),
        _ans(ids["A2"][2], False),
        _ans(ids["A2"][3], False),
    ]
    r = client.post(f"/courses/{course_id}/placement/result", headers=auth, json={"answers": answers})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["recommended_level"] == "A2"
    assert body["recommended_unit_content_key"].startswith("nl.a2.")
    assert body["per_level"]["A1"] == {"correct": 4, "total": 4}
    assert body["per_level"]["A2"] == {"correct": 1, "total": 4}
    # No side effects.
    uid = user_id(auth)
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ExerciseAttempt.id)).where(ExerciseAttempt.user_id == uid)) == 0
        assert db.scalar(select(func.count(LessonProgress.id)).where(LessonProgress.user_id == uid)) == 0
        assert db.scalar(select(func.count(UserLexemeSRS.id)).where(UserLexemeSRS.user_id == uid)) == 0


def test_placement_result_fail_a1_recommends_course_start(client, auth):
    course_id, ids = make_course([("A1", 4), ("A2", 4)])
    answers = [_ans(ids["A1"][0], True), _ans(ids["A1"][1], False), _ans(ids["A1"][2], False), _ans(ids["A1"][3], False)]
    r = client.post(f"/courses/{course_id}/placement/result", headers=auth, json={"answers": answers})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["recommended_level"] == "A1"
    assert body["recommended_unit_content_key"].startswith("nl.a1.")


def test_placement_result_pass_all_recommends_highest(client, auth):
    course_id, ids = make_course([("A1", 4), ("A2", 4)])
    answers = [_ans(e, True) for e in ids["A1"]] + [_ans(e, True) for e in ids["A2"]]
    r = client.post(f"/courses/{course_id}/placement/result", headers=auth, json={"answers": answers})
    assert r.status_code == 200
    assert r.json()["recommended_level"] == "A2"


def test_placement_result_empty_answers_recommends_start(client, auth):
    course_id, ids = make_course([("A1", 4), ("A2", 4)])
    r = client.post(f"/courses/{course_id}/placement/result", headers=auth, json={"answers": []})
    assert r.status_code == 200, r.text
    body = r.json()
    # Course start (first reading/writing unit), reported at its own level.
    assert body["recommended_unit_content_key"].startswith("nl.a1.")
    assert body["recommended_level"] == "A1"
    assert body["per_level"] == {}


def test_placement_result_ignores_foreign_answers(client, auth):
    course_id, ids = make_course([("A1", 4)])
    _, other_ids = make_course([("A1", 4)])
    answers = [_ans(e, True) for e in ids["A1"]] + [_ans(other_ids["A1"][0], True)]
    r = client.post(f"/courses/{course_id}/placement/result", headers=auth, json={"answers": answers})
    assert r.status_code == 200
    # Foreign answer ignored: A1 still only 4 total.
    assert r.json()["per_level"]["A1"] == {"correct": 4, "total": 4}


def test_placement_result_unknown_course_404(client, auth):
    r = client.post(f"/courses/{uuid4().hex}/placement/result", headers=auth, json={"answers": []})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "course_not_found"
