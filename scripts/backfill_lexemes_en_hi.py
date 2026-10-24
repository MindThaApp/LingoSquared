#!/usr/bin/env python3
"""Idempotently backfill en-hi (Hindi target) lexemes for the "Hindi A1"
course, so en-hi practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: en->X backfill. All plumbing lives in
scripts/_target_lexeme_backfill_common.py (see its docstring for the tag
scheme); this file is data only: one hand-written English gloss and one part
of speech per citation form.

Scope: A1 (the "en-hi" manifest group, units 01-19) and A2 (the "en-hi-a2"
group, units 20-25, added 2026-10-24 in session 11). A2 is a separate Course
row, so its lexemes are first-sight per course and carry their own gloss and
part-of-speech tables (GLOSSES_A2, POS_SETS_A2): a token re-taught in A2 is
glossed for the sense A2 teaches. B1+ is not classified yet; extend LEVELS
and the tables together.

Glossing rules followed here (PRACTICE_PACK_RECIPE.md §0.1, §6.6):
* the gloss is the sense the unit actually teaches at first sight,
* inflected forms say who they belong to ("get up (habitual, masc.)"),
  gender pairs are glossed "(masc.)"/"(fem.)" so the two are never
  interchangeable answers.

Normalization: Devanagari has no case, so normalize() is the identity with
ONE exception. unit01 lesson03 dialogue lines list the speaker labels in
their romanized spelling ("Priya", "Arjun") as introduced_tokens, although
the spoken text writes the same names as प्रिया and अर्जुन. Both pairs are
the same word, so the romanized spelling is mapped to the Devanagari
citation form (otherwise a Latin-script lexeme would enter the Hindi pools).
No nukta/chandrabindu/anusvara spelling variants exist in the realizations;
है/हैं and मेरा/मेरे etc. are genuinely different forms and stay separate.

Run (after the en-hi course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_hi.py

Add --dry-run to classify without touching the database.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _target_lexeme_backfill_common import (  # noqa: E402
    classify,
    manifest_group,
    pos_lookup,
    run,
    split_words,
)

LANG = "hi"
LEVELS = {"a1": "en-hi", "a2": "en-hi-a2"}

PROPER_NOUNS = {"प्रिया", "अर्जुन", "भारत", "लंदन", "अमेरिका", "दिल्ली", "मुंबई"}

# Romanized speaker-label spellings -> the Devanagari citation form.
_SPELLING_VARIANTS = {"Priya": "प्रिया", "Arjun": "अर्जुन"}


def normalize(token: str) -> str:
    return _SPELLING_VARIANTS.get(token, token)


GLOSSES: dict[str, str] = {
    # unit01 greetings
    "आप": "you (formal, respectful)", "तुम": "you (informal, familiar)",
    "कैसे": "how (masc. plural or formal; also: in what way)", "हैं": "are; is (with a formal or plural subject)",
    "कैसी": "how (fem.)", "हो": "you are (informal)", "मैं": "I",
    "ठीक": "fine; okay", "हूँ": "I am", "शुक्रिया": "thank you", "और": "and; more",
    "नमस्ते": "hello; goodbye", "नमस्कार": "hello (more formal, respectful)",
    "फिर": "again; then", "मिलेंगे": "we will meet", "अलविदा": "goodbye; farewell",
    "मिलते": "meet (habitual, masc. plural, or we)", "शुभ": "auspicious; good",
    "रात्रि": "night (formal)", "आपका": "your (formal, masc.)", "दिन": "day",
    "अच्छा": "good; nice (masc.); I see", "रहे": "may it be; stay",
    "नाम": "name", "क्या": "what; (question word)", "है": "is (he, she, it)",
    "तुम्हारा": "your (informal, masc.)", "मेरा": "my (masc.)", "प्रिया": "Priya",
    "आपसे": "with you (formal)", "मिलकर": "on meeting", "खुशी": "happiness; joy",
    "हुई": "happened; became (fem.)", "मुझे": "to me; me", "भी": "also; too",
    "कहाँ": "where", "से": "from; with", "भारत": "India",
    "यह": "this", "तुम्हारी": "your (informal, fem.)", "पहली": "first (fem.)",
    "बार": "time (occasion)", "हाँ": "yes", "मेरी": "my (fem.)", "योग": "yoga",
    "सीखना": "to learn", "चाहता": "want (masc.)", "अर्जुन": "Arjun",
    "तुमसे": "with you (informal)", "लगा": "felt; seemed (masc.)",
    "लेकिन": "but", "अभी": "now; currently", "लंदन": "London", "में": "in",
    "रहता": "live (habitual, masc.)", "अमेरिका": "America", "चाहती": "want (fem.)",
    "करती": "do (habitual, fem.)", "नहीं": "no; not", "सीख": "learn (stem)",
    "रही": "in progress (fem., as in am learning)", "चलो": "let's go; come on",
    "शुरू": "start; beginning", "करते": "do (habitual, masc. plural, or we)",
    # unit02 numbers
    "शून्य": "zero", "एक": "one", "दो": "two", "तीन": "three", "चार": "four",
    "पाँच": "five", "छह": "six", "सात": "seven", "आठ": "eight", "नौ": "nine",
    "दस": "ten", "ग्यारह": "eleven", "बारह": "twelve", "पंद्रह": "fifteen",
    "बीस": "twenty", "तीस": "thirty", "पचास": "fifty", "सौ": "hundred",
    "कीमत": "price; cost", "रुपये": "rupees", "इसकी": "its (of this, fem.)",
    "फ़ोन": "phone", "नंबर": "number", "आपकी": "your (formal, fem.)",
    "उम्र": "age", "साल": "year",
    # unit03 dates
    "आज": "today", "सोमवार": "Monday", "मंगलवार": "Tuesday",
    "बुधवार": "Wednesday", "गुरुवार": "Thursday", "शुक्रवार": "Friday",
    "शनिवार": "Saturday", "रविवार": "Sunday", "कौन": "who; which",
    "सा": "(particle: with 'who' it makes 'which')", "क्लास": "class",
    "को": "on; to", "जनवरी": "January", "फ़रवरी": "February", "मार्च": "March",
    "अप्रैल": "April", "मई": "May", "जून": "June", "जुलाई": "July",
    "अगस्त": "August", "सितंबर": "September", "अक्टूबर": "October",
    "नवंबर": "November", "दिसंबर": "December", "तारीख़": "date (day of the month)",
    "कितनी": "how many; how much (fem.)", "कब": "when", "अगली": "next (fem.)",
    "जन्मदिन": "birthday", "कोई": "any; some", "बात": "matter; talk",
    # unit04 time
    "बजे": "o'clock; at ... o'clock", "बजा": "o'clock (only in 'it is one o'clock')",
    "कितने": "how many; how much (masc.)", "सुबह": "morning",
    "दोपहर": "afternoon; noon", "शाम": "evening", "रात": "night",
    "कल": "tomorrow; yesterday",
    # unit05 family
    "परिवार": "family", "पिता": "father", "माँ": "mother", "भाई": "brother",
    "बहन": "sister", "माता-पिता": "parents",
    "मेरे": "my (masc. plural, or respectful)", "दादा": "paternal grandfather",
    "दादी": "paternal grandmother", "नाना": "maternal grandfather",
    "नानी": "maternal grandmother", "दिल्ली": "Delhi", "मुंबई": "Mumbai",
    "के": "of (before a masc. plural or respected noun)",
    "रहती": "live (habitual, fem.)", "रहते": "live (habitual, masc. plural, or respectful)",
    "बड़ा": "older; big (masc.)", "बड़ी": "older; big (fem.)",
    "छोटा": "younger; small (masc.)", "छोटी": "younger; small (fem.)",
    "तुम्हारे": "your (informal, masc. plural, or respectful)",
    # unit06 food
    "खाना": "food; meal", "चाय": "tea", "कॉफ़ी": "coffee", "पानी": "water",
    "जूस": "juice", "चाहिए": "would like; need", "आपको": "to you (formal)",
    "तुम्हें": "to you (informal)", "बहुत": "very; a lot",
    "स्वादिष्ट": "delicious; tasty", "रोटी": "flatbread", "चावल": "rice",
    "सब्ज़ी": "vegetable dish", "दाल": "lentils", "कप": "cup", "गिलास": "glass",
    "प्लेट": "plate", "कृपया": "please", "कुछ": "something; anything",
    "बस": "enough; that's all", "खाते": "eat (habitual, masc. plural, or we)",
    "या": "or",
    # unit07 shopping
    "दुकान": "shop", "बाज़ार": "market", "दुकानदार": "shopkeeper",
    "कमीज़": "shirt", "बैग": "bag", "टोपी": "hat",
    "जी": "respectful particle (like 'sir' or 'madam')", "सिर्फ़": "only; just",
    "बताओ": "tell! (informal command)", "का": "of (masc.)", "की": "of (fem.)",
    "सस्ता": "cheap (masc.)", "महंगा": "expensive (masc.)",
    "सस्ती": "cheap (fem.)", "महंगी": "expensive (fem.)",
    "खरीदना": "to buy", "खरीदते": "buy (habitual, masc. plural, or we)",
    # unit08 places
    "घर": "home; house", "स्कूल": "school", "अस्पताल": "hospital",
    "बैंक": "bank", "पार्क": "park", "स्टेशन": "station", "यहाँ": "here",
    "वहाँ": "there", "पास": "near", "दूर": "far", "सामने": "in front of",
    "पीछे": "behind", "डाकघर": "post office", "थोड़ा": "a little",
    "तो": "so; then (emphasis)", "सही": "correct; right",
    # unit09 directions
    "सीधे": "straight ahead", "बाएँ": "left", "दाएँ": "right",
    "जाओ": "go! (informal command)", "मुड़ो": "turn! (informal command)",
    "गिनो": "count! (informal command)", "जाऊँ": "I should go",
    "तक": "until; up to", "पहले": "first; before",
    "नुक्कड़": "street corner", "पर": "at; on",
    "समझ": "understand (stem)", "गया": "went; gone (masc.); also marks completion, as in understood",
    # unit10 routines
    "उठता": "get up (habitual, masc.)", "उठती": "get up (habitual, fem.)",
    "रोज़": "every day", "नाश्ता": "breakfast", "करता": "do (habitual, masc.)",
    "काम": "work", "जाता": "go (habitual, masc.)", "जाती": "go (habitual, fem.)",
    "वह": "he; she; that", "वे": "they", "सोता": "sleep (habitual, masc.)",
    "सोती": "sleep (habitual, fem.)",
    "उठते": "get up (habitual, masc. plural, or informal you to a man)",
    "सोते": "sleep (habitual, masc. plural, or informal you to a man)",
    "वापस": "back", "आता": "come (habitual, masc.)", "आती": "come (habitual, fem.)",
    "खाता": "eat (habitual, masc.)", "खाती": "eat (habitual, fem.)",
    "आते": "come (habitual, masc. plural, or informal you to a man)",
    # unit11 plans
    "फ़िल्म": "movie", "देखते": "watch (habitual, masc. plural, or we)",
    "साथ": "together; with", "पीते": "drink (habitual, masc. plural, or we)",
    "सुझाव": "suggestion", "विचार": "idea; thought", "व्यस्त": "busy",
    "माफ़": "sorry; forgiven", "करना": "to do", "हम": "we",
    "संदेश": "message",
    # unit12 past events
    "था": "was (masc.)", "थी": "was (fem.)", "कैसा": "how (masc. singular)",
    "अच्छी": "good; nice (fem.)", "गई": "went; gone (fem.)",
    "मिला": "met (masc.)", "मिली": "met (fem.)",
    "मिले": "met (we, they, or masc. plural)",
    # unit13 preferences
    "पसंद": "liking; liked", "संगीत": "music", "किताब": "book",
    "किताबें": "books", "खेल": "sport; game", "ज़्यादा": "more",
    # unit14 comparisons
    "लंबा": "tall; long (masc.)", "लंबी": "tall; long (fem.)",
    "नया": "new (masc.)", "नई": "new (fem.)",
    # unit15 travel
    "जाना": "to go", "टिकट": "ticket", "ट्रेन": "train",
    "प्लेटफ़ॉर्म": "platform", "हमें": "to us; for us",
    # unit16 health
    "सिर": "head", "दर्द": "pain; ache", "बुखार": "fever", "डॉक्टर": "doctor",
    "आराम": "rest", "दवा": "medicine", "करो": "do! (informal command)",
    # unit17 work
    "शिक्षक": "teacher (male)", "शिक्षिका": "teacher (female)",
    "इंजीनियर": "engineer", "दफ़्तर": "office",
    "जाते": "go (habitual, masc. plural, or informal you to a man)",
    # unit18 housing
    "कमरा": "room", "कमरे": "rooms", "रसोई": "kitchen", "बाथरूम": "bathroom",
    "बेडरूम": "bedroom", "मेज़": "table", "कुर्सी": "chair",
    "कुर्सियाँ": "chairs", "बिस्तर": "bed", "खिड़की": "window",
    "खिड़कियाँ": "windows",
    # unit19 weather
    "मौसम": "weather", "धूप": "sun; sunshine", "बारिश": "rain", "हवा": "wind",
    "गर्म": "hot", "ठंडा": "cold (masc.)", "ठंडी": "cold (fem.)",
    "बादल": "cloud; clouds", "बुरा": "bad (masc.)", "बाहर": "outside",
}

POS_SETS = {
    "proper_noun": PROPER_NOUNS,
    "pronoun": split_words(
        "आप तुम मैं क्या यह वह वे हम हमें मुझे आपसे तुमसे आपको तुम्हें कौन कुछ कोई "
        "आपका आपकी तुम्हारा तुम्हारी तुम्हारे मेरा मेरी मेरे इसकी कितने कितनी"
    ),
    "preposition": split_words("से में को के का की तक पर"),
    "particle": split_words("और भी नहीं लेकिन सा तो जी या बस"),
    "adjective": split_words(
        "कैसे कैसी कैसा अच्छा अच्छी ठीक शुभ पहली अगली बड़ा बड़ी छोटा छोटी "
        "स्वादिष्ट सस्ता महंगा सस्ती महंगी सही व्यस्त ज़्यादा लंबा लंबी नया नई "
        "गर्म ठंडा ठंडी बुरा पसंद"
    ),
    "adverb": split_words(
        "कहाँ फिर अभी कब कल बहुत सिर्फ़ यहाँ वहाँ पास दूर सामने पीछे थोड़ा सीधे बाएँ "
        "दाएँ पहले रोज़ वापस साथ बाहर कृपया"
    ),
    "verb": split_words(
        "हैं हो हूँ है रहे मिलेंगे मिलते मिलकर हुई चाहता चाहती सीखना सीख रही "
        "करती करता करते करना करो रहता रहती रहते लगा चलो चाहिए खाते खरीदना खरीदते "
        "बताओ जाओ मुड़ो गिनो जाऊँ समझ गया उठता उठती जाता जाती सोता सोती उठते सोते "
        "आता आती खाता खाती आते देखते पीते था थी गई मिला मिली मिले जाना जाते"
    ),
    "phrase": split_words("शुक्रिया नमस्ते नमस्कार अलविदा हाँ"),
}
POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())

CATEGORY_TAGS: dict[str, list[str]] = {}
for _tag, _words in {
    "hi_number": "शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह पंद्रह बीस "
                 "तीस पचास सौ",
    "hi_weekday": "सोमवार मंगलवार बुधवार गुरुवार शुक्रवार शनिवार रविवार",
    "hi_month": "जनवरी फ़रवरी मार्च अप्रैल मई जून जुलाई अगस्त सितंबर अक्टूबर नवंबर दिसंबर",
    "hi_family": "परिवार पिता माँ भाई बहन माता-पिता दादा दादी नाना नानी",
}.items():
    for _w in _words.split():
        CATEGORY_TAGS.setdefault(_w, []).append(_tag)

part_of_speech = pos_lookup(POS_SETS)


# ---------------------------------------------------------------------------
# A2 (course "Hindi A2", manifest group en-hi-a2, units 20-25). Separate
# tables: A2 is its own Course, so every token is first-sight again and is
# glossed for the sense the A2 unit teaches. Each gloss is hand-written; no
# Devanagari and no transliteration inside a gloss. Forms that differ by
# gender or number say so, so a bare-word prompt names exactly one form.
# ---------------------------------------------------------------------------
GLOSSES_A2: dict[str, str] = {
    # unit20 changing an address
    "पता": "address", "नया": "new (masc.)", "नई": "new (fem.)",
    "मेरा": "my (masc.)", "अपना": "one's own (masc.)",
    "अपनी": "one's own (fem.)", "अपने": "one's own (masc. plural, or respectful)",
    "बदलना": "to change", "मुझे": "to me; me", "है": "is (he, she, it)",
    "आधार": "Aadhaar (India's national ID system)", "कार्ड": "card",
    "केंद्र": "centre", "जाना": "to go",
    "दस्तावेज़": "document", "फ़ॉर्म": "form", "भरना": "to fill in",
    "ने": "(marks the doer of a past action)",
    "मैंने": "I (as the doer of a past action)",
    "भरा": "filled in (past, masc. singular object)", "लाना": "to bring",
    "लाया": "brought (masc.)", "लाए": "brought (you, formal; or masc. plural)",
    "क्या": "what; (question word)", "आप": "you (formal, respectful)",
    "हाँ": "yes", "मैं": "I", "बदला": "changed (past, masc. singular object)",
    "आपको": "to you (formal)", "अर्जुन": "Arjun", "प्रिया": "Priya",
    "क्लर्क": "clerk", "गांधी": "Gandhi", "रोड": "road", "दिल्ली": "Delhi",
    "आपका": "your (formal, masc.)",
    # unit21 giving an opinion
    "फ़िल्म": "film; movie", "यह": "this", "कैसी": "how (fem.)",
    "लगना": "to seem; to feel (to someone)", "लगती": "seems (fem.)",
    "अच्छी": "good; nice (fem.)", "कहानी": "story",
    "मज़ेदार": "fun; entertaining",
    "पसंद": "liking; liked", "क्योंकि": "because", "बहुत": "very; a lot",
    "लगता": "seems (masc.)", "कि": "that (joins a statement to what was said)",
    "बुरी": "bad (fem.)",
    "नहीं": "no; not", "किताब": "book", "किताबें": "books", "हैं": "are",
    # unit22 opening a bank account
    "बैंक": "bank", "खाता": "account", "खोलना": "to open", "पैसे": "money",
    "चाहिए": "need; would like",
    "पहचान": "identity", "पत्र": "paper; card (as in identity card)",
    "खोला": "opened (past, masc. singular object)", "दो": "two",
    "भरे": "filled in (past, masc. plural object)",
    "कर्मचारी": "employee", "अच्छा": "good; nice (masc.)", "खुश": "happy",
    "था": "was (masc.)", "गया": "went (masc.)",
    # unit23 at the doctor
    "दर्द": "pain; ache", "बुखार": "fever", "सिर": "head", "तीन": "three",
    "दिन": "day", "से": "since; for (a length of time); from; with",
    "कब": "when",
    "दवा": "medicine", "आराम": "rest", "करना": "to do", "तुम्हें": "to you (informal)",
    "डॉक्टर": "doctor", "समस्या": "problem", "भी": "also; too",
    "किया": "did (past, masc. singular object)", "ठीक": "fine; well; okay",
    # unit24 a repair
    "पंखा": "fan", "खराब": "broken; faulty", "मकान": "house (as a rented home)",
    "मालिक": "owner", "नल": "tap", "कल": "tomorrow; yesterday",
    "होगा": "will be (masc.)", "मरम्मत": "repair", "सूचना": "notice",
    "पंखे": "fan (the form used before a postposition)",
    # unit25 a job interview
    "हूँ": "I am", "हो": "you are (informal)", "कितने": "how many (masc.)",
    "साल": "year", "का": "of (masc.)", "अनुभव": "experience",
    "नौकरी": "job", "इंटरव्यू": "interview", "मैनेजर": "manager",
    "सोमवार": "Monday", "को": "on; to", "शुरू": "start; beginning",
    "कर": "do (stem, used before can)", "सकता": "can; be able to (masc.)",
}

POS_SETS_A2 = {
    "proper_noun": split_words("अर्जुन प्रिया दिल्ली गांधी"),
    "pronoun": split_words(
        "मेरा मुझे मैं मैंने आप आपको आपका यह क्या कितने तुम्हें अपना अपनी अपने"
    ),
    "preposition": split_words("से को का"),
    "particle": split_words("ने नहीं कि क्योंकि भी"),
    "adjective": split_words(
        "नया नई कैसी अच्छी अच्छा बुरी मज़ेदार खुश ठीक खराब पसंद"
    ),
    "adverb": split_words("बहुत कब कल"),
    "verb": split_words(
        "है हूँ हो हैं बदलना भरना लाना लाया लाए भरा बदला लगना लगती लगता "
        "खोलना खोला भरे था गया करना किया होगा सकता कर जाना चाहिए"
    ),
    "phrase": split_words("हाँ"),
}
POS_SETS_A2["noun"] = set(GLOSSES_A2) - set().union(*POS_SETS_A2.values())

CATEGORY_TAGS_A2: dict[str, list[str]] = {}
for _tag, _words in {
    "hi_number": "दो तीन",
    "hi_weekday": "सोमवार",
}.items():
    for _w in _words.split():
        CATEGORY_TAGS_A2.setdefault(_w, []).append(_tag)

part_of_speech_a2 = pos_lookup(POS_SETS_A2)


def iter_specs():
    for level, group in LEVELS.items():
        realizations, _ = manifest_group(group)
        a2 = level == "a2"
        yield from classify(
            lang=LANG,
            level=level,
            unit_files=realizations,
            glosses=GLOSSES_A2 if a2 else GLOSSES,
            part_of_speech=part_of_speech_a2 if a2 else part_of_speech,
            normalize=normalize,
            category_tags=CATEGORY_TAGS_A2 if a2 else CATEGORY_TAGS,
        )


def main() -> int:
    return run(
        description=__doc__,
        source_language="en",
        target_language=LANG,
        levels=LEVELS,
        iter_specs=iter_specs,
    )


if __name__ == "__main__":
    raise SystemExit(main())
