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

from collections.abc import Iterator

EN_PHRASE_LEXEME_UNIT_STEMS = frozenset({
    "a1_unit60_invitations",
    "a1_unit62_phone_calls",
    "a1_unit63_asking_for_help",
    "a1_unit64_compliments",
    "a1_unit65_returns_exchanges",
    "a1_unit66_pharmacy_symptoms",
    "a1_unit67_family_news",
    "a1_unit68_borrowing_lending",
})


def iter_taught_phrase_lexemes(
    realization_path_stem: str,
    lesson: dict[str, object],
    teaching_overlays: dict[str, dict[str, object]],
) -> Iterator[tuple[str, str, str]]:
    """Yield explicitly taught English chunks with their source glosses."""
    if realization_path_stem not in EN_PHRASE_LEXEME_UNIT_STEMS:
        return
    for item in lesson.get("teaching", []):
        if item.get("kind") not in {"phrase", "dialogue", "reading"}:
            continue
        content_key = item["content_key"]
        token = (
            item.get("target", {}).get("text", "").casefold().replace("’", "'").strip()
        )
        if " " not in token or len(token) > 255:
            continue
        gloss = str(teaching_overlays.get(content_key, {}).get("gloss", "")).strip()
        if not gloss:
            raise ValueError(f"missing source-language phrase gloss for {content_key!r}")
        if len(gloss) <= 255:
            yield content_key, token, gloss


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
    "zero": "noun", "one": "noun", "two": "noun", "three": "noun",
    "four": "noun", "five": "noun", "six": "noun", "seven": "noun",
    "eight": "noun", "nine": "noun", "ten": "noun", "eleven": "noun",
    "twelve": "noun", "thirteen": "noun", "fifteen": "noun", "twenty": "noun",
    "twenty-one": "noun", "thirty": "noun", "forty": "noun", "fifty": "noun",
    "hundred": "noun", "twenty-five": "noun", "old": "adjective", "years": "noun",
    "it's": "pronoun", "dollars": "noun", "phone": "noun", "number": "noun",
    "market": "noun", "apples": "noun", "they're": "pronoun", "ok": "adjective",
    "this": "pronoun", "shop": "noun", "much": "adverb",
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
    "parents": "noun", "siblings": "noun", "grandmother": "noun", "grandfather": "noun",
    "aunt": "noun", "uncle": "noun", "cousin": "noun", "his": "pronoun",
    "her": "pronoun", "she's": "pronoun", "brothers": "noun", "do": "verb",
    "any": "particle", "don't": "verb", "only": "adjective", "child": "noun",
    "photo": "noun", "family": "noun", "who": "pronoun", "just": "adverb",
    # Unit 7 (food, drink, and ordering), added 2026-07-05.
    "coffee": "noun", "tea": "noun", "water": "noun", "bread": "noun",
    "soup": "noun", "salad": "noun", "sandwich": "noun", "i'd": "pronoun",
    "like": "verb", "please": "adverb", "anything": "pronoun", "else": "adverb",
    "that's": "pronoun", "all": "pronoun", "for": "preposition", "here": "adverb",
    "or": "particle", "go": "verb", "menu": "noun", "price": "noun",
    "cafe": "noun", "2": "symbol", "3": "symbol", "5": "symbol",
    "6": "symbol", "sure": "adjective",
    # Unit 8 (shopping: prices and quantities), added 2026-07-05.
    "pound": "noun", "of": "preposition", "dozen": "noun", "eggs": "noun",
    "bottle": "noun", "bag": "noun", "kilo": "noun", "tomatoes": "noun",
    "rice": "noun", "pounds": "noun", "fresh": "adjective", "per": "preposition",
    "4": "symbol",
    # Unit 9 (common places and locations), added 2026-07-05.
    "bank": "noun", "hospital": "noun", "pharmacy": "noun", "park": "noun",
    "restaurant": "noun", "next": "adjective", "across": "preposition", "from": "preposition",
    "between": "preposition", "behind": "preposition", "front": "noun", "where": "pronoun",
    "excuse": "verb", "me": "pronoun", "far": "adjective",
    # Unit 10 (asking for and following directions), added 2026-07-05.
    "turn": "verb", "left": "noun", "right": "noun", "straight": "adverb",
    "stop": "verb", "corner": "noun", "get": "verb", "minutes": "noun",
    "can't": "verb", "miss": "verb", "take": "verb", "first": "adjective",
    "street": "noun", "second": "adjective", "directions": "noun",
    # Unit 11 (talking about the weather), added 2026-07-05.
    "sunny": "adjective", "rainy": "adjective", "cloudy": "adjective", "cold": "adjective",
    "hot": "adjective", "windy": "adjective", "weather": "noun", "warm": "adjective",
    "raining": "verb", "should": "verb", "umbrella": "noun", "tomorrow": "noun",
    "will": "verb", "be": "verb", "rain": "verb", "let's": "pronoun",
    "idea": "noun", "but": "particle", "going": "verb", "so": "adverb",
    # Unit 12 (clothing: sizes and colors), added 2026-07-05.
    "shirt": "noun", "pants": "noun", "shoes": "noun", "jacket": "noun",
    "dress": "noun", "small": "adjective", "medium": "adjective", "large": "adjective",
    "blue": "adjective", "black": "adjective", "size": "noun", "color": "noun",
    "20": "symbol", "i'll": "pronoun", "we": "pronoun",
    # Unit 13 (talking about feelings), added 2026-07-05.
    "happy": "adjective", "sad": "adjective", "tired": "adjective", "excited": "adjective",
    "worried": "adjective", "feeling": "noun", "little": "adjective", "because": "particle",
    "big": "adjective", "test": "noun", "class": "noun", "almost": "adverb",
    "over": "adjective", "last": "adjective", "year": "noun", "writer": "noun",
    "oh": "particle", "understand": "verb",
    # Unit 14 (phone calls and messages), added 2026-07-05.
    "free": "adjective", "tonight": "noun", "sorry": "adjective", "repeat": "verb",
    "speak": "verb", "more": "adverb", "slowly": "adverb", "hear": "verb",
    "well": "adverb", "6pm": "noun", "message": "noun", "suggest": "verb",
    "meeting": "noun", "place": "noun", "about": "preposition", "that": "pronoun",
    # Unit 15 (handling money and payments), added 2026-07-05.
    "cash": "noun", "card": "noun", "credit": "noun", "debit": "noun",
    "total": "noun", "cards": "noun", "pay": "verb", "tax": "noun",
    "10": "symbol", "by": "preposition", "1": "symbol",
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
    "prefer": "verb", "hate": "verb", "calmer": "adjective", "very": "adverb",
    "strong": "adjective", "why": "adverb", "think": "verb", "prefers": "verb",
    "thinks": "verb",
    # Unit 20 (making basic comparisons), added 2026-07-06.
    "bigger": "adjective", "smaller": "adjective", "cheaper": "adjective", "expensive": "adjective",
    "faster": "adjective", "than": "particle", "nicer": "adjective", "cheapest": "adjective",
    "red": "adjective", "car": "noun", "white": "adjective",
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
    "reports": "noun", "interesting": "adjective", "company": "noun", "downtown": "noun",
    "answer": "verb", "emails": "noun", "sometimes": "adverb", "with": "preposition",
    "clients": "noun", "job": "noun",
    # Unit 24 (describing a home), added 2026-07-06.
    "bedroom": "noun", "kitchen": "noun", "bathroom": "noun", "living": "adjective",
    "room": "noun", "garden": "noun", "many": "adjective", "rooms": "noun",
    "there": "pronoun", "there's": "pronoun", "apartment": "noun", "has": "verb",
    "bedrooms": "noun", "favorite": "adjective", "tell": "verb", "isn't": "verb",
    "balcony": "noun", "upstairs": "adverb", "near": "preposition", "easy": "adjective",
    "eat": "verb",
    # Unit 25 (A2: registering with local authorities), added 2026-07-06.
    "address": "noun", "appointment": "noun", "document": "noun", "proof": "noun",
    "residency": "noun", "form": "noun", "confirmation": "noun", "wondering": "verb",
    "whether": "particle", "could": "verb", "make": "verb", "possible": "adjective",
    "come": "verb", "update": "verb", "moved": "verb", "id": "noun",
    "utility": "noun", "bill": "noun", "bring": "verb", "such": "preposition",
    "lived": "verb", "since": "preposition", "lease": "noun", "when": "adverb",
    "10am": "symbol", "4471": "symbol",
    # Unit 26 (A2: giving opinions with reasons), added 2026-07-06.
    "opinion": "noun", "agree": "verb", "other": "adjective", "hand": "noun",
    "dog": "noun", "dogs": "noun", "space": "noun", "run": "verb",
    "playground": "noun", "fair": "adjective", "point": "noun", "they": "pronoun",
    "move": "verb", "farther": "adverb", "away": "adverb",
    # Unit 27 (A2: opening a bank account), added 2026-07-07 -- part of the
    # nl-en A2 course-routing fix (see backfill_lexemes_nl_en.py's docstring).
    "checking": "adjective", "account": "noun", "monthly": "adjective", "fee": "noun",
    "minimum": "adjective", "balance": "noun", "direct": "adjective", "deposit": "noun",
    "documents": "noun", "you'll": "pronoun", "dmv": "proper_noun", "business": "noun",
    "days": "noun", "keep": "verb", "500": "symbol", "sounds": "verb",
    "teller": "noun", "both": "pronoun",
    # Unit 28 (A2: attending a doctor's appointment), added 2026-07-07 --
    # nl-en's practice-pool extension alongside unit27. "appointment"/
    # "card"/"headache"/"sore"/"throat"/"fever"/"up" already exist (units
    # 25/15/22/16 respectively) -- only genuinely new-to-unit28 tokens
    # added here.
    "medicine": "noun", "prescription": "noun", "follow": "verb", "getting": "verb",
    "worse": "adjective", "insurance": "noun", "i've": "pronoun", "had": "verb",
    "early": "adverb", "confirmed": "verb", "3pm": "symbol", "7724": "symbol",
    "back": "adverb", "within": "preposition", "twice": "adverb", "plenty": "noun",
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
    # Units 30-42 (hobbies through personality), added 2026-07-11 by
    # the prs-en depth-extension worker (a fresh-context worker
    # extending Endless Practice coverage from unit29 to unit42, per a
    # depth audit finding prs-en well below the 10hr publish bar).
    # Every introduced_token across all four lessons of each unit is
    # classified here (not just the tokens used as fillable practice
    # slots), matching this module's own established completeness
    # discipline -- _classify() in every X-en backfill script raises if
    # ANY introduced_token in a covered unit is missing from this dict.
    # Known homograph avoided deliberately: "cook" already has a
    # NOUN entry (unit23 occupation_noun, "I'm a cook"); unit41
    # reintroduces "cook" as a VERB ("I like to cook dinner"), but no
    # new entry was added here and no unit41 practice template uses
    # "cook" as a fillable slot for the verb sense -- same discipline
    # as the existing "close"/"cold"/"report" entries above.
    #
    # Deduplicated 2026-07-11: three concurrent workers (prs-en, fa-en,
    # nl-en depth sprints) each appended a full units 30-42 classification
    # block, leaving every token declared 2-3 times (Python last-wins hid
    # it). Merged down to this single per-unit block; for the ~21 tokens
    # whose duplicates disagreed on POS (mostly contractions and
    # punctuation-attached forms -- he's/we'll, work?/walks,/okay,, post,
    # exercise, once, outside, around, etc.), the kept POS was decided from
    # the token's actual usage in docs/content/realizations/en/ units
    # 30-42, not by last-wins. Lexeme dry-run counts (fa/prs 1011 en, nl
    # 1011 en + 1072 nl) are unchanged by the dedup -- POS is a per-token
    # lookup, so the key set, not the values, drives the count.
    # Unit 30
    "reading": "noun", "cooking": "noun", "painting": "noun", "running": "noun",
    "goes": "verb", "video": "noun", "games": "noun", "always": "adverb",
    "often": "adverb", "cooks": "verb", "rarely": "adverb", "never": "adverb",
    "paint": "verb", "ever": "adverb", "play": "verb", "book": "noun",
    "different": "adjective", "hobbies": "noun", "mornings": "noun", "friends": "noun",
    "paints": "verb",
    # Unit 31
    "tall": "adjective", "short": "adjective", "hair": "noun", "long": "adjective",
    "blond": "adjective", "curly": "adjective", "eyes": "noun", "brown": "adjective",
    "green": "adjective", "glasses": "noun", "wears": "verb", "coworker": "noun",
    "starting": "verb", "mia": "proper_noun", "does.": "verb", "door": "noun",
    "now": "adverb", "same": "adjective", "laugh": "verb", "lot": "noun",
    # Unit 32
    "cat": "noun", "sister's": "noun", "fish": "noun", "bird": "noun",
    "pet": "noun", "pets": "noun", "luna.": "proper_noun", "likes": "verb",
    "friendly": "adjective", "mia,": "proper_noun", "yes,": "particle", "nice!": "adjective",
    "loves": "verb", "ball.": "noun", "named": "verb", "max.": "proper_noun",
    "morning.": "noun", "walks,": "noun", "still": "adverb", "watch": "verb",
    "swim.": "verb",
    # Unit 33
    "bus": "noun", "drive": "verb", "bike": "noun", "ride": "verb",
    "work?": "noun", "takes": "verb", "late": "adjective", "daniel?": "proper_noun",
    "it?": "pronoun", "okay,": "adjective", "parking": "noun", "difficult.": "adjective",
    "drives": "verb", "office.": "noun", "worry": "verb",
    # Unit 34
    "soccer": "noun", "saturdays": "noun", "tennis": "noun", "plays": "verb",
    "basketball": "noun", "swimming": "noun", "yoga": "noun", "exercise": "verb",
    "times": "noun", "swims": "verb", "weekends": "noun", "gym": "noun",
    "pool": "noun", "us": "pronoun", "really": "adverb", "house": "noun",
    "stay": "verb", "active": "adjective", "ways": "noun", "before": "preposition",
    "team": "noun", "already": "adverb", "neighbor": "noun", "even": "adverb",
    "though": "particle", "anyone's": "pronoun", "sport": "noun",
    # Unit 35
    "call": "verb", "mom": "noun", "laptop": "noun", "uses": "verb",
    "tablet": "noun", "reads": "verb", "books": "noun", "computer": "noun",
    "app": "noun", "camera": "noun", "photos": "noun", "text": "verb",
    "sends": "verb", "friend": "noun", "download": "verb", "downloads": "verb",
    "wifi": "noun", "fast": "adjective", "battery": "noun", "low": "adjective",
    "use": "verb", "slow": "adjective", "most": "adverb", "mostly": "adverb",
    "apps": "noun", "map": "noun", "them": "pronoun", "names": "noun",
    "their": "pronoun", "phones": "noun", "differently": "adverb", "people": "noun",
    "instead": "adverb", "maps": "noun", "tries": "verb", "recipes": "noun",
    "laptops": "noun", "chat": "verb",
    # Unit 36
    "course": "noun", "taking": "verb", "community": "noun", "college": "noun",
    "homework": "noun", "subject": "noun", "math": "noun", "study": "verb",
    "studies": "verb", "studying": "verb", "doing": "verb", "photography": "noun",
    "how's": "adverb", "learning": "verb", "teach": "verb", "sometime": "adverb",
    "something": "pronoun", "outside": "adverb", "nights": "noun", "learn": "verb",
    "skills": "noun", "spanish": "proper_noun", "wants": "verb", "travel": "verb",
    "mexico": "proper_noun", "someday": "adverb", "talk": "verb", "classes": "noun",
    "october": "proper_noun",
    # Unit 37
    "party": "noun", "having": "verb", "gift": "noun", "bought": "verb",
    "invite": "verb", "celebrate": "verb", "congratulations": "noun", "coworkers": "noun",
    "congratulate": "verb", "him": "pronoun", "promotion": "noun", "wish": "verb",
    "surprise": "noun", "planning": "verb", "know": "verb", "daniel's": "proper_noun",
    "12th": "symbol", "didn't": "verb", "office": "noun", "perfect": "adjective",
    "buy": "verb", "cake": "noun", "definitely": "adverb", "we'll": "pronoun",
    "were": "verb", "arrived": "verb", "found": "verb", "balloons": "noun",
    "break": "noun", "everyone": "pronoun", "said": "verb", "congratulated": "verb",
    "gave": "verb", "pair": "noun", "framed": "adjective", "took": "verb",
    "herself": "pronoun", "thanked": "verb", "wonderful": "adjective",
    # Unit 38
    "chore": "noun", "washing": "verb", "dishes": "noun", "least": "adverb",
    "laundry": "noun", "sundays": "noun", "vacuum": "verb", "vacuums": "verb",
    "trash": "noun", "out": "particle", "clean": "verb", "wash": "verb",
    "cleans": "verb", "mess": "noun", "coming": "verb", "some": "pronoun",
    "cleaning": "verb", "leave": "verb", "own": "adjective", "habits": "noun",
    "washes": "verb", "mind": "verb", "hates": "verb", "mia's": "proper_noun",
    "luna": "proper_noun", "fur": "noun", "everywhere": "adverb", "guests": "noun",
    "asked": "verb", "vacuumed": "verb", "thankful": "adjective",
    # Unit 39
    "neighborhood": "noun", "helpful": "adjective", "nearby": "adverb", "quiet": "adjective",
    "noisy": "adjective", "mine": "pronoun", "neighbors": "noun", "live": "verb",
    "along": "preposition", "grocery": "noun", "five-minute": "adjective", "say": "verb",
    "might": "verb", "soon": "adverb", "mr": "noun", "lopez": "proper_noun",
    "waters": "verb", "plants": "noun", "neighborhoods": "noun", "restaurants": "noun",
    "shops": "noun", "knows": "verb", "several": "adjective", "says": "verb",
    "hallway": "noun", "lives": "verb", "barks": "verb", "talking": "verb",
    "decided": "verb",
    # Unit 40
    "post office": "noun", "letters": "noun", "letter": "noun", "package": "noun",
    "stamp": "noun", "envelope": "noun", "put": "verb", "mailbox": "noun",
    "postcard": "noun", "express": "verb", "mail": "noun", "regular": "adjective",
    "cost": "verb", "chicago": "proper_noun", "receipt": "noun", "around": "preposition",
    "post": "noun", "sent": "verb", "paid": "verb", "wanted": "verb",
    "quickly": "adverb", "ready": "adjective", "clerk": "noun", "weighed": "verb",
    "chose": "verb", "packages": "noun", "buys": "verb", "writes": "verb",
    "feels": "verb", "personal": "adjective",
    # Unit 41
    "recipe": "noun", "grandmother's": "noun", "ingredient": "noun", "onions": "noun",
    "chop": "verb", "boil": "verb", "pasta": "noun", "taste": "verb",
    "sauce": "noun", "needs": "verb", "salt": "noun", "bake": "verb",
    "forget": "verb", "add": "verb", "making": "verb", "show": "verb",
    "these": "pronoun", "pieces": "noun", "delicious": "adjective", "makes": "verb",
    "using": "verb", "mother's": "noun", "taught": "verb", "without": "preposition",
    "cutting": "verb", "fingers": "noun", "yet": "adverb", "he's": "pronoun",
    "chopped": "verb", "while": "particle", "boiled": "verb", "made": "verb",
    "tasted": "verb",
    # Unit 42
    "funny": "adjective", "hardworking": "adjective", "employee": "noun", "shy": "adjective",
    "calm": "adjective", "talkative": "adjective", "warms": "verb", "sense": "noun",
    "humor": "noun", "gets": "verb", "once": "particle", "project": "noun",
    "finishes": "verb", "tasks": "noun", "meetings": "noun", "comfortable": "adjective",
    "relaxed": "adjective", "personalities": "noun", "meets": "verb", "creative": "adjective",
    "helps": "verb", "relax": "verb", "upset": "adjective", "outgoing": "adjective",
    "organized": "adjective", "plans": "noun", "group": "noun", "patient": "adjective",
    "teaches": "verb", "enjoy": "verb", "spending": "verb",
}

