import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ContentItem,
    ContentKey,
    Course,
    Exercise,
    Language,
    Lesson,
    Lexeme,
    PracticeTemplate,
    Unit,
)
from app.schemas.api import ImportRequest, PracticeArtifactImport


logger = logging.getLogger(__name__)

KINDS = {
    "vocabulary",
    "phrase",
    "grammar_note",
    "dialogue",
    "pronunciation_note",
    "cultural_note",
}


def validation_errors(db: Session, data: ImportRequest):
    codes = set(db.scalars(select(Language.code)))
    errors = []
    seen = set()

    for ci, course in enumerate(data.courses):
        if course.source_language not in codes:
            errors.append(f"courses[{ci}].source_language is unsupported")
        if course.target_language not in codes:
            errors.append(f"courses[{ci}].target_language is unsupported")

        key = (
            course.source_language,
            course.target_language,
            course.title,
        )
        if key in seen:
            errors.append(f"courses[{ci}] duplicates a course in this payload")
        seen.add(key)

        if not course.units:
            errors.append(f"courses[{ci}].units must not be empty")

        unit_orders = [unit.order for unit in course.units]
        if len(set(unit_orders)) != len(unit_orders):
            errors.append(f"courses[{ci}] has duplicate unit order")

        for ui, unit in enumerate(course.units):
            if not unit.lessons:
                errors.append(
                    f"courses[{ci}].units[{ui}].lessons must not be empty"
                )

            lesson_orders = [lesson.order for lesson in unit.lessons]
            if len(set(lesson_orders)) != len(lesson_orders):
                errors.append(f"unit {ui} has duplicate lesson order")

            for li, lesson in enumerate(unit.lessons):
                if not lesson.exercises:
                    errors.append(f"lesson {li} exercises must not be empty")

                for ti, card in enumerate(lesson.teaching):
                    if not card.text_blocks:
                        errors.append(
                            f"lesson {li} teaching card {ti} requires text_blocks"
                        )

                    for block in card.text_blocks:
                        language = db.get(Language, block.language_code)
                        if not language:
                            errors.append(
                                f"lesson {li} teaching card {ti} language "
                                "is unsupported"
                            )
                        elif block.direction != language.direction:
                            errors.append(
                                f"lesson {li} teaching card {ti} direction "
                                "is incorrect"
                            )

                exercise_orders = [
                    exercise.order
                    for exercise in lesson.exercises
                ]
                if len(set(exercise_orders)) != len(exercise_orders):
                    errors.append(f"lesson {li} has duplicate exercise order")

                for ei, exercise in enumerate(lesson.exercises):
                    block_groups = [
                        ("text_blocks", exercise.prompt.get("text_blocks"))
                    ]
                    if exercise.type.value == "flashcard":
                        block_groups.append(
                            (
                                "back_text_blocks",
                                exercise.prompt.get("back_text_blocks"),
                            )
                        )

                    for field, blocks in block_groups:
                        if not isinstance(blocks, list) or not blocks:
                            errors.append(
                                f"exercise {ei} requires prompt.{field}"
                            )
                            continue

                        for block in blocks:
                            language = db.get(
                                Language,
                                block.get("language_code"),
                            )
                            if not language:
                                errors.append(
                                    f"exercise {ei} {field} language "
                                    "is unsupported"
                                )
                            elif block.get("direction") != language.direction:
                                errors.append(
                                    f"exercise {ei} {field} direction "
                                    "is incorrect"
                                )

        for item in course.content_items:
            if item.language_code not in codes:
                errors.append(
                    f"content item language {item.language_code} is unsupported"
                )

    return list(dict.fromkeys(errors))


def _match_by_content_key(existing_rows, incoming_items):
    """Partition incoming items against existing DB rows at one level
    (units under a course, lessons under a unit, exercises/teaching
    cards under a lesson) by content_key.

    Only existing rows that HAVE a non-null content_key are eligible to
    match (pre-content_key rows are structurally unmatchable -- they
    fall through to the position-only create/skip path exactly as
    before this feature existed). Returns
    (matched: list[(existing_row, incoming_item)],
     unmatched_incoming: list[incoming_item]).
    """
    existing_by_key = {
        row.content_key: row for row in existing_rows if row.content_key
    }
    matched = []
    unmatched = []
    for item in incoming_items:
        key = item.content_key
        existing = existing_by_key.get(key) if key else None
        if existing is not None:
            matched.append((existing, item))
        else:
            unmatched.append(item)
    return matched, unmatched


