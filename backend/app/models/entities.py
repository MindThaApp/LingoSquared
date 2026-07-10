import enum
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc)


class ExerciseType(str, enum.Enum):
    multiple_choice = "multiple_choice"
    translation = "translation"
    reverse_translation = "reverse_translation"
    fill_in_blank = "fill_in_blank"
    word_order = "word_order"
    matching_pairs = "matching_pairs"
    listening_placeholder = "listening_placeholder"
    speaking_placeholder = "speaking_placeholder"
    dialogue_response = "dialogue_response"
    grammar_check = "grammar_check"
    flashcard = "flashcard"
    reading_comprehension = "reading_comprehension"
    writing_prompt = "writing_prompt"
    listen_select = "listen_select"
    listen_type = "listen_type"
    listen_order = "listen_order"
    dialogue_comprehension = "dialogue_comprehension"
    speak_repeat = "speak_repeat"
    speak_response = "speak_response"


class UnitSection(str, enum.Enum):
    reading_writing = "reading_writing"
    speaking = "speaking"


class CEFRLevel(str, enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class Language(Base):
    __tablename__ = "languages"
    __table_args__ = (
        CheckConstraint(
            "script IN ('latin','cyrillic','han','arabic','devanagari')",
            name="ck_languages_script",
        ),
        CheckConstraint("direction IN ('ltr','rtl')"),
    )

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    native_name: Mapped[str] = mapped_column(String(80))
    script: Mapped[str] = mapped_column(String(16))
    direction: Mapped[str] = mapped_column(String(3))


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(String(100), default="")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LearningPath(Base):
    __tablename__ = "learning_paths"
    __table_args__ = (
        UniqueConstraint(
            "source_language",
            "target_language",
            name="uq_learning_paths_direction",
        ),
        CheckConstraint(
            "source_language <> target_language",
            name="ck_learning_paths_distinct_languages",
        ),
        CheckConstraint(
            "(source_language = 'en') <> (target_language = 'en')",
            name="ck_learning_paths_english_hub",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    key: Mapped[str] = mapped_column(String(16), unique=True)
    source_language: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    target_language: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("source_language", "target_language", "title"),
        CheckConstraint("source_language <> target_language"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    learning_path_id: Mapped[str | None] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_language: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    target_language: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[CEFRLevel] = mapped_column(
        Enum(
            CEFRLevel,
            native_enum=False,
            create_constraint=True,
            name="ck_courses_cefr_level",
        ),
        default=CEFRLevel.A1,
        server_default="A1",
    )
    units = relationship(
        "Unit",
        cascade="all, delete-orphan",
        order_by="Unit.order",
    )


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("course_id", "order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(200))
    order: Mapped[int] = mapped_column(Integer)
    section: Mapped[UnitSection] = mapped_column(
        Enum(UnitSection, native_enum=False),
        default=UnitSection.reading_writing,
        server_default="reading_writing",
    )
    # Stable authoring key (e.g. "prs.a1.unit01"), nullable — content
    # imported before this column existed has no recoverable key. Unique
    # PER COURSE when present (DB-level partial unique index on
    # (course_id, content_key), migration 0015 -- NOT globally unique:
    # 0013 originally made this a bare global unique index, but fa-en/
    # nl-en/prs-en all realize the same underlying English target-
    # language content and so legitimately share identical content_key
    # values across different courses; a global constraint 500'd the
    # very next cross-course import, fixed 2026-07-07). Lets
    # import_content() update an already-shipped unit in place by key
    # instead of only ever matching by (course_id, order).
    content_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    lessons = relationship(
        "Lesson",
        cascade="all, delete-orphan",
        order_by="Lesson.order",
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("unit_id", "order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    unit_id: Mapped[str] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(200))
    order: Mapped[int] = mapped_column(Integer)
    # See Unit.content_key above — nullable, unique per parent (unit_id
    # here) not globally, migration 0015.
    content_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    exercises = relationship(
        "Exercise",
        cascade="all, delete-orphan",
        order_by="Exercise.order",
    )
    teaching_items = relationship(
        "ContentItem",
        cascade="all, delete-orphan",
        order_by="ContentItem.teaching_order",
    )


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (UniqueConstraint("lesson_id", "order"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE")
    )
    type: Mapped[ExerciseType] = mapped_column(
        Enum(
            ExerciseType,
            native_enum=False,
            create_constraint=True,
            name="ck_exercises_type",
            length=32,
        )
    )
    order: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[dict] = mapped_column(JSON)
    correct_response: Mapped[Any] = mapped_column(JSON)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    xp: Mapped[int] = mapped_column(Integer, default=10)
    # See Unit.content_key above — nullable, unique per parent (lesson_id
    # here) not globally, migration 0015. This is the field that lets a
    # content fix (e.g. a jargon-leak or
    # typo correction) update an already-shipped Exercise row in place
    # (same id, so every ExerciseAttempt/ContentIssueReport/ReviewItem
    # that references it is completely unaffected) instead of the old
    # create-missing-only behavior silently leaving stale rows forever.
    content_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )


class ContentItem(Base):
    __tablename__ = "content_items"
    __table_args__ = (
        UniqueConstraint(
            "lesson_id",
            "teaching_order",
            name="uq_content_items_lesson_teaching_order",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE")
    )
    lesson_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lessons.id",
            ondelete="CASCADE",
            name="fk_content_items_lesson_id",
        ),
        nullable=True,
    )
    teaching_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(30))
    language_code: Mapped[str] = mapped_column(ForeignKey("languages.code"))
    title: Mapped[str] = mapped_column(String(200), default="")
    content: Mapped[dict] = mapped_column(JSON)
    # See Unit.content_key above — nullable, unique per parent (lesson_id
    # here) not globally, migration 0015. Only meaningful for
    # lesson-scoped teaching cards (lesson_id is not null); standalone
    # ContentItem rows (course-level reference material, lesson_id
    # NULL) are out of scope for this update path.
    content_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )


class Lexeme(Base):
    """A reviewed token that practice generation may place in typed slots.

    Surface forms are course-scoped because the same token can be introduced
    at different points (and with different beginner-safe senses) in different
    courses. Part of speech remains in the identity so homographs with distinct
    grammatical behavior do not get collapsed into one sampler record.
    """

    __tablename__ = "lexemes"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "language_code",
            "token",
            "part_of_speech",
            name="uq_lexemes_course_language_token_pos",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
    )
    token: Mapped[str] = mapped_column(String(255))
    language_code: Mapped[str] = mapped_column(
        ForeignKey("languages.code", ondelete="RESTRICT"),
        index=True,
    )
    part_of_speech: Mapped[str] = mapped_column(String(40))
    english_gloss: Mapped[str] = mapped_column(String(255))
    agreement_tags: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance_lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="RESTRICT"),
        index=True,
    )
    provenance_lesson_content_key: Mapped[str] = mapped_column(String(255))
    provenance_content_key: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PracticeTemplate(Base):
    __tablename__ = "practice_templates"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "content_key",
            name="uq_practice_templates_course_content_key",
        ),
        CheckConstraint(
            "type IN ('multiple_choice','fill_in_blank','word_order',"
            "'translation','matching_pairs','listen_select')",
            name="ck_practice_templates_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    content_key: Mapped[str] = mapped_column(String(255))
    provenance_lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="RESTRICT"), index=True
    )
    type: Mapped[str] = mapped_column(String(32))
    frame: Mapped[dict] = mapped_column(JSON)
    slots: Mapped[dict] = mapped_column(JSON)
    slot_relations: Mapped[list] = mapped_column(
        JSON, default=list, server_default="[]"
    )
    answer_derivation: Mapped[dict] = mapped_column(JSON)
    feedback_frame: Mapped[dict] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserLexemeSRS(Base):
    __tablename__ = "user_lexeme_srs"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "lexeme_id",
            name="uq_user_lexeme_srs_user_lexeme",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    lexeme_id: Mapped[str] = mapped_column(
        ForeignKey("lexemes.id", ondelete="RESTRICT"),
        index=True,
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True,
    )
    ease_factor: Mapped[float] = mapped_column(
        Float, default=2.5, server_default="2.5"
    )
    interval_days: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    repetitions: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    mastery: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0"
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    introduced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    suspended: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    last_session_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )


