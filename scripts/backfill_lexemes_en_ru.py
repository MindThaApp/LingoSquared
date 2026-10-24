#!/usr/bin/env python3
"""Idempotently backfill en-ru (Russian target) lexemes for the "Russian A1"
course, so en-ru practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24. All plumbing lives in
scripts/_target_lexeme_backfill_common.py (see its docstring for the tag
scheme); this file is data only: one hand-written English gloss and one part
of speech per citation form.

Scope: A1 only (the "en-ru-a1" manifest group, units 01-24). A2+ is not
classified yet; extend LEVELS and the tables below together.

Glossing rules followed here (PRACTICE_PACK_RECIPE.md section 0.1, 6.6):
* the gloss is the sense the unit actually teaches at first sight; a token
  with two taught senses gets both ("a; b"),
* inflected forms say what they do ("you (informal), after the word for
  'at'"), so a bare-word translation prompt names one form,
* gender pairs are glossed "(masc.)"/"(fem.)" so the two are never
  interchangeable answers; formal/informal "you" is always spelled out,
* no Russian inside any gloss.

Normalization: all tokens fold to lowercase except the proper nouns below.
The realizations carry NO stress marks (U+0301) and never mix ё/е spellings of
one word (checked over all 425 raw tokens / 376 folded), so no citation-form
remapping is needed. A token that is both a letter and a word (а, в, с, у) is
one lexeme whose gloss gives both taught senses.

Run (after the en-ru course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_ru.py

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

LANG = "ru"
LEVELS = {"a1": "en-ru-a1"}

PROPER_NOUNS = {
    "Анна", "Максим", "Виктор", "Канады", "Канада", "Москвы", "Москва",
    "Ирина", "Петровна", "Джон", "Ольга", "Тверской", "Чайковского",
    "Пушкина", "Олег", "Мария", "Настя", "Дима", "Тулы",
}
_PROPER_BY_LOWER = {p.lower(): p for p in PROPER_NOUNS}


def normalize(token: str) -> str:
    lower = token.lower()
    return _PROPER_BY_LOWER.get(lower, lower)


GLOSSES: dict[str, str] = {
    # unit01 greetings
    "з": "the letter Z", "д": "the letter D", "р": "the letter R",
    "а": "the letter A; and, but (contrast)", "в": "the letter V; in; at",
    "с": "the letter S; from; with", "т": "the letter T",
    "у": "the letter U; at; near (also used to say who has something)", "е": "the letter Ye",
    "ъ": "the hard sign (a letter with no sound of its own)",
    "ь": "the soft sign (a letter with no sound of its own)",
    "й": "the letter short I",
    "здравствуйте": "hello (formal)", "привет": "hi (informal)",
    "доброе": "good (neuter, in greetings)", "утро": "morning", "добрый": "good (masc., in greetings)",
    "день": "day", "вечер": "evening", "как": "how", "дела": "affairs; how things are",
    "поживаете": "you are getting along (formal)", "хорошо": "well; fine",
    "спасибо": "thank you", "так": "so", "себе": "oneself (dative form)",
    "тебя": "you (informal), after the word for 'at'",
    "до": "until; up to; to (a destination)", "свидания": "meeting (as in 'goodbye')",
    "пока": "bye (informal)", "завтра": "tomorrow", "Анна": "Anna",
    "Максим": "Maksim", "тоже": "also; too", "ну": "well (filler)",
    # unit02 introductions
    "вас": "you (formal), object form", "зовут": "they call (as in 'what is your name')",
    "меня": "me (object form)", "Виктор": "Viktor", "вы": "you (formal or plural)",
    "ты": "you (informal)", "можно": "is it possible; may I", "на": "on; in; at; to",
    "давайте": "let's (formal or plural)", "перейдём": "we will switch over",
    "откуда": "from where", "я": "I", "из": "from (out of)",
    "Канады": "Canada", "Канада": "Canada",
    "Москвы": "Moscow", "Москва": "Moscow",
    "познакомимся": "we will get acquainted", "очень": "very",
    "приятно": "pleasant; pleased", "Ирина": "Irina",
    "Петровна": "Petrovna (a woman's patronymic)", "Джон": "John",
    # unit03 numbers
    "один": "one (masc.)", "два": "two (masc. or neuter)", "три": "three",
    "четыре": "four", "пять": "five", "брат": "brother",
    "брата": "brother, as used after two to four",
    "книга": "book", "книги": "books, as used after two to four",
    "рубль": "ruble", "рублей": "rubles, as used after five and up",
    "шесть": "six", "семь": "seven", "восемь": "eight", "девять": "nine",
    "десять": "ten", "книг": "books, as used after five and up",
    "мне": "to me; for me", "лет": "years (of age), as used after five and up",
    "сколько": "how much; how many", "вам": "to you (formal)", "это": "this; this is",
    "стоит": "costs (one thing)", "стоят": "cost (several things)",
    "яблоки": "apples", "рубля": "rubles, as used after two to four",
    "покупатель": "customer", "продавец": "seller; salesperson", "хлеб": "bread",
    # unit04 dates
    "какой": "which; what kind of (masc.)", "сегодня": "today",
    "понедельник": "Monday", "вторник": "Tuesday", "среда": "Wednesday",
    "четверг": "Thursday", "пятница": "Friday", "суббота": "Saturday",
    "воскресенье": "Sunday", "какое": "which; what kind of (neuter)",
    "число": "date; number", "первое": "first (neuter, in a date)",
    "третье": "third (neuter, in a date)", "пятое": "fifth (neuter, in a date)",
    "десятое": "tenth (neuter, in a date)",
    "января": "of January", "апреля": "of April", "октября": "of October",
    "во": "on; in (before a weekday)", "встреча": "meeting",
    "да": "yes", "девятого": "ninth (in a date, 'on the ninth')",
    # unit05 time
    "который": "which (in 'what time is it')", "час": "hour; o'clock",
    "сейчас": "now", "часа": "o'clock, as used after two to four",
    "часов": "o'clock, as used after five and up",
    "котором": "which (prepositional case)", "часу": "hour (prepositional case)",
    "утром": "in the morning", "днём": "in the afternoon; by day",
    "вечером": "in the evening", "ночью": "at night",
    "дня": "in the afternoon (said after a clock time)",
    "вечера": "in the evening (said after a clock time)",
    "скажите": "tell me (formal command)", "пожалуйста": "please; you're welcome",
    "когда": "when", "отходит": "departs; leaves", "поезд": "train",
    "пассажир": "passenger", "кассир": "ticket clerk; cashier",
    "утра": "in the morning (said after a clock time)",
    # unit06 family
    "есть": "there is; there are (also used to say someone has something)", "мать": "mother", "отец": "father",
    "сестра": "sister", "мой": "my (masc.)", "моя": "my (fem.)",
    "бабушка": "grandmother", "дедушка": "grandfather", "муж": "husband",
    "жена": "wife", "сын": "son", "дочь": "daughter", "и": "and",
    "дети": "children", "кто": "who", "её": "her", "фото": "photo",
    "Ольга": "Olga", "семья": "family", "вот": "here is; here are; there",
    "эта": "this (fem.)", "девочка": "girl",
    # unit07 food
    "меню": "menu", "официант": "waiter", "официантка": "waitress",
    "этот": "this (masc.)", "столик": "small table (in a restaurant)",
    "стол": "table; desk", "свободен": "free; vacant (masc.)",
    "садитесь": "sit down (formal command)", "что": "what; that (conjunction)",
    "будете": "you will (formal)", "заказывать": "to order",
    "хочу": "I want", "чай": "tea", "кофе": "coffee", "борщ": "borscht (beet soup)",
    "салат": "salad", "мороженое": "ice cream",
    "принесите": "bring (formal command)", "турист": "tourist", "пить": "to drink",
    "сладкое": "dessert; something sweet",
    # unit08 shopping
    "магазин": "store", "сто": "one hundred", "молоко": "milk",
    "дайте": "give me (formal command)", "килограмм": "kilogram",
    "полкило": "half a kilo", "штука": "piece (item)",
    "штуку": "piece (item), as the object of 'give me'",
    "штук": "pieces, as used after five and up",
    "помидоры": "tomatoes", "огурцы": "cucumbers", "картофель": "potatoes",
    "капуста": "cabbage", "яблок": "apples, as used after a quantity word (kilo, five and up)",
    "апельсины": "oranges", "апельсинов": "oranges, as used after a quantity word (kilo, five and up)",
    "помидоров": "tomatoes, as used after a quantity word (kilo, five and up)", "кило": "kilo (colloquial)",
    "двести": "two hundred",
    # unit09 places
    "где": "where", "находится": "is located", "улица": "street",
    "улице": "street (prepositional case, 'on the street')",
    "Тверской": "Tverskaya (a Moscow street name)", "банк": "bank",
    "аптека": "pharmacy", "вокзал": "train station", "гостиница": "hotel",
    "ресторан": "restaurant", "библиотека": "library",
    "Чайковского": "Tchaikovsky (in a street name)",
    "Пушкина": "Pushkin (in a street name)",
    "вашей": "your (formal), feminine, prepositional case",
    "моей": "my, feminine, prepositional case", "большое": "big; large (neuter)",
    # unit10 directions
    "дойти": "to get to (on foot)", "музей": "museum",
    "музея": "museum, after the word for 'to/until'", "прямо": "straight ahead",
    "идите": "go (formal command)", "направо": "to the right", "потом": "then; afterwards",
    "налево": "to the left", "поверните": "turn (formal command)",
    "за": "behind; around", "углом": "corner (instrumental case)",
    "квартал": "block (city)", "квартала": "blocks, as used after two to four",
    "далеко": "far", "отсюда": "from here", "банка": "banks, as used after two to four",
    "простите": "excuse me (formal command)", "прохожий": "passerby",
    "просто": "simply; simple", "минут": "minutes, as used after five and up",
    "пешком": "on foot",
    # unit11 routines
    "встаю": "I get up", "встаёте": "you get up (formal)",
    "завтракаю": "I have breakfast", "работаю": "I work",
    "девяти": "nine (genitive case, after 'from' or 'until')",
    "пяти": "five (genitive case, after 'from' or 'until')", "ужинаю": "I have dinner",
    "ложусь": "I lie down; I go (to bed)", "спать": "to sleep",
    "одиннадцать": "eleven", "Олег": "Oleg", "делаете": "you do (formal)",
    "Мария": "Maria", "работаете": "you work (formal)", "понятно": "understood; I see",
    # unit12 plans
    "давай": "let's (informal)", "пойдём": "we will go; let's go",
    "кино": "the movies; cinema", "субботу": "Saturday, as 'on Saturday'",
    "согласен": "agreed (said by a man)", "к": "to; toward",
    "сожалению": "regret (dative case, in 'unfortunately')", "не": "not",
    "могу": "I can", "мы": "we", "встретимся": "we will meet",
    "Настя": "Nastya", "Дима": "Dima", "кинотеатра": "movie theater, after the word for 'at'",
    "отлично": "great; excellent", "субботы": "Saturday, after the word for 'until'",
    # unit13 past events
    "вчера": "yesterday", "был": "was (masc.)", "дома": "at home",
    "была": "was (fem.)", "она": "she", "ходил": "went (masc.)",
    "ходила": "went (fem.)", "смотрел": "watched (masc.)",
    "смотрела": "watched (fem.)", "фильм": "film", "делал": "did (masc.)",
    "хороший": "good (masc.)", "отдыхала": "rested (fem.)",
    # unit14 preferences
    "нравится": "is pleasing (used to say you like something)",
    "не хочу": "I don't want", "сок": "juice", "тебе": "to you (informal)",
    # unit15 comparisons
    "лучше": "better", "чем": "than", "хуже": "worse", "кафе": "cafe",
    "больше": "bigger; more", "то": "that (neuter)", "меньше": "smaller; less",
    "дом": "house", "тот": "that (masc.)",
    # unit16 health
    "болит": "hurts", "голова": "head", "живот": "stomach", "горло": "throat",
    "температура": "temperature; fever", "простуда": "a cold (illness)",
    "плохо": "bad; badly", "ещё": "also; still; more", "нужно": "necessary; need to",
    "отдыхать": "to rest", "много": "a lot; much", "воды": "water (in 'a lot of water')",
    # unit17 work
    "врач": "doctor", "больнице": "hospital (prepositional case, 'at the hospital')",
    "больница": "hospital", "учитель": "teacher", "работает": "works (he or she)",
    "школа": "school", "школе": "school (prepositional case, 'at school')",
    "инженер": "engineer", "он": "he", "офис": "office",
    "офисе": "office (prepositional case, 'in the office')",
    "кем": "as whom; as what", "работаешь": "you work (informal)",
    "магазине": "store (prepositional case, 'in the store')", "повар": "cook; chef",
    "ресторане": "restaurant (prepositional case, 'in the restaurant')",
    # unit18 housing
    "квартира": "apartment", "кухня": "kitchen",
    "кухне": "kitchen (prepositional case, 'in the kitchen')", "спальня": "bedroom",
    "кровать": "bed", "спальне": "bedroom (prepositional case, 'in the bedroom')",
    "диван": "sofa", "гостиной": "living room (prepositional case, 'in the living room')",
    "гостиная": "living room", "ванная": "bathroom", "живёшь": "you live (informal)",
    "живу": "I live", "квартире": "apartment (prepositional case, 'in the apartment')",
    "комнат": "rooms, as used after five and up", "две": "two (fem.)",
    "комнаты": "rooms, as used after two to four",
    # unit19 travel
    "билет": "ticket", "Тулы": "Tula (a city)",
    "платформа": "platform", "платформы": "platform, as 'of the platform'",
    # unit20 weather
    "холодно": "cold (weather)", "тепло": "warm (weather)", "погода": "weather",
    "идёт": "goes; it is (raining)", "дождь": "rain", "солнце": "sun",
    "ветер": "wind", "какая": "which; what kind of (fem.)", "тогда": "then; in that case",
    "останемся": "we will stay",
    # unit21 clothing
    "нужна": "needed (fem. thing)", "куртка": "jacket", "рубашка": "shirt",
    "платье": "dress", "размер": "size", "средний": "medium (masc.)",
    "синяя": "blue (fem.)",
    # unit22 emotions
    "рад": "glad (said by a man)", "рада": "glad (said by a woman)",
    "грустно": "sad", "устал": "tired (said by a man)",
    "устала": "tired (said by a woman)", "потому": "for that reason (as in 'because')",
    "работы": "work (in 'a lot of work')", "себя": "oneself; yourself",
    "чувствуешь": "you feel (informal)", "выходной": "day off",
    # unit23 communication
    "алло": "hello (on the phone)", "говори": "speak (informal command)",
    "медленно": "slowly", "повтори": "repeat (informal command)",
    "напиши": "write; text (informal command)", "сообщение": "message",
    # unit24 money
    "картой": "card (instrumental case, 'by card')", "карта": "card",
    "наличными": "in cash", "рубли": "rubles (several)", "нужны": "needed (plural things)",
    "чек": "receipt", "нужен": "needed (masc. thing)", "триста": "three hundred",
    "только": "only",
}

POS_SETS = {
    "symbol": split_words("з д р т е ъ ь й"),
    "proper_noun": PROPER_NOUNS,
    "pronoun": split_words(
        "тебя вас меня вы ты я мы он она мне вам тебе её кто что кем это этот эта "
        "тот то мой моя моей вашей себя себе который котором какой какое какая"
    ),
    "preposition": split_words("в с у до на из во за к"),
    "particle": split_words(
        "а и ну да не только тоже так вот чем потому"
    ),
    "adjective": split_words(
        "доброе добрый приятно первое третье пятое десятое свободен сладкое "
        "большое согласен хороший средний синяя рад рада устал устала нужна "
        "нужен нужны нужно холодно тепло грустно плохо понятно можно"
    ),
    "adverb": split_words(
        "как хорошо очень сегодня сейчас завтра вчера дома утром днём вечером "
        "ночью где откуда когда прямо направо налево потом далеко отсюда "
        "просто пешком много ещё медленно тогда лучше хуже больше меньше "
        "наличными сколько отлично"
    ),
    "verb": split_words(
        "поживаете зовут перейдём познакомимся стоит стоят скажите отходит есть "
        "садитесь будете заказывать хочу принесите пить дайте находится дойти "
        "идите поверните простите встаю встаёте завтракаю работаю ужинаю ложусь "
        "спать делаете работаете давайте давай пойдём могу встретимся был была "
        "ходил ходила смотрел смотрела делал отдыхала нравится болит отдыхать "
        "работает работаешь живёшь живу идёт останемся чувствуешь говори "
        "повтори напиши"
    ) | {"не хочу"},
    "phrase": split_words("здравствуйте привет спасибо пожалуйста алло пока"),
}
POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())

CATEGORY_TAGS: dict[str, list[str]] = {}
for _tag, _words in {
    "ru_number": "один два три четыре пять шесть семь восемь девять десять "
                 "одиннадцать сто двести триста две",
    "ru_weekday": "понедельник вторник среда четверг пятница суббота воскресенье",
    "ru_month": "января апреля октября",
    "ru_family": "мать отец брат сестра бабушка дедушка муж жена сын дочь дети семья",
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
