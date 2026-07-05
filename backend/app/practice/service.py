import hashlib
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import (
    Course,
    Lesson,
    LessonProgress,
    Lexeme,
    PracticeItem,
    PracticeTemplate,
    Unit,
    UserLexemeSRS,
)
from app.services.tts import GOOGLE_TTS_SUPPORTED_LANGUAGES


PRACTICE_XP = 5
RECENT_ITEM_LIMIT = 50
SLOT_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")
RECOGNITION_TYPES = ("multiple_choice", "listen_select")
STRUCTURED_TYPES = ("word_order", "matching_pairs", "fill_in_blank")
PRODUCTION_TYPES = ("translation",)
CHECKPOINT_MASTERY_BANDS = (0.0, 0.5, 0.8)


def _as_values(value: Any) -> set[Any]:
    if isinstance(value, list):
        return set(value)
    return {value}


def _requested_matches(requested: Any, actual: Any) -> bool:
    """Compiler contract: requested lists are OR; Lexeme lists are membership."""
    return bool(_as_values(requested) & _as_values(actual))


def lexeme_matches(lexeme: Lexeme, constraints: dict[str, Any]) -> bool:
    if lexeme.language_code != constraints.get("language_code"):
        return False
    if not _requested_matches(
        constraints.get("part_of_speech"),
        lexeme.part_of_speech,
    ):
        return False
    actual_tags = lexeme.agreement_tags or {}
    return all(
        tag in actual_tags and _requested_matches(requested, actual_tags[tag])
        for tag, requested in constraints.get("agreement_tags", {}).items()
    )


def _relation_holds(
    relation: dict[str, Any],
    filled: dict[str, Lexeme],
) -> bool:
    assigned = [filled[name] for name in relation.get("slots", []) if name in filled]
    if len(assigned) < 2:
        return True
    if relation.get("kind") == "distinct":
        return len({lexeme.id for lexeme in assigned}) == len(assigned)
    if relation.get("kind") == "same_tag":
        tag = relation.get("tag")
        if any(tag not in (lexeme.agreement_tags or {}) for lexeme in assigned):
            return False
        shared = _as_values((assigned[0].agreement_tags or {}).get(tag))
        for lexeme in assigned[1:]:
            shared &= _as_values((lexeme.agreement_tags or {}).get(tag))
        return bool(shared)
    return False


def fill_slots(
    template: PracticeTemplate,
    lexemes: list[Lexeme],
    rng: random.Random,
    target_lexeme: Lexeme | None = None,
) -> dict[str, Lexeme] | None:
    # Smallest-domain-first backtracking makes same_tag/distinct constraints
    # reliable without embedding PostgreSQL-specific JSON predicates. When a
    # target_lexeme is given (review/practice generation for a specific due
    # lexeme), try forcing it into each slot it's eligible for before giving
    # up on this template, rather than just filling normally.
    base_candidates = {
        name: [item for item in lexemes if lexeme_matches(item, constraints)]
        for name, constraints in template.slots.items()
    }
    if any(not values for values in base_candidates.values()):
        return None

    target_slots: list[str | None]
    if target_lexeme is None:
        target_slots = [None]
    else:
        target_slots = [
            name
            for name, constraints in template.slots.items()
            if lexeme_matches(target_lexeme, constraints)
        ]
        if not target_slots:
            return None
        rng.shuffle(target_slots)

    for forced_slot in target_slots:
        candidates = {
            name: list(values) for name, values in base_candidates.items()
        }
        if forced_slot is not None:
            candidates[forced_slot] = [target_lexeme]

        names = sorted(
            candidates,
            key=lambda name: (len(candidates[name]), name),
        )
        for values in candidates.values():
            values.sort(key=lambda item: item.id)
            rng.shuffle(values)

        filled: dict[str, Lexeme] = {}

        def assign(index: int) -> bool:
            if index == len(names):
                return True
            name = names[index]
            for lexeme in candidates[name]:
                filled[name] = lexeme
                if all(
                    _relation_holds(relation, filled)
                    for relation in (template.slot_relations or [])
                ) and assign(index + 1):
                    return True
            filled.pop(name, None)
            return False

        if assign(0):
            return dict(filled)

    return None