# Units 43-48 (colors, seasons, emergencies, lost items, appointments,
# library borrowing), added 2026-07-12 for the shared X->en backfill scripts.
EN_POS.update({
    "sky": "noun", "grass": "noun", "yellow": "adjective", "sun": "noun",
    "dark": "adjective", "wearing": "verb", "light": "adjective",
    "painted": "verb", "bright": "adjective", "fun": "adjective",
    "our": "pronoun", "presentation": "noun", "choose": "verb",
    "colors": "noun", "looks": "verb", "professional": "adjective",
    "choice": "noun", "everything": "pronoun", "gardens": "noun",
    "especially": "adverb", "beautiful": "adjective", "reminds": "verb",
    "everyday": "adjective", "conversations": "noun",
    "spring": "noun", "flowers": "noun", "bloom": "verb", "summer": "noun",
    "beach": "noun", "fall": "noun", "change": "verb", "winter": "noun",
    "snows": "verb", "season": "noun", "walking": "noun",
    "seasons": "noun", "playing": "noun", "find": "verb",
    "outdoors": "adverb",
    "emergency": "noun", "police": "noun", "ambulance": "noun",
    "fire": "noun", "department": "noun", "911": "symbol",
    "burning": "verb", "smell": "noun", "smoke": "noun", "pan": "noun",
    "caught": "verb", "off": "particle", "stove": "noun",
    "hurry": "verb", "friend's": "pronoun", "goodness": "noun",
    "wait": "verb", "case": "noun", "safer": "adjective",
    "until": "preposition", "elevator": "noun", "stairs": "noun",
    "third": "adjective", "give": "verb", "finally": "adverb",
    "waited": "verb", "notice": "noun", "safe": "adjective",
    "came": "verb", "check": "verb", "relieved": "adjective",
    "hurt": "adjective",
    "lost": "adjective", "keys": "noun", "wallet": "noun",
    "backpack": "noun", "seen": "verb", "anyone": "pronoun",
    "strap": "noun", "where's": "pronoun", "fountain": "noun",
    "you're": "pronoun", "inside": "preposition", "ask": "verb",
    "holding": "verb", "desk": "noun", "lose": "verb", "item": "noun",
    "main": "adjective", "gate": "noun", "describe": "verb",
    "its": "pronoun", "special": "adjective", "details": "noun",
    "staff": "noun", "called": "verb", "told": "verb", "whole": "adjective",
    "story": "noun", "track": "noun", "things": "noun",
    "available": "adjective", "confirm": "verb", "reschedule": "verb",
    "max": "proper_noun", "seems": "verb", "lately": "adverb",
    "due": "adjective", "yearly": "adjective", "checkup": "noun",
    "vet": "noun", "dog's": "pronoun", "max's": "pronoun",
    "dentist": "noun", "service": "noun", "you'd": "pronoun",
    "receptionist": "noun", "changes": "noun", "nervous": "adjective",
    "borrow": "verb", "return": "verb", "borrowed": "verb",
    "weeks": "noun", "cookbook": "noun", "fill": "verb",
    "visiting": "verb", "libraries": "noun", "let": "verb",
    "items": "noun", "few": "adjective", "librarian": "noun",
    "finished": "verb", "used": "verb", "started": "verb",
    "borrowing": "noun", "returned": "verb", "picked": "verb",
    "got": "verb", "checked": "verb", "practice": "noun",
    "teaching": "noun", "reminded": "verb",
})

