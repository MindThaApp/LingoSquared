#!/usr/bin/env python3
"""Idempotently backfill target-side en-nl Dutch A1+A2 lexemes.

Run with ``--dry-run`` to parse and classify content without importing the
application or connecting to PostgreSQL.  The realization files' complete
``introduced_tokens`` inventories are authoritative.

Extended repeatedly through 2026-07-06 (most recently units 17-19: work/
occupation, housing, weather, added by a parallel session -- and units 20-23:
clothing, emotions, communication, money, added by this pass -- together
closing the en-nl practice-pool gap behind its lesson content, which goes
through unit23) to keep pace with new practice-template packs -- see
docs/content/practice/en-nl/a1_unit01.yaml onward. (Docstring corrected
2026-07-06 after a fresh-context review pass flagged it as stale -- it
previously said "units 1-7" long after the code had been extended well past
that.)

**Real bug fixed 2026-07-07 (Dutch QA pass)**: this script used to have NO
A2 handling at all -- ``UNIT_FILES`` only ever globbed ``a1_unit*.yaml``
(<=23), so every A2 lexeme (units 24-28: bureaucracy/opinions/banking/
health/housing) was silently never backfilled, for as long as A2 content
has existed -- meaning Endless Practice/SRS had zero lexeme pool for any
A2-introduced vocabulary. Root cause: "Dutch A1" and "Dutch A2" import as
TWO SEPARATE course rows (`POST /admin/content/import` dedups by
`(source_language, target_language, title)`, and the A2 overlay declares a
distinct `course.title: Dutch A2`) -- same root cause already found and
fixed for fa/prs in `backfill_lexemes.py`/`backfill_lexemes_fa_en.py`/
`backfill_lexemes_prs_en.py`. Fixed by adding `UNIT_FILES_A2` (its own
LOCAL 1-based unit ordering, looked up against the separate "Dutch A2"
course) and restructuring `iter_specs()`/`main()` to classify and backfill
each level against its own course, matching that established pattern.

**Extended 2026-07-11** to cover the four new Dutch A2 units 74-77 (travel
disruption, screen time/online habits, weekly schedule, shopping
complaint/returns) that ``UNIT_FILES_A2``'s broad ``a2_unit*_*.yaml`` glob
picked up automatically -- their lexemes were unclassified, so
``nl_agreement_tags()``'s ``lesson_categories[unit_lesson]`` lookup raised
``KeyError: 'er_is_een_vertraging'`` (unit74's own first lesson) the moment
any of these units' tokens were classified. Fixed by adding the same three
things every prior unit round added: ``NL_GLOSSES`` entries (hand-classified
from each unit's own overlay glosses/notes, never guessed), POS-set
membership (``NOUNS``/``VERBS``/``ADJECTIVES``/``ADVERBS``/``PREPOSITIONS``/
``PARTICLES``/``PROPER_NOUNS``/``PRONOUNS``), and ``lesson_categories``
entries for each of the 24 new lesson content_keys across the four units.
Deliberately did NOT add the finer-grained per-unit ``semantic`` slot-preset
tags (like unit73's ``job_interview_vocab``/``job_role_noun``) beyond a
handful of broad recognition-only vocab tags -- those fine frame-specific
tags were added in prior units specifically to support a practice-template
authoring pass, and no ``docs/content/practice/en-nl/a2_unit7[4-7].yaml``
pack exists yet (only through unit28), so there is nothing yet to wire them
into; add them alongside that future practice-template pass instead of
speculatively now.

**Extended again 2026-07-11**, same day, for that deferred practice-
template pass: ``docs/content/practice/en-nl/a2_unit74.yaml`` through
``a2_unit77.yaml`` now exist, so ``nl_agreement_tags()`` gained one
single-member ``*_single`` semantic tag per lesson's hero full-sentence
frame (25 new tags total, one block per unit, placed right after each
unit's existing broad recognition-only block) -- e.g.
``reisvertraging_vertraging_single``, ``schermtijd_scherm_single``,
``drukkeweek_daarna_single``, ``terugbrengen_koptelefoon_single``. Every
one has exactly one member by construction (a single ``t == "token"``
check), which is what makes it safe to embed in a fixed multi-word
``render_frame``/``slot_text`` template (AUTHORING_GUIDE.md #17) without
a candidate-pool grammaticality judgment call -- the existing broader
per-unit vocab/verb tags (``travel_disruption_vocab``, etc.) are still
used as-is, unchanged, for the bare-word ``multiple_choice``/
``listen_select``/``matching_pairs`` templates in the same four packs.

**Extended 2026-07-11** to cover the Dutch B1 course (units 01-11, all now
`status: reviewed`), which was imported to the DB but entirely absent from
this script -- B1 lessons were creating zero Lexeme rows, so B1 content
never fed the lexeme-level SRS or practice pool. B1 is a SEPARATE course
row from A1/A2 ("Dutch B1", not "Dutch A1"/"Dutch A2" -- same
`(source_language, target_language, title)` course-dedup pattern already
documented above for A2), so it gets its own `UNIT_FILES_B1` glob (all 11
files match `b1_unit*_*.yaml` with no gaps, every one hand-glossed below,
same discipline UNIT_FILES_A2 established) and its own `_classify_nl(...,
"b1")` call in `iter_specs()`/`courses_by_level` entry in `main()`. Every
genuinely new `introduced_tokens` value across all 11 units was
hand-classified from each overlay's own `gloss`/`example_gloss` fields, not
guessed. Real homograph/polysemy collisions found and handled the same way
prior rounds established (see "zijn"/"over" notes elsewhere in this
docstring): capitalized "Steeds" (B1's "steeds meer" = "more and more,"
grammatically distinct from the pre-existing lowercase "steeds" = "still,"
part of "nog steeds") and capitalized "Beste" (B1's email-salutation "Beste
collega's," = "Dear colleagues," distinct from the pre-existing lowercase
"beste" = "best," the unit14 superlative) were each given their OWN fresh
NL_GLOSSES entry rather than reused, since case-sensitive dict keys make
this safe with zero risk to the pre-existing lowercase/uppercase sibling.
Same treatment for lowercase "stad" (B1's common noun "the city," distinct
from the pre-existing capitalized "Stad," a unit14 comparison-ad placeholder
brand/product name classified as a proper noun) and lowercase "groet" (B1's
common noun "regards; greeting" inside "met vriendelijke groet," distinct
from the pre-existing capitalized "Groet," a unit11 standalone message-
closing PHRASE). Genuine same-meaning case variants (e.g. lowercase "zou"/
"misschien"/"geweldig"/"sommige"/"alles"/"vorige" reusing the gloss already
established for their capitalized sentence-initial siblings, and vice versa
for "Ken"/"Later"/"Soms"/"Nu"/"Vorige") were reused directly, same
convention as every prior round's `for _token in (...)` case-variant blocks.
Deliberately did NOT add the finer-grained per-unit `semantic` slot-preset
tags beyond the blanket `lesson_categories` entry per lesson -- no
`docs/content/practice/en-nl/b1_unit*.yaml` pack exists yet, same "add
those alongside a future practice-template authoring pass instead of
speculatively now" discipline the A2 unit 74-77 round already established.
`wrapup_production` (B1's own review lesson in every one of the 11 units)
reuses one shared generic `lesson_categories` value across all 11 units --
same intentional bare-suffix-collision-reuse precedent already established
for `advertentie_lezen`/`bonnetje_lezen`/`een_kaartje_kopen` elsewhere in
this file (all 11 lessons really are the same kind of generic unit-review
wrapup, so one shared descriptive tag is correct, not a bug).

Known limitation surfaced while extending this (units 5-6): this script keys
its in-memory `specs` dict by bare token string, and `nl_part_of_speech()` is
a pure function of the token with no context -- so a genuine homograph across
units (same spelling, different part of speech/meaning) can only ever get ONE
classification, whichever set the token happens to sit in. Concretely: "zijn"
already means "are" (verb, from units 1-4) and unit05 introduces "zijn"
meaning "his" (possessive pronoun) -- the second sense silently never gets
its own lexeme row; the token stays classified as the verb, with the verb's
english_gloss. Practice templates must NOT rely on "zijn" (his) as a
generation slot value until this is fixed (needs POS-aware/context-aware
keying); bake it as literal frame text instead, same as this pack's
a1_unit05.yaml does for its zijn_haar lesson templates.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Extended 2026-07-09 (practice-template depth-closing pass) to also cover
# units 29-33 (hobbies/appearance/animals/sports/transportation) -- these are
# file-numbered units appended after unit23 in scripts/content_manifest.txt's
# en-nl line (still the same "Dutch A1" course, not a level change; see each
# realization file's own review.notes for why the file numbering jumps).
# Units 24-28 are NOT included here -- those are the SEPARATE "Dutch A2"
# course, handled below by UNIT_FILES_A2. Extended 2026-07-12 to include
# the next reviewed A1 Endless Practice coverage batch, units 43-48.
UNIT_FILES = tuple(sorted(
    p for p in (REPO_ROOT / "docs/content/realizations/nl").glob("a1_unit*_*.yaml")
    if 1 <= int(p.name[len("a1_unit"):len("a1_unit")+2]) <= 23
    or 29 <= int(p.name[len("a1_unit"):len("a1_unit")+2]) <= 33
    or 43 <= int(p.name[len("a1_unit"):len("a1_unit")+2]) <= 48
))

# A2 units (24-28: bureaucracy, opinions, banking, health, housing) live in a
# SEPARATE course row ("Dutch A2", not "Dutch A1") -- `POST /admin/content/
# import` matches/creates courses by (source_language, target_language,
# title), and every a2_unit*.yaml overlay declares `course.title: Dutch A2`,
# distinct from A1's `Dutch A1`. Real bug found live 2026-07-07 (Dutch QA
# pass), same root cause already found and fixed in backfill_lexemes.py/
# backfill_lexemes_fa_en.py/backfill_lexemes_prs_en.py for fa/prs: this used
# to have NO A2 handling at all -- UNIT_FILES above only ever globbed
# a1_unit*.yaml (<=23), so every A2 lexeme (units 24-28) was silently never
# backfilled, for as long as A2 content has existed. Kept as its own tuple
# with LOCAL 1-based ordering (looked up against the "Dutch A2" course
# separately in main(), never mixed with UNIT_FILES' indices) -- unit.order
# is assigned per-course at compile/import time (see scripts/
# content_manifest.txt's separate "en-nl"/"en-nl-a2" compile groups), so a2_
# unit24 is unit.order=1 within the "Dutch A2" course, not 24.
UNIT_FILES_A2 = tuple(sorted(
    (REPO_ROOT / "docs/content/realizations/nl").glob("a2_unit*_*.yaml")
))

# B1 units (01-11: hypothetical situations, opinion/nuance, workplace
# meetings, relative clauses, indirect speech, obligations, ability/kunnen-
# konden, real/unreal conditionals, agreement/disagreement, work
# responsibilities, storytelling) live in a THIRD separate course row
# ("Dutch B1", not "Dutch A1"/"Dutch A2") -- added 2026-07-11, same
# course-dedup reasoning as UNIT_FILES_A2's own comment above. A plain glob
# is safe here (matching UNIT_FILES_A2's own precedent) because all 11 real
# files match `b1_unit*_*.yaml` with no gaps and no numbers past 11 exist
# yet, and every token every one of them introduces is hand-glossed below --
# this glob does NOT get to silently pick up a future, not-yet-glossed
# b1_unit12+ file the way a broader A1-style range-filtered glob would need
# re-auditing for; a genuinely new B1 unit added later will still hard-crash
# this script (by design, see the module-level KeyError note above) until
# someone extends this file again.
UNIT_FILES_B1 = tuple(sorted(
    (REPO_ROOT / "docs/content/realizations/nl").glob("b1_unit*_*.yaml")
))

# Each lexical gloss is deliberately atomic. Capitalized sentence-initial forms
# below reuse the same hand-authored gloss as their lowercase lexical form.
NL_GLOSSES = {
    "'s": "in the (fixed time expression)",
    "Aangenaam": "pleased to meet you", "Belgisch": "Belgian", "België": "Belgium",
    "Duits": "German", "Duitsland": "Germany", "Egypte": "Egypt", "Engels": "English",
    "Goedemiddag": "good afternoon", "Goedemorgen": "good morning", "Goedenavond": "good evening",
    "Hallo": "hello", "Hoi": "hi", "Lotte": "Lotte", "Medewerker": "staff member",
    "Nederland": "the Netherlands", "Nederlands": "Dutch", "Noor": "Noor", "Omar": "Omar",
    "Prima": "fine; great", "Taalcafé": "language café", "Workshop": "workshop",
    "Pauze": "break", "Welkom": "welcome",
    "aan": "at; on", "acht": "eight", "achtentwintig": "twenty-eight",
    "achtentwintigste": "twenty-eighth", "achtenveertig": "forty-eight", "achtste": "eighth",
    "achttien": "eighteen", "achttiende": "eighteenth", "april": "April", "augustus": "August",
    "avond": "evening", "avonds": "in the evening", "begint": "starts", "behalve": "except",
    "beleefd": "polite", "ben": "am; are", "bent": "are (polite)", "bibliotheek": "library",
    "bij": "at; by", "bijdrage": "fee; contribution", "boek": "book", "boeken": "books",
    "cent": "cent", "dag": "day", "dan": "then", "dank": "thanks", "dat": "that",
    "datum": "date", "de": "the", "december": "December", "derde": "third",
    "dertien": "thirteen", "dertiende": "thirteenth", "dertig": "thirty", "dertigste": "thirtieth",
    "dinsdag": "Tuesday", "dit": "this", "donderdag": "Thursday", "drie": "three",
    "drieëntwintigste": "twenty-third", "drieënveertig": "forty-three", "dus": "so",
    "eenendertigste": "thirty-first", "eenentwintig": "twenty-one", "eenentwintigste": "twenty-first",
    "eenheid": "unit", "eerste": "first", "elf": "eleven", "elfde": "eleventh", "en": "and",
    "er": "there", "euro": "euro", "februari": "February", "formeel": "formal", "gaat": "goes; is going",
    "geen": "no; not any", "groep": "group", "half": "half", "halverwege": "halfway",
    "heb": "have", "heet": "am called; are called", "hele": "whole", "herhalen": "repeat",
    "het": "the; it", "hier": "here", "hoe": "how", "hoeveelste": "which numbered date",
    "hoofdletter": "capital letter", "huisnummer": "house number", "ik": "I", "in": "in",
    "informeel": "informal", "inleverdatum": "due date", "inschrijven": "register; sign up",
    "is": "is", "jaar": "year", "januari": "January", "je": "you; your (informal)",
    "jij": "you (informal, stressed)", "jou": "you (informal object)", "juli": "July", "juni": "June",
    "keer": "time; occasion", "kom": "come", "komt": "comes; come (polite)", "kost": "costs",
    "krijgen": "get; receive", "kwart": "quarter", "kwartier": "quarter-hour", "laat": "late; what time",
    "leer": "learn", "maand": "month", "maandag": "Monday", "maart": "March", "me": "myself; me",
    "mei": "May", "mensen": "people", "met": "with", "middag": "afternoon", "middags": "in the afternoon",
    "mijn": "my", "moet": "must; is due", "na": "after", "naam": "name", "naar": "toward; to",
    "nacht": "night", "nachts": "at night", "negen": "nine", "negende": "ninth",
    "negenennegentig": "ninety-nine", "negenentwintigste": "twenty-ninth", "negentien": "nineteen",
    "negentiende": "nineteenth", "negentig": "ninety", "nieuw": "new", "normaal": "normally",
    "november": "November", "nul": "zero", "nummer": "number", "ochtend": "morning",
    "ochtends": "in the morning", "of": "or", "oktober": "October", "om": "at (a time); around",
    "ontmoeten": "meet", "ook": "also; too", "op": "on; at", "open": "open", "oud": "old",
    "over": "past; after", "rooster": "schedule", "september": "September", "slecht": "bad",
    "spreek": "speak", "stoelen": "chairs", "taalcafé": "language café", "tachtig": "eighty",
    "tafel": "table", "te": "to", "telefoonnummer": "phone number", "terug": "back; returned",
    "tien": "ten", "tiende": "tenth", "tiental": "multiple of ten", "tijd": "time", "tot": "until; see you",
    "twaalf": "twelve", "twaalfde": "twelfth", "twee": "two", "tweede": "second",
    "tweeëndertig": "thirty-two", "tweeëntwintig": "twenty-two", "tweeëntwintigste": "twenty-second",
    "tweeënveertig": "forty-two", "twintig": "twenty", "twintigste": "twentieth", "u": "you (polite)",
    "uit": "from; out of", "uur": "hour; o'clock", "vandaag": "today", "vandaan": "from",
    "veertien": "fourteen", "veertiende": "fourteenth", "veertig": "forty", "vier": "four",
    "vierde": "fourth", "vierentwintigste": "twenty-fourth", "vijf": "five", "vijfde": "fifth",
    "vijfentwintigste": "twenty-fifth", "vijfenzestig": "sixty-five", "vijfenzeventig": "seventy-five",
    "vijftien": "fifteen", "vijftiende": "fifteenth", "vijftig": "fifty", "volgende": "next",
    "voor": "for; before", "vrijdag": "Friday", "vrijdagmiddag": "Friday afternoon", "vóór": "before",
    "wanneer": "when", "wat": "what", "week": "week", "welke": "which", "wil": "want",
    "woensdag": "Wednesday", "woon": "live; reside", "workshop": "workshop", "zaal": "room; hall",
    "zaterdag": "Saturday", "zes": "six", "zesde": "sixth", "zesentwintigste": "twenty-sixth",
    "zestien": "sixteen", "zestiende": "sixteenth", "zestig": "sixty", "zeven": "seven",
    "zevende": "seventh", "zevenentachtig": "eighty-seven", "zevenentwintigste": "twenty-seventh",
    "zeventien": "seventeen", "zeventiende": "seventeenth", "zeventig": "seventy", "ziens": "seeing",
    "zijn": "are", "zitten": "sit; are sitting", "zondag": "Sunday", "één": "one",
}

NL_GLOSSES.update({
    "Dagen": "days", "Goed": "good; well", "hoeveel": "how many; how much",
    "Inleverdatum": "due date", "ja": "yes", "kun": "can",
    "leuk": "nice; pleasant",
    "Maanden": "months", "nee": "no", "niet": "not", "waar": "where", "wij": "we",
})

# Unit 5 (family) and unit 6 (food/ordering), added 2026-07-05.
NL_GLOSSES.update({
    "vader": "father", "moeder": "mother", "ouders": "parents", "broer": "brother",
    "zus": "sister", "kind": "the child", "kinderen": "the children", "een": "a; an",
    "opa": "grandfather", "oma": "grandmother", "oom": "uncle", "tante": "aunt",
    "neef": "male cousin; nephew", "nicht": "female cousin; niece",
    "gezin": "family (household)", "wonen": "live; reside", "Rotterdam": "Rotterdam",
    "hebben": "have (plural/infinitive)", "jouw": "your (emphatic)", "Dit": "this",
    "haar": "her", "heet": "am called; are called", "Sander": "Sander (a Dutch male name)",
    "Fenna": "Fenna (a Dutch female name)", "Jan": "Jan (a Dutch male name)",
    "Marieke": "Marieke (a Dutch female name)", "elke": "every", "maand": "month",
    "Heb": "have", "broers": "brothers", "zussen": "sisters", "Geen": "no; not any",
    "Wonen": "live; reside", "Utrecht": "Utrecht", "familie": "family (relatives in general)",
    "maar": "but", "woont": "lives; resides", "Amsterdam": "Amsterdam",
    "Zie": "see (imperative/question form)", "hem": "him", "vaak": "often",
    "koffie": "coffee", "thee": "tea", "water": "water", "melk": "milk", "sap": "juice",
    "brood": "bread", "broodje": "sandwich roll", "kaas": "cheese", "appel": "apple",
    "wil": "want", "graag": "gladly; please (with wil)", "alstublieft": "please (formal)",
    "alsjeblieft": "please (informal)", "wilt": "want (with u, formal)",
    "drinken": "to drink; drink", "eten": "to eat; eat", "appelsap": "apple juice",
    "Mag": "may; can (polite)", "Menukaart": "menu", "Koffie": "coffee",
    "Thee": "tea", "Broodje": "sandwich roll", "Appelsap": "apple juice",
    "iets": "something", "Komt": "comes", "eraan": "on its way (part of komt eraan)",
})

# Unit 7 (shopping at the market), added 2026-07-05.
NL_GLOSSES.update({
    "markt": "the market", "winkel": "the shop", "kraam": "the stall",
    "appels": "apples", "peren": "pears", "tomaten": "tomatoes", "paprika's": "bell peppers",
    "kilo": "a kilo", "per": "per", "honderd": "hundred", "gram": "grams",
    "pond": "a pound (500 grams)", "500": "500", "stuk": "one piece; one item",
    "stuks": "pieces; items", "prijskaartje": "the price label",
    "Appels": "Apples", "Peren": "Pears", "Tomaten": "Tomatoes", "Paprika's": "Bell peppers",
    "mag": "may; can (polite)", "neem": "take", "Anders": "otherwise; anything else",
    "nog": "still; else", "kan": "can", "Kan": "can", "pinnen": "pay by card",
    "Verkoper": "vendor", "natuurlijk": "of course", "Bedankt": "thanks",
})

# Unit 9 (asking for and giving directions), added 2026-07-06.
NL_GLOSSES.update({
    "links": "left", "rechts": "right", "linksaf": "to the left; turn left",
    "rechtsaf": "to the right; turn right", "rechtdoor": "straight ahead",
    "ga": "go", "sla": "turn", "loop": "walk", "Ga": "Go", "Sla": "Turn",
    "Loop": "Walk", "vanaf": "from", "route": "the route", "START": "START",
    "DOEL": "DESTINATION", "Route": "Route", "Graag": "gladly", "gedaan": "done",
})

# Unit 10 (describing a daily routine), added 2026-07-06.
NL_GLOSSES.update({
    "opstaan": "to get up", "sta": "get up (with ik)", "zich": "oneself (reflexive)",
    "aankleden": "to get dressed", "kleed": "get dressed (with ik)",
    "ontbijten": "to have breakfast", "ontbijt": "have breakfast (with ik)",
    "werken": "to work", "werk": "work (with ik)", "eet": "eat (with ik)",
    "afwassen": "to do the dishes", "was": "do the dishes (with ik)",
    "af": "off (separable prefix)", "slapen": "to sleep", "slaap": "sleep (with ik)",
    "In": "In", "gewone": "ordinary", "hoofdzin": "main clause", "deel": "part",
    "einde": "end", "scheidbaar": "separable", "achteraan": "at the end",
    "07": "07", "eerst": "first", "daarna": "after that", "Eerst": "First",
    "Daarna": "After that", "Na": "After", "staat": "stands; is placed",
    "werkwoord": "verb", "ziet": "sees; looks", "eruit": "out (part of 'looks like')",
    "pas": "not until; only",
})

# Unit 11 (making simple plans), added 2026-07-06.
NL_GLOSSES.update({
    "samen": "together", "film": "the film", "gaan": "to go", "Zullen": "Shall",
    "we": "we", "activiteit": "activity", "manier": "way; manner",
    "stellen": "to propose (part of voorstellen)", "zin": "desire; mood",
    "idee": "idea", "goed": "good", "plan": "the plan", "Sorry": "Sorry",
    "want": "because", "korte": "short", "reden": "reason", "maakt": "makes",
    "afwijzing": "decline; refusal", "vriendelijk": "friendly",
    "afspreken": "to arrange to meet", "geeft": "gives", "afspraak": "appointment",
    "17": "17", "bericht": "the message", "uitnodiging": "the invitation",
    "Groet": "Regards", "zullen": "shall", "Vrijdag": "Friday", "kort": "short",
    "staan": "to stand; to be placed", "spreken": "to speak (part of afspreken)",
})

# Unit 12 (talking about recent events, perfect tense), added 2026-07-06.
NL_GLOSSES.update({
    "gesprekken": "conversations", "gebruik": "use", "voltooide": "completed",
    "gebeurtenis": "event", "meestal": "usually", "voltooid": "completed",
    "deelwoord": "participle", "gedronken": "drank; drunk", "gegaan": "went; gone",
    "Denk": "think", "eindpositie": "end position", "meeste": "most",
    "werkwoorden": "verbs", "gebruiken": "to use", "gegeten": "ate; eaten",
    "gewerkt": "worked", "kopen": "to buy", "gekocht": "bought", "Bij": "With",
    "komen": "to come", "gekomen": "came; come", "gisteren": "yesterday",
    "vanmorgen": "this morning", "Gisteren": "Yesterday", "Vanmorgen": "This morning",
    "Daar": "There",
})

# Unit 13 (expressing preferences), added 2026-07-06.
NL_GLOSSES.update({
    "lekker": "tasty; nice", "vinden": "to find; to consider",
    "vind": "find; consider (with ik)", "Vind": "Find; consider",
    "tomatensoep": "tomato soup", "activiteiten": "activities",
    "fietsen": "to cycle", "wandelen": "to walk", "winkelen": "to shop",
    "doen": "to do", "Houden": "To love; to be fond of", "drukt": "expresses",
    "sterke": "strong", "algemene": "general", "voorkeur": "preference",
    "houd": "love; am fond of (with ik)", "muziek": "music", "films": "films",
    "Zeg": "Say", "smaak": "taste", "Wil": "Want", "liever": "rather; prefer",
    "blauwe": "blue", "trui": "sweater", "Liever": "Rather; prefer",
    "zien": "to see", "ene": "the one", "optie": "option", "boven": "over; above",
    "andere": "other", "kiest": "chooses", "houdt": "loves; is fond of",
    "Hij": "He", "park": "the park", "zo": "so",
})

# Unit 14 (making comparisons), added 2026-07-06.
NL_GLOSSES.update({
    "vergelijkingen": "comparisons", "voeg": "add", "toe": "to (separable prefix)",
    "bijvoeglijk": "adjectival", "naamwoord": "word; noun", "groot": "big",
    "klein": "small", "rugzak": "the backpack", "groter": "bigger", "tas": "the bag",
    "kleiner": "smaller", "vijfenveertig": "forty-five", "duur": "expensive",
    "goedkoop": "cheap", "duurder": "more expensive", "goedkoper": "cheaper",
    "Gebruik": "Use", "net": "just", "plus": "plus", "als": "as; if",
    "dingen": "things", "gelijk": "equal", "vergelijken": "to compare",
    "Deze": "This", "mooi": "nice-looking; pretty", "die": "that",
    "praktisch": "practical", "superlatief": "superlative", "st": "-st (suffix)",
    "Van": "Of", "deze": "this", "duurst": "most expensive", "beter": "better",
    "best": "best", "onregelmatig": "irregular", "beste": "best (attributive)",
    "keuze": "choice", "Veel": "Much; many", "meer": "more", "meest": "most",
    "werkt": "works", "dezelfde": "the same", "lange": "long", "treinreis": "train trip",
    "heeft": "has", "ruimte": "room; space", "Bergsport": "Bergsport",
    "sterk": "strong", "Schoudertas": "Shoulder bag", "Stad": "City",
    "lichter": "lighter", "minder": "less", "reis": "trip", "sterker": "stronger",
    "grote": "big", "nodig": "necessary", "Precies": "Exactly", "precies": "exactly",
    "mooist": "prettiest", "schoudertas": "the shoulder bag", "licht": "light (weight)",
    "koop": "buy (with ik)", "Koop": "Buy", "vorm": "form", "koopt": "buys",
    "zij": "she; they", "hij": "he; it",
})

# Unit 15 (traveling by train), added 2026-07-06.
NL_GLOSSES.update({
    "kaartje": "the ticket", "Wilt": "Would (want, formal)", "enkele": "single (one-way)",
    "retour": "the return ticket", "balie": "the counter", "beleefde": "polite",
    "perron": "the platform", "welk": "which", "vertrekt": "departs", "trein": "the train",
    "vertraging": "the delay", "Let": "Pay (attention)", "plaats": "place",
    "minuten": "minutes", "ingang": "the entrance", "uitgang": "the exit",
    "wachtruimte": "the waiting room", "Rechtdoor": "Straight ahead",
    "Kaartje": "Ticket", "Centraal": "Central", "Vertrek": "Departure",
    "Aankomst": "Arrival", "Retour": "Return", "Prijs": "Price", "We": "We",
    "moeten": "must; need to", "daar": "there", "bord": "the sign",
    "probleem": "the problem", "O": "Oh", "al": "already", "Perron": "Platform",
    "stappen": "to step",
})

# Unit 16 (describing a basic health problem), added 2026-07-06.
NL_GLOSSES.update({
    "voel": "feel (with ik)", "ziek": "sick", "hoofdpijn": "a headache",
    "buikpijn": "a stomach ache", "scheelt": "is the matter", "keelpijn": "a sore throat",
    "Gaat": "Goes", "koorts": "a fever", "verkouden": "having a cold", "Ziek": "Sick",
    "bijvoeglijke": "adjectival", "naamwoorden": "words; nouns", "Koorts": "Fever",
    "zelfstandige": "substantive (noun-like)", "apotheek": "the pharmacy",
    "Waarmee": "With what", "helpen": "to help", "Heeft": "Has", "tegen": "for; against",
    "tablet": "a tablet", "Neem": "Take", "Advies": "Advice", "Rust": "Rest",
    "drink": "drink", "veel": "much; a lot", "Voel": "Feel", "dagen": "days",
    "steeds": "still (part of nog steeds)", "huisarts": "the family doctor",
    "Nog": "Still; not yet", "moe": "tired", "genomen": "taken", "nu": "now",
    "rusten": "to rest", "Beterschap": "Get well soon", "Dank": "Thanks",
    "morgen": "tomorrow",
})

# Unit 17 (work and occupation), added 2026-07-06. "werk" is already
# classified as a VERB (ik-form of werken, from unit10's daily-routine
# content) -- this unit also uses "werk" as a NOUN ("Wat doe je voor
# werk?", object of "voor"), the same token/different-POS homograph
# limitation documented in this file's module docstring (see the "zijn"
# note). Per that established precedent, "werk" is NOT given a new
# noun-generative tag; that question phrase is baked as literal frame
# text in the practice template instead of using "werk" as a fillable
# slot value.
NL_GLOSSES.update({
    "Elke": "Every", "Sommige": "Some", "Ze": "she", "Zij": "She",
    "baan": "job", "begin": "start (with ik)", "benieuwd": "curious",
    "beroep": "the occupation", "denk": "think (with ik)", "doe": "do (with je)",
    "eigen": "own", "eigenlijk": "actually", "extra": "extra",
    "kantoor": "office", "kok": "cook", "krijgt": "gets",
    "later": "later", "maak": "make (with je)", "pauze": "the break",
    "restaurant": "restaurant", "ritme": "rhythm", "stop": "stop; finish (with ik)",
    "uren": "hours", "verpleegkundige": "nurse", "vroeg": "early",
})

# Unit 18 (housing), added 2026-07-06.
NL_GLOSSES.update({
    "Appartement": "Apartment", "altijd": "always", "appartement": "the apartment",
    "badkamer": "the bathroom", "balkon": "the balcony", "fijn": "nice",
    "gezellig": "cozy", "kamers": "rooms", "keuken": "the kitchen",
    "klinkt": "sounds", "langs": "by (part of 'komen langs', to come by/visit)",
    "nieuwe": "new (inflected)", "slaapkamer": "the bedroom", "slaapkamers": "bedrooms",
    "snel": "soon; quickly", "tuin": "the garden", "welkom": "welcome",
    "woonkamer": "the living room", "zeggen": "to say",
})

# Unit 19 (weather), added 2026-07-06.
NL_GLOSSES.update({
    "Als": "If", "Laten": "Let's", "Morgen": "Tomorrow", "Perfect": "Perfect",
    "Weerbericht": "Weather forecast", "Zaterdag": "Saturday", "Zondag": "Sunday",
    "bewolkt": "cloudy", "binnen": "inside", "blijven": "stay (with we)",
    "kijken": "watch (with we)", "koud": "cold", "maken": "to make",
    "regent": "is raining", "wandeling": "the walk", "warm": "warm",
    "weekend": "the weekend", "weer": "the weather", "weerbericht": "the weather forecast",
    "zonnig": "sunny",
})

# Unit 20 (buying clothes), added 2026-07-06.
NL_GLOSSES.update({
    "jas": "the coat", "trui": "the sweater", "broek": "the pants; the trousers",
    "schoenen": "the shoes", "maat": "the size", "Welke": "Which",
    "zwart": "black", "blauw": "blue", "past": "fits", "Past": "Fits",
    "passen": "to try on; to fit", "klein": "small", "groot": "big",
    "negentig": "ninety", "Winterjas": "winter coat", "kleur": "the color",
    "warm": "warm", "zoek": "look for (with ik)", "M": "M",
    "Natuurlijk": "Of course", "neemt": "takes (with hij/zij)",
    "nemen": "to take",
})

# Unit 21 (expressing feelings), added 2026-07-06.
NL_GLOSSES.update({
    "blij": "happy", "verdrietig": "sad", "boos": "angry",
    "omdat": "because", "regent": "rains", "zenuwachtig": "nervous",
    "voor": "for; about", "zorgen": "worries", "Maak": "Make",
    "Waarom": "Why", "voelt": "feels", "zich": "oneself; himself/herself",
    "alleen": "alone", "Maar": "But", "nieuwe": "new", "baan": "job",
    "appartement": "apartment", "beetje": "a bit", "denk": "think (with ik)",
    "kunt": "can (with je/jij)", "eerlijk": "honest(ly)", "gezegd": "said",
    "helpt": "helps", "vast": "surely; definitely", "trots": "proud",
    "dienst": "shift", "heel": "very; really", "echt": "really; truly",
})

# Unit 22 (calling and texting), added 2026-07-06.
NL_GLOSSES.update({
    "bellen": "to call", "bel": "call (with ik)", "Met": "This is",
    "wie": "who", "U": "You (polite)", "herhalen": "to repeat",
    "snel": "fast; quickly", "hoor": "hear (with ik)",
    "horen": "to hear", "sms": "the text message", "stuur": "send (with ik)",
    "later": "later", "terug": "back", "belt": "calls",
    "Fijn": "Nice", "fijn": "nice", "ging": "went", "dacht": "thought",
    "betekent": "means", "spreekt": "speaks", "Spreek": "Speak",
    "wel": "indeed; well", "vertellen": "to tell", "Zijn": "His",
    "denken": "to think",
})

# Unit 23 (money and paying), added 2026-07-06.
NL_GLOSSES.update({
    "totaal": "total", "Totaal": "Total", "pinnen": "to pay by card",
    "contant": "cash", "betalen": "to pay", "Hier": "Here",
    "rekening": "the bill", "Rekening": "Bill", "delen": "to split; to share",
    "apart": "separately", "afrekenen": "to settle the bill; to pay",
    "wisselgeld": "the change", "nodig": "needed", "vijfendertig": "thirty-five",
    "vijfentwintig": "twenty-five", "hoofdgerechten": "main courses",
    "koffies": "coffees", "Betaald": "Paid", "pin": "card (payment)",
    "Zullen": "Shall", "vragen": "to ask for", "goed": "good",
    "idee": "idea", "betaalt": "pays", "Jij": "You",
    "hebt": "have (with jij)", "geholpen": "helped", "lief": "sweet; kind",
    "uw": "your (formal)", "mij": "me",
})

# A2 unit 24 (gemeente/bureaucracy: registering with local authorities),
# added 2026-07-07.
NL_GLOSSES.update({
    "schrijven": "write (part of 'inschrijven', to register)",
    "Zou": "Would (conditional of zullen)", "schikken": "to suit; to be convenient",
    "paspoort": "the passport", "huurcontract": "the rental contract",
    "geboorteakte": "the birth certificate", "geldig": "valid",
    "Moet": "Must; do (need to)", "meenemen": "to bring along",
    "Sinds": "Since", "adres": "the address", "sinds": "since",
    "vorige": "previous; last", "BSN": "the BSN (Citizen Service Number)",
    "persoonlijke": "personal (inflected)", "overheid": "the government",
    "DigiD": "DigiD (Dutch digital identity system)", "online": "online",
    "zaken": "matters; affairs", "regelen": "to arrange",
    "gemeente": "the municipality", "documenten": "documents",
    "indien": "if", "toepassing": "application (van toepassing, applicable)",
    "vooraf": "in advance", "inschrijving": "the registration",
    "ontvangt": "receives", "post": "the mail; post",
    "Ambtenaar": "Official (civil servant)", "waarmee": "with what; how",
    "Alstublieft": "Here you go; please (formal)",
    "Alles": "Everything", "orde": "order (in orde, in order)",
    "paar": "a couple; a few (in 'een paar')", "Geweldig": "Great; wonderful",
    "hulp": "the help", "ingeschreven": "registered (past participle of inschrijven)",
})

# A2 unit 25 (meningen/opinions: giving opinions with reasons), added 2026-07-07.
NL_GLOSSES.update({
    "fietspad": "the bike path", "mening": "the opinion",
    "Volgens": "According to", "gevaarlijk": "dangerous", "smal": "narrow",
    "eens": "agreed; in agreement (het eens zijn, to agree)",
    "gedeeltelijk": "partially", "Aan": "On (aan de andere kant, on the other hand)",
    "kant": "the side", "veiliger": "safer", "bespaart": "saves",
    "voetgangers": "the pedestrians", "weinig": "little; not much",
    "snap": "understand (with ik)", "fietsers": "cyclists",
    "ze": "they; she (unstressed)", "pad": "the path", "breder": "wider",
    "helemaal": "completely; entirely", "mee": "along; with (mee eens, in agreement)",
    "auto": "the car", "s": "'s (possessive/plural marker, as in auto's)",
    "straat": "the street", "Misschien": "Maybe", "wordt": "becomes",
    "vindt": "thinks; finds (with hij/zij)",
})

# A2 unit 26 (bankrekening/banking: opening a bank account), added 2026-07-07.
NL_GLOSSES.update({
    "bankrekening": "the bank account", "openen": "to open",
    "betaalrekening": "the payment/checking account", "salaris": "the salary",
    "Uw": "Your (formal)", "werkgever": "the employer",
    "stort": "deposits (with hij/zij)", "Storten": "To deposit",
    "infinitief": "the infinitive", "identiteitsbewijs": "the identity document",
    "Heeft": "Have; has (formal question form)", "bankpas": "the bank card",
    "app": "the app", "mobiel": "mobile", "bankieren": "to bank (do banking)",
    "gebruikt": "uses", "storten": "to deposit", "geopend": "opened",
})

# A2 unit 27 (huisarts/health: a doctor's visit), added 2026-07-07.
NL_GLOSSES.update({
    "bezoek": "the visit", "klachten": "symptoms; complaints", "erg": "very",
    "pijn": "the pain", "griepje": "a mild flu; a cold", "waarschijnlijk": "probably",
    "ernstig": "serious", "Maakt": "Make (formal imperative)",
    "recept": "the prescription", "schrijf": "prescribe; write (with ik)",
    "pillen": "the pills", "rust": "rest (imperative, with u)",
    "innemen": "to take (medicine)", "terugkomen": "to come back",
    "infinitieven": "infinitives", "scheidbare": "separable (inflected)",
    "Diagnose": "Diagnosis", "voorgeschreven": "prescribed",
    "Voelt": "Feel(s) (formal)", "Huisarts": "Doctor (family doctor/GP)",
    "vervelend": "unpleasant; annoying", "dokter": "the doctor",
})

# A2 unit 28 (probleem melden/housing: reporting a maintenance issue),
# added 2026-07-07.
NL_GLOSSES.update({
    "verwarming": "the heating", "monteur": "the technician; repairman",
    "morgenochtend": "tomorrow morning", "melding": "the report; notification",
    "vierentwintig": "twenty-four", "contact": "contact",
    "Bevestiging": "Confirmation", "ontvangen": "received",
    "thuis": "at home", "Bel": "Call (imperative)",
    "woningcorporatie": "the housing corporation",
    "Woningcorporatie": "Housing corporation",
    "gisteravond": "last night; yesterday evening", "sturen": "to send",
    "Tussen": "Between",
})

# Unit 29 (hobbies: free-time activities), added 2026-07-09 by the
# practice-template depth-closing pass (see UNIT_FILES' own comment for the
# file-numbering context -- still the "Dutch A1" course).
NL_GLOSSES.update({
    "lezen": "to read", "sporten": "to exercise; to play sports",
    "koken": "to cook", "sport": "exercise; play sports (with ik)",
    "kook": "cook (with ik)", "vrienden": "friends", "vrije": "free (inflected)",
    "lees": "read (with ik)", "luisteren": "to listen",
    "tekenen": "to draw", "teken": "draw (with ik)", "gamen": "to game",
    "luister": "listen (with ik)", "game": "game (with ik)",
    "soms": "sometimes", "nooit": "never", "elk": "every (neuter)",
    "de-woorden": "de-words (common-gender nouns)", "zoals": "such as; like",
    "het-woorden": "het-words (neuter nouns)", "Kook": "Cook",
    "kookt": "cooks", "ontspannend": "relaxing", "Game": "Game",
    "hobby's": "hobbies", "weet": "know (with ik)", "buiten": "outside",
    "ons": "us", "allebei": "both", "zie": "see (with ik)",
})

# Unit 30 (appearance: describing people), added 2026-07-09.
NL_GLOSSES.update({
    "lang": "tall; long", "jong": "young", "Oud": "Old",
    "aantal": "number; amount", "jaren": "years", "betekenen": "to mean",
    "indruk": "impression", "zonder": "without", "getal": "a number",
    # "Opa" (capitalized) is a real homograph-of-case with the already-
    # classified common noun "opa" (unit05, "grandfather") -- here it is
    # used as a name-like reference to Lotte's specific grandfather, the
    # same convention as the capitalized Sander/Fenna/Nina proper nouns.
    "Opa": "Grandpa (Lotte's grandfather, used as a name)",
    "blond": "blond", "bruin": "brown", "grijs": "grey",
    # "Haar" (capitalized, the noun "hair") is a genuine homograph-of-case
    # with the already-classified possessive pronoun "haar" (her, unit05).
    # Since nl_part_of_speech() keys on the exact token, this capitalized
    # form gets its OWN classification (noun) rather than colliding with
    # the lowercase possessive.
    "Haar": "Hair",
    "woord": "word", "lidwoord": "the article (grammar term)",
    "blijft": "remains; stays", "ogen": "eyes", "groen": "green",
    "meervoud": "the plural", "bruine": "brown (inflected)",
    "groene": "green (inflected)", "meisje": "the girl", "Nina": "Nina",
    "Oké": "Okay", "herken": "recognize (with ik)",
    "anders": "different(ly)", "langer": "taller; longer", "Je": "You",
    "kent": "know (with hij/zij/je)", "patroon": "the pattern",
})

# Unit 31 (animals and pets), added 2026-07-09.
NL_GLOSSES.update({
    "dier": "the animal", "huisdier": "the pet", "hond": "the dog",
    "kat": "the cat", "vis": "the fish", "vogel": "the bird",
    "ontkent": "negates", "onbepaald": "indefinite",
    "zelfstandig": "substantive (noun-like)",
    "ken": "know (with je, inverted)", "uitlaten": "to walk (an animal)",
    "Uitlaten": "To walk (an animal)", "eerdere": "earlier; previous",
    "les": "the lesson", "geven": "to give", "geef": "give (with ik)",
    "spelen": "to play", "speelt": "plays", "Meervoud": "Plural",
    "honden": "dogs", "dieren": "animals", "klinker": "the vowel",
    "verdubbelt": "doubles", "medeklinker": "the consonant",
    "katten": "cats", "vissen": "fish (plural)", "vogels": "birds",
    "Laat": "Walk (imperative, part of uitlaten)",
    "houden": "to love; to be fond of; to hold", "beiden": "both (of them)",
    "Pico": "Pico (a pet bird's name)", "alle": "all",
})

# Unit 32 (sports and exercise), added 2026-07-09.
NL_GLOSSES.update({
    "voetbal": "football; soccer", "yoga": "yoga", "doet": "does",
    # "hardlopen"/"zwemmen" (and their capitalized subject-position forms)
    # are classified as nouns here -- every real use in this unit is as the
    # object of "aan"/"van" (doen aan hardlopen, houden van zwemmen), the
    # infinitive-as-gerund pattern Dutch uses after prepositions, matching
    # how "hardlopen" is also used as a bare subject ("Hardlopen is niet
    # scheidbaar").
    "hardlopen": "running; to run", "zwemmen": "swimming; to swim",
    "Doen": "To do", "specifieke": "specific", "noemt": "names; calls",
    "Beide": "Both", "hard": "hard; fast", "dicht": "close; near",
    "huis": "the house", "Hardlopen": "Running",
    "loopt": "walks; runs", "rustig": "calm(ly)", "bewegen": "to move",
    "zwemt": "swims", "bijna": "almost", "proberen": "to try",
})

# Unit 33 (transportation and commuting), added 2026-07-09.
NL_GLOSSES.update({
    "fiets": "the bike", "reist": "travels", "lopen": "to walk",
    "reizen": "to travel", "fietst": "cycles", "rijdt": "drives",
    "lessen": "lessons", "Die": "Those; that", "woorden": "words",
    "vervoer": "transport", "loket": "the counter; ticket window",
    "onbekende": "a stranger", "Welk": "Which",
    "centrum": "the town centre", "ver": "far",
    "Fietsen": "Cycling; to cycle", "dichtbij": "nearby; close by",
    "rijd": "drive (with ik)",
})

for _token in ("Een", "Twee"):
    if _token not in NL_GLOSSES:
        NL_GLOSSES[_token] = NL_GLOSSES[_token.casefold()]

# Unit 8 (locating places), added 2026-07-05.
NL_GLOSSES.update({
    "station": "the station", "supermarkt": "the supermarket", "ziekenhuis": "the hospital",
    "bank": "the bank", "postkantoor": "the post office", "bushalte": "the bus stop",
    "naast": "next to", "tegenover": "opposite; across from", "achter": "behind",
    "tussen": "between", "buurt": "neighbourhood; area", "van": "of; from",
    "kaart": "the map", "buurtkaart": "the neighbourhood map",
    "BUURTKAART": "NEIGHBOURHOOD MAP", "Bibliotheek": "Library", "Ziekenhuis": "Hospital",
    "Postkantoor": "Post office", "Supermarkt": "Supermarket", "Bank": "Bank",
    "Bushalte": "Bus stop", "Kijk": "look", "Mooi": "nice; good",
})

# A2 unit 73 (sollicitatiegesprek/job interview), added 2026-07-10.
NL_GLOSSES.update({
    "vacature": "vacancy; job opening", "solliciteren": "to apply",
    "Kantoor": "Office", "Bloem": "Bloem", "zoekt": "is looking for",
    "administratief": "administrative", "medewerker": "employee; assistant",
    "sollicitatiegesprek": "job interview", "langskomen": "to come by",
    "ervaring": "experience", "vrijwilliger": "volunteer",
    "vaardigheid": "skill", "Typen": "Typing", "belangrijke": "important",
    "goede": "good", "vaardigheden": "skills", "beschikbaar": "available",
    "werktijden": "working hours", "Ervaring": "Experience",
    "klantcontact": "customer contact", "pre": "plus; advantage",
    "Werktijden": "Working hours", "Vertelt": "Tell",
    "had": "had", "gesprek": "conversation; interview",
    "gesolliciteerd": "applied",
})

# A2 unit 74 (reisvertraging/travel disruption), added 2026-07-11. Widened
# the already-existing "over" gloss (unit15-era, "past; after") to also cover
# the time-duration sense this unit uses ("Over tien minuten" = "In ten
# minutes") -- this is ordinary polysemy of the single Dutch preposition
# "over", not a distinct homograph/different-POS collision like the "zijn"/
# "werk" cases documented in this file's module docstring, so widening the
# one gloss (rather than adding a conflicting second entry) is safe.
NL_GLOSSES["over"] = "past; after; in (a duration, as in 'over tien minuten')"
NL_GLOSSES.update({
    "seinstoring": "the signal failure", "valt": "falls; is cancelled (with hij/zij, part of uitvallen)",
    "door": "through; because of; during (as in 'door de week')",
    "aansluiting": "the connection", "mis": "miss (with ik)",
    "servicebalie": "the service desk", "Kunt": "can (with u/je, formal or informal)",
    "alternatieve": "alternative (inflected)", "verbinding": "the connection",
    "intercity": "the intercity train", "via": "via; through",
    "Belangrijke": "important (inflected)", "mededeling": "the notice; announcement",
    "rijden": "to run (trains/buses); to drive", "Arnhem": "Arnhem",
    "treinen": "trains", "Reizigers": "Travelers", "kunnen": "can (infinitive/plural)",
    "omreizen": "to reroute", "Amersfoort": "Amersfoort", "duurt": "lasts (with hij/zij)",
    "ongeveer": "about; approximately", "adviseren": "to advise",
    "reizigers": "travelers", "reisplanner": "the journey planner",
    "raadplegen": "to consult", "NS": "NS (Dutch national railway company)",
    "uitgevallen": "cancelled; failed (past participle of uitvallen)",
    "weten": "to know", "inderdaad": "indeed", "Over": "past; after; in (a duration, as in 'over tien minuten')",
    "spoor": "the platform; track", "even": "just; briefly",
})

# A2 unit 75 (schermtijd/screen time and online habits), added 2026-07-11.
NL_GLOSSES.update({
    "scherm": "the screen", "telefoon": "the phone", "sociale": "social (inflected)",
    "media": "media", "chat": "chat (with ik)", "apps": "apps",
    "schermtijd": "screen time", "gewoonte": "the habit",
    "doorbrengen": "to spend (time)", "hun": "their",
    "Sociale": "Social (inflected)", "gezond": "healthy",
    "Probeer": "Try (imperative)", "brengen": "to bring; to spend (time) (part of doorbrengen)",
    "Eigenlijk": "actually", "kijk": "look (with ik)",
    "Jawel": "yes indeed (contradicting a negative assumption)",
    "wegleggen": "to put away", "probeer": "try (with ik)",
})

# A2 unit 76 (drukke week/describing a weekly schedule), added 2026-07-11.
NL_GLOSSES.update({
    "cursus": "the course", "volgorde": "the order; sequence",
    "Ten": "finally (part of 'ten slotte')", "slotte": "finally (part of 'ten slotte')",
    "avondeten": "the dinner; evening meal",
    "doordeweekse": "weekday (adjective, as in 'doordeweekse dag')",
    "Door": "through; because of; during (as in 'door de week')",
    "verschil": "the difference", "agenda": "the schedule; planner",
    "zit": "sits; is (with hij/zij, idiomatic 'zit vol' = is full)",
    "vol": "full", "Volgende": "next", "druk": "busy",
    "woensdagavond": "Wednesday evening", "taalcursus": "the language course",
    "leest": "reads (with hij/zij)", "Best": "pretty; quite (degree adverb, as in 'best druk')",
    "vrij": "free; off (a day)", "lekkers": "something tasty (as in 'iets lekkers')",
    "gewoon": "just; simply",
})

# A2 unit 77 (iets terugbrengen/shopping complaint and returns), added
# 2026-07-11.
NL_GLOSSES.update({
    "koptelefoon": "the headphones", "kapot": "broken",
    "linkerkant": "the left side", "geld": "the money",
    "ruilen": "to exchange", "terugkrijgen": "to get back",
    "bonnetje": "the receipt", "geleden": "ago",
    "retourbeleid": "the return policy", "artikel": "the item; article",
    "terugbrengen": "to return (an item)", "regel": "arrange (with ik, part of regelen)",
    "Retourbeleid": "the return policy", "aankoop": "the purchase",
    "defect": "defective", "exemplaar": "the copy; item (replacement)",
    "teruggekregen": "got back (past participle of terugkrijgen)",
})

# B1 unit 01 (hypothetische situaties/hypothetical situations), added
# 2026-07-11. "zou"/"misschien"/"geweldig"/"Soms" reuse the gloss already
# established for their existing capitalized/lowercase sentence-initial
# sibling (same meaning, safe direct reuse, see this file's own docstring
# note on this round); "Toch" is this unit's own capitalized sentence-
# initial variant of the lowercase "toch" this same block defines.
NL_GLOSSES.update({
    "Spanje": "Spain", "zou": "would", "zouden": "would (plural)",
    "jullie": "you (plural)", "rijk": "rich", "vaker": "more often",
    "Stel": "imagine (imperative, in 'stel je voor')",
    "loterij": "the lottery", "winnen": "to win", "stoppen": "to stop",
    "wereld": "the world", "rondreizen": "to travel around",
    "misschien": "maybe", "meteen": "immediately",
    "geweldig": "great; wonderful", "kon": "could", "kiezen": "to choose",
    "willen": "to want", "Anouk": "Anouk (a Dutch female name)",
    "Soms": "sometimes", "denkt": "thinks", "opnieuw": "again",
    "studeren": "to study", "worden": "to become",
    "kosten": "to cost; to take (time)", "toch": "still; nevertheless",
    "Toch": "still; nevertheless", "bezoeken": "to visit",
})

# B1 unit 02 (mening en nuance/opinion and nuance), added 2026-07-11.
# "sommige" reuses the existing capitalized "Sommige" ("Some") gloss --
# same meaning, safe direct reuse. "Steeds" (capitalized, this unit's own
# "steeds meer" = "more and more") is a REAL polysemy/homograph collision
# with the pre-existing lowercase "steeds" = "still" (part of "nog steeds",
# unit16) -- given its own fresh entry rather than reused, see this file's
# own docstring note on this round.
NL_GLOSSES.update({
    "hoewel": "although", "vlees": "meat", "ondanks": "despite",
    "milieu": "the environment", "echter": "however",
    "sommige": "some", "makkelijk": "easy", "kleine": "little (inflected)",
    "stap": "the step", "daarmee": "with that; with it",
    "groente": "vegetables", "gezondheid": "health",
    "Steeds": "more and more (with a comparative, e.g. 'steeds meer')",
    "Sommigen": "some (people)", "Anderen": "others",
    "vooral": "mainly; especially", "veranderen": "to change",
    "enerzijds": "on one hand", "anderzijds": "on the other hand",
})

# B1 unit 03 (werkoverleg/workplace meetings), added 2026-07-11. "Beste"
# (this unit's own email-salutation "Beste collega's," = "Dear
# colleagues,") is a REAL homograph collision with the pre-existing
# lowercase "beste" = "best (attributive)" (unit14's superlative) -- given
# its own fresh entry rather than reused. "groet" (this unit's own "met
# vriendelijke groet" = "kind regards," a common noun) is likewise given
# its own fresh entry rather than reused from the pre-existing capitalized
# "Groet" (a standalone unit11 message-closing PHRASE, a different
# grammatical role for the same underlying word).
NL_GLOSSES.update({
    "rapport": "the report", "nakijken": "to check; to review",
    "voorstellen": "to propose; to suggest", "vergadering": "the meeting",
    "beginnen": "to begin; to start", "punt": "the point; the item",
    "bespreken": "to discuss", "afronden": "to finish; to complete",
    "cijfers": "the figures; the numbers",
    "lukken": "to work out; to succeed",
    "gang": "way (in 'ga uw gang,' go ahead)",
    "jaarverslag": "the annual report", "Beste": "Dear (letter/email salutation)",
    "collega's": "colleagues", "ontvang": "receive (with ik)",
    "opmerkingen": "comments", "hoop": "hope (with ik)",
    "lukt": "works out; succeeds",
    "vriendelijke": "kind; friendly (inflected)",
    "groet": "regards; greeting", "Jasper": "Jasper (a Dutch male name)",
    "mogelijk": "possible",
})

# B1 unit 04 (ingewikkelde zinnen/relative clauses), added 2026-07-11. "Ken"
# reuses the existing lowercase "ken" ("know (with je, inverted)") gloss --
# same meaning, safe direct reuse (both are the "Ken je...?"/"ken je...?"
# question form). "stad" (this unit's own common noun "the city") is a REAL
# collision with the pre-existing capitalized "Stad" -- that token is a
# unit14 comparison-ad placeholder brand/product name classified as a
# proper noun, an unrelated meaning -- given its own fresh entry rather
# than reused.
NL_GLOSSES.update({
    "collega": "the colleague", "aardig": "nice; kind",
    "stad": "the city", "praat": "talk (with ik)",
    "waarover": "about which", "interessant": "interesting",
    "Ken": "know (with je, inverted)", "vrouw": "the woman",
    "Bedoel": "mean (question form, with je)", "geboren": "born",
    "wereldje": "small world (diminutive of wereld)", "drinkt": "drinks",
    "toevallig": "coincidental; what a coincidence",
    "vriendin": "girlfriend; female friend",
    "universiteit": "the university", "bedrijf": "a company",
    "Sara": "Sara (a name)", "vlak": "right (next to); close",
})

# B1 unit 05 (indirecte rede/indirect speech), added 2026-07-11. "Later"
# reuses the existing lowercase "later" gloss -- same meaning, safe direct
# reuse.
NL_GLOSSES.update({
    "zei": "said", "gehoord": "heard", "ophalen": "to pick up",
    "Later": "later", "belde": "called", "konden": "could (plural)",
})

# B1 unit 06 (verplichtingen/obligations), added 2026-07-11. "alles" reuses
# the existing capitalized "Alles" ("Everything") gloss -- same meaning,
# safe direct reuse.
NL_GLOSSES.update({
    "schoonmaken": "to clean", "kamer": "the room", "eerder": "earlier",
    "opruimen": "to tidy up", "hoef": "need to (don't need to, with ik)",
    "vanavond": "tonight",
    "hoeft": "need to (don't need to, with hij/zij/u)",
    "cadeau": "the present; the gift", "roken": "to smoke",
    "rookvrij": "smoke-free", "gebouw": "the building",
    "Trouwens": "by the way", "wist": "knew", "niets": "nothing",
    "alles": "everything", "geregeld": "arranged", "vriend": "friend",
    "gelukkig": "fortunately",
    "zelf": "-self (emphatic, e.g. himself)", "brengt": "brings",
})

# B1 unit 07 (kunnen en konden/ability, present and past), added
# 2026-07-11. "Vorige" reuses the existing lowercase "vorige" ("previous;
# last") gloss -- same meaning, safe direct reuse. ophalen/kon/eerder/zou/
# gelukkig were already classified by earlier B1 units above.
NL_GLOSSES.update({
    "moest": "had to (past of moeten)", "Vorige": "previous; last",
    "mogelijkheid": "the possibility",
})

# B1 unit 08 (reële en irreële situaties/real and unreal conditionals),
# added 2026-07-11. "Nu" reuses the existing lowercase "nu" ("now") gloss --
# same meaning, safe direct reuse. "Vorig" (uninflected, used with the
# het-word "jaar") is a distinct exact token from "Vorige" (inflected, used
# with the de-word "week") -- ordinary Dutch adjective agreement, not a
# homograph, each gets its own entry since dict keys are exact strings.
# zou/studeren/eerder/Sara/willen were already classified by earlier B1
# units above.
NL_GLOSSES.update({
    "geweten": "known (past participle of weten)", "feest": "the party",
    "Vorig": "last (uninflected, with a het-word like 'jaar')",
    "hoorde": "heard (simple past)", "Nu": "now",
    "voorwaarde": "the condition",
})

# B1 unit 09 (eens en oneens/agreement and disagreement), added 2026-07-11.
# worden/Toch/denkt were already classified by earlier B1 units above.
NL_GLOSSES.update({
    "ermee": "with it (in 'het ermee eens zijn')",
    "vierdaagse": "four-day (inflected)", "werkweek": "the work week",
    "bedrijven": "companies", "zegt": "says",
    "gelukkiger": "happier", "blijf": "remain; stay (with ik)",
    "sceptisch": "skeptical", "praten": "to talk",
})

# B1 unit 10 (werkverantwoordelijkheden/work responsibilities), added
# 2026-07-11. rapport was already classified by unit03 above.
NL_GLOSSES.update({
    "verantwoordelijk": "responsible", "medicatie": "the medication",
    "patiënten": "the patients", "klaar": "done; ready",
    "gepland": "planned", "planning": "the schedule; the planning",
    "ergens": "somewhere; something", "meneer": "Mr.; sir",
    "Bakker": "Bakker (a Dutch surname)", "vraagt": "asks",
    "taak": "the task",
})

# B1 unit 11 (een verhaal vertellen/telling a story), added 2026-07-11.
# belde/opnieuw/zei/kon/Sara were already classified by earlier B1 units
# above.
NL_GLOSSES.update({
    "Terwijl": "while",
    "nam": "took (simple past of nemen, in 'nam niet op,' didn't answer)",
    "Toen": "when; then",
    "opnam": "picked up (the phone; simple past of opnemen)",
    "deed": "did (simple past of doen)", "jammer": "a shame; a pity",
    "gebeurde": "happened (simple past of gebeuren)",
    "grappigs": "funny (indeclinable form after 'iets')",
    "Uiteindelijk": "in the end; eventually",
    "lachten": "laughed (plural simple past of lachen)",
    "verhaal": "the story", "grappig": "funny",
})

# A1 units 43-48 (seasons, emergencies, lost items, appointments, library
# borrowing, waste sorting), added 2026-07-12 alongside UNIT_FILES' extended
# range above.
NL_GLOSSES.update({
    "seizoen": "the season", "lente": "spring", "zomer": "summer",
    "herfst": "autumn; fall", "winter": "winter",
    "eigenschap": "the characteristic; property", "schaatsen": "to ice-skate",
    "tulpen": "tulips", "seizoenen": "seasons",
    "allemaal": "all; everyone", "Vier": "four",
    "favorieten": "favorites",
    "brand": "fire", "alarmnummer": "emergency number",
    "nooduitgang": "emergency exit", "politie": "police",
    "ambulance": "ambulance", "brandweer": "fire brigade",
    "Politie": "police", "iedereen": "everyone", "Rustig": "calm",
    "Iedereen": "everyone", "112": "112",
    "kwijt": "missing; lost", "gevonden": "found",
    "portemonnee": "wallet", "Telefoon": "phone",
    "spannend": "exciting; tense", "genoeg": "enough",
    "Woensdag": "Wednesday", "computerhulp": "computer help",
    "Voor": "for", "Waarvoor": "for what; what for",
    "bevestigd": "confirmed", "help": "help (with ik)",
    "herinneren": "to remind",
    "lenen": "to borrow", "bibliotheekpas": "library card",
    "28": "28", "weken": "weeks", "leenbon": "loan receipt",
    "Leenbon": "loan receipt", "leent": "borrows",
    "geleend": "borrowed", "leen": "borrow (with ik)",
    "afval": "waste; trash", "scheiden": "to sort; to separate",
    "GFT": "organic waste", "bak": "bin", "Restafval": "residual waste",
    "grijze": "grey", "Papier": "paper", "container": "container",
    "glasbak": "glass recycling container", "glas": "glass",
    "papier": "paper", "ophaaldag": "collection day",
    "Maandag": "Monday", "Afvalkalender": "waste collection calendar",
    "Donderdag": "Thursday", "restafval": "residual waste",
    "gescheiden": "sorted; separated", "bakken": "bins",
    "regels": "rules",
})

# Case variants are tokens in their own right because provenance preserves the
# realization spelling. Their gloss is the explicit lexical gloss above.
for _token in (
    "Achtenveertig Ben Bent Dagen Dan Dat De En Er Goed Het Hoe Hoeveel Ik Inleverdatum Is Ja Jou Kom Kun Leuk "
    "Maanden Mijn Nee Niet Nul Om Op Tot Twaalf Vandaag Waar Wanneer Wat Welke Wij"
).split():
    if _token not in NL_GLOSSES:
        NL_GLOSSES[_token] = NL_GLOSSES[_token.casefold()]

for _number in "0 00 06 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 18 19 20 21 22 24 25 28 29 30 31 32 40 42 43 45 48 50 65 75 87 90 99 112 2024 2026".split():
    NL_GLOSSES[_number] = _number

SYMBOLS = set("'s 0 00 06 07 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 24 25 28 29 30 31 32 40 42 43 45 48 50 65 75 87 90 99 112 500 2024 2026".split())
PROPER_NOUNS = {"België", "Duitsland", "Egypte", "Lotte", "Nederland", "Noor", "Omar",
                "Rotterdam", "Sander", "Fenna", "Jan", "Marieke", "Utrecht", "Amsterdam",
                "Bergsport", "Schoudertas", "Stad", "Centraal", "M"}
PRONOUNS = set("ik Ik je jij jou Jou me u Wij wij Mijn mijn Welke welke Wat wat Hoeveel hoeveel jouw haar hem iets zich we We Hij hij Deze deze die zij welk Waarmee Ze Zij Jij U Zijn wie mij uw".split())
PREPOSITIONS = set("aan bij in met na naar om Om op Op over te tot Tot uit voor vóór per naast tegenover achter tussen van vanaf In Na Bij boven Van tegen Met".split())
PARTICLES = set("behalve dan Dan dat Dat de De dit Dit dus een Een en En er Er geen Geen het Het Ja ja Nee nee Niet niet of ook wel maar nog Anders af eerst Eerst pas want als plus toe st O langs Als Maar omdat".split())
ADJECTIVES = set("Belgisch beleefd Duits Engels formeel Goed goed hele informeel laat Leuk leuk Nederlands nieuw normaal open oud slecht volgende elke Mooi gewone scheidbaar korte kort vriendelijk voltooide voltooid meeste sterke algemene blauwe andere ene lekker groot klein groter kleiner duur goedkoop duurder goedkoper bijvoeglijk gelijk mooi praktisch duurst beter best onregelmatig beste meer Veel meest dezelfde lange sterk lichter sterker grote nodig mooist licht beleefde ziek verkouden Ziek bijvoeglijke zelfstandige moe Elke Sommige benieuwd eigen extra vroeg fijn gezellig nieuwe welkom bewolkt koud warm zonnig Fijn blauw blij boos verdrietig zenuwachtig trots lief zwart".split())
ADVERBS = set("avonds vandaan halverwege hier hoe Hoe hoeveelste middags nachts ochtends terug vandaag Vandaag waar Waar wanneer Wanneer graag vaak natuurlijk links rechts linksaf rechtsaf rechtdoor Rechtdoor Graag achteraan daarna Daarna eruit samen meestal gisteren vanmorgen Gisteren Vanmorgen Daar daar liever Liever zo net minder Precies precies al veel steeds Nog nu eigenlijk later altijd snel binnen Hier Natuurlijk Waarom alleen echt eerlijk heel vast apart contant".split())
VERBS = set("begint ben Ben bent Bent heb Heb heet inschrijven is Is kom Kom komt Komt kost krijgen leer moet ontmoeten spreek wil wilt woon wonen Wonen woont zijn zitten Kun kun herhalen gaat drinken eten Mag mag Zie hebben neem kan Kan pinnen Kijk ga sla loop Ga Sla Loop gedaan opstaan sta aankleden kleed ontbijten ontbijt werken werk eet afwassen was slapen slaap staat ziet gaan Zullen zullen stellen maakt afspreken geeft staan spreken gebruik gedronken gegaan Denk gebruiken gegeten gewerkt kopen gekocht komen gekomen vinden vind Vind fietsen wandelen winkelen doen Houden drukt houd Zeg Wil zien kiest houdt voeg Gebruik vergelijken werkt heeft koop Koop koopt Wilt vertrekt moeten Let stappen voel scheelt Gaat helpen Heeft Neem Rust drink Voel genomen rusten begin denk doe krijgt maak stop zeggen klinkt Laten blijven kijken maken regent Maak Past Spreek afrekenen bel bellen belt betaalt betalen betekent dacht delen geholpen gezegd ging hebt helpt hoor horen neemt nemen passen past spreekt stuur vertellen voelt vragen zoek Betaald kunt denken".split())
PHRASES = {"Aangenaam", "Goedemiddag", "Goedemorgen", "Goedenavond", "Hallo", "Hoi", "Prima", "ziens",
           "alstublieft", "alsjeblieft", "eraan", "Bedankt", "Sorry", "Groet", "Beterschap", "Perfect"}
NOUNS = set("Achtenveertig Dagen Inleverdatum Maanden Medewerker Nul Pauze Taalcafé Twaalf Welkom Workshop acht achtentwintig achtentwintigste achtenveertig achtste achttien achttiende april augustus avond bibliotheek bijdrage boek boeken cent dag dank datum december derde dertien dertiende dertig dertigste dinsdag donderdag drie drieëntwintigste drieënveertig eenendertigste eenentwintig eenentwintigste eenheid eerste elf elfde euro februari groep half hoofdletter huisnummer inleverdatum jaar januari juli juni keer kwart kwartier maand maandag maart mei mensen middag naam nacht negen negende negenennegentig negenentwintigste negentien negentiende negentig november nul nummer ochtend oktober rooster september stoelen taalcafé tachtig tafel telefoonnummer tien tiende tiental tijd twaalf twaalfde twee tweede tweeëndertig tweeëntwintig tweeëntwintigste tweeënveertig twintig twintigste uur veertien veertiende veertig vier vierde vierentwintigste vijf vijfde vijfentwintigste vijfenzestig vijfenzeventig vijftien vijftiende vijftig vrijdag vrijdagmiddag week woensdag workshop zaal zaterdag zes zesde zesentwintigste zestien zestiende zestig zeven zevende zevenentachtig zevenentwintigste zeventien zeventiende zeventig zondag één "
              "vader moeder ouders broer zus kind kinderen opa oma oom tante neef nicht gezin maand familie broers zussen "
              "koffie thee water melk sap brood broodje kaas appel appelsap Menukaart Koffie Thee Broodje Appelsap "
              "markt winkel kraam appels peren tomaten paprika's Appels Peren Tomaten Paprika's kilo honderd gram pond stuk stuks "
              "prijskaartje Verkoper Twee "
              "station supermarkt ziekenhuis bank postkantoor bushalte buurt kaart buurtkaart BUURTKAART "
              "Bibliotheek Ziekenhuis Postkantoor Supermarkt Bank Bushalte "
              "route Route START DOEL "
              "hoofdzin deel einde werkwoord "
              "film activiteit manier zin idee plan reden afwijzing afspraak bericht uitnodiging Vrijdag "
              "gesprekken gebeurtenis deelwoord eindpositie werkwoorden "
              "tomatensoep activiteiten voorkeur muziek films smaak trui optie park "
              "naamwoord rugzak tas vijfenveertig dingen superlatief keuze treinreis ruimte reis vorm schoudertas vergelijkingen "
              "kaartje retour balie perron trein vertraging plaats minuten ingang uitgang wachtruimte "
              "Kaartje Vertrek Aankomst Retour Prijs bord probleem Perron enkele "
              "hoofdpijn buikpijn keelpijn koorts Koorts naamwoorden apotheek tablet Advies dagen huisarts Dank morgen "
              "baan beroep kantoor kok pauze restaurant ritme uren verpleegkundige "
              "appartement Appartement badkamer balkon kamers keuken slaapkamer slaapkamers tuin woonkamer "
              "Morgen Weerbericht Zaterdag Zondag wandeling weekend weer weerbericht "
              "Rekening Totaal Winterjas broek dienst hoofdgerechten jas kleur koffies maat pin rekening schoenen sms totaal vijfendertig vijfentwintig wisselgeld zorgen beetje".split())

# A2 units 24-28 (gemeente/meningen/bankrekening/huisarts/probleem melden),
# added 2026-07-07 alongside UNIT_FILES_A2 above.
SYMBOLS.update({"s"})
PROPER_NOUNS.update({"BSN", "DigiD"})
PRONOUNS.update({"Alles", "Uw", "ze", "waarmee"})
PREPOSITIONS.update({"Sinds", "sinds", "Volgens", "Aan", "Tussen"})
PARTICLES.update({"indien"})
ADJECTIVES.update({
    "geldig", "vorige", "persoonlijke", "gevaarlijk", "smal", "eens",
    "veiliger", "breder", "weinig", "mobiel", "ernstig", "scheidbare",
    "vervelend", "Geweldig",
})
ADVERBS.update({
    "online", "vooraf", "Misschien", "helemaal", "mee", "erg",
    "waarschijnlijk", "morgenochtend", "thuis", "gisteravond", "gedeeltelijk",
})
VERBS.update({
    "schrijven", "Zou", "schikken", "Moet", "meenemen", "ontvangt", "regelen",
    "ingeschreven", "stort", "Storten", "storten", "bankieren", "gebruikt",
    "geopend", "Heeft", "openen", "snap", "bespaart", "wordt", "vindt",
    "Maakt", "schrijf", "rust", "innemen", "terugkomen", "voorgeschreven",
    "Voelt", "ontvangen", "sturen", "Bel",
})
PHRASES.update({"Alstublieft"})
NOUNS.update({
    "paspoort", "huurcontract", "geboorteakte", "adres", "overheid", "zaken",
    "gemeente", "documenten", "toepassing", "inschrijving", "post",
    "Ambtenaar", "orde", "paar", "hulp", "fietspad", "mening", "kant",
    "voetgangers", "fietsers", "pad", "auto", "straat", "bankrekening",
    "betaalrekening", "salaris", "werkgever", "infinitief",
    "identiteitsbewijs", "bankpas", "app", "klachten", "pijn", "griepje",
    "recept", "pillen", "infinitieven", "Diagnose", "dokter", "verwarming",
    "monteur", "melding", "contact", "Bevestiging", "woningcorporatie",
    "Woningcorporatie", "bezoek", "Huisarts", "vierentwintig",
})

# A2 unit 73 (sollicitatiegesprek/job interview), added 2026-07-10 alongside
# the new realization file picked up by UNIT_FILES_A2's broad glob.
PROPER_NOUNS.update({"Kantoor", "Bloem"})
ADJECTIVES.update({
    "administratief", "belangrijke", "goede", "beschikbaar",
})
ADVERBS.update({"pre"})
VERBS.update({
    "solliciteren", "zoekt", "langskomen", "Typen", "Vertelt", "had",
    "gesolliciteerd",
})
NOUNS.update({
    "vacature", "medewerker", "sollicitatiegesprek", "ervaring",
    "vrijwilliger", "vaardigheid", "vaardigheden", "werktijden",
    "klantcontact", "gesprek",
    "Ervaring", "Werktijden",
})

# A2 unit 74 (reisvertraging/travel disruption), added 2026-07-11.
PROPER_NOUNS.update({"Arnhem", "Amersfoort", "NS"})
PREPOSITIONS.update({"door", "via", "Over"})
ADJECTIVES.update({"alternatieve", "Belangrijke"})
ADVERBS.update({"ongeveer", "inderdaad", "even"})
VERBS.update({
    "valt", "mis", "rijden", "kunnen", "omreizen", "duurt", "adviseren",
    "raadplegen", "uitgevallen", "weten", "Kunt",
})
NOUNS.update({
    "seinstoring", "aansluiting", "servicebalie", "verbinding", "intercity",
    "mededeling", "treinen", "Reizigers", "reizigers", "reisplanner", "spoor",
})

# A2 unit 75 (schermtijd/screen time and online habits), added 2026-07-11.
PRONOUNS.update({"hun"})
PARTICLES.update({"Jawel"})
ADJECTIVES.update({"sociale", "Sociale", "gezond"})
ADVERBS.update({"Eigenlijk"})
VERBS.update({
    "chat", "doorbrengen", "brengen", "kijk", "wegleggen", "probeer", "Probeer",
})
NOUNS.update({"scherm", "telefoon", "media", "schermtijd", "gewoonte", "apps"})

# A2 unit 76 (drukke week/describing a weekly schedule), added 2026-07-11.
PREPOSITIONS.update({"Door"})
ADJECTIVES.update({"doordeweekse", "vol", "Volgende", "druk", "vrij"})
ADVERBS.update({"Ten", "slotte", "Best", "gewoon"})
VERBS.update({"zit", "leest"})
NOUNS.update({
    "cursus", "volgorde", "avondeten", "verschil", "agenda", "woensdagavond",
    "taalcursus", "lekkers",
})

# A2 unit 77 (iets terugbrengen/shopping complaint and returns), added
# 2026-07-11.
ADJECTIVES.update({"kapot", "defect"})
ADVERBS.update({"geleden"})
VERBS.update({
    "ruilen", "terugkrijgen", "terugbrengen", "regel", "teruggekregen",
})
NOUNS.update({
    "koptelefoon", "linkerkant", "geld", "bonnetje", "retourbeleid",
    "artikel", "Retourbeleid", "aankoop", "exemplaar",
})

# Units 29-33 (hobbies, appearance, animals, sports, transportation), added
# 2026-07-09 alongside UNIT_FILES' extended range above -- still the same
# "Dutch A1" course, not a new course boundary (see UNIT_FILES' own comment).
PROPER_NOUNS.update({"Opa", "Nina", "Pico"})
PHRASES.update({"Oké"})
PRONOUNS.update({"Je", "Die", "beiden", "ons", "Welk"})
PREPOSITIONS.update({"zonder"})
PARTICLES.update({"zoals"})
ADJECTIVES.update({
    "vrije", "ontspannend", "elk", "lang", "jong", "Oud", "blond", "bruin",
    "grijs", "groen", "bruine", "groene", "langer", "anders", "onbepaald",
    "zelfstandig", "eerdere", "alle", "specifieke", "Beide", "dicht",
    "rustig", "ver",
})
ADVERBS.update({
    "soms", "nooit", "buiten", "allebei", "hard", "bijna", "dichtbij",
})
VERBS.update({
    "lezen", "sporten", "koken", "sport", "kook", "lees", "luisteren",
    "tekenen", "teken", "gamen", "luister", "game", "Kook", "kookt", "Game",
    "weet", "zie", "betekenen", "blijft", "herken", "kent", "ontkent",
    "ken", "uitlaten", "Uitlaten", "geven", "geef", "spelen", "speelt",
    "verdubbelt", "Laat", "houden", "doet", "Doen", "noemt", "loopt",
    "bewegen", "zwemt", "proberen", "reist", "lopen", "reizen", "fietst",
    "rijdt", "rijd",
})
NOUNS.update({
    "vrienden", "de-woorden", "het-woorden", "hobby's", "aantal", "jaren",
    "indruk", "getal", "Haar", "woord", "lidwoord", "ogen", "meervoud",
    "meisje", "patroon", "dier", "huisdier", "hond", "kat", "vis", "vogel",
    "les", "Meervoud", "honden", "dieren", "klinker", "medeklinker",
    "katten", "vissen", "vogels", "voetbal", "yoga", "hardlopen", "zwemmen",
    "Hardlopen", "huis", "fiets", "lessen", "woorden", "vervoer", "loket",
    "onbekende", "centrum", "Fietsen",
})

# Units 43-48 (seasons, emergencies, lost items, appointments, library
# borrowing, waste sorting), added 2026-07-12 alongside UNIT_FILES' extended
# range above.
PROPER_NOUNS.update({"GFT"})
PRONOUNS.update({"iedereen", "Iedereen"})
PREPOSITIONS.update({"Voor"})
ADJECTIVES.update({
    "kwijt", "gevonden", "spannend", "grijze", "Rustig", "gescheiden",
})
ADVERBS.update({"allemaal", "genoeg"})
VERBS.update({
    "schaatsen", "help", "herinneren", "lenen", "leent", "geleend", "leen",
    "scheiden",
})
NOUNS.update({
    "seizoen", "lente", "zomer", "herfst", "winter", "eigenschap",
    "tulpen", "seizoenen", "Vier", "favorieten", "brand", "alarmnummer",
    "nooduitgang", "politie", "Politie", "ambulance", "brandweer",
    "portemonnee", "Telefoon", "Woensdag", "computerhulp", "Waarvoor",
    "bevestigd", "bibliotheekpas", "weken", "leenbon", "Leenbon",
    "afval", "bak", "Restafval", "Papier", "container", "glasbak",
    "glas", "papier", "ophaaldag", "Maandag", "Afvalkalender",
    "Donderdag", "restafval", "bakken", "regels",
})


# B1 units 01-11, added 2026-07-11. Grouped by unit for traceability, same
# convention as every prior round's POS-set additions. Case-dup/homograph
# tokens whose gloss is reused/distinct per the NL_GLOSSES comments above
# still need their OWN exact-string POS-set membership here, since
# nl_part_of_speech() keys on the exact token too.

# Unit 01.
PROPER_NOUNS.update({"Spanje", "Anouk"})
ADJECTIVES.update({"rijk", "geweldig"})
ADVERBS.update({"vaker", "misschien", "meteen", "opnieuw", "toch", "Toch", "Soms"})
VERBS.update({
    "zou", "zouden", "Stel", "winnen", "stoppen", "rondreizen", "kon",
    "kiezen", "willen", "denkt", "studeren", "worden", "kosten", "bezoeken",
})
NOUNS.update({"loterij", "wereld"})
PRONOUNS.update({"jullie"})

# Unit 02.
ADJECTIVES.update({"sommige", "makkelijk", "kleine"})
ADVERBS.update({"echter", "vooral", "enerzijds", "anderzijds", "Steeds"})
VERBS.update({"veranderen"})
NOUNS.update({"vlees", "milieu", "stap", "groente", "gezondheid"})
PRONOUNS.update({"daarmee", "Sommigen", "Anderen"})
PREPOSITIONS.update({"ondanks"})
PARTICLES.update({"hoewel"})

# Unit 03.
ADJECTIVES.update({"vriendelijke", "mogelijk"})
NOUNS.update({
    "rapport", "vergadering", "punt", "cijfers", "gang", "jaarverslag",
    "collega's", "opmerkingen",
})
VERBS.update({
    "nakijken", "voorstellen", "beginnen", "bespreken", "afronden",
    "lukken", "ontvang", "hoop", "lukt",
})
PROPER_NOUNS.update({"Jasper"})
ADJECTIVES.update({"Beste"})
NOUNS.update({"groet"})

# Unit 04.
NOUNS.update({
    "collega", "stad", "vrouw", "wereldje", "vriendin", "universiteit",
    "bedrijf",
})
ADJECTIVES.update({"aardig", "interessant", "toevallig"})
VERBS.update({"praat", "Ken", "Bedoel", "geboren", "drinkt"})
PRONOUNS.update({"waarover"})
PROPER_NOUNS.update({"Sara"})
ADVERBS.update({"vlak"})

# Unit 05.
VERBS.update({"zei", "gehoord", "ophalen", "belde", "konden"})
ADVERBS.update({"Later"})

# Unit 06.
VERBS.update({
    "schoonmaken", "opruimen", "hoef", "hoeft", "roken", "wist",
    "geregeld", "brengt",
})
ADVERBS.update({"eerder", "vanavond", "Trouwens", "gelukkig"})
NOUNS.update({"kamer", "cadeau", "gebouw", "vriend"})
ADJECTIVES.update({"rookvrij"})
PRONOUNS.update({"niets", "alles", "zelf"})

# Unit 07.
VERBS.update({"moest"})
ADJECTIVES.update({"Vorige"})
NOUNS.update({"mogelijkheid"})

# Unit 08.
VERBS.update({"geweten"})
NOUNS.update({"feest", "voorwaarde"})
ADJECTIVES.update({"Vorig"})
VERBS.update({"hoorde"})
ADVERBS.update({"Nu"})

# Unit 09.
PRONOUNS.update({"ermee"})
ADJECTIVES.update({"vierdaagse", "gelukkiger", "sceptisch"})
NOUNS.update({"werkweek", "bedrijven"})
VERBS.update({"zegt", "blijf", "praten"})

# Unit 10.
ADJECTIVES.update({"verantwoordelijk", "klaar"})
NOUNS.update({
    "medicatie", "patiënten", "planning", "meneer", "taak",
})
VERBS.update({"gepland", "vraagt"})
PRONOUNS.update({"ergens"})
PROPER_NOUNS.update({"Bakker"})

# Unit 11.
PARTICLES.update({"Terwijl", "Toen"})
VERBS.update({"nam", "opnam", "deed", "gebeurde", "lachten"})
ADJECTIVES.update({"jammer", "grappigs", "grappig"})
ADVERBS.update({"Uiteindelijk"})
NOUNS.update({"verhaal"})


def nl_part_of_speech(token: str) -> str:
    for pos, members in (
        ("symbol", SYMBOLS), ("proper_noun", PROPER_NOUNS), ("pronoun", PRONOUNS),
        ("preposition", PREPOSITIONS), ("particle", PARTICLES), ("adjective", ADJECTIVES),
        ("adverb", ADVERBS), ("verb", VERBS), ("phrase", PHRASES), ("noun", NOUNS),
    ):
        if token in members:
            return pos
    raise ValueError(f"missing explicit Dutch part of speech for {token!r}")


def nl_agreement_tags(token: str, lesson_key: str) -> dict[str, object]:
    t = token.casefold()
    semantic: list[str] = []
    unit_lesson = lesson_key.split(".")[-1]
    lesson_categories = {
        "jij_je_en_u": "register_language", "groeten_en_welzijn": "wellbeing",
        "namen": "name_exchange", "herkomst_en_taal": "origin_language",
        "taalcafe": "cafe_small_talk", "eerste_ontmoeting": "first_meeting_dialogue",
        "nul_tot_twaalf": "number", "vanaf_dertien": "number",
        "telefoon_en_huisnummer": "contact_number", "leeftijd_en_aantallen": "age_quantity",
        "prijzen": "price", "inschrijven_bij_de_bibliotheek": "library_registration",
        "weekdagen": "weekday", "maanden": "month", "rangtelwoorden": "ordinal_number",
        "datum_vragen": "date_expression", "bibliotheekdatum": "library_date",
        "taalcafe_afspraak": "cafe_appointment", "hele_en_halve_uren": "clock_time",
        "kwartieren": "quarter_hour", "hoe_laat": "time_question",
        "digitale_tijd_en_dagdelen": "time_of_day", "rooster_lezen": "schedule",
        "afspreken_bij_het_taalcafe": "cafe_meetup_time",
        "direct_family": "family_member", "extended_family": "extended_family_member",
        "mijn_je": "possessive_pronoun", "zijn_haar": "possessive_pronoun",
        "lotte_profiel": "family_profile", "taalcafe_familie_dialoog": "family_dialogue",
        "dranken": "drink", "ik_wil_graag": "food_request",
        "aantallen_bestellen": "polite_request", "wat_wilt_u": "food_request",
        "menukaart": "menu_item", "taalcafe_bestelling": "food_dialogue",
        "op_de_markt": "market_place", "prijs_vragen": "price_question",
        "hoeveelheden": "quantity_phrase", "prijskaartjes": "price_label",
        "kopen_en_betalen": "buying_paying", "marktgesprek": "market_dialogue",
        "plaatsen": "common_place", "naast_en_tegenover": "location_position",
        "achter_en_voor": "location_position", "waar_en_meer_plaatswoorden": "location_question",
        "eenvoudige_kaart": "map_reading", "waar_is_de_bushalte": "place_dialogue",
        "richtingswoorden": "direction_word", "bevelsvormen": "imperative_direction",
        "de_weg_vragen": "route_question", "korte_route": "short_route",
        "route_op_de_kaart": "route_map", "vanaf_het_taalcafe": "route_dialogue",
        "dagelijkse_activiteiten": "daily_activity", "scheidbare_werkwoorden": "separable_verb_lesson",
        "activiteiten_en_tijden": "routine_time", "eerst_dan_daarna": "sequence_lesson",
        "omars_routine_lezen": "routine_reading", "een_dag_bij_het_taalcafe": "routine_dialogue",
        "een_activiteit_voorstellen": "activity_proposal", "ja_of_nee": "accept_decline",
        "dag_en_tijd_afspreken": "schedule_time", "een_bericht_lezen": "invitation_reading",
        "een_plan_schrijven": "plan_writing", "lotte_en_omar_maken_een_plan": "plan_dialogue",
        "voltooide_tijd": "past_tense_intro", "met_hebben": "hebben_perfect",
        "met_zijn": "zijn_perfect", "wanneer_gebeurde_het": "past_event_time",
        "een_kort_verslag_lezen": "past_reading", "lotte_en_omar_gisteren": "past_dialogue",
        "eten_en_drinken": "taste_preference", "activiteiten": "activity_lesson",
        "houden_van": "strong_preference", "kiezen": "preference_choice",
        "voorkeur_lezen": "preference_reading", "lotte_en_omar_kiezen": "preference_dialogue",
        "grootte_vergelijken": "size_comparison", "prijzen_vergelijken": "price_comparison",
        "net_zo_als": "equal_comparison", "de_beste_keuze": "superlative_choice",
        "advertentie_lezen": "comparison_reading", "lotte_en_omar_kiezen_tas": "comparison_dialogue",
        "een_kaartje_kopen": "ticket_purchase", "vertrektijd_en_perron": "departure_time",
        "vertraging": "delay_announcement", "de_weg_op_het_station": "station_directions",
        "een_kaartje_lezen": "ticket_reading", "lotte_en_omar_op_reis": "travel_dialogue",
        "niet_lekker_voelen": "feeling_unwell", "wat_scheelt_eraan": "symptom_question",
        "koorts_en_verkouden": "fever_cold", "bij_de_apotheek": "pharmacy_visit",
        "advies_lezen": "health_reading", "lotte_checkt_omar": "health_dialogue",
        "wat_doe_je_voor_werk": "job_question", "waar_werk_je": "workplace_question",
        "mijn_werkdag": "work_schedule", "collegas_beschrijven": "colleague_description",
        "werkprofielen_lezen": "work_profile_reading", "werk_gesprek": "work_dialogue",
        "mijn_appartement": "apartment_description", "hoeveel_kamers": "room_count_question",
        "balkon_en_tuin": "housing_feature", "groot_of_klein": "room_size",
        # NOTE: unit18's lesson05 real content_key is
        # nl.a1.unit18.lesson05.advertentie_lezen -- its bare lesson-name
        # segment ("advertentie_lezen") is IDENTICAL to unit14's own
        # lesson05 ("nl.a1.unit14.lesson05.advertentie_lezen"), and this
        # dict is keyed by that bare segment alone (see the "zijn"
        # homograph note in this file's module docstring for the same
        # class of same-string/different-context limitation). No new
        # entry is added here for it -- unit18 lesson05's tokens simply
        # inherit unit14's existing "comparison_reading" value by
        # coincidence. Harmless: no practice template anywhere keys a
        # slot_preset on that literal string, it is purely descriptive
        # metadata. Flagging so a future editor doesn't mistake this for
        # a missing entry and add a duplicate "advertentie_lezen" key,
        # which would silently overwrite (and corrupt) unit14's mapping
        # instead, since Python dict literals keep only the last value
        # for a repeated key with no error.
        "nieuw_appartement": "apartment_dialogue",
        "wat_voor_weer": "weather_question", "koud_of_warm": "temperature_description",
        "het_weerbericht": "weather_forecast", "plannen_maken_bij_weer": "weather_plan",
        "weerbericht_lezen": "weather_reading", "weekend_plannen": "weekend_plan_dialogue",
        "ik_zoek_een_jas": "clothing_item_request", "welke_maat": "clothing_size",
        "welke_kleur": "clothing_color", "past_het": "clothing_fit",
        # unit20's lesson05 AND unit23's lesson05 both use the exact same
        # bare content_key suffix "bonnetje_lezen" (one unit reads a
        # clothing receipt, the other a restaurant bill) -- same dict-
        # keyed-by-bare-suffix collision already documented above for
        # unit14/unit18's "advertentie_lezen". A single shared, honestly
        # generic value ("receipt_reading") is correct for BOTH lessons
        # (both really are "read a receipt" comprehension exercises), so
        # this is not a corruption risk like the advertentie_lezen case --
        # deliberately reused, not accidental.
        "bonnetje_lezen": "receipt_reading", "winterjas_passen": "clothing_dialogue",
        "blij_verdrietig_boos": "basic_feeling", "waarom_ben_je_blij": "feeling_reason",
        "zenuwachtig_voor_iets": "nervous_about", "naar_gevoelens_vragen": "feeling_question",
        "bericht_lezen": "feeling_message_reading", "eerste_dienst_gesprek": "feeling_dialogue",
        "ik_bel_je": "phone_call_intro", "met_wie_spreek_ik": "phone_identity",
        "kun_je_dat_herhalen": "phone_clarification", "een_sms_sturen": "text_message",
        "sms_gesprek_lezen": "text_exchange_reading", "telefoontje_na_dienst": "phone_call_dialogue",
        "hoeveel_kost_het": "total_price_question", "pinnen_of_contant": "payment_method",
        "de_rekening_delen": "bill_splitting", "wisselgeld": "change_handling",
        "rekening_vragen": "bill_dialogue",
        # A2 unit 24 (gemeente/bureaucracy), added 2026-07-07.
        "een_afspraak_maken": "appointment_scheduling",
        "wat_heb_je_nodig": "document_requirements",
        "bij_de_balie": "counter_interaction", "je_bsn_nummer": "bsn_explanation",
        "brief_lezen": "registration_letter_reading",
        "gemeente_afspraak": "gemeente_dialogue",
        # A2 unit 25 (meningen/opinions), added 2026-07-07.
        "wat_vind_je_daarvan": "opinion_question", "volgens_mij": "opinion_phrase",
        "eens_of_niet_eens": "agreement_disagreement",
        "aan_de_andere_kant": "counterargument",
        "forumbericht_lezen": "opinion_reading", "fietspad_gesprek": "opinion_dialogue",
        # A2 unit 26 (bankrekening/banking), added 2026-07-07.
        "rekening_openen": "account_opening",
        "betaalrekening_voor_salaris": "salary_account",
        "bij_de_bank": "bank_counter_interaction", "mijn_bankpas": "bank_card_info",
        "folder_lezen": "banking_reading", "bank_afspraak": "bank_dialogue",
        # A2 unit 27 (huisarts/health), added 2026-07-07.
        "afspraak_bij_huisarts": "doctor_appointment",
        "wat_zijn_de_klachten": "symptom_question", "de_diagnose": "diagnosis",
        "recept_en_advies": "prescription_advice",
        "samenvatting_lezen": "health_summary_reading",
        "huisarts_consult": "doctor_dialogue",
        # A2 unit 28 (probleem melden/housing), added 2026-07-07.
        "er_is_een_probleem": "housing_problem_report",
        "de_verwarming_werkt_niet": "heating_problem",
        "wanneer_komt_de_monteur": "technician_scheduling",
        "een_melding_doen": "issue_report",
        "bevestiging_lezen": "confirmation_reading",
        "verwarming_melden": "housing_report_dialogue",
        # Unit 29 (hobbies), added 2026-07-09.
        "lezen_sporten_koken": "hobby_verbs_set1",
        "muziek_tekenen_gamen": "hobby_verbs_set2",
        "vrije_tijd_vraag": "free_time_question",
        "taalcafe_hobbies": "hobby_dialogue",
        "hobbys_vergelijken": "hobby_reading",
        "weekend_plan": "hobby_weekend_dialogue",
        # Unit 30 (appearance), added 2026-07-09.
        "lang_klein_oud_jong": "appearance_size_age",
        "haar_beschrijven": "appearance_hair",
        "ogen_en_eruitzien": "appearance_eyes",
        "taalcafe_nina": "appearance_dialogue",
        "sander_fenna_vergelijken": "appearance_reading",
        "taalcafe_herkenning": "appearance_recognition_dialogue",
        # Unit 31 (animals and pets), added 2026-07-09.
        "huisdieren_woorden": "pet_noun_lesson",
        "zorg_voor_huisdieren": "pet_care",
        "van_dieren_houden": "pet_plural_preference",
        "taalcafe_lottes_hond": "pet_dialogue",
        "omar_fenna_sander_dieren": "pet_reading",
        "taalcafe_ninas_vogel": "pet_wrapup_dialogue",
        # Unit 32 (sports and exercise), added 2026-07-09.
        "sport_woorden": "sport_noun_lesson",
        "hoe_vaak_sport_je": "sport_frequency",
        "ik_sport_graag": "sport_preference",
        "taalcafe_sander_hardlopen": "sport_dialogue",
        "lotte_fenna_sport": "sport_reading",
        "taalcafe_samen_sporten": "sport_wrapup_dialogue",
        # Unit 33 (transportation), added 2026-07-09. "een_kaartje_kopen" is
        # deliberately NOT re-added here -- this unit's lesson03 (buying a
        # train ticket) reuses the exact same bare content_key suffix as
        # unit15's own "een_kaartje_kopen" lesson (also a ticket-purchase
        # scenario), same dict-keyed-by-bare-suffix collision already
        # documented above for advertentie_lezen/bonnetje_lezen -- unit15's
        # existing "ticket_purchase" value is honestly generic enough to
        # cover both, and this is purely descriptive metadata no template
        # keys a slot_preset on directly, so reusing it is safe, not a bug.
        "vervoer_woorden": "transport_noun_lesson",
        "iedereen_reist_anders": "transport_habit",
        "taalcafe_fenna_omar": "transport_dialogue",
        "wie_reist_hoe": "transport_reading",
        "taalcafe_samen_fietsen": "transport_wrapup_dialogue",
        # Unit 43 (seasons), added 2026-07-12.
        "lente_en_zomer": "season_noun_lesson",
        "herfst_en_winter": "season_noun_lesson",
        "gesprek_bij_het_taalcafe": "season_dialogue",
        "lezen_seizoenen": "season_reading",
        "sander_komt_erbij": "season_wrapup_dialogue",
        # Unit 44 (emergencies), added 2026-07-12.
        "hulp_en_brand": "emergency_help",
        "alarmnummer_en_nooduitgang": "emergency_safety_noun_lesson",
        "politie_ambulance_brandweer": "emergency_service_noun_lesson",
        "brand_bij_het_taalcafe": "emergency_dialogue",
        "lezen_over_de_brand": "emergency_reading",
        "sander_komt_aan": "emergency_wrapup_dialogue",
        # Unit 45 (lost items), added 2026-07-12.
        "kwijt_en_gevonden": "lost_found_status",
        "telefoon_rugzak_portemonnee": "lost_item_noun_lesson",
        "nina_vraagt_bij_de_balie": "lost_item_dialogue",
        "bericht_gevonden_telefoon": "lost_item_reading",
        "sander_checkt_zijn_portemonnee": "lost_item_wrapup_dialogue",
        # Unit 46 (appointments), added 2026-07-12.
        "afspraak_maken": "appointment_scheduling",
        "tijd_beschikbaar": "appointment_time_availability",
        "computerhulp": "appointment_purpose",
        "omar_helpt_herinneren": "appointment_wrapup_dialogue",
        # Unit 47 (library borrowing), added 2026-07-12.
        "lenen_en_terugbrengen": "library_borrow_return",
        "bibliotheekpas": "library_card",
        "inleverdatum": "due_date",
        "balie_lenen": "library_borrow_dialogue",
        "leenbon_lezen": "library_receipt_reading",
        "terug_bij_taalcafe": "library_wrapup_dialogue",
        # Unit 48 (waste sorting), added 2026-07-12.
        "afval_scheiden": "waste_sorting",
        "de_bakken": "waste_bin_lesson",
        "papier_en_glas": "recyclable_material_lesson",
        "omar_helpt_nina": "waste_sorting_dialogue",
        "afvalkalender_lezen": "waste_calendar_reading",
        "lotte_hoort_het": "waste_sorting_wrapup_dialogue",
        # A2 unit 73 (sollicitatiegesprek/job interview), added 2026-07-10.
        "ik_wil_solliciteren": "job_application_interest",
        "ik_bel_over_de_vacature": "job_interview_appointment",
        "mijn_ervaring_en_vaardigheden": "experience_and_skills",
        "ben_ik_beschikbaar": "availability_and_hours",
        "een_vacature_lezen": "job_ad_reading",
        "het_sollicitatiegesprek": "job_interview_dialogue",
        # A2 unit 74 (reisvertraging/travel disruption), added 2026-07-11.
        "er_is_een_vertraging": "delay_report",
        "de_trein_valt_uit": "cancellation_report",
        "ik_mis_mijn_aansluiting": "missed_connection",
        "bij_de_servicebalie": "service_desk_request",
        "mededeling_lezen": "disruption_notice_reading",
        "lotte_bij_de_balie": "disruption_dialogue",
        # A2 unit 75 (schermtijd/screen time and online habits), added
        # 2026-07-11.
        "ik_gebruik_mijn_telefoon_vaak": "phone_use_frequency",
        "ik_chat_met_vrienden": "chat_habit",
        "te_veel_schermtijd": "screen_time_opinion",
        "minder_tijd_op_je_telefoon": "reduce_screen_time_opinion",
        "blog_lezen": "screen_time_reading",
        "omar_en_lotte_praten": "screen_time_dialogue",
        # A2 unit 76 (drukke week/describing a weekly schedule), added
        # 2026-07-11.
        "op_maandag_en_woensdag": "weekly_schedule_days",
        "eerst_werken_dan_sporten": "sequencing_activities",
        "door_de_week_versus_weekend": "weekday_weekend_contrast",
        "een_drukke_agenda": "busy_schedule",
        "ninas_week_lezen": "weekly_schedule_reading",
        "lotte_en_omar_over_de_week": "weekly_schedule_dialogue",
        # A2 unit 77 (iets terugbrengen/shopping complaint and returns),
        # added 2026-07-11.
        "deze_koptelefoon_is_kapot": "broken_item_report",
        "ik_wil_mijn_geld_terug": "refund_request",
        "heeft_u_het_bonnetje_nog": "receipt_question",
        "het_retourbeleid": "return_policy_statement",
        "beleid_lezen": "return_policy_reading",
        "omar_brengt_de_koptelefoon_terug": "return_dialogue",
        # B1 unit 01 (hypothetische situaties/hypothetical situations),
        # added 2026-07-11.
        "ik_zou_graag": "hypothetical_wish_singular",
        "wij_zouden": "hypothetical_wish_plural",
        "als_had_was": "unreal_conditional_als",
        "de_loterij": "lottery_hypothetical",
        "opnieuw_kiezen": "redo_choice_hypothetical",
        # B1 unit 02 (mening en nuance/opinion and nuance), added
        # 2026-07-11.
        "hoewel": "concession_hoewel",
        "ondanks_dat": "concession_ondanks_dat",
        "toch_echter": "contrast_toch_echter",
        "gesprek_vlees": "opinion_dialogue_meat",
        "artikel_minder_vlees": "opinion_article_reading",
        # B1 unit 03 (werkoverleg/workplace meetings), added 2026-07-11.
        "zou_u": "polite_request_zou_u",
        "voorstellen": "meeting_proposal",
        "agenda_vragen": "meeting_agenda_question",
        "overleg_met_bakker": "meeting_dialogue",
        "email_lezen": "meeting_email_reading",
        # B1 unit 04 (ingewikkelde zinnen/relative clauses), added
        # 2026-07-11. "die"/"dat"/"waar" are single-word bare lesson-key
        # suffixes -- verified no collision with any existing
        # lesson_categories key (every other key in this dict is a
        # multi-word snake_case string).
        "die": "relative_clause_die",
        "dat": "relative_clause_dat",
        "waar": "relative_clause_waar",
        "klein_wereldje": "small_world_dialogue",
        "sara_lezen": "relative_clause_reading",
        # B1 unit 05 (indirecte rede/indirect speech), added 2026-07-11.
        "zei_dat": "reported_speech_statement",
        "zei_dat_zou": "reported_speech_future",
        "vroeg_of": "reported_speech_question",
        "omar_belde": "reported_speech_dialogue",
        "omar_belde_lezen": "reported_speech_reading",
        # B1 unit 06 (verplichtingen/obligations), added 2026-07-11.
        "moet_schoonmaken": "obligation_moet",
        "had_moeten_opruimen": "past_regret_had_moeten",
        "hoef_niet_koken": "no_obligation_hoeven",
        "mag_niet_roken": "prohibition_mag_niet",
        "omar_bezoek_lezen": "obligation_reading",
        # B1 unit 07 (kunnen en konden/ability, present and past), added
        # 2026-07-11.
        "kan_paspoort_ophalen": "present_ability_kan",
        "kon_niet_komen": "past_ability_kon",
        "had_kunnen_ophalen": "past_regret_had_kunnen",
        "zou_kunnen_afspraak": "hypothetical_ability_zou_kunnen",
        "paspoort_lezen": "ability_reading",
        # B1 unit 08 (reële en irreële situaties/real and unreal
        # conditionals), added 2026-07-11.
        "reele_conditie_park": "real_conditional",
        "onreele_heden_studeren": "unreal_present_conditional",
        "onreele_verleden_feest": "unreal_past_conditional",
        "weekend_dialoog": "conditional_dialogue",
        "sara_feest_lezen": "conditional_reading",
        # B1 unit 09 (eens en oneens/agreement and disagreement), added
        # 2026-07-11.
        "eens_werkweek": "agreement_eens",
        "oneens_werkweek": "disagreement_oneens",
        "jij_zegt_dat": "restating_opinion",
        "debat_dialoog": "debate_dialogue",
        "werkweek_lezen": "debate_reading",
        # B1 unit 10 (werkverantwoordelijkheden/work responsibilities),
        # added 2026-07-11.
        "verantwoordelijk_medicatie": "job_responsibility_statement",
        "bijna_klaar_rapport": "work_status_update",
        "zou_u_kunnen_helpen": "polite_help_request",
        "bakker_dialoog": "workplace_dialogue",
        "werkdag_lezen": "workday_reading",
        # B1 unit 11 (een verhaal vertellen/telling a story), added
        # 2026-07-11.
        "terwijl_koken": "background_action_terwijl",
        "eerst_later": "sequencing_eerst_later",
        "toen_opnam": "past_narrative_toen",
        "sara_dialoog": "storytelling_dialogue",
        "verhaal_lezen": "storytelling_reading",
        # B1's own review lesson (unit 01-11's "wrapup_production" bare
        # suffix, identical across all 11 units) -- same intentional
        # bare-suffix-collision-reuse precedent already established for
        # advertentie_lezen/bonnetje_lezen/een_kaartje_kopen elsewhere in
        # this dict: every one of these 11 lessons really is the same kind
        # of generic unit-review production wrapup, so one shared
        # descriptive value is correct, not a missing-entry bug.
        "wrapup_production": "b1_unit_review",
    }
    semantic.append(lesson_categories[unit_lesson])
    if t in {"jij", "je"}: semantic.append("informal_address")
    if t == "u": semantic.append("polite_address")
    if token in {"Hallo", "Hoi", "Goedemorgen", "Goedemiddag", "Goedenavond"}: semantic.append("greeting")
    if t in {"goed", "prima", "slecht"}: semantic.append("wellbeing_answer")
    if token in {"Lotte", "Noor", "Omar", "Sander", "Fenna", "Jan", "Marieke"}: semantic.append("person_name")
    if token in {"Nederland", "België", "Duitsland", "Egypte"}: semantic.append("place_name")
    if token in {"Rotterdam", "Utrecht", "Amsterdam"}: semantic.append("place_name")
    if t in {"nederland", "belgië", "duitsland", "egypte"}: semantic.append("country")
    if t in {"nederlands", "belgisch", "engels", "duits"}: semantic.append("language_or_nationality")
    # Unit 5 (family): narrower tags so practice-template slots only ever
    # combine grammatically valid words -- see the homograph note in this
    # file's module docstring for why "zijn" (his) is deliberately excluded.
    if t in {"broer", "zus"}: semantic.append("sibling")
    if t in {"vader", "moeder", "broer", "zus", "kind", "opa", "oma", "oom", "tante"}:
        semantic.append("family_singular")
    if t in {"opa", "oma", "oom", "tante"}: semantic.append("extended_only")
    # Exact-case check (not casefolded): the capitalized "Mijn" variant is a
    # separate lexeme (sentence-initial only, from units 2-4) and must NOT
    # be eligible here -- every practice-template slot using this tag places
    # the word mid-sentence, where a capital would render as a real
    # capitalization error (e.g. "Dit is Mijn broer.").
    if token in {"mijn", "je", "jouw"}: semantic.append("possessive_flexible")
    # Narrower than place_name: only Dutch city names (spelled identically in
    # English), safe for a translation-frame slot with default token
    # rendering. place_name also includes country names whose english_gloss
    # differs from the raw token (Nederland -> "the Netherlands"), which
    # would leak an untranslated Dutch word into an English frame if used
    # the same way -- narrow this instead of reusing place_name there.
    if token in {"Rotterdam", "Utrecht", "Amsterdam"}: semantic.append("city_name")
    number_words = set("nul één twee drie vier vijf zes zeven acht negen tien elf twaalf dertien veertien vijftien zestien zeventien achttien negentien twintig dertig veertig vijftig zestig zeventig tachtig negentig eenentwintig tweeëntwintig tweeëndertig tweeënveertig achtenveertig vijfenzeventig negenennegentig drieënveertig vijfenzestig zevenentachtig achtentwintig vijfentwintig vijfendertig vierentwintig".split())
    if t in number_words or token in SYMBOLS and token != "'s": semantic.append("number")
    # Extended 2026-07-06 (unit17: negen/twaalf/vijf/elf are the real
    # clock-hour numbers this unit's schedule content actually uses --
    # "Ik begin om negen uur."/"Ik heb pauze om twaalf uur."/"Ik stop om
    # vijf uur."/"Ik begin later, om elf uur.").
    if t in {"twee", "drie", "zeven", "acht", "veertien", "achttien", "twintig", "negen", "twaalf", "vijf", "elf"} or token in {"2", "3", "7", "8", "14", "18", "20"}: semantic.append("hour_number")
    if t in set("maandag dinsdag woensdag donderdag vrijdag zaterdag zondag".split()): semantic.append("weekday")
    # "weekday" above is contaminated for matching_pairs use: the
    # lesson_categories catch-all tags EVERY token introduced in the
    # "weekdagen" lesson (including "hoofdletter"/"dag"/"Dagen", which are
    # NOT weekday names) with the same "weekday" string, and the casefold
    # comparison above also folds in the capitalized sentence-initial
    # "Vrijdag" as a case-duplicate of "vrijdag" -- both already documented
    # as a real, unfixed bug in docs/content/practice/en-nl/a1_unit11.yaml's
    # review notes. Added here (additive only, does not change "weekday"
    # itself, so every existing template that already reads "weekday" keeps
    # its current behavior) so a matching_pairs preset can request a clean,
    # exact-case, case-deduplicated 7-member pool instead.
    if token in {"maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"}:
        semantic.append("weekday_pure")
    if t in set("januari februari maart april mei juni juli augustus september oktober november december".split()): semantic.append("month")
    if t.endswith(("de", "ste")) and t not in {"de", "zelfde"}: semantic.append("ordinal_number")
    if t in {"ochtend", "middag", "avond", "nacht", "ochtends", "middags", "avonds", "nachts", "vrijdagmiddag"}: semantic.append("time_of_day")
    if t in {"ochtend", "middag", "avond", "nacht"}: semantic.append("day_period")
    # Unit 7 (shopping at the market): produce items are the same 4-member
    # group across every lesson (they're literally what's for sale) --
    # a single reusable tag, safe as both a bare-word recognition slot and
    # embedded in "een kilo {item}" / "Dan neem ik een kilo {item},
    # alstublieft." frames, since every member is a plural mass/count noun
    # that collocates naturally with "kilo".
    if t in {"appels", "peren", "tomaten", "paprika's"}: semantic.append("produce")
    # "produce" above is casefolded, so it also matches the capitalized
    # sentence-initial variants ("Appels", "Peren", "Tomaten", "Paprika's")
    # as case-duplicates of the same word -- harmless for the existing
    # bare-word/translation slots that already use "produce" (each draw is
    # independent), but a matching_pairs slot could draw both cases of the
    # same word into two different "pairs". Additive exact-case tag for
    # matching_pairs use only.
    if token in {"appels", "peren", "tomaten", "paprika's"}: semantic.append("produce_pure")
    # Narrower than a generic "quantity" tag: only kilo/pond are directly
    # attested with "tomaten" in this unit's real content ("Een pond
    # tomaten, alstublieft."); "gram" always collocates with "honderd" (never
    # bare "een gram"), and "stuk" pairs with a count context, not a weight
    # phrase -- excluded to avoid an unnatural-sounding generated sentence.
    if t in {"kilo", "pond"}: semantic.append("market_quantity")
    # Unit 8 (locating places): a 7-member "place" tag (both lowercase and
    # the capitalized map-label variants) for bare-word recognition, plus a
    # narrower "place_non_station" tag excluding "station" -- every
    # generated sentence in this unit fixes "het station" as the anchor
    # place ("De {item} is naast het station."), so including "station"
    # itself in the fillable slot would risk a self-referential sentence
    # ("The station is next to the station."), same bug class as nl-en
    # unit09's hospital self-reference catch earlier this session.
    if t in {"station", "supermarkt", "bibliotheek", "ziekenhuis", "bank", "postkantoor", "bushalte"}:
        semantic.append("place")
    if t in {"supermarkt", "bibliotheek", "ziekenhuis", "bank", "postkantoor", "bushalte"}:
        semantic.append("place_non_station")
    # All 4 are freely interchangeable in "De X is {item} het station."/
    # "Het X is {item} de Y." location frames -- verified against this
    # unit's real content, which uses all 4 with the same "is ... het
    # station" sentence shape.
    if t in {"naast", "tegenover", "achter", "voor"}: semantic.append("position")
    # Unit 9 (directions): the 5 core direction words, safe as a group for
    # bare-word recognition only (not a single shared generative frame --
    # "sla" idiomatically only pairs with linksaf/rechtsaf, never rechtdoor,
    # see turn_direction below).
    if t in {"links", "rechts", "linksaf", "rechtsaf", "rechtdoor"}:
        semantic.append("direction_word")
    # Casefolded above, so "Rechtdoor" (capitalized sentence-initial variant)
    # is a case-duplicate of "rechtdoor" under this tag -- harmless for
    # existing bare-word slots, but unsafe for a matching_pairs slot (could
    # draw both cases as if they were two different pairs). Additive
    # exact-case tag for matching_pairs use only.
    if token in {"links", "rechts", "linksaf", "rechtsaf", "rechtdoor"}:
        semantic.append("direction_word_pure")
    # Narrower: only these two are attested after "Sla ___." in this unit's
    # real content ("Sla linksaf."/"Sla rechtsaf.") -- "rechtdoor" pairs with
    # "ga", not "sla" ("Sla rechtdoor" is not idiomatic Dutch), so it is
    # deliberately excluded from this tag.
    if t in {"linksaf", "rechtsaf"}: semantic.append("turn_direction")
    # Unit 10 (daily routine): all 7 routine-verb INFINITIVES (both
    # separable and non-separable) are safe together for bare-word
    # recognition only -- there's no shared sentence frame here (each
    # conjugated ik-form is irregular/differently-structured: sta/kleed/
    # ontbijt/werk/eet/was/slaap), so this tag is never used to fill a
    # generative frame, only to test infinitive-to-meaning recognition.
    if t in {"opstaan", "aankleden", "ontbijten", "werken", "eten", "afwassen", "slapen"}:
        semantic.append("routine_verb_infinitive")
    # Only 3 members -- kept out of multiple_choice/listen_select (which
    # need >=4 real candidates), used only in translation/fill_in_blank
    # templates below.
    if t in {"eerst", "dan", "daarna"}: semantic.append("sequence_word")
    # Unit 11 (making simple plans): 4-member bare-word recognition set
    # spanning adverb/verb/noun -- deliberately recognition-only (no shared
    # frame), since these words don't collocate uniformly (e.g. "samen"
    # is an adverb modifying a whole proposal, "afspreken" a verb, "bericht"/
    # "uitnodiging" nouns for different concrete things).
    if t in {"samen", "afspreken", "bericht", "uitnodiging"}:
        semantic.append("plan_vocab")
    # Unit 12 (perfect tense): the two auxiliary groups must NEVER be mixed
    # in one tag -- "Ik heb gegaan" is ungrammatical (gaan/komen take zijn,
    # not hebben). 4-member hebben-participle group is safe for bare-word
    # recognition (their infinitives are also tagged separately below).
    if t in {"gedronken", "gegeten", "gewerkt", "gekocht"}: semantic.append("participle_hebben")
    if t in {"drinken", "eten", "werken", "kopen"}: semantic.append("infinitive_hebben")
    # Only 2 members (gaan/komen take zijn) -- kept out of multiple_choice/
    # listen_select, used only in translation templates below.
    if t in {"gegaan", "gekomen"}: semantic.append("participle_zijn")
    # Only 2 members -- same reasoning, translation-only.
    if t in {"gisteren", "vanmorgen"}: semantic.append("recent_time")
    # Unit 13 (expressing preferences): "lekker" (food/drink) and "leuk"
    # (activities) are grammatically distinct registers in Dutch and must
    # never be mixed into one generative frame (real content explicitly
    # teaches this contrast) -- kept as two separate 3-member tags, each
    # verified safe in its own "Ik vind {item} lekker/leuk." frame.
    if t in {"koffie", "thee", "tomatensoep"}: semantic.append("lekker_food")
    if t in {"fietsen", "wandelen", "winkelen"}: semantic.append("activity_leuk")
    # Broader 6-member bare-word recognition tag spanning both groups
    # (mixed noun/verb) -- safe since recognition doesn't require shared
    # collocation, only the two frame-specific tags above are used
    # generatively.
    if t in {"koffie", "thee", "tomatensoep", "fietsen", "wandelen", "winkelen"}:
        semantic.append("preference_item")
    # Unit 14 (making comparisons): 6-member regular comparative tag, all
    # verified safe in "De rugzak is {item} dan de tas." (each -er/-der
    # form takes "dan" grammatically; the real content's own advertisement
    # actually uses lichter/sterker to describe the bag, but the frame's
    # own subject/object choice here is a drill sentence, not a factual
    # claim, so reversed pairings are still grammatically valid).
    if t in {"groter", "kleiner", "duurder", "goedkoper", "lichter", "sterker"}:
        semantic.append("comparative_adj")
    # Only 2 members ("net zo {item} als" doesn't take -er/-st at all) --
    # kept out of multiple_choice/listen_select, translation/fill_in_blank
    # only.
    if t in {"mooi", "praktisch"}: semantic.append("equal_adj")
    # 4-member bare-word recognition only -- these superlatives are
    # structurally too different to share one generative frame (duurst/
    # mooist are predicative -st forms, beste is attributive, meest
    # modifies ruimte differently) -- same discipline as this unit's
    # sibling tags above.
    if t in {"duurst", "mooist", "beste", "meest"}: semantic.append("superlative_word")
    # Unit 15 (traveling by train): 6-member bare-word recognition tag
    # spanning station/travel nouns -- no shared generative frame needed,
    # recognition-only.
    if t in {"kaartje", "perron", "vertraging", "ingang", "uitgang", "wachtruimte"}:
        semantic.append("travel_noun")
    # Casefolded above, so "Kaartje"/"Perron" (capitalized sentence-initial
    # variants) are case-duplicates under this tag -- harmless for existing
    # bare-word slots, unsafe for matching_pairs. Additive exact-case tag
    # for matching_pairs use only.
    if token in {"kaartje", "perron", "vertraging", "ingang", "uitgang", "wachtruimte"}:
        semantic.append("travel_noun_pure")
    # Narrower 3-member subset (just the station places), safe for "Waar
    # is de {item}?" -- verified all three take "de" and fit this exact
    # question shape, directly attested for wachtruimte in the real
    # content.
    if t in {"ingang", "uitgang", "wachtruimte"}: semantic.append("station_place")
    # Unit 16 (describing a basic health problem): the core grammar point
    # is that symptom NOUNS take hebben (Ik heb hoofdpijn.) while symptom
    # ADJECTIVES take zijn (Ik ben ziek.) -- the real content's own
    # zijn_note lesson makes this contrast explicit, so these two tags
    # must NEVER be mixed (mixing would generate "Ik heb ziek."/"Ik ben
    # hoofdpijn.", both ungrammatical), same discipline as unit12's
    # participle_hebben/participle_zijn split.
    if t in {"hoofdpijn", "buikpijn", "keelpijn", "koorts"}: semantic.append("symptom_hebben")
    # Casefolded above, so "Koorts" (capitalized sentence-initial variant) is
    # a case-duplicate of "koorts" under this tag -- harmless for existing
    # bare-word slots, unsafe for matching_pairs. Additive exact-case tag
    # for matching_pairs use only.
    if token in {"hoofdpijn", "buikpijn", "keelpijn", "koorts"}: semantic.append("symptom_hebben_pure")
    # Only 2 members -- kept out of multiple_choice/listen_select (which
    # need >=4), used only in word_order/fill_in_blank/translation.
    if t in {"ziek", "verkouden"}: semantic.append("symptom_zijn")
    # Unit 17 (work and occupation): broad 8-member recognition-only tag
    # (bare-word MC/listen_select/translation), safe because it's never
    # used to fill one shared generative sentence -- restaurant/
    # ziekenhuis/kantoor each take a different article/preposition
    # combination (een restaurant / het ziekenhuis / op kantoor with no
    # article at all), verified directly from this unit's real content.
    if t in {"beroep", "kok", "verpleegkundige", "restaurant", "ziekenhuis", "kantoor", "baan", "pauze"}:
        semantic.append("work_vocab")
    # Exact-case variant for matching_pairs (avoids a casefold case-dup
    # drawing e.g. both "Pauze" and "pauze" as if they were two different
    # pairs), same convention as every other _pure tag in this file.
    if token in {"beroep", "kok", "verpleegkundige", "restaurant", "ziekenhuis", "kantoor", "baan", "pauze"}:
        semantic.append("work_vocab_pure")
    # Narrower 2-member generative tag: kok/verpleegkundige both take
    # "werken als" + the bare occupation noun with no article --
    # verified ("Ik werk als kok."/"Ik werk als verpleegkundige."),
    # unlike the workplace nouns above which are deliberately excluded
    # from any shared generative frame.
    if t in {"kok", "verpleegkundige"}: semantic.append("occupation")
    # Narrower 2-member generative tag: begin/stop are both regular
    # ik-form verbs sharing the identical "Ik {verb} om {hour} uur."
    # frame shape (verified: "Ik begin om negen uur."/"Ik stop om vijf
    # uur."). "pauze" is deliberately excluded -- its real sentence is
    # "Ik heb pauze om {hour} uur.", built around a different verb
    # ("heb", not the {verb} slot itself), so mixing it in would drop
    # "heb" and generate an ungrammatical sentence.
    if t in {"begin", "stop"}: semantic.append("schedule_verb")
    # Unit 18 (housing): 5-member generative room tag. "een" is Dutch's
    # single invariant indefinite article (unlike "de"/"het" for
    # definites), so "Ik heb een {item}." is grammatically safe for all
    # 5 members regardless of each noun's own gender -- verified: real
    # content uses "een appartement"/"een woonkamer"/"een slaapkamer"/
    # "een keuken"/"een badkamer".
    if t in {"appartement", "woonkamer", "slaapkamer", "keuken", "badkamer"}:
        semantic.append("room_word")
    if token in {"appartement", "woonkamer", "slaapkamer", "keuken", "badkamer"}:
        semantic.append("room_word_pure")
    # Broader 7-member recognition-only tag (adds balkon/tuin) -- safe
    # for bare-word MC/listen_select/translation, NOT a shared
    # generative frame: balkon/tuin use the "Er is (geen) {item}."
    # existential pattern, a different sentence shape from the room
    # words' "Ik heb een {item}."
    if t in {"appartement", "woonkamer", "slaapkamer", "keuken", "badkamer", "balkon", "tuin"}:
        semantic.append("housing_vocab")
    if token in {"appartement", "woonkamer", "slaapkamer", "keuken", "badkamer", "balkon", "tuin"}:
        semantic.append("housing_vocab_pure")
    # 3-member recognition-only tag -- groot/klein/gezellig each attach
    # to a different subject in the real content (De woonkamer is
    # groot./De keuken is klein./Het appartement is klein maar
    # gezellig.), so kept out of any single shared generative frame,
    # translation/word_order only.
    if t in {"groot", "klein", "gezellig"}: semantic.append("home_adjective")
    # Unit 19 (weather): 4-member generative adjective tag -- all four
    # attach to the impersonal "Het is {item}." pattern (verified: "Het
    # is zonnig."/"Het is bewolkt."/"Het is koud (vandaag)."/"Het is
    # warm (vandaag)." -- dropping the optional "vandaag" leaves a
    # still-valid standalone sentence for koud/warm).
    if t in {"zonnig", "bewolkt", "koud", "warm"}: semantic.append("weather_adj")
    if token in {"zonnig", "bewolkt", "koud", "warm"}: semantic.append("weather_adj_pure")
    # Broader 8-member recognition-only tag (adds regent, a verb, plus
    # weer/weerbericht/wandeling nouns) -- safe for bare-word MC/
    # listen_select/translation only, NOT a shared generative frame:
    # "regent" is impersonal "Het regent." with no adjective slot at
    # all, a different sentence shape from the weather_adj members.
    if t in {"zonnig", "bewolkt", "koud", "warm", "regent", "weer", "weerbericht", "wandeling"}:
        semantic.append("weather_vocab")
    if token in {"zonnig", "bewolkt", "koud", "warm", "regent", "weer", "weerbericht", "wandeling"}:
        semantic.append("weather_vocab_pure")
    # Unit 20 (buying clothes): broad 6-member recognition-only tag
    # (bare-word MC/listen_select/matching_pairs) -- "schoenen" is always
    # plural with no article, "maat"/"kleur" don't collocate with the
    # other 4's "Ik zoek een {item}." shape, so this stays recognition-
    # only, never a shared generative frame.
    if t in {"jas", "trui", "broek", "schoenen", "maat", "kleur"}:
        semantic.append("clothing_noun")
    # Narrower 3-member generative tag: jas/trui/broek are each
    # grammatical after "een" as a singular countable noun -- verified
    # directly ("Ik zoek een jas."); "schoenen" is excluded (always
    # plural, "Ik zoek een schoenen" is ungrammatical).
    if t in {"jas", "trui", "broek"}: semantic.append("clothing_item_singular")
    # Only 2 real colors taught in this unit -- kept out of
    # multiple_choice/listen_select/matching_pairs (need >=3 distinct),
    # used only in word_order/translation/fill_in_blank. Both take the
    # identical "in het {item}" pattern regardless of the color word's
    # own gender, per this unit's own teaching note.
    if t in {"zwart", "blauw"}: semantic.append("color")
    # "klein"/"groot" are already-existing unit14 comparative-lesson
    # adjectives (small/big), reused here bare (not comparative) in this
    # unit's own "Het is te {item}." pattern -- verified directly
    # ("Het is te klein."/"Het is te groot."). Only 2 members, translation/
    # word_order only, same discipline as several sibling 2-member tags
    # above (equal_adj, symptom_zijn, etc.).
    if t in {"klein", "groot"}: semantic.append("size_too_adj")
    # Unit 21 (expressing feelings): 5-member generative adjective tag --
    # all five are verified safe in BOTH "Ik ben {item}." and "Hij voelt
    # zich {item}." (the real content uses "zenuwachtig"/"blij" in both
    # shapes, and "trots" is grammatically identical: "Ik ben trots."/
    # "Hij voelt zich trots." are both natural Dutch), plus the question
    # frame "Waarom ben je {item}?" (real content's own lesson02 teaches
    # exactly this shape for "blij").
    if t in {"blij", "verdrietig", "boos", "zenuwachtig", "trots"}:
        semantic.append("feeling_adj")
    # Unit 22 (calling and texting): 4-member recognition-only tag
    # spanning noun/verb ("sms" is a noun, the rest are verb infinitives)
    # -- no shared generative frame (each collocates differently: "Ik bel
    # je."/"Ik stuur een sms."/"Ik hoor je niet goed."/"Ik moet je iets
    # vertellen." are all structurally different), same discipline as
    # unit11's plan_vocab and unit17's work_vocab.
    if t in {"bellen", "sms", "horen", "vertellen"}: semantic.append("communication_word")
    # Unit 23 (money and paying): 5-member recognition-only verb tag
    # (bare infinitives), also verified safe together in the polite
    # request frame "Mag ik {item}?" -- every member is a natural answer
    # to "what would you like to do" after "mag ik" (verified: "Mag ik
    # pinnen?"/"Mag ik apart afrekenen?" are both real content; "betalen"/
    # "delen"/"vragen" are grammatically identical bare-infinitive slots
    # in the same "Mag ik ...?" shape even where not the literal unit
    # text).
    if t in {"betalen", "pinnen", "afrekenen", "delen", "vragen"}:
        semantic.append("payment_verb")
    # 3-member noun tag -- rekening/wisselgeld/totaal are the three core
    # money nouns taught in this unit, recognition-only (each takes a
    # different article/context: "de rekening", "het wisselgeld", "in
    # totaal"), safe for bare-word MC/listen_select (exactly meets the
    # >=3 distinct-gloss floor).
    if t in {"rekening", "wisselgeld", "totaal"}: semantic.append("payment_noun")
    # A2 unit 27 (huisarts/health: a doctor's visit), added 2026-07-07 by the
    # practice-template authoring pass. Narrow generative tags, each verified
    # against the real lesson content before use in a shared frame:
    # - medical_professional (2 members: huisarts, dokter) is safe in "Ik wil
    #   graag een afspraak maken bij de {item}." -- "bij de huisarts" is the
    #   real unit text; "bij de dokter" is equally natural informal Dutch
    #   (same register as "bij de tandarts").
    if t in {"huisarts", "dokter"}: semantic.append("medical_professional")
    # - symptom_word (3 members: hoofdpijn, koorts, pijn) is safe in "Ik heb
    #   {item}." -- all three are singular/mass nouns for a specific
    #   complaint, verified natural in this exact frame ("Ik heb hoofdpijn."/
    #   "Ik heb koorts."/"Ik heb pijn." are all idiomatic). "klachten" is
    #   deliberately excluded -- it's the plural umbrella term the doctor
    #   asks about (Wat zijn uw klachten?), not something a patient states
    #   this way.
    if t in {"hoofdpijn", "koorts", "pijn"}: semantic.append("symptom_word")
    # - visit_noun (9 members, mixed concrete nouns from across this unit) is
    #   recognition-only (bare-word multiple_choice/listen_select/
    #   matching_pairs) -- no shared generative frame needed, same discipline
    #   as unit11's plan_vocab/unit17's work_vocab/unit22's
    #   communication_word.
    if t in {"huisarts", "afspraak", "reden", "bezoek", "klachten", "griepje", "recept", "pillen", "dokter"}:
        semantic.append("visit_noun")
    # Casefolded above, so "Huisarts" (the capitalized dialogue-speaker-label
    # variant introduced in lesson06) is a case-duplicate of "huisarts" under
    # this tag -- harmless for existing bare-word MC/listen_select slots, but
    # unsafe for matching_pairs (could draw both cases as if they were two
    # different pairs). Additive exact-case tag for matching_pairs use only,
    # same convention as every other _pure tag in this file.
    if token in {"huisarts", "afspraak", "reden", "bezoek", "klachten", "griepje", "recept", "pillen", "dokter"}:
        semantic.append("visit_noun_pure")
    # - reassurance_adj (2 members: ernstig, vervelend) is safe in both
    #   "Het is niet {item}." and "Is het {item}?" -- verified: "Het is niet
    #   ernstig."/"Is het ernstig?" are the real unit text; "Het is niet
    #   vervelend."/"Is het vervelend?" are equally grammatical standalone
    #   sentences (a different but coherent meaning, "it's not
    #   annoying"/"is it annoying?"), not a factual claim this drill needs to
    #   preserve. Only 2 members -- kept out of multiple_choice/listen_select
    #   (need >=3), translation/word_order only.
    if t in {"ernstig", "vervelend"}: semantic.append("reassurance_adj")
    # - separable_health_verb (2 members: innemen, terugkomen, both real
    #   infinitives from this unit's own grammar-note teaching card) is
    #   recognition-only; kept out of multiple_choice/listen_select (need
    #   >=3), used only in matching_pairs (exactly meets the >=2
    #   distinct-token floor).
    if t in {"innemen", "terugkomen"}: semantic.append("separable_health_verb")
    # A2 unit 28 (probleem melden/housing: reporting a maintenance issue),
    # added 2026-07-07 by the same practice-template authoring pass.
    # - housing_report_noun (6 members) is recognition-only (bare-word
    #   multiple_choice/listen_select/matching_pairs), same discipline as
    #   visit_noun above -- these six don't share one generative frame
    #   (verwarming/appartement especially must never be mixed into the same
    #   fillable slot, see heating_word below).
    if t in {"probleem", "verwarming", "monteur", "melding", "contact", "woningcorporatie"}:
        semantic.append("housing_report_noun")
    # Casefolded above, so "Woningcorporatie" (the capitalized dialogue-
    # speaker-label variant introduced in lesson06) is a case-duplicate of
    # "woningcorporatie" under this tag -- same convention as visit_noun_pure
    # above, additive exact-case tag for matching_pairs use only.
    if token in {"probleem", "verwarming", "monteur", "melding", "contact", "woningcorporatie"}:
        semantic.append("housing_report_noun_pure")
    # - heating_word (1 member: verwarming) is the ONLY noun from this unit
    #   safe in "De {item} werkt niet." -- "appartement" is also a noun
    #   taught in the same lesson (de_verwarming_werkt_niet) but "De
    #   appartement werkt niet" is nonsensical (an apartment doesn't "work"),
    #   so it is deliberately excluded from this narrower tag even though
    #   both share the broader housing_report_noun/lesson-category tags.
    if t == "verwarming": semantic.append("heating_word")
    # - technician_word (1 member: monteur) is safe in "Wanneer komt de
    #   {item} langs?" -- the only noun this question can take.
    if t == "monteur": semantic.append("technician_word")
    # - arrival_time_word (1 member: morgenochtend) is safe in "De monteur
    #   komt {item} langs." -- "gisteravond" (yesterday evening) is
    #   grammatically parseable there but temporally contradicts the present-
    #   tense near-future "komt", so it is deliberately excluded.
    if t == "morgenochtend": semantic.append("arrival_time_word")
    # - housing_time_adverb (3 members: morgenochtend, gisteravond, thuis) is
    #   recognition-only (bare-word MC/listen_select/matching_pairs) --
    #   mixed time/location adverbs with no shared frame, same discipline as
    #   unit22's communication_word.
    if t in {"morgenochtend", "gisteravond", "thuis"}: semantic.append("housing_time_adverb")
    # - duration_number (5 members: drie, twee, negen, elf, vierentwintig --
    #   every number token actually introduced across units 27-28's own
    #   realization files) is safe in "Wij nemen binnen {item} uur contact
    #   met u op." (within X hours) and as a bare-word MC/listen_select tag
    #   (5 distinct glosses). Deliberately NOT the broader shared "number"
    #   tag: that pool also includes a same-course token "s" (a genuine,
    #   unrelated pre-existing tagging quirk from unit25's auto's/possessive
    #   marker, still being authored by a parallel session as of this
    #   writing) whose gloss is nonsensical here -- this narrower, unit
    #   27/28-local tag avoids depending on that pool's correctness.
    if t in {"drie", "twee", "negen", "elf", "vierentwintig"}: semantic.append("duration_number")
    # "april" is introduced in the same lesson as the ordinal-number teaching
    # cards (the lesson combines "de vijfde april" -- ordinal + month), so
    # the blanket lesson_categories["rangtelwoorden"] tag above wrongly also
    # marks the month noun itself as an ordinal_number candidate. Every
    # ordinal_number-slot frame in this unit is literally "... {item}
    # april." -- if "item" could resolve to "april", that generates
    # self-referential output ("Het is de april april."), same bug class as
    # the station/hospital self-reference catches elsewhere in this file.
    # Strip the blanket tag from any genuine month noun.
    if "month" in semantic and "ordinal_number" in semantic:
        semantic = [s for s in semantic if s != "ordinal_number"]

    # A2 units 24-26 (gemeente/meningen/bankrekening) practice-template
    # tags, added 2026-07-07. Each tag below is a brand-new, uniquely-named
    # string assigned to exactly the listed tokens -- unlike the blanket
    # lesson_categories tags above (contaminated across every token in a
    # lesson, including unrelated pronouns/particles), these are narrow and
    # safe to use directly as a generative-frame or fill_in_blank slot
    # constraint. Every generative frame below was checked against this
    # unit's real realization content for grammaticality (reversed-pairing
    # convention already established by unit14's comparative_adj/unit21's
    # feeling_adj: a member need not be literally combined with the frame
    # in the source text as long as it's grammatically identical there).
    #
    # Unit 24 (gemeente/bureaucracy).
    if t in {"paspoort", "huurcontract", "geboorteakte", "afspraak", "adres",
             "gemeente", "documenten", "overheid"}:
        semantic.append("gemeente_vocab_noun")
    # 3-member subset verified safe in "Mag ik uw {item} zien?" -- directly
    # attested for paspoort in the real content's own matching_pairs pair
    # ("Mag ik uw paspoort zien?" -> "May I see your passport?"); huurcontract/
    # geboorteakte are grammatically identical objects of the same verb.
    if t in {"paspoort", "huurcontract", "geboorteakte"}:
        semantic.append("gemeente_doc_noun")
    if t in {"inschrijven", "schikken", "regelen", "ontvangt"}:
        semantic.append("gemeente_verb")
    # Single-member tags (exactly one token each, by construction) -- always
    # safe for a fill_in_blank slot regardless of the rest of the course's
    # lexeme pool, matching this unit's own real fill_in_blank exercises.
    if t == "schikken":
        semantic.append("gemeente_schikken_single")
    # Exact-case check (not casefolded): unit27's own realization separately
    # introduces the capitalized sentence-initial "Huisarts" (a different
    # lexeme, same case-duplicate class documented throughout this file --
    # see "weekday"/"weekday_pure") -- casefolding here would silently widen
    # this tag to 2 members and break the single-candidate guarantee.
    if token == "huisarts":
        semantic.append("gemeente_huisarts_single")
    if t == "regelen":
        semantic.append("gemeente_regelen_single")

    # Unit 25 (meningen/opinions).
    if t in {"fietspad", "mening", "idee", "kant", "voetgangers", "fietsers",
             "auto", "straat", "ruimte"}:
        semantic.append("opinion_noun")
    # 5-member generative adjective tag verified safe in "Volgens mij is het
    # fietspad {item}." -- gevaarlijk/smal are directly attested there;
    # veiliger/breder/duur are grammatically identical predicate adjectives
    # in the same slot (reversed-pairing convention, see module note above).
    if t in {"gevaarlijk", "smal", "veiliger", "breder", "duur"}:
        semantic.append("opinion_adj")
    # Exact-case (not casefolded): unrelated earlier units already introduce
    # capitalized "Denk" (unit12, "Denk aan de eindpositie") and "Vind"
    # (unit13, "Vind je dit lekker?") as separate lexemes -- casefolding
    # would silently pull those in as case-duplicates of this unit's own
    # lowercase "denk"/"vind", same class as the huisarts fix above.
    if token in {"vind", "snap", "moeten", "wordt", "denk", "vindt", "bespaart"}:
        semantic.append("opinion_verb")
    if t == "gedeeltelijk":
        semantic.append("opinion_gedeeltelijk_single")
    if t == "veiliger":
        semantic.append("opinion_veiliger_single")

    # Unit 26 (bankrekening/banking).
    if t in {"bankrekening", "betaalrekening", "salaris", "werkgever",
             "identiteitsbewijs", "bankpas", "app"} or token == "Medewerker":
        semantic.append("bank_vocab_noun")
    # 2-member generative tag verified safe in "Ik wil graag een {item}
    # openen." -- both are directly attested opening this way in the real
    # content (lesson01/lesson02).
    if t in {"bankrekening", "betaalrekening"}:
        semantic.append("bank_account_noun")
    # Exact-case (not casefolded): this unit's own lesson02 grammar note
    # separately introduces capitalized sentence-initial "Storten" ("Storten
    # is de infinitief van stort.") as a case-duplicate of lowercase
    # "storten" -- same class as the huisarts/opinion_verb fixes above;
    # casefolding would give this tag a near-duplicate-gloss ("To deposit"
    # vs "to deposit") second member, confusing in a multiple_choice option
    # list even though it's technically the same word.
    if token in {"openen", "storten", "gebruikt", "geopend", "bankieren"}:
        semantic.append("bank_verb")
    if t == "openen":
        semantic.append("bank_openen_single")
    if t == "nodig":
        semantic.append("bank_nodig_single")

    # Unit 29 (hobbies) practice-template tags, added 2026-07-09. 6-member
    # bare-infinitive recognition-only tag (no shared generative frame --
    # each collocates differently, same discipline as unit10's
    # routine_verb_infinitive/unit17's work_vocab).
    if t in {"lezen", "sporten", "koken", "luisteren", "tekenen", "gamen"}:
        semantic.append("hobby_verb")
    # 4-member frequency-adverb tag, verified safe generatively in
    # "Ik lees {item} een boek."/"Ik sport {item} op zaterdag."/"Ik kook
    # {item} voor vrienden." (all four grammatical in each frame -- this is
    # NOT the fill_in_blank ambiguity trap the real unit29 realization
    # flagged, since every practice template here uses translation/
    # word_order with the ENGLISH side disambiguating which word is meant,
    # never a bare Dutch fill_in_blank on this pool).
    if t in {"altijd", "vaak", "soms", "nooit"}: semantic.append("freq_adverb")
    # Single-member tags (by construction, exactly one token each) -- safe
    # fill_in_blank slots regardless of the rest of the course's pool,
    # matching this unit's own real fill_in_blank resolutions (blanking
    # boek/vrienden/vrije rather than the interchangeable hobby verbs/
    # frequency adverbs, per its own review.notes).
    if t == "boek": semantic.append("hobby_boek_single")
    if t == "vrienden": semantic.append("hobby_vrienden_single")
    if t == "vrije": semantic.append("hobby_vrije_single")

    # Unit 30 (appearance) practice-template tags, added 2026-07-09. 4-member
    # hair-color tag (bare form, reusing unit20's "zwart"), verified safe in
    # "Lotte heeft lang {item} haar." -- all four grammatical there ("lang
    # blond/bruin/grijs/zwart haar").
    if t in {"blond", "bruin", "grijs", "zwart"}: semantic.append("hair_color_adj")
    # 3-member eye-color tag (INFLECTED -e forms, since "ogen" is plural and
    # takes agreement per this unit's own ogen_agreement_note), verified safe
    # in "Lotte heeft {item} ogen." -- reuses unit13's already-classified
    # "blauwe".
    if t in {"blauwe", "bruine", "groene"}: semantic.append("eye_color_adj")
    # 2-member tags -- kept out of multiple_choice/listen_select (need >=3),
    # translation/word_order only, matching this unit's own review.notes
    # (blanking lang/kort or oud/jong directly is genuinely ambiguous with
    # no in-frame disambiguation, the same risk class already resolved for
    # unit14/unit20's sibling 2-member tags).
    if t in {"lang", "klein"}: semantic.append("height_adj")
    # Exact-case (not casefolded): this unit's own lesson01 grammar note
    # separately introduces capitalized sentence-initial "Oud" ("Oud kan een
    # precies aantal jaren betekenen...") as a case-duplicate of lowercase
    # "oud" -- same class as the huisarts/opinion_verb fixes elsewhere in
    # this file; casefolding would give this tag a near-duplicate-gloss
    # ("Old" vs "old") second member of the same word, not a real 3rd
    # candidate.
    if token in {"oud", "jong"}: semantic.append("age_adj")
    if t == "ogen": semantic.append("appearance_ogen_single")
    if t == "eruit": semantic.append("appearance_eruit_single")
    # Widen the already-established "person_name" tag (unit01 area) to
    # include this unit's two new named characters -- additive only, does
    # not change what "person_name" already matched, same convention as the
    # weekday_pure/travel_noun_pure "_pure" tags elsewhere in this file.
    if token in {"Nina", "Opa"}: semantic.append("person_name")

    # Unit 31 (animals) practice-template tags, added 2026-07-09. 4-member
    # pet-noun tag, verified safe generatively in "Ik heb een {item}." (all
    # four grammatical there -- safe for translation, where the ENGLISH side
    # disambiguates; NOT used in any bare Dutch fill_in_blank, matching this
    # unit's own review.notes resolution of the identical risk).
    if t in {"hond", "kat", "vis", "vogel"}: semantic.append("pet_noun")
    # 4-member plural tag, verified safe in "Ik houd van {item}." (all four
    # grammatical: "Ik houd van honden/katten/vissen/vogels.").
    if t in {"honden", "katten", "vissen", "vogels"}: semantic.append("pet_noun_plural")
    # 3-member bare-infinitive recognition-only tag (different collocations
    # per this unit's own doc: uitlaten/eten geven/spelen met each take
    # different objects/prepositions) -- same discipline as hobby_verb above.
    # Exact-case (not casefolded): this unit's own lesson02 grammar note
    # separately introduces capitalized sentence-initial "Uitlaten" as a
    # case-duplicate of lowercase "uitlaten", same class as the age_adj fix
    # above.
    if token in {"uitlaten", "geven", "spelen"}: semantic.append("pet_care_verb")
    # Single-member tags, reusing already-classified tokens (elke/van) --
    # additive, does not disturb either token's existing semantic tags.
    # Exact-case (not casefolded): earlier units already introduce
    # capitalized sentence-initial "Elke" (unit14 area) and "Van" (unit14
    # area) as separate lexemes -- casefolding would silently widen each
    # tag to 2 members, same class as the age_adj/pet_care_verb fixes above.
    if token == "elke": semantic.append("animal_elke_single")
    if token == "van": semantic.append("animal_van_single")

    # Unit 32 (sports) practice-template tags, added 2026-07-09. 4-member
    # sport-noun tag (hardlopen/zwemmen classified as nouns -- see their
    # NL_GLOSSES comment), verified safe generatively in "Ik houd van
    # {item}."/"Ik doe aan {item}." (all four grammatical in both frames,
    # translation-only per this unit's own review.notes, which explicitly
    # avoided any bare Dutch fill_in_blank on this exact pool).
    # Exact-case (not casefolded): this unit's own lesson04 grammar note
    # separately introduces capitalized subject-position "Hardlopen"
    # ("Hardlopen is niet scheidbaar...") as a case-duplicate of lowercase
    # "hardlopen", same class as the age_adj/pet_care_verb fixes above.
    if token in {"voetbal", "yoga", "hardlopen", "zwemmen"}: semantic.append("sport_noun")
    if t == "dicht": semantic.append("sport_dicht_single")

    # Unit 33 (transportation) practice-template tags, added 2026-07-09.
    # 3-member transport-noun tag, verified safe in "Ik reis met de
    # {item}." (all three grammatical: "met de trein/fiets/auto").
    if t in {"trein", "fiets", "auto"}: semantic.append("transport_noun")
    # 3-member conjugated-verb recognition-only tag (different subjects,
    # no shared frame) -- same discipline as pet_care_verb above.
    if t in {"fietst", "rijdt", "reist"}: semantic.append("transport_verb")
    # Broader mixed noun/verb recognition-only pool for a bigger
    # matching_pairs finale, same combined-slot-preset technique as
    # a2_unit24's gemeente_noun_or_verb.
    if t in {"trein", "fiets", "auto", "fietst", "rijdt", "reist", "lopen", "reizen"}:
        semantic.append("transport_vocab")
    # Exact-case (not casefolded): "alstublieft" is also introduced in A2
    # unit24 (gemeente) as both lowercase and a capitalized sentence-initial
    # "Alstublieft" -- casefolding here would pull in both the a2-course
    # capitalized variant AND (harmlessly, since A1/A2 are separate courses
    # per AUTHORING_GUIDE #18) widen the a1-course pool with a same-course
    # case-duplicate if this unit's own dialogue ever capitalizes it.
    if token == "alstublieft": semantic.append("vervoer_alstublieft_single")

    # A2 unit 73 (sollicitatiegesprek/job interview), added 2026-07-10.
    # Recognition-only employment vocabulary spanning nouns/adjectives/verbs
    # from the job-ad and interview lessons. The narrower tags below carry
    # any shared-frame assumptions.
    if t in {"vacature", "solliciteren", "medewerker", "sollicitatiegesprek",
             "ervaring", "vrijwilliger", "vaardigheid", "vaardigheden",
             "beschikbaar", "werktijden", "klantcontact", "gesprek"}:
        semantic.append("job_interview_vocab")
    # Exact-case tag for matching_pairs: Ervaring/Werktijden appear as
    # sentence-initial/heading variants in the reading lesson and should not
    # be drawn alongside their lowercase case-duplicates.
    if token in {"vacature", "solliciteren", "medewerker", "sollicitatiegesprek",
                 "ervaring", "vrijwilliger", "vaardigheid", "vaardigheden",
                 "beschikbaar", "werktijden", "klantcontact", "gesprek"}:
        semantic.append("job_interview_vocab_pure")
    # Two singular role/position nouns safe after "een" in the application
    # context: "een administratief medewerker" and "een vrijwilliger".
    if t in {"medewerker", "vrijwilliger"}:
        semantic.append("job_role_noun")
    # Skills/experience nouns used in "Ik heb {item}" frames. "ervaring" is
    # mass-singular; "vaardigheden" is plural, but both are directly attested
    # in this unit's "Ik heb ..." sentences.
    if t in {"ervaring", "vaardigheden"}:
        semantic.append("job_have_noun")
    # Availability/time vocabulary is recognition-only; beschikbaar is an
    # adjective while werktijden is a plural noun.
    if t in {"beschikbaar", "werktijden"}:
        semantic.append("availability_vocab")
    if t == "beschikbaar":
        semantic.append("job_beschikbaar_single")
    if t == "klantcontact":
        semantic.append("job_klantcontact_single")

    # A2 unit 74 (reisvertraging/travel disruption), added 2026-07-11.
    # Recognition-only travel-disruption vocabulary; no practice-template
    # pack exists yet for this unit (only through a2_unit28.yaml), so no
    # finer generative-frame tags are added -- add those alongside a future
    # practice-template authoring pass instead, same discipline as this
    # file's own note for unit73 above.
    if t in {"seinstoring", "aansluiting", "servicebalie", "verbinding",
             "intercity", "mededeling", "reisplanner", "spoor"}:
        semantic.append("travel_disruption_vocab")
    if t in {"rijden", "omreizen", "adviseren", "raadplegen", "weten"}:
        semantic.append("travel_disruption_verb")

    # A2 unit 75 (schermtijd/screen time and online habits), added
    # 2026-07-11. Recognition-only, same discipline as unit74 above.
    if t in {"scherm", "telefoon", "media", "schermtijd", "gewoonte", "apps"}:
        semantic.append("screen_time_vocab")
    if t in {"chat", "doorbrengen", "wegleggen", "probeer"}:
        semantic.append("screen_time_verb")

    # A2 unit 76 (drukke week/describing a weekly schedule), added
    # 2026-07-11. Recognition-only, same discipline as unit74 above.
    if t in {"rooster", "cursus", "volgorde", "agenda", "verschil"}:
        semantic.append("weekly_schedule_vocab")
    # 3-member sequencing-connector tag, verified safe generatively in
    # "{item} werk ik, {item2} sport ik." style chaining -- kept
    # recognition-only here since no practice-template pack exists yet to
    # consume it as a generative frame (see the module-docstring note).
    if t in {"eerst", "daarna", "slotte"}: semantic.append("sequence_connector")

    # A2 unit 77 (iets terugbrengen/shopping complaint and returns), added
    # 2026-07-11. Recognition-only, same discipline as unit74 above.
    if t in {"koptelefoon", "linkerkant", "bonnetje", "retourbeleid",
             "artikel", "aankoop", "exemplaar"}:
        semantic.append("shopping_complaint_vocab")
    # Exact-case (not casefolded) sibling for matching_pairs, added
    # 2026-07-11 alongside the practice-template pass: the casefolded
    # "shopping_complaint_vocab" pool above genuinely contains both
    # lowercase "retourbeleid" (lesson04 vocab card) and capitalized
    # "Retourbeleid" (lesson05 reading's heading), both meaning "the
    # return policy" with an identical English gloss -- fine for
    # bare-word multiple_choice/listen_select (one word shown at a
    # time), but a real risk for matching_pairs, which could sample
    # both as two simultaneous cards that look like duplicate pairs.
    # Restricting to the exact-case lowercase token excludes the
    # capitalized duplicate, same class of fix as this file's existing
    # job_interview_vocab_pure/housing_report_noun_pure precedent.
    if token in {"koptelefoon", "linkerkant", "bonnetje", "retourbeleid",
                 "artikel", "aankoop", "exemplaar"}:
        semantic.append("shopping_complaint_vocab_pure")
    if t in {"ruilen", "terugkrijgen", "terugbrengen", "regel"}:
        semantic.append("shopping_complaint_verb")

    # Single-member render_frame-safe tags for units 74-77, added 2026-07-11
    # alongside the first docs/content/practice/en-nl/a2_unit7[4-7].yaml
    # practice-template pass (the four broader recognition-only tags just
    # above were deliberately left bare-word-only when this file was first
    # extended for these units, per this module's own docstring note -- this
    # is that deferred follow-up). Each tag below has EXACTLY one member, so
    # it can safely anchor a fixed multi-word frame (word_order/translation/
    # fill_in_blank via render_frame/slot_text) without the multi-candidate
    # ambiguity §17 warns about -- no grammaticality-across-candidates
    # judgment call is needed when there is only one candidate. Casefold
    # matching (`t == ...`) is used throughout, deliberately unifying a
    # token with its own sentence-initial capitalized variant where one
    # exists in this unit (verified by hand, not guessed): "daarna"/"Daarna"
    # (unit76 lesson02 mid-sentence vs. lesson06 grammar-note sentence-
    # initial, identical meaning) and "retourbeleid"/"Retourbeleid" (unit77
    # lesson04 vocab card vs. lesson05 reading's heading, identical
    # meaning) -- same safe-reuse pattern as this file's existing Ervaring/
    # Werktijden precedent, not a new risk class. Every other token below
    # was grepped against the full NL_GLOSSES dict to confirm no unrelated
    # capitalized homograph exists that casefolding could accidentally pull
    # in.
    if t == "vertraging": semantic.append("reisvertraging_vertraging_single")
    if t == "seinstoring": semantic.append("reisvertraging_seinstoring_single")
    if t == "aansluiting": semantic.append("reisvertraging_aansluiting_single")
    if t == "verbinding": semantic.append("reisvertraging_verbinding_single")
    if t == "spoor": semantic.append("reisvertraging_spoor_single")

    if t == "scherm": semantic.append("schermtijd_scherm_single")
    if t == "telefoon": semantic.append("schermtijd_telefoon_single")
    if t == "chat": semantic.append("schermtijd_chat_single")
    if t == "schermtijd": semantic.append("schermtijd_schermtijd_single")
    if t == "doorbrengen": semantic.append("schermtijd_doorbrengen_single")
    if t == "gewoonte": semantic.append("schermtijd_gewoonte_single")
    if t == "wegleggen": semantic.append("schermtijd_wegleggen_single")

    if t == "rooster": semantic.append("drukkeweek_rooster_single")
    if t == "daarna": semantic.append("drukkeweek_daarna_single")
    if t == "slotte": semantic.append("drukkeweek_slotte_single")
    if t == "verschil": semantic.append("drukkeweek_verschil_single")
    if t == "agenda": semantic.append("drukkeweek_agenda_single")
    if t == "volgorde": semantic.append("drukkeweek_volgorde_single")

    if t == "koptelefoon": semantic.append("terugbrengen_koptelefoon_single")
    if t == "bonnetje": semantic.append("terugbrengen_bonnetje_single")
    if t == "retourbeleid": semantic.append("terugbrengen_retourbeleid_single")
    if t == "ruilen": semantic.append("terugbrengen_ruilen_single")
    if t == "artikel": semantic.append("terugbrengen_artikel_single")
    if t == "terugkrijgen": semantic.append("terugbrengen_terugkrijgen_single")

    tags: dict[str, object] = {"semantic": list(dict.fromkeys(semantic))}
    if t in {"jij", "je"}: tags["register"] = "informal"
    elif t == "u": tags["register"] = "polite"
    return tags


def _classify_nl(unit_files, level):
    # A FRESH specs dict per level/course -- Lexeme uniqueness is scoped by
    # `Lexeme.course_id`, and "Dutch A1"/"Dutch A2" are two entirely separate
    # course rows (see UNIT_FILES_A2's comment), so a token re-taught in A2
    # needs its own A2-scoped Lexeme row rather than silently reusing A1's.
    specs: dict[str, dict] = {}
    for unit_order, realization_path in enumerate(unit_files, 1):
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson["teaching"]:
                for token in item.get("introduced_tokens", []):
                    token = str(token)
                    if token not in NL_GLOSSES:
                        raise ValueError(f"missing explicit Dutch gloss for {token!r}")
                    tags = nl_agreement_tags(token, lesson_key)
                    existing = specs.get(token)
                    if existing is None:
                        specs[token] = {
                            "level": level,
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": item["content_key"],
                            "token": token, "language_code": "nl", "part_of_speech": nl_part_of_speech(token),
                            "english_gloss": NL_GLOSSES[token], "agreement_tags": tags,
                        }
                    else:
                        prior = existing["agreement_tags"].setdefault("semantic", [])
                        prior.extend(value for value in tags["semantic"] if value not in prior)
    yield from specs.values()


def iter_specs():
    yield from _classify_nl(UNIT_FILES, "a1")
    yield from _classify_nl(UNIT_FILES_A2, "a2")
    yield from _classify_nl(UNIT_FILES_B1, "b1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    specs = list(iter_specs())
    if args.dry_run:
        a1_count = sum(spec["level"] == "a1" for spec in specs)
        a2_count = sum(spec["level"] == "a2" for spec in specs)
        b1_count = sum(spec["level"] == "b1" for spec in specs)
        print(f"Lexeme backfill dry run: {len(specs)} nl ({a1_count} a1, {a2_count} a2, {b1_count} b1).")
        return 0

    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        courses_by_level = {}
        for level, title in (("a1", "Dutch A1"), ("a2", "Dutch A2"), ("b1", "Dutch B1")):
            needed = any(spec["level"] == level for spec in specs)
            course = db.scalar(
                select(Course).where(
                    Course.source_language == "en",
                    Course.target_language == "nl",
                    Course.title == title,
                )
            )
            if course is None:
                if needed:
                    print(f"ERROR: en-nl {title!r} course must be imported first", file=sys.stderr)
                    return 1
                continue
            courses_by_level[level] = course

        lessons_by_level = {
            level: {
                (unit.order, lesson.order): lesson
                for unit in db.scalars(select(Unit).where(Unit.course_id == course.id))
                for lesson in db.scalars(select(Lesson).where(Lesson.unit_id == unit.id))
            }
            for level, course in courses_by_level.items()
        }
        created = updated = 0
        for raw_spec in specs:
            spec = dict(raw_spec)
            level = spec.pop("level")
            course = courses_by_level[level]
            lesson = lessons_by_level[level].get(
                (spec.pop("unit_order"), spec.pop("lesson_order"))
            )
            if lesson is None:
                print(f"ERROR: imported course is missing {spec['lesson_content_key']}", file=sys.stderr)
                db.rollback(); return 1
            existing = db.scalar(select(Lexeme).where(Lexeme.course_id == course.id, Lexeme.language_code == "nl", Lexeme.token == spec["token"], Lexeme.part_of_speech == spec["part_of_speech"]))
            if existing:
                existing.english_gloss = spec["english_gloss"]
                existing.agreement_tags = spec["agreement_tags"]
                updated += 1
                continue
            db.add(Lexeme(course_id=course.id, provenance_lesson_id=lesson.id, provenance_lesson_content_key=spec.pop("lesson_content_key"), provenance_content_key=spec.pop("content_key"), **spec))
            created += 1
        db.commit()
    print(f"Lexeme backfill complete: {created} created, {updated} updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
