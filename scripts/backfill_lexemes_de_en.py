#!/usr/bin/env python3
"""Idempotently backfill de-en (English target, German source) lexemes for the
"Englisch A1" course, so de-en practice packs and unit checkpoints have
per-unit lexeme pools (`generate_checkpoint()` needs BOTH practice templates
and lexemes on a unit's own lessons).

Session 10, 2026-10-24. All plumbing lives in
scripts/_target_lexeme_backfill_common.py (see its docstring for the tag
scheme); this file is data only.

X->en DIRECTION: the lexemes are ENGLISH tokens, so ``english_gloss`` holds the
GERMAN meaning -- it is the answer text of multiple_choice and the prompt of
translation exercises (see the IMPORTANT note in _en_target_lexeme_common.py).
It must never contain the English answer word.

Scope: A1 only (the "de-en" manifest group, units 01-14 of the shared English
realization). English classification (part of speech, citation form,
semantic category tags) is shared with nl-en/fa-en/prs-en through
scripts/_en_target_lexeme_common.py; the German glosses below are this
direction's own, hand-written.

Glossing rules followed here:
* the gloss is the sense the unit teaches at first sight,
* inflected/contracted forms say whose form they are, and du/Sie are marked
  (informal/formal) where it matters,
* no English word in a gloss (it would leak the answer in a translation prompt).

Run (after the de-en course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_de_en.py

Add --dry-run to classify without touching the database.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _en_target_lexeme_common import (  # noqa: E402
    EN_POS,
    en_agreement_tags,
    en_token_display,
    normalize_en_token,
)
from _target_lexeme_backfill_common import classify, manifest_group, run  # noqa: E402

LANG = "en"
LEVELS = {"a1": "de-en"}


def normalize(token: str) -> str:
    """Citation form: casefolded, sentence punctuation stripped, proper nouns
    keep their capital (the shared English convention)."""
    key = normalize_en_token(token)
    if key not in EN_POS:
        raise ValueError(f"missing English classification for {key!r} in EN_POS")
    return en_token_display(token, EN_POS[key])


def part_of_speech(token: str) -> str:
    return EN_POS[normalize_en_token(token)]


EN_TARGET_TO_DE_GLOSS: dict[str, str] = {
    # unit01 greetings
    "hello": "hallo (neutral)", "hi": "hallo (locker)",
    "good": "gut", "morning": "Morgen; Vormittag", "afternoon": "Nachmittag",
    "evening": "Abend", "goodbye": "auf Wiedersehen", "bye": "tschüss",
    "how": "wie", "are": "bist; sind (Form von „sein“)",
    "you": "du; Sie (formell)", "i'm": "ich bin", "fine": "prima",
    "thanks": "danke", "not": "nicht", "bad": "schlecht", "and": "und",
    "okay": "in Ordnung", "nice": "schön; nett", "to": "zu", "meet": "kennenlernen",
    "too": "ebenfalls", "see": "sehen", "later": "später", "have": "haben",
    "a": "ein; eine", "day": "Tag",
    # unit02 introductions
    "what": "was", "what's": "was ist", "your": "dein; Ihr (formell)",
    "name": "Name", "my": "mein", "is": "ist", "Leila": "Leila", "i": "ich",
    "am": "bin", "student": "Student; Studentin", "teacher": "Lehrer; Lehrerin",
    "yes": "ja", "no": "nein", "new": "neu", "member": "Mitglied", "he": "er",
    "she": "sie (weiblich)", "an": "ein; eine (vor Vokal)",
    "engineer": "Ingenieur; Ingenieurin", "library": "Bibliothek",
    "assistant": "Assistent; Assistentin", "Daniel": "Daniel",
    "welcome": "willkommen", "the": "der; die; das", "thank": "danken",
    # unit03 numbers
    "zero": "null", "one": "eins", "two": "zwei", "three": "drei", "four": "vier",
    "five": "fünf", "six": "sechs", "seven": "sieben", "eight": "acht",
    "nine": "neun", "ten": "zehn", "eleven": "elf", "twelve": "zwölf",
    "thirteen": "dreizehn", "fifteen": "fünfzehn", "twenty": "zwanzig",
    "twenty-one": "einundzwanzig", "thirty": "dreißig", "forty": "vierzig",
    "fifty": "fünfzig", "hundred": "hundert", "old": "alt",
    "twenty-five": "fünfundzwanzig", "years": "Jahre", "much": "viel",
    "this": "dies; das hier", "it's": "es ist", "dollars": "Dollar",
    "phone": "Telefon", "number": "Nummer; Zahl", "market": "Markt",
    "apples": "Äpfel", "they're": "sie sind", "ok": "einverstanden",
    "shop": "Geschäft",
    # unit04 dates
    "monday": "Montag", "tuesday": "Dienstag", "wednesday": "Mittwoch",
    "thursday": "Donnerstag", "friday": "Freitag", "saturday": "Samstag",
    "sunday": "Sonntag", "it": "es", "today": "heute", "january": "Januar",
    "march": "März", "july": "Juli", "september": "September",
    "december": "Dezember", "which": "welche; welcher; welches", "month": "Monat",
    "today's": "heutige; heutiges (von heute)", "date": "Datum", "7th": "der 7. (Datum)",
    "can": "können; kann", "also": "auch", "write": "schreiben", "as": "als",
    "when's": "wann ist", "birthday": "Geburtstag", "3rd": "der 3. (Datum)",
    "opens": "öffnet", "again": "wieder", "open": "öffnen; geöffnet sein",
    "on": "am (vor einem Wochentag oder Datum)", "9th": "der 9. (Datum)",
    "great": "großartig", "then": "dann",
    # unit05 time
    "time": "Zeit; Uhrzeit", "o'clock": "Uhr (bei der Uhrzeit)", "half": "halb",
    "past": "nach (bei der Uhrzeit)", "quarter": "Viertel", "night": "Nacht",
    "store": "Laden", "at": "um (bei der Uhrzeit)",
    "in": "am; im (vor einer Tageszeit)", "closes": "schließt (er/sie/es)",
    "does": "tut (er/sie/es; Hilfsverb in Fragen)", "close": "schließen",
    # unit06 family
    "mother": "Mutter", "father": "Vater", "brother": "Bruder",
    "sister": "Schwester", "parents": "Eltern", "siblings": "Geschwister",
    "grandmother": "Großmutter", "grandfather": "Großvater", "aunt": "Tante",
    "uncle": "Onkel", "cousin": "Cousin; Cousine", "his": "sein",
    "her": "ihr (zu einer Frau gehörig)", "she's": "sie ist",
    "brothers": "Brüder", "do": "tun (Hilfsverb in Fragen)",
    "any": "irgendwelche", "don't": "tue nicht; tun nicht (Hilfsverb)",
    "only": "einzig", "child": "Kind", "photo": "Foto", "family": "Familie",
    "who": "wer", "just": "nur",
    # unit07 food
    "coffee": "Kaffee", "tea": "Tee", "water": "Wasser", "bread": "Brot",
    "soup": "Suppe", "salad": "Salat", "sandwich": "belegtes Brot",
    "i'd": "ich möchte", "like": "möchten", "please": "bitte",
    "anything": "irgendetwas", "else": "sonst", "that's": "das ist",
    "all": "alles", "for": "für; zum", "here": "hier", "or": "oder",
    "go": "gehen; zum Mitnehmen", "menu": "Speisekarte", "price": "Preis",
    "cafe": "Café", "3": "Ziffer (drei)", "2": "Ziffer (zwei)", "5": "Ziffer (fünf)",
    "6": "Ziffer (sechs)", "sure": "klar; sicher",
    # unit08 shopping
    "pound": "Pfund", "of": "von (bei Mengenangaben)", "dozen": "Dutzend",
    "eggs": "Eier", "bottle": "Flasche", "bag": "Tüte", "rice": "Reis",
    "kilo": "Kilo", "tomatoes": "Tomaten", "pounds": "Pfund (mehrere)",
    "fresh": "frisch", "per": "pro", "4": "Ziffer (vier)",
    # unit09 places
    "bank": "Bank (Geldinstitut)", "hospital": "Krankenhaus", "pharmacy": "Apotheke",
    "park": "Park", "restaurant": "Restaurant", "next": "neben; nächster",
    "across": "gegenüber", "from": "von", "between": "zwischen",
    "behind": "hinter", "front": "Vorderseite; vor", "where": "wo",
    "far": "weit entfernt", "excuse": "entschuldigen", "me": "mich; mir",
    # unit10 directions
    "turn": "abbiegen", "left": "links", "right": "rechts", "straight": "geradeaus",
    "stop": "anhalten", "corner": "Ecke", "get": "gelangen; kommen",
    "minutes": "Minuten", "can't": "kann nicht; können nicht", "miss": "verfehlen",
    "take": "nehmen", "first": "erste; erster", "street": "Straße",
    "second": "zweite; zweiter", "directions": "Wegbeschreibung",
    # unit11 weather
    "sunny": "sonnig", "rainy": "regnerisch", "cloudy": "bewölkt", "cold": "kalt",
    "hot": "heiß", "windy": "windig", "weather": "Wetter", "warm": "warm",
    "raining": "es regnet (gerade)", "should": "sollte; solltest; sollten",
    "umbrella": "Regenschirm", "tomorrow": "morgen",
    "will": "werden (Zukunft)", "be": "sein", "rain": "regnen",
    "let's": "lass uns; lassen Sie uns", "idea": "Idee", "but": "aber",
    "going": "vorhaben; im Begriff sein", "so": "deshalb",
    # unit12 clothing
    "shirt": "Hemd", "pants": "Hose", "shoes": "Schuhe", "jacket": "Jacke",
    "dress": "Kleid", "small": "klein", "medium": "mittel",
    "large": "groß (Kleidergröße)", "blue": "blau", "black": "schwarz",
    "size": "Größe", "color": "Farbe", "20": "Ziffer (zwanzig)", "i'll": "ich werde",
    "we": "wir",
    # unit13 emotions
    "happy": "glücklich", "sad": "traurig", "tired": "müde", "excited": "aufgeregt (voller Vorfreude)",
    "worried": "besorgt", "feeling": "Gefühl; sich fühlen", "little": "ein wenig",
    "because": "weil", "big": "groß", "test": "Prüfung", "class": "Unterricht",
    "almost": "fast", "over": "vorbei", "last": "letzte; letzter", "year": "Jahr",
    "writer": "Schriftsteller; Schriftstellerin", "oh": "ach",
    "understand": "verstehen",
    # unit14 communication
    "free": "frei (Zeit haben)", "tonight": "heute Abend", "sorry": "tut mir leid",
    "repeat": "wiederholen", "that": "das (dort)", "speak": "sprechen",
    "more": "mehr", "slowly": "langsam", "hear": "hören", "well": "gut (Adverb)",
    "6pm": "18 Uhr", "message": "Nachricht", "suggest": "vorschlagen",
    "meeting": "Treffen", "place": "Ort", "about": "wie wäre es mit",
}
GLOSSES = EN_TARGET_TO_DE_GLOSS

# Semantic category tags shared with the other X->en directions
# (greeting, number, day_part, farewell, ...). The per-direction
# "volume_*" singleton tags belong to other courses and are dropped.
CATEGORY_TAGS: dict[str, list[str]] = {}
for _token in GLOSSES:
    _semantic = en_agreement_tags(normalize_en_token(_token)).get("semantic") or []
    _kept = [t for t in _semantic if not t.startswith("volume_")]
    if _kept:
        CATEGORY_TAGS[_token] = _kept


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
        )


def main() -> int:
    return run(
        description=__doc__,
        source_language="de",
        target_language=LANG,
        levels=LEVELS,
        iter_specs=iter_specs,
    )


if __name__ == "__main__":
    raise SystemExit(main())
