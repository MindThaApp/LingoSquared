#!/usr/bin/env python3
"""Validate and compile layered Lingo² YAML into ImportRequest JSON.

Dependency:
    python -m pip install PyYAML>=6.0

Multi-unit example:
    python scripts/compile_content.py compile \
        --realization \
            docs/content/realizations/fa/a1_unit01_greetings.yaml \
            docs/content/realizations/fa/a1_unit02.yaml \
        --overlay \
            docs/content/overlays/en-fa/a1_unit01.yaml \
            docs/content/overlays/en-fa/a1_unit02.yaml \
        --output compiled/farsi_a1.json

Each realization path is paired by position with the corresponding overlay
path. Units are emitted in realization argument order.

The compiler deliberately uses PyYAML rather than a partial in-house parser.
A partial parser could silently reinterpret multilingual content, folded text,
Unicode escapes, or nested answer specifications.

Current tokenizer limitation:
    The untaught-vocabulary validator uses a simple Unicode word tokenizer.
    This is adequate for whitespace-delimited languages in the first round but
    is not suitable for Chinese segmentation. A language-specific tokenizer is
    required before zh content is published.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is required. Install it with "
        "`python -m pip install 'PyYAML>=6.0'`, or run this script in "
        "the content-build container once that dependency is added.",
        file=sys.stderr,
    )
    raise SystemExit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPINE = REPO_ROOT / "docs/content/universal_spine.yaml"

# scripts/_fill_in_blank_ambiguity_check.py holds the real lexeme-matching
# logic (byte-ported from backend/app/practice/service.py's lexeme_matches())
# for AUTHORING_GUIDE.md #17's fill_in_blank ambiguity check. Reused here
# rather than reimplemented so the standalone audit script and this
# permanent compiler validator can never silently drift apart.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from _fill_in_blank_ambiguity_check import (  # noqa: E402
    lexeme_matches as _fib_lexeme_matches,
    load_lexemes_for_pair as _fib_load_lexemes_for_pair,
)

RTL_LANGUAGES = {"fa", "prs", "ar"}
# Persian-script codepoint purity only applies to fa/prs (Persian-range
# yeh/keheh are the CORRECT codepoints there). Arabic (ar) is RTL too but
# uses the opposite convention -- Arabic-range yeh U+064A / kaf U+0643 are
# the correct codepoints for ar, so it must not be checked against this
# same forbidden-codepoint list. Kept as a separate set from RTL_LANGUAGES
# rather than special-casing "ar" inline, so any future RTL/Arabic-script
# language (e.g. a future Urdu path) defaults to no script-purity
# assumption unless explicitly added here.
PERSIAN_SCRIPT_LANGUAGES = {"fa", "prs"}
FORBIDDEN_PERSIAN_CODEPOINTS = {
    "\u064a": "Arabic Yeh U+064A (ي); use Persian Yeh U+06CC (ی)",
    "\u0643": "Arabic Kaf U+0643 (ك); use Persian Keheh U+06A9 (ک)",
}
# Python's \w covers Devanagari letters, but not the dependent vowel signs,
# nukta, virama, and related combining marks that complete a word. Keep the
# Devanagari branch separate so those marks do not attach to other scripts.
DEVANAGARI_WORD_CHARS = (
    "\u0900-\u0963"
    "\u0966-\u096f"
    "\u0971-\u097f"
)
TOKEN_RE = re.compile(
    rf"[{DEVANAGARI_WORD_CHARS}][\w\u200c{DEVANAGARI_WORD_CHARS}]*|"
    r"[\w\u200c]+",
    re.UNICODE,
)
SPEAKER_LABEL_RE = re.compile(
    r"^[ \t]*(?P<label>[^\n:]{1,40}?)[ \t]*:",
    re.MULTILINE,
)
ACCEPTED_VARIANT_STATUSES = {"correct", "acceptable_with_note"}
PRACTICE_EXERCISE_TYPES = {
    "multiple_choice",
    "fill_in_blank",
    "word_order",
    "translation",
    "matching_pairs",
    "listen_select",
}
PRACTICE_ANSWER_KINDS = {
    "render_frame",
    "slot_text",
    "slot_gloss",
    "ordered_slot_texts",
    "matching_pairs",
}
SLOT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SLOT_PLACEHOLDER_RE = re.compile(r"\{([a-z][a-z0-9_]*)\}")
_MISSING = object()
MIN_MATCHING_PAIR_COUNT = 6


class Report:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, location: str, message: str):
        self.errors.append(f"{location}: {message}")

    def warn(self, location: str, message: str):
        self.warnings.append(f"{location}: {message}")

    def print(self):
        for warning in self.warnings:
            print(f"WARN: {warning}", file=sys.stderr)
        for error in self.errors:
            print(f"ERROR: {error}", file=sys.stderr)

        print(
            f"Validation complete: {len(self.errors)} error(s), "
            f"{len(self.warnings)} warning(s).",
            file=sys.stderr,
        )


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = yaml.safe_load(handle)
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {path}: {exc}") from exc

    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping at its root")
    return value


def walk(value: Any, location: str = "$"):
    yield location, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{location}[{index}]")


def tokenize(text: str) -> set[str]:
    return {
        token.casefold()
        for token in TOKEN_RE.findall(text)
        if token.strip()
    }


VALID_UNIT_SECTIONS = {"reading_writing", "speaking"}


def validate_unit_sections(realization: dict[str, Any], report: Report):
    for unit_index, unit in enumerate(realization.get("units", [])):
        section = unit.get("section", "reading_writing")
        if section not in VALID_UNIT_SECTIONS:
            report.error(
                f"realization.units[{unit_index}].section",
                f"{section!r} is not a valid unit section; must be one of "
                f"{sorted(VALID_UNIT_SECTIONS)}",
            )


def validate_content_keys(realization: dict[str, Any], report: Report):
    seen: dict[str, str] = {}

    for location, value in walk(realization, "realization"):
        if not isinstance(value, dict) or "content_key" not in value:
            continue

        key = value["content_key"]
        if not isinstance(key, str) or not key.strip():
            report.error(location, "content_key must be a non-empty string")
            continue

        if key in seen:
            report.error(
                location,
                f"duplicate content_key {key!r}; first defined at {seen[key]}",
            )
        else:
            seen[key] = location


def validate_global_content_keys(
    realizations: list[tuple[Path, dict[str, Any]]],
    report: Report,
):
    seen: dict[str, tuple[Path, str]] = {}

    for path, realization in realizations:
        seen_in_file: set[str] = set()

        for location, value in walk(realization, "realization"):
            if not isinstance(value, dict) or "content_key" not in value:
                continue

            key = value["content_key"]
            if not isinstance(key, str) or not key.strip():
                continue

            if key in seen_in_file:
                continue
            seen_in_file.add(key)

            previous = seen.get(key)
            if previous is None:
                seen[key] = (path, location)
                continue

            previous_path, previous_location = previous
            if previous_path != path:
                report.error(
                    f"{path}:{location}",
                    f"duplicate content_key {key!r} across realization files; "
                    f"first defined at {previous_path}:{previous_location}",
                )


def validate_spine_references(
    spine: dict[str, Any],
    realization: dict[str, Any],
    report: Report,
):
    known = {
        outcome.get("id")
        for outcome in spine.get("outcomes", [])
        if isinstance(outcome, dict)
    }

    for location, value in walk(realization, "realization"):
        if not isinstance(value, dict):
            continue

        references = []
        if "spine_outcome_id" in value:
            references.append(value["spine_outcome_id"])
        if "spine_outcome_ids" in value:
            listed = value["spine_outcome_ids"]
            if not isinstance(listed, list):
                report.error(
                    location,
                    "spine_outcome_ids must be a list",
                )
                continue
            references.extend(listed)

        for reference in references:
            if reference is None:
                continue
            if reference not in known:
                report.error(
                    location,
                    f"unresolved spine outcome {reference!r}",
                )


def validate_script_purity(
    document: dict[str, Any],
    target_language: str,
    document_name: str,
    report: Report,
):
    if target_language not in PERSIAN_SCRIPT_LANGUAGES:
        return

    for location, value in walk(document, document_name):
        if not isinstance(value, str):
            continue
        for character, explanation in FORBIDDEN_PERSIAN_CODEPOINTS.items():
            if character in value:
                report.error(location, explanation)


def validate_text_block_directions(
    document: dict[str, Any],
    document_name: str,
    report: Report,
):
    for location, value in walk(document, document_name):
        if not isinstance(value, dict):
            continue
        if "text" not in value or "language_code" not in value:
            continue

        language_code = value.get("language_code")
        expected = "rtl" if language_code in RTL_LANGUAGES else "ltr"
        actual = value.get("direction")

        if actual != expected:
            report.error(
                location,
                f"direction for {language_code!r} must be {expected!r}, "
                f"got {actual!r}",
            )


def validate_overlay_references(
    realization: dict[str, Any],
    overlay: dict[str, Any],
    report: Report,
):
    teaching_keys = set()
    exercise_keys = set()
    lesson_keys = set()

    for _, value in walk(realization):
        if not isinstance(value, dict):
            continue
        key = value.get("content_key")
        if not key:
            continue
        if "introduced_tokens" in value:
            teaching_keys.add(key)
        if "type" in value and "tested_text" in value:
            exercise_keys.add(key)
        if "teaching" in value and "exercises" in value:
            lesson_keys.add(key)

    for key in overlay.get("lessons", {}):
        if key not in lesson_keys:
            report.error(
                f"overlay.lessons.{key}",
                "references an unknown realization lesson",
            )

    for key in overlay.get("teaching", {}):
        if key not in teaching_keys:
            report.error(
                f"overlay.teaching.{key}",
                "references an unknown realization teaching item",
            )

    for key in overlay.get("exercises", {}):
        if key not in exercise_keys:
            report.error(
                f"overlay.exercises.{key}",
                "references an unknown realization exercise",
            )


YAML_BOOLEAN_CONTROL_KEYS = {
    "case_sensitive",
    "human_reviewed",
    "orthography_strict",
    "target_language_first",
}


def validate_no_stray_yaml_booleans(
    realization: dict[str, Any],
    overlay: dict[str, Any],
    report: Report,
):
    def check_value(value: Any, location: str):
        if isinstance(value, bool):
            report.error(
                location,
                f"parsed as YAML boolean {value!r} where a string is "
                "expected — quote it as a string in the source YAML "
                '(for example, "Yes" instead of Yes)',
            )
        elif isinstance(value, list):
            for i, item in enumerate(value):
                check_value(item, f"{location}[{i}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                if isinstance(key, bool):
                    report.error(
                        f"{location}.{key!r}",
                        f"parsed a mapping key as YAML boolean {key!r}; "
                        "quote it as a string in the source YAML",
                    )
                if key in YAML_BOOLEAN_CONTROL_KEYS:
                    continue
                check_value(item, f"{location}.{key}")

    check_value(overlay, "overlay")

    for unit_index, unit in enumerate(realization.get("units", [])):
        if not isinstance(unit, dict):
            continue
        for lesson_index, lesson in enumerate(unit.get("lessons", [])):
            if not isinstance(lesson, dict):
                continue
            lesson_location = (
                f"realization.units[{unit_index}].lessons[{lesson_index}]"
            )
            for teaching_index, item in enumerate(lesson.get("teaching", [])):
                check_value(
                    item,
                    f"{lesson_location}.teaching[{teaching_index}]",
                )
            for exercise_index, exercise in enumerate(lesson.get("exercises", [])):
                check_value(
                    exercise,
                    f"{lesson_location}.exercises[{exercise_index}]",
                )


def normalize_dialogue_option(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = SPEAKER_LABEL_RE.sub("", value, count=1)
    value = re.sub(r"[^\w\u200c]+", " ", value, flags=re.UNICODE)
    normalized = " ".join(value.casefold().split())
    return normalized or None


def dialogue_speaker_and_text(
    block: dict[str, Any],
) -> tuple[str | None, str | None, bool]:
    speaker = block.get("speaker")
    text = block.get("text")
    if not isinstance(text, str):
        return None, None, False
    if isinstance(speaker, str) and speaker.strip():
        return speaker.strip(), text, True
    match = SPEAKER_LABEL_RE.match(text)
    if not match:
        return None, text, False
    return match.group("label").strip(), text[match.end() :].strip(), False


def _option_values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _accepted_answer_values(exercise_overlay: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    if "correct_response" in exercise_overlay:
        normalized = normalize_dialogue_option(exercise_overlay["correct_response"])
        if normalized:
            values.add(normalized)
    for variant in exercise_overlay.get("accepted_answers", []):
        value = variant.get("value") if isinstance(variant, dict) else variant
        normalized = normalize_dialogue_option(value)
        if normalized:
            values.add(normalized)
    return values


def _dialogue_turn(
    speaker: str | None,
    text: str | None,
    *,
    structured_speaker: bool,
    content_key: Any,
    source_text: Any = None,
) -> dict[str, Any] | None:
    target_norm = normalize_dialogue_option(text)
    if not target_norm:
        return None
    return {
        "speaker": speaker,
        "structured_speaker": structured_speaker,
        "target_text": text,
        "target_norm": target_norm,
        "source_norm": normalize_dialogue_option(source_text),
        "content_key": content_key or "<unknown>",
    }


def _lesson_dialogue_turns(
    lesson: dict[str, Any],
    teaching_overlays: dict[str, Any],
) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []

    def add_text_blocks(blocks: Any, content_key: Any):
        if not isinstance(blocks, list):
            return
        for index, block in enumerate(blocks):
            if not isinstance(block, dict):
                continue
            speaker, text, structured = dialogue_speaker_and_text(block)
            turn = _dialogue_turn(
                speaker,
                text,
                structured_speaker=structured,
                content_key=f"{content_key}.text_blocks[{index}]",
            )
            if turn:
                turns.append(turn)

    add_text_blocks(lesson.get("text_blocks"), lesson.get("content_key"))

    for item in lesson.get("teaching", []):
        if not isinstance(item, dict):
            continue
        content_key = item.get("content_key")
        add_text_blocks(item.get("text_blocks"), content_key)
        target = item.get("target", {})
        if item.get("kind") != "dialogue" or not isinstance(target, dict):
            continue
        speaker, target_text, structured = dialogue_speaker_and_text(target)
        overlay_entry = teaching_overlays.get(content_key, {})
        source_text = None
        if isinstance(overlay_entry, dict):
            source_text = overlay_entry.get("gloss")
        turn = _dialogue_turn(
            speaker,
            target_text,
            structured_speaker=structured,
            content_key=content_key,
            source_text=source_text,
        )
        if turn:
            turns.append(turn)

    return turns


def _is_dialogue_audio_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.casefold()
    return "dialogue" in normalized or "dialog" in normalized


def _matching_tested_turns(
    turns: list[dict[str, Any]],
    tested_norm: str,
) -> list[dict[str, Any]]:
    matches = []
    for turn in turns:
        line_norm = turn["target_norm"]
        if line_norm == tested_norm:
            matches.append(turn)
        elif tested_norm in line_norm or line_norm in tested_norm:
            matches.append(turn)
    return matches


def validate_same_speaker_dialogue_distractors(
    realization: dict[str, Any],
    overlay: dict[str, Any],
    report: Report,
):
    teaching_overlays = overlay.get("teaching", {})
    exercise_overlays = overlay.get("exercises", {})
    if not isinstance(teaching_overlays, dict):
        teaching_overlays = {}
    if not isinstance(exercise_overlays, dict):
        exercise_overlays = {}

    for unit in realization.get("units", []):
        for lesson in unit.get("lessons", []):
            if not isinstance(lesson, dict):
                continue

            turns = _lesson_dialogue_turns(lesson, teaching_overlays)
            if len(turns) < 2:
                continue

            for exercise in lesson.get("exercises", []):
                if not isinstance(exercise, dict):
                    continue
                if exercise.get("type") not in {
                    "listen_select",
                    "dialogue_comprehension",
                    "dialogue_response",
                }:
                    continue
                if exercise.get("type") == "listen_select" and not (
                    _is_dialogue_audio_key(exercise.get("media_asset_key"))
                    or any(turn.get("speaker") for turn in turns)
                ):
                    continue

                key = exercise.get("content_key")
                exercise_overlay = exercise_overlays.get(key, {})
                if not isinstance(exercise_overlay, dict):
                    continue

                tested_norm = normalize_dialogue_option(exercise.get("tested_text"))
                if not tested_norm:
                    continue
                matching_turns = _matching_tested_turns(turns, tested_norm)
                if not matching_turns:
                    continue

                wrong_options = []
                for field in ("distractors", "options"):
                    for option in _option_values(exercise_overlay.get(field)):
                        normalized = normalize_dialogue_option(option)
                        if normalized:
                            wrong_options.append((field, option, normalized))

                correct_values = {
                    normalize_dialogue_option(exercise_overlay.get("correct_option")),
                    *_accepted_answer_values(exercise_overlay),
                }
                wrong_options = [
                    option
                    for option in wrong_options
                    if option[2] not in correct_values
                ]
                if not wrong_options:
                    continue

                for tested_turn in matching_turns:
                    tested_speaker = tested_turn.get("speaker")
                    if not tested_speaker:
                        continue
                    structured = tested_turn.get("structured_speaker")
                    for other_turn in turns:
                        if other_turn.get("speaker") != tested_speaker:
                            continue
                        spoken_values = {
                            value
                            for value in (
                                other_turn["target_norm"],
                                other_turn["source_norm"],
                            )
                            if value
                        }
                        for field, option, normalized in wrong_options:
                            if normalized not in spoken_values:
                                continue
                            message = (
                                "wrong option "
                                f"{option!r} matches a line by speaker "
                                f"{tested_speaker!r} in the same dialogue "
                                f"({other_turn['content_key']}); dialogue "
                                "distractors must not be anything the "
                                "tested speaker says anywhere in that audio"
                            )
                            location = f"overlay.exercises.{key}.{field}"
                            if structured and other_turn.get("structured_speaker"):
                                report.error(location, message)
                            else:
                                report.warn(
                                    location,
                                    message
                                    + " (speaker attribution is not fully "
                                    "structured, so this is a warning)",
                                )


def normalize_order_token(value: Any, *, case_sensitive: bool = False) -> Any:
    """Mirror backend/app/api/router.py's normalized() for order tokens."""
    if isinstance(value, str):
        text = value.strip() if case_sensitive else value.strip().casefold()
        return " ".join(text.split())
    return value


