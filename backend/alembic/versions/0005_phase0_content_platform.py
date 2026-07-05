"""add Phase 0 content, objective, offline, and retention schema"""

from alembic import op
import sqlalchemy as sa

from app.models import (
    AnswerSpec,
    ContentIssueReport,
    ContentKey,
    ContentRelease,
    ContentReview,
    DailyQuest,
    Dialogue,
    DialogueEdge,
    DialogueNode,
    ExerciseObjective,
    LearningObjective,
    LearningObjectivePrerequisite,
    LearningPath,
    LessonObjective,
    MediaAsset,
    NotificationPreference,
    PushSubscription,
    StreakFreezeBalance,
    StreakFreezeEvent,
    SyncOperation,
    UserCourseEnrollment,
    UserDailyQuestProgress,
    UserObjectiveMastery,
)


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


EXERCISE_TYPES = (
    "multiple_choice",
    "translation",
    "reverse_translation",
    "fill_in_blank",
    "word_order",
    "matching_pairs",
    "listening_placeholder",
    "speaking_placeholder",
    "dialogue_response",
    "grammar_check",
    "flashcard",
    "reading_comprehension",
    "writing_prompt",
    "listen_select",
    "listen_type",
    "listen_order",
    "dialogue_comprehension",
    "speak_repeat",
    "speak_response",
)


PHASE0_TABLES = (
    LearningPath.__table__,
    LearningObjective.__table__,
    LearningObjectivePrerequisite.__table__,
    ContentRelease.__table__,
    ContentKey.__table__,
    MediaAsset.__table__,
    Dialogue.__table__,
    DialogueNode.__table__,
    DialogueEdge.__table__,
    ContentReview.__table__,
    AnswerSpec.__table__,
    LessonObjective.__table__,
    ExerciseObjective.__table__,
    ContentIssueReport.__table__,
    UserObjectiveMastery.__table__,
    UserCourseEnrollment.__table__,
    PushSubscription.__table__,
    NotificationPreference.__table__,
    DailyQuest.__table__,
    UserDailyQuestProgress.__table__,
    StreakFreezeBalance.__table__,
    StreakFreezeEvent.__table__,
    SyncOperation.__table__,
)


def _column_names(bind, table_name):
    return {
        column["name"]
        for column in sa.inspect(bind).get_columns(table_name)
    }


def _constraint_names(bind, table_name, kind):
    inspector = sa.inspect(bind)
    if kind == "unique":
        constraints = inspector.get_unique_constraints(table_name)
    elif kind == "check":
        constraints = inspector.get_check_constraints(table_name)
    elif kind == "foreign_key":
        constraints = inspector.get_foreign_keys(table_name)
    else:
        raise ValueError(f"unsupported constraint kind: {kind}")
    return {constraint.get("name") for constraint in constraints}


def upgrade():
    bind = op.get_bind()

    # New tables are created in dependency order. The project already uses
    # model metadata in 0001_initial.py; this follows that established
    # convention while limiting creation to the Phase 0 table snapshot.
    for table in PHASE0_TABLES:
        table.create(bind=bind, checkfirst=True)

    course_columns = _column_names(bind, "courses")
    if "learning_path_id" not in course_columns:
        op.add_column(
            "courses",
            sa.Column("learning_path_id", sa.String(length=36), nullable=True),
        )

    course_foreign_keys = _constraint_names(bind, "courses", "foreign_key")
    if "fk_courses_learning_path_id" not in course_foreign_keys:
        op.create_foreign_key(
            "fk_courses_learning_path_id",
            "courses",
            "learning_paths",
            ["learning_path_id"],
            ["id"],
            ondelete="SET NULL",
        )

    course_indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("courses")
    }
    if "ix_courses_learning_path_id" not in course_indexes:
        op.create_index(
            "ix_courses_learning_path_id",
            "courses",
            ["learning_path_id"],
        )

    attempt_columns = _column_names(bind, "exercise_attempts")
    additions = (
        (
            "content_release_id",
            sa.Column(
                "content_release_id",
                sa.String(length=36),
                nullable=True,
            ),
        ),
        (
            "lesson_session_id",
            sa.Column("lesson_session_id", sa.String(length=36), nullable=True),
        ),
        (
            "client_operation_id",
            sa.Column("client_operation_id", sa.String(length=36), nullable=True),
        ),
        (
            "device_id",
            sa.Column("device_id", sa.String(length=36), nullable=True),
        ),
        (
            "outcome",
            sa.Column("outcome", sa.String(length=32), nullable=True),
        ),
        (
            "feedback_snapshot",
            sa.Column("feedback_snapshot", sa.JSON(), nullable=True),
        ),
        (
            "objective_snapshot",
            sa.Column("objective_snapshot", sa.JSON(), nullable=True),
        ),
        (
            "occurred_at",
            sa.Column(
                "occurred_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        ),
        (
            "received_at",
            sa.Column(
                "received_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        ),
    )
    for name, column in additions:
        if name not in attempt_columns:
            op.add_column("exercise_attempts", column)

    attempt_foreign_keys = sa.inspect(bind).get_foreign_keys("exercise_attempts")
    content_release_fk_exists = any(
        fk.get("constrained_columns") == ["content_release_id"]
        for fk in attempt_foreign_keys
    )
    if not content_release_fk_exists:
        op.create_foreign_key(
            "fk_exercise_attempts_content_release_id",
            "exercise_attempts",
            "content_releases",
            ["content_release_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Exercise attempts are historical records. Replace the legacy
    # exercise ON DELETE CASCADE foreign key with RESTRICT.
    exercise_fk = next(
        (
            fk
            for fk in attempt_foreign_keys
            if fk.get("constrained_columns") == ["exercise_id"]
        ),
        None,
    )
    if exercise_fk and exercise_fk.get("name"):
        op.drop_constraint(
            exercise_fk["name"],
            "exercise_attempts",
            type_="foreignkey",
        )
        op.create_foreign_key(
            "fk_exercise_attempts_exercise_id",
            "exercise_attempts",
            "exercises",
            ["exercise_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    attempt_uniques = _constraint_names(
        bind,
        "exercise_attempts",
        "unique",
    )
    if "uq_exercise_attempts_user_client_operation" not in attempt_uniques:
        op.create_unique_constraint(
            "uq_exercise_attempts_user_client_operation",
            "exercise_attempts",
            ["user_id", "client_operation_id"],
        )

    # The legacy non-native enum is a VARCHAR sized for the previous values.
    # Expand it and replace any prior exercise-type check with the complete
    # forward-compatible value set.
    checks = sa.inspect(bind).get_check_constraints("exercises")
    for check in checks:
        sqltext = str(check.get("sqltext") or "")
        name = check.get("name")
        if name and "type" in sqltext and "multiple_choice" in sqltext:
            op.drop_constraint(name, "exercises", type_="check")

    op.alter_column(
        "exercises",
        "type",
        existing_type=sa.String(length=21),
        type_=sa.String(length=32),
        existing_nullable=False,
    )

    check_names = _constraint_names(bind, "exercises", "check")
    if "ck_exercises_type" not in check_names:
        quoted = ",".join(f"'{value}'" for value in EXERCISE_TYPES)
        op.create_check_constraint(
            "ck_exercises_type",
            "exercises",
            f"type IN ({quoted})",
        )


def downgrade():
    raise RuntimeError(
        "0005 downgrade is intentionally unsupported because it would remove "
        "immutable releases, attempts, reviews, sync history, and learner state. "
        "Restore a verified pre-upgrade backup instead."
    )
