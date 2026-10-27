#!/usr/bin/env python3
"""Derive units of a new TARGET language from a rich source target course.

derive_direction.py reuses one target course across LEARNER languages (same
target sentences, translated overlays).  This tool does the other axis: the
learner language stays (en) and the TARGET language changes.  It takes A1 units
of a deep course (en-nl: Dutch targets, English overlay) and rebuilds them for a
thin one (en-es: Spanish targets, English overlay) by *translating* the target
side instead of hand-authoring YAML:

    extract  nl units -> flat JSON to translate / author     (.local/derive-target/<new>/)
    (translate atoms.src.json -> atoms.tr.json, author.src.json -> author.tr.json)
    lexemes  list new target tokens that still need a gloss + part of speech
    (write lexemes.tr.json)
    inject   realizations + overlays + manifest line + backfill gloss block
    check    compiler validate/compile of the course + backfill dry run

What is translated, what is derived, what is authored (docs/content/DIRECTION_PIPELINE.md):

* atoms (atoms.*.json): every distinct source-target string (teaching targets,
  examples, titles, media texts, pair left sides, prompts).  Translated once,
  reused everywhere the exact text occurs, including inside English feedback.
* derived, never sent: introduced_tokens, tested_text (when it is a sentence atom or the
  answer), word_bank tiles (from the translated answer), punctuation variants of
  accepted answers, content keys (slugs re-derived from the translation),
  pair right sides, all English glosses/titles/options.
* authored (author.*.json): things that must be rewritten for the new language and
  not translated: distractors, fill-in-blank frames and answers, free-production
  answers with their variants, tested spans of comprehension items, grammar notes
  and feedback/instructions that talk about the source language, tile distractors.
  Every such slot is flagged AUTHOR in the report.
* flagged (report.json, lint): gender, formal/informal register, obligatory
  contractions, word-order variants that the tile bank cannot build, leftover
  source-language words, cast names.  Errors block inject unless acknowledged in
  ack.json ({"<id>:<FLAG>": "reason"}) or forced.

Not derived: practice packs (hand-authored per language, PRACTICE_PACK_RECIPE.md),
audio (media assets stay pending_generation), native review.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import derive_direction as dd  # noqa: E402  (load/dump/manifest helpers)

ROOT = HERE.parent
CONTENT = ROOT / "docs/content"
MANIFEST = ROOT / "scripts/manifest.d/content"
DEFAULT_WORK = ROOT / ".local/derive-target"

# ---------------------------------------------------------------------------
# Per-language configuration (formal / informal markers, gender, contractions)
# ---------------------------------------------------------------------------
DEV = "\u0900-\u0963\u0966-\u096f\u0971-\u097f"       # see PUNCT_CHARS below
CFG = {
    # code: formal marker, informal marker (regexes over lowercase text)
    "nl": dict(name="Dutch", formal=r"\b(u|uw)\b", informal=r"\b(je|jij|jou|jouw|jullie)\b",
               short=("ik", "je", "op", "om", "de", "te", "ze", "nu", "zo", "er", "van", "het", "een", "niet", "geen", "voor", "naar", "bij", "dat", "ook", "maar", "wel", "nog", "zijn", "heeft", "als", "hij", "zij", "jij", "mijn", "jullie", "aan"),
               grammar=r"\b(split(?:s|ting)?|separable|prefix(?:es)?|main clause|het-?words?|de-?words?|neuter|common gender|inversion|bare adjective|extra -e|final position|verb-second|halfway|counts forward|netherlands|holland|belgi\w+|flanders|gemeente|digid|sinterklaas|koningsdag|stroopwafel)\b"),
    "de": dict(
        name="German",
        case_sensitive=True,                 # nouns are capitalised: never casefold tested_text / tiles; slugs transliterate umlauts
        translit=True,
        rekey_exercises=True,
        strict_residual=True,                # source-language words inside English fields are found by vocabulary, not by "occurs in an English field"
        per_card_keys=True,                  # a reading card's gloss keys translate per card (the same source word is another token in another text)
        rewrite_gloss=True,                  # rewritten grammar cards must also get an authored English title + gloss
        formal=r"\bIhnen\b|\bIhr(?:e|en|em|er|es)?\b|(?<=[\w,]) Sie\b",    # matched on the original case: sentence-initial Sie is ambiguous (she/they)
        informal=r"(?i:\b(?:du|dich|dir|dein\w*)\b)",
        gender=dict(mode="agent"),           # learner speaks as themselves: Ich bin Student / Studentin
        contractions=[(r"\b[iI]n dem\b", "im"), (r"\b[aA]n dem\b", "am"), (r"\b[zZ]u dem\b", "zum"), (r"\b[zZ]u der\b", "zur"),
                      (r"\b[vV]on dem\b", "vom"), (r"\b[bB]ei dem\b", "beim")],
        note=("Natural standard German. Nouns capitalised (Hund, not hund); real spelling (ä ö ü ß, no ae/ue). Informal source roles -> du, formal -> Sie "
              "(capital Sie/Ihnen/Ihr). Verb second in main clauses, verb-first questions, separable verbs split (Ich stehe um sieben Uhr auf), "
              "cases marked (accusative: Ich habe einen Hund; dative after mit/bei/zu). "
              "Contract in dem/an dem/zu dem/zu der/von dem/bei dem -> im/am/zum/zur/vom/beim."),
    ),
    "es": dict(
        name="Spanish",
        formal=r"\busted(es)?\b",
        informal=r"\b(tú|tu|te|ti|contigo|vosotros)\b|\b(tienes|puedes|quieres|eres|estás|vives|necesitas|hablas|haces|vas|sabes|dices|prefieres|llamas)\b",
        gender=dict(
            copula=r"\b(estoy|soy|estás|eres|estamos|somos|me siento|te sientes)\b",
            skip="de en a aquí ahí allí ahora bien mal ya con sin por para un una el la los las mi tu su casa muy tan mucho poco".split(),
            swap=(("o", "a"), ("os", "as")),
        ),
        contractions=[(r"\b[dD]e el\b", "del"), (r"\b[aA] el\b", "al")],
    ),
    "it": dict(
        name="Italian",
        rekey_exercises=True,                # exercise key tails re-derived from the translation (no Dutch slugs)
        strict_residual=True,                # source-language words inside English fields are found by vocabulary
        per_card_keys=True,                  # reading-card gloss keys translate per card
        rewrite_gloss=True,                  # rewritten grammar cards get an authored English title + gloss
        always_desc=True,                    # the unit description quotes Dutch phrases: author it for every unit
        formal=r"\blei\b",
        informal=r"\b(tu|ti|te|tuo|tua|tuoi|tue)\b|\b(hai|puoi|vuoi|vai|fai|devi|sai|dici|vieni|parli|abiti|lavori|preferisci|prendi|ti chiami)\b",
        # learner speaks as themselves: Sono stanco / Sono stanca (-o/-a; -e adjectives and -i/-e plurals need no alternate)
        gender=dict(copula=r"\b(sono|sei|siamo|mi sento|ti senti)\b", skip="di in a qui lì ora bene male già con senza per un una il la i le mio tua molto".split(), swap=(("o", "a"),)),
        # articulated prepositions are obligatory (di il -> del, in l' -> nell'); never accept the open form as a variant
        contractions=[(r"\b[dD]i il\b", "del"), (r"\b[dD]i lo\b", "dello"), (r"\b[dD]i la\b", "della"), (r"\b[dD]i l'", "dell'"),
                      (r"\b[dD]i i\b", "dei"), (r"\b[dD]i gli\b", "degli"), (r"\b[dD]i le\b", "delle"),
                      (r"\b[aA] il\b", "al"), (r"\b[aA] lo\b", "allo"), (r"\b[aA] la\b", "alla"), (r"\b[aA] l'", "all'"),
                      (r"\b[aA] i\b", "ai"), (r"\b[aA] gli\b", "agli"), (r"\b[aA] le\b", "alle"),
                      (r"\b[iI]n il\b", "nel"), (r"\b[iI]n lo\b", "nello"), (r"\b[iI]n la\b", "nella"), (r"\b[iI]n l'", "nell'"),
                      (r"\b[iI]n i\b", "nei"), (r"\b[iI]n gli\b", "negli"), (r"\b[iI]n le\b", "nelle"),
                      (r"\b[dD]a il\b", "dal"), (r"\b[dD]a lo\b", "dallo"), (r"\b[dD]a la\b", "dalla"), (r"\b[dD]a l'", "dall'"),
                      (r"\b[dD]a i\b", "dai"), (r"\b[dD]a gli\b", "dagli"), (r"\b[dD]a le\b", "dalle"),
                      (r"\b[sS]u il\b", "sul"), (r"\b[sS]u lo\b", "sullo"), (r"\b[sS]u la\b", "sulla"), (r"\b[sS]u l'", "sull'"),
                      (r"\b[sS]u i\b", "sui"), (r"\b[sS]u gli\b", "sugli"), (r"\b[sS]u le\b", "sulle")],
        # elision: lo/la/una before a vowel is written l'/l'/un' (no space); `un` never takes an apostrophe before a masculine noun
        elisions=[(r"(?<![\w'’])[lL][oa] (?=[aeiouàèéìòùhAEIOU])", "l'"), (r"(?<![\w'’])[uU]na (?=[aeiouàèéìòùAEIOU])", "un'"),
                  (r"(?<![\w'’])[uU]n['’]\s?(?=(?:amico|albergo|uomo|orologio|ombrello|ufficio|aereo|autobus|anno|esame|ospedale|inverno|appuntamento|indirizzo)\b)", "un (masculine nouns take no apostrophe)")],
        note=("Natural standard Italian. Informal source roles -> tu, formal -> Lei (capital Lei/Le/La only for 'you'; verb in the third person: Lei ha, "
              "Può aiutarmi?). Obligatory articulated prepositions: di/a/da/in/su + il/lo/la/l'/i/gli/le -> del, al, dal, nel, sul ... "
              "(nel parco, dell'ufficio, alla stazione, sul tavolo). Elision: l'amico, l'acqua, un'amica (but un amico), dov'è, c'è. "
              "Pro-drop: no subject pronoun unless it contrasts (Sono di Roma). Speaker-gendered adjectives/participles as the learner "
              "answer (Sono stanco/stanca, Sono stato/stata) need the other gender as an accepted alternate."),
    ),
    "fr": dict(
        name="French",
        rekey_exercises=True,                # exercise key tails re-derived from the translation
        strict_residual=True,
        per_card_keys=True,
        rewrite_gloss=True,
        speaker_label_no_space=True,         # "Camille: Bonjour." even though French puts a space before other colons
        straight_apostrophe=True,            # j'ai, l'école: the grader folds both, the corpus uses the straight one
        formal=r"\b(?:vous|votre|vos)\b",
        informal=r"\b(?:tu|toi|ton|ta|tes|te)\b|(?<!\w)t'",
        gender=dict(mode="fr"),              # speaker-gendered adjective / participle / agent noun after je suis, je me sens ...
        contractions=[(r"\b[dD]e le\b", "du"), (r"\b[àÀ] le\b", "au"), (r"\b[dD]e les\b", "des"), (r"\b[àÀ] les\b", "aux")],
        elision=True,                        # je/le/la/de/ne/me/te/se/que/ce + vowel or mute h -> j'/l'/d'/n'/m'/t'/s'/qu'/c'
        note=("Natural standard French (metropolitan). Straight apostrophes (j'ai, l'école). Informal source roles -> tu, formal -> vous "
              "(service staff, strangers). Obligatory contractions: du, au, des, aux. Obligatory elision before a vowel or mute h (l'hôtel, j'habite, "
              "c'est, qu'il, d'abord). Hyphenated inversions and elided forms are single tiles (vas-tu, est-ce, l'école). "
              "Speaker-gendered words (je suis fatigué/fatiguée, étudiant/étudiante) need the other gender as an accepted alternate (#alt)."),
    ),
    "pl": dict(
        name="Polish",
        rekey_exercises=True,                # exercise key tails re-derived from the translation
        strict_residual=True,
        per_card_keys=True,
        rewrite_gloss=True,
        formal=r"\b(?:pan|pani|panie|panu|panią|pana|panowie|panów|państwo|państwa|państwu|państwem|paniom)\b",
        informal=r"\b(?:ty|ciebie|cię|ci|tobie|tobą|twój|twoja|twoje|twoim|twoją|twojego|twojej|masz|jesteś|możesz|chcesz|lubisz|robisz|"
                 r"mieszkasz|pracujesz|idziesz|czujesz|wiesz|potrzebujesz|jesteście|wy|wam|wasz\w*)\b",
        gender=dict(mode="pl"),              # speaker-gendered: jestem zmęczony/zmęczona, byłem/byłam, chciałbym/chciałabym, jestem studentem/studentką
        note=("Natural standard Polish with full diacritics (ą ć ę ł ń ó ś ź ż): the grader does not fold them, so a diacritic-less answer is never accepted "
              "and must never be listed as a variant. Informal source roles -> ty (2nd person singular), formal -> pan/pani (3rd person: Czy pan jest ...?, "
              "Proszę pani). Seven cases (name the case you use: accusative after widzę/mam/chcę, genitive after nie ma/brak/numbers 5+, locative after w/na/o, "
              "instrumental after z and with jestem + noun, dative after dać/pomóc, genitive after do/od/z). Verbs agree in person, tense and gender: "
              "speaker-gendered words (byłem/byłam, jestem zmęczony/zmęczona, studentem/studentką) need the other gender as an accepted alternate (#alt). "
              "Aspect pairs (robić/zrobić, pisać/napisać): imperfective for habit and process, perfective for a finished result. "
              "Pro-drop: leave the subject pronoun out unless it is contrastive (Mam psa, not Ja mam psa). Masculine personal plural uses -i/-y forms (oni są zmęczeni), "
              "other plurals -e. Cast names: write the nominative name as the source name (it is mapped), but write DECLINED forms directly with the final Polish name "
              "(z Ewą, do Marka, u Kasi, w Krakowie)."),
    ),
    "ro": dict(
        name="Romanian",
        rekey_exercises=True,
        strict_residual=True,
        per_card_keys=True,
        rewrite_gloss=True,
        fold_chars={"\u015f": "\u0219", "\u015e": "\u0218", "\u0163": "\u021b", "\u0162": "\u021a"},   # cedilla -> comma-below (the grader folds both, the corpus uses ș ț)
        diacritics="ro",                     # ORTHO lint: no cedilla, â/î placement
        formal=r"\b(?:dumneavoastr[aă]|dvs|dumneata|v[aă]|v-|vi-)(?!\w)",
        informal=r"\b(?:tu|tine|te|ți|tău|ta|tale|tăi|ești|vrei|poți|vii|ai)\b|\bți-|-ți\b|\bt-",
        gender=dict(mode="ro"),              # speaker-gendered adjective / participle / agent noun after sunt, mă simt ...
        note=("Natural standard Romanian. Diacritics are mandatory and use comma-below ș ț (never cedilla ş ţ), plus ă â î: î at the start and end of a word, â inside "
              "(România, mâncare, pâine, gândesc, cânt, dar înainte, încă, în). Informal source roles -> tu (te rog, ai, ești), formal -> dumneavoastră "
              "(vă rog, aveți, sunteți; staff, strangers, doctors). Nouns have three genders: masculine, feminine, neuter (neuter is masculine in the singular "
              "and feminine in the plural: un scaun / două scaune). The definite article is a suffix: casă / casa, un băiat / băiatul, o fată / fata, "
              "plural casele, băieții. Hyphenated clitics are single tiles (mi-e, m-am, nu-mi, ți-e, s-a, n-am). Speaker-gendered words (sunt obosit/obosită, "
              "sunt student/studentă) need the other gender as an accepted alternate (#alt). Names: avoid vocative/genitive/dative forms of the mapped "
              "cast names (use pentru Lotte, cu Lotte, de la Lotte); lui Omar is fine."),
    ),
    "ru": dict(
        name="Russian",
        script="cyrillic",                   # tokens, tiles, lexeme keys and content-key slugs (TRANSLIT_RU) work on Cyrillic; no stress marks, no Latin letters
        rekey_exercises=True,
        strict_residual=True,
        per_card_keys=True,
        rewrite_gloss=True,
        yo_fold=True,                        # an accepted free-text answer with ё also accepts е (the grader does not fold them; the ru corpus lists both)
        formal=r"\b(?:вы|вас|вам|вами|ваш\w*)\b",
        informal=r"\b(?:ты|тебя|тебе|тобой|тво(?:й|я|ё|е|и|их|ей|его|ему|им|ими|ю|ем)|давай(?:те)?)\b",
        gender=dict(mode="ru"),              # speaker-gendered past tense, short adjective or agent noun after я: устал/устала, рад/рада, студент/студентка
        note=("Natural standard Russian (contemporary, Moscow norm). Cyrillic only, written with ё where it is normal in the course (идёт, всё, ещё) "
              "and NO stress marks. Informal source roles -> ты, formal or service staff and strangers -> Вы/вы (capital Вы only for one person in a "
              "formal address). Six cases: nominative for the subject, accusative for the object (читаю книгу), genitive after нет/у/из/для/numbers "
              "(у меня нет брата), dative for мне нравится / мне нужно / дать кому, instrumental after с and for the profession after работаю "
              "(работаю учителем), prepositional after в/на/о (в школе, на работе). Gender: a learner who speaks as themselves with a past-tense verb or "
              "short adjective needs the other gender as an accepted alternate (#alt): Я устал / Я устала, Я был / Я была, Я рад / Я рада, "
              "Я студент / Я студентка. Aspect: use imperfective for habits and ongoing actions (я читал), perfective for a finished result (я прочитал); "
              "future with буду + infinitive only for imperfective. Verbs of motion: идти (on foot) / ехать (by vehicle). No articles; the verb 'to be' is "
              "dropped in the present (Я дома, У меня есть брат). Short answers: keep word order natural, topic first. "
              "Tiles: every word is one tile, a hyphenated word (по-русски, кто-то) is one tile."),
    ),
    "ar": dict(
        name="Arabic",
        script="arabic",                     # RTL; tokens / tiles / lexeme keys use \w (letters only: harakat are NOT \w, so the A1 text carries none)
        rekey_exercises=True,
        strict_residual=True,
        per_card_keys=True,
        rewrite_gloss=True,
        arabic_punct=True,                   # ? , ; written as the Arabic question mark / comma / semicolon in target text
        formal=r"(?!)",                      # MSA has no tu/vous split at A1: the REGISTER lint never fires
        informal=r"(?!)",
        gender=dict(mode="ar"),              # speaker gender (انا متعب/متعبة) and addressee gender (تريد/تريدين, اشرب/اشربي, انت مريض/مريضة)
        note=("Natural Modern Standard Arabic (fusha), the register of ar units 01-24. Write WITHOUT tashkeel (no harakat, no tatweel): the course "
              "convention and the tokenizer both rely on it, and the grader accepts answers with or without harakat; the notes give a transliteration "
              "in parentheses instead (مال (māl)). Spell hamza exactly (أ إ آ ؤ ئ) and use Arabic yeh ي, kaf ك, teh marbuta ة, alef maqsura ى; "
              "a hamza-only slip is graded 'almost', never auto-accepted, so keep ONE spelling per word through the course. Western digits (5, not ٥). "
              "Punctuation: ، ؟ ؛ (the full stop stays '.'). Attached particles are written joined and are ONE tile / token: و (and), ب (with, by), "
              "ل (for, to), ك, ف, سـ (will): وقهوة, بالبطاقة, للمدرسة, سأدفع. Never leave them detached (و قهوة). Definite article ال is attached "
              "(الكتاب); ل + ال contracts to لل (للمدرسة, not لالمدرسة); sun letters assimilate only in pronunciation, so in a transliteration write "
              "ash-shams, ar-raʾs, at-tuffāḥ, but al-qamar, al-baṭn. Dual: two of something is the dual noun, not the numeral + plural "
              "(كتابان / كتابين, not اثنان كتب). Gender: every 2nd-person verb, imperative and predicate adjective differs for a man and a woman "
              "(تشرب / تشربين, اشرب / اشربي, أنت متعب / متعبة) and so do predicates after أنا (أنا طالب / طالبة): the learner answer needs the other gender as "
              "an accepted alternate (#alt). Cast: Layla ليلى and Nour نور are women, Yusuf يوسف and Karim كريم are men. Prices in dirhams or dinars as the "
              "existing units do. Notes quote Arabic followed by a transliteration in parentheses: مال (māl) means money."),
    ),
    "hi": dict(
        name="Hindi",
        script="devanagari",                 # tokens / tiles / norm keys keep the vowel signs (DEV); slugs transliterate (translit_hi); no Latin letters in Hindi text
        rekey_exercises=True,
        strict_residual=True,
        per_card_keys=True,
        rewrite_gloss=True,
        danda=True,                          # sentences end with the danda; an internal danda also gets a full-stop variant (the grader only strips boundary punctuation)
        spell_fold="hi",                     # chandrabindu/anusvara and the optional nukta are folded by the grader, but the lexeme backfill keeps them apart: one spelling per word
        formal=r"(?<![%(W)s])(?:आप|आपका|आपकी|आपके|आपको|आपसे|आपने|आपमें)(?![%(W)s])" % dict(W=DEV + r"\w"),
        informal=r"(?<![%(W)s])(?:तुम|तुम्हारा|तुम्हारी|तुम्हारे|तुम्हें|तुम्हे|तुमसे|तुमने|तुमको|तू|तेरा|तेरी|तेरे|तुझे)(?![%(W)s])" % dict(W=DEV + r"\w"),
        gender=dict(mode="hi"),              # speaker-gendered participle / adjective / agent noun after मैं: जाता हूँ / जाती हूँ, थका / थकी, छात्र / छात्रा
        note=("Natural everyday Hindi in Devanagari, not overly Sanskritised (use the common word: पानी, दोस्त, अस्पताल, रविवार; keep established English "
              "loans in Devanagari: डॉक्टर, फ़ोन, टिकट, स्टेशन). Sentences end with the danda । (? and ! stay). No Latin letters. Informal source roles -> तुम "
              "(verb हो / -ते हो; तू only for a child or a pet), formal or service staff and strangers -> आप (verb हैं / -ते हैं). Postpositions follow the noun and "
              "make it oblique: घर में, दुकान पर, दोस्त के साथ, बाज़ार से, स्कूल को; का/की/के agree with the thing owned (मेरा भाई, मेरी बहन, मेरे दोस्त). "
              "Word order is subject - object - verb. Simple present: -ता/-ती/-ते + हूँ/है/हो/हैं; progressive: रहा/रही/रहे + हूँ/है; "
              "need and obligation: मुझे ... चाहिए / मुझे ... जाना है; mujhe-type constructions for pain, liking and having. "
              "Gender: a learner speaking as themselves needs the other gender as an accepted alternate (#alt): मैं जाता हूँ / मैं जाती हूँ, मैं थका हूँ / मैं थकी हूँ, "
              "मैं छात्र हूँ / मैं छात्रा हूँ. Past transitive uses ने (मैंने खाना खाया) and does not change with the speaker. "
              "Spelling: use चँद्रबिंदु where it is standard (हूँ, कहाँ, यहाँ, मैं with anusvara) and keep ONE spelling per word in the whole unit - the grader folds "
              "ँ/ं and the nukta of क़ ख़ ग़ ज़ फ़, but the lexemes do not. Keep ड़ ढ़ with the nukta. Avoid hyphenated reduplications (a hyphenated word is one tile, but keep it rare)."),
    ),
    "pt": dict(name="Portuguese", formal=r"\bo senhor|a senhora\b", informal=r"\btu\b"),
}
TARGET_ANSWER_TYPES = {
    "word_order", "listen_order", "fill_in_blank", "translation", "writing_prompt",
    "dictation", "listen_type", "dialogue_response", "speak_response",
}
GERMAN_FREE_TEXT_TYPES = {"writing_prompt", "dialogue_response", "listen_type", "translation", "reverse_translation", "grammar_check"}   # compile_content.py
YO_FOLD_TYPES = {"fill_in_blank", "translation", "writing_prompt", "dictation", "listen_type", "dialogue_response", "speak_response",
                 "reverse_translation", "grammar_check"}
SEP = " || "
BLANK = "___"
# Python's \w misses the Devanagari vowel signs, nukta, virama and chandrabindu (U+0900-0963); DEV keeps them inside words.
# The danda (U+0964/0965) stays punctuation.  A no-op for every other script.
PUNCT_CHARS = re.compile(rf"[^\w{DEV}\s'’\-‌]", re.U)
TOKEN_RE = re.compile(rf"[\w{DEV}'’\-‌]+", re.U)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
_EN_VOCAB: set[str] | None = None


def strip_punct(s: str) -> str:
    return " ".join(PUNCT_CHARS.sub(" ", s).split()) if "\n" in s else " ".join(PUNCT_CHARS.sub("", s).split())


def boundary_strip(s: str) -> str:
    """Only the punctuation at both ends (the dictation compiler check ignores just that)."""
    return re.sub(r"^[\s.!?¿¡;:,\"“”„«»…—–؟،؛।]+|[\s.!?¿¡;:,\"“”„«»…—–؟،؛।]+$", "", s)


def norm(s: str) -> str:
    """Same folding as compile_content.normalize_dialogue_option."""
    return " ".join(re.sub(rf"[^\w{DEV}‌]+", " ", s, flags=re.U).casefold().split())


def tokens(s: str) -> list[str]:
    return [t for t in (x.strip("-") for x in TOKEN_RE.findall(strip_punct(s))) if t]       # a bare "-e" ending is not a word


TRANSLIT_DE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"})


TRANSLIT_LIG = str.maketrans({"œ": "oe", "Œ": "Oe", "æ": "ae", "Æ": "Ae", "ł": "l", "Ł": "L"})      # sœur -> soeur, not "sur"; Polish ł does not decompose (słowo -> slowo)


# Cyrillic -> the Latin of the existing ru content keys (zhivot, solntse, u_menya, davay_poydyom); a no-op for Latin text
TRANSLIT_RU = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"})


# Arabic -> Latin consonant skeleton for content-key slugs (no short vowels are written): alqraa_walriyada
TRANSLIT_AR = str.maketrans({
    "ا": "a", "أ": "a", "إ": "i", "آ": "a", "ٱ": "a", "ء": "a", "ؤ": "u", "ئ": "i", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh",
    "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a", "غ": "gh", "ف": "f",
    "ق": "q", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "ة": "a", "و": "w", "ي": "y", "ى": "a"})
AR_MARKS = re.compile("[\u064b-\u065f\u0670\u0640]")

# Devanagari -> the Latin of the existing hi content keys (mujhe_sir_dard_hai, main_theek_nahin_hoon): consonant + inherent a,
# matras, anusvara/chandrabindu as n, final and medial schwa dropped.  Keys only; no learner-facing text is transliterated.
_HI_CONS = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny", "ट": "t", "ठ": "th",
            "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh",
            "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h"}
_HI_NUKTA = {"क": "q", "ख": "kh", "ग": "g", "ज": "z", "फ": "f", "ड": "r", "ढ": "rh"}
_HI_VOW = {"अ": "a", "आ": "a", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o"}
_HI_MATRA = {"ा": "a", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e"}


def translit_hi_word(w: str) -> str:
    units: list[list] = []          # [text, kind]  kind: C (consonant + inherent a), c (bare consonant), V (vowel)
    i = 0
    while i < len(w):
        ch = w[i]
        if ch in _HI_CONS:
            c = _HI_CONS[ch]
            if i + 1 < len(w) and w[i + 1] == "\u093c":
                c = _HI_NUKTA.get(ch, c)
                i += 1
            units.append([c, "C"])
        elif ch in _HI_MATRA and units:
            units[-1][1] = "c"
            units.append([_HI_MATRA[ch], "V"])
        elif ch == "\u094d" and units:          # virama: no inherent vowel
            units[-1][1] = "c"
        elif ch in "\u0901\u0902\u0903":
            units.append(["h" if ch == "\u0903" else "n", "N"])
        elif ch in _HI_VOW:
            units.append([_HI_VOW[ch], "V"])
        i += 1
    out = []
    for j, (t, k) in enumerate(units):
        if k == "C":
            last = j == len(units) - 1 or all(u[1] == "N" for u in units[j + 1:])
            nxt_c = j + 1 < len(units) and units[j + 1][1] in "Cc"
            after_c = j + 2 < len(units) and units[j + 2][1] in "CV" or (j + 2 < len(units) and units[j + 1][1] == "c")
            prev_v = j > 0 and units[j - 1][1] in "VN" or (j > 0 and units[j - 1][1] == "C")
            if last or (j > 0 and nxt_c and after_c and prev_v and units[j - 1][1] != "c"):
                out.append(t)
                continue
            out.append(t + "a")
        else:
            out.append(t)
    return "".join(out)


def translit_hi(s: str) -> str:
    return " ".join(translit_hi_word(w) if re.search(r"[\u0900-\u097f]", w) else w for w in s.split())


def slug(s: str, words: int = 4, translit: bool = False) -> str:
    if translit:
        s = s.translate(TRANSLIT_DE)
    if re.search(r"[\u0900-\u097f]", s):
        s = translit_hi(s.replace("।", " "))
    if re.search(r"[\u0400-\u04ff]", s):
        s = s.lower().translate(TRANSLIT_RU)
    if re.search(r"[\u0600-\u06ff]", s):
        s = AR_MARKS.sub("", s).translate(TRANSLIT_AR)
    s = unicodedata.normalize("NFKD", s.translate(TRANSLIT_LIG)).encode("ascii", "ignore").decode()
    parts = re.findall(r"[a-z0-9]+", s.lower())[:words]
    return "_".join(parts)[:36] or "x"


def atom_id(text: str) -> str:
    return "a_" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:7]


def shuffled(tiles: list[str]) -> list[str]:
    """Deterministic scramble that never equals the answer order."""
    out = sorted(tiles, key=lambda t: hashlib.sha1((t + str(tiles.index(t))).encode()).hexdigest())
    if out == tiles and len(set(tiles)) > 1:
        out = tiles[1:] + tiles[:1]
    return out


def register_of(text: str, src: str) -> str | None:
    cfg = CFG.get(src)
    if not cfg:
        return None
    low = text if cfg.get("case_sensitive") else text.casefold()
    f = bool(re.search(cfg["formal"], low))
    i = bool(re.search(cfg["informal"], low))
    return "formal" if f and not i else "informal" if i and not f else None


AGENT_UMLAUT = {"Arzt": "Ärztin", "Koch": "Köchin", "Anwalt": "Anwältin"}
AGENT_UNDO = {v: k for k, v in AGENT_UMLAUT.items()}
AGENT_RE = re.compile(r"\b(Ich bin|bin ich)\s+(?:(ein|eine)\s+)?([A-ZÄÖÜ][\wäöüß]+)")


def agent_gender_alt(text: str) -> str | None:
    """German 'Ich bin Student' -> 'Ich bin Studentin' (and back); None when the noun is not an agent noun."""
    m = AGENT_RE.search(text)
    if not m:
        return None
    art, noun = m.group(2), m.group(3)
    if noun in AGENT_UNDO:
        other = AGENT_UNDO[noun]
    elif noun.endswith("in") and len(noun) > 5 and noun[:-2].endswith(("er", "ent", "ist", "or", "eur", "ler", "ner", "ger", "ter")):
        other = noun[:-2]
    elif noun.endswith(("er", "ent", "ist", "or", "eur", "arzt", "Arzt")) and len(noun) > 4:
        other = AGENT_UMLAUT.get(noun, noun + "in")
    else:
        return None
    new_art = {"ein": "eine", "eine": "ein"}.get(art, art)
    head = text[:m.start(2) if art else m.start(3)]
    return head + (new_art + " " if art else "") + other + text[m.end():]


def yaml_strings(o):
    """Every string value (never a mapping key) of a loaded YAML document."""
    if isinstance(o, dict):
        for v in o.values():
            yield from yaml_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from yaml_strings(v)
    elif isinstance(o, str):
        yield o


# --- French: speaker-gendered words -----------------------------------------------------------------------
FR_COPULA = re.compile(r"\b(?:je suis|je me sens|j'étais|je me suis|moi aussi,? je suis)\s+"
                       r"(?:(?:très|trop|assez|un peu|vraiment|tout à fait|bien|déjà|souvent|toujours|pas|jamais|aussi|si|plutôt|complètement)\s+)*"
                       r"(?:(un|une)\s+)?([a-zàâçéèêëîïôûùüÿœ]{4,})", re.I)
FR_NOT_GENDERED = frozenset((
    "dans chez avec sans pour vers près loin ici là-bas bien très trop assez peu plus moins aussi déjà encore souvent toujours jamais "
    "debout ensemble seul? ouvert? tard tôt demain hier maintenant aujourd comme dessus dessous devant derrière entre parmi depuis "
    "malade triste jeune calme timide rapide riche pauvre simple sympathique timide drôle fort optimiste pessimiste sociable "
    "stressé? libre propre agréable difficile facile possible mince célèbre mauvais gentil? "
    "ensuite alors aussi arrivé? "
).replace("?", "").split()) - {"stressé", "seul", "ouvert", "gentil", "arrivé"}
FR_F2M = (("trice", ("teur",)), ("euse", ("eux", "eur")), ("ière", ("ier",)), ("ère", ("er",)), ("ive", ("if",)), ("ienne", ("ien",)),
          ("onne", ("on",)), ("elle", ("el",)), ("ée", ("é",)), ("ie", ("i",)), ("ue", ("u",)), ("nte", ("nt",)), ("nde", ("nd",)),
          ("rde", ("rd",)), ("tte", ("t",)), ("ite", ("it",)), ("ine", ("in",)), ("aine", ("ain",)), ("ise", ("is",)), ("sse", ("s",)))
FR_M2F = (("eux", ("euse",)), ("eur", ("euse", "rice")), ("ier", ("ière",)), ("er", ("ère",)), ("if", ("ive",)), ("ien", ("ienne",)),
          ("on", ("onne",)), ("el", ("elle",)), ("é", ("ée",)), ("i", ("ie",)), ("u", ("ue",)), ("nt", ("nte",)), ("nd", ("nde",)),
          ("rd", ("rde",)), ("in", ("ine",)), ("ain", ("aine",)), ("s", ("se", "sse")), ("t", ("te", "tte")), ("l", ("le",)),
          ("d", ("de",)), ("n", ("ne",)), ("r", ("re",)), ("m", ("me",)), ("p", ("pe",)), ("g", ("gue",)), ("c", ("che", "que")),
          ("x", ("se",)))
FR_FEM_ONLY = ("ée", "euse", "ière", "ère", "ive", "ienne", "onne", "trice", "nte", "nde", "rde", "tte", "ite", "aine")


def fr_gender_alts(text: str) -> list[str]:
    """French 'Je suis fatigué.' -> ['Je suis fatiguée.'] (and back): candidate alternates (a noun/adjective can have two spellings)."""
    m = FR_COPULA.search(text)
    if not m:
        return []
    art, w = m.group(1), m.group(2)
    lw = w.lower()
    if lw in FR_NOT_GENDERED or lw.endswith(("ment", "tion", "sion")) or lw in ("sûr", "tout", "toute", "fois", "moi", "toi", "lui", "elle", "nous", "vous"):
        return []
    cands: list[str] = []
    if lw.endswith(FR_FEM_ONLY) or lw.endswith(("ie", "ue")) and len(lw) > 4:
        for suf, reps in FR_F2M:
            if lw.endswith(suf) and len(lw) - len(suf) >= 2:
                cands = [lw[:-len(suf)] + r for r in reps]
                break
    elif not lw.endswith("e"):
        for suf, reps in FR_M2F:
            if lw.endswith(suf) and len(lw) - len(suf) >= 2:
                cands = [lw[:-len(suf)] + r for r in reps]
                break
    out = []
    for c in cands:
        c = c.capitalize() if w[:1].isupper() else c
        head = text[:m.start(2)]
        if art:
            flipped = "une" if art.lower() == "un" else "un"
            head = text[:m.start(1)] + (flipped.capitalize() if art[:1].isupper() else flipped) + text[m.end(1):m.start(2)]
        out.append(head + c + text[m.end(2):])
    return out


# --- Polish: speaker-gendered words ------------------------------------------------------------------------
PL_COPULA = re.compile(
    r"\b(jestem|jesteś|czuję się|czujesz się|byłem|byłam|byłeś|byłaś|czułem się|czułam się|czułeś się|czułaś się)"
    r"((?:\s+(?:bardzo|trochę|dość|zbyt|już|też|także|naprawdę|całkiem|raczej|nie|zawsze|często|teraz|dziś|dzisiaj|strasznie|dosyć|jeszcze))*)"
    r"\s+([^\W\d_]{4,})", re.I)
PL_PAST = re.compile(r"\b([^\W\d_]+?)(łem|łam|łeś|łaś|łbym|łabym|łbyś|łabyś)\b", re.I)
PL_PAST_M2F = {"łem": "łam", "łeś": "łaś", "łbym": "łabym", "łbyś": "łabyś"}
PL_PAST_F2M = {v: k for k, v in PL_PAST_M2F.items()}
PL_PAST_IRREG = {"poszedł": "poszł", "przyszedł": "przyszł", "wyszedł": "wyszł", "doszedł": "doszł", "wszedł": "weszł", "zszedł": "zeszł", "odszedł": "odeszł",
                 "przeszedł": "przeszł", "poszła": "poszedł"}
PL_AGENT = {"studentem": "studentką", "uczniem": "uczennicą", "lekarzem": "lekarką", "nauczycielem": "nauczycielką", "kelnerem": "kelnerką",
            "fryzjerem": "fryzjerką", "kucharzem": "kucharką", "pielęgniarzem": "pielęgniarką", "aktorem": "aktorką", "pracownikiem": "pracownicą",
            "informatykiem": "informatyczką", "sprzedawcą": "sprzedawczynią", "Polakiem": "Polką", "Anglikiem": "Angielką", "Amerykaninem": "Amerykanką",
            "Niemcem": "Niemką", "Francuzem": "Francuzką", "Holendrem": "Holenderką", "Włochem": "Włoszką", "Hiszpanem": "Hiszpanką", "turystą": "turystką",
            "kierowcą": "kierowczynią", "malarzem": "malarką", "kolegą": "koleżanką", "przyjacielem": "przyjaciółką", "inżynierem": "inżynierką",
            "programistą": "programistką", "sprzątaczem": "sprzątaczką", "dentystą": "dentystką", "księgarzem": "księgarką", "piekarzem": "piekarką"}
PL_AGENT.update({v: k for k, v in list(PL_AGENT.items())})
PL_NOT_GENDERED = frozenset("tutaj teraz blisko daleko razem przy obok koło dzisiaj wtedy gotów gotowi zawsze często".split())
PL_F2M_STEM = (("zaczę", "zaczą"), ("wzię", "wzią"), ("zaję", "zają"), ("wyję", "wyją"), ("ję", "ją"))


def _keep_case(old: str, new: str) -> str:
    return new[:1].upper() + new[1:] if old[:1].isupper() else new


def pl_adj_flip(w: str) -> str | None:
    lw = w.lower()
    if w[:1].isupper() or lw in PL_NOT_GENDERED or len(lw) < 4:
        return None
    if lw.endswith("y"):
        return w[:-1] + "a"
    if lw.endswith("i"):
        return (w[:-1] + "a") if lw[-2] in "kg" else (w + "a")
    if lw.endswith("ia"):
        return w[:-1]
    if lw.endswith("a") and lw[-2] in "nłtwrkgdzbcmspj":
        return w[:-1] + ("i" if lw[-2] in "kg" else "y")
    return None


def pl_gender_alts(text: str) -> list[str]:
    """Polish 'Jestem zmęczony.' / 'Byłem w domu.' -> the other gender, every speaker-gendered word flipped together (None when there is none)."""
    out = text
    changed = False

    def cop(m):
        nonlocal changed
        new = pl_adj_flip(m.group(3))
        if new is None and m.group(3) in PL_AGENT:
            new = PL_AGENT[m.group(3)]
        if new is None and m.group(3).lower() in PL_AGENT:
            new = PL_AGENT[m.group(3).lower()]
        if new is None:
            return m.group(0)
        changed = True
        return m.group(0)[:m.start(3) - m.start(0)] + new
    out = PL_COPULA.sub(cop, out)

    def past(m):
        nonlocal changed
        stem, end = m.group(1), m.group(2).lower()
        lw = (stem + end).lower()
        if lw in ("chciałem",) and False:
            return m.group(0)
        if end in PL_PAST_M2F:
            new_end = PL_PAST_M2F[end]
            new_stem = stem
            full_m = (stem + "ł").lower()
            if full_m in PL_PAST_IRREG:
                new_stem = PL_PAST_IRREG[full_m][:-1]
            elif stem.endswith("ą"):
                new_stem = stem[:-1] + "ę"
        else:
            new_end = PL_PAST_F2M[end]
            new_stem = stem
            full_f = stem.lower() + "ł"
            irregular = {"poszł": "poszedł", "przyszł": "przyszedł", "wyszł": "wyszedł", "doszł": "doszedł", "weszł": "wszedł", "zeszł": "zszedł", "odeszł": "odszedł", "przeszł": "przeszedł"}
            if full_f in irregular:
                new_stem = irregular[full_f][:-1]
            else:
                for a, b in PL_F2M_STEM:
                    if stem.lower().endswith(a):
                        new_stem = stem[:-len(a)] + b
                        break
        changed = True
        return _keep_case(m.group(0), new_stem + new_end)
    out = PL_PAST.sub(past, out)
    return [out] if changed and out != text else []
# --- Russian: speaker-gendered words ------------------------------------------------------------------------
RU_ADV = frozenset("не ни уже тоже также очень всегда часто иногда редко потом сегодня вчера завтра сейчас там здесь тут ещё еще никогда просто почти совсем только "
                   "сам сама а и но да вот же вообще обычно утром вечером днём днем ночью".split())
RU_NOT_VERB = frozenset("стол пол угол осёл козёл орёл ствол котёл посол сокол школа скала пила игла метла мгла смола мало мол ил футбол вокзал зал канал".split())
RU_IRREG_M2F = {"мог": "могла", "смог": "смогла", "помог": "помогла", "лёг": "легла", "лег": "легла", "вёз": "везла", "нёс": "несла", "умер": "умерла",
                "шёл": "шла", "шел": "шла", "пошёл": "пошла", "пошел": "пошла", "ушёл": "ушла", "ушел": "ушла", "пришёл": "пришла", "пришел": "пришла",
                "нашёл": "нашла", "нашел": "нашла", "зашёл": "зашла", "зашел": "зашла", "вошёл": "вошла", "вошел": "вошла", "вышел": "вышла",
                "перешёл": "перешла", "перешел": "перешла", "дошёл": "дошла", "дошел": "дошла", "прошёл": "прошла", "прошел": "прошла"}
RU_IRREG_F2M = {}
for _m, _f in RU_IRREG_M2F.items():
    RU_IRREG_F2M.setdefault(_f, _m)
RU_IRREG_F2M.update({"шла": "шёл", "пошла": "пошёл", "ушла": "ушёл", "пришла": "пришёл", "нашла": "нашёл", "зашла": "зашёл", "вошла": "вошёл",
                     "перешла": "перешёл", "дошла": "дошёл", "прошла": "прошёл", "легла": "лёг"})
# short adjectives and agent nouns (masculine <-> feminine); the first listed spelling of a form is the one produced
RU_PAIRS_M2F = {
    "рад": "рада", "готов": "готова", "должен": "должна", "занят": "занята", "болен": "больна", "голоден": "голодна", "согласен": "согласна",
    "свободен": "свободна", "уверен": "уверена", "прав": "права", "один": "одна", "доволен": "довольна", "виноват": "виновата",
    "благодарен": "благодарна", "сыт": "сыта", "здоров": "здорова", "женат": "замужем", "жив": "жива", "вынужден": "вынуждена",
    "студент": "студентка", "учитель": "учительница", "актёр": "актриса", "актер": "актриса", "официант": "официантка",
    "продавец": "продавщица", "переводчик": "переводчица", "певец": "певица", "художник": "художница", "писатель": "писательница",
    "танцор": "танцовщица", "пенсионер": "пенсионерка", "школьник": "школьница", "турист": "туристка", "повар": "повариха",
    "секретарь": "секретарша", "директор": "директорша", "кассир": "кассирша", "медбрат": "медсестра", "программист": "программистка",
    "журналист": "журналистка", "музыкант": "музыкантка", "водитель": "водительница", "администратор": "администраторша",
    "иностранец": "иностранка", "москвич": "москвичка", "англичанин": "англичанка", "американец": "американка", "русский": "русская",
}
RU_PAIRS_F2M = {f: m for m, f in reversed(list(RU_PAIRS_M2F.items()))}
RU_PAIRS_F2M.update({"замужем": "женат", "актриса": "актёр"})


def _ru_case(w: str, new: str) -> str:
    return new[:1].upper() + new[1:] if w[:1].isupper() else new


def ru_gender_alts(text: str) -> list[str]:
    """Russian 'Я устал.' -> ['Я устала.'] (and back): the other gender of every speaker-gendered word that follows я
    (past-tense verb, short adjective, agent noun; adverbs and не in between are skipped)."""
    parts, last = [], 0
    for sm in re.finditer(r"[^.!?\n]+", text):
        sent = sm.group(0)
        words = list(re.finditer(r"[\w'-]+", sent))
        low = [w.group(0).casefold() for w in words]
        if "я" not in low:
            continue
        new = sent
        changed = False
        # walk right to left so earlier offsets stay valid
        repl = []
        i = low.index("я") + 1
        while i < len(words):
            w = low[i]
            if w in RU_ADV:
                i += 1
                continue
            other = None
            if w in RU_NOT_VERB:
                pass
            elif w in RU_IRREG_M2F:
                other = RU_IRREG_M2F[w]
            elif w in RU_IRREG_F2M:
                other = RU_IRREG_F2M[w]
            elif w in RU_PAIRS_M2F:
                other = RU_PAIRS_M2F[w]
            elif w in RU_PAIRS_F2M:
                other = RU_PAIRS_F2M[w]
            elif w.endswith("лся") and len(w) > 4:
                other = w[:-3] + "лась"
            elif w.endswith("лась") and len(w) > 5:
                other = w[:-4] + "лся"
            elif w.endswith("л") and len(w) >= 3 and w[-2] in "аеиоуыяёю":
                other = w + "а"
            elif w.endswith("ла") and len(w) >= 4 and w[-3] in "аеиоуыяёю":
                other = w[:-1]
            if other:
                repl.append((words[i].start(), words[i].end(), _ru_case(words[i].group(0), other)))
                changed = True
                # a coordinated past-tense verb later in the sentence (купил хлеб и пошёл домой) flips with it
                for j in range(i + 1, len(words)):
                    wj = low[j]
                    if wj in RU_NOT_VERB:
                        continue
                    o2 = RU_IRREG_M2F.get(wj) or RU_IRREG_F2M.get(wj)
                    if not o2 and wj.endswith("лся") and len(wj) > 4:
                        o2 = wj[:-3] + "лась"
                    elif not o2 and wj.endswith("лась") and len(wj) > 5:
                        o2 = wj[:-4] + "лся"
                    elif not o2 and wj.endswith("л") and len(wj) >= 4 and wj[-2] in "аеиоуыяёю":
                        o2 = wj + "а"
                    elif not o2 and wj.endswith("ла") and len(wj) >= 5 and wj[-3] in "аеиоуыяёю":
                        o2 = wj[:-1]
                    if o2:
                        repl.append((words[j].start(), words[j].end(), _ru_case(words[j].group(0), o2)))
                break
            break
        if changed:
            for a, b, r in reversed(repl):
                new = new[:a] + r + new[b:]
            parts.append(text[last:sm.start()] + new)
            last = sm.end()
    return ["".join(parts) + text[last:]] if parts else []


RU_YO_SAME = frozenset(("все", "всё", "ее", "её", "нем", "нём", "узнает", "дает"))        # real minimal pairs / not worth flagging


def yo_fold(s: str) -> str:
    return s.replace("ё", "е").replace("Ё", "Е")


# obligatory elision: je le la de ne me te se que ce (+ jusque, lorsque ...) before a vowel / mute h; exceptions are h aspiré words and onze/oui/yaourt
FR_ELIDE = re.compile(
    r"(?<![\w'’-])(je|le|la|de|ne|me|te|se|que|ce|jusque|lorsque|puisque|quoique|si(?= ils?\b))\s+"
    r"(?=(?:[aeiouyâàéèêëîïôöûùüœæ]|h(?![ao]ut|aricot|ockey|uit|amburger|éros|asard|onte|ibou|érisson|andball|all\b|anche|angar|omard|arpe"
    r"|ollande|ongr|ameau|asch|ors|asard|ussard|ublot|ache\b|aut))[\w'’-]*)", re.I)
FR_ELIDE_OK = frozenset(("onze", "onzième", "oui", "ouistiti", "yaourt", "yaourts", "yoga", "yéti", "yen", "ukulélé", "un?", ""))


def fr_elision_errors(text: str) -> list[str]:
    out = []
    for m in FR_ELIDE.finditer(text):
        nxt = re.match(r"[\w'’-]+", text[m.end():])
        word = nxt.group(0).lower() if nxt else ""
        if word in FR_ELIDE_OK and word:
            continue
        if m.group(1).lower() in ("le", "la") and word in ("y", "yacht"):
            continue
        out.append(f"{m.group(1)} {word}")
    return out


# --- Arabic: speaker / addressee gender, dual, clitics, article, script -----------------------------------------
# The A1 text is unvocalised, so only a few forms differ in writing between a man and a woman: predicate adjectives and agent nouns (متعب / متعبة),
# 2nd-person present verbs (تشرب / تشربين) and imperatives (اشرب / اشربي). 1st-person verbs and the pronouns أنا / أنت / ـك are the same for both.
AR_ADV = frozenset("جدا جدًا دائما غالبا احيانا أحيانا كثيرا قليلا الآن اليوم اليوم هنا هناك أيضا ايضا فعلا حقا لا ليس لست لستَ ما مازال ما زال ربما فقط تماما بالفعل كان كنت".split())
AR_PRED_M = frozenset((
    "متعب مريض جائع عطشان سعيد حزين غاضب مشغول جاهز مسرور خائف قلق متحمس متوتر مرتاح مرهق نشيط كسول مرتبك حر فرحان زعلان مستعد ممتن"
    " متأخر مبكر موجود متزوج أعزب غني فقير طويل قصير نحيف سمين شاب كبير صغير جديد قديم ذكي لطيف هادئ اجتماعي خجول كريم مهذب صبور"
    " طالب معلم مدرس مهندس طبيب ممرض موظف بائع طباخ طاه سائق محاسب مدير ممثل مغني كاتب صحفي مصور رسام لاعب سباح مبرمج مترجم موسيقي"
    " عامل صيدلي نجار خباز حلاق ممرض مزارع شرطي جندي مدرب مرشد سائح زائر ضيف جار صديق مبتدئ متعلم ناجح مسافر مقيم مواطن أجنبي"
    " مصري لبناني سوري عراقي أردني مغربي فلسطيني سعودي تونسي جزائري عربي هولندي أمريكي إنجليزي فرنسي ألماني إيطالي إسباني").split())
AR_PRED_F_IRREG = {"حر": "حرة", "شاب": "شابة", "طاه": "طاهية", "جار": "جارة", "صديق": "صديقة", "ضيف": "ضيفة", "زائر": "زائرة", "عامل": "عاملة",
                   "فرحان": "فرحانة", "عطشان": "عطشانة", "زعلان": "زعلانة"}
AR_FLIP_M2F = {m: AR_PRED_F_IRREG.get(m, m + "ة") for m in AR_PRED_M}
AR_FLIP_F2M = {f: m for m, f in AR_FLIP_M2F.items()}
AR_NISBA_NOT = frozenset("هادئ".split())
# 2nd person: masculine imperative -> feminine (strip nothing, add ي); irregular ones listed
AR_IMP_M2F = {w: w + "ي" for w in (
    "اشرب استرح اجلس افتح اكتب اقرأ انتظر ادخل اذهب استمع اسمع تحدث ساعد اتصل انظر اترك اختر ارجع اسأل أجب جرب خذ تفضل اصعد انزل امش اركب"
    " اشتر ادفع اطلب ابحث اعمل ارتح تعال تأكد تذكر سامح سامحني اعذرني افعل اترك أعد صل اختم اغسل البس ارتد انتبه قف اخرج ابدأ ابق قم").split()}
AR_IMP_M2F.update({"قل": "قولي", "خذ": "خذي", "تعال": "تعالي", "ضع": "ضعي", "قف": "قفي", "قم": "قومي", "عد": "عودي", "صل": "صلي"})
AR_IMP_F2M = {f: m for m, f in AR_IMP_M2F.items()}
AR_NOT_2F = frozenset("تين تمرين تأمين تسعين تعيين تدوين تلوين تحسين تمارين تكوين تسمين تخمين تهجين ثلاثين عشرين ثمانين سبعين ستين خمسين أربعين تحيين".split())
AR_Q_START = frozenset("هل ماذا متى أين كيف لماذا ما كم من لا لن لم".split())
AR_FEM_3 = frozenset("هي".split())
AR_SUN = "تثدذرزسشصضطظنل"


def _ar_words(sent: str):
    return list(re.finditer(r"[\u0621-\u064a\u0671]+", sent))


def ar_gender_alts(text: str) -> list[str]:
    """Arabic gender alternates: after أنا / أنت a predicate adjective or agent noun, a 2nd-person present verb (تريد <-> تريدين)
    and an imperative (اشرب <-> اشربي). Returns ['<text with every gendered word flipped>'] or []."""
    parts, last = [], 0
    for sm in re.finditer(r"[^.!؟?\n]+", text):
        sent = sm.group(0)
        words = _ar_words(sent)
        low = [w.group(0) for w in words]
        repl: list[tuple[int, int, str]] = []
        for i, w in enumerate(low):
            base = w[1:] if w[:1] in "وف" and len(w) > 3 and w[1:] in (AR_IMP_M2F | AR_IMP_F2M) else w
            off = len(w) - len(base)
            # predicate after أنا / أنت
            if w in ("انا", "أنا", "انت", "أنت", "وأنا", "وأنت", "فأنا", "فأنت") or (w in ("وانا", "وانت")):
                j = i + 1
                while j < len(low) and low[j] in AR_ADV:
                    j += 1
                if j < len(low):
                    x = low[j]
                    o = AR_FLIP_M2F.get(x) or AR_FLIP_F2M.get(x)
                    if o is None and x.endswith("ة") and len(x) > 3 and x[:-1] in AR_FLIP_M2F:
                        o = x[:-1]
                    if o:
                        repl.append((words[j].start(), words[j].end(), o))
                        # a coordinated predicate (متعب وجائع) flips with it
                        if j + 1 < len(low) and low[j + 1][:1] == "و" and low[j + 1][1:] in (AR_FLIP_M2F | AR_FLIP_F2M):
                            y = low[j + 1][1:]
                            repl.append((words[j + 1].start(), words[j + 1].end(), "و" + (AR_FLIP_M2F.get(y) or AR_FLIP_F2M.get(y))))
                continue
            # imperative at the start of a sentence / clause
            if base in AR_IMP_M2F or base in AR_IMP_F2M:
                if i == 0 or (low[i - 1] in ("ثم", "و", "ف", "يا") or i == 1 and low[0] in ("من", "لو")) :
                    o = AR_IMP_M2F.get(base) or AR_IMP_F2M.get(base)
                    repl.append((words[i].start() + off, words[i].end(), o))
                    continue
            # 2nd-person present verb
            fem_sent = any(x in AR_FEM_3 for x in low)
            if len(w) >= 5 and w[0] == "ت" and w.endswith("ين") and w not in AR_NOT_2F and not fem_sent and not w.endswith("تين"):
                repl.append((words[i].start(), words[i].end(), w[:-2]))
            elif (len(w) >= 3 and w[0] == "ت" and not w.endswith(("ين", "ون", "ان", "ة", "ا")) and not fem_sent
                  and (i == 0 and w[:2] != "تا" or (i > 0 and (low[i - 1] in AR_Q_START or low[i - 1] in ("انت", "أنت", "هل", "لا", "لن", "لم", "ماذا"))))
                  and w not in ("تلفاز", "تذكرة", "تفاح", "تاريخ", "تمر", "تين", "تعب", "تحت", "تلك", "تشرفنا", "تفضلي")):
                repl.append((words[i].start(), words[i].end(), w + ("ين" if not w.endswith("ي") else "ن")))
        if repl:
            new = sent
            for a, b, r in sorted(repl, reverse=True):
                new = new[:a] + r + new[b:]
            parts.append(text[last:sm.start()] + new)
            last = sm.end()
    return ["".join(parts) + text[last:]] if parts else []


# --- Hindi: speaker-gendered words ---------------------------------------------------------------------------
HI_STOP = frozenset("तुम आप वह वो वे हम ये यह लोग".split())
HI_AUX = frozenset("हूँ हूं था थी".split())
HI_M2F = {"था": "थी", "गया": "गई", "आया": "आई", "हुआ": "हुई", "रहा": "रही", "सोया": "सोई", "चला": "चली", "उठा": "उठी", "बैठा": "बैठी",
          "पहुँचा": "पहुँची", "पहुंचा": "पहुंची", "लौटा": "लौटी", "निकला": "निकली", "थका": "थकी", "अकेला": "अकेली", "भूखा": "भूखी", "प्यासा": "प्यासी",
          "अच्छा": "अच्छी", "खड़ा": "खड़ी", "बड़ा": "बड़ी", "छोटा": "छोटी", "पतला": "पतली", "मोटा": "मोटी", "लंबा": "लंबी", "बूढ़ा": "बूढ़ी",
          "दुबला": "दुबली", "वाला": "वाली", "नया": "नई", "जागा": "जागी", "मुड़ा": "मुड़ी", "रुका": "रुकी", "फँसा": "फँसी", "भीगा": "भीगी",
          "छात्र": "छात्रा", "शिक्षक": "शिक्षिका", "अध्यापक": "अध्यापिका", "लेखक": "लेखिका", "गायक": "गायिका", "पाठक": "पाठिका",
          "अभिनेता": "अभिनेत्री", "नर्तक": "नर्तकी", "कलाकार": "कलाकार", "ग्वाला": "ग्वालिन", "दर्जी": "दर्जी", "सेवक": "सेविका"}
HI_M2F = {m: f for m, f in HI_M2F.items() if m != f and m not in ("कलाकार", "दर्जी")}
HI_F2M = {f: m for m, f in reversed(list(HI_M2F.items()))}
HI_NOT_VERB = frozenset("रास्ता पता सस्ता नाश्ता रिश्ता फ़रिश्ता देवता माता पिता नेता दाता सजा खाता".split())


def hi_flip(w: str, nxt: str | None) -> str | None:
    """The other-gender spelling of one word that follows मैं, or None."""
    if w in HI_M2F:
        return HI_M2F[w]
    if w in HI_F2M:
        return HI_F2M[w]
    if w in HI_NOT_VERB:
        return None
    if len(w) >= 3 and nxt is not None and (nxt in HI_AUX or nxt.endswith(("रहता", "रहती"))):
        if w.endswith("ता"):
            return w[:-2] + "ती"
        if w.endswith("ती"):
            return w[:-2] + "ता"
    if len(w) >= 4 and w.endswith(("ूँगा", "ूंगा", "ऊँगा", "ऊंगा")):
        return w[:-1] + "ी"
    if len(w) >= 4 and w.endswith(("ूँगी", "ूंगी", "ऊँगी", "ऊंगी")):
        return w[:-1] + "ा"
    return None


def hi_gender_alts(text: str) -> list[str]:
    """Hindi 'मैं रोज़ स्कूल जाता हूँ।' -> ['मैं रोज़ स्कूल जाती हूँ।'] (and back): every gendered word that follows मैं in the sentence
    (ergative मैंने is not subject-gendered and is not matched; another subject pronoun ends the span)."""
    parts, last = [], 0
    for sm in re.finditer(r"[^।.!?\n]+", text):
        sent = sm.group(0)
        words = list(re.finditer(rf"[\w{DEV}]+", sent))
        low = [w.group(0) for w in words]
        if "मैं" not in low:
            continue
        i0 = low.index("मैं")
        repl = []
        for i in range(i0 + 1, len(words)):
            if low[i] in HI_STOP or low[i] == "मैं":
                break
            o = hi_flip(low[i], low[i + 1] if i + 1 < len(low) else None)
            if o:
                repl.append((words[i].start(), words[i].end(), o))
        if repl:
            new = sent
            for a, b, r in reversed(repl):
                new = new[:a] + r + new[b:]
            parts.append(text[last:sm.start()] + new)
            last = sm.end()
    return ["".join(parts) + text[last:]] if parts else []


AR_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})


def ar_fold(s: str) -> str:
    """Spelling-variant key: harakat removed; alef-hamza forms, alef maqsura / yeh, teh marbuta / heh, hamza on waw / yeh folded."""
    return AR_MARKS.sub("", s).translate(AR_FOLD)


AR_PERSIAN = re.compile("[\u06cc\u06a9\u067e\u0686\u06af\u0698\u06a4\u06be\u06c1]")
AR_DUAL_NUM = re.compile(r"(?<![\w])(?:اثنان|اثنين|اثنتان|اثنتين|إثنان|إثنين)\s+(?!و|من|في|فقط|بالضبط|ف)([\u0621-\u064a]+)")
SUN_LATIN = re.compile(r"\bal-(sh|th|dh|[stdrznṣḍṭẓ])(?=[a-zāīūʿʾḥṣḍṭẓ])")      # lowercase only: a capitalised Al-Saeed is a proper name


def ar_sun_errors(s: str) -> list[str]:
    """English text transliterates Arabic: the article assimilates to a sun letter (ash-shams, ar-raʾs), never al-shams."""
    return [m.group(0) + "…" for m in SUN_LATIN.finditer(s) if m.group(1) != "l"]


def hi_fold(s: str) -> str:
    """Spelling variants the grader folds (chandrabindu -> anusvara, nukta of क ख ग ज फ) - used to find one word written two ways."""
    s = s.replace("\u0901", "\u0902")
    return re.sub("([\u0915\u0916\u0917\u091c\u092b])\u093c", r"\1", s)


# --- Romanian: speaker-gendered words and orthography -----------------------------------------------------
RO_COPULA = re.compile(r"\b(?:sunt|eram|nu sunt|mă simt|nu mă simt|mă simțeam|m-am simțit|mă simt la fel de)\s+"
                       r"(?:(?:foarte|prea|destul de|puțin|tot|deja|mereu|întotdeauna|așa|chiar|și eu|mai|încă|niciodată|nu|puțin)\s+)*"
                       r"(?:(un|o)\s+)?([a-zăâîșț]{4,})", re.I)
RO_NOT_GENDERED = frozenset("acasă aici acolo bine rău destul foarte mereu prea gata mare verde liniștit? aproape departe între lângă dintr la din cu pentru despre "
                            "sus jos afară înăuntru ocupat? singur? sigur? pe în de lângă după înainte acord vreme liber? tare gri bej maro roz cuminte "
                            "fericit? trist? tânăr? ".replace("?", "").split()) - {"singur", "sigur", "ocupat", "liber", "liniștit", "fericit", "trist", "tânăr"}
RO_VOWEL_END = ("a", "e", "i", "o", "u", "â", "î")


def ro_gender_alts(text: str) -> list[str]:
    """Romanian 'Sunt obosit.' -> ['Sunt obosită.'] (and back); [] when the word is not speaker-gendered."""
    m = RO_COPULA.search(text)
    if not m:
        return []
    art, w = m.group(1), m.group(2)
    lw = w.lower()
    if lw in RO_NOT_GENDERED or lw.endswith(("ment", "ție", "ință", "ime")):
        return []
    cands: list[str] = []
    if lw.endswith("ă") and len(lw) > 4:
        base = lw[:-1]
        if lw.endswith("oasă"):
            cands = [lw[:-4] + "os"]
        elif lw.endswith("oară"):
            cands = [lw[:-4] + "or"]
        else:
            cands = [base]
    elif lw.endswith("oare"):
        cands = [lw[:-4] + "or"]
    elif not lw.endswith(RO_VOWEL_END):
        if lw.endswith("os"):
            cands = [lw[:-2] + "oasă"]
        elif lw.endswith("or"):
            cands = [lw[:-2] + "oare"] if lw.endswith("tor") else [lw[:-2] + "oară", lw + "ă", lw[:-2] + "oare"]
        else:
            cands = [lw + "ă"]
    else:
        return []
    new_art = {"un": "o", "o": "un", "Un": "O", "O": "Un"}.get(art, art)
    out = []
    for c in cands:
        if w[:1].isupper():
            c = c[:1].upper() + c[1:]
        head = text[:m.start(1)] + new_art + " " if art else text[:m.start(2)]
        out.append(head + c + text[m.end():])
    return out


RO_CEDILLA = re.compile("[\u015f\u015e\u0163\u0162]")
RO_I_INSIDE = re.compile(r"(?<=[^\W\d_])î")
RO_PREFIX_I = re.compile(r"^(?:ne|re|pre|dez|sub|co|supra|extra|contra|anti|prea|auto|bine|rău|mai|semi|inter|multi)î", re.I)


def ro_ortho_errors(text: str) -> list[str]:
    """Comma-below ș ț only; â is never word-initial or word-final, î never word-internal (except after prefixes)."""
    out = []
    if RO_CEDILLA.search(text):
        out.append("cedilla ş/ţ (write comma-below ș/ț)")
    for w in re.findall(r"[^\W\d_]+", text):
        if w[:1] in "âÂ" or w[-1:] in "âÂ":
            out.append(f"{w!r}: â is only written inside a word (î at the start or end)")
        elif RO_I_INSIDE.search(w) and not RO_PREFIX_I.match(w) and "-" not in w:
            out.append(f"{w!r}: î inside a word (write â)")
    return out


class Unresolved(Exception):
    pass


# ---------------------------------------------------------------------------
# One unit
# ---------------------------------------------------------------------------
class UnitDeriver:
    def __init__(self, plan: "Plan", src_stem: str, new_no: int):
        self.p = plan
        self.stem = src_stem                         # a1_unit23_money
        m = re.match(r"^(a1|a2)_unit(\d+)_(.+)$", src_stem)
        if not m:
            raise SystemExit(f"{src_stem}: expected a1_unitNN_name or a2_unitNN_name (A1 and A2 are supported)")
        self.level, self.src_no, self.suffix = m.group(1), int(m.group(2)), m.group(3)
        self.new_no = new_no
        self.new_suffix = plan.suffixes.get(self.suffix, self.suffix)       # --suffixes: file / topic name in the new language
        self.new_stem = f"{self.level}_unit{new_no:02d}_{self.new_suffix}"
        self.real = dd.load(CONTENT / f"realizations/{plan.src}/{src_stem}.yaml")
        self.ovl = dd.load(CONTENT / f"overlays/{plan.src_pair}/{self.level}_unit{self.src_no:02d}.yaml")
        self.keymap: dict[str, str] = {}
        self.atom_texts: dict[str, str] = {}         # exact src text -> atom id (this unit)
        self.atom_norms: dict[str, str] = {}         # norm -> atom id
        self.used_slugs: dict[str, set[str]] = defaultdict(set)
        self.compose: dict[str, tuple[list[str], bool]] = {}
        self.id_text: dict[str, str] = {}
        self.rewrite_cks: set[str] = set()           # grammar_note cards whose explanation is rewritten (title + gloss are authored too)
        self.card_tr: dict[str, str] = {}            # card content key -> translated target text

    def compose_for(self, text: str):
        """([line, ...], strip_speaker) when `text` is built from teaching lines (gaps between lines allowed)."""
        for ln in self.lines:
            m = re.match(r"^[^\W\d_]+:\s+", ln)
            if m and ln[m.end():] == text:
                return [ln], True
        pos, used = 0, []
        for ln in self.lines:
            if text.startswith(ln, pos):
                used.append(ln)
                pos += len(ln)
                while pos < len(text) and text[pos] == " ":
                    pos += 1
                if pos >= len(text):
                    return (used, False) if len(used) > 1 else None
        return None

    # -- registry helpers --------------------------------------------------
    def T(self, text: str, kind: str, en: str | None = None, where: str | None = None) -> str:
        # gloss keys must be single tokens of the card text, so they translate separately
        if kind == "media":
            comps = self.compose_for(text)
            if comps:
                parts = [self.T(c, "teach", None, where) for c in comps[0]]
                joined = " ".join(parts)
                if comps[1]:
                    joined = re.sub(rf"^(?:[^\W\d_]|[{DEV}])+:\s*", "", joined)
                known = self.atom_texts.get(text)
                if known and known.startswith("d_"):
                    return self.p.derived[known]
                if known:                        # already a plain teaching atom: keep it
                    return self.T(text, "teach", None, where)
                aid = "d_" + hashlib.sha1(text.encode()).hexdigest()[:7]
                self.atom_texts[text] = aid
                self.id_text[aid] = text
                self.atom_norms.setdefault(norm(text), aid)
                self.p.derived[aid] = joined
                return joined
        aid = atom_id((("gk\0" + (where + "\0" if self.p.per_card_keys and where else "")) if kind == "gloss-key" else "") + text)
        self.p.add_atom(aid, text, kind, en, where, self.stem)
        if kind != "gloss-key":
            self.id_text[aid] = text
            self.atom_texts[text] = aid
            if kind != "title":                      # titles lose their punctuation; prefer sentence atoms
                self.atom_norms.setdefault(norm(text), aid)
        tr = self.p.tr_atoms.get(aid)
        if kind != "gloss-key" and f"{self.stem}#t#{text}" in self.p.tr_atoms:        # this unit translates a shared word differently
            tr = self.p.tr_atoms[f"{self.stem}#t#{text}"]
        if tr is None:
            self.p.missing.add(aid)
            return f"<<{aid}>>"
        return self.p.names(self.p.speaker_colon(text, tr))

    def gloss_key(self, ck: str, key: str) -> str:
        """Gloss keys are shared atoms; "<source content_key>#gk#<source key>" in atoms.tr.json overrides one card."""
        scoped = self.p.tr_atoms.get(f"{ck}#gk#{key}")
        return self.p.names(scoped) if scoped else self.T(key, "gloss-key")

    def T_by_norm(self, text: str) -> str | None:
        aid = self.atom_norms.get(norm(text))
        if aid is None:
            return None
        if aid in self.p.derived:
            return self.p.derived[aid]
        tr = self.p.tr_atoms.get(aid)
        if tr is None:
            self.p.missing.add(aid)
            return f"<<{aid}>>"
        return self.p.names(tr)

    def A(self, slot: str, src: str, kind: str, ctx: dict | None = None, required: bool = True) -> str | None:
        """Authored slot.  Returns the translator's text or a placeholder."""
        self.p.add_author(slot, src, kind, ctx or {}, self.stem)
        v = self.p.tr_author.get(slot)
        if v is None:
            if required:
                self.p.missing.add(slot)
                return f"<<{slot}>>"
            return None
        return self.p.names(v) if re.search(r"#(?:ans|alt|dist|frame|tested|bank)$", slot) else self.p.names_en(v)

    def flag(self, key: str, code: str, msg: str, level: str = "error") -> None:
        self.p.flags.append(dict(id=key, code=code, level=level, msg=msg, unit=self.stem))

    def en(self, s: str, scope: str | None = None) -> str:
        """English text: cast names and language name swapped.  `scope` ("<source content_key>|title", "|gloss",
        "|example_gloss", "|gloss:<source key>") selects a scoped authored rewrite from en_override.json before the
        exact-string one."""
        if scope and scope in self.p.en_over:
            return self.p.names_en(self.p.en_over[scope])
        if s in self.p.en_over:                      # authored English rewrite (en_override.json)
            return self.p.names_en(self.p.en_over[s])
        s = self.p.names_en(s)
        for k, v in self.p.en_over.items():          # "~word": word-level rewrite of source-language words that survive in English text
            if k.startswith("~"):
                s = re.sub(rf"(?<![\w{DEV}]){re.escape(k[1:])}(?![\w{DEV}])", v, s)
        return s.replace(self.p.src_name, self.p.new_name)

    def segment_items(self) -> list[tuple[str, str]]:
        """Sentence-sized pieces of multi-sentence atoms (a sign `Open: negen uur tot vijf uur. Kaartje: acht euro.`), so English feedback that
        quotes one piece is substituted too.  Only when the translation splits into the same number of pieces."""
        if getattr(self, "_segs", None) is not None:
            return self._segs
        segs: dict[str, str] = {}
        eng = self.p.english_words()
        for text in list(self.atom_texts):
            if "\n" in text:
                continue
            parts = re.split(r"(?<=[.!?])\s+", text.strip())
            if len(parts) < 2:
                continue
            aid = self.atom_texts[text]
            tr = self.p.derived.get(aid) or self.p.tr_atoms.get(aid)
            if not tr:
                continue
            tr = self.p.names(tr)
            tparts = re.split(r"(?<=[.!?])\s+", tr.strip())
            if len(tparts) != len(parts):
                continue
            for a, b in zip(parts, tparts):
                words = re.findall(r"[^\W\d_]{3,}", a.casefold())
                if len(a) >= 6 and a not in self.atom_texts and words and not all(w in eng for w in words):
                    segs.setdefault(a, b)
        self._seg_tr = segs
        self._segs = [(a, a) for a in segs]
        return self._segs

    def en_checked(self, s: str, slot: str, kind: str, ctx: dict | None = None) -> str:
        """English text that may quote or discuss the source language.  Quoted atoms are
        substituted; anything still source-language needs authoring.  The substituted target text is masked
        before the residual check, so a cognate in the translation (Tulpen, Party) is not mistaken for a leftover."""
        out = s
        subs: dict[str, str] = {}
        eng = self.p.english_words()
        for text, aid in sorted(list(self.atom_texts.items()) + self.segment_items(), key=lambda kv: -len(kv[0])):
            if len(text) < 3 or text in self.p.names_map:
                continue                              # a cast name in English prose is mapped by names_en, never quoted as target text
            # whole word ("gras" is not inside "grass"); a lowercase source atom also matches its sentence-initial capital ("Boom is tree")
            first = text[0]
            head = f"[{first}{first.upper()}]" if first.islower() else re.escape(first)
            word = rf"(?<![^\W\d_])(?<![{DEV}])" + head + re.escape(text[1:]) + rf"(?![^\W\d_])(?![{DEV}])"
            if not re.search(word, out):
                continue
            quoted_only = all(self.p.is_english(w) for w in re.findall(r"[^\W\d_]{3,}", text.casefold())) and not any(c in text for c in " ,.")
            pat = re.compile((r"(?<=['\"*\u2018\u201c])" if quoted_only else "") + word[len(rf"(?<![^\W\d_])(?<![{DEV}])"):] if quoted_only else word)

            def put(m, text=text):
                ph = f"\x00{len(subs)}\x00"
                tr = self._seg_tr[text] if text not in self.atom_texts else self.T(text, "quote")
                if m.group(0)[:1].isupper() and text[:1].islower() and not tr.startswith("<<"):
                    tr = tr[:1].upper() + tr[1:]
                subs[ph] = tr
                return ph
            out = pat.sub(put, out)
        out = self.en(out)
        left = self.residual(re.sub(r"\x00\d+\x00", " ", out))
        gpat = CFG.get(self.p.src, {}).get("grammar")
        if "*" in s or re.search(r"\bunits?\s+\d+", s, re.I) or left or (gpat and re.search(gpat, out, re.I)):
            return self.A(slot, s, kind, dict(ctx or {}, why=",".join(left) or "italic span / unit cross-reference"))
        for ph, val in subs.items():
            out = out.replace(ph, val)
        return out

    def residual(self, s: str) -> list[str]:
        low = s.casefold()
        toks = set(re.findall(r"[^\W\d_]{3,}", low))
        short = set(CFG.get(self.p.src, {}).get("short", ()))
        toks |= {x for x in re.findall(r"[^\W\d_]{2,}", low) if x in short}
        keep = {k.casefold() for k in self.p.names_map}          # cast and place names are not leftovers
        return sorted((toks & (self.src_only | short)) - keep)

    # -- build ---------------------------------------------------------------
    def prepass(self) -> None:
        """Register every atom first so quoting can be substituted, and compute vocab sets."""
        R, O = self.real, self.ovl
        # media texts that are concatenations / speaker-stripped copies of teaching lines need no translation of their own
        self.lines = [t["target"]["text"] for u in R["units"] for l in u["lessons"] for t in l.get("teaching") or []]
        gl = lambda sect, k, f: ((O.get(sect) or {}).get(k) or {}).get(f)
        for a in R.get("media_assets") or []:
            self.T(a["text"], "media")
        for u in R["units"]:
            self.T(u["title"], "title", gl("units", u["content_key"], "title"))
            for l in u["lessons"]:
                self.T(l["title"], "title", gl("lessons", l["content_key"], "title"))
                for t in l.get("teaching") or []:
                    ck = t["content_key"]
                    en = gl("teaching", ck, "gloss")
                    self.T(t["target"]["text"], "teach", en if isinstance(en, str) else None, ck)
                    if t.get("kind") == "grammar_note" and len(t["target"]["text"].split()) > 8:
                        self.rewrite_cks.add(ck)
                        self.p.atom_ctx[atom_id(t["target"]["text"])]["rewrite"] = (
                            f"grammar explanation written in {self.p.src_name}: REWRITE it for {self.p.new_name} grammar, do not translate")
                        self.flag(ck, "GRAMMAR_REWRITE", "grammar_note card explains source-language grammar; rewrite per language", "warn")
                    exs = t.get("example")
                    exs = [exs] if isinstance(exs, dict) else (exs or [])
                    egl = gl("teaching", ck, "example_gloss")
                    egl = [egl] if isinstance(egl, str) else (egl or [])
                    for i, e in enumerate(exs):
                        self.T(e["text"], "example", egl[i] if i < len(egl) else None, ck)
                    for k, v in (gl("teaching", ck, "glosses") or {}).items():
                        self.T(k, "gloss-key", v, ck)
                for e in l["exercises"]:
                    for b in (e.get("prompt") or {}).get("target_blocks") or []:
                        if b.get("language_code") == self.p.src and BLANK not in b["text"]:
                            self.T(b["text"], "prompt", gl("exercises", e["content_key"], "instruction"), e["content_key"])
        # vocab sets
        srclex = set()
        for text in self.atom_texts:
            srclex |= set(re.findall(r"[^\W\d_]{3,}", text.casefold()))
        srclex = set()
        for text in self.atom_texts:
            srclex |= set(re.findall(r"[^\W\d_]{3,}", text.casefold()))
        # Source-language option sentences that are not atoms of their own (e.g. a correct option that also appears
        # inside a longer teaching line) are still source text: a text is source text when most of its words occur in the
        # source atoms and not in the English strings (instructions, titles, glosses).
        allsrc2: set[str] = set()
        for text in self.atom_texts:
            allsrc2 |= set(re.findall(r"[^\W\d_]{2,}", text.casefold()))
        clean_env: set[str] = set()
        for sect in ("units", "lessons"):
            for v in (O.get(sect) or {}).values():
                clean_env.update(re.findall(r"[^\W\d_]{2,}", str(v.get("title") or "").casefold()))
        for v in (O.get("teaching") or {}).values():
            for f in ("title", "gloss", "example_gloss"):
                x = v.get(f)
                for s in ([x] if isinstance(x, str) else x or []):
                    clean_env.update(re.findall(r"[^\W\d_]{2,}", s.casefold()))
        for v in (O.get("exercises") or {}).values():
            clean_env.update(re.findall(r"[^\W\d_]{2,}", str(v.get("instruction") or "").casefold()))
        short_set = set(CFG.get(self.p.src, {}).get("short", ()))
        eng = self.p.english_words()
        def is_src(s, instruction=""):
            if self.p.src_name in str(instruction) and "English" not in str(instruction):
                return True              # "Choose the Dutch sentence ..." -> the options are Dutch
            names_cf2 = {k.casefold() for k in self.p.names_map}
            toks = [x for x in re.findall(r"[^\W\d_]{2,}", str(s).casefold()) if x not in names_cf2]
            hits = [x for x in toks if x in allsrc2 and ((len(x) >= 3 and x not in eng) or x in short_set)]
            return bool(toks) and len(hits) / len(toks) >= 0.5
        self.is_src = is_src
        env: set[str] = set()
        def add_en(s):
            if isinstance(s, str):
                env.update(re.findall(r"[^\W\d_]{3,}", s.casefold()))
        for sect in ("units", "lessons"):
            for v in (O.get(sect) or {}).values():
                add_en(v.get("title"))
        for v in (O.get("teaching") or {}).values():
            for f in ("title", "gloss", "example_gloss"):
                x = v.get(f)
                for s in ([x] if isinstance(x, str) else x or []):
                    add_en(s)
            for s in (v.get("glosses") or {}).values():
                add_en(s)
        for ck, v in (O.get("exercises") or {}).items():
            add_en(v.get("instruction"))
            co = v.get("correct_option")
            if isinstance(co, str) and (norm(co) in self.atom_norms or is_src(co, v.get("instruction", ""))):
                continue          # source-language options (also word_order answers) are not English vocabulary
            add_en(co)
            for d in v.get("distractors") or []:
                add_en(d)
        for u in R["units"]:
            for l in u["lessons"]:
                for e in l["exercises"]:
                    for b in (e.get("prompt") or {}).get("target_blocks") or []:
                        if b.get("language_code") != self.p.src:
                            add_en(b["text"])

        # Pair sides.  Default: left is source-language text, right is English.  A right side that
        # consists only of source-language words (field -> value pairs) is source text too, and a
        # pair whose right side is a teaching atom and whose left is not is reversed (English left).
        allsrc = set(self.p.src_lexicon)             # inflected forms that occur on a pair side only (leest, luistert) are source text too
        teach_norms = set(self.atom_norms)
        for text in self.atom_texts:
            allsrc |= set(re.findall(r"[^\W\d_]{2,}", text.casefold()))
        names_cf = {k.casefold() for k in self.p.names_map}
        self.pair_target: set[str] = set()           # kept for callers that test membership regardless of side
        self.right_target: set[str] = set()
        self.lt_target: set[str] = set()             # left sides that are target text
        self.rt_target: set[str] = set()             # right sides that are target text: an English right equal to a left (museum) is NOT
        for u in R["units"]:
            for l in u["lessons"]:
                for e in l["exercises"]:
                    ck = e["content_key"]
                    for pr in e.get("pairs") or []:
                        L, Rt = pr["left"], pr["right"]
                        if norm(Rt) in teach_norms and norm(L) not in teach_norms:
                            self.pair_target.add(Rt)
                            self.right_target.add(Rt)
                            self.rt_target.add(Rt)
                            continue
                        self.pair_target.add(L)
                        self.lt_target.add(L)
                        tk = re.findall(r"[^\W\d_]{2,}", Rt.casefold())
                        if self.p.strict_residual:
                            eng2 = self.p.en_vocab | self.p.cast_words
                            is_right = bool(tk) and all(t in allsrc for t in tk) and not all(t in eng2 for t in tk)
                        else:
                            tk = [x for x in tk if x not in names_cf]
                            is_right = bool(tk) and sum(x in allsrc and ((len(x) >= 3 and x not in eng) or x in short_set) for x in tk) / len(tk) >= 0.6
                        if is_right or Rt in self.p.pair_force:
                            self.pair_target.add(Rt)
                            self.rt_target.add(Rt)
                            if Rt not in self.atom_texts:
                                self.right_target.add(Rt)
                                self.flag(ck, "PAIR_RIGHT_TARGET",
                                          f"pair right side {Rt!r} was treated as {self.p.src_name} text; check it is not English", "warn")
        for u in R["units"]:
            for l in u["lessons"]:
                for e in l["exercises"]:
                    for pr in e.get("pairs") or []:
                        for side, other, tgt in ((pr["left"], pr["right"], self.lt_target), (pr["right"], pr["left"], self.rt_target)):
                            if side in tgt:
                                self.T(side, "pair", other, e["content_key"])
        for u in R["units"]:
            for l in u["lessons"]:
                for e in l["exercises"]:
                    for pr in e.get("pairs") or []:
                        for side, tgt in ((pr["left"], self.lt_target), (pr["right"], self.rt_target)):
                            if side not in tgt:
                                add_en(side)
        srclex = set()
        for text in self.atom_texts:
            srclex |= set(re.findall(r"[^\W\d_]{3,}", text.casefold()))
        if self.p.strict_residual:
            # `env` is built from the English fields themselves, so a source word quoted inside an English instruction or option
            # (*sporten*, doen aan) counted as English.  Strict mode: every word of the source course that no other English overlay uses.
            self.src_only = (({w for w in self.p.src_lexicon if len(w) >= 4} | srclex) - self.p.en_vocab - self.p.cast_words) | (
                (srclex | self.p.source_vocab()) - self.p.english_words() - self.p.cast_words)      # either test finds a leftover
        else:
            # English vocabulary: words that occur in >= 10 overlay files of other pairs (never the source pair's own files,
            # which quote the source language).  A source word that is not English vocabulary counts as leftover in English text.
            self.src_only = (srclex | self.p.source_vocab()) - self.p.english_words()

    def options_are_target(self, ov: dict, instruction: str = "") -> bool:
        co = ov.get("correct_option")
        return isinstance(co, str) and (norm(co) in self.atom_norms or self.is_src(co, instruction or ov.get("instruction", ""))) and "distractors" in ov

    def build(self) -> tuple[dict, dict]:
        self.prepass()
        R, O = copy.deepcopy(self.real), copy.deepcopy(self.ovl)
        sp, tp = self.p.src, self.p.tgt
        # -- keys -----------------------------------------------------------
        old_unit = R["units"][0]["content_key"]
        unit_tail = old_unit.split(".", 3)[3]
        prefix_old = f"{sp}.{self.level}.unit{self.src_no:02d}."
        prefix_new = f"{tp}.{self.level}.unit{self.new_no:02d}."
        self.keymap[old_unit] = prefix_new + (self.new_suffix if unit_tail == self.suffix else unit_tail)
        media_slugs: set[str] = set()
        for a in R.get("media_assets") or []:
            parts = a["content_key"].split(".")
            idx = max((i for i, s in enumerate(parts) if re.fullmatch(r"\d+", s)), default=len(parts) - 1)
            si = idx - 1
            while si > 2 and parts[si] in ("formal", "informal"):
                si -= 1
            base = slug(self.T(a["text"], "media"), 5, self.p.translit)
            s = base
            n = 2
            while s in media_slugs or s in self.p.media_slugs:
                s = f"{base}_{n}"
                n += 1
            media_slugs.add(s)
            self.p.media_slugs.add(s)
            parts[si] = s
            if len(parts) > 3 and parts[3] == self.suffix:
                parts[3] = self.new_suffix
            parts[0] = tp
            self.keymap[a["content_key"]] = ".".join(parts)
        for u in R["units"]:
            for l in u["lessons"]:
                lk = l["content_key"]
                m = re.match(r"^(.*\.lesson\d+)\.(.+)$", lk)
                nl = prefix_new + m.group(1)[len(prefix_old):] + "." + slug(self.T(l["title"], "title"), 4, self.p.translit)
                self.keymap[lk] = nl
                seen: set[str] = set()
                for t in l.get("teaching") or []:
                    ck = t["content_key"]
                    mm = re.match(r"^(.*\.teach)\.(.+)$", ck)
                    base = slug(self.T(t["target"]["text"], "teach"), 3, self.p.translit)
                    s, n = base, 2
                    while s in seen:
                        s = f"{base}_{n}"
                        n += 1
                    seen.add(s)
                    self.keymap[ck] = prefix_new + mm.group(1)[len(prefix_old):] + "." + s
                for e in l["exercises"]:
                    ck = e["content_key"]
                    self.keymap[ck] = prefix_new + ck[len(prefix_old):]
        for k in list(self.keymap):
            if not (k.startswith(f"{sp}.{self.level}.")):
                raise SystemExit(f"unexpected key {k}")
        # -- realization ---------------------------------------------------------
        for a in R.get("media_assets") or []:
            a["text"] = self.T(a["text"], "media")
            a["language"] = tp
        self.media_tr = {a["content_key"]: a["text"] for a in R.get("media_assets") or []}
        O_ex = O.setdefault("exercises", {})
        O_te = O.setdefault("teaching", {})
        for u in R["units"]:
            u["title"] = self.T(u["title"], "title")
            for l in u["lessons"]:
                l["title"] = self.T(l["title"], "title")
                for t in l.get("teaching") or []:
                    self.teach(t, O_te.get(t["content_key"]))
                for i, e in enumerate(l["exercises"]):
                    self.exercise(e, O_ex.get(e["content_key"]), l)
        if self.p.rekey:
            self.rekey_exercises(R)
        # -- overlay English passthroughs -----------------------------------------
        for sect in ("units", "lessons"):
            for kk, v in (O.get(sect) or {}).items():
                v["title"] = self.en(v["title"], kk + "|title")
        for ck, v in (O_te).items():
            for f in ("title", "gloss"):
                if isinstance(v.get(f), str):
                    okey = f"{ck}|{f}"
                    left = [] if okey in self.p.en_over else self.residual(self.en(v[f], okey))
                    if ck in self.rewrite_cks or left:
                        # a rewritten grammar card needs its own English title/gloss; leftover source words can be authored away too
                        got = self.A(f"{ck}#{f}", v[f], f, dict(en=v[f], card=self.card_tr.get(ck), why=",".join(left) or "grammar card rewritten"),
                                     required=ck in self.rewrite_cks and self.p.rewrite_gloss)
                        if got is not None:
                            v[f] = got
                            continue
                    if left:
                        self.flag(ck, "LEFTOVER", f"{f} {v[f]!r} still contains {self.p.src_name} words {left}")
                    v[f] = self.en(v[f], okey)
            eg = v.get("example_gloss")
            if isinstance(eg, str):
                v["example_gloss"] = self.en(eg, f"{ck}|example_gloss")
            elif isinstance(eg, list):
                v["example_gloss"] = [self.en(x, f"{ck}|example_gloss{i}") for i, x in enumerate(eg)]
            if "note" in v:
                v["note"] = self.en_checked(v["note"], ck + "#note", "note", dict(en=v.get("gloss")))
            if isinstance(v.get("glosses"), dict):
                if not self.p.per_card_keys:
                    v["glosses"] = OrderedDict((self.gloss_key(ck, k), self.en(val, f"{ck}|gloss:{k}")) for k, val in v["glosses"].items())
                else:
                    new_gl = OrderedDict()
                    for k, val in v["glosses"].items():
                        gk = self.T(k, "gloss-key", None, ck)
                        left = self.residual(self.en(val, f"{ck}|gloss:{k}")) if self.p.strict_residual else []
                        # a gloss may explain a source word ('completes komt ... aan'): authored, with the translated key as context
                        new_gl[gk] = (self.A(f"{ck}#gv:{k}", val, "gloss-value", dict(key=gk, card=self.card_tr.get(ck), why=",".join(left)))
                                      if left else self.en(val, f"{ck}|gloss:{k}"))
                    if len(new_gl) < len(v["glosses"]) and not any(g.startswith("<<") for g in new_gl):
                        self.flag(ck, "GLOSS_KEY", f"two gloss keys translate to the same word ({len(v['glosses'])} source keys, {len(new_gl)} distinct): rephrase the card so each key is its own word")
                    v["glosses"] = new_gl
                card = next((t for u in R["units"] for l in u["lessons"] for t in l.get("teaching") or [] if t["content_key"] == ck), None)
                for k in v["glosses"]:
                    if card and not k.startswith("<<") and not re.search(rf"(?<![\w{DEV}'’\-]){re.escape(k)}(?![\w{DEV}'’\-])", card["target"]["text"], re.I):
                        self.flag(ck, "GLOSS_KEY", f"gloss key {k!r} is not a whole-word token of the card text (keys must be single words that occur in it)")
        # -- header ---------------------------------------------------------------
        self.grammar_lint(O)
        R, O = self.finish(R, O)
        self.english_leftover_scan(R, O)
        return R, O

    def english_leftover_scan(self, R, O) -> None:
        """Final net over every English field of the finished overlay: a source-language word that is not a word of the translated target
        text (so a cognate or a quoted target word is fine) is a leftover (`Pinnen is the verb`, `Jong means young`)."""
        if not self.p.strict_residual:
            return
        tgt: set[str] = set()

        def collect(o):
            if isinstance(o, dict):
                for v in o.values():
                    collect(v)
            elif isinstance(o, list):
                for v in o:
                    collect(v)
            elif isinstance(o, str):
                tgt.update(re.findall(r"[^\W\d_]{2,}", o.casefold()))
        collect(R)
        collect({k: v for k, v in O.items() if k == "exercises"})              # accepted answers, options: target text lives there too
        skip = {"title", "gloss", "note", "feedback", "instruction", "hint", "description", "example_gloss", "glosses", "prompt"}
        cast = {w.casefold() for kv in self.p.names_map.items() for w in kv}

        def walk(o, path, ck):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, path + [str(k)], str(k) if path and path[-1] in ("exercises", "teaching", "units", "lessons") else ck)
            elif isinstance(o, list):
                for v in o:
                    walk(v, path, ck)
            elif isinstance(o, str) and path and path[-1] in skip and "<<" not in o:
                t = re.sub(r"\*[^*]*\*", " ", o)
                t = re.sub(r"['\"\u2018\u201c][^'\"\u2019\u201d]{2,}['\"\u2019\u201d]", " ", t)
                left = sorted(set(re.findall(r"[^\W\d_]{3,}", t.casefold())) & self.src_only - tgt - cast)
                if left:
                    self.flag(ck or "?", "LEFTOVER", f"{path[-1]} {o[:120]!r} still contains {self.p.src_name} words {left}")
        walk({k: v for k, v in O.items() if k in ("exercises", "teaching", "units", "lessons")}, [], None)

    def grammar_lint(self, O: dict) -> None:
        """English strings that still describe source-language grammar (split verbs, het-words, ...) after rewriting."""
        pat = CFG.get(self.p.src, {}).get("grammar")
        if not pat:
            return
        def chk(key: str, field: str, s) -> None:
            if isinstance(s, str) and re.search(pat, s, re.I):
                self.flag(key, "SOURCE_GRAMMAR", f"{field} {s!r} still describes {self.p.src_name} grammar; rewrite it (note/feedback/instruction slot or en_override.json)")
        for sect in ("units", "lessons"):
            for k, v in (O.get(sect) or {}).items():
                chk(k, "title", v.get("title"))
        for k, v in (O.get("teaching") or {}).items():
            for f in ("title", "gloss", "note"):
                chk(k, f, v.get(f))
            for g in (v.get("glosses") or {}).values():
                chk(k, "glosses", g)
        for k, v in (O.get("exercises") or {}).items():
            for f in ("instruction", "feedback"):
                chk(k, f, v.get(f))

    def rekey_exercises(self, R: dict) -> None:
        """Exercise key tails carry source-language words and cast names (choose_ik_sport): rebuild them from the translated tested text."""
        for u in R["units"]:
            for l in u["lessons"]:
                seen: set[str] = set()
                for e in l["exercises"]:
                    old = e["content_key"]
                    verb = self.keymap[old].rsplit(".", 1)[1].split("_", 1)[0]
                    txt = e.get("tested_text") or ""
                    if not txt or txt.startswith("<<"):
                        continue
                    base = f"{verb}_{slug(txt, 3, self.p.translit)}"
                    tail, n = base, 2
                    while tail in seen:
                        tail, n = f"{base}_{n}", n + 1
                    seen.add(tail)
                    head = self.keymap[old].rsplit(".", 1)[0]
                    self.keymap[old] = f"{head}.{tail}"

    # -- teaching ---------------------------------------------------------------
    def teach(self, t: dict, ov: dict | None) -> None:
        tgt = t["target"]
        tgt["text"] = self.T(tgt["text"], "teach")
        self.card_tr[t["content_key"]] = tgt["text"]
        tgt["language_code"] = self.p.tgt
        if t["target"].get("speaker"):
            sp_ = tgt["speaker"]
            # a role label ("de medewerker") is source-language text; a cast name is mapped
            tgt["speaker"] = self.T(sp_, "speaker") if (sp_[:1].islower() or " " in sp_) else self.p.names(sp_)
            if CFG.get(self.p.tgt, {}).get("script") == "cyrillic" and (sp_[:1].islower() or " " in sp_):
                tgt["speaker"] = tgt["speaker"][:1].upper() + tgt["speaker"][1:]       # ru speaker labels are case-sensitive in the validator (Сотрудник:)
            lab = re.match(r"([^\W\d_][^:\n]{0,30}?)\s*:", tgt["text"])
            if lab and lab.group(1).casefold() == str(tgt["speaker"]).casefold():
                tgt["speaker"] = lab.group(1)             # the structured speaker must spell the label as the card (and the audio text) does
        exs = t.get("example")
        for e in ([exs] if isinstance(exs, dict) else (exs or [])):
            e["text"] = self.T(e["text"], "example")
            e["language_code"] = self.p.tgt
        # target tokens plus the tokens of the card's examples (the source course introduces example words on the card too)
        ex_toks = [w for e in ([exs] if isinstance(exs, dict) else (exs or [])) for w in tokens(e["text"])]
        t["introduced_tokens"] = list(OrderedDict.fromkeys(tokens(tgt["text"]) + ex_toks))
        for atom_txt in [tgt["text"]] + ([e["text"] for e in ([exs] if isinstance(exs, dict) else (exs or []))] if self.p.cs else []):
            self.lints(t["content_key"], atom_txt, kind="teach")

    # -- exercises ---------------------------------------------------------------
    def exercise(self, e: dict, ov: dict | None, lesson: dict) -> None:
        sp, tp = self.p.src, self.p.tgt
        ck, ty = e["content_key"], e["type"]
        ov = ov if ov is not None else {}
        if ov is not None and ck not in (self.ovl.get("exercises") or {}):
            self.flag(ck, "NO_OVERLAY", "exercise has no overlay entry; copied as is", "warn")
        en_inst = ov.get("instruction")
        ctx = dict(type=ty, instruction=en_inst)
        mk = e.get("media_asset_key")
        if mk and getattr(self, "media_tr", None) and mk in self.media_tr:
            ctx["media"] = self.media_tr[mk]                      # translated audio text: the context a tested span / feedback refers to
        # prompt blocks
        frame_src = None
        n_en = 0
        for b in (e.get("prompt") or {}).get("target_blocks") or []:
            if b.get("language_code") == sp:
                if BLANK in b["text"]:
                    frame_src = b["text"]
                    b["text"] = self.A(ck + "#frame", frame_src, "frame", dict(ctx, en=en_inst))
                else:
                    b["text"] = self.T(b["text"], "prompt")
                b["language_code"] = tp
            else:
                # English prompt text may quote the source sentence ("What does '...' mean?"): substitute / author it
                b["text"] = (self.en_checked(b["text"], f"{ck}#prompt{n_en}", "prompt_en", dict(ctx))
                             if self.p.strict_residual else self.en(b["text"]))
                n_en += 1
        pr_tr = [b["text"] for b in (e.get("prompt") or {}).get("target_blocks") or [] if b.get("language_code") == tp]
        if pr_tr:
            ctx["prompt"] = " ".join(pr_tr)
        # overlay fields
        if "instruction" in ov:
            ov["instruction"] = self.en_checked(ov["instruction"], ck + "#instruction", "instruction", ctx)
        has_opts = "correct_option" in ov and "distractors" in ov
        old_accepted = copy.deepcopy(ov.get("accepted_answers") or [])
        acc_vals = [a.get("value") for a in old_accepted]
        canon_src = (acc_vals[0] if acc_vals and isinstance(acc_vals[0], str) else ov.get("correct_option"))
        ans_target = (self.options_are_target(ov, en_inst or "") if has_opts else (ty in TARGET_ANSWER_TYPES and isinstance(canon_src, str)))
        if ty == "translation" and e.get("prompt"):
            bl = (self.real_prompt_langs(e))
            if sp in bl:
                self.flag(ck, "REVERSE_TRANSLATION", "translation prompt is in the source language; answers are English. Not derived automatically")
        tested_src = e.get("tested_text", "")
        alts: list[str] = []
        canon_tr: str | None = None
        if ty == "matching_pairs":
            for p_ in e.get("pairs") or []:
                p_["left"] = self.pr(p_["left"], "left")
                p_["right"] = self.pr(p_["right"])
            for a in ov.get("accepted_answers") or []:
                if isinstance(a.get("value"), list):
                    for pr in a["value"]:
                        pr["left"] = self.pr(pr["left"], "left")
                        pr["right"] = self.pr(pr["right"])
            self.pair_collisions(ck, e.get("pairs") or [])
        elif has_opts and ans_target:
            canon_tr = self.T_by_norm(ov["correct_option"]) or self.T(ov["correct_option"], "option")
            ov["correct_option"] = canon_tr
            dist = self.A(ck + "#dist", SEP.join(ov["distractors"]), "distractors",
                          dict(ctx, correct_src=canon_src, correct_tr=canon_tr, n=len(ov["distractors"])))
            ov["distractors"] = [x for x in re.split(r"\s*\|\|\s*", dist) if x] if not dist.startswith("<<") else ov["distractors"]
            if not dist.startswith("<<") and len(ov["distractors"]) != len(self.ovl["exercises"][ck]["distractors"]):
                self.flag(ck, "DIST_COUNT", f"expected {len(self.ovl['exercises'][ck]['distractors'])} distractors", "warn")
            ov["accepted_answers"] = [dict(a, value=canon_tr) if isinstance(a.get("value"), str) else a for a in old_accepted[:1]]
            alts = [canon_tr]
        elif has_opts:
            if not self.p.strict_residual:
                opts_src = [ov["correct_option"]] + list(ov["distractors"])
                gpat = CFG.get(self.p.src, {}).get("grammar")
                if any(self.residual(self.en(x)) or (gpat and re.search(gpat, x, re.I)) for x in opts_src):
                    # English options that quote or discuss the source language need rewriting for the new one
                    got = self.A(ck + "#options", SEP.join(opts_src), "options", dict(ctx))
                    parts = [x for x in re.split(r"\s*\|\|\s*", got) if x]
                    if not got.startswith("<<") and len(parts) == len(opts_src):
                        ov["correct_option"], ov["distractors"] = parts[0], parts[1:]
                        for a in ov.get("accepted_answers") or []:
                            if isinstance(a.get("value"), str):
                                a["value"] = parts[0]
                    elif not got.startswith("<<"):
                        self.flag(ck, "OPTIONS_COUNT", f"#options needs {len(opts_src)} options (correct first)")
                else:
                    ov["correct_option"] = self.en(ov["correct_option"])
                    ov["distractors"] = [self.en(d) for d in ov["distractors"]]
                    for a in ov.get("accepted_answers") or []:
                        if isinstance(a.get("value"), str):
                            a["value"] = self.en(a["value"])
            else:
                left = self.residual(self.en(SEP.join([ov["correct_option"]] + list(ov["distractors"]))))
                got = None
                if left:                                   # options quote or discuss the source language: authored (correct || distractor || ...)
                    got = self.A(ck + "#opts", SEP.join([ov["correct_option"]] + list(ov["distractors"])), "options",
                                 dict(ctx, why=",".join(left), n=len(ov["distractors"]) + 1), required=self.p.strict_residual)
                if got and not got.startswith("<<"):
                    parts = [x for x in re.split(r"\s*\|\|\s*", got) if x]
                    ov["correct_option"], ov["distractors"] = self.en(parts[0]), [self.en(d) for d in parts[1:]]
                    ov["accepted_answers"] = [dict(a, value=ov["correct_option"]) if isinstance(a.get("value"), str) else a
                                              for a in ov.get("accepted_answers") or []]
                else:
                    ov["correct_option"] = self.en(ov["correct_option"])
                    ov["distractors"] = [self.en(d) for d in ov["distractors"]]
                for a in ov.get("accepted_answers") or []:
                    if isinstance(a.get("value"), str):
                        a["value"] = self.en(a["value"])
        elif ans_target:
            canon_tr, alts = self.answers(ck, ty, ov, canon_src, acc_vals, frame_src, ctx)
        else:
            for a in ov.get("accepted_answers") or []:
                if isinstance(a.get("value"), str):
                    a["value"] = self.en(a["value"])
        # tested text
        if "tested_text" in e:
            e["tested_text"] = self.tested(e, ck, tested_src, canon_src, canon_tr, ctx)
            if ty == "dictation" and isinstance(ov.get("correct_response"), str):
                ov["correct_response"] = e["tested_text"]      # A2 dictation: overlay holds the audio text (= tested_text) as a plain string
        # word bank
        if "word_bank" in e:
            self.bank(e, ck, tested_src, e["tested_text"], alts, ctx)
        if "feedback" in ov:
            ov["feedback"] = self.en_checked(ov["feedback"], ck + "#feedback", "feedback",
                                             dict(ctx, correct=canon_tr, tested=e.get("tested_text")))
        # lints on learner-produced alternates
        if ans_target and ty in TARGET_ANSWER_TYPES:
            produced = ty in ("translation", "writing_prompt", "dialogue_response", "speak_response", "fill_in_blank")
            for a in alts:      # transcription types (dictation, listen_*) copy someone else's sentence: no gender/register lint
                self.lints(ck, a, kind="answer" if produced else "transcribe", answers=alts, src_text=canon_src)
        if "media_asset_key" in e:
            pass

    def pr(self, right: str, side: str = "right") -> str:
        if right in (self.lt_target if side == "left" else self.rt_target):
            return self.T(right, "pair")
        if self.p.strict_residual and self.residual(self.en(right)):
            return self.T(right, "pair")          # English side that still quotes a source word: translated like an atom (its translation is English)
        return self.en(right)

    def pair_collisions(self, ck: str, pairs: list[dict]) -> None:
        """The grader keys a matching answer by the normalised left (and right) text: two sides that differ only by
        punctuation or case collapse into one key and the exact answer grades wrong (en-es unit69 'esta incluido.' / '?')."""
        for side in ("left", "right"):
            seen: dict[str, str] = {}
            for pr in pairs:
                txt = pr[side]
                if txt.startswith("<<"):
                    continue
                k = norm(txt)
                if k in seen:
                    self.flag(ck, "PAIR_COLLISION", f"matching {side} items {seen[k]!r} and {txt!r} normalise to the same key; reword one")
                seen[k] = txt

    def real_prompt_langs(self, e: dict) -> set[str]:
        return {b.get("language_code") for b in (e.get("prompt") or {}).get("target_blocks") or []}

    # -- answers / variants --------------------------------------------------------
    def answers(self, ck, ty, ov, canon_src, acc_vals, frame_src, ctx):
        strs = [v for v in acc_vals if isinstance(v, str)]
        src_punct = any(re.search(r"[.!?,;:]", v) for v in strs)
        src_plain = any(not re.search(r"[.!?,;:]", v) for v in strs) or not strs
        classes = list(OrderedDict.fromkeys(norm(v) for v in strs))
        by_class = OrderedDict()
        for v in strs:
            by_class.setdefault(norm(v), v)
        if ty != "fill_in_blank" and norm(canon_src) in self.atom_norms:
            base = self.T_by_norm(canon_src)
            alts = [base]
        else:
            src_show = SEP.join(by_class.values())
            got = self.A(ck + "#ans", src_show, "answer",
                         dict(ctx, source_forms=list(by_class.values()), frame=frame_src))
            alts = [x for x in re.split(r"\s*\|\|\s*", got) if x]
            base = alts[0]
        extra = self.p.tr_author.get(ck + "#alt")
        extra = self.p.names(extra) if extra else None
        if extra:
            alts += [x for x in re.split(r"\s*\|\|\s*", extra) if x]
        if len(classes) > len(alts) and ty not in ("fill_in_blank",) and not any(x.startswith("<<") for x in alts):
            self.flag(ck, "VARIANTS", f"source accepted {len(classes)} distinct forms ({list(by_class.values())}); "
                      f"{len(alts)} given. Add `{ck}#alt` if the target language has real alternatives", "warn")
        out: list[str] = []
        for x in alts:
            if src_punct:
                out.append(x)
            if src_plain:
                out.append(boundary_strip(x) if ty == "dictation" else strip_punct(x) if ty != "fill_in_blank" else x)
        out = list(OrderedDict.fromkeys(out))
        if CFG.get(self.p.tgt, {}).get("danda") and ty in YO_FOLD_TYPES and ty != "dictation":
            # the grader strips boundary punctuation only: an inner danda between two sentences also accepts the full stop a keyboard gives
            out = list(OrderedDict.fromkeys(out + [re.sub(r"।(?=\s)", ".", x) for x in out if re.search(r"।(?=\s)", x)]))
        if self.p.translit and ty in GERMAN_FREE_TEXT_TYPES:
            # the German compiler wants the full ASCII transliteration (ä->ae ...) of every typed answer with umlauts
            out = list(OrderedDict.fromkeys(out + [x.translate(TRANSLIT_DE) for x in out if x.translate(TRANSLIT_DE) != x]))
        if CFG.get(self.p.tgt, {}).get("yo_fold") and ty in YO_FOLD_TYPES:
            out = list(OrderedDict.fromkeys(out + [yo_fold(x) for x in out if yo_fold(x) != x]))      # е for ё is a keyboard habit, not an error
        canon_form = out[0]
        if "correct_option" in ov:
            ov["correct_option"] = base if re.search(r"[.!?]", canon_src) else (re.sub(rf"^[^\w{DEV}]+|[^\w{DEV}]+$", "", base) if ty == "dictation" else strip_punct(base))
        new_acc = []
        proto = ov.get("accepted_answers") or [{"status": "correct"}]
        for v in out:
            new_acc.append(dict(proto[0], value=v))
        ov["accepted_answers"] = new_acc
        if ty == "fill_in_blank" and frame_src:
            frame_tr = self.p.tr_author.get(ck + "#frame")
            if frame_tr and not any(x.startswith("<<") for x in alts):
                full = frame_tr.replace(BLANK, alts[0])
                if self.p.tr_atoms and norm(full) not in {norm(self.p.tr_atoms.get(a, "")) for a in self.p.atoms}:
                    self.flag(ck, "FILL_CHECK", f"frame filled with the answer ({full!r}) is not a translated sentence of this unit", "warn")
                if frame_tr.count(BLANK) != frame_src.count(BLANK):
                    self.flag(ck, "BLANK_COUNT", "frame must keep the same number of ___ blanks")
        return base, alts

    def tested(self, e, ck, tested_src, canon_src, canon_tr, ctx):
        """tested_text: sentence atom, the answer, or an authored span."""
        if canon_tr is not None and canon_src and norm(tested_src) == norm(canon_src):
            if canon_tr.startswith("<<"):
                return canon_tr
            if tested_src != strip_punct(canon_src) and tested_src == boundary_strip(canon_src):
                return boundary_strip(canon_tr)          # dictation: the compiler compares with the audio text, inner commas included
            body = strip_punct(canon_tr)
            if e.get("type") == "dictation":          # dictation tested_text must equal the audio text up to boundary punctuation only
                body = re.sub(rf"^[^\w{DEV}]+|[^\w{DEV}]+$", "", canon_tr)
            if self.p.cs:
                return body
            return body if tested_src == strip_punct(canon_src) else body.lower() if tested_src == tested_src.lower() else body
        aid = self.atom_norms.get(norm(tested_src))
        if aid is not None:
            atom_tr = self.T_by_norm(tested_src)
            if atom_tr.startswith("<<"):
                return atom_tr
            body = strip_punct(atom_tr)
            keep_case = tested_src == strip_punct(self.id_text[aid])
            return body if keep_case or self.p.cs else body.casefold()
        v = self.A(ck + "#tested", tested_src, "tested", dict(ctx, canon=canon_tr))
        low = {a.casefold(): b.casefold() for a, b in self.p.names_map.items()}       # tested spans are written in lowercase: omar -> mathieu
        return re.sub(rf"(?<![\w{DEV}])(" + "|".join(map(re.escape, low)) + rf")(?![\w{DEV}])", lambda m: low[m.group(1)], v) if low and not v.startswith("<<") else v

    def bank(self, e, ck, tested_src, tested_tr, alts, ctx):
        ov = (self.p.tr_author.get(ck + "#bank") or "") if not tested_tr.startswith("<<") else ""
        if ov:          # authored tiles: a gendered word order exercise offers both forms (zostałem | zostałam); the canonical sentence must stay buildable
            tiles = [x.strip() for x in ov.split("|") if x.strip()]
            pool = [t.casefold() for t in tiles]
            for t in (t.casefold() for t in tokens(tested_tr)):
                if t in pool:
                    pool.remove(t)
                else:
                    self.flag(ck, "TILES", f"authored #bank {tiles} cannot build the answer {tested_tr!r}")
                    break
            e["word_bank"] = tiles
            return
        src_tokens = [t.casefold() for t in tokens(tested_src)]
        bank_src = [t.casefold() for t in e["word_bank"]]
        if sorted(src_tokens) != sorted(bank_src):
            got = self.A(ck + "#bank", " | ".join(e["word_bank"]), "bank", dict(ctx, tested=tested_tr))
            e["word_bank"] = [x.strip() for x in got.split("|") if x.strip()]
            return
        if tested_tr.startswith("<<"):
            e["word_bank"] = ["<<bank>>"]
            return
        tiles = tokens(tested_tr)
        e["word_bank"] = shuffled(tiles)
        # every accepted alternate must be buildable from the tiles
        for a in alts:
            if sorted(t.casefold() for t in tokens(a)) != sorted(t.casefold() for t in tiles):
                self.flag(ck, "TILES", f"accepted variant {a!r} cannot be built from tiles {tiles}: word-order variants need their own tile set")

    # -- lints -------------------------------------------------------------------
    def lints(self, key: str, text: str, kind: str, answers: list[str] | None = None, src_text: str | None = None):
        if text.startswith("<<"):
            return
        tp, sp = self.p.tgt, self.p.src
        cfg = CFG.get(tp, {})
        for pat, fix in cfg.get("contractions", []):
            if re.search(pat, text):
                self.flag(key, "CONTRACTION", f"{text!r}: obligatory contraction not applied (use {fix!r}); never accept the uncontracted form as a variant")
        for pat, fix in cfg.get("elisions", []):
            if re.search(pat, text):
                self.flag(key, "ELISION", f"{text!r}: obligatory elision / apostrophe rule not applied (use {fix!r})")
        if src_text:
            src_reg = register_of(src_text, sp)
            tr_reg = register_of(text, tp) if cfg else None
            if src_reg and tr_reg and src_reg != tr_reg:
                self.flag(key, "REGISTER", f"source is {src_reg} ({src_text!r}) but translation reads {tr_reg} ({text!r})")
        if cfg.get("elision") and kind in ("teach", "answer", "transcribe"):
            for bad in fr_elision_errors(text):
                self.flag(key, "ELISION", f"{text!r}: obligatory elision not applied ({bad!r}); never accept the unelided form as a variant")
        if cfg.get("diacritics") == "ro":
            for bad in ro_ortho_errors(text):
                self.flag(key, "ORTHO", f"{text!r}: {bad}")
        if cfg.get("straight_apostrophe") and "’" in text:
            self.flag(key, "APOSTROPHE", f"{text!r}: use the straight apostrophe (')")
        if cfg.get("script") == "cyrillic" and kind in ("teach", "answer", "transcribe"):
            if "\u0301" in text:
                self.flag(key, "STRESS", f"{text!r}: no stress marks in learner-facing Russian text")
            plain = re.sub(r"\{[^}]*\}", "", text)
            if re.search(r"[A-Za-z]", plain):
                self.flag(key, "SCRIPT", f"{text!r}: Latin letters in Russian text (write it in Cyrillic, or acknowledge a real exception in ack.json)")
            self.yo_lint(key, text)
        if cfg.get("script") == "arabic" and kind in ("teach", "answer", "transcribe"):
            self.arabic_lint(key, text)
        if cfg.get("script") == "devanagari" and kind in ("teach", "answer", "transcribe"):
            plain = re.sub(r"\{[^}]*\}", "", text)
            if re.search(r"[A-Za-z]", plain):
                self.flag(key, "SCRIPT", f"{text!r}: Latin letters in Hindi text (write it in Devanagari, or acknowledge a real exception in ack.json)")
            if re.search(r"[\u0900-\u097f][^\u0900-\u097f\w]*\.(?:\s|$)", text):
                self.flag(key, "DANDA", f"{text!r}: end a Hindi sentence with the danda । (not a full stop)")
            self.spell_lint(key, text, hi_fold)
        g = cfg.get("gender")
        if g and kind == "answer" and g.get("mode") == "ar":
            alts_ar = ar_gender_alts(text)
            if alts_ar and not any(norm(a) in {norm(x) for x in (answers or [])} for a in alts_ar):
                self.flag(key, "GENDER", f"gendered word in {text!r} (speaker or addressee); add the other gender ({alts_ar[0]!r}) via `{key}#alt`")
        elif g and kind == "answer" and g.get("mode") == "hi":
            alts_hi = hi_gender_alts(text)
            if alts_hi and not any(norm(a) in {norm(x) for x in (answers or [])} for a in alts_hi):
                self.flag(key, "GENDER", f"speaker-gendered word in {text!r}; add the other gender ({alts_hi[0]!r}) via `{key}#alt`")
        elif g and kind == "answer" and g.get("mode") == "ru":
            alts_ru = ru_gender_alts(text)
            if alts_ru and not any(norm(a) in {norm(x) for x in (answers or [])} for a in alts_ru):
                self.flag(key, "GENDER", f"speaker-gendered word in {text!r}; add the other gender ({alts_ru[0]!r}) via `{key}#alt`")
        elif g and kind == "answer" and g.get("mode") == "fr":
            alts_fr = fr_gender_alts(text)
            if alts_fr and not any(norm(a) in {norm(x) for x in (answers or [])} for a in alts_fr):
                self.flag(key, "GENDER", f"speaker-gendered word in {text!r}; add the other gender ({alts_fr[0]!r}) via `{key}#alt`")
        elif g and kind == "answer" and g.get("mode") == "pl":
            alts_pl = pl_gender_alts(text)
            if alts_pl and not any(norm(a) in {norm(x) for x in (answers or [])} for a in alts_pl):
                self.flag(key, "GENDER", f"speaker-gendered word in {text!r}; add the other gender ({alts_pl[0]!r}) via `{key}#alt`")

        elif g and kind == "answer" and g.get("mode") == "ro":
            alts_ro = ro_gender_alts(text)
            if alts_ro and not any(norm(a) in {norm(x) for x in (answers or [])} for a in alts_ro):
                self.flag(key, "GENDER", f"speaker-gendered word in {text!r}; add the other gender ({alts_ro[0]!r}) via `{key}#alt`")
        elif g and kind == "answer" and g.get("mode") == "agent":
            alt = agent_gender_alt(text)
            if alt and norm(alt) not in {norm(x) for x in (answers or [])}:
                self.flag(key, "GENDER", f"speaker-gendered noun in {text!r}; add the other gender ({alt!r}) via `{key}#alt`")
        elif g and kind == "answer":
            m = re.search(g["copula"] + r"\s+(?:(?:muy|tan|un poco|bastante|molto|più)\s+)?(\w{3,}?)(os|as|o|a|i|e)\b", text, re.I)
            if m:
                stem, end = m.group(2), m.group(3)
                if (stem + end).lower() not in g["skip"]:
                    flip = dict(g["swap"])
                    flip.update({b: a for a, b in g["swap"]})
                    other = flip.get(end.lower())
                    if other:
                        alt = text[:m.start(2)] + stem + other + text[m.end():]
                        if norm(alt) not in {norm(x) for x in (answers or [])}:
                            self.flag(key, "GENDER", f"speaker-gendered form in {text!r}; add the other gender ({alt!r}) via `{key}#alt`")
        if self.p.cs:
            self.case_lint(key, text)

    def arabic_lint(self, key: str, text: str) -> None:
        plain = re.sub(r"\{[^}]*\}", "", text)
        if AR_MARKS.search(plain):
            self.flag(key, "HARAKAT", f"{text!r}: no harakat / tatweel in A1 Arabic text (the course is unvocalised; \\w tokenisation splits a word at a haraka; give the vowels in the note's transliteration)")
        if re.search(r"[A-Za-z]", plain):
            self.flag(key, "SCRIPT", f"{text!r}: Latin letters in Arabic text (write it in Arabic script, or acknowledge a real exception in ack.json)")
        if AR_PERSIAN.search(plain):
            self.flag(key, "SCRIPT", f"{text!r}: Persian / Urdu letter in Arabic text (use Arabic yeh ي, kaf ك, heh ه / teh marbuta ة)")
        if re.search("[\u0660-\u0669\u06f0-\u06f9]", plain):
            self.flag(key, "ARDIGIT", f"{text!r}: the en-ar course writes Western digits (5), not Arabic-Indic digits")
        if re.search(r"[?;]", plain) or re.search(r"[\u0621-\u064a],", plain):
            self.flag(key, "PUNCT", f"{text!r}: Arabic punctuation in Arabic text (؟ ، ؛ instead of ? , ;)")
        if re.search(r"(?:^|\s)[وفبلك]\s+(?=[\u0621-\u064a])", plain):
            self.flag(key, "CLITIC", f"{text!r}: a detached و ف ب ل ك; the particle is written joined to the next word and is one token / tile")
        if re.search(r"(?<![\u0621-\u064a])[وف]?لال(?=[\u0621-\u064a])", plain):
            self.flag(key, "ARTICLE", f"{text!r}: ل + ال contracts to لل (للمدرسة, not لالمدرسة)")
        if re.search(r"(?<![\u0621-\u064a])[وفبكل]?الال", plain):
            self.flag(key, "ARTICLE", f"{text!r}: doubled definite article")
        m = AR_DUAL_NUM.search(plain)
        if m:
            self.flag(key, "DUAL", f"{text!r}: 'two X' is the dual noun (كتابان / كتابين), not the numeral اثنان + a noun")
        if self.p.ar_forms is None:
            self.p.ar_forms = defaultdict(set)
            up, low = self.p.lexicon
            for k in up | low:
                self.p.ar_forms[ar_fold(k)].add(k)
        for t in tokens(text):
            f = ar_fold(t)
            seen = self.p.ar_forms[f]
            if seen and t not in seen:
                self.flag(key, "AR_MIXED", f"{t!r} in {text!r}: the course also spells this word {sorted(seen)} (hamza / alef / yeh / teh marbuta variant); one spelling per word, or acknowledge two real words", level="warn")
            seen.add(t)

    def yo_lint(self, key: str, text: str) -> None:
        self.spell_lint(key, text, yo_fold)

    def spell_lint(self, key: str, text: str, fold) -> None:
        """One spelling per word: идёт and идет (ru), हूँ and हूं (hi) must not both occur in the course (they would become two lexemes)."""
        seen = self.p.yo_forms
        if seen is None:
            seen = self.p.yo_forms = defaultdict(set)
            up, low = self.p.lexicon
            for k in up | low:
                seen[fold(k.casefold())].add(k.casefold())
        code = "SPELL_MIXED" if fold is hi_fold else "YO_MIXED"
        for t in tokens(text):
            c = t.casefold()
            f = fold(c)
            if fold is yo_fold and (f in RU_YO_SAME or c in RU_YO_SAME):
                continue
            if seen[f] and c not in seen[f]:
                self.flag(key, code, f"{t!r} in {text!r}: the course also spells this word {sorted(seen[f])}; use one spelling")
            seen[f].add(c)

    def case_lint(self, key: str, text: str) -> None:
        """Case-sensitive targets (German): a known common noun written lowercase, or a known non-noun capitalised mid-sentence.
        Sentence starts, quoted phrases (*Was machst du?*) and cast names are skipped; nominalised verbs/adjectives (Kochen, etwas Neues)
        are legitimate exceptions to acknowledge in ack.json."""
        up, low = self.p.lexicon
        start = True
        for m in re.finditer(r"[^\W\d_][\w'’\-]*|[.!?:\n*\"“„]", text):
            t = m.group(0)
            if t in (".", "!", "?", ":", "\n", "*", '"', "“", "„"):
                start = True
                continue
            first, start = start, False
            if first or t in up or t in low or t in self.p.case_ok or t in self.p.names_map.values():
                continue
            cap = t[0].upper() + t[1:]
            if t[0].islower() and cap in up and cap not in self.p.case_ok and cap not in self.p.proper_nouns:
                self.flag(key, "CASE", f"{t!r} in {text!r}: German nouns are capitalised ({cap!r})")
            elif t[0].isupper() and (t[0].lower() + t[1:]) in low:
                self.flag(key, "CASE", f"{t!r} in {text!r}: capitalised mid-sentence, but {t[0].lower() + t[1:]!r} is a known non-noun")

    # -- header -----------------------------------------------------------------
    def finish(self, R: dict, O: dict) -> tuple[dict, dict]:
        tp, sp = self.p.tgt, self.p.src
        base_r = dd.load(self.p.base_real)
        base_o = dd.load(self.p.base_ovl)
        note = (f"Derived by scripts/derive_target.py from {sp}/{self.stem}.yaml ({self.p.src_pair} overlay): target text "
                f"translated, distractors/notes/feedback authored, tiles and tokens derived. Needs native {self.p.new_name} review "
                f"(register, naturalness, distractor plausibility). No sibling-file consultation was done for the authored parts "
                f"beyond the source ctx shown in author.src.json.")
        R["target_language"] = tp
        R["cefr_level"] = self.level.upper()
        R["status"] = "complete_draft"
        R["generation_provenance"] = {
            "method": "ai_generated", "authoring_system": "claude", "human_reviewed": False,
            "source_material": f"Translated from {sp} {self.level.upper()} unit {self.src_no:02d} ({self.stem}) by scripts/derive_target.py.",
        }
        R["review"] = {"status": "unreviewed", "required_next_reviewer": "native_speaker_review", "notes": note}
        R["course"] = copy.deepcopy(base_r["course"])
        R["realization_version"] = base_r.get("realization_version", R.get("realization_version"))
        for u in R["units"]:
            u.pop("planned_lesson_count", None) if False else None
        newO = OrderedDict()
        for k in ("schema_version", "overlay_version"):
            newO[k] = base_o.get(k, O.get(k))
        newO["overlay_key"] = f"{self.p.new_pair}.{self.level}.unit{self.new_no:02d}"
        newO["source_language"] = base_o["source_language"]
        newO["target_language"] = tp
        newO["status"] = "complete_draft"
        newO["generation_provenance"] = {"method": "ai_generated", "authoring_system": "claude", "human_reviewed": False}
        newO["review"] = {"status": "unreviewed", "required_next_reviewer": "native_speaker_review", "notes": note}
        if "answer_policy" in base_o:
            newO["answer_policy"] = copy.deepcopy(base_o["answer_policy"])
        desc = self.en(O["course"]["description"])
        if (self.p.strict_residual and self.residual(desc)) or self.p.always_desc:
            desc = self.A(f"{self.stem}#desc", O["course"]["description"], "description", dict(why=",".join(self.residual(desc))))
        newO["course"] = {"title": base_o["course"]["title"], "description": desc}
        for k in ("units", "lessons", "teaching", "exercises"):
            if k in O:
                newO[k] = O[k]
        if CFG.get(tp, {}).get("script") == "arabic":
            def _rtl(o):                     # target-language text blocks are RTL (the source blocks say ltr)
                if isinstance(o, dict):
                    if o.get("language_code") == tp and "text" in o:
                        o["direction"] = "rtl"
                    for v in o.values():
                        _rtl(v)
                elif isinstance(o, list):
                    for v in o:
                        _rtl(v)
            _rtl(R)
            for sv in yaml_strings(newO):
                bad = ar_sun_errors(sv)
                if bad:
                    self.flag(self.stem, "SUNLETTER", f"transliteration {bad[0]!r} in {sv[:80]!r}: the article assimilates to a sun letter (ash-shams, ar-raʾs)")
        R = self.remap(R)
        newO = self.remap(newO)
        return R, newO

    def remap(self, o):
        if isinstance(o, dict):
            return OrderedDict((self.keymap.get(k, k) if isinstance(k, str) else k, self.remap(v)) for k, v in o.items())
        if isinstance(o, list):
            return [self.remap(v) for v in o]
        if isinstance(o, str):
            return self.keymap.get(o, o)
        return o