def _bump_to_temp_orders(rows):
    """Phase 1 of a two-phase reorder: give every row about to be
    updated a guaranteed-unique negative order first, so phase 2 can
    set everyone's real final order (which may differ from today's --
    e.g. two exercises swapping position as part of a content fix)
    without transiently violating the (parent_id, order) unique
    constraint. Caller must db.flush() after this and again after
    phase 2."""
    for offset, row in enumerate(rows, start=1):
        row.order = -offset


def _update_exercise(row: Exercise, exercise_data) -> None:
    row.type = exercise_data.type
    row.order = exercise_data.order
    row.prompt = exercise_data.prompt
    row.correct_response = exercise_data.correct_response
    row.feedback = exercise_data.feedback
    row.xp = exercise_data.xp
    row.content_key = exercise_data.content_key


def _sync_exercises(
    db: Session,
    lesson: Lesson,
    exercises_data,
    errors: list[str],
    counters: dict[str, int],
    location: str,
) -> None:
    existing = list(
        db.scalars(select(Exercise).where(Exercise.lesson_id == lesson.id))
    )
    matched, unmatched_incoming = _match_by_content_key(
        existing, exercises_data
    )

    _bump_to_temp_orders([row for row, _ in matched])
    db.flush()
    for row, exercise_data in matched:
        _update_exercise(row, exercise_data)
    db.flush()
    counters["updated_exercises"] += len(matched)

    # Recomputed AFTER the update phase so newly-final orders (from the
    # matched rows above) correctly count as occupied.
    occupied_orders = {
        order
        for (order,) in db.execute(
            select(Exercise.order).where(Exercise.lesson_id == lesson.id)
        )
    }
    for exercise_data in unmatched_incoming:
        if exercise_data.order in occupied_orders:
            # No content_key on the incoming item means this is either
            # legacy (pre-content_key) content or a plain re-import of
            # something already present - the exact "nothing new to
            # append" no-op the original create-missing-only behavior
            # handled silently. Only surface a warning when the author
            # DID supply a content_key (so a genuine update was
            # expected) and it still collided with something unrelated
            # - that's a real, worth-reporting ambiguity.
            if exercise_data.content_key:
                errors.append(
                    f"{location}: exercise order {exercise_data.order} "
                    "conflicts with an existing, unaffected exercise; "
                    f"skipped (content_key={exercise_data.content_key!r})"
                )
            continue
        db.add(Exercise(lesson_id=lesson.id, **exercise_data.model_dump()))
        occupied_orders.add(exercise_data.order)
        counters["created_exercises"] += 1


def _teaching_item_fields(card, course_id: str, lesson_id: str, teaching_order: int) -> dict:
    return {
        "course_id": course_id,
        "lesson_id": lesson_id,
        "teaching_order": teaching_order,
        "kind": card.kind,
        "language_code": card.text_blocks[0].language_code,
        "title": card.title or "",
        "content": {
            "text_blocks": [block.model_dump() for block in card.text_blocks],
            "note": card.note,
            # 2026-07-07 vocabulary-example addition (CONTRACT.md,
            # AUTHORING_GUIDE.md #19). Only stored when present so
            # pre-existing cards' content JSON stays byte-identical.
            **(
                {
                    "examples": [
                        example.model_dump() for example in card.examples
                    ]
                }
                if card.examples
                else {}
            ),
            # Reading-track tap glosses are author-provided and live in
            # the existing JSON payload. Omit the key for every legacy card.
            **({"glosses": card.glosses} if card.glosses is not None else {}),
        },
        "content_key": card.content_key,
    }


