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
import unicodedata
from typing import Literal

from app.core.errors import fail
from app.models import ExerciseType

Result = Literal["correct", "almost", "incorrect"]

# Exercise types whose correct_response is free-typed text compared against
# what the learner typed. listen_order is deliberately excluded here even
# though it sometimes carries a plain-string answer - callers must check
# the actual correct_response shape for it (a list means tile ordering, not
# free text) rather than treating it as free text by type name alone.
FREE_TEXT_EXERCISE_TYPES = {
    "translation",
    "reverse_translation",
    "writing_prompt",
    "dialogue_response",
    "listen_type",
    "dictation",
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
    # A string-valued fill-in blank is a free-text answer. Array-valued
    # blanks remain shape-checked by the caller below.
    "fill_in_blank",
}

QUOTE_FOLD = str.maketrans({
    "’": "'", "‘": "'", "ʼ": "'", "´": "'", "`": "'",
    "“": '"', "”": '"', "„": '"', "«": '"', "»": '"',
})
INTERNAL_PUNCTUATION = frozenset(",;:.!?¿¡…،؛؟«»\"„")


def canonical_text(
    value: str,
    *,
    case_sensitive: bool = False,
    dictation: bool = False,
    punctuation_strict: bool = False,
) -> str:
    """Normalize text equivalences shared by all grading paths.

    Dictation keeps its byte-sensitive whitespace and punctuation behavior;
    it only receives Unicode NFC and equivalent quote folding. Other text
    collapses whitespace and, unless punctuation_strict is set, ignores
    punctuation at the boundaries and the listed punctuation within text.
    """
    text = unicodedata.normalize("NFC", value).translate(QUOTE_FOLD).strip()
    if dictation:
        return text
    if not punctuation_strict:
        start, end = 0, len(text)
        while start < end and unicodedata.category(text[start]).startswith("P"):
            start += 1
        while end > start and unicodedata.category(text[end - 1]).startswith("P"):
            end -= 1
        text = text[start:end]
        text = "".join(" " if char in INTERNAL_PUNCTUATION else char for char in text)
    text = text if case_sensitive else text.casefold()
    return " ".join(text.split())

# Ramin's 2026-08-04 decision: dictation grading ignores only punctuation at
# the answer boundaries. The realization corpus currently uses leading ¿ and
# terminal . ? ؟; the wider approved set covers the equivalent boundaries in
# the other shipped scripts. Keep this in sync with scripts/compile_content.py.
DICTATION_BOUNDARY_PUNCTUATION: frozenset[str] = frozenset(
    {".", "?", "!", "…", "¿", "¡", "؟", "।", "۔", "،"}
)

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

# ---------------------------------------------------------------------------
# Invisible-formatting equivalence (2026-07-22)
#
# Persian/Dari orthography writes the imperfective prefix mi-, the plural
# -ha, the ezafe -ye and most compounds with a ZERO-WIDTH NON-JOINER
# (U+200C) rather than a space: می‌کنم, لباس‌ها, درباره‌ی. The character is
# INVISIBLE - it changes letter shaping, never pronunciation or meaning -
# and no mainstream input method types it by default: mobile Persian
# keyboards, most desktop layouts, and every speech-to-text transcript
# produce either the joined form (میکنم) or a plain space (می کنم).
#
# fa resolves to script='arabic', which means grade_answer() runs FULLY
# STRICT (no distance-1 tolerance at all), so before this change a single
# missing U+200C was graded exactly as wrong as a wrong word. A corpus
# audit found 296 of 912 (32%) en-fa free-text exercises whose only
# accepted answer carried a ZWNJ, including 49 speak_response items that
# were therefore IMPOSSIBLE to pass (STT never emits U+200C).
#
# The same shape applies to Arabic diacritics (harakat U+064B-U+0652,
# superscript alef U+0670) and the tatweel/kashida U+0640: they are
# pronunciation/justification hints layered on top of the consonantal
# skeleton, are optional in every modern register, and are essentially
# never typed. The ar course states this explicitly in its own register
# policy ("the unvocalized written forms used for grading are
# gender-neutral by construction"), and defect class 1.30 in
# docs/CONTENT_DEFECT_REGISTRY.md is the same bug found and hand-patched
# per-instance before. This fixes it once, in grading, instead of in 296
# content files.
#
# Deliberately NOT included here: the Arabic/Persian look-alike letters in
# ARABIC_PERSIAN_SCRIPT_PAIRS (ي/ی, ك/ک, ة/ه, ۀ/ه, ى/ی). Those are VISIBLE,
# meaning-bearing letters and frequently the thing being tested - they stay
# unforgiven, see is_script_confusion(). Also not included: the combining
# hamza U+0654 (خانهٔ is a real spelling variant of خانه‌ی, and stripping it
# would collide with the ۀ/ه script pair) and Arabic-Indic digits.
# ---------------------------------------------------------------------------

