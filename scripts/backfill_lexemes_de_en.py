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

Scope: A1 (the "de-en" manifest group, units 01-14 of the shared English
realization), A2 (the "de-en-a2" group, units 25-40, session 11) and B1 (the
"de-en-b1" group, units 01-19 of the shared B1 realization, session 12). A1, A2
and B1 are separate courses, so each glosses every token it introduces;
B1_SENSE_FIXES re-glosses the A1/A2 tokens whose B1 unit teaches another sense.
The B1 course must be imported first: the runner stops with "ERROR: de-en
'Englisch B1' course must be imported first" (exit 1, nothing written) when the
de-en-b1 course row is missing. English classification (part of speech, citation form,
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
    en_agreement_tags,
    en_token_display,
    normalize_en_token,
)
from _target_lexeme_backfill_common import classify, manifest_group, run  # noqa: E402

# The shared EN_POS only covers A1 and part of A2; nl-en's supplement
# (shared file wins) classifies the remaining A2/B1 tokens. Only the part of
# speech is taken from it; every German gloss in this file is hand-written.
from backfill_lexemes_nl_en import EN_POS_ALL as EN_POS  # noqa: E402

LANG = "en"
LEVELS = {"a1": "de-en", "a2": "de-en-a2", "b1": "de-en-b1"}


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
# --- A2 (session 11): German glosses for the tokens the 16 A2 units introduce
# that the A1 table above does not already cover. A1 and A2 are separate
# course rows, so A2 glosses every token again at its first A2 sight; tokens
# whose A2 sense differs from the A1 gloss are re-glossed in A2_SENSE_FIXES.
A2_GLOSSES: dict[str, str] = {
    # unit25 bureaucracy
    "appointment": "Termin", "document": "Dokument; Unterlage", "proof": "Nachweis",
    "residency": "Wohnsitz", "form": "Formular", "confirmation": "Bestätigung",
    "was": "war (Vergangenheit von „sein“)", "wondering": "sich fragen (Verlaufsform)",
    "whether": "ob", "could": "könnte; könnten", "make": "machen; vereinbaren",
    "would": "würde; würden", "possible": "möglich", "come": "kommen",
    "need": "brauchen; müssen", "update": "aktualisieren; ändern",
    "address": "Adresse", "moved": "umgezogen; zog um", "id": "Ausweis",
    "utility": "Versorgungs- (Strom, Gas, Wasser)", "bill": "Rechnung",
    "bring": "mitbringen", "such": "solche (in „wie zum Beispiel“)",
    "if": "wenn; falls", "lease": "Mietvertrag", "tell": "sagen; erzählen",
    "long": "lang; lange", "lived": "wohnte; gewohnt", "since": "seit",
    "10am": "zehn Uhr vormittags", "works": "passt (ist machbar)",
    "4471": "vierundvierzig einundsiebzig (Nummer)",
    # unit26 opinions
    "think": "denken; meinen", "opinion": "Meinung", "other": "andere; anderer",
    "hand": "Hand; Seite (in „andererseits“)", "agree": "zustimmen; einer Meinung sein",
    "dog": "Hund", "dogs": "Hunde", "space": "Platz", "run": "rennen; laufen",
    "very": "sehr", "playground": "Spielplatz", "fair": "berechtigt; fair",
    "point": "Punkt; Argument", "maybe": "vielleicht", "they": "sie (Plural)",
    "move": "verlegen; verschieben", "farther": "weiter (entfernt)",
    "away": "weg; entfernt", "better": "besser",
    # unit27 banking
    "checking": "Giro- (beim Konto)", "account": "Konto", "debit": "Debit-; Abbuchungs-",
    "card": "Karte", "monthly": "monatlich", "fee": "Gebühr", "minimum": "Mindest-",
    "balance": "Kontostand", "direct": "direkt", "deposit": "Einzahlung",
    "documents": "Dokumente; Unterlagen", "you'll": "du wirst; Sie werden",
    "DMV": "Kfz-Zulassungsstelle (US-Behörde)", "business": "Geschäfts-; Werk-",
    "days": "Tage", "there": "dort; da", "keep": "behalten; halten",
    "500": "fünfhundert", "arrive": "ankommen; eintreffen", "with": "mit",
    "sounds": "klingt", "teller": "Bankangestellte(r) am Schalter",
    "both": "beide", "there's": "es gibt; da ist", "when": "wann; wenn",
    # unit28 doctor
    "medicine": "Medikament; Arznei", "prescription": "Rezept (vom Arzt)",
    "follow": "folgen; befolgen", "up": "auf; nach oben (in festen Wendungen)",
    "getting": "werden (Verlaufsform)", "worse": "schlimmer; schlechter",
    "insurance": "Versicherung", "headache": "Kopfschmerzen",
    "sore": "wund; schmerzend", "throat": "Hals; Rachen", "fever": "Fieber",
    "doctor": "Arzt; Ärztin", "i've": "ich habe (Kurzform)", "had": "hatte; gehabt",
    "early": "früh", "confirmed": "bestätigt", "3pm": "fünfzehn Uhr",
    "7724": "siebenundsiebzig vierundzwanzig (Nummer)", "wrong": "falsch; verkehrt",
    "twice": "zweimal", "drink": "trinken", "plenty": "reichlich; viel",
    "back": "zurück", "doesn't": "tut nicht (er/sie/es; Hilfsverb)",
    "within": "innerhalb", "week": "Woche",
    # unit29 maintenance
    "leaking": "undicht sein; tropfen", "sink": "Spüle; Waschbecken",
    "building": "Gebäude", "manager": "Hausverwalter; Hausverwalterin",
    "plumber": "Klempner; Klempnerin", "repair": "Reparatur", "kitchen": "Küche",
    "apartment": "Wohnung", "bathroom": "Badezimmer", "report": "melden",
    "problem": "Problem", "been": "gewesen (Partizip von „sein“)",
    "someone": "jemand", "fix": "reparieren", "2pm": "vierzehn Uhr",
    "4pm": "sechzehn Uhr", "has": "hat", "received": "erhalten; bekommen",
    "6180": "einundsechzig achtzig (Nummer)", "send": "schicken", "home": "Zuhause",
    "here's": "hier ist",
    # unit30 job interview
    "experience": "Erfahrung", "position": "Stelle; Position",
    "availability": "Verfügbarkeit", "strength": "Stärke", "requirement": "Anforderung",
    "social": "sozial", "media": "Medien", "marketing": "Marketing",
    "strengths": "Stärken", "being": "sein (Verlaufsform)",
    "organized": "gut organisiert", "available": "verfügbar", "start": "anfangen; beginnen",
    "resume": "Lebenslauf", "deadline": "Frist; Abgabetermin",
    "bright": "hell (hier Teil eines Firmennamens)",
    "Path": "Pfad (hier Teil eines Firmennamens)", "looking": "suchen (Verlaufsform)",
    "coordinator": "Koordinator; Koordinatorin", "requirements": "Anforderungen",
    "strong": "stark; gut", "writing": "Schreiben; schriftlicher Ausdruck",
    "skills": "Fähigkeiten", "immediately": "sofort",
    "interview": "Vorstellungsgespräch", "deadlines": "Fristen",
    "work": "arbeiten", "team": "Team", "coming": "kommen (Verlaufsform)",
    "managed": "leitete; geleitet", "questions": "Fragen", "role": "Rolle; Aufgabe",
    "typical": "typisch", "looks": "sieht aus; schaut",
    # unit31 travel disruption
    "delay": "Verspätung", "cancelled": "gestrichen; abgesagt",
    "alternative": "Alternative", "notice": "Hinweis; Durchsage",
    "signal": "Signal", "why": "warum", "train": "Zug", "delayed": "verspätet",
    "another": "ein anderer; noch ein", "way": "Weg; Möglichkeit",
    "departure": "Abfahrt", "5:15": "Viertel nach fünf", "6:00": "sechs Uhr",
    "bus": "Bus", "5:30": "halb sechs", "outside": "draußen; vor",
    "station": "Bahnhof", "instead": "stattdessen", "help": "helfen; Hilfe",
    "tracks": "Gleise", "leaves": "fährt ab; geht ab",
    # unit32 online habits
    "screen": "Bildschirm", "messaging": "Nachrichten schreiben", "app": "App",
    "notification": "Benachrichtigung", "download": "herunterladen",
    "check": "nachsehen; kontrollieren", "mostly": "meistens", "use": "benutzen; nutzen",
    "apps": "Apps", "talk": "sprechen; reden", "cooking": "Kochen",
    "every": "jeder; jede; jedes", "useful": "nützlich", "staying": "bleiben (Verlaufsform)",
    "touch": "Kontakt (in „in Verbindung bleiben“)", "waste": "Verschwendung",
    "lot": "Menge (in „sehr viel“)", "know": "wissen; kennen", "post": "Beitrag; Post",
    "photos": "Fotos", "notifications": "Benachrichtigungen", "many": "viele",
    "times": "Mal", "enjoy": "genießen; gern tun", "sharing": "teilen",
    "friends": "Freunde", "spend": "verbringen; ausgeben", "thing": "Sache; Ding",
    # unit33 weekly schedule
    "weekday": "Wochentag", "weekend": "Wochenende", "schedule": "Zeitplan; Terminplan",
    "after": "nach", "finally": "schließlich; endlich", "weekdays": "unter der Woche",
    "company": "Firma", "email": "E-Mail", "meetings": "Besprechungen",
    "relax": "sich entspannen", "online": "online", "mondays": "montags",
    "wednesdays": "mittwochs", "classes": "Kurse; Unterrichtsstunden", "study": "lernen; studieren",
    "fridays": "freitags", "visit": "besuchen", "usually": "normalerweise; meist",
    "look": "aussehen; schauen", "mornings": "morgens", "running": "Laufen; Joggen",
    "before": "vor", "saturdays": "samstags", "play": "spielen", "soccer": "Fußball",
    "coworkers": "Kollegen; Kolleginnen", "sundays": "sonntags",
    # unit34 shopping complaint
    "refund": "Rückerstattung", "exchange": "umtauschen", "receipt": "Kassenbon; Beleg",
    "return": "zurückgeben", "policy": "Regelung; Richtlinie", "defective": "defekt",
    "blender": "Mixer", "stopped": "hörte auf; blieb stehen", "working": "funktionieren (Verlaufsform)",
    "items": "Artikel; Waren", "returned": "zurückgegeben", "30": "dreißig",
    "exchanged": "umgetauscht", "refunded": "erstattet", "bought": "kaufte; gekauft",
    "thirty-five": "fünfunddreißig",
    # unit35 prescription
    "pharmacist": "Apotheker; Apothekerin", "tablet": "Tablette", "dose": "Dosis",
    "refill": "Folgerezept; Nachfüllung", "side": "Seite (in „Nebenwirkung“)",
    "effects": "Wirkungen", "once": "einmal", "hours": "Stunden",
    "pick": "abholen; auswählen", "food": "Essen; Nahrung",
    "shouldn't": "sollte nicht", "bed": "Bett", "taking": "einnehmen (Verlaufsform)",
    "tablets": "Tabletten", "may": "dürfen; können", "feel": "sich fühlen",
    "refills": "Folgerezepte", "course": "Verlauf (in „natürlich“)", "gave": "gab",
    # unit36 document correction
    "certificate": "Urkunde; Bescheinigung", "mistake": "Fehler", "spelled": "geschrieben (Buchstabierung)",
    "correct": "richtig; korrekt", "copy": "Kopie", "passport": "Reisepass",
    "mistakes": "Fehler (Plural)", "registration": "Eintragung; Anmeldung",
    "correction": "Berichtigung; Korrektur", "request": "Antrag; Bitte",
    "corrected": "berichtigt; korrigiert", "office": "Amt; Büro",
    "reference": "Aktenzeichen; Referenz", "3092": "dreißig zweiundneunzig (Nummer)",
    # unit37 video calls
    "video": "Video", "call": "anrufen; telefonieren", "camera": "Kamera",
    "microphone": "Mikrofon", "connection": "Verbindung", "mute": "stummschalten",
    "face": "Gesicht", "faster": "schneller", "than": "als (beim Vergleich)",
    "less": "weniger", "personal": "persönlich", "were": "waren",
    "calls": "Anrufe; Gespräche", "prefer": "lieber mögen; bevorzugen",
    "people": "Leute; Menschen", "headphones": "Kopfhörer", "now": "jetzt",
    "until": "bis (zeitlich)", "asks": "fragt", "question": "Frage",
    "them": "sie; ihnen (Plural)", "save": "speichern; sparen", "still": "noch; immer noch",
    "classmates": "Mitschüler; Mitschülerinnen", "always": "immer",
    "speaking": "sprechen (Verlaufsform)", "exactly": "genau",
    # unit38 repair visit
    "reschedule": "verschieben (auf einen neuen Termin)", "neighbor": "Nachbar; Nachbarin",
    "key": "Schlüssel", "leak": "undichte Stelle; Leck", "fixed": "repariert",
    "won't": "wird nicht; werden nicht", "leave": "hinterlassen; verlassen",
    "rescheduled": "verschoben (auf einen neuen Termin)", "9am": "neun Uhr vormittags",
    "11am": "elf Uhr vormittags", "door": "Tür", "confirm": "bestätigen",
    "by": "bis (spätestens)", "under": "unter",
    # unit39 after the interview
    "offer": "anbieten; Angebot", "contract": "Vertrag", "salary": "Gehalt",
    "accept": "annehmen", "reply": "antworten", "yesterday": "gestern",
    "interested": "interessiert", "full": "voll; Vollzeit-", "dear": "sehr geehrte; liebe",
    "Mia": "Mia", "calling": "anrufen (Verlaufsform)", "job": "Stelle; Arbeit",
    "news": "Neuigkeiten", "hour": "Stunde", "lunch": "Mittagessen",
    "wonderful": "wunderbar",
    # unit40 online order problem
    "order": "bestellen; Bestellung", "delivery": "Lieferung", "parcel": "Paket",
    "damaged": "beschädigt", "broken": "kaputt", "replacement": "Ersatz",
    "arrived": "angekommen", "yet": "schon; bisher", "lamp": "Lampe",
    "8154": "einundachtzig vierundfünfzig (Nummer)", "box": "Karton; Schachtel",
    "put": "legen; stellen; tun", "sent": "schickte; geschickt",
}