def render_frame(
    frame: dict[str, Any],
    filled: dict[str, Lexeme],
    blank_slot: str | None = None,
) -> str:
    rendering = frame.get("slot_rendering", {})

    def replacement(match: re.Match) -> str:
        name = match.group(1)
        if name == blank_slot:
            return "___"
        field = rendering.get(name, "token")
        return str(getattr(filled[name], field))

    return SLOT_RE.sub(replacement, frame["text"])


def derive_answer(
    derivation: dict[str, Any],
    filled: dict[str, Lexeme],
) -> Any:
    kind = derivation["kind"]
    if kind == "slot_text":
        return filled[derivation["slot"]].token
    if kind == "slot_gloss":
        return filled[derivation["slot"]].english_gloss
    if kind == "render_frame":
        return render_frame(derivation["frame"], filled)
    if kind == "ordered_slot_texts":
        return [filled[name].token for name in derivation["slots"]]
    if kind == "matching_pairs":
        return {
            filled[name].token: filled[name].english_gloss
            for name in derivation["slots"]
        }
    raise ValueError(f"unsupported answer derivation {kind!r}")


def _block(frame: dict[str, Any], text_value: str) -> dict[str, str]:
    return {
        "text": text_value,
        "language_code": frame["language_code"],
        "direction": frame["direction"],
    }


def _instruction_block(course: Course, text_value: str) -> dict[str, str]:
    return {
        "text": text_value,
        "language_code": course.source_language,
        "direction": (
            "rtl" if course.source_language in {"fa", "prs"} else "ltr"
        ),
    }


def _answer_language(
    template: PracticeTemplate,
    course: Course | None,
) -> str:
    derivation = template.answer_derivation
    kind = derivation["kind"]
    if kind in {"slot_text", "slot_gloss"}:
        slot = template.slots[derivation["slot"]]
        return "en" if kind == "slot_gloss" else slot["language_code"]
    if kind == "render_frame":
        return derivation["frame"]["language_code"]
    if kind in {"ordered_slot_texts", "matching_pairs"}:
        return template.slots[derivation["slots"][0]]["language_code"]
    if course is None:
        raise ValueError(f"cannot infer answer language for {kind!r}")
    return course.target_language


def _distractor_values(
    template: PracticeTemplate,
    answer: str,
    lexemes: list[Lexeme],
    rng: random.Random,
) -> list[str]:
    derivation = template.answer_derivation
    if derivation["kind"] == "slot_gloss":
        constraints = template.slots[derivation["slot"]]
        values = [
            lexeme.english_gloss
            for lexeme in lexemes
            if lexeme_matches(lexeme, constraints)
        ]
    elif derivation["kind"] == "slot_text":
        constraints = template.slots[derivation["slot"]]
        values = [
            lexeme.token for lexeme in lexemes if lexeme_matches(lexeme, constraints)
        ]
    else:
        answer_language = _answer_language(template, None)
        values = []
        for constraints in template.slots.values():
            matching = [
                lexeme
                for lexeme in lexemes
                if lexeme_matches(lexeme, constraints)
            ]
            if answer_language == "en":
                values.extend(lexeme.english_gloss for lexeme in matching)
            elif answer_language == constraints.get("language_code"):
                values.extend(lexeme.token for lexeme in matching)
        # There is deliberately no language-only fallback. If no declared
        # slot can supply same-category values in the answer language, the
        # caller's minimum-option check rejects this generated instance.
    values = sorted({str(value) for value in values if str(value) != answer})
    rng.shuffle(values)
    return values[:3]


