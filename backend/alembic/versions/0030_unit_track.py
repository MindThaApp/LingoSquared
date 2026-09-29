"""add core/situation track to units

Fresh 0001 schemas already include live ORM columns, so DDL is guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "units" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("units")}
    if "track" not in columns:
        op.add_column(
            "units",
            sa.Column("track", sa.String(length=16), nullable=False, server_default="core"),
        )
    constraints = {item["name"] for item in sa.inspect(bind).get_check_constraints("units")}
    if "ck_units_track" not in constraints:
        op.create_check_constraint(
            "ck_units_track", "units", "track IN ('core','situation')"
        )


def downgrade():
    raise RuntimeError("0030 downgrade is intentionally unsupported; restore a verified pre-upgrade backup.")
