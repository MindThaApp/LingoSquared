"""single-use password reset tokens

Stores only the SHA-256 digest of each emailed token. Fresh 0001 schemas
already create the table from the ORM model, so the DDL is guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

_TABLE = "password_reset_tokens"


def upgrade():
    bind = op.get_bind()
    if _TABLE in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_password_reset_tokens_user_id", _TABLE, ["user_id"])
    op.create_index("ix_password_reset_tokens_expires_at", _TABLE, ["expires_at"])
    op.create_index("uq_password_reset_tokens_sha256", _TABLE, ["token_sha256"], unique=True)


def downgrade():
    bind = op.get_bind()
    if _TABLE in sa.inspect(bind).get_table_names():
        op.drop_table(_TABLE)
