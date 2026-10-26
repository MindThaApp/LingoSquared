#!/usr/bin/env python3
"""Idempotently backfill en-it (Italian target) lexemes for the "Italian A1"
course, so en-it practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: en->X backfill outside the six launch directions.
All plumbing lives in scripts/_target_lexeme_backfill_common.py (see its
docstring for the tag scheme); this file is data only: one hand-written
English gloss and one part of speech per citation form.

Scope: A1 (the "en-it-a1" manifest group, units 01-24), A2 (the "en-it-a2"
group, units 25-34, added in session 11) and B1 (the "en-it-b1" group, units
35-53, added in session 12). B2+ is not classified yet; extend
LEVELS and the tables below together. The A2 course is its own course, so a
token already glossed for A1 is simply reused at first sight in A2.

Glossing rules followed here (PRACTICE_PACK_RECIPE.md §0.1, §6.6):
* the gloss is the sense the unit actually teaches at first sight; a token
  with two taught senses gets both ("lo": "it (object); the (masc., ...)"),
* inflected forms say who they belong to ("you have (informal)"), so a
  bare-word translation prompt names one form,
* gender pairs are glossed "(masc.)"/"(fem.)" so the two are never
  interchangeable answers.

Elided forms are glossed exactly as the realizations' introduced_tokens spell
them: the tokenizer splits at the apostrophe, so "Di dov'è" yields the tokens
dov + è, "trent'anni" yields trent, "un po' d'italiano" yields po + d, while
"l'una", "l'acqua", "un'acqua", "l'ufficio", "c'è", "ce n'è", "all'incrocio",
"dov'è" (unit18) and "anch'io" are single tokens. "po'" (unit22) is distinct
from "po" (unit02). Sentence-initial capitals fold to lowercase; the proper
nouns below keep their capital. "Lei" (formal you) folds to "lei".
"sei" is first taught as "you are" (unit02); its later "six" sense is part
of the same gloss.

Run (after the en-it course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_it.py

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

LANG = "it"
LEVELS = {"a1": "en-it-a1", "a2": "en-it-a2", "b1": "en-it-b1"}

PROPER_NOUNS = {"Elena", "Sam", "Chicago", "Milano", "Roma", "Bologna", "Italia",
                "Firenze", "Napoli", "Colosseo",
                # derived A1 depth units (session 15): cast and places
                "Giulia", "Marco", "Luca", "Chiara", "Nina", "Pico", "Torino"}
_PROPER_BY_LOWER = {p.lower(): p for p in PROPER_NOUNS}


def normalize(token: str) -> str:
    lower = token.lower()
    return _PROPER_BY_LOWER.get(lower, lower)


GLOSSES: dict[str, str] = {
    # unit01 greetings
    "ciao": "hi; bye", "buongiorno": "good morning; good day",
    "come": "how; like", "stai": "you are (informal), as in how are you",
    "sta": "is; you are (formal), as in how are you", "tu": "you (informal)",
    "informale": "informal", "lei": "you (formal)", "formale": "formal",
    "o": "or", "rispettoso": "respectful", "bene": "well; fine",
    "grazie": "thank you", "e": "and", "buonasera": "good evening",
    "buonanotte": "good night", "arrivederla": "goodbye (formal)",
    "a": "to; at; in", "domani": "tomorrow", "ci": "each other; us",
    "vediamo": "we see", "si": "yourself (formal)", "chiama": "is called",
    "scusi": "excuse me (formal)", "ti": "yourself (informal)",
    "chiami": "you are called (informal)", "mi": "myself; me",
    "chiamo": "I am called", "Elena": "Elena", "io": "I",
    "sono": "I am; they are", "Sam": "Sam", "piacere": "pleasure",
    "di": "of; from", "conoscerla": "to meet you (formal)",
    "benvenuto": "welcome (masc.)", "in": "in", "ufficio": "office",
    "mille": "thousand",
    # unit02 introductions
    "dove": "where", "sei": "you are (informal); six",
    "dov": "where (shortened form)", "è": "is", "americano": "American (masc.)",
    "Chicago": "Chicago", "italiana": "Italian (fem.)", "Milano": "Milan",
    "americana": "American (fem.)", "italiano": "Italian (masc.); Italian (language)",
    "parli": "you speak (informal)", "parla": "speaks; you speak (formal)",
    "parlo": "I speak", "un": "a; an (masc.)",
    "po": "bit (shortened form, in: a little)", "d": "of (shortened form before a vowel)",
    "inglese": "English (language)", "studio": "I study", "da": "for; since; from",
    "anno": "year", "quanto": "how long; how much", "studi": "you study (informal)",
    "che": "what; which", "lavoro": "work; job; I work", "fai": "you do (informal)",
    "fa": "does; makes; you do (formal)", "ingegnere": "engineer",
    "qui": "here", "per": "for", "due": "two", "anni": "years",
    "bello": "nice; beautiful (masc.)",
    # unit03 numbers
    "zero": "zero", "uno": "one", "tre": "three", "quattro": "four",
    "cinque": "five", "sette": "seven", "otto": "eight", "nove": "nine",
    "dieci": "ten", "quanti": "how many (masc.)", "hai": "you have (informal)",
    "ho": "I have", "trent": "thirty (shortened form)", "costa": "costs",
    "caffè": "coffee", "euro": "euro", "cornetto": "croissant",
    "cinquanta": "fifty", "ne": "of it; of them", "vuole": "you want (formal)",
    "vorrei": "I would like", "qual": "which; what (shortened form)",
    "il": "the (masc.)", "tuo": "your (informal, masc.)", "numero": "number",
    "telefono": "phone", "mio": "my (masc.)", "perfetto": "perfect",
    # unit04 dates
    "lunedì": "Monday", "martedì": "Tuesday", "mercoledì": "Wednesday",
    "giovedì": "Thursday", "venerdì": "Friday", "sabato": "Saturday",
    "domenica": "Sunday", "giorno": "day", "oggi": "today", "data": "date",
    "gennaio": "January", "febbraio": "February", "marzo": "March",
    "aprile": "April", "quindici": "fifteen", "quando": "when",
    "arrivi": "you arrive (informal)", "Roma": "Rome", "arrivo": "I arrive",
    "pomeriggio": "afternoon", "dopodomani": "the day after tomorrow",
    # unit05 time
    "ore": "hours; o'clock (in telling time)", "le": "the (fem. plural)",
    "l'una": "one o'clock", "dodici": "twelve", "mezzo": "half",
    "quarto": "quarter", "meno": "minus; less", "ora": "hour; time (of day)",
    "alle": "at the (fem. plural), used for clock times", "mattina": "morning",
    "sera": "evening",
    # unit06 family
    "la": "the (fem.)", "madre": "mother", "padre": "father",
    "fratello": "brother", "sorella": "sister", "questo": "this (masc.)",
    "questa": "this (fem.)", "mia": "my (fem.)", "nonno": "grandfather",
    "nonna": "grandmother", "fratelli": "brothers; siblings",
    "sorelle": "sisters", "una": "a; an; one (fem.)", "marito": "husband",
    "moglie": "wife", "figli": "children", "sì": "yes", "maschio": "boy; male",
    "femmina": "girl; female", "figlio": "son", "figlia": "daughter",
    # unit07 food
    "panino": "sandwich", "l'acqua": "the water", "cosa": "what",
    "desidera": "you would like (formal)", "favore": "favor",
    "basta": "is enough", "così": "like this; so", "menù": "menu",
    "conto": "bill; check", "un'acqua": "a water",
    # unit08 shopping
    "mele": "apples", "banane": "bananas", "i": "the (masc. plural)",
    "pomodori": "tomatoes", "patate": "potatoes", "costano": "they cost",
    "al": "to the; per", "chilo": "kilo", "va": "goes; works out",
    "lo": "it (object); the (masc., before some sounds)", "prendo": "I take",
    # unit09 places
    "farmacia": "pharmacy", "banca": "bank", "stazione": "station",
    "l'ufficio": "the office", "postale": "postal", "vicino": "near; nearby",
    "via": "street; road", "c'è": "there is", "ce n'è": "there is one (of them)",
    "accanto": "next (to)", "alla": "to the; at the (fem.)",
    # unit10 directions
    "destra": "right", "sinistra": "left", "sempre": "always",
    "dritto": "straight ahead", "all'incrocio": "at the intersection",
    "museo": "museum", "vada": "go (formal command)", "poi": "then",
    "giri": "turn (formal command)", "lontano": "far", "no": "no",
    "solo": "only", "minuti": "minutes", "piedi": "feet", "molto": "very; a lot",
    "gentile": "kind", "continui": "continue (formal command)",
    # unit11 routines
    "faccio": "I do; I make", "colazione": "breakfast", "vado": "I go",
    "torno": "I go back; I return", "casa": "home; house", "letto": "bed",
    "solito": "usual", "torni": "you go back (informal)", "trenta": "thirty",
    "presto": "early; soon", "anch'io": "me too; I too",
    # unit12 plans
    "stasera": "tonight", "andiamo": "we go; let's go", "cinema": "cinema",
    "davanti": "in front (of)", "allora": "then; so", "se": "if", "non": "not",
    # unit13 past events
    "ieri": "yesterday", "stamattina": "this morning",
    "andato": "went; gone (masc.)", "andata": "went; gone (fem.)",
    "visto": "seen", "bel": "nice; fine (before a masc. noun)", "film": "film",
    "mangiato": "eaten; ate", "pranzo": "lunch", "fatto": "done; made",
    # unit14 preferences
    "preferire": "to prefer", "preferisco": "I prefer",
    "preferisci": "you prefer (informal)", "tè": "tea",
    "piace": "is pleasing (used to say you like something)",
    "te": "you (after a preposition)", "me": "me (after a preposition)",
    # unit15 comparisons
    "più": "more", "dei": "of the (masc. plural); than the (masc. plural)",
    "delle": "of the (fem. plural); than the (fem. plural)", "quale": "which",
    "buone": "good (fem. plural)",
    # unit16 health
    "male": "pain; badly", "testa": "head", "pancia": "stomach; belly",
    "gola": "throat", "sento": "I feel", "febbre": "fever", "tosse": "cough",
    "dottore": "doctor (male)", "dottoressa": "doctor (female)",
    "riposa": "rest (informal command)", "medicina": "medicine",
    "devo": "I must; I need to", "andare": "to go",
    "dal": "to the (person's place, masc.); from the (masc.)",
    "prendi": "you take (informal); take (informal command)",
    # unit17 work
    "insegnante": "teacher", "commesso": "shop assistant (male)",
    "scuola": "school", "lavori": "you work (informal)", "inizio": "I start",
    "finisco": "I finish", "inizi": "you start (informal)",
    # unit18 housing
    "cucina": "kitchen", "soggiorno": "living room", "camera": "room; bedroom",
    "bagno": "bathroom", "stanze": "rooms", "tavolo": "table", "sedia": "chair",
    "divano": "sofa", "nella": "in the (fem.)", "nel": "in the (masc.)",
    "dietro": "behind", "sopra": "above; on", "sotto": "under",
    "dov'è": "where is", "finestra": "window",
    # unit19 travel
    "treno": "train", "binario": "platform", "biglietto": "ticket",
    "parte": "leaves; departs",
    # unit20 weather
    "caldo": "hot", "freddo": "cold", "piove": "it rains", "sole": "sun",
    "tempo": "weather; time", "restiamo": "we stay",
    # unit21 clothing
    "maglietta": "T-shirt", "pantaloni": "pants; trousers", "scarpe": "shoes",
    "giacca": "jacket", "blu": "blue", "taglia": "size (clothing)",
    "piccola": "small (fem.)", "media": "medium (fem.)", "grande": "big; large",
    # unit22 emotions
    "felice": "happy", "triste": "sad", "stanco": "tired (masc.)",
    "nervoso": "nervous (masc.)", "senti": "you feel (informal)",
    "perché": "because; why", "po'": "bit (in: a little)",
    "stanca": "tired (fem.)", "ma": "but", "sto": "I am (how I feel)",
    # unit23 communication
    "pronto": "hello (answering the phone)", "chi": "who",
    "messaggio": "message", "mando": "I send", "puoi": "you can (informal)",
    "ripetere": "to repeat", "piano": "slowly; slow",
    # unit24 money
    "soldi": "money", "carta": "card", "contanti": "cash",
    "scontrino": "receipt", "pago": "I pay", "con": "with; by",
    "posso": "I can", "pagare": "to pay", "certo": "certainly",
    "ecco": "here is; here it is",
    # A2 unit25 bureaucracy
    "c": "there (shortened form of ci, in: there is)",
    "documento": "document; ID", "d'identità": "of identity (in: identity document)",
    "codice": "code", "fiscale": "tax; fiscal", "contratto": "contract",
    "d'affitto": "of rent (in: rental contract)", "modulo": "form",
    "registrare": "to register", "residenza": "residence",
    "entro": "by; within", "prendere": "to take; to have",
    "appuntamento": "appointment", "comune": "town hall; municipality",
    "porti": "bring (formal command)", "consegnare": "to hand in; to submit",
    # A2 unit26 opinions
    "secondo": "according to", "quartiere": "neighborhood",
    "comodo": "convenient; comfortable (masc.)", "rumoroso": "noisy (masc.)",
    "d'accordo": "in agreement (in: I agree)",
    "metropolitana": "subway; metro", "capisco": "I understand",
    "vero": "true", "però": "however; but", "negozi": "shops",
    "utili": "useful (plural)", "troppo": "too; too much", "utile": "useful",
    # A2 unit27 bank
    "corrente": "current; checking (in: checking account)",
    "l'indirizzo": "the address", "aprire": "to open",
    "inclusa": "included (fem.)", "aiutarla": "to help you (formal)",
    "servono": "are needed", "informazioni": "information", "Italia": "Italy",
    # A2 unit28 doctor
    "mal": "ache; pain", "forte": "strong; severe", "leggera": "light; mild (fem.)",
    "giorni": "days", "sintomi": "symptoms", "ha": "has; you have (formal)",
    "prenda": "take (formal command)", "beva": "drink (formal command)",
    "molta": "a lot of; much (fem.)", "acqua": "water",
    "prenotare": "to book", "visita": "visit; medical examination",
    # A2 unit29 home repairs
    "perdita": "leak; loss", "d'acqua": "of water (in: water leak)",
    "lavandino": "sink", "pavimento": "floor", "bagnato": "wet (masc.)",
    "dica": "tell (formal command)", "tecnico": "technician",
    "riparazione": "repair", "può": "can; you can (formal)", "venire": "to come",
    # A2 unit30 interview
    "l'esperienza": "the experience", "l'ingegnere": "the engineer",
    "gruppo": "group; team", "disponibile": "available",
    "esperienza": "experience", "della": "of the (fem.)",
    "sua": "your (formal, fem.); his; her", "l'orario": "the schedule; the hours",
    "dalle": "from the (fem. plural)", "confermo": "I confirm",
    "colloquio": "interview",
    # A2 unit31 travel disruption
    "Bologna": "Bologna", "ritardo": "delay", "cancellato": "cancelled (masc.)",
    "coincidenza": "connection (between trains)", "venti": "twenty",
    "perso": "lost; missed", "alternativa": "alternative", "autobus": "bus",
    "sostitutivo": "replacement (masc.)", "quaranta": "forty", "tardi": "late",
    # A2 unit32 online life
    "internet": "internet", "social": "social media", "notizie": "news",
    "messaggi": "messages", "mandare": "to send", "uso": "I use",
    "ogni": "every; each", "leggere": "to read", "spesso": "often",
    "poco": "little; not much", "perdo": "I lose; I waste",
    # A2 unit33 busy week
    "durante": "during", "settimana": "week", "palestra": "gym", "fine": "end",
    "invece": "instead; on the other hand", "riposo": "I rest", "vedo": "I see",
    "gli": "the (masc. plural)", "amici": "friends", "prima": "first; before",
    # A2 unit34 complaint
    "caricatore": "charger", "prodotto": "product",
    "difettoso": "faulty; defective (masc.)", "funziona": "works",
    "rimborso": "refund", "sostituzione": "replacement", "possiamo": "we can",
    "fare": "to do; to make", "oppure": "or else", "quattordici": "fourteen",
    "reso": "return (of goods)",
    # B1 unit35 abilities
    "modo": "way; manner (in: make sure that)", "riceva": "receives (subjunctive)",
    "ricevere": "to receive", "avrei": "I would have",
    "potuto": "been able to (past participle)",
    "ricevesse": "received (imperfect subjunctive)", "conferma": "confirmation",
    # B1 unit36 obligations
    "bisogna": "it is necessary", "consegni": "hands in (subjunctive)",
    "firmi": "signs (subjunctive)", "firmare": "to sign",
    "bisognava": "it was necessary",
    "l": "it (shortened form of lo, in: I did not do it)",
    "chiamassi": "called (imperfect subjunctive, I)", "chiamare": "to call",
    # B1 unit37 hypotheses
    "arriva": "arrives", "arrivare": "to arrive", "chiamerò": "I will call",
    "arrivasse": "arrived (imperfect subjunctive)", "chiamerei": "I would call",
    # B1 unit38 debate
    "sul": "on the (masc.)", "sia": "is (subjunctive)", "risparmiare": "to save",
    "pensa": "thinks", "manca": "is missing",
    # B1 unit39 work
    "occupo": "I take care of", "del": "of the (masc.)", "rapporto": "report",
    "responsabile": "responsible", "quasi": "almost", "controllare": "to check",
    # B1 unit40 storytelling
    "arrivato": "arrived (masc.)", "dopo": "after; then",
    "consegnato": "handed in (past participle)", "mentre": "while",
    "preparavo": "I was preparing", "chiamato": "called (past participle)",
    "detto": "said (past participle)", "aspettava": "was waiting",
    # B1 unit41-43
    "piovere": "to rain", "resto": "I stay", "restare": "to stay",
    "usciamo": "we go out", "uscire": "to go out",
    "controllo": "I check", "email": "email", "trovato": "found (past participle)",
    "trovare": "to find", "riunione": "meeting", "inizia": "starts",
    "iniziare": "to start", "chiesto": "asked (past participle)",
    "chiedere": "to ask",
    # B1 unit44 purposes
    "studiare": "to study", "l'italiano": "the Italian language",
    "lavorare": "to work", "parto": "I leave", "partire": "to leave",
    "perdere": "to lose; to miss",
    # B1 unit45 advice
    "fossi": "I were (subjunctive)", "parlerei": "I would speak", "capo": "boss",
    "dovresti": "you should", "spiegare": "to explain", "problema": "problem",
    "chiedi": "you ask (informal)", "ferie": "vacation; time off",
    "buona": "good (fem.)", "idea": "idea", "penso": "I think",
    # B1 unit46 serious complaint
    "riscaldamento": "heating", "già": "already", "volte": "times",
    "mandasse": "sent (imperfect subjunctive)", "stesso": "itself; the very same",
    "possibile": "possible",
    # B1 unit47 regrets
    "dovuto": "had to; should have (past participle)",
    "avessi": "I had (subjunctive)", "saputo": "known (past participle)",
    # B1 unit48 plans
    "intenzione": "intention", "settimane": "weeks",
    "comprato": "bought (past participle)", "probabilmente": "probably",
    "tornerò": "I will return", "agosto": "August", "forse": "maybe",
    "resterò": "I will stay", "mese": "month",
    # B1 unit49 conditional
    "viaggerei": "I would travel", "viaggiare": "to travel",
    "potessi": "I could (subjunctive)", "andrei": "I would go",
    "potresti": "could you (informal)", "chiudere": "to close",
    "preferirei": "I would prefer",
    # B1 unit50 meetings
    "proporrei": "I would suggest", "rimandare": "to postpone",
    "potremmo": "we could", "procede": "is progressing", "progetto": "project",
    "finito": "finished (masc.)", "manderò": "I will send", "un'email": "an email",
    "dettagli": "details",
    # B1 unit51 descriptions
    "ristorante": "restaurant", "abbiamo": "we have",
    "visitato": "visited (past participle)", "collega": "colleague",
    "lavora": "works", "unire": "to join; to combine", "fatti": "facts",
    "persona": "person", "cui": "which; whom (after a preposition)",
    "simpatica": "nice; friendly (fem.)", "città": "city", "abito": "I live",
    # B1 unit52 summarizing
    "Firenze": "Florence", "Napoli": "Naples", "Colosseo": "the Colosseum",
    "bistecca": "steak", "nuotato": "swum (past participle)", "mare": "sea",
    "breve": "short; brief", "punto": "point", "principale": "main",
    "divertito": "had fun (past participle)", "dettaglio": "detail",
    "essenziale": "essential", "riassumere": "to summarize", "viaggio": "trip",
    # B1 unit53 concessions
    "anche": "even; also", "ragione": "reason; right (in: you are right)",
    "nonostante": "despite", "continua": "continues", "opinione": "opinion",
    "tuttavia": "however", "credo": "I believe", "necessario": "necessary",
    "cambiare": "to change", "qualcosa": "something", "primo": "first (masc.)",
    "chiaro": "clear",
}

POS_SETS = {
    "proper_noun": PROPER_NOUNS,
    "pronoun": split_words(
        "tu lei ci si ti mi io che quanto cosa chi ne questo questa te me "
        "quale qual lo mio mia tuo quanti sua l cui qualcosa"
    ),
    "preposition": split_words(
        "entro secondo durante della dalle a di in da per con al alla alle dal nel nella dei delle accanto "
        "davanti dietro sopra sotto del sul nonostante"
    ),
    "particle": split_words(
        "e o il la le i un una non se ma d perché come c gli oppure però invece mentre"
    ),
    "adjective": split_words(
        "informale formale rispettoso americano americana italiana italiano "
        "bello perfetto lontano gentile buone "
        "fiscale comodo rumoroso utile utili corrente inclusa forte leggera molta "
        "bagnato disponibile cancellato sostitutivo difettoso "
        "bel caldo freddo piccola media grande felice triste stanco stanca "
        "nervoso blu postale vicino dritto benvenuto "
        "responsabile simpatica buona breve principale essenziale necessario "
        "primo chiaro possibile finito stesso"
    ),
    "adverb": split_words(
        "dove dov quando sì no poi allora così bene domani oggi dopodomani meno più molto solo sempre presto "
        "ieri stamattina stasera male piano certo anch'io qui po po' "
        "troppo spesso poco tardi prima ogni "
        "quasi dopo già forse probabilmente anche tuttavia"
    ),
    "verb": {"ce n'è"} | split_words(
        "stai sta vediamo chiama chiami chiamo sono sei è parli parla parlo "
        "studio studi fai fa ho hai costa vuole vorrei costano va prendo "
        "c'è vada giri continui faccio vado torno torni andiamo "
        "andato andata visto mangiato fatto preferire preferisco preferisci "
        "piace sento devo andare prendi inizio finisco inizi lavori parte "
        "piove restiamo senti sto mando puoi ripetere pago posso pagare "
        "desidera basta riposa arrivi arrivo dov'è conoscerla scusi "
        "registrare prendere porti consegnare capisco aprire aiutarla servono "
        "ha prenda beva prenotare dica può venire confermo perso mandare uso "
        "leggere perdo riposo vedo funziona possiamo fare "
        "riceva ricevere ricevesse avrei potuto bisogna consegni firmi firmare "
        "bisognava chiamassi chiamare arriva arrivare chiamerò arrivasse chiamerei "
        "sia risparmiare pensa manca occupo controllare arrivato consegnato "
        "preparavo chiamato detto aspettava piovere resto restare usciamo uscire "
        "controllo trovato trovare inizia iniziare chiesto chiedere studiare "
        "lavorare parto partire perdere fossi parlerei dovresti spiegare chiedi "
        "penso mandasse dovuto avessi saputo comprato tornerò resterò viaggerei "
        "viaggiare potessi andrei potresti chiudere preferirei proporrei "
        "rimandare potremmo procede manderò abbiamo visitato lavora unire abito "
        "nuotato riassumere divertito continua credo cambiare"
    ),
    "phrase": split_words(
        "ciao buongiorno buonasera buonanotte grazie ecco pronto arrivederla "
        "d'identità d'affitto d'accordo"
    ),
}
# --- derive_target.py: derived units (generated; keep markers) ---
DERIVED_TARGET_GLOSSES: dict[str, str] = {
    "Chiara": "Chiara",
    "Giulia": "Giulia",
    "Luca": "Luca",
    "Marco": "Marco",
    "Nina": "Nina",
    "Pico": "Pico",
    "abita": "lives",
    "acquisti": "purchases; shopping",
    "adulti": "adults",
    "aggettivo": "adjective",
    "ai": "to the; at the (plural)",
    "all'istituto": "at the institute",
    "allo": "at the; to the (before s+consonant)",
    "alta": "tall (fem.)",
    "alto": "tall (masc.)",
    "altri": "other (masc. plural)",
    "ama": "loves",
    "amano": "they love",
    "amare": "to love",
    "amiamo": "we love",
    "amo": "I love",
    "ancora": "yet; still",
    "animale": "animal",
    "animali": "animals",
    "anziano": "old; elderly (masc.)",
    "app": "app",
    "are": "-are (verb ending)",
    "arrivederci": "goodbye",
    "ascoltare": "to listen to",
    "ascolto": "I listen to",
    "assistenza": "assistance; care",
    "auguri": "best wishes; congratulations",
    "avere": "to have",
    "azzurri": "blue (masc. plural)",
    "bassa": "short (fem.)",
    "basso": "short (masc.)",
    "bicicletta": "bicycle; bike",
    "biondi": "blond (masc. plural)",
    "buon": "good (before a masculine noun)",
    "calcio": "football; soccer",
    "calma": "calm",
    "cambia": "changes",
    "cane": "dog",
    "cani": "dogs",
    "capelli": "hair",
    "carino": "nice; sweet",
    "castani": "brown (hair; masc. plural)",
    "castano": "brown (masc.)",
    "centro": "centre; town centre",
    "cerca": "looks for",
    "cercare": "to look for; to search",
    "cerchi": "you look for (informal)",
    "cerco": "I look for",
    "com'è": "what is ... like?; how is",
    "comparativo": "comparative",
    "compleanno": "birthday",
    "compro": "I buy",
    "computer": "computer",
    "confronti": "comparisons",
    "conoscerti": "to meet you; to know you",
    "conosci": "you know (informal)",
    "corre": "runs",
    "correre": "to run",
    "corretti": "correct (masc. plural)",
    "corri": "you run (informal)",
    "corro": "I run",
    "corso": "course",
    "corti": "short (masc. plural)",
    "cos'altro": "what else",
    "cose": "things",
    "cucinare": "to cook",
    "cucini": "you cook (informal)",
    "cucino": "I cook",
    "dai": "from the (plural)",
    "dalla": "from the (fem.)",
    "dare": "to give",
    "descrivere": "to describe",
    "dice": "says",
    "diciotto": "eighteen",
    "dire": "to say",
    "disegnare": "to draw",
    "disegno": "I draw",
    "diversi": "different (masc. plural)",
    "do": "I give",
    "domestici": "domestic; pet (plural)",
    "domestico": "domestic; pet (as in animale domestico)",
    "dà": "gives",
    "ed": "and (before a vowel)",
    "entrambi": "both",
    "ere": "-ere (verb ending)",
    "esatta": "exact (fem.)",
    "facciamo": "we do; we make",
    "felici": "happy (plural)",
    "femminile": "feminine",
    "festa": "party",
    "festeggia": "celebrates",
    "festeggiamo": "we celebrate",
    "festeggiare": "to celebrate",
    "finale": "final; last",
    "forma": "form",
    "gatta": "cat (female)",
    "gatti": "cats",
    "gatto": "cat",
    "generale": "general",
    "gioca": "plays",
    "giocare": "to play",
    "giochi": "you play (informal)",
    "gioco": "I play",
    "giovane": "young",
    "grigi": "grey (masc. plural)",
    "guarda": "look! (informal command)",
    "h": "the letter h",
    "hobby": "hobby",
    "impara": "learns",
    "imparare": "to learn",
    "impari": "you learn (informal)",
    "imparo": "I learn",
    "iniziamo": "we start; let's start",
    "insieme": "together",
    "interessante": "interesting",
    "invita": "invites",
    "invitare": "to invite",
    "inviti": "you invite (informal)",
    "invito": "I invite",
    "iscritto": "enrolled; registered",
    "jogging": "jogging",
    "l'aggettivo": "the adjective",
    "l'animale": "the animal",
    "l'app": "the app",
    "l'età": "the age",
    "l'invito": "I invite him/her/it",
    "l'istituto": "the institute",
    "l'uccello": "the bird",
    "l'università": "the university",
    "legge": "reads",
    "leggo": "I read",
    "lezione": "lesson",
    "libero": "free",
    "libro": "book",
    "linguistico": "language (adjective)",
    "lui": "he; him",
    "lunghi": "long (masc. plural)",
    "lì": "there",
    "macchina": "car",
    "mai": "never; ever",
    "manda": "sends",
    "mangiare": "to eat",
    "marroni": "brown (eyes)",
    "maschile": "masculine",
    "mette": "puts",
    "mezzi": "means; vehicles",
    "molti": "many (masc. plural)",
    "muoversi": "to move",
    "musica": "music",
    "neri": "black (masc. plural)",
    "nessuna": "no; none (fem.)",
    "nessuno": "nobody; none; neither",
    "noi": "we; us",
    "nuota": "swims",
    "nuotare": "to swim",
    "nuoto": "swimming",
    "nuova": "new (fem.)",
    "nuove": "new (fem. plural)",
    "nuovo": "new (masc.)",
    "occhi": "eyes",
    "parco": "park",
    "parole": "words",
    "passeggiamo": "we go for a walk",
    "passeggiare": "to go for a walk",
    "passeggiata": "walk; stroll",
    "pelo": "fur; coat",
    "pensiero": "thought; kind gesture",
    "pesce": "fish",
    "pesci": "fish (plural)",
    "piccolo": "small",
    "plurale": "plural",
    "plurali": "plural (plural form)",
    "porta": "takes; carries",
    "portare": "to take; to carry",
    "porto": "I take; I carry",
    "pratica": "practice",
    "precedente": "previous",
    "preciso": "precise; specific",
    "preferisce": "prefers",
    "prende": "takes",
    "previsioni": "forecast",
    "pronome": "pronoun",
    "proporre": "to suggest",
    "prossimo": "next",
    "quand'è": "when is",
    "quella": "that one (fem.)",
    "quindi": "so; therefore",
    "ragazza": "girl",
    "regalo": "gift; present",
    "regolare": "regular",
    "resta": "stays; remains",
    "riconosco": "I recognise",
    "rilassa": "relaxes",
    "sai": "you know (informal)",
    "sanitaria": "health (adjective, fem.)",
    "segue": "follows; takes (a course)",
    "seguire": "to follow; to take (a course)",
    "seguo": "I follow; I take (a course)",
    "sembrano": "they look; they seem",
    "so": "I know",
    "soltanto": "only; just",
    "sostituisce": "replaces; stands for",
    "spagnolo": "Spanish",
    "spasso": "walk; outing (as in portare a spasso)",
    "specifico": "specific",
    "sport": "sport",
    "sportello": "counter; ticket window",
    "squadra": "team",
    "studia": "studies",
    "sugli": "about the (masc. plural)",
    "suo": "his; her",
    "trasporti": "transport",
    "tutti": "everyone; all",
    "tutto": "all; the whole",
    "uccelli": "birds",
    "uccello": "bird",
    "uguale": "the same",
    "un'app": "an app",
    "un'impressione": "an impression",
    "universitario": "university (adjective)",
    "usa": "uses",
    "usano": "they use",
    "usare": "to use",
    "usi": "you use (informal)",
    "vai": "you go (informal)",
    "vanno": "they go",
    "vengo": "I come",
    "verbo": "verb",
    "verdi": "green (plural)",
    "vi": "you (plural); to you (plural)",
    "viaggia": "travels",
    "videogiochi": "video games",
    "viene": "comes; is coming",
    "vieni": "you come (informal)",
    "vocale": "vowel",
    "voglio": "I want",
    "voi": "you (plural)",
    "volentieri": "gladly; with pleasure",
    "vorresti": "you would like (informal)",
    "yoga": "yoga",
}
DERIVED_TARGET_POS: dict[str, str] = {
    "Chiara": "proper_noun",
    "Giulia": "proper_noun",
    "Luca": "proper_noun",
    "Marco": "proper_noun",
    "Nina": "proper_noun",
    "Pico": "proper_noun",
    "abita": "verb",
    "ai": "preposition",
    "all'istituto": "phrase",
    "allo": "preposition",
    "alta": "adjective",
    "alto": "adjective",
    "altri": "adjective",
    "ama": "verb",
    "amano": "verb",
    "amare": "verb",
    "amiamo": "verb",
    "amo": "verb",
    "ancora": "adverb",
    "anziano": "adjective",
    "arrivederci": "phrase",
    "ascoltare": "verb",
    "ascolto": "verb",
    "avere": "verb",
    "azzurri": "adjective",
    "bassa": "adjective",
    "basso": "adjective",
    "biondi": "adjective",
    "buon": "adjective",
    "cambia": "verb",
    "carino": "adjective",
    "castani": "adjective",
    "castano": "adjective",
    "cerca": "verb",
    "cercare": "verb",
    "cerchi": "verb",
    "cerco": "verb",
    "com'è": "phrase",
    "compro": "verb",
    "conoscerti": "verb",
    "conosci": "verb",
    "corre": "verb",
    "correre": "verb",
    "corretti": "adjective",
    "corri": "verb",
    "corro": "verb",
    "corti": "adjective",
    "cos'altro": "phrase",
    "cucinare": "verb",
    "cucini": "verb",
    "cucino": "verb",
    "dai": "preposition",
    "dalla": "preposition",
    "dare": "verb",
    "descrivere": "verb",
    "dice": "verb",
    "dire": "verb",
    "disegnare": "verb",
    "disegno": "verb",
    "diversi": "adjective",
    "do": "verb",
    "domestici": "adjective",
    "domestico": "adjective",
    "dà": "verb",
    "ed": "particle",
    "entrambi": "pronoun",
    "esatta": "adjective",
    "facciamo": "verb",
    "felici": "adjective",
    "femminile": "adjective",
    "festeggia": "verb",
    "festeggiamo": "verb",
    "festeggiare": "verb",
    "finale": "adjective",
    "generale": "adjective",
    "gioca": "verb",
    "giocare": "verb",
    "giochi": "verb",
    "gioco": "verb",
    "giovane": "adjective",
    "grigi": "adjective",
    "guarda": "verb",
    "impara": "verb",
    "imparare": "verb",
    "impari": "verb",
    "imparo": "verb",
    "iniziamo": "verb",
    "insieme": "adverb",
    "interessante": "adjective",
    "invita": "verb",
    "invitare": "verb",
    "inviti": "verb",
    "invito": "verb",
    "iscritto": "adjective",
    "l'invito": "phrase",
    "legge": "verb",
    "leggo": "verb",
    "libero": "adjective",
    "linguistico": "adjective",
    "lui": "pronoun",
    "lunghi": "adjective",
    "lì": "adverb",
    "mai": "adverb",
    "manda": "verb",
    "mangiare": "verb",
    "marroni": "adjective",
    "maschile": "adjective",
    "mette": "verb",
    "molti": "adjective",
    "muoversi": "verb",
    "neri": "adjective",
    "nessuna": "adjective",
    "nessuno": "pronoun",
    "noi": "pronoun",
    "nuota": "verb",
    "nuotare": "verb",
    "nuova": "adjective",
    "nuove": "adjective",
    "nuovo": "adjective",
    "passeggiamo": "verb",
    "passeggiare": "verb",
    "piccolo": "adjective",
    "plurale": "adjective",
    "plurali": "adjective",
    "porta": "verb",
    "portare": "verb",
    "porto": "verb",
    "precedente": "adjective",
    "preciso": "adjective",
    "preferisce": "verb",
    "prende": "verb",
    "proporre": "verb",
    "prossimo": "adjective",
    "quand'è": "phrase",
    "quella": "pronoun",
    "quindi": "adverb",
    "regolare": "adjective",
    "resta": "verb",
    "riconosco": "verb",
    "rilassa": "verb",
    "sai": "verb",
    "sanitaria": "adjective",
    "segue": "verb",
    "seguire": "verb",
    "seguo": "verb",
    "sembrano": "verb",
    "so": "verb",
    "soltanto": "adverb",
    "sostituisce": "verb",
    "specifico": "adjective",
    "studia": "verb",
    "sugli": "preposition",
    "suo": "pronoun",
    "tutti": "pronoun",
    "tutto": "adjective",
    "uguale": "adjective",
    "universitario": "adjective",
    "usa": "verb",
    "usano": "verb",
    "usare": "verb",
    "usi": "verb",
    "vai": "verb",
    "vanno": "verb",
    "vengo": "verb",
    "verdi": "adjective",
    "vi": "pronoun",
    "viaggia": "verb",
    "viene": "verb",
    "vieni": "verb",
    "voglio": "verb",
    "voi": "pronoun",
    "volentieri": "adverb",
    "vorresti": "verb",
}
DERIVED_TARGET_CITATION: dict[str, str] = {
}
for _tok, _gloss in DERIVED_TARGET_GLOSSES.items():
    GLOSSES.setdefault(_tok, _gloss)
for _tok, _pos in DERIVED_TARGET_POS.items():
    POS_SETS.setdefault(_pos, set()).add(_tok)
# --- end derive_target.py ---

POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())

CATEGORY_TAGS: dict[str, list[str]] = {}
for _tag, _words in {
    "it_number": "zero uno due tre quattro cinque sette otto nove dieci "
                 "dodici quindici trenta cinquanta venti quaranta quattordici",
    "it_weekday": "lunedì martedì mercoledì giovedì venerdì sabato domenica",
    "it_month": "gennaio febbraio marzo aprile",
    "it_family": "madre padre fratello sorella nonno nonna fratelli sorelle "
                 "marito moglie figli figlio figlia",
}.items():
    for _w in _words.split():
        CATEGORY_TAGS.setdefault(_w, []).append(_tag)

# First-sight glosses reused from A1 that do not fit the A2 unit's sense,
# keyed by (realization stem, token).
GLOSS_OVERRIDES = {
    ("a2_unit27_banca", "conto"): "bank account; bill",
    ("a2_unit30_colloquio", "parli"): "speak (formal command)",
    ("a2_unit31_viaggio_interrotto", "dal"): "from the (masc.)",
    ("a2_unit32_vita_online", "tempo"): "time",
    ("a2_unit34_reclamo", "lo"): "the (masc., before some sounds)",
    ("b1_unit35_capacita", "che"): "that (introduces a clause)",
    ("b1_unit38_dibattito", "piano"): "plan",
    ("b1_unit38_dibattito", "tempo"): "time",
    ("b1_unit38_dibattito", "pronto"): "ready",
    ("b1_unit38_dibattito", "fa"): "makes; does",
    ("b1_unit41_condizioni", "chiamo"): "I call",
    ("b1_unit45_consigli", "ci"): "about it; there",
    ("b1_unit52_riassumere", "si"): "himself (reflexive)",
    ("b1_unit53_concessioni", "secondo"): "second (masc.)",
}

# POS of a B1 first-sight sense that differs from the A1/A2 entry.
POS_OVERRIDES = {
    ("b1_unit35_capacita", "che"): "particle",
    ("b1_unit38_dibattito", "piano"): "noun",
    ("b1_unit38_dibattito", "pronto"): "adjective",
    ("b1_unit53_concessioni", "secondo"): "adjective",
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
