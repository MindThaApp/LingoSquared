"""unify lexeme SRS with generated practice items"""

import sqlalchemy as sa
from alembic import op

from app.models import UserLexemeSRS


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    UserLexemeSRS.__table__.create(bind=bind, checkfirst=True)

    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("practice_items")
    }
    if "source" not in columns:
        op.add_column(
            "practice_items",
            sa.Column(
                "source",
                sa.String(length=16),
                nullable=False,
                server_default=sa.text("'practice'"),
            ),
        )
    if "session_id" not in columns:
        op.add_column(
            "practice_items",
            sa.Column("session_id", sa.String(length=36), nullable=True),
        )
    if "target_lexeme_id" not in columns:
        op.add_column(
            "practice_items",
            sa.Column("target_lexeme_id", sa.String(length=36), nullable=True),
        )

    foreign_keys = {
        foreign_key.get("name")
        for foreign_key in sa.inspect(bind).get_foreign_keys("practice_items")
    }
    if "fk_practice_items_target_lexeme_id" not in foreign_keys:
        op.create_foreign_key(
            "fk_practice_items_target_lexeme_id",
            "practice_items",
            "lexemes",
            ["target_lexeme_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("practice_items")
    }
    if "ix_practice_items_session_id" not in indexes:
        op.create_index(
            "ix_practice_items_session_id",
            "practice_items",
            ["session_id"],
        )
    if "ix_practice_items_target_lexeme_id" not in indexes:
        op.create_index(
            "ix_practice_items_target_lexeme_id",
            "practice_items",
            ["target_lexeme_id"],
        )


def downgrade():
    raise RuntimeError(
        "0008 downgrade is intentionally unsupported because it would remove "
        "lexeme scheduling state and generated-review provenance. Restore a "
        "verified pre-upgrade backup instead."
    )
