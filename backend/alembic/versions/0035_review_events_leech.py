"""review event log + leech tracking

Adds the append-only review_events table (one row per scheduled review, the
input for a later FSRS fit) and lapses/leech columns on user_lexeme_srs.
Fresh 0001 schemas already create these from the ORM models, so every step is
guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


_TABLE = "review_events"
_INDEXES = (
    ("ix_review_events_user_reviewed", ["user_id", "reviewed_at"]),
    ("ix_review_events_user_lexeme", ["user_id", "lexeme_id"]),
)


def _cols(bind, table):
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if _TABLE not in insp.get_table_names():
        op.create_table(
            _TABLE,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("lexeme_id", sa.String(36), sa.ForeignKey("lexemes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("exercise_id", sa.String(36), sa.ForeignKey("exercises.id", ondelete="SET NULL"), nullable=True),
            sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="SET NULL"), nullable=True),
            sa.Column("source", sa.String(16), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("result", sa.String(16), nullable=False),
            sa.Column("self_grade", sa.String(8), nullable=True),
            sa.Column("quality", sa.Integer, nullable=False),
            sa.Column("correct", sa.Boolean, nullable=False),
            sa.Column("previous_interval_days", sa.Integer, nullable=False),
            sa.Column("new_interval_days", sa.Integer, nullable=False),
            sa.Column("previous_ease", sa.Float, nullable=False),
            sa.Column("new_ease", sa.Float, nullable=False),
            sa.Column("previous_due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("new_due_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("latency_ms", sa.Integer, nullable=True),
        )
        for name, cols in _INDEXES:
            op.create_index(name, _TABLE, cols)
    have = _cols(bind, "user_lexeme_srs")
    if "lapses" not in have:
        op.add_column(
            "user_lexeme_srs",
            sa.Column("lapses", sa.Integer, nullable=False, server_default="0"),
        )
    if "leech" not in have:
        op.add_column(
            "user_lexeme_srs",
            sa.Column("leech", sa.Boolean, nullable=False, server_default=sa.false()),
        )


def downgrade():
    bind = op.get_bind()
    if _TABLE in sa.inspect(bind).get_table_names():
        op.drop_table(_TABLE)
    have = _cols(bind, "user_lexeme_srs")
    for col in ("leech", "lapses"):
        if col in have:
            op.drop_column("user_lexeme_srs", col)
