"""record the successor of a rotated refresh token

Adds replaced_by_id + successor_sealed so /auth/refresh can answer a
retried rotation (lost response, concurrent tab) idempotently, grace_replays
to cap how many retries the grace window answers, and an index on
replaced_by_id (ON DELETE SET NULL looks up referencing rows for every
pruned token). Fresh 0001 schemas already include the current model shape,
so all DDL is guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


_TABLE = "refresh_tokens"
_FK = "refresh_tokens_replaced_by_id_fkey"
_INDEX = "ix_refresh_tokens_replaced_by_id"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns(_TABLE)}
    if "replaced_by_id" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("replaced_by_id", sa.String(length=36), nullable=True),
        )
    if "successor_sealed" not in columns:
        op.add_column(_TABLE, sa.Column("successor_sealed", sa.Text(), nullable=True))
    if "grace_replays" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("grace_replays", sa.Integer(), nullable=False, server_default="0"),
        )

    foreign_keys = sa.inspect(bind).get_foreign_keys(_TABLE)
    has_fk = any(fk.get("constrained_columns") == ["replaced_by_id"] for fk in foreign_keys)
    if not has_fk:
        op.create_foreign_key(
            _FK,
            _TABLE,
            _TABLE,
            ["replaced_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes(_TABLE)}
    if _INDEX not in indexes:
        # The column is new and all-NULL, so a plain build is quick.
        op.create_index(_INDEX, _TABLE, ["replaced_by_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return
    if _INDEX in {index["name"] for index in inspector.get_indexes(_TABLE)}:
        op.drop_index(_INDEX, table_name=_TABLE)
    for fk in inspector.get_foreign_keys(_TABLE):
        if fk.get("constrained_columns") == ["replaced_by_id"] and fk.get("name"):
            op.drop_constraint(fk["name"], _TABLE, type_="foreignkey")
    columns = {column["name"] for column in sa.inspect(bind).get_columns(_TABLE)}
    if "grace_replays" in columns:
        op.drop_column(_TABLE, "grace_replays")
    if "successor_sealed" in columns:
        op.drop_column(_TABLE, "successor_sealed")
    if "replaced_by_id" in columns:
        op.drop_column(_TABLE, "replaced_by_id")
