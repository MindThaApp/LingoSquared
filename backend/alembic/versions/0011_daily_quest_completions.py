"""add daily quest completion records"""

import sqlalchemy as sa
from alembic import op


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "quest_completions" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "quest_completions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("quest_code", sa.String(length=80), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column(
                "awarded_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "quest_code",
                "date",
                name="uq_quest_completions_user_code_date",
            ),
        )
        op.create_index(
            op.f("ix_quest_completions_user_id"),
            "quest_completions",
            ["user_id"],
            unique=False,
        )


def downgrade():
    op.drop_index(
        op.f("ix_quest_completions_user_id"),
        table_name="quest_completions",
    )
    op.drop_table("quest_completions")
