"""allow general app/page feedback reports

Adds the nullable columns needed for unauthenticated page-level feedback
and relaxes the ContentIssueReport target check from exactly one
exercise/practice item to at most one. Guarded throughout so a fresh
0001-created schema, which already reflects current models, does not fail
when this migration reaches head.
"""

import sqlalchemy as sa
from alembic import op


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

_TABLE = "content_issue_reports"


def _column(bind, name):
    return next(
        (
            column
            for column in sa.inspect(bind).get_columns(_TABLE)
            if column["name"] == name
        ),
        None,
    )


def _check_names(bind):
    return {
        constraint.get("name")
        for constraint in sa.inspect(bind).get_check_constraints(_TABLE)
    }


def upgrade():
    bind = op.get_bind()
    if _TABLE not in sa.inspect(bind).get_table_names():
        return

    page_path_col = _column(bind, "page_path")
    if page_path_col is None:
        op.add_column(
            _TABLE,
            sa.Column("page_path", sa.String(length=255), nullable=True),
        )

    reporter_col = _column(bind, "reporter_user_id")
    if reporter_col is not None and not reporter_col["nullable"]:
        op.alter_column(
            _TABLE,
            "reporter_user_id",
            existing_type=sa.String(length=36),
            nullable=True,
        )

    check_names = _check_names(bind)
    if "ck_content_issue_reports_exactly_one_target" in check_names:
        op.drop_constraint(
            "ck_content_issue_reports_exactly_one_target",
            _TABLE,
            type_="check",
        )
        check_names = _check_names(bind)

    if "ck_content_issue_reports_at_most_one_target" not in check_names:
        op.create_check_constraint(
            "ck_content_issue_reports_at_most_one_target",
            _TABLE,
            "num_nonnulls(exercise_id, practice_item_id) <= 1",
        )


def downgrade():
    raise RuntimeError(
        "0017 downgrade is intentionally unsupported: page-level reports "
        "may have no exercise_id/practice_item_id and no reporter_user_id, "
        "which would violate the previous NOT NULL/exactly-one constraints. "
        "Restore a verified pre-upgrade backup instead."
    )
