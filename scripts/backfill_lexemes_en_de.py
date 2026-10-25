#!/usr/bin/env python3
"""Idempotently backfill en-de (German target) lexemes for the "German A1"
course, so en-de practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: en->X backfill, German. All plumbing lives in
scripts/_target_lexeme_backfill_common.py (see its docstring for the tag
scheme); this file is data only: one hand-written English gloss and one part
of speech per citation form.

Scope: A1 (the "en-de" manifest group, units 01-24), A2 (the "en-de-a2"
group, units 25-34; session 11) and B1 (the "en-de-b1" group, units 35-53;
session 12). B2+ is not classified yet; extend LEVELS and the tables below
together. A1, A2 and B1 are separate courses, so each re-glosses every token
it introduces, function words included. B1_GLOSS_OVERRIDES holds the few
tokens whose B1 sense differs from the A1/A2 entry.

The B1 course must be imported first: the runner stops with a clear error
("course must be imported first") when the en-de-b1 course row is missing.

Glossing rules followed here (PRACTICE_PACK_RECIPE.md §0.1, §6.6):
* the gloss is the sense the unit actually teaches at first sight; a token
  with two taught senses gets both ("a; b"),
* inflected forms say who they belong to ("you have (formal)", "I take"),
  so a bare-word translation prompt names one form,
* no German word and no German infinitive appears in any gloss.

German case is meaningful, so normalize() does NOT lowercase-fold. Nouns
keep their capital. Only the sentence-initial capitals of non-nouns are
mapped to their citation form, through the explicit CITATION_FORMS table.

Deliberate decisions (capitalized token that is more than one thing):
* "Sie" (formal you) and "sie" (she; it; they) stay two separate tokens:
  unit01 teaches "Sie" as the formal pronoun, unit05 teaches lowercase "sie".
* "Morgen" (noun, morning, from "Guten Morgen") and "morgen" (adverb,
  tomorrow, unit12) stay two separate tokens.
* "Treffen" (noun, meeting) and "treffen" (verb, meet) stay two separate
  tokens; the genitive "Treffens" is mapped to "Treffen".
* "Zahlen" (unit24, "Zahlen Sie bar oder mit Karte?") is the sentence-initial
  VERB, not the noun "numbers": mapped to "zahlen".
* "Arbeiten" (unit11, "Arbeiten Sie heute?") is the sentence-initial verb:
  mapped to "arbeiten".
* "Essen" (unit07, "Zum Hier-Essen") and "Mitnehmen" are nominalised verbs
  taught as nouns, so they keep their capital.
* "Blau" (unit21, "in Blau") is the same word as adjective "blau": mapped.
* "Cafe" (unit11 spelling) is the same word as "Café" (unit07): mapped.
* "Annas" (possessive) is mapped to the proper noun "Anna".
* "Mögen" / "Nehmen" / "Gehen" / "Halten" / "Biegen" / "Haben" / "Brauchen" /
  "Sprechen" / "Trinken" / "Machen" / "Können" / "Kann" are sentence-initial
  verbs, mapped to their lowercase form.

Run (after the en-de course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_de.py

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

LANG = "de"
LEVELS = {"a1": "en-de", "a2": "en-de-a2", "b1": "en-de-b1"}

PROPER_NOUNS = {
    "Anna", "Felix", "Berlin", "Deutschland", "England", "Frankreich",
    "Italien", "Spanien", "Russland",
}

# Sentence-initial (or otherwise capitalised) form -> citation form.
# Anything not listed here is its own citation form (nouns, proper nouns,
# and lowercase words).
CITATION_FORMS: dict[str, str] = {
    # unit01
    "Hallo": "hallo", "Guten": "guten", "Tschüss": "tschüss", "Auf": "auf",
    "Bis": "bis", "Gute": "gute", "Wie": "wie", "Gut": "gut", "Sehr": "sehr",
    "Und": "und", "Bitte": "bitte", "Kein": "kein", "Gern": "gern",
    # unit02
    "Ich": "ich", "Freut": "freut", "Ganz": "ganz", "Du": "du",
    "Woher": "woher",
    # unit04
    "Welcher": "welcher", "Der": "der", "Man": "man", "Wann": "wann",
    "Mein": "mein",
    # unit05
    "Es": "es",
    # unit06
    "Wer": "wer", "Das": "das", "Er": "er", "Haben": "haben", "Nein": "nein",
    "Ist": "ist", "Ja": "ja",
    # unit07
    "Hier": "hier", "Zum": "zum", "Was": "was", "Sonst": "sonst",
    # unit08
    "Kann": "kann", "Natürlich": "natürlich",
    # unit09
    "Die": "die", "Wo": "wo",
    # unit10
    "Biegen": "biegen", "Gehen": "gehen", "Halten": "halten",
    "Nehmen": "nehmen",
    # unit11
    "Dann": "dann", "Arbeiten": "arbeiten", "Annas": "Anna",
    "Cafe": "Café",
    # unit12, unit14, unit17, unit19, unit20, unit21
    "Mögen": "mögen", "Brauchen": "brauchen", "Trinken": "trinken",
    "Machen": "machen", "Mir": "mir", "Meine": "meine", "Wir": "wir",
    "Blau": "blau",
    # unit23, unit24
    "Können": "können", "Sprechen": "sprechen", "Treffens": "Treffen",
    "Mit": "mit", "Zahlen": "zahlen",
    # sign text
    "Geschlossen": "geschlossen",
    # A2 (units 25-34)
    "Welche": "welche", "Bekomme": "bekomme", "Gibt": "gibt",
    "Kommen": "kommen", "In": "in", "Am": "am", "Leider": "leider",
    "Vielen": "vielen",
    # B1 (units 35-53): sentence-initial forms of non-nouns, plus the
    # dictation spelling "tag" of the noun Tag
    "Letzte": "letzte", "Konnten": "konnten", "Könnten": "könnten",
    "Wenn": "wenn", "Aber": "aber", "Müssen": "müssen", "Während": "während",
    "Als": "als", "Wirklich": "wirklich", "Vielleicht": "vielleicht",
    "Obwohl": "obwohl", "Zwar": "zwar", "Deshalb": "deshalb",
    "Außerdem": "außerdem", "Zusammenfassend": "zusammenfassend",
    "Einverstanden": "einverstanden", "Warum": "warum", "Wofür": "wofür",
    "An": "an", "Danke": "danke", "tag": "Tag",
}


def normalize(token: str) -> str:
    return CITATION_FORMS.get(token, token)


GLOSSES: dict[str, str] = {
    # unit01 greetings
    "hallo": "hello", "guten": "good (in a greeting)", "Morgen": "morning",
    "Tag": "day", "Abend": "evening", "tschüss": "bye",
    "auf": "on; to (in the formal goodbye); up (part of the verb meaning get up)",
    "Wiedersehen": "meeting again", "bis": "until",
    "bald": "soon", "später": "later", "gute": "good (in a greeting)",
    "Nacht": "night", "Sie": "you (formal)", "du": "you (informal)",
    "wie": "how", "geht": "goes; is going (as in how you are doing)",
    "es": "it", "Ihnen": "to you (formal)", "geht's": "it goes (in how's it going?)",
    "gut": "good; well", "danke": "thank you; thanks", "sehr": "very",
    "und": "and", "dir": "to you (informal)", "bitte": "please; you're welcome",
    "Entschuldigung": "excuse me; sorry", "kein": "no; not a",
    "Problem": "problem", "gern": "gladly; with pleasure",
    "geschehen": "happened; done",
    # unit02 introductions
    "heißen": "are called (formal you)", "ich": "I", "heiße": "I am called",
    "Anna": "Anna", "heißt": "is called; you are called (informal)",
    "Felix": "Felix", "freut": "pleases; delights", "mich": "me",
    "ganz": "quite; entirely", "meinerseits": "on my part", "bin": "I am",
    "bist": "you are (informal)", "Deutschland": "Germany",
    "England": "England", "Frankreich": "France", "Italien": "Italy",
    "Spanien": "Spain", "Russland": "Russia", "woher": "from where",
    "kommen": "come; you come (formal)", "komme": "I come",
    "aus": "from; out of", "kommst": "you come (informal)", "Name": "name",
    "Land": "country",
    # unit03 numbers
    "null": "zero", "eins": "one", "zwei": "two", "drei": "three",
    "vier": "four", "fünf": "five", "sechs": "six", "sieben": "seven",
    "acht": "eight", "neun": "nine", "zehn": "ten", "elf": "eleven",
    "zwölf": "twelve", "dreizehn": "thirteen", "vierzehn": "fourteen",
    "fünfzehn": "fifteen", "sechzehn": "sixteen", "siebzehn": "seventeen",
    "achtzehn": "eighteen", "neunzehn": "nineteen", "zwanzig": "twenty",
    "dreißig": "thirty", "vierzig": "forty", "fünfzig": "fifty",
    "sechzig": "sixty", "siebzig": "seventy", "achtzig": "eighty",
    "neunzig": "ninety", "hundert": "one hundred",
    "einundzwanzig": "twenty-one", "zweiunddreißig": "thirty-two",
    "alt": "old", "sind": "are (formal you; we; they)",
    "achtundzwanzig": "twenty-eight", "Jahre": "years",
    "wenn": "if; when", "auch": "also; too", "fragen": "to ask", "darf": "may; am allowed to",
    "einunddreißig": "thirty-one",
    # unit04 dates
    "Montag": "Monday", "Dienstag": "Tuesday", "Mittwoch": "Wednesday",
    "Donnerstag": "Thursday", "Freitag": "Friday", "Samstag": "Saturday",
    "Sonntag": "Sunday", "welcher": "which (masc.)", "ist": "is",
    "heute": "today", "Januar": "January", "März": "March", "Mai": "May",
    "Juli": "July", "September": "September", "Dezember": "December",
    "Monat": "month", "der": "the (masc. nominative; fem. dative)",
    "Wievielte": "which date; what number in a series",
    "siebte": "seventh", "man": "one; you (people in general)",
    "kann": "can", "als": "as", "schreiben": "to write", "wann": "when",
    "haben": "have; you have (formal)", "Geburtstag": "birthday",
    "mein": "my (before a masc. or neuter noun)", "dritte": "third",
    "öffnet": "opens", "wieder": "again", "die": "the (fem. or plural)",
    "Bibliothek": "library", "am": "on the; at the",
    "den": "the (masc. accusative)", "neunten": "ninth",
    "geschlossen": "closed",
    # unit05 time
    "spät": "late", "Uhr": "o'clock; clock", "halb": "half",
    "Viertel": "quarter", "nach": "after; past", "vor": "before; to (in telling time)",
    "Mittag": "noon", "Nachmittag": "afternoon", "Mitternacht": "midnight",
    "Laden": "shop; store", "um": "at (a time); around",
    "morgens": "in the morning", "schließt": "closes",
    "sie": "she; it; they", "dann": "then",
    "Öffnungszeiten": "opening hours",
    # unit06 family
    "Vater": "father", "Mutter": "mother", "Bruder": "brother",
    "Schwester": "sister", "Eltern": "parents", "Geschwister": "siblings",
    "Großmutter": "grandmother", "Großvater": "grandfather", "Tante": "aunt",
    "Onkel": "uncle", "Cousin": "cousin (male)", "Cousine": "cousin (female)",
    "meine": "my (before a fem. noun or plural)",
    "sein": "his (before a masc. or neuter noun)",
    "Ihr": "your (formal, before a masc. or neuter noun)",
    "Ihre": "your (formal, before a fem. noun or plural)",
    "wer": "who", "das": "this; that; the (neuter)", "er": "he",
    "habe": "I have", "Schwestern": "sisters", "nein": "no",
    "keine": "no; not any (fem. or plural)", "Einzelkind": "only child",
    "Foto": "photo", "Familie": "family", "ja": "yes",
    "Lehrerin": "teacher (female)", "Brüder": "brothers", "nur": "only",
    "eine": "a; an (fem.); one (fem.)",
    # unit07 food
    "Kaffee": "coffee", "Tee": "tea", "Wasser": "water", "Brot": "bread",
    "Suppe": "soup", "Salat": "salad", "Sandwich": "sandwich",
    "möchte": "I would like", "einen": "a; an (masc. accusative)",
    "ein": "a; an (masc. or neuter)", "sonst": "otherwise; else",
    "noch": "still; more", "etwas": "something; anything",
    "alles": "everything; all", "zum": "to the; for the (a contraction)",
    "hier": "here", "Essen": "eating; food", "oder": "or",
    "Mitnehmen": "taking away; takeaway", "Speisekarte": "menu",
    "Preis": "price", "Café": "cafe", "3": "three (as a digit)",
    "2": "two (as a digit)", "1": "one (as a digit)",
    "4": "four (as a digit)", "5": "five (as a digit)",
    "6": "six (as a digit)", "was": "what", "möchten": "would like (formal you)",
    "macht": "makes; comes to (a total)", "Euro": "euro",
    # unit08 shopping
    "Pfund": "pound (weight)", "Äpfel": "apples", "Dutzend": "dozen",
    "Eier": "eggs", "Flasche": "bottle", "Tüte": "bag", "Reis": "rice",
    "Kilo": "kilo", "Tomaten": "tomatoes", "kosten": "cost (plural)",
    "frisch": "fresh", "pro": "per", "Markt": "market",
    "Preisschild": "price tag", "natürlich": "of course; naturally",
    # unit09 places
    "Bank": "bank", "Krankenhaus": "hospital", "Apotheke": "pharmacy",
    "Park": "park", "Restaurant": "restaurant", "neben": "next to",
    "dem": "the (masc. or neuter dative)", "gegenüber": "across from; opposite",
    "vom": "from the; of the (a contraction)", "zwischen": "between",
    "hinter": "behind", "wo": "where", "weit": "far", "von": "from; of",
    "nicht": "not",
    # unit10 directions
    "biegen": "turn (formal command)", "links": "left", "ab": "off (completes a verb meaning to turn)",
    "rechts": "right", "gehen": "go; we go; you go (formal)",
    "geradeaus": "straight ahead", "halten": "stop (formal command)",
    "an": "on (completes a verb meaning to stop)", "Ecke": "corner",
    "zur": "to the (fem.)", "Minuten": "minutes", "können": "can; you can (formal)",
    "verfehlen": "to miss", "nehmen": "take; you take (formal)",
    "erste": "first", "Straße": "street", "zweite": "second",
    "Wegbeschreibung": "directions", "abbiegen": "to turn off (a road)",
    # unit11 daily routine
    "aufstehen": "to get up", "stehe": "I stand; I get up",
    "frühstücken": "to have breakfast", "arbeiten": "to work",
    "arbeite": "I work", "lernen": "to learn", "lerne": "I learn",
    "Deutsch": "German (language)", "schlafen": "to sleep",
    "gehe": "I go", "frühstücke": "I have breakfast",
    "stehen": "stand; you get up (formal)", "steht": "stands; gets up",
    "frühstückt": "has breakfast (he/she/it)", "arbeitet": "works (he/she/it)",
    "im": "in the", "lernt": "learns (he/she/it)",
    # unit12 plans
    "morgen": "tomorrow", "Zeit": "time", "wir": "we", "ins": "into the; to the",
    "Museum": "museum", "leider": "unfortunately",
    "viel": "much; many", "Nachricht": "message",
    # unit13 past
    "gestern": "yesterday", "gemacht": "done; made", "gekauft": "bought",
    "gegessen": "eaten", "gegangen": "gone", "war": "was",
    # unit14 preferences
    "mögen": "like (formal you)", "mag": "I like; he/she likes",
    "lieber": "rather; preferably", "trinke": "I drink", "nehme": "I take",
    "aber": "but", "trinkt": "drinks (he/she/it)", "nimmt": "takes (he/she/it)",
    # unit15 comparisons
    "billiger": "cheaper", "teurer": "more expensive", "kälter": "colder",
    "näher": "nearer; closer", "kostet": "costs",
    # unit16 travel
    "Bahnhof": "train station", "Gleis": "platform; track", "Zug": "train",
    "Fahrkarte": "ticket", "Berlin": "Berlin", "Abfahrt": "departure",
    "einfach": "one-way; simple", "hin": "there (toward a place)",
    "zurück": "back", "fährt": "travels; departs (a vehicle)", "Art": "type; kind",
    # unit17 health
    "Kopfschmerzen": "headache", "Bauchschmerzen": "stomachache",
    "Hals": "throat; neck", "Kopf": "head", "tut": "does (part of the phrase meaning hurts)",
    "weh": "sore; painful", "mir": "to me", "schlecht": "bad; sick",
    "brauchen": "need; you need (formal)", "Hilfe": "help",
    "brauche": "I need", "Pause": "break; pause", "trinken": "drink (formal command)",
    "machen": "do; make", "hat": "has (he/she/it)", "braucht": "needs (he/she/it)",
    # unit18 work
    "Beruf": "job; profession", "Ingenieur": "engineer",
    "Kellnerin": "waitress; server", "beruflich": "for work; professionally",
    "Büro": "office", "bringe": "I bring", "bringt": "brings (he/she/it)",
    # unit19 housing
    "Wohnung": "apartment; flat", "klein": "small", "Zimmer": "room",
    "Küche": "kitchen", "Bad": "bathroom", "hell": "bright",
    "Wohnzimmer": "living room", "Tisch": "table", "Stuhl": "chair",
    "gibt": "gives (in a fixed phrase: there is)", "in": "in",
    # unit20 weather
    "Wetter": "weather", "sonnig": "sunny", "kalt": "cold", "warm": "warm",
    "regnet": "rains; is raining", "Idee": "idea",
    # unit21 clothing
    "Kleidung": "clothing", "kaufe": "I buy", "Hemd": "shirt",
    "Hose": "pants; trousers", "Jacke": "jacket", "suche": "I look for",
    "Größe": "size", "blau": "blue", "rot": "red", "passt": "fits",
    "M": "M (medium size)", "Farbe": "color", "kaufen": "to buy",
    # unit22 feelings
    "Gefühl": "feeling; emotion", "froh": "glad; happy", "müde": "tired",
    "traurig": "sad", "fühlen": "feel (formal you)", "sich": "yourself (formal); themselves",
    "weil": "because", "frei": "free; off",
    # unit23 phone
    "Telefon": "telephone; phone", "anrufen": "to call by phone",
    "rufe": "I call", "wiederholen": "to repeat", "sprechen": "speak (formal command)",
    "langsam": "slowly; slow", "wegen": "because of; about",
    "des": "of the (masc. or neuter genitive)", "Treffen": "meeting",
    "schreibe": "I write", "treffen": "we meet; to meet", "uns": "us; ourselves; each other",
    # unit24 money
    "Geld": "money", "bezahlen": "to pay", "bar": "in cash", "Karte": "card",
    "mit": "with; by (means of)", "Betrag": "amount", "zahlen": "pay; to pay",
    "Quittung": "receipt", "Zahlung": "payment", "zahlt": "pays (he/she/it)",
    # b1 (units 35-53). New tokens only; tokens already glossed above keep
    # their A1/A2 entry unless B1_GLOSS_OVERRIDES says the unit teaches
    # another sense.
    "Frau": "Mrs.; Ms.; woman", "Klein": "Klein (a surname)",
    "Bürgeramt": "registration office; citizens' office",
    "sagen": "to say; to tell", "ob": "whether; if", "letzte": "last",
    "konnte": "could; was able to (I, he, she)",
    "konnten": "could; were able to (formal you; they)",
    "schon": "already", "Nummer": "number", "geben": "to give; give (formal you)",
    "könnte": "could (hypothetical; I, he, she)",
    "Formular": "form (to fill in)", "fehlt": "is missing",
    "müssen": "must; have to (we; they; formal you)",
    "dürfen": "may; are allowed to (we; they; formal you)",
    "ohne": "without", "Unterschrift": "signature",
    "hätte": "would have; had (hypothetical; I, he, she)",
    "früher": "earlier; sooner", "sollen": "should; ought to (infinitive)",
    "fertig": "finished; ready", "stimmt": "is correct; is right",
    "unterschreibe": "I sign", "jetzt": "now", "helfen": "to help",
    "würde": "would (I, he, she)", "dringend": "urgent",
    "wäre": "would be (hypothetical; I, he, she)", "sofort": "immediately",
    "stimme": "I agree", "Homeoffice": "working from home",
    "besser": "better", "spart": "saves (time or money)",
    "denn": "because (giving a reason in a main clause)",
    "Teamarbeit": "teamwork", "einfacher": "easier; simpler",
    "denken": "think; you think (formal)", "über": "about; over",
    "Videoanrufe": "video calls", "praktisch": "practical",
    "Projekt": "project", "zuständig": "responsible (for)", "Planung": "planning",
    "Bericht": "report", "wofür": "for what; what for",
    "diese": "this (before a fem. noun)", "Stand": "status; state of progress",
    "beim": "at the; with the (a contraction)", "während": "while; during",
    "arbeitete": "worked; was working (I, he, she)", "klingelte": "rang",
    "kam": "came (I, he, she)", "beschäftigt": "busy", "sagte": "said (I, he, she)",
    "plötzlich": "suddenly", "gesagt": "said (past participle)",
    "Freundin": "friend (female); girlfriend", "bestimmt": "surely; certainly",
    "regnen": "to rain", "bleibe": "I stay", "bleiben": "to stay",
    "Hause": "home (as in at home)", "wandern": "to hike", "allein": "alone",
    "immer": "always", "hatte": "had (I, he, she)",
    "vorbei": "by; over (part of the verb meaning to drop by)",
    "vorbeikommen": "to drop by", "wirklich": "really", "schön": "nice; beautiful",
    "fragte": "asked (I, he, she)", "gefragt": "asked (past participle)",
    "Kollegin": "colleague (female)", "geantwortet": "answered (past participle)",
    "antworten": "to answer", "sparen": "to save (money)", "Reise": "trip; journey",
    "spricht": "speaks (he, she)", "damit": "so that", "ihn": "him; it (masc. accusative)",
    "versteht": "understands (he, she)", "verstehen": "to understand",
    "schreibt": "writes (he, she)", "vergisst": "forgets (he, she)",
    "vergessen": "to forget", "warum": "why", "spreche": "I speak",
    "Stress": "stress", "bei": "at; with (as in at work)", "Arbeit": "work",
    "Ihrer": "your (formal, before a fem. noun after a preposition)",
    "schlafe": "I sleep", "abends": "in the evening",
    "keinen": "no; not a (masc. accusative)", "sollten": "should (we; they; formal you)",
    "öfter": "more often", "Ihrem": "your (formal, before a masc. noun after a preposition)",
    "Chef": "boss", "schwierig": "difficult", "sollte": "should (I, he, she)",
    "versuchen": "to try", "guter": "good (before a masc. noun)", "Rat": "advice",
    "danken": "to thank", "funktionieren": "to work; to function",
    "angerufen": "called (past participle)", "so": "so; as", "schnell": "fast; quick",
    "möglich": "possible", "reparieren": "to repair", "König": "König (a surname)",
    "leid": "sorry (in the phrase meaning I am sorry)", "passiert": "happened",
    "schicke": "I send", "schicken": "to send", "Techniker": "technician",
    "schnelle": "quick (before a fem. noun)", "melden": "to report; to notify",
    "lange": "for a long time; long", "warten": "to wait",
    "wünschte": "wished (in: I wish I had...)",
    "kaputtgegangen": "broken (past participle, of breaking down)",
    "repariert": "repaired (past participle)",
    "nächste": "next (after an article)", "Mal": "time (an occasion)",
    "Sommer": "summer", "ziehen": "to move (to a new place)", "werde": "I will",
    "nächstes": "next (without an article)", "Jahr": "year",
    "eigenes": "own (before a neuter noun)", "wahrscheinlich": "probably",
    "Job": "job", "wechseln": "to change", "vielleicht": "perhaps; maybe",
    "ziehe": "I move (to a new place)", "umziehen": "to move house",
    "spannend": "exciting", "beide": "both", "Hauptpunkt": "main point",
    "nächster": "next (before a fem. noun after a preposition)",
    "neue": "new (before a fem. or plural noun)", "zusammenfassend": "in summary",
    "lässt": "lets (in the phrase meaning it can be said)",
    "Frühstück": "breakfast", "anbietet": "offers", "außerdem": "also; besides",
    "erwähnt": "mentions", "Detail": "detail", "gerade": "just now; right now",
    "unser": "our (before a masc. or neuter noun)", "gelesen": "read (past participle)",
    "wissen": "to know (a fact)", "obwohl": "although", "riskant": "risky",
    "Filiale": "branch (of a business)", "zwar": "admittedly (it is true that...)",
    "Chance": "chance; opportunity", "groß": "big; great", "Bedenken": "doubts; concerns",
    "Ende": "end", "deshalb": "therefore; that is why",
    "genauen": "precise; exact (before a masc. accusative noun)", "Plan": "plan",
    "mehr": "more", "kochen": "to cook", "reich": "rich",
    "zweites": "second (before a neuter noun)", "vorschlagen": "to suggest",
    "schließen": "to close", "klingt": "sounds", "klingen": "to sound",
    "neues": "new (before a neuter noun)", "Rezept": "recipe",
    "ausprobieren": "to try out", "toll": "great; wonderful",
    "könnten": "could (we; they; formal you)", "Meeting": "meeting (a business meeting)",
    "14": "fourteen", "15": "fifteen", "verschieben": "to postpone; to move to another time",
    "Zeitplan": "schedule; timetable", "besprechen": "to discuss",
    "passen": "to fit; to suit", "einverstanden": "in agreement; agreed",
    "geehrte": "dear (in a formal letter greeting)", "Vogel": "Vogel (a surname)",
    "Kunde": "customer (male)", "bestellt": "orders", "bestellen": "to order",
    "Herr": "Mr.; gentleman", "Braun": "Braun (a surname)", "beliebt": "popular",
    "sitzen": "to sit; we sit", "reserviert": "reserved", "Mann": "man",
    "Fenster": "window", "sitzt": "sits", "Lieblingsplatz": "favorite spot",
}

# A2 (session 11): units 25-34, glosses for the tokens A1 did not teach.
GLOSSES.update({
    # unit25 Behördengang
    "Termin": "appointment", "Anmeldung": "registration (with the authorities)",
    "für": "for", "Pass": "passport", "Meldeformular": "registration form",
    "bringen": "bring (formal command)", "mitbringen": "to bring along",
    "Ihren": "your (formal, before a masc. noun used as an object)",
    "Weber": "Weber (a surname)", "Adresse": "address",
    "Lindenstraße": "Linden Street (a street name)",
    "8": "the digit 8 (a house number)", "wohne": "I live (reside)",
    "wohnen": "to live (reside)", "muss": "must; have to (I, he, she, it)",
    "abgeben": "to hand in; to submit", "bestätigen": "to confirm",
    "vielen": "many; much (in a thank-you)", "Dank": "thanks",
    # unit26 Meinungen
    "finde": "I find; I consider (giving an opinion)", "Meinung": "opinion", "ruhig": "quiet; calm",
    "interessant": "interesting", "teuer": "expensive",
    "denke": "I think", "dass": "that (introducing a clause)",
    "Kurs": "course; class", "anderer": "different; other (in 'of a different opinion')",
    "verstehe": "I understand",
    # unit27 Bankkonto
    "Bankkonto": "bank account", "Konto": "account",
    "eröffnen": "to open (an account)", "Telefonnummer": "phone number",
    "Kosten": "costs; expenses", "Bankkarte": "bank card",
    "Online-Banking": "online banking", "gehört": "belongs; is part of",
    "monatlich": "monthly; per month", "welche": "which (fem. or plural)",
    "Unterlagen": "documents; papers", "bekomme": "I get; I receive",
    "monatliche": "monthly (before a plural noun)",
    # unit28 Beim Arzt
    "Arzt": "doctor; physician", "Symptom": "symptom",
    "Halsschmerzen": "sore throat", "seit": "since; for (a length of time up to now)",
    "Tagen": "days (dative plural, as in for three days)",
    "stark": "strong; severe", "starke": "strong; severe (before a plural noun)",
    "wiederkommen": "to come back", "Fieber": "fever",
    # unit29 Wohnungsproblem
    "meiner": "my (before a fem. noun after 'in')", "Heizung": "heating",
    "funktioniert": "works; functions", "Reparatur": "repair",
    "Handwerker": "tradesman; repair worker", "kommt": "comes; is coming",
    "jemand": "someone; anyone",
    # unit30 Vorstellungsgespräch
    "Vorstellungsgespräch": "job interview", "Erfahrung": "experience",
    "Bewerbung": "job application", "Stärke": "strength", "Team": "team",
    "verfügbar": "available", "Teilzeit": "part-time work",
    "Stelle": "job; position", "Aufgaben": "tasks; duties",
    "gehören": "belong", "zu": "to; too (before 'much')",
    "Einladung": "invitation", "freundlichen": "friendly (after 'with', before a plural noun)",
    "Grüßen": "greetings (plural)",
    # unit31 Reisechaos
    "Verspätung": "delay", "fällt": "falls; is cancelled (with the particle 'out')",
    "Alternative": "alternative; option", "alternative": "alternative (before a fem. noun)",
    "Bus": "bus", "Verbindung": "service; transport link",
    "spätere": "later (before a fem. noun)",
    "Anschluss": "connecting train or bus (the next one you change to)",
    "verpasse": "I miss (a train or bus)", "meinen": "my (before a masc. noun used as an object)",
    # unit32 Online-Alltag
    "online": "online", "Nachrichten": "news", "lese": "I read",
    "jeden": "every (before a masc. noun used as an object)",
    "Smartphone": "smartphone", "benutze": "I use",
    "soziale": "social (before a plural noun)", "Medien": "media",
    "nützlich": "useful", "manchmal": "sometimes",
    # unit33 Wochenplan
    "Vormittag": "late morning; the time before noon",
    "vormittags": "in the late mornings", "unter": "under; during (a week)",
    "Woche": "week", "Wochenende": "weekend", "zuerst": "first; at first",
    "danach": "afterwards", "tun": "to do", "treffe": "I meet",
    # unit34 Beschwerde
    "Artikel": "item; article", "kaputt": "broken",
    "Kassenbon": "till receipt (from a shop)", "umtauschen": "to exchange (a purchase)",
    "Ersatz": "replacement", "Reklamation": "complaint about a purchase",
    "zurückbekommen": "to get back",
})

POS_SETS = {
    "proper_noun": PROPER_NOUNS,
    "symbol": split_words("1 2 3 4 5 6 M"),
    "pronoun": split_words(
        "Sie du ich es Ihnen dir mich ihm sie er wer wir mir uns sich was "
        "etwas alles man das mein meine sein Ihr Ihre keine"
    ),
    "preposition": split_words(
        "auf bis aus nach vor um am im ins zum zur vom von neben dem gegenüber "
        "zwischen hinter in an ab mit wegen pro des zurück hin"
    ),
    "particle": split_words(
        "und oder aber weil wenn als der die den ein einen eine kein nicht "
        "nein ja guten gute welcher bitte"
    ),
    "adjective": split_words(
        "null eins zwei drei vier fünf sechs sieben acht neun zehn elf zwölf "
        "dreizehn vierzehn fünfzehn sechzehn siebzehn achtzehn neunzehn zwanzig "
        "dreißig vierzig fünfzig sechzig siebzig achtzig neunzig hundert "
        "einundzwanzig zweiunddreißig achtundzwanzig einunddreißig alt "
        "siebte dritte neunten erste zweite geschlossen halb spät "
        "frisch weit gut schlecht einfach klein hell sonnig kalt warm blau rot "
        "froh müde traurig frei langsam billiger teurer kälter näher "
        "weh bar lieber"
    ),
    "adverb": split_words(
        "wie woher wann wo hier heute bald später gern ganz sehr wieder dann "
        "morgens noch leider gestern morgen natürlich sonst auch links rechts "
        "geradeaus beruflich viel nur meinerseits geht's"
    ),
    "verb": split_words(
        "geht heißen heiße heißt freut bin bist sind kommen komme kommst "
        "fragen darf ist kann schreiben haben öffnet schließt habe möchte "
        "möchten macht kosten biegen gehen halten verfehlen nehmen abbiegen "
        "aufstehen stehe frühstücken arbeiten arbeite lernen lerne schlafen "
        "gehe frühstücke stehen steht frühstückt arbeitet lernt gemacht "
        "gekauft gegessen gegangen war mögen mag trinke nehme trinkt nimmt "
        "kostet fährt tut brauchen brauche trinken machen hat braucht bringe "
        "bringt gibt regnet kaufe suche passt kaufen fühlen anrufen rufe "
        "wiederholen sprechen schreibe treffen bezahlen zahlen zahlt können "
        "geschehen"
    ),
    "phrase": split_words("hallo tschüss danke Entschuldigung"),
}
for _pos, _words in {
    "proper_noun": "Weber Lindenstraße",
    "symbol": "8",
    "pronoun": "Ihren meiner meinen jemand jeden",
    "preposition": "für seit unter zu",
    "particle": "dass welche",
    "adjective": (
        "vielen ruhig interessant teuer anderer monatlich monatliche stark "
        "starke verfügbar nützlich kaputt alternative spätere soziale "
        "freundlichen"
    ),
    "adverb": "manchmal zuerst danach online vormittags",
    "verb": (
        "bringen mitbringen wohne wohnen muss abgeben bestätigen finde denke "
        "verstehe eröffnen gehört bekomme wiederkommen funktioniert kommt "
        "gehören fällt verpasse lese benutze tun treffe umtauschen "
        "zurückbekommen"
    ),
}.items():
    POS_SETS[_pos] = set(POS_SETS.get(_pos, ())) | split_words(_words)
# B1 (units 35-53): parts of speech of the new tokens; everything not listed
# here and not in an earlier set is a noun.
for _pos, _words in {
    "proper_noun": "Klein König Vogel Braun",
    "symbol": "14 15",
    "pronoun": "diese Ihrer Ihrem unser beide ihn",
    "preposition": "ohne über beim bei",
    "particle": (
        "ob denn während damit obwohl zwar keinen"
    ),
    "adjective": (
        "letzte fertig dringend besser einfacher praktisch zuständig beschäftigt "
        "schön schwierig guter möglich schnell schnelle leid nächste nächstes "
        "nächster eigenes spannend neue riskant groß genauen reich zweites neues "
        "toll einverstanden geehrte beliebt reserviert"
    ),
    "adverb": (
        "schon früher sofort wofür plötzlich bestimmt allein immer vorbei "
        "wirklich warum abends öfter so lange wahrscheinlich vielleicht "
        "zusammenfassend außerdem gerade deshalb mehr jetzt"
    ),
    "verb": (
        "sagen konnte konnten könnte geben fehlt müssen dürfen hätte sollen "
        "stimmt unterschreibe helfen würde wäre stimme spart denken arbeitete "
        "klingelte kam sagte gesagt regnen bleibe bleiben wandern hatte "
        "vorbeikommen fragte gefragt geantwortet antworten sparen spricht "
        "versteht verstehen schreibt vergisst vergessen spreche schlafe sollten "
        "sollte versuchen danken funktionieren angerufen reparieren passiert "
        "schicke schicken melden warten wünschte kaputtgegangen repariert ziehen "
        "werde wechseln ziehe umziehen lässt anbietet erwähnt gelesen wissen "
        "kochen vorschlagen schließen klingt klingen ausprobieren könnten "
        "verschieben besprechen passen bestellt bestellen sitzen sitzt"
    ),
}.items():
    POS_SETS[_pos] = set(POS_SETS.get(_pos, ())) | split_words(_words)
POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())

CATEGORY_TAGS: dict[str, list[str]] = {}
for _tag, _words in {
    "de_number": "null eins zwei drei vier fünf sechs sieben acht neun zehn elf "
                 "zwölf dreizehn vierzehn fünfzehn sechzehn siebzehn achtzehn "
                 "neunzehn zwanzig dreißig vierzig fünfzig sechzig siebzig "
                 "achtzig neunzig hundert einundzwanzig zweiunddreißig "
                 "achtundzwanzig einunddreißig",
    "de_weekday": "Montag Dienstag Mittwoch Donnerstag Freitag Samstag Sonntag",
    "de_month": "Januar März Mai Juli September Dezember",
    "de_family": "Vater Mutter Bruder Schwester Eltern Geschwister Großmutter "
                 "Großvater Tante Onkel Cousin Cousine Brüder Schwestern "
                 "Einzelkind Familie",
}.items():
    for _w in _words.split():
        CATEGORY_TAGS.setdefault(_w, []).append(_tag)

part_of_speech = pos_lookup(POS_SETS)

# (realization stem, token) -> gloss, for tokens the B1 unit teaches in another
# sense than the A1/A2 entry.
B1_GLOSS_OVERRIDES = {
    ("b1_unit37_hypothesen", "an"): "at; on; to (also the particle of the verb meaning to call)",
    ("b1_unit42_zeitablauf", "als"): "when (for one event in the past)",
    ("b1_unit52_besprechungen", "passt"): "suits; fits (a schedule)",
}


def iter_specs():
    for level, group in LEVELS.items():
        realizations, _ = manifest_group(group)
        yield from classify(
            lang=LANG,
            level=level,
            unit_files=realizations,
            glosses=GLOSSES,
            part_of_speech=part_of_speech,
            normalize=normalize,
            category_tags=CATEGORY_TAGS,
            gloss_overrides=B1_GLOSS_OVERRIDES,
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
