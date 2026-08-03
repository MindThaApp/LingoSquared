"""allow dictation course exercise type

Widen the exercises.type check constraint for course-content dictation.
Guarded so a fresh 0001-created schema, which already reflects current
models, does not fail when this migration reaches head.
"""

import sqlalchemy as sa
from alembic import op


revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

_TABLE = "exercises"
_CHECK_NAME = "ck_exercises_type"
_EXERCISE_TYPES = (
    "multiple_choice",
    "translation",
    "reverse_translation",
    "fill_in_blank",
    "word_order",
    "matching_pairs",
    "listening_placeholder",
    "speaking_placeholder",
    "dialogue_response",
    "grammar_check",
    "flashcard",
    "reading_comprehension",
    "writing_prompt",
    "listen_select",
    "listen_type",
    "dictation",
    "listen_order",
    "dialogue_comprehension",
    "speak_repeat",
    "speak_response",
)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return

    existing = {
        constraint.get("name"): constraint.get("sqltext", "")
        for constraint in inspector.get_check_constraints(_TABLE)
    }
    if _CHECK_NAME in existing:
        # Fresh 0001 create_all uses the current ORM enum and therefore
        # already has the widened constraint.
        if "dictation" in str(existing[_CHECK_NAME]):
            return
        op.drop_constraint(_CHECK_NAME, _TABLE, type_="check")

    quoted = ",".join(f"'{value}'" for value in _EXERCISE_TYPES)
    op.create_check_constraint(
        _CHECK_NAME,
        _TABLE,
        f"type IN ({quoted})",
    )


def downgrade():
    raise RuntimeError(
        "0027 downgrade is intentionally unsupported: existing dictation "
        "exercises would violate the previous exercises.type constraint. "
        "Restore a verified pre-upgrade backup instead."
    )