def canonical_order_answer_tokens(
    value: Any,
    *,
    case_sensitive: bool = False,
) -> list[Any] | None:
    """Mirror router.canonical_order_tokens() exactly for answer values."""
    if isinstance(value, str):
        collapsed = normalize_order_token(value, case_sensitive=case_sensitive)
        return collapsed.split(" ") if collapsed else []
    if isinstance(value, list):
        return [
            normalize_order_token(item, case_sensitive=case_sensitive)
            for item in value
        ]
    return None


def order_sequence_key(value: Any, *, case_sensitive: bool = False) -> Any:
    """Punctuation-insensitive key used only to align tiles to tested_text."""
    token = normalize_order_token(value, case_sensitive=case_sensitive)
    if not isinstance(token, str):
        return token

    start = 0
    end = len(token)
    while start < end and unicodedata.category(token[start]).startswith("P"):
        start += 1
    while end > start and unicodedata.category(token[end - 1]).startswith("P"):
        end -= 1
    return token[start:end]


def sentence_order_tokens_from_word_bank(
    tested_text: Any,
    word_bank: list[Any],
    *,
    case_sensitive: bool = False,
) -> list[Any] | None:
    """Return word_bank tokens ordered by tested_text, when unambiguous.

    Real word-order tiles often retain punctuation on the tile while
    tested_text stores the bare sentence. Align by punctuation-stripped
    token keys, but return the original normalized tile tokens so the final
    comparison still mirrors the grader-facing answer shape.
    """
    tested_tokens = canonical_order_answer_tokens(
        tested_text,
        case_sensitive=case_sensitive,
    )
    if tested_tokens is None:
        return None

    available: dict[Any, list[Any]] = {}
    for token in word_bank:
        normalized = normalize_order_token(token, case_sensitive=case_sensitive)
        key = order_sequence_key(normalized, case_sensitive=case_sensitive)
        available.setdefault(key, []).append(normalized)

    ordered = []
    for token in tested_tokens:
        key = order_sequence_key(token, case_sensitive=case_sensitive)
        matches = available.get(key)
        if not matches:
            return None
        ordered.append(matches.pop(0))

    if any(matches for matches in available.values()):
        return None
    return ordered