# A1 tokens that A2 teaches in another sense (first sight per course).
A2_SENSE_FIXES: dict[str, str] = {
    "this": "diese; diesen (zeitlich, z. B. diesen Freitag)",
    "last": "letzte; vorige (zeitlich)", "about": "über (worüber man spricht)",
    "close": "nah; in der Nähe", "open": "eröffnen; öffnen", "get": "bekommen; erhalten",
    "cold": "Erkältung", "take": "nehmen; einnehmen", "see": "aufsuchen; sehen",
    "stop": "aufhören (mit etwas)", "meet": "einhalten; erfüllen (Fristen)",
    "next": "nächste; nächster", "meeting": "Besprechung", "turn": "einschalten; drehen",
    "class": "Kurs", "too": "zu (zu viel)", "from": "ab; von",
}

# B1 ("de-en-b1" group, units 01-19; session 12). B1 is its own course, so
# every token it introduces is glossed again; tokens already glossed for A1/A2
# keep that entry unless B1_SENSE_FIXES re-glosses them for the sense the B1
# unit teaches (resolved per token, first sight in the course). New tokens only
# below; German glosses are hand-written and never contain the English answer.
B1_GLOSSES: dict[str, str] = {
    # unit01 necessity
    "must": "müssen", "task": "Aufgabe", "rent": "Miete", "finish": "beenden; fertig machen",
    "pay": "bezahlen", "called": "rief an; angerufen", "earlier": "früher; eher",
    "forgot": "vergaß", "forget": "vergessen", "you're": "du bist; Sie sind",
    "busy": "beschäftigt; viel zu tun", "renew": "erneuern; verlängern", "gym": "Fitnessstudio",
    "membership": "Mitgliedschaft", "set": "einstellen; festlegen", "reminder": "Erinnerung",
    "late": "spät; zu spät", "did": "tat; machte (Hilfsverb in Fragen)", "done": "getan; erledigt",
    "dentist": "Zahnarzt; Zahnärztin", "everything": "alles",
    # unit02 abilities
    "able": "fähig; imstande", "manage": "schaffen; es hinbekommen", "license": "Führerschein; Lizenz",
    "person": "Person", "friend": "Freund; Freundin", "system": "System",
    "their": "ihr; ihre (Plural)", "licenses": "Führerscheine; Lizenzen", "everyone": "alle; jeder",
    "changed": "änderte; geändert", "hers": "ihrer; ihre; ihres (Besitz)",
    "wasn't": "war nicht", "really": "wirklich; tatsächlich", "want": "wollen; möchten",
    # unit03 hypotheticals
    "stay": "bleiben", "paint": "malen", "rains": "regnet", "loves": "liebt; mag sehr",
    "near": "in der Nähe von", "house": "Haus", "known": "gewusst; gekannt",
    "signed": "unterschrieb; angemeldet", "checks": "prüft; sieht nach", "plans": "Pläne",
    "walk": "Spaziergang", "painting": "Mal-; Malerei", "didn't": "tat nicht; taten nicht (Hilfsverb)",
    "join": "mitmachen; beitreten", "sign": "unterschreiben; sich anmelden",
    # unit04 debate
    "disagree": "nicht zustimmen; anderer Meinung sein", "believe": "glauben; meinen",
    "reason": "Grund", "focus": "sich konzentrieren", "respect": "respektieren",
    "thinks": "denkt; findet", "easily": "leicht; mühelos", "disagrees": "stimmt nicht zu",
    "believes": "glaubt; meint", "likes": "mag; gefällt", "seeing": "sehen (Verlaufsform)",
    "each": "jeder; jede; jedes (einzeln)", "other's": "des anderen; der anderen",
    "important": "wichtig", "conversations": "Gespräche", "saves": "spart",
    "makes": "macht", "sense": "Sinn", "different": "anders; verschieden",
    # unit05 workplace
    "responsible": "verantwortlich", "project": "Projekt", "technical": "technisch",
    "sales": "Verkaufs-; Vertrieb", "gives": "gibt", "short": "kurz", "expects": "erwartet",
    "tells": "sagt; erzählt", "truth": "Wahrheit", "delays": "Verzögerungen",
    "review": "durchsehen; überprüfen", "numbers": "Zahlen", "notes": "Notizen; Anmerkungen",
    "appreciate": "zu schätzen wissen; schätzen", "let": "lassen",
    # unit06 narrative
    "while": "während", "flat": "platt; ohne Luft", "tire": "Reifen", "pull": "ziehen",
    "stranger": "Fremder; Fremde", "mechanic": "Mechaniker; Mechanikerin",
    "said": "sagte; gesagt", "driving": "fahren (Verlaufsform)", "went": "ging; fuhr",
    "pulled": "zog; fuhr (rechts ran)", "helped": "half; geholfen",
    "already": "schon; bereits", "kept": "hielt; gehalten", "word": "Wort",
    "suddenly": "plötzlich", "quiet": "ruhig", "car": "Auto", "offered": "bot an",
    "say": "sagen", "got": "bekam; wurde", "happened": "geschah; passierte",
    "kind": "freundlich; nett", "him": "ihn; ihm",
    # unit07 conditions
    "unless": "es sei denn; wenn nicht", "condition": "Bedingung", "result": "Ergebnis; Folge",
    "starts": "beginnt; fängt an", "ready": "fertig; bereit", "backup": "Ersatz-; Reserve-",
    "plan": "Plan", "writes": "schreibt", "conference": "Konferenz; Besprechungs-",
    "room": "Raum; Zimmer", "joins": "kommt dazu; schließt sich an", "shorter": "kürzer",
    "cannot": "kann nicht; können nicht",
    # unit08 sequencing
    "soon": "bald", "lock": "abschließen; verschließen", "upstairs": "oben; nach oben",
    "mail": "Post", "locks": "schließt ab", "careful": "sorgfältig; vorsichtig",
    "routine": "Routine", "dinner": "Abendessen", "washes": "wäscht", "hands": "Hände",
    "clears": "räumt ab; räumt auf", "table": "Tisch", "arrives": "kommt an",
    # unit09 reported speech
    "told": "sagte; erzählte", "asked": "fragte; bat", "says": "sagt", "summary": "Zusammenfassung",
    "enough": "genug; ausreichend", "read": "las; lesen", "Mia's": "Mias",
    "finished": "beendete; fertiggestellt", "needed": "brauchte; benötigte", "ask": "fragen",
    "perfect": "perfekt",
    # unit10 purpose
    "goal": "Ziel", "design": "Gestaltung; Design", "improve": "verbessern", "money": "Geld",
    "prepare": "vorbereiten", "english": "Englisch", "remember": "sich merken; sich erinnern",
    "vocabulary": "Wortschatz; Vokabeln", "clear": "klar; deutlich", "helps": "hilft",
    "choose": "wählen; auswählen", "goals": "Ziele", "practices": "übt",
    "updates": "Aktualisierungen; Neuigkeiten", "sound": "klingen", "professional": "professionell",
    "reads": "liest", "descriptions": "Beschreibungen", "program": "Programm; Studiengang",
    "studying": "lernen; studieren (Verlaufsform)", "saving": "sparen (Verlaufsform)",
    # unit11 unreal hypotheticals
    "rather": "lieber", "opportunity": "Gelegenheit; Chance", "regret": "Bedauern; Reue",
    "chance": "Chance; Risiko", "cheaper": "billiger; günstiger", "tense": "Zeitform",
    "unreal": "unwirklich", "present": "gegenwärtig", "situation": "Situation",
    "sooner": "früher; eher", "confident": "selbstbewusst; zuversichtlich", "found": "fand; gefunden",
    "wants": "will; möchte", "expensive": "teuer", "joined": "trat bei; machte mit",
    "timing": "Zeitpunkt", "saved": "sparte; gespart", "definitely": "auf jeden Fall; definitiv",
    # unit12 concession
    "although": "obwohl", "even": "sogar; selbst", "though": "obwohl; doch",
    "despite": "trotz", "distractions": "Ablenkungen", "however": "jedoch; allerdings",
    "valid": "berechtigt; gültig", "convince": "überzeugen", "prefers": "bevorzugt; mag lieber",
    "finishes": "beendet; schließt ab", "clause": "Nebensatz; Teilsatz", "followed": "gefolgt",
    "noun": "Nomen; Substantiv", "sentence": "Satz", "period": "Punkt (Satzzeichen)",
    "semicolon": "Semikolon", "flexibility": "Flexibilität", "teamwork": "Teamarbeit",
    "builds": "schafft; baut auf", "comfortable": "bequem; angenehm", "misses": "vermisst",
    "gets": "bekommt; kommt", "talking": "sprechen (Verlaufsform)", "colleagues": "Kollegen; Kolleginnen",
    "during": "während", "breaks": "Pausen", "noise": "Lärm", "alone": "allein",
    "change": "ändern; wechseln", "mind": "Meinung; Verstand", "probably": "wahrscheinlich",
    "matters": "ist wichtig; zählt", "most": "am meisten", "our": "unser; unsere",
    "preferences": "Vorlieben",
    # unit13 relative clauses
    "whose": "dessen; deren", "approved": "genehmigte; genehmigt", "downtown": "Innenstadt",
    "coworker": "Kollege; Kollegin", "studies": "lernt; studiert", "Spanish": "Spanisch",
    "colleague": "Kollege; Kollegin", "sits": "sitzt", "leads": "leitet", "projects": "Projekte",
    "defining": "bestimmend", "relative": "Relativ-; relativ", "commas": "Kommas",
    "mean": "bedeuten; meinen", "non-defining": "nicht bestimmend", "add": "hinzufügen",
    "extra": "zusätzlich; extra", "information": "Information; Informationen",
    "identified": "identifiziert; bestimmt", "meets": "trifft; erfüllt", "approve": "genehmigen",
    "several": "mehrere", "easier": "leichter; einfacher", "fifth": "fünfte; fünfter",
    "floor": "Stockwerk; Boden", "eats": "isst", "together": "zusammen",
    "finishing": "abschließen (Verlaufsform)", "has already": "hat schon", "met": "traf; kennengelernt",
    "woman": "Frau", "desk": "Schreibtisch", "window": "Fenster", "designer": "Designer; Designerin",
    "logo": "Logo", "won": "gewann; gewonnen", "award": "Preis; Auszeichnung",
    "used": "benutzte; gewohnt", "smaller": "kleiner", "ours": "unseres; unsere; unser (Besitz)",
    "explains": "erklärt",
    # unit14 professional communication
    "possibly": "möglicherweise; vielleicht", "agenda": "Tagesordnung", "formal": "förmlich; formell",
    "workplace": "Arbeitsplatz", "requests": "Bitten; Anfragen", "softened": "abgeschwächt",
    "conditional": "Bedingungs-; bedingt", "command": "Befehl", "these": "diese (Plural)",
    "forms": "Formen", "polite": "höflich", "budget": "Budget", "afterward": "danach; anschließend",
    "hope": "hoffen", "doing": "tun (Verlaufsform)", "tomorrow's": "morgig; von morgen",
    "latest": "neueste; aktuellste", "client": "Kunde; Kundin", "best": "Bestes",
    "advance": "Voraus (im Voraus)", "updated": "aktualisiert",
    # unit15 complaints
    "complain": "sich beschweren", "resolve": "lösen; klären", "issue": "Problem; Anliegen",
    "product": "Produkt", "item": "Artikel", "written": "schriftlich; geschrieben",
    "complaint": "Beschwerde", "parts": "Teile", "specific": "bestimmt; konkret",
    "resolution": "Lösung", "chair": "Stuhl", "ordered": "bestellte; bestellt", "wheel": "Rad",
    "proceed": "weitermachen; vorgehen", "we'll": "wir werden",
    # unit16 advice
    "advice": "Rat; Ratschlag", "overwhelmed": "überfordert", "prioritize": "priorisieren; Prioritäten setzen",
    "workload": "Arbeitsbelastung; Arbeitspensum", "decline": "ablehnen", "closer": "näher",
    "asking": "fragen; bitten (Verlaufsform)", "suggestions": "Vorschläge",
    "hypothetical": "Annahme; Hypothese", "recommendation": "Empfehlung", "softer": "sanfter; weicher",
    "suggestion": "Vorschlag", "stronger": "stärker", "depending": "abhängen (Verlaufsform)",
    "try": "versuchen; ausprobieren", "top": "oben; Spitze; obendrauf",
    "goes": "geht", "leading": "leiten (Verlaufsform)", "seem": "scheinen; wirken",
    "handle": "bewältigen; handhaben", "solid": "solide; fest",
    # unit17 regret
    "wish": "wünschen; Wunsch", "hindsight": "Rückblick; im Nachhinein",
    "procrastinate": "aufschieben; trödeln", "talked": "sprach; gesprochen",
    "express": "ausdrücken", "participle": "Partizip", "describe": "beschreiben",
    "happen": "geschehen; passieren", "missed": "verpasste; verpasst", "wait": "warten",
    "worry": "sich Sorgen machen", "end": "Ende", "true": "wahr; stimmt",
    # unit18 future plans
    "arrangement": "Verabredung; feste Vereinbarung", "intention": "Absicht; Vorhaben",
    "prediction": "Vorhersage; Prognose", "months": "Monate", "might": "könnte; vielleicht",
    "continuous": "fortlaufend; durchgehend", "agreed": "stimmte zu; vereinbart",
    "decision": "Entscheidung", "made": "machte; gemacht", "without": "ohne", "steps": "Schritte",
    "feels": "fühlt sich", "completely": "völlig; ganz", "predicts": "sagt voraus",
    "agrees": "stimmt zu", "exciting": "spannend; aufregend",
    # unit19 summarizing
    "main": "Haupt-; wichtigste", "detail": "Detail; Einzelheit", "own": "eigen",
    "words": "Wörter; Worte", "covered": "behandelte; abgedeckt", "phrase": "Ausdruck; Wendung",
    "give": "geben", "points": "Punkte", "keeping": "behalten (Verlaufsform)",
    "highlight": "hervorheben", "single": "einzeln; einzig", "separately": "getrennt; einzeln",
    "details": "Details; Einzelheiten", "condensed": "verkürzt; gekürzt", "original": "ursprünglich; Original-",
    "article": "Artikel", "communication": "Kommunikation", "examples": "Beispiele",
    "background": "Hintergrund", "wrote": "schrieb", "messages": "Nachrichten",
    "guessing": "raten (Verlaufsform)", "out": "heraus; aus; weggelassen",
    "ideas": "Ideen", "helpful": "hilfreich",
}

