"""add unit checkpoint attempt records"""

import sqlalchemy as sa
from alembic import op


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "checkpoint_attempts" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "checkpoint_attempts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("unit_id", sa.String(length=36), nullable=False),
            sa.Column("total_items", sa.Integer(), nullable=False),
            sa.Column("passed", sa.Boolean(), nullable=True),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column(
                "weak_outcomes",
                sa.JSON(),
                server_default=sa.text("'[]'::json"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
            sa.Column(
                "scored_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.CheckConstraint(
                "total_items BETWEEN 12 AND 15",
                name="ck_checkpoint_attempts_total_items",
            ),
            sa.CheckConstraint(
                "score IS NULL OR (score >= 0 AND score <= 1)",
                name="ck_checkpoint_attempts_score",
            ),
            sa.ForeignKeyConstraint(
                ["unit_id"],
                ["units.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_checkpoint_attempts_user_unit_created",
            "checkpoint_attempts",
            ["user_id", "unit_id", "created_at"],
            unique=False,
        )


def downgrade():
    op.drop_index(
        "ix_checkpoint_attempts_user_unit_created",
        table_name="checkpoint_attempts",
    )
    op.drop_table("checkpoint_attempts")