def build_prompt(
    template: PracticeTemplate,
    course: Course,
    filled: dict[str, Lexeme],
    lexemes: list[Lexeme],
    rng: random.Random,
) -> tuple[dict[str, Any], Any] | None:
    answer = derive_answer(template.answer_derivation, filled)
    rendered = render_frame(template.frame, filled)
    answer_language = _answer_language(template, course)

    if template.type == "fill_in_blank":
        slot = template.answer_derivation["slot"]
        blanked = render_frame(template.frame, filled, slot)
        if not blanked.replace("___", "").strip():
            # The frame's entire visible text is the one slot being blanked
            # out (e.g. frame.text == "{letter}") — masking it leaves zero
            # context, an unanswerable prompt with nothing to read. Found
            # live 2026-07-05 (a fresh Endless Practice fa item rendered as
            # just a blank underscore with no other text), reproducible
            # across multiple launch-pair packs, not fa-specific. Reject
            # this template instance so the caller falls back to another
            # template rather than generating a blank item.
            return None
        prompt = {
            "text_blocks": [
                _instruction_block(course, "Fill in the missing word."),
                _block(template.frame, blanked)
            ],
            "answer_language_code": answer_language,
        }
    elif template.type == "translation":
        prompt = {
            "text_blocks": [
                _instruction_block(course, "Translate this."),
                _block(template.frame, rendered),
            ],
            "answer_language_code": answer_language,
        }
    elif template.type == "multiple_choice":
        if not isinstance(answer, str):
            return None
        options = [answer, *_distractor_values(template, answer, lexemes, rng)]
        options = list(dict.fromkeys(options))
        if len(options) < 3:
            return None
        rng.shuffle(options)
        prompt = {
            "text_blocks": [_block(template.frame, rendered)],
            "options": options,
        }
    elif template.type == "listen_select":
        if course.target_language not in GOOGLE_TTS_SUPPORTED_LANGUAGES:
            return None
        if not isinstance(answer, str):
            return None
        options = [answer, *_distractor_values(template, answer, lexemes, rng)]
        options = list(dict.fromkeys(options))
        if len(options) < 3:
            return None
        rng.shuffle(options)
        prompt = {
            "text_blocks": [
                _instruction_block(course, "Tap to listen")
            ],
            "options": options,
            "audio_text": rendered,
            "audio_language_code": course.target_language,
        }
    elif template.type == "word_order":
        if isinstance(answer, list):
            ordered = answer
        else:
            ordered = str(answer).split()
            frame_tokens = rendered.split()
            # Script-ramp templates may display separated letters in `frame`
            # while render_frame derives the joined word (س ل ا م -> سلام).
            # WordOrder submits an array, so retain those reviewed bank units
            # when their concatenation is exactly the derived answer.
            if (
                len(ordered) == 1
                and len(frame_tokens) > 1
                and "".join(frame_tokens) == str(answer)
            ):
                ordered = frame_tokens
        answer = ordered
        word_bank = list(ordered)
        rng.shuffle(word_bank)
        if len(word_bank) > 1 and word_bank == ordered:
            word_bank = word_bank[1:] + word_bank[:1]
        prompt = {
            "text_blocks": [
                _instruction_block(course, "Put the words in the correct order.")
            ],
            "word_bank": word_bank,
            "answer_language_code": answer_language,
        }
    elif template.type == "matching_pairs":
        if not isinstance(answer, dict) or len(answer) != len(
            template.answer_derivation["slots"]
        ):
            return None
        prompt = {
            "text_blocks": [_block(template.frame, rendered)],
            "pairs": [
                {"left": left, "right": right}
                for left, right in answer.items()
            ],
            "answer_language_code": answer_language,
        }
    else:
        return None
    return prompt, answer


def _signature(template_id: str, slots: dict[str, str]) -> tuple:
    return template_id, tuple(sorted(slots.items()))


