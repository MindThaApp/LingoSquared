"""scope content_key uniqueness per-parent, not globally

Real bug found live 2026-07-07 while performance-testing the Endless
Practice engine: 0013's `content_key` indexes were GLOBALLY unique
(`ix_{table}_content_key` on the bare column), on the incorrect
assumption that content_key strings are unique system-wide. They are
not -- fa-en, nl-en, and prs-en all realize the SAME underlying English
target-language content (`docs/content/realizations/en/*.yaml`), so
importing fresh content_key-bearing units/lessons/exercises/teaching
cards for a SECOND of those three courses (after the first already has
matching content_key values) hits a real `UniqueViolation` and the
import 500s. Reproduced live: imported prs-en cleanly into an isolated
DB, then nl-en into the same DB -- `IntegrityError: duplicate key value
violates unique constraint "ix_units_content_key" ... Key
(content_key)=(en.a1.unit01.greetings) already exists`.

The application-level matching logic (`_match_by_content_key()` in
`app/content/service.py`) was never actually wrong -- every caller
already scopes its `existing` query to the right parent
(`Unit.course_id == course.id`, `Lesson.unit_id == unit.id`,
`Exercise.lesson_id == lesson.id`) before building the lookup dict, so
content_key matching itself is already correctly per-course/per-unit/
per-lesson. Only the DATABASE-level uniqueness guarantee was too
strict. Fix: replace each global partial unique index with a composite
one scoped to the natural parent column every table already has
(course_id for units, unit_id for lessons, lesson_id for
exercises/content_items) -- content_key strings are unique-by-
construction within one course's own hierarchy (they encode their own
unit/lesson/exercise path), so this is sufficient to prevent real
duplicates within a course while allowing the same key to exist
across different courses that happen to share source content.
"""

import sqlalchemy as sa
from alembic import op


revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

# (table, old global index name, new composite index name, parent column)
_SPECS = (
    ("units", "ix_units_content_key", "ix_units_course_content_key", "course_id"),
    ("lessons", "ix_lessons_content_key", "ix_lessons_unit_content_key", "unit_id"),
    (
        "exercises",
        "ix_exercises_content_key",
        "ix_exercises_lesson_content_key",
        "lesson_id",
    ),
    (
        "content_items",
        "ix_content_items_content_key",
        "ix_content_items_lesson_content_key",
        "lesson_id",
    ),
)


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for table, old_name, new_name, parent_col in _SPECS:
        existing_indexes = {ix["name"] for ix in inspector.get_indexes(table)}
        if old_name in existing_indexes:
            op.drop_index(old_name, table_name=table)
        # Re-inspect: the drop above changes what's live, and a fresh
        # install may never have created the old global index at all
        # (0001's create_all() doesn't know about indexes added by a
        # later migration's raw DDL) but could already have the new one
        # if this migration ran once and is being re-run defensively.
        existing_indexes = {
            ix["name"] for ix in sa.inspect(bind).get_indexes(table)
        }
        if new_name not in existing_indexes:
            op.create_index(
                new_name,
                table,
                [parent_col, "content_key"],
                unique=True,
                postgresql_where=sa.text("content_key IS NOT NULL"),
            )


def downgrade():
    raise RuntimeError(
        "0015 downgrade is intentionally unsupported: the whole point of "
        "this migration is that the SAME content_key legitimately exists "
        "across different courses (fa-en/nl-en/prs-en all realize the same "
        "underlying English content) -- confirmed live, re-creating the "
        "old global unique index against real post-fix data fails with "
        "a UniqueViolation the moment more than one course has imported "
        "matching content_key values, which is the expected/desired state, "
        "not a corruption to revert. Restore a verified pre-upgrade backup "
        "instead if the old (broken) global constraint is genuinely needed."
    )
