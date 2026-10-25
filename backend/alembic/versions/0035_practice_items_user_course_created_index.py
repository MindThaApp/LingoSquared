"""index practice_items (user_id, course_id, created_at)

Serves the newest-items lookups in app/practice/service.py (_batch_rng,
_recent_signatures). Fresh 0001 schemas already create it from the ORM
model, so the DDL is guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


_TABLE = "practice_items"
_INDEX = "ix_practice_items_user_course_created"


def _has_index(bind) -> bool:
    return any(i["name"] == _INDEX for i in sa.inspect(bind).get_indexes(_TABLE))


def upgrade():
    bind = op.get_bind()
    if not _has_index(bind):
        op.create_index(_INDEX, _TABLE, ["user_id", "course_id", "created_at"])


def downgrade():
    bind = op.get_bind()
    if _has_index(bind):
        op.drop_index(_INDEX, table_name=_TABLE)
