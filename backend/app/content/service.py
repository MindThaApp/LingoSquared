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


def _import_units(db: Session, course: Course, units_data):
    """Create units (and their lessons/teaching/exercises) under `course`.

    Additive only -- callers are responsible for ensuring `units_data`
    contains no units that already exist under `course` (matched by the
    `(course_id, order)` unique constraint on `Unit`), so this never
    touches or duplicates existing content.
    """
    for unit_data in units_data:
        unit = Unit(
            course_id=course.id,
            title=unit_data.title,
            order=unit_data.order,
            section=unit_data.section,
        )
        db.add(unit)
        db.flush()

        for lesson_data in unit_data.lessons:
            lesson = Lesson(
                unit_id=unit.id,
                title=lesson_data.title,
                order=lesson_data.order,
            )
            db.add(lesson)
            db.flush()

            for teaching_order, card in enumerate(
                lesson_data.teaching,
                1,
            ):
                db.add(
                    ContentItem(
                        course_id=course.id,
                        lesson_id=lesson.id,
                        teaching_order=teaching_order,
                        kind=card.kind,
                        language_code=card.text_blocks[0].language_code,
                        title=card.title or "",
                        content={
                            "text_blocks": [
                                block.model_dump()
                                for block in card.text_blocks
                            ],
                            "note": card.note,
                        },
                    )
                )

            for exercise_data in lesson_data.exercises:
                db.add(
                    Exercise(
                        lesson_id=lesson.id,
                        **exercise_data.model_dump(),
                    )
                )


def import_content(db: Session, data: ImportRequest):
    errors = validation_errors(db, data)
    if errors:
        return 0, errors

    count = 0

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
            # would cascade-wipe real user progress). But an existing
            # course previously could never receive units authored
            # AFTER its initial import either: this branch used to
            # `continue` unconditionally, silently discarding every
            # new unit in course_data along with it. Units are unique
            # per (course_id, order), so any unit in course_data whose
            # `order` isn't already present under `existing` is new
            # content that was never imported -- append exactly those,
            # and leave every already-present unit/lesson/exercise
            # byte-for-byte untouched.
            existing_orders = {
                order
                for (order,) in db.execute(
                    select(Unit.order).where(
                        Unit.course_id == existing.id
                    )
                )
            }
            new_units = [
                unit_data
                for unit_data in course_data.units
                if unit_data.order not in existing_orders
            ]
            if not new_units:
                logger.info(
                    "Skipping existing course, no new units to append: "
                    "id=%s source=%s target=%s title=%r",
                    existing.id,
                    existing.source_language,
                    existing.target_language,
                    existing.title,
                )
                continue

            logger.info(
                "Appending %d new unit(s) to existing course: "
                "id=%s source=%s target=%s title=%r",
                len(new_units),
                existing.id,
                existing.source_language,
                existing.target_language,
                existing.title,
            )
            _import_units(db, existing, new_units)
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

        _import_units(db, course, course_data.units)

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
    return count, []


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
