"""flag unreviewable lexeme SRS rows

Revision ID: 0039
Revises: 0038
"""

import sqlalchemy as sa
from alembic import op


revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None

_TABLE = "user_lexeme_srs"
_COLUMN = "unreviewable_at"


def _columns(bind):
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return None
    return {column["name"] for column in inspector.get_columns(_TABLE)}


def upgrade():
    bind = op.get_bind()
    columns = _columns(bind)
    if columns is not None and _COLUMN not in columns:
        op.add_column(
            _TABLE,
            sa.Column(_COLUMN, sa.DateTime(timezone=True), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    columns = _columns(bind)
    if columns is not None and _COLUMN in columns:
        op.drop_column(_TABLE, _COLUMN)
