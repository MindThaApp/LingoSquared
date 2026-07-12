"""add social login identities

Guarded for fresh 0001-created schemas: the live ORM snapshot already
contains current tables/columns at 0001, so every later migration must check
existence before creating schema objects.
"""

import sqlalchemy as sa
from alembic import op


revision = "0023"
down_revision = "0022"
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

    if "users" in tables and "password_hash" in _column_names(bind, "users"):
        password_hash_column = next(
            column
            for column in sa.inspect(bind).get_columns("users")
            if column["name"] == "password_hash"
        )
        if not password_hash_column.get("nullable"):
            op.alter_column(
                "users",
                "password_hash",
                existing_type=sa.Text(),
                nullable=True,
            )

    tables = _table_names(bind)
    if "user_identities" not in tables:
        op.create_table(
            "user_identities",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("provider", sa.String(length=16), nullable=False),
            sa.Column("provider_subject", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "provider IN ('google','apple')",
                name="ck_user_identities_provider",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("provider", "provider_subject"),
        )

    tables = _table_names(bind)
    if "user_identities" not in tables:
        return
    columns = _column_names(bind, "user_identities")
    indexes = _index_names(bind, "user_identities")
    if "user_id" in columns and "ix_user_identities_user_id" not in indexes:
        op.create_index(
            "ix_user_identities_user_id",
            "user_identities",
            ["user_id"],
        )


def downgrade():
    raise RuntimeError(
        "0023 downgrade is intentionally unsupported: social-login users may "
        "have null password_hash values and linked user_identities rows. "
        "Restore a verified pre-upgrade backup if this migration must be "
        "undone."
    )