# ---------------------------------------------------------------------------
# Plan (all units of one run)
# ---------------------------------------------------------------------------
class Plan:
    def __init__(self, args, work: Path):
        self.src_pair, self.new_pair = args.source, args.new
        self.src, self.tgt = self.src_pair.split("-")[1], self.new_pair.split("-")[1]
        self.src_name = CFG.get(self.src, {}).get("name", self.src)
        self.new_name = CFG.get(self.tgt, {}).get("name", self.tgt)
        self.cs = bool(CFG.get(self.tgt, {}).get("case_sensitive"))      # case carries meaning (German nouns)
        self.translit = bool(CFG.get(self.tgt, {}).get("translit"))
        self.strict_residual = bool(CFG.get(self.tgt, {}).get("strict_residual"))
        self.per_card_keys = bool(CFG.get(self.tgt, {}).get("per_card_keys"))
        self.rewrite_gloss = bool(CFG.get(self.tgt, {}).get("rewrite_gloss"))
        self.always_desc = bool(CFG.get(self.tgt, {}).get("always_desc"))     # the unit description is always authored (it quotes source-language phrases)
        self.rekey = bool(CFG.get(self.tgt, {}).get("rekey_exercises"))     # exercise key tails re-derived from the translation
        self.suffixes = dict(kv.split("=", 1) for kv in (getattr(args, "suffixes", None) or "").split(",") if "=" in kv)
        self._lex = None
        self.yo_forms = None
        self.ar_forms = None
        self.work = work
        self.names_map = dict(kv.split("=", 1) for kv in (args.names or "").split(",") if "=" in kv)
        # English fields name the cast in Latin letters when the target script is not Latin (Лотте -> Nastya): --names-en
        self.names_en_map = dict(kv.split("=", 1) for kv in (getattr(args, "names_en", None) or "").split(",") if "=" in kv) or self.names_map
        self.units = args.units
        self.atoms: OrderedDict[str, str] = OrderedDict()
        self.atom_ctx: dict[str, dict] = {}
        self.author: OrderedDict[str, str] = OrderedDict()
        self.author_ctx: dict[str, dict] = {}
        self.missing: set[str] = set()
        self.flags: list[dict] = []
        self.media_slugs: set[str] = set()
        self.derived: dict[str, str] = {}
        self.tr_atoms = load_json(work / "atoms.tr.json")
        self.tr_author = load_json(work / "author.tr.json")
        self.acks = load_json(work / "ack.json")
        # English strings that describe source-language grammar (titles, glosses, notes): exact string -> rewrite for the new language
        self.en_over = load_json(work / "en_override.json")
        self.pair_force = set(load_json(work / "pair_force.json") or [])      # pair right sides that are source text although they look English ("pin")
        # base files of the target course: header/answer policy come from them
        group = args.group or self.new_pair
        real, ovl = manifest_group(group)
        self.group = group
        self.base_real, self.base_ovl = real[0], ovl[0]
        first = args.first_unit or next_unit_number(self.tgt)
        self.derivers = [UnitDeriver(self, s, first + i) for i, s in enumerate(self.units)]
        # media keys of the other files of the target course are taken: a later batch must not reuse their slugs
        mine = {d.new_stem for d in self.derivers}
        for fp in (CONTENT / f"realizations/{self.tgt}").glob("*.yaml"):
            if fp.stem in mine:
                continue
            for m in re.finditer(r"content_key:\s*\w+\.\w+\.audio\.(\S+)\.\d+\s*$", fp.read_text(encoding="utf-8"), re.M):
                self.media_slugs.update(x for x in m.group(1).split(".") if x not in ("neutral", "formal", "informal", "polite"))

    def source_vocab(self) -> set[str]:
        """Every word of the source course's realizations (all A1 files), for leftover detection in English text."""
        if getattr(self, "_svocab", None) is None:
            voc: set[str] = set()
            def walk(o):
                if isinstance(o, dict):
                    if isinstance(o.get("text"), str) and self.src in (o.get("language_code"), o.get("language")):
                        voc.update(re.findall(r"[^\W\d_]{3,}", o["text"].casefold()))
                    if isinstance(o.get("title"), str):                      # unit / lesson titles are source-language text
                        voc.update(re.findall(r"[^\W\d_]{3,}", o["title"].casefold()))
                    for v in o.values():
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
            for f in sorted((CONTENT / f"realizations/{self.src}").glob("a[12]_*.yaml")):
                walk(dd.load(f))
            self._svocab = voc
        return self._svocab

    def is_english(self, w: str) -> bool:
        """An English word for the quote-substitution guard: english_words() minus `not_english.json` of the work dir (source words that
        earlier derived courses leaked into English fields until the cross-course vocabulary counts them: 'markt', 'strand')."""
        return w in self.english_words() and w not in set(load_json(self.work / "not_english.json") or [])

    def english_words(self) -> set[str]:
        """English vocabulary: words found (as string values, never keys) in >= 2 files of >= 4 different English-learner courses.
        A word quoted from one target language (Vogel in en-de, perro in en-es) is therefore not English, which the older
        'in >= 10 overlay files' rule could not tell (de-en and en-de overlays quote German hundreds of times)."""
        if getattr(self, "_english", None) is None:
            dirs = [d for d in sorted((CONTENT / "overlays").iterdir())
                    if d.is_dir() and d.name.startswith("en-") and self.src not in d.name.split("-") and d.name != self.new_pair]
            files = [f for d in dirs for f in d.glob("*.yaml")]
            sig = f"{len(files)}:{max((f.stat().st_mtime_ns for f in files), default=0)}:{self.new_pair}"
            cache = self.work / "english_words.cache.json"
            cached = load_json(cache)
            if cached.get("sig") == sig:
                words = set(cached["words"])
            else:
                per: dict[str, Counter] = {}
                for d in dirs:
                    c: Counter = Counter()
                    for f in d.glob("*.yaml"):
                        seen: set[str] = set()
                        for text in yaml_strings(dd.load(f)):
                            seen.update(re.findall(r"[^\W\d_]{3,}", text.casefold()))
                        c.update(seen)
                    per[d.name] = c
                tally: Counter = Counter()
                for c in per.values():
                    tally.update(w for w, n in c.items() if n >= 2)
                words = {w for w, n in tally.items() if n >= 4}
                dump_json(cache, dict(sig=sig, words=sorted(words)))
            self._english = words | {"april", "blond", "receptionist", "popcorn", "concert", "band", "fruit", "giraffe", "croissant", "croissants", "meter",
                                     # English words that a Germanic/Romance course spells the same way
                                     "sport", "sports", "yoga", "computer", "internet", "app", "apps", "hobby", "hobbies", "jogging", "hotel", "taxi", "bus",
                                     "film", "menu", "team", "stress", "test", "tennis", "online", "email", "video", "radio", "jazz", "pizza", "cinema",
                                     "park", "gym", "poster", "sandwich", "toilet", "bar", "pop", "rock", "club", "boss", "plan", "idee"}
        return self._english

    @property
    def en_vocab(self) -> set[str]:
        """Words used in the English fields of the other courses' overlays (anything the source course quotes is not in here)."""
        global _EN_VOCAB
        if _EN_VOCAB is None:
            cnt: Counter = Counter()
            for pair in ("en-de", "en-es", "en-fr", "en-it", "en-pl", "en-ro"):
                if pair in (self.src_pair, self.new_pair):          # never the course being derived: a leak there would legitimise itself
                    continue
                for fp in (CONTENT / f"overlays/{pair}").glob("*.yaml"):
                    toks: set[str] = set()
                    # values only: content keys of derived units still carry source-language slugs (choose_ontbijten) and would
                    # legitimise those words as English
                    for text in yaml_strings(dd.load(fp)):
                        toks.update(re.findall(r"[^\W\d_]{3,}", text.casefold()))
                    cnt.update(toks)
            # a word that only one or two overlay files use is more likely a leak of an earlier derived course than English
            _EN_VOCAB = {w for w, n in cnt.items() if n >= 3}
        return _EN_VOCAB

    @property
    def cast_words(self) -> set[str]:
        self.src_lexicon                                      # loads _src_names / _gloss_words
        return ({w.casefold() for kv in list(self.names_map.items()) for w in kv} | self._src_names | self._gloss_words
                | {"opa", "taalcafé", "taalcafe"})

    @property
    def src_lexicon(self) -> set[str]:
        """Lowercase words of the source target course (every introduced token of its realizations): recognises
        source-language pair sides whose inflected forms occur nowhere else (leest, luistert)."""
        if getattr(self, "_src_lex", None) is None:
            raw: set[str] = set()
            for fp in (CONTENT / f"realizations/{self.src}").glob("*.yaml"):
                for m in re.finditer(r"introduced_tokens:\s*\[([^\]]*)\]", fp.read_text(encoding="utf-8")):
                    raw.update(re.findall(r"[^\W\d_]{2,}", m.group(1)))
            low = {w for w in raw if w[0].islower()}
            self._src_names = {w.casefold() for w in raw if w[0].isupper() and w.casefold() not in low}    # Marieke, Pico: never lowercase
            self._src_lex = {w.casefold() for w in raw}
            # English glosses of the source lexemes are English words even when spelled like a source word (blond)
            self._gloss_words: set[str] = set()
            try:
                spec = importlib.util.spec_from_file_location("bf_src_" + self.src, ROOT / f"scripts/backfill_lexemes_{self.src_pair.split('-')[0]}_{self.src}.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                gl = {}
                for name in dir(mod):
                    d = getattr(mod, name)
                    if name.endswith("GLOSSES") and isinstance(d, dict):
                        gl.update({k: v for k, v in d.items() if isinstance(v, str)})
                keys = {k.casefold() for k in gl}
                for k, v in gl.items():
                    for w in re.findall(r"[^\W\d_]{3,}", v.casefold()):
                        if w not in keys or w == k.casefold():     # glosses quote source words ('komt ... aan'): only real English or a cognate of its own entry (blond)
                            self._gloss_words.add(w)
            except Exception:
                pass
        return self._src_lex

    @property
    def lexicon(self) -> tuple[set[str], set[str]]:
        """(capitalised, lowercase) lexemes already known to the target backfill."""
        if self._lex is None:
            try:
                g = load_backfill(self).GLOSSES
            except (OSError, SystemExit, AttributeError):
                g = {}
            self._lex = ({k for k in g if k[:1].isupper()}, {k for k in g if k[:1].islower()})
        return self._lex

    @property
    def proper_nouns(self) -> set[str]:
        try:
            mod = load_backfill(self)
            return set(getattr(mod, "PROPER_NOUNS", ())) | set(getattr(mod, "POS_SETS", {}).get("proper_noun", ()))
        except (OSError, SystemExit, AttributeError):
            return set()

    case_ok = frozenset({"Sie", "Ihnen", "Ihr", "Ihre", "Ihren", "Ihrem", "Ihrer", "Ihres"})   # formal address: capital is correct mid-sentence

    SPEAKER_SRC = re.compile(r"(?:^|(?<=[.!?] ))[^\W\d_]+(?: [^\W\d_]+)?:\s")
    SPEAKER_FIX = re.compile(r"(?:^|(?<=[.!?] ))([A-ZÉÈ][^\W\d_']*(?: [a-zéèê]+)?) : ")

    def speaker_colon(self, src: str, tr: str) -> str:
        """French typography puts a space before the colon, but a dialogue speaker label must stay `Name: text`
        (the speaker-strip that derives media text and tested spans needs it)."""
        if CFG.get(self.tgt, {}).get("speaker_label_no_space") and self.SPEAKER_SRC.search(src):
            return self.SPEAKER_FIX.sub(r"\1: ", tr)
        return tr

    def names(self, s: str, table: dict | None = None) -> str:
        """Cast / place names in one pass, so a chain (Lotte=Anna, Anna=Petra) never maps twice."""
        if CFG.get(self.tgt, {}).get("straight_apostrophe"):
            s = s.replace("\u2019", "'")
        if table is None and CFG.get(self.tgt, {}).get("arabic_punct") and re.search(r"[\u0621-\u064a]", s):
            s = s.replace("?", "؟").replace(",", "،").replace(";", "؛")

        fold = CFG.get(self.tgt, {}).get("fold_chars")
        if fold:
            s = s.translate(str.maketrans(fold))
        table = self.names_map if table is None else table
        if not table:
            return s
        pat = re.compile(r"\b(" + "|".join(re.escape(a) for a in sorted(table, key=len, reverse=True)) + r")\b")
        return pat.sub(lambda m: table[m.group(1)], s)

    def names_en(self, s: str) -> str:
        return self.names(s, self.names_en_map)

    def add_atom(self, aid, text, kind, en, where, unit):
        self.atoms.setdefault(aid, text)
        c = self.atom_ctx.setdefault(aid, dict(kind=kind, en=[], where=[]))
        if en and en not in c["en"] and len(c["en"]) < 3:
            c["en"].append(en)
        if where and where not in c["where"] and len(c["where"]) < 2:
            c["where"].append(where)
        if kind in ("teach", "title") and c["kind"] in ("media", "prompt", "pair", "quote"):
            c["kind"] = kind
        reg = register_of(text, self.src)
        if reg:
            c["register"] = reg

    def add_author(self, slot, src, kind, ctx, unit):
        self.author.setdefault(slot, src)
        self.author_ctx.setdefault(slot, dict(ctx, kind=kind))

    def build_all(self):
        out = []
        for d in self.derivers:
            out.append((d,) + d.build())
        return out


def plain(o):
    if isinstance(o, dict):
        return {k: plain(v) for k, v in o.items()}
    if isinstance(o, list):
        return [plain(v) for v in o]
    return o


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def dump_json(p: Path, o) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def manifest_group(group: str):
    fp = MANIFEST / f"{group}.txt"
    for line in fp.read_text(encoding="utf-8").splitlines():
        if line.startswith(group + "|"):
            parts = line.split("|")
            return [ROOT / x for x in parts[1].split()], [ROOT / x for x in parts[2].split()]
    raise SystemExit(f"{group!r} missing in {fp}")


def next_unit_number(tgt: str) -> int:
    nums = [int(m.group(1)) for p in (CONTENT / f"realizations/{tgt}").glob("*.yaml")
            if (m := re.match(r"^[ab][12]_unit(\d+)_", p.name))]
    return max(nums, default=0) + 1


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def make_plan(args) -> Plan:
    work = Path(args.work) if args.work else DEFAULT_WORK / (args.new or "en-es")
    work.mkdir(parents=True, exist_ok=True)
    saved = load_json(work / "plan.json")
    args.source = args.source or saved.get("source") or "en-nl"          # without flags the saved plan decides, never the en-es default
    args.new = args.new or saved.get("new") or "en-es"
    if saved.get("new") == args.new:
        args.group = args.group or saved.get("group")
    if not args.units:
        args.units = saved.get("units")
        args.first_unit = args.first_unit or saved.get("first_unit")
        args.names = args.names or saved.get("names")
        args.names_en = getattr(args, "names_en", None) or saved.get("names_en")
        args.suffixes = getattr(args, "suffixes", None) or saved.get("suffixes")
        if not args.units:
            raise SystemExit("--units a1_unitNN_name ... required on first run")
    args.units = apply_level(args.units, getattr(args, "level", None), getattr(args, "force", False))
    return Plan(args, work)


# Dutch-culture A2 units: a localisation decision, not a translation (A1 equivalents: bibliotheek_lenen, afval_scheiden, fiets_huren, rondvaart).
# Refused unless --force; en-es A2 already covers the topic through its own authored unit (tramites).
SKIP_SOURCE_UNITS = {"a1": ("bibliotheek_lenen", "afval_scheiden", "fiets_huren", "rondvaart"), "a2": ("gemeente",)}


def apply_level(units, level, force=False):
    """--level A2: complete bare stems and reject stems of another level; refuse Dutch-culture units (SKIP_SOURCE_UNITS)."""
    out = []
    for u in units or []:
        if level:
            lv = level.lower()
            if re.match(r"^a[12]_unit", u) and not u.startswith(lv + "_"):
                raise SystemExit(f"{u}: --level {level} but the stem is another level")
            if not re.match(r"^a[12]_unit", u):
                u = f"{lv}_{u}"
        m = re.match(r"^(a[12])_unit\d+_(.+)$", u)
        if m and m.group(2) in SKIP_SOURCE_UNITS[m.group(1)]:
            msg = f"{u}: Dutch-culture unit (localisation decision, not a translation)"
            if m.group(1) == "a2" and not force:       # A1 runs keep their old behaviour (warning only)
                raise SystemExit(msg + "; --force to derive it anyway")
            print("warning: " + msg, file=sys.stderr)
        out.append(u)
    return out


def guide(plan: Plan) -> str:
    return f"""# Translator guide: {plan.src_name} -> {plan.new_name} (derive_target)

Files in this folder
  atoms.src.json     {{id: {plan.src_name} text}}  -> write atoms.tr.json {{id: {plan.new_name} text}}   (TRANSLATE)
  atoms.ctx.json     English meaning, kind, register, where used (read only)
  author.src.json    {{slot: text}}  -> write author.tr.json {{slot: ...}}                  (AUTHOR, not translate)
  author.ctx.json    what the slot is for, what the expected answer is
  lexemes.src.json   (after `lexemes`) token needs "gloss | pos"                             (AUTHOR)
  ack.json           {{"<id>:<FLAG>": "why this lint is a false positive"}}

Rules
* Natural {plan.new_name} for the English meaning in atoms.ctx.json, not a calque of the {plan.src_name} wording.
  Keep the cast: write the {plan.src_name} names as they are; --names maps them ({plan.names_map or 'none'}) after translation.
* Register: ctx.register=formal -> usted-style address of the {plan.new_name} formal form; informal -> tu-style.  Match the sibling units.
* Tiles/word order: answers are cut into tiles from the translated sentence; give word-order alternatives (`#alt`)
  ONLY if they use exactly the same words.
* Slots (all values plain strings):
    <ck>#ans   canonical answer || alternative || ...   (fill_in_blank: the blank filler(s))
    <ck>#alt   extra accepted answers || ...  (gender, formal/informal, regional); may be added to ANY answer exercise
    <ck>#dist  wrong {plan.new_name} options || ...      (same count as the source; plausible learner errors in {plan.new_name}, never English)
    <ck>#frame sentence with ___ for the blank (same number of blanks)
    <ck>#tested the short {plan.new_name} span the item tests; must occur in the (translated) audio text
    <ck>#bank  tile1 | tile2 | ...                       (only when the source tiles included distractors)
    <ck>#note / #feedback / #instruction  rewrite in English about {plan.new_name} (the source text discusses {plan.src_name})
* Obligatory contractions are always applied (es del/al, fr du/au, it nel/del...); never list the uncontracted form as a variant.
* Gender: when the learner speaks as themselves with a gendered adjective, add the other gender via `#alt`.
* Lexemes (`lexemes.tr.json`): {{token: "english gloss | pos"}}; for a case-sensitive target a sentence-initial capital of a non-noun
  is written as {{"Hast": "=hast"}} (citation-form alias) next to its own entry {{"hast": "you have (informal) | verb"}}.
{CFG.get(plan.tgt, {}).get("note", "")}
"""


def cmd_extract(args):
    plan = make_plan(args)
    built = plan.build_all()
    w = plan.work
    # keep earlier translations for unchanged text (ids are text hashes)
    dump_json(w / "plan.json", dict(source=plan.src_pair, new=plan.new_pair, units=plan.units,
                                    first_unit=plan.derivers[0].new_no, names=args.names, names_en=getattr(args, "names_en", None), group=plan.group,
                                    suffixes=getattr(args, "suffixes", None)))
    atoms = OrderedDict(sorted(plan.atoms.items(), key=lambda kv: kv[0]))
    dump_json(w / "atoms.src.json", plan.atoms)
    dump_json(w / "atoms.ctx.json", plan.atom_ctx)
    dump_json(w / "author.src.json", plan.author)
    dump_json(w / "author.ctx.json", plan.author_ctx)
    (w / "GUIDE.md").write_text(guide(plan), encoding="utf-8")
    view = []
    for aid, text in plan.atoms.items():
        c = plan.atom_ctx[aid]
        view.append(f"{aid}\t{c['kind']}\t{c.get('register','')}\t{text!r}\t{' / '.join(c['en'])}")
    (w / "atoms.view.tsv").write_text("\n".join(view) + "\n", encoding="utf-8")
    by_kind = defaultdict(int)
    for s, c in plan.author_ctx.items():
        by_kind[c["kind"]] += 1
    todo_a = [a for a in plan.atoms if a not in plan.tr_atoms]
    todo_s = [s for s in plan.author if s not in plan.tr_author and plan.author_ctx[s]["kind"] != "alt"]
    print(f"units: {', '.join(d.new_stem for d in plan.derivers)}")
    print(f"atoms to translate: {len(todo_a)} of {len(plan.atoms)}")
    print(f"author slots: {len(todo_s)} of {len(plan.author) - by_kind.get('alt', 0)}  {dict(by_kind)}")
    print(f"work dir: {w}")


def active_flags(plan: Plan) -> list[dict]:
    out = []
    for f in plan.flags:
        if f"{f['id']}:{f['code']}" in plan.acks:
            continue
        out.append(f)
    return out


def cmd_status(args):
    plan = make_plan(args)
    plan.build_all()
    missing = sorted(plan.missing)
    print(f"missing translations/slots: {len(missing)}")
    for m in missing[:40]:
        print("  ", m)
    fl = active_flags(plan)
    errs = [f for f in fl if f["level"] == "error"]
    print(f"flags: {len(errs)} errors, {len(fl) - len(errs)} warnings")
    for f in fl[:60]:
        print(f"  [{f['level']}] {f['code']} {f['id']}: {f['msg'][:160]}")
    dump_json(plan.work / "report.json", dict(missing=missing, flags=fl))


def new_tokens(plan: Plan, built) -> tuple[dict, object]:
    """Tokens of the derived units that the target backfill has no gloss for.

    Case-sensitive targets (German): a sentence-initial capital of a non-noun (`Hast`) is its own raw token. Give it
    the value `=hast` in lexemes.tr.json to map it to its citation form instead of glossing it as a noun."""
    mod = load_backfill(plan)
    tr = load_json(plan.work / "lexemes.tr.json")
    out: dict[str, dict] = {}
    for d, R, O in built:
        for u in R["units"]:
            for l in u["lessons"]:
                for t in l.get("teaching") or []:
                    for raw in t.get("introduced_tokens") or []:
                        raw = str(raw)
                        alias = tr.get(raw, "")
                        tok = alias[1:].strip() if alias.startswith("=") else mod.normalize(raw)
                        if tok in mod.GLOSSES or tok in out:
                            continue
                        info = dict(example=t["target"]["text"], en=(O["teaching"].get(t["content_key"]) or {}).get("gloss"),
                                    unit=d.new_stem)
                        if plan.cs and tok[:1].isupper() and tok[:1].lower() + tok[1:] in mod.GLOSSES:
                            info["hint"] = f"capitalised: gloss as a NEW noun, or write '={tok[:1].lower() + tok[1:]}' if it is only a sentence-initial form"
                        elif plan.cs and tok[:1].isupper():
                            info["hint"] = "capitalised: a noun/proper noun, or '=lowercase' (and gloss that) for a sentence-initial verb/adjective/pronoun"
                        out[tok] = info
    return out, mod


def load_backfill(plan: Plan):
    path = ROOT / f"scripts/backfill_lexemes_{plan.src_pair.split('-')[0]}_{plan.tgt}.py"
    spec = importlib.util.spec_from_file_location("bf_" + plan.tgt, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_lexemes(args):
    plan = make_plan(args)
    built = plan.build_all()
    if plan.missing & set(plan.atoms):
        raise SystemExit("translate atoms.src.json first (atoms missing: %d)" % len(plan.missing & set(plan.atoms)))
    toks, _mod = new_tokens(plan, built)
    tr = load_json(plan.work / "lexemes.tr.json")
    dump_json(plan.work / "lexemes.src.json", {t: "" for t in toks})
    dump_json(plan.work / "lexemes.ctx.json", toks)
    todo = [t for t in toks if t not in tr]
    print(f"new tokens needing a gloss: {len(toks)} ({len(todo)} not yet in lexemes.tr.json)")
    print("format: {token: 'english gloss | pos'}   pos in noun verb adjective adverb pronoun preposition particle phrase proper_noun (noun is the default)")


GEN_BEGIN = "# --- derive_target.py: derived units (generated; keep markers) ---"
GEN_END = "# --- end derive_target.py ---"


def write_backfill_block(plan: Plan, lex: dict[str, str], allowed: set[str] | None = None) -> Path:
    path = ROOT / f"scripts/backfill_lexemes_{plan.src_pair.split('-')[0]}_{plan.tgt}.py"
    text = path.read_text(encoding="utf-8")
    existing: dict[str, tuple[str, str]] = {}
    cites: dict[str, str] = {}
    if GEN_BEGIN in text:
        block = text[text.index(GEN_BEGIN):text.index(GEN_END)]
        m = re.search(r"DERIVED_TARGET_GLOSSES: dict\[str, str\] = (\{.*?\n\})\nDERIVED_TARGET_POS", block, re.S)
        g = eval(m.group(1)) if m else {}  # literal dict written by this tool
        m2 = re.search(r"DERIVED_TARGET_POS: dict\[str, str\] = (\{.*?\n\})\n", block, re.S)
        p = eval(m2.group(1)) if m2 else {}
        m3 = re.search(r"DERIVED_TARGET_CITATION: dict\[str, str\] = (\{.*?\n\})\n", block, re.S)
        cites = eval(m3.group(1)) if m3 else {}
        for k, v in g.items():
            existing[k] = (v, p.get(k, "noun"))
    for tok, val in lex.items():
        if val.strip().startswith("="):                      # sentence-initial form -> citation form
            cites[tok] = val.strip()[1:].strip()
            continue
        if allowed is not None and tok not in existing and tok not in allowed:
            continue                                # a token already glossed by the hand-written table stays there
        gloss, _, pos = val.rpartition("|")
        if not _:                                   # no "|": the whole value is the gloss
            gloss, pos = val, ""
        existing[tok] = (gloss.strip(), pos.strip() or "noun")
    gl = "{\n" + "".join(f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v[0], ensure_ascii=False)},\n" for k, v in sorted(existing.items())) + "}"
    ps = "{\n" + "".join(f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v[1])},\n" for k, v in sorted(existing.items()) if v[1] != "noun") + "}"
    cs = "{\n" + "".join(f"    {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in sorted(cites.items())) + "}"
    cite_code = ("if DERIVED_TARGET_CITATION and \"CITATION_FORMS\" in globals():\n    CITATION_FORMS.update(DERIVED_TARGET_CITATION)\n"
                 if cites else "")
    block = (f"{GEN_BEGIN}\n"
             f"DERIVED_TARGET_GLOSSES: dict[str, str] = {gl}\nDERIVED_TARGET_POS: dict[str, str] = {ps}\n"
             f"DERIVED_TARGET_CITATION: dict[str, str] = {cs}\n" + cite_code +
             "for _tok, _gloss in DERIVED_TARGET_GLOSSES.items():\n    GLOSSES.setdefault(_tok, _gloss)\n"
             "for _tok, _pos in DERIVED_TARGET_POS.items():\n    POS_SETS.setdefault(_pos, set()).add(_tok)\n"
             f"{GEN_END}\n")
    if GEN_BEGIN in text:
        text = text[:text.index(GEN_BEGIN)] + block + text[text.index(GEN_END) + len(GEN_END) + 1:]
    else:
        anchor = 'POS_SETS["noun"] = set(GLOSSES)'
        if anchor not in text:
            raise SystemExit(f"{path.name}: anchor {anchor!r} not found")
        text = text.replace(anchor, block + "\n" + anchor, 1)
    path.write_text(text, encoding="utf-8")
    return path


