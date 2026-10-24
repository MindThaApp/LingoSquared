#!/usr/bin/env python3
"""Idempotently backfill en-ro (Romanian target) lexemes for the "Romanian A1"
course, so en-ro practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: en->X backfill outside the six launch directions.
All plumbing lives in scripts/_target_lexeme_backfill_common.py (see its
docstring for the tag scheme); this file is data only: one hand-written
English gloss and one part of speech per citation form.

Scope: A1 only (the "en-ro" manifest group, units 01-20). A2+ is not
classified yet; extend LEVELS and the tables below together.

Glossing rules followed here (PRACTICE_PACK_RECIPE.md §0.1, §6.6):
* the gloss is the sense the unit actually teaches at first sight; a token
  with two taught senses gets both ("more; still; May (the month)"),
* inflected forms say who they belong to ("you have (formal)"), so a
  bare-word translation prompt names one form,
* gender pairs are glossed "(masc.)"/"(fem.)" so the two are never
  interchangeable answers.

Diacritics: the realizations consistently use the modern comma-below forms
(ș U+0219, ț U+021B); no cedilla ş/ţ spelling occurs in any introduced token
(the cedilla/Moldovan spellings only appear in provenance notes), so no
spelling mapping is needed. Hyphenated clitic tokens ("mi-e", "nu-mi") are
glossed exactly as the realization spells them.

Sentence-initial capitals fold to lowercase; the proper nouns below keep
their capital.

Run (after the en-ro course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_ro.py

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

LANG = "ro"
LEVELS = {"a1": "en-ro"}

PROPER_NOUNS = {"Ana", "Mihai", "București"}
_PROPER_BY_LOWER = {p.lower(): p for p in PROPER_NOUNS}


def normalize(token: str) -> str:
    lower = token.lower()
    return _PROPER_BY_LOWER.get(lower, lower)


GLOSSES: dict[str, str] = {
    # unit01 greetings
    "bună": "hi; hello", "salut": "hi; bye (informal)", "ziua": "the day",
    "la": "at; to", "revedere": "seeing again (in a farewell)",
    "tu": "you (informal)", "dumneavoastră": "you (formal)",
    "ce": "what", "mai": "more; still; May (the month)", "faceți": "you do (formal)",
    "faci": "you do (informal)", "bine": "well; fine",
    "mulțumesc": "thank you", "mă": "me; myself", "numesc": "I am named",
    "Ana": "Ana", "cum": "how", "vă": "you (formal, object)",
    "numiți": "you are named (formal)", "cheamă": "calls; is called",
    "Mihai": "Mihai", "te": "you (informal, object)", "îmi": "to me",
    "pare": "seems", "și": "and; also", "mie": "to me (emphatic)",
    # unit02 numbers
    "zero": "zero", "unu": "one", "doi": "two (masc.)", "două": "two (fem. and neut.)",
    "trei": "three", "patru": "four", "cinci": "five", "șase": "six",
    "șapte": "seven", "opt": "eight", "nouă": "nine", "zece": "ten",
    "unsprezece": "eleven", "doisprezece": "twelve", "treisprezece": "thirteen",
    "paisprezece": "fourteen", "cincisprezece": "fifteen", "șaisprezece": "sixteen",
    "șaptesprezece": "seventeen", "optsprezece": "eighteen",
    "nouăsprezece": "nineteen", "douăzeci": "twenty", "treizeci": "thirty",
    "patruzeci": "forty", "cincizeci": "fifty", "șaizeci": "sixty",
    "șaptezeci": "seventy", "optzeci": "eighty", "nouăzeci": "ninety",
    "o": "a; an (fem.); one (fem.)", "sută": "hundred", "câți": "how many (masc. plural)",
    "ani": "years", "ai": "you have (informal)", "am": "I have",
    "aveți": "you have (formal)", "de": "of (after numbers above nineteen)",
    "care": "which; what", "e": "is (short form)", "numărul": "the number", "tău": "your (informal, masc. and neut.)",
    "telefon": "telephone; phone", "este": "is",
    # unit03 dates
    "astăzi": "today", "mâine": "tomorrow", "luni": "Monday", "marți": "Tuesday",
    "miercuri": "Wednesday", "joi": "Thursday", "vineri": "Friday",
    "sâmbătă": "Saturday", "duminică": "Sunday", "zi": "day",
    "săptămână": "week", "ieri": "yesterday", "săptămâna": "the week",
    "trecută": "last; past (fem.)", "viitoare": "next; coming (fem.)",
    "zilele": "the days", "nu": "not; no", "se": "oneself (reflexive marker)",
    "scriu": "they write (with the reflexive: are written)", "cu": "with", "literă": "letter", "mare": "big; capital (of a letter)",
    "ianuarie": "January", "februarie": "February", "martie": "March",
    "aprilie": "April", "iunie": "June", "iulie": "July", "august": "August (month)",
    "septembrie": "September", "octombrie": "October", "noiembrie": "November",
    "decembrie": "December", "întâi": "first", "dată": "date", "mulți": "many (masc. plural)",
    "lunile": "the months", "când": "when", "întâlnirea": "the meeting",
    # unit04 time
    "ora": "the hour; the time", "jumătate": "half", "cât": "how much",
    "un": "a; an (masc. and neut.); one (masc. and neut.)", "sfert": "quarter", "fără": "without; to (minutes before the hour)",
    "oră": "hour; time of day", "târziu": "late", "dimineața": "the morning",
    "după": "after", "amiaza": "midday; noon (with the article)", "seara": "the evening",
    "noaptea": "the night", "cursul": "the class; the course", "începe": "begins",
    # unit05 family
    "familie": "family", "mamă": "mother", "tată": "father", "părinți": "parents",
    "meu": "my (masc. and neut.)", "mea": "my (fem.)", "mama": "the mother", "tatăl": "the father",
    "da": "yes", "frate": "brother", "soră": "sister", "frați": "brothers",
    "surori": "sisters", "copil": "child", "copii": "children", "fiu": "son",
    "fiică": "daughter", "căsătorit": "married (masc.)",
    # unit06 food
    "aș": "I would", "dori": "like; wish (after \"I would\")", "apă": "water",
    "cafea": "coffee", "ceai": "tea", "suc": "juice", "lapte": "milk",
    "mi-e": "I am (for hunger, thirst)", "sete": "thirst", "foame": "hunger",
    "pâine": "bread", "mâncare": "food", "carne": "meat", "pui": "chicken",
    "fructe": "fruit", "rog": "I ask (in a polite request)",
    # unit07 shopping
    "costă": "costs", "leu": "Romanian currency unit (singular)",
    "lei": "Romanian currency units (plural)", "scump": "expensive",
    "ieftin": "cheap", "piață": "market", "roșii": "tomatoes", "cartofi": "potatoes",
    "kilogram": "kilogram; kilo", "vreau": "I want", "unde": "where",
    "pot": "I can", "să": "to; so that", "cumpăr": "I buy",
    # unit08 places
    "gară": "train station", "magazin": "store; shop", "bancă": "bank",
    "aproape": "near; close", "departe": "far", "magazinul": "the store",
    "banca": "the bank", "gara": "the train station", "spital": "hospital",
    "poștă": "post office", "bibliotecă": "library", "biblioteca": "the library",
    "stație": "stop (for a bus)", "autobuz": "bus", "lângă": "next to",
    "vizavi": "opposite; across", "între": "between", "spitalul": "the hospital",
    "poșta": "the post office", "stația": "the stop (for a bus)",
    # unit09 directions
    "ajung": "I arrive; I get to", "mergeți": "go (formal command)",
    "înainte": "ahead; forward", "dreapta": "right (side)", "stânga": "left (side)",
    "aici": "here", "acolo": "there", "apoi": "then; afterwards",
    # unit10 routines
    "trezesc": "I wake up (reflexive)", "mănânc": "I eat", "beau": "I drink",
    "lucrez": "I work", "merg": "I go", "acasă": "home; at home",
    "culc": "I go to bed (reflexive)",
    # unit11 plans
    "mergem": "we go; let us go", "cinema": "movie theater; cinema",
    "parc": "park", "atunci": "in that case; then", "sigur": "sure; certainly",
    # unit12 past events
    "fost": "been; was", "mâncat": "eaten (as in 'have eaten')", "băut": "drunk (as in 'have drunk')",
    "a": "has (helper for the past)",
    # unit13 preferences
    "place": "is pleasing (as in \"I like\")", "cafeaua": "the coffee",
    "ceaiul": "the tea", "nu-mi": "not to me (as in \"I don't like\")",
    "pâinea": "the bread", "prefer": "I prefer", "sau": "or",
    # unit14 comparisons
    "mic": "small (masc. and neut.)", "mică": "small (fem.)", "decât": "than",
    # unit15 travel
    "tren": "train", "pleacă": "leaves; departs (he, she, it)", "trenul": "the train",
    "peron": "platform", "peronul": "the platform", "bilet": "ticket",
    "București": "Bucharest", "drum": "road; journey", "bun": "good (masc. and neut.)",
    # unit16 health
    "doare": "hurts", "cap": "head", "capul": "the head", "stomac": "stomach",
    "stomacul": "the stomach", "simt": "I feel", "sunt": "I am",
    "bolnav": "sick (masc.)", "nevoie": "need", "doctor": "doctor (physician)",
    "odihnă": "rest", "multă": "much; a lot of (fem.)",
    # unit17 work
    "lucrează": "he or she works", "inginer": "engineer", "birou": "office",
    "profesoară": "teacher (fem.)", "școală": "school", "lucrați": "you work (formal)",
    # unit18 housing
    "are": "he or she has", "casă": "house", "cameră": "room", "camere": "rooms",
    "dormitor": "bedroom", "bucătărie": "kitchen", "baie": "bathroom",
    "casa": "the house", "apartament": "apartment", "fereastră": "window",
    "apartamentul": "the apartment", "baia": "the bathroom",
    # unit19 weather
    "vreme": "weather", "vremea": "the weather", "soare": "sun; sunny",
    "cald": "warm; hot", "plouă": "it rains", "vânt": "wind", "frig": "cold",
    # unit20 clothing
    "tricou": "t-shirt", "culoare": "color", "roșu": "red", "albastru": "blue",
    "pantaloni": "pants; trousers", "mărime": "size", "pantalonii": "the pants; the trousers",
}

POS_SETS = {
    "proper_noun": split_words("Ana Mihai București"),
    "pronoun": split_words(
        "tu dumneavoastră mă vă te îmi mie se ce care câți"
    ),
    "preposition": split_words("la de cu fără după între lângă vizavi"),
    "particle": split_words("și nu da o un să sau decât"),
    "phrase": split_words("bună salut mulțumesc mi-e nu-mi"),
    "adjective": split_words(
        "doi două trei patru cinci șase șapte opt nouă zece unsprezece "
        "doisprezece treisprezece paisprezece cincisprezece șaisprezece "
        "șaptesprezece optsprezece nouăsprezece douăzeci treizeci patruzeci "
        "cincizeci șaizeci șaptezeci optzeci nouăzeci unu zero mulți tău meu "
        "mea trecută viitoare mare întâi căsătorit scump ieftin mic mică "
        "bolnav multă cald roșu albastru bun mulți"
    ),
    "adverb": split_words(
        "mai bine cum cât când unde astăzi mâine ieri târziu aproape departe "
        "înainte aici acolo apoi acasă atunci sigur"
    ),
    "verb": split_words(
        "faceți faci numesc cheamă pare numiți ai am aveți e este scriu începe "
        "aș dori rog costă vreau pot cumpăr ajung mergeți trezesc mănânc beau "
        "lucrez merg culc mergem fost mâncat băut a place prefer pleacă doare "
        "simt sunt lucrează lucrați are plouă"
    ),
}
POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())

CATEGORY_TAGS: dict[str, list[str]] = {}
for _tag, _words in {
    "ro_weekday": "luni marți miercuri joi vineri sâmbătă duminică",
    "ro_month": (
        "ianuarie februarie martie aprilie iunie iulie august septembrie "
        "octombrie noiembrie decembrie"
    ),
    "ro_family": (
        "mamă tată părinți mama tatăl frate soră frați surori copil copii fiu "
        "fiică familie"
    ),
    "ro_number": (
        "zero unu doi două trei patru cinci șase șapte opt nouă zece unsprezece "
        "doisprezece treisprezece paisprezece cincisprezece șaisprezece "
        "șaptesprezece optsprezece nouăsprezece douăzeci treizeci patruzeci "
        "cincizeci șaizeci șaptezeci optzeci nouăzeci sută"
    ),
}.items():
    for _w in _words.split():
        CATEGORY_TAGS.setdefault(_w, []).append(_tag)

part_of_speech = pos_lookup(POS_SETS)


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
        source_language="en",
        target_language=LANG,
        levels=LEVELS,
        iter_specs=iter_specs,
    )


if __name__ == "__main__":
    raise SystemExit(main())
