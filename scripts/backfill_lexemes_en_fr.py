#!/usr/bin/env python3
"""Idempotently backfill en-fr (French target) lexemes for the "French A1"
course, so en-fr practice packs and unit checkpoints have per-unit lexeme
pools (`generate_checkpoint()` needs BOTH practice templates and lexemes on a
unit's own lessons).

Session 10, 2026-10-24: en->X backfill, sibling of backfill_lexemes_en_es.py.
All plumbing lives in scripts/_target_lexeme_backfill_common.py (see its
docstring for the tag scheme); this file is data only: one hand-written
English gloss and one part of speech per citation form.

Scope: A1 (the "en-fr" group, units 01-14) and A2 (the "en-fr-a2" group, units
15-24; table A2_ENTRIES, session 11) and B1 (the "en-fr-b1" group, units
25-43; table B1_ENTRIES plus B1_REGLOSS, session 12). B1 is its own course, so
every B1 token is classified for it afresh; tokens A1/A2 already glossed reuse
that gloss unless B1_REGLOSS says the B1 unit teaches another sense. B2+ is not
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
LEVELS = {"a1": "en-fr", "a2": "en-fr-a2", "b1": "en-fr-b1"}

PROPER_NOUNS = {
    "Camille", "Noé", "Montreuil", "Lille", "Inès", "Mathieu", "Trois-Frères",
    "Saint-Ouen", "Lyon", "Paris", "Fleurs", "Fournier", "Lambert",
    "République", "Vitale", "Girard", "Lefebvre", "Dijon",
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
    "comment": "how", "allez-vous": "are you doing (formal)",
    "vas-tu": "are you doing (informal)", "je": "I",
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
    "se": "himself; herself; themselves; each other", "parle": "speaks; talks",
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
    "face": "opposite; facing", "côté": "side; next to", "d'ici": "from here",
    "loin": "far", "n'est": "is not", "excusez-moi": "excuse me",
    "minutes": "minutes", "pied": "foot", "prie": "I beg; (in a set phrase) you are welcome",
    # unit08 dates
    "lundi": "Monday", "samedi": "Saturday", "lieu": "place",
    "dimanche": "Sunday", "demain": "tomorrow", "hier": "yesterday",
    "jour": "day", "sommes": "we are", "mars": "March", "date": "calendar date",
    "premier": "first (masc.)", "termine": "ends", "vingt-deux": "twenty-two",
    "quand": "when", "séance": "session", "donc": "so; therefore",
    "temps": "time (to do something)", "préparer": "to prepare",
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
    "s'est": "has (helper of a reflexive verb in the past)",
    "dernier": "last (masc.)", "n'ai": "I have not", "pu": "been able to",
    "venir": "to come", "oh": "oh", "rapidement": "quickly",
    "l'épicerie": "the grocery store", "trouvé": "found", "là-bas": "over there",
    # unit13 preferences
    "préférer": "to prefer", "préfère": "prefer; prefers", "tarte": "tart; pie",
    "chocolat": "chocolate", "aimer": "to like; to love",
    "j'aime": "I like", "mieux": "better (adverb)", "plats": "dishes",
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
    "celui-ci": "this one (masc.)", "l'air": "the look; the appearance",
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
# --- A2 additions (session 11): "French A2" course, units 15-24 ---------------
# One entry per A2 first-sight token: (part of speech, hand-written gloss).
# Codes: n noun, v verb, a adjective, d adverb, p preposition, c conjunction/
# particle, r pronoun, h phrase, N proper noun, s symbol.
_POS_CODE = {
    "n": "noun", "v": "verb", "a": "adjective", "d": "adverb",
    "p": "preposition", "c": "particle", "r": "pronoun", "h": "phrase",
    "N": "proper_noun", "s": "symbol",
}
A2_ENTRIES: dict[str, tuple[str, str]] = {
    # unit15 administrative procedures
    "mairie": ("n", "town hall"), "dois": ("v", "I must; you must (informal)"),
    "changement": ("n", "change"), "d'adresse": ("h", "of address"),
    "signaler": ("v", "to report; to notify"), "pièce": ("n", "document; piece"),
    "d'identité": ("h", "of identity"), "devez": ("v", "you must (formal or plural)"),
    "présenter": ("v", "to present; to show"), "valide": ("a", "valid"),
    "justificatif": ("n", "supporting document; proof"),
    "domicile": ("n", "home address; residence"), "récent": ("a", "recent (masc.)"),
    "obligatoire": ("a", "compulsory"), "rendez-vous": ("n", "appointment"),
    "j'aimerais": ("v", "I would like"), "remplir": ("v", "to fill in; to fill out"),
    "formulaire": ("n", "form (to fill in)"), "partir": ("v", "to leave"),
    "l'agent": ("n", "the officer; the clerk"),
    "d'accueil": ("h", "of welcome; front-desk (after a noun)"),
    "explique": ("v", "explains; explain"),
    "démarche": ("n", "procedure; step to take"), "suivre": ("v", "to follow"),
    "délai": ("n", "time limit; deadline"), "jours": ("n", "days"),
    "registre": ("n", "register (level of formality); record book"),
    "formel": ("a", "formal (masc.)"), "démarches": ("n", "procedures; formalities"),
    "administratives": ("a", "administrative (fem. plural)"),
    "faudrait": ("v", "it would be necessary"),
    "apportiez": ("v", "that you bring (subjunctive)"),
    "votre": ("a", "your (formal or plural)"),
    "pourriez-vous": ("v", "could you (formal)"), "confirmer": ("v", "to confirm"),
    "nouvelle": ("a", "new (fem.)"), "adresse": ("n", "address"),
    "faut": ("v", "it is necessary"),
    "n'expire": ("v", "expires (with a formal n' that does not negate)"),
    "envoyez": ("v", "send (formal or plural command)"),
    "dossier": ("n", "file; application folder"),
    "est-ce": ("h", "is it that (opens a yes/no question)"),
    "qu'il": ("h", "that he; that it"), "avis": ("n", "opinion; notice"),
    "présentez-vous": ("v", "report in person (formal command)"),
    "l'accueil": ("n", "the reception desk"), "mois": ("n", "month; months"),
    "emménagement": ("n", "moving in"), "madame": ("n", "madam; Mrs"),
    "monsieur": ("n", "sir; Mr"),
    "présentiez": ("v", "that you present (subjunctive)"),
    "carte": ("n", "card"), "facture": ("n", "bill; invoice"),
    "d'électricité": ("h", "of electricity"),
    "Fleurs": ("N", "Fleurs (part of a street name)"),
    "troisième": ("a", "third"), "arrondissement": ("n", "city district"),
    "remplissiez": ("v", "that you fill in (subjunctive)"),
    # unit16 opinions
    "pâtisserie": ("n", "pastry-making; pastry shop"),
    "intéressante": ("a", "interesting (fem.)"), "utile": ("a", "useful"),
    "quotidien": ("n", "everyday life"), "parce": ("c", "because (first half of a two-word conjunction)"),
    "créatif": ("a", "creative (masc.)"), "vend": ("v", "sells"),
    "tous": ("a", "every; all (masc. plural)"), "toujours": ("d", "always; still"),
    "boulangers": ("n", "bakers"), "par": ("p", "by; through"),
    "contre": ("p", "against"), "demande": ("v", "requires; asks for"),
    "créativité": ("n", "creativity"), "stable": ("a", "stable"),
    "financièrement": ("d", "financially"),
    "pâtissiers": ("n", "pastry chefs (masc. plural)"),
    "demandés": ("a", "in demand (masc. plural)"), "mariages": ("n", "weddings"),
    "même": ("d", "even; same"), "si": ("c", "if"),
    "indicatif": ("n", "indicative (a verb mood)"), "jamais": ("d", "never; ever"),
    "subjonctif": ("n", "subjunctive (a verb mood)"),
    "vaudrait": ("v", "would be worth"),
    "choisisses": ("v", "that you choose (informal, subjunctive)"),
    "pense": ("v", "think; thinks"), "vaut": ("v", "is worth"),
    "commencer": ("v", "to start"), "possible": ("a", "possible"),
    "sois": ("v", "that you be (informal, subjunctive)"),
    "heureuse": ("a", "happy (fem.)"), "d'un": ("h", "from one; on one (side)"),
    "créative": ("a", "creative (fem.)"), "dépend": ("v", "depends"),
    "chacun": ("r", "each person; everyone"), "son": ("a", "his; her; one's (masc.)"),
    "spécialité": ("n", "specialty; field of study"), "l'année": ("n", "the year"),
    "encore": ("d", "yet; still; again"), "risqué": ("a", "risky"),
    "gens": ("n", "people"), "achètent": ("v", "buy (they)"),
    "stabilité": ("n", "stability"), "passion": ("n", "passion"),
    # unit17 bank account
    "ouvrir": ("v", "to open"), "compte": ("n", "account"),
    "courant": ("a", "current; checking (masc.)"), "prouve": ("v", "proves"),
    "actuellement": ("d", "currently"), "contrat": ("n", "contract"),
    "revenus": ("n", "income"), "apporté": ("v", "brought (past participle)"),
    "fiche": ("n", "slip; sheet"), "paie": ("n", "pay (wages)"),
    "bancaire": ("a", "bank; banking"), "pouvez": ("v", "you can (formal or plural)"),
    "payer": ("v", "to pay"), "retirer": ("v", "to withdraw"),
    "l'argent": ("n", "the money"), "virement": ("n", "bank transfer"),
    "employeur": ("n", "employer"), "salaire": ("n", "salary"),
    "découvert": ("n", "overdraft"), "autorisé": ("a", "authorised (masc.)"),
    "laisse": ("v", "leaves; lets"), "marge": ("n", "margin; leeway"),
    "agence": ("n", "branch; agency"), "centre-ville": ("n", "town centre"),
    "conseillère": ("n", "advisor (fem.)"), "répond": ("v", "answers"),
    "toutes": ("a", "every; all (fem. plural)"), "questions": ("n", "questions"),
    "conseiller": ("n", "advisor (masc.)"), "renseignements": ("n", "information"),
    "comptes": ("n", "accounts"), "courants": ("a", "current; checking (masc. plural)"),
    "pourriez": ("v", "could (you, formal)"),
    "m'expliquer": ("v", "to explain to me"), "signer": ("v", "to sign"),
    "soit": ("v", "that it be (subjunctive)"), "actif": ("a", "active (masc.)"),
    "faut-il": ("v", "is it necessary (question)"), "prête": ("a", "ready (fem.)"),
    "tenue": ("n", "keeping; upkeep"),
    "gratuit": ("a", "free of charge (masc.)"),
    "gratuite": ("a", "free of charge (fem.)"), "première": ("a", "first (fem.)"),
    "année": ("n", "year"), "conditionnel": ("n", "conditional (a verb mood)"),
    "politesse": ("n", "politeness"), "notre": ("a", "our"),
    "apprentissage": ("n", "apprenticeship"),
    "pâtissière": ("n", "pastry chef (fem.)"), "félicitations": ("n", "congratulations"),
    "dire": ("v", "to say; to tell"), "élevés": ("a", "high (masc. plural)"),
    "restent": ("v", "stay; remain (they)"), "raisonnables": ("a", "reasonable (plural)"),
    "aurez": ("v", "you will have (formal or plural)"), "cents": ("n", "cents"),
    "sera": ("v", "will be"), "receviez": ("v", "that you receive (subjunctive)"),
    # unit18 at the doctor
    "gorge": ("n", "throat"), "depuis": ("p", "since; for"),
    "commencé": ("v", "started (past participle)"), "tôt": ("d", "early"),
    "douleur": ("n", "pain"), "forte": ("a", "strong; severe (fem.)"),
    "surtout": ("d", "especially"), "avaler": ("v", "to swallow"),
    "épuisé": ("a", "exhausted (masc.)"), "épuisée": ("a", "exhausted (fem.)"),
    "cause": ("n", "cause"), "debout": ("d", "standing up"),
    "chaleur": ("n", "heat"), "fours": ("n", "ovens"),
    "empirer": ("v", "to get worse"), "empire": ("v", "gets worse"),
    "docteur": ("n", "doctor"), "voix": ("n", "voice"),
    "enrouée": ("a", "hoarse (fem.)"),
    "s'améliorer": ("v", "to get better; to improve"),
    "s'améliore": ("v", "gets better; improves"),
    "revenez": ("v", "come back (formal or plural command)"),
    "voir": ("v", "to see"), "arrêt": ("n", "stop; sick leave"),
    "m'a": ("v", "has (to me, for me)"), "conseille": ("v", "advise; advises"),
    "reposiez": ("v", "that you rest (subjunctive)"), "boire": ("v", "to drink"),
    "d'eau": ("h", "of water"), "chaude": ("a", "hot; warm (fem.)"),
    "preniez": ("v", "that you take (subjunctive)"), "sirop": ("n", "syrup; cough syrup"),
    "fois": ("n", "times; occasions"), "veux": ("v", "I want; you want (informal)"),
    "reveniez": ("v", "that you come back (subjunctive)"), "reposer": ("v", "to rest"),
    "confirmation": ("n", "confirmation"), "Fournier": ("N", "Fournier"),
    "mardi": ("n", "Tuesday"), "14h30": ("s", "14:30 (half past two in the afternoon)"),
    "cabinet": ("n", "doctor's office; practice"), "Lambert": ("N", "Lambert"),
    "République": ("N", "Republic (part of a street name)"),
    "d'arriver": ("h", "of arriving"), "d'apporter": ("h", "of bringing"),
    "Vitale": ("N", "Vitale (name of the French health insurance card)"),
    "d'autres": ("h", "of others; other"), "symptômes": ("n", "symptoms"),
    "fièvre": ("n", "fever"), "exemple": ("n", "example"),
    "toute": ("a", "whole; all (fem.)"), "journée": ("n", "whole day"),
    "vois": ("v", "see (I)"), "ouvrez": ("v", "open (formal or plural command)"),
    "bouche": ("n", "mouth"), "angine": ("n", "tonsillitis; throat infection"),
    "vos": ("a", "your (plural)"), "cordes": ("n", "cords; strings"),
    "vocales": ("a", "vocal (fem. plural)"), "irritées": ("a", "irritated (fem. plural)"),
    "autant": ("d", "as much"), "miel": ("n", "honey"),
    "prescrire": ("v", "to prescribe"),
    # unit19 housing problem
    "panne": ("n", "breakdown; fault"), "four": ("n", "oven"),
    "utiliser": ("v", "to use"), "pâtisseries": ("n", "pastries"),
    "chauffage": ("n", "heating"), "marche": ("v", "works (of a device); walks"),
    "froid": ("a", "cold"), "fonctionne": ("v", "works; functions"),
    "salle": ("n", "room"), "bain": ("n", "bath"), "fuite": ("n", "leak"),
    "fuir": ("v", "to leak"), "fuit": ("v", "leaks"), "sous": ("p", "under"),
    "l'évier": ("n", "the sink"), "robinet": ("n", "tap; faucet"),
    "réparer": ("v", "to repair"), "réparation": ("n", "repair"),
    "vite": ("d", "quickly"), "propriétaire": ("n", "landlord; owner"),
    "locataire": ("n", "tenant"), "doit": ("v", "must; has to (he, she, one)"),
    "envoyer": ("v", "to send"), "quelqu'un": ("r", "someone"),
    "tant": ("d", "so much; so many"), "problèmes": ("n", "problems"),
    "serait": ("v", "would be"), "passer": ("v", "to come by; to drop by"),
    "vienne": ("v", "that he or she comes (subjunctive)"),
    "réparé": ("v", "repaired (past participle)"), "dès": ("p", "from; as early as"),
    "m'appeliez": ("v", "that you call me (subjunctive)"),
    "problème": ("n", "problem"), "écris": ("v", "write (I; you, informal)"),
    "appartement": ("n", "flat; apartment"),
    "n'y": ("h", "not there (as in there is no ...)"),
    "savoir": ("v", "to know"), "pourrez": ("v", "you will be able to (formal or plural)"),
    "chauffe": ("v", "heats; warms"), "vraiment": ("d", "really"),
    "l'appartement": ("n", "the flat; the apartment"), "Girard": ("N", "Girard"),
    "étage": ("n", "floor; storey"), "désolé": ("a", "sorry (masc.)"),
    "d'entendre": ("h", "of hearing"),
    "j'en": ("h", "I ... of it; I ... some of it"),
    "appeler": ("v", "to call"), "technicien": ("n", "technician"),
    "devrait": ("v", "should; ought to"), "entre": ("p", "between"),
    "serai": ("v", "I will be"), "chez": ("p", "at the home of"),
    "matinée": ("n", "morning (the whole morning)"),
    "n'hésitez": ("v", "do not hesitate (formal command)"),
    "rappeler": ("v", "to call back"), "passera": ("v", "will come by"),
    "9h": ("s", "9 o'clock"), "12h": ("s", "12 o'clock (noon)"),
    # unit20 job interview
    "Lefebvre": ("N", "Lefebvre"), "cherche": ("v", "looks for; is looking for"),
    "un(e)": ("c", "a (masc. or fem.)"),
    "apprenti(e)": ("n", "apprentice (masc. or fem.)"),
    "motivé(e)": ("a", "motivated (masc. or fem.)"),
    "rentrée": ("n", "start of the new school or work year"),
    "demandons": ("v", "we ask for"), "disponibilité": ("n", "availability"),
    "compris": ("a", "included (masc.)"),
    "candidature": ("n", "job application"), "postuler": ("v", "to apply (for a job)"),
    "postulé": ("v", "applied (past participle)"),
    "passionnée": ("a", "passionate; keen (fem.)"), "entretien": ("n", "interview"),
    "d'embauche": ("h", "of hiring"),
    "présente": ("v", "introduces; presents"), "m'appelle": ("v", "I am called"),
    "l'expérience": ("n", "the experience"), "d'": ("p", "of; from (before a vowel)"),
    "suivi": ("v", "followed; attended (past participle)"), "ami": ("n", "friend (masc.)"),
    "stage": ("n", "internship; work placement"), "cet": ("a", "this (masc., before a vowel)"),
    "semaines": ("n", "weeks"), "disponible": ("a", "available"),
    "point": ("n", "point"), "fort": ("a", "strong (masc.)"),
    "motivée": ("a", "motivated (fem.)"), "j'apprends": ("v", "I learn"),
    "utilise": ("v", "uses"), "pourrais": ("v", "I could"),
    "poser": ("v", "to ask (a question); to put"),
    "travaillerais": ("v", "I would work"), "matins": ("n", "mornings"),
    "l'apprentissage": ("n", "the apprenticeship"),
    "formateur": ("n", "trainer (masc.)"), "former": ("v", "to train"),
    "auprès": ("p", "alongside; with"), "chef": ("n", "head; chef"),
    "pâtissier": ("n", "pastry chef (masc.)"), "intéressée": ("a", "interested (fem.)"),
    "récemment": ("d", "recently"), "envie": ("n", "wish; desire"),
    "d'aller": ("h", "of going"), "d'être": ("h", "of being"),
    "venue": ("v", "come (fem. past participle)"),
    "parlez-moi": ("v", "tell me (formal command)"), "expérience": ("n", "experience"),
    "début": ("n", "beginning"), "professionnelle": ("a", "professional (fem.)"),
    "appris": ("v", "learned (past participle)"),
    "viennoiseries": ("n", "breakfast pastries (croissants and similar)"),
    "seriez-vous": ("v", "would you be (formal)"),
    "pose": ("v", "poses; puts"), "aucun": ("a", "no; not any"),
    "fermés": ("a", "closed (masc. plural)"), "plupart": ("n", "most; majority"),
    "travailleriez": ("v", "you would work (formal)"),
    "l'ouverture": ("n", "the opening"), "j'espérais": ("v", "I was hoping"),
    # unit21 disrupted journey
    "train": ("n", "train"), "annulé": ("a", "cancelled (masc.)"),
    "technique": ("a", "technical"), "voie": ("n", "platform; track"),
    "partira": ("v", "will leave"), "correspondance": ("n", "connection (to another train)"),
    "Dijon": ("N", "Dijon"), "billet": ("n", "ticket"), "valable": ("a", "valid"),
    "aux": ("p", "to the; at the (plural)"), "voyageurs": ("n", "travellers"),
    "18h40": ("s", "18:40 (twenty to seven in the evening)"),
    "retardé": ("a", "delayed (masc.)"), "quarante": ("n", "forty"),
    "peuvent": ("v", "can (they)"),
    "prévenir": ("v", "to warn; to let someone know"),
    "j'arriverai": ("v", "I will arrive"), "rater": ("v", "to miss"),
    "raté": ("v", "missed (past participle)"), "arriver": ("v", "to arrive"),
    "prévu": ("a", "expected; scheduled (masc.)"), "annoncé": ("a", "announced (masc.)"),
    "dix-neuf": ("n", "nineteen"), "soirée": ("n", "evening"),
    # unit22 digital life
    "consulter": ("v", "to check; to consult"), "messages": ("n", "messages"),
    "consulte": ("v", "checks; consults"), "réseaux": ("n", "networks"),
    "sociaux": ("a", "social (masc. plural)"), "métro": ("n", "underground; subway"),
    "rester": ("v", "to stay; to remain"), "contact": ("n", "contact"),
    "j'utilise": ("v", "I use"), "d'écran": ("h", "of the screen"),
    "j'essaie": ("v", "I try"), "limiter": ("v", "to limit"),
    "vingt-et-une": ("a", "twenty-one (fem.)"), "appli": ("n", "app"),
    "recettes": ("n", "recipes"), "presque": ("d", "almost"),
    "message": ("n", "message"), "parfois": ("d", "sometimes"),
    "ligne": ("n", "line"), "internet": ("n", "the internet"),
    "pauses": ("n", "breaks"), "déménagement": ("n", "move (to a new home)"),
    "utilises": ("v", "use (you, informal)"), "souvent": ("d", "often"),
    "réponds": ("v", "answer; reply (I)"),
    # unit23 busy week
    "chargée": ("a", "busy (fem.)"), "j'appelle": ("v", "I call"),
    "réviser": ("v", "to revise; to study again"), "planning": ("n", "schedule"),
    "d'inès": ("h", "of Inès"), "jeudi": ("n", "Thursday"), "appel": ("n", "call"),
    "révise": ("v", "revises; studies"), "travailler": ("v", "to work"),
    "travaille": ("v", "works; work (I; he, she)"), "général": ("a", "general"),
    "reposes": ("v", "rest (you, informal)"), "tranquille": ("a", "calm; quiet"),
    # unit24 complaint
    "réclamation": ("n", "complaint"), "service": ("n", "service; department"),
    "client": ("n", "customer"), "balance": ("n", "scale (for weighing)"),
    "ticket": ("n", "receipt; ticket"), "caisse": ("n", "cash register; checkout"),
    "gardé": ("v", "kept (past participle)"), "l'échange": ("n", "the exchange"),
    "l'écran": ("n", "the screen"), "l'allume": ("v", "turn(s) it on"),
    "noir": ("a", "black; dark"), "produit": ("n", "product"),
    "défectueux": ("a", "faulty (masc.)"), "magasin": ("n", "shop"),
    "reprend": ("v", "takes back"), "remboursement": ("n", "refund"),
    "demander": ("v", "to ask for"), "retours": ("n", "returns"),
    "produits": ("n", "products"), "échangés": ("a", "exchanged (masc. plural)"),
    "remboursés": ("a", "refunded (masc. plural)"), "pendant": ("p", "during; for"),
    "échange": ("n", "exchange"), "vendeur": ("n", "salesperson (masc.)"),
    "propose": ("v", "suggests; offers"), "cas": ("n", "case"),
    "proposer": ("v", "to suggest; to offer"), "nouveau": ("a", "new (masc.)"),
    "modèle": ("n", "model"), "pourrai": ("v", "I will be able to"),
    "présentation": ("n", "showing; presentation"),
}
POS_SETS["preposition"].discard("d'autres")  # A2 classifies the elided form as a phrase
for _tok, (_code, _gloss) in A2_ENTRIES.items():
    GLOSSES[_tok] = _gloss
    if _code != "n":
        POS_SETS.setdefault(_POS_CODE[_code], set()).add(_tok)

B1_ENTRIES: dict[str, tuple[str, str]] = {
    # unit25 abilities
    "complet": ("a", "complete; full (masc.)"), "prêt": ("a", "ready (masc.)"),
    "expliquer": ("v", "to explain"), "pouvoir": ("v", "to be able to; can"),
    "phrase": ("n", "sentence; clause"), "intégrée": ("a", "embedded (fem.)"),
    "copie": ("n", "copy"), "j'aurais": ("v", "I would have"),
    "leur": ("r", "them; to them"), "lui": ("r", "him; her; to him; to her"),
    "l'envoyer": ("h", "to send it"), "aurais": ("v", "I would have; you would have (informal)"),
    "travaillais": ("v", "I was working; you were working (informal)"),
    "n'aurais": ("v", "I would not have; you would not have (informal)"),
    # unit26 obligations
    "préviens": ("v", "I warn; I let know"), "badge": ("n", "badge; pass"),
    "sac": ("n", "bag"), "prévienne": ("v", "let know (subjunctive)"),
    "apportes": ("v", "you bring (informal)"), "uniforme": ("n", "uniform"),
    "obligation": ("n", "obligation"), "j'oublie": ("v", "I forget"),
    "aurait": ("v", "would have (he, she)"), "fallu": ("v", "been necessary (past participle)"),
    "veille": ("n", "the day before"), "pars": ("v", "leave (I; you, informal)"),
    "l'avais": ("h", "had it (imperfect)"),
    # unit27 hypotheses
    "passerai": ("v", "I will come by"), "finir": ("v", "to finish"),
    "j'irai": ("v", "I will go"), "condition": ("n", "condition"),
    "résultat": ("n", "result"), "futur": ("n", "future"),
    "j'avais": ("v", "I had"), "passerais": ("v", "I would come by"),
    "n'avais": ("v", "I did not have"), "resterais": ("v", "I would stay"),
    "longtemps": ("d", "for a long time"), "régler": ("v", "to settle; to sort out"),
    "finirais": ("v", "I would finish"), "irréelle": ("a", "unreal (fem.)"),
    "présent": ("n", "present (tense)"), "imparfait": ("n", "imperfect (a past tense)"),
    "vas": ("v", "you go; you are going (informal)"),
    # unit28 debate
    "court": ("a", "short (masc.)"), "l'organisation": ("n", "the organisation"),
    "importante": ("a", "important (fem.)"), "l'équipe": ("n", "the team"),
    "répondre": ("v", "to answer; to reply"), "l'avis": ("n", "the opinion"),
    "raison": ("n", "reason; being right"), "commande": ("n", "order (for goods)"),
    "commandes": ("n", "orders (for goods)"), "pause": ("n", "break"),
    "longue": ("a", "long (fem.)"), "aiderait": ("v", "would help"),
    "déjà": ("d", "already"), "garder": ("v", "to keep"),
    "qu'une": ("c", "that a (fem.)"), "refuses": ("v", "you refuse (informal)"),
    "l'idée": ("n", "the idea"), "long": ("a", "long (masc.)"),
    "proposes": ("v", "you suggest (informal)"), "solution": ("n", "solution"),
    "vraie": ("a", "real; true (fem.)"),
    # unit29 work
    "responsable": ("a", "in charge; responsible"), "importantes": ("a", "important (fem. plural)"),
    "liste": ("n", "list"), "vouvoiement": ("n", "using the formal form of address"),
    "collègue": ("n", "colleague"), "terminée": ("a", "finished (fem.)"),
    "livraison": ("n", "delivery"), "vérifier": ("v", "to check"),
    "elles": ("r", "they (fem.)"), "prêtes": ("a", "ready (fem. plural)"),
    "d'aide": ("h", "of help"),
    # unit30 narrative
    "préparais": ("v", "I was preparing; you were preparing (informal)"),
    "appelé": ("v", "called (past participle)"), "fond": ("n", "background"),
    "composé": ("a", "compound"), "événement": ("n", "event"),
    "principal": ("a", "main (masc.)"), "séquence": ("n", "sequence"),
    "fallait": ("v", "was necessary"), "livreur": ("n", "delivery person (masc.)"),
    "passée": ("v", "gone by; passed (fem. past participle)"),
    "avons": ("v", "we have"), "fini": ("v", "finished (past participle)"),
    # unit31 conditions
    "arrive": ("v", "arrives; I arrive"), "finirons": ("v", "we will finish"),
    "n'arrive": ("v", "does not arrive"), "préviendrai": ("v", "I will warn; I will let know"),
    "écrirai": ("v", "I will write"), "écriras": ("v", "you will write (informal)"),
    # unit32 sequences
    "l'envoie": ("h", "I send it"), "habituel": ("a", "usual (masc.)"),
    "l'événement": ("n", "the event"), "suivant": ("a", "following; next (masc.)"),
    "répondu": ("v", "answered (past participle)"), "été": ("v", "been (past participle)"),
    "confirmé": ("v", "confirmed (past participle)"), "envoies": ("v", "you send (informal)"),
    "réponse": ("n", "answer; reply"), "m'as": ("h", "you have (with me; helper verb)"),
    "prévenu": ("v", "warned; informed (past participle)"),
    "t'ai": ("h", "I have (with you; helper verb)"),
    # unit33 reported speech
    "rapporter": ("v", "to report (what was said)"), "demandé": ("v", "asked (past participle)"),
    "concordance": ("n", "agreement (of tenses)"), "verbe": ("n", "verb"),
    "d'introduction": ("h", "of introduction"), "n'a": ("v", "has not"),
    "rien": ("r", "nothing"), "d'autre": ("h", "else; other"),
    "maintenant": ("d", "now"),
    # unit34 goals
    "économies": ("n", "savings"), "formation": ("n", "training course"),
    "avancée": ("a", "advanced (fem.)"), "infinitif": ("n", "infinitive"),
    "but": ("n", "goal; purpose"), "étudier": ("v", "to study"),
    "forme": ("v", "trains (he, she)"), "puisse": ("v", "could; may (subjunctive)"),
    "seule": ("a", "alone; on one's own (fem.)"), "indépendante": ("a", "independent (fem.)"),
    "différent": ("a", "different (masc.)"), "pourquoi": ("d", "why"),
    "montre": ("v", "shows"), "bientôt": ("d", "soon"),
    "n'auras": ("v", "you will not have (informal)"),
    # unit35 advice
    "devrais": ("v", "I should; you should (informal)"), "parler": ("v", "to speak; to talk"),
    "emploi": ("n", "job; (in a set phrase) schedule"), "conseil": ("n", "piece of advice"),
    "j'étais": ("v", "I was"), "demanderais": ("v", "I would ask"),
    "repos": ("n", "rest"), "t'aidera": ("h", "will help you"),
    "n'ose": ("v", "do not dare (I); does not dare"), "directement": ("d", "directly"),
    "essayer": ("v", "to try"),
    # unit36 serious complaint
    "cassé": ("a", "broken (masc.)"), "livré": ("v", "delivered (past participle)"),
    "correctement": ("d", "correctly; properly"), "poli": ("a", "polite (masc.)"),
    "souhaiterais": ("v", "I would like (formal)"), "remplacement": ("n", "replacement"),
    "a-t-il": ("h", "has he; has it (question)"), "enverrons": ("v", "we will send"),
    "résolution": ("n", "resolution; settling"), "d'apprendre": ("h", "of learning; to hear (news)"),
    "situation": ("n", "situation"), "souhaitez-vous": ("v", "do you wish (formal)"),
    # unit37 regrets
    "concours": ("n", "competition; contest"), "dû": ("v", "had to; should have (past participle)"),
    "m'entraîner": ("h", "to train (myself)"), "davantage": ("d", "more"),
    "regret": ("n", "regret"), "regrette": ("v", "regret; regrets"),
    "l'aide": ("n", "the help"), "n'as": ("v", "you have not (informal)"),
    "eu": ("v", "had (past participle)"), "t'entraîner": ("h", "to train (yourself)"),
    "souhait": ("n", "wish"), "réalisé": ("a", "fulfilled; achieved (masc.)"),
    # unit38 plans
    "l'examen": ("n", "the exam"), "l'intention": ("n", "the intention"),
    "intention": ("n", "intention"), "projet": ("n", "plan; project"),
    "fixe": ("a", "fixed"), "réussirai": ("v", "I will succeed; I will pass"),
    "probablement": ("d", "probably"), "nerveuse": ("a", "nervous (fem.)"),
    "simple": ("a", "simple"), "prédiction": ("n", "prediction"),
    "assez": ("d", "fairly; quite; enough"), "sûre": ("a", "sure (fem.)"),
    "examen": ("n", "exam"), "penses": ("v", "you think (informal)"),
    "réussir": ("v", "to succeed; to pass"),
    # unit39 summarising
    "pétrir": ("v", "to knead"), "pâte": ("n", "dough"),
    "laisser": ("v", "to let; to leave"), "cuire": ("v", "to bake; to cook"),
    "haute": ("a", "high (fem.)"), "température": ("n", "temperature"),
    "points": ("n", "points"), "principaux": ("a", "main (masc. plural)"),
    "ordre": ("n", "order; sequence"), "étapes": ("n", "steps; stages"),
    "résumé": ("n", "summary"), "raconté": ("v", "told; recounted (past participle)"),
    "histoire": ("n", "story; history"), "n'était": ("v", "was not"),
    "important": ("a", "important (masc.)"), "distinguer": ("v", "to distinguish"),
    "détails": ("n", "details"), "essentiel": ("a", "essential (masc.)"),
    "expliqué": ("v", "explained (past participle)"), "l'essentiel": ("n", "the essential part"),
    # unit40 concessions
    "pétrin": ("n", "kneading machine; dough mixer"), "électrique": ("a", "electric"),
    "rapide": ("a", "fast; quick"), "pétrissage": ("n", "kneading"),
    "main": ("n", "hand"), "donne": ("v", "gives"),
    "concession": ("n", "concession"), "reformuler": ("v", "to rephrase"),
    "position": ("n", "position"), "nuance": ("n", "nuance; shade of meaning"),
    "cependant": ("d", "however"), "rapidité": ("n", "speed"),
    "priorité": ("n", "priority"), "qualité": ("n", "quality"),
    "connecteur": ("n", "linking word"), "deuxième": ("a", "second"),
    "machine": ("n", "machine"), "méthode": ("n", "method"),
    "traditionnelle": ("a", "traditional (fem.)"), "sent": ("v", "feels; smells"),
    # unit41 conditional hypotheses
    "propre": ("a", "own"), "j'utiliserais": ("v", "I would use"),
    "bio": ("a", "organic"), "hypothèse": ("n", "hypothesis"),
    "congé": ("n", "time off; leave"), "adoucir": ("v", "to soften"),
    "rêves": ("v", "you dream (informal)"), "patron": ("n", "boss; owner (masc.)"),
    "quelque": ("a", "some"),
    # unit42 meetings
    "peut-être": ("d", "perhaps"), "d'essayer": ("h", "of trying"),
    "vitrine": ("n", "shop window; display case"), "suggestion": ("n", "suggestion"),
    "formelle": ("a", "formal (fem.)"), "adoucie": ("a", "softened (fem.)"),
    "réunion": ("n", "meeting"), "convenu": ("v", "agreed (past participle)"),
    "confirme": ("v", "confirm (I); confirms"), "essaierons": ("v", "we will try"),
    "professionnel": ("a", "professional (masc.)"), "bref": ("a", "brief (masc.)"),
    "laquelle": ("r", "which one (fem.)"), "proposeriez-vous": ("v", "would you suggest (formal)"),
    "proposerais": ("v", "I would suggest"), "citron": ("n", "lemon"),
    "revisitée": ("a", "revisited; given a new twist (fem.)"),
    "essayons-la": ("h", "let us try it (fem.)"), "pouvez-vous": ("v", "can you (formal or plural)"),
    "écrit": ("n", "writing"),
    # unit43 descriptions
    "patient": ("a", "patient (masc.)"), "apprise": ("v", "learned (fem. past participle)"),
    "objet": ("n", "object"), "direct": ("a", "direct"),
    "secret": ("n", "secret"), "dont": ("r", "of which; whose; about which"),
    "complément": ("n", "complement; object (grammar)"), "remplace": ("v", "replaces"),
    "introduit": ("v", "introduces"), "sévère": ("a", "strict; severe"),
    "t'a": ("h", "has (with you; helper verb)"), "celle": ("r", "the one (fem.)"),
}
# B1 re-glosses of tokens that A1/A2 already classified in a different sense.
# Applied to the B1 course only.
B1_REGLOSS: dict[str, str] = {
    "peux": "I can; you can (informal)",
    "avis": "opinion",
    "service": "service; shift; department",
}
for _tok, (_code, _gloss) in B1_ENTRIES.items():
    GLOSSES[_tok] = _gloss
    if _code != "n":
        POS_SETS.setdefault(_POS_CODE[_code], set()).add(_tok)

# --- derive_target.py: derived units (generated; keep markers) ---
DERIVED_TARGET_GLOSSES: dict[str, str] = {
    "aider": "to help",
    "aller-retour": "return ticket; round trip",
    "allez": "come on; go (formal or plural)",
    "allô": "hello (on the phone)",
    "appelles": "you call (informal)",
    "attention": "attention; watch out",
    "bains": "bath (as in bathroom)",
    "balcon": "balcony",
    "bienvenue": "welcome",
    "bleu": "blue",
    "bois": "drink (informal command)",
    "bureau": "office; desk",
    "car": "because",
    "certaines": "some (fem. plural)",
    "chambre": "bedroom",
    "chambres": "bedrooms",
    "change": "changes",
    "chaud": "hot; warm",
    "chaussures": "shoes",
    "colère": "anger",
    "comprimé": "tablet; pill",
    "content": "happy (masc.)",
    "cosy": "cozy",
    "couleur": "color",
    "cuisinier": "cook (masc.)",
    "curieuse": "curious (fem.)",
    "d'attente": "of waiting (as in waiting room)",
    "disent": "say (they)",
    "départ": "departure",
    "ensoleillé": "sunny",
    "entendre": "to hear",
    "er": "ending of regular verbs",
    "es-tu": "are you (informal)",
    "faisons": "let's do; let's make",
    "fait-il": "is it (of weather)",
    "faites-vous": "do you wear (size, formal)",
    "fier": "proud (masc.)",
    "film": "film",
    "fin": "end",
    "finis": "finish (I form)",
    "fière": "proud (fem.)",
    "gardent": "keep (they)",
    "grand": "big (masc.)",
    "guichet": "ticket counter",
    "honnêtement": "honestly",
    "horaires": "working hours; schedule",
    "infirmier": "nurse (masc.)",
    "infirmière": "nurse (fem.)",
    "jardin": "garden",
    "joli": "pretty; nice (masc.)",
    "l'appareil": "the phone (device)",
    "l'entrée": "the entrance",
    "l'essayer": "to try it on",
    "l'hôpital": "the hospital",
    "l'intérieur": "the inside",
    "m": "M (medium clothing size)",
    "m'aide": "helps me",
    "m'appeler": "to call me",
    "malade": "sick; ill",
    "manteau": "coat",
    "masculin": "masculine",
    "monte": "gets on; goes up",
    "médecin": "doctor",
    "métier": "occupation; trade",
    "météo": "weather forecast",
    "nerveux": "nervous (masc.)",
    "noire": "black (fem.)",
    "nouvel": "new (before a vowel, masc.)",
    "nuageux": "cloudy",
    "panneau": "sign; notice board",
    "pantalon": "pants; trousers",
    "parka": "parka; winter coat",
    "parlez": "you speak (formal or plural)",
    "part": "leaves; departs",
    "part-dieu": "Part-Dieu (station name)",
    "pensais": "I thought",
    "pensé": "thought",
    "personnes": "people",
    "petit": "small (masc.)",
    "pile": "exactly; right on the dot",
    "pièces": "rooms",
    "pleut": "rains; is raining",
    "prenez": "take (formal command)",
    "pris": "taken",
    "promenade": "walk",
    "pull": "sweater",
    "quai": "platform",
    "quels": "which (plural)",
    "rappelle": "call back (I form)",
    "repose-toi": "rest (informal command)",
    "restaurant": "restaurant",
    "rhume": "cold (illness)",
    "rythme": "rhythm",
    "rétablissement": "recovery",
    "salon": "living room",
    "sens": "feel (I or you informal)",
    "sent-il": "does he feel",
    "seras": "you will be (informal)",
    "seul": "alone (masc.)",
    "sms": "text message",
    "sortie": "exit",
    "super": "great",
    "sympa": "nice; friendly",
    "sûrement": "surely",
    "t'appeler": "to call you",
    "t'appelle": "I call you",
    "t'entends": "you hear (informal)",
    "t'envoie": "I send you",
    "t'inquiète": "worry (informal command)",
    "taille": "size",
    "tranquillement": "calmly; peacefully",
    "travaillent": "work (they)",
    "travailles-tu": "do you work (informal)",
    "triste": "sad",
    "truc": "thing; something (informal)",
    "tête": "head",
    "ventre": "stomach; belly",
    "verbes": "verbs",
    "vie": "life",
    "voulez-vous": "do you want (formal)",
    "vouvoie": "uses the formal you",
    "évidemment": "of course",
}
DERIVED_TARGET_POS: dict[str, str] = {
    "aider": "verb",
    "allez": "verb",
    "allô": "particle",
    "appelles": "verb",
    "bienvenue": "adjective",
    "bleu": "adjective",
    "bois": "verb",
    "car": "particle",
    "certaines": "adjective",
    "change": "verb",
    "chaud": "adjective",
    "content": "adjective",
    "cosy": "adjective",
    "curieuse": "adjective",
    "d'attente": "phrase",
    "disent": "verb",
    "ensoleillé": "adjective",
    "entendre": "verb",
    "es-tu": "verb",
    "faisons": "verb",
    "fait-il": "verb",
    "faites-vous": "verb",
    "fier": "adjective",
    "finis": "verb",
    "fière": "adjective",
    "gardent": "verb",
    "grand": "adjective",
    "honnêtement": "adverb",
    "joli": "adjective",
    "l'essayer": "verb",
    "m'aide": "verb",
    "m'appeler": "verb",
    "malade": "adjective",
    "masculin": "adjective",
    "monte": "verb",
    "nerveux": "adjective",
    "noire": "adjective",
    "nouvel": "adjective",
    "nuageux": "adjective",
    "parlez": "verb",
    "part": "verb",
    "part-dieu": "proper_noun",
    "pensais": "verb",
    "pensé": "verb",
    "petit": "adjective",
    "pile": "adverb",
    "pleut": "verb",
    "prenez": "verb",
    "pris": "verb",
    "quels": "pronoun",
    "rappelle": "verb",
    "repose-toi": "verb",
    "sens": "verb",
    "sent-il": "verb",
    "seras": "verb",
    "seul": "adjective",
    "super": "adjective",
    "sympa": "adjective",
    "sûrement": "adverb",
    "t'appeler": "verb",
    "t'appelle": "verb",
    "t'entends": "verb",
    "t'envoie": "verb",
    "t'inquiète": "verb",
    "tranquillement": "adverb",
    "travaillent": "verb",
    "travailles-tu": "verb",
    "triste": "adjective",
    "voulez-vous": "verb",
    "vouvoie": "verb",
    "évidemment": "adverb",
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

# A2 re-uses a few A1 spellings in a different sense; the A2 course gets its own
# gloss (and part of speech) keyed by (realization stem, token).
GLOSS_OVERRIDES = {
    ("a2_unit17_compte_bancaire", "frais"): "fees; charges",
    ("a2_unit20_entretien_embauche", "poste"): "job; position",
    ("a2_unit22_vie_numerique", "regarde"): "look at; watch (I; he, she)",
    ("a2_unit22_vie_numerique", "passe"): "spend (time); pass",
}
POS_OVERRIDES = {("a2_unit17_compte_bancaire", "frais"): "noun"}


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
        ) if level != "b1" else classify(
            lang=LANG,
            level=level,
            unit_files=realizations,
            glosses={**GLOSSES, **B1_REGLOSS},
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
