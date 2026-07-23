#!/usr/bin/env python3
"""Audit phantom ``introduced_tokens`` that later exercises require.

This is deliberately a standalone, warning-level corpus check.  It does not
participate in content compilation.

Usage:
    .content-venv/bin/python3 scripts/_phantom_introduced_tokens_check.py
"""
from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
REALIZATIONS_DIR = REPO_ROOT / "docs/content/realizations"
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
CYRILLIC_RE = re.compile(r"[\u0400-\u052f]")
PRODUCTION_EXERCISE_TYPES = {
    "writing_prompt",
    "speak_response",
    "translation",
    "word_order",
    "fill_in_blank",
}
PRODUCTION_KEY_VERBS = (
    "writing_prompt",
    "speak_",
    "translation",
    "translate_",
    "word_order",
    "order_",
    "fill_in_blank",
    "fill_",
    "write_",
)


@dataclass(frozen=True)
class Phantom:
    path: Path
    unit_key: str
    card_key: str
    token: str
    lesson_index: int


@dataclass(frozen=True)
class ExerciseUse:
    lesson_index: int
    exercise_key: str
    field: str


@dataclass(frozen=True)
class Violation:
    phantom: Phantom
    use: ExerciseUse


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(
        character
        for character in value
        if unicodedata.category(character) != "Mn" and character != "\u0640"
    )
    # Treat Arabic/Persian orthographic variants and joiners as equivalent.
    value = value.translate(
        str.maketrans(
            {
                "ي": "ی",
                "ى": "ی",
                "ك": "ک",
                "ة": "ه",
                "ۀ": "ه",
                "ؤ": "و",
                "ئ": "ی",
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "\u200c": "",
                "\u200d": "",
            }
        )
    )
    return " ".join(WORD_RE.findall(value))


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        # Structured localized values put their surface form in ``text``.
        if isinstance(value.get("text"), str):
            yield value["text"]
        else:
            for item in value.values():
                yield from _strings(item)


def _words(values: Iterable[str]) -> list[str]:
    return [
        word
        for value in values
        for word in _normalize(value).split()
    ]


def _latin_stems(word: str) -> set[str]:
    """Broad suffix removal: ambiguity intentionally suppresses warnings."""
    stems = {word}
    suffixes = (
        "issements", "issement", "ations", "ation", "ements", "ement",
        "mente", "mente", "ingly", "ies", "ing", "ées", "ée", "es", "ed",
        "er", "est", "en", "e", "s",
    )
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            stems.add(word[:-len(suffix)])
    return stems


def _word_variant(left: str, right: str) -> bool:
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    if len(shorter) >= 3 and shorter in longer:
        return True

    if ARABIC_RE.search(left + right):
        # Persian/Arabic inflection is often affixal.  A short common beginning
        # is intentionally enough to suppress a warning (کنم/کنیم, for
        # example); false positives are worse than missed defects in this
        # warning-level audit.
        prefix = len(shorter)
        for index, (a, b) in enumerate(zip(shorter, longer)):
            if a != b:
                prefix = index
                break
        return prefix >= 2 and len(shorter) >= 3

    if CYRILLIC_RE.search(left + right):
        # Three stable initial letters conservatively cover common Russian
        # nominal/adjectival paradigms (e.g. нужен/нужны).
        prefix = len(shorter)
        for index, (a, b) in enumerate(zip(shorter, longer)):
            if a != b:
                prefix = index
                break
        return prefix >= 3 and len(shorter) >= 4

    if _latin_stems(left) & _latin_stems(right):
        return True
    prefix = len(shorter)
    for index, (a, b) in enumerate(zip(shorter, longer)):
        if a != b:
            prefix = index
            break
    # This intentionally accepts a wide family resemblance (lernen/lernt,
    # quiero/quiere, etc.).  The check is an audit for obvious phantoms, not a
    # language-specific lemmatizer.
    return prefix >= 3 and len(shorter) >= 4


def _surface_appears(token: str, surfaces: Iterable[str]) -> bool:
    return _surface_words_appear(token, _words(surfaces))


def _surface_words_appear(token: str, surface_words: Iterable[str]) -> bool:
    token_words = _normalize(token).split()
    surface_words = set(surface_words)
    if not token_words or not surface_words:
        return False
    # Phrase metadata is considered supported if every component has a surface
    # realization.  Requiring adjacency would create false positives for
    # naturally reordered or inflected phrases.
    return all(
        any(_word_variant(token_word, surface_word) for surface_word in surface_words)
        for token_word in token_words
    )


def _is_capitalized_name(token: str) -> bool:
    """Treat a capitalized single token as a likely proper noun/name."""
    words = WORD_RE.findall(unicodedata.normalize("NFKD", token))
    if len(words) != 1:
        return False
    first_cased = next(
        (character for character in words[0] if character.lower() != character.upper()),
        None,
    )
    return first_cased is not None and first_cased.isupper()