def _tier_order(mastery: float) -> tuple[tuple[str, ...], ...]:
    if mastery < 0.3:
        return RECOGNITION_TYPES, STRUCTURED_TYPES, PRODUCTION_TYPES
    if mastery <= 0.7:
        return STRUCTURED_TYPES, RECOGNITION_TYPES, PRODUCTION_TYPES
    return PRODUCTION_TYPES, STRUCTURED_TYPES, RECOGNITION_TYPES


def _completed_lesson_ids(
    db: Session,
    user_id: str,
    course_id: str,
) -> list[str]:
    return list(
        db.scalars(
            select(LessonProgress.lesson_id)
            .join(Lesson, Lesson.id == LessonProgress.lesson_id)
            .join(Unit, Unit.id == Lesson.unit_id)
            .where(
                LessonProgress.user_id == user_id,
                LessonProgress.completed_at.is_not(None),
                Unit.course_id == course_id,
            )
        )
    )


def _material(
    db: Session,
    course: Course,
    completed_lesson_ids: list[str],
) -> tuple[list[PracticeTemplate], list[Lexeme]]:
    templates = list(
        db.scalars(
            select(PracticeTemplate)
            .where(
                PracticeTemplate.course_id == course.id,
                PracticeTemplate.provenance_lesson_id.in_(
                    completed_lesson_ids
                ),
                PracticeTemplate.active.is_(True),
            )
            .order_by(PracticeTemplate.content_key)
        )
    )
    if course.target_language not in GOOGLE_TTS_SUPPORTED_LANGUAGES:
        templates = [
            template
            for template in templates
            if template.type != "listen_select"
        ]

    lexemes = list(
        db.scalars(
            select(Lexeme)
            .where(
                Lexeme.course_id == course.id,
                Lexeme.provenance_lesson_id.in_(completed_lesson_ids),
            )
            .order_by(Lexeme.id)
        )
    )
    return templates, lexemes


def _batch_rng(
    db: Session,
    user_id: str,
    course_id: str,
    namespace: str,
) -> random.Random:
    lock_key = f"{namespace}:{user_id}:{course_id}"
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": lock_key},
    )
    counter = db.scalar(
        select(func.count(PracticeItem.id)).where(
            PracticeItem.user_id == user_id,
            PracticeItem.course_id == course_id,
        )
    ) or 0
    material = f"{namespace}:{user_id}:{course_id}:{counter}".encode()
    seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return random.Random(seed)


def _recent_signatures(
    db: Session,
    user_id: str,
    course_id: str,
) -> set[tuple]:
    recent = list(
        db.scalars(
            select(PracticeItem)
            .where(
                PracticeItem.user_id == user_id,
                PracticeItem.course_id == course_id,
            )
            .order_by(
                PracticeItem.created_at.desc(),
                PracticeItem.id.desc(),
            )
            .limit(RECENT_ITEM_LIMIT)
        )
    )
    return {
        _signature(item.template_id, item.filled_slots)
        for item in recent
    }


def _generate_target_item(
    db: Session,
    *,
    user_id: str,
    course: Course,
    target: Lexeme,
    mastery: float,
    templates: list[PracticeTemplate],
    lexemes: list[Lexeme],
    rng: random.Random,
    signatures: set[tuple],
    source: str,
    session_id: str | None,
    allow_existing_signature: bool = False,
) -> PracticeItem | None:
    for tier in _tier_order(mastery):
        candidates = [
            template for template in templates if template.type in tier
        ]
        rng.shuffle(candidates)

        for template in candidates:
            # Multiple attempts permit different valid OTHER-slot fillings.
            for _ in range(max(2, len(template.slots) * 2)):
                filled = fill_slots(
                    template,
                    lexemes,
                    rng,
                    target_lexeme=target,
                )
                if filled is None:
                    break

                stored_slots = {
                    name: lexeme.token for name, lexeme in filled.items()
                }
                signature = _signature(template.id, stored_slots)
                if (
                    signature in signatures
                    and not allow_existing_signature
                ):
                    continue

                built = build_prompt(
                    template,
                    course,
                    filled,
                    lexemes,
                    rng,
                )
                if built is None:
                    continue

                prompt, correct_response = built
                item = PracticeItem(
                    user_id=user_id,
                    course_id=course.id,
                    template_id=template.id,
                    filled_slots=stored_slots,
                    prompt=prompt,
                    correct_response=correct_response,
                    xp_value=PRACTICE_XP,
                    source=source,
                    session_id=session_id,
                    target_lexeme_id=target.id,
                    expires_at=(
                        datetime.now(timezone.utc) + timedelta(hours=24)
                    ),
                )
                db.add(item)
                db.flush()
                signatures.add(signature)
                return item

    return None