def cmd_inject(args):
    plan = make_plan(args)
    built = plan.build_all()
    if plan.missing and not args.allow_missing:
        raise SystemExit(f"{len(plan.missing)} translations/slots missing (run `status`): {sorted(plan.missing)[:8]}")
    fl = active_flags(plan)
    errs = [f for f in fl if f["level"] == "error"]
    for f in fl:
        print(f"[{f['level']}] {f['code']} {f['id']}: {f['msg'][:200]}")
    if errs and not args.force:
        raise SystemExit(f"{len(errs)} lint errors; fix them or acknowledge in ack.json (or --force)")
    # lexemes
    toks, _mod = new_tokens(plan, built)
    lex = load_json(plan.work / "lexemes.tr.json")
    missing_lex = [t for t in toks if t not in lex]
    if missing_lex and not args.skip_lexemes:
        raise SystemExit(f"{len(missing_lex)} tokens lack a gloss (run `lexemes`, fill lexemes.tr.json): {missing_lex[:10]}")
    written = []
    new_real, new_ovl = [], []
    for d, R, O in built:
        rp = CONTENT / f"realizations/{plan.tgt}/{d.new_stem}.yaml"
        op = CONTENT / f"overlays/{plan.new_pair}/{d.level}_unit{d.new_no:02d}.yaml"
        dd.dump(plain(R), rp)
        dd.dump(plain(O), op)
        written += [rp, op]
        new_real.append(rp.relative_to(ROOT).as_posix())
        new_ovl.append(op.relative_to(ROOT).as_posix())
    update_manifest(plan.group, new_real, new_ovl)
    if not args.skip_lexemes and lex:
        # all of lexemes.tr.json: gloss entries and `=citation` aliases (an alias target may not occur as a raw token itself)
        written.append(write_backfill_block(plan, dict(lex), None))
    for p in written:
        print("wrote", p.relative_to(ROOT))


