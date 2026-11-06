"""FSRS scheduler, the 0037 migration (SM-2 backfill, upgrade and downgrade)
and the review API on migrated state."""

import importlib.util
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text

from app.db.session import SessionLocal, engine
from app.models import Exercise, Lexeme, ReviewEvent, ReviewItem, UserLexemeSRS
from app.review import fsrs
from app.review.scheduler import legacy_state, schedule
from test_endless_practice import (
    artifact,
    create_course_with_lexemes,
    import_templates,
)
from test_phase_a_srs import complete_via_api, user_id
from test_srs_review_upgrade import _review_item

NOW = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------- algorithm


def test_retrievability_is_ninety_percent_at_one_stability():
    for s in (0.5, 1, 10, 365):
        assert math.isclose(fsrs.retrievability(s, s), 0.9, rel_tol=1e-9)
    assert fsrs.retrievability(0, 5) == 1.0


def test_next_interval_equals_stability_at_target_retention():
    for s in (1.0, 7.0, 90.0):
        assert fsrs.next_interval(s) == round(s)
    assert fsrs.next_interval(0.01) == 1
    assert fsrs.next_interval(1e9) == fsrs.MAX_INTERVAL_DAYS
    assert fsrs.next_interval(30, retention=0.8) > 30


def test_initial_state_matches_default_weights():
    assert fsrs.initial_stability(fsrs.AGAIN) == 0.4872
    assert fsrs.initial_stability(fsrs.EASY) == 13.8206
    d = [fsrs.initial_difficulty(g) for g in (1, 2, 3, 4)]
    assert d == sorted(d, reverse=True) and all(1 <= x <= 10 for x in d)


def test_ratings_order_stability_and_difficulty():
    out = {g: fsrs.review(10.0, 5.0, 10.0, g) for g in (1, 2, 3, 4)}
    assert out[1][0] < out[2][0] < out[3][0] < out[4][0]
    assert out[1][1] > out[2][1] > out[3][1] > out[4][1]
    assert out[1][0] < 10.0  # a lapse never increases stability


def test_stability_grows_more_when_recall_was_harder():
    # Lower retrievability at review time (longer gap) earns more growth.
    soon = fsrs.review(10.0, 5.0, 2.0, fsrs.GOOD)[0]
    late = fsrs.review(10.0, 5.0, 30.0, fsrs.GOOD)[0]
    assert late > soon >= 10.0


def test_difficulty_is_clamped_and_ease_mapping_round_trips():
    d = 5.0
    for _ in range(100):
        d = fsrs.next_difficulty(d, fsrs.AGAIN)
    assert d <= 10.0
    for ease in (1.3, 1.5, 2.0, 2.5, 2.8):
        back = fsrs.ease_from_difficulty(fsrs.difficulty_from_ease(ease))
        assert math.isclose(back, ease, abs_tol=1e-9)
    assert fsrs.difficulty_from_ease(2.5) == 5.0
    assert fsrs.difficulty_from_ease(1.3) == 9.0
    assert fsrs.difficulty_from_ease(9.0) == 1.0


def test_legacy_state_rules():
    new = SimpleNamespace(
        repetitions=0, interval_days=1, ease_factor=2.5, last_reviewed_at=None
    )
    assert legacy_state(new) is None
    seeded = SimpleNamespace(
        repetitions=1, interval_days=3, ease_factor=2.5, last_reviewed_at=NOW
    )
    assert legacy_state(seeded) == (3.0, 5.0)
    hard = SimpleNamespace(
        repetitions=5, interval_days=40, ease_factor=1.3, last_reviewed_at=NOW
    )
    assert legacy_state(hard) == (40.0, 9.0)


def test_review_events_columns_written_by_scheduler():
    it = SimpleNamespace(
        repetitions=3, interval_days=10, ease_factor=2.5, mastery=0.4,
        due_at=NOW, last_reviewed_at=NOW - timedelta(days=10), lapses=0,
        leech=False,
    )
    schedule(it, "almost", now=NOW)
    assert it.last_schedule["rating"] == fsrs.HARD
    assert it.last_schedule["previous_stability"] == 10.0


# ---------------------------------------------------------------- migration

_MIG = Path(__file__).resolve().parents[1] / "alembic/versions/0037_fsrs_state.py"
_STATE_COLS = {
    "user_lexeme_srs": ("stability", "difficulty"),
    "review_items": ("stability", "difficulty"),
    "review_events": ("rating", "new_stability", "new_difficulty"),
}


def _migration():
    spec = importlib.util.spec_from_file_location("mig0037", _MIG)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(fn_name):
    mod = _migration()
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            getattr(mod, fn_name)()


def _columns(table):
    with engine.connect() as conn:
        return {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :t"
                ),
                {"t": table},
            )
        }


