"""drop dead Phase 0 scaffolding tables (12 unreferenced ORM models)

A 2026-07-10 backend-architecture review found 12 ORM models in
app/models/entities.py with zero references anywhere in app/ outside
their own definitions -- the fourth instance of the dead-scaffolding
pattern (after AnswerSpec, MediaAsset/Dialogue*, and
DailyQuest/UserDailyQuestProgress, all removed in 0019). Their tables
physically exist on every already-migrated database because
0001_initial.py runs Base.metadata.create_all() against the live model
set (and 0005 also created them explicitly, edited the same day to
stop). The model classes were removed from entities.py; this migration
drops the leftover tables.

Also removed here, because they point INTO the dead content_releases
table from live tables:
- exercise_attempts.content_release_id (column + FK, never read or
  written anywhere in app/)
- content_keys.content_release_id (column + FK, never read or written;
  ContentKey itself is live via app/content/service.py)
- content_issue_reports.content_release_id keeps its COLUMN (it is part
  of the ContentIssueOut admin-triage API shape, always null) but its
  FK constraint to content_releases is dropped.

Guarded like 0019: fresh databases migrated 0001->head never create any
of this (the live model set no longer contains it), so every action
checks existence first. Drop order is FK-safe: referencing tables drop
before referenced ones (e.g. learning_objective_prerequisites before
learning_objectives, content_reviews/user_course_enrollments/
sync_operations before content_releases).
"""

import sqlalchemy as sa
from alembic import op


revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


# Children first, parents last. Within the dead set:
#   learning_objectives <- learning_objective_prerequisites,
#       lesson_objectives, exercise_objectives, user_objective_mastery
#   content_releases <- content_reviews, user_course_enrollments,
#       sync_operations (plus the live-table FKs handled separately)
# The remaining tables only reference live tables (users,
# learning_paths, courses) and can drop in any order.
_DEAD_TABLES = (
    "learning_objective_prerequisites",
    "lesson_objectives",
    "exercise_objectives",
    "user_objective_mastery",
    "learning_objectives",
    "content_reviews",
    "user_course_enrollments",
    "sync_operations",
    "content_releases",
    "notification_preferences",
    "streak_freeze_balances",
    "streak_freeze_events",
)

# Live tables holding a foreign key into the dead content_releases
# table, mapped to whether the column itself should also be dropped
# (False keeps the column and only detaches the constraint).
_CONTENT_RELEASE_REFS = (
    ("exercise_attempts", True),
    ("content_keys", True),
    ("content_issue_reports", False),
)


def _table_names(bind):
    return set(sa.inspect(bind).get_table_names())


def _column_names(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    tables = _table_names(bind)

    # 1. Detach (and mostly drop) the live-table columns that reference
    #    content_releases, so the table itself can drop cleanly.
    for table, drop_column in _CONTENT_RELEASE_REFS:
        if table not in tables:
            continue
        if "content_release_id" not in _column_names(bind, table):
            continue
        for fk in sa.inspect(bind).get_foreign_keys(table):
            if (
                fk.get("referred_table") == "content_releases"
                and fk.get("constrained_columns") == ["content_release_id"]
                and fk.get("name")
            ):
                op.drop_constraint(fk["name"], table, type_="foreignkey")
        if drop_column:
            op.drop_column(table, "content_release_id")

    # 2. Drop the dead tables, children before parents.
    tables = _table_names(bind)
    for table in _DEAD_TABLES:
        if table in tables:
            op.drop_table(table)
            tables.remove(table)


def downgrade():
    raise RuntimeError(
        "0021 downgrade is intentionally unsupported: it removes confirmed "
        "dead Phase 0 scaffolding tables/columns. Restore a verified "
        "pre-upgrade backup if those objects are needed."
    )
