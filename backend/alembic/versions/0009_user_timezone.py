"""add user.timezone for timezone-aware streak/daily-window computation"""

import sqlalchemy as sa
from alembic import op


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("users")
    }
    if "timezone" not in columns:
        op.add_column(
            "users",
            sa.Column("timezone", sa.String(length=64), nullable=True),
        )


def downgrade():
    op.drop_column("users", "timezone")