def _generate_prioritized(
    db: Session,
    *,
    user_id: str,
    course: Course,
    size: int,
    templates: list[PracticeTemplate],
    lexemes: list[Lexeme],
    srs_rows: list[UserLexemeSRS],
    source: str,
    session_id: str | None,
    rng: random.Random,
) -> list[PracticeItem]:
    now = datetime.now(timezone.utc)
    lexeme_by_id = {lexeme.id: lexeme for lexeme in lexemes}
    eligible_rows = [
        row for row in srs_rows if row.lexeme_id in lexeme_by_id
    ]
    due_rows = sorted(
        (row for row in eligible_rows if row.due_at <= now),
        key=lambda row: (row.due_at, row.mastery, row.lexeme_id),
    )
    non_due_rows = sorted(
        (row for row in eligible_rows if row.due_at > now),
        key=lambda row: (row.mastery, row.due_at, row.lexeme_id),
    )
    srs_by_lexeme = {row.lexeme_id: row for row in eligible_rows}

    signatures = _recent_signatures(db, user_id, course.id)
    generated: list[PracticeItem] = []

    # One item per scheduled lexeme before any reinforcement repetition.
    for row in [*due_rows, *non_due_rows]:
        if len(generated) >= size:
            break
        target = lexeme_by_id[row.lexeme_id]
        item = _generate_target_item(
            db,
            user_id=user_id,
            course=course,
            target=target,
            mastery=row.mastery,
            templates=templates,
            lexemes=lexemes,
            rng=rng,
            signatures=signatures,
            source=source,
            session_id=session_id,
        )
        if item is None:
            # A due lexeme must not disappear solely because its last surface
            # form is in the recency window.
            item = _generate_target_item(
                db,
                user_id=user_id,
                course=course,
                target=target,
                mastery=row.mastery,
                templates=templates,
                lexemes=lexemes,
                rng=rng,
                signatures=signatures,
                source=source,
                session_id=session_id,
                allow_existing_signature=True,
            )
        if item is not None:
            generated.append(item)

    fallback = (
        [lexeme_by_id[row.lexeme_id] for row in eligible_rows]
        if source == "review"
        else list(lexemes)
    )
    rng.shuffle(fallback)

    attempts = 0
    max_attempts = max(size * 50, len(fallback) * 10)
    while (
        fallback
        and len(generated) < size
        and attempts < max_attempts
    ):
        target = fallback[attempts % len(fallback)]
        attempts += 1
        row = srs_by_lexeme.get(target.id)
        if row is not None:
            mastery = row.mastery
        elif source == "checkpoint":
            mastery = CHECKPOINT_MASTERY_BANDS[
                (attempts - 1) % len(CHECKPOINT_MASTERY_BANDS)
            ]
        else:
            mastery = 0.0
        item = _generate_target_item(
            db,
            user_id=user_id,
            course=course,
            target=target,
            mastery=mastery,
            templates=templates,
            lexemes=lexemes,
            rng=rng,
            signatures=signatures,
            source=source,
            session_id=session_id,
            allow_existing_signature=attempts > len(fallback) * 2,
        )
        if item is not None:
            generated.append(item)

    return generated


