"""Reorder-import safety check required by docs/A2_REBUILD_PLAN.md section 4.4
(decision Q5: interleave the existing A2 scenario units after the grammar
block they use).

Tests only: they drive the real import_content() with a payload whose units
carry NEW `order` values for already-imported content_keys, with a fully
populated learner (progress, completions, attempts, SRS incl. unreviewable_at,
XP/streak, quests, checkpoints, issue reports) and assert that every
user-owned row, and every content primary key it points at, survives
byte-for-byte. Nothing here touches real content.
"""
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select

from app.api.router import speaking_unlocked
from app.content.service import import_content
from app.db.session import SessionLocal, engine
from app.models import (
    CheckpointAttempt,
    ContentIssueReport,
    Course,
    Exercise,
    ExerciseAttempt,
    Lesson,
    LessonProgress,
    Lexeme,
    QuestCompletion,
    ReviewEvent,
    ReviewItem,
    SkillProgress,
    Unit,
    UnitSection,
    User,
    UserLexemeSRS,
    UserStats,
)
from app.schemas.api import ImportRequest

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)

# key -> (track, section)
UNITS = {
    "t.s1": ("situation", UnitSection.reading_writing),
    "t.s2": ("situation", UnitSection.reading_writing),
    "t.g1": ("core", UnitSection.reading_writing),
    "t.g2": ("core", UnitSection.reading_writing),
    "t.g3": ("core", UnitSection.reading_writing),
    "t.sp": ("core", UnitSection.speaking),
}
# Today's shape: scenarios first, then grammar, then speaking.
BEFORE = {"t.s1": 1, "t.s2": 2, "t.g1": 3, "t.g2": 4, "t.g3": 5, "t.sp": 6}
# Q5 shape: each scenario right after the grammar block it uses.
INTERLEAVED = {"t.g1": 1, "t.s1": 2, "t.g2": 3, "t.s2": 4, "t.g3": 5, "t.sp": 6}


def _payload(title, orders, extra=()):
    units = []
    for key, order in orders.items():
        track, section = UNITS.get(key, ("core", UnitSection.reading_writing))
        units.append(
            {
                "title": key,
                "order": order,
                "section": section.value,
                "track": track,
                "content_key": key,
                "lessons": [
                    {
                        "title": f"{key} lesson",
                        "order": 1,
                        "content_key": f"{key}.l1",
                        "exercises": [
                            {
                                "type": "translation",
                                "order": n,
                                "content_key": f"{key}.l1.e{n}",
                                "prompt": {
                                    "text_blocks": [
                                        {"text": "t", "language_code": "en", "direction": "ltr"}
                                    ]
                                },
                                "correct_response": "t",
                            }
                            for n in (1, 2)
                        ],
                    }
                ],
            }
        )
    return ImportRequest.model_validate(
        {
            "courses": [
                {
                    "source_language": "en",
                    "target_language": "es",
                    "title": title,
                    "units": units,
                }
            ]
        }
    )


def _import(payload):
    with SessionLocal() as db:
        count, errors, counters = import_content(db, payload)
    assert not errors, errors
    return counters


def _orders(db, course_id):
    return {
        u.content_key: u.order
        for u in db.scalars(select(Unit).where(Unit.course_id == course_id))
    }


def _row(obj):
    return {
        c.key: getattr(obj, c.key) for c in inspect(obj.__class__).mapper.column_attrs
    }


def _snapshot(db, user_id, course_id):
    """Every row owned by the learner (or hanging off the course content they
    reference), as plain dicts, keyed by table and primary key."""
    def rows(model, *where):
        return sorted(
            (_row(r) for r in db.scalars(select(model).where(*where))),
            key=lambda d: str(d.get("id", d.get("user_id"))),
        )

    return {
        "lesson_progress": rows(LessonProgress, LessonProgress.user_id == user_id),
        "exercise_attempts": rows(ExerciseAttempt, ExerciseAttempt.user_id == user_id),
        "review_items": rows(ReviewItem, ReviewItem.user_id == user_id),
        "srs": rows(UserLexemeSRS, UserLexemeSRS.user_id == user_id),
        "review_events": rows(ReviewEvent, ReviewEvent.user_id == user_id),
        "user_stats": rows(UserStats, UserStats.user_id == user_id),
        "quests": rows(QuestCompletion, QuestCompletion.user_id == user_id),
        "checkpoints": rows(CheckpointAttempt, CheckpointAttempt.user_id == user_id),
        "skill_progress": rows(SkillProgress, SkillProgress.user_id == user_id),
        "issue_reports": rows(
            ContentIssueReport, ContentIssueReport.reporter_user_id == user_id
        ),
        "lexemes": rows(Lexeme, Lexeme.course_id == course_id),
        "unit_ids": {
            u.content_key: u.id
            for u in db.scalars(select(Unit).where(Unit.course_id == course_id))
        },
        "lesson_ids": {
            l.content_key: l.id
            for l in db.scalars(
                select(Lesson).join(Unit).where(Unit.course_id == course_id)
            )
        },
        "exercise_ids": {
            e.content_key: e.id
            for e in db.scalars(
                select(Exercise).join(Lesson).join(Unit).where(Unit.course_id == course_id)
            )
        },
    }