def _drop_fsrs_columns():
    with engine.begin() as conn:
        for table, cols in _STATE_COLS.items():
            for c in cols:
                conn.execute(text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {c}"))


# (repetitions, interval_days, ease, reviewed?) -> a spread of SM-2 states.
_SM2_STATES = [
    (0, 1, 2.5, False),   # checkpoint-seeded, never reviewed: stays NULL
    (1, 3, 2.5, True),    # placement seed
    (2, 6, 2.36, True),
    (5, 40, 1.3, True),   # ease floor
    (9, 200, 2.9, True),  # ease above default
    (0, 2, 1.7, True),    # lapsed back to the start
]


def test_migration_0037_upgrade_and_downgrade_on_sm2_data(client, admin, auth):
    course_id, _ = create_course_with_lexemes()
    uid = user_id(auth)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with SessionLocal() as db:
        lexemes = list(db.scalars(select(Lexeme).where(Lexeme.course_id == course_id)))
        assert len(lexemes) >= len(_SM2_STATES)
        for lex, (reps, interval, ease, reviewed) in zip(lexemes, _SM2_STATES):
            db.add(
                UserLexemeSRS(
                    user_id=uid, lexeme_id=lex.id, course_id=course_id,
                    ease_factor=ease, interval_days=interval, repetitions=reps,
                    mastery=0.5, introduced_at=now,
                    due_at=now + timedelta(days=interval),
                    last_reviewed_at=now - timedelta(days=1) if reviewed else None,
                )
            )
        exercises = list(db.scalars(select(Exercise).limit(2)))
        db.add(ReviewItem(user_id=uid, exercise_id=exercises[0].id,
                          interval_days=0, ease_factor=2.3, repetitions=0,
                          due_at=now + timedelta(minutes=10)))
        db.add(ReviewItem(user_id=uid, exercise_id=exercises[1].id,
                          interval_days=10, ease_factor=2.0, repetitions=3,
                          due_at=now + timedelta(days=4)))
        db.commit()
        lex_ids = [x.id for x in lexemes[: len(_SM2_STATES)]]

    def snapshot():
        with SessionLocal() as db:
            rows = {
                r.lexeme_id: r
                for r in db.scalars(
                    select(UserLexemeSRS).where(UserLexemeSRS.user_id == uid)
                )
            }
            return {
                k: (r.ease_factor, r.interval_days, r.repetitions, r.due_at,
                    r.stability, r.difficulty)
                for k, r in rows.items()
            }

    # Put the schema back to its pre-0037 shape, SM-2 data intact.
    with SessionLocal() as db:
        db.execute(text("UPDATE user_lexeme_srs SET stability=NULL, difficulty=NULL"))
        db.commit()
    before = {k: v[:4] for k, v in snapshot().items()}
    _drop_fsrs_columns()
    try:
        assert "stability" not in _columns("user_lexeme_srs")
        _run("upgrade")
        for table, cols in _STATE_COLS.items():
            assert set(cols) <= _columns(table)
        after = snapshot()
        # Due dates, intervals and repetitions are untouched by the backfill.
        assert {k: v[:4] for k, v in after.items()} == before
        for lid, (reps, interval, ease, reviewed) in zip(lex_ids, _SM2_STATES):
            _, _, _, _, stability, difficulty = after[lid]
            if not reviewed and reps == 0 and interval <= 1:
                assert stability is None and difficulty is None
                continue
            assert stability == float(max(1, interval))
            assert math.isclose(
                difficulty, fsrs.difficulty_from_ease(ease), abs_tol=1e-6
            )
            # First FSRS review of a migrated card keeps the schedule sane.
            item = SimpleNamespace(
                repetitions=reps, interval_days=interval, ease_factor=ease,
                mastery=0.5, stability=stability, difficulty=difficulty,
                due_at=now + timedelta(days=interval),
                last_reviewed_at=now + timedelta(days=interval) - timedelta(days=interval),
                lapses=0, leech=False,
            )
            for grade, lo, hi in (("good", 0.9, 4.0), ("easy", 1.0, 12.0)):
                it = SimpleNamespace(**vars(item))
                schedule(it, "correct", now=now + timedelta(days=interval),
                         self_grade=grade)
                ratio = it.interval_days / max(1, interval)
                assert lo <= ratio <= hi, (interval, ease, grade, ratio)
            it = SimpleNamespace(**vars(item))
            schedule(it, "incorrect", now=now + timedelta(days=interval))
            assert 1 <= it.interval_days <= max(1, interval)
        with engine.connect() as conn:
            items = {
                r[0]: r[1:]
                for r in conn.execute(
                    text(
                        "SELECT interval_days, stability, difficulty, due_at "
                        "FROM review_items WHERE user_id = :u"
                    ),
                    {"u": uid},
                )
            }
        assert sorted(items) == [0, 10]
        assert items[0][0] == 0.4872 and items[0][1] == 7.6
        assert items[10][0] == 10.0
        assert math.isclose(items[10][1], fsrs.difficulty_from_ease(2.0), abs_tol=1e-6)
        assert items[0][2] == now + timedelta(minutes=10)
        # Idempotent: a second run (fresh create_all schema path) is a no-op.
        _run("upgrade")
        assert {k: v for k, v in snapshot().items()} == after

        # Review one FSRS-only change, then downgrade: SM-2 columns resume.
        _run("downgrade")
        for table, cols in _STATE_COLS.items():
            assert not set(cols) & _columns(table)
        with engine.connect() as conn:
            eases = sorted(
                r[0] for r in conn.execute(
                    text("SELECT ease_factor FROM review_items WHERE user_id = :u"),
                    {"u": uid})
            )
        # 2.0 round-trips exactly; the history-less failed card (D=7.6)
        # comes back as ease 1.72 rather than its original 2.3.
        assert math.isclose(eases[0], 1.72, abs_tol=1e-6)
        assert math.isclose(eases[1], 2.0, abs_tol=1e-6)
        down = {k: v[:4] for k, v in _snapshot_sm2(uid).items()}
        for lid, (reps, interval, ease, reviewed) in zip(lex_ids, _SM2_STATES):
            e, i, r, due = down[lid]
            assert (i, r, due) == (interval, reps, before[lid][3])
            assert math.isclose(e, ease, abs_tol=1e-6)
    finally:
        cols = _columns("user_lexeme_srs")
        if "stability" not in cols:
            _run("upgrade")


def _snapshot_sm2(uid):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT lexeme_id, ease_factor, interval_days, repetitions, due_at "
                "FROM user_lexeme_srs WHERE user_id = :u"
            ),
            {"u": uid},
        )
        return {r[0]: tuple(r[1:]) for r in rows}


