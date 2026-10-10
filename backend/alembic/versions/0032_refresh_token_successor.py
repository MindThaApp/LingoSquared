"""record the successor of a rotated refresh token

Adds replaced_by_id + successor_sealed so /auth/refresh can answer a
retried rotation (lost response, concurrent tab) idempotently. Fresh 0001
schemas already include the current model shape, so all DDL is guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


_TABLE = "refresh_tokens"
_FK = "refresh_tokens_replaced_by_id_fkey"


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


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return
    for fk in inspector.get_foreign_keys(_TABLE):
        if fk.get("constrained_columns") == ["replaced_by_id"] and fk.get("name"):
            op.drop_constraint(fk["name"], _TABLE, type_="foreignkey")
    columns = {column["name"] for column in sa.inspect(bind).get_columns(_TABLE)}
    if "successor_sealed" in columns:
        op.drop_column(_TABLE, "successor_sealed")
    if "replaced_by_id" in columns:
        op.drop_column(_TABLE, "replaced_by_id")
