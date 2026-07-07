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
    "does": "verb",
    # KNOWN HOMOGRAPH LIMITATION (same class as the Dutch scripts'
    # documented "zijn" issue): "close" is classified "verb" here (the
    # store closes, unit05) but unit26 also introduces "close" as an
    # ADJECTIVE ("very close to the playground"). This module can only
    # hold one POS per bare token string. Kept as "verb" since that's
    # the sense an existing shipped pack (fa-en unit05) depends on in
    # its literal frame text; no unit26 practice pack exists yet in any
    # direction, so nothing currently needs the adjective sense as a
    # fillable slot. Whoever authors unit26 practice content must NOT
    # rely on "close" as a slot value for the adjective sense until this
    # gets real POS-aware/context-aware keying.
    "close": "verb", "in": "preposition",
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
    # Unit 11 (talking about the weather), added 2026-07-05.
    "sunny": "adjective", "rainy": "adjective", "cloudy": "adjective",
    "cold": "adjective", "hot": "adjective", "windy": "adjective",
    "weather": "noun", "warm": "adjective", "raining": "verb", "should": "verb",
    "umbrella": "noun", "tomorrow": "noun", "will": "verb", "be": "verb",
    "rain": "verb", "let's": "pronoun", "idea": "noun", "but": "particle",
    "going": "verb", "so": "adverb",
    # Unit 12 (clothing: sizes and colors), added 2026-07-05.
    "shirt": "noun", "pants": "noun", "shoes": "noun", "jacket": "noun",
    "dress": "noun", "small": "adjective", "medium": "adjective",
    "large": "adjective", "blue": "adjective", "black": "adjective",
    "size": "noun", "color": "noun", "20": "symbol", "i'll": "pronoun",
    "we": "pronoun",
    # Unit 13 (talking about feelings), added 2026-07-05.
    "happy": "adjective", "sad": "adjective", "tired": "adjective",
    "excited": "adjective", "worried": "adjective", "feeling": "noun",
    "little": "adjective", "because": "particle", "big": "adjective",
    "test": "noun", "class": "noun", "almost": "adverb", "over": "adjective",
    "last": "adjective", "year": "noun", "writer": "noun", "oh": "particle",
    "understand": "verb",
    # Unit 14 (phone calls and messages), added 2026-07-05.
    "free": "adjective", "tonight": "noun", "sorry": "adjective",
    "repeat": "verb", "speak": "verb", "more": "adverb", "slowly": "adverb",
    "hear": "verb", "well": "adverb", "6pm": "noun", "message": "noun",
    "suggest": "verb", "meeting": "noun", "place": "noun", "about": "preposition",
    "that": "pronoun",
    # Unit 15 (handling money and payments), added 2026-07-05.
    "cash": "noun", "card": "noun", "credit": "noun", "debit": "noun",
    "total": "noun", "cards": "noun", "pay": "verb", "tax": "noun", "10": "symbol",
    "by": "preposition", "1": "symbol",
    # Unit 16 (describing a daily routine), added 2026-07-05.
    "wake": "verb", "up": "particle", "dressed": "adjective", "dinner": "noun",
    "bed": "noun", "every": "adjective", "usually": "adverb", "breakfast": "noun",
    "after": "preposition",
    # Unit 17 (making simple plans), added 2026-07-05.
    "want": "verb", "movie": "noun", "weekend": "noun", "would": "verb",
    "walk": "noun", "love": "verb", "busy": "adjective", "maybe": "adverb",
    "another": "adjective", "lunch": "noun", "1pm": "noun", "works": "verb",
    # Unit 18 (describing a recent event), added 2026-07-05.
    "went": "verb", "saw": "verb", "ate": "verb", "visited": "verb",
    "worked": "verb", "did": "verb", "yesterday": "noun", "together": "adverb",
    "watched": "verb", "writer's": "noun", "s": "particle", "was": "verb",
    "week": "noun",
    # Unit 19 (expressing likes and preferences), added 2026-07-05.
    "like": "verb", "don't": "verb", "prefer": "verb", "hate": "verb",
    "calmer": "adjective", "very": "adverb", "strong": "adjective",
    "why": "adverb", "think": "verb", "prefers": "verb", "thinks": "verb",
    # Unit 20 (making basic comparisons), added 2026-07-06.
    "bigger": "adjective", "smaller": "adjective", "cheaper": "adjective",
    "expensive": "adjective", "faster": "adjective", "than": "particle",
    "nicer": "adjective", "cheapest": "adjective", "red": "adjective",
    "car": "noun", "white": "adjective",
    # Unit 21 (handling a basic journey/travel), added 2026-07-06.
    "ticket": "noun", "platform": "noun", "train": "noun", "departure": "noun",
    "arrival": "noun", "boston": "proper_noun", "way": "noun", "round": "adjective",
    "trip": "noun", "leaves": "verb", "9:15": "symbol", "arrives": "verb",
    "11:30": "symbol", "arrive": "verb",
    # Unit 22 (common symptoms/health), added 2026-07-06.
    "headache": "noun", "stomachache": "noun", "fever": "noun", "cough": "noun",
    "sore": "adjective", "throat": "noun", "rest": "verb", "need": "verb",
    "wrong": "adjective", "feel": "verb", "doctor": "noun", "doesn't": "verb",
    "look": "verb", "drink": "verb", "help": "verb", "better": "adjective",
    "if": "particle",
    # Unit 23 (describing a job), added 2026-07-06 (restored after a
    # merge incident silently reverted this and the unit 24-26 entries
    # below -- see docs/BUILD_LOG.md for the incident and its fix).
    "nurse": "noun", "cook": "noun", "driver": "noun", "patients": "noun",
    "reports": "noun", "interesting": "adjective", "company": "noun",
    "downtown": "noun", "answer": "verb", "emails": "noun", "sometimes": "adverb",
    "with": "preposition", "clients": "noun", "job": "noun",
    # Unit 24 (describing a home), added 2026-07-06.
    "bedroom": "noun", "kitchen": "noun", "bathroom": "noun", "living": "adjective",
    "room": "noun", "garden": "noun", "many": "adjective", "rooms": "noun",
    "there": "pronoun", "there's": "pronoun", "apartment": "noun", "has": "verb",
    "bedrooms": "noun", "favorite": "adjective", "tell": "verb", "isn't": "verb",
    "balcony": "noun", "upstairs": "adverb", "near": "preposition", "easy": "adjective",
    "eat": "verb",
    # Unit 25 (A2: registering with local authorities), added 2026-07-06.
    "address": "noun", "appointment": "noun", "document": "noun", "proof": "noun",
    "residency": "noun", "form": "noun", "confirmation": "noun", "was": "verb",
    "wondering": "verb", "whether": "particle", "could": "verb", "make": "verb",
    "an": "particle", "would": "verb", "possible": "adjective", "come": "verb",
    "this": "pronoun", "friday": "noun", "update": "verb", "my": "pronoun",
    "because": "particle", "moved": "verb", "last": "adjective", "month": "noun",
    "photo": "noun", "id": "noun", "utility": "noun", "bill": "noun",
    "your": "pronoun", "please": "adverb", "bring": "verb", "such": "preposition",
    "as": "preposition", "you": "pronoun", "have": "verb", "lived": "verb",
    "at": "preposition", "new": "adjective", "since": "preposition", "so": "adverb",
    "also": "adverb", "lease": "noun", "will": "verb", "when": "adverb",
    "yes": "particle", "10am": "symbol", "4471": "symbol", "works": "verb",
    # Unit 26 (A2: giving opinions with reasons), added 2026-07-06.
    "opinion": "noun", "agree": "verb", "on": "preposition", "other": "adjective",
    "hand": "noun", "about": "preposition", "dog": "noun", "park": "noun",
    "good": "adjective", "idea": "noun", "dogs": "noun", "space": "noun",
    "run": "verb", "very": "adverb", "playground": "noun",
    "fair": "adjective", "point": "noun", "they": "pronoun", "should": "verb",
    "move": "verb", "little": "adjective", "farther": "adverb", "away": "adverb",
    # Unit 27 (A2: opening a bank account), added 2026-07-07 -- part of the
    # nl-en A2 course-routing fix (see backfill_lexemes_nl_en.py's docstring).
    "checking": "adjective", "account": "noun", "monthly": "adjective",
    "fee": "noun", "minimum": "adjective", "balance": "noun",
    "direct": "adjective", "deposit": "noun", "documents": "noun",
    "you'll": "pronoun", "dmv": "proper_noun", "business": "noun",
    "days": "noun", "keep": "verb", "500": "symbol", "sounds": "verb",
    "teller": "noun", "both": "pronoun",
    # Unit 28 (A2: attending a doctor's appointment), added 2026-07-07 --
    # nl-en's practice-pool extension alongside unit27. "appointment"/
    # "card"/"headache"/"sore"/"throat"/"fever"/"up" already exist (units
    # 25/15/22/16 respectively) -- only genuinely new-to-unit28 tokens
    # added here.
    "medicine": "noun", "prescription": "noun", "follow": "verb",
    "getting": "verb", "worse": "adjective", "insurance": "noun",
    "i've": "pronoun", "had": "verb", "early": "adverb", "confirmed": "verb",
    "3pm": "symbol", "7724": "symbol", "back": "adverb", "within": "preposition",
    "twice": "adverb", "plenty": "noun",
    # KNOWN HOMOGRAPH LIMITATION (same class as "close" above): "cold" is
    # already classified "adjective" (unit11's weather_condition sense --
    # "It's cold today"), but unit28 also introduces "cold" as a NOUN ("You
    # have a bad cold", an illness) via the exact same bare token. This
    # module can only hold one POS per bare token string, so the existing
    # "adjective" classification wins; nothing currently needs "cold" as a
    # fillable noun slot (unit28's practice pack deliberately does not use
    # it), but whoever authors a future template must NOT rely on "cold" as
    # a noun-slot candidate until this gets real POS-aware/context-aware
    # keying.
    # Unit 29 (A2, reporting a maintenance problem), added 2026-07-07.
    "leaking": "verb", "sink": "noun", "building": "noun", "manager": "noun",
    "plumber": "noun", "repair": "noun",
    # "report" is a homograph, same class as "close"/"cold" above: this
    # unit's lesson02 introduces it first as a VERB ("I'd like to report a
    # problem..."), but lesson03's reading text reintroduces the same bare
    # token as a NOUN ("Your report of a leaking kitchen sink..."). Kept
    # as "verb" (the first-established sense) since that's what this
    # pack's own templates need; the noun sense is never used as a
    # fillable slot value in any practice template.
    "report": "verb", "problem": "noun", "been": "verb", "someone": "pronoun",
    "fix": "verb", "2pm": "symbol", "4pm": "symbol", "received": "verb",
    "6180": "symbol", "send": "verb", "home": "noun", "here's": "pronoun",
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
    # Narrower than "number": excludes bare "hundred", which the real content
    # only ever teaches with an article ("one hundred") -- the broad "number"
    # tag let a price/age/total frame draw bare "hundred" and generate real,
    # shipped nonsense like "I have hundred dollars."/"I'm hundred years
    # old." (found via a fresh-context review pass). Use this in any frame
    # that embeds the number mid-sentence in a price/age/total context;
    # "number" itself stays fine for pure bare-word recognition, where no
    # article is needed anyway.
    if token in {"zero", "one", "two", "three", "four", "five", "six", "seven",
                 "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fifteen",
                 "twenty", "twenty-one", "thirty", "forty", "fifty",
                 "twenty-five"}:
        semantics.append("number_no_hundred")
    # Narrower still: only one through twelve, safe for any clock-hour
    # frame ("It's {item} o'clock."/"I wake up at {item} every day.") --
    # the broad "number" tag let these frames draw values like "fifty" or
    # "hundred", producing "It's fifty o'clock." (also found via the same
    # review pass; a real 12-hour clock only ever has hours 1-12).
    if token in {"one", "two", "three", "four", "five", "six", "seven",
                 "eight", "nine", "ten", "eleven", "twelve"}:
        semantics.append("hour_number")
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
    # Narrower than food_item: excludes "sandwich" specifically, since it's
    # used as the fixed anchor in "I'd like a {item} and a sandwich,
    # please." -- including it in the slot would let the sampler generate
    # "I'd like a sandwich and a sandwich, please." (self-reference, the
    # same bug class as the well-known "hospital is next to the hospital"
    # catch, just via an "and" conjunction instead of a fixed anchor noun;
    # found via a fresh-context review pass).
    if token in {"coffee", "tea", "water", "bread", "soup", "salad"}:
        semantics.append("food_item_non_sandwich")
    if token in {"headache", "stomachache", "fever", "cough"}:
        # "sore"/"throat" (the two-word "sore throat" compound) are
        # deliberately excluded -- a single-word slot can't fill a
        # multi-word compound without producing "I have a sore." or
        # "I have a throat.".
        semantics.append("symptom_noun")
    # Unit 23 (describing a job): 5-member occupation tag (includes
    # "teacher"/"engineer", already classified since unit01, tagged
    # additively here) for bare-word recognition. Narrower 4-member
    # "occupation_a" EXCLUDES "engineer" -- real content shows "I'm a
    # nurse." but "I'm an engineer." (article agreement: engineer starts
    # with a vowel sound), so a shared "I'm a {item}." frame must never
    # offer engineer as a candidate, or it generates "I'm a engineer."
    if token in {"teacher", "nurse", "engineer", "cook", "driver"}:
        semantics.append("occupation_noun")
    if token in {"teacher", "nurse", "cook", "driver"}:
        semantics.append("occupation_a")
    # Unit 24 (describing a home): 4-member room tag, verified all four
    # collocate naturally in "There's a {item}." ("There's a bedroom/
    # kitchen/bathroom/garden." are all grammatical, and the real
    # content uses this exact shape for kitchen). "living room" (a
    # two-word compound) is deliberately excluded since it doesn't fit
    # a single-token slot.
    if token in {"bedroom", "kitchen", "bathroom", "garden"}:
        semantics.append("room_noun")
    # Unit 25 (A2, registering with local authorities): 4-member bare-
    # word recognition tag, no shared generative frame attempted --
    # these abstract nouns don't collocate uniformly at A2 register.
    if token in {"appointment", "document", "form", "confirmation"}:
        semantics.append("bureaucracy_noun")
    # Unit 26 (A2, giving opinions with reasons): 4-member bare-word
    # recognition tag drawn from the dog-park scenario's concrete nouns.
    if token in {"dog", "park", "playground", "space"}:
        semantics.append("dogpark_noun")
    if token in {"zero", "two", "three", "four", "five", "six", "seven", "eight",
                 "nine", "ten", "eleven", "twelve", "thirteen", "fifteen",
                 "twenty", "twenty-one", "thirty", "forty", "fifty", "hundred",
                 "twenty-five"}:
        # "number" minus "one" -- safe for any "{item} things" plural-count
        # frame ("Can I have {item} pounds?"), where "one" would need the
        # singular "pound" instead and silently produce a real grammar
        # error if included here (found while designing unit08's templates).
        semantics.append("count_plural")
    if token in {"zero", "two", "three", "four", "five", "six", "seven", "eight",
                 "nine", "ten", "eleven", "twelve", "thirteen", "fifteen",
                 "twenty", "twenty-one", "thirty", "forty", "fifty",
                 "twenty-five"}:
        # count_plural minus bare "hundred" -- same reasoning as
        # number_no_hundred above, for plural-count frames specifically
        # ("Can I have {item} pounds/dozen eggs, please?").
        semantics.append("count_plural_no_hundred")
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
    if token in {"sunny", "rainy", "cloudy", "cold", "hot", "windy"}:
        semantics.append("weather_condition")
    if token in {"shirt", "pants", "shoes", "jacket", "dress"}:
        semantics.append("clothing_item")
    # Narrower than clothing_item: excludes "pants"/"shoes" (always plural in
    # English), safe for "Do you have this {item} in a medium?" -- "this
    # pants"/"this shoes" would be a real number-agreement error.
    if token in {"shirt", "jacket", "dress"}:
        semantics.append("clothing_singular")
    if token in {"small", "medium", "large"}:
        semantics.append("clothing_size")
    if token in {"blue", "black"}:
        semantics.append("clothing_color")
    if token in {"happy", "sad", "tired", "excited", "worried"}:
        semantics.append("feeling")
    if token in {"cash", "card", "credit", "debit"}:
        semantics.append("payment_method")
    # Narrower than payment_method: just the two words that modify "cards"
    # in "Do you take {item} cards?" -- "cash"/"card" alone there would be
    # semantically odd ("Do you take cash cards?" is not a real phrase).
    if token in {"credit", "debit"}:
        semantics.append("card_type")
    if token in {"dinner", "breakfast"}:
        semantics.append("meal")
    if token in {"went", "saw", "ate", "visited", "worked"}:
        semantics.append("past_verb")
    # Narrower than past_verb: only the intransitive-safe ones for "I {item}
    # yesterday." -- "saw"/"visited" are transitive and would leave that
    # frame feeling incomplete ("I saw yesterday." / "I visited yesterday.")
    if token in {"went", "ate", "worked"}:
        semantics.append("past_verb_intransitive")
    if token in {"like", "don't", "prefer", "love", "hate"}:
        semantics.append("preference_verb")
    # Narrower than preference_verb: excludes "don't" (an auxiliary needing a
    # following verb -- "I don't tea." is not a sentence), safe for
    # "I {item} tea/coffee." frames.
    if token in {"like", "prefer", "love", "hate"}:
        semantics.append("preference_verb_full")
    # Unit 20: 5 one-word "-er" comparatives, verified interchangeable in
    # "This X is {item} than that X." -- all take "than" grammatically
    # (unlike "more expensive", a two-word phrase that doesn't fit a single
    # slot, and unlike "cheapest", a superlative that does NOT take "than").
    if token in {"bigger", "smaller", "cheaper", "faster", "nicer"}:
        semantics.append("comparative_adj")
    # "cheapest" is the only superlative introduced so far -- kept as its
    # own single-member tag (never used for multiple_choice/listen_select,
    # only word_order/fill_in_blank/translation, which don't need >=4
    # candidates) rather than folded into comparative_adj, since mixing
    # degrees would let the sampler generate "This bag is cheapest than
    # that bag." -- superlatives never take "than".
    if token == "cheapest":
        semantics.append("superlative_adj")
    if token in {"red", "white"}:
        semantics.append("color")
    # Unit 21: 5-member bare-word recognition tag. Deliberately NOT used in
    # any shared generative frame -- these nouns don't collocate uniformly
    # (e.g. "I need a ticket"/"I need a train" work but "I need a platform"/
    # "departure"/"arrival" don't), so this stays recognition-only, same
    # discipline as en-nl unit08's place_non_station lessons that reused
    # bare-word recognition rather than forcing a risky shared frame.
    if token in {"ticket", "platform", "train", "departure", "arrival"}:
        semantics.append("travel_noun")
    # Unit 27 (A2, opening a bank account): 8-member bare-word recognition
    # tag for the unit's single-token banking nouns -- verified all share
    # POS "noun" in EN_POS. Deliberately NOT used in any shared generative
    # frame (these abstract/concrete nouns don't collocate uniformly at A2
    # register -- "keep a minimum {item}" only works for "balance", not
    # "fee"/"deposit"/"teller"/etc.), same recognition-only discipline as
    # unit25's bureaucracy_noun/unit26's dogpark_noun.
    if token in {"account", "fee", "balance", "deposit", "business", "days",
                 "documents", "teller"}:
        semantics.append("banking_noun")
    # Unit 27: 4-member bare-word recognition tag for the unit's single-
    # token banking-related adjectives (each modifies a different noun in
    # its own compound -- "checking account", "monthly fee", "minimum
    # balance", "direct deposit" -- so, same as banking_noun, kept
    # recognition-only, no shared generative frame attempted).
    if token in {"checking", "monthly", "minimum", "direct"}:
        semantics.append("banking_adjective")
    # Unit 28 (A2, attending a doctor's appointment): 3-member bare-word
    # recognition tag for the unit's single-token, genuinely-standalone
    # nouns (each has its own real independent meaning -- medicijn/recept/
    # verzekering -- unlike "insurance card"/"follow-up appointment", which
    # are true two-word compounds and stay recognition-only via their own
    # component tokens instead). Deliberately NOT used in any shared
    # generative frame (same "don't force it" reasoning as banking_noun/
    # bureaucracy_noun -- these three don't collocate uniformly: "I need
    # a {item}" works for prescription but reads oddly for the mass noun
    # medicine, and not at all for insurance alone without "card").
    if token in {"medicine", "prescription", "insurance"}:
        semantics.append("health_followup_noun")
    # Unit 28: 2-member adjective tag for the unit's real comparative
    # symptom-condition adjectives. Both are genuine, safe alternatives in
    # "It's getting {item}." (a symptom can get either worse or better --
    # real, grammatical, and thematically apt for a doctor's-appointment
    # unit) -- kept small (2 members) so it's intentionally NOT used for
    # multiple_choice/listen_select (which need >=3 distinct candidates),
    # only word_order/translation, matching this module's own precedent
    # for other small tags (e.g. the single-member "superlative_adj").
    if token in {"worse", "better"}:
        semantics.append("condition_adjective")
    # Unit 29 (A2, reporting a maintenance problem): 3-member bare-word
    # recognition tag for the unit's single-token, genuinely-standalone
    # maintenance nouns (each has its own real independent meaning --
    # sink/plumber/repair -- unlike "building manager", a true two-word
    # compound whose components ("building"/"manager") are deliberately
    # left OUT of this tag and out of every semantic tag -- same
    # discipline as "sore"/"throat" (unit22's "sore throat" compound)
    # staying untagged, no practice template ever uses them as a fillable
    # slot). Deliberately NOT used in any shared generative frame either
    # (same "don't force it" reasoning as health_followup_noun/
    # bureaucracy_noun -- "I need a {item}" reads naturally for plumber/
    # repair but oddly for the fixture noun sink).
    if token in {"sink", "plumber", "repair"}:
        semantics.append("maintenance_noun")

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