def update_manifest(group: str, real: list[str], ovl: list[str]) -> None:
    fp = MANIFEST / f"{group}.txt"
    lines = fp.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if line.startswith(group + "|"):
            parts = line.split("|")
            r, o = parts[1].split(), parts[2].split()
            r += [x for x in real if x not in r]
            o += [x for x in ovl if x not in o]
            if len(r) != len(o):
                raise SystemExit("manifest realization/overlay counts differ")
            line = "|".join([parts[0], " ".join(r), " ".join(o)])
        out.append(line)
    fp.write_text("\n".join(out) + "\n", encoding="utf-8")


def cmd_check(args):
    plan = make_plan(args)
    py = ROOT / ".content-venv/bin/python"
    py = str(py if py.exists() else sys.executable)
    real, ovl = manifest_group(plan.group)
    rc = 0
    for cmd in (
        [py, "scripts/compile_content.py", "validate", "--realization", *map(str, real), "--overlay", *map(str, ovl)],
        [py, "scripts/compile_content.py", "compile", "--realization", *map(str, real), "--overlay", *map(str, ovl), "--out", str(plan.work / "compiled.json")],
        [py, f"scripts/backfill_lexemes_{plan.src_pair.split('-')[0]}_{plan.tgt}.py", "--dry-run"],
        # Dutch text left in the derived course (English feedback/notes, target text): see scripts/_dutch_leftover_check.py
        [py, "scripts/_dutch_leftover_check.py", "--pairs", plan.new_pair, "--quiet"],
    ):
        print("$", " ".join(cmd[:3]), "...")
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        tail = (r.stdout + r.stderr).strip().splitlines()[-6:]
        print("\n".join(tail))
        rc |= r.returncode
    return rc


