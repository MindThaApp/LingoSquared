#!/usr/bin/env python3
"""Idempotently backfill reviewed nl-en A1 lexemes (English target,
Dutch source) from the shared en realization units 1 and 2.

Written directly (not via Codex -- Codex was rate-limited at authoring
time) mirroring scripts/backfill_lexemes.py's structure and rigor.
Target-side English classification lives in
scripts/_en_target_lexeme_common.py (shared with backfill_lexemes_fa_en.py
and backfill_lexemes_prs_en.py, since all three teach the identical
English realization to different source-language speakers -- only the
Dutch/Farsi/Dari source-side classification differs per script).

Needs both the app's DB settings/imports (in backend/) and this repo's
docs/content/ (at the repo root). Run via docker compose from backend/,
mounting the full repo on top of the existing image/network/env:

    cd backend
    docker compose run --rm \
      -v "$(cd .. && pwd):/repo" \
      -e PYTHONPATH=/repo/backend \
      --entrypoint python \
      api /repo/scripts/backfill_lexemes_nl_en.py

Add --dry-run to classify without touching the database.

Dutch source-side words are extracted from the nl-en overlay's `gloss:`
fields (the Dutch translation shown for each taught English item),
mirroring exactly how the reference script extracts English words from
the en-fa overlay's English gloss text.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from _en_target_lexeme_common import EN_POS, en_agreement_tags  # noqa: E402

# Dutch gloss for each shared English target token -- this is
# course-specific (source_language=nl), NOT shared with the fa-en/prs-en
# backfill scripts, unlike EN_POS/en_agreement_tags above. Found via live
# verification that a naive shared "english_gloss" would have made
# slot_gloss-derived multiple_choice exercises match an English word
# against itself instead of its actual Dutch meaning -- see the
# IMPORTANT note in _en_target_lexeme_common.py.
EN_TARGET_TO_NL_GLOSS: dict[str, str] = {
    "hello": "hallo", "hi": "hoi", "good": "goed", "morning": "ochtend",
    "afternoon": "middag", "evening": "avond", "goodbye": "tot ziens",
    "bye": "doei", "how": "hoe", "are": "bent (2e persoon)",
    "you": "jij / u", "i'm": "ik ben", "fine": "goed", "thanks": "bedankt",
    "not": "niet", "bad": "slecht", "and": "en", "okay": "oké",
    "nice": "leuk", "to": "te", "meet": "ontmoeten", "too": "ook",
    "see": "zien", "later": "later", "have": "hebben", "a": "een",
    "day": "dag", "what": "wat", "is": "is", "what's": "wat is",
    "your": "jouw / uw", "name": "naam", "my": "mijn", "leila": "Leila",
    "i": "ik", "am": "ben", "student": "student", "teacher": "leraar",
    "yes": "ja", "no": "nee", "new": "nieuw", "member": "lid",
    "he": "hij", "she": "zij", "an": "een", "engineer": "ingenieur",
    "library": "bibliotheek", "assistant": "medewerker", "daniel": "Daniel",
    "work": "werken", "at": "bij", "the": "de", "welcome": "welkom",
    "thank": "danken",
    # Unit 3 (numbers/ages/prices/phones/market), added 2026-07-05.
    "zero": "nul", "one": "een", "two": "twee", "three": "drie", "four": "vier",
    "five": "vijf", "six": "zes", "seven": "zeven", "eight": "acht", "nine": "negen",
    "ten": "tien", "eleven": "elf", "twelve": "twaalf", "thirteen": "dertien",
    "fifteen": "vijftien", "twenty": "twintig", "twenty-one": "eenentwintig",
    "thirty": "dertig", "forty": "veertig", "fifty": "vijftig", "hundred": "honderd",
    "twenty-five": "vijfentwintig", "old": "oud", "years": "jaar",
    "it's": "het is", "dollars": "dollar", "phone": "telefoon", "number": "nummer",
    "market": "markt", "apples": "appels", "they're": "ze zijn", "ok": "oké",
    "this": "dit", "shop": "winkel", "much": "veel",
    # Unit 4 (days/months/calendar dates), added 2026-07-05.
    "monday": "maandag", "tuesday": "dinsdag", "wednesday": "woensdag",
    "thursday": "donderdag", "friday": "vrijdag", "saturday": "zaterdag",
    "sunday": "zondag", "it": "het", "today": "vandaag", "january": "januari",
    "march": "maart", "july": "juli", "september": "september",
    "december": "december", "which": "welke", "month": "maand",
    "today's": "vandaag", "date": "datum", "7th": "7", "can": "kan",
    "also": "ook", "write": "schrijven", "as": "als", "when's": "wanneer is",
    "birthday": "verjaardag", "3rd": "3", "opens": "gaat open", "again": "weer",
    "open": "open", "on": "op", "great": "geweldig", "then": "dan", "9th": "9",
    # Unit 5 (telling the time), added 2026-07-05.
    "time": "tijd", "o'clock": "uur", "half": "half", "past": "over",
    "quarter": "kwart", "night": "nacht", "store": "winkel", "closes": "gaat dicht",
    "does": "doet", "close": "dicht", "in": "in",
    # Unit 6 (family members and relationships), added 2026-07-05.
    "mother": "moeder", "father": "vader", "brother": "broer", "sister": "zus",
    "parents": "ouders", "siblings": "broers en zussen", "grandmother": "oma",
    "grandfather": "opa", "aunt": "tante", "uncle": "oom", "cousin": "neef/nicht",
    "his": "zijn", "her": "haar", "she's": "zij is", "brothers": "broers",
    "do": "doe", "any": "een aantal", "don't": "doe niet", "only": "enig",
    "child": "kind", "photo": "foto", "family": "familie", "who": "wie",
    "just": "maar",
    # Unit 7 (food, drink, and ordering), added 2026-07-05.
    "coffee": "koffie", "tea": "thee", "water": "water", "bread": "brood",
    "soup": "soep", "salad": "salade", "sandwich": "boterham/broodje",
    "i'd": "ik zou", "like": "willen (graag)", "please": "alstublieft",
    "anything": "iets", "else": "anders", "that's": "dat is", "all": "alles",
    "for": "voor", "here": "hier", "or": "of", "go": "gaan", "menu": "menu",
    "price": "prijs", "cafe": "cafe", "2": "2", "3": "3", "5": "5", "6": "6",
    "sure": "zeker",
    # Unit 8 (shopping: prices and quantities), added 2026-07-05.
    "pound": "pond", "of": "van", "dozen": "dozijn", "eggs": "eieren",
    "bottle": "fles", "bag": "zak", "kilo": "kilo", "tomatoes": "tomaten",
    "rice": "rijst", "pounds": "pond", "fresh": "vers", "per": "per", "4": "4",
    # Unit 9 (common places and locations), added 2026-07-05.
    "bank": "bank", "hospital": "ziekenhuis", "pharmacy": "apotheek",
    "park": "park", "restaurant": "restaurant", "next": "naast (next to)",
    "across": "tegenover (across from)", "from": "van", "between": "tussen",
    "behind": "achter", "front": "voor (in front of)", "where": "waar",
    "excuse": "excuseer", "me": "mij", "far": "ver",
    # Unit 10 (asking for and following directions), added 2026-07-05.
    "turn": "sla af", "left": "links", "right": "rechts", "straight": "rechtdoor",
    "stop": "stop", "corner": "hoek", "get": "komen", "minutes": "minuten",
    "can't": "kunt niet", "miss": "missen", "take": "neem", "first": "eerste",
    "street": "straat", "second": "tweede", "directions": "route",
    # Unit 11 (talking about the weather), added 2026-07-05.
    "sunny": "zonnig", "rainy": "regenachtig", "cloudy": "bewolkt",
    "cold": "koud", "hot": "heet", "windy": "winderig", "weather": "weer",
    "warm": "warm", "raining": "regent", "should": "kunt beter",
    "umbrella": "paraplu", "tomorrow": "morgen", "will": "zal", "be": "zijn",
    "rain": "regenen", "let's": "laten we", "idea": "idee", "but": "maar",
    "going": "gaat", "so": "dus",
    # Unit 12 (clothing: sizes and colors), added 2026-07-05.
    "shirt": "shirt/overhemd", "pants": "broek", "shoes": "schoenen",
    "jacket": "jas/jasje", "dress": "jurk", "small": "kleine maat",
    "medium": "middelmaat", "large": "grote maat", "blue": "blauw",
    "black": "zwart", "size": "maat", "color": "kleur", "20": "20",
    "i'll": "ik zal", "we": "wij",
    # Unit 13 (talking about feelings), added 2026-07-05.
    "happy": "blij", "sad": "verdrietig", "tired": "moe", "excited": "enthousiast/opgewonden",
    "worried": "bezorgd", "feeling": "gevoel", "little": "beetje",
    "because": "omdat", "big": "groot", "test": "examen/toets", "class": "les",
    "almost": "bijna", "over": "voorbij", "last": "laatste", "year": "jaar",
    "writer": "schrijver", "oh": "oh", "understand": "begrijpen",
    # Unit 14 (phone calls and messages), added 2026-07-05.
    "free": "vrij", "tonight": "vanavond", "sorry": "sorry", "repeat": "herhalen",
    "speak": "praten", "more": "meer", "slowly": "langzamer", "hear": "horen",
    "well": "goed", "6pm": "18.00 uur", "message": "bericht", "suggest": "voorstellen",
    "meeting": "afspraak", "place": "plaats", "about": "wat dacht je van",
    "that": "dat",
    # Unit 15 (handling money and payments), added 2026-07-05.
    "cash": "contant geld", "card": "kaart", "credit": "krediet", "debit": "debet",
    "total": "totaalbedrag", "cards": "kaarten", "pay": "betalen", "tax": "belasting",
    "10": "10", "by": "met", "1": "1",
    # Unit 16 (describing a daily routine), added 2026-07-05.
    "wake": "wakker worden", "up": "op", "dressed": "aangekleed", "dinner": "avondeten",
    "bed": "bed", "every": "elke", "usually": "meestal", "breakfast": "ontbijt",
    "after": "na",
    # Unit 17 (making simple plans), added 2026-07-05.
    "want": "willen", "movie": "film", "weekend": "weekend", "would": "zou",
    "walk": "wandeling", "love": "graag willen", "busy": "druk", "maybe": "misschien",
    "another": "een andere", "lunch": "lunch", "1pm": "1 uur 's middags", "works": "komt uit",
    # Unit 18 (describing a recent event), added 2026-07-05.
    "went": "ging", "saw": "zag", "ate": "at", "visited": "bezocht",
    "worked": "werkte", "did": "deed", "yesterday": "gisteren", "together": "samen",
    "watched": "keek", "writer's": "van de schrijver", "s": "s (bezitsvorm)",
    "was": "was", "week": "week",
    # Unit 19 (expressing likes and preferences), added 2026-07-05.
    "like": "leuk vinden", "don't": "niet leuk vinden", "prefer": "de voorkeur geven aan",
    "hate": "haten", "calmer": "rustiger", "very": "heel", "strong": "sterk",
    "why": "waarom", "think": "denken", "prefers": "geeft de voorkeur aan",
    "thinks": "denkt",
    # Unit 20 (making basic comparisons), added 2026-07-06.
    "bigger": "groter", "smaller": "kleiner", "cheaper": "goedkoper",
    "expensive": "duur", "faster": "sneller", "than": "dan", "nicer": "mooier",
    "cheapest": "goedkoopst", "red": "rood", "car": "auto", "white": "wit",
    # Unit 21 (handling a basic journey/travel), added 2026-07-06.
    "ticket": "kaartje", "platform": "perron", "train": "trein",
    "departure": "vertrek", "arrival": "aankomst", "boston": "Boston",
    "way": "manier; kant", "round": "retour (rond)", "trip": "reis",
    "leaves": "vertrekt", "9:15": "9:15", "arrives": "komt aan",
    "11:30": "11:30", "arrive": "aankomen",
}

UNIT_FILES = (
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit01_greetings.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit01.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit02_introductions.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit02.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit03_numbers.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit03.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit04_dates.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit04.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit05_time.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit05.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit06_family.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit06.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit07_food.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit07.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit08_shopping.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit08.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit09_places.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit09.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit10_directions.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit10.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit11_weather.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit11.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit12_clothing.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit12.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit13_emotions.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit13.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit14_communication.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit14.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit15_money.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit15.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit16_routines.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit16.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit17_plans.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit17.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit18_past_events.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit18.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit19_preferences.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit19.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit20_comparisons.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit20.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit21_travel.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit21.yaml",
    ),
)

# Dutch word tokenizer -- Latin script plus Dutch diacritics (ë, ï, etc.)
NL_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ]+(?:['’-][A-Za-zÀ-ÿ]+)*")

# Hand-classified from every unique word appearing in the nl-en overlay's
# `gloss:` fields across both units (confirmed by reading both files).
NL_POS: dict[str, str] = {
    "hallo": "noun", "hoi": "noun", "goedemorgen": "noun", "goedemiddag": "noun",
    "goedenavond": "noun", "tot": "preposition", "ziens": "noun", "doei": "noun",
    "hoe": "adverb", "gaat": "verb", "het": "pronoun", "met": "preposition",
    "je": "pronoun", "u": "pronoun", "en": "particle", "jij": "pronoun",
    "bedankt": "noun", "niet": "particle", "slecht": "adjective", "ben": "verb",
    "oké": "adjective", "leuk": "adjective", "te": "preposition",
    "ontmoeten": "verb", "jou": "pronoun", "ook": "adverb", "later": "adverb",
    "fijne": "adjective", "dag": "noun", "heet": "verb", "mijn": "pronoun",
    "naam": "noun", "is": "verb", "leila": "proper_noun", "ik": "pronoun",
    "student": "noun", "leraar": "noun", "ja": "particle", "dat": "pronoun",
    "nee": "particle", "een": "particle", "nieuw": "adjective", "lid": "noun",
    "hij": "pronoun", "zij": "pronoun", "ingenieur": "noun", "bibliotheek": "noun",
    "bibliotheekmedewerker": "noun", "daniel": "proper_noun", "werk": "verb",
    "bij": "preposition", "welkom": "adjective", "in": "preposition", "dank": "noun",
    "de": "particle", "goed": "adjective",
    # Unit 3 (numbers/ages/prices/phones/market), added 2026-07-05.
    "acht": "noun", "appels": "noun", "bent": "verb", "bestaat": "verb",
    "dertien": "noun", "dertig": "noun", "dit": "pronoun", "dollar": "noun",
    "drie": "noun", "een-twee-drie-vier": "phrase", "eenentwintig": "noun",
    "elf": "noun", "hoeveel": "adverb", "honderd": "noun", "jaar": "noun",
    "kost": "verb", "markt": "noun", "naar": "preposition", "negen": "noun",
    "nul": "noun", "oud": "adjective", "prijs": "noun", "telefoonnummer": "noun",
    "tien": "noun", "twaalf": "noun", "twee": "noun", "twintig": "noun",
    "uw": "pronoun", "van": "preposition", "veertig": "noun", "vier": "noun",
    "vijf": "noun", "vijf-vijf-vijf": "phrase", "vijfentwintig": "noun",
    "vijftien": "noun", "vijftig": "noun", "vraagt": "verb", "wat": "pronoun",
    "winkel": "noun", "zegt": "verb", "zes": "noun", "zeven": "noun",
    # Unit 4 (days/months/calendar dates), added 2026-07-05.
    "als": "particle", "dan": "adverb", "datum": "noun", "december": "noun",
    "dinsdag": "noun", "donderdag": "noun", "geweldig": "adjective",
    "januari": "noun", "juli": "noun", "kunt": "verb", "maand": "noun",
    "maandag": "noun", "maart": "noun", "open": "adjective", "opengaat": "verb",
    "opent": "verb", "opnieuw": "adverb", "schrijven": "verb", "september": "noun",
    "vandaag": "noun", "verjaardag": "noun", "vrijdag": "noun", "wanneer": "adverb",
    "weer": "adverb", "welke": "pronoun", "woensdag": "noun", "zaterdag": "noun",
    "zondag": "noun",
    # Unit 5 (telling the time), added 2026-07-05.
    "avond": "noun", "avonds": "adverb", "dicht": "adjective", "half": "noun",
    "kwart": "noun", "laat": "adverb", "middag": "noun", "nacht": "noun",
    "ochtend": "noun", "ochtends": "adverb", "om": "preposition", "over": "preposition",
    "s": "particle", "uur": "noun", "voor": "preposition",
    # Unit 6 (family members and relationships), added 2026-07-05.
    "broer": "noun", "broers": "noun", "die": "pronoun", "enig": "adjective",
    "er": "particle", "familie": "noun", "foto": "noun", "grootmoeder": "noun",
    "grootvader": "noun", "haar": "pronoun", "heb": "verb", "kind": "noun",
    "lerares": "noun", "maar": "particle", "moeder": "noun", "neef": "noun",
    "nicht": "noun", "of": "particle",
    "oma": "noun", "oom": "noun", "opa": "noun", "ouders": "noun",
    "tante": "noun", "vader": "noun", "wie": "pronoun", "ze": "pronoun",
    "zijn": "pronoun", "zus": "noun", "zussen": "noun", "één": "noun",
    # Unit 7 (food, drink, and ordering), added 2026-07-05.
    "alles": "pronoun", "alstublieft": "phrase", "anders": "adverb",
    "bestelt": "verb", "boterham": "noun", "brood": "noun", "broodje": "noun",
    "cafe": "noun", "café": "noun", "cafémenu": "noun", "graag": "adverb", "groet": "verb", "hier": "adverb",
    "iets": "pronoun", "koffie": "noun", "mag": "verb", "meeneemt": "verb",
    "meenemen": "verb", "menu": "noun", "nog": "adverb", "oke": "adjective",
    "opeet": "verb", "opeten": "verb", "salade": "noun", "sandwich": "noun",
    "soep": "noun", "thee": "noun", "water": "noun", "wil": "verb",
    # Unit 8 (shopping: prices and quantities), added 2026-07-05.
    "dozijn": "noun", "eieren": "noun", "fles": "noun", "kilo": "noun",
    "kosten": "verb", "natuurlijk": "adverb", "per": "preposition", "pond": "noun",
    "rijst": "noun", "tomaten": "noun", "vers": "adjective", "zak": "noun",
    # Unit 9 (common places and locations), added 2026-07-05.
    "achter": "preposition", "apotheek": "noun", "bank": "noun",
    "naast": "preposition", "pardon": "noun", "park": "noun",
    "restaurant": "noun", "tegenover": "preposition", "tussen": "preposition",
    "ver": "adjective", "vreemde": "noun", "waar": "pronoun", "weg": "noun",
    "ziekenhuis": "noun",
    # Unit 10 (asking for and following directions), added 2026-07-05.
    "aan": "preposition", "eerste": "adjective", "ga": "verb", "herhaalt": "verb",
    "hoek": "noun", "kom": "verb", "komt": "verb", "links": "noun",
    "linksaf": "adverb", "minuten": "noun", "missen": "verb", "neem": "verb",
    "rechtdoor": "adverb", "rechterkant": "noun", "rechts": "noun",
    "rechtsaf": "adverb", "route": "noun", "sla": "verb", "stop": "verb",
    "straat": "noun", "tweede": "adjective",
    # Unit 11 (talking about the weather), added 2026-07-05.
    "beter": "adverb", "bewolkt": "adjective", "dus": "adverb", "gaan": "verb",
    "idee": "noun", "koud": "adjective", "laten": "verb", "morgen": "noun",
    "op": "preposition", "paraplu": "noun", "regenachtig": "adjective",
    "regenen": "verb", "regent": "verb", "warm": "adjective", "we": "pronoun",
    "winderig": "adjective", "wordt": "verb", "zonnig": "adjective",
    # Unit 12 (clothing: sizes and colors), added 2026-07-05.
    "beschikbaar": "adjective", "blauw": "adjective", "broek": "noun",
    "grote": "adjective", "hebben": "verb", "heeft": "verb", "jas": "noun",
    "jasje": "noun", "jurk": "noun", "kleine": "adjective", "kleur": "noun",
    "maat": "noun", "medium": "adjective", "middelmaat": "noun",
    "overhemd": "noun", "schoenen": "noun", "shirt": "noun", "zwart": "adjective",
    "m": "symbol",
    # Unit 13 (talking about feelings), added 2026-07-05.
    "beetje": "noun", "begrijp": "verb", "bezorgd": "adjective", "bijna": "adverb",
    "blij": "adjective", "enthousiast": "adjective", "examen": "noun",
    "groot": "adjective", "laatste": "adjective", "les": "noun", "moe": "adjective",
    "oh": "particle", "omdat": "particle", "opgewonden": "adjective",
    "schrijver": "noun", "verdrietig": "adjective", "voel": "verb", "voelt": "verb",
    "voorbij": "adjective", "zich": "pronoun",
    # Unit 14 (phone calls and messages), added 2026-07-05.
    "af": "particle", "afspreken": "verb", "alsjeblieft": "phrase",
    "bericht": "noun", "dacht": "verb", "herhalen": "verb", "horen": "verb",
    "kan": "verb", "kun": "verb", "langzamer": "adverb", "plaats": "noun",
    "praten": "verb", "sorry": "adjective", "spreken": "verb", "stelt": "verb",
    "tijd": "noun", "vanavond": "adverb",
    # Unit 15 (handling money and payments), added 2026-07-05.
    "accepteert": "verb", "accepteren": "verb", "alleen": "adverb",
    "belasting": "noun", "betaal": "verb", "betaalpas": "noun", "contant": "noun",
    "creditcard": "noun", "creditcards": "noun", "doen": "verb", "geld": "noun",
    "kaart": "noun", "pinpas": "noun", "totaal": "noun", "totaalbedrag": "noun",
    # Unit 16 (describing a daily routine), added 2026-07-05.
    "aankleden": "verb", "avondeten": "noun", "bed": "noun", "daarna": "adverb",
    "doe": "verb", "doet": "verb", "elke": "adjective", "kleed": "verb",
    "me": "pronoun", "meestal": "adverb", "ontbijt": "noun", "wakker": "adjective",
    "word": "verb", "worden": "verb",
    # Unit 17 (making simple plans), added 2026-07-05.
    "andere": "adjective", "druk": "adjective", "film": "noun", "heel": "adverb",
    "keer": "noun", "kijken": "verb", "lunchen": "verb", "mij": "pronoun",
    "misschien": "adverb", "uit": "preposition", "wandelen": "verb",
    "weekend": "noun", "zin": "noun",
    # Unit 18 (describing a recent event), added 2026-07-05. Note: several of
    # these are English infinitives embedded parenthetically inside this
    # unit's Dutch gloss text itself (e.g. gloss "ging (verleden tijd van
    # go)") -- classified as verbs to match their real grammatical role.
    "at": "verb", "bezocht": "verb", "eat": "verb", "gedaan": "verb",
    "gegeten": "verb", "gekeken": "verb", "gewerkt": "verb", "gezien": "verb",
    "ging": "verb", "gisteren": "adverb", "go": "verb", "hebt": "verb",
    "samen": "adverb", "see": "verb", "verleden": "noun", "visit": "verb",
    "vorig": "adjective", "vorige": "adjective", "was": "verb", "week": "noun",
    "werkte": "verb", "work": "verb", "zag": "verb",
    # Unit 19 (expressing likes and preferences), added 2026-07-05.
    "denk": "verb", "denkt": "verb", "dol": "adjective", "erg": "adverb",
    "geef": "verb", "geeft": "verb", "geven": "verb", "haten": "verb",
    "hou": "verb", "rustiger": "adjective", "sterk": "adjective",
    "vinden": "verb", "voorkeur": "noun", "waarom": "adverb", "zo": "adverb",
    # Unit 20 (making basic comparisons), added 2026-07-06.
    "auto": "noun", "blauwe": "adjective", "duurder": "adjective",
    "goedkoopst": "adjective", "goedkoopste": "adjective", "goedkoper": "adjective",
    "groter": "adjective", "kleiner": "adjective", "mooier": "adjective",
    "rode": "adjective", "sneller": "adjective", "tas": "noun", "vind": "verb",
    "witte": "adjective",
    # Unit 21 (handling a basic journey/travel), added 2026-07-06.
    "aankomst": "noun", "boston": "proper_noun", "enkele": "adjective",
    "kaartje": "noun", "loketmedewerker": "noun", "perron": "noun",
    "reis": "noun", "retour": "noun", "trein": "noun", "vanaf": "preposition",
    "vertrek": "noun", "vertrekt": "verb",
}

NL_GLOSSES: dict[str, str] = {
    "hallo": "hello", "hoi": "hi (informal)", "goedemorgen": "good morning",
    "goedemiddag": "good afternoon", "goedenavond": "good evening",
    "tot": "until; to", "ziens": "seeing (fixed expression 'tot ziens')",
    "doei": "bye (informal)", "hoe": "how", "gaat": "goes (3rd person 'gaan')",
    "het": "it", "met": "with", "je": "you (informal)", "u": "you (formal)",
    "en": "and", "jij": "you (informal, emphatic)", "bedankt": "thanks",
    "niet": "not", "slecht": "bad", "ben": "am (1st person 'zijn')",
    "oké": "okay", "leuk": "nice; fun", "te": "to",
    "ontmoeten": "to meet", "jou": "you (informal, object form)",
    "ook": "also; too", "later": "later", "fijne": "nice; pleasant",
    "dag": "day", "heet": "is called/named (3rd person 'heten')",
    "mijn": "my", "naam": "name", "is": "is (3rd person 'zijn')",
    "leila": "Leila (name)", "ik": "I", "student": "student", "leraar": "teacher",
    "ja": "yes", "dat": "that", "nee": "no", "een": "a; an", "nieuw": "new",
    "lid": "member", "hij": "he", "zij": "she", "ingenieur": "engineer",
    "bibliotheek": "library", "bibliotheekmedewerker": "library assistant",
    "daniel": "Daniel (name)", "werk": "work (1st person 'werken')",
    "bij": "at; by", "welkom": "welcome", "in": "in", "dank": "thanks (short form)",
    "de": "the (common gender)", "goed": "good; well",
    # Unit 3 (numbers/ages/prices/phones/market), added 2026-07-05.
    "acht": "eight", "appels": "apples", "bent": "are (formal 'u bent')",
    "bestaat": "exists", "dertien": "thirteen", "dertig": "thirty", "dit": "this",
    "dollar": "dollar(s)", "drie": "three", "een-twee-drie-vier": "one-two-three-four",
    "eenentwintig": "twenty-one", "elf": "eleven", "hoeveel": "how much; how many",
    "honderd": "hundred", "jaar": "year(s)", "kost": "costs", "markt": "market",
    "naar": "to; for", "negen": "nine", "nul": "zero", "oud": "old",
    "prijs": "price", "telefoonnummer": "phone number", "tien": "ten",
    "twaalf": "twelve", "twee": "two", "twintig": "twenty", "uw": "your (formal)",
    "van": "of; from", "veertig": "forty", "vier": "four", "vijf": "five",
    "vijf-vijf-vijf": "five-five-five", "vijfentwintig": "twenty-five",
    "vijftien": "fifteen", "vijftig": "fifty", "vraagt": "asks", "wat": "what",
    "winkel": "shop", "zegt": "says", "zes": "six", "zeven": "seven",
    # Unit 4 (days/months/calendar dates), added 2026-07-05.
    "als": "as", "dan": "then", "datum": "date", "december": "December",
    "dinsdag": "Tuesday", "donderdag": "Thursday", "geweldig": "great",
    "januari": "January", "juli": "July", "kunt": "can (formal 'u kunt')",
    "maand": "month", "maandag": "Monday", "maart": "March", "open": "open",
    "opengaat": "opens (goes open)", "opent": "opens", "opnieuw": "again",
    "schrijven": "to write", "september": "September", "vandaag": "today",
    "verjaardag": "birthday", "vrijdag": "Friday", "wanneer": "when",
    "weer": "again", "welke": "which", "woensdag": "Wednesday",
    "zaterdag": "Saturday", "zondag": "Sunday",
    # Unit 5 (telling the time), added 2026-07-05.
    "avond": "evening", "avonds": "in the evening ('s avonds)", "dicht": "closed",
    "half": "half", "kwart": "quarter", "laat": "late",
    "middag": "afternoon", "nacht": "night", "ochtend": "morning",
    "ochtends": "in the morning ('s ochtends)", "om": "at", "over": "past",
    "s": "fragment of 's ochtends/'s avonds", "uur": "hour; o'clock", "voor": "to",
    # Unit 6 (family members and relationships), added 2026-07-05.
    "broer": "brother", "broers": "brothers", "die": "that; who", "enig": "only",
    "er": "there (of it/them)", "familie": "family", "foto": "photo",
    "grootmoeder": "grandmother", "grootvader": "grandfather", "haar": "her",
    "heb": "have", "kind": "child", "lerares": "teacher (female)", "maar": "but; only",
    "moeder": "mother", "neef": "nephew; male cousin",
    "nicht": "niece; female cousin", "of": "or", "oma": "grandmother",
    "oom": "uncle", "opa": "grandfather", "ouders": "parents", "tante": "aunt",
    "vader": "father", "wie": "who", "ze": "she; they", "zijn": "his",
    "zus": "sister", "zussen": "sisters", "één": "one",
    # Unit 7 (food, drink, and ordering), added 2026-07-05.
    "alles": "everything; all", "alstublieft": "please (formal)",
    "anders": "else; otherwise", "bestelt": "orders", "boterham": "sandwich",
    "brood": "bread", "broodje": "(small) sandwich; roll", "cafe": "cafe",
    "café": "cafe", "cafémenu": "cafe menu",
    "graag": "gladly", "groet": "greets", "hier": "here", "iets": "something",
    "koffie": "coffee", "mag": "may", "meeneemt": "takes away",
    "meenemen": "to take away", "menu": "menu", "nog": "still; more",
    "oke": "okay", "opeet": "eats (here)", "opeten": "to eat (here)",
    "salade": "salad", "sandwich": "sandwich", "soep": "soup", "thee": "tea",
    "water": "water", "wil": "wants",
    # Unit 8 (shopping: prices and quantities), added 2026-07-05.
    "dozijn": "dozen", "eieren": "eggs", "fles": "bottle", "kilo": "kilo",
    "kosten": "to cost", "natuurlijk": "of course; sure", "per": "per",
    "pond": "pound", "rijst": "rice", "tomaten": "tomatoes", "vers": "fresh",
    "zak": "bag",
    # Unit 9 (common places and locations), added 2026-07-05.
    "achter": "behind", "apotheek": "pharmacy", "bank": "bank",
    "naast": "next to", "pardon": "excuse me", "park": "park",
    "restaurant": "restaurant", "tegenover": "across from", "tussen": "between",
    "ver": "far", "vreemde": "stranger", "waar": "where", "weg": "way; road",
    "ziekenhuis": "hospital",
    # Unit 10 (asking for and following directions), added 2026-07-05.
    "aan": "at; on", "eerste": "first", "ga": "go", "herhaalt": "repeats",
    "hoek": "corner", "kom": "come", "komt": "comes", "links": "left",
    "linksaf": "to the left", "minuten": "minutes", "missen": "to miss",
    "neem": "take", "rechtdoor": "straight", "rechterkant": "right side",
    "rechts": "right", "rechtsaf": "to the right", "route": "route",
    "sla": "turn", "stop": "stop", "straat": "street", "tweede": "second",
    # Unit 11 (talking about the weather), added 2026-07-05.
    "beter": "better", "bewolkt": "cloudy", "dus": "so", "gaan": "to go",
    "idee": "idea", "koud": "cold", "laten": "let", "morgen": "tomorrow",
    "op": "on", "paraplu": "umbrella", "regenachtig": "rainy",
    "regenen": "to rain", "regent": "rains", "warm": "warm", "we": "we",
    "winderig": "windy", "wordt": "becomes; will be", "zonnig": "sunny",
    # Unit 12 (clothing: sizes and colors), added 2026-07-05.
    "beschikbaar": "available", "blauw": "blue", "broek": "pants",
    "grote": "big; large", "hebben": "to have", "heeft": "has", "jas": "jacket",
    "jasje": "small jacket", "jurk": "dress", "kleine": "small", "kleur": "color",
    "maat": "size", "medium": "medium", "middelmaat": "medium size",
    "overhemd": "shirt (dress shirt)", "schoenen": "shoes", "shirt": "shirt",
    "zwart": "black", "m": "size M / medium",
    # Unit 13 (talking about feelings), added 2026-07-05.
    "beetje": "a bit; little", "begrijp": "understand", "bezorgd": "worried",
    "bijna": "almost", "blij": "happy", "enthousiast": "excited",
    "examen": "test; exam", "groot": "big", "laatste": "last", "les": "class; lesson",
    "moe": "tired", "oh": "oh", "omdat": "because", "opgewonden": "excited",
    "schrijver": "writer", "verdrietig": "sad", "voel": "feel", "voelt": "feels",
    "voorbij": "over; past", "zich": "oneself (reflexive)",
    # Unit 14 (phone calls and messages), added 2026-07-05.
    "af": "off", "afspreken": "to meet up", "alsjeblieft": "please (informal)",
    "bericht": "message", "dacht": "thought", "herhalen": "to repeat",
    "horen": "to hear", "kan": "can", "kun": "can", "langzamer": "more slowly",
    "plaats": "place", "praten": "to talk", "sorry": "sorry", "spreken": "to speak",
    "stelt": "suggests", "tijd": "time", "vanavond": "tonight",
    # Unit 15 (handling money and payments), added 2026-07-05.
    "accepteert": "accepts", "accepteren": "to accept", "alleen": "only",
    "belasting": "tax", "betaal": "pay", "betaalpas": "debit card",
    "contant": "cash", "creditcard": "credit card", "creditcards": "credit cards",
    "doen": "to do", "geld": "money", "kaart": "card", "pinpas": "debit card",
    "totaal": "total", "totaalbedrag": "total amount",
    # Unit 16 (describing a daily routine), added 2026-07-05.
    "aankleden": "to get dressed", "avondeten": "dinner", "bed": "bed",
    "daarna": "then; after that", "doe": "do", "doet": "does", "elke": "every",
    "kleed": "dress", "me": "myself; me", "meestal": "usually",
    "ontbijt": "breakfast", "wakker": "awake", "word": "become", "worden": "to become",
    # Unit 17 (making simple plans), added 2026-07-05.
    "andere": "other; another", "druk": "busy", "film": "movie", "heel": "very; quite",
    "keer": "time; occasion", "kijken": "to watch; to see", "lunchen": "to have lunch",
    "mij": "me", "misschien": "maybe", "uit": "out", "wandelen": "to walk",
    "weekend": "weekend", "zin": "desire; mood",
    # Unit 18 (describing a recent event), added 2026-07-05.
    "at": "ate", "bezocht": "visited", "eat": "to eat", "gedaan": "done",
    "gegeten": "eaten", "gekeken": "watched; looked", "gewerkt": "worked",
    "gezien": "seen", "ging": "went", "gisteren": "yesterday", "go": "to go",
    "hebt": "have", "samen": "together", "see": "to see", "verleden": "past",
    "visit": "to visit", "vorig": "previous; last", "vorige": "previous; last",
    "was": "was", "week": "week", "werkte": "worked", "work": "to work",
    "zag": "saw",
    # Unit 19 (expressing likes and preferences), added 2026-07-05.
    "denk": "think", "denkt": "thinks", "dol": "crazy; wild", "erg": "very; quite",
    "geef": "give", "geeft": "gives", "geven": "to give", "haten": "to hate",
    "hou": "love; hold", "rustiger": "calmer", "sterk": "strong",
    "vinden": "to find; to consider", "voorkeur": "preference", "waarom": "why",
    "zo": "so",
    # Unit 20 (making basic comparisons), added 2026-07-06.
    "auto": "car", "blauwe": "blue", "duurder": "more expensive",
    "goedkoopst": "cheapest", "goedkoopste": "cheapest", "goedkoper": "cheaper",
    "groter": "bigger", "kleiner": "smaller", "mooier": "nicer", "rode": "red",
    "sneller": "faster", "tas": "bag", "vind": "find; consider", "witte": "white",
    # Unit 21 (handling a basic journey/travel), added 2026-07-06.
    "aankomst": "arrival", "boston": "Boston", "enkele": "single (one-way)",
    "kaartje": "ticket", "loketmedewerker": "ticket clerk", "perron": "platform",
    "reis": "trip; journey", "retour": "round trip", "trein": "train",
    "vanaf": "from", "vertrek": "departure", "vertrekt": "departs",
}


def nl_agreement_tags(token: str) -> dict[str, object]:
    semantics: list[str] = []
    if token in {"hallo", "hoi", "goedemorgen", "goedemiddag", "goedenavond", "welkom"}:
        semantics.append("greeting")
    if token in {"goedemorgen", "goedemiddag", "goedenavond", "dag"}:
        semantics.append("time_period")
    if token in {"tot", "ziens", "doei", "later"}:
        semantics.append("farewell")
    if token in {"hoe", "gaat"}:
        semantics.append("wellbeing_question")
    if token in {"slecht", "oké", "niet", "goed"}:
        semantics.append("wellbeing_answer")
    if token in {"bedankt", "dank", "leuk", "welkom"}:
        semantics.append("politeness")
    if token in {"ja", "nee"}:
        semantics.append("politeness")
    if token in {"naam", "mijn", "heet", "ik", "ben", "is", "je", "u", "jij"}:
        semantics.append("identity")
    if token in {"leila", "daniel"}:
        semantics.append("person_name")
    if token in {"bibliotheek", "bibliotheekmedewerker", "lid", "student", "leraar", "ingenieur", "nieuw", "werk"}:
        semantics.append("dialogue_word")
    if token in {"acht", "dertien", "dertig", "drie", "eenentwintig", "elf",
                 "honderd", "negen", "nul", "tien", "twaalf", "twee", "twintig",
                 "veertig", "vier", "vijf", "vijfentwintig", "vijftien",
                 "vijftig", "zes", "zeven"}:
        semantics.append("number")
    if token in {"oud", "jaar", "vijfentwintig"}:
        semantics.append("age_phrase")
    if token in {"dollar", "prijs", "kost", "hoeveel"}:
        semantics.append("price_phrase")
    if token in {"telefoonnummer"}:
        semantics.append("phone_phrase")
    if token in {"markt", "appels", "winkel", "bestaat", "vraagt", "zegt", "dit", "van", "naar"}:
        semantics.append("market_dialogue")

    tags: dict[str, object] = {}
    if semantics:
        tags["semantic"] = semantics

    person = {
        "ik": "first", "ben": "first",
        "je": "second", "u": "second", "jij": "second", "jou": "second", "mijn": "first",
        "hij": "third", "zij": "third", "het": "third", "is": "third", "heet": "third",
    }.get(token)
    if person:
        tags["person"] = person
    if token in {"je", "jij", "jou"}:
        tags["register"] = "informal"
    elif token == "u":
        tags["register"] = "formal"
    return tags


def iter_specs():
    en_specs: dict[str, dict] = {}
    nl_specs: dict[str, dict] = {}
    for unit_order, (realization_path, overlay_path) in enumerate(UNIT_FILES, 1):
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
        overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
        teaching_overlays = overlay["teaching"]
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson["teaching"]:
                content_key = item["content_key"]
                gloss = teaching_overlays.get(content_key, {}).get("gloss", "")

                for token in item.get("introduced_tokens", []):
                    token = token.casefold().replace("’", "'")
                    if token not in EN_POS:
                        raise ValueError(
                            f"missing English classification for {token!r} "
                            f"in _en_target_lexeme_common.py (lesson {lesson_key})"
                        )
                    existing = en_specs.get(token)
                    tags = en_agreement_tags(token)
                    if existing is None:
                        en_specs[token] = {
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "en",
                            "part_of_speech": EN_POS[token],
                            "english_gloss": EN_TARGET_TO_NL_GLOSS[token], "agreement_tags": tags,
                        }
                    else:
                        for key, value in tags.items():
                            if key == "semantic":
                                prior = existing["agreement_tags"].setdefault(key, [])
                                prior.extend(v for v in value if v not in prior)
                            else:
                                existing["agreement_tags"].setdefault(key, value)

                for match in NL_TOKEN_RE.findall(gloss):
                    token = match.casefold()
                    if token not in NL_POS:
                        raise ValueError(
                            f"missing explicit Dutch gloss for {token!r} "
                            f"(from gloss text {gloss!r}, lesson {lesson_key})"
                        )
                    tags = nl_agreement_tags(token)
                    existing = nl_specs.get(token)
                    if existing is None:
                        nl_specs[token] = {
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": content_key,
                            "token": token, "language_code": "nl",
                            "part_of_speech": NL_POS[token],
                            "english_gloss": NL_GLOSSES[token], "agreement_tags": tags,
                        }
                    else:
                        for key, value in tags.items():
                            if key == "semantic":
                                prior = existing["agreement_tags"].setdefault(key, [])
                                prior.extend(v for v in value if v not in prior)
                            else:
                                existing["agreement_tags"].setdefault(key, value)
    yield from en_specs.values()
    yield from nl_specs.values()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    specs = list(iter_specs())
    if args.dry_run:
        en_count = sum(spec["language_code"] == "en" for spec in specs)
        nl_count = sum(spec["language_code"] == "nl" for spec in specs)
        print(f"Lexeme backfill dry run: {en_count} en, {nl_count} nl.")
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        course = db.scalar(
            select(Course).where(
                Course.source_language == "nl",
                Course.target_language == "en",
                Course.title == "Engels A1",
            )
        )
        if course is None:
            print("ERROR: nl-en 'Engels A1' course must be imported first", file=sys.stderr)
            return 1

        lessons = {
            (unit.order, lesson.order): lesson
            for unit in db.scalars(select(Unit).where(Unit.course_id == course.id))
            for lesson in db.scalars(select(Lesson).where(Lesson.unit_id == unit.id))
        }
        created = 0
        updated = 0
        for spec in specs:
            lesson = lessons.get((spec.pop("unit_order"), spec.pop("lesson_order")))
            if lesson is None:
                print(f"ERROR: imported course is missing {spec['lesson_content_key']}", file=sys.stderr)
                db.rollback()
                return 1
            existing = db.scalar(
                select(Lexeme).where(
                    Lexeme.course_id == course.id,
                    Lexeme.language_code == spec["language_code"],
                    Lexeme.token == spec["token"],
                    Lexeme.part_of_speech == spec["part_of_speech"],
                )
            )
            if existing:
                existing.english_gloss = spec["english_gloss"]
                existing.agreement_tags = spec["agreement_tags"]
                updated += 1
                continue
            db.add(
                Lexeme(
                    course_id=course.id,
                    provenance_lesson_id=lesson.id,
                    provenance_lesson_content_key=spec.pop("lesson_content_key"),
                    provenance_content_key=spec.pop("content_key"),
                    **spec,
                )
            )
            created += 1
        db.commit()
    print(f"Lexeme backfill complete: {created} created, {updated} updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
