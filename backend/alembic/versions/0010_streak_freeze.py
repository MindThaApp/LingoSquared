"""add streak freeze fields to user_stats"""

import sqlalchemy as sa
from alembic import op


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("user_stats")
    }
    if "streak_freezes_available" not in columns:
        op.add_column(
            "user_stats",
            sa.Column(
                "streak_freezes_available",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
    if "last_freeze_used_date" not in columns:
        op.add_column(
            "user_stats",
            sa.Column("last_freeze_used_date", sa.Date(), nullable=True),
        )


def downgrade():
    op.drop_column("user_stats", "last_freeze_used_date")
    op.drop_column("user_stats", "streak_freezes_available")