def _complete(db, user_id, lesson_id):
    db.add(
        LessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            started_at=NOW,
            completed_at=NOW,
            correct_count=2,
            answer_count=3,
            xp_earned=20,
        )
    )


def _seed_learner(title, completed_keys=("t.s1", "t.g1", "t.g2")):
    """Create the course at BEFORE order, then a learner with data touching
    every user-owned table that points into the course."""
    _import(_payload(title, BEFORE))
    with SessionLocal() as db:
        course = db.scalar(select(Course).where(Course.title == title))
        user = User(email=f"reorder-{uuid4()}@example.com", password_hash="test-only")
        db.add(user)
        db.flush()
        lessons = {
            l.content_key: l
            for l in db.scalars(
                select(Lesson).join(Unit).where(Unit.course_id == course.id)
            )
        }
        exercises = {
            e.content_key: e
            for e in db.scalars(
                select(Exercise).join(Lesson).join(Unit).where(Unit.course_id == course.id)
            )
        }
        units = {u.content_key: u for u in db.scalars(select(Unit).where(Unit.course_id == course.id))}
        for key in completed_keys:
            _complete(db, user.id, lessons[f"{key}.l1"].id)
        # an in-progress (started, not completed) lesson
        db.add(LessonProgress(user_id=user.id, lesson_id=lessons["t.g3.l1"].id, started_at=NOW))
        attempts = []
        for key in ("t.s1.l1.e1", "t.g1.l1.e1", "t.g2.l1.e2"):
            a = ExerciseAttempt(
                user_id=user.id,
                exercise_id=exercises[key].id,
                response="t",
                correct=True,
                xp_awarded=10,
                outcome="correct",
                client_operation_id=str(uuid4()),
            )
            db.add(a)
            attempts.append(a)
        db.flush()
        db.add(
            ReviewItem(
                user_id=user.id,
                exercise_id=exercises["t.s1.l1.e1"].id,
                interval_days=6,
                repetitions=3,
                ease_factor=2.1,
                stability=4.2,
                difficulty=5.5,
                mastery=0.4,
                due_at=NOW + timedelta(days=3),
            )
        )
        for i, key in enumerate(("t.s1", "t.g1")):
            lex = Lexeme(
                course_id=course.id,
                token=f"palabra{i}",
                language_code="es",
                part_of_speech="noun",
                english_gloss=f"word{i}",
                agreement_tags={},
                provenance_lesson_id=lessons[f"{key}.l1"].id,
                provenance_lesson_content_key=f"{key}.l1",
                provenance_content_key=f"{key}.lex",
            )
            db.add(lex)
            db.flush()
            db.add(
                UserLexemeSRS(
                    user_id=user.id,
                    lexeme_id=lex.id,
                    course_id=course.id,
                    ease_factor=2.3,
                    interval_days=9,
                    repetitions=4,
                    stability=7.7,
                    difficulty=4.4,
                    mastery=0.6,
                    due_at=NOW - timedelta(days=1),
                    # one flagged unreviewable, one not
                    unreviewable_at=NOW if i == 0 else None,
                    last_reviewed_at=NOW - timedelta(days=5),
                    introduced_at=NOW - timedelta(days=20),
                    lapses=2,
                    leech=bool(i),
                    suspended=bool(i),
                )
            )
            db.add(
                ReviewEvent(
                    user_id=user.id,
                    lexeme_id=lex.id,
                    course_id=course.id,
                    source="srs",
                    result="correct",
                    quality=4,
                    correct=True,
                    previous_interval_days=3,
                    new_interval_days=9,
                    previous_ease=2.2,
                    new_ease=2.3,
                    new_due_at=NOW,
                )
            )
        db.add(
            UserStats(
                user_id=user.id,
                total_xp=345,
                streak_days=12,
                last_activity_date=date(2026, 11, 14),
                daily_goal=30,
                streak_freezes_available=2,
                last_freeze_used_date=date(2026, 11, 10),
            )
        )
        db.add(QuestCompletion(user_id=user.id, quest_code="daily_xp", date=date(2026, 11, 14)))
        db.add(
            CheckpointAttempt(
                user_id=user.id,
                unit_id=units["t.g1"].id,
                total_items=12,
                passed=True,
                score=0.9,
                weak_outcomes=["x"],
                scored_at=NOW,
            )
        )
        db.add(SkillProgress(user_id=user.id, course_id=course.id, completed_lessons=3, mastery=0.5))
        db.add(
            ContentIssueReport(
                reporter_user_id=user.id,
                exercise_id=exercises["t.s1.l1.e2"].id,
                attempt_id=attempts[0].id,
                category="wrong_answer",
                description="keep me",
                status="open",
            )
        )
        db.commit()
        return course.id, user.id


