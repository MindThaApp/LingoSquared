#!/usr/bin/env python3
"""Audit matching-pairs answers taught only later in the same unit.

This is deliberately a standalone, warning-level corpus check: the corpus
contains known instances, so it must not make content compilation fail.

Usage:
    .content-venv/bin/python3 scripts/_matching_pairs_forward_reference_check.py
"""
from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
REALIZATIONS_DIR = REPO_ROOT / "docs/content/realizations"
WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)


@dataclass(frozen=True)
class Introduction:
    value: str
    normalized: str
    lesson_index: int
    lesson_key: str


@dataclass(frozen=True)
class Violation:
    path: Path
    unit_key: str
    lesson_key: str
    exercise_key: str
    right: str
    taught_lesson_key: str


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("’", "'")
    return " ".join(WORD_RE.findall(value))


def _introduced(lesson: dict[str, Any], lesson_index: int) -> list[Introduction]:
    lesson_key = str(lesson.get("content_key", f"<lesson {lesson_index + 1}>"))
    result: list[Introduction] = []
    cards: list[tuple[dict[str, Any], list[str]]] = []
    lesson_words: set[str] = set()
    for card in lesson.get("teaching", []) or []:
        if not isinstance(card, dict):
            continue
        card_values: list[str] = []
        for value in card.get("introduced_tokens", []) or []:
            if isinstance(value, str) and (normalized := _normalize(value)):
                result.append(Introduction(value, normalized, lesson_index, lesson_key))
                card_values.extend(normalized.split())
                lesson_words.update(normalized.split())
        cards.append((card, card_values))

    for card, card_values in cards:
        # introduced_tokens are commonly stored as individual words even
        # when the teaching card introduces a phrase. Reconstruct only
        # contiguous phrases actually present in a teaching target. Words
        # may be de-duplicated from one card because another card in the
        # same lesson already introduces them.
        target = card.get("target")
        target_text = target.get("text") if isinstance(target, dict) else None
        if isinstance(target_text, str):
            words = _normalize(target_text).split()
            introduced_words = set(card_values) | lesson_words
            for start in range(len(words)):
                for end in range(start + 2, min(len(words), start + 8) + 1):
                    phrase_words = words[start:end]
                    if all(word in introduced_words for word in phrase_words):
                        phrase = " ".join(phrase_words)
                        result.append(
                            Introduction(phrase, phrase, lesson_index, lesson_key)
                        )
    return result


def _english_stems(word: str) -> set[str]:
    """Return deliberately broad possible stems; ambiguity suppresses warnings."""
    stems = {word}
    if len(word) > 3 and word.endswith("s"):
        stems.add(word[:-1])
    if len(word) > 4 and word.endswith("es"):
        stems.add(word[:-2])
    if len(word) > 4 and word.endswith("ies"):
        stems.add(word[:-3] + "y")
    if len(word) > 4 and word.endswith("ed"):
        stems.update((word[:-2], word[:-1]))
    if len(word) > 5 and word.endswith("ing"):
        stems.update((word[:-3], word[:-3] + "e"))
    if len(word) > 4 and word.endswith("er"):
        stems.update((word[:-2], word[:-1]))
    if len(word) > 5 and word.endswith("est"):
        stems.update((word[:-3], word[:-2]))
    if len(word) > 4 and word[-1] == word[-2]:
        stems.add(word[:-1])
    return {stem for stem in stems if len(stem) >= 3}


def _possibly_inflected_match(left: str, right: str, language: str) -> bool:
    if left == right:
        return True
    left_words = left.split()
    right_words = right.split()
    if len(left_words) != len(right_words):
        return False
    if language != "en":
        return False
    return all(
        bool(_english_stems(a) & _english_stems(b))
        for a, b in zip(left_words, right_words)
    )


def find_violations() -> list[Violation]:
    documents: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(REALIZATIONS_DIR.glob("*/*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(document, dict):
            documents.append((path, document))

    violations: list[Violation] = []
    for path, document in documents:
        language = str(document.get("target_language", ""))
        prior_unit_values: list[str] = []
        for unit in document.get("units", []) or []:
            if not isinstance(unit, dict):
                continue
            unit_key = str(unit.get("content_key", "<no unit content_key>"))
            lessons = unit.get("lessons", []) or []
            introductions = [
                intro
                for lesson_index, lesson in enumerate(lessons)
                if isinstance(lesson, dict)
                for intro in _introduced(lesson, lesson_index)
            ]
            for lesson_index, lesson in enumerate(lessons):
                if not isinstance(lesson, dict):
                    continue
                lesson_key = str(
                    lesson.get("content_key", f"<lesson {lesson_index + 1}>")
                )
                taught_so_far = [
                    intro.normalized
                    for intro in introductions
                    if intro.lesson_index <= lesson_index
                ]
                for exercise in lesson.get("exercises", []) or []:
                    if not isinstance(exercise, dict) or exercise.get("type") != "matching_pairs":
                        continue
                    exercise_key = str(
                        exercise.get("content_key", "<no exercise content_key>")
                    )
                    for pair in exercise.get("pairs", []) or []:
                        if not isinstance(pair, dict) or not isinstance(pair.get("right"), str):
                            continue
                        right = pair["right"]
                        normalized = _normalize(right)
                        later = [
                            intro
                            for intro in introductions
                            if intro.lesson_index > lesson_index
                            and intro.normalized == normalized
                        ]
                        if not normalized or not later:
                            continue
                        if any(
                            _possibly_inflected_match(normalized, taught, language)
                            for taught in taught_so_far + prior_unit_values
                        ):
                            continue
                        first_later = min(later, key=lambda intro: intro.lesson_index)
                        violations.append(
                            Violation(
                                path.relative_to(REPO_ROOT),
                                unit_key,
                                lesson_key,
                                exercise_key,
                                right,
                                first_later.lesson_key,
                            )
                        )
            prior_unit_values.extend(
                intro.normalized for intro in introductions
            )
    return violations


def main() -> int:
    violations = find_violations()
    for item in violations:
        print(
            "WARN: "
            f"{item.path}: unit={item.unit_key} lesson={item.lesson_key} "
            f"exercise={item.exercise_key} right={item.right!r} "
            f"first_taught_in={item.taught_lesson_key}"
        )
    print(f"Matching-pairs forward-reference check: {len(violations)} violation(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
