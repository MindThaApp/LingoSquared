"""track exercise retirement timestamps

Fresh 0001 schemas already include live ORM columns, so DDL is guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "exercises" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("exercises")}
    if "retired_at" not in columns:
        op.add_column(
            "exercises",
            sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("exercises")}
    if "ix_exercises_retired_at" not in indexes:
        op.create_index("ix_exercises_retired_at", "exercises", ["retired_at"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "exercises" not in inspector.get_table_names():
        return
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("exercises")}
    if "ix_exercises_retired_at" in indexes:
        op.drop_index("ix_exercises_retired_at", table_name="exercises")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("exercises")}
    if "retired_at" in columns:
        op.drop_column("exercises", "retired_at")