def _assert_survived(before, after, *, expect_unreviewable_cleared=True, added_units=()):
    # Content identity: no unit/lesson/exercise/lexeme row was recreated.
    # (added_units: content_keys legitimately created by the import.)
    for k in ("unit_ids", "lesson_ids", "exercise_ids"):
        kept = {
            key: pk for key, pk in after[k].items()
            if not any(key == a or key.startswith(a + ".") for a in added_units)
        }
        assert before[k] == kept, f"{k} changed (row recreated or lost)"
    for table in before:
        if table in ("unit_ids", "lesson_ids", "exercise_ids", "srs"):
            continue
        assert before[table] == after[table], f"{table} changed across reorder"
    # SRS: every row and every scheduling field identical; the only permitted
    # change is import_content()'s documented unreviewable_at reset.
    assert len(before["srs"]) == len(after["srs"])
    for b, a in zip(before["srs"], after["srs"]):
        assert b["id"] == a["id"]
        b2, a2 = dict(b), dict(a)
        flagged = b2.pop("unreviewable_at"), a2.pop("unreviewable_at")
        assert b2 == a2, "SRS scheduling state changed across reorder"
        if expect_unreviewable_cleared:
            assert flagged[1] is None


@pytest.mark.parametrize(
    "name,target",
    [
        ("interleave_q5", INTERLEAVED),
        # move a unit with progress (g1) after another (s2) ...
        ("progress_unit_after", {"t.s1": 1, "t.s2": 2, "t.g2": 3, "t.g3": 4, "t.g1": 5, "t.sp": 6}),
        # ... and a unit with progress (g2) before another (s1)
        ("progress_unit_before", {"t.g2": 1, "t.s1": 2, "t.s2": 3, "t.g1": 4, "t.g3": 5, "t.sp": 6}),
        ("full_reverse", {"t.sp": 1, "t.g3": 2, "t.g2": 3, "t.g1": 4, "t.s2": 5, "t.s1": 6}),
        ("swap_adjacent", {"t.s2": 1, "t.s1": 2, "t.g1": 3, "t.g2": 4, "t.g3": 5, "t.sp": 6}),
        ("gaps_and_big_orders", {"t.g1": 10, "t.s1": 20, "t.g2": 30, "t.s2": 40, "t.g3": 50, "t.sp": 60}),
    ],
)
def test_reorder_preserves_all_user_data(name, target):
    course_id, user_id = _seed_learner(f"Reorder {name} {uuid4()}")
    with SessionLocal() as db:
        before = _snapshot(db, user_id, course_id)
    counters = _import(_payload(db_title(course_id), target))
    assert counters["created_units"] == 0 and counters["created_lessons"] == 0
    assert counters["created_exercises"] == 0 and counters["retired_exercises"] == 0
    with SessionLocal() as db:
        assert _orders(db, course_id) == target
        after = _snapshot(db, user_id, course_id)
    _assert_survived(before, after)


def db_title(course_id):
    with SessionLocal() as db:
        return db.get(Course, course_id).title


def test_reorder_is_idempotent_and_roundtrips():
    course_id, user_id = _seed_learner(f"Reorder roundtrip {uuid4()}")
    title = db_title(course_id)
    with SessionLocal() as db:
        before = _snapshot(db, user_id, course_id)
    _import(_payload(title, INTERLEAVED))
    _import(_payload(title, INTERLEAVED))  # re-run: no-op
    _import(_payload(title, BEFORE))  # and back
    with SessionLocal() as db:
        assert _orders(db, course_id) == BEFORE
        after = _snapshot(db, user_id, course_id)
    _assert_survived(before, after)


def test_insert_new_units_before_existing_shifts_orders_safely():
    """Section 4.4's literal scenario: new units inserted BEFORE existing ones
    push the existing orders up while progress stays attached."""
    course_id, user_id = _seed_learner(f"Reorder insert {uuid4()}")
    title = db_title(course_id)
    with SessionLocal() as db:
        before = _snapshot(db, user_id, course_id)
    target = {"t.new1": 1, "t.new2": 2}
    target.update({k: v + 2 for k, v in BEFORE.items()})
    counters = _import(_payload(title, target))
    assert counters["created_units"] == 2
    with SessionLocal() as db:
        assert _orders(db, course_id) == target
        after = _snapshot(db, user_id, course_id)
    _assert_survived(before, after, added_units=("t.new1", "t.new2"))