ZWNJ = "‌"  # ZERO WIDTH NON-JOINER

# Characters with no phonemic, semantic or orthographic content at all:
# always removed from both sides before comparing, in any script.
ALWAYS_INVISIBLE_CHARS: frozenset[str] = frozenset(
    {
        "​",  # ZERO WIDTH SPACE
        "‍",  # ZERO WIDTH JOINER
        "‎",  # LEFT-TO-RIGHT MARK
        "‏",  # RIGHT-TO-LEFT MARK
        "؜",  # ARABIC LETTER MARK
        "﻿",  # ZERO WIDTH NO-BREAK SPACE / BOM
        "ـ",  # ARABIC TATWEEL (kashida - pure justification filler)
    }
)

# Arabic combining vowel/nunation/sukun/shadda marks + superscript alef.
# Optional in every modern register of Arabic, Persian and Dari.
ARABIC_DIACRITIC_CHARS: frozenset[str] = frozenset(
    [chr(code) for code in range(0x064B, 0x0653)] + ["ٰ"]
)

# Everything stripped outright before comparison. ZWNJ is NOT in here: it
# is handled separately because it may correspond to a SPACE on the other
# side, not only to nothing (see is_invisible_formatting_only_difference).
STRIPPED_FORMATTING_CHARS: frozenset[str] = (
    ALWAYS_INVISIBLE_CHARS | ARABIC_DIACRITIC_CHARS
)

# Minimum length (of the normalized CORRECT answer) for distance-1 typo
# tolerance to apply at all. Answers this short or shorter require an
# exact match - see is_too_short_for_typo_tolerance() below for why.
#
# Why 4 (i.e. block <= 3): on a 2-3 character word, almost every
# distance-1 neighbor is itself a real word rather than a plausible typo
# - Dutch je/ze, hij/zij, in/en, de/te/we are exactly the grammatical
# contrasts short function words exist to test, so forgiving them as
# typos silently marks the tested distinction correct. At 4+ characters
# the distance-1 neighborhood is overwhelmingly nonwords (a genuine
# single-letter slip on e.g. a 5-letter word stays forgiven), so 3 is
# the conservative floor: strict enough to protect short function-word
# contrasts, low enough not to regress legitimate typo forgiveness on
# normal-length vocabulary.
MIN_ANSWER_LENGTH_FOR_TYPO_TOLERANCE = 4

