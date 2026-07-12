"""add admin user-management account flags

Guarded for fresh 0001-created schemas: the live ORM snapshot already
contains current columns at 0001, so later migrations must check existence
before creating schema objects.
"""

import sqlalchemy as sa
from alembic import op


revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def _table_names(bind):
    return set(sa.inspect(bind).get_table_names())


def _column_names(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    if "users" not in _table_names(bind):
        return

    columns = _column_names(bind, "users")
    if "is_admin" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )
    if "is_active" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )


def downgrade():
    raise RuntimeError(
        "0026 downgrade is intentionally unsupported: admin/active account "
        "flags are security-sensitive. Restore a verified pre-upgrade backup "
        "if this migration must be undone."
    )
