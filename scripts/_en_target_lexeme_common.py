"""Shared English target-language lexeme classification for the three
X->en Endless Practice backfill scripts (nl-en, fa-en, prs-en), which
all teach the SAME English realization
(docs/content/realizations/en/a1_unit01_greetings.yaml +
a1_unit02_introductions.yaml) to different source-language speakers.

Written by hand, mirroring the rigor of scripts/backfill_lexemes.py's
Farsi classification -- every introduced_token across both units is
classified explicitly, nothing left to a fallback guess. Shared across
the three backfill scripts rather than tripled, since it's the exact
same underlying English vocabulary for all three; each backfill script
still writes lexemes against its own course_id (lexemes are scoped per
course, not shared in the DB), so this only shares the classification
logic, not any data.

Semantic categories reuse the same vocabulary the en-fa pilot pack
established (greeting, time_period, farewell, wellbeing_question,
wellbeing_answer, politeness, person_name, identity, dialogue_word) --
this is a legitimate reuse, not a mechanical copy: this English
realization covers the identical universal spine outcomes
(greetings.open_close_exchange, introductions.exchange_identity) as
the Farsi one, so the same communicative categories genuinely apply
here too, just to different words.

IMPORTANT, found via live verification (a real bug caught before it
shipped across all three pairs): this module deliberately does NOT
export an `english_gloss` mapping. The `Lexeme.english_gloss` field is
consumed by `slot_gloss`-derived multiple_choice/translation exercises
as the literal comprehension-check answer text shown to the learner --
for an X->en course, that MUST be the SOURCE language's translation
(Dutch/Farsi/Dari), not another English string, or the exercise
degenerates to matching an English word against itself. Since the
source language differs per course, each backfill script (nl_en/fa_en/
prs_en) must supply its OWN gloss dict for these shared English
tokens -- only POS and semantic tags are safely shareable here, because
those are properties of the English word itself, not of the direction
being taught.
"""
from __future__ import annotations

EN_POS: dict[str, str] = {
    "hello": "noun", "hi": "noun", "good": "adjective", "morning": "noun",
    "afternoon": "noun", "evening": "noun", "goodbye": "noun", "bye": "noun",
    "how": "adverb", "are": "verb", "you": "pronoun", "i'm": "pronoun",
    "fine": "adjective", "thanks": "noun", "not": "particle", "bad": "adjective",
    "and": "particle", "okay": "adjective", "nice": "adjective", "to": "preposition",
    "meet": "verb", "too": "adverb", "see": "verb", "later": "adverb",
    "have": "verb", "a": "particle", "day": "noun", "what": "pronoun",
    "is": "verb", "what's": "pronoun", "your": "pronoun", "name": "noun",
    "my": "pronoun", "leila": "proper_noun", "i": "pronoun", "am": "verb",
    "student": "noun", "teacher": "noun", "yes": "particle", "no": "particle",
    "new": "adjective", "member": "noun", "he": "pronoun", "she": "pronoun",
    "an": "particle", "engineer": "noun", "library": "noun", "assistant": "noun",
    "daniel": "proper_noun", "work": "verb", "at": "preposition", "the": "particle",
    "welcome": "verb", "thank": "verb",
}

def en_agreement_tags(token: str) -> dict[str, object]:
    semantics: list[str] = []
    if token in {"hello", "hi", "goodbye", "bye", "welcome"}:
        semantics.append("greeting")
    if token in {"morning", "afternoon", "evening", "day"}:
        semantics.append("time_period")
    if token in {"goodbye", "bye", "see", "later"}:
        semantics.append("farewell")
    if token == "how":
        semantics.append("wellbeing_question")
    if token in {"fine", "okay", "bad"}:
        semantics.append("wellbeing_answer")
    if token in {"thanks", "thank", "nice", "welcome"}:
        semantics.append("politeness")
    if token in {"yes", "no"}:
        semantics.append("politeness")
    if token in {"name", "my", "your", "what", "what's", "i'm", "i", "am", "is", "are"}:
        semantics.append("identity")
    if token in {"leila", "daniel"}:
        semantics.append("person_name")
    if token in {"work", "library", "assistant", "member", "student", "teacher", "engineer", "new"}:
        semantics.append("dialogue_word")

    tags: dict[str, object] = {}
    if semantics:
        tags["semantic"] = semantics

    person = {
        "i": "first", "i'm": "first", "am": "first",
        "you": "second", "your": "second", "are": "second",
        "he": "third", "she": "third", "is": "third",
    }.get(token)
    if person:
        tags["person"] = person
    return tags


# The exact set of unique introduced_tokens across both units, casefolded --
# any lexeme classification consumer should assert against this set to
# catch a token the realization introduces that this module hasn't
# classified yet (mirrors the reference script's "raise if gloss missing"
# discipline).
EN_KNOWN_TOKENS = frozenset(EN_POS.keys())