def _order_answer_values(exercise_overlay: dict[str, Any]) -> list[tuple[str, Any]]:
    if "correct_response" in exercise_overlay:
        return [("correct_response", exercise_overlay["correct_response"])]

    values = []
    for index, variant in enumerate(exercise_overlay.get("accepted_answers", [])):
        value = variant.get("value") if isinstance(variant, dict) else variant
        values.append((f"accepted_answers[{index}]", value))
    return values


def _counter_diff(
    expected: Counter[Any],
    actual: Counter[Any],
) -> tuple[dict[Any, int], dict[Any, int]]:
    missing = expected - actual
    extra = actual - expected
    return dict(missing), dict(extra)


def validate_order_word_bank_answers(
    realization: dict[str, Any],
    overlay: dict[str, Any],
    report: Report,
):
    exercise_overlays = overlay.get("exercises", {})

    for unit in realization.get("units", []):
        for lesson in unit.get("lessons", []):
            for exercise in lesson.get("exercises", []):
                if exercise.get("type") not in {"word_order", "listen_order"}:
                    continue

                key = exercise.get("content_key", "<unknown>")
                word_bank = exercise.get("word_bank")
                if not isinstance(word_bank, list):
                    continue

                exercise_overlay = exercise_overlays.get(key, {})
                if not isinstance(exercise_overlay, dict):
                    continue

                case_sensitive = bool(exercise_overlay.get("case_sensitive"))
                # WordOrder.tsx exposes one fixed word_bank, so every accepted
                # variant must be buildable from that exact multiset. Variants
                # with genuinely different wording need a different exercise
                # shape; otherwise one of the advertised correct answers is
                # mechanically impossible to click.
                tile_tokens = [
                    normalize_order_token(item, case_sensitive=case_sensitive)
                    for item in word_bank
                ]
                tile_counts = Counter(tile_tokens)
                expected_tokens = sentence_order_tokens_from_word_bank(
                    exercise.get("tested_text"),
                    word_bank,
                    case_sensitive=case_sensitive,
                )

                for answer_location, answer_value in _order_answer_values(
                    exercise_overlay
                ):
                    answer_tokens = canonical_order_answer_tokens(
                        answer_value,
                        case_sensitive=case_sensitive,
                    )
                    if answer_tokens is None:
                        continue

                    answer_counts = Counter(answer_tokens)
                    if answer_counts != tile_counts:
                        missing, extra = _counter_diff(tile_counts, answer_counts)
                        report.error(
                            f"overlay.exercises.{key}.{answer_location}",
                            "word_bank tiles do not match order-answer tokens: "
                            f"{len(tile_tokens)} tile(s) vs "
                            f"{len(answer_tokens)} answer token(s); "
                            f"missing from answer {missing}; "
                            f"extra in answer {extra}",
                        )
                        continue

                    if (
                        expected_tokens is None
                        or answer_tokens == expected_tokens
                        or answer_tokens != tile_tokens
                    ):
                        continue

                    report.error(
                        f"overlay.exercises.{key}.{answer_location}",
                        "order-answer tokens match the displayed word_bank "
                        "order instead of tested_text sentence order: "
                        f"expected {expected_tokens!r}; "
                        f"got {answer_tokens!r}",
                    )


def validate_matching_pairs_minimum_scale(
    realization: dict[str, Any],
    report: Report,
):
    for unit in realization.get("units", []):
        for lesson in unit.get("lessons", []):
            for exercise in lesson.get("exercises", []):
                if exercise.get("type") != "matching_pairs":
                    continue

                key = exercise.get("content_key", "<unknown>")
                pairs = exercise.get("pairs")
                if not isinstance(pairs, list):
                    continue

                if len(pairs) < MIN_MATCHING_PAIR_COUNT:
                    # WARNING, not error: AUTHORING_GUIDE.md §16 is an aim
                    # ("6-12 where the unit's vocabulary genuinely supports
                    # it - don't pad"), and it explicitly grandfathers
                    # already-shipped small exercises pending a retrofit
                    # pass. A hard floor would block every import over
                    # legacy content (50 instances in en-fa alone).
                    report.warn(
                        f"realization.exercises.{key}.pairs",
                        "matching_pairs below AUTHORING_GUIDE.md §16 aim "
                        f"(found {len(pairs)}, aim {MIN_MATCHING_PAIR_COUNT}-12) "
                        "- pool earlier-taught vocabulary if the unit "
                        "supports it; do not pad",
                    )


def _matching_pair_tuple(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, dict):
        return None
    left = value.get("left")
    right = value.get("right")
    if not isinstance(left, str) or not isinstance(right, str):
        return None
    return left, right


def _matching_pair_counter(values: Any) -> Counter[tuple[str, str]] | None:
    if isinstance(values, dict):
        pairs = []
        for left, right in values.items():
            if not isinstance(left, str) or not isinstance(right, str):
                return None
            pairs.append((left, right))
        return Counter(pairs)

    if not isinstance(values, list):
        return None

    pairs: list[tuple[str, str]] = []
    for value in values:
        pair = _matching_pair_tuple(value)
        if pair is not None:
            pairs.append(pair)
            continue
        if not isinstance(value, dict) or len(value) != 1:
            return None
        left, right = next(iter(value.items()))
        if not isinstance(left, str) or not isinstance(right, str):
            return None
        pairs.append((left, right))
    return Counter(pairs)


def _overlay_matching_pair_answers(
    exercise_overlay: dict[str, Any],
) -> list[tuple[str, Counter[tuple[str, str]] | None]]:
    if "correct_response" in exercise_overlay:
        return [
            (
                "correct_response",
                _matching_pair_counter(exercise_overlay["correct_response"]),
            )
        ]

    answers = []
    for index, variant in enumerate(exercise_overlay.get("accepted_answers", [])):
        value = variant.get("value") if isinstance(variant, dict) else variant
        answers.append(
            (
                f"accepted_answers[{index}]",
                _matching_pair_counter(value),
            )
        )
    return answers


def _format_pair_counter(counter: Counter[tuple[str, str]]) -> list[str]:
    return [
        f"{left!r} -> {right!r}"
        for (left, right), count in sorted(counter.items())
        for _ in range(count)
    ]


def validate_matching_pairs_overlay_mirror(
    realization: dict[str, Any],
    overlay: dict[str, Any],
    report: Report,
):
    exercise_overlays = overlay.get("exercises", {})
    if not isinstance(exercise_overlays, dict):
        exercise_overlays = {}

    for unit in realization.get("units", []):
        for lesson in unit.get("lessons", []):
            for exercise in lesson.get("exercises", []):
                if exercise.get("type") != "matching_pairs":
                    continue

                key = exercise.get("content_key", "<unknown>")
                realization_pairs = _matching_pair_counter(exercise.get("pairs"))
                if realization_pairs is None:
                    continue

                exercise_overlay = exercise_overlays.get(key, {})
                if not isinstance(exercise_overlay, dict):
                    continue

                for answer_location, overlay_pairs in _overlay_matching_pair_answers(
                    exercise_overlay
                ):
                    location = f"overlay.exercises.{key}.{answer_location}"
                    if overlay_pairs is None:
                        report.error(
                            location,
                            "matching_pairs answer must be a list of "
                            "{left, right} string pairs that mirrors "
                            "realization pairs",
                        )
                        continue

                    if overlay_pairs == realization_pairs:
                        continue

                    missing, extra = _counter_diff(
                        realization_pairs,
                        overlay_pairs,
                    )
                    report.error(
                        location,
                        "matching_pairs answer does not mirror realization "
                        "pairs exactly: "
                        f"{sum(realization_pairs.values())} realization "
                        "pair(s) vs "
                        f"{sum(overlay_pairs.values())} overlay pair(s); "
                        f"missing from overlay {_format_pair_counter(missing)}; "
                        f"extra in overlay {_format_pair_counter(extra)}",
                    )


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(_text_values(item))
        return values
    if isinstance(value, dict):
        values = []
        text = value.get("text")
        if isinstance(text, str):
            values.append(text)
        for key, item in value.items():
            if key == "text":
                continue
            values.extend(_text_values(item))
        return values
    return []