def _sync_teaching(
    db: Session,
    lesson: Lesson,
    course_id: str,
    teaching_data,
    errors: list[str],
    counters: dict[str, int],
    location: str,
) -> None:
    # Teaching cards have no explicit `order` field (unlike
    # units/lessons/exercises) -- their position in the incoming list
    # IS the intended teaching_order, matching how they've always been
    # imported. A content_key match still lets an existing card's
    # wording/kind/title be corrected in place even if its position
    # also changed.
    existing = list(
        db.scalars(select(ContentItem).where(ContentItem.lesson_id == lesson.id))
    )
    incoming_with_position = list(enumerate(teaching_data, 1))
    existing_by_key = {
        row.content_key: row for row in existing if row.content_key
    }
    matched = []
    unmatched = []
    for position, card in incoming_with_position:
        existing_row = existing_by_key.get(card.content_key) if card.content_key else None
        if existing_row is not None:
            matched.append((existing_row, card, position))
        else:
            unmatched.append((card, position))

    for offset, (row, _card, _position) in enumerate(matched, start=1):
        row.teaching_order = -offset
    db.flush()
    for row, card, position in matched:
        for field, value in _teaching_item_fields(
            card, course_id, lesson.id, position
        ).items():
            setattr(row, field, value)
    db.flush()
    counters["updated_teaching_items"] += len(matched)

    occupied_positions = {
        order
        for (order,) in db.execute(
            select(ContentItem.teaching_order).where(
                ContentItem.lesson_id == lesson.id
            )
        )
        if order is not None
    }
    for card, position in unmatched:
        if position in occupied_positions:
            # See the matching comment in _sync_exercises: only warn
            # when a content_key was actually supplied and still
            # collided - a keyless re-import hitting an already-
            # occupied position is the ordinary no-op case.
            if card.content_key:
                errors.append(
                    f"{location}: teaching card position {position} "
                    "conflicts with an existing, unaffected teaching "
                    f"card; skipped (content_key={card.content_key!r})"
                )
            continue
        db.add(ContentItem(**_teaching_item_fields(card, course_id, lesson.id, position)))
        occupied_positions.add(position)


def _create_lesson(
    db: Session, unit: Unit, lesson_data, counters: dict[str, int] | None = None
) -> Lesson:
    lesson = Lesson(
        unit_id=unit.id,
        title=lesson_data.title,
        order=lesson_data.order,
        content_key=lesson_data.content_key,
    )
    db.add(lesson)
    db.flush()
    for teaching_order, card in enumerate(lesson_data.teaching, 1):
        db.add(
            ContentItem(
                **_teaching_item_fields(card, unit.course_id, lesson.id, teaching_order)
            )
        )
        if counters is not None:
            counters["created_teaching_items"] += 1
    for exercise_data in lesson_data.exercises:
        db.add(Exercise(lesson_id=lesson.id, **exercise_data.model_dump()))
        if counters is not None:
            counters["created_exercises"] += 1
    return lesson


def _sync_lessons(
    db: Session,
    unit: Unit,
    lessons_data,
    errors: list[str],
    counters: dict[str, int],
    location: str,
) -> None:
    existing = list(db.scalars(select(Lesson).where(Lesson.unit_id == unit.id)))
    matched, unmatched_incoming = _match_by_content_key(existing, lessons_data)

    _bump_to_temp_orders([row for row, _ in matched])
    db.flush()
    for row, lesson_data in matched:
        row.title = lesson_data.title
        row.order = lesson_data.order
        row.content_key = lesson_data.content_key
    db.flush()
    counters["updated_lessons"] += len(matched)
    for row, lesson_data in matched:
        _sync_exercises(
            db,
            row,
            lesson_data.exercises,
            errors,
            counters,
            f"{location}.{lesson_data.content_key}",
        )
        _sync_teaching(
            db,
            row,
            unit.course_id,
            lesson_data.teaching,
            errors,
            counters,
            f"{location}.{lesson_data.content_key}",
        )

    occupied_orders = {
        order
        for (order,) in db.execute(
            select(Lesson.order).where(Lesson.unit_id == unit.id)
        )
    }
    for lesson_data in unmatched_incoming:
        if lesson_data.order in occupied_orders:
            # See the matching comment in _sync_exercises.
            if lesson_data.content_key:
                errors.append(
                    f"{location}: lesson order {lesson_data.order} "
                    "conflicts with an existing, unaffected lesson; "
                    f"skipped (content_key={lesson_data.content_key!r})"
                )
            continue
        _create_lesson(db, unit, lesson_data, counters)
        occupied_orders.add(lesson_data.order)
        counters["created_lessons"] += 1


def _create_unit(
    db: Session, course: Course, unit_data, counters: dict[str, int] | None = None
) -> Unit:
    unit = Unit(
        course_id=course.id,
        title=unit_data.title,
        order=unit_data.order,
        section=unit_data.section,
        content_key=unit_data.content_key,
    )
    db.add(unit)
    db.flush()
    for lesson_data in unit_data.lessons:
        _create_lesson(db, unit, lesson_data, counters)
        if counters is not None:
            counters["created_lessons"] += 1
    return unit