# ---------------------------------------------------------------------------
# Practice packs (Endless Practice + unit checkpoint) for the derived units
# ---------------------------------------------------------------------------
PACK_GOOD_POS = ["noun", "verb", "adjective", "adverb"]
PACK_POS_ALL = ["symbol", "noun", "proper_noun", "pronoun", "verb", "adjective", "adverb", "preposition", "particle", "phrase"]
TOKEN_WORD = re.compile(r"(?:[^\W\d_]|[\u0900-\u0963\u0971-\u097f])+(?:['\u2019-](?:[^\W\d_]|[\u0900-\u0963\u0971-\u097f])+)*", re.U)


def _plain_en(s: str, limit: int = 230) -> str:
    s = re.sub(r"[*{}]", "", s or "")
    s = " ".join(s.split())
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "."


def _lesson_no(ck: str) -> str:
    return re.search(r"\.(lesson\d+)\.", ck).group(1)


def pack_sentences(lesson: dict, O: dict, minw: int = 3, maxw: int = 11):
    """Single-sentence teaching lines of one lesson: (text, english gloss or None, note or None)."""
    out = []
    for t in lesson.get("teaching") or []:
        ck = t["content_key"]
        ov = (O.get("teaching") or {}).get(ck) or {}
        gl = ov.get("gloss") if isinstance(ov.get("gloss"), str) else None
        eg = ov.get("example_gloss")
        eg = [eg] if isinstance(eg, str) else (eg or [])
        texts = [(t["target"]["text"], gl)]
        exs = t.get("example")
        exs = [exs] if isinstance(exs, dict) else (exs or [])
        for i, e in enumerate(exs):
            texts.append((e["text"], eg[i] if i < len(eg) else None))
        for text, gloss in texts:
            raw = text
            m = re.match(rf"^(?:[^\W\d_]|[{DEV}])+:\s+(.)", text)
            if m:
                if not (m.group(1).isupper() or m.group(1) in "¿¡"):     # "Atención: el tren ..." is not a speaker label
                    continue
                text = re.sub(rf"^(?:[^\W\d_]|[{DEV}])+:\s+", "", text)
                if gloss:
                    gloss = re.sub(rf"^(?:[^\W\d_]|[{DEV}])+:\s+", "", gloss)
            if re.search(r"[:→{}\n]", text) or len(re.findall(r"[.!?]", text)) != 1 or not re.search(r"[.!?]$", text):
                continue
            n = len(TOKEN_WORD.findall(text))
            if minw <= n <= maxw:
                out.append((text, gloss, ov.get("note") if raw == t["target"]["text"] else None))
    return out


