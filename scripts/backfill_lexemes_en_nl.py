#!/usr/bin/env python3
"""Idempotently backfill target-side en-nl Dutch A1 lexemes for units 1-4.

Run with ``--dry-run`` to parse and classify content without importing the
application or connecting to PostgreSQL.  The realization files' complete
``introduced_tokens`` inventories are authoritative.
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

UNIT_FILES = tuple(sorted((REPO_ROOT / "docs/content/realizations/nl").glob("a1_unit0[1-4]_*.yaml")))

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

SYMBOLS = set("'s 0 00 06 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 18 19 20 21 22 24 25 29 30 31 32 40 42 43 45 48 50 65 75 87 90 99 2024 2026".split())
PROPER_NOUNS = {"België", "Duitsland", "Egypte", "Lotte", "Nederland", "Noor", "Omar"}
PRONOUNS = set("ik Ik je jij jou Jou me u Wij wij Mijn mijn Welke welke Wat wat Hoeveel hoeveel".split())
PREPOSITIONS = set("aan bij in met na naar om Om op Op over te tot Tot uit voor vóór".split())
PARTICLES = set("behalve dan Dan dat Dat de De dit dus en En er Er geen het Het Ja ja Nee nee Niet niet of ook wel".split())
ADJECTIVES = set("Belgisch beleefd Duits Engels formeel Goed hele informeel laat Leuk leuk Nederlands nieuw normaal open oud slecht volgende".split())
ADVERBS = set("avonds vandaan halverwege hier hoe Hoe hoeveelste middags nachts ochtends terug vandaag Vandaag waar Waar wanneer Wanneer".split())
VERBS = set("begint ben Ben bent Bent heb heet inschrijven is Is kom Kom komt kost krijgen leer moet ontmoeten spreek wil woon zijn zitten Kun kun herhalen gaat".split())
PHRASES = {"Aangenaam", "Goedemiddag", "Goedemorgen", "Goedenavond", "Hallo", "Hoi", "Prima", "ziens"}
NOUNS = set("Achtenveertig Dagen Inleverdatum Maanden Medewerker Nul Pauze Taalcafé Twaalf Welkom Workshop acht achtentwintig achtentwintigste achtenveertig achtste achttien achttiende april augustus avond bibliotheek bijdrage boek boeken cent dag dank datum december derde dertien dertiende dertig dertigste dinsdag donderdag drie drieëntwintigste drieënveertig eenendertigste eenentwintig eenentwintigste eenheid eerste elf elfde euro februari groep half hoofdletter huisnummer inleverdatum jaar januari juli juni keer kwart kwartier maand maandag maart mei mensen middag naam nacht negen negende negenennegentig negenentwintigste negentien negentiende negentig november nul nummer ochtend oktober rooster september stoelen taalcafé tachtig tafel telefoonnummer tien tiende tiental tijd twaalf twaalfde twee tweede tweeëndertig tweeëntwintig tweeëntwintigste tweeënveertig twintig twintigste uur veertien veertiende veertig vier vierde vierentwintigste vijf vijfde vijfentwintigste vijfenzestig vijfenzeventig vijftien vijftiende vijftig vrijdag vrijdagmiddag week woensdag workshop zaal zaterdag zes zesde zesentwintigste zestien zestiende zestig zeven zevende zevenentachtig zevenentwintigste zeventien zeventiende zeventig zondag één".split())


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
    }
    semantic.append(lesson_categories[unit_lesson])
    if t in {"jij", "je"}: semantic.append("informal_address")
    if t == "u": semantic.append("polite_address")
    if token in {"Hallo", "Hoi", "Goedemorgen", "Goedemiddag", "Goedenavond"}: semantic.append("greeting")
    if t in {"goed", "prima", "slecht"}: semantic.append("wellbeing_answer")
    if token in {"Lotte", "Noor", "Omar"}: semantic.append("person_name")
    if token in {"Nederland", "België", "Duitsland", "Egypte"}: semantic.append("place_name")
    if t in {"nederland", "belgië", "duitsland", "egypte"}: semantic.append("country")
    if t in {"nederlands", "belgisch", "engels", "duits"}: semantic.append("language_or_nationality")
    number_words = set("nul één twee drie vier vijf zes zeven acht negen tien elf twaalf dertien veertien vijftien zestien zeventien achttien negentien twintig dertig veertig vijftig zestig zeventig tachtig negentig eenentwintig tweeëntwintig tweeëndertig tweeënveertig achtenveertig vijfenzeventig negenennegentig drieënveertig vijfenzestig zevenentachtig achtentwintig".split())
    if t in number_words or token in SYMBOLS and token != "'s": semantic.append("number")
    if t in {"twee", "drie", "zeven", "acht", "veertien", "achttien", "twintig"} or token in {"2", "3", "7", "8", "14", "18", "20"}: semantic.append("hour_number")
    if t in set("maandag dinsdag woensdag donderdag vrijdag zaterdag zondag".split()): semantic.append("weekday")
    if t in set("januari februari maart april mei juni juli augustus september oktober november december".split()): semantic.append("month")
    if t.endswith(("de", "ste")) and t not in {"de", "zelfde"}: semantic.append("ordinal_number")
    if t in {"ochtend", "middag", "avond", "nacht", "ochtends", "middags", "avonds", "nachts", "vrijdagmiddag"}: semantic.append("time_of_day")
    if t in {"ochtend", "middag", "avond", "nacht"}: semantic.append("day_period")
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
