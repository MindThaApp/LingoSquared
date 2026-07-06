"""Phase C: typo tolerance ("almost") and script-confusion detection.

Kept as pure functions (no DB access) so callers resolve any DB-backed
context (e.g. a language's script) themselves and pass it in - see
app/api/router.py's exercise_answer()/review_answer()/practice_answer().
"""
from typing import Literal

Result = Literal["correct", "almost", "incorrect"]

# Exercise types whose correct_response is free-typed text compared against
# what the learner typed. fill_in_blank and listen_order are deliberately
# excluded here even though they sometimes carry a plain-string answer -
# callers must check the actual correct_response shape for those two typez
# (a list/pair-mapping there means "choice-like", not free text) rather than
# treat them as free text purely by exercise-type name.
FREE_TEXT_EXERCISE_TYPES = {
    "translation",
    "reverse_translation",
    "writing_prompt",
    "dialogue_response",
    "listen_type",
    "grammar_check",
    # STT transcripts (speak_response/speak_repeat, added 2026-07-06) are
    # free-typed text same as any other free-text answer, just produced by
    # transcription instead of a keyboard — belongs in the same typo-
    # tolerant bucket as dialogue_response/translation. This matters more
    # here than elsewhere: STT introduces its own transcription noise on
    # top of normal typing variance, so the distance-1 tolerance genuinely
    # helps avoid marking a correctly-spoken answer wrong over something
    # like a dropped accent or a missing period.
    "speak_response",
    "speak_repeat",
}

# Exercise types that are always choice/selection-based and must never
# produce "almost" - a wrong option is simply incorrect.
CHOICE_EXERCISE_TYPES = {
    "multiple_choice",
    "matching_pairs",
    "word_order",
    "listen_select",
}

# Arabic-vs-Persian letter pairs that must never be silently forgiven as a
# typo, even at edit-distance 1, because the distinction is frequently the
# content being tested. Each pair is a frozenset of the two codepoints that
# are considered "the same shape, wrong script" for each other.
ARABIC_PERSIAN_SCRIPT_PAIRS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"ي", "ی"}),  # Arabic yeh ي vs Persian yeh ی
        frozenset({"ك", "ک"}),  # Arabic kaf ك vs Persian keheh ک
        frozenset({"ة", "ه"}),  # Arabic teh marbuta ة vs heh ه
        frozenset({"ۀ", "ه"}),  # Urdu-style heh goal ۀ-related vs heh ه
        frozenset({"ى", "ی"}),  # Arabic alef maksura ى vs Persian yeh ی
    }
)

LATIN_RANGE_STARTS = (0x0041, 0x0061, 0x00C0, 0x0100)


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def is_latin_script_text(value: str) -> bool:
    """True if every alphabetic character in value is in the Latin script.

    Used only as a fallback when the caller has no authoritative
    Language.script value to pass in (see grade_answer's script param).
    """
    has_alpha = False
    for ch in value:
        if not ch.isalpha():
            continue
        has_alpha = True
        code = ord(ch)
        if not (
            0x0041 <= code <= 0x024F  # basic Latin + Latin-1 supp + extended-A/B
            or 0x1E00 <= code <= 0x1EFF  # Latin extended additional
        ):
            return False
    return has_alpha


def damerau_levenshtein(a: str, b: str) -> int:
    """Optimal-string-alignment Damerau-Levenshtein distance (insert, delete,
    substitute, or transpose of adjacent characters, each cost 1)."""
    if a == b:
        return 0
    len_a, len_b = len(a), len(b)
    if len_a == 0:
        return len_b
    if len_b == 0:
        return len_a

    d = [[0] * (len_b + 1) for _ in range(len_a + 1)]
    for i in range(len_a + 1):
        d[i][0] = i
    for j in range(len_b + 1):
        d[0][j] = j

    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,  # deletion
                d[i][j - 1] + 1,  # insertion
                d[i - 1][j - 1] + cost,  # substitution
            )
            if (
                i > 1
                and j > 1
                and a[i - 1] == b[j - 2]
                and a[i - 2] == b[j - 1]
            ):
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + cost)  # transposition

    return d[len_a][len_b]


def _single_substitution_pair(a: str, b: str) -> tuple[str, str] | None:
    """If a and b are the same length and differ in exactly one position,
    return the differing (a_char, b_char) pair; otherwise None."""
    if len(a) != len(b):
        return None
    diffs = [(x, y) for x, y in zip(a, b) if x != y]
    if len(diffs) != 1:
        return None
    return diffs[0]


def is_script_confusion(a: str, b: str) -> bool:
    """True if a and b differ by exactly one character that is an
    Arabic/Persian script-purity pair - never a forgivable typo."""
    pair = _single_substitution_pair(a, b)
    if pair is None:
        return False
    candidate = frozenset(pair)
    return candidate in ARABIC_PERSIAN_SCRIPT_PAIRS


def grade_answer(
    response: str,
    correct: str,
    *,
    exercise_type: str,
    script: str | None = None,
    orthography_strict: bool | None = None,
) -> Result:
    """Grade one free-text answer into correct/almost/incorrect.

    - exercise_type outside FREE_TEXT_EXERCISE_TYPES always returns
      "correct"/"incorrect" (never "almost") - callers should not even
      call this for choice-type exercises, but it's enforced here too as
      a safety net.
    - script is the target Language.script value ('latin'|'cyrillic'|
      'han'|'arabic') for the *correct* answer, resolved by the caller
      from the Language table. Default strictness: tolerant for 'latin',
      strict for everything else (in particular 'arabic', which covers
      fa/prs). Falls back to a character-based Latin heuristic if the
      caller has no script value handy.
    - orthography_strict, when not None, overrides the script-based
      default in either direction (author-set per exercise).
    - A single-character substitution that crosses an Arabic/Persian
      script-purity boundary (e.g. Arabic kaf vs Persian keheh) is never
      treated as an "almost" typo, regardless of strictness settings.
    """
    normalized_response = _normalize(response)
    normalized_correct = _normalize(correct)

    if normalized_response == normalized_correct:
        return "correct"

    if exercise_type not in FREE_TEXT_EXERCISE_TYPES:
        return "incorrect"

    if is_script_confusion(normalized_response, normalized_correct):
        return "incorrect"

    if orthography_strict is True:
        return "incorrect"
    if orthography_strict is False:
        tolerant = True
    elif script is not None:
        tolerant = script == "latin"
    else:
        tolerant = is_latin_script_text(normalized_correct)

    if not tolerant:
        return "incorrect"

    if damerau_levenshtein(normalized_response, normalized_correct) == 1:
        return "almost"

    return "incorrect"
