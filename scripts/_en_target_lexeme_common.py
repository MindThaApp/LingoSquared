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
    # Unit 3 (numbers/ages/prices/phones/market), added 2026-07-05.
    "zero": "noun", "one": "noun", "two": "noun", "three": "noun", "four": "noun",
    "five": "noun", "six": "noun", "seven": "noun", "eight": "noun", "nine": "noun",
    "ten": "noun", "eleven": "noun", "twelve": "noun", "thirteen": "noun",
    "fifteen": "noun", "twenty": "noun", "twenty-one": "noun", "thirty": "noun",
    "forty": "noun", "fifty": "noun", "hundred": "noun", "twenty-five": "noun",
    "old": "adjective", "years": "noun", "it's": "pronoun", "dollars": "noun",
    "phone": "noun", "number": "noun", "market": "noun", "apples": "noun",
    "they're": "pronoun", "ok": "adjective", "this": "pronoun", "shop": "noun",
    "much": "adverb",
    # Unit 4 (days/months/calendar dates), added 2026-07-05.
    "monday": "noun", "tuesday": "noun", "wednesday": "noun", "thursday": "noun",
    "friday": "noun", "saturday": "noun", "sunday": "noun", "it": "pronoun",
    "today": "noun", "january": "noun", "march": "noun", "july": "noun",
    "september": "noun", "december": "noun", "which": "pronoun", "month": "noun",
    "today's": "pronoun", "date": "noun", "7th": "noun", "can": "verb",
    "also": "adverb", "write": "verb", "as": "preposition", "when's": "pronoun",
    "birthday": "noun", "3rd": "noun", "opens": "verb", "again": "adverb",
    "open": "verb", "on": "preposition", "great": "adjective", "then": "adverb",
    "9th": "noun",
    # Unit 5 (telling the time), added 2026-07-05.
    "time": "noun", "o'clock": "noun", "half": "noun", "past": "preposition",
    "quarter": "noun", "night": "noun", "store": "noun", "closes": "verb",
    "does": "verb", "close": "verb", "in": "preposition",
    # Unit 6 (family members and relationships), added 2026-07-05.
    "mother": "noun", "father": "noun", "brother": "noun", "sister": "noun",
    "parents": "noun", "siblings": "noun", "grandmother": "noun",
    "grandfather": "noun", "aunt": "noun", "uncle": "noun", "cousin": "noun",
    "his": "pronoun", "her": "pronoun", "she's": "pronoun", "brothers": "noun",
    "do": "verb", "any": "particle", "don't": "verb", "only": "adjective",
    "child": "noun", "photo": "noun", "family": "noun", "who": "pronoun",
    "just": "adverb",
    # Unit 7 (food, drink, and ordering), added 2026-07-05.
    "coffee": "noun", "tea": "noun", "water": "noun", "bread": "noun",
    "soup": "noun", "salad": "noun", "sandwich": "noun", "i'd": "pronoun",
    "like": "verb", "please": "adverb", "anything": "pronoun", "else": "adverb",
    "that's": "pronoun", "all": "pronoun", "for": "preposition", "here": "adverb",
    "or": "particle", "go": "verb", "menu": "noun", "price": "noun",
    "cafe": "noun", "2": "symbol", "3": "symbol", "5": "symbol", "6": "symbol",
    "sure": "adjective",
    # Unit 8 (shopping: prices and quantities), added 2026-07-05.
    "pound": "noun", "of": "preposition", "dozen": "noun", "eggs": "noun",
    "bottle": "noun", "bag": "noun", "kilo": "noun", "tomatoes": "noun",
    "rice": "noun", "pounds": "noun", "fresh": "adjective", "per": "preposition",
    "4": "symbol",
    # Unit 9 (common places and locations), added 2026-07-05.
    "bank": "noun", "hospital": "noun", "pharmacy": "noun", "park": "noun",
    "restaurant": "noun", "next": "adjective", "across": "preposition",
    "from": "preposition", "between": "preposition", "behind": "preposition",
    "front": "noun", "where": "pronoun", "excuse": "verb", "me": "pronoun",
    "far": "adjective",
    # Unit 10 (asking for and following directions), added 2026-07-05.
    "turn": "verb", "left": "noun", "right": "noun", "straight": "adverb",
    "stop": "verb", "corner": "noun", "get": "verb", "minutes": "noun",
    "can't": "verb", "miss": "verb", "take": "verb", "first": "adjective",
    "street": "noun", "second": "adjective", "directions": "noun",
}