def _is_dialogue_card(card: dict[str, Any]) -> bool:
    key = str(card.get("content_key", "")).casefold()
    return (
        str(card.get("kind", "")).casefold() == "dialogue"
        or ".teach.turn" in key
        or "dialogue_line" in key
    )


def _is_production_exercise(exercise: dict[str, Any]) -> bool:
    exercise_type = exercise.get("type")
    if isinstance(exercise_type, str) and exercise_type.strip():
        normalized_type = exercise_type.strip().casefold()
        return (
            normalized_type in PRODUCTION_EXERCISE_TYPES
            or normalized_type.startswith(("speak_", "translate_", "order_", "fill_", "write_"))
        )

    key_parts = re.split(r"[.\-]", str(exercise.get("content_key", "")).casefold())
    verb = key_parts[-1] if key_parts else ""
    return verb.startswith(PRODUCTION_KEY_VERBS)


def _exercise_uses(exercise: dict[str, Any], token: str) -> str | None:
    if not _is_production_exercise(exercise):
        return None
    for field in ("tested_text", "accepted_answers", "word_bank"):
        if _surface_appears(token, _strings(exercise.get(field))):
            return field
    return None


def find_results() -> tuple[list[Violation], list[Phantom]]:
    violations: list[Violation] = []
    metadata_only: list[Phantom] = []
    for path in sorted(REALIZATIONS_DIR.glob("*/*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            continue
        for unit in document.get("units", []) or []:
            if not isinstance(unit, dict):
                continue
            unit_key = str(unit.get("content_key", "<no unit content_key>"))
            lessons = unit.get("lessons", []) or []
            taught_surface_words = {
                word
                for lesson in lessons
                if isinstance(lesson, dict)
                for card in lesson.get("teaching", []) or []
                if isinstance(card, dict)
                for word in _words(
                    (
                        *_strings(card.get("target")),
                        *_strings(card.get("example")),
                    )
                )
            }
            exercises: list[tuple[int, dict[str, Any]]] = [
                (lesson_index, exercise)
                for lesson_index, lesson in enumerate(lessons)
                if isinstance(lesson, dict)
                for exercise in lesson.get("exercises", []) or []
                if isinstance(exercise, dict)
            ]
            token_card_provenance: dict[str, list[dict[str, Any]]] = {}
            for lesson in lessons:
                if not isinstance(lesson, dict):
                    continue
                for card in lesson.get("teaching", []) or []:
                    if not isinstance(card, dict):
                        continue
                    for token in card.get("introduced_tokens", []) or []:
                        if isinstance(token, str):
                            token_card_provenance.setdefault(_normalize(token), []).append(card)
            for lesson_index, lesson in enumerate(lessons):
                if not isinstance(lesson, dict):
                    continue
                for card_index, card in enumerate(lesson.get("teaching", []) or []):
                    if not isinstance(card, dict):
                        continue
                    card_key = str(
                        card.get("content_key", f"<card {card_index + 1}>")
                    )
                    for token in card.get("introduced_tokens", []) or []:
                        provenance = token_card_provenance.get(
                            _normalize(token) if isinstance(token, str) else "",
                            [],
                        )
                        if (
                            not isinstance(token, str)
                            or _is_capitalized_name(token)
                            or (
                                provenance
                                and all(_is_dialogue_card(item) for item in provenance)
                                and not any(
                                    str(item.get("kind", "")).casefold()
                                    in {"vocabulary", "phrase"}
                                    for item in provenance
                                )
                            )
                            or _surface_words_appear(token, taught_surface_words)
                        ):
                            continue
                        phantom = Phantom(
                            path.relative_to(REPO_ROOT),
                            unit_key,
                            card_key,
                            token,
                            lesson_index,
                        )
                        later_use = None
                        for exercise_lesson_index, exercise in exercises:
                            if exercise_lesson_index < lesson_index:
                                continue
                            field = _exercise_uses(exercise, token)
                            if field is not None:
                                later_use = ExerciseUse(
                                    exercise_lesson_index,
                                    str(
                                        exercise.get(
                                            "content_key",
                                            "<no exercise content_key>",
                                        )
                                    ),
                                    field,
                                )
                                break
                        if later_use is None:
                            metadata_only.append(phantom)
                        else:
                            violations.append(Violation(phantom, later_use))
    return violations, metadata_only


def main() -> int:
    violations, metadata_only = find_results()
    for item in violations:
        phantom = item.phantom
        print(
            "WARN: "
            f"{phantom.path}: unit={phantom.unit_key} card={phantom.card_key} "
            f"phantom_token={phantom.token!r} "
            f"later_exercise={item.use.exercise_key} field={item.use.field}"
        )
    for item in metadata_only:
        print(
            "NOTE: "
            f"{item.path}: unit={item.unit_key} card={item.card_key} "
            f"phantom_token={item.token!r} later_exercise=<none>"
        )
    print(
        "Phantom introduced_tokens check: "
        f"{len(violations)} violation(s), "
        f"{len(metadata_only)} metadata-only note(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
