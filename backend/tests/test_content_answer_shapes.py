"""Corpus-wide answer-shape regression test.

For EVERY exercise in the real on-disk content corpus (every course listed
in scripts/manifest.d/content/*.txt, compiled through the real
scripts/compile_content.py), construct the CORRECT answer in the exact
payload shape the real frontend component for that exercise type submits
(see frontend/src/components/exercises/*.tsx), push it through the real
grade() function (app/review/grading.py), and assert the result is
"correct".

Why this exists: this project has repeatedly shipped exercises that were
ungradeable-correct regardless of learner input because the frontend's
submitted payload shape and the authored accepted_answers shape silently
disagreed — matching_pairs (flat dict vs [{left,right}] array, found live
2026-07-05) and word_order/listen_order (token list vs space-joined string,
~84% of the corpus, found live 2026-07-07) are both documented in CLAUDE.md's
footguns. Nothing in the type system connects the compiler's output shape,
the grader's expectations, and each component's submission shape — only
actually grading a correct answer for every real exercise catches the next
instance of this bug class before a learner does.

Frontend payload shapes this test mirrors (source of truth: the components,
re-verified 2026-07-10 against app/review/grading.py, which the exercise-
level grading logic moved into verbatim from app/api/router.py the same
day):
- MultipleChoice.tsx (multiple_choice / listen_select / dialogue_comprehension),
  ReadingComprehension.tsx, GrammarCheck.tsx-with-options: submits ONE option
  string verbatim from prompt.options — so the correct answer must actually
  BE one of the rendered options or the exercise is unanswerable.
- Translation.tsx (translation / reverse_translation / listen_type),
  FillInBlank.tsx, WritingPrompt.tsx, DialogueResponse.tsx (dialogue_response
  / speak_response), SpeakRepeat.tsx, GrammarCheck.tsx-without-options:
  submits value.trim(), always a plain string.
- WordOrder.tsx (word_order / listen_order): submits a list of tile strings
  in click order, each tile taken verbatim from prompt.word_bank (each tile
  usable once) — so the correct token sequence must be buildable from the
  word bank or the exercise is unanswerable.
- MatchingPairs.tsx: submits [{left, right}] in prompt.pairs order, left
  verbatim from prompt.pairs, right verbatim from the rendered right column
  (which is exactly the pairs' rights, shuffled).
- Flashcard.tsx: submits "known"/"unknown" (self-report; "known" grades
  correct by definition).
- Placeholder.tsx (listening_placeholder / speaking_placeholder): submits ""
  unconditionally — deliberately has no correct answer, so those types are
  skipped (none exist in the current corpus anyway).

Environment: needs the repo root (docs/content/** + scripts/) visible.
Inside the standard test container only backend/ is mounted, so run with the
full-repo mount (same recipe as backfill_lexemes.py's docstring):

    docker compose run --rm -v "$(cd .. && pwd):/repo" \
        -e LINGO_REPO_ROOT=/repo api \
        sh -c 'DATABASE_URL=... python -m pytest tests/test_content_answer_shapes.py'

Without the mount the module skips (same convention as
test_exercise_renderer_registration.py) rather than failing the standard
container-only run for an environment constraint.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from app.review.grading import decode_feedback, grade, is_multi_answer_response, normalized
from app.content.seed import LANGUAGES
from app.models.entities import ExerciseType

SCRIPT_BY_LANGUAGE = {code: script for code, _name, _native, script, _dir in LANGUAGES}

# Rendered by Placeholder.tsx, which always submits "" — deliberately not
# gradeable-correct, so there is no correct payload to construct.
PLACEHOLDER_TYPES = {"listening_placeholder", "speaking_placeholder"}

# Components that render prompt.options and submit one option string.
OPTION_TYPES = {
    "multiple_choice",
    "listen_select",
    "dialogue_comprehension",
    "reading_comprehension",
}

# Components that render a text input and submit value.trim() (a string).
TEXT_INPUT_TYPES = {
    "translation",
    "reverse_translation",
    "listen_type",
    "dictation",
    "fill_in_blank",
    "writing_prompt",
    "dialogue_response",
    "speak_response",
    "speak_repeat",
}

ORDER_TYPES = {"word_order", "listen_order"}


def _find_repo_root() -> Path | None:
    override = os.environ.get("LINGO_REPO_ROOT")
    candidates = [Path(override)] if override else []
    candidates.append(Path(__file__).resolve().parents[2])
    for candidate in candidates:
        if (candidate / "scripts" / "compile_content.py").exists() and (
            candidate / "scripts" / "manifest.d" / "content"
        ).is_dir():
            return candidate
    return None


def _load_compiler(repo_root: Path):
    spec = importlib.util.spec_from_file_location(
        "lingo_compile_content",
        repo_root / "scripts" / "compile_content.py",
    )
    module = importlib.util.module_from_spec(spec)
    # compile_content.py inserts its own scripts/ dir into sys.path for its
    # _fill_in_blank_ambiguity_check import, so no extra path setup needed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _parse_manifest(repo_root: Path) -> list[tuple[str, list[Path], list[Path]]]:
    """content_manifest.txt: course_name|realization paths|overlay paths."""
    courses = []
    manifest = repo_root / "scripts" / "manifest.d" / "content"
    raw_lines = [
        l for fp in sorted(manifest.glob("*.txt")) for l in fp.read_text(encoding="utf-8").splitlines()
    ]
    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, realizations, overlays = line.split("|")
        courses.append(
            (
                name.strip(),
                [repo_root / p for p in realizations.split()],
                [repo_root / p for p in overlays.split()],
            )
        )
    return courses


@dataclass
class Case:
    case_id: str
    exercise: dict[str, Any] | None = None
    compile_error: str | None = None
    skip_reason: str | None = None
    notes: list[str] = field(default_factory=list)


_CASES: list[Case] | None = None


def _load_cases() -> list[Case]:
    global _CASES
    if _CASES is not None:
        return _CASES

    repo_root = _find_repo_root()
    if repo_root is None:
        _CASES = [
            Case(
                case_id="content-corpus-unavailable",
                skip_reason=(
                    "repo root (scripts/compile_content.py + "
                    "scripts/manifest.d/content/*.txt) not visible in this "
                    "environment — run with the full repo mounted and "
                    "LINGO_REPO_ROOT set (see module docstring)."
                ),
            )
        ]
        return _CASES

    compiler = _load_compiler(repo_root)
    cases: list[Case] = []

    for course_name, realization_paths, overlay_paths in _parse_manifest(repo_root):
        try:
            realizations = [compiler.load_yaml(p) for p in realization_paths]
            overlays = [compiler.load_yaml(p) for p in overlay_paths]
            compiled = compiler.compile_import_request(realizations, overlays)
        except Exception as exc:  # noqa: BLE001 — any compile failure is the finding
            cases.append(
                Case(
                    case_id=f"{course_name}::COMPILE",
                    compile_error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue

        for course in compiled["courses"]:
            for unit in course["units"]:
                for lesson in unit["lessons"]:
                    for exercise in lesson["exercises"]:
                        key = exercise.get("content_key") or f"order{exercise['order']}"
                        cases.append(
                            Case(
                                case_id=(
                                    f"{course_name}::{unit['content_key']}"
                                    f"::{key}::{exercise['type']}"
                                ),
                                exercise=exercise,
                            )
                        )

    _CASES = cases
    return cases


def pytest_generate_tests(metafunc):
    if "case" not in metafunc.fixturenames:
        return
    params = []
    for case in _load_cases():
        marks = [pytest.mark.skip(reason=case.skip_reason)] if case.skip_reason else []
        params.append(pytest.param(case, id=case.case_id, marks=marks))
    metafunc.parametrize("case", params)


def _accepted_values(correct: Any) -> tuple[Any, list[Any]]:
    """Return (canonical, all accepted variants) for either the plain or the
    multi-answer {"canonical","accepted"} compiled correct_response shape."""
    if is_multi_answer_response(correct):
        return correct["canonical"], list(correct["accepted"])
    return correct, [correct]


def _pick_option(
    options: Any, accepted: list[Any], case_sensitive: bool
) -> tuple[str | None, str | None]:
    """Find the rendered option a learner would click for a correct answer.

    Mirrors MultipleChoice/ReadingComprehension/GrammarCheck: the submitted
    payload is one of prompt.options verbatim. Grading normalizes both sides,
    so match options against accepted values via the same normalized()."""
    if not isinstance(options, list) or not options:
        return None, "prompt.options is missing/empty for an option-based component"
    accepted_normalized = [normalized(value, case_sensitive) for value in accepted]
    for option in options:
        if normalized(option, case_sensitive) in accepted_normalized:
            return option, None
    return None, (
        "no rendered option matches any accepted correct answer — the "
        f"learner cannot answer correctly (options={options!r}, "
        f"accepted={accepted!r})"
    )


def _correct_tokens(canonical: Any) -> list[str] | None:
    """Token sequence of the correct answer, preserving original text so the
    tiles can be matched verbatim. Accepts both authored shapes (space-joined
    string, or explicit token list)."""
    if isinstance(canonical, str):
        return canonical.split()
    if isinstance(canonical, list) and all(isinstance(t, str) for t in canonical):
        return list(canonical)
    return None


def _build_word_order_answer(
    exercise: dict[str, Any], canonical: Any, case_sensitive: bool
) -> tuple[list[str] | None, str | None]:
    """Mirror WordOrder.tsx: the submission is a list of tiles clicked from
    prompt.word_bank, each tile usable once, in the correct sentence order."""
    tokens = _correct_tokens(canonical)
    if tokens is None:
        return None, (
            "correct_response is neither a string nor a list of tokens "
            f"({canonical!r}) — WordOrder.tsx cannot represent it"
        )
    word_bank = exercise["prompt"].get("word_bank")
    if not isinstance(word_bank, list) or not word_bank:
        return None, "prompt.word_bank is missing/empty for a word-bank component"

    remaining = list(word_bank)
    chosen: list[str] = []
    for token in tokens:
        # Prefer a verbatim tile; fall back to a normalized match (grading
        # normalizes, so a case/whitespace-differing tile still grades right).
        tile_index = None
        for i, tile in enumerate(remaining):
            if tile == token:
                tile_index = i
                break
        if tile_index is None:
            token_normalized = normalized(token, case_sensitive)
            for i, tile in enumerate(remaining):
                if (
                    isinstance(tile, str)
                    and normalized(tile, case_sensitive) == token_normalized
                ):
                    tile_index = i
                    break
        if tile_index is None:
            return None, (
                f"correct token {token!r} has no available tile in "
                f"word_bank {word_bank!r} — the learner cannot build the "
                "correct answer"
            )
        chosen.append(remaining.pop(tile_index))
    return chosen, None


def _pairs_mapping(canonical: Any, case_sensitive: bool) -> dict[str, Any] | None:
    """Normalize the correct matching_pairs answer into {normalized-left:
    right} regardless of authored shape ([{left,right}] or flat dict)."""
    if isinstance(canonical, dict):
        return {normalized(k, case_sensitive): v for k, v in canonical.items()}
    if isinstance(canonical, list) and all(
        isinstance(item, dict) and {"left", "right"} <= set(item) for item in canonical
    ):
        return {
            normalized(item["left"], case_sensitive): item["right"]
            for item in canonical
        }
    return None


def _build_matching_pairs_answer(
    exercise: dict[str, Any], canonical: Any, case_sensitive: bool
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Mirror MatchingPairs.tsx: [{left, right}] in prompt.pairs order, left
    verbatim from pairs, right verbatim from the rendered right column."""
    pairs = exercise["prompt"].get("pairs")
    if not isinstance(pairs, list) or not pairs:
        return None, "prompt.pairs is missing/empty for a matching component"
    mapping = _pairs_mapping(canonical, case_sensitive)
    if mapping is None:
        return None, (
            f"correct_response {canonical!r} is neither a [{{left,right}}] "
            "list nor a flat mapping — MatchingPairs.tsx cannot represent it"
        )

    rendered_rights = [p.get("right") for p in pairs]
    answer = []
    for p in pairs:
        left = p.get("left")
        correct_right = mapping.get(normalized(left, case_sensitive))
        if correct_right is None:
            return None, (
                f"displayed left {left!r} has no correct match in "
                f"correct_response {canonical!r} — the learner must match "
                "every left but has no correct option for this one"
            )
        # The component can only submit a right that is actually rendered.
        display_right = None
        if correct_right in rendered_rights:
            display_right = correct_right
        else:
            want = normalized(correct_right, case_sensitive)
            for r in rendered_rights:
                if normalized(r, case_sensitive) == want:
                    display_right = r
                    break
        if display_right is None:
            return None, (
                f"correct right {correct_right!r} for left {left!r} is not "
                f"among the rendered rights {rendered_rights!r} — the "
                "learner cannot pick it"
            )
        answer.append({"left": left, "right": display_right})
    return answer, None


