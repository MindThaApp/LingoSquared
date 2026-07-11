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
# Not GOOGLE_TTS_SUPPORTED_LANGUAGES specifically: this gate exists to
# ask "can a learner actually hear this?", and since 2026-07-06 Azure
# covers Farsi (fa) where Google has zero Persian/Dari voices at all --
# using the Google-only set here was stale from the day Azure shipped,
# silently keeping fa's listen_select generation off even though fa
# now has a real, working TTS voice.
#
# Not TTS_SUPPORTED_LANGUAGES either (2026-07-07, Fable audit finding):
# that set is static language-membership, added the day a provider
# integration merges -- it says nothing about whether that provider has
# real credentials configured on THIS deploy target right now. fa was
# added to it the moment Azure code landed, while azure_speech_key still
# defaults to empty until Ramin actually provisions a key. Gating
# generation on membership alone would let listen_select items generate
# for fa with no real voice configured -- the exact unanswerable-audio
# class already hit twice this project via other mechanisms.
# tts_actually_configured() checks real credentials, not just language
# membership; Dari (prs) has zero coverage from either provider and is
# correctly still excluded either way.
from app.services.tts import tts_actually_configured


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


def _base_slot_candidates(
    template: PracticeTemplate,
    lexemes: list[Lexeme],
) -> dict[str, list[Lexeme]]:
    """The set of lexemes matching each of a template's slot constraints.

    Pure function of (template's own slot constraints, the course-wide
    lexeme pool) -- lexeme_matches() has no external state, so this
    result is identical every time it's computed for the same
    (template, lexemes) pair. Split out from fill_slots() so callers
    generating many items in one request can compute it ONCE per
    template and reuse it across every fill_slots() call for that
    template, instead of re-scanning the entire lexeme pool per slot on
    every single attempt (the real combinatorial cost behind the
    77-second /practice/{course_id}/batch found live 2026-07-07 on
    prs-en's largest course: 280 templates x 426 lexemes x repeated
    per-attempt rescans added up to tens of millions of redundant
    lexeme_matches() calls for one batch request)."""
    return {
        name: [item for item in lexemes if lexeme_matches(item, constraints)]
        for name, constraints in template.slots.items()
    }