def build_pack(plan: Plan, d: "UnitDeriver", specs_all: list, excl: set[str]) -> tuple[Path, dict]:
    tp, sp = plan.tgt, plan.src
    R = dd.load(CONTENT / f"realizations/{tp}/{d.new_stem}.yaml")
    O = dd.load(CONTENT / f"overlays/{plan.new_pair}/{d.level}_unit{d.new_no:02d}.yaml")
    unit = R["units"][0]
    nn = d.new_no
    pair = plan.new_pair
    specs = [s for s in specs_all if s["lesson_content_key"].startswith(f"{tp}.{d.level}.unit{nn:02d}.")]
    wtag = lambda s: next(x for x in s["agreement_tags"]["semantic"] if x.startswith("w_"))
    good, seen = [], set()
    for s in specs:
        tok, gl = s["token"], s["english_gloss"]
        base = re.sub(r"\s*\([^)]*\)", "", gl).split(";")[0].strip().lower()
        if (s["part_of_speech"] in PACK_GOOD_POS and re.fullmatch(rf"(?:[^\W\d_]|[{DEV}]){{3,}}", tok) and tok not in excl
                and base not in seen):
            seen.add(base)
            good.append(dict(token=tok, tag=wtag(s), gloss=gl, lesson=s["lesson_content_key"], pos=s["part_of_speech"]))
    if len(good) < 3:
        raise SystemExit(f"{d.new_stem}: only {len(good)} usable lexemes for a pack (need >= 3 for recognition templates)")
    pool_tags = [g["tag"] for g in good]
    lesson_by_ck = {l["content_key"]: l for l in unit["lessons"]}
    en_lesson_title = lambda ck: ((O.get("lessons") or {}).get(ck) or {}).get("title") or ""
    # lessons that own lexemes, in order
    lex_lessons = []
    for s in specs:
        if s["lesson_content_key"] not in lex_lessons:
            lex_lessons.append(s["lesson_content_key"])
    good_lessons = list(OrderedDict.fromkeys(g["lesson"] for g in good))
    counters: dict[str, int] = defaultdict(int)
    templates: list[dict] = []
    used_tags: set[str] = set(pool_tags)

    def key(lesson_ck: str, verb: str) -> str:
        ln = _lesson_no(lesson_ck)
        counters[ln] += 1
        return f"practice.{pair}.{tp}.{d.level}.unit{nn:02d}.{ln}.{verb}.{counters[ln]:03d}"

    def frame(text: str, lang: str, **kw) -> dict:
        rtl = lang == tp and CFG.get(tp, {}).get("script") == "arabic"
        return dict(text=text, language_code=lang, direction="rtl" if rtl else "ltr", **kw)

    content = dict(language_code=tp, part_of_speech=PACK_GOOD_POS, agreement_tags=dict(semantic=pool_tags))

    def anchor(g: dict) -> dict:
        used_tags.add(g["tag"])
        return dict(language_code=tp, part_of_speech=g["pos"], agreement_tags=dict(semantic=g["tag"]))

    # -- unit-wide recognition / production / matching templates, spread over the lessons that own lexemes
    plan_generic = ["choose", "listen", "translate", "match", "choose", "translate"]
    for i, verb in enumerate(plan_generic):
        lck = good_lessons[i % len(good_lessons)]
        title = en_lesson_title(lck)
        if title.split(",")[0].split(" ")[0] not in set(plan.names_map.values()):         # 'Marco, Chiara and Luca on animals' keeps its capitals
            title = title.lower()
        title = title or "this unit"
        fb = frame(f"{{item}} is one of this unit's words, from the lesson on {_plain_en(title, 80)}.", "en")
        if verb in ("choose", "listen"):
            templates.append(dict(content_key=key(lck, verb), lesson_content_key=lck,
                                  type="multiple_choice" if verb == "choose" else "listen_select",
                                  frame=frame("{item}", tp), slots=dict(item=content),
                                  answer_derivation=dict(kind="slot_gloss", slot="item"), feedback_frame=fb))
        elif verb == "translate":
            templates.append(dict(content_key=key(lck, verb), lesson_content_key=lck, type="translation",
                                  frame=frame("{item}", "en", slot_rendering=dict(item="english_gloss")),
                                  slots=dict(item=content), answer_derivation=dict(kind="slot_text", slot="item"),
                                  feedback_frame=fb))
        elif verb == "match" and len(good) >= 6:
            names = ["first", "second", "third", "fourth", "fifth", "sixth"]
            templates.append(dict(content_key=key(lck, verb), lesson_content_key=lck, type="matching_pairs",
                                  frame=frame(" · ".join("{%s}" % n for n in names), tp),
                                  slots={n: content for n in names},
                                  slot_relations=[dict(kind="distinct", slots=names)],
                                  answer_derivation=dict(kind="matching_pairs", slots=names),
                                  feedback_frame=frame(f"Match each {plan.new_name} word with its English meaning; the words come from this unit's lessons.", "en")))
    # -- sentence-based structured / production templates anchored to single lexemes
    rot = ["order", "fill", "translate"]
    for lck in good_lessons:
        lesson = lesson_by_ck[lck]
        here = [g for g in good if g["lesson"] == lck]
        # sentences of this lesson first, then of the rest of the unit (the anchor lexeme's own lesson stays the template's lesson)
        sents = pack_sentences(lesson, O)
        for other in unit["lessons"]:
            if other is not lesson:
                sents += pack_sentences(other, O)
        made = 0
        used_sent: set[str] = set()
        for g in here:
            if made >= 3:
                break
            for text, gloss, note in sents:
                if text in used_sent:
                    continue
                words = TOKEN_WORD.findall(text)
                if words.count(g["token"]) != 1 or words.index(g["token"]) == 0:
                    continue
                m = re.search(rf"(?<![\w{DEV}]){re.escape(g['token'])}(?![\w{DEV}])", text)
                if not m:
                    continue
                blank = text[:m.start()] + "{item}" + text[m.end():]
                verb = rot[made % 3]
                if verb == "translate" and not (gloss and "{" not in gloss):
                    verb = "order"
                fbtxt = _plain_en((gloss + " " if gloss else "") + (note or f"{g['token']} means {g['gloss']}."))
                slots = dict(item=anchor(g))
                if verb == "order":
                    tpl = dict(type="word_order", frame=frame(blank, tp), slots=slots,
                               answer_derivation=dict(kind="render_frame", frame=frame(blank, tp)))
                elif verb == "fill":
                    slots["hint"] = anchor(g)
                    tpl = dict(type="fill_in_blank", frame=frame(blank + " ({hint})", tp, slot_rendering=dict(hint="english_gloss")),
                               slots=slots, answer_derivation=dict(kind="slot_text", slot="item"))
                else:
                    tpl = dict(type="translation", frame=frame(gloss, "en"), slots=slots,
                               answer_derivation=dict(kind="render_frame", frame=frame(blank, tp)))
                tpl.update(content_key=key(lck, {"word_order": "order", "fill_in_blank": "fill", "translation": "translate"}[tpl["type"]]),
                           lesson_content_key=lck, feedback_frame=frame(fbtxt, "en"))
                ordered = dict(content_key=tpl["content_key"], lesson_content_key=lck, type=tpl["type"], frame=tpl["frame"],
                               slots=tpl["slots"], answer_derivation=tpl["answer_derivation"], feedback_frame=tpl["feedback_frame"])
                templates.append(ordered)
                used_sent.add(text)
                made += 1
                break
    notes = (f"Generated by scripts/derive_target.py packs from the unit's realization/overlay and the {pair} backfill lexemes "
             f"(tags {tp}_{d.level}_u{nn} / w_<token>). {len(good)} pool lexemes (pos noun/verb/adjective/adverb, one gloss each); "
             f"unit-wide choose/listen/translate/match templates use the union of their w_ tags, sentence templates are single-lexeme "
             f"anchors on the unit's own teaching lines. Needs native review of frames and feedback.")
    pack = OrderedDict(
        schema_version="1.0", pack_key=f"practice.{pair}.{d.level}.unit{nn:02d}", source_language=plan.src_pair.split("-")[0],
        target_language=tp, unit_content_key=unit["content_key"],
        review=OrderedDict(status="unreviewed", required_next_reviewer="native_speaker_review", fresh_context="false", notes=notes),
        tag_schema=OrderedDict(part_of_speech=PACK_POS_ALL, agreement_tags=OrderedDict(semantic=sorted(used_tags))),
        templates=templates)
    path = CONTENT / f"practice/{pair}/{d.level}_unit{nn:02d}.yaml"
    return path, pack