def _media_asset_text(item: dict[str, Any]) -> str | None:
    values: list[str] = []
    for field in ("text", "script"):
        if field in item:
            values.extend(_text_values(item[field]))
    text = " ".join(value.strip() for value in values if value.strip())
    return text or None


def _media_asset_texts(
    realization: dict[str, Any],
) -> dict[Any, str]:
    texts = {}
    for item in realization.get("media_assets", []):
        if not isinstance(item, dict):
            continue
        key = item.get("content_key")
        text = _media_asset_text(item)
        if key and text:
            texts[key] = text
    return texts


def _normalized_contains(haystack: str, needle: str) -> bool:
    normalized_haystack = normalize_audio_text(haystack)
    normalized_needle = normalize_audio_text(needle)
    if normalized_haystack and normalized_needle:
        if normalized_needle in normalized_haystack:
            return True

    normalized_haystack = normalize_dialogue_option(haystack)
    normalized_needle = normalize_dialogue_option(needle)
    if not normalized_haystack or not normalized_needle:
        return False
    return normalized_needle in normalized_haystack


def normalize_audio_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = re.sub(r"[^\w\u200c]+", " ", value, flags=re.UNICODE)
    normalized = " ".join(value.casefold().split())
    return normalized or None


def validate_listen_audio_contains_tested_text(
    realization: dict[str, Any],
    report: Report,
):
    media_texts = _media_asset_texts(realization)

    for unit in realization.get("units", []):
        for lesson in unit.get("lessons", []):
            for exercise in lesson.get("exercises", []):
                exercise_type = exercise.get("type")
                if exercise_type not in {"listen_order", "listen_type"}:
                    continue

                tested_text = exercise.get("tested_text")
                media_key = exercise.get("media_asset_key")
                if not isinstance(tested_text, str) or not media_key:
                    continue

                media_text = media_texts.get(media_key)
                if media_text is None:
                    continue

                if _normalized_contains(media_text, tested_text):
                    continue

                key = exercise.get("content_key", "<unknown>")
                report.error(
                    f"realization.exercises.{key}.media_asset_key",
                    f"media asset {media_key!r} text/script does not contain "
                    f"tested_text {tested_text!r}",
                )


#: Keys where a real YAML boolean is the intended, correct type — internal
#: control flags never rendered to a learner, not the "author meant to write
#: the string Yes/No and got silently coerced" footgun this check exists for.
#: `interchangeable` (AUTHORING_GUIDE.md#17, added 2026-07-06) opts a
#: fill_in_blank template's answer_derivation into accepting any of its
#: slot's own matching candidates as correct, for slots whose pool is a
#: closed set of true synonyms (e.g. je/jij) that a single fixed answer
#: can't fairly grade.
PRACTICE_BOOLEAN_CONTROL_KEYS = {"interchangeable"}


def validate_no_practice_yaml_booleans(
    pack: dict[str, Any],
    report: Report,
):
    """Apply the existing YAML-boolean footgun rule to practice content."""
    for location, value in walk(pack.get("templates", []), "practice.templates"):
        if isinstance(value, bool):
            if location.rsplit(".", 1)[-1] in PRACTICE_BOOLEAN_CONTROL_KEYS:
                continue
            report.error(
                location,
                f"parsed as YAML boolean {value!r} — quote learner-facing "
                "Yes/No/True/False/On/Off values as strings",
            )


# Compiled practice artifact contract (artifact_version 1):
# {
#   artifact_type, artifact_version, source_language, target_language,
#   packs: [{pack_key, unit_content_key, tag_schema,
#            templates: [{content_key, lesson_content_key, type, frame,
#                         slots, answer_derivation, feedback_frame}]}]
# }
# Phase 2 may select only templates whose lesson_content_key is completed,
# query Lexeme rows by the slot constraints, render frames, then execute one
# of PRACTICE_ANSWER_KINDS. No expression language or runtime code is stored.
# Constraint semantics are fixed: a scalar requested tag equals a scalar
# Lexeme tag or is a member of a list-valued Lexeme tag; a requested list is
# an OR query. part_of_speech uses the same scalar/list OR convention.


def _validate_frame_slots(
    frame: Any,
    slots: dict[str, Any],
    location: str,
    report: Report,
    *,
    require_all: bool,
):
    if not isinstance(frame, dict):
        report.error(location, "must be a mapping")
        return
    text = frame.get("text")
    if not isinstance(text, str) or not text.strip():
        report.error(f"{location}.text", "must be a non-empty string")
        return

    placeholders = set(SLOT_PLACEHOLDER_RE.findall(text))
    residue = SLOT_PLACEHOLDER_RE.sub("", text)
    if "{" in residue or "}" in residue:
        report.error(
            f"{location}.text",
            "contains malformed slot syntax; use {snake_case_slot_name}",
        )

    unknown = sorted(placeholders - set(slots))
    if unknown:
        report.error(
            f"{location}.text",
            f"references undefined slot(s): {', '.join(unknown)}",
        )
    if require_all:
        unused = sorted(set(slots) - placeholders)
        if unused:
            report.error(
                f"{location}.text",
                f"does not reference declared slot(s): {', '.join(unused)}",
            )
    rendering = frame.get("slot_rendering", {})
    if not isinstance(rendering, dict):
        report.error(f"{location}.slot_rendering", "must be a mapping")
    else:
        for slot, field in rendering.items():
            if slot not in placeholders:
                report.error(
                    f"{location}.slot_rendering.{slot}",
                    "references a slot not present in this frame",
                )
            if field not in {"token", "english_gloss"}:
                report.error(
                    f"{location}.slot_rendering.{slot}",
                    "must be token or english_gloss",
                )


def _validate_slot_constraints(
    slots: Any,
    tag_schema: dict[str, Any],
    location: str,
    report: Report,
):
    if not isinstance(slots, dict) or not slots:
        report.error(location, "must be a non-empty mapping")
        return {}

    known_pos = set(tag_schema.get("part_of_speech", []))
    known_tags = tag_schema.get("agreement_tags", {})
    if not isinstance(known_tags, dict):
        known_tags = {}

    for slot_name, constraints in slots.items():
        slot_location = f"{location}.{slot_name}"
        if not isinstance(slot_name, str) or not SLOT_NAME_RE.fullmatch(slot_name):
            report.error(slot_location, "slot name must be snake_case")
            continue
        if not isinstance(constraints, dict):
            report.error(slot_location, "constraints must be a mapping")
            continue

        pos_values = constraints.get("part_of_speech")
        if isinstance(pos_values, str):
            pos_values = [pos_values]
        if not isinstance(pos_values, list) or not pos_values:
            report.error(
                f"{slot_location}.part_of_speech",
                "must name at least one declared part of speech",
            )
        else:
            for pos in pos_values:
                if pos not in known_pos:
                    report.error(
                        f"{slot_location}.part_of_speech",
                        f"references undeclared part-of-speech tag {pos!r}",
                    )

        agreement = constraints.get("agreement_tags", {})
        if not isinstance(agreement, dict):
            report.error(
                f"{slot_location}.agreement_tags",
                "must be a mapping",
            )
            continue
        for tag_name, requested in agreement.items():
            allowed = known_tags.get(tag_name)
            if not isinstance(allowed, list):
                report.error(
                    f"{slot_location}.agreement_tags.{tag_name}",
                    "references an undeclared agreement tag",
                )
                continue
            requested_values = requested if isinstance(requested, list) else [requested]
            for requested_value in requested_values:
                if requested_value not in allowed:
                    report.error(
                        f"{slot_location}.agreement_tags.{tag_name}",
                        f"references undeclared tag value {requested_value!r}",
                    )
    return slots


def _validate_answer_derivation(
    derivation: Any,
    slots: dict[str, Any],
    location: str,
    report: Report,
):
    if not isinstance(derivation, dict):
        report.error(location, "must be a mapping")
        return
    kind = derivation.get("kind")
    if kind not in PRACTICE_ANSWER_KINDS:
        report.error(
            f"{location}.kind",
            f"must be one of {sorted(PRACTICE_ANSWER_KINDS)}",
        )
        return
    if kind == "render_frame":
        _validate_frame_slots(
            derivation.get("frame"),
            slots,
            f"{location}.frame",
            report,
            require_all=False,
        )
    elif kind in {"slot_text", "slot_gloss"}:
        slot = derivation.get("slot")
        if slot not in slots:
            report.error(f"{location}.slot", f"references unknown slot {slot!r}")
    else:
        referenced = derivation.get("slots")
        if not isinstance(referenced, list) or not referenced:
            report.error(f"{location}.slots", "must be a non-empty list")
        else:
            for slot in referenced:
                if slot not in slots:
                    report.error(
                        f"{location}.slots",
                        f"references unknown slot {slot!r}",
                    )