def _sync_units(
    db: Session,
    course: Course,
    units_data,
    errors: list[str],
    counters: dict[str, int],
) -> None:
    """Reconcile `units_data` against `course`'s existing units.

    A unit/lesson/exercise/teaching-card whose content_key matches an
    already-shipped row is updated IN PLACE (same primary key -- every
    ExerciseAttempt/ContentIssueReport/ReviewItem/LessonProgress that
    references it is completely unaffected, since none of those
    snapshot or re-derive from the exercise's content). Anything with
    no content_key match falls back to the original position-only
    behavior: create if its `order` is free, otherwise leave the
    existing row alone and report the conflict rather than guess.
    Nothing is ever deleted, even if content_key'd content that used
    to exist is absent from `units_data` -- an author removing an
    exercise/lesson/unit doesn't destroy real user history that
    references it (and the RESTRICT foreign keys wouldn't allow it
    anyway).
    """
    existing = list(db.scalars(select(Unit).where(Unit.course_id == course.id)))
    matched, unmatched_incoming = _match_by_content_key(existing, units_data)

    _bump_to_temp_orders([row for row, _ in matched])
    db.flush()
    for row, unit_data in matched:
        row.title = unit_data.title
        row.order = unit_data.order
        row.section = unit_data.section
        row.content_key = unit_data.content_key
    db.flush()
    counters["updated_units"] += len(matched)
    for row, unit_data in matched:
        _sync_lessons(
            db,
            row,
            unit_data.lessons,
            errors,
            counters,
            f"unit {unit_data.content_key}",
        )

    occupied_orders = {
        order
        for (order,) in db.execute(
            select(Unit.order).where(Unit.course_id == course.id)
        )
    }
    for unit_data in unmatched_incoming:
        if unit_data.order in occupied_orders:
            # See the matching comment in _sync_exercises.
            if unit_data.content_key:
                errors.append(
                    f"course {course.id}: unit order {unit_data.order} "
                    "conflicts with an existing, unaffected unit; "
                    f"skipped (content_key={unit_data.content_key!r})"
                )
            continue
        _create_unit(db, course, unit_data, counters)
        occupied_orders.add(unit_data.order)
        counters["created_units"] += 1


def import_content(db: Session, data: ImportRequest):
    errors = validation_errors(db, data)
    if errors:
        return 0, errors, {}

    count = 0
    counters = {
        "created_units": 0,
        "updated_units": 0,
        "created_lessons": 0,
        "updated_lessons": 0,
        "created_exercises": 0,
        "updated_exercises": 0,
        "created_teaching_items": 0,
        "updated_teaching_items": 0,
    }
    sync_errors: list[str] = []

    for course_data in data.courses:
        existing = db.scalar(
            select(Course).where(
                Course.source_language == course_data.source_language,
                Course.target_language == course_data.target_language,
                Course.title == course_data.title,
            )
        )

        if existing:
            # Course already exists -- never delete/recreate it (that
            # would cascade-wipe real user progress). Reconcile its
            # units/lessons/exercises/teaching against course_data:
            # content_key matches update in place, brand-new content
            # (by content_key or, absent one, by a free `order`) is
            # appended, and anything ambiguous is left untouched and
            # reported rather than guessed at.
            logger.info(
                "Reconciling existing course against incoming content: "
                "id=%s source=%s target=%s title=%r",
                existing.id,
                existing.source_language,
                existing.target_language,
                existing.title,
            )
            _sync_units(db, existing, course_data.units, sync_errors, counters)
            continue

        course = Course(
            source_language=course_data.source_language,
            target_language=course_data.target_language,
            title=course_data.title,
            description=course_data.description,
            level=course_data.level,
        )
        db.add(course)
        db.flush()

        for unit_data in course_data.units:
            _create_unit(db, course, unit_data, counters)
            counters["created_units"] += 1

        for item_data in course_data.content_items:
            db.add(
                ContentItem(
                    course_id=course.id,
                    lesson_id=None,
                    teaching_order=None,
                    **item_data.model_dump(),
                )
            )

        count += 1

    db.commit()
    return count, sync_errors, counters