# BEGIN volume practice singleton tags (generated 2026-07-13)
VOLUME_PRACTICE_SINGLETON_TAGS = {'3rd': ['volume_fa_en_a1_unit04_day_ordinal_12_single'], 'bad': ['volume_fa_en_a1_unit01_item_05_single', 'volume_nl_en_a1_unit01_item_05_single', 'volume_prs_en_a1_unit01_item_06_single'], 'boil': ['volume_fa_en_a1_unit41_item_04_single'], 'cat': ['volume_nl_en_a1_unit32_item_10_single'], 'chop': ['volume_prs_en_a1_unit41_item_03_single'], 'day': ['volume_fa_en_a1_unit01_item_03_single', 'volume_nl_en_a1_unit01_item_03_single', 'volume_prs_en_a1_unit01_time_period_02_single'], 'friday': ['volume_fa_en_a1_unit04_weekday_09_single', 'volume_prs_en_a1_unit04_weekday_10_single'], 'hi': ['volume_prs_en_a1_unit01_item_04_single'], 'july': ['volume_fa_en_a1_unit04_month_10_single', 'volume_prs_en_a1_unit04_month_12_single'], 'leila': ['volume_fa_en_a1_unit02_person_name_07_single', 'volume_nl_en_a1_unit02_person_name_06_single', 'volume_prs_en_a1_unit02_person_name_08_single'], 'letter': ['volume_prs_en_a1_unit40_item_05_single'], 'new': ['volume_nl_en_a1_unit02_new_08_single'], 'noisy': ['volume_prs_en_a1_unit39_item_07_single'], 'one': ['volume_nl_en_a1_unit03_item_11_single', 'volume_nl_en_a1_unit03_item_12_single'], 'park': ['volume_fa_en_a1_unit39_item_06_single'], 'party': ['volume_prs_en_a1_unit37_item_11_single'], 'phone': ['volume_fa_en_a1_unit35_item_11_single', 'volume_nl_en_a1_unit35_item_04_single'], 'see': ['volume_fa_en_a1_unit01_farewell_verb_02_single', 'volume_nl_en_a1_unit01_see_02_single'], 'shy': ['volume_fa_en_a1_unit42_item_01_single', 'volume_nl_en_a1_unit42_item_01_single', 'volume_prs_en_a1_unit42_item_01_single'], 'soccer': ['volume_nl_en_a1_unit34_item_07_single'], 'test': ['volume_fa_en_a1_unit36_item_08_single'], 'trash': ['volume_prs_en_a1_unit38_item_09_single'], 'work': ['volume_nl_en_a1_unit02_work_09_single']}
# END volume practice singleton tags

