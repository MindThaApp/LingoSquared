#!/usr/bin/env python3
"""Idempotently backfill en-fr (French target) lexemes for the "French A1"
course, so en-fr practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: en->X backfill, sibling of backfill_lexemes_en_es.py.
All plumbing lives in scripts/_target_lexeme_backfill_common.py (see its
docstring for the tag scheme); this file is data only: one hand-written
English gloss and one part of speech per citation form.

Scope: A1 only (the "en-fr" manifest group, units 01-14). A2+ is not
classified yet; extend LEVELS and the tables below together.

Glossing rules followed here (PRACTICE_PACK_RECIPE.md section 0.1, 6.6):
* the gloss is the sense the unit actually teaches at first sight,
* inflected forms say who they belong to ("you have (informal)"),
* gender pairs are glossed "(masc.)"/"(fem.)" so the two are never
  interchangeable answers,
* no gloss contains a French word.

Tokens are keyed exactly as the realizations spell them. The realizations
mix the typographic apostrophe (unit 01/02/03 items such as "c’est",
"j’habite") with the straight one (later items such as "c'est", "j'ai");
both spellings are separate introduced tokens and both are glossed. Elided
and hyphenated forms are single tokens ("l'eau", "qu'est-ce", "vas-tu").

Sentence-initial capitals fold to lowercase; the proper nouns below keep
their capital.

Run (after the en-fr course is imported), from backend/:

    docker compose run --rm -v "$(cd .. && pwd):/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api /repo/scripts/backfill_lexemes_en_fr.py

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

LANG = "fr"
LEVELS = {"a1": "en-fr"}

PROPER_NOUNS = {
    "Camille", "Noé", "Montreuil", "Lille", "Inès", "Mathieu", "Trois-Frères",
    "Saint-Ouen", "Lyon", "Paris",
}
_PROPER_BY_LOWER = {p.lower(): p for p in PROPER_NOUNS}


def normalize(token: str) -> str:
    lower = token.lower()
    return _PROPER_BY_LOWER.get(lower, lower)


GLOSSES: dict[str, str] = {
    # unit01 greetings
    "bonjour": "hello; good morning", "salut": "hi; bye (informal)",
    "au": "at the; to the (masc.)", "revoir": "to see again",
    "tu": "you (informal)", "vous": "you (formal or plural)",
    "comment": "how", "allez-vous": "do you go; are you doing (formal)",
    "vas-tu": "do you go; are you doing (informal)", "je": "I",
    "m’appelle": "I am called", "Camille": "Camille",
    "appelez-vous": "are you called (formal)",
    "t’appelles": "are you called (informal)", "moi": "me",
    "c’est": "it is; this is", "Noé": "Noé",
    "enchanté": "delighted; nice to meet you (said by a man)",
    "enchantée": "delighted; nice to meet you (said by a woman)",
    "et": "and", "toi": "you (informal, after a preposition or for emphasis)",
    "j’habite": "I live", "êtes": "you are (formal or plural)",
    "un": "a; an (masc.)", "atelier": "workshop", "ça": "that; it",
    "va": "goes; is going", "très": "very", "bien": "well; fine",
    "merci": "thank you", "pas": "not", "mal": "bad; badly",
    "suis": "I am", "peu": "little; a little", "fatigué": "tired (masc.)",
    "fatiguée": "tired (fem.)", "là": "here; there", "pour": "for",
    "l’atelier": "the workshop", "oui": "yes", "habitez": "you live (formal)",
    "dans": "in", "le": "the (masc.)", "quartier": "neighbourhood",
    "à": "at; in; to", "Montreuil": "Montreuil", "d’ici": "from here",
    "de": "of; from", "Lille": "Lille", "commence": "begins; starts",
    "tout": "all; very; completely", "l’heure": "the hour; the time",
    "Inès": "Inès", "cuisine": "cooking; kitchen", "Mathieu": "Mathieu",
    "rue": "street", "des": "of the (plural); some",
    "Trois-Frères": "Trois-Frères (street name)",
    "Saint-Ouen": "Saint-Ouen", "non": "no", "Lyon": "Lyon", "ah": "oh; ah",
    # unit02 numbers
    "zéro": "zero", "deux": "two", "trois": "three", "quatre": "four",
    "cinq": "five", "six": "six", "sept": "seven", "huit": "eight",
    "neuf": "nine", "dix": "ten", "onze": "eleven", "douze": "twelve",
    "treize": "thirteen", "quatorze": "fourteen", "quinze": "fifteen",
    "seize": "sixteen", "vingt": "twenty", "trente": "thirty",
    "trente-quatre": "thirty-four", "soixante": "sixty",
    "soixante-dix": "seventy", "quatre-vingts": "eighty",
    "quatre-vingt-dix": "ninety", "cent": "one hundred",
    "quel": "which; what (masc.)", "âge": "age", "as-tu": "do you have (informal)",
    "j'ai": "I have", "vingt-huit": "twenty-eight", "ans": "years",
    "avez-vous": "do you have (formal)", "ai": "I have", "est": "is",
    "ton": "your (informal, masc.)", "numéro": "number",
    "téléphone": "telephone; phone", "c'est": "it is; this is",
    "peux": "you can (informal)", "répéter": "to repeat", "il": "he; it",
    "te": "you; to you (informal)", "plaît": "pleases", "sûr": "sure",
    "besoin": "need", "œufs": "eggs", "combien": "how much; how many",
    "d'œufs": "of eggs", "tasses": "cups", "farine": "flour",
    "une": "a; an (fem.)", "demi-tasse": "half a cup", "sucre": "sugar",
    "sur": "on", "la": "the (fem.)", "table": "table", "recette": "recipe",
    "as": "you have (informal)", "aussi": "also; too",
    "environ": "about; approximately", "parfait": "perfect",
    "dis": "say; tell (informal command)", "comme": "like; as",
    "t’écris": "I write to you", "prochain": "next (masc.)",
    "cours": "class", "dernière": "last (fem.)", "question": "question",
    # unit03 family
    "mère": "mother", "père": "father", "frère": "brother", "sœur": "sister",
    "fils": "son", "fille": "daughter; girl", "parents": "parents",
    "frères": "brothers", "sœurs": "sisters", "ma": "my (fem.)",
    "mon": "my (masc.)", "mes": "my (plural)", "ta": "your (informal, fem.)",
    "famille": "family", "grande": "big; tall (fem.)", "petite": "small (fem.)",
    "grand-père": "grandfather", "grand-mère": "grandmother",
    "grands-parents": "grandparents", "oncle": "uncle", "tante": "aunt",
    "cousin": "cousin (male)", "cousine": "cousin (female)",
    "on": "we; one", "maison": "house; home", "beaucoup": "a lot; many",
    "cousins": "cousins", "habites": "you live (informal)", "près": "near",
    "tes": "your (informal, plural)", "avec": "with", "Paris": "Paris",
    "habitent": "they live", "s’appelle": "is called", "elle": "she; it",
    "habite": "lives", "ses": "his; her; its (plural)", "a": "has",
    "regarde": "look (informal command)", "voici": "here is; here are",
    "ce": "this; that (masc.)", "sont": "they are",
    "adorable": "adorable; lovely", "d’autres": "of others; other",
    "plus": "more", "mais": "but", "ils": "they (masc.)",
    "se": "himself; herself; themselves; each other", "parle": "speaks; talk",
    "chaque": "each; every", "semaine": "week", "comprends": "I understand",
    "ici": "here", "d’avoir": "of having", "sa": "his; her (fem. noun)",
    "soi": "oneself",
    # unit04 shopping
    "marché": "market", "boulangerie": "bakery", "les": "the (plural)",
    "légumes": "vegetables", "fruits": "fruits", "prix": "price",
    "cher": "expensive (masc.)", "chers": "expensive (masc. plural)",
    "aujourd'hui": "today", "kilo": "kilo", "voudrais": "I would like",
    "tomates": "tomatoes", "litre": "liter", "lait": "milk",
    "s'il": "if it (start of a polite request)", "euro": "euro",
    "euros": "euros", "coûte": "costs", "pain": "bread",
    "fait": "makes; does; comes to", "en": "in; of it",
    "autre": "other; else", "chose": "thing", "fromage": "cheese",
    "du": "some; of the (masc.)", "fermée": "closed (fem.)",
    "peut": "can; is able to", "acheter": "to buy", "frais": "fresh (masc.)",
    "attendez": "wait (formal command)", "cinquante": "fifty",
    "voilà": "here you are; there it is",
    # unit05 food
    "poulet": "chicken", "poisson": "fish", "salade": "salad", "riz": "rice",
    "l'eau": "the water", "vin": "wine", "dessert": "dessert",
    "l'addition": "the bill; the check", "avez": "you have (formal)",
    "choisi": "chosen; decided", "café": "coffee; café",
    "qu'est-ce": "what is it", "que": "that; what", "délicieux": "delicious",
    "boisson": "drink", "verre": "glass", "rouge": "red",
    "cette": "this (fem.)", "l'atelier": "the workshop",
    "nous": "we; us", "donné": "given", "faim": "hunger",
    "suite": "following; (in a set phrase) right away",
    # unit06 time
    "l'heure": "the hour; the time", "matin": "morning",
    "l'après-midi": "the afternoon", "soir": "evening", "midi": "noon",
    "minuit": "midnight", "quelle": "which; what (fem.)",
    "heure": "hour; o'clock", "heures": "hours; o'clock", "quart": "quarter",
    "demie": "half (fem.)", "moins": "less; minus",
    "prochaine": "next (fem.)", "dix-huit": "eighteen",
    "crois": "I think; I believe", "pratique": "practical; convenient",
    "après": "after", "travail": "work", "d'accord": "okay; agreed",
    "finit": "finishes; ends", "vers": "around; towards",
    "d'habitude": "usually", "alors": "so; then",
    # unit07 places
    "gare": "train station", "pharmacie": "pharmacy", "banque": "bank",
    "l'école": "the school", "poste": "post office", "où": "where",
    "face": "face; front", "côté": "side", "d'ici": "from here",
    "loin": "far", "n'est": "is not", "excusez-moi": "excuse me",
    "minutes": "minutes", "pied": "foot", "prie": "I ask; I beg",
    # unit08 dates
    "lundi": "Monday", "samedi": "Saturday", "lieu": "place",
    "dimanche": "Sunday", "demain": "tomorrow", "hier": "yesterday",
    "jour": "day", "sommes": "we are", "mars": "March", "date": "date",
    "premier": "first (masc.)", "termine": "ends", "vingt-deux": "twenty-two",
    "quand": "when", "séance": "session", "donc": "so; therefore",
    "temps": "time; weather", "préparer": "to prepare",
    "l'occasion": "the occasion", "bonne": "good (fem.)", "idée": "idea",
    "voit": "sees",
    # unit09 directions
    "gauche": "left", "droite": "right", "droit": "straight",
    "coin": "corner", "traverser": "to cross", "boutique": "shop",
    "carrefour": "intersection", "aller": "to go",
    "tournez": "turn (formal command)", "continuez": "continue (formal command)",
    "jusqu'au": "as far as the (masc.)", "connais": "you know (informal)",
    "ustensiles": "utensils", "y": "there (a place already mentioned)",
    "tournes": "you turn (informal)", "ensuite": "next; then",
    "continues": "you continue (informal)", "traverses": "you cross (informal)",
    "exactement": "exactly", "juste": "just; right",
    # unit10 routines
    "réveiller": "to wake up", "me": "me; myself",
    "réveille": "wake up; wakes up", "lever": "to get up",
    "lève": "get up; gets up", "prendre": "to take; to have (a meal)",
    "douche": "shower", "s'habiller": "to get dressed",
    "m'habille": "I get dressed", "avant": "before",
    "petit-déjeuner": "breakfast", "prends": "I take; you take (informal)",
    "quitter": "to leave", "quitte": "leave; leaves", "d'abord": "first; at first",
    "rentrer": "to go home; to return", "rentre": "go home; goes home",
    "dîner": "to have dinner; dinner", "dîne": "have dinner; has dinner",
    "dînons": "we have dinner", "ensemble": "together",
    "coucher": "to go to bed", "couche": "go to bed; goes to bed",
    "vingt-trois": "twenty-three", "week-end": "weekend", "tard": "late",
    "puis": "then", "vais": "I go; I am going", "fais": "I do; you do (informal)",
    "quoi": "what", "rentres": "you go home (informal)",
    "repose": "rest; rests",
    # unit11 plans
    "libre": "free", "es": "you are (informal)", "occupé": "busy (masc.)",
    "vendredi": "Friday", "retrouver": "to meet up with",
    "retrouve": "meet; meets up with", "passe": "come by; pass by",
    "dit": "says; tells", "faire": "to do; to make",
    "courses": "shopping; errands", "viens": "I come; you come (informal)",
    "chercher": "to look for; to fetch", "ne": "not (first half of a negation)",
    "plaisir": "pleasure", "devant": "in front of",
    # unit12 past events
    "préparé": "prepared; made", "gâteau": "cake", "acheté": "bought",
    "oublié": "forgot; forgotten", "beurre": "butter", "aimé": "liked",
    "goûté": "tasted", "sauce": "sauce", "avoir": "to have",
    "participe": "participle", "passé": "past", "arrivé": "arrived (masc.)",
    "arrivée": "arrived (fem.)", "retard": "delay; lateness",
    "allé": "gone (masc.)", "allée": "gone (fem.)", "resté": "stayed",
    "nettoyer": "to clean", "être": "to be", "accord": "agreement",
    "sujet": "subject", "bus": "bus", "finalement": "finally; in the end",
    "était": "was", "qui": "who; which; that",
    "s'est": "himself/herself/itself is (reflexive past helper)",
    "dernier": "last (masc.)", "n'ai": "I have not", "pu": "been able to",
    "venir": "to come", "oh": "oh", "rapidement": "quickly",
    "l'épicerie": "the grocery store", "trouvé": "found", "là-bas": "over there",
    # unit13 preferences
    "préférer": "to prefer", "préfère": "prefer; prefers", "tarte": "tart; pie",
    "chocolat": "chocolate", "aimer": "to like; to love",
    "j'aime": "I like", "mieux": "better", "plats": "dishes",
    "salés": "savoury (masc. plural)", "sucrés": "sweet (masc. plural)",
    "détester": "to hate", "déteste": "hate; hates", "épices": "spices",
    "trop": "too much; too", "fortes": "strong (fem. plural)",
    "plutôt": "rather", "sucré": "sweet (masc.)", "salé": "savoury (masc.)",
    "facile": "easy", "préfères": "you prefer (informal)", "quiche": "quiche",
    "aimes": "you like (informal)", "ou": "or", "dérange": "bothers; disturbs",
    "pourrait": "could; might", "qu'on": "that we; that one",
    "prépare": "prepare; prepares", "sucrée": "sweet (fem.)",
    "salée": "savoury (fem.)",
    # unit14 comparisons
    "l'autre": "the other", "difficile": "difficult",
    "meilleur": "better (masc.)", "bon": "good (masc.)",
    "chère": "expensive (fem.)", "adjectif": "adjective",
    "irrégulier": "irregular", "comparons": "we compare",
    "d'acheter": "of buying", "sortes": "kinds; sorts",
    "lequel": "which one (masc.)", "prend": "takes",
    "celui-ci": "this one (masc.)", "l'air": "the air; the look",
    "trouve": "find; finds; think", "vrai": "true",
    "celui-là": "that one (masc.)", "meilleure": "better (fem.)",
    "option": "option", "reste": "stays; remains; is left",
    "d'argent": "of money",
}

POS_SETS = {
    "proper_noun": PROPER_NOUNS,
    "pronoun": split_words(
        "tu vous je moi toi ça il elle ils on nous te me se y quoi qui "
        "lequel celui-ci celui-là soi ce qu'est-ce qu'on s'il"
    ),
    "preposition": split_words(
        "au pour dans à de sur avec près des du en vers après avant devant "
        "jusqu'au face côté d'ici d'autres d'avoir d'œufs d'acheter d'argent "
        "d'habitude d'abord d'accord"
    ),
    "particle": split_words(
        "un une le la les et mais ou que ne pas n'est n'ai s'est qu'est-ce"
    ),
    "adjective": split_words(
        "fatigué fatiguée grande petite cher chers fermée frais délicieux "
        "rouge cette prochain prochaine dernière dernier pratique parfait "
        "premier bonne droit libre occupé arrivé arrivée allé allée sucré "
        "salé sucrée salée salés sucrés fortes facile difficile meilleur "
        "meilleure bon chère irrégulier vrai adorable sûr quel quelle "
        "ton ta tes ma mon mes sa ses autre l'autre enchanté enchantée "
        "chaque demie"
    ),
    "adverb": split_words(
        "comment très bien peu mal là tout ici beaucoup aussi environ comme "
        "aujourd'hui loin demain hier donc alors ensuite exactement juste "
        "ensemble tard puis plutôt trop mieux finalement rapidement là-bas "
        "plus moins quand où tard"
    ),
    "verb": split_words(
        "revoir allez-vous vas-tu m’appelle appelez-vous t’appelles j’habite "
        "êtes va suis habitez commence as-tu j'ai avez-vous ai est peux "
        "répéter plaît as dis t’écris sont habites habitent s’appelle habite "
        "a regarde parle comprends fait voudrais coûte peut acheter attendez "
        "avez choisi donné crois finit prie termine sommes préparer voit "
        "traverser aller tournez continuez connais tournes continues traverses "
        "réveiller réveille lever lève prendre s'habiller m'habille prends "
        "quitter quitte rentrer rentre dîner dîne dînons coucher couche vais "
        "fais rentres repose es retrouver retrouve passe dit faire viens "
        "chercher préparé acheté oublié aimé goûté avoir resté nettoyer être "
        "était pu venir trouvé préférer préfère aimer j'aime détester déteste "
        "préfères aimes dérange pourrait prépare comparons prend trouve reste "
        "voici sûr"
    ),
    "phrase": split_words(
        "bonjour salut merci oui non ah oh excusez-moi voilà d'accord "
        "attendez"
    ),
}
# Items that sit in exactly one set: remove the helper overlaps declared above.
for _w in ("sûr", "attendez", "d'accord", "tard", "voici", "qu'est-ce",
           "d'habitude", "d'abord", "d'ici", "face", "côté", "autre",
           "l'autre"):
    for _pos, _set in POS_SETS.items():
        _set.discard(_w)
POS_SETS["adjective"] |= {"sûr", "autre", "l'autre"}
POS_SETS["adverb"] |= {"tard", "d'habitude", "d'abord", "d'ici"}
POS_SETS["preposition"] |= {"face", "côté"}
POS_SETS["phrase"] |= {"attendez", "d'accord", "voici", "qu'est-ce"}
_D_FORMS = {"d’autres", "d’avoir", "d’ici", "d'œufs", "d'acheter", "d'argent"}
for _set in POS_SETS.values():
    _set -= _D_FORMS
POS_SETS["phrase"] |= _D_FORMS | {"c'est", "c’est"}
POS_SETS["adverb"] |= {"combien"}
POS_SETS["noun"] = set(GLOSSES) - set().union(*POS_SETS.values())

CATEGORY_TAGS: dict[str, list[str]] = {}
for _tag, _words in {
    "fr_number": "zéro deux trois quatre cinq six sept huit neuf dix onze douze "
                 "treize quatorze quinze seize vingt trente trente-quatre "
                 "soixante soixante-dix quatre-vingts quatre-vingt-dix cent "
                 "vingt-huit vingt-deux vingt-trois dix-huit cinquante",
    "fr_weekday": "lundi vendredi samedi dimanche",
    "fr_month": "mars",
    "fr_family": "mère père frère sœur fils fille parents frères sœurs "
                 "grand-père grand-mère grands-parents oncle tante cousin "
                 "cousine cousins famille",
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
