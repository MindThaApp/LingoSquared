#!/usr/bin/env python3
"""Idempotently backfill en-pl (Polish target) lexemes for the "Polish A1"
course, so en-pl practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24. All plumbing lives in
scripts/_target_lexeme_backfill_common.py (see its docstring for the tag
scheme); this file is data only: one hand-written English gloss and one part
of speech per citation form.

Scope: A1 ("en-pl", units 01-20) and A2 ("en-pl-a2", units 21-26; session 11).
B1+ is not classified yet; extend LEVELS and the tables below together.

Glossing rules followed here (PRACTICE_PACK_RECIPE.md section 0.1, 6.6):
* the gloss is the sense the unit actually teaches at first sight,
* inflected forms say whose form / which case ("you have (informal)",
  "of the bank"), so a bare-word translation prompt names one form,
* gender pairs are glossed "(masc.)"/"(fem.)" so the two are never
  interchangeable answers.

Sentence-initial capitals fold to lowercase; the proper nouns below (and the
clothing size letter M) keep their capital.

Run (after the en-pl course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_pl.py

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

LANG = "pl"
LEVELS = {"a1": "en-pl", "a2": "en-pl-a2"}

PROPER_NOUNS = {
    "Anna", "Kowalska", "Kanady", "Warszawie", "Marek", "Wójcik", "Ewa",
    "Gdańsku", "Krakowie", "Kraków", "Krakowa", "Warszawa", "Warszawy",
    "Kwiatowa",
}
# Capital kept on purpose: proper nouns plus the clothing size letter.
_KEEP_CASE = PROPER_NOUNS | {"M"}
_KEEP_BY_LOWER = {p.lower(): p for p in _KEEP_CASE}


def normalize(token: str) -> str:
    lower = token.lower()
    return _KEEP_BY_LOWER.get(lower, lower)


GLOSSES: dict[str, str] = {
    # unit01 greetings
    "pan": "Mr.; sir (formal address to a man)",
    "pani": "Mrs.; ma'am (formal address to a woman)",
    "ty": "you (informal, singular)", "jak": "how", "się": "oneself (reflexive word)",
    "ma": "has; (in a greeting) is doing", "masz": "you have (informal)",
    "dobrze": "well; fine", "dziękuję": "thank you; I thank", "a": "and; but",
    "cześć": "hi; bye (informal)", "dzień": "day", "dobry": "good (masc.)",
    "wieczór": "evening", "dobranoc": "good night", "do": "to; until; up to",
    "widzenia": "seeing (in the goodbye phrase)", "zobaczenia": "seeing (in 'see you')",
    "miłego": "nice (masc., of a day)", "dnia": "of the day",
    "nazywa": "is called (he; she; formal you)", "na": "on; for",
    "imię": "first name", "nazywam": "I am called (with się)",
    "Anna": "Anna", "Kowalska": "Kowalska", "mam": "I have",
    "bardzo": "very", "mi": "to me", "miło": "pleasant; nice",
    "skąd": "where from", "jesteś": "you are (informal)", "jestem": "I am",
    "z": "from; with", "Kanady": "Canada (after 'from')",
    "mieszkam": "I live", "w": "in; at; on", "Warszawie": "Warsaw (after 'in')",
    "Marek": "Marek", "Wójcik": "Wójcik", "jest": "is",
    "ale": "but", "czy": "whether (starts a yes/no question)",
    "mówi": "speaks; says (he; she; formal you)", "po": "after; in (a language)",
    "polsku": "Polish (after 'po': in Polish)", "tak": "yes; so", "trochę": "a little",
    "jeszcze": "still; yet", "uczę": "I am learning; I teach",
    # unit02 numbers
    "zero": "zero", "jeden": "one", "dwa": "two", "trzy": "three",
    "cztery": "four", "pięć": "five", "sześć": "six", "siedem": "seven",
    "osiem": "eight", "dziewięć": "nine", "dziesięć": "ten",
    "jedenaście": "eleven", "dwanaście": "twelve", "piętnaście": "fifteen",
    "dwadzieścia": "twenty", "trzydzieści": "thirty",
    "pięćdziesiąt": "fifty", "sto": "one hundred",
    "ile": "how much; how many", "to": "this; it", "kosztuje": "it costs",
    "złotych": "zloty (currency, plural form after a number)",
    "jaki": "what kind of; which (masc.)", "pana": "your (formal, to a man)",
    "numer": "number", "telefonu": "of the phone",
    "twój": "your (informal, masc.)", "lat": "years (after 5-21, 25-31 and round tens)",
    "lata": "years (after 2-4, 22-24, 32-34 ...)", "było": "it was",
    "porozmawiać": "to talk; to chat",
    # unit03 dates
    "poniedziałek": "Monday", "wtorek": "Tuesday", "środa": "Wednesday",
    "czwartek": "Thursday", "piątek": "Friday", "sobota": "Saturday",
    "niedziela": "Sunday", "dziś": "today", "tygodnia": "of the week",
    "we": "on; in (variant of 'w' before some sounds)",
    "idę": "I go; I am going", "kina": "cinema (after 'to')",
    "styczeń": "January", "luty": "February", "marzec": "March",
    "kwiecień": "April", "maj": "May", "czerwiec": "June", "lipiec": "July",
    "sierpień": "August", "wrzesień": "September",
    "październik": "October", "listopad": "November", "grudzień": "December",
    "urodziny": "birthday", "kiedy": "when", "są": "they are",
    "twoje": "your (informal, neuter or plural)", "moje": "my (neuter)",
    "dziesiątego": "tenth (in a date)", "maja": "of May",
    "spotkanie": "meeting", "piętnastego": "fifteenth (in a date)",
    "lutego": "of February", "możemy": "we can", "znowu": "again",
    "spotkać": "to meet", "panu": "to you (formal, to a man)",
    "odpowiada": "it suits; it works for", "ci": "to you (informal)",
    "data": "date (calendar date)", "jaka": "what kind of; which (fem.)",
    "będzie": "will be", "świetnie": "great; excellent",
    # unit04 time
    "pierwsza": "one o'clock", "druga": "two o'clock", "trzecia": "three o'clock",
    "czwarta": "four o'clock", "piąta": "five o'clock", "szósta": "six o'clock",
    "siódma": "seven o'clock", "ósma": "eight o'clock",
    "dziewiąta": "nine o'clock", "dziesiąta": "ten o'clock",
    "jedenasta": "eleven o'clock", "dwunasta": "twelve o'clock",
    "która": "which (fem.)", "godzina": "hour; time of day",
    "mówimy": "we say", "nie": "no; not", "rano": "in the morning",
    "południe": "noon", "południu": "noon (after 'po': in the afternoon)",
    "wieczorem": "in the evening", "nocy": "at night",
    "o": "at (a time); about", "której": "which (fem., after 'at')",
    "godzinie": "hour (after 'at')", "czwartej": "four o'clock (after 'at')",
    "siódmej": "seven o'clock (after 'at')",
    "dziesiątej": "ten o'clock (after 'at')", "Ewa": "Ewa",
    "wstaje": "gets up (he; she)", "pociąg": "train",
    "odjeżdża": "departs; leaves (he; she; it)", "może": "maybe; perhaps",
    # unit05 family
    "rodzina": "family", "matka": "mother", "ojciec": "father",
    "brat": "brother", "siostra": "sister", "rodzice": "parents",
    "mój": "my (masc.)", "moja": "my (fem.)", "moi": "my (plural, people)",
    "dziadek": "grandfather", "babcia": "grandmother", "wujek": "uncle",
    "ciotka": "aunt", "syn": "son", "córka": "daughter", "mieć": "to have",
    "brata": "brother (object form)", "siostrę": "sister (object form)",
    "syna": "son (object form)", "córkę": "daughter (object form)",
    "i": "and", "lub": "or", "tylko": "only", "gdzie": "where",
    "on": "he", "ona": "she", "mieszka": "lives (he; she)",
    "Gdańsku": "Gdańsk (after 'in')", "Krakowie": "Kraków (after 'in')",
    "ja": "I", "fajna": "nice; cool (fem.)",
    # unit06 food
    "chleb": "bread", "masło": "butter", "ser": "cheese", "woda": "water",
    "mleko": "milk", "kawa": "coffee", "herbata": "tea",
    "proszę": "please; I ask for", "kawę": "coffee (object form)",
    "herbatę": "tea (object form)", "wodę": "water (object form)",
    "zupa": "soup", "sok": "juice", "cukier": "sugar", "rachunek": "bill; check",
    "lubić": "to like", "lubię": "I like", "lubi": "likes (he; she)",
    "zupę": "soup (object form)", "danie": "dish", "polecać": "to recommend",
    "polecam": "I recommend", "poleca": "recommends (he; she; formal you)",
    "co": "what", "już": "already; right away", "podaję": "I serve; I hand over",
    # unit07 shopping
    "banan": "banana", "pomidor": "tomato", "ogórek": "cucumber",
    "ziemniak": "potato", "cebula": "onion", "tanio": "cheap; cheaply",
    "drogo": "expensive; expensively", "kosztować": "to cost",
    "kosztują": "they cost", "banany": "bananas", "grejpfrut": "grapefruit",
    "mandarynka": "tangerine", "pomarańcza": "orange", "kilo": "kilo",
    "pół": "half", "poproszę": "I would like; please give me",
    "bananów": "of bananas", "pomidorów": "of tomatoes",
    "ziemniaków": "of potatoes", "dla": "for", "świeże": "fresh (plural)",
    "razem": "together; in total", "pomidory": "tomatoes",
    # unit08 places
    "bank": "bank", "poczta": "post office", "apteka": "pharmacy",
    "restauracja": "restaurant", "hotel": "hotel", "park": "park",
    "blisko": "near; close", "daleko": "far", "niedaleko": "not far",
    "obok": "next to", "naprzeciwko": "across from; opposite",
    "banku": "of the bank", "hotelu": "of the hotel", "parku": "of the park",
    "przepraszam": "excuse me; I am sorry",
    # unit09 directions
    "iść": "to go (on foot)", "dojść": "to get to; to arrive at",
    "prosto": "straight ahead", "tam": "there", "potem": "then; after that",
    "prawo": "right (direction)", "lewo": "left (direction)",
    "skręcić": "to turn", "ulica": "street", "rozumiem": "I understand",
    # unit10 routines
    "wstawać": "to get up", "wstaję": "I get up", "jeść": "to eat",
    "jem": "I eat", "śniadanie": "breakfast", "pić": "to drink",
    "piję": "I drink", "obiad": "lunch; midday meal", "pracować": "to work",
    "pracuję": "I work", "dom": "home; house", "domu": "home; house (after 'to')",
    "wracać": "to return; to go back", "wracam": "I return; I go back",
    "spać": "to sleep", "śpię": "I sleep", "też": "too; also",
    "wcześnie": "early",
    # unit11 plans
    "chcieć": "to want", "chcę": "I want", "chcesz": "you want (informal)",
    "kino": "cinema; movie theater", "móc": "to be able to; can",
    "mogę": "I can", "możesz": "you can (informal)", "przyjść": "to come",
    "chętnie": "gladly; with pleasure", "niestety": "unfortunately",
    "sobotę": "Saturday (after 'on')",
    # unit12 past events
    "wczoraj": "yesterday", "byłem": "I was (said by a man)",
    "byłam": "I was (said by a woman)", "kinie": "cinema (after 'in')",
    "film": "movie; film", "zobaczyłem": "I saw (said by a man)",
    "zobaczyłam": "I saw (said by a woman)",
    "zrobiłem": "I did; I made (said by a man)",
    "zrobiłam": "I did; I made (said by a woman)",
    "pyszny": "tasty; delicious (masc.)",
    # unit13 preferences
    "muzyka": "music", "muzykę": "music (object form)",
    "lubisz": "you like (informal)", "wolę": "I prefer",
    # unit14 comparisons
    "młody": "young (masc.)", "stary": "old (masc.)",
    "starszy": "older (masc.)", "starsza": "older (fem.)",
    "młodszy": "younger (masc.)", "młodsza": "younger (fem.)",
    "niż": "than", "zły": "bad (masc.)", "lepszy": "better (masc.)",
    "lepsza": "better (fem.)", "gorszy": "worse (masc.)",
    "gorsza": "worse (fem.)",
    # unit15 travel
    "dworzec": "station", "bilet": "ticket", "peron": "platform",
    "Kraków": "Kraków", "Krakowa": "Kraków (after 'to')",
    "jechać": "to go (by vehicle); to travel", "jadę": "I go (by vehicle)",
    "jedzie": "goes (by vehicle) (he; she)", "jutro": "tomorrow",
    "autobus": "bus", "Warszawa": "Warsaw", "Warszawy": "Warsaw (after 'to')",
    "dokąd": "where to", "miłej": "pleasant (fem., of a trip)",
    "podróży": "of the trip",
    # unit16 health
    "boleć": "to hurt; to ache", "boli": "it hurts (he; she; it)",
    "bolą": "they hurt", "mnie": "me", "głowa": "head", "gardło": "throat",
    "brzuch": "stomach", "zęby": "teeth", "cię": "you (object, informal)",
    "czuć": "to feel", "czuję": "I feel", "czujesz": "you feel (informal)",
    "źle": "badly; poorly", "gorączka": "fever", "gorączkę": "fever (object form)",
    "chory": "sick (masc.)", "chora": "sick (fem.)", "odpocząć": "to rest",
    # unit17 work
    "inżynierem": "engineer (after 'is' or 'am')",
    "nauczycielką": "teacher, fem. (after 'is' or 'am')",
    "inżynier": "engineer", "nauczyciel": "teacher (masc.)",
    "nauczycielka": "teacher (fem.)",
    "nauczycielem": "teacher, masc. (after 'is' or 'am')",
    "pracujesz": "you work (informal)", "szkoła": "school", "biuro": "office",
    "szkole": "school (after 'at')", "biurze": "office (after 'at')",
    # unit18 housing
    "mieszkanie": "apartment", "duży": "big; large (masc.)", "pokój": "room",
    "pokoi": "of rooms", "pokoje": "rooms", "kuchnia": "kitchen",
    "mała": "small (fem.)", "sypialnia": "bedroom", "łazienka": "bathroom",
    "pokoju": "room (after 'in')", "kuchni": "kitchen (after 'in')",
    "sypialni": "bedroom (after 'in')", "łazience": "bathroom (after 'in')",
    "lodówka": "refrigerator; fridge", "piekarnik": "oven",
    # unit19 weather
    "pogoda": "weather", "zimno": "cold", "gorąco": "hot", "pada": "it rains",
    "śnieg": "snow", "mgła": "fog", "dobra": "good (fem.)",
    "straszna": "terrible (fem.)", "bo": "because",
    # unit20 clothing
    "sklep": "store; shop", "koszula": "shirt", "spodnie": "pants; trousers",
    "kupić": "to buy", "koszulę": "shirt (object form)", "kolor": "color",
    "sukienka": "dress", "niebieska": "blue (fem.)", "czerwona": "red (fem.)",
    "rozmiar": "size", "M": "size M", "chce": "wants (he; she; formal you)",
    # a2 unit21 official matters
    "nowy": "new (masc.)", "urząd": "office (government)",
    "urzędzie": "office (after 'in', government)", "adres": "address",
    "dokumenty": "documents", "dowód": "proof; ID card",
    "osobisty": "personal (masc.)", "zameldować": "to register (as a resident)",
    "chciałabym": "I would like (said by a woman)",
    "czym": "what; how (in 'how can I help')", "pomóc": "to help",
    "ponieważ": "because (joins two clauses)",
    "przeprowadziłam": "I moved (house; said by a woman)",
    "muszę": "I must; I have to", "umowa": "agreement; contract",
    "umowę": "contract (object form)", "najmu": "of renting; rental",
    "dni": "days", "Kwiatowa": "Kwiatowa (a street name)",
    "od": "since; from", "przeprowadzki": "of the move (change of home)",
    "wszystko": "everything", "gotowe": "ready; done (neut.)",
    # a2 unit22 opinions
    "opinia": "opinion", "opinię": "opinion (object form)",
    "myślę": "I think", "że": "that (introduces a clause)",
    "rację": "being right (object form, in 'you are right')",
    "jedzenie": "food", "smaczne": "tasty (neut.)",
    "moim": "my (in 'in my opinion')", "zdaniem": "opinion; view (in 'in my opinion')",
    "droga": "expensive (fem.)", "za": "too (before an adjective)",
    "zgadzam": "I agree", "spróbuję": "I will try", "raz": "time; once",
    # a2 unit23 bank
    "konto": "account", "pieniądze": "money", "pieniędzy": "money (form used after 'a lot of')",
    "pesel": "PESEL (national ID number)",
    "chciałbym": "I would like (said by a man)", "otworzyć": "to open",
    "bankowe": "bank (neut., as in 'bank account')", "potrzebuję": "I need",
    "dowodu": "ID card (form used after 'I need')",
    "osobistego": "personal (form used after 'I need')",
    "żeby": "in order to", "wpłacić": "to pay in; to deposit",
    "oczywiście": "of course",
    # a2 unit24 doctor
    "panią": "Ms.; ma'am (object form)", "trzech": "three (form used after 'since')",
    "powinna": "should (she; formal you to a woman)",
    "powinnam": "I should (said by a woman)", "lekarstwo": "medicine",
    "brać": "to take", "razy": "times", "dziennie": "per day; daily",
    "wrócić": "to return; to come back", "tydzień": "week",
    # a2 unit25 repairs
    "mieszkaniu": "apartment (after 'in')", "ogrzewanie": "heating",
    "działa": "works; is working", "zepsute": "broken (neut.)",
    "naprawić": "to repair; to fix",
    "mógłby": "could (he; polite request to a man)",
    "najszybciej": "soonest; most quickly",
    # a2 unit26 interview
    "praca": "work; job", "pracy": "work; job (form used after 'looking for')",
    "rozmowa": "conversation; interview", "rozmowę": "conversation; interview (object form)",
    "kwalifikacyjna": "job-interview (fem., describes 'interview')",
    "kwalifikacyjną": "job-interview (fem., object form)",
    "doświadczenie": "experience", "doświadczenia": "experience (form used after 'no' or 'of')",
    "pytania": "questions", "pracowałem": "I worked (said by a man)",
    "jako": "as (in the role of)", "dostępny": "available (masc.)",
    "razu": "time; occasion (in 'right away')", "godziny": "hours",
    "elastyczne": "flexible (plural)", "jakie": "what kind of (plural)",
    "doskonale": "excellent; perfectly",
}

POS_SETS = {
    "proper_noun": PROPER_NOUNS,
    "pronoun": split_words(
        "pan pani ty się mi ja on ona to mój moja moi twój twoje moje "
        "mnie cię ci panu pana co która której jaki jaka"
    ),
    "preposition": split_words("z w we po do na o dla obok naprzeciwko"),
    "particle": split_words(
        "a ale i lub czy nie tak bo niż też tylko jeszcze już jak gdzie kiedy "
        "skąd dokąd ile"
    ),
    "adjective": split_words(
        "dobry miłego fajna pyszny młody stary starszy starsza młodszy młodsza "
        "zły lepszy lepsza gorszy gorsza chory chora duży mała dobra straszna "
        "niebieska czerwona świeże miłej pierwsza druga trzecia czwarta piąta "
        "szósta siódma ósma dziewiąta dziesiąta jedenasta dwunasta czwartej "
        "siódmej dziesiątej dziesiątego piętnastego pół zero jeden dwa trzy "
        "cztery pięć sześć siedem osiem dziewięć dziesięć jedenaście dwanaście "
        "piętnaście dwadzieścia trzydzieści pięćdziesiąt sto"
    ),
    "adverb": split_words(
        "dobrze bardzo miło trochę dziś znowu świetnie rano wieczorem nocy "
        "może polsku blisko daleko niedaleko prosto tam potem wcześnie "
        "chętnie niestety wczoraj tanio drogo razem źle jutro zimno gorąco "
        "południu"
    ),
    "verb": split_words(
        "ma masz mam mieć jest jestem jesteś mieszkam mieszka mówi uczę kosztuje "
        "było idę są możemy spotkać odpowiada będzie nazywa nazywam mówimy "
        "wstaje odjeżdża lubić lubię lubi polecać polecam poleca podaję "
        "kosztować kosztują poproszę proszę przepraszam iść dojść skręcić "
        "rozumiem wstawać wstaję jeść jem pić piję pracować pracuję wracać "
        "wracam spać śpię chcieć chcę chcesz móc mogę możesz przyjść byłem "
        "byłam zobaczyłem zobaczyłam zrobiłem zrobiłam lubisz wolę jechać "
        "jadę jedzie boleć boli bolą czuć czuję czujesz odpocząć pracujesz "
        "pada kupić chce porozmawiać dziękuję"
    ),
    "phrase": split_words(
        "cześć dobranoc widzenia zobaczenia"
    ),
}
POS_SETS["proper_noun"] = POS_SETS["proper_noun"] | {"Kwiatowa"}
POS_SETS["verb"] |= split_words(
    "zameldować chciałabym pomóc przeprowadziłam muszę myślę zgadzam spróbuję "
    "chciałbym otworzyć potrzebuję wpłacić powinna powinnam brać wrócić działa "
    "naprawić mógłby pracowałem"
)
POS_SETS["adjective"] |= split_words(
    "nowy osobisty gotowe smaczne droga bankowe osobistego elastyczne dostępny "
    "kwalifikacyjna kwalifikacyjną zepsute trzech"
)
POS_SETS["adverb"] |= split_words("oczywiście najszybciej dziennie doskonale")
POS_SETS["pronoun"] |= split_words("czym wszystko moim panią jakie")
POS_SETS["preposition"] |= split_words("od za jako")
POS_SETS["particle"] |= split_words("ponieważ żeby że")
POS_SETS["verb"] |= split_words(
    "zameldować chciałabym pomóc przeprowadziłam muszę myślę zgadzam spróbuję "
    "chciałbym otworzyć potrzebuję wpłacić powinna powinnam brać wrócić działa "
    "naprawić mógłby pracowałem"
)
POS_SETS["adjective"] |= split_words(
    "nowy osobisty gotowe smaczne droga bankowe osobistego elastyczne dostępny "
    "kwalifikacyjna kwalifikacyjną zepsute trzech"
)
POS_SETS["adverb"] |= split_words("oczywiście najszybciej dziennie doskonale")
POS_SETS["pronoun"] |= split_words("czym wszystko moim panią jakie")
POS_SETS["preposition"] |= split_words("od za jako")
POS_SETS["particle"] |= split_words("ponieważ żeby że")
POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())

CATEGORY_TAGS: dict[str, list[str]] = {}
for _tag, _words in {
    "pl_number": "zero jeden dwa trzy cztery pięć sześć siedem osiem dziewięć "
                 "dziesięć jedenaście dwanaście piętnaście dwadzieścia "
                 "trzydzieści pięćdziesiąt sto",
    "pl_weekday": "poniedziałek wtorek środa czwartek piątek sobota niedziela",
    "pl_month": "styczeń luty marzec kwiecień maj czerwiec lipiec sierpień "
                "wrzesień październik listopad grudzień",
    "pl_family": "rodzina matka ojciec brat siostra rodzice dziadek babcia "
                 "wujek ciotka syn córka",
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