def en_agreement_tags(token: str) -> dict[str, object]:
    semantics: list[str] = []

    for semantic in VOLUME_PRACTICE_SINGLETON_TAGS.get(token, ()):
        semantics.append(semantic)
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
    # Unit 30 (hobbies): 4-member gerund-noun tag, verified all four fit
    # "I like {item}." (reading/cooking/painting/running are all
    # grammatical there). "video games" is a 2-word compound, deliberately
    # excluded (a single-token slot can't fill it).
    if token in {"reading", "cooking", "painting", "running"}:
        semantics.append("hobby_noun")
    # Unit 30: 5-member frequency-adverb tag (includes "sometimes",
    # already classified since unit23, tagged additively here), verified
    # all five fit "I {item} play tennis."
    if token in {"always", "often", "sometimes", "rarely", "never"}:
        semantics.append("frequency_adverb")
    # Unit 31 (appearance): 3-member eye-color tag (includes "blue",
    # already classified since unit12's clothing_color, tagged additively
    # here), verified all three fit "Her eyes are {item}." Bare-word
    # recognition only (mc/listen/translation) -- 3 members is at the
    # multiple_choice/listen_select floor, not enough for matching_pairs.
    if token in {"blue", "brown", "green"}:
        semantics.append("eye_color")
    # Unit 31: 2-member height tag, word_order/translation only (below
    # the 3-candidate mc/listen_select floor). Verified both fit "My
    # brother is {item}."
    if token in {"tall", "short"}:
        semantics.append("height_adj")
    # Unit 32 (animals): 4-member pet-noun tag (includes "dog", already
    # classified since unit26's dogpark_noun, tagged additively here),
    # verified all four fit "I have a {item}."
    if token in {"dog", "cat", "fish", "bird"}:
        semantics.append("pet_noun")
    # Unit 33 (transportation): 4-member tag (includes "train"/"car",
    # already classified since unit21/unit20 respectively, tagged
    # additively here), verified all four fit "I take the {item} to
    # work." "walk" is deliberately excluded -- already classified
    # "noun" from unit17's own different sense, and "I take the walk to
    # work" is not idiomatic.
    if token in {"bus", "train", "car", "bike"}:
        semantics.append("transport_noun")
    # Unit 34 (sports): 3-member tag, verified all three fit "We play
    # {item}." "swimming"/"yoga"/"exercise" are deliberately excluded --
    # each needs its own different collocating verb ("go swimming", "do
    # yoga", "do exercise"), not "play".
    if token in {"soccer", "tennis", "basketball"}:
        semantics.append("play_sport_noun")
    # Unit 35 (technology): 6-member tag (includes "phone", already
    # classified since unit03's phone_phrase, tagged additively here),
    # verified all six fit "I have a new {item}."
    if token in {"phone", "laptop", "tablet", "computer", "app", "camera"}:
        semantics.append("device_noun")
    # Unit 36 (education): 6-member bare-word recognition tag (includes
    # "class"/"student"/"test", already classified since unit13/unit01/
    # unit13 respectively, tagged additively here).
    if token in {"class", "course", "student", "homework", "subject", "test"}:
        semantics.append("education_noun")
    # Narrower than education_noun: only the 3 members that take a
    # countable "a {item} every Friday" article naturally (excludes
    # "student"/"subject", which don't fit that frame at all, and
    # "homework", which is uncountable and can't take "a" -- "I have a
    # homework every Friday" is ungrammatical).
    if token in {"class", "course", "test"}:
        semantics.append("recurring_class_noun")
    # Unit 37 (celebrations): 4-member bare-word recognition tag
    # (includes "birthday", already classified since unit04, tagged
    # additively here). Deliberately NOT used in any shared generative
    # frame -- these four don't collocate uniformly ("having a
    # birthday"/"having a gift" both read oddly compared to "having a
    # party"), same recognition-only discipline as bureaucracy_noun.
    if token in {"birthday", "party", "gift", "congratulations"}:
        semantics.append("celebration_noun")
    # Single-member tag, word_order/translation only (same precedent as
    # the existing single-member "superlative_adj"): "party" is the only
    # celebration_noun member that fits "We are having a {item} on
    # Saturday." naturally.
    if token == "party":
        semantics.append("party_word")
    # Unit 38 (household): 4-member bare-word recognition tag.
    if token in {"chore", "dishes", "laundry", "trash"}:
        semantics.append("chore_noun")
    # Single-member tag, word_order/translation only: "trash" is the only
    # chore_noun member that fits "Can you take out the {item}?"
    if token == "trash":
        semantics.append("trash_word")
    # Unit 39 (neighborhood): 3-member adjective tag (includes
    # "friendly", already classified since unit32, tagged additively
    # here), verified all three fit "My neighbors are very {item}."
    if token in {"quiet", "noisy", "friendly"}:
        semantics.append("neighborhood_adj")
    # Unit 40 (post office): 5-member bare-word recognition tag.
    if token in {"letter", "package", "stamp", "envelope", "mailbox"}:
        semantics.append("post_noun")
    # Narrower than post_noun: only the 2 members that fit "I need to
    # send a {item}." naturally ("send a stamp"/"send an envelope"/"send
    # a mailbox" are not real phrases).
    if token in {"letter", "package"}:
        semantics.append("sendable_noun")
    # Unit 41 (cooking): 3-member verb tag, bare-word recognition only.
    # "cook" is deliberately excluded -- already classified "noun" (the
    # occupation sense, unit23), see the module-level comment on EN_POS
    # above documenting this homograph.
    if token in {"chop", "boil", "taste"}:
        semantics.append("cooking_verb")
    # Single-member tag, word_order/translation only: "chop" is the only
    # cooking_verb member that fits "Can you {item} the onions for me?"
    if token == "chop":
        semantics.append("chop_word")
    # Unit 42 (personality): 6-member adjective tag (includes "friendly",
    # already classified since unit32, tagged additively here), verified
    # all six fit "My neighbor is very {item}."
    if token in {"friendly", "funny", "hardworking", "shy", "calm", "talkative"}:
        semantics.append("personality_adj")
    # Unit 30 (hobbies): 4-member gerund-noun tag, all safe in "I like
    # {item}." (every member is a genuine gerund/hobby noun with the same
    # syntax -- "I like reading."/"I like cooking."/"I like painting."/
    # "I like running." -- no article needed for any of them).
    if token in {"reading", "cooking", "painting", "running"}:
        semantics.append("hobby_noun")
    # Unit 30: 5-member frequency-adverb tag, all safe as the pre-verb
    # adverb in "She {item} cooks dinner." (standard English mid-position
    # frequency-adverb placement, grammatical for all five).
    if token in {"always", "often", "sometimes", "rarely", "never"}:
        semantics.append("frequency_adverb")
    # Unit 31 (appearance): reuses A1 unit12's existing 'color' tag scope
    # (same course level, per AUTHORING_GUIDE.md #18) by adding the two new
    # eye-color adjectives taught here. Restricted to the 3-member subset
    # genuinely safe in "Her eyes are {item}." -- "blue"/"brown"/"green" are
    # all real, common eye colors; "black"/"red"/"white" (unit12's car-color
    # members) are deliberately excluded from this narrower eye_color tag
    # since black/white eyes would be a strange claim and red isn't a real
    # eye color.
    if token in {"blue", "brown", "green"}:
        semantics.append("eye_color")
    # Unit 32 (animals): 4-member pet-noun tag, all safe in "I have a
    # {item}." (four common countable singular pet nouns).
    if token in {"dog", "cat", "fish", "bird"}:
        semantics.append("pet_noun")
    # Unit 33 (transportation): 4-member bare-word recognition tag. Each
    # mode collocates with a DIFFERENT verb in the real content ("take the
    # bus/train", "drive my car", "ride my bike") so, same discipline as
    # unit25's bureaucracy_noun, deliberately NOT used in any single shared
    # generative frame.
    if token in {"bus", "train", "car", "bike"}:
        semantics.append("transport_noun")
    # Unit 34 (sports): 5-member bare-word recognition tag for every sport/
    # activity noun this unit introduces.
    if token in {"soccer", "tennis", "basketball", "swimming", "yoga"}:
        semantics.append("sport_noun")
    # Narrower than sport_noun: the 3-member subset that's a true ball sport
    # you "play" (excludes swimming/yoga, which use different verbs --
    # "play swimming"/"play yoga" are ungrammatical), safe in "We play
    # {item}."
    if token in {"soccer", "tennis", "basketball"}:
        semantics.append("ball_sport")
    # Unit 35 (technology): 5-member device-noun tag, all safe in "I have a
    # {item}." (five common countable singular devices).
    if token in {"phone", "laptop", "tablet", "computer", "camera"}:
        semantics.append("device_noun")
    # Unit 36 (education): narrower 3-member subset of this unit's
    # education nouns that's genuinely safe in "I have a {item}." --
    # "class"/"course"/"test" are all countable singular nouns that
    # collocate with "have a"; "homework"/"subject" are deliberately
    # excluded (homework is uncountable -- "I have a homework" is
    # ungrammatical; "I have a subject" isn't a natural claim either).
    if token in {"class", "course", "test"}:
        semantics.append("class_noun")
    # Unit 37 (celebrations): 4-member bare-word recognition tag. These
    # nouns don't collocate uniformly with one verb ("have a party"/"have a
    # cake" work, "have a birthday" reads oddly as a claim, "have a gift" is
    # ambiguous between giving and receiving), so kept recognition-only,
    # same discipline as unit25's bureaucracy_noun.
    if token in {"birthday", "party", "gift", "cake"}:
        semantics.append("celebration_noun")
    # Unit 38 (household): 3-member bare-word recognition tag for this
    # unit's single-token chore nouns. Each pairs with its own fixed verb in
    # the real content ("do the dishes"/"do the laundry"/"take out the
    # trash"), so kept recognition-only.
    if token in {"dishes", "laundry", "trash"}:
        semantics.append("chore_noun")
    # Unit 39 (neighborhood): 4-member tag, all safe in "There's a {item}
    # nearby." (mirrors unit24's room_noun "There's a {item}." precedent).
    if token in {"neighbor", "park", "store", "street"}:
        semantics.append("neighborhood_noun")
    # Unit 40 (post office): 4-member bare-word recognition tag for this
    # unit's single-token mail-item nouns. Kept recognition-only (no single
    # verb collocates naturally across all four -- "send a letter/package"
    # works, "send a stamp/envelope" reads oddly, since those are things you
    # buy or use, not send).
    if token in {"letter", "package", "stamp", "envelope"}:
        semantics.append("mail_noun")
    # Unit 41 (cooking): 3-member cooking-verb tag, all safe as the bare
    # infinitive in "Can you {item} it?" (three real cooking actions with
    # identical syntax).
    if token in {"chop", "boil", "taste"}:
        semantics.append("cooking_verb")
    # Unit 42 (personality): 6-member adjective tag, all safe in "My
    # neighbor is very {item}." (six genuine personality adjectives, all
    # gradable with "very").
    if token in {"friendly", "funny", "hardworking", "shy", "calm", "talkative"}:
        semantics.append("personality_adjective")
    # Units 30-42 (nl-en depth-completion sprint, added 2026-07-11) --
    # every semantic tag a new nl-en practice-pack slot preset references.
    # Unit 30 (hobbies): 4-member gerund-noun tag, verified all four
    # collocate in "I like {item}." (the unit's own lesson03 teaches this
    # exact pattern). Excludes "video games" (two-word compound).
    if token in {"reading", "cooking", "painting", "running"}:
        semantics.append("hobby_activity")
    # Unit 31 (appearance): 4-member adjective tag, bare-word recognition
    # only. Excludes "hair" (a noun, would break part_of_speech
    # uniformity within the tag).
    if token in {"tall", "short", "blond", "curly"}:
        semantics.append("trait_adj")
    # Unit 31: 3-member eye-color adjective tag, used in the generative
    # frame "Her eyes are {item}." -- directly matches the unit's own
    # taught sentence "Her eyes are blue."
    if token in {"blue", "brown", "green"}:
        semantics.append("eye_color")
    # Unit 32 (animals): 4-member noun tag, used in "I have a {item}."
    # (verified consonant-initial, safe with "a"; matches the unit's own
    # taught sentence "I have a dog."). Excludes the hypernym "pet".
    if token in {"dog", "cat", "fish", "bird"}:
        semantics.append("pet_animal")
    # Unit 33 (transportation): 4-member noun tag, bare-word recognition
    # only -- the unit's own overlay notes flag that each vehicle takes
    # its own verb (take the bus/train, drive the car, ride the bike), so
    # no single shared frame is safe. Excludes "walk" (used as a verb).
    if token in {"bus", "train", "car", "bike"}:
        semantics.append("vehicle_noun")
    # Unit 34 (sports): 6-member noun tag, bare-word recognition/matching
    # only (mixed play/go/do collocations across members).
    if token in {"soccer", "tennis", "basketball", "swimming", "yoga", "exercise"}:
        semantics.append("sport_noun")
    # Unit 34: narrower 3-member subset of sport_noun, verified all three
    # take "play" (unlike swimming/yoga, which need go/do) -- used in the
    # generative frame "We play {item}."
    if token in {"soccer", "tennis", "basketball"}:
        semantics.append("play_sport")
    # Unit 35 (technology): 6-member noun tag, bare-word recognition/
    # matching only (includes "app").
    if token in {"phone", "laptop", "tablet", "computer", "app", "camera"}:
        semantics.append("device_noun")
    # Unit 35: narrower 5-member subset excluding "app" (needs "an", not
    # "a") -- used in the generative frame "I have a {item}."
    if token in {"phone", "laptop", "tablet", "computer", "camera"}:
        semantics.append("device_noun_a")
    # Unit 36 (education): 6-member noun tag, bare-word recognition only
    # (mixed collocations -- "I have a {item}" doesn't generalize).
    if token in {"class", "course", "student", "homework", "subject", "test"}:
        semantics.append("education_noun")
    # Unit 37 (celebrations): 4-member noun tag, bare-word recognition
    # only. Excludes "invite"/"celebrate" (verbs, would break
    # part_of_speech uniformity).
    if token in {"birthday", "party", "gift", "congratulations"}:
        semantics.append("celebration_noun")
    # Unit 38 (household): 4-member noun tag, bare-word recognition only.
    # Excludes "vacuum"/"clean" (verbs here).
    if token in {"chore", "dishes", "laundry", "trash"}:
        semantics.append("household_noun")
    # Unit 39 (neighborhood): 3-member adjective tag, bare-word
    # recognition only -- "friendly" collides with unit32's/unit42's
    # own uses of the same word (same POS, reused not redeclared).
    if token in {"quiet", "noisy", "friendly"}:
        semantics.append("neighborhood_adj")
    # Unit 40 (post): 5-member noun tag, bare-word recognition only.
    # Excludes the two-word compound "post office".
    if token in {"letter", "package", "stamp", "envelope", "mailbox"}:
        semantics.append("post_noun")
    # Unit 41 (cooking): 3-member verb tag, bare-word recognition only.
    # Deliberately excludes "cook" -- already classified "noun" (unit23's
    # occupation sense), so a verb-POS slot would find zero candidates
    # for it.
    if token in {"chop", "boil", "taste"}:
        semantics.append("cooking_verb")
    # Unit 42 (personality): 6-member adjective tag, used in the
    # generative frame "She is {item}." -- verified grammatical for
    # every member, matching the unit's own predicate-adjective examples.
    if token in {"friendly", "funny", "hardworking", "shy", "calm", "talkative"}:
        semantics.append("personality_adj")

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
