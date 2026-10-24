#!/usr/bin/env python3
"""Idempotently backfill en-es (Spanish target) lexemes for the "Spanish A1"
course, so en-es practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: first en->X backfill outside the six launch
directions. All plumbing lives in scripts/_target_lexeme_backfill_common.py
(see its docstring for the tag scheme); this file is data only:
one hand-written English gloss and one part of speech per citation form.

Scope: A1 ("en-es" manifest group, units 01-15) and A2 ("en-es-a2", units
16-25; session 11). B1+ is not classified yet; extend LEVELS and the tables
below together. A token already glossed for A1 keeps that gloss in A2 unless
A2_GLOSS_OVERRIDES says the A2 unit teaches another sense.

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
LEVELS = {"a1": "en-es", "a2": "en-es-a2"}

PROPER_NOUNS = {
    "Elena", "Mateo", "Lucía", "Diego", "Carlos", "Ana", "México", "Colombia",
    "Londres", "España", "Barcelona", "Sofía", "Madrid", "Rosa", "García",
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
    "soy": "I am (identity, origin)", "Diego": "Diego", "mucho": "much; a lot", "gusto": "pleasure",
    "igualmente": "likewise", "este": "this (masc.)", "es": "is (identity, origin)",
    "Carlos": "Carlos", "esta": "this (fem.)", "Ana": "Ana", "de": "of; from",
    "dónde": "where (question)", "México": "Mexico", "eres": "you are (informal), for identity and origin",
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
    "por": "for; by; through", "favor": "favour; kindness (in the phrase for please)", "claro": "of course; sure",
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
    "mira": "look (command)", "estos": "these", "son": "they are (identity, description)",
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
    "ven": "they see (with se: they meet up)", "siguiente": "next; following",
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
    "derecho": "straight ahead", "dobla": "turn (command; literally: fold)",
    "izquierda": "left", "gira": "turn (command; literally: spin)", "derecha": "right",
    "cruza": "cross (command)", "llego": "I get to; I arrive", "fácil": "easy",
    "pierdas": "get lost (in a negative command)",
    "llegar": "to arrive; to get to", "desde": "from (a starting point)",
    "sigo": "I keep going; I continue", "doblo": "I turn",
    "muchas": "many (fem.)", "nada": "nothing",
    # unit10 weather
    "tiempo": "weather; time", "sol": "sun", "lluvia": "rain", "viento": "wind",
    "nube": "cloud", "ni": "not even; nor", "hace": "makes; does (also used for weather)",
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
    # a2 unit16 tramites (A2 course, glossed at first sight in that course)
    "cita": "appointment", "trámite": "procedure; official paperwork",
    "registrarse": "to register (oneself)", "quisiera": "I would like",
    "hacer": "to do; to make", "registrarme": "to register myself",
    "pasaporte": "passport", "contrato": "contract", "alquiler": "rent",
    "comprobante": "proof; supporting document",
    "domicilio": "home address; residence", "documentos": "documents",
    "traigo": "I bring", "podría": "could; you could (formal)",
    "ayudarme": "to help me", "dirección": "address", "mes": "month",
    "pasado": "last; past", "necesario": "necessary",
    "traiga": "bring (after a phrase like it is necessary that; formal)",
    "llegue": "arrive (after a phrase like it is important that; formal)",
    "traer": "to bring", "siguientes": "following (plural)",
    "válido": "valid", "si": "if", "corresponde": "applies; is appropriate",
    "haga": "make; do (formal command)", "venir": "to come",
    "recibirá": "will receive; you will receive (formal)",
    "registro": "registration; record", "correo": "mail; post",
    "unos": "some; about (masc. plural)", "puedo": "I can",
    "ayudarle": "to help you (formal)", "nueva": "new (fem.)",
    "mostrarme": "to show me", "orden": "order; tidy state",
    "firme": "sign (formal command)", "listo": "ready; done",
    "recibiré": "I will receive", "paciencia": "patience", "ayuda": "help",
    "registró": "registered (he or she did)",
    "pasa": "happens; goes by",
    # a2 unit17 opiniones
    "opinión": "opinion", "pensar": "to think", "parece": "seems",
    "mejor": "better; best", "tiendas": "shops", "piensas": "you think (informal)",
    "sea": "is; may be (after a phrase like I do not think that)",
    "tranquilo": "calm; quiet (masc.)", "extraño": "I miss",
    "tranquilidad": "peace and quiet", "sin": "without",
    "embargo": "however (as the second half of a fixed phrase)",
    "ventajas": "advantages", "era": "was (a past description)",
    "conveniencia": "convenience", "supongo": "I suppose",
    "cree": "believes; thinks", "piensa": "thinks",
    # a2 unit18 banco
    "bancaria": "bank (as in bank account)", "abrir": "to open",
    "gustaría": "would please (used to say you would like)",
    "identificación": "identification; ID", "tarjeta": "card",
    "débito": "debit", "saldo": "balance (of an account)",
    "le": "to you (formal); to him; to her", "daremos": "we will give",
    "consultar": "to check; to look up", "puede": "can; you can (formal)",
    "línea": "line; online", "gratuita": "free of charge (fem.)",
    "cualquier": "any", "sucursal": "branch (of a bank)",
    "transferencias": "transfers", "cuentas": "accounts",
    "gratuitas": "free of charge (fem. plural)", "excelente": "excellent",
    "abrió": "opened (he or she did)",
    # a2 unit19 medico
    "dolor": "pain; ache", "cabeza": "head", "fiebre": "fever",
    "sentirse": "to feel (oneself)", "duele": "hurts; aches",
    "ayer": "yesterday", "consultorio": "doctor's office",
    "explicarme": "to explain to me", "recomiendo": "I recommend",
    "descanse": "rest (formal command)", "tome": "take (formal command)",
    "estas": "these (fem.)", "pastillas": "pills",
    "beba": "drink (formal command)", "mucha": "much; a lot of (fem.)",
    "paciente": "patient (person)", "García": "García (a surname)",
    "síntoma": "symptom", "leve": "mild", "recomendación": "recommendation",
    "descansar": "to rest", "tomar": "to take; to drink",
    "recetadas": "prescribed (fem. plural)", "beber": "to drink",
    "síntomas": "symptoms", "continúan": "they continue",
    "doctora": "doctor (female)", "tenía": "had (he or she; ongoing past)",
    "recomendó": "recommended (he or she did)",
    "descansara": "would rest (past, after a request)",
    "bebiera": "would drink (past, after a request)",
    # a2 unit20 mantenimiento
    "calentador": "water heater", "gotera": "leak (in a roof or pipe)",
    "plomero": "plumber", "funciona": "works; functions",
    "empeorando": "getting worse", "revisemos": "we check (after a phrase like it is necessary that)",
    "pronto": "soon", "ahí": "there", "estaré": "I will be (a place or state)",
    "problema": "problem", "reportado": "reported", "técnico": "technician",
    "asignado": "assigned", "confirma": "confirms; is confirmed",
    "visita": "visit", "esté": "be (formal command; a place or state)",
    "disponible": "available", "enviaré": "I will send", "ese": "that (masc.)",
    "rápida": "quick (fem.)", "reportó": "reported (he or she did)",
    "casera": "landlady", "enviará": "will send; you will send (formal)",
    # a2 unit21 entrevista
    "entrevista": "interview", "presentarse": "to introduce oneself",
    "presentarme": "to introduce myself", "interesa": "interests; is of interest to",
    "horario": "schedule; working hours", "busca": "looks for; is wanted",
    "profesor": "teacher (male)", "experiencia": "experience",
    "interesados": "interested people", "enviar": "to send",
    "currículum": "résumé; CV", "alguna": "any; some (fem.)",
    "oportunidad": "opportunity", "presentó": "introduced (he or she did)",
    "explicó": "explained (he or she did)", "preguntó": "asked (he or she did)",
    "terminar": "to finish",
    # a2 unit22 viaje interrumpido
    "retraso": "delay", "tren": "train", "lleva": "carries; takes; has been (of time elapsed)",
    "minutos": "minutes", "cancelado": "cancelled (masc.)",
    "cancelada": "cancelled (fem.)", "opción": "option",
    "centro": "town centre; downtown", "pasajeros": "passengers",
    "pueden": "they can; you can (plural)", "autobús": "bus",
    "salida": "exit", "principal": "main", "disculpe": "excuse me (formal)",
    "tarda": "takes (time)", "avisar": "to let someone know",
    # a2 unit23 vida digital
    "móvil": "mobile phone", "redes": "networks", "sociales": "social (plural)",
    "miro": "I look at; I watch", "paso": "I spend (time)",
    "leer": "to read", "noticias": "news", "escribir": "to write",
    "mensajes": "messages", "útil": "useful", "veces": "times (occasions)",
    "cansa": "tires; is tiring",
    # a2 unit24 semana ocupada
    "gimnasio": "gym", "fin": "end", "descanso": "I rest", "veo": "I see",
    "amigos": "friends", "compro": "I buy", "normalmente": "normally",
    "haces": "you do (informal)",
    # a2 unit25 reclamacion
    "cremallera": "zipper", "devolver": "to return (an item)",
    "reembolso": "refund", "ofrecerle": "to offer you (formal)",
    "cambio": "exchange; change", "artículo": "item; article",
    "debe": "must; should; you must (formal)", "recibo": "receipt",
    "estar": "to be (a state or place)", "usar": "to use",
    "ofrecer": "to offer", "compré": "I bought",
}

POS_SETS = {
    "proper_noun": PROPER_NOUNS,
    "pronoun": split_words(
        "usted tú nos se me te este esta su tu mi yo qué cuántos cuál mis tus "
        "estos ellos sus tuyo eso mí algo cuánto todo esa nosotros lo esto les "
        "contigo alguien nada ese estas alguna le"
    ),
    "preposition": split_words(
        "hasta de en al por para con a del entre desde durante sin"
    ),
    "particle": split_words("y que un el la una los las o no sí ni porque pero si embargo"),
    "adjective": split_words(
        "buenos buenas buen primera bueno media perfecto próxima grande pequeña "
        "muchos menor bonito cada cierto siguiente buena genial incluido fresca "
        "medio todos frescas frescos útiles fácil muchas nublado importante "
        "mediana barato nervioso nerviosa contento contenta cansado cansada "
        "preocupado preocupada orgulloso orgullosa nuevo nerviosos preocupados "
        "orgullosos contentos otra interesante desocupado pequeño mismo viejo "
        "pasado necesario siguientes válido nueva mejor tranquilo bancaria "
        "gratuita gratuitas cualquier excelente mucha leve recetadas reportado "
        "asignado disponible rápida principal útil cancelado cancelada listo "
        "sociales unos"
    ),
    "adverb": split_words(
        "cómo bien muy luego mucho igualmente dónde poco todavía aquí también "
        "dentro claro como así más cerca hoy cuándo después menos antes "
        "entonces ya primero tan lejos enfrente bastante donde derecho "
        "demasiado casi mal solo ahora juntos definitivamente exacto ayer pronto ahí normalmente"
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
        "enseña prefieren enseñar alquilar llamar mudarse viste mudarme cocinas "
        "registrarse quisiera hacer registrarme traigo podría ayudarme traiga "
        "llegue traer corresponde haga venir recibirá puedo ayudarle mostrarme "
        "firme recibiré registró pensar parece piensas sea extraño era supongo "
        "cree piensa abrir gustaría daremos consultar puede abrió sentirse duele "
        "explicarme recomiendo descanse tome beba descansar tomar beber "
        "continúan tenía recomendó descansara bebiera funciona empeorando "
        "revisemos estaré confirma esté enviaré reportó enviará presentarse "
        "presentarme interesa busca enviar presentó explicó preguntó terminar "
        "lleva pueden disculpe tarda avisar miro paso leer escribir cansa "
        "descanso veo compro haces devolver ofrecerle debe estar usar ofrecer "
        "compré pasa"
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

A2_GLOSS_OVERRIDES = {
    ("a2_unit18_banco", "cuenta"): "account (bank); bill",
    ("a2_unit21_entrevista", "puesto"): "position; job post",
    ("a2_unit21_entrevista", "hace"): "makes; does; ago (with a length of time)",
    ("a2_unit17_opiniones", "razón"): "reason; being right",
    ("a2_unit16_tramites", "desde"): "since; from",
}

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
            gloss_overrides=A2_GLOSS_OVERRIDES,
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