def collect_content_keys(
    documents: list[tuple[Path, dict[str, Any]]],
) -> dict[str, str]:
    keys: dict[str, str] = {}
    for path, document in documents:
        for location, value in walk(document, "content"):
            if isinstance(value, dict):
                key = value.get("content_key")
                if isinstance(key, str) and key.strip() and key not in keys:
                    keys[key] = f"{path}:{location}"
    return keys


def validate_practice_packs(
    packs: list[tuple[Path, dict[str, Any]]],
    existing_documents: list[tuple[Path, dict[str, Any]]] | None = None,
) -> Report:
    report = Report()
    existing_keys = collect_content_keys(existing_documents or [])
    seen = dict(existing_keys)
    expected_pair: tuple[Any, Any] | None = None
    # Cache of (source_language, target_language) -> lexeme list (or None if
    # unmapped/failed to load) for the AUTHORING_GUIDE.md #17 ambiguity
    # check below, so each direction's real backfill_lexemes*.py data is
    # only loaded once per validate_practice_packs() call, not per template.
    _ambiguity_lexeme_cache: dict[tuple[Any, Any], list[dict] | None] = {}

    for path, pack in packs:
        prefix = f"{path}:practice"
        pair = (pack.get("source_language"), pack.get("target_language"))
        if expected_pair is None:
            expected_pair = pair
        elif pair != expected_pair:
            report.error(prefix, f"language pair {pair!r} does not match {expected_pair!r}")

        validate_no_practice_yaml_booleans(pack, report)
        validate_script_purity(
            pack,
            pack.get("target_language"),
            str(path),
            report,
        )
        validate_text_block_directions(pack, str(path), report)

        tag_schema = pack.get("tag_schema", {})
        if not isinstance(tag_schema, dict):
            report.error(f"{prefix}.tag_schema", "must be a mapping")
            tag_schema = {}

        templates = pack.get("templates")
        if not isinstance(templates, list) or not templates:
            report.error(f"{prefix}.templates", "must be a non-empty list")
            continue

        for index, template in enumerate(templates):
            location = f"{prefix}.templates[{index}]"
            if not isinstance(template, dict):
                report.error(location, "must be a mapping")
                continue
            key = template.get("content_key")
            if not isinstance(key, str) or not key.strip():
                report.error(f"{location}.content_key", "must be a non-empty string")
            elif key in seen:
                report.error(
                    f"{location}.content_key",
                    f"duplicate content_key {key!r}; first defined at {seen[key]}",
                )
            else:
                seen[key] = location

            exercise_type = template.get("type")
            if exercise_type not in PRACTICE_EXERCISE_TYPES:
                report.error(
                    f"{location}.type",
                    f"{exercise_type!r} is not supported; must be one of "
                    f"{sorted(PRACTICE_EXERCISE_TYPES)}",
                )

            lesson_key = template.get("lesson_content_key")
            if not isinstance(lesson_key, str) or not lesson_key.strip():
                report.error(
                    f"{location}.lesson_content_key",
                    "must be a non-empty string",
                )
            elif existing_documents and lesson_key not in existing_keys:
                report.error(
                    f"{location}.lesson_content_key",
                    f"references unknown lesson content_key {lesson_key!r}",
                )

            slots = _validate_slot_constraints(
                template.get("slots"),
                tag_schema,
                f"{location}.slots",
                report,
            )
            _validate_frame_slots(
                template.get("frame"),
                slots,
                f"{location}.frame",
                report,
                require_all=False,
            )
            _validate_answer_derivation(
                template.get("answer_derivation"),
                slots,
                f"{location}.answer_derivation",
                report,
            )
            derivation = template.get("answer_derivation", {})
            if exercise_type == "fill_in_blank" and isinstance(derivation, dict):
                if derivation.get("kind") != "slot_text":
                    report.error(
                        f"{location}.answer_derivation.kind",
                        "fill_in_blank requires slot_text so Phase 2 knows which slot to blank",
                    )
                else:
                    frame_text = template.get("frame", {}).get("text", "")
                    placeholder = "{" + str(derivation.get("slot")) + "}"
                    if placeholder not in frame_text:
                        report.error(
                            f"{location}.frame.text",
                            "fill_in_blank answer slot must appear in the frame",
                        )
                    elif not derivation.get("interchangeable"):
                        # AUTHORING_GUIDE.md #17 corpus-wide audit
                        # (2026-07-06/07): a fill_in_blank slot whose real
                        # course-wide candidate pool has >1 distinct token,
                        # with nothing else in the frame able to prefer one
                        # over another, is structurally unanswerable with
                        # certainty -- not a hypothetical, a real shipped
                        # bug ("Ben ___ nieuw hier?" je/jij). Reuses the
                        # exact lexeme_matches() port
                        # scripts/_fill_in_blank_ambiguity_check.py already
                        # verified against the real backend function, so
                        # this can never silently drift from the standalone
                        # audit tool's own judgment.
                        pair_key = (pack.get("source_language"), pack.get("target_language"))
                        if pair_key not in _ambiguity_lexeme_cache:
                            try:
                                _ambiguity_lexeme_cache[pair_key] = _fib_load_lexemes_for_pair(*pair_key)
                            except Exception as exc:  # pragma: no cover - defensive
                                report.warn(
                                    prefix,
                                    f"could not load lexeme data for ambiguity check on {pair_key!r}: {exc!r}",
                                )
                                _ambiguity_lexeme_cache[pair_key] = None
                        lexemes = _ambiguity_lexeme_cache[pair_key]
                        if lexemes is not None:
                            blanked_slot = derivation.get("slot")
                            constraints = slots.get(blanked_slot)
                            if isinstance(constraints, dict):
                                distinct_tokens = {
                                    lx["token"]
                                    for lx in lexemes
                                    if _fib_lexeme_matches(lx, constraints)
                                }
                                if len(distinct_tokens) > 1:
                                    if len(slots) == 1:
                                        report.error(
                                            f"{location}.answer_derivation",
                                            f"fill_in_blank slot {blanked_slot!r} has "
                                            f"{len(distinct_tokens)} distinct candidates "
                                            f"({sorted(distinct_tokens)[:8]}"
                                            f"{'...' if len(distinct_tokens) > 8 else ''}) and no "
                                            "other visible text in the frame to disambiguate which "
                                            "one is correct -- remove the duplicate if a sibling "
                                            "template already tests this vocabulary unambiguously, "
                                            "add real disambiguating context, mark "
                                            "answer_derivation.interchangeable: true if every "
                                            "candidate is a true synonym here, or use a different "
                                            "exercise type (see AUTHORING_GUIDE.md #17)",
                                        )
                                    else:
                                        report.warn(
                                            f"{location}.answer_derivation",
                                            f"fill_in_blank slot {blanked_slot!r} has "
                                            f"{len(distinct_tokens)} distinct candidates with other "
                                            f"visible slot(s) {sorted(s for s in slots if s != blanked_slot)} "
                                            "in the same frame -- confirm by hand whether the other "
                                            "visible slot(s) actually disambiguate the answer before "
                                            "shipping (AUTHORING_GUIDE.md #17); not auto-failed since "
                                            "a second visible slot can legitimately narrow the answer",
                                        )
            if exercise_type == "translation" and isinstance(derivation, dict):
                answer_language = None
                if derivation.get("kind") == "slot_text":
                    answer_slot = slots.get(derivation.get("slot"), {})
                    answer_language = answer_slot.get("language_code")
                elif derivation.get("kind") == "render_frame":
                    answer_language = derivation.get("frame", {}).get("language_code")
                if answer_language != pack.get("target_language"):
                    report.error(
                        f"{location}.answer_derivation",
                        "translation must deterministically produce a target-language answer",
                    )

            relations = template.get("slot_relations", [])
            if not isinstance(relations, list):
                report.error(f"{location}.slot_relations", "must be a list")
            for relation_index, relation in enumerate(relations):
                relation_location = f"{location}.slot_relations[{relation_index}]"
                if not isinstance(relation, dict) or relation.get("kind") not in {"distinct", "same_tag"}:
                    report.error(relation_location, "kind must be distinct or same_tag")
                    continue
                relation_slots = relation.get("slots", [])
                if not isinstance(relation_slots, list) or len(relation_slots) < 2:
                    report.error(f"{relation_location}.slots", "must name at least two slots")
                elif any(slot not in slots for slot in relation_slots):
                    report.error(f"{relation_location}.slots", "references an unknown slot")
                if relation.get("kind") == "same_tag" and not isinstance(relation.get("tag"), str):
                    report.error(f"{relation_location}.tag", "same_tag requires a tag name")
            _validate_frame_slots(
                template.get("feedback_frame"),
                slots,
                f"{location}.feedback_frame",
                report,
                require_all=False,
            )
    return report


def compile_practice_packs(
    packs: list[dict[str, Any]],
) -> dict[str, Any]:
    first = packs[0]
    return {
        "artifact_type": "lingosquared.practice_templates",
        "artifact_version": 1,
        "source_language": first["source_language"],
        "target_language": first["target_language"],
        "packs": [
            {
                "pack_key": pack["pack_key"],
                "unit_content_key": pack["unit_content_key"],
                "tag_schema": copy.deepcopy(pack["tag_schema"]),
                "templates": copy.deepcopy(pack["templates"]),
            }
            for pack in packs
        ],
    }


