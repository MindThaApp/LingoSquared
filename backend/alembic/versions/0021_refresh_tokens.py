"""add refresh tokens

Guarded for fresh 0001-created schemas: the live ORM snapshot already
contains current tables/columns at 0001, so every later migration must check
existence before creating schema objects.
"""

import sqlalchemy as sa
from alembic import op


revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def _table_names(bind):
    return set(sa.inspect(bind).get_table_names())


def _column_names(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _index_names(bind, table):
    return {index["name"] for index in sa.inspect(bind).get_indexes(table)}


def upgrade():
    bind = op.get_bind()
    tables = _table_names(bind)

    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("token_hash", sa.Text(), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    tables = _table_names(bind)
    if "refresh_tokens" not in tables:
        return

    columns = _column_names(bind, "refresh_tokens")
    indexes = _index_names(bind, "refresh_tokens")
    if "user_id" in columns and "ix_refresh_tokens_user_id" not in indexes:
        op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    indexes = _index_names(bind, "refresh_tokens")
    if "expires_at" in columns and "ix_refresh_tokens_expires_at" not in indexes:
        op.create_index(
            "ix_refresh_tokens_expires_at",
            "refresh_tokens",
            ["expires_at"],
        )
    indexes = _index_names(bind, "refresh_tokens")
    if (
        {"user_id", "expires_at"}.issubset(columns)
        and "ix_refresh_tokens_user_expires" not in indexes
    ):
        op.create_index(
            "ix_refresh_tokens_user_expires",
            "refresh_tokens",
            ["user_id", "expires_at"],
        )


def downgrade():
    bind = op.get_bind()
    if "refresh_tokens" in _table_names(bind):
        op.drop_table("refresh_tokens")
