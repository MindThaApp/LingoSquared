"""add due-review index and remove dead scaffolding

Guarded for fresh 0001-created schemas: the live ORM snapshot already
contains current tables/columns at 0001, so every later migration must check
existence before creating or dropping schema objects.
"""

import sqlalchemy as sa
from alembic import op


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

_SRS_TABLE = "user_lexeme_srs"
_SRS_DUE_INDEX = "ix_user_lexeme_srs_user_due_active"
_DEAD_TABLES = (
    "dialogue_edges",
    "dialogue_nodes",
    "answer_specs",
    "user_daily_quest_progress",
    "daily_quests",
    "dialogues",
    "media_assets",
)


def _table_names(bind):
    return set(sa.inspect(bind).get_table_names())


def _column_names(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _index_names(bind, table):
    return {index["name"] for index in sa.inspect(bind).get_indexes(table)}


def upgrade():
    bind = op.get_bind()
    tables = _table_names(bind)

    if _SRS_TABLE in tables:
        columns = _column_names(bind, _SRS_TABLE)
        if {"user_id", "due_at", "suspended"}.issubset(columns):
            if _SRS_DUE_INDEX not in _index_names(bind, _SRS_TABLE):
                op.create_index(
                    _SRS_DUE_INDEX,
                    _SRS_TABLE,
                    ["user_id", "due_at"],
                    postgresql_where=sa.text("NOT suspended"),
                )

    if "user_stats" in tables:
        columns = _column_names(bind, "user_stats")
        for column in ("hearts", "gems"):
            if column in columns:
                op.drop_column("user_stats", column)
                columns.remove(column)

    tables = _table_names(bind)
    for table in _DEAD_TABLES:
        if table in tables:
            op.drop_table(table)
            tables.remove(table)


def downgrade():
    raise RuntimeError(
        "0019 downgrade is intentionally unsupported: it removes confirmed "
        "dead scaffolding tables/columns. Restore a verified pre-upgrade "
        "backup if those objects are needed."
    )