def validate_untaught_vocabulary(
    realization: dict[str, Any],
    report: Report,
):
    taught: set[str] = set()

    units = realization.get("units", [])
    for unit_index, unit in enumerate(units):
        for lesson_index, lesson in enumerate(unit.get("lessons", [])):
            lesson_location = (
                f"realization.units[{unit_index}].lessons[{lesson_index}]"
            )

            for teaching_index, item in enumerate(
                lesson.get("teaching", [])
            ):
                introduced = item.get("introduced_tokens", [])
                if not isinstance(introduced, list):
                    report.error(
                        f"{lesson_location}.teaching[{teaching_index}]",
                        "introduced_tokens must be a list",
                    )
                    continue
                for token in introduced:
                    if isinstance(token, str):
                        taught.update(tokenize(token))
                    elif isinstance(token, bool):
                        report.error(
                            f"{lesson_location}.teaching[{teaching_index}]"
                            f".introduced_tokens",
                            f"token parsed as YAML boolean {token!r} — likely "
                            "an unquoted Yes/No/True/False/On/Off value; "
                            "quote it as a string in the source YAML",
                        )

            for exercise_index, exercise in enumerate(
                lesson.get("exercises", [])
            ):
                tested_text = exercise.get("tested_text", "")
                if not isinstance(tested_text, str):
                    report.error(
                        f"{lesson_location}.exercises[{exercise_index}]",
                        "tested_text must be a string",
                    )
                    continue

                tested = tokenize(tested_text)
                missing = sorted(tested - taught)
                if missing:
                    report.error(
                        f"{lesson_location}.exercises[{exercise_index}]",
                        "tests tokens not introduced in this or an earlier "
                        f"lesson: {', '.join(missing)}",
                    )


# AUTHORING_GUIDE.md #19: every `kind: vocabulary` teaching card must carry
# at least one real example sentence (`example:` on the realization card,
# `example_gloss:` on the overlay's teaching entry). Enforcement is gated
# per file on `schema_version`: files at >= 1.1 hard-fail a missing
# example; the pre-existing 1.0 corpus only warns until each file's
# retrofit lands (and bumps that file to 1.1). Shape problems in an
# example that IS present are always hard errors regardless of version —
# there is no legacy content with malformed examples to grandfather in.
VOCAB_EXAMPLE_REQUIRED_VERSION = (1, 1)


def schema_version_tuple(document: dict[str, Any]) -> tuple[int, ...]:
    raw = document.get("schema_version")
    if not isinstance(raw, str):
        return (1, 0)
    try:
        return tuple(int(part) for part in raw.strip().split("."))
    except ValueError:
        return (1, 0)


def teaching_example_entries(item: dict[str, Any]) -> list[Any]:
    """Normalize a teaching card's `example:` to a list (it may be a
    single text-block mapping or a list of them)."""
    raw = item.get("example")
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def validate_vocabulary_examples(
    realization: dict[str, Any],
    overlay: dict[str, Any],
    report: Report,
):
    require_example = (
        schema_version_tuple(realization) >= VOCAB_EXAMPLE_REQUIRED_VERSION
    )
    require_gloss = (
        schema_version_tuple(overlay) >= VOCAB_EXAMPLE_REQUIRED_VERSION
    )
    target_language = realization.get("target_language")
    teaching_overlays = overlay.get("teaching")
    if not isinstance(teaching_overlays, dict):
        teaching_overlays = {}

    for unit_index, unit in enumerate(realization.get("units", [])):
        for lesson_index, lesson in enumerate(unit.get("lessons", [])):
            for teaching_index, item in enumerate(
                lesson.get("teaching", [])
            ):
                if not isinstance(item, dict):
                    continue
                location = (
                    f"realization.units[{unit_index}]"
                    f".lessons[{lesson_index}].teaching[{teaching_index}]"
                )
                entries = teaching_example_entries(item)
                content_key = item.get("content_key")
                item_overlay = teaching_overlays.get(content_key)
                if not isinstance(item_overlay, dict):
                    item_overlay = {}

                if not entries:
                    if item_overlay.get("example_gloss") is not None:
                        report.error(
                            f"overlay.teaching.{content_key}.example_gloss",
                            "has an example_gloss but the realization card "
                            "declares no example",
                        )
                    if item.get("kind") == "vocabulary":
                        message = (
                            "vocabulary card has no example sentence "
                            "(AUTHORING_GUIDE.md #19: add `example:` with a "
                            "real sentence using the word, plus "
                            "`example_gloss:` in the overlay)"
                        )
                        if require_example:
                            report.error(location, message)
                        else:
                            report.warn(
                                location,
                                message + " — becomes a hard error once "
                                "this file is retrofitted to "
                                "schema_version 1.1",
                            )
                    continue

                target_text = ""
                target = item.get("target")
                if isinstance(target, dict) and isinstance(
                    target.get("text"), str
                ):
                    target_text = target["text"]

                introduced: set[str] = set()
                raw_tokens = item.get("introduced_tokens", [])
                if isinstance(raw_tokens, list):
                    for token in raw_tokens:
                        if isinstance(token, str):
                            introduced.add(token.casefold().strip())
                            introduced.update(tokenize(token))

                any_token_found = not introduced
                for entry_index, entry in enumerate(entries):
                    entry_location = f"{location}.example[{entry_index}]"
                    if not isinstance(entry, dict) or not isinstance(
                        entry.get("text"), str
                    ) or not entry["text"].strip():
                        report.error(
                            entry_location,
                            "example must be a text-block mapping with "
                            "non-empty text, language_code, and direction",
                        )
                        continue
                    text = entry["text"].strip()
                    if entry.get("language_code") != target_language:
                        report.error(
                            f"{entry_location}.language_code",
                            f"must be the target language "
                            f"{target_language!r}, got "
                            f"{entry.get('language_code')!r}",
                        )
                    if len(text.split()) < 2:
                        report.error(
                            entry_location,
                            "example must be a real sentence with context "
                            "around the word, not another bare word "
                            f"(got {text!r})",
                        )
                    if (
                        target_text
                        and tokenize(text) == tokenize(target_text)
                    ):
                        report.error(
                            entry_location,
                            "example adds no context beyond the card's own "
                            "target text",
                        )
                    example_tokens = tokenize(text)
                    folded_text = text.casefold()
                    if any(
                        token in example_tokens or token in folded_text
                        for token in introduced
                    ):
                        any_token_found = True

                if not any_token_found:
                    report.warn(
                        location,
                        "no example sentence contains any of the card's "
                        "introduced_tokens — fine if the word appears "
                        "inflected, otherwise the example probably doesn't "
                        "demonstrate this card's word",
                    )

                glosses = item_overlay.get("example_gloss")
                if glosses is None:
                    if content_key in teaching_overlays:
                        message = (
                            "card has example sentence(s) but the overlay "
                            "entry has no example_gloss "
                            "(AUTHORING_GUIDE.md #19)"
                        )
                        overlay_location = (
                            f"overlay.teaching.{content_key}"
                        )
                        if require_gloss:
                            report.error(overlay_location, message)
                        else:
                            report.warn(
                                overlay_location,
                                message + " — becomes a hard error once "
                                "this overlay is retrofitted to "
                                "schema_version 1.1",
                            )
                    continue
                gloss_list = (
                    glosses if isinstance(glosses, list) else [glosses]
                )
                if len(gloss_list) != len(entries):
                    report.error(
                        f"overlay.teaching.{content_key}.example_gloss",
                        f"has {len(gloss_list)} gloss(es) for "
                        f"{len(entries)} example sentence(s); counts must "
                        "match positionally",
                    )
                for gloss_index, gloss in enumerate(gloss_list):
                    if not isinstance(gloss, str) or not gloss.strip():
                        report.error(
                            f"overlay.teaching.{content_key}"
                            f".example_gloss[{gloss_index}]",
                            "must be a non-empty string",
                        )


def validate_audio_references(
    realization: dict[str, Any],
    report: Report,
):
    declared = {
        item.get("content_key")
        for item in realization.get("media_assets", [])
        if isinstance(item, dict) and item.get("content_key")
    }

    for location, value in walk(realization, "realization"):
        if not isinstance(value, dict):
            continue
        media_key = value.get("media_asset_key")
        if media_key and media_key not in declared:
            report.warn(
                location,
                f"media asset {media_key!r} is not declared yet; "
                "audio generation is deferred",
            )

    if realization.get("omitted_lessons"):
        report.warn(
            "realization.omitted_lessons",
            "this unit is intentionally partial and is not publication-ready",
        )


def validate_course_consistency(
    realizations: list[tuple[Path, dict[str, Any]]],
    overlays: list[tuple[Path, dict[str, Any]]],
    report: Report,
):
    first_realization_path, first_realization = realizations[0]
    first_overlay_path, first_overlay = overlays[0]

    expected_target_language = first_realization.get("target_language")
    expected_level = first_realization.get("cefr_level")
    expected_source_language = first_overlay.get("source_language")
    expected_title = first_overlay.get("course", {}).get("title")

    for path, realization in realizations[1:]:
        target_language = realization.get("target_language")
        if target_language != expected_target_language:
            report.error(
                f"{path}:target_language",
                f"{target_language!r} does not match "
                f"{expected_target_language!r} from "
                f"{first_realization_path}:target_language",
            )

        level = realization.get("cefr_level")
        if level != expected_level:
            report.error(
                f"{path}:cefr_level",
                f"{level!r} does not match {expected_level!r} from "
                f"{first_realization_path}:cefr_level",
            )

    for path, overlay in overlays[1:]:
        source_language = overlay.get("source_language")
        if source_language != expected_source_language:
            report.error(
                f"{path}:source_language",
                f"{source_language!r} does not match "
                f"{expected_source_language!r} from "
                f"{first_overlay_path}:source_language",
            )

        title = overlay.get("course", {}).get("title")
        if title != expected_title:
            report.error(
                f"{path}:course.title",
                f"{title!r} does not match {expected_title!r} from "
                f"{first_overlay_path}:course.title",
            )


