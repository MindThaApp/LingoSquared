"""add push_subscriptions table (Phase E4, web push)

Direct-Claude build during a Codex usage-limit outage (reset not until
the next day) -- per this project's standing contingency (see CLAUDE.md,
the Phase C precedent), continued rather than blocked. Defensively
checks table existence before create_table, following the same guarded
pattern every migration after 0001 must use (see CLAUDE.md footguns).
"""

import sqlalchemy as sa
from alembic import op


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = sa.inspect(bind).get_table_names()
    if "push_subscriptions" not in tables:
        op.create_table(
            "push_subscriptions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "user_id",
                sa.String(length=36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("endpoint", sa.String(length=1024), nullable=False),
            sa.Column("p256dh", sa.String(length=255), nullable=False),
            sa.Column("auth", sa.String(length=255), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "endpoint", name="uq_push_subscriptions_endpoint"
            ),
        )
        op.create_index(
            "ix_push_subscriptions_user_id",
            "push_subscriptions",
            ["user_id"],
        )


def downgrade():
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