def _build_frontend_answer(
    exercise: dict[str, Any], case_sensitive: bool
) -> tuple[Any, str | None]:
    """Construct the correct submission exactly as the real component would,
    or explain why no correct submission is constructible."""
    exercise_type = exercise["type"]
    canonical, accepted = _accepted_values(exercise["correct_response"])

    if exercise_type == "flashcard":
        return "known", None

    if exercise_type in ORDER_TYPES:
        return _build_word_order_answer(exercise, canonical, case_sensitive)

    if exercise_type == "matching_pairs":
        return _build_matching_pairs_answer(exercise, canonical, case_sensitive)

    options = exercise["prompt"].get("options")
    # grammar_check renders options when present, a text input otherwise
    # (GrammarCheck.tsx, 2026-07 fix for closed yes/no questions).
    if exercise_type in OPTION_TYPES or (
        exercise_type == "grammar_check" and isinstance(options, list) and options
    ):
        return _pick_option(options, accepted, case_sensitive)

    if exercise_type in TEXT_INPUT_TYPES or exercise_type == "grammar_check":
        if not isinstance(canonical, str):
            return None, (
                f"correct_response {canonical!r} is not a string, but the "
                f"{exercise_type} component submits value.trim() (a string) "
                "— the learner cannot type a matching answer"
            )
        return canonical.strip(), None

    return None, f"no known frontend submission shape for type {exercise_type!r}"