class PracticeItem(Base):
    __tablename__ = "practice_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    template_id: Mapped[str] = mapped_column(
        ForeignKey("practice_templates.id", ondelete="RESTRICT"), index=True
    )
    filled_slots: Mapped[dict] = mapped_column(JSON)
    prompt: Mapped[dict] = mapped_column(JSON)
    correct_response: Mapped[Any] = mapped_column(JSON)
    xp_value: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(
        String(16), default="practice", server_default="practice"
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    target_lexeme_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "lexemes.id",
            ondelete="RESTRICT",
            name="fk_practice_items_target_lexeme_id",
        ),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"
    __table_args__ = (
        UniqueConstraint(
            "practice_item_id",
            name="uq_practice_attempts_practice_item",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    practice_item_id: Mapped[str] = mapped_column(
        ForeignKey("practice_items.id", ondelete="RESTRICT"), index=True
    )
    response: Mapped[Any] = mapped_column(JSON)
    correct: Mapped[bool] = mapped_column(Boolean)
    xp_awarded: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CheckpointAttempt(Base):
    __tablename__ = "checkpoint_attempts"
    __table_args__ = (
        Index(
            "ix_checkpoint_attempts_user_unit_created",
            "user_id",
            "unit_id",
            "created_at",
        ),
        CheckConstraint(
            "total_items BETWEEN 12 AND 15",
            name="ck_checkpoint_attempts_total_items",
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 1)",
            name="ck_checkpoint_attempts_score",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    unit_id: Mapped[str] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE")
    )
    total_items: Mapped[int] = mapped_column(Integer)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    weak_outcomes: Mapped[list] = mapped_column(
        JSON,
        default=list,
        server_default="[]",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
    )
    scored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE")
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    answer_count: Mapped[int] = mapped_column(Integer, default=0)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "client_operation_id",
            name="uq_exercise_attempts_user_client_operation",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    exercise_id: Mapped[str] = mapped_column(
        ForeignKey(
            "exercises.id",
            ondelete="RESTRICT",
            name="fk_exercise_attempts_exercise_id",
        )
    )
    content_release_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_releases.id", ondelete="SET NULL"),
        nullable=True,
    )
    lesson_session_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    client_operation_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    device_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    response: Mapped[Any] = mapped_column(JSON)
    correct: Mapped[bool] = mapped_column(Boolean)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    xp_awarded: Mapped[int] = mapped_column(Integer)
    feedback_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    objective_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserStats(Base):
    __tablename__ = "user_stats"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_goal: Mapped[int] = mapped_column(Integer, default=20)
    streak_freezes_available: Mapped[int] = mapped_column(Integer, default=0)
    last_freeze_used_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class QuestCompletion(Base):
    __tablename__ = "quest_completions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "quest_code",
            "date",
            name="uq_quest_completions_user_code_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    quest_code: Mapped[str] = mapped_column(String(80))
    date: Mapped[date] = mapped_column(Date)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
    )


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    # Browser PushSubscription fields (W3C Push API) -- endpoint is globally
    # unique per browser+device registration, not per user, since the same
    # physical subscription can't be registered twice even across accounts.
    endpoint: Mapped[str] = mapped_column(String(1024))
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now,
    )


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (UniqueConstraint("user_id", "exercise_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE")
    )
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    mastery: Mapped[float] = mapped_column(Float, default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    threshold: Mapped[int] = mapped_column(Integer)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    achievement_id: Mapped[str] = mapped_column(ForeignKey("achievements.id"))
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SkillProgress(Base):
    __tablename__ = "skill_progress"
    __table_args__ = (UniqueConstraint("user_id", "course_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    course_id: Mapped[str] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE")
    )
    completed_lessons: Mapped[int] = mapped_column(Integer, default=0)
    mastery: Mapped[float] = mapped_column(Float, default=0)


class VocabularyProgress(Base):
    __tablename__ = "vocabulary_progress"
    __table_args__ = (UniqueConstraint("user_id", "content_item_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    content_item_id: Mapped[str] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE")
    )
    mastery: Mapped[float] = mapped_column(Float, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class GrammarProgress(Base):
    __tablename__ = "grammar_progress"
    __table_args__ = (UniqueConstraint("user_id", "content_item_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    content_item_id: Mapped[str] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE")
    )
    mastery: Mapped[float] = mapped_column(Float, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class TTSUsage(Base):
    __tablename__ = "tts_usage"

    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    characters: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class LearningObjective(Base):
    __tablename__ = "learning_objectives"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('universal','realization')",
            name="ck_learning_objectives_scope",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    key: Mapped[str] = mapped_column(String(255), unique=True)
    scope: Mapped[str] = mapped_column(String(20))
    language_code: Mapped[str | None] = mapped_column(
        ForeignKey("languages.code", ondelete="RESTRICT"),
        nullable=True,
    )
    cefr_level: Mapped[CEFRLevel] = mapped_column(
        Enum(
            CEFRLevel,
            native_enum=False,
            create_constraint=True,
            name="ck_learning_objectives_cefr_level",
        ),
        default=CEFRLevel.A1,
    )
    title: Mapped[str] = mapped_column(String(255))
    can_do: Mapped[str] = mapped_column(Text)
    spine_objective_id: Mapped[str | None] = mapped_column(
        ForeignKey("learning_objectives.id", ondelete="SET NULL"),
        nullable=True,
    )
    module_kind: Mapped[str | None] = mapped_column(String(40), nullable=True)
    modalities: Mapped[list] = mapped_column(JSON, default=list)
    assessment_requirements: Mapped[list] = mapped_column(JSON, default=list)
    objective_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class LearningObjectivePrerequisite(Base):
    __tablename__ = "learning_objective_prerequisites"
    __table_args__ = (
        UniqueConstraint(
            "objective_id",
            "prerequisite_objective_id",
            name="uq_learning_objective_prerequisites_pair",
        ),
        CheckConstraint(
            "objective_id <> prerequisite_objective_id",
            name="ck_learning_objective_prerequisites_not_self",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    objective_id: Mapped[str] = mapped_column(
        ForeignKey("learning_objectives.id", ondelete="CASCADE")
    )
    prerequisite_objective_id: Mapped[str] = mapped_column(
        ForeignKey("learning_objectives.id", ondelete="CASCADE")
    )
    required_mastery: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ContentRelease(Base):
    __tablename__ = "content_releases"
    __table_args__ = (
        UniqueConstraint(
            "learning_path_id",
            "cefr_level",
            "version",
            name="uq_content_releases_path_level_version",
        ),
        CheckConstraint(
            "status IN ('draft','review','published','retired')",
            name="ck_content_releases_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    learning_path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="RESTRICT")
    )
    course_id: Mapped[str | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[str] = mapped_column(String(40))
    cefr_level: Mapped[CEFRLevel] = mapped_column(
        Enum(
            CEFRLevel,
            native_enum=False,
            create_constraint=True,
            name="ck_content_releases_cefr_level",
        ),
        default=CEFRLevel.A1,
    )
    schema_version: Mapped[str] = mapped_column(String(20), default="1")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    content_checksum: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ContentKey(Base):
    __tablename__ = "content_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    key: Mapped[str] = mapped_column(String(255), unique=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_release_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_releases.id", ondelete="SET NULL"),
        nullable=True,
    )
    supersedes_content_key_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ContentReview(Base):
    __tablename__ = "content_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    content_release_id: Mapped[str] = mapped_column(
        ForeignKey("content_releases.id", ondelete="CASCADE")
    )
    content_key_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_stage: Mapped[str] = mapped_column(String(50))
    reviewer_system: Mapped[str] = mapped_column(String(50))
    reviewer_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    fresh_context: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    findings: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LessonObjective(Base):
    __tablename__ = "lesson_objectives"
    __table_args__ = (
        UniqueConstraint(
            "lesson_id",
            "objective_id",
            "role",
            name="uq_lesson_objectives_mapping",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE")
    )
    objective_id: Mapped[str] = mapped_column(
        ForeignKey("learning_objectives.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(30), default="teach")
    required_mastery: Mapped[float] = mapped_column(Float, default=0.0)
    order: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ExerciseObjective(Base):
    __tablename__ = "exercise_objectives"
    __table_args__ = (
        UniqueConstraint(
            "exercise_id",
            "objective_id",
            "role",
            name="uq_exercise_objectives_mapping",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    exercise_id: Mapped[str] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE")
    )
    objective_id: Mapped[str] = mapped_column(
        ForeignKey("learning_objectives.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(30), default="assess")
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class ContentIssueReport(Base):
    __tablename__ = "content_issue_reports"
    __table_args__ = (
        # At most one of exercise_id/practice_item_id may be set. General
        # app/page feedback uses neither id and stores page_path instead.
        # num_nonnulls() is Postgres-specific but this project is
        # Postgres-only (see db/session.py).
        CheckConstraint(
            "num_nonnulls(exercise_id, practice_item_id) <= 1",
            name="ck_content_issue_reports_at_most_one_target",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    reporter_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    exercise_id: Mapped[str | None] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=True,
    )
    practice_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("practice_items.id", ondelete="RESTRICT"),
        nullable=True,
    )
    content_release_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_releases.id", ondelete="SET NULL"),
        nullable=True,
    )
    content_key_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    attempt_id: Mapped[str | None] = mapped_column(
        ForeignKey("exercise_attempts.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    learner_response: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    client_context: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="open")
    triage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    duplicate_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_issue_reports.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    triaged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class UserObjectiveMastery(Base):
    __tablename__ = "user_objective_mastery"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "objective_id",
            name="uq_user_objective_mastery",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    objective_id: Mapped[str] = mapped_column(
        ForeignKey("learning_objectives.id", ondelete="CASCADE")
    )
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class UserCourseEnrollment(Base):
    __tablename__ = "user_course_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "learning_path_id",
            name="uq_user_course_enrollments_path",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    learning_path_id: Mapped[str] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE")
    )
    active_course_id: Mapped[str | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
    )
    active_release_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_releases.id", ondelete="SET NULL"),
        nullable=True,
    )
    current_content_key: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    sync_cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    timezone: Mapped[str] = mapped_column(String(100), default="UTC")
    reminder_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    days_of_week: Mapped[list] = mapped_column(JSON, default=list)
    notification_types: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class StreakFreezeBalance(Base):
    __tablename__ = "streak_freeze_balances"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    available: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )


class StreakFreezeEvent(Base):
    __tablename__ = "streak_freeze_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(50))
    activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SyncOperation(Base):
    __tablename__ = "sync_operations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "operation_id",
            name="uq_sync_operations_user_operation",
        ),
        UniqueConstraint(
            "user_id",
            "device_id",
            "sequence",
            name="uq_sync_operations_user_device_sequence",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    operation_id: Mapped[str] = mapped_column(String(36))
    device_id: Mapped[str] = mapped_column(String(36))
    sequence: Mapped[int] = mapped_column(Integer)
    operation_type: Mapped[str] = mapped_column(String(50))
    content_release_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_releases.id", ondelete="SET NULL"),
        nullable=True,
    )
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    canonical_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