def qualify_pair_message(
    message: str,
    realization_path: Path,
    overlay_path: Path,
) -> str:
    if message.startswith("realization"):
        return f"{realization_path}:{message}"
    if message.startswith("overlay"):
        return f"{overlay_path}:{message}"
    return f"{realization_path} + {overlay_path}: {message}"


def merge_pair_report(
    aggregate: Report,
    pair_report: Report,
    realization_path: Path,
    overlay_path: Path,
):
    aggregate.errors.extend(
        qualify_pair_message(message, realization_path, overlay_path)
        for message in pair_report.errors
    )
    aggregate.warnings.extend(
        qualify_pair_message(message, realization_path, overlay_path)
        for message in pair_report.warnings
    )


def apply_distractor_overrides(
    correct_option: Any,
    distractors: list[Any],
    overrides: dict[str, Any],
) -> list[Any]:
    result = list(distractors)

    for removed in overrides.get("remove", []):
        result = [item for item in result if item != removed]

    replacements = overrides.get("replace", [])
    for replacement in replacements:
        old = replacement.get("from")
        new = replacement.get("to")
        result = [new if item == old else item]

    result.extend(overrides.get("add", []))

    requested_order = overrides.get("order")
    options = [correct_option, *result]

    if requested_order:
        ordered = [item for item in requested_order if item in options]
        ordered.extend(item for item in options if item not in ordered)
        options = ordered

    deduplicated = []
    for option in options:
        if option not in deduplicated:
            deduplicated.append(option)
    return deduplicated


def canonical_response(exercise_overlay: dict[str, Any]) -> Any:
    """Compile an exercise's answer key without changing structured answers.

    Exercises with an explicit correct_response retain that value exactly.
    A single accepted_answers value also retains the historical scalar, list,
    or mapping shape. Multiple accepted variants compile to an internal
    canonical/accepted wrapper used by the grader.

    Variant-specific notes are intentionally not included in the response
    wrapper because the current AnswerOut contract only exposes exercise-level
    feedback. Surfacing per-variant notes would require a separate API change.
    """
    if "correct_response" in exercise_overlay:
        return copy.deepcopy(exercise_overlay["correct_response"])

    variants = exercise_overlay.get("accepted_answers", [])
    if not isinstance(variants, list) or not variants:
        raise ValueError("exercise overlay has no accepted answer")

    accepted = []
    canonical = _MISSING

    for index, variant in enumerate(variants):
        if isinstance(variant, dict):
            if "value" not in variant:
                raise ValueError(
                    f"accepted answer at index {index} has no value"
                )
            status = variant.get("status", "correct")
            if status not in ACCEPTED_VARIANT_STATUSES:
                raise ValueError(
                    f"accepted answer at index {index} has unsupported "
                    f"status {status!r}"
                )
            value = copy.deepcopy(variant["value"])
        else:
            status = "correct"
            value = copy.deepcopy(variant)

        accepted.append(value)
        if status == "correct" and canonical is _MISSING:
            canonical = copy.deepcopy(value)

    if canonical is _MISSING:
        raise ValueError(
            "exercise overlay must have at least one correct accepted answer"
        )

    if len(accepted) == 1:
        return canonical

    return {
        "canonical": canonical,
        "accepted": accepted,
    }


def validate_dialogue_teaching_card(
    card: dict[str, Any],
    content_key: str,
) -> None:
    """Reject legacy single-block dialogue exchanges that break TTS."""
    blocks = card.get("text_blocks", [])
    if card.get("kind") != "dialogue" or len(blocks) != 1:
        return

    block = blocks[0]
    text = block.get("text") if isinstance(block, dict) else None
    if not isinstance(text, str) or "\n" not in text:
        return

    for match in SPEAKER_LABEL_RE.finditer(text):
        label = match.group("label").strip()
        words = label.split()
        if not 1 <= len(words) <= 2:
            continue
        if not all(
            any(character.isalpha() for character in word)
            and all(
                character.isalpha() or character in {"'", "’", "-"}
                for character in word
            )
            for word in words
        ):
            continue

        first_letter = next(
            (character for character in label if character.isalpha()),
            "",
        )
        if first_letter.islower():
            continue

        raise ValueError(
            f"{content_key}: dialogue teaching card must use one "
            "text_block per speaker turn with speaker metadata; embedded "
            "speaker labels and newlines are not allowed"
        )


def compile_teaching_item(
    item: dict[str, Any],
    item_overlay: dict[str, Any],
    source_language: str,
) -> dict[str, Any]:
    target = copy.deepcopy(item["target"])
    validate_dialogue_teaching_card(
        {
            "kind": item["kind"],
            "text_blocks": [target],
        },
        item.get("content_key", "<unknown teaching card>"),
    )
    blocks = [target]

    gloss = item_overlay.get("gloss")
    if gloss:
        blocks.append(
            {
                "text": gloss,
                "language_code": source_language,
                "direction": (
                    "rtl" if source_language in RTL_LANGUAGES else "ltr"
                ),
            }
        )

    compiled = {
        "kind": item["kind"],
        "title": item_overlay.get("title"),
        "text_blocks": blocks,
        "note": item_overlay.get("note"),
        # Additive: lets import_content() match this exact teaching card
        # against an already-shipped row and update it in place.
        "content_key": item["content_key"],
    }

    # AUTHORING_GUIDE.md #19 / CONTRACT.md "Vocabulary-example addition":
    # each realization `example:` entry (a target-language text block)
    # pairs positionally with an overlay `example_gloss:` string to form
    # one compiled example — same two-block shape as the card itself.
    # Only emitted when at least one example exists, so every pre-#19
    # card compiles byte-identical to before (no spurious import churn).
    example_entries = teaching_example_entries(item)
    if example_entries:
        raw_glosses = item_overlay.get("example_gloss")
        if raw_glosses is None:
            glosses: list[Any] = []
        elif isinstance(raw_glosses, list):
            glosses = raw_glosses
        else:
            glosses = [raw_glosses]
        compiled_examples = []
        for index, entry in enumerate(example_entries):
            example_blocks = [copy.deepcopy(entry)]
            gloss = glosses[index] if index < len(glosses) else None
            if isinstance(gloss, str) and gloss.strip():
                example_blocks.append(
                    {
                        "text": gloss,
                        "language_code": source_language,
                        "direction": (
                            "rtl"
                            if source_language in RTL_LANGUAGES
                            else "ltr"
                        ),
                    }
                )
            compiled_examples.append({"text_blocks": example_blocks})
        compiled["examples"] = compiled_examples

    return compiled


def compile_feedback(
    exercise_overlay: dict[str, Any],
    prompt: dict[str, Any],
    content_key: str,
) -> str | None:
    """Compile the overlay's feedback: field plus Phase C's optional
    feedback_by_option/orthography_strict/case_sensitive into
    Exercise.feedback.

    case_sensitive (2026-07-07) is a sibling of orthography_strict, not a
    replacement: orthography_strict only ever controls typo-edit-distance
    tolerance, never case. Added specifically for German, where the
    formal "Sie" (capital, "you" formal) vs lowercase "sie" ("she"/"they")
    is a real grammatical distinction with no equivalent in nl/en/fa/prs
    content authored so far - without this flag, an exercise testing that
    distinction is ungradeable (both the exact-match and the "almost"
    typo-tolerance path would silently treat a wrong-case answer as
    correct or near-correct). Author it per-exercise in the overlay, same
    place as orthography_strict/feedback_by_option.

    Backward compatible: when none of the three optional fields are
    present, returns the bare feedback string (or None) exactly as
    before - a JSON object is only encoded when there is Phase C metadata
    to carry, so every pre-Phase-C overlay compiles identically to
    before."""
    generic = exercise_overlay.get("feedback")
    feedback_by_option = exercise_overlay.get("feedback_by_option")
    orthography_strict = exercise_overlay.get("orthography_strict")
    case_sensitive = exercise_overlay.get("case_sensitive")

    if feedback_by_option is None and orthography_strict is None and case_sensitive is None:
        return generic

    if feedback_by_option is not None:
        if not isinstance(feedback_by_option, dict):
            raise ValueError(
                f"{content_key}.feedback_by_option must be a mapping of "
                "option string to explanation"
            )
        options = prompt.get("options")
        if isinstance(options, list):
            stale = set(feedback_by_option) - set(options)
            if stale:
                raise ValueError(
                    f"{content_key}.feedback_by_option has keys that don't "
                    f"match any option/distractor: {sorted(stale)}"
                )

    payload: dict[str, Any] = {}
    if generic is not None:
        payload["generic"] = generic
    if feedback_by_option is not None:
        payload["feedback_by_option"] = feedback_by_option
    if orthography_strict is not None:
        if not isinstance(orthography_strict, bool):
            raise ValueError(
                f"{content_key}.orthography_strict must be true or false"
            )
        payload["orthography_strict"] = orthography_strict
    if case_sensitive is not None:
        if not isinstance(case_sensitive, bool):
            raise ValueError(
                f"{content_key}.case_sensitive must be true or false"
            )
        payload["case_sensitive"] = case_sensitive

    return json.dumps(payload)