def test_units_absent_from_payload_are_retained_not_deleted():
    """A reorder payload that omits a unit (author mistake) must not delete it
    or its learner rows; it is parked at a free order."""
    course_id, user_id = _seed_learner(f"Reorder omit {uuid4()}")
    title = db_title(course_id)
    with SessionLocal() as db:
        before = _snapshot(db, user_id, course_id)
    partial = {k: v for k, v in INTERLEAVED.items() if k != "t.s2"}
    _import(_payload(title, partial))
    with SessionLocal() as db:
        orders = _orders(db, course_id)
        assert set(orders) == set(BEFORE), "unit deleted by reorder import"
        assert len(set(orders.values())) == len(orders)
        after = _snapshot(db, user_id, course_id)
    _assert_survived(before, after)


def test_reorder_clears_unreviewable_flag_and_nothing_else_in_srs():
    """Characterises the one intentional write on the SRS table: any import
    that changes a course clears unreviewable_at (content may have made words
    buildable) -- a reorder counts as a change. Due dates, intervals, FSRS
    state, lapses, leech and suspended flags must be untouched."""
    course_id, user_id = _seed_learner(f"Reorder unrev {uuid4()}")
    title = db_title(course_id)
    with SessionLocal() as db:
        flagged = list(
            db.scalars(
                select(UserLexemeSRS).where(
                    UserLexemeSRS.user_id == user_id,
                    UserLexemeSRS.unreviewable_at.is_not(None),
                )
            )
        )
        assert len(flagged) == 1
    # Real reorder: flag cleared, schedule intact.
    _import(_payload(title, INTERLEAVED))
    with SessionLocal() as db:
        row = db.get(UserLexemeSRS, flagged[0].id)
        assert row.unreviewable_at is None
        assert row.due_at == NOW - timedelta(days=1)
        assert (row.interval_days, row.repetitions, row.lapses) == (9, 4, 2)
        assert (row.stability, row.difficulty, row.mastery) == (7.7, 4.4, 0.6)


def _lock_state(course_id, user_id):
    with SessionLocal() as db:
        sp = db.scalar(select(Unit).where(Unit.course_id == course_id, Unit.content_key == "t.sp"))
        return speaking_unlocked(db, course_id, user_id, sp.order)


def test_speaking_gate_counts_only_core_units_and_survives_interleave():
    # g1,g2 + s1 complete, g3 (core, before speaking) incomplete -> locked.
    course_id, user_id = _seed_learner(f"Reorder gate {uuid4()}")
    title = db_title(course_id)
    assert _lock_state(course_id, user_id) is False
    # Interleaving situation units must not change the answer.
    _import(_payload(title, INTERLEAVED))
    assert _lock_state(course_id, user_id) is False
    # Completing the last core RW unit unlocks speaking at any scenario placement,
    # even though situation unit s2 (incomplete, no progress) sits before it.
    with SessionLocal() as db:
        lesson = db.scalar(select(Lesson).join(Unit).where(Unit.course_id == course_id, Lesson.content_key == "t.g3.l1"))
        lp = db.scalar(select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson.id))
        lp.completed_at = NOW
        db.commit()
    assert _lock_state(course_id, user_id) is True
    for target in (BEFORE, INTERLEAVED, {"t.g1": 1, "t.g2": 2, "t.g3": 3, "t.sp": 4, "t.s1": 5, "t.s2": 6}):
        _import(_payload(title, target))
        # NB: scenarios moved AFTER speaking just fall outside the gate.
        assert _lock_state(course_id, user_id) is True, target


def test_speaking_gate_relocks_if_incomplete_core_unit_moves_before_speaking():
    """Documents the one gate-visible consequence of a reorder: it is driven
    purely by unit.order, so moving an INCOMPLETE core reading/writing unit in
    front of speaking re-locks a user who had it unlocked. Q5 only moves
    situation units (not counted), so Q5 itself cannot trigger this."""
    course_id, user_id = _seed_learner(
        f"Reorder relock {uuid4()}", completed_keys=("t.s1", "t.g1", "t.g2")
    )
    title = db_title(course_id)
    # g3 sits AFTER speaking -> gate open.
    _import(_payload(title, {"t.s1": 1, "t.s2": 2, "t.g1": 3, "t.g2": 4, "t.sp": 5, "t.g3": 6}))
    assert _lock_state(course_id, user_id) is True
    # Move incomplete core g3 before speaking -> locked again, data untouched.
    _import(_payload(title, {"t.s1": 1, "t.s2": 2, "t.g1": 3, "t.g2": 4, "t.g3": 5, "t.sp": 6}))
    assert _lock_state(course_id, user_id) is False
    with SessionLocal() as db:
        assert db.scalar(select(LessonProgress).where(LessonProgress.user_id == user_id).limit(1)) is not None