def fill_slots(
    template: PracticeTemplate,
    lexemes: list[Lexeme],
    rng: random.Random,
    target_lexeme: Lexeme | None = None,
    slot_candidates: dict[str, list[Lexeme]] | None = None,
) -> dict[str, Lexeme] | None:
    # Smallest-domain-first backtracking makes same_tag/distinct constraints
    # reliable without embedding PostgreSQL-specific JSON predicates. When a
    # target_lexeme is given (review/practice generation for a specific due
    # lexeme), try forcing it into each slot it's eligible for before giving
    # up on this template, rather than just filling normally.
    #
    # slot_candidates lets a caller pass in an already-computed
    # _base_slot_candidates() result (see that function's docstring) to
    # skip re-scanning the whole lexeme pool on every call; a fresh copy
    # is made below before any mutation either way, so a cached/shared
    # dict passed in here is never modified.
    base_candidates = (
        slot_candidates
        if slot_candidates is not None
        else _base_slot_candidates(template, lexemes)
    )
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
    default_field: str = "token",
    emphasize: bool = False,
) -> str:
    rendering = frame.get("slot_rendering", {})

    def replacement(match: re.Match) -> str:
        name = match.group(1)
        if name == blank_slot:
            return "___"
        field = rendering.get(name, default_field)
        value = str(getattr(filled[name], field))
        # `emphasize` wraps just the substituted span in the existing
        # single-asterisk convention (docs/content/AUTHORING_GUIDE.md #15,
        # `frontend/src/components/EmphasizedText.tsx`) so a mixed-language
        # rendered frame visually distinguishes the substituted portion
        # from the surrounding frame text, instead of reading as one
        # undistinguished run-on line. Only the caller that substitutes a
        # DIFFERENT language's text into the frame (word_order's English-
        # gloss hint, below) opts in; ordinary token rendering is unaffected.
        return f"*{value}*" if emphasize else value

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
            "rtl" if course.source_language in {"ar", "fa", "prs"} else "ltr"
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
        if template.answer_derivation.get("interchangeable") and isinstance(answer, str):
            # A subtler variant of the bare-slot bug above, found live
            # 2026-07-06: some visible text survives masking (e.g. "Ben ___
            # nieuw hier?"), but the slot's own candidate pool is a closed
            # set of true register/stress synonyms for the SAME referent
            # (je/jij, alsjeblieft/alstublieft, mijn/je/jouw as "whose
            # brother?") with nothing else in the frame able to prefer one
            # over another — any pool member is equally correct Dutch, yet
            # grading only accepted the one the sampler happened to fill.
            # `interchangeable: true` is an explicit, opt-in content flag
            # (only set on templates a reviewer has confirmed are a true
            # synonym pool, NOT on ordinary open-vocabulary slots like
            # country/person_name/greeting, where only one value is
            # correct and the rest are real distractors) — when set,
            # accept every candidate that still satisfies this slot's own
            # constraints, using the existing generic multi-answer grading
            # shape ({"canonical", "accepted"}) `grade()` already handles
            # for hand-authored content.
            constraints = template.slots[slot]
            pool = sorted({
                lexeme.token
                for lexeme in lexemes
                if lexeme_matches(lexeme, constraints)
            })
            if len(pool) > 1:
                answer = {"canonical": answer, "accepted": pool}
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
        if not tts_actually_configured(course.target_language):
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
        # Found live 2026-07-05: this branch never showed the learner
        # anything about what phrase to build — only the generic
        # instruction plus a shuffled word bank, with zero context. A
        # compiled lesson's hand-authored word_order card bakes the
        # target phrase directly into its instruction text (e.g.
        # "Arrange the letters to build سلام."); this generated version
        # has no equivalent, making it an unguessable puzzle for any
        # slotted phrase the learner hasn't already memorized verbatim.
        # Fix: render the same frame with each slot's `english_gloss`
        # substituted for its `token` as a hint line. For a fully fixed
        # frame (no `{slot}` placeholders at all, e.g. the letter-ramp
        # spelling drills above) this harmlessly reproduces the exact
        # same "reveal the phrase, test assembling/spelling it" pattern
        # the compiled content already uses deliberately; for a genuine
        # slotted frame it gives a real (if ungrammatical) word-by-word
        # English cue without literally handing over the correct token
        # order.
        #
        # Second fix, found live 2026-07-06 (real user report): the
        # substituted English gloss(es) were spliced into the Dutch/target
        # frame with no visual distinction at all -- e.g. frame "Ben {item}
        # nieuw hier?" with item's gloss "you; your (informal)" rendered as
        # the single undistinguished run-on line "Ben you; your (informal)
        # nieuw hier?", unreadable at a glance. `emphasize=True` wraps just
        # the substituted gloss span(s) in the existing single-asterisk
        # convention (AUTHORING_GUIDE.md #15) so the frontend renders them
        # italic+bold, visually separated from the surrounding target-
        # language words, the same fix Ramin asked for directly.
        hint = render_frame(
            template.frame,
            filled,
            default_field="english_gloss",
            emphasize=True,
        )
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
                _instruction_block(course, "Put the words in the correct order."),
                _block(template.frame, hint),
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


def _prompt_signature(prompt: dict[str, Any]) -> tuple:
    # A slot's actual value can be masked out of the rendered prompt
    # entirely (fill_in_blank's "___", word_order's gloss-substituted hint
    # line) -- two DIFFERENT underlying slot fillings can then render an
    # IDENTICAL prompt, which _signature() above can't catch since it's
    # keyed on the abstract (template, slot values) pair, not on what the
    # learner actually sees. Found live 2026-07-06 (real user report: "all
    # the questions are the same") -- a fresh Endless Practice batch for a
    # single-lesson-old nl account returned 7 of 10 items as the byte-
    # identical "Fill in the missing word. / Ben ___ nieuw hier?" prompt
    # (je/jij each masked away identically), because the only anti-repeat
    # check compared the hidden slot values, which legitimately differed
    # every time. This signature instead hashes what's actually rendered
    # (visible text blocks, options, word bank, audio cue) so two prompts
    # that LOOK the same to the learner are always treated as a repeat,
    # regardless of what's hidden underneath.
    texts = tuple(block.get("text", "") for block in prompt.get("text_blocks") or ())
    options = tuple(sorted(prompt.get("options") or ()))
    word_bank = tuple(sorted(prompt.get("word_bank") or ()))
    audio = prompt.get("audio_text", "")
    return ("visible", texts, options, word_bank, audio)