# Small, table-driven spoken transcript number vocabulary. Persian and Dari
# share the same spoken number words here; digits are normalized separately.
SPOKEN_NUMBER_WORDS = {
    "en": {**dict(enumerate(("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"))), 30: "thirty", 40: "forty", 50: "fifty", 60: "sixty", 70: "seventy", 80: "eighty", 90: "ninety", 100: "hundred"},
    "nl": {**dict(enumerate(("nul", "een", "twee", "drie", "vier", "vijf", "zes", "zeven", "acht", "negen", "tien", "elf", "twaalf", "dertien", "veertien", "vijftien", "zestien", "zeventien", "achttien", "negentien", "twintig"))), 30: "dertig", 40: "veertig", 50: "vijftig", 60: "zestig", 70: "zeventig", 80: "tachtig", 90: "negentig", 100: "honderd"},
    "fr": {**dict(enumerate(("zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf", "vingt"))), 30: "trente", 40: "quarante", 50: "cinquante", 60: "soixante", 70: "soixante-dix", 80: "quatre-vingts", 90: "quatre-vingt-dix", 100: "cent"},
    "de": {**dict(enumerate(("null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn", "zwanzig"))), 30: "dreißig", 40: "vierzig", 50: "fünfzig", 60: "sechzig", 70: "siebzig", 80: "achtzig", 90: "neunzig", 100: "hundert"},
    "es": {**dict(enumerate(("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte"))), 30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa", 100: "cien"},
    "it": {**dict(enumerate(("zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove", "dieci", "undici", "dodici", "tredici", "quattordici", "quindici", "sedici", "diciassette", "diciotto", "diciannove", "venti"))), 30: "trenta", 40: "quaranta", 50: "cinquanta", 60: "sessanta", 70: "settanta", 80: "ottanta", 90: "novanta", 100: "cento"},
    "fa": {**dict(enumerate(("صفر", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه", "ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده", "بیست"))), 30: "سی", 40: "چهل", 50: "پنجاه", 60: "شصت", 70: "هفتاد", 80: "هشتاد", 90: "نود", 100: "صد"},
}
SPOKEN_NUMBER_LANGUAGES = {"prs": "fa"}
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
SPOKEN_SHORT_FUNCTION_WORDS = {
    "en": {"a", "an", "the", "to", "of", "in", "on", "at", "by", "is", "it", "he", "we", "my", "as", "or"},
    "nl": {"de", "het", "een", "en", "ik", "je", "ze", "te", "op", "in", "er", "om", "is"},
    "fr": {"le", "la", "les", "de", "du", "un", "en", "et", "à", "au", "ce", "il", "je"},
    "de": {"der", "die", "das", "ein", "im", "zu", "an", "in", "er", "es", "du"},
    "es": {"el", "la", "los", "las", "de", "y", "a", "en", "un", "es", "al", "mi"},
    "it": {"il", "lo", "la", "di", "a", "e", "un", "in", "è", "mi", "si"},
    "fa": {"به", "از", "در", "که", "و", "را", "با", "تا"},
    "ar": {"في", "من", "إلى", "على", "عن", "و", "لا", "ما"},
}
SPOKEN_SHORT_FUNCTION_WORDS["prs"] = SPOKEN_SHORT_FUNCTION_WORDS["fa"]


def _spoken_number_match(left: str, right: str, language_code: str | None) -> bool:
    language = SPOKEN_NUMBER_LANGUAGES.get(language_code, language_code)
    words = SPOKEN_NUMBER_WORDS.get(language)
    if not words:
        return False
    left_ascii = left.translate(PERSIAN_DIGITS)
    right_ascii = right.translate(PERSIAN_DIGITS)
    for digit, word in words.items():
        if (left_ascii == str(digit) and right == word) or (
            right_ascii == str(digit) and left == word
        ):
            return True
    return left_ascii.isdigit() and right_ascii.isdigit() and left_ascii == right_ascii


def _spoken_token_match(left: str, right: str, language_code: str | None) -> bool:
    if left == right or _spoken_number_match(left, right, language_code):
        return True
    size = len(right)  # apply the threshold to the target answer token
    limit = 1 if 4 <= size <= 7 else 2 if size >= 8 else 0
    return limit > 0 and damerau_levenshtein(left, right) <= limit


def _spoken_tokens_match(response: list[str], correct: list[str], language_code: str | None) -> bool:
    language = SPOKEN_NUMBER_LANGUAGES.get(language_code, language_code)
    if language == "nl":
        response = _normalize_dutch_half_hour(response)
        correct = _normalize_dutch_half_hour(correct)
    return len(response) == len(correct) and all(
        _spoken_token_match(left, right, language_code)
        for left, right in zip(response, correct)
    )


def _normalize_dutch_half_hour(tokens: list[str]) -> list[str]:
    """Normalize Dutch half-hour speech ("half drie") against 2:30 digits."""
    number_words = SPOKEN_NUMBER_WORDS["nl"]
    word_numbers = {word: number for number, word in number_words.items()}
    normalized: list[str] = []
    index = 0
    while index < len(tokens):
        if (
            index + 1 < len(tokens)
            and tokens[index] == "half"
            and tokens[index + 1] in word_numbers
            and 1 <= word_numbers[tokens[index + 1]] <= 12
        ):
            hour = (word_numbers[tokens[index + 1]] - 1) % 12
            normalized.append(f"__time_{hour}:30__")
            index += 2
        elif (
            index + 1 < len(tokens)
            and tokens[index].translate(PERSIAN_DIGITS).isdigit()
            and tokens[index + 1].translate(PERSIAN_DIGITS) == "30"
        ):
            hour = int(tokens[index].translate(PERSIAN_DIGITS)) % 12
            normalized.append(f"__time_{hour}:30__")
            index += 2
        else:
            normalized.append(tokens[index])
            index += 1
    return normalized


def _is_short_function_word(token: str, language_code: str | None) -> bool:
    language = SPOKEN_NUMBER_LANGUAGES.get(language_code, language_code)
    return len(token) <= 3 and token in SPOKEN_SHORT_FUNCTION_WORDS.get(language, set())


def spoken_answer_result(
    response: str,
    correct: str,
    *,
    language_code: str | None,
) -> Result:
    """Grade a microphone transcript with bounded word-level tolerance."""
    # Spoken grading always follows the transcript normalization contract:
    # casefold and ignore punctuation, irrespective of typed-answer metadata.
    normalized_response = _normalize(response)
    normalized_correct = _normalize(correct)
    if is_invisible_formatting_only_difference(
        normalized_response, normalized_correct
    ):
        return "correct"
    if normalized_response == normalized_correct:
        return "correct"
    response_tokens = normalized_response.split()
    correct_tokens = normalized_correct.split()
    if _spoken_tokens_match(response_tokens, correct_tokens, language_code):
        return "almost"
    # Permit exactly one omitted or inserted short token across the answer.
    for index, token in enumerate(response_tokens):
        if _is_short_function_word(token, language_code) and _spoken_tokens_match(
            response_tokens[:index] + response_tokens[index + 1 :],
            correct_tokens,
            language_code,
        ):
            return "almost"
    for index, token in enumerate(correct_tokens):
        if _is_short_function_word(token, language_code) and _spoken_tokens_match(
            response_tokens,
            correct_tokens[:index] + correct_tokens[index + 1 :],
            language_code,
        ):
            return "almost"
    return "incorrect"


def _uses_spoken_tolerance(input_mode: str, exercise_type: str) -> bool:
    return input_mode == "spoken" or exercise_type in {"speak_repeat", "speak_response"}


def _normalize(value: str, *, case_sensitive: bool = False, exercise_type: str | None = None, punctuation_strict: bool = False) -> str:
    return canonical_text(
        value,
        case_sensitive=case_sensitive,
        dictation=exercise_type == "dictation",
        punctuation_strict=punctuation_strict,
    )


def normalize_dictation_boundary_punctuation(value: str) -> str:
    """Trim whitespace and iteratively remove dictation boundary marks."""
    normalized = value.strip()
    while normalized and normalized[0] in DICTATION_BOUNDARY_PUNCTUATION:
        normalized = normalized[1:].lstrip()
    while normalized and normalized[-1] in DICTATION_BOUNDARY_PUNCTUATION:
        normalized = normalized[:-1].rstrip()
    return normalized


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


def _is_direct_script_confusion(a: str, b: str) -> bool:
    pair = _single_substitution_pair(a, b)
    if pair is None:
        return False
    candidate = frozenset(pair)
    return candidate in ARABIC_PERSIAN_SCRIPT_PAIRS


def is_script_confusion(a: str, b: str) -> bool:
    """True if a and b differ by exactly one character that is an
    Arabic/Persian script-purity pair - never a forgivable typo.

    Checked a second time with invisible formatting removed (2026-07-22):
    _single_substitution_pair() requires equal lengths, so a ZWNJ or a
    harakat present on only one side would otherwise HIDE a genuine
    wrong-script letter behind the length mismatch (e.g. "میكنم" against
    "می‌کنم" - Arabic kaf, no ZWNJ). Since grading now forgives those
    characters, the script-purity check has to see through them too, or
    the one thing that must never be forgiven could slip past on an
    orthography_strict: False exercise.
    """
    if _is_direct_script_confusion(a, b):
        return True
    flat_a = strip_invisible_formatting(a).replace(ZWNJ, "")
    flat_b = strip_invisible_formatting(b).replace(ZWNJ, "")
    if flat_a == a and flat_b == b:
        return False
    return _is_direct_script_confusion(flat_a, flat_b)


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


def strip_invisible_formatting(value: str) -> str:
    """Remove every character in STRIPPED_FORMATTING_CHARS (bidi/zero-width
    marks, tatweel, Arabic harakat). ZWNJ deliberately survives - it is
    resolved by is_invisible_formatting_only_difference() below, which also
    has to allow it to line up with a SPACE."""
    if not any(ch in STRIPPED_FORMATTING_CHARS for ch in value):
        return value
    return "".join(ch for ch in value if ch not in STRIPPED_FORMATTING_CHARS)


def _zwnj_flexible_match(a: str, b: str) -> bool:
    """True if a and b line up when every ZWNJ is allowed to correspond to
    nothing, to a space, or to a ZWNJ on the other side.

    A plain SPACE is NOT deletable - only a ZWNJ may vanish. "کتاب ها" vs
    "کتابها" (an authored word space the learner dropped) therefore stays
    incorrect, exactly as before; only positions where one side actually
    wrote a ZWNJ become flexible. The relation is symmetric by
    construction, so it does not matter whether the ZWNJ is on the
    authored side (the overwhelmingly common case) or the learner's.

    Linear-DP reachability rather than a regex with optional groups: an
    `[‌ ]?` per ZWNJ backtracks exponentially in the number of ZWNJs,
    and the learner's side is attacker-controlled. Cost here is
    O(len(a) * len(b)), the same order as damerau_levenshtein() already
    accepts on the same bounded payload (see _MAX_PAYLOAD_JSON_CHARS in
    app/schemas/api.py), and the caller gates it behind a cheap O(n)
    necessary condition first.
    """
    len_a, len_b = len(a), len(b)
    # reachable[j] == "prefix a[:i] can align with prefix b[:j]" for the
    # row i currently being processed.
    reachable = [False] * (len_b + 1)
    reachable[0] = True
    for i in range(len_a + 1):
        nxt = [False] * (len_b + 1)
        for j in range(len_b + 1):
            if not reachable[j]:
                continue
            # drop a ZWNJ on b's side (same row, j ascending so the newly
            # reachable cell is still visited by this loop)
            if j < len_b and b[j] == ZWNJ:
                reachable[j + 1] = True
            # drop a ZWNJ on a's side
            if i < len_a and a[i] == ZWNJ:
                nxt[j] = True
            # consume one character from each side: identical characters,
            # or a ZWNJ facing the space a learner typed instead of it
            if i < len_a and j < len_b:
                x, y = a[i], b[j]
                if x == y or {x, y} == {ZWNJ, " "}:
                    nxt[j + 1] = True
        if i < len_a:
            reachable = nxt
    return reachable[len_b]


def is_invisible_formatting_only_difference(a: str, b: str) -> bool:
    """True if a and b are the same answer once characters that carry no
    pronunciation or meaning are disregarded - Persian ZWNJ, Arabic
    harakat, tatweel, zero-width/bidi marks. See the block comment above
    ZWNJ for why this is a correctness fix and not leniency.

    Never forgives an ARABIC_PERSIAN_SCRIPT_PAIRS swap (ي/ی, ك/ک, ة/ه,
    ۀ/ه, ى/ی): those are visible letters, and nothing here rewrites,
    folds or deletes a letter - only the formatting characters listed in
    STRIPPED_FORMATTING_CHARS are removed, and only a ZWNJ is allowed to
    correspond to a space. Not script-gated, because it cannot fire
    unless one of those characters is actually present (harakat/tatweel
    are Arabic-block codepoints; a ZWNJ in Latin text is meaningless
    formatting too) - so it works even on the call paths where the
    caller has no Language.script value to pass in.
    """
    if a == b:
        return True
    stripped_a = strip_invisible_formatting(a)
    stripped_b = strip_invisible_formatting(b)
    if stripped_a == stripped_b:
        return True
    if ZWNJ not in stripped_a and ZWNJ not in stripped_b:
        return False
    # Cheap O(n) necessary condition before the O(n*m) matcher: a ZWNJ may
    # only become nothing or a space, and a space stays a space, so the two
    # sides must be identical once ZWNJs and spaces are removed from both.
    if stripped_a.replace(ZWNJ, "").replace(" ", "") != stripped_b.replace(
        ZWNJ, ""
    ).replace(" ", ""):
        return False
    return _zwnj_flexible_match(stripped_a, stripped_b)


def dictation_answers_equal(response: str, correct: str) -> bool:
    """Compare dictation answers with the approved narrow forgiveness."""
    normalized_response = normalize_dictation_boundary_punctuation(
        canonical_text(response, dictation=True)
    )
    normalized_correct = normalize_dictation_boundary_punctuation(
        canonical_text(correct, dictation=True)
    )
    if not normalized_response or not normalized_correct:
        return response == correct
    return normalized_response == normalized_correct or (
        is_invisible_formatting_only_difference(
            normalized_response, normalized_correct
        )
    )


def answers_equivalent(a, b) -> bool:
    """Equality for two ALREADY-normalized answer values that ignores
    invisible formatting. Recurses into lists so word_order/listen_order
    token lists compare token-by-token; any other type (dict pair-mappings,
    numbers) falls back to plain equality."""
    if a == b:
        return True
    if isinstance(a, str) and isinstance(b, str):
        return is_invisible_formatting_only_difference(a, b)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            answers_equivalent(x, y) for x, y in zip(a, b)
        )
    return False


def is_too_short_for_typo_tolerance(correct: str) -> bool:
    """True if the (already-normalized) correct answer is too short for
    distance-1 typo tolerance to be meaningful - i.e. any mismatch must
    grade "incorrect", never "almost".

    Same "hard-block before the typo-tolerance check" shape as
    is_script_confusion()/is_case_only_difference() above (2026-07-10,
    found by a pedagogy review): a distance-1 edit on a 2-3 character
    word almost always produces a genuinely DIFFERENT word, not a typo -
    Dutch "je"/"ze", "hij"/"zij", "in"/"en" are real grammatical
    contrasts that exercises specifically test, and forgiving them as
    "almost" (which counts as correct for XP/SRS) silently defeats the
    exercise. Keyed on the CORRECT answer's length, not the response's,
    so a genuine deletion typo against a longer target (e.g. "tre" for
    "tree") stays forgiven - the authored answer is the stable,
    per-exercise-deterministic side to measure.

    Applies regardless of script (not Latin-gated like the tolerant-by-
    default heuristic): the "distance-1 on a tiny word = different word"
    logic holds for any script, and for non-Latin scripts this only
    matters when an author explicitly set orthography_strict: False -
    exactly the case where a short function word still shouldn't be
    forgiven. Known accepted limitation: the length check is on the
    whole normalized answer, not per-token, so a short-word swap inside
    a longer phrase ("ik ga" vs "ik za") is still forgiven - a per-token
    check would be a bigger behavior change than this conservative floor
    is meant to be."""
    return len(correct) < MIN_ANSWER_LENGTH_FOR_TYPO_TOLERANCE


def is_arabic_hamza_only_difference(
    response: str,
    correct: str,
    *,
    language_code: str | None,
    exercise_type: str,
    case_sensitive: bool = False,
    punctuation_strict: bool = False,
) -> bool:
    """Whether an Arabic answer differs only by أ/إ/آ versus ا spelling."""
    if language_code != "ar":
        return False
    normalized_response = _normalize(
        response,
        case_sensitive=case_sensitive,
        exercise_type=exercise_type,
        punctuation_strict=punctuation_strict,
    )
    normalized_correct = _normalize(
        correct,
        case_sensitive=case_sensitive,
        exercise_type=exercise_type,
        punctuation_strict=punctuation_strict,
    )
    if normalized_response == normalized_correct:
        return False
    fold_hamza = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا"})
    return normalized_response.translate(fold_hamza) == normalized_correct.translate(
        fold_hamza
    )


def grade_answer(
    response: str,
    correct: str,
    *,
    exercise_type: str,
    script: str | None = None,
    language_code: str | None = None,
    orthography_strict: bool | None = None,
    case_sensitive: bool = False,
    punctuation_strict: bool = False,
    input_mode: str = "typed",
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
      ar/fa/prs). language_code distinguishes Arabic from Persian/Dari:
      only 'ar' treats أ/إ/آ versus ا as an "almost" spelling difference.
      Falls back to a character-based Latin heuristic if the caller has no
      script value handy.
    - dictation is byte-strict after trimming surrounding whitespace and
      iteratively removing approved boundary punctuation, apart from the
      same invisible-formatting forgiveness applied to every strict path.
      Case, visible diacritics, script, internal whitespace, and internal
      punctuation stay strict. If boundary normalization empties either
      value, raw byte equality is required.
    - For non-dictation answers, orthography_strict, when not None, overrides
      the script-based default in either direction (author-set per exercise).
    - Invisible formatting characters (Persian ZWNJ U+200C, Arabic harakat
      U+064B-U+0652/U+0670, tatweel U+0640, zero-width/bidi marks) never
      decide correct-vs-incorrect: an answer that differs only in those grades
      "correct", ahead of every strictness branch, in every script.
      A ZWNJ may correspond to nothing or to a space (می‌کنم = میکنم =
      می کنم) because that is what real Persian keyboards and STT emit; a
      plain word space is still required. See
      is_invisible_formatting_only_difference().
    - A single-character substitution that crosses an Arabic/Persian
      script-purity boundary (e.g. Arabic kaf vs Persian keheh) is never
      treated as an "almost" typo, regardless of strictness settings, and
      is never absorbed by the invisible-formatting rule above either -
      those are visible letters, frequently the thing being tested.
    - A correct answer shorter than MIN_ANSWER_LENGTH_FOR_TYPO_TOLERANCE
      (i.e. 3 characters or fewer after normalization) requires an exact
      match - never "almost", regardless of strictness settings, because
      distance-1 on a word that short almost always yields a genuinely
      different word (Dutch je/ze, hij/zij, in/en), frequently the exact
      contrast being tested. See is_too_short_for_typo_tolerance().
    - case_sensitive (author-set per exercise, same feedback_meta blob as
      orthography_strict), when True, prevents casefolding of non-dictation
      answers and never forgives a case-only mismatch (e.g. "sie" vs "Sie") as a
      distance-1 typo either - both the exact-match and the almost-typo
      paths respect it. Defaults to False (the historical always-
      casefold behavior) so every exercise that doesn't opt in keeps
      grading exactly as before.
    """
    if _uses_spoken_tolerance(input_mode, exercise_type):
        return spoken_answer_result(
            response,
            correct,
            language_code=language_code,
        )

    if exercise_type == "dictation":
        # Do not casefold, collapse internal whitespace, fold visible
        # diacritics, or apply typo tolerance here. Invisible formatting
        # retains the same forgiveness as every other strict path.
        return (
            "correct" if dictation_answers_equal(response, correct) else "incorrect"
        )

    normalized_response = _normalize(response, case_sensitive=case_sensitive, exercise_type=exercise_type, punctuation_strict=punctuation_strict)
    normalized_correct = _normalize(correct, case_sensitive=case_sensitive, exercise_type=exercise_type, punctuation_strict=punctuation_strict)

    # Arabic-only hamza spelling tolerance. Keep this keyed to the actual
    # language code: Persian and Dari use the same script but distinguish
    # these visible spellings. Exact spelling has already gone through the
    # invisible-formatting check below; this path earns "almost" only when
    # folding hamza forms on both sides makes the answers equal.
    if is_arabic_hamza_only_difference(
        response,
        correct,
        language_code=language_code,
        exercise_type=exercise_type,
        case_sensitive=case_sensitive,
        punctuation_strict=punctuation_strict,
    ):
        return "almost"

    # Invisible formatting (Persian ZWNJ, Arabic harakat, tatweel, bidi
    # marks) is resolved HERE, on the fully-correct path, deliberately:
    # "almost" would still deny full credit on some paths, and a missing
    # U+200C is not a typo - it is the same answer, written the way every
    # real Persian input method and every STT transcript writes it. Sits
    # ahead of every strictness branch for the same reason, so a strict
    # exercise (script='arabic', orthography_strict=True, a Phase F
    # checkpoint) still can't fail a learner over a character they cannot
    # see and their keyboard will not type.
    if is_invisible_formatting_only_difference(
        normalized_response, normalized_correct
    ):
        return "correct"

    if exercise_type not in FREE_TEXT_EXERCISE_TYPES:
        return "incorrect"

    if is_script_confusion(normalized_response, normalized_correct):
        return "incorrect"

    if case_sensitive and is_case_only_difference(
        normalized_response, normalized_correct
    ):
        return "incorrect"

    if is_too_short_for_typo_tolerance(normalized_correct):
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
def normalized(v,case_sensitive=False,punctuation_strict=False):
    """Collapse whitespace and (unless case_sensitive) casefold, recursively
    for list/dict values. case_sensitive is a 2026-07-07 addition (German's
    formal "Sie" vs lowercase "sie"/"they" - a real grammatical distinction
    with no equivalent in any language shipped before, unlike Dutch/
    English/Farsi/Dari) - defaults to False so every existing call site
    (and every exercise that hasn't opted in) keeps casefolding exactly as
    before."""
    if isinstance(v,str):
        return canonical_text(v, case_sensitive=case_sensitive, punctuation_strict=punctuation_strict)
    if isinstance(v,list): return [normalized(x,case_sensitive,punctuation_strict) for x in v]
    if isinstance(v,dict): return {str(k):normalized(x,case_sensitive,punctuation_strict) for k,x in sorted(v.items())}
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
        return frozenset((normalized(k,case_sensitive,True), normalized(v,case_sensitive,True)) for k, v in value.items())
    if isinstance(value, list) and all(
        isinstance(item, dict) and {"left", "right"} <= set(item) for item in value
    ):
        return frozenset((normalized(item["left"],case_sensitive,True), normalized(item["right"],case_sensitive,True)) for item in value)
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
        collapsed = normalized(value,case_sensitive,True)
        return collapsed.split(" ") if collapsed else []
    if isinstance(value, list):
        return normalized(value,case_sensitive,True)
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
def grade(response,correct,exercise_type=None,*,script=None,language_code: str | None = None,orthography_strict=None,case_sensitive=False,punctuation_strict=False,input_mode="typed"):
    """Returns the 3-state result: 'correct' | 'almost' | 'incorrect'.
    'almost' (Phase C typo tolerance) is only ever returned for free-typed
    answers on eligible exercise types - flashcard, multi-answer, and
    choice-type grading below always resolve straight to correct/incorrect.
    case_sensitive (2026-07-07, author-set per exercise via feedback_meta,
    same as orthography_strict) skips casefolding everywhere in this
    function and never lets a case-only mismatch through as "almost" via
    grade_answer() - defaults to False so every exercise that hasn't opted
    in keeps grading exactly as before."""
    type_value = exercise_type_value(exercise_type)
    if (
        _uses_spoken_tolerance(input_mode, type_value)
        and isinstance(response, str)
        and isinstance(correct, str)
    ):
        return spoken_answer_result(
            response,
            correct,
            language_code=language_code,
        )
    if exercise_type == ExerciseType.flashcard:
        report=normalized(response, punctuation_strict=True)
        if not isinstance(report,str) or report not in {"known","unknown"}:
            fail(422,"invalid_flashcard_response","Flashcard response must be 'known' or 'unknown'")
        return "correct" if report == "known" else "incorrect"
    order_based = type_value in ORDER_BASED_EXERCISE_TYPES
    if is_multi_answer_response(correct):
        if _uses_spoken_tolerance(input_mode, type_value) and isinstance(response, str):
            verdicts = [
                spoken_answer_result(
                    response,
                    item,
                    language_code=language_code,
                )
                for item in correct["accepted"]
                if isinstance(item, str)
            ]
            return "correct" if "correct" in verdicts else "almost" if "almost" in verdicts else "incorrect"
        elif order_based:
            response_tokens = canonical_order_tokens(response,case_sensitive)
            is_ok = response_tokens is not None and any(
                answers_equivalent(response_tokens, canonical_order_tokens(item,case_sensitive)) for item in correct["accepted"]
            )
        elif type_value == "dictation":
            is_ok = isinstance(response, str) and any(
                isinstance(item, str)
                and dictation_answers_equal(response, item)
                for item in correct["accepted"]
            )
        elif type_value == "matching_pairs":
            response_pairs = canonical_pairs(response, case_sensitive)
            is_ok = response_pairs is not None and any(
                canonical_pairs(item, case_sensitive) == response_pairs
                for item in correct["accepted"]
            )
        elif type_value in FREE_TEXT_EXERCISE_TYPES and isinstance(response, str):
            verdicts = [
                grade_answer(
                    response,
                    item,
                    exercise_type=type_value,
                    script=script,
                    language_code=language_code,
                    input_mode=input_mode,
                    orthography_strict=orthography_strict,
                    case_sensitive=case_sensitive,
                    punctuation_strict=punctuation_strict,
                )
                for item in correct["accepted"]
                if isinstance(item, str)
            ]
            return "correct" if "correct" in verdicts else "almost" if "almost" in verdicts else "incorrect"
        else:
            # answers_equivalent(), not ==: this branch never reaches
            # grade_answer(), so without it a multi-accepted-answer Persian
            # exercise would still fail on a missing ZWNJ / harakat even
            # though the single-accepted-answer version of the same
            # exercise passes. Same rule, same place in the flow (the
            # fully-correct path).
            normalized_response=normalized(response,case_sensitive,True)
            is_ok = any(answers_equivalent(normalized_response, normalized(item,case_sensitive,True)) for item in correct["accepted"])
        return "correct" if is_ok else "incorrect"
    free_text_eligible = type_value in FREE_TEXT_EXERCISE_TYPES or type_value == "listen_order"
    if free_text_eligible and isinstance(response, str) and isinstance(correct, str):
        return grade_answer(
            response,
            correct,
            exercise_type=type_value,
            script=script,
            language_code=language_code,
            input_mode=input_mode,
            orthography_strict=orthography_strict,
            case_sensitive=case_sensitive,
            punctuation_strict=punctuation_strict,
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
            return "correct" if answers_equivalent(canonical_order_tokens(response,case_sensitive), correct_tokens) else "incorrect"
    return "correct" if answers_equivalent(normalized(response,case_sensitive,True), normalized(correct,case_sensitive,True)) else "incorrect"