def cmd_packs(args):
    import yaml
    plan = make_plan(args)
    sys.path.insert(0, str(ROOT / "scripts"))
    bf = importlib.import_module(f"backfill_lexemes_{plan.src_pair.split('-')[0]}_{plan.tgt}")
    specs_all = list(bf.iter_specs())
    excl = set(load_json(plan.work / "packs_exclude.json").get("tokens", []))
    paths = []
    for d in plan.derivers:
        path, pack = build_pack(plan, d, specs_all, excl)
        path.parent.mkdir(parents=True, exist_ok=True)
        class D(yaml.SafeDumper):
            pass
        D.add_representer(OrderedDict, lambda dumper, o: dumper.represent_mapping("tag:yaml.org,2002:map", o.items()))
        path.write_text(yaml.dump(pack, Dumper=D, sort_keys=False, allow_unicode=True, width=10000, default_flow_style=None), encoding="utf-8")
        paths.append(path.relative_to(ROOT).as_posix())
        print("wrote", paths[-1], f"({len(pack['templates'])} templates)")
    fp = MANIFEST.parent / "practice" / f"{plan.new_pair}.txt"
    lines = fp.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if line.startswith(plan.new_pair + "|"):
            head, _, rest = line.partition("|")
            cur = set(rest.split()) | set(paths)
            line = head + "|" + " ".join(sorted(cur))
        out.append(line)
    fp.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("updated", fp.relative_to(ROOT))