def test_every_compiled_exercise_grades_correct_with_frontend_payload(case: Case):
    if case.compile_error is not None:
        pytest.fail(f"course failed to compile: {case.compile_error}")

    exercise = case.exercise
    assert exercise is not None

    type_string = exercise["type"]
    if type_string in PLACEHOLDER_TYPES:
        pytest.skip("Placeholder.tsx submits '' unconditionally — not gradeable")

    # Backend must actually know this type (ExerciseType is the DB enum the
    # import path stores into).
    exercise_type = ExerciseType(type_string)

    feedback_meta = decode_feedback(exercise.get("feedback"))
    case_sensitive = bool(feedback_meta.get("case_sensitive"))

    answer, construction_error = _build_frontend_answer(exercise, case_sensitive)
    assert construction_error is None, (
        f"frontend cannot construct a correct submission: {construction_error}"
    )

    script = SCRIPT_BY_LANGUAGE.get(exercise["prompt"].get("answer_language_code"))
    result = grade(
        answer,
        exercise["correct_response"],
        exercise_type,
        script=script,
        orthography_strict=feedback_meta.get("orthography_strict"),
        case_sensitive=case_sensitive,
    )
    assert result == "correct", (
        f"the exact correct answer, submitted in the real frontend payload "
        f"shape, graded {result!r} instead of 'correct' — "
        f"submitted={answer!r}, correct_response={exercise['correct_response']!r}"
    )
