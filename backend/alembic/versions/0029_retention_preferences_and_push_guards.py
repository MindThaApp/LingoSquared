"""course recommendation and deduplicated push send guards

Fresh 0001 schemas already contain current ORM columns/tables, so all DDL
is guarded for both fresh and historically migrated databases.
"""

import sqlalchemy as sa
from alembic import op


revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "courses" in tables:
        columns = {column["name"] for column in inspector.get_columns("courses")}
        if "recommended" not in columns:
            op.add_column(
                "courses",
                sa.Column("recommended", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
    if "push_notification_guards" not in tables and "users" in tables:
        op.create_table(
            "push_notification_guards",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("trigger_code", sa.String(length=40), nullable=False),
            sa.Column("local_date", sa.Date(), nullable=False),
            sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("user_id", "trigger_code", "local_date", name="uq_push_notification_guards_user_trigger_date"),
        )


def downgrade():
    raise RuntimeError("0029 downgrade is intentionally unsupported; restore a verified pre-upgrade backup.")