def compile_exercise(
    exercise: dict[str, Any],
    exercise_overlay: dict[str, Any],
    order: int,
    source_language: str,
    target_language: str,
    content_key: str = "",
) -> dict[str, Any]:
    prompt = copy.deepcopy(exercise.get("prompt", {}))
    target_blocks = prompt.pop("target_blocks", [])
    text_blocks = []

    instruction = exercise_overlay.get("instruction")
    if instruction:
        text_blocks.append(
            {
                "text": instruction,
                "language_code": source_language,
                "direction": (
                    "rtl" if source_language in RTL_LANGUAGES else "ltr"
                ),
            }
        )

    text_blocks.extend(target_blocks)
    prompt["text_blocks"] = text_blocks

    if exercise["type"] in {
        "listen_select",
        "listen_type",
        "listen_order",
    }:
        prompt["audio_text"] = exercise["tested_text"]
        prompt["audio_language_code"] = target_language

    if "answer_language_code" in exercise_overlay:
        prompt["answer_language_code"] = exercise_overlay["answer_language_code"]
    else:
        prompt["answer_language_code"] = (
            source_language
            if exercise["type"] == "reverse_translation"
            else target_language
        )

    media_key = exercise.get("media_asset_key")
    if media_key:
        prompt["media_asset_key"] = media_key

    if "correct_option" in exercise_overlay:
        prompt["options"] = apply_distractor_overrides(
            exercise_overlay["correct_option"],
            exercise_overlay.get("distractors", []),
            exercise_overlay.get("distractor_overrides", {}),
        )
    elif "options" in exercise_overlay:
        prompt["options"] = copy.deepcopy(exercise_overlay["options"])

    for field in ("word_bank", "pairs", "back_text_blocks"):
        if field in exercise:
            prompt[field] = copy.deepcopy(exercise[field])

    return {
        "type": exercise["type"],
        "order": order,
        "prompt": prompt,
        "correct_response": canonical_response(exercise_overlay),
        "feedback": compile_feedback(exercise_overlay, prompt, content_key),
        "xp": exercise.get("xp", 10),
        # Additive: lets import_content() match this exact exercise
        # against an already-shipped row and update it in place instead
        # of silently leaving a stale copy forever (the mechanism the
        # already-imported "w_or_v"/"y_or_long_i" jargon-leak bug needed
        # and didn't have).
        "content_key": content_key,
    }


def compile_import_request(
    realization: Any,
    overlay: Any,
) -> dict[str, Any]:
    realizations = realization if isinstance(realization, list) else [realization]
    overlays = overlay if isinstance(overlay, list) else [overlay]

    if len(realizations) != len(overlays):
        raise ValueError(
            "realization and overlay document counts must match; "
            f"got {len(realizations)} realization(s) and "
            f"{len(overlays)} overlay(s)"
        )
    if not realizations:
        raise ValueError("at least one realization/overlay pair is required")

    compiled_units = []

    for realization_document, overlay_document in zip(
        realizations,
        overlays,
    ):
        source_language = overlay_document["source_language"]
        lesson_overlays = overlay_document.get("lessons", {})
        teaching_overlays = overlay_document.get("teaching", {})
        exercise_overlays = overlay_document.get("exercises", {})

        for unit in realization_document.get("units", []):
            compiled_lessons = []

            for lesson_order, lesson in enumerate(
                unit.get("lessons", []),
                1,
            ):
                lesson_key = lesson["content_key"]
                lesson_overlay = lesson_overlays.get(lesson_key, {})

                teaching = [
                    compile_teaching_item(
                        item,
                        teaching_overlays.get(item["content_key"], {}),
                        source_language,
                    )
                    for item in lesson.get("teaching", [])
                ]

                exercises = []
                for exercise_order, exercise in enumerate(
                    lesson.get("exercises", []),
                    1,
                ):
                    key = exercise["content_key"]
                    exercises.append(
                        compile_exercise(
                            exercise,
                            exercise_overlays[key],
                            exercise_order,
                            source_language,
                            realization_document["target_language"],
                            content_key=key,
                        )
                    )

                compiled_lessons.append(
                    {
                        "title": lesson_overlay.get(
                            "title",
                            lesson.get("title", lesson_key),
                        ),
                        "order": lesson_order,
                        "teaching": teaching,
                        "exercises": exercises,
                        # Additive: see the exercise-level content_key comment.
                        "content_key": lesson_key,
                    }
                )

            compiled_units.append(
                {
                    "title": overlay_document.get("units", {}).get(
                        unit["content_key"],
                        {},
                    ).get(
                        "title",
                        unit.get("title", unit["content_key"]),
                    ),
                    "order": len(compiled_units) + 1,
                    "section": unit.get("section", "reading_writing"),
                    "lessons": compiled_lessons,
                    # Additive: see the exercise-level content_key comment.
                    "content_key": unit["content_key"],
                }
            )

    first_realization = realizations[0]
    first_overlay = overlays[0]
    course_overlay = first_overlay.get("course", {})

    return {
        "courses": [
            {
                "source_language": first_overlay["source_language"],
                "target_language": first_realization["target_language"],
                "title": course_overlay["title"],
                "description": course_overlay.get("description", ""),
                "level": first_realization["cefr_level"],
                "units": compiled_units,
                "content_items": [],
            }
        ]
    }


def validate_documents(
    spine: dict[str, Any],
    realization: dict[str, Any],
    overlay: dict[str, Any],
) -> Report:
    report = Report()

    target_language = realization.get("target_language")
    if overlay.get("target_language") != target_language:
        report.error(
            "overlay.target_language",
            "must match realization.target_language",
        )

    validate_content_keys(realization, report)
    validate_unit_sections(realization, report)
    validate_spine_references(spine, realization, report)
    validate_script_purity(
        realization,
        target_language,
        "realization",
        report,
    )
    validate_script_purity(
        overlay,
        target_language,
        "overlay",
        report,
    )
    validate_text_block_directions(realization, "realization", report)
    validate_text_block_directions(overlay, "overlay", report)
    validate_overlay_references(realization, overlay, report)
    validate_no_stray_yaml_booleans(realization, overlay, report)
    validate_same_speaker_dialogue_distractors(realization, overlay, report)
    validate_order_word_bank_answers(realization, overlay, report)
    validate_matching_pairs_minimum_scale(realization, report)
    validate_matching_pairs_overlay_mirror(realization, overlay, report)
    validate_untaught_vocabulary(realization, report)
    validate_vocabulary_examples(realization, overlay, report)
    validate_listen_audio_contains_tested_text(realization, report)
    validate_audio_references(realization, report)

    return report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate or compile layered Lingo² course content."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("validate", "compile"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument(
            "--spine",
            type=Path,
            default=DEFAULT_SPINE,
        )
        subparser.add_argument(
            "--realization",
            type=Path,
            nargs="+",
            required=True,
        )
        subparser.add_argument(
            "--overlay",
            type=Path,
            nargs="+",
            required=True,
        )

        if command == "compile":
            subparser.add_argument(
                "--output",
                type=Path,
                help="Output JSON path. Omit to write JSON to stdout.",
            )

    for command in ("practice-validate", "practice-compile"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--pack", type=Path, nargs="+", required=True)
        subparser.add_argument(
            "--content-root",
            type=Path,
            default=REPO_ROOT / "docs/content/realizations",
            help="Root scanned for existing lesson/exercise content_key collisions.",
        )
        if command == "practice-compile":
            subparser.add_argument(
                "--output",
                type=Path,
                help="Output JSON path. Omit to write JSON to stdout.",
            )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command in {"practice-validate", "practice-compile"}:
        try:
            packs = [(path, load_yaml(path)) for path in args.pack]
            existing = [
                (path, load_yaml(path))
                for path in sorted(args.content_root.rglob("*.yaml"))
            ]
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

        report = validate_practice_packs(packs, existing)
        report.print()
        if report.errors:
            return 1
        if args.command == "practice-validate":
            return 0

        compiled = compile_practice_packs([document for _, document in packs])
        rendered = json.dumps(compiled, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0

    if len(args.realization) != len(args.overlay):
        print(
            "ERROR: --realization and --overlay require the same number "
            f"of paths; got {len(args.realization)} realization path(s) "
            f"and {len(args.overlay)} overlay path(s).",
            file=sys.stderr,
        )
        return 2

    try:
        spine = load_yaml(args.spine)
        realization_documents = [
            (path, load_yaml(path))
            for path in args.realization
        ]
        overlay_documents = [
            (path, load_yaml(path))
            for path in args.overlay
        ]
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = Report()

    for (
        realization_path,
        realization,
    ), (
        overlay_path,
        overlay,
    ) in zip(realization_documents, overlay_documents):
        pair_report = validate_documents(
            spine,
            realization,
            overlay,
        )
        merge_pair_report(
            report,
            pair_report,
            realization_path,
            overlay_path,
        )

    validate_global_content_keys(realization_documents, report)
    validate_course_consistency(
        realization_documents,
        overlay_documents,
        report,
    )

    report.print()

    if report.errors:
        return 1

    if args.command == "validate":
        return 0

    try:
        compiled = compile_import_request(
            [document for _, document in realization_documents],
            [document for _, document in overlay_documents],
        )
    except (KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: compilation failed: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(
        compiled,
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
