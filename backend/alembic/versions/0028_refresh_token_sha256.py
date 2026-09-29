"""add indexed SHA-256 lookup for refresh tokens

Legacy rows remain without a digest and are rejected on next use. Fresh
0001 schemas already include the current model shape, so all DDL is guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


_TABLE = "refresh_tokens"
_COLUMN = "token_sha256"
_INDEX = "uq_refresh_tokens_token_sha256"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns(_TABLE)}
    if _COLUMN not in columns:
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.String(length=64), nullable=True))

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes(_TABLE)}
    if _INDEX not in indexes:
        op.create_index(_INDEX, _TABLE, [_COLUMN], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in inspector.get_indexes(_TABLE)}
    if _INDEX in indexes:
        op.drop_index(_INDEX, table_name=_TABLE)
    columns = {column["name"] for column in inspector.get_columns(_TABLE)}
    if _COLUMN in columns:
        op.drop_column(_TABLE, _COLUMN)
