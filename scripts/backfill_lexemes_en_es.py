#!/usr/bin/env python3
"""Idempotently backfill en-es (Spanish target) lexemes for the "Spanish A1"
course, so en-es practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: first en->X backfill outside the six launch
directions. All plumbing lives in scripts/_target_lexeme_backfill_common.py
(see its docstring for the tag scheme); this file is data only:
one hand-written English gloss and one part of speech per citation form.

Scope: A1 only (the "en-es" manifest group, units 01-15). A2+ is not
classified yet; extend LEVELS and the tables below together.

Glossing rules followed here (PRACTICE_PACK_RECIPE.md §0.1, §6.6):
* the gloss is the sense the unit actually teaches at first sight; a token
  with two taught senses gets both ("cooking; kitchen"),
* inflected forms say who they belong to ("you have (informal)"), so a
  bare-word translation prompt names one form,
* gender pairs are glossed "(masc.)"/"(fem.)" so the two are never
  interchangeable answers.

Sentence-initial capitals fold to lowercase; the proper nouns below keep
their capital.

Run (after the en-es course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_es.py

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

LANG = "es"
LEVELS = {"a1": "en-es"}

PROPER_NOUNS = {
    "Elena", "Mateo", "Lucía", "Diego", "Carlos", "Ana", "México", "Colombia",
    "Londres", "España", "Barcelona", "Sofía", "Madrid", "Rosa",
}
_PROPER_BY_LOWER = {p.lower(): p for p in PROPER_NOUNS}


def normalize(token: str) -> str:
    lower = token.lower()
    return _PROPER_BY_LOWER.get(lower, lower)


GLOSSES: dict[str, str] = {
    # unit01 greetings
    "usted": "you (formal)", "tú": "you (informal)", "cómo": "how",
    "está": "is; are (formal you), for states and places", "estás": "you are (informal), for states and places",
    "bien": "well; fine", "gracias": "thank you", "muy": "very", "y": "and",
    "hola": "hello", "buenos": "good (masc. plural)", "días": "days",
    "buenas": "good (fem. plural)", "tardes": "afternoons", "noches": "nights",
    "adiós": "goodbye", "hasta": "until", "luego": "later", "nos": "us; each other",
    "vemos": "we see", "que": "that", "tenga": "may you have (formal)",
    "un": "a; an (masc.)", "buen": "good (before a masc. noun)", "día": "day",
    "se": "himself; herself; yourself (formal)", "llama": "is called",
    "me": "me; myself", "llamo": "I am called", "Lucía": "Lucía",
    "te": "you; yourself (informal)", "llamas": "you are called (informal)",
    "soy": "I am", "Diego": "Diego", "mucho": "much; a lot", "gusto": "pleasure",
    "igualmente": "likewise", "este": "this (masc.)", "es": "is",
    "Carlos": "Carlos", "esta": "this (fem.)", "Ana": "Ana", "de": "of; from",
    "dónde": "where (question)", "México": "Mexico", "eres": "you are (informal)",
    "Colombia": "Colombia", "vivo": "I live", "en": "in; at; on",
    "Londres": "London", "habla": "speaks; you speak (formal)",
    "español": "Spanish (language)", "sí": "yes", "poco": "little; a little",
    "todavía": "still", "estoy": "I am (a state or place)", "aprendiendo": "learning",
    "su": "your (formal); his; her", "primera": "first (fem.)",
    "vez": "time (occasion)", "aquí": "here", "tu": "your (informal)", "mi": "my",
    "vengo": "I come", "al": "to the", "taller": "workshop",
    "cocina": "cooking; kitchen", "yo": "I", "también": "also; too",
    "gusta": "is pleasing (used to say you like something)", "cocinar": "to cook",
    "qué": "what; how (exclamation)", "Elena": "Elena", "Mateo": "Mateo",
    "pero": "but", "España": "Spain", "bueno": "good; well (okay)",
    "dentro": "inside",
    # unit02 numbers
    "cero": "zero", "uno": "one", "dos": "two", "tres": "three", "cuatro": "four",
    "cinco": "five", "seis": "six", "siete": "seven", "ocho": "eight",
    "nueve": "nine", "diez": "ten", "once": "eleven", "doce": "twelve",
    "trece": "thirteen", "catorce": "fourteen", "quince": "fifteen",
    "veinte": "twenty", "treinta": "thirty", "cien": "one hundred",
    "cuántos": "how many", "años": "years", "tienes": "you have (informal)",
    "tengo": "I have", "veintiocho": "twenty-eight",
    "tiene": "has; you have (formal)", "cuál": "which; what",
    "número": "number", "teléfono": "phone", "el": "the (masc.)",
    "puedes": "you can (informal)", "repetir": "to repeat",
    "por": "for; by; through", "favor": "favor", "claro": "of course; sure",
    "necesito": "I need", "huevos": "eggs", "necesitas": "you need (informal)",
    "tazas": "cups", "harina": "flour", "media": "half (fem.)", "taza": "cup",
    "azúcar": "sugar", "la": "the (fem.)", "mesa": "table",
    "para": "for; in order to", "receta": "recipe", "como": "about; like",
    "perfecto": "perfect", "oye": "hey; listen", "así": "so; that way",
    "escribo": "I write", "próxima": "next (fem.)", "clase": "class",
    "una": "a; an; one (fem.)", "pregunta": "question", "más": "more",
    # unit03 family
    "madre": "mother", "padre": "father", "hermano": "brother",
    "hermana": "sister", "hijo": "son", "hija": "daughter", "padres": "parents",
    "hermanos": "siblings; brothers", "familia": "family", "hermanas": "sisters",
    "grande": "big", "pequeña": "small (fem.)", "abuelo": "grandfather",
    "abuela": "grandmother", "abuelos": "grandparents", "tío": "uncle",
    "tía": "aunt", "primo": "cousin (male)", "prima": "cousin (female)",
    "mis": "my (plural)", "somos": "we are", "casa": "home; house",
    "muchos": "many (masc.)", "primos": "cousins", "vives": "you live (informal)",
    "cerca": "near; close", "tus": "your (informal, plural)", "con": "with",
    "viven": "they live", "Barcelona": "Barcelona", "menor": "younger",
    "Sofía": "Sofía", "vive": "lives", "sus": "his; her; their (plural)",
    "mira": "look", "estos": "these", "son": "are (they are)",
    "bonito": "nice; pretty", "no": "no; not", "ellos": "they",
    "hablamos": "we talk", "cada": "each; every", "semana": "week",
    "entiendo": "I understand", "tener": "to have", "a": "to; at",
    # unit04 dates
    "lunes": "Monday", "martes": "Tuesday", "miércoles": "Wednesday",
    "jueves": "Thursday", "viernes": "Friday", "sábado": "Saturday",
    "domingo": "Sunday", "hoy": "today", "los": "the (masc. plural)",
    "enero": "January", "febrero": "February", "marzo": "March",
    "abril": "April", "mayo": "May", "junio": "June", "julio": "July",
    "agosto": "August", "septiembre": "September", "octubre": "October",
    "noviembre": "November", "diciembre": "December", "cumpleaños": "birthday",
    "fecha": "date", "veintidós": "twenty-two", "cuándo": "when",
    "felicidades": "congratulations; happy birthday",
    "después": "after; afterwards", "hay": "there is; there are",
    "veintinueve": "twenty-nine", "termina": "ends", "del": "of the",
    "cierto": "certain; true", "tuyo": "yours (informal)",
    # unit05 time
    "hora": "hour; time", "las": "the (fem. plural)", "cuarto": "quarter",
    "menos": "minus; less", "mañana": "morning; tomorrow",
    "tarde": "afternoon; late", "noche": "night; evening", "empieza": "starts",
    "eso": "that", "antes": "before", "acuerdo": "agreement",
    "ven": "they see", "siguiente": "next; following",
    "almorzar": "to have lunch", "hambre": "hunger", "comemos": "we eat",
    "buena": "good (fem.)", "idea": "idea", "restaurante": "restaurant",
    "genial": "great", "entonces": "then; so",
    # unit06 food
    "sándwich": "sandwich", "ensalada": "salad", "sopa": "soup",
    "agua": "water", "café": "coffee", "quiero": "I want",
    "mí": "me (after a preposition)", "quieres": "you want (informal)",
    "comer": "to eat", "menú": "menu", "podemos": "we can", "ver": "to see",
    "provecho": "benefit", "postre": "dessert", "pastel": "cake",
    "cuenta": "bill; check", "o": "or", "incluido": "included",
    "quieren": "you want (plural); they want", "algo": "something",
    "comida": "food; meal",
    # unit07 shopping
    "mercado": "market", "fruta": "fruit", "verdura": "vegetable",
    "fresca": "fresh (fem.)", "pan": "bread", "cuánto": "how much",
    "cuesta": "costs", "docena": "dozen", "kilo": "kilo",
    "tomates": "tomatoes", "medio": "half (masc.)",
    "necesita": "needs; you need (formal)", "creo": "I think; I believe",
    "ya": "already", "tenemos": "we have", "todo": "everything; all",
    "puesto": "market stall", "Rosa": "Rosa", "todos": "all; every (plural)",
    "vamos": "let's go; we go", "necesitamos": "we need",
    "ingredientes": "ingredients", "primero": "first (adverb)",
    "verduras": "vegetables", "frescas": "fresh (fem. plural)", "tan": "so",
    "frescos": "fresh (masc. plural)", "quiere": "wants; you want (formal)",
    "señorita": "miss; young lady", "cuestan": "they cost",
    # unit08 places
    "banco": "bank", "farmacia": "pharmacy", "abre": "opens", "parque": "park",
    "biblioteca": "library", "lejos": "far", "lado": "side",
    "enfrente": "opposite; across", "entre": "between", "bastante": "quite",
    "barrio": "neighborhood", "lugares": "places", "útiles": "useful (plural)",
    "donde": "where (not a question)", "compramos": "we buy; we bought",
    "ah": "ah", "comimos": "we ate",
    # unit09 directions
    "calle": "street", "esquina": "corner", "sigue": "keep going; continue",
    "derecho": "straight ahead", "dobla": "turn (command)",
    "izquierda": "left", "gira": "turn (command)", "derecha": "right",
    "cruza": "cross (command)", "llego": "I get to; I arrive", "fácil": "easy",
    "pierdas": "get lost (in a negative command)",
    "llegar": "to arrive; to get to", "desde": "from (a starting point)",
    "sigo": "I keep going; I continue", "doblo": "I turn",
    "muchas": "many (fem.)", "nada": "nothing",
    # unit10 weather
    "tiempo": "weather; time", "sol": "sun", "lluvia": "rain", "viento": "wind",
    "nube": "cloud", "ni": "not even; nor", "hace": "makes; does",
    "calor": "heat", "frío": "cold", "llueve": "it rains; it's raining",
    "nublado": "cloudy", "invierno": "winter", "Madrid": "Madrid",
    "demasiado": "too; too much", "porque": "because", "ir": "to go",
    "importante": "important", "llevar": "to bring; to carry",
    "camino": "way; path", "tienda": "shop; store", "prefiero": "I prefer",
    "casi": "almost", "verdad": "truth; true", "llegamos": "we arrive",
    "razón": "reason",
    # unit11 clothing
    "camisa": "shirt", "pantalón": "trousers; pants", "chaqueta": "jacket",
    "zapatos": "shoes", "delantal": "apron", "talla": "size (clothing)",
    "usas": "you wear; you use (informal)", "uso": "I wear; I use",
    "mediana": "medium (size)", "queda": "fits; suits", "mal": "badly",
    "voy": "I go; I'm going", "comprarlo": "to buy it",
    "veinticinco": "twenty-five", "barato": "cheap", "solo": "only",
    "delantales": "aprons", "esa": "that (fem.)", "ayudo": "I help",
    "buscamos": "we are looking for", "usan": "you wear (plural); they wear",
    # unit12 emotions
    "nervioso": "nervous (masc.)", "nerviosa": "nervous (fem.)",
    "contento": "happy (masc.)", "contenta": "happy (fem.)",
    "cansado": "tired (masc.)", "cansada": "tired (fem.)",
    "preocupado": "worried (masc.)", "preocupada": "worried (fem.)",
    "orgulloso": "proud (masc.)", "orgullosa": "proud (fem.)",
    "sientes": "you feel (informal)", "siento": "I feel",
    "quema": "is burning", "preocupes": "worry (in a negative command)",
    "empezar": "to start", "nuevo": "new", "estaban": "they were (a state)",
    "nerviosos": "nervous (plural)", "durante": "during", "quemó": "burned",
    "preocupados": "worried (plural)", "empezaron": "they started",
    "final": "end", "salió": "turned out; came out", "ahora": "now",
    "están": "they are (a state)", "orgullosos": "proud (plural)",
    "contentos": "happy (plural)", "ay": "oh no", "hacemos": "we do",
    "intentarlo": "to try it", "otra": "another (fem.)",
    "nosotros": "we; us", "lo": "it", "logramos": "we managed",
    "juntos": "together",
    # unit13 work
    "trabajo": "job; work", "oficina": "office", "escritorio": "desk",
    "escuela": "school", "enseño": "I teach", "estudiantes": "students",
    "trabajar": "to work", "contador": "accountant",
    "profesora": "teacher (female)", "trabajas": "you work (informal)",
    "preferimos": "we prefer", "esto": "this (thing)", "trabaja": "works",
    "enseña": "teaches", "les": "to them", "prefieren": "they prefer",
    "interesante": "interesting", "enseñar": "to teach",
    "contigo": "with you (informal)", "definitivamente": "definitely",
    # unit14 housing
    "apartamento": "apartment", "dormitorio": "bedroom", "baño": "bathroom",
    "sala": "living room", "alquilar": "to rent", "edificio": "building",
    "desocupado": "vacant; available", "pequeño": "small (masc.)",
    "dormitorios": "bedrooms", "alguien": "someone", "periódico": "newspaper",
    "anuncios": "ads", "llamar": "to call", "agencia": "agency",
    "mismo": "same; very (as in: this very day)",
    # unit15 comparisons
    "viejo": "old", "equipo": "team", "mudarse": "to move (house)",
    "espacio": "space", "viste": "you saw (informal)",
    "mudarme": "to move (house), said of myself", "sentido": "sense",
    "exacto": "exactly", "cocinas": "you cook (informal)",
}

POS_SETS = {
    "proper_noun": PROPER_NOUNS,
    "pronoun": split_words(
        "usted tú nos se me te este esta su tu mi yo qué cuántos cuál mis tus "
        "estos ellos sus tuyo eso mí algo cuánto todo esa nosotros lo esto les "
        "contigo alguien nada"
    ),
    "preposition": split_words(
        "hasta de en al por para con a del entre desde durante"
    ),
    "particle": split_words("y que un el la una los las o no sí ni porque pero"),
    "adjective": split_words(
        "buenos buenas buen primera bueno media perfecto próxima grande pequeña "
        "muchos menor bonito cada cierto siguiente buena genial incluido fresca "
        "medio todos frescas frescos útiles fácil muchas nublado importante "
        "mediana barato nervioso nerviosa contento contenta cansado cansada "
        "preocupado preocupada orgulloso orgullosa nuevo nerviosos preocupados "
        "orgullosos contentos otra interesante desocupado pequeño mismo viejo"
    ),
    "adverb": split_words(
        "cómo bien muy luego mucho igualmente dónde poco todavía aquí también "
        "dentro claro como así más cerca hoy cuándo después menos antes "
        "entonces ya primero tan lejos enfrente bastante donde derecho "
        "demasiado casi mal solo ahora juntos definitivamente exacto"
    ),
    "verb": split_words(
        "está estás vemos tenga llama llamo llamas soy es eres vivo habla estoy "
        "aprendiendo vengo gusta cocinar tienes tengo tiene puedes repetir "
        "necesito necesitas escribo somos vives viven vive mira son hablamos "
        "entiendo tener hay termina empieza ven almorzar comemos quiero quieres "
        "comer podemos ver quieren cuesta necesita creo tenemos vamos "
        "necesitamos quiere cuestan abre compramos comimos sigue dobla gira "
        "cruza llego pierdas llegar sigo doblo hace llueve ir llevar prefiero "
        "llegamos usas uso queda voy comprarlo ayudo buscamos usan sientes "
        "siento quema preocupes empezar estaban quemó empezaron salió están "
        "hacemos intentarlo logramos enseño trabajar trabajas preferimos trabaja "
        "enseña prefieren enseñar alquilar llamar mudarse viste mudarme cocinas"
    ),
    "phrase": split_words("hola gracias adiós oye felicidades ah ay"),
}
POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())

CATEGORY_TAGS: dict[str, list[str]] = {}
for _tag, _words in {
    "es_number": "cero uno dos tres cuatro cinco seis siete ocho nueve diez once "
                 "doce trece catorce quince veinte treinta cien veintiocho "
                 "veintidós veintinueve veinticinco",
    "es_weekday": "lunes martes miércoles jueves viernes sábado domingo",
    "es_month": "enero febrero marzo abril mayo junio julio agosto septiembre "
                "octubre noviembre diciembre",
    "es_family": "madre padre hermano hermana hijo hija padres hermanos hermanas "
                 "abuelo abuela abuelos tío tía primo prima primos familia",
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
