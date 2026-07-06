#!/usr/bin/env python3
"""Idempotently backfill target-side en-nl Dutch A1 lexemes for units 1-13.

Run with ``--dry-run`` to parse and classify content without importing the
application or connecting to PostgreSQL.  The realization files' complete
``introduced_tokens`` inventories are authoritative.

Extended repeatedly through 2026-07-06 (most recently units 11-13: plans,
recent events/perfect tense, preferences) to keep pace with new practice-
template packs -- see docs/content/practice/en-nl/a1_unit01.yaml through
a1_unit13.yaml. Units 14+ are the exact next step for whoever continues the
practice-pool sync (see docs/BUILD_LOG.md). (Docstring corrected 2026-07-06
after a fresh-context review pass flagged it as stale -- it previously said
"units 1-7" long after the code had been extended well past that.)

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

UNIT_FILES = tuple(sorted(
    p for p in (REPO_ROOT / "docs/content/realizations/nl").glob("a1_unit*_*.yaml")
    if 1 <= int(p.name[len("a1_unit"):len("a1_unit")+2]) <= 16
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

# Case variants are tokens in their own right because provenance preserves the
# realization spelling. Their gloss is the explicit lexical gloss above.
for _token in (
    "Achtenveertig Ben Bent Dagen Dan Dat De En Er Goed Het Hoe Hoeveel Ik Inleverdatum Is Ja Jou Kom Kun Leuk "
    "Maanden Mijn Nee Niet Nul Om Op Tot Twaalf Vandaag Waar Wanneer Wat Welke Wij"
).split():
    if _token not in NL_GLOSSES:
        NL_GLOSSES[_token] = NL_GLOSSES[_token.casefold()]

for _number in "0 00 06 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 18 19 20 21 22 24 25 29 30 31 32 40 42 43 45 48 50 65 75 87 90 99 2024 2026".split():
    NL_GLOSSES[_number] = _number

SYMBOLS = set("'s 0 00 06 07 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 24 25 29 30 31 32 40 42 43 45 48 50 65 75 87 90 99 500 2024 2026".split())
PROPER_NOUNS = {"België", "Duitsland", "Egypte", "Lotte", "Nederland", "Noor", "Omar",
                "Rotterdam", "Sander", "Fenna", "Jan", "Marieke", "Utrecht", "Amsterdam",
                "Bergsport", "Schoudertas", "Stad", "Centraal"}
PRONOUNS = set("ik Ik je jij jou Jou me u Wij wij Mijn mijn Welke welke Wat wat Hoeveel hoeveel jouw haar hem iets zich we We Hij hij Deze deze die zij welk Waarmee".split())
PREPOSITIONS = set("aan bij in met na naar om Om op Op over te tot Tot uit voor vóór per naast tegenover achter tussen van vanaf In Na Bij boven Van tegen".split())
PARTICLES = set("behalve dan Dan dat Dat de De dit Dit dus een Een en En er Er geen Geen het Het Ja ja Nee nee Niet niet of ook wel maar nog Anders af eerst Eerst pas want als plus toe st O".split())
ADJECTIVES = set("Belgisch beleefd Duits Engels formeel Goed goed hele informeel laat Leuk leuk Nederlands nieuw normaal open oud slecht volgende elke Mooi gewone scheidbaar korte kort vriendelijk voltooide voltooid meeste sterke algemene blauwe andere ene lekker groot klein groter kleiner duur goedkoop duurder goedkoper bijvoeglijk gelijk mooi praktisch duurst beter best onregelmatig beste meer Veel meest dezelfde lange sterk lichter sterker grote nodig mooist licht beleefde ziek verkouden Ziek bijvoeglijke zelfstandige moe".split())
ADVERBS = set("avonds vandaan halverwege hier hoe Hoe hoeveelste middags nachts ochtends terug vandaag Vandaag waar Waar wanneer Wanneer graag vaak natuurlijk links rechts linksaf rechtsaf rechtdoor Rechtdoor Graag achteraan daarna Daarna eruit samen meestal gisteren vanmorgen Gisteren Vanmorgen Daar daar liever Liever zo net minder Precies precies al veel steeds Nog nu".split())
VERBS = set("begint ben Ben bent Bent heb Heb heet inschrijven is Is kom Kom komt Komt kost krijgen leer moet ontmoeten spreek wil wilt woon wonen Wonen woont zijn zitten Kun kun herhalen gaat drinken eten Mag mag Zie hebben neem kan Kan pinnen Kijk ga sla loop Ga Sla Loop gedaan opstaan sta aankleden kleed ontbijten ontbijt werken werk eet afwassen was slapen slaap staat ziet gaan Zullen zullen stellen maakt afspreken geeft staan spreken gebruik gedronken gegaan Denk gebruiken gegeten gewerkt kopen gekocht komen gekomen vinden vind Vind fietsen wandelen winkelen doen Houden drukt houd Zeg Wil zien kiest houdt voeg Gebruik vergelijken werkt heeft koop Koop koopt Wilt vertrekt moeten Let stappen voel scheelt Gaat helpen Heeft Neem Rust drink Voel genomen rusten".split())
PHRASES = {"Aangenaam", "Goedemiddag", "Goedemorgen", "Goedenavond", "Hallo", "Hoi", "Prima", "ziens",
           "alstublieft", "alsjeblieft", "eraan", "Bedankt", "Sorry", "Groet", "Beterschap"}
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
              "hoofdpijn buikpijn keelpijn koorts Koorts naamwoorden apotheek tablet Advies dagen huisarts Dank morgen".split())


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
        "eten_en_drinken": "taste_preference", "activiteiten": "activity_preference",
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
    number_words = set("nul één twee drie vier vijf zes zeven acht negen tien elf twaalf dertien veertien vijftien zestien zeventien achttien negentien twintig dertig veertig vijftig zestig zeventig tachtig negentig eenentwintig tweeëntwintig tweeëndertig tweeënveertig achtenveertig vijfenzeventig negenennegentig drieënveertig vijfenzestig zevenentachtig achtentwintig".split())
    if t in number_words or token in SYMBOLS and token != "'s": semantic.append("number")
    if t in {"twee", "drie", "zeven", "acht", "veertien", "achttien", "twintig"} or token in {"2", "3", "7", "8", "14", "18", "20"}: semantic.append("hour_number")
    if t in set("maandag dinsdag woensdag donderdag vrijdag zaterdag zondag".split()): semantic.append("weekday")
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
    # Only 2 members -- kept out of multiple_choice/listen_select (which
    # need >=4), used only in word_order/fill_in_blank/translation.
    if t in {"ziek", "verkouden"}: semantic.append("symptom_zijn")
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
    tags: dict[str, object] = {"semantic": list(dict.fromkeys(semantic))}
    if t in {"jij", "je"}: tags["register"] = "informal"
    elif t == "u": tags["register"] = "polite"
    return tags


def iter_specs():
    specs: dict[str, dict] = {}
    for unit_order, realization_path in enumerate(UNIT_FILES, 1):
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
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": item["content_key"],
                            "token": token, "language_code": "nl", "part_of_speech": nl_part_of_speech(token),
                            "english_gloss": NL_GLOSSES[token], "agreement_tags": tags,
                        }
                    else:
                        prior = existing["agreement_tags"].setdefault("semantic", [])
                        prior.extend(value for value in tags["semantic"] if value not in prior)
    yield from specs.values()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    specs = list(iter_specs())
    if args.dry_run:
        print(f"Lexeme backfill dry run: {len(specs)} nl.")
        return 0

    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        course = db.scalar(select(Course).where(Course.source_language == "en", Course.target_language == "nl", Course.title == "Dutch A1"))
        if course is None:
            print("ERROR: en-nl Dutch A1 course must be imported first", file=sys.stderr)
            return 1
        lessons = {(unit.order, lesson.order): lesson for unit in db.scalars(select(Unit).where(Unit.course_id == course.id)) for lesson in db.scalars(select(Lesson).where(Lesson.unit_id == unit.id))}
        created = updated = 0
        for raw_spec in specs:
            spec = dict(raw_spec)
            lesson = lessons.get((spec.pop("unit_order"), spec.pop("lesson_order")))
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