def _practice_lesson_id(
    db: Session,
    course_id: str,
    lesson_content_key: str,
) -> tuple[str | None, str | None]:
    """Resolve a compiled lesson key without relying on unit/lesson order.

    Phase 1 stores stable lesson keys alongside every Lexeme because the
    legacy Lesson table predates content keys. ContentKey is retained as a
    compatibility path for courses imported through the newer release model.
    """
    lexeme_lesson_ids = set(
        db.scalars(
            select(Lexeme.provenance_lesson_id).where(
                Lexeme.course_id == course_id,
                Lexeme.provenance_lesson_content_key == lesson_content_key,
            )
        )
    )
    if len(lexeme_lesson_ids) == 1:
        return lexeme_lesson_ids.pop(), None
    if len(lexeme_lesson_ids) > 1:
        return None, f"lesson key {lesson_content_key!r} maps to multiple lessons"

    content_key = db.scalar(
        select(ContentKey).where(
            ContentKey.key == lesson_content_key,
            ContentKey.entity_type == "lesson",
        )
    )
    if content_key and content_key.entity_id:
        lesson_id = db.scalar(
            select(Lesson.id)
            .join(Unit, Unit.id == Lesson.unit_id)
            .where(
                Lesson.id == content_key.entity_id,
                Unit.course_id == course_id,
            )
        )
        if lesson_id:
            return lesson_id, None

    # Real gap found 2026-07-07: neither of the above paths covers a lesson
    # that produced zero Lexeme rows (e.g. a dialogue/grammar-review lesson
    # with no `kind: vocabulary` cards for the backfill script to attach
    # provenance to) on a course imported through the actual import_content()
    # flow, which never writes to the ContentKey table at all -- that table
    # is only a "newer release model" compatibility path this project
    # doesn't use yet. Lesson.content_key itself is always populated by
    # import_content() though, so fall back to it directly before giving up.
    lesson_id = db.scalar(
        select(Lesson.id)
        .join(Unit, Unit.id == Lesson.unit_id)
        .where(
            Lesson.content_key == lesson_content_key,
            Unit.course_id == course_id,
        )
    )
    if lesson_id:
        return lesson_id, None
    return None, f"lesson key {lesson_content_key!r} was not found in the course"


def import_practice_templates(
    db: Session,
    course: Course,
    data: PracticeArtifactImport,
):
    errors = []
    if (course.source_language, course.target_language) != (
        data.source_language,
        data.target_language,
    ):
        errors.append("artifact language pair does not match the target course")

    resolved = []
    seen = set()
    for pack in data.packs:
        for template in pack.templates:
            if template.content_key in seen:
                errors.append(
                    f"duplicate template content_key {template.content_key!r}"
                )
                continue
            seen.add(template.content_key)
            lesson_id, error = _practice_lesson_id(
                db,
                course.id,
                template.lesson_content_key,
            )
            if error:
                errors.append(error)
            else:
                resolved.append((template, lesson_id))
    if errors:
        return 0, 0, list(dict.fromkeys(errors))

    created = 0
    updated = 0
    for template, lesson_id in resolved:
        row = db.scalar(
            select(PracticeTemplate).where(
                PracticeTemplate.course_id == course.id,
                PracticeTemplate.content_key == template.content_key,
            )
        )
        values = template.model_dump(
            exclude={"lesson_content_key"},
            mode="json",
        )
        if row is None:
            row = PracticeTemplate(
                course_id=course.id,
                provenance_lesson_id=lesson_id,
                active=True,
                **values,
            )
            db.add(row)
            created += 1
        else:
            row.provenance_lesson_id = lesson_id
            row.active = True
            for field, value in values.items():
                setattr(row, field, value)
            updated += 1
    db.commit()
    return created, updated, []


def export_content(db: Session):
    result = []

    courses = db.scalars(
        select(Course).order_by(
            Course.source_language,
            Course.target_language,
            Course.title,
        )
    )

    for course in courses:
        result.append(
            {
                "source_language": course.source_language,
                "target_language": course.target_language,
                "title": course.title,
                "description": course.description,
                "level": course.level.value,
                "units": [
                    {
                        "title": unit.title,
                        "order": unit.order,
                        "section": unit.section.value,
                        "lessons": [
                            {
                                "title": lesson.title,
                                "order": lesson.order,
                                "teaching": [
                                    {
                                        "kind": item.kind,
                                        "title": item.title or None,
                                        "text_blocks": item.content["text_blocks"],
                                        "note": item.content.get("note"),
                                    }
                                    for item in lesson.teaching_items
                                ],
                                "exercises": [
                                    {
                                        "type": exercise.type.value,
                                        "order": exercise.order,
                                        "prompt": exercise.prompt,
                                        "correct_response": (
                                            exercise.correct_response
                                        ),
                                        "feedback": exercise.feedback,
                                        "xp": exercise.xp,
                                    }
                                    for exercise in lesson.exercises
                                ],
                            }
                            for lesson in unit.lessons
                        ],
                    }
                    for unit in course.units
                ],
                "content_items": [
                    {
                        "kind": item.kind,
                        "language_code": item.language_code,
                        "title": item.title,
                        "content": item.content,
                    }
                    for item in db.scalars(
                        select(ContentItem).where(
                            ContentItem.course_id == course.id,
                            ContentItem.lesson_id.is_(None),
                        )
                    )
                ],
            }
        )

    return {"courses": result}
