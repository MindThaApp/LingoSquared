"""gamification: per-user hearts/gems state and the append-only gem ledger

Adds two NEW tables only (user_game_state, gem_transactions). Nothing existing
is altered or removed; downgrade drops only these two new tables.

Revision ID: 0040
Revises: 0039
"""

import sqlalchemy as sa
from alembic import op


revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "user_game_state" not in tables:
        op.create_table(
            "user_game_state",
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("hearts", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("hearts_anchor_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_practice_restore_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("gem_balance", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("leaderboard_opt_out", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.CheckConstraint("hearts >= 0 AND hearts <= 5", name="ck_user_game_state_hearts"),
            sa.CheckConstraint("gem_balance >= 0", name="ck_user_game_state_gems"),
        )
    if "gem_transactions" not in tables:
        op.create_table(
            "gem_transactions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("idempotency_key", sa.String(128), nullable=False),
            sa.Column("balance_after", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("user_id", "idempotency_key", name="uq_gem_transactions_user_key"),
        )
        op.create_index("ix_gem_transactions_user_created", "gem_transactions", ["user_id", "created_at"])


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    # Only the two tables this revision introduced.
    if "gem_transactions" in tables:
        op.drop_table("gem_transactions")
    if "user_game_state" in tables:
        op.drop_table("user_game_state")