def _tier_order(
    mastery: float,
    tier_rotation: int = 0,
) -> tuple[tuple[str, ...], ...]:
    if mastery < 0.3:
        # Fresh/low-mastery Endless Practice items still need recognition,
        # but broad MC templates can build for nearly every lexeme. Rotate
        # the first-choice tier by final batch position so recognition,
        # structured, and production formats all get first chance without
        # changing the mastery ladder for stronger lexemes.
        tiers = (RECOGNITION_TYPES, STRUCTURED_TYPES, PRODUCTION_TYPES)
        rotation = tier_rotation % len(tiers)
        return tiers[rotation:] + tiers[:rotation]
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


def _course_lesson_ids(db: Session, course_id: str) -> list[str]:
    return list(
        db.scalars(
            select(Lesson.id)
            .join(Unit, Unit.id == Lesson.unit_id)
            .where(Unit.course_id == course_id)
            .order_by(Unit.order, Lesson.order, Lesson.id)
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
    if not tts_actually_configured(course.target_language):
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
    signatures: set[tuple] = set()
    for item in recent:
        signatures.add(_signature(item.template_id, item.filled_slots))
        signatures.add(_prompt_signature(item.prompt))
    return signatures


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
    slot_candidate_cache: dict[str, dict[str, list]] | None = None,
    tier_rotation: int = 0,
) -> PracticeItem | None:
    for tier in _tier_order(mastery, tier_rotation):
        candidates = [
            template for template in templates if template.type in tier
        ]
        rng.shuffle(candidates)

        for template in candidates:
            slot_candidates = None
            if slot_candidate_cache is not None:
                slot_candidates = slot_candidate_cache.get(template.id)
                if slot_candidates is None:
                    slot_candidates = _base_slot_candidates(template, lexemes)
                    slot_candidate_cache[template.id] = slot_candidates

            # Multiple attempts permit different valid OTHER-slot fillings.
            for _ in range(max(2, len(template.slots) * 2)):
                filled = fill_slots(
                    template,
                    lexemes,
                    rng,
                    target_lexeme=target,
                    slot_candidates=slot_candidates,
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
                visible = _prompt_signature(prompt)
                if (
                    visible in signatures
                    and not allow_existing_signature
                ):
                    continue

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
                signatures.add(visible)
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
    # Per-template slot-candidate memoization, scoped to this one
    # generation call (a fresh course-wide lexeme pool/template set each
    # time _generate_prioritized() is invoked, so nothing here is stale
    # across requests) -- see _base_slot_candidates()'s docstring for
    # why this is safe and what it fixes.
    slot_candidate_cache: dict[str, dict[str, list]] = {}

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
            slot_candidate_cache=slot_candidate_cache,
            tier_rotation=len(generated) if source == "practice" else 0,
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
                slot_candidate_cache=slot_candidate_cache,
                tier_rotation=len(generated) if source == "practice" else 0,
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
        # Checkpoints no longer flow through this function at all (see
        # generate_checkpoint(), 2026-07-10) -- only practice and review
        # reach here, and both are deliberately mastery-adaptive.
        mastery = row.mastery if row is not None else 0.0
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
            # Scoped to source == "practice" only. Found live 2026-07-06
            # (real user report: "all the questions are the same") -- this
            # padding loop used to flip allow_existing_signature=True for
            # EVERY source once attempts passed a fixed threshold, so once
            # a thin course's real variety ran out it mechanically filled
            # the rest of the batch with repeats/near-repeats rather than
            # just returning fewer items. For ad-hoc Endless Practice
            # (source == "practice", the actual reported page), a course
            # with only one lesson's worth of material genuinely doesn't
            # have `size` distinct items to give yet -- returning fewer
            # honest items is correct; padding with visible duplicates is
            # not. Review keeps the old threshold-based escape hatch: a
            # review session is a fixed due-item batch, not an open-ended
            # feed. (Checkpoints used to take the same escape hatch here
            # for the same reason -- a fixed-size scored assessment must
            # reach its 12-15 item minimum even on a rate-limited retake
            # reusing the same unit's material, confirmed live by
            # test_checkpoint_retake_delay_and_expiry -- but since
            # 2026-07-10 checkpoint generation has its own stratified,
            # fixed-difficulty loop in generate_checkpoint() carrying an
            # equivalent escape hatch, and never reaches this function.)
            allow_existing_signature=(
                False if source == "practice" else attempts > len(fallback) * 2
            ),
            slot_candidate_cache=slot_candidate_cache,
            tier_rotation=len(generated) if source == "practice" else 0,
        )
        if item is not None:
            generated.append(item)

    return generated


def generate_batch(
    db: Session,
    user_id: str,
    course: Course,
    size: int,
    is_admin: bool = False,
) -> tuple[bool, list[PracticeItem]]:
    completed = _completed_lesson_ids(db, user_id, course.id)
    if not completed:
        if not is_admin:
            return True, []
        completed = _course_lesson_ids(db, course.id)

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
    # A checkpoint is a criterion-referenced test of the WHOLE unit
    # against a fixed 80% pass bar, not an adaptive practice session.
    # This used to delegate to _generate_prioritized() with
    # source="checkpoint", which a 2026-07-10 pedagogy review found
    # miscalibrated the assessment in two ways, both fixed here
    # (regular practice/review keep their mastery-adaptive behavior in
    # _generate_prioritized() -- this is checkpoint-only):
    #
    # 1. Item selection was biased toward the learner's due/weakest
    #    lexemes (SRS-priority order) rather than representative of the
    #    unit -- two learners, or two attempts, could face materially
    #    different samples with whole lessons unrepresented. Now targets
    #    are stratified across the unit's lessons: round-robin over
    #    per-lesson lexeme buckets (shuffled within each bucket), so the
    #    12-15 items spread as evenly across every lesson as the
    #    material allows.
    # 2. Exercise-format difficulty tracked live per-lexeme mastery via
    #    _tier_order(), so a learner with tracked-weak lexemes got
    #    recognition-heavy (easier) formats against the same pass bar --
    #    the weakest learners got the easiest test, inverting assessment
    #    discrimination. Only untracked lexemes (the pure test-out case)
    #    already got the fixed CHECKPOINT_MASTERY_BANDS cycling. Now
    #    EVERY item cycles those bands (0.0/0.5/0.8 -> a consistent
    #    recognition/structured/production mix) regardless of the
    #    learner's SRS state, which this function no longer reads at all.
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

    rng = _batch_rng(
        db,
        user_id,
        course.id,
        f"checkpoint-unit:{unit_id}",
    )

    by_lesson: dict[str, list[Lexeme]] = {}
    for lexeme in lexemes:
        by_lesson.setdefault(lexeme.provenance_lesson_id, []).append(lexeme)
    # _material() orders lexemes by id, so bucket contents are
    # deterministic before the seeded shuffle.
    buckets = [
        by_lesson[lesson_id]
        for lesson_id in lesson_ids
        if lesson_id in by_lesson
    ]
    for bucket in buckets:
        rng.shuffle(bucket)
    # Round-robin across lesson buckets: every lesson with material is
    # represented within the first len(buckets) targets and again each
    # round after, so the sample can never cluster on 1-2 lessons'
    # vocabulary the way SRS-priority ordering could.
    targets: list[Lexeme] = []
    for round_index in range(max(len(bucket) for bucket in buckets)):
        for bucket in buckets:
            if round_index < len(bucket):
                targets.append(bucket[round_index])

    signatures = _recent_signatures(db, user_id, course.id)
    slot_candidate_cache: dict[str, dict[str, list]] = {}
    generated: list[PracticeItem] = []
    attempts = 0
    max_attempts = max(size * 50, len(targets) * 10)
    while len(generated) < size and attempts < max_attempts:
        target = targets[attempts % len(targets)]
        attempts += 1
        # Band indexed by items GENERATED (not attempts), so a failed
        # attempt -- e.g. a target no template can host -- never skips a
        # band: the final 12-15 items always carry the full fixed
        # difficulty mix.
        mastery = CHECKPOINT_MASTERY_BANDS[
            len(generated) % len(CHECKPOINT_MASTERY_BANDS)
        ]
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
            source="checkpoint",
            session_id=session_id,
            # Same threshold-based escape hatch checkpoints had in
            # _generate_prioritized()'s padding loop: a checkpoint is a
            # fixed-size scored assessment that must reach its 12-item
            # minimum even on a retake reusing the same unit's material
            # (the recent-signature window still holds the previous
            # attempt's items -- confirmed live by
            # test_checkpoint_retake_delay_and_expiry). Returning fewer
            # honest items is correct for open-ended practice, not here.
            allow_existing_signature=attempts > len(targets) * 2,
            slot_candidate_cache=slot_candidate_cache,
        )
        if item is not None:
            generated.append(item)
    return generated


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
