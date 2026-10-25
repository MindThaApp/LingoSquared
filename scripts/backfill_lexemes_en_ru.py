#!/usr/bin/env python3
"""Idempotently backfill en-ru (Russian target) lexemes for the "Russian A1"
course, so en-ru practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24. All plumbing lives in
scripts/_target_lexeme_backfill_common.py (see its docstring for the tag
scheme); this file is data only: one hand-written English gloss and one part
of speech per citation form.

Scope: A1 (the "en-ru-a1" manifest group, units 01-24), A2 (the
"en-ru-a2" group, units 25-34; session 11) and B1 (the "en-ru-b1" group, units
35-53; session 12). B2+ is not classified yet; extend LEVELS and the tables
below together. The B1 course is separate again, so B1 re-glosses every token it
introduces (already-glossed A1/A2 tokens reuse their gloss; GLOSS_OVERRIDES
keys a different B1 sense by (realization stem, token)). A run before the B1
course is imported errors cleanly ("... course must be imported first"). A1 and A2 are separate courses, so A2
re-glosses every token it introduces, function words included; where A2 teaches
a different sense of an A1 token (банка, дня, за, работы) GLOSS_OVERRIDES keys the
A2 gloss by (realization stem, token).

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
LEVELS = {"a1": "en-ru-a1", "a2": "en-ru-a2", "b1": "en-ru-b1"}

PROPER_NOUNS = {
    "Анна", "Максим", "Виктор", "Канады", "Канада", "Москвы", "Москва",
    "Ирина", "Петровна", "Джон", "Ольга", "Тверской", "Чайковского",
    "Пушкина", "Олег", "Мария", "Настя", "Дима", "Тулы",
    "Настю", "Насти", "Диме",
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

# A2 (session 11): units 25-34, glosses for the tokens A1 did not teach.
GLOSSES.update({
    # unit25 registration
    "регистрация": "registration",
    "регистрацию": "registration (accusative case, as in 'for registration')",
    "зарегистрироваться": "to register (oneself)", "адрес": "address",
    "копия": "copy", "паспорт": "passport",
    "паспорта": "passport (genitive case, 'of the passport')",
    "заявление": "application form; written request", "договор": "contract",
    "аренды": "rent (genitive case, as in 'rental contract')",
    "по": "by; at (an address); on (as in 'on Tuesdays'); according to",
    "новому": "new (dative case, masc., after the word for 'at an address')",
    "адресу": "address (dative case, as in 'at the address')",
    "новый": "new (masc.)", "приходите": "come (formal command)",
    "десяти": "ten (dative case, as in 'by ten o'clock')",
    # unit26 opinions
    "моему": "my (dative case, in the phrase for 'in my opinion')",
    "удобно": "convenient; comfortable", "думаю": "I think",
    "важно": "important", "потому что": "because", "быстро": "quickly; fast",
    "согласна": "agreed (said by a woman)",
    "согласны": "agreed (said by several people)", "трудно": "difficult; hard",
    "понимаю": "I understand", "мнение": "opinion", "для": "for",
    "думаешь": "you think (informal)", "работать": "to work",
    "ехать": "to go (by vehicle); to travel", "вместе": "together",
    "людьми": "people (instrumental case, as in 'with people')",
    "спокойнее": "calmer; more peaceful", "но": "but",
    # unit27 bank
    "открыть": "to open", "счёт": "bank account",
    "банке": "bank (prepositional case, 'in the bank')",
    "сотрудник": "employee; staff member", "номер": "number",
    "телефона": "phone (genitive case, as in 'phone number')",
    "обслуживание": "service; upkeep", "карты": "card (genitive case, 'of the card')",
    "бесплатное": "free of charge (neuter)",
    "бесплатной": "free of charge (fem., after 'will be')",
    "будет": "will be (he, she or it)", "конечно": "of course",
    # unit28 doctor
    "беспокоит": "bothers; troubles", "сильно": "strongly; badly",
    "уже": "already; by now", "принимайте": "take (formal command, of medicine)",
    "лекарство": "medicine", "раза": "times, as used after two to four",
    "отдыхайте": "rest (formal command)", "снова": "again",
    "пятницу": "Friday (accusative case, as in 'on Friday')",
    "идти": "to go (on foot)", "работу": "work (accusative case, 'to work')",
    "записаться": "to make an appointment; to sign up",
    "врачу": "doctor (dative case, as in 'to the doctor')",
    "прийти": "to come (arrive on foot)",
    # unit29 repairs
    "проблема": "problem", "отопление": "heating", "течёт": "leaks; flows",
    "кран": "tap; faucet", "мастер": "repairman; tradesman",
    "придёт": "will come (he or she)",
    "одной": "one (fem., prepositional case, 'in one room')",
    "комнате": "room (prepositional case, 'in the room')", "или": "or",
    "всей": "whole; all (fem., prepositional case)",
    # unit30 interview
    "собеседование": "job interview", "опыт": "experience",
    "опыте": "experience (prepositional case, as in 'about experience')",
    "расскажите": "tell about; recount (formal command)", "о": "about; of",
    "вашем": "your (formal, prepositional case, masc. or neuter)",
    "можете": "you can (formal)", "начать": "to begin", "график": "schedule",
    "должность": "position; job title",
    "должности": "position (prepositional case, 'in this position')",
    "этой": "this (fem., prepositional case)", "работала": "worked (fem.)",
    "детьми": "children (instrumental case, as in 'with children')",
    # unit31 delay
    "задержка": "delay", "задерживается": "is delayed", "двадцать": "twenty",
    "отмена": "cancellation", "рейс": "flight; scheduled trip",
    "рейса": "flight (genitive case, 'of the flight')",
    "пересадка": "connection; transfer",
    "пересадку": "connection; transfer (accusative case, 'for the connection')",
    "успею": "I will make it in time", "другой": "other; another (masc.)",
    "третьей": "third (fem., genitive case, 'from the third platform')",
    "через": "in (a length of time); after",
    # unit32 online life
    "интернет": "internet",
    "интернетом": "internet (instrumental case, as in 'use the internet')",
    "онлайн": "online", "каждый": "every; each (masc.)", "пользуюсь": "I use",
    "пользуешься": "you use (informal)", "часто": "often", "редко": "rarely",
    "телефон": "phone", "телефоном": "phone (instrumental case, 'with the phone')",
    "новости": "news", "читаю": "I read", "читать": "to read", "видео": "video",
    "смотрю": "I watch", "смотреть": "to watch", "полезно": "useful",
    "иногда": "sometimes", "занимает": "takes (time)",
    "времени": "time (genitive case, as in 'a lot of time')",
    "стараюсь": "I try", "сидеть": "to sit; to stay",
    # unit33 week
    "неделя": "week", "обычная": "usual; ordinary (fem.)", "обычно": "usually",
    "проходит": "passes; goes by (of time)", "твоя": "your (informal, fem.)",
    "будни": "weekdays", "выходные": "weekend; days off", "отдыхаю": "I rest",
    "вторникам": "Tuesdays (dative plural, as in 'on Tuesdays')",
    "после": "after", "хожу": "I go (regularly, on foot)",
    "курсы": "courses; classes", "встречаюсь": "I meet up (with someone)",
    "друзьями": "friends (instrumental case, as in 'with friends')",
    # unit34 complaint
    "купила": "bought (said by a woman)", "эту": "this (fem., accusative case)",
    "рубашку": "shirt (accusative case, as an object)",
    "мала": "too small (fem.)", "обменять": "to exchange",
})

# A2 senses that differ from the A1 gloss of the same token.
GLOSS_OVERRIDES: dict[tuple[str, str], str] = {
    ("a2_unit27_bank", "банка"): "bank (genitive case, as in 'employee of the bank')",
    ("a2_unit28_u_vracha", "дня"): "days, as used after two to four",
    ("a2_unit30_sobesedovanie", "за"): "for (as in 'thank you for')",
    ("a2_unit30_sobesedovanie", "работы"): "work (genitive case, as in 'work experience')",
}

# ---- B1 (units 35-53), session 12 -------------------------------------------
GLOSSES.update({
    # unit35 abilities
    "сказать": "to say", "документ": "document", "готов": "ready (masc.)",
    "раньше": "before; earlier", "мог": "could; was able to (masc.)",
    "объяснить": "to explain", "могли": "could (plural or formal)",
    "если": "if", "бы": "would (a word that makes a statement hypothetical)",
    "было": "was; there was (neuter)", "время": "time",
    "проверить": "to check", "правильный": "correct; right (masc.)",
    # unit36 duties
    "должен": "must; obliged to (masc.)", "отправить": "to send",
    "форму": "form (accusative case, as an object)", "сделать": "to do; to make",
    "нельзя": "it is not allowed; must not", "опаздывать": "to be late",
    "успел": "managed to; had time to (masc.)",
    # unit37 hypotheses
    "отправь": "send (informal command)", "проверю": "I will check",
    "отправлю": "I will send", "сделаешь": "you will do (informal)",
    "проверил": "checked (masc.; with 'would', 'would check')",
    "попросил": "asked; requested (masc.; with 'would', 'would ask')",
    "Настю": "Nastya (accusative case, as in 'ask Nastya')",
    # unit38 debates
    "тем": "that (instrumental case, as in 'agree with the idea that')",
    "там": "there", "тихо": "quiet; quietly", "думает": "thinks (he or she)",
    "лишняя": "unnecessary; superfluous (fem.)", "нам": "to us; for us",
    "обсудить": "to discuss", "план": "plan", "важен": "important (masc.)",
    "проект": "project", "срочный": "urgent (masc.)",
    # unit39 work
    "отвечаю": "I am responsible; I answer", "отчёт": "report",
    "проверяю": "I check", "данные": "data",
    "отвечаете": "you are responsible; you answer (formal)",
    "работе": "work (prepositional case, as in 'in progress')",
    "жду": "I wait; I am waiting", "от": "from (a person or source)",
    "коллег": "colleagues (genitive plural, as in 'from colleagues')",
    "коллега": "colleague", "неделе": "week (prepositional case, 'this week')",
    "помогите": "help (formal command)", "таблицу": "spreadsheet; table (accusative case)",
    "посмотрю": "I will look", "обеда": "lunch (genitive case, 'after lunch')",
    # unit40 story
    "читал": "was reading; read (masc.)", "письмо": "letter; email",
    "позвонил": "called; phoned (masc., completed once)", "процесс": "process",
    "прошлом": "past (prepositional case, 'in the past')",
    "одно": "one (neuter)", "законченное": "completed; finished (neuter)",
    "событие": "event", "сначала": "at first; first", "сказал": "said (masc.)",
    "началась": "began; started (fem. past, as in 'the meeting had started')",
    "случилось": "happened", "этого": "this (genitive case, as in 'after that')",
    "открыл": "opened (masc.)", "ссылку": "link (accusative case)",
    # unit41 conditions
    "хорошая": "good (fem.)", "парк": "park",
    "хорошей": "good (fem., after a negated 'will be')",
    "будешь": "you will be (informal)", "делать": "to do",
    "Насти": "Nastya (genitive case, as in 'Nastya has')",
    "поможет": "will help (he or she)", "Диме": "Dima (dative case, 'help Dima')",
    "позвоню": "I will call", "позже": "later",
    # unit42 routine
    "прихожу": "I come; I arrive", "домой": "home (as in 'come home')",
    "готовлю": "I cook; I prepare", "ужин": "dinner", "делаешь": "you do (informal)",
    "пришёл": "came; arrived (masc.)", "зазвонил": "rang; started to ring (masc.)",
    "раз": "time (as in 'one time')",
    # unit43 reported speech
    "без": "without", "изменения": "change (genitive case, 'without change')",
    "спросила": "asked (fem.)", "ли": "whether (question word after a verb)",
    "делает": "does; is doing (he or she)",
    "глагола": "verb (genitive case, 'after the verb')",
    # unit44 purpose
    "учится": "studies; learns (he or she)",
    "вечерам": "evenings (dative plural, 'in the evenings')",
    "чтобы": "in order to; so that", "получить": "to get; to receive",
    "повышение": "promotion", "инфинитив": "infinitive", "субъект": "subject (of a sentence)",
    "зачем": "why; what for", "учишься": "you study (informal)",
    "откладывает": "puts aside; saves (he or she)", "деньги": "money",
    "купить": "to buy", "машину": "car (accusative case)",
    "прошедшее": "past (the past tense)", "разные": "different; various",
    "откладываешь": "you save (informal)", "учусь": "I study",
    "откладываю": "I save",
    # unit45 advice
    "сплю": "I sleep", "ночам": "nights (dative plural, 'at night')",
    "совет": "advice", "твоём": "your (informal, prepositional case, masc.)",
    "месте": "place (prepositional case, 'in your place')",
    "пил": "drank (masc.; with 'would', 'would drink')",
    "сделал": "did (masc.; with 'would', 'would do')",
    "моём": "my (prepositional case, masc.)", "попробую": "I will try",
    # unit46 complaint
    "пожаловаться": "to complain", "приходил": "came (more than once; masc. past)",
    "всё": "all; still (as in 'still leaking')", "решена": "solved; resolved (fem.)",
    "прислали": "sent (plural past, 'you sent')",
    "другого": "another; different (masc., accusative case)",
    "вежливая": "polite (fem.)", "просьба": "request",
    "мастера": "repairman (genitive or accusative case, 'a different repairman')",
    "пришлите": "send (formal command)", "жаль": "pity; sorry",
    "хотите": "you want (formal)", "сделали": "did (plural past, 'we did')",
    # unit47 regrets
    "взял": "took (masc.)", "зонт": "umbrella", "теперь": "now",
    "весь": "all; whole; entirely (masc.)", "мокрый": "wet (masc.)",
    "надо": "necessary; must", "взять": "to take", "сожаление": "regret",
    "промок": "got soaked; got wet (masc.)",
    # unit48 plans
    "идём": "we are going", "нас": "us (after the word for 'at')",
    "билеты": "tickets", "настоящее": "present (neuter, 'present tense')",
    "точный": "exact; precise (masc.)", "собираюсь": "I am planning to",
    "бегать": "to run; to jog", "утрам": "mornings (dative plural, 'in the mornings')",
    "намерение": "intention", "может": "can; may (he, she or it)",
    "быть": "to be (also in the phrase for 'maybe')", "начнёшь": "you will start",
    "идея": "idea", "наверное": "probably", "права": "right; correct (fem.)",
    "побегаю": "I will go for a run", "вместо": "instead of",
    # unit49 unreal conditions
    "путешествовал": "traveled (masc.; with 'would', 'would travel')",
    "нереальное": "unreal (neuter)", "условие": "condition",
    "денег": "money (genitive case, 'more money')", "купил": "bought (masc.; with 'would', 'would buy')",
    "новую": "new (fem., accusative case)", "помочь": "to help",
    "этим": "this (instrumental case, 'with this')",
    "смягчённая": "softened (fem.)",
    "хотела": "wanted (fem.; with 'would', 'would like')",
    "чашку": "cup (accusative case)",
    "путешествовала": "traveled (fem.; with 'would', 'would travel')",
    "отчётом": "report (instrumental case, 'with the report')",
    "просил": "asked (masc.; 'I would not be asking')",
    # unit50 meetings
    "предложил": "suggested (masc.; with 'would', 'would suggest')",
    "перенести": "to move; to postpone", "встречу": "meeting (accusative case)",
    "порекомендовал": "recommended (masc.; with 'would', 'would recommend')",
    "формальное": "formal (neuter)", "смягчённое": "softened (neuter)",
    "предложение": "suggestion; sentence", "нет": "there is no; no",
    "всех": "all (genitive plural)", "данных": "data (genitive plural)",
    "отчёта": "report (genitive case, 'for the report')",
    "пятницы": "Friday (genitive case, 'by Friday')", "формальная": "formal (fem.)",
    "почему": "why", "среды": "Wednesday (genitive case, 'by Wednesday')",
    # unit51 descriptions
    "инженером": "engineer (instrumental case, 'as an engineer')",
    "которая": "who; which (fem.)",
    "учительницей": "teacher (fem., instrumental case, 'as a teacher')",
    "которое": "which (neuter)", "которые": "who; which (plural)",
    "относительное": "relative (neuter)", "местоимение": "pronoun",
    "согласуется": "agrees (with)", "роде": "gender (prepositional case, 'in gender')",
    "числе": "number (prepositional case, 'in number')",
    "которым": "whom; which (instrumental case, masc., 'with whom')",
    "над": "over; above (also 'on' in 'work on a project')",
    "проектом": "project (instrumental case, 'on the project')",
    "подруга": "friend (female)",
    "которой": "whom; which (fem., instrumental case, 'with whom')",
    "предлог": "preposition (a word like 'in' or 'with')",
    "творительном": "instrumental (prepositional case, masc.)",
    "падеже": "case (grammatical; prepositional case)",
    "новым": "new (instrumental case)", "познакомиться": "to meet; to get acquainted",
    "говорите": "you speak; you talk (formal)", "интересный": "interesting (masc.)",
    # unit52 retelling
    "короче": "shorter (also in the phrase for 'in short')",
    "говоря": "saying (as in the phrase for 'in short')",
    "поездка": "trip", "отличной": "excellent (fem., instrumental case)",
    "главное": "the main thing; main (neuter)", "все": "everyone; all",
    "были": "were", "довольны": "pleased; satisfied (plural)",
    "связки": "connectors (plural)", "главной": "main (fem., genitive case)",
    "мысли": "idea; thought (genitive case, 'of the main idea')",
    "во-первых": "firstly; first of all", "гуляли": "walked; strolled (plural past)",
    "лесу": "forest (prepositional case, 'in the forest')",
    "во-вторых": "secondly", "готовили": "cooked; prepared (plural past)",
    "итоге": "result (prepositional case, 'in the end')",
    "прекрасными": "wonderful (plural, instrumental case)", "порядок": "order",
    "пересказа": "retelling (genitive case, 'of a retelling')",
    "поехали": "went (by vehicle; plural past)", "дачу": "dacha; country house (accusative case)",
    "солнечно": "sunny", "правда": "truth (also 'right?' as a tag question)",
    "именно": "exactly; precisely",
    # unit53 concessions
    "хотя": "although", "работа": "work", "удобна": "convenient (fem.)",
    "хватает": "is enough (as in 'I miss', literally 'is not enough for me')",
    "общения": "communication; contact (genitive case)",
    "коллегами": "colleagues (instrumental case, 'with colleagues')",
    "связка": "connector (a linking word)",
    "придаточное": "subordinate (neuter, 'subordinate clause')",
    "уступительная": "concessive (fem.)", "менее": "less", "более": "more",
    "сильная": "stronger; strong (fem.)", "контраста": "contrast (genitive case)",
    "экономишь": "you save (informal)", "действительно": "really; indeed",
    "легче": "easier", "сосредоточиться": "to concentrate",
})

# B1 senses that differ from the A1/A2 gloss of the same token.
GLOSS_OVERRIDES.update({
    ("b1_unit37_gipotezy", "времени"): "time (genitive case, as in 'there was no time')",
    ("b1_unit37_gipotezy", "тебя"): "you (informal), object form (as in 'ask you')",
    ("b1_unit38_debaty", "согласен"): "in agreement; I agree (said by a man)",
    ("b1_unit38_debaty", "согласна"): "in agreement; I agree (said by a woman)",
    ("b1_unit39_rabota", "за"): "for (as in 'responsible for')",
    ("b1_unit43_kosvennaja_rech", "стоит"): "stands; is placed (also 'it is worth', as in advice: 'you should')",
    ("b1_unit44_celi", "по"): "in; on (as in 'in the evenings'); by; according to",
    ("b1_unit45_sovety", "можно"): "possible; allowed (as in 'what else can be done')",
    ("b1_unit51_opisanija", "который"): "who; which; that (relative pronoun, masc.)",
    ("b1_unit51_opisanija", "котором"): "which (prepositional case, 'about which')",
})

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
for _pos, _words in {
    "pronoun": "моему вашем этой твоя эту",
    "preposition": "по для о через после",
    "particle": "но или",
    "adjective": (
        "новому новый удобно важно согласна согласны трудно спокойнее "
        "бесплатное бесплатной одной всей другой третьей каждый обычная "
        "полезно мала"
    ),
    "adverb": (
        "быстро сильно уже снова вместе конечно часто редко иногда обычно "
        "онлайн"
    ),
    "verb": (
        "зарегистрироваться приходите думаю понимаю думаешь работать ехать "
        "открыть будет принимайте отдыхайте идти записаться прийти "
        "беспокоит течёт придёт расскажите можете начать задерживается "
        "успею пользуюсь пользуешься читаю читать смотрю смотреть занимает "
        "стараюсь сидеть проходит отдыхаю хожу встречаюсь купила обменять "
        "работала"
    ),
}.items():
    POS_SETS[_pos] = set(POS_SETS.get(_pos, ())) | split_words(_words)

for _pos, _words in {
    "proper_noun": "Настю Насти Диме",
    "pronoun": (
        "тем нам нас все всех этого этим твоём моём всё весь которая которое "
        "которые которым которой"
    ),
    "preposition": "без от над вместо",
    "particle": "если бы ли чтобы хотя нет",
    "adjective": (
        "готов правильный должен лишняя важен срочный хорошая хорошей вежливая "
        "мокрый точный новую новым другого разные формальное смягчённое "
        "смягчённая формальная нереальное законченное одно решена настоящее "
        "прошедшее главное главной интересный отличной довольны прекрасными "
        "удобна сильная уступительная относительное придаточное творительном "
        "права надо жаль"
    ),
    "adverb": (
        "раньше сначала теперь позже домой там наверное именно действительно "
        "легче короче менее более почему зачем тихо солнечно нельзя говоря"
    ),
    "verb": (
        "сказать мог объяснить могли было проверить отправить сделать "
        "опаздывать успел отправь проверю отправлю сделаешь проверил попросил "
        "думает обсудить отвечаю проверяю отвечаете жду помогите посмотрю "
        "читал позвонил сказал началась случилось открыл будешь делать поможет "
        "позвоню прихожу готовлю делаешь пришёл зазвонил спросила делает "
        "учится получить откладывает купить откладываешь учусь откладываю "
        "сплю пил сделал попробую пожаловаться приходил прислали пришлите "
        "хотите сделали взял взять промок идём собираюсь бегать начнёшь "
        "побегаю путешествовал купил помочь хотела путешествовала просил "
        "предложил перенести порекомендовал согласуется говорите познакомиться "
        "гуляли готовили поехали хватает сосредоточиться экономишь может быть "
        "были учишься"
    ),
}.items():
    POS_SETS[_pos] = set(POS_SETS.get(_pos, ())) | split_words(_words)
POS_SETS["particle"] = set(POS_SETS["particle"]) | {"потому что"}
POS_SETS["particle"] = set(POS_SETS["particle"]) | {"во-первых", "во-вторых"}
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
            gloss_overrides=GLOSS_OVERRIDES,
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