# --------------------------------------------------------------------- API


def test_review_answer_on_migrated_card_stays_near_old_due_date(client, admin, auth):
    uid, course_id, lexeme_id, item_id = _review_item(client, admin, auth)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        from app.models import PracticeItem

        srs = db.scalar(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == uid, UserLexemeSRS.lexeme_id == lexeme_id
            )
        )
        # Pre-FSRS row as it looks after migration: 30-day interval, on time.
        srs.interval_days, srs.repetitions, srs.ease_factor = 30, 6, 2.2
        srs.stability, srs.difficulty = 30.0, fsrs.difficulty_from_ease(2.2)
        srs.last_reviewed_at = now - timedelta(days=30)
        srs.due_at = now - timedelta(minutes=5)
        correct = db.get(PracticeItem, item_id).correct_response
        db.commit()
    res = client.post(
        f"/practice/items/{item_id}/answer", headers=auth,
        json={"response": correct},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert 30 <= body["next_interval_days"] <= 120
    with SessionLocal() as db:
        ev = db.scalar(select(ReviewEvent).where(ReviewEvent.user_id == uid))
        assert ev.rating == fsrs.GOOD
        assert ev.new_stability > 30 and ev.new_difficulty is not None
        srs = db.scalar(
            select(UserLexemeSRS).where(UserLexemeSRS.lexeme_id == lexeme_id,
                                        UserLexemeSRS.user_id == uid)
        )
        assert srs.stability == ev.new_stability
        assert srs.interval_days == body["next_interval_days"]
    forecast = client.get("/me/reviews/forecast", headers=auth).json()
    assert set(forecast) == {"today", "tomorrow", "this_week"}


def test_wrong_review_lowers_stability_via_api(client, admin, auth):
    uid, _, lexeme_id, item_id = _review_item(client, admin, auth)
    with SessionLocal() as db:
        srs = db.scalar(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == uid, UserLexemeSRS.lexeme_id == lexeme_id
            )
        )
        srs.interval_days, srs.repetitions = 20, 5
        srs.stability, srs.difficulty = 20.0, 5.0
        srs.last_reviewed_at = datetime.now(timezone.utc) - timedelta(days=20)
        db.commit()
    res = client.post(
        f"/practice/items/{item_id}/answer", headers=auth,
        json={"response": "__wrong__"},
    )
    assert res.status_code == 200 and res.json()["correct"] is False
    with SessionLocal() as db:
        srs = db.scalar(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == uid, UserLexemeSRS.lexeme_id == lexeme_id
            )
        )
        assert srs.stability < 20.0 and srs.difficulty > 5.0
        assert srs.lapses == 1 and srs.interval_days < 20
