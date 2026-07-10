"""Grading: the single module for answer grading across every answer
endpoint (lesson exercises, legacy SM-2 reviews, practice/review/checkpoint
PracticeItems).

Originally Phase C's typo tolerance ("almost") and script-confusion
detection only; the exercise-level grading layer (normalized(),
canonical_pairs(), canonical_order_tokens(), grade(), decode_feedback(),
etc.) was moved here verbatim from app/api/router.py on 2026-07-10 so
grading truth lives in one file instead of being split between this
module and the router.

Kept as pure functions (no DB access) so callers resolve any DB-backed
context (e.g. a language's script) themselves and pass it in - see
app/api/router.py's exercise_answer()/review_answer()/practice_answer()
(resolve_script() stays in the router for exactly that reason).
"""
import json
from typing import Literal

from app.core.errors import fail
from app.models import ExerciseType

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


def _normalize(value: str, *, case_sensitive: bool = False) -> str:
    folded = value if case_sensitive else value.casefold()
    return " ".join(folded.strip().split())


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


def is_case_only_difference(a: str, b: str) -> bool:
    """True if a and b are genuinely different strings that would compare
    equal under casefold - i.e. the ONLY thing wrong is letter case.

    Used so a case_sensitive exercise (2026-07-07, added for German's
    formal "Sie" vs lowercase "sie"/"they" - a real grammatical
    distinction with no equivalent in any language this project shipped
    before, unlike Dutch/English/Farsi/Dari where case never carries
    meaning) never forgives a case-only mismatch as a distance-1 typo -
    same "hard-block before the typo-tolerance check" shape as
    is_script_confusion() above, just keyed on casefold-equality instead
    of a fixed script-pair table, since ANY casing slip (not just a
    single character) is the exact thing case_sensitive exists to catch."""
    return a != b and a.casefold() == b.casefold()