# A1/A2 tokens whose B1 unit teaches another sense (first sight in the B1 course
# decides which unit that is; the entry replaces the A1/A2 gloss).
B1_SENSE_FIXES: dict[str, str] = {
    "right": "richtig; recht haben", "managed": "schaffte; geschafft",
    "save": "sparen", "class": "Kurs; Unterricht", "about": "über; darüber",
    "one": "eins; eine (Ersatzwort für ein Nomen)", "take": "nehmen; belegen (einen Kurs)",
    "miss": "verpassen; vermissen", "working": "arbeiten (Verlaufsform)",
    "report": "Bericht; melden", "update": "Update; aktualisieren", "office": "Büro; Amt",
    "manager": "Vorgesetzter; Teamleitung", "meet": "sich treffen; kennenlernen",
    "meeting": "Besprechung; Meeting", "delay": "Verzögerung; verzögern",
    "as": "wie; so (bei „sobald“)", "before": "vor; bevor", "after": "nach; nachdem",
    "over": "über; vorbei; rechts ran", "order": "Reihenfolge; Bestellung; um zu",
    "so": "damit; also", "taking": "besuchen; nehmen (Verlaufsform)",
    "past": "Vergangenheit; vergangen", "works": "arbeitet; funktioniert",
    "follow": "folgen; befolgen", "request": "Bitte; Anfrage", "left": "ließ; verließ; ließ weg",
    "moved": "verschoben; zog um", "looking": "blicken; schauen (Verlaufsform)",
    "fixed": "behoben; repariert", "this": "diese; dieser; dieses",
}

GLOSSES = EN_TARGET_TO_DE_GLOSS

# Semantic category tags shared with the other X->en directions
# (greeting, number, day_part, farewell, ...). The per-direction
# "volume_*" singleton tags belong to other courses and are dropped.
CATEGORY_TAGS: dict[str, list[str]] = {}
for _token in {**GLOSSES, **A2_GLOSSES, **A2_SENSE_FIXES, **B1_GLOSSES, **B1_SENSE_FIXES}:
    _semantic = en_agreement_tags(normalize_en_token(_token)).get("semantic") or []
    _kept = [t for t in _semantic if not t.startswith("volume_")]
    if _kept:
        CATEGORY_TAGS[_token] = _kept


GLOSSES_BY_LEVEL = {
    "a1": GLOSSES,
    "a2": {**GLOSSES, **A2_GLOSSES, **A2_SENSE_FIXES},
    "b1": {**GLOSSES, **A2_GLOSSES, **B1_GLOSSES, **B1_SENSE_FIXES},
}


def iter_specs():
    for level, group in LEVELS.items():
        realizations, _ = manifest_group(group)
        yield from classify(
            lang=LANG,
            level=level,
            unit_files=realizations,
            glosses=GLOSSES_BY_LEVEL[level],
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