def generate_batch(
    db: Session,
    user_id: str,
    course: Course,
    size: int,
) -> tuple[bool, list[PracticeItem]]:
    completed = _completed_lesson_ids(db, user_id, course.id)
    if not completed:
        return True, []

    templates, lexemes = _material(db, course, completed)
    if not templates or not lexemes:
        return False, []

    srs_rows = list(
        db.scalars(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == user_id,
                UserLexemeSRS.course_id == course.id,
                UserLexemeSRS.suspended.is_(False),
            )
        )
    )
    rng = _batch_rng(db, user_id, course.id, "practice-batch")
    return False, _generate_prioritized(
        db,
        user_id=user_id,
        course=course,
        size=size,
        templates=templates,
        lexemes=lexemes,
        srs_rows=srs_rows,
        source="practice",
        session_id=None,
        rng=rng,
    )


def generate_checkpoint(
    db: Session,
    user_id: str,
    course: Course,
    unit_id: str,
    size: int = 15,
    session_id: str | None = None,
) -> list[PracticeItem]:
    size = max(12, min(15, size))
    lesson_ids = list(
        db.scalars(
            select(Lesson.id)
            .where(Lesson.unit_id == unit_id)
            .order_by(Lesson.order, Lesson.id)
        )
    )
    if not lesson_ids:
        return []

    templates, lexemes = _material(db, course, lesson_ids)
    if not templates or not lexemes:
        return []

    srs_rows = list(
        db.scalars(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == user_id,
                UserLexemeSRS.course_id == course.id,
                UserLexemeSRS.suspended.is_(False),
            )
        )
    )
    rng = _batch_rng(
        db,
        user_id,
        course.id,
        f"checkpoint-unit:{unit_id}",
    )
    return _generate_prioritized(
        db,
        user_id=user_id,
        course=course,
        size=size,
        templates=templates,
        lexemes=lexemes,
        srs_rows=srs_rows,
        source="checkpoint",
        session_id=session_id,
        rng=rng,
    )


def generate_review_batch(
    db: Session,
    user_id: str,
    course: Course,
    size: int,
    session_id: str,
) -> list[PracticeItem]:
    completed = _completed_lesson_ids(db, user_id, course.id)
    if not completed:
        return []

    templates, lexemes = _material(db, course, completed)
    srs_rows = list(
        db.scalars(
            select(UserLexemeSRS).where(
                UserLexemeSRS.user_id == user_id,
                UserLexemeSRS.course_id == course.id,
                UserLexemeSRS.suspended.is_(False),
            )
        )
    )
    if not templates or not lexemes or not srs_rows:
        return []

    rng = _batch_rng(db, user_id, course.id, "review-session")
    return _generate_prioritized(
        db,
        user_id=user_id,
        course=course,
        size=size,
        templates=templates,
        lexemes=lexemes,
        srs_rows=srs_rows,
        source="review",
        session_id=session_id,
        rng=rng,
    )


def generate_review_retry(
    db: Session,
    user_id: str,
    course: Course,
    srs: UserLexemeSRS,
    session_id: str,
) -> PracticeItem | None:
    completed = _completed_lesson_ids(db, user_id, course.id)
    templates, lexemes = _material(db, course, completed)
    target = next(
        (lexeme for lexeme in lexemes if lexeme.id == srs.lexeme_id),
        None,
    )
    if target is None:
        return None

    rng = _batch_rng(db, user_id, course.id, "review-retry")
    return _generate_target_item(
        db,
        user_id=user_id,
        course=course,
        target=target,
        mastery=srs.mastery,
        templates=templates,
        lexemes=lexemes,
        rng=rng,
        signatures=set(),
        source="review",
        session_id=session_id,
        allow_existing_signature=True,
    )