def grade_answer(
    response: str,
    correct: str,
    *,
    exercise_type: str,
    script: str | None = None,
    orthography_strict: bool | None = None,
    case_sensitive: bool = False,
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
    - case_sensitive (author-set per exercise, same feedback_meta blob as
      orthography_strict), when True, compares without casefolding and
      never forgives a case-only mismatch (e.g. "sie" vs "Sie") as a
      distance-1 typo either - both the exact-match and the almost-typo
      paths respect it. Defaults to False (the historical always-
      casefold behavior) so every exercise that doesn't opt in keeps
      grading exactly as before.
    """
    normalized_response = _normalize(response, case_sensitive=case_sensitive)
    normalized_correct = _normalize(correct, case_sensitive=case_sensitive)

    if normalized_response == normalized_correct:
        return "correct"

    if exercise_type not in FREE_TEXT_EXERCISE_TYPES:
        return "incorrect"

    if is_script_confusion(normalized_response, normalized_correct):
        return "incorrect"

    if case_sensitive and is_case_only_difference(
        normalized_response, normalized_correct
    ):
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


# ---------------------------------------------------------------------------
# Exercise-level grading, moved verbatim from app/api/router.py (2026-07-10).
# ---------------------------------------------------------------------------
def normalized(v,case_sensitive=False):
    """Collapse whitespace and (unless case_sensitive) casefold, recursively
    for list/dict values. case_sensitive is a 2026-07-07 addition (German's
    formal "Sie" vs lowercase "sie"/"they" - a real grammatical distinction
    with no equivalent in any language shipped before, unlike Dutch/
    English/Farsi/Dari) - defaults to False so every existing call site
    (and every exercise that hasn't opted in) keeps casefolding exactly as
    before."""
    if isinstance(v,str):
        s = v.strip() if case_sensitive else v.strip().casefold()
        return " ".join(s.split())
    if isinstance(v,list): return [normalized(x,case_sensitive) for x in v]
    if isinstance(v,dict): return {str(k):normalized(x,case_sensitive) for k,x in sorted(v.items())}
    return v
def is_multi_answer_response(correct):
    return (
        isinstance(correct,dict)
        and set(correct)=={"canonical","accepted"}
        and isinstance(correct["accepted"],list)
    )
def canonical_pairs(value,case_sensitive=False):
    """Canonicalize a matching_pairs answer into an order-independent set of
    (left,right) tuples, regardless of representation. CONTRACT.md documents
    the submitted `response` as a flat {left: right} pair-mapping (what
    MatchingPairs.tsx sends and what the Endless Practice engine's
    derive_answer() produces), but hand-authored lesson content's
    accepted_answers/correct_response has historically been written as a
    list of {"left":...,"right":...} objects instead (matching the prompt's
    `pairs` display shape) - a real mismatch that made every compiled
    matching_pairs exercise ungradeable-correct regardless of what the
    learner picked. Accept either shape here so both compare equal."""
    if isinstance(value, dict):
        return frozenset((normalized(k,case_sensitive), normalized(v,case_sensitive)) for k, v in value.items())
    if isinstance(value, list) and all(
        isinstance(item, dict) and {"left", "right"} <= set(item) for item in value
    ):
        return frozenset((normalized(item["left"],case_sensitive), normalized(item["right"],case_sensitive)) for item in value)
    return None
ORDER_BASED_EXERCISE_TYPES = {"word_order", "listen_order"}
def canonical_order_tokens(value,case_sensitive=False):
    """Canonicalize a word_order/listen_order answer into a token list,
    regardless of whether it was authored as a single space-joined string
    (the majority pattern across hand-authored content - e.g. correct_
    response "Hallo met Omar") or as an explicit token list matching the
    prompt's word_bank order (e.g. ["Hallo","met","Omar"], the shape the
    Endless Practice engine's derive_answer() always produces for this
    type). WordOrder.tsx always submits `response` as a list built purely
    from tile-click order, never a string - so a plain joined-string
    correct_response could never equal it, marking every token-for-token,
    correctly-ordered submission wrong regardless of what was actually
    clicked (found live 2026-07-07 from a real user report: "Hallo met
    Omar" tiles clicked in the exact right order still graded incorrect).
    Same class of authored-shape-vs-submitted-shape mismatch as
    canonical_pairs()/matching_pairs above. Splitting the string on
    whitespace (after casefolding/stripping via normalized()) also keeps
    any punctuation attached to a token - e.g. a hypothetical "Hallo,"
    tile - comparing correctly against a same-shaped correct string,
    since both sides go through the identical split, not a separate
    punctuation-stripping step."""
    if isinstance(value, str):
        collapsed = normalized(value,case_sensitive)
        return collapsed.split(" ") if collapsed else []
    if isinstance(value, list):
        return normalized(value,case_sensitive)
    return None
def display_correct_response(correct):
    if is_multi_answer_response(correct):
        return correct["canonical"]
    return correct
def decode_feedback(raw):
    """Decode Exercise.feedback. Phase C stores an optional JSON object
    ({"generic","feedback_by_option","orthography_strict","case_sensitive"})
    in the same Text column that historically held a bare feedback string -
    decode defensively so every pre-Phase-C row (plain string or None) keeps
    behaving exactly as before. case_sensitive (2026-07-07) is a sibling of
    orthography_strict, not a replacement - orthography_strict only ever
    controlled typo-edit-distance tolerance and never affected case, which
    is why German's formal "Sie" vs lowercase "sie"/"they" (a real
    grammatical distinction with no equivalent in nl/en/fa/prs) needed its
    own opt-in flag instead."""
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except (ValueError, TypeError):
        return {"generic": raw}
    if not isinstance(decoded, dict):
        return {"generic": raw}
    return decoded
def select_feedback(feedback_meta, response, result):
    if result != "correct":
        by_option = feedback_meta.get("feedback_by_option") or {}
        if isinstance(response, str) and response in by_option:
            return by_option[response]
    return feedback_meta.get("generic")
def exercise_type_value(exercise_type):
    return exercise_type.value if hasattr(exercise_type, "value") else exercise_type
def grade(response,correct,exercise_type=None,*,script=None,orthography_strict=None,case_sensitive=False):
    """Returns the 3-state result: 'correct' | 'almost' | 'incorrect'.
    'almost' (Phase C typo tolerance) is only ever returned for free-typed
    answers on eligible exercise types - flashcard, multi-answer, and
    choice-type grading below always resolve straight to correct/incorrect.
    case_sensitive (2026-07-07, author-set per exercise via feedback_meta,
    same as orthography_strict) skips casefolding everywhere in this
    function and never lets a case-only mismatch through as "almost" via
    grade_answer() - defaults to False so every exercise that hasn't opted
    in keeps grading exactly as before."""
    if exercise_type == ExerciseType.flashcard:
        report=normalized(response)
        if not isinstance(report,str) or report not in {"known","unknown"}:
            fail(422,"invalid_flashcard_response","Flashcard response must be 'known' or 'unknown'")
        return "correct" if report == "known" else "incorrect"
    type_value = exercise_type_value(exercise_type)
    order_based = type_value in ORDER_BASED_EXERCISE_TYPES
    if is_multi_answer_response(correct):
        if order_based:
            response_tokens = canonical_order_tokens(response,case_sensitive)
            is_ok = response_tokens is not None and any(
                response_tokens == canonical_order_tokens(item,case_sensitive) for item in correct["accepted"]
            )
        else:
            normalized_response=normalized(response,case_sensitive)
            is_ok = any(normalized_response==normalized(item,case_sensitive) for item in correct["accepted"])
        return "correct" if is_ok else "incorrect"
    free_text_eligible = (
        type_value in FREE_TEXT_EXERCISE_TYPES
        or type_value in {"fill_in_blank", "listen_order"}
    )
    if free_text_eligible and isinstance(response, str) and isinstance(correct, str):
        return grade_answer(
            response,
            correct,
            exercise_type=type_value,
            script=script,
            orthography_strict=orthography_strict,
            case_sensitive=case_sensitive,
        )
    if type_value == "matching_pairs":
        correct_pairs = canonical_pairs(correct,case_sensitive)
        if correct_pairs is not None:
            return "correct" if canonical_pairs(response,case_sensitive) == correct_pairs else "incorrect"
    if order_based:
        # word_order/listen_order's `response` is always a list (WordOrder.
        # tsx submits tile-click order), but hand-authored correct_response
        # is very often authored as a plain joined string instead of a
        # token list matching word_bank - canonicalize both shapes into
        # comparable token lists rather than picking one shape as
        # authoritative (same pattern as canonical_pairs() above for
        # matching_pairs). Falls through to the generic comparison below
        # only if canonicalization can't apply (neither string nor list).
        correct_tokens = canonical_order_tokens(correct,case_sensitive)
        if correct_tokens is not None:
            return "correct" if canonical_order_tokens(response,case_sensitive) == correct_tokens else "incorrect"
    return "correct" if normalized(response,case_sensitive)==normalized(correct,case_sensitive) else "incorrect"
