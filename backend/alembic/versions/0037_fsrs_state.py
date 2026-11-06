"""FSRS review state (replaces SM-2 scheduling)

Adds stability/difficulty to user_lexeme_srs and review_items and
rating/new_stability/new_difficulty to review_events. The SM-2 columns
(ease_factor, interval_days, repetitions) stay: the scheduler keeps them
populated as derived values so the API shape is unchanged.

Backfill (due_at is never touched, so no user's due date moves):
  stability  = max(1, interval_days)   SM-2's interval is FSRS's interval at
                                       90% retention, i.e. the stability
  difficulty = 5 - (ease - 2.5) * 10/3, clamped to [1, 10]
Lexeme cards never reviewed (repetitions 0, interval <= 1, no
last_reviewed_at) keep NULL state and start as new FSRS cards on their first
review. History-less review_items (created by a wrong answer) get the FSRS
initial Again state.

Downgrade writes ease_factor back from difficulty (exact inverse of the
mapping above, floor 1.3) and drops the columns. interval_days is already
current, so SM-2 resumes where FSRS left off. Fresh 0001 schemas already
create the columns from the ORM models, so DDL is guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None

_STATE = ("stability", "difficulty")
_EVENT = {"rating": sa.Integer, "new_stability": sa.Float, "new_difficulty": sa.Float}

_DIFFICULTY = (
    "CASE WHEN 5 - (ease_factor - 2.5) * 10.0 / 3.0 > 10 THEN 10 "
    "WHEN 5 - (ease_factor - 2.5) * 10.0 / 3.0 < 1 THEN 1 "
    "ELSE 5 - (ease_factor - 2.5) * 10.0 / 3.0 END"
)
_STABILITY = "CASE WHEN interval_days < 1 THEN 1 ELSE interval_days END"
_EASE = (
    "CASE WHEN 2.5 - (difficulty - 5) * 0.3 < 1.3 THEN 1.3 "
    "ELSE 2.5 - (difficulty - 5) * 0.3 END"
)


def _cols(bind, table):
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    for table in ("user_lexeme_srs", "review_items"):
        have = _cols(bind, table)
        for name in _STATE:
            if name not in have:
                op.add_column(table, sa.Column(name, sa.Float(), nullable=True))
    have = _cols(bind, "review_events")
    for name, typ in _EVENT.items():
        if name not in have:
            op.add_column("review_events", sa.Column(name, typ(), nullable=True))
    op.execute(
        f"UPDATE user_lexeme_srs SET stability = {_STABILITY}, "
        f"difficulty = {_DIFFICULTY} WHERE stability IS NULL AND "
        "(repetitions > 0 OR interval_days > 1 OR last_reviewed_at IS NOT NULL)"
    )
    op.execute(
        f"UPDATE review_items SET stability = {_STABILITY}, "
        f"difficulty = {_DIFFICULTY} WHERE stability IS NULL AND "
        "(repetitions > 0 OR interval_days > 1)"
    )
    # Review items are created by a wrong answer: a history-less one is a
    # just-failed card (FSRS initial Again state).
    op.execute(
        "UPDATE review_items SET stability = 0.4872, difficulty = 7.6 "
        "WHERE stability IS NULL"
    )


def downgrade():
    bind = op.get_bind()
    for table in ("user_lexeme_srs", "review_items"):
        if "difficulty" in _cols(bind, table):
            op.execute(
                f"UPDATE {table} SET ease_factor = {_EASE} "
                "WHERE difficulty IS NOT NULL"
            )
        for name in _STATE:
            if name in _cols(bind, table):
                op.drop_column(table, name)
    for name in _EVENT:
        if name in _cols(bind, "review_events"):
            op.drop_column("review_events", name)