def cmd_fixintro(args):
    """Inflected targets (Polish): an exercise tests or shows a case/person form of a lemma the lesson only introduced in another form
    (`uwielbiam` vs `uwielbiać`). Runs the compiler validation and adds the reported tokens (errors and the matching_pairs / prompt warnings) to the introduced_tokens of the last teaching
    item of that lesson (a form the learner sees in the exercise's own sentence). Re-run after every inject; review the printed list."""
    plan = make_plan(args)
    py = ROOT / ".content-venv/bin/python"
    py = str(py if py.exists() else sys.executable)
    real, ovl = manifest_group(plan.group)
    r = subprocess.run([py, "scripts/compile_content.py", "validate", "--realization", *map(str, real), "--overlay", *map(str, ovl)],
                       cwd=ROOT, capture_output=True, text=True)
    mine = {f"{d.new_stem}.yaml" for d in plan.derivers}
    todo: dict[tuple[str, int], set[str]] = defaultdict(set)
    for line in (r.stdout + r.stderr).splitlines():
        m = re.match(r"(?:ERROR|WARN): (\S+?):realization\.units\[0\]\.lessons\[(\d+)\]\..*?(?:tokens not introduced in this or an earlier lesson|untaught tokens): (.+)$", line)
        if m and Path(m.group(1)).name in mine:
            todo[(m.group(1), int(m.group(2)))] |= {t.strip() for t in m.group(3).split(",")}
    for (path, li), toks in sorted(todo.items()):
        doc = dd.load(Path(path))
        teaching = doc["units"][0]["lessons"][li]["teaching"]
        item = teaching[-1]
        have = item.setdefault("introduced_tokens", [])
        add = [t for t in sorted(toks) if t not in have]
        have.extend(add)
        dd.dump(doc, Path(path))
        print(f"{Path(path).name} lesson {li + 1}: +{add} (review: the form is only shown in the exercise sentence)")
    print(f"fixintro: {sum(len(v) for v in todo.values())} tokens in {len(todo)} lessons")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("extract", cmd_extract), ("status", cmd_status), ("lexemes", cmd_lexemes),
                     ("inject", cmd_inject), ("check", cmd_check), ("packs", cmd_packs), ("fixintro", cmd_fixintro)):
        p = sub.add_parser(name)
        p.add_argument("--source", help="source course pair (default: the saved plan, else en-nl)")
        p.add_argument("--new", help="new target course pair (default: the saved plan, else en-es)")
        p.add_argument("--group", help="manifest group receiving the units (default = --new)")
        p.add_argument("--units", nargs="*", help="source realization stems, e.g. a1_unit23_money (A2: a2_unit78_afgelopen_weekend)")
        p.add_argument("--level", choices=("A1", "A2", "a1", "a2"), help="CEFR level of --units: bare stems (unit78_afgelopen_weekend) get this prefix, "
                       "and a stem of another level is an error; A2 is the default group-less path (use --group en-es-a2)")
        p.add_argument("--first-unit", type=int, help="unit number of the first derived unit (default: next free)")
        p.add_argument("--names", help="cast map, e.g. Lotte=Elena,Omar=Mateo")
        p.add_argument("--names-en", dest="names_en", help="cast map for the English fields when the target script is not Latin, e.g. Lotte=Nastya,Omar=Dima (default: --names)")
        p.add_argument("--suffixes", help="topic name map for file names / unit keys, e.g. sporten=sport,vervoer=verkehr")
        p.add_argument("--work")
        p.add_argument("--allow-missing", action="store_true")
        p.add_argument("--skip-lexemes", action="store_true")
        p.add_argument("--force", action="store_true")
        p.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    return args.fn(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