def en_agreement_tags(token: str) -> dict[str, object]:
    semantics: list[str] = []
    if token in {"hello", "hi", "goodbye", "bye", "welcome"}:
        semantics.append("greeting")
    if token in {"morning", "afternoon", "evening", "day", "night"}:
        semantics.append("time_period")
    # Narrower than time_period: exactly the 4 parts of the day, excluding
    # the pre-existing "day" member of time_period (which means the whole
    # day, not a time-of-day period -- mixing it into a "which part of the
    # day" recognition exercise would be a confusing distractor).
    if token in {"morning", "afternoon", "evening", "night"}:
        semantics.append("day_part")
    # Narrower still: excludes "night" too -- natives say "at night", not
    # "in the night", so a "... in the {item}." frame must never offer
    # night as a candidate.
    if token in {"morning", "afternoon", "evening"}:
        semantics.append("day_part_in")
    if token in {"goodbye", "bye", "see", "later", "then"}:
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
    if token in {"zero", "one", "two", "three", "four", "five", "six", "seven",
                 "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fifteen",
                 "twenty", "twenty-one", "thirty", "forty", "fifty", "hundred",
                 "twenty-five"}:
        semantics.append("number")
    if token in {"old", "years", "twenty-five"}:
        semantics.append("age_phrase")
    if token in {"it's", "dollars", "much"}:
        semantics.append("price_phrase")
    if token in {"phone", "number"}:
        semantics.append("phone_phrase")
    if token in {"market", "apples", "shop", "they're", "ok", "this"}:
        semantics.append("market_dialogue")
    # Narrower than market_dialogue: singular place nouns only, safe for a
    # "Daniel is at the {item}." slot (excludes "apples", which is plural and
    # would make that frame ungrammatical -- "This is the apples" is not a
    # valid sentence).
    if token in {"market", "shop"}:
        semantics.append("place_singular")
    if token in {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}:
        semantics.append("weekday")
    if token in {"january", "march", "july", "september", "december"}:
        semantics.append("month")
    if token in {"7th", "3rd", "9th"}:
        semantics.append("day_ordinal")
    if token in {"mother", "father", "brother", "sister"}:
        semantics.append("family_singular")
    if token in {"parents", "siblings"}:
        semantics.append("family_collective")
    if token in {"grandmother", "grandfather", "aunt", "uncle", "cousin"}:
        semantics.append("extended_family")
    # Includes "my"/"your" (already tagged identity above) alongside the new
    # "his"/"her" -- all four are safe alternatives in "This is {item}
    # sister." (unlike, say, unit03's age_phrase pair, these truly are
    # interchangeable determiners in the same syntactic slot).
    if token in {"my", "your", "his", "her"}:
        semantics.append("possessive")
    if token in {"coffee", "tea", "water", "bread", "soup", "salad", "sandwich"}:
        semantics.append("food_item")
    if token in {"zero", "two", "three", "four", "five", "six", "seven", "eight",
                 "nine", "ten", "eleven", "twelve", "thirteen", "fifteen",
                 "twenty", "twenty-one", "thirty", "forty", "fifty", "hundred",
                 "twenty-five"}:
        # "number" minus "one" -- safe for any "{item} things" plural-count
        # frame ("Can I have {item} pounds?"), where "one" would need the
        # singular "pound" instead and silently produce a real grammar
        # error if included here (found while designing unit08's templates).
        semantics.append("count_plural")
    if token in {"pound", "dozen", "bottle", "bag", "kilo"}:
        semantics.append("quantity_unit")
    # Countable, always-plural-in-this-context food nouns, safe for "How much
    # are the {item}?" -- excludes the unit07 food_item set (coffee/tea/
    # water/bread/soup/salad/sandwich), which are mass/singular nouns and
    # would produce "How much are the coffee?" (needs "is", not "are") if
    # mixed in here.
    if token in {"apples", "eggs", "tomatoes"}:
        semantics.append("food_plural")
    if token in {"bank", "hospital", "pharmacy", "park", "restaurant"}:
        semantics.append("place")
    # Narrower than place: excludes "hospital" specifically, since it's used
    # as the fixed anchor in this unit's "The {item} is next to/behind the
    # hospital." frames -- including it in the slot would let the sampler
    # generate "The hospital is next to the hospital." (self-reference).
    if token in {"bank", "pharmacy", "park", "restaurant"}:
        semantics.append("place_non_hospital")
    # Only left/right are safe alternatives in "Turn {item}." -- "straight"
    # pairs with "go", not "turn" ("Turn straight" is not English), so it is
    # deliberately excluded from this tag.
    if token in {"left", "right"}:
        semantics.append("turn_direction")
    if token in {"first", "second"}:
        semantics.append("street_ordinal")

    tags: dict[str, object] = {}
    if semantics:
        tags["semantic"] = semantics

    person = {
        "i": "first", "i'm": "first", "am": "first",
        "you": "second", "your": "second", "are": "second",
        "he": "third", "she": "third", "is": "third",
        "it's": "third", "they're": "third", "she's": "third",
        "his": "third", "her": "third", "who": "third", "i'd": "first",
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
