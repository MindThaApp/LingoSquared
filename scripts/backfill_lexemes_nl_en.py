#!/usr/bin/env python3
"""Idempotently backfill reviewed nl-en A1+A2 lexemes (English target,
Dutch source) from the shared en realization.

Written directly (not via Codex -- Codex was rate-limited at authoring
time) mirroring scripts/backfill_lexemes.py's structure and rigor.
Target-side English classification lives in
scripts/_en_target_lexeme_common.py (shared with backfill_lexemes_fa_en.py
and backfill_lexemes_prs_en.py, since all three teach the identical
English realization to different source-language speakers -- only the
Dutch/Farsi/Dari source-side classification differs per script).

**Real bug fixed 2026-07-07 (Dutch QA pass)**: A1 (units 1-24) and A2
(units 25-27: bureaucracy/opinions/banking) import as TWO SEPARATE course
rows ("Engels A1"/"Engels A2" -- `POST /admin/content/import` dedups by
`(source_language, target_language, title)`), but this script used to mix
A2 units 25/26 into the SAME `UNIT_FILES` tuple as A1 (continuous
numbering) and look everything up against only the "Engels A1" course.
Since "Engels A1" never actually grows to contain a unit position 25/26,
that lookup doesn't silently misresolve (unlike the analogous fa/prs bug)
-- it hard-fails with "ERROR: imported course is missing ..." and rolls
back the ENTIRE backfill, A1 included, the instant A2 content is actually
imported alongside A1. Same root cause already found and fixed for fa/prs
in `backfill_lexemes.py`/`backfill_lexemes_fa_en.py`/
`backfill_lexemes_prs_en.py`. Fixed by splitting A2 into its own
`UNIT_FILES_A2` (LOCAL 1-based ordering, looked up against the separate
"Engels A2" course) and restructuring `iter_specs()`/`main()` to classify
and backfill each level against its own course. Also closes a real
coverage gap found while fixing this: unit27 (banking) existed on disk but
this script never classified it at all -- added alongside the fix.

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
    # Unit 22 (describing a basic health problem), added 2026-07-06.
    "headache": "hoofdpijn", "stomachache": "buikpijn", "fever": "koorts",
    "cough": "hoest", "sore": "pijnlijk", "throat": "keel", "wrong": "mis",
    "feel": "voelen", "rest": "rusten", "need": "moeten; nodig hebben",
    "doctor": "dokter", "look": "eruitzien", "drink": "drinken",
    "if": "als", "doesn't": "doet niet", "better": "beter",
    # Unit 23 (describing a job), added 2026-07-06.
    "nurse": "verpleegkundige", "cook": "kok", "driver": "chauffeur",
    "patients": "patiënten", "help": "helpen", "reports": "rapporten",
    "interesting": "interessant", "company": "bedrijf", "downtown": "in het centrum",
    "answer": "beantwoorden", "emails": "e-mails", "sometimes": "soms",
    "with": "met", "clients": "klanten", "job": "baan",
    # Unit 24 (describing a home), added 2026-07-06.
    "bedroom": "slaapkamer", "kitchen": "keuken", "bathroom": "badkamer",
    "living": "woon-", "room": "kamer", "garden": "tuin", "many": "veel",
    "rooms": "kamers", "there": "er", "there's": "er is", "apartment": "appartement",
    "has": "heeft", "bedrooms": "slaapkamers", "favorite": "favoriete",
    "tell": "vertel", "isn't": "is niet", "balcony": "balkon", "upstairs": "boven",
    "near": "dichtbij", "easy": "makkelijk", "eat": "eten",
    # Unit 25 (A2: registering with local authorities), added 2026-07-06.
    "appointment": "afspraak", "document": "document", "proof": "bewijs",
    "residency": "woonplaats", "form": "formulier", "confirmation": "bevestiging",
    "wondering": "vragen (zich afvragen)", "whether": "of", "could": "kon; zou kunnen",
    "make": "maken", "possible": "mogelijk", "come": "komen", "update": "bijwerken",
    "address": "adres", "moved": "verhuisde", "id": "identiteitsbewijs",
    "utility": "nuts- (voorziening)", "bill": "rekening", "bring": "meenemen",
    "such": "zoals", "lived": "woonde", "since": "sinds", "lease": "huurcontract",
    "when": "wanneer", "10am": "10:00 uur", "4471": "4471",
    # Unit 26 (A2: giving opinions with reasons), added 2026-07-06.
    "opinion": "mening", "other": "andere", "hand": "kant (aan de andere kant)",
    "agree": "het eens zijn", "dog": "hond", "dogs": "honden", "space": "ruimte",
    "run": "rennen", "playground": "speeltuin", "fair": "redelijk", "point": "punt",
    "they": "zij", "move": "verplaatsen", "farther": "verder", "away": "weg",
    # Unit 27 (A2: opening a bank account), added 2026-07-07 -- part of the
    # nl-en A2 course-routing fix (see this file's docstring). "debit"/
    # "card"/"documents"' sibling singular "document" etc. already exist
    # above (unit15/25); only genuinely new-to-unit27 tokens are added here.
    "checking": "betaal- (in betaalrekening)", "account": "de rekening",
    "monthly": "maandelijks", "fee": "de kosten", "minimum": "het minimum",
    "balance": "het saldo", "direct": "automatisch (in automatische bijschrijving)",
    "deposit": "de bijschrijving; storten", "documents": "documenten",
    "you'll": "u zult", "dmv": "de RDW (vergelijkbaar Nederlands orgaan)",
    "business": "werk- (in werkdagen)", "days": "dagen",
    "keep": "aanhouden", "500": "500", "sounds": "klinkt",
    "teller": "de bankmedewerker", "both": "allebei",
    # Unit 28 (A2: attending a doctor's appointment), added 2026-07-07 --
    # nl-en's practice-pool extension alongside unit27. "appointment"/
    # "insurance card"-sibling "card"/"headache"/"sore"/"throat"/"fever"/
    # "up" already have glosses above (units 25/15/22/16); only genuinely
    # new-to-unit28 tokens are added here, cross-checked against
    # docs/content/overlays/nl-en/a2_unit28.yaml's own real gloss text.
    "medicine": "medicijn", "prescription": "recept",
    "follow": "vervolg- (in follow-up appointment)",
    "getting": "wordt (in getting worse)", "worse": "erger",
    "insurance": "verzekering", "i've": "ik heb", "had": "gehad",
    "early": "vroeg", "confirmed": "bevestigd", "3pm": "15.00 uur",
    "7724": "7724", "back": "terug", "within": "binnen",
    "twice": "twee keer", "plenty": "veel",
    # Unit 29 (A2: reporting a maintenance problem), added 2026-07-07.
    # Atomic per-token glosses -- cross-checked against, but not copy-
    # pasted from, docs/content/overlays/nl-en/a2_unit29.yaml's own real
    # gloss text. "kitchen"/"apartment"/"bathroom" reuse their existing
    # unit24 senses unchanged (recapped, not retaught).
    "leaking": "lekken", "sink": "de gootsteen", "building": "het gebouw",
    "manager": "de beheerder", "plumber": "de loodgieter",
    "repair": "de reparatie", "report": "melden", "problem": "het probleem",
    "been": "geweest (in it's been -- is al ... geweest)",
    "someone": "iemand", "fix": "repareren", "2pm": "14.00 uur",
    "4pm": "16.00 uur", "received": "ontvangen", "6180": "6180",
    "send": "sturen", "home": "thuis", "here's": "hier is",
    # Units 30-42 (nl-en depth-completion sprint, added 2026-07-11 --
    # see docs/content/practice/nl-en/a1_unit30.yaml's notes). Dutch
    # gloss for every English introduced_token these units use.
    "12th": "12e", "active": "actief", "add": "toevoegen", "along": "langs", "already": "al",
    "always": "altijd", "anyone's": "niemands", "app": "app", "apps": "apps",
    "around": "ongeveer", "arrived": "kwam aan", "asked": "vroeg", "bake": "bakken",
    "ball.": "bal", "balloons": "ballonnen", "barks": "blaft", "basketball": "basketbal",
    "battery": "batterij", "before": "voor", "bike": "fiets", "bird": "vogel",
    "blond": "blond", "boil": "koken", "boiled": "kookte", "book": "boek", "books": "boeken",
    "bought": "kocht", "break": "pauze", "brown": "bruin", "bus": "bus", "buy": "kopen",
    "buys": "koopt", "cake": "taart", "call": "bellen", "calm": "kalm", "camera": "camera",
    "cat": "kat", "celebrate": "vieren", "chat": "chatten", "chicago": "Chicago",
    "chop": "fijnsnijden", "chopped": "sneed fijn", "chore": "klusje", "chose": "koos",
    "classes": "lessen", "clean": "schoonmaken", "cleaning": "schoonmaken",
    "cleans": "maakt schoon", "clerk": "medewerker", "college": "college",
    "comfortable": "op zijn gemak", "coming": "komend", "community": "gemeenschap",
    "computer": "computer", "congratulate": "feliciteren", "congratulated": "feliciteerde",
    "congratulations": "felicitaties", "cooking": "koken", "cooks": "kookt", "cost": "kosten",
    "course": "cursus", "coworker": "collega", "coworkers": "collega's",
    "creative": "creatief", "curly": "krullend", "cutting": "snijden", "daniel's": "Daniels",
    "daniel?": "Daniel", "decided": "besloot", "definitely": "zeker", "delicious": "heerlijk",
    "didn't": "deed niet", "different": "verschillende", "differently": "anders",
    "difficult.": "lastig", "dishes": "afwas", "does.": "doet", "doing": "doen",
    "door": "deur", "download": "downloaden", "downloads": "downloadt", "drive": "rijden",
    "drives": "rijdt", "employee": "werknemer", "enjoy": "genieten van",
    "envelope": "envelop", "even": "zelfs", "ever": "weleens", "everyone": "iedereen",
    "everywhere": "overal", "exercise": "sporten / bewegen", "express": "spoedpost",
    "eyes": "ogen", "fast": "snel", "feels": "voelt aan", "fingers": "vingers",
    "finishes": "maakt af", "fish": "vis", "five-minute": "vijf-minuten",
    "forget": "vergeten", "found": "vond", "framed": "ingelijst", "friend": "vriend",
    "friendly": "vriendelijk", "friends": "vrienden", "funny": "grappig",
    "fur": "haar / vacht", "games": "spellen", "gave": "gaf", "gets": "wordt / raakt",
    "gift": "cadeau", "glasses": "een bril", "goes": "gaat", "grandmother's": "oma's",
    "green": "groen", "grocery": "supermarkt", "group": "groep", "guests": "gasten",
    "gym": "sportschool", "habits": "gewoontes", "hair": "haar", "hallway": "gang",
    "hardworking": "hardwerkend", "hates": "haat", "having": "hebbend", "he's": "hij is",
    "helpful": "behulpzaam", "helps": "helpt", "herself": "zichzelf", "him": "hem",
    "hobbies": "hobby's", "homework": "huiswerk", "house": "huis", "how's": "hoe gaat het",
    "humor": "humor", "ingredient": "ingrediënt", "instead": "in plaats daarvan",
    "invite": "uitnodigen", "it?": "het", "know": "weten", "knows": "kent",
    "laptop": "laptop", "laptops": "laptops", "late": "laat", "laugh": "lachen",
    "laundry": "was", "learn": "leren", "learning": "leren", "least": "minst",
    "leave": "achterlaten", "letter": "brief", "letters": "brieven", "likes": "houdt van",
    "live": "wonen", "lives": "woont", "long": "lang", "lopez": "Lopez", "lot": "veel",
    "loves": "houdt van", "low": "laag", "luna": "Luna", "luna.": "Luna", "made": "maakte",
    "mail": "post", "mailbox": "brievenbus", "makes": "maakt", "making": "makend",
    "map": "kaart", "maps": "kaarten", "math": "wiskunde", "max.": "Max",
    "meetings": "vergaderingen", "meets": "ontmoet", "mess": "puinhoop", "mexico": "Mexico",
    "mia": "Mia", "mia's": "Mia's", "mia,": "Mia", "might": "misschien", "mind": "erg vinden",
    "mine": "de mijne", "mom": "moeder", "morning.": "ochtend", "mornings": "ochtenden",
    "most": "meest", "mostly": "meestal", "mother's": "moeders", "mr": "meneer",
    "named": "genaamd", "names": "namen", "nearby": "dichtbij", "needs": "heeft nodig",
    "neighbor": "buur", "neighborhood": "buurt", "neighborhoods": "buurten",
    "neighbors": "buren", "never": "nooit", "nice!": "leuk", "nights": "avonden",
    "noisy": "lawaaierig", "now": "nu", "october": "oktober", "office": "kantoor",
    "office.": "kantoor", "often": "vaak", "okay,": "oké,", "once": "zodra", "onions": "uien",
    "organized": "georganiseerd", "out": "uit / buiten", "outgoing": "extravert",
    "outside": "buiten", "own": "eigen", "package": "pakketje", "packages": "pakketjes",
    "paid": "betaalde", "paint": "schilderen", "painting": "schilderen",
    "paints": "schildert", "pair": "paar", "parking": "parkeren", "party": "feest",
    "pasta": "pasta", "patient": "geduldig", "people": "mensen", "perfect": "perfect",
    "personal": "persoonlijk", "personalities": "persoonlijkheden", "pet": "huisdier",
    "pets": "huisdieren", "phones": "telefoons", "photography": "fotografie",
    "photos": "foto's", "pieces": "stukjes", "planning": "plannen", "plans": "plant",
    "plants": "planten", "play": "spelen", "plays": "speelt", "pool": "zwembad",
    "post": "post", "post office": "postkantoor", "postcard": "ansichtkaart",
    "project": "project", "promotion": "promotie", "put": "zette", "quickly": "snel",
    "quiet": "rustig", "rarely": "zelden", "reading": "lezen", "reads": "leest",
    "ready": "klaar", "really": "echt", "receipt": "kwitantie", "recipe": "recept",
    "recipes": "recepten", "regular": "gewoon", "relax": "ontspannen",
    "relaxed": "ontspannen", "restaurants": "restaurants", "ride": "rijden",
    "running": "hardlopen", "said": "zei", "salt": "zout", "same": "hetzelfde",
    "saturdays": "zaterdagen", "sauce": "saus", "say": "zeggen", "says": "zegt",
    "sends": "stuurt", "sense": "gevoel", "sent": "stuurde", "several": "verschillende",
    "shops": "winkels", "short": "kort", "show": "laten zien", "shy": "verlegen",
    "sister's": "zus haar", "skills": "vaardigheden", "slow": "traag", "soccer": "voetbal",
    "some": "sommige", "someday": "ooit", "something": "iets", "sometime": "een keer",
    "soon": "binnenkort", "spanish": "Spaans", "spending": "doorbrengend", "sport": "sport",
    "stamp": "postzegel", "starting": "beginnend", "stay": "blijven", "still": "toch",
    "studies": "studeert", "study": "studeren", "studying": "studeren", "subject": "vak",
    "sundays": "zondagen", "surprise": "verrassing", "swim.": "zwemmen",
    "swimming": "zwemmen", "swims": "zwemt", "tablet": "tablet", "takes": "neemt",
    "taking": "volgend", "talk": "praten", "talkative": "praatgraag", "talking": "pratend",
    "tall": "lang", "tasks": "taken", "taste": "proeven", "tasted": "proefde",
    "taught": "leerde", "teach": "leren / onderwijzen", "teaches": "leert", "team": "team",
    "tennis": "tennis", "text": "appen", "thanked": "bedankte", "thankful": "dankbaar",
    "their": "hun", "them": "hen", "these": "deze", "though": "toch", "times": "keer",
    "took": "nam", "trash": "vuilnis", "travel": "reizen", "tries": "probeert",
    "upset": "boos", "us": "ons", "use": "gebruiken", "uses": "gebruikt",
    "using": "gebruikend", "vacuum": "stofzuigen", "vacuumed": "stofzuigde",
    "vacuums": "stofzuigt", "video": "video", "walks,": "wandelt", "wanted": "wilde",
    "wants": "wil", "warms": "warmt op", "wash": "wassen", "washes": "wast",
    "washing": "wassend", "watch": "kijken naar", "waters": "geeft water", "ways": "manieren",
    "we'll": "we zullen", "wears": "draagt", "weekends": "weekends", "weighed": "woog",
    "were": "waren", "while": "terwijl", "wifi": "wifi", "wish": "wensen",
    "without": "zonder", "wonderful": "geweldig", "work?": "werk", "worry": "zorgen maken",
    "writes": "schrijft", "yes,": "ja,", "yet": "nog", "yoga": "yoga",
}

EN_TARGET_TO_NL_GLOSS.update({
    "sky": "lucht", "grass": "gras", "yellow": "geel", "sun": "zon",
    "dark": "donker", "wearing": "draagt", "light": "licht",
    "painted": "geverfd", "bright": "fel", "fun": "leuk", "our": "onze",
    "presentation": "presentatie", "choose": "kiezen", "colors": "kleuren",
    "looks": "ziet eruit", "professional": "professioneel", "choice": "keuze",
    "everything": "alles", "gardens": "tuinen", "especially": "vooral",
    "beautiful": "mooi", "reminds": "herinnert", "everyday": "alledaags",
    "conversations": "gesprekken", "spring": "lente", "flowers": "bloemen",
    "bloom": "bloeien", "summer": "zomer", "beach": "strand", "fall": "herfst",
    "change": "veranderen", "winter": "winter", "snows": "sneeuwt",
    "season": "seizoen", "walking": "wandelen", "seasons": "seizoenen",
    "playing": "spelen", "find": "vinden", "outdoors": "buiten",
    "emergency": "noodgeval", "police": "politie", "ambulance": "ambulance",
    "fire": "brand", "department": "dienst", "911": "911", "burning": "brandt",
    "smell": "geur", "smoke": "rook", "pan": "pan", "caught": "vatte",
    "off": "uit", "stove": "fornuis", "hurry": "haasten",
    "friend's": "van een vriend", "goodness": "goedheid", "wait": "wachten",
    "case": "geval", "safer": "veiliger", "until": "totdat",
    "elevator": "lift", "stairs": "trap", "third": "derde", "give": "geven",
    "finally": "eindelijk", "waited": "wachtte", "notice": "bericht",
    "safe": "veilig", "came": "kwam", "check": "controleren",
    "relieved": "opgelucht", "hurt": "gewond", "lost": "kwijt",
    "keys": "sleutels", "wallet": "portemonnee", "backpack": "rugzak",
    "seen": "gezien", "anyone": "iemand", "strap": "band",
    "where's": "waar is", "fountain": "fontein", "you're": "je bent",
    "inside": "binnen", "ask": "vragen", "holding": "vasthouden",
    "desk": "balie", "lose": "verliezen", "item": "voorwerp",
    "main": "hoofd-", "gate": "poort", "describe": "beschrijven",
    "its": "zijn/haar", "special": "speciaal", "details": "details",
    "staff": "personeel", "called": "belde", "told": "vertelde",
    "whole": "hele", "story": "verhaal", "track": "bijhouden",
    "things": "dingen", "available": "beschikbaar", "confirm": "bevestigen",
    "reschedule": "verzetten", "max": "Max", "seems": "lijkt",
    "lately": "de laatste tijd", "due": "toe aan", "yearly": "jaarlijks",
    "checkup": "controle", "vet": "dierenarts", "dog's": "van de hond",
    "max's": "van Max", "dentist": "tandarts", "service": "service",
    "you'd": "je zou", "receptionist": "receptionist", "changes": "wijzigingen",
    "nervous": "zenuwachtig", "borrow": "lenen", "return": "terugbrengen",
    "borrowed": "geleend", "weeks": "weken", "cookbook": "kookboek",
    "fill": "invullen", "visiting": "bezoeken", "libraries": "bibliotheken",
    "let": "laten", "items": "voorwerpen", "few": "paar",
    "librarian": "bibliothecaris", "finished": "klaar", "used": "gebruikte",
    "started": "begon", "borrowing": "lenen", "returned": "teruggebracht",
    "picked": "opgehaald", "got": "kreeg", "checked": "controleerde",
    "practice": "oefening", "teaching": "lesgeven", "reminded": "herinnerde",
})

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
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit22_health.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit22.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit23_work.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit23.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit24_housing.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit24.yaml",
    ),
    # Units 30-42, added 2026-07-11 as part of the nl-en depth-completion
    # sprint (see docs/content/practice/nl-en/a1_unit30.yaml's notes) --
    # units 25-29 are the SEPARATE A2 course (UNIT_FILES_A2 below), so the
    # A1 realization sequence continues at unit30 (hobbies) on disk. Note
    # the one filename irregularity: unit30's overlay is named
    # "a1_unit25.yaml" (nl-en's own older sequential numbering, predating
    # the "match the realization's own unit number" convention adopted
    # from unit31 onward) -- confirmed by reading its unit_key
    # (en.a1.unit30.hobbies), not a typo. All all other unit31+ overlay
    # filenames match their realization's own unit number exactly.
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit30_hobbies.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit25.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit31_appearance.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit31.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit32_animals.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit32.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit33_transportation.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit33.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit34_sports.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit34.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit35_technology.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit35.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit36_education.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit36.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit37_celebrations.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit37.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit38_household.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit38.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit39_neighborhood.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit39.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit40_post.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit40.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit41_cooking.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit41.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit42_personality.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit42.yaml",
    ),
    # Units 43-48 (colors / seasons / emergencies / lost items /
    # appointments / library), added 2026-07-12 for the Endless Practice
    # coverage-extension batch. Kept in the A1 tuple because these files
    # import into the same "Engels A1" course row as units 30-42.
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit43_colors.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit43.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit44_seasons.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit44.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit45_emergencies.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit45.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit46_lost_items.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit46.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit47_appointments.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit47.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a1_unit48_library.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a1_unit48.yaml",
    ),
)

# A2 units (25-27: bureaucracy, opinions, banking) live in a SEPARATE course
# row ("Engels A2", not "Engels A1") -- `POST /admin/content/import`
# matches/creates courses by (source_language, target_language, title), and
# every a2_unit*.yaml overlay declares `course.title: Engels A2`, distinct
# from A1's `Engels A1`. Real bug found live 2026-07-07 (Dutch QA pass), same
# root cause already found and fixed in backfill_lexemes.py/
# backfill_lexemes_fa_en.py/backfill_lexemes_prs_en.py for fa/prs: this used
# to mix units 25/26 INTO the single UNIT_FILES tuple above at continuous
# positions 25/26, then main() looked them up against the "Engels A1"
# course's own units -- which only ever has 24 (the real "Engels A1" course
# never grows to contain a position 25/26), so the lookup didn't silently
# misresolve here (unlike the fa/prs incident) -- it hard-failed with
# "ERROR: imported course is missing ..." and rolled back the ENTIRE
# backfill (A1 included) the moment any A2 content was actually imported
# alongside A1, which is worse than a silent gap. Kept as its own tuple with
# LOCAL 1-based ordering (looked up against the separate "Engels A2" course
# in main()) -- also closes a real coverage gap found while fixing this:
# unit27 (banking) existed on disk (docs/content/realizations/en/
# a2_unit27_banking.yaml, docs/content/overlays/nl-en/a2_unit27.yaml,
# scripts/content_manifest.txt's "nl-en-a2" entry) but this script never
# classified it at all.
UNIT_FILES_A2 = (
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit25_bureaucracy.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a2_unit25.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit26_opinions.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a2_unit26.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit27_banking.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a2_unit27.yaml",
    ),
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit28_doctor.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a2_unit28.yaml",
    ),
    # Unit 29 (A2: reporting a maintenance problem), added 2026-07-07 --
    # closing the practice-pool gap for the newest A2 unit (units 25-28
    # already had fa-en/nl-en/prs-en packs; unit29 had none). EN_POS/
    # en_agreement_tags for this unit's vocabulary (including the new
    # 3-member maintenance_noun tag [sink, plumber, repair]) were added to
    # _en_target_lexeme_common.py as part of this same pass -- verified
    # every introduced_token across this realization file against EN_POS's
    # keys: zero missing. Only this script's own Dutch (target-side)
    # gloss dict needed extending (18 new tokens, cross-checked against
    # docs/content/overlays/nl-en/a2_unit29.yaml's own real text, not
    # copy-pasted from it).
    (
        REPO_ROOT / "docs/content/realizations/en/a2_unit29_maintenance.yaml",
        REPO_ROOT / "docs/content/overlays/nl-en/a2_unit29.yaml",
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
    # Unit 22 (describing a basic health problem), added 2026-07-06.
    "buikpijn": "noun", "dokter": "noun", "drinken": "verb", "hoest": "noun",
    "hoofdpijn": "noun", "keelpijn": "noun", "koorts": "noun", "moet": "verb",
    "rusten": "verb", "weet": "verb", "zeker": "adjective", "ziet": "verb",
    # Unit 23 (describing a job), added 2026-07-06.
    "baan": "noun", "beantwoord": "verb", "bedrijf": "noun", "centrum": "noun",
    "chauffeur": "noun", "e-mails": "noun", "help": "verb", "interessant": "adjective",
    "klanten": "noun", "klein": "adjective", "kok": "noun", "ontmoet": "verb",
    "patiënten": "noun", "rapporten": "noun", "schrijf": "verb", "soms": "adverb",
    "verpleegkundige": "noun",
    # Unit 24 (describing a home), added 2026-07-06.
    "appartement": "noun", "badkamer": "noun", "balkon": "noun",
    "bovenverdieping": "noun", "daar": "adverb", "eten": "verb",
    "favoriete": "adjective", "kamer": "noun", "kamers": "noun", "keuken": "noun",
    "makkelijk": "adjective", "slaapkamer": "noun", "slaapkamers": "noun",
    "tuin": "noun", "vertel": "verb", "woonkamer": "noun",
    # Unit 25 (A2: registering with local authorities), added 2026-07-06.
    "adres": "noun", "afspraak": "noun", "bevestigingsnummer": "noun",
    "bewijs": "noun", "bijwerken": "verb", "breng": "verb", "deze": "pronoun",
    "document": "noun", "energierekening": "noun", "formulier": "noun",
    "huurcontract": "noun", "identiteitsbewijs": "noun", "komen": "verb",
    "kon": "verb", "maken": "verb", "medewerker": "noun", "mee": "particle",
    "mogelijk": "adjective", "nieuwe": "adjective", "past": "verb",
    "sinds": "preposition", "verhuisd": "verb", "vertellen": "verb",
    "vroeg": "verb", "werken": "verb", "woonplaats": "noun", "woont": "verb",
    "zoals": "preposition", "zou": "verb",
    # Unit 26 (A2: giving opinions with reasons), added 2026-07-06.
    "eens": "adverb", "ermee": "adverb", "kant": "noun", "mening": "noun",
    # Unit 27 (A2: opening a bank account), added 2026-07-07 -- Dutch words
    # extracted from this unit's own overlay gloss text, part of the nl-en
    # A2 course-routing fix (see this file's docstring).
    "aanhoudt": "verb", "allebei": "pronoun", "automatische": "adjective",
    "betaalrekening": "noun", "bijschrijving": "noun", "binnen": "preposition",
    "documenten": "noun", "geen": "particle", "klinkt": "verb",
    "krijg": "verb", "maandelijkse": "adjective", "minimumsaldo": "noun",
    "net": "adverb", "nodig": "adjective", "openen": "verb", "rdw": "proper_noun",
    "rekening": "noun", "werkdagen": "noun",
    # Unit 28 (A2: attending a doctor's appointment), added 2026-07-07 --
    # Dutch words extracted from this unit's own overlay gloss text, part
    # of the nl-en A2 practice-pool extension alongside unit27.
    "medicijn": "noun", "recept": "noun", "vervolgafspraak": "noun",
    "erger": "adjective", "verzekeringspas": "noun", "willen": "verb",
    "zien": "verb", "al": "adverb", "dagen": "noun", "tevoren": "adverb",
    "aankomen": "verb", "bevestigd": "verb", "hand": "noun",
    "flinke": "adjective", "verkoudheid": "noun", "medicijnen": "noun",
    "nemen": "verb", "gedurende": "preposition", "drink": "verb",
    "veel": "adverb", "terugkomen": "verb", "terug": "adverb",
    # Unit 29 (A2: reporting a maintenance problem), added 2026-07-07 --
    # Dutch words extracted from this unit's own overlay gloss text,
    # closing the practice-pool gap alongside the fa-en/prs-en passes.
    "gootsteen": "noun", "hartelijk": "adverb", "huismeester": "noun",
    "iemand": "pronoun", "keukengootsteen": "noun", "lekken": "verb",
    "lekt": "verb", "loodgieter": "noun", "melden": "verb", "mis": "adjective",
    "ontvangen": "verb", "probleem": "noun", "reparatie": "noun",
    "reparatienummer": "noun", "reparatieverzoek": "noun",
    "repareren": "verb", "stuur": "verb", "thuis": "adverb",
    "vanochtend": "adverb", "wees": "verb",
    # Units 30-42 (nl-en depth-completion sprint, added 2026-07-11).
    # Every Dutch word found in these units' overlay gloss text.
    "aankwam": "verb", "aanstaande": "adjective", "aanvoelt": "verb", "actief": "adjective",
    "afgelopen": "adjective", "afval": "noun", "afwas": "noun", "alle": "adjective",
    "allemaal": "adverb", "altijd": "adverb", "anderen": "pronoun", "app": "noun",
    "appartementsgebouw": "noun", "appen": "verb", "apps": "noun", "aten": "verb",
    "avondopleiding": "noun", "bal": "noun", "ballonnen": "noun", "basketbal": "noun",
    "batterij": "noun", "bedankte": "verb", "begin": "noun", "bel": "verb", "bellen": "verb",
    "belt": "verb", "berichtje": "noun", "besloot": "verb", "betaalde": "verb",
    "betere": "adjective", "bewegen": "verb", "bezoek": "noun", "binnenkort": "adverb",
    "birthday": "noun", "blaft": "verb", "blijven": "verb", "blond": "adjective",
    "boek": "noun", "boeken": "noun", "boos": "adjective", "brengen": "verb", "brief": "noun",
    "brieven": "noun", "brievenbus": "noun", "bril": "noun", "bruin": "adjective",
    "bruine": "adjective", "buiten": "adverb", "buren": "noun", "bus": "noun",
    "busrit": "noun", "buur": "noun", "buurman": "noun", "buurt": "noun",
    "buurtcollege": "noun", "buurvrouw": "noun", "cadeau": "noun", "camera": "noun",
    "chicago": "proper_noun", "collega": "noun", "collega's": "noun", "college": "noun",
    "community": "noun", "computer": "noun", "computercursus": "noun",
    "creatief": "adjective", "cursist": "noun", "cursus": "noun", "daniels": "proper_noun",
    "dankbaar": "adjective", "deur": "noun", "dichtbij": "adverb", "door": "preposition",
    "downloaden": "verb", "draagt": "verb", "duurde": "verb", "duurt": "verb",
    "echt": "adverb", "eigen": "adjective", "elk": "adjective", "enorm": "adverb",
    "envelop": "noun", "ergens": "adverb", "erover": "adverb", "eruit": "adverb",
    "ervan": "adverb", "ervoor": "adverb", "expresverzending": "noun",
    "extravert": "adjective", "favoriet": "adjective", "feest": "noun", "feestje": "noun",
    "felicitaties": "noun", "feliciteerde": "verb", "feliciteren": "verb", "fiets": "noun",
    "fijn": "adjective", "fijnsnijden": "verb", "foto's": "noun", "fotografieles": "noun",
    "gaf": "verb", "gang": "noun", "gebouw": "noun", "gebruik": "verb", "gebruiken": "verb",
    "gebruikt": "verb", "gedag": "noun", "geduldig": "adjective", "gefeliciteerd": "particle",
    "gelukkige": "adjective", "gemaakt": "verb", "gemak": "noun", "genieten": "verb",
    "georganiseerd": "adjective", "gesprek": "noun", "gevoel": "noun",
    "geweldige": "adjective", "gewone": "adjective", "gewoontes": "noun",
    "gisteravond": "adverb", "goede": "adjective", "grappig": "adjective",
    "groen": "adjective", "groene": "adjective", "groep": "noun", "haat": "verb",
    "had": "verb", "hakken": "verb", "happy": "adjective", "hardloopschoenen": "noun",
    "hardlopen": "verb", "hardwerkend": "adjective", "heerlijk": "adjective",
    "helpen": "verb", "helpt": "verb", "hem": "pronoun", "hen": "pronoun",
    "hetzelfde": "adjective", "hobby's": "noun", "hoeft": "verb", "hond": "noun",
    "houden": "verb", "houdt": "verb", "huis": "noun", "huisdier": "noun",
    "huisdieren": "noun", "huishoudelijke": "adjective", "huiswerk": "noun", "hulp": "noun",
    "humor": "noun", "hun": "pronoun", "iedereen": "pronoun", "ingelijste": "adjective",
    "ingrediënt": "noun", "jouw": "pronoun", "kaartapp": "noun", "kaarten": "noun",
    "kalm": "adjective", "kantoor": "noun", "kat": "noun", "kennen": "verb", "kent": "verb",
    "kijkt": "verb", "klaar": "adjective", "klopt": "verb", "klusje": "noun",
    "klusjes": "noun", "koken": "verb", "kook": "verb", "kookapp": "noun", "kookt": "verb",
    "kookte": "verb", "kookvaardigheden": "noun", "koop": "verb", "koopt": "verb",
    "koos": "verb", "kopen": "verb", "kort": "adjective", "kreeg": "verb",
    "krullend": "adjective", "kwam": "verb", "kwitantie": "noun", "lachen": "verb",
    "lang": "adjective", "laptop": "noun", "lastig": "adjective", "lawaaierig": "adjective",
    "leer": "verb", "leerde": "verb", "leert": "verb", "lees": "verb", "leren": "verb",
    "lessen": "noun", "lezen": "verb", "lief": "adjective", "liever": "adverb",
    "ligt": "verb", "lopen": "verb", "lopez": "proper_noun", "luna": "proper_noun",
    "lunch": "noun", "maak": "verb", "maakt": "verb", "maakte": "verb",
    "maandagavond": "noun", "manier": "noun", "max": "proper_noun", "meer": "adverb",
    "meneer": "noun", "mensen": "noun", "mexico": "proper_noun", "mia": "proper_noun",
    "mia's": "proper_noun", "moeten": "verb", "na": "preposition", "naartoe": "adverb",
    "namen": "noun", "neemt": "verb", "niemands": "pronoun", "nieuws": "noun",
    "nooit": "adverb", "nu": "adverb", "ogen": "noun", "oktober": "proper_noun",
    "ongeveer": "adverb", "ontspannen": "verb", "ooit": "adverb", "opschieten": "verb",
    "opschrijven": "verb", "opwarmen": "verb", "oude": "adjective", "overal": "adverb",
    "overkant": "noun", "paar": "noun", "pakje": "noun", "pakketje": "noun",
    "pakketjes": "noun", "parkeren": "verb", "pasta": "noun", "pauzeruimte": "noun",
    "perfect": "adjective", "persoonlijker": "adjective", "persoonlijkheden": "noun",
    "plannen": "verb", "planten": "noun", "post": "noun", "postbus": "noun",
    "postkantoor": "noun", "postzegel": "noun", "praatgraag": "adjective",
    "prima": "adjective", "probeert": "verb", "proefde": "verb", "proeven": "verb",
    "project": "noun", "puinhoop": "noun", "raakt": "verb", "raken": "verb",
    "recepten": "noun", "reizen": "verb", "rest": "noun", "restaurants": "noun",
    "rijdt": "verb", "rit": "noun", "rond": "preposition", "rustig": "adjective",
    "rustige": "adjective", "saus": "noun", "schieten": "verb", "schilder": "verb",
    "schilderen": "verb", "schildert": "verb", "schoon": "adjective", "schoonmaken": "verb",
    "schrijft": "verb", "sneed": "verb", "snel": "adverb", "snijden": "verb",
    "spaans": "proper_noun", "speel": "verb", "speelt": "verb", "spelen": "verb",
    "spoedpost": "noun", "sport": "noun", "sporten": "verb", "sportschool": "noun",
    "spraakzaam": "adjective", "steeds": "adverb", "stil": "adjective", "stofzuigde": "verb",
    "stofzuigen": "verb", "stofzuigt": "verb", "studeer": "verb", "stukjes": "noun",
    "sturen": "verb", "stuurde": "verb", "stuurt": "verb", "supermarkt": "noun",
    "taak": "noun", "taart": "noun", "tablet": "noun", "taken": "noun", "team": "noun",
    "tegen": "preposition", "tekstbericht": "noun", "telefoon": "noun", "tennis": "noun",
    "tennist": "verb", "terwijl": "particle", "tijdens": "preposition", "toch": "adverb",
    "toe": "particle", "toen": "adverb", "toets": "noun", "toevoegen": "verb",
    "traag": "adjective", "tuurlijk": "adverb", "uien": "noun", "uitgelaten": "verb",
    "uitlaten": "verb", "uitnodigen": "verb", "vaak": "adverb", "vaardigheden": "noun",
    "vaat": "noun", "vak": "noun", "vergaderingen": "noun", "verhuizen": "verb",
    "verjaardagscadeau": "noun", "verjaardagspakketje": "noun", "verlegen": "adjective",
    "verrassing": "noun", "verrassingsfeestje": "noun", "verschillend": "adjective",
    "verschillende": "adjective", "versturen": "verb", "videobellen": "verb",
    "videogames": "noun", "vieren": "verb", "vindt": "verb", "vingers": "noun", "vis": "noun",
    "vloeistof": "noun", "voetbal": "noun", "voetballen": "verb", "vogel": "noun",
    "volg": "verb", "volgen": "verb", "volgende": "adjective", "volgt": "verb",
    "vond": "verb", "vooral": "adverb", "voordat": "particle", "vriendelijk": "adjective",
    "vrienden": "noun", "vrije": "adjective", "vuilnis": "noun", "wandelt": "verb",
    "want": "particle", "waren": "verb", "wel": "adverb", "weleens": "adverb",
    "wensen": "verb", "werkt": "verb", "wifi": "noun", "wilde": "verb", "wilt": "verb",
    "winkels": "noun", "wist": "verb", "wonen": "verb", "woog": "verb", "yoga": "noun",
    "zaterdagochtend": "noun", "zeggen": "verb", "zei": "verb", "zelden": "adverb",
    "zelf": "pronoun", "zette": "verb", "zetten": "verb", "zie": "verb", "zodra": "particle",
    "zoeken": "verb", "zonder": "preposition", "zorgen": "noun", "zout": "noun",
    "zullen": "verb", "zwembad": "noun", "zwemmen": "verb", "zwemt": "verb",
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
    # Unit 22 (describing a basic health problem), added 2026-07-06.
    "buikpijn": "stomachache", "dokter": "doctor", "drinken": "to drink",
    "hoest": "cough", "hoofdpijn": "headache", "keelpijn": "sore throat",
    "koorts": "fever", "moet": "must", "rusten": "to rest",
    "weet": "know (with ik)", "zeker": "sure; certain", "ziet": "sees; looks",
    # Unit 23 (describing a job), added 2026-07-06.
    "baan": "job", "beantwoord": "answer (with ik)", "bedrijf": "company",
    "centrum": "center; downtown", "chauffeur": "driver", "e-mails": "emails",
    "help": "help (with ik)", "interessant": "interesting", "klanten": "clients",
    "klein": "small", "kok": "cook", "ontmoet": "meet (with ik)",
    "patiënten": "patients", "rapporten": "reports", "schrijf": "write (with ik)",
    "soms": "sometimes", "verpleegkundige": "nurse",
    # Unit 24 (describing a home), added 2026-07-06.
    "appartement": "apartment", "badkamer": "bathroom", "balkon": "balcony",
    "bovenverdieping": "upstairs (floor above)", "daar": "there", "eten": "to eat",
    "favoriete": "favorite", "kamer": "room", "kamers": "rooms", "keuken": "kitchen",
    "makkelijk": "easy", "slaapkamer": "bedroom", "slaapkamers": "bedrooms",
    "tuin": "garden", "vertel": "tell (with ik)", "woonkamer": "living room",
    # Unit 25 (A2: registering with local authorities), added 2026-07-06.
    "adres": "address", "afspraak": "appointment", "bevestigingsnummer": "confirmation number",
    "bewijs": "proof", "bijwerken": "to update", "breng": "bring (with ik)",
    "deze": "this", "document": "document", "energierekening": "energy bill",
    "formulier": "form", "huurcontract": "lease", "identiteitsbewijs": "ID",
    "komen": "to come", "kon": "could", "maken": "to make", "medewerker": "clerk",
    "mee": "along (part of meebrengen)", "mogelijk": "possible", "nieuwe": "new",
    "past": "fits; works (time)", "sinds": "since", "verhuisd": "moved",
    "vertellen": "to tell", "vroeg": "asked (part of zich afvragen)",
    "werken": "to work", "woonplaats": "residency; place of residence",
    "woont": "lives", "zoals": "such as", "zou": "would",
    # Unit 26 (A2: giving opinions with reasons), added 2026-07-06.
    "eens": "agreed (part of het eens zijn)", "ermee": "with it",
    "kant": "side", "mening": "opinion",
    # Unit 27 (A2: opening a bank account), added 2026-07-07.
    "aanhoudt": "keeps; maintains (with u, formal)", "allebei": "both",
    "automatische": "automatic (inflected)", "betaalrekening": "payment/checking account",
    "bijschrijving": "deposit; credit entry", "binnen": "within",
    "documenten": "documents", "geen": "no; not any", "klinkt": "sounds",
    "krijg": "get; receive (with ik)", "maandelijkse": "monthly (inflected)",
    "minimumsaldo": "minimum balance", "net": "just (net als, just like)",
    "nodig": "necessary; needed", "openen": "to open",
    "rdw": "RDW (Dutch DMV equivalent)", "rekening": "account",
    "werkdagen": "business days; work days",
    # Unit 28 (A2: attending a doctor's appointment), added 2026-07-07.
    "medicijn": "medicine", "recept": "prescription",
    "vervolgafspraak": "follow-up appointment", "erger": "worse",
    "verzekeringspas": "insurance card", "willen": "to want", "zien": "to see",
    "al": "already", "dagen": "days", "tevoren": "beforehand (van tevoren)",
    "aankomen": "to arrive", "bevestigd": "confirmed",
    "hand": "hand (idiom: wat is er aan de hand -- what's wrong)",
    "flinke": "bad; severe (inflected)", "verkoudheid": "a cold (illness)",
    "medicijnen": "medicines", "nemen": "to take",
    "gedurende": "for; during", "drink": "drink (imperative, with jij/u)",
    "veel": "much; a lot", "terugkomen": "to come back", "terug": "back",
    # Unit 29 (A2: reporting a maintenance problem), added 2026-07-07.
    # English glosses for the Dutch words extracted from this unit's own
    # overlay gloss text (see the matching NL_POS block above).
    "gootsteen": "sink", "hartelijk": "hearty; warmly (hartelijk dank)",
    "huismeester": "building manager", "iemand": "someone",
    "keukengootsteen": "kitchen sink", "lekken": "to leak",
    "lekt": "leaks (3rd person 'lekken')", "loodgieter": "plumber",
    "melden": "to report", "mis": "wrong (wat is er mis)",
    "ontvangen": "received", "probleem": "problem", "reparatie": "repair",
    "reparatienummer": "repair number", "reparatieverzoek": "repair request",
    "repareren": "to repair; to fix",
    "stuur": "send (1st person 'sturen')", "thuis": "home; at home",
    "vanochtend": "this morning", "wees": "be (imperative 'zijn')",
    # Units 30-42 (nl-en depth-completion sprint, added 2026-07-11).
    # English glosses for the Dutch words in these units' overlay gloss
    # text (see the matching NL_POS block above).
    "aankwam": "arrived", "aanstaande": "upcoming / next", "aanvoelt": "feels (like)",
    "actief": "active", "afgelopen": "last / past", "afval": "trash", "afwas": "dishes",
    "alle": "all", "allemaal": "all", "altijd": "always", "anderen": "others", "app": "app",
    "appartementsgebouw": "apartment building", "appen": "to text / message", "apps": "apps",
    "aten": "ate", "avondopleiding": "evening course", "bal": "ball", "ballonnen": "balloons",
    "basketbal": "basketball", "batterij": "battery", "bedankte": "thanked",
    "begin": "start / beginning", "bel": "call", "bellen": "to call", "belt": "calls",
    "berichtje": "text message", "besloot": "decided", "betaalde": "paid", "betere": "better",
    "bewegen": "to exercise / move", "bezoek": "guests / visit", "binnenkort": "soon",
    "birthday": "birthday", "blaft": "barks", "blijven": "to stay", "blond": "blond",
    "boek": "book", "boeken": "books", "boos": "upset / angry", "brengen": "to spend (time)",
    "brief": "letter", "brieven": "letters", "brievenbus": "mailbox", "bril": "glasses",
    "bruin": "brown", "bruine": "brown", "buiten": "outside", "buren": "neighbors",
    "bus": "bus", "busrit": "bus ride", "buur": "neighbor", "buurman": "neighbor (male)",
    "buurt": "neighborhood", "buurtcollege": "community college",
    "buurvrouw": "neighbor (female)", "cadeau": "gift", "camera": "camera",
    "chicago": "Chicago", "collega": "coworker", "collega's": "coworkers",
    "college": "college", "community": "community", "computer": "computer",
    "computercursus": "computer course", "creatief": "creative",
    "cursist": "student (course participant)", "cursus": "course", "daniels": "Daniel's",
    "dankbaar": "thankful", "deur": "door", "dichtbij": "close / nearby", "door": "through",
    "downloaden": "to download", "draagt": "wears", "duurde": "took (time)",
    "duurt": "takes (time) / lasts", "echt": "really", "eigen": "own", "elk": "each / every",
    "enorm": "enormously / a lot", "envelop": "envelope",
    "ergens": "somewhere / about anything", "erover": "about it",
    "eruit": "out / like (in look like)", "ervan": "of it", "ervoor": "for it",
    "expresverzending": "express mail", "extravert": "outgoing", "favoriet": "favorite",
    "feest": "party", "feestje": "party (small)", "felicitaties": "congratulations",
    "feliciteerde": "congratulated", "feliciteren": "to congratulate", "fiets": "bike",
    "fijn": "nice / fine", "fijnsnijden": "to chop finely", "foto's": "photos",
    "fotografieles": "photography class", "gaf": "gave", "gang": "hallway",
    "gebouw": "building", "gebruik": "use", "gebruiken": "to use", "gebruikt": "uses",
    "gedag": "hello", "geduldig": "patient", "gefeliciteerd": "congratulations",
    "gelukkige": "happy", "gemaakt": "made", "gemak": "ease / comfort",
    "genieten": "to enjoy", "georganiseerd": "organized", "gesprek": "conversation",
    "gevoel": "sense / feeling", "geweldige": "wonderful / great", "gewone": "regular",
    "gewoontes": "habits", "gisteravond": "last night", "goede": "good", "grappig": "funny",
    "groen": "green", "groene": "green", "groep": "group", "haat": "hates", "had": "had",
    "hakken": "to chop", "happy": "happy", "hardloopschoenen": "running shoes",
    "hardlopen": "to run / running", "hardwerkend": "hardworking", "heerlijk": "delicious",
    "helpen": "to help", "helpt": "helps", "hem": "him", "hen": "them",
    "hetzelfde": "the same", "hobby's": "hobbies", "hoeft": "needs to", "hond": "dog",
    "houden": "to like / love", "houdt": "likes / loves", "huis": "house", "huisdier": "pet",
    "huisdieren": "pets", "huishoudelijke": "household", "huiswerk": "homework",
    "hulp": "help", "humor": "humor", "hun": "their", "iedereen": "everyone",
    "ingelijste": "framed", "ingrediënt": "ingredient", "jouw": "your", "kaartapp": "map app",
    "kaarten": "maps", "kalm": "calm", "kantoor": "office", "kat": "cat", "kennen": "to know",
    "kent": "knows", "kijkt": "watches / looks", "klaar": "ready",
    "klopt": "is right / correct", "klusje": "chore", "klusjes": "chores",
    "koken": "to cook / cooking", "kook": "cook", "kookapp": "cooking app", "kookt": "cooks",
    "kookte": "cooked", "kookvaardigheden": "cooking skills", "koop": "buy", "koopt": "buys",
    "koos": "chose", "kopen": "to buy", "kort": "short", "kreeg": "got", "krullend": "curly",
    "kwam": "came / arrived", "kwitantie": "receipt", "lachen": "to laugh",
    "lang": "tall / long", "laptop": "laptop", "lastig": "difficult", "lawaaierig": "noisy",
    "leer": "learn", "leerde": "taught / learned", "leert": "learns / teaches",
    "lees": "read", "leren": "to learn", "lessen": "classes", "lezen": "to read / reading",
    "lief": "sweet / kind", "liever": "rather / prefer", "ligt": "lies", "lopen": "to walk",
    "lopez": "Lopez", "luna": "Luna", "lunch": "lunch", "maak": "make / take",
    "maakt": "takes / makes", "maakte": "made", "maandagavond": "Monday evening",
    "manier": "way", "max": "Max", "meer": "more", "meneer": "Mr.", "mensen": "people",
    "mexico": "Mexico", "mia": "Mia", "mia's": "Mia's", "moeten": "must / need to",
    "na": "after", "naartoe": "to (destination)", "namen": "names", "neemt": "takes",
    "niemands": "nobody's", "nieuws": "news", "nooit": "never", "nu": "now", "ogen": "eyes",
    "oktober": "October", "ongeveer": "about / approximately",
    "ontspannen": "to relax / relaxed", "ooit": "someday / ever",
    "opschieten": "to get along", "opschrijven": "to write down", "opwarmen": "to warm up",
    "oude": "old", "overal": "everywhere", "overkant": "across the street", "paar": "pair",
    "pakje": "package", "pakketje": "package", "pakketjes": "packages",
    "parkeren": "to park / parking", "pasta": "pasta", "pauzeruimte": "break room",
    "perfect": "perfect", "persoonlijker": "more personal",
    "persoonlijkheden": "personalities", "plannen": "to plan", "planten": "plants",
    "post": "mail / post", "postbus": "mailbox / PO box", "postkantoor": "post office",
    "postzegel": "stamp", "praatgraag": "talkative", "prima": "fine / okay",
    "probeert": "tries", "proefde": "tasted", "proeven": "to taste", "project": "project",
    "puinhoop": "mess", "raakt": "gets", "raken": "to get / become", "recepten": "recipes",
    "reizen": "to travel", "rest": "rest", "restaurants": "restaurants", "rijdt": "drives",
    "rit": "ride / trip", "rond": "around", "rustig": "quiet", "rustige": "quiet",
    "saus": "sauce", "schieten": "(part of get along)", "schilder": "paint",
    "schilderen": "to paint / painting", "schildert": "paints", "schoon": "clean",
    "schoonmaken": "to clean", "schrijft": "writes", "sneed": "cut / chopped",
    "snel": "quickly", "snijden": "to cut", "spaans": "Spanish", "speel": "play",
    "speelt": "plays", "spelen": "to play / playing", "spoedpost": "express mail",
    "sport": "sport", "sporten": "to exercise / play sports", "sportschool": "gym",
    "spraakzaam": "talkative", "steeds": "still", "stil": "quiet / silent",
    "stofzuigde": "vacuumed", "stofzuigen": "to vacuum", "stofzuigt": "vacuums",
    "studeer": "study", "stukjes": "pieces", "sturen": "to send", "stuurde": "sent",
    "stuurt": "sends", "supermarkt": "grocery store", "taak": "task / chore", "taart": "cake",
    "tablet": "tablet", "taken": "tasks", "team": "team", "tegen": "to / against",
    "tekstbericht": "text message", "telefoon": "phone", "tennis": "tennis",
    "tennist": "plays tennis", "terwijl": "while", "tijdens": "during",
    "toch": "still / anyway", "toe": "to / toward", "toen": "then / when", "toets": "test",
    "toevoegen": "to add", "traag": "slow", "tuurlijk": "of course", "uien": "onions",
    "uitgelaten": "walked (a pet)", "uitlaten": "to walk (a pet)", "uitnodigen": "to invite",
    "vaak": "often", "vaardigheden": "skills", "vaat": "dishes", "vak": "subject",
    "vergaderingen": "meetings", "verhuizen": "to move", "verjaardagscadeau": "birthday gift",
    "verjaardagspakketje": "birthday package", "verlegen": "shy", "verrassing": "surprise",
    "verrassingsfeestje": "surprise party", "verschillend": "different",
    "verschillende": "different", "versturen": "to send", "videobellen": "to video chat",
    "videogames": "video games", "vieren": "to celebrate", "vindt": "finds / thinks",
    "vingers": "fingers", "vis": "fish", "vloeistof": "liquid", "voetbal": "soccer",
    "voetballen": "to play soccer", "vogel": "bird", "volg": "take (a course)",
    "volgen": "to take / follow (a course)", "volgende": "next / following",
    "volgt": "takes / follows", "vond": "found", "vooral": "mostly / especially",
    "voordat": "before", "vriendelijk": "friendly", "vrienden": "friends", "vrije": "free",
    "vuilnis": "trash", "wandelt": "walks", "want": "because", "waren": "were",
    "wel": "indeed / though", "weleens": "ever / sometimes", "wensen": "to wish",
    "werkt": "works", "wifi": "wifi", "wilde": "wanted", "wilt": "want (formal)",
    "winkels": "shops", "wist": "knew", "wonen": "to live", "woog": "weighed", "yoga": "yoga",
    "zaterdagochtend": "Saturday morning", "zeggen": "to say", "zei": "said",
    "zelden": "rarely", "zelf": "herself / himself", "zette": "put", "zetten": "to put",
    "zie": "see", "zodra": "as soon as", "zoeken": "to look for", "zonder": "without",
    "zorgen": "worries / to worry", "zout": "salt", "zullen": "will", "zwembad": "pool",
    "zwemmen": "to swim / swimming", "zwemt": "swims",
}

NL_POS.update({
    # Units 43-48 (A1 continuation: colors through library), added 2026-07-12.
    "alledaagse": "adjective", "ambulance": "noun", "ander": "adjective",
    "arriveert": "verb", "balie": "noun", "band": "noun", "beiden": "pronoun",
    "belde": "verb", "belden": "verb", "beschrijf": "verb",
    "bevestigde": "verb", "bevestigen": "verb", "bewaarde": "verb",
    "bewaren": "verb", "bibliothecaris": "noun", "bibliotheekboek": "noun",
    "bibliotheekpas": "noun", "bibliotheken": "noun", "bijzonder": "adverb",
    "bijzondere": "adjective", "bladeren": "noun", "blijf": "verb",
    "bloeien": "verb", "bloemen": "noun", "bracht": "verb", "brand": "noun",
    "branden": "verb", "brandweer": "noun", "buitenlucht": "noun",
    "controle": "noun", "denken": "verb", "derde": "adjective",
    "details": "noun", "dienst": "noun", "dierenarts": "noun",
    "donkerblauw": "adjective", "donkerblauwe": "adjective",
    "eerder": "adverb", "eerst": "adverb", "erin": "adverb",
    "eventuele": "adjective", "exemplaar": "noun", "fel": "adjective",
    "fontein": "noun", "fornuis": "noun", "fotografieboek": "noun",
    "geel": "adjective", "gele": "adjective", "geleend": "verb",
    "gelijk": "noun", "gesprekken": "noun", "gevonden": "verb", "gevonden-voorwerpenloket": "noun",
    "goddank": "particle", "gewond": "adjective", "gewoon": "adverb",
    "haalde": "verb", "hele": "adjective", "herfst": "noun",
    "herinnerde": "verb", "hoofdingang": "noun", "inleverdatum": "noun",
    "inleveren": "verb", "jaarlijkse": "adjective", "keukenbrand": "noun",
    "kalme": "adjective", "keuze": "noun", "kies": "verb", "kiezen": "verb", "kleuren": "noun", "kookboek": "noun",
    "krijgen": "verb", "kunnen": "verb", "kwijt": "adjective",
    "kwijtgeraakt": "verb", "kwijtraakt": "verb", "kwijtraakte": "verb",
    "laatst": "adverb", "leende": "verb", "leent": "verb", "lenen": "verb",
    "lente": "noun", "letten": "verb", "leuke": "adjective",
    "leuker": "adjective", "leila's": "proper_noun", "lichtgroen": "adjective",
    "lievelingskleur": "noun", "lievelingsseizoen": "noun", "lift": "noun",
    "lijkt": "verb", "logisch": "adjective", "langs": "adverb",
    "maandagochtend": "noun", "max's": "proper_noun", "mededeling": "noun",
    "meekomen": "verb", "meeste": "adjective", "meteen": "adverb",
    "minder": "adverb", "mooi": "adjective", "nadat": "particle",
    "niemand": "pronoun", "noodgeval": "noun", "o": "noun", "oefenen": "verb",
    "oogt": "verb", "onze": "pronoun", "opgelucht": "adjective",
    "ophalen": "verb", "pan": "noun", "parkkantoor": "noun",
    "personeel": "noun", "politie": "noun", "portemonnee": "noun",
    "precies": "adverb", "presentatie": "noun", "professioneel": "adjective",
    "regen": "noun", "receptionist": "noun", "reserveren": "verb",
    "rood": "adjective", "rook": "noun", "rugzak": "noun", "ruik": "verb",
    "schiet": "verb", "seizoen": "noun", "sleutels": "noun", "slotte": "noun",
    "sneeuwt": "verb", "spullen": "noun", "tandarts": "noun", "tegelijk": "adverb",
    "ten": "preposition", "terugbrengen": "verb", "terugkreeg": "verb",
    "tijden": "noun", "trap": "noun", "tuinen": "noun", "uitkomt": "verb",
    "veiliger": "adjective", "veilig": "adjective", "verandert": "verb",
    "verhaal": "noun", "verhuisde": "verb", "verkleuren": "verb",
    "verlaat": "verb", "verloren": "adjective", "vertelde": "verb",
    "vertelt": "verb", "verzetten": "verb", "vloog": "verb",
    "voorjaar": "noun", "voortaan": "adverb", "voorwerp": "noun",
    "vraag": "verb", "vragen": "verb", "vriend": "noun", "vrij": "adjective",
    "vroeger": "adverb", "vul": "verb", "vuur": "noun", "waarop": "adverb",
    "wacht": "verb", "wachten": "verb", "wachtten": "verb", "weken": "noun",
    "winter": "noun", "wit": "adjective", "zeg": "verb", "zeiden": "verb",
    "zekerheid": "noun", "zenuwachtig": "adjective", "zet": "verb",
    "zit": "verb", "zodat": "particle", "zomer": "noun", "zon": "noun",
    "zorgde": "verb", "zwarte": "adjective",
})

NL_GLOSSES.update({
    # Units 43-48 (A1 continuation: colors through library), added 2026-07-12.
    "alledaagse": "everyday", "ambulance": "ambulance", "ander": "other",
    "arriveert": "arrives", "balie": "counter; desk", "band": "strap",
    "beiden": "both of them", "belde": "called", "belden": "called",
    "beschrijf": "describe", "bevestigde": "confirmed", "bevestigen": "to confirm",
    "bewaarde": "kept; saved", "bewaren": "to keep; to save",
    "bibliothecaris": "librarian", "bibliotheekboek": "library book",
    "bibliotheekpas": "library card", "bibliotheken": "libraries",
    "bijzonder": "especially; particularly", "bijzondere": "special",
    "bladeren": "leaves", "blijf": "stay", "bloeien": "to bloom",
    "bloemen": "flowers", "bracht": "brought", "brand": "fire",
    "branden": "to burn", "brandweer": "fire department",
    "buitenlucht": "outdoor air; outdoors", "controle": "checkup",
    "denken": "to think", "derde": "third", "details": "details",
    "dienst": "service", "dierenarts": "veterinarian",
    "donkerblauw": "dark blue", "donkerblauwe": "dark blue",
    "eerder": "earlier; before", "eerst": "first", "erin": "in it",
    "eventuele": "possible; any", "exemplaar": "one; copy",
    "fel": "bright", "fontein": "fountain", "fornuis": "stove",
    "fotografieboek": "photography book", "geel": "yellow", "gele": "yellow",
    "geleend": "borrowed", "gelijk": "right; correct", "gesprekken": "conversations", "gevonden": "found",
    "gevonden-voorwerpenloket": "lost-and-found desk", "goddank": "thank goodness",
    "gewond": "hurt; injured", "gewoon": "just; ordinary", "haalde": "picked up",
    "hele": "whole", "herfst": "fall; autumn", "herinnerde": "reminded",
    "hoofdingang": "main entrance", "inleverdatum": "return due date",
    "inleveren": "to return; hand in", "jaarlijkse": "yearly",
    "keukenbrand": "kitchen fire", "kalme": "calm", "keuze": "choice", "kies": "choose",
    "kiezen": "to choose", "kleuren": "colors", "kookboek": "cookbook", "krijgen": "to get",
    "kunnen": "can; to be able to", "kwijt": "lost", "kwijtgeraakt": "lost",
    "kwijtraakt": "loses", "kwijtraakte": "lost", "laatst": "last",
    "leende": "borrowed", "leent": "borrows", "lenen": "to borrow",
    "lente": "spring", "letten": "to pay attention", "leuke": "nice; fun",
    "leuker": "more fun", "leila's": "Leila's", "lichtgroen": "light green",
    "lievelingskleur": "favorite color", "lievelingsseizoen": "favorite season",
    "lift": "elevator", "lijkt": "seems", "logisch": "logical",
    "langs": "by; along", "maandagochtend": "Monday morning", "max's": "Max's",
    "mededeling": "notice; announcement", "meekomen": "to come along",
    "meeste": "most", "meteen": "immediately", "minder": "less",
    "mooi": "beautiful; nice", "nadat": "after", "niemand": "nobody",
    "noodgeval": "emergency", "o": "oh", "oefenen": "to practice",
    "oogt": "looks; appears", "onze": "our", "opgelucht": "relieved",
    "ophalen": "to pick up", "pan": "pan", "parkkantoor": "park office",
    "personeel": "staff", "politie": "police", "portemonnee": "wallet",
    "precies": "exactly", "presentatie": "presentation",
    "professioneel": "professional", "regen": "rain", "receptionist": "receptionist",
    "reserveren": "to reserve; to book", "rood": "red", "rook": "smoke",
    "rugzak": "backpack", "ruik": "smell", "schiet": "hurry; shoot",
    "seizoen": "season", "sleutels": "keys", "slotte": "end (ten slotte: finally)",
    "sneeuwt": "snows", "spullen": "things; belongings",
    "tandarts": "dentist", "tegelijk": "at the same time", "ten": "at; to",
    "terugbrengen": "to bring back; return", "terugkreeg": "got back",
    "tijden": "times", "trap": "stairs", "tuinen": "gardens",
    "uitkomt": "suits; works out", "veiliger": "safer", "veilig": "safe",
    "verandert": "changes", "verhaal": "story", "verhuisde": "moved",
    "verkleuren": "to change color", "verlaat": "leave", "verloren": "lost",
    "vertelde": "told", "vertelt": "tells", "verzetten": "to reschedule",
    "vloog": "flew", "voorjaar": "spring", "voortaan": "from now on",
    "voorwerp": "object; item", "vraag": "ask", "vragen": "to ask",
    "vriend": "friend", "vrij": "free; available", "vroeger": "before; earlier",
    "vul": "fill in", "vuur": "fire", "waarop": "on which; when",
    "wacht": "wait", "wachten": "to wait", "wachtten": "waited",
    "weken": "weeks", "winter": "winter", "wit": "white", "zeg": "say",
    "zeiden": "said", "zekerheid": "certainty; safety", "zenuwachtig": "nervous",
    "zet": "put; turn", "zit": "is sitting; is located", "zodat": "so that",
    "zomer": "summer", "zon": "sun", "zorgde": "made sure; cared",
    "zwarte": "black",
})


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


def _classify_unit_files(unit_files, level):
    # FRESH dicts per level/course -- Lexeme uniqueness is scoped by
    # `Lexeme.course_id`, and "Engels A1"/"Engels A2" are two entirely
    # separate course rows (see UNIT_FILES_A2's comment), so a token
    # re-taught in A2 needs its own A2-scoped Lexeme row rather than
    # silently reusing A1's.
    en_specs: dict[str, dict] = {}
    nl_specs: dict[str, dict] = {}
    for unit_order, (realization_path, overlay_path) in enumerate(unit_files, 1):
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
                            "level": level,
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
                            "level": level,
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


def iter_specs():
    yield from _classify_unit_files(UNIT_FILES, "a1")
    yield from _classify_unit_files(UNIT_FILES_A2, "a2")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    specs = list(iter_specs())
    if args.dry_run:
        en_count = sum(spec["language_code"] == "en" for spec in specs)
        nl_count = sum(spec["language_code"] == "nl" for spec in specs)
        a1_count = sum(spec["level"] == "a1" for spec in specs)
        a2_count = sum(spec["level"] == "a2" for spec in specs)
        print(f"Lexeme backfill dry run: {en_count} en, {nl_count} nl ({a1_count} a1, {a2_count} a2).")
        return 0

    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        courses_by_level = {}
        for level, title in (("a1", "Engels A1"), ("a2", "Engels A2")):
            needed = any(spec["level"] == level for spec in specs)
            course = db.scalar(
                select(Course).where(
                    Course.source_language == "nl",
                    Course.target_language == "en",
                    Course.title == title,
                )
            )
            if course is None:
                if needed:
                    print(f"ERROR: nl-en {title!r} course must be imported first", file=sys.stderr)
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
        created = 0
        updated = 0
        for spec in specs:
            level = spec.pop("level")
            course = courses_by_level[level]
            lesson = lessons_by_level[level].get(
                (spec.pop("unit_order"), spec.pop("lesson_order"))
            )
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
