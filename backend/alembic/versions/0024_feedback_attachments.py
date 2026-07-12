"""add feedback screenshot attachments

Guarded for fresh 0001-created schemas: the live ORM snapshot already
contains current tables/columns at 0001, so every later migration must check
existence before creating schema objects.
"""

import sqlalchemy as sa
from alembic import op


revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def _table_names(bind):
    return set(sa.inspect(bind).get_table_names())


def _column_names(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def _index_names(bind, table):
    return {index["name"] for index in sa.inspect(bind).get_indexes(table)}


def _unique_constraint_names(bind, table):
    return {
        constraint["name"]
        for constraint in sa.inspect(bind).get_unique_constraints(table)
    }


def upgrade():
    bind = op.get_bind()
    tables = _table_names(bind)

    if "feedback_attachments" not in tables:
        op.create_table(
            "feedback_attachments",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("key", sa.String(length=80), nullable=False),
            sa.Column("report_id", sa.String(length=36), nullable=True),
            sa.Column("content_type", sa.String(length=40), nullable=False),
            sa.Column("byte_size", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["report_id"],
                ["content_issue_reports.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key", name="uq_feedback_attachments_key"),
        )

    tables = _table_names(bind)
    if "feedback_attachments" not in tables:
        return

    columns = _column_names(bind, "feedback_attachments")
    if "report_id" in columns and "created_at" in columns:
        indexes = _index_names(bind, "feedback_attachments")
        if "ix_feedback_attachments_report_created" not in indexes:
            op.create_index(
                "ix_feedback_attachments_report_created",
                "feedback_attachments",
                ["report_id", "created_at"],
            )

    constraints = _unique_constraint_names(bind, "feedback_attachments")
    if "key" in columns and "uq_feedback_attachments_key" not in constraints:
        op.create_unique_constraint(
            "uq_feedback_attachments_key",
            "feedback_attachments",
            ["key"],
        )


def downgrade():
    raise RuntimeError(
        "0024 downgrade is intentionally unsupported: feedback attachment "
        "metadata may point at private uploaded files. Restore a verified "
        "pre-upgrade backup if this migration must be undone."
    )
