"""add indexes for lexeme browser and mistakes hub

Guarded for fresh 0001-created schemas: the live ORM snapshot already
contains current tables/columns at 0001, so every later migration must check
existence before creating schema objects.
"""

import sqlalchemy as sa
from alembic import op


revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def _table_names(bind):
    return set(sa.inspect(bind).get_table_names())


def _column_names(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _index_names(bind, table):
    return {index["name"] for index in sa.inspect(bind).get_indexes(table)}


def _create_index_if_possible(bind, table, name, columns):
    if table not in _table_names(bind):
        return
    existing_columns = _column_names(bind, table)
    if not set(columns).issubset(existing_columns):
        return
    if name in _index_names(bind, table):
        return
    op.create_index(name, table, columns)


def upgrade():
    bind = op.get_bind()
    _create_index_if_possible(
        bind,
        "user_lexeme_srs",
        "ix_user_lexeme_srs_user_course_due",
        ["user_id", "course_id", "due_at"],
    )
    _create_index_if_possible(
        bind,
        "user_lexeme_srs",
        "ix_user_lexeme_srs_user_course_mastery",
        ["user_id", "course_id", "mastery"],
    )
    _create_index_if_possible(
        bind,
        "user_lexeme_srs",
        "ix_user_lexeme_srs_user_course_introduced",
        ["user_id", "course_id", "introduced_at"],
    )
    _create_index_if_possible(
        bind,
        "practice_items",
        "ix_practice_items_course_target_lexeme",
        ["course_id", "target_lexeme_id"],
    )
    _create_index_if_possible(
        bind,
        "practice_attempts",
        "ix_practice_attempts_user_created",
        ["user_id", "created_at"],
    )


def downgrade():
    bind = op.get_bind()
    for table, name in (
        ("practice_attempts", "ix_practice_attempts_user_created"),
        ("practice_items", "ix_practice_items_course_target_lexeme"),
        ("user_lexeme_srs", "ix_user_lexeme_srs_user_course_introduced"),
        ("user_lexeme_srs", "ix_user_lexeme_srs_user_course_mastery"),
        ("user_lexeme_srs", "ix_user_lexeme_srs_user_course_due"),
    ):
        if table in _table_names(bind) and name in _index_names(bind, table):
            op.drop_index(name, table_name=table)
