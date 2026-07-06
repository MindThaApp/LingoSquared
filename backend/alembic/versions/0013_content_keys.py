"""add nullable content_key columns to units/lessons/exercises/content_items

Additive-only: every pre-existing row gets content_key = NULL (no
backfill attempted here — content imported before this migration has
no recoverable stable key). Enables import_content() to match incoming
content against already-shipped rows by content_key and update them in
place instead of only ever appending/skipping by position. Follows the
same per-course-scoped-uniqueness pattern already proven by
PracticeTemplate.content_key, except these keys are globally unique by
construction (e.g. "prs.a1.unit01.lesson01.exercise04.match_final_group")
so a single global unique index is sufficient.
"""

import sqlalchemy as sa
from alembic import op


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

_TABLES = ("units", "lessons", "exercises", "content_items")


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table in _TABLES:
        existing_columns = {col["name"] for col in inspector.get_columns(table)}
        if "content_key" not in existing_columns:
            op.add_column(
                table,
                sa.Column("content_key", sa.String(length=255), nullable=True),
            )
        existing_indexes = {ix["name"] for ix in inspector.get_indexes(table)}
        index_name = f"ix_{table}_content_key"
        if index_name not in existing_indexes:
            op.create_index(
                index_name,
                table,
                ["content_key"],
                unique=True,
                postgresql_where=sa.text("content_key IS NOT NULL"),
            )


def downgrade():
    for table in _TABLES:
        op.drop_index(f"ix_{table}_content_key", table_name=table)
        op.drop_column(table, "content_key")
