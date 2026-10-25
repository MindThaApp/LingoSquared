#!/usr/bin/env python3
"""Idempotently backfill en-ro (Romanian target) lexemes for the "Romanian A1"
course, so en-ro practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: en->X backfill outside the six launch directions.
All plumbing lives in scripts/_target_lexeme_backfill_common.py (see its
docstring for the tag scheme); this file is data only: one hand-written
English gloss and one part of speech per citation form.

Scope: A1 ("en-ro", units 01-20), A2 ("en-ro-a2", units 21-26; session 11) and
B1 ("en-ro-b1", units 01-19; session 12). B2+ is not classified yet; extend
LEVELS and the tables below together. The B1 course must be imported before
this script runs; otherwise it exits with a clear error (see run()).

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
LEVELS = {"a1": "en-ro", "a2": "en-ro-a2", "b1": "en-ro-b1"}

PROPER_NOUNS = {"Ana", "Mihai", "București", "Elena", "Radu", "Diana", "Vasile", "Ionescu"}
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
    # a2 unit21 city hall
    "primărie": "city hall", "primăria": "the city hall",
    "programare": "appointment", "programarea": "the appointment",
    "înscriu": "I register; I enroll", "noua": "the new (fem.)", "adresă": "address",
    "liberă": "free; available (fem.)", "act": "official document",
    "acte": "official documents", "buletin": "ID card", "buletinul": "the ID card",
    "trebuie": "must; it is needed", "actul": "the official document",
    "proprietate": "property; ownership", "formularul": "the form",
    "completați": "you fill in (formal)", "acest": "this (masc.)", "formular": "form",
    "pentru": "for", "înscrierea": "the registration", "contract": "contract",
    "contractul": "the contract", "închiriere": "rental; renting",
    "orele": "the hours", "programările": "the appointments", "până": "until",
    "fac": "they make; they do", "completat": "filled in", "perfect": "perfect",
    "poftim": "here you are", "totul": "everything", "în": "in", "ordine": "order",
    "Elena": "Elena", "puteți": "you can (formal)", "veți": "you will (formal)",
    "primi": "to receive", "confirmarea": "the confirmation", "prin": "by; through",
    "mult": "much; a lot",
    # a2 unit22 opinions
    "cred": "I think; I believe", "crede": "thinks; believes (he; she)",
    "că": "that (introduces a clause)", "trafic": "traffic", "traficul": "the traffic",
    "aglomerat": "crowded", "prea": "too", "multe": "many (fem.)", "mașini": "cars",
    "părere": "opinion", "părerea": "the opinion", "despre": "about",
    "acord": "agreement", "parcul": "the park", "foarte": "very",
    "frumos": "beautiful; nice (masc.)", "oraș": "city; town", "orașul": "the city",
    "opinia": "the opinion", "dar": "but", "interesant": "interesting",
    "parcuri": "parks", "familii": "families", "dreptate": "being right",
    "plăcere": "pleasure",
    # a2 unit23 bank
    "cont": "account", "curent": "current; checking (of an account)",
    "deschid": "I open", "deschis": "opened", "necesare": "necessary (plural)",
    "dovadă": "proof", "dovada": "the proof", "adresei": "of the address",
    "deschide": "to open", "precum": "such as", "informații": "information",
    "card": "card", "cardul": "the card", "va": "will (he; she; it)", "sosi": "to arrive",
    "zile": "days", "lucrătoare": "working (fem. plural)",
    "suficient": "enough; sufficient", "semnătură": "signature", "Radu": "Radu",
    "primesc": "I receive; I get", "ajutor": "help",
    # a2 unit24 doctor
    "doctoriță": "doctor (woman)", "tare": "hard; severe", "ales": "chosen (in 'especially')",
    "confirmată": "confirmed (fem.)", "rugăm": "we ask (in 'we ask you to')",
    "veniți": "you come (formal)", "minute": "minutes", "devreme": "early",
    "doctorița": "the doctor (woman)", "Vasile": "Vasile", "recomand": "I recommend",
    "medicament": "medicine", "ori": "times", "pe": "on; per", "timp": "time",
    "control": "check-up; follow-up visit", "înțeleg": "I understand",
    "întorc": "I return", "doar": "only", "dacă": "if", "durerea": "the pain",
    "trece": "passes; goes away", "însănătoșire": "recovery", "grabnică": "speedy (fem.)",
    # a2 unit25 housing problems
    "robinet": "faucet; tap", "robinetul": "the faucet", "din": "from; of",
    "curge": "leaks; flows", "meșter": "repairman; craftsman",
    "poate": "can; may (he; she; it)", "veni": "to come", "reparație": "repair",
    "curând": "soon", "posibil": "possible", "douăsprezece": "twelve",
    "reparația": "the repair", "meșterul": "the repairman", "suna": "to call (by phone)",
    "rău": "bad; sorry", "aud": "I hear", "asta": "this; that",
    "ați": "you have (formal, helper for the past)", "observat": "noticed",
    "problema": "the problem", "administratorul": "the administrator",
    "Ionescu": "Ionescu", "fie": "be (as in 'must be')", "fiți": "you be (formal)",
    # a2 unit26 interview
    "Diana": "Diana", "experiență": "experience", "domeniu": "field; area",
    "lucrat": "worked", "ca": "as", "tehniciană": "technician (woman)",
    "sunteți": "you are (formal)", "disponibilă": "available (fem.)",
    "avea": "to have", "întrebare": "question", "program": "schedule; program",
    "căutăm": "we are looking for", "tehnician": "technician (man)",
    "complet": "full; complete", "ore": "hours", "disponibil": "available (masc.)",
    "vom": "we will", "contacta": "to contact", "întrebări": "questions",
    "mine": "me (after 'for')", "programul": "the schedule",
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
POS_SETS["verb"] |= split_words(
    "înscriu trebuie completați puteți veți primi cred crede deschid deschide "
    "va sosi primesc rugăm veniți recomand înțeleg întorc trece curge poate "
    "veni suna aud ați observat fie fiți lucrat sunteți avea căutăm vom contacta fac"
)
POS_SETS["adjective"] |= split_words(
    "noua liberă acest completat perfect aglomerat multe frumos interesant "
    "curent necesare lucrătoare suficient ales confirmată grabnică posibil "
    "disponibilă disponibil complet deschis douăsprezece"
)
POS_SETS["adverb"] |= split_words("mult prea foarte devreme curând rău doar tare")
POS_SETS["pronoun"] |= split_words("totul asta mine")
POS_SETS["preposition"] |= split_words("pentru până prin despre din pe ca precum în")
POS_SETS["particle"] |= split_words("că dacă dar")
POS_SETS["phrase"] |= split_words("poftim")
POS_SETS["proper_noun"] = POS_SETS["proper_noun"] | {"Elena", "Radu", "Diana", "Vasile", "Ionescu"}
# B1 (session 12): tokens first taught in the Romanian B1 course. Format:
# token: (part-of-speech code, English gloss). Codes: n noun, v verb, a
# adjective, d adverb, r pronoun, p preposition, t particle, N proper noun.
# Subjunctive forms are glossed "(that) he or she ..." so a bare-word prompt
# names one form; past participles carry no person.
_B1_POS_CODES = {
    "n": "noun", "v": "verb", "a": "adjective", "d": "adverb", "r": "pronoun",
    "p": "preposition", "t": "particle", "h": "phrase", "N": "proper_noun",
}
B1_ENTRIES: dict[str, tuple[str, str]] = {
    'plec': ('v', 'I leave; I go'),
    'pleci': ('v', 'you leave (informal)'),
    'azi': ('d', 'today'),
    'plece': ('v', '(that) he or she leaves'),
    'plecăm': ('v', 'we leave'),
    'noi': ('r', 'we'),
    'plecați': ('v', 'you leave (formal or plural)'),
    'ei': ('r', 'they (masc.)'),
    'împreună': ('d', 'together'),
    'ar': ('v', 'would (helper for "would have")'),
    'fi': ('v', 'to be'),
    'trebuit': ('v', 'had to; needed to'),
    'ocupat': ('a', 'busy (masc.)'),
    'raport': ('n', 'report'),
    'termin': ('v', 'I finish'),
    'terminați': ('v', 'you finish (formal or plural)'),
    'termine': ('v', '(that) he or she finishes'),
    'important': ('a', 'important (masc.)'),
    'deja': ('d', 'already'),
    'eu': ('r', 'I'),
    'raportul': ('n', 'the report'),
    'întârzii': ('v', 'I run late; you run late'),
    'teme': ('n', 'homework (plural)'),
    'cine': ('r', 'who'),
    'temele': ('n', 'the homework'),
    'anul': ('n', 'the year'),
    'trecut': ('a', 'last; past'),
    'ocupată': ('a', 'busy (fem.)'),
    'acesta': ('a', 'this (after the noun)'),
    'ajută': ('v', 'he or she helps'),
    'singură': ('a', 'alone (fem.)'),
    'lucreze': ('v', '(that) he or she works'),
    'ceară': ('v', '(that) he or she asks for'),
    'corectat': ('v', 'to be corrected; to be graded'),
    'ea': ('r', 'she'),
    'organizarea': ('n', 'the organization'),
    'așa': ('d', 'so; like that'),
    'stresată': ('a', 'stressed (fem.)'),
    'întârzie': ('v', 'he or she is late'),
    'totuși': ('d', 'however; still'),
    'poți': ('v', 'you can (informal)'),
    'vorbesc': ('v', 'I speak'),
    'vorbești': ('v', 'you speak (informal)'),
    'engleză': ('n', 'English (language)'),
    'franceză': ('n', 'French (language)'),
    'putem': ('v', 'we can'),
    'vorbească': ('v', '(that) he or she speaks'),
    'vorbim': ('v', 'we speak'),
    'vorbiți': ('v', 'you speak (formal or plural)'),
    'spaniolă': ('n', 'Spanish (language)'),
    'el': ('r', 'he'),
    'putut': ('v', 'been able to'),
    'putea': ('v', 'to be able (as in "I would be able")'),
    'practică': ('n', 'practice'),
    'client': ('n', 'client'),
    'clientul': ('n', 'the client'),
    'nou': ('a', 'new (masc.)'),
    'problemă': ('n', 'problem'),
    'ajut': ('v', 'I help'),
    'clienți': ('n', 'clients'),
    'străini': ('a', 'foreign (masc. plural)'),
    'puțin': ('d', 'a little'),
    'practicăm': ('v', 'we practice'),
    'avem': ('v', 'we have'),
    'acum': ('d', 'now'),
    'biroul': ('n', 'the office'),
    'lui': ('t', 'of (before a masculine name)'),
    'practicat': ('v', 'practiced'),
    'probleme': ('n', 'problems'),
    'mulțumit': ('a', 'pleased; satisfied (masc.)'),
    'clienților': ('n', 'of the clients'),
    'clienții': ('n', 'the clients'),
    'puțină': ('a', 'a little (fem.)'),
    'ajute': ('v', '(that) he or she helps'),
    'altă': ('a', 'another (fem.)'),
    'limbă': ('n', 'language'),
    'fapt': ('n', 'fact'),
    'voi': ('v', 'I will'),
    'merge': ('v', 'to go'),
    'vei': ('v', 'you will (informal)'),
    'vor': ('v', 'they will'),
    'au': ('v', 'they have'),
    'planuri': ('n', 'plans'),
    'weekend': ('n', 'weekend'),
    'munte': ('n', 'mountain'),
    'rămâne': ('v', 'to stay'),
    'liber': ('a', 'free (masc.)'),
    'lucra': ('v', 'to work (as in "I will work")'),
    'data': ('n', 'the time; the occasion'),
    'studia': ('v', 'to study'),
    'germana': ('n', 'German (language)'),
    'viitor': ('a', 'next; future (masc.)'),
    'nimic': ('r', 'nothing'),
    'învăța': ('v', 'to learn'),
    'repede': ('d', 'quickly'),
    'momentan': ('d', 'at the moment'),
    'probabil': ('d', 'probably'),
    'lucrul': ('n', 'the work; working'),
    'eficient': ('a', 'efficient'),
    'productiv': ('a', 'productive'),
    'importantă': ('a', 'important (fem.)'),
    'echipa': ('n', 'the team'),
    'comunicarea': ('n', 'the communication'),
    'ușoară': ('a', 'easy (fem.)'),
    'spus': ('v', 'said'),
    'ambele': ('a', 'both (fem.)'),
    'avantaje': ('n', 'advantages'),
    'pierdem': ('v', 'we lose; we waste'),
    'drumul': ('n', 'the way; the commute'),
    'greu': ('a', 'hard; difficult'),
    'comunicăm': ('v', '(that) we communicate'),
    'directă': ('a', 'direct (fem.)'),
    'variante': ('n', 'options'),
    'bune': ('a', 'good (fem. plural)'),
    'an': ('n', 'year'),
    'dianei': ('N', 'of Diana'),
    'soluția': ('n', 'the solution'),
    'sarcini': ('n', 'tasks'),
    'individuale': ('a', 'individual (fem. plural)'),
    'întâlniri': ('n', 'meetings'),
    'față': ('n', 'face; front'),
    'soluție': ('n', 'solution'),
    'colegi': ('n', 'colleagues'),
    'cea': ('t', 'the (fem., before "best")'),
    'amestec': ('n', 'mix'),
    'ideea': ('n', 'the idea'),
    'echipă': ('n', 'team'),
    'propune': ('v', 'to propose'),
    'ne': ('r', 'us; ourselves'),
    'întâlnim': ('v', '(that) we meet'),
    'ședința': ('n', 'the meeting'),
    'ordinea': ('n', 'the order'),
    'proiectul': ('n', 'the project'),
    'puncte': ('n', 'points'),
    'propunerea': ('n', 'the proposal'),
    'trimiteți': ('v', '(that) you send (formal or plural)'),
    'desigur': ('d', 'of course'),
    'îl': ('r', 'him; it (object)'),
    'trimit': ('v', 'I send'),
    'v': ('r', 'you (formal, short object form)'),
    'ruga': ('v', 'to ask (as in "I would ask")'),
    'verificați': ('v', '(that) you check (formal or plural)'),
    'termenul': ('n', 'the deadline'),
    'limită': ('n', 'limit'),
    'verific': ('v', 'I check'),
    'trimite': ('v', 'he or she sends'),
    'bineînțeles': ('d', 'of course; naturally'),
    'vedem': ('v', 'we see'),
    'tuturor': ('r', 'to everyone'),
    'cere': ('v', 'he or she asks for'),
    'mesaj': ('n', 'message'),
    'continuăm': ('v', '(that) we continue'),
    'aceeași': ('a', 'the same (fem.)'),
    'trimis': ('v', 'sent'),
    'stimă': ('n', 'esteem (as in "regards")'),
    'ședință': ('n', 'meeting'),
    'mergeam': ('v', 'I was going'),
    'spre': ('p', 'toward'),
    'dat': ('v', 'given; ran (into)'),
    'stradă': ('n', 'street'),
    'colega': ('n', 'the colleague (fem.)'),
    'descrie': ('v', 'describes'),
    'acțiunea': ('n', 'the action'),
    'fond': ('n', 'background'),
    'evenimentul': ('n', 'the event'),
    'principal': ('a', 'main (masc.)'),
    'imperfectul': ('n', 'the imperfect (tense)'),
    'perfectul': ('n', 'the perfect (tense)'),
    'compus': ('a', 'compound'),
    'era': ('v', 'he or she was'),
    'întârziată': ('a', 'late (fem.)'),
    'cauza': ('n', 'the cause'),
    'traficului': ('n', 'of the traffic'),
    'aceea': ('r', 'that (as in "that is why")'),
    'întârziat': ('v', 'was late'),
    'vorbirea': ('n', 'the speech'),
    'indirectă': ('a', 'indirect (fem.)'),
    'română': ('n', 'Romanian (language)'),
    'păstra': ('v', 'to keep'),
    'timpul': ('n', 'the tense; the time'),
    'verbului': ('n', 'of the verb'),
    'original': ('a', 'original'),
    'mers': ('v', 'gone'),
    'povestit': ('v', 'told (a story)'),
    'văzut': ('v', 'seen'),
    's': ('r', 'himself; herself (reflexive, in "s-a")'),
    'întâmplat': ('v', 'happened'),
    'serios': ('d', 'seriously; really'),
    'groaznic': ('a', 'terrible'),
    'sper': ('v', 'I hope'),
    'ajuns': ('v', 'arrived'),
    'obișnuită': ('a', 'ordinary (fem.)'),
    'mergea': ('v', 'he or she was going'),
    'toată': ('a', 'whole (fem.)'),
    'zona': ('n', 'the area'),
    'acea': ('a', 'that (fem.)'),
    'cele': ('r', 'the (fem. plural, in "in the end")'),
    'urmă': ('n', 'end; trace (as in "in the end")'),
    'computerul': ('n', 'the computer'),
    'blochează': ('v', 'freezes; crashes'),
    'des': ('d', 'often'),
    'câteva': ('a', 'a few'),
    'locul': ('n', 'the place'),
    'it': ('n', 'IT'),
    'reporniți': ('v', '(that) you restart (formal or plural)'),
    'condiționalului': ('n', 'of the conditional'),
    'optativ': ('n', 'optative (mood)'),
    'folosite': ('a', 'used (fem. plural)'),
    'sfat': ('n', 'advice'),
    'condiție': ('n', 'condition'),
    'idee': ('n', 'idea'),
    'încerca': ('v', 'to try'),
    'încercat': ('v', 'tried'),
    'funcționat': ('v', 'worked (functioned)'),
    'trebui': ('v', 'to be necessary (as in "should")'),
    'funcționează': ('v', 'works (functions)'),
    'dă': ('v', 'gives'),
    'prima': ('a', 'first (fem.)'),
    'acceptă': ('v', 'accepts'),
    'al': ('t', 'the (before "second")'),
    'doilea': ('a', 'second (masc.)'),
    'anei': ('N', 'of Ana'),
    'imprimanta': ('n', 'the printer'),
    'coletul': ('n', 'the package'),
    'deteriorat': ('a', 'damaged'),
    'lipsește': ('v', 'is missing'),
    'piesă': ('n', 'part; piece'),
    'colet': ('n', 'package'),
    'reclamație': ('n', 'complaint'),
    'sunat': ('v', 'called'),
    'nimeni': ('r', 'nobody'),
    'm': ('r', 'me (short object form, in "m-a")'),
    'ajutat': ('v', 'helped'),
    'email': ('n', 'email'),
    'primit': ('v', 'received'),
    'răspuns': ('n', 'answer'),
    'rambursare': ('n', 'refund'),
    'produs': ('n', 'product'),
    'rezolvare': ('n', 'resolution'),
    'doriți': ('v', 'you wish (formal or plural)'),
    'forma': ('n', 'the form'),
    'politicoasă': ('a', 'polite (fem.)'),
    'folosită': ('a', 'used (fem.)'),
    'concretă': ('a', 'concrete (fem.)'),
    'trimitem': ('v', 'we send'),
    'aceasta': ('r', 'this (fem.)'),
    'exact': ('d', 'exactly'),
    'scaunul': ('n', 'the chair'),
    'stricat': ('a', 'broken'),
    'scaun': ('n', 'chair'),
    'lună': ('n', 'month'),
    'destul': ('d', 'quite; enough'),
    'condiționalul': ('n', 'the conditional'),
    'exprimă': ('v', 'expresses'),
    'regret': ('n', 'regret'),
    'obligație': ('n', 'obligation'),
    'neîndeplinită': ('a', 'unfulfilled (fem.)'),
    'vrut': ('v', 'wanted'),
    'regretă': ('v', 'he or she regrets'),
    'facă': ('v', '(that) he or she does'),
    'dorință': ('n', 'wish'),
    'împlinit': ('a', 'fulfilled'),
    'diferit': ('a', 'different (masc.)'),
    'corect': ('a', 'correct'),
    'verifica': ('v', 'to check'),
    'regretul': ('n', 'the regret'),
    'urmat': ('v', 'followed'),
    'intenție': ('n', 'intention'),
    'clară': ('a', 'clear (fem.)'),
    'uitat': ('v', 'forgot; forgotten'),
    'notez': ('v', '(that) I note down'),
    'agendă': ('n', 'planner'),
    'agenda': ('n', 'the planner'),
    'întâlnire': ('n', 'meeting; appointment'),
    'programată': ('a', 'scheduled (fem.)'),
    'fixă': ('a', 'fixed (fem.)'),
    'viitorul': ('n', 'the future'),
    'plan': ('n', 'plan'),
    'fix': ('a', 'fixed (masc.)'),
    'stabilit': ('a', 'set; established'),
    'gând': ('n', 'thought; idea'),
    'asemenea': ('d', 'likewise (in "also")'),
    'ceva': ('r', 'something'),
    'plănuiți': ('v', 'you plan (formal or plural)'),
    'încă': ('d', 'still; yet'),
    'deosebire': ('n', 'difference'),
    'pleca': ('v', 'to leave'),
    'combinat': ('v', 'combined'),
    'predicție': ('n', 'prediction'),
    'nesigură': ('a', 'uncertain (fem.)'),
    'diferită': ('a', 'different (fem.)'),
    'planul': ('n', 'the plan'),
    'intenția': ('n', 'the intention'),
    'întreabă': ('v', 'asks'),
    'scurt': ('a', 'short (masc.)'),
    'decis': ('v', 'decided'),
    'amâne': ('v', '(that) he or she postpones'),
    'anunță': ('v', 'announces'),
    'rezumat': ('n', 'summary'),
    'condensat': ('a', 'condensed'),
    'versiunea': ('n', 'the version'),
    'scurtă': ('a', 'short (fem.)'),
    'unei': ('t', 'of a (fem.)'),
    'povești': ('n', 'stories'),
    'lungi': ('a', 'long (plural)'),
    'principală': ('a', 'main (fem.)'),
    'detaliu': ('n', 'detail'),
    'separă': ('v', 'separates'),
    'detalii': ('n', 'details'),
    'durat': ('v', 'lasted'),
    'vorbit': ('v', 'spoken; talked'),
    'buget': ('n', 'budget'),
    'întrebat': ('v', 'asked'),
    'păstrează': ('v', 'keeps'),
    'evenimentelor': ('n', 'of the events'),
    'moment': ('n', 'moment'),
    'discutat': ('v', 'discussed'),
    'afară': ('d', 'outside; left out'),
    'ploua': ('v', 'to rain (as in "it would rain")'),
    'citit': ('v', 'read (past participle)'),
    'articol': ('n', 'article'),
    'lung': ('a', 'long (masc.)'),
    'articolul': ('n', 'the article'),
    'construiască': ('v', '(that) he or she builds'),
    'școala': ('n', 'the school'),
    'studiază': ('v', 'he or she studies'),
    'engleza': ('n', 'English (language)'),
    'obțină': ('v', '(that) he or she gets'),
    'promovare': ('n', 'promotion'),
    'conjunctiv': ('n', 'subjunctive (mood)'),
    'scopul': ('n', 'the purpose'),
    'acțiuni': ('n', 'actions'),
    'face': ('v', 'makes; does'),
    'lucru': ('n', 'thing; work'),
    'economisească': ('v', '(that) he or she saves'),
    'bani': ('n', 'money'),
    'economisesc': ('v', 'I save'),
    'persoana': ('n', 'the person'),
    'conjunctivul': ('n', 'the subjunctive'),
    'formă': ('n', 'form'),
    'indicativul': ('n', 'the indicative'),
    'treia': ('a', 'third (fem.)'),
    'schimbă': ('v', 'changes'),
    'cumpără': ('v', 'buys'),
    'cumpere': ('v', '(that) he or she buys'),
    'citesc': ('v', 'I read'),
    'cărți': ('n', 'books'),
    'limba': ('n', 'the language'),
    'abstract': ('a', 'abstract'),
    'obiect': ('n', 'object'),
    'concret': ('a', 'concrete (masc.)'),
    'studiați': ('v', 'you study (formal or plural)'),
    'fiecare': ('r', 'each; every'),
    'seară': ('n', 'evening'),
    'studiez': ('v', 'I study'),
    'obțin': ('v', 'I get; I obtain'),
    'atât': ('d', 'so much'),
    'îi': ('r', 'them (object); to him or her'),
    'scopurile': ('n', 'the goals'),
    'lor': ('r', 'their'),
    'introduce': ('v', 'introduces'),
    'reală': ('a', 'real (fem.)'),
    'parte': ('n', 'part'),
    'condiția': ('n', 'the condition'),
    'doua': ('a', 'second (fem.)'),
    'rezultatul': ('n', 'the result'),
    'rămân': ('v', 'I stay'),
    'negăm': ('v', 'we negate'),
    'afirmativ': ('a', 'affirmative'),
    'negativ': ('a', 'negative'),
    'rămânem': ('v', 'we stay'),
    'situație': ('n', 'situation'),
    'condiții': ('n', 'conditions'),
    'opuse': ('a', 'opposite (plural)'),
    'rezultate': ('n', 'results'),
    'diferite': ('a', 'different (plural)'),
    'termină': ('v', 'finishes'),
    'prezentarea': ('n', 'the presentation'),
    'dimineață': ('n', 'morning'),
    'obicei': ('n', 'habit'),
    'întâmplă': ('v', 'happens'),
    'e-mailurile': ('n', 'the emails'),
    'singur': ('a', 'alone (masc.)'),
    'eveniment': ('n', 'event'),
    'terminat': ('v', 'finished'),
    'ceea': ('r', 'that which'),
    's-a': ('v', 'has (reflexive past helper)'),
    'începuse': ('v', 'had begun'),
    'făcut': ('v', 'done; made'),
    'intrat': ('v', 'entered'),
    'ascultat': ('v', 'listened'),
    'restul': ('n', 'the rest'),
    'discuției': ('n', 'of the discussion'),
    'l-a': ('v', 'has him or it (past helper)'),
    'raportează': ('v', 'reports'),
    'zis': ('v', 'said'),
    'altcineva': ('r', 'someone else'),
    'repetăm': ('v', 'we repeat'),
    'cuvintele': ('n', 'the words'),
    'exacte': ('a', 'exact (plural)'),
    'tip': ('n', 'type'),
    'exactă': ('a', 'exact (fem.)'),
    'scris': ('v', 'written'),
    'ajunge': ('v', 'arrives'),
    'raporta': ('v', 'to report'),
    'răspunsuri': ('n', 'answers'),
    'gata': ('a', 'ready'),
    'prezentare': ('n', 'presentation'),
    'deși': ('t', 'although'),
    'convenabil': ('a', 'convenient'),
    'recunoaște': ('v', 'acknowledges'),
    'punct': ('n', 'point'),
    'valid': ('a', 'valid'),
    'celeilalte': ('a', 'of the other (fem.)'),
    'părți': ('n', 'sides; parts'),
    'spune': ('v', 'says'),
    'propria': ('a', 'own (fem.)'),
    'toate': ('a', 'all (fem. plural)'),
    'acestea': ('r', 'these'),
    'economisește': ('v', 'saves'),
    'puternic': ('a', 'strong'),
    'leagă': ('v', 'links'),
    'într-un': ('p', 'in a (masc.)'),
    'argument': ('n', 'argument'),
    'simplu': ('a', 'simple'),
    'ușor': ('a', 'easy; easily'),
    'colegii': ('n', 'the colleagues'),
    'uneori': ('d', 'sometimes'),
    'liniștea': ('n', 'the quiet'),
    'legate': ('a', 'linked (fem. plural)'),
    'alți': ('a', 'other (masc. plural)'),
    'preferă': ('v', 'prefers'),
    'citi': ('v', 'to read (as in "I would read")'),
    'condițional': ('a', 'conditional'),
    'prezent': ('n', 'present (tense)'),
    'arată': ('v', 'shows'),
    'ipotetică': ('a', 'hypothetical (fem.)'),
    'nereală': ('a', 'unreal (fem.)'),
    'bogată': ('a', 'rich (fem.)'),
    'călători': ('v', 'to travel'),
    'observați': ('v', 'you notice (formal or plural)'),
    'apare': ('v', 'appears'),
    'ale': ('t', 'of (plural possessive)'),
    'propoziției': ('n', 'of the clause'),
    'rezultat': ('n', 'result'),
    'ipoteză': ('n', 'hypothesis'),
    'prefera': ('v', 'to prefer'),
    'nicio': ('a', 'no; not a single (fem.)'),
    'propoziție': ('n', 'clause'),
    'ipotetic': ('a', 'hypothetical (masc.)'),
    'înmoaie': ('v', 'softens'),
    'preferință': ('n', 'preference'),
    'sugera': ('v', 'to suggest'),
    'începem': ('v', '(that) we begin'),
    'actualizarea': ('n', 'the update'),
    'proiectului': ('n', 'of the project'),
    'într-o': ('p', 'in a (fem.)'),
    'cel': ('t', 'the (masc., before "most")'),
    'imperativ': ('n', 'imperative'),
    'direct': ('a', 'direct (masc.)'),
    'spuneți': ('v', '(that) you say (formal or plural)'),
    'stadiul': ('n', 'the status; the stage'),
    'raportului': ('n', 'of the report'),
    'formularea': ('n', 'the wording'),
    'cerere': ('n', 'request'),
    'formală': ('a', 'formal (fem.)'),
    'potrivită': ('a', 'suitable (fem.)'),
    'actualizare': ('n', 'update'),
    'context': ('n', 'context'),
    'profesional': ('a', 'professional (masc.)'),
    'amânare': ('n', 'postponement'),
    'mulțumire': ('n', 'thanks'),
    'încheie': ('v', 'ends'),
    'schimbul': ('n', 'the exchange'),
    'replici': ('n', 'lines of dialogue'),
    'confirma': ('v', 'to confirm'),
    'combină': ('v', 'combines'),
    'fapte': ('n', 'facts'),
    'subiect': ('n', 'subject'),
    'genul': ('n', 'the gender'),
    'antecedentului': ('n', 'of the antecedent'),
    'lucrăm': ('v', 'we work'),
    'modern': ('a', 'modern'),
    'colegul': ('n', 'the colleague (masc.)'),
    'propoziția': ('n', 'the clause'),
    'relativă': ('a', 'relative (fem.)'),
    'prepoziție': ('n', 'preposition'),
    'stă': ('v', 'stays; stands'),
    'cărui': ('r', 'whose (masc.)'),
    'cărei': ('r', 'whose (fem.)'),
    'carte': ('n', 'book'),
    'preferată': ('a', 'favorite (fem.)'),
    'proiecte': ('n', 'projects'),
    'învață': ('v', 'learns'),
    'posedat': ('a', 'possessed'),
    'masculin': ('a', 'masculine'),
    'neutru': ('a', 'neuter'),
    'feminin': ('a', 'feminine'),
    'singurele': ('a', 'the only (fem. plural)'),
    'forme': ('n', 'forms'),
    'gen': ('n', 'gender'),
    'cui': ('r', 'whom; whose'),
    'vorbitorului': ('n', 'of the speaker'),
    'iar': ('t', 'and; while'),
    'învăț': ('v', 'I learn'),
}
for _tok, (_code, _gloss) in B1_ENTRIES.items():
    GLOSSES[_tok] = _gloss
    _pos = _B1_POS_CODES[_code]
    if _pos != "noun":
        POS_SETS[_pos] = POS_SETS[_pos] | {_tok}

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

# A2 re-teaches a few A1 tokens in a different sense; the global gloss would
# be shown to the learner as the correct answer, so override per unit file.
GLOSS_OVERRIDES = {
    ("a2_unit21_birocratie", "poștă"): "post office; mail",
    ("a2_unit22_opinii", "sunt"): "I am; there are",
    ("a2_unit25_probleme_locuinta", "fiu"): "I be (as in 'I must be')",
    ("a2_unit25_probleme_locuinta", "înainte"): "before; ahead",
    # B1 re-teaches a few earlier tokens in a different sense.
    ("b1_unit01_necessity", "pe"): "(marks a person as the object)",
    ("b1_unit06_narrative", "mare"): "big; heavy",
    ("b1_unit06_narrative", "ca"): "so; as",
    ("b1_unit07_sfaturi", "fac"): "(that) I do",
    ("b1_unit07_sfaturi", "dată"): "time (occasion)",
    ("b1_unit16_nuante", "ori"): "times (as in \"most of the time\")",
    ("b1_unit18_intalniri_profesionale", "scriu"): "I write",
}
POS_OVERRIDES = {
    ("a2_unit25_probleme_locuinta", "fiu"): "verb",
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
            gloss_overrides=GLOSS_OVERRIDES,
            pos_overrides=POS_OVERRIDES,
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
