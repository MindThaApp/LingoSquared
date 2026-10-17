#!/usr/bin/env python3
"""Idempotently backfill target-side en-nl Dutch A1+A2 lexemes.

Run with ``--dry-run`` to parse and classify content without importing the
application or connecting to PostgreSQL.  The realization files' complete
``introduced_tokens`` inventories are authoritative.

Extended repeatedly through 2026-07-06 (most recently units 17-19: work/
occupation, housing, weather, added by a parallel session -- and units 20-23:
clothing, emotions, communication, money, added by this pass -- together
closing the en-nl practice-pool gap behind its lesson content, which goes
through unit23) to keep pace with new practice-template packs -- see
docs/content/practice/en-nl/a1_unit01.yaml onward. (Docstring corrected
2026-07-06 after a fresh-context review pass flagged it as stale -- it
previously said "units 1-7" long after the code had been extended well past
that.)

**Real bug fixed 2026-07-07 (Dutch QA pass)**: this script used to have NO
A2 handling at all -- ``UNIT_FILES`` only ever globbed ``a1_unit*.yaml``
(<=23), so every A2 lexeme (units 24-28: bureaucracy/opinions/banking/
health/housing) was silently never backfilled, for as long as A2 content
has existed -- meaning Endless Practice/SRS had zero lexeme pool for any
A2-introduced vocabulary. Root cause: "Dutch A1" and "Dutch A2" import as
TWO SEPARATE course rows (`POST /admin/content/import` dedups by
`(source_language, target_language, title)`, and the A2 overlay declares a
distinct `course.title: Dutch A2`) -- same root cause already found and
fixed for fa/prs in `backfill_lexemes.py`/`backfill_lexemes_fa_en.py`/
`backfill_lexemes_prs_en.py`. Fixed by adding `UNIT_FILES_A2` (its own
LOCAL 1-based unit ordering, looked up against the separate "Dutch A2"
course) and restructuring `iter_specs()`/`main()` to classify and backfill
each level against its own course, matching that established pattern.

**Extended 2026-07-11** to cover the four new Dutch A2 units 74-77 (travel
disruption, screen time/online habits, weekly schedule, shopping
complaint/returns) that ``UNIT_FILES_A2``'s broad ``a2_unit*_*.yaml`` glob
picked up automatically -- their lexemes were unclassified, so
``nl_agreement_tags()``'s ``lesson_categories[unit_lesson]`` lookup raised
``KeyError: 'er_is_een_vertraging'`` (unit74's own first lesson) the moment
any of these units' tokens were classified. Fixed by adding the same three
things every prior unit round added: ``NL_GLOSSES`` entries (hand-classified
from each unit's own overlay glosses/notes, never guessed), POS-set
membership (``NOUNS``/``VERBS``/``ADJECTIVES``/``ADVERBS``/``PREPOSITIONS``/
``PARTICLES``/``PROPER_NOUNS``/``PRONOUNS``), and ``lesson_categories``
entries for each of the 24 new lesson content_keys across the four units.
Deliberately did NOT add the finer-grained per-unit ``semantic`` slot-preset
tags (like unit73's ``job_interview_vocab``/``job_role_noun``) beyond a
handful of broad recognition-only vocab tags -- those fine frame-specific
tags were added in prior units specifically to support a practice-template
authoring pass, and no ``docs/content/practice/en-nl/a2_unit7[4-7].yaml``
pack exists yet (only through unit28), so there is nothing yet to wire them
into; add them alongside that future practice-template pass instead of
speculatively now.

**Extended again 2026-07-11**, same day, for that deferred practice-
template pass: ``docs/content/practice/en-nl/a2_unit74.yaml`` through
``a2_unit77.yaml`` now exist, so ``nl_agreement_tags()`` gained one
single-member ``*_single`` semantic tag per lesson's hero full-sentence
frame (25 new tags total, one block per unit, placed right after each
unit's existing broad recognition-only block) -- e.g.
``reisvertraging_vertraging_single``, ``schermtijd_scherm_single``,
``drukkeweek_daarna_single``, ``terugbrengen_koptelefoon_single``. Every
one has exactly one member by construction (a single ``t == "token"``
check), which is what makes it safe to embed in a fixed multi-word
``render_frame``/``slot_text`` template (AUTHORING_GUIDE.md #17) without
a candidate-pool grammaticality judgment call -- the existing broader
per-unit vocab/verb tags (``travel_disruption_vocab``, etc.) are still
used as-is, unchanged, for the bare-word ``multiple_choice``/
``listen_select``/``matching_pairs`` templates in the same four packs.

**Extended 2026-07-11** to cover the Dutch B1 course (units 01-11, all now
`status: reviewed`), which was imported to the DB but entirely absent from
this script -- B1 lessons were creating zero Lexeme rows, so B1 content
never fed the lexeme-level SRS or practice pool. B1 is a SEPARATE course
row from A1/A2 ("Dutch B1", not "Dutch A1"/"Dutch A2" -- same
`(source_language, target_language, title)` course-dedup pattern already
documented above for A2), so it gets its own `UNIT_FILES_B1` glob (all 11
files match `b1_unit*_*.yaml` with no gaps, every one hand-glossed below,
same discipline UNIT_FILES_A2 established) and its own `_classify_nl(...,
"b1")` call in `iter_specs()`/`courses_by_level` entry in `main()`. Every
genuinely new `introduced_tokens` value across all 11 units was
hand-classified from each overlay's own `gloss`/`example_gloss` fields, not
guessed. Real homograph/polysemy collisions found and handled the same way
prior rounds established (see "zijn"/"over" notes elsewhere in this
docstring): capitalized "Steeds" (B1's "steeds meer" = "more and more,"
grammatically distinct from the pre-existing lowercase "steeds" = "still,"
part of "nog steeds") and capitalized "Beste" (B1's email-salutation "Beste
collega's," = "Dear colleagues," distinct from the pre-existing lowercase
"beste" = "best," the unit14 superlative) were each given their OWN fresh
NL_GLOSSES entry rather than reused, since case-sensitive dict keys make
this safe with zero risk to the pre-existing lowercase/uppercase sibling.
Same treatment for lowercase "stad" (B1's common noun "the city," distinct
from the pre-existing capitalized "Stad," a unit14 comparison-ad placeholder
brand/product name classified as a proper noun) and lowercase "groet" (B1's
common noun "regards; greeting" inside "met vriendelijke groet," distinct
from the pre-existing capitalized "Groet," a unit11 standalone message-
closing PHRASE). Genuine same-meaning case variants (e.g. lowercase "zou"/
"misschien"/"geweldig"/"sommige"/"alles"/"vorige" reusing the gloss already
established for their capitalized sentence-initial siblings, and vice versa
for "Ken"/"Later"/"Soms"/"Nu"/"Vorige") were reused directly, same
convention as every prior round's `for _token in (...)` case-variant blocks.
Deliberately did NOT add the finer-grained per-unit `semantic` slot-preset
tags beyond the blanket `lesson_categories` entry per lesson -- no
`docs/content/practice/en-nl/b1_unit*.yaml` pack exists yet, same "add
those alongside a future practice-template authoring pass instead of
speculatively now" discipline the A2 unit 74-77 round already established.
`wrapup_production` (B1's own review lesson in every one of the 11 units)
reuses one shared generic `lesson_categories` value across all 11 units --
same intentional bare-suffix-collision-reuse precedent already established
for `advertentie_lezen`/`bonnetje_lezen`/`een_kaartje_kopen` elsewhere in
this file (all 11 lessons really are the same kind of generic unit-review
wrapup, so one shared descriptive tag is correct, not a bug).

**Extended 2026-07-22** to the last 33 unclassified A1 units -- 34-42
(technology, education, birthdays, chores, neighbourhood, post, cooking,
personality, colours) and 49-72 (the errand/outing service-encounter arc).
Before this, ``UNIT_FILES`` globbed only 1-23 / 29-33 / 43-48, so those 33
units produced ZERO lexemes and their unit checkpoints could never generate
(``generate_checkpoint()`` needs lexemes AND templates scoped to the unit's
own lessons, and hard-fails ``checkpoint_unavailable`` under 12 items). A1
lexemes go 1073 -> 1406. Full rationale, the three deliberate departures from
how earlier rounds did this (sentence-initial capitals are FOLDED rather than
registered; de/het gender and singular/plural are recorded; per-unit slot tags
are provided up front rather than deferred), and the hand-checked homograph
merges are all documented in the big block comment above
``NL_CITATION_FORMS``. A2 and B1 output is byte-identical to before this
change (verified spec-by-spec); for A1 the change is purely additive -- no
gloss, part of speech or semantic tag was removed from any pre-existing
lexeme.

**The same change fixed a live data-corruption bug.** ``_classify_nl()``
derives ``unit_order`` from the file's POSITION in ``UNIT_FILES``, which
``main()`` then matches against the imported course's ``Unit.order`` -- and
``Unit.order`` comes from scripts/content_manifest.txt, which lists every a1
file. Skipping units the manifest imports therefore silently shifted every
later unit's provenance: a1_unit43 sat at position 29 while DB unit.order 29
was a1_unit34, so 79 lexemes claiming units 43-48 were written onto units
34-39's lesson rows -- the clean 9-unit offset (= the 9 skipped files 34-42)
reported the same day. See the INVARIANT note on ``UNIT_FILES``. NOTE FOR
WHOEVER RUNS THE BACKFILL NEXT: re-running this script does NOT repair
already-misattached rows. ``main()``'s update branch only rewrites
``english_gloss`` and ``agreement_tags`` on an existing ``Lexeme``; it never
touches ``provenance_lesson_id`` / ``provenance_lesson_content_key``. The 79
bad rows need an explicit DB fix (or a delete-and-reimport of the en-nl A1
lexemes) -- fixing the script is necessary but not sufficient.

Known limitation surfaced while extending this (units 5-6): this script keys
its in-memory `specs` dict by bare token string, and `nl_part_of_speech()` is
a pure function of the token with no context -- so a genuine homograph across
units (same spelling, different part of speech/meaning) can only ever get ONE
classification, whichever set the token happens to sit in. Concretely: "zijn"
already means "are" (verb, from units 1-4) and unit05 introduces "zijn"
meaning "his" (possessive pronoun) -- the second sense silently never gets
its own lexeme row; the token stays classified as the verb, with the verb's
english_gloss. Practice templates must NOT rely on "zijn" (his) as a
generation slot value until this is fixed (needs POS-aware/context-aware
keying); bake it as literal frame text instead, same as this pack's
a1_unit05.yaml does for its zijn_haar lesson templates.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Extended 2026-07-09 (practice-template depth-closing pass) to also cover
# units 29-33 (hobbies/appearance/animals/sports/transportation) -- these are
# file-numbered units appended after unit23 in scripts/content_manifest.txt's
# en-nl line (still the same "Dutch A1" course, not a level change; see each
# realization file's own review.notes for why the file numbering jumps).
# Units 24-28 are NOT included here -- those are the SEPARATE "Dutch A2"
# course, handled below by UNIT_FILES_A2. Extended 2026-07-12 to include
# the next reviewed A1 Endless Practice coverage batch, units 43-48.
#
# **Extended 2026-07-22 to 29-72 (i.e. every a1_unit*_*.yaml on disk), and
# this was ALSO the fix for a live data-corruption bug -- read this before
# ever narrowing the range again.**
#
# `_classify_nl()` derives `unit_order` from `enumerate(unit_files, 1)`, i.e.
# the POSITION of the file inside this tuple, and `main()` then looks that
# number up against the imported course's real `Unit.order`. `Unit.order` is
# assigned from scripts/content_manifest.txt's en-nl line, which lists EVERY
# a1 file on disk. So the moment this glob SKIPS a unit that the manifest
# imports, every later unit's position silently drifts and its lexemes get
# attached to the WRONG lesson rows -- with no error anywhere, because the
# lookup still finds *a* lesson.
#
# That is exactly what happened: with the old 1-23 / 29-33 / 43-48 filter,
# a1_unit43 sat at position 29 while the DB's unit.order 29 was a1_unit34
# (units 34-42 were on disk and imported, but skipped here). Result: 79
# en-nl A1 lexemes claiming units 43-48 were written onto units 34-39's
# lesson rows -- the clean 9-unit offset (exactly the 9 skipped files
# 34-42) reported 2026-07-22. Including 34-42 and 49-72 below restores
# position == unit.order for the whole course.
#
# INVARIANT: this tuple must stay a CONTIGUOUS prefix-matching mirror of the
# en-nl line in scripts/content_manifest.txt. Never skip a unit the manifest
# imports. (A1 numbering legitimately jumps 23 -> 29 because 24-28 are the
# separate "Dutch A2" course and are absent from the A1 manifest line too,
# so that gap does NOT desynchronise the positions.)
UNIT_FILES = tuple(sorted(
    p for p in (REPO_ROOT / "docs/content/realizations/nl").glob("a1_unit*_*.yaml")
    if 1 <= int(p.name[len("a1_unit"):len("a1_unit")+2]) <= 23
    or 29 <= int(p.name[len("a1_unit"):len("a1_unit")+2]) <= 72
))

# A2 units (24-28: bureaucracy, opinions, banking, health, housing) live in a
# SEPARATE course row ("Dutch A2", not "Dutch A1") -- `POST /admin/content/
# import` matches/creates courses by (source_language, target_language,
# title), and every a2_unit*.yaml overlay declares `course.title: Dutch A2`,
# distinct from A1's `Dutch A1`. Real bug found live 2026-07-07 (Dutch QA
# pass), same root cause already found and fixed in backfill_lexemes.py/
# backfill_lexemes_fa_en.py/backfill_lexemes_prs_en.py for fa/prs: this used
# to have NO A2 handling at all -- UNIT_FILES above only ever globbed
# a1_unit*.yaml (<=23), so every A2 lexeme (units 24-28) was silently never
# backfilled, for as long as A2 content has existed. Kept as its own tuple
# with LOCAL 1-based ordering (looked up against the "Dutch A2" course
# separately in main(), never mixed with UNIT_FILES' indices) -- unit.order
# is assigned per-course at compile/import time (see scripts/
# content_manifest.txt's separate "en-nl"/"en-nl-a2" compile groups), so a2_
# unit24 is unit.order=1 within the "Dutch A2" course, not 24.
#
# Restricted to the files scripts/content_manifest.txt's en-nl-a2 line
# actually imports. A realization file can sit on disk before it is wired
# into the course (e.g. a2_unit78_afgelopen_weekend.yaml, a pilot still
# awaiting native review): the DB has no Unit/Lesson rows for it and
# lesson_categories has no entries for its lessons, so globbing it in
# crashed nl_agreement_tags() with KeyError: 'wat_heb_je_gedaan'. Mirroring
# the manifest also keeps position == unit.order, the same invariant
# UNIT_FILES documents above.
def _manifest_realizations(group: str) -> frozenset[str]:
    manifest = REPO_ROOT / "scripts/content_manifest.txt"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.startswith(group + "|"):
            return frozenset(line.split("|")[1].split())
    raise SystemExit(f"{group!r} group missing from {manifest}")


_A2_MANIFEST = _manifest_realizations("en-nl-a2")
UNIT_FILES_A2 = tuple(sorted(
    p for p in (REPO_ROOT / "docs/content/realizations/nl").glob("a2_unit*_*.yaml")
    if p.relative_to(REPO_ROOT).as_posix() in _A2_MANIFEST
))

# B1 units (01-11: hypothetical situations, opinion/nuance, workplace
# meetings, relative clauses, indirect speech, obligations, ability/kunnen-
# konden, real/unreal conditionals, agreement/disagreement, work
# responsibilities, storytelling) live in a THIRD separate course row
# ("Dutch B1", not "Dutch A1"/"Dutch A2") -- added 2026-07-11, same
# course-dedup reasoning as UNIT_FILES_A2's own comment above. A plain glob
# is safe here (matching UNIT_FILES_A2's own precedent) because all 11 real
# files match `b1_unit*_*.yaml` with no gaps and no numbers past 11 exist
# yet, and every token every one of them introduces is hand-glossed below --
# this glob does NOT get to silently pick up a future, not-yet-glossed
# b1_unit12+ file the way a broader A1-style range-filtered glob would need
# re-auditing for; a genuinely new B1 unit added later will still hard-crash
# this script (by design, see the module-level KeyError note above) until
# someone extends this file again.
UNIT_FILES_B1 = tuple(sorted(
    (REPO_ROOT / "docs/content/realizations/nl").glob("b1_unit*_*.yaml")
))

UNIT_FILES_B2 = tuple(sorted(
    (REPO_ROOT / "docs/content/realizations/nl").glob("b2_unit*_*.yaml")
))

# C1 units (01-08: extended discourse, implicature, register control,
# concession, counterfactuals, idiom, mediation, persuasion) are a FIFTH
# separate course row ("Dutch C1"). Same plain-glob reasoning as B1/B2: every
# token every one of the 8 files introduces is hand-glossed in the C1 block
# below, and a future c1_unit09+ will hard-crash this script until glossed.
UNIT_FILES_C1 = tuple(sorted(
    (REPO_ROOT / "docs/content/realizations/nl").glob("c1_unit*_*.yaml")
))

# Each lexical gloss is deliberately atomic. Capitalized sentence-initial forms
# below reuse the same hand-authored gloss as their lowercase lexical form.
NL_GLOSSES = {
    "'s": "in the (fixed time expression)",
    "Aangenaam": "pleased to meet you", "Belgisch": "Belgian", "België": "Belgium",
    "Duits": "German", "Duitsland": "Germany", "Egypte": "Egypt", "Engels": "English",
    "Goedemiddag": "good afternoon", "Goedemorgen": "good morning", "Goedenavond": "good evening",
    "Hallo": "hello", "Hoi": "hi", "Lotte": "Lotte", "Medewerker": "staff member",
    "Nederland": "the Netherlands", "Nederlands": "Dutch", "Noor": "Noor", "Omar": "Omar",
    "Prima": "fine; great", "Taalcafé": "language café", "Workshop": "workshop",
    "Pauze": "break", "Welkom": "welcome",
    "aan": "at; on", "acht": "eight", "achtentwintig": "twenty-eight",
    "achtentwintigste": "twenty-eighth", "achtenveertig": "forty-eight", "achtste": "eighth",
    "achttien": "eighteen", "achttiende": "eighteenth", "april": "April", "augustus": "August",
    "avond": "evening", "avonds": "in the evening", "begint": "starts", "behalve": "except",
    "beleefd": "polite", "ben": "am; are", "bent": "are (polite)", "bibliotheek": "library",
    "bij": "at; by", "bijdrage": "fee; contribution", "boek": "book", "boeken": "books",
    "cent": "cent", "dag": "day", "dan": "then", "dank": "thanks", "dat": "that",
    "datum": "date", "de": "the", "december": "December", "derde": "third",
    "dertien": "thirteen", "dertiende": "thirteenth", "dertig": "thirty", "dertigste": "thirtieth",
    "dinsdag": "Tuesday", "dit": "this", "donderdag": "Thursday", "drie": "three",
    "drieëntwintigste": "twenty-third", "drieënveertig": "forty-three", "dus": "so",
    "eenendertigste": "thirty-first", "eenentwintig": "twenty-one", "eenentwintigste": "twenty-first",
    "eenheid": "unit", "eerste": "first", "elf": "eleven", "elfde": "eleventh", "en": "and",
    "er": "there", "euro": "euro", "februari": "February", "formeel": "formal", "gaat": "goes; is going",
    "geen": "no; not any", "groep": "group", "half": "half", "halverwege": "halfway",
    "heb": "have", "heet": "am called; are called", "hele": "whole", "herhalen": "repeat",
    "het": "the; it", "hier": "here", "hoe": "how", "hoeveelste": "which numbered date",
    "hoofdletter": "capital letter", "huisnummer": "house number", "ik": "I", "in": "in",
    "informeel": "informal", "inleverdatum": "due date", "inschrijven": "register; sign up",
    "is": "is", "jaar": "year", "januari": "January", "je": "you; your (informal)",
    "jij": "you (informal, stressed)", "jou": "you (informal object)", "juli": "July", "juni": "June",
    "keer": "time; occasion", "kom": "come", "komt": "comes; come (polite)", "kost": "costs",
    "krijgen": "get; receive", "kwart": "quarter", "kwartier": "quarter-hour", "laat": "late; what time",
    "leer": "learn", "maand": "month", "maandag": "Monday", "maart": "March", "me": "myself; me",
    "mei": "May", "mensen": "people", "met": "with", "middag": "afternoon", "middags": "in the afternoon",
    "mijn": "my", "moet": "must; is due", "na": "after", "naam": "name", "naar": "toward; to",
    "nacht": "night", "nachts": "at night", "negen": "nine", "negende": "ninth",
    "negenennegentig": "ninety-nine", "negenentwintigste": "twenty-ninth", "negentien": "nineteen",
    "negentiende": "nineteenth", "negentig": "ninety", "nieuw": "new", "normaal": "normally",
    "november": "November", "nul": "zero", "nummer": "number", "ochtend": "morning",
    "ochtends": "in the morning", "of": "or", "oktober": "October", "om": "at (a time); around",
    "ontmoeten": "meet", "ook": "also; too", "op": "on; at", "open": "open", "oud": "old",
    "over": "past; after", "rooster": "schedule", "september": "September", "slecht": "bad",
    "spreek": "speak", "stoelen": "chairs", "taalcafé": "language café", "tachtig": "eighty",
    "tafel": "table", "te": "to", "telefoonnummer": "phone number", "terug": "back; returned",
    "tien": "ten", "tiende": "tenth", "tiental": "multiple of ten", "tijd": "time", "tot": "until; see you",
    "twaalf": "twelve", "twaalfde": "twelfth", "twee": "two", "tweede": "second",
    "tweeëndertig": "thirty-two", "tweeëntwintig": "twenty-two", "tweeëntwintigste": "twenty-second",
    "tweeënveertig": "forty-two", "twintig": "twenty", "twintigste": "twentieth", "u": "you (polite)",
    "uit": "from; out of", "uur": "hour; o'clock", "vandaag": "today", "vandaan": "from",
    "veertien": "fourteen", "veertiende": "fourteenth", "veertig": "forty", "vier": "four",
    "vierde": "fourth", "vierentwintigste": "twenty-fourth", "vijf": "five", "vijfde": "fifth",
    "vijfentwintigste": "twenty-fifth", "vijfenzestig": "sixty-five", "vijfenzeventig": "seventy-five",
    "vijftien": "fifteen", "vijftiende": "fifteenth", "vijftig": "fifty", "volgende": "next",
    "voor": "for; before", "vrijdag": "Friday", "vrijdagmiddag": "Friday afternoon", "vóór": "before",
    "wanneer": "when", "wat": "what", "week": "week", "welke": "which", "wil": "want",
    "woensdag": "Wednesday", "woon": "live; reside", "workshop": "workshop", "zaal": "room; hall",
    "zaterdag": "Saturday", "zes": "six", "zesde": "sixth", "zesentwintigste": "twenty-sixth",
    "zestien": "sixteen", "zestiende": "sixteenth", "zestig": "sixty", "zeven": "seven",
    "zevende": "seventh", "zevenentachtig": "eighty-seven", "zevenentwintigste": "twenty-seventh",
    "zeventien": "seventeen", "zeventiende": "seventeenth", "zeventig": "seventy", "ziens": "seeing",
    "zijn": "are", "zitten": "sit; are sitting", "zondag": "Sunday", "één": "one",
}

NL_GLOSSES.update({
    "Dagen": "days", "Goed": "good; well", "hoeveel": "how many; how much",
    "Inleverdatum": "due date", "ja": "yes", "kun": "can",
    "leuk": "nice; pleasant",
    "Maanden": "months", "nee": "no", "niet": "not", "waar": "where", "wij": "we",
})

# Unit 5 (family) and unit 6 (food/ordering), added 2026-07-05.
NL_GLOSSES.update({
    "vader": "father", "moeder": "mother", "ouders": "parents", "broer": "brother",
    "zus": "sister", "kind": "the child", "kinderen": "the children", "een": "a; an",
    "opa": "grandfather", "oma": "grandmother", "oom": "uncle", "tante": "aunt",
    "neef": "male cousin; nephew", "nicht": "female cousin; niece",
    "gezin": "family (household)", "wonen": "live; reside", "Rotterdam": "Rotterdam",
    "hebben": "have (plural/infinitive)", "jouw": "your (emphatic)", "Dit": "this",
    "haar": "her", "heet": "am called; are called", "Sander": "Sander (a Dutch male name)",
    "Fenna": "Fenna (a Dutch female name)", "Jan": "Jan (a Dutch male name)",
    "Marieke": "Marieke (a Dutch female name)", "elke": "every", "maand": "month",
    "Heb": "have", "broers": "brothers", "zussen": "sisters", "Geen": "no; not any",
    "Wonen": "live; reside", "Utrecht": "Utrecht", "familie": "family (relatives in general)",
    "maar": "but", "woont": "lives; resides", "Amsterdam": "Amsterdam",
    "Zie": "see (imperative/question form)", "hem": "him", "vaak": "often",
    "koffie": "coffee", "thee": "tea", "water": "water", "melk": "milk", "sap": "juice",
    "brood": "bread", "broodje": "sandwich roll", "kaas": "cheese", "appel": "apple",
    "wil": "want", "graag": "gladly; please (with wil)", "alstublieft": "please (formal)",
    "alsjeblieft": "please (informal)", "wilt": "want (with u, formal)",
    "drinken": "to drink; drink", "eten": "to eat; eat", "appelsap": "apple juice",
    "Mag": "may; can (polite)", "Menukaart": "menu", "Koffie": "coffee",
    "Thee": "tea", "Broodje": "sandwich roll", "Appelsap": "apple juice",
    "iets": "something", "Komt": "comes", "eraan": "on its way (part of komt eraan)",
})

# Unit 7 (shopping at the market), added 2026-07-05.
NL_GLOSSES.update({
    "markt": "the market", "winkel": "the shop", "kraam": "the stall",
    "appels": "apples", "peren": "pears", "tomaten": "tomatoes", "paprika's": "bell peppers",
    "kilo": "a kilo", "per": "per", "honderd": "hundred", "gram": "grams",
    "pond": "a pound (500 grams)", "500": "500", "stuk": "one piece; one item",
    "stuks": "pieces; items", "prijskaartje": "the price label",
    "Appels": "Apples", "Peren": "Pears", "Tomaten": "Tomatoes", "Paprika's": "Bell peppers",
    "mag": "may; can (polite)", "neem": "take", "Anders": "otherwise; anything else",
    "nog": "still; else", "kan": "can", "Kan": "can", "pinnen": "pay by card",
    "Verkoper": "vendor", "natuurlijk": "of course", "Bedankt": "thanks",
})

# Unit 9 (asking for and giving directions), added 2026-07-06.
NL_GLOSSES.update({
    "links": "left", "rechts": "right", "linksaf": "to the left; turn left",
    "rechtsaf": "to the right; turn right", "rechtdoor": "straight ahead",
    "ga": "go", "sla": "turn", "loop": "walk", "Ga": "Go", "Sla": "Turn",
    "Loop": "Walk", "vanaf": "from", "route": "the route", "START": "START",
    "DOEL": "DESTINATION", "Route": "Route", "Graag": "gladly", "gedaan": "done",
})

# Unit 10 (describing a daily routine), added 2026-07-06.
NL_GLOSSES.update({
    "opstaan": "to get up", "sta": "get up (with ik)", "zich": "oneself (reflexive)",
    "aankleden": "to get dressed", "kleed": "get dressed (with ik)",
    "ontbijten": "to have breakfast", "ontbijt": "have breakfast (with ik)",
    "werken": "to work", "werk": "work (with ik)", "eet": "eat (with ik)",
    "afwassen": "to do the dishes", "was": "do the dishes (with ik)",
    "af": "off (separable prefix)", "slapen": "to sleep", "slaap": "sleep (with ik)",
    "In": "In", "gewone": "ordinary", "hoofdzin": "main clause", "deel": "part",
    "einde": "end", "scheidbaar": "separable", "achteraan": "at the end",
    "07": "07", "eerst": "first", "daarna": "after that", "Eerst": "First",
    "Daarna": "After that", "Na": "After", "staat": "stands; is placed",
    "werkwoord": "verb", "ziet": "sees; looks", "eruit": "out (part of 'looks like')",
    "pas": "not until; only",
})

# Unit 11 (making simple plans), added 2026-07-06.
NL_GLOSSES.update({
    "samen": "together", "film": "the film", "gaan": "to go", "Zullen": "Shall",
    "we": "we", "activiteit": "activity", "manier": "way; manner",
    "stellen": "to propose (part of voorstellen)", "zin": "desire; mood",
    "idee": "idea", "goed": "good", "plan": "the plan", "Sorry": "Sorry",
    "want": "because", "korte": "short", "reden": "reason", "maakt": "makes",
    "afwijzing": "decline; refusal", "vriendelijk": "friendly",
    "afspreken": "to arrange to meet", "geeft": "gives", "afspraak": "appointment",
    "17": "17", "bericht": "the message", "uitnodiging": "the invitation",
    "Groet": "Regards", "zullen": "shall", "Vrijdag": "Friday", "kort": "short",
    "staan": "to stand; to be placed", "spreken": "to speak (part of afspreken)",
})

# Unit 12 (talking about recent events, perfect tense), added 2026-07-06.
NL_GLOSSES.update({
    "gesprekken": "conversations", "gebruik": "use", "voltooide": "completed",
    "gebeurtenis": "event", "meestal": "usually", "voltooid": "completed",
    "deelwoord": "participle", "gedronken": "drank; drunk", "gegaan": "went; gone",
    "Denk": "think", "eindpositie": "end position", "meeste": "most",
    "werkwoorden": "verbs", "gebruiken": "to use", "gegeten": "ate; eaten",
    "gewerkt": "worked", "kopen": "to buy", "gekocht": "bought", "Bij": "With",
    "komen": "to come", "gekomen": "came; come", "gisteren": "yesterday",
    "vanmorgen": "this morning", "Gisteren": "Yesterday", "Vanmorgen": "This morning",
    "Daar": "There",
})

# Unit 13 (expressing preferences), added 2026-07-06.
NL_GLOSSES.update({
    "lekker": "tasty; nice", "vinden": "to find; to consider",
    "vind": "find; consider (with ik)", "Vind": "Find; consider",
    "tomatensoep": "tomato soup", "activiteiten": "activities",
    "fietsen": "to cycle", "wandelen": "to walk", "winkelen": "to shop",
    "doen": "to do", "Houden": "To love; to be fond of", "drukt": "expresses",
    "sterke": "strong", "algemene": "general", "voorkeur": "preference",
    "houd": "love; am fond of (with ik)", "muziek": "music", "films": "films",
    "Zeg": "Say", "smaak": "taste", "Wil": "Want", "liever": "rather; prefer",
    "blauwe": "blue", "trui": "sweater", "Liever": "Rather; prefer",
    "zien": "to see", "ene": "the one", "optie": "option", "boven": "over; above",
    "andere": "other", "kiest": "chooses", "houdt": "loves; is fond of",
    "Hij": "He", "park": "the park", "zo": "so",
})

# Unit 14 (making comparisons), added 2026-07-06.
NL_GLOSSES.update({
    "vergelijkingen": "comparisons", "voeg": "add", "toe": "to (separable prefix)",
    "bijvoeglijk": "adjectival", "naamwoord": "word; noun", "groot": "big",
    "klein": "small", "rugzak": "the backpack", "groter": "bigger", "tas": "the bag",
    "kleiner": "smaller", "vijfenveertig": "forty-five", "duur": "expensive",
    "goedkoop": "cheap", "duurder": "more expensive", "goedkoper": "cheaper",
    "Gebruik": "Use", "net": "just", "plus": "plus", "als": "as; if",
    "dingen": "things", "gelijk": "equal", "vergelijken": "to compare",
    "Deze": "This", "mooi": "nice-looking; pretty", "die": "that",
    "praktisch": "practical", "superlatief": "superlative", "st": "-st (suffix)",
    "Van": "Of", "deze": "this", "duurst": "most expensive", "beter": "better",
    "best": "best", "onregelmatig": "irregular", "beste": "best (attributive)",
    "keuze": "choice", "Veel": "Much; many", "meer": "more", "meest": "most",
    "werkt": "works", "dezelfde": "the same", "lange": "long", "treinreis": "train trip",
    "heeft": "has", "ruimte": "room; space", "Bergsport": "Bergsport",
    "sterk": "strong", "Schoudertas": "Shoulder bag", "Stad": "City",
    "lichter": "lighter", "minder": "less", "reis": "trip", "sterker": "stronger",
    "grote": "big", "nodig": "necessary", "Precies": "Exactly", "precies": "exactly",
    "mooist": "prettiest", "schoudertas": "the shoulder bag", "licht": "light (weight)",
    "koop": "buy (with ik)", "Koop": "Buy", "vorm": "form", "koopt": "buys",
    "zij": "she; they", "hij": "he; it",
})

# Unit 15 (traveling by train), added 2026-07-06.
NL_GLOSSES.update({
    "kaartje": "the ticket", "Wilt": "Would (want, formal)", "enkele": "single (one-way)",
    "retour": "the return ticket", "balie": "the counter", "beleefde": "polite",
    "perron": "the platform", "welk": "which", "vertrekt": "departs", "trein": "the train",
    "vertraging": "the delay", "Let": "Pay (attention)", "plaats": "place",
    "minuten": "minutes", "ingang": "the entrance", "uitgang": "the exit",
    "wachtruimte": "the waiting room", "Rechtdoor": "Straight ahead",
    "Kaartje": "Ticket", "Centraal": "Central", "Vertrek": "Departure",
    "Aankomst": "Arrival", "Retour": "Return", "Prijs": "Price", "We": "We",
    "moeten": "must; need to", "daar": "there", "bord": "the sign",
    "probleem": "the problem", "O": "Oh", "al": "already", "Perron": "Platform",
    "stappen": "to step",
})

# Unit 16 (describing a basic health problem), added 2026-07-06.
NL_GLOSSES.update({
    "voel": "feel (with ik)", "ziek": "sick", "hoofdpijn": "a headache",
    "buikpijn": "a stomach ache", "scheelt": "is the matter", "keelpijn": "a sore throat",
    "Gaat": "Goes", "koorts": "a fever", "verkouden": "having a cold", "Ziek": "Sick",
    "bijvoeglijke": "adjectival", "naamwoorden": "words; nouns", "Koorts": "Fever",
    "zelfstandige": "substantive (noun-like)", "apotheek": "the pharmacy",
    "Waarmee": "With what", "helpen": "to help", "Heeft": "Has", "tegen": "for; against",
    "tablet": "a tablet", "Neem": "Take", "Advies": "Advice", "Rust": "Rest",
    "drink": "drink", "veel": "much; a lot", "Voel": "Feel", "dagen": "days",
    "steeds": "still (part of nog steeds)", "huisarts": "the family doctor",
    "Nog": "Still; not yet", "moe": "tired", "genomen": "taken", "nu": "now",
    "rusten": "to rest", "Beterschap": "Get well soon", "Dank": "Thanks",
    "morgen": "tomorrow",
})

# Unit 17 (work and occupation), added 2026-07-06. "werk" is already
# classified as a VERB (ik-form of werken, from unit10's daily-routine
# content) -- this unit also uses "werk" as a NOUN ("Wat doe je voor
# werk?", object of "voor"), the same token/different-POS homograph
# limitation documented in this file's module docstring (see the "zijn"
# note). Per that established precedent, "werk" is NOT given a new
# noun-generative tag; that question phrase is baked as literal frame
# text in the practice template instead of using "werk" as a fillable
# slot value.
NL_GLOSSES.update({
    "Elke": "Every", "Sommige": "Some", "Ze": "she", "Zij": "She",
    "baan": "job", "begin": "start (with ik)", "benieuwd": "curious",
    "beroep": "the occupation", "denk": "think (with ik)", "doe": "do (with je)",
    "eigen": "own", "eigenlijk": "actually", "extra": "extra",
    "kantoor": "office", "kok": "cook", "krijgt": "gets",
    "later": "later", "maak": "make (with je)", "pauze": "the break",
    "restaurant": "restaurant", "ritme": "rhythm", "stop": "stop; finish (with ik)",
    "uren": "hours", "verpleegkundige": "nurse", "vroeg": "early",
})

# Unit 18 (housing), added 2026-07-06.
NL_GLOSSES.update({
    "Appartement": "Apartment", "altijd": "always", "appartement": "the apartment",
    "badkamer": "the bathroom", "balkon": "the balcony", "fijn": "nice",
    "gezellig": "cozy", "kamers": "rooms", "keuken": "the kitchen",
    "klinkt": "sounds", "langs": "by (part of 'komen langs', to come by/visit)",
    "nieuwe": "new (inflected)", "slaapkamer": "the bedroom", "slaapkamers": "bedrooms",
    "snel": "soon; quickly", "tuin": "the garden", "welkom": "welcome",
    "woonkamer": "the living room", "zeggen": "to say",
})

# Unit 19 (weather), added 2026-07-06.
NL_GLOSSES.update({
    "Als": "If", "Laten": "Let's", "Morgen": "Tomorrow", "Perfect": "Perfect",
    "Weerbericht": "Weather forecast", "Zaterdag": "Saturday", "Zondag": "Sunday",
    "bewolkt": "cloudy", "binnen": "inside", "blijven": "stay (with we)",
    "kijken": "watch (with we)", "koud": "cold", "maken": "to make",
    "regent": "is raining", "wandeling": "the walk", "warm": "warm",
    "weekend": "the weekend", "weer": "the weather", "weerbericht": "the weather forecast",
    "zonnig": "sunny",
})

# Unit 20 (buying clothes), added 2026-07-06.
NL_GLOSSES.update({
    "jas": "the coat", "trui": "the sweater", "broek": "the pants; the trousers",
    "schoenen": "the shoes", "maat": "the size", "Welke": "Which",
    "zwart": "black", "blauw": "blue", "past": "fits", "Past": "Fits",
    "passen": "to try on; to fit", "klein": "small", "groot": "big",
    "negentig": "ninety", "Winterjas": "winter coat", "kleur": "the color",
    "warm": "warm", "zoek": "look for (with ik)", "M": "M",
    "Natuurlijk": "Of course", "neemt": "takes (with hij/zij)",
    "nemen": "to take",
})

# Unit 21 (expressing feelings), added 2026-07-06.
NL_GLOSSES.update({
    "blij": "happy", "verdrietig": "sad", "boos": "angry",
    "omdat": "because", "regent": "rains", "zenuwachtig": "nervous",
    "voor": "for; about", "zorgen": "worries", "Maak": "Make",
    "Waarom": "Why", "voelt": "feels", "zich": "oneself; himself/herself",
    "alleen": "alone", "Maar": "But", "nieuwe": "new", "baan": "job",
    "appartement": "apartment", "beetje": "a bit", "denk": "think (with ik)",
    "kunt": "can (with je/jij)", "eerlijk": "honest(ly)", "gezegd": "said",
    "helpt": "helps", "vast": "surely; definitely", "trots": "proud",
    "dienst": "shift", "heel": "very; really", "echt": "really; truly",
})

# Unit 22 (calling and texting), added 2026-07-06.
NL_GLOSSES.update({
    "bellen": "to call", "bel": "call (with ik)", "Met": "This is",
    "wie": "who", "U": "You (polite)", "herhalen": "to repeat",
    "snel": "fast; quickly", "hoor": "hear (with ik)",
    "horen": "to hear", "sms": "the text message", "stuur": "send (with ik)",
    "later": "later", "terug": "back", "belt": "calls",
    "Fijn": "Nice", "fijn": "nice", "ging": "went", "dacht": "thought",
    "betekent": "means", "spreekt": "speaks", "Spreek": "Speak",
    "wel": "indeed; well", "vertellen": "to tell", "Zijn": "His",
    "denken": "to think",
})

# Unit 23 (money and paying), added 2026-07-06.
NL_GLOSSES.update({
    "totaal": "total", "Totaal": "Total", "pinnen": "to pay by card",
    "contant": "cash", "betalen": "to pay", "Hier": "Here",
    "rekening": "the bill", "Rekening": "Bill", "delen": "to split; to share",
    "apart": "separately", "afrekenen": "to settle the bill; to pay",
    "wisselgeld": "the change", "nodig": "needed", "vijfendertig": "thirty-five",
    "vijfentwintig": "twenty-five", "hoofdgerechten": "main courses",
    "koffies": "coffees", "Betaald": "Paid", "pin": "card (payment)",
    "Zullen": "Shall", "vragen": "to ask for", "goed": "good",
    "idee": "idea", "betaalt": "pays", "Jij": "You",
    "hebt": "have (with jij)", "geholpen": "helped", "lief": "sweet; kind",
    "uw": "your (formal)", "mij": "me",
})

# A2 unit 24 (gemeente/bureaucracy: registering with local authorities),
# added 2026-07-07.
NL_GLOSSES.update({
    "schrijven": "write (part of 'inschrijven', to register)",
    "Zou": "Would (conditional of zullen)", "schikken": "to suit; to be convenient",
    "paspoort": "the passport", "huurcontract": "the rental contract",
    "geboorteakte": "the birth certificate", "geldig": "valid",
    "Moet": "Must; do (need to)", "meenemen": "to bring along",
    "Sinds": "Since", "adres": "the address", "sinds": "since",
    "vorige": "previous; last", "BSN": "the BSN (Citizen Service Number)",
    "persoonlijke": "personal (inflected)", "overheid": "the government",
    "DigiD": "DigiD (Dutch digital identity system)", "online": "online",
    "zaken": "matters; affairs", "regelen": "to arrange",
    "gemeente": "the municipality", "documenten": "documents",
    "indien": "if", "toepassing": "application (van toepassing, applicable)",
    "vooraf": "in advance", "inschrijving": "the registration",
    "ontvangt": "receives", "post": "the mail; post",
    "Ambtenaar": "Official (civil servant)", "waarmee": "with what; how",
    "Alstublieft": "Here you go; please (formal)",
    "Alles": "Everything", "orde": "order (in orde, in order)",
    "paar": "a couple; a few (in 'een paar')", "Geweldig": "Great; wonderful",
    "hulp": "the help", "ingeschreven": "registered (past participle of inschrijven)",
})

# A2 unit 25 (meningen/opinions: giving opinions with reasons), added 2026-07-07.
NL_GLOSSES.update({
    "fietspad": "the bike path", "mening": "the opinion",
    "Volgens": "According to", "gevaarlijk": "dangerous", "smal": "narrow",
    "eens": "agreed; in agreement (het eens zijn, to agree)",
    "gedeeltelijk": "partially", "Aan": "On (aan de andere kant, on the other hand)",
    "kant": "the side", "veiliger": "safer", "bespaart": "saves",
    "voetgangers": "the pedestrians", "weinig": "little; not much",
    "snap": "understand (with ik)", "fietsers": "cyclists",
    "ze": "they; she (unstressed)", "pad": "the path", "breder": "wider",
    "helemaal": "completely; entirely", "mee": "along; with (mee eens, in agreement)",
    "auto": "the car", "s": "'s (possessive/plural marker, as in auto's)",
    "straat": "the street", "Misschien": "Maybe", "wordt": "becomes",
    "vindt": "thinks; finds (with hij/zij)",
})

# A2 unit 26 (bankrekening/banking: opening a bank account), added 2026-07-07.
NL_GLOSSES.update({
    "bankrekening": "the bank account", "openen": "to open",
    "betaalrekening": "the payment/checking account", "salaris": "the salary",
    "Uw": "Your (formal)", "werkgever": "the employer",
    "stort": "deposits (with hij/zij)", "Storten": "To deposit",
    "infinitief": "the infinitive", "identiteitsbewijs": "the identity document",
    "Heeft": "Have; has (formal question form)", "bankpas": "the bank card",
    "app": "the app", "mobiel": "mobile", "bankieren": "to bank (do banking)",
    "gebruikt": "uses", "storten": "to deposit", "geopend": "opened",
})

# A2 unit 27 (huisarts/health: a doctor's visit), added 2026-07-07.
NL_GLOSSES.update({
    "bezoek": "the visit", "klachten": "symptoms; complaints", "erg": "very",
    "pijn": "the pain", "griepje": "a mild flu; a cold", "waarschijnlijk": "probably",
    "ernstig": "serious", "Maakt": "Make (formal imperative)",
    "recept": "the prescription", "schrijf": "prescribe; write (with ik)",
    "pillen": "the pills", "rust": "rest (imperative, with u)",
    "innemen": "to take (medicine)", "terugkomen": "to come back",
    "infinitieven": "infinitives", "scheidbare": "separable (inflected)",
    "Diagnose": "Diagnosis", "voorgeschreven": "prescribed",
    "Voelt": "Feel(s) (formal)", "Huisarts": "Doctor (family doctor/GP)",
    "vervelend": "unpleasant; annoying", "dokter": "the doctor",
})

# A2 unit 28 (probleem melden/housing: reporting a maintenance issue),
# added 2026-07-07.
NL_GLOSSES.update({
    "verwarming": "the heating", "monteur": "the technician; repairman",
    "morgenochtend": "tomorrow morning", "melding": "the report; notification",
    "vierentwintig": "twenty-four", "contact": "contact",
    "Bevestiging": "Confirmation", "ontvangen": "received",
    "thuis": "at home", "Bel": "Call (imperative)",
    "woningcorporatie": "the housing corporation",
    "Woningcorporatie": "Housing corporation",
    "gisteravond": "last night; yesterday evening", "sturen": "to send",
    "Tussen": "Between",
})

# Unit 29 (hobbies: free-time activities), added 2026-07-09 by the
# practice-template depth-closing pass (see UNIT_FILES' own comment for the
# file-numbering context -- still the "Dutch A1" course).
NL_GLOSSES.update({
    "lezen": "to read", "sporten": "to exercise; to play sports",
    "koken": "to cook", "sport": "exercise; play sports (with ik)",
    "kook": "cook (with ik)", "vrienden": "friends", "vrije": "free (inflected)",
    "lees": "read (with ik)", "luisteren": "to listen",
    "tekenen": "to draw", "teken": "draw (with ik)", "gamen": "to game",
    "luister": "listen (with ik)", "game": "game (with ik)",
    "soms": "sometimes", "nooit": "never", "elk": "every (neuter)",
    "de-woorden": "de-words (common-gender nouns)", "zoals": "such as; like",
    "het-woorden": "het-words (neuter nouns)", "Kook": "Cook",
    "kookt": "cooks", "ontspannend": "relaxing", "Game": "Game",
    "hobby's": "hobbies", "weet": "know (with ik)", "buiten": "outside",
    "ons": "us", "allebei": "both", "zie": "see (with ik)",
})

# Unit 30 (appearance: describing people), added 2026-07-09.
NL_GLOSSES.update({
    "lang": "tall; long", "jong": "young", "Oud": "Old",
    "aantal": "number; amount", "jaren": "years", "betekenen": "to mean",
    "indruk": "impression", "zonder": "without", "getal": "a number",
    # "Opa" (capitalized) is a real homograph-of-case with the already-
    # classified common noun "opa" (unit05, "grandfather") -- here it is
    # used as a name-like reference to Lotte's specific grandfather, the
    # same convention as the capitalized Sander/Fenna/Nina proper nouns.
    "Opa": "Grandpa (Lotte's grandfather, used as a name)",
    "blond": "blond", "bruin": "brown", "grijs": "grey",
    # "Haar" (capitalized, the noun "hair") is a genuine homograph-of-case
    # with the already-classified possessive pronoun "haar" (her, unit05).
    # Since nl_part_of_speech() keys on the exact token, this capitalized
    # form gets its OWN classification (noun) rather than colliding with
    # the lowercase possessive.
    "Haar": "Hair",
    "woord": "word", "lidwoord": "the article (grammar term)",
    "blijft": "remains; stays", "ogen": "eyes", "groen": "green",
    "meervoud": "the plural", "bruine": "brown (inflected)",
    "groene": "green (inflected)", "meisje": "the girl", "Nina": "Nina",
    "Oké": "Okay", "herken": "recognize (with ik)",
    "anders": "different(ly)", "langer": "taller; longer", "Je": "You",
    "kent": "know (with hij/zij/je)", "patroon": "the pattern",
})

# Unit 31 (animals and pets), added 2026-07-09.
NL_GLOSSES.update({
    "dier": "the animal", "huisdier": "the pet", "hond": "the dog",
    "kat": "the cat", "vis": "the fish", "vogel": "the bird",
    "ontkent": "negates", "onbepaald": "indefinite",
    "zelfstandig": "substantive (noun-like)",
    "ken": "know (with je, inverted)", "uitlaten": "to walk (an animal)",
    "Uitlaten": "To walk (an animal)", "eerdere": "earlier; previous",
    "les": "the lesson", "geven": "to give", "geef": "give (with ik)",
    "spelen": "to play", "speelt": "plays", "Meervoud": "Plural",
    "honden": "dogs", "dieren": "animals", "klinker": "the vowel",
    "verdubbelt": "doubles", "medeklinker": "the consonant",
    "katten": "cats", "vissen": "fish (plural)", "vogels": "birds",
    "Laat": "Walk (imperative, part of uitlaten)",
    "houden": "to love; to be fond of; to hold", "beiden": "both (of them)",
    "Pico": "Pico (a pet bird's name)", "alle": "all",
})

# Unit 32 (sports and exercise), added 2026-07-09.
NL_GLOSSES.update({
    "voetbal": "football; soccer", "yoga": "yoga", "doet": "does",
    # "hardlopen"/"zwemmen" (and their capitalized subject-position forms)
    # are classified as nouns here -- every real use in this unit is as the
    # object of "aan"/"van" (doen aan hardlopen, houden van zwemmen), the
    # infinitive-as-gerund pattern Dutch uses after prepositions, matching
    # how "hardlopen" is also used as a bare subject ("Hardlopen is niet
    # scheidbaar").
    "hardlopen": "running; to run", "zwemmen": "swimming; to swim",
    "Doen": "To do", "specifieke": "specific", "noemt": "names; calls",
    "Beide": "Both", "hard": "hard; fast", "dicht": "close; near",
    "huis": "the house", "Hardlopen": "Running",
    "loopt": "walks; runs", "rustig": "calm(ly)", "bewegen": "to move",
    "zwemt": "swims", "bijna": "almost", "proberen": "to try",
})

# Unit 33 (transportation and commuting), added 2026-07-09.
NL_GLOSSES.update({
    "fiets": "the bike", "reist": "travels", "lopen": "to walk",
    "reizen": "to travel", "fietst": "cycles", "rijdt": "drives",
    "lessen": "lessons", "Die": "Those; that", "woorden": "words",
    "vervoer": "transport", "loket": "the counter; ticket window",
    "onbekende": "a stranger", "Welk": "Which",
    "centrum": "the town centre", "ver": "far",
    "Fietsen": "Cycling; to cycle", "dichtbij": "nearby; close by",
    "rijd": "drive (with ik)",
})

for _token in ("Een", "Twee"):
    if _token not in NL_GLOSSES:
        NL_GLOSSES[_token] = NL_GLOSSES[_token.casefold()]

# Unit 8 (locating places), added 2026-07-05.
NL_GLOSSES.update({
    "station": "the station", "supermarkt": "the supermarket", "ziekenhuis": "the hospital",
    "bank": "the bank", "postkantoor": "the post office", "bushalte": "the bus stop",
    "naast": "next to", "tegenover": "opposite; across from", "achter": "behind",
    "tussen": "between", "buurt": "neighbourhood; area", "van": "of; from",
    "kaart": "the map", "buurtkaart": "the neighbourhood map",
    "BUURTKAART": "NEIGHBOURHOOD MAP", "Bibliotheek": "Library", "Ziekenhuis": "Hospital",
    "Postkantoor": "Post office", "Supermarkt": "Supermarket", "Bank": "Bank",
    "Bushalte": "Bus stop", "Kijk": "look", "Mooi": "nice; good",
})

# A2 unit 73 (sollicitatiegesprek/job interview), added 2026-07-10.
NL_GLOSSES.update({
    "vacature": "vacancy; job opening", "solliciteren": "to apply",
    "Kantoor": "Office", "Bloem": "Bloem", "zoekt": "is looking for",
    "administratief": "administrative", "medewerker": "employee; assistant",
    "sollicitatiegesprek": "job interview", "langskomen": "to come by",
    "ervaring": "experience", "vrijwilliger": "volunteer",
    "vaardigheid": "skill", "Typen": "Typing", "belangrijke": "important",
    "goede": "good", "vaardigheden": "skills", "beschikbaar": "available",
    "werktijden": "working hours", "Ervaring": "Experience",
    "klantcontact": "customer contact", "pre": "plus; advantage",
    "Werktijden": "Working hours", "Vertelt": "Tell",
    "had": "had", "gesprek": "conversation; interview",
    "gesolliciteerd": "applied",
})

# A2 unit 74 (reisvertraging/travel disruption), added 2026-07-11. Widened
# the already-existing "over" gloss (unit15-era, "past; after") to also cover
# the time-duration sense this unit uses ("Over tien minuten" = "In ten
# minutes") -- this is ordinary polysemy of the single Dutch preposition
# "over", not a distinct homograph/different-POS collision like the "zijn"/
# "werk" cases documented in this file's module docstring, so widening the
# one gloss (rather than adding a conflicting second entry) is safe.
NL_GLOSSES["over"] = "past; after; in (a duration, as in 'over tien minuten')"
NL_GLOSSES.update({
    "seinstoring": "the signal failure", "valt": "falls; is cancelled (with hij/zij, part of uitvallen)",
    "door": "through; because of; during (as in 'door de week')",
    "aansluiting": "the connection", "mis": "miss (with ik)",
    "servicebalie": "the service desk", "Kunt": "can (with u/je, formal or informal)",
    "alternatieve": "alternative (inflected)", "verbinding": "the connection",
    "intercity": "the intercity train", "via": "via; through",
    "Belangrijke": "important (inflected)", "mededeling": "the notice; announcement",
    "rijden": "to run (trains/buses); to drive", "Arnhem": "Arnhem",
    "treinen": "trains", "Reizigers": "Travelers", "kunnen": "can (infinitive/plural)",
    "omreizen": "to reroute", "Amersfoort": "Amersfoort", "duurt": "lasts (with hij/zij)",
    "ongeveer": "about; approximately", "adviseren": "to advise",
    "reizigers": "travelers", "reisplanner": "the journey planner",
    "raadplegen": "to consult", "NS": "NS (Dutch national railway company)",
    "uitgevallen": "cancelled; failed (past participle of uitvallen)",
    "weten": "to know", "inderdaad": "indeed", "Over": "past; after; in (a duration, as in 'over tien minuten')",
    "spoor": "the platform; track", "even": "just; briefly",
})

# A2 unit 75 (schermtijd/screen time and online habits), added 2026-07-11.
NL_GLOSSES.update({
    "scherm": "the screen", "telefoon": "the phone", "sociale": "social (inflected)",
    "media": "media", "chat": "chat (with ik)", "apps": "apps",
    "schermtijd": "screen time", "gewoonte": "the habit",
    "doorbrengen": "to spend (time)", "hun": "their",
    "Sociale": "Social (inflected)", "gezond": "healthy",
    "Probeer": "Try (imperative)", "brengen": "to bring; to spend (time) (part of doorbrengen)",
    "Eigenlijk": "actually", "kijk": "look (with ik)",
    "Jawel": "yes indeed (contradicting a negative assumption)",
    "wegleggen": "to put away", "probeer": "try (with ik)",
})

# A2 unit 76 (drukke week/describing a weekly schedule), added 2026-07-11.
NL_GLOSSES.update({
    "cursus": "the course", "volgorde": "the order; sequence",
    "Ten": "finally (part of 'ten slotte')", "slotte": "finally (part of 'ten slotte')",
    "avondeten": "the dinner; evening meal",
    "doordeweekse": "weekday (adjective, as in 'doordeweekse dag')",
    "Door": "through; because of; during (as in 'door de week')",
    "verschil": "the difference", "agenda": "the schedule; planner",
    "zit": "sits; is (with hij/zij, idiomatic 'zit vol' = is full)",
    "vol": "full", "Volgende": "next", "druk": "busy",
    "woensdagavond": "Wednesday evening", "taalcursus": "the language course",
    "leest": "reads (with hij/zij)", "Best": "pretty; quite (degree adverb, as in 'best druk')",
    "vrij": "free; off (a day)", "lekkers": "something tasty (as in 'iets lekkers')",
    "gewoon": "just; simply",
})

# A2 unit 77 (iets terugbrengen/shopping complaint and returns), added
# 2026-07-11.
NL_GLOSSES.update({
    "koptelefoon": "the headphones", "kapot": "broken",
    "linkerkant": "the left side", "geld": "the money",
    "ruilen": "to exchange", "terugkrijgen": "to get back",
    "bonnetje": "the receipt", "geleden": "ago",
    "retourbeleid": "the return policy", "artikel": "the item; article",
    "terugbrengen": "to return (an item)", "regel": "arrange (with ik, part of regelen)",
    "Retourbeleid": "the return policy", "aankoop": "the purchase",
    "defect": "defective", "exemplaar": "the copy; item (replacement)",
    "teruggekregen": "got back (past participle of terugkrijgen)",
})

# B1 unit 01 (hypothetische situaties/hypothetical situations), added
# 2026-07-11. "zou"/"misschien"/"geweldig"/"Soms" reuse the gloss already
# established for their existing capitalized/lowercase sentence-initial
# sibling (same meaning, safe direct reuse, see this file's own docstring
# note on this round); "Toch" is this unit's own capitalized sentence-
# initial variant of the lowercase "toch" this same block defines.
NL_GLOSSES.update({
    "Spanje": "Spain", "zou": "would", "zouden": "would (plural)",
    "jullie": "you (plural)", "rijk": "rich", "vaker": "more often",
    "Stel": "imagine (imperative, in 'stel je voor')",
    "loterij": "the lottery", "winnen": "to win", "stoppen": "to stop",
    "wereld": "the world", "rondreizen": "to travel around",
    "misschien": "maybe", "meteen": "immediately",
    "geweldig": "great; wonderful", "kon": "could", "kiezen": "to choose",
    "willen": "to want", "Anouk": "Anouk (a Dutch female name)",
    "Soms": "sometimes", "denkt": "thinks", "opnieuw": "again",
    "studeren": "to study", "worden": "to become",
    "kosten": "to cost; to take (time)", "toch": "still; nevertheless",
    "Toch": "still; nevertheless", "bezoeken": "to visit",
})

# B1 unit 02 (mening en nuance/opinion and nuance), added 2026-07-11.
# "sommige" reuses the existing capitalized "Sommige" ("Some") gloss --
# same meaning, safe direct reuse. "Steeds" (capitalized, this unit's own
# "steeds meer" = "more and more") is a REAL polysemy/homograph collision
# with the pre-existing lowercase "steeds" = "still" (part of "nog steeds",
# unit16) -- given its own fresh entry rather than reused, see this file's
# own docstring note on this round.
NL_GLOSSES.update({
    "hoewel": "although", "vlees": "meat", "ondanks": "despite",
    "milieu": "the environment", "echter": "however",
    "sommige": "some", "makkelijk": "easy", "kleine": "little (inflected)",
    "stap": "the step", "daarmee": "with that; with it",
    "groente": "vegetables", "gezondheid": "health",
    "Steeds": "more and more (with a comparative, e.g. 'steeds meer')",
    "Sommigen": "some (people)", "Anderen": "others",
    "vooral": "mainly; especially", "veranderen": "to change",
    "enerzijds": "on one hand", "anderzijds": "on the other hand",
})

# B1 unit 03 (werkoverleg/workplace meetings), added 2026-07-11. "Beste"
# (this unit's own email-salutation "Beste collega's," = "Dear
# colleagues,") is a REAL homograph collision with the pre-existing
# lowercase "beste" = "best (attributive)" (unit14's superlative) -- given
# its own fresh entry rather than reused. "groet" (this unit's own "met
# vriendelijke groet" = "kind regards," a common noun) is likewise given
# its own fresh entry rather than reused from the pre-existing capitalized
# "Groet" (a standalone unit11 message-closing PHRASE, a different
# grammatical role for the same underlying word).
NL_GLOSSES.update({
    "rapport": "the report", "nakijken": "to check; to review",
    "voorstellen": "to propose; to suggest", "vergadering": "the meeting",
    "beginnen": "to begin; to start", "punt": "the point; the item",
    "bespreken": "to discuss", "afronden": "to finish; to complete",
    "cijfers": "the figures; the numbers",
    "lukken": "to work out; to succeed",
    "gang": "way (in 'ga uw gang,' go ahead)",
    "jaarverslag": "the annual report", "Beste": "Dear (letter/email salutation)",
    "collega's": "colleagues", "ontvang": "receive (with ik)",
    "opmerkingen": "comments", "hoop": "hope (with ik)",
    "lukt": "works out; succeeds",
    "vriendelijke": "kind; friendly (inflected)",
    "groet": "regards; greeting", "Jasper": "Jasper (a Dutch male name)",
    "mogelijk": "possible",
})

# B1 unit 04 (ingewikkelde zinnen/relative clauses), added 2026-07-11. "Ken"
# reuses the existing lowercase "ken" ("know (with je, inverted)") gloss --
# same meaning, safe direct reuse (both are the "Ken je...?"/"ken je...?"
# question form). "stad" (this unit's own common noun "the city") is a REAL
# collision with the pre-existing capitalized "Stad" -- that token is a
# unit14 comparison-ad placeholder brand/product name classified as a
# proper noun, an unrelated meaning -- given its own fresh entry rather
# than reused.
NL_GLOSSES.update({
    "collega": "the colleague", "aardig": "nice; kind",
    "stad": "the city", "praat": "talk (with ik)",
    "waarover": "about which", "interessant": "interesting",
    "Ken": "know (with je, inverted)", "vrouw": "the woman",
    "Bedoel": "mean (question form, with je)", "geboren": "born",
    "wereldje": "small world (diminutive of wereld)", "drinkt": "drinks",
    "toevallig": "coincidental; what a coincidence",
    "vriendin": "girlfriend; female friend",
    "universiteit": "the university", "bedrijf": "a company",
    "Sara": "Sara (a name)", "vlak": "right (next to); close",
})

# B1 unit 05 (indirecte rede/indirect speech), added 2026-07-11. "Later"
# reuses the existing lowercase "later" gloss -- same meaning, safe direct
# reuse.
NL_GLOSSES.update({
    "zei": "said", "gehoord": "heard", "ophalen": "to pick up",
    "Later": "later", "belde": "called", "konden": "could (plural)",
})

# B1 unit 06 (verplichtingen/obligations), added 2026-07-11. "alles" reuses
# the existing capitalized "Alles" ("Everything") gloss -- same meaning,
# safe direct reuse.
NL_GLOSSES.update({
    "schoonmaken": "to clean", "kamer": "the room", "eerder": "earlier",
    "opruimen": "to tidy up", "hoef": "need to (don't need to, with ik)",
    "vanavond": "tonight",
    "hoeft": "need to (don't need to, with hij/zij/u)",
    "cadeau": "the present; the gift", "roken": "to smoke",
    "rookvrij": "smoke-free", "gebouw": "the building",
    "Trouwens": "by the way", "wist": "knew", "niets": "nothing",
    "alles": "everything", "geregeld": "arranged", "vriend": "friend",
    "gelukkig": "fortunately",
    "zelf": "-self (emphatic, e.g. himself)", "brengt": "brings",
})

# B1 unit 07 (kunnen en konden/ability, present and past), added
# 2026-07-11. "Vorige" reuses the existing lowercase "vorige" ("previous;
# last") gloss -- same meaning, safe direct reuse. ophalen/kon/eerder/zou/
# gelukkig were already classified by earlier B1 units above.
NL_GLOSSES.update({
    "moest": "had to (past of moeten)", "Vorige": "previous; last",
    "mogelijkheid": "the possibility",
})

# B1 unit 08 (reële en irreële situaties/real and unreal conditionals),
# added 2026-07-11. "Nu" reuses the existing lowercase "nu" ("now") gloss --
# same meaning, safe direct reuse. "Vorig" (uninflected, used with the
# het-word "jaar") is a distinct exact token from "Vorige" (inflected, used
# with the de-word "week") -- ordinary Dutch adjective agreement, not a
# homograph, each gets its own entry since dict keys are exact strings.
# zou/studeren/eerder/Sara/willen were already classified by earlier B1
# units above.
NL_GLOSSES.update({
    "geweten": "known (past participle of weten)", "feest": "the party",
    "Vorig": "last (uninflected, with a het-word like 'jaar')",
    "hoorde": "heard (simple past)", "Nu": "now",
    "voorwaarde": "the condition",
})

# B1 unit 09 (eens en oneens/agreement and disagreement), added 2026-07-11.
# worden/Toch/denkt were already classified by earlier B1 units above.
NL_GLOSSES.update({
    "ermee": "with it (in 'het ermee eens zijn')",
    "vierdaagse": "four-day (inflected)", "werkweek": "the work week",
    "bedrijven": "companies", "zegt": "says",
    "gelukkiger": "happier", "blijf": "remain; stay (with ik)",
    "sceptisch": "skeptical", "praten": "to talk",
})

# B1 unit 10 (werkverantwoordelijkheden/work responsibilities), added
# 2026-07-11. rapport was already classified by unit03 above.
NL_GLOSSES.update({
    "verantwoordelijk": "responsible", "medicatie": "the medication",
    "patiënten": "the patients", "klaar": "done; ready",
    "gepland": "planned", "planning": "the schedule; the planning",
    "ergens": "somewhere; something", "meneer": "Mr.; sir",
    "Bakker": "Bakker (a Dutch surname)", "vraagt": "asks",
    "taak": "the task",
})

# B1 unit 11 (een verhaal vertellen/telling a story), added 2026-07-11.
# belde/opnieuw/zei/kon/Sara were already classified by earlier B1 units
# above.
NL_GLOSSES.update({
    "Terwijl": "while",
    "nam": "took (simple past of nemen, in 'nam niet op,' didn't answer)",
    "Toen": "when; then",
    "opnam": "picked up (the phone; simple past of opnemen)",
    "deed": "did (simple past of doen)", "jammer": "a shame; a pity",
    "gebeurde": "happened (simple past of gebeuren)",
    "grappigs": "funny (indeclinable form after 'iets')",
    "Uiteindelijk": "in the end; eventually",
    "lachten": "laughed (plural simple past of lachen)",
    "verhaal": "the story", "grappig": "funny",
})

# A1 units 43-48 (seasons, emergencies, lost items, appointments, library
# borrowing, waste sorting), added 2026-07-12 alongside UNIT_FILES' extended
# range above.
NL_GLOSSES.update({
    "seizoen": "the season", "lente": "spring", "zomer": "summer",
    "herfst": "autumn; fall", "winter": "winter",
    "eigenschap": "the characteristic; property", "schaatsen": "to ice-skate",
    "tulpen": "tulips", "seizoenen": "seasons",
    "allemaal": "all; everyone", "Vier": "four",
    "favorieten": "favorites",
    "brand": "fire", "alarmnummer": "emergency number",
    "nooduitgang": "emergency exit", "politie": "police",
    "ambulance": "ambulance", "brandweer": "fire brigade",
    "Politie": "police", "iedereen": "everyone", "Rustig": "calm",
    "Iedereen": "everyone", "112": "112",
    "kwijt": "missing; lost", "gevonden": "found",
    "portemonnee": "wallet", "Telefoon": "phone",
    "spannend": "exciting; tense", "genoeg": "enough",
    "Woensdag": "Wednesday", "computerhulp": "computer help",
    "Voor": "for", "Waarvoor": "for what; what for",
    "bevestigd": "confirmed", "help": "help (with ik)",
    "herinneren": "to remind",
    "lenen": "to borrow", "bibliotheekpas": "library card",
    "28": "28", "weken": "weeks", "leenbon": "loan receipt",
    "Leenbon": "loan receipt", "leent": "borrows",
    "geleend": "borrowed", "leen": "borrow (with ik)",
    "afval": "waste; trash", "scheiden": "to sort; to separate",
    "GFT": "organic waste", "bak": "bin", "Restafval": "residual waste",
    "grijze": "grey", "Papier": "paper", "container": "container",
    "glasbak": "glass recycling container", "glas": "glass",
    "papier": "paper", "ophaaldag": "collection day",
    "Maandag": "Monday", "Afvalkalender": "waste collection calendar",
    "Donderdag": "Thursday", "restafval": "residual waste",
    "gescheiden": "sorted; separated", "bakken": "bins",
    "regels": "rules",
})

# Case variants are tokens in their own right because provenance preserves the
# realization spelling. Their gloss is the explicit lexical gloss above.
for _token in (
    "Achtenveertig Ben Bent Dagen Dan Dat De En Er Goed Het Hoe Hoeveel Ik Inleverdatum Is Ja Jou Kom Kun Leuk "
    "Maanden Mijn Nee Niet Nul Om Op Tot Twaalf Vandaag Waar Wanneer Wat Welke Wij"
).split():
    if _token not in NL_GLOSSES:
        NL_GLOSSES[_token] = NL_GLOSSES[_token.casefold()]

for _number in "0 00 06 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 18 19 20 21 22 24 25 28 29 30 31 32 40 42 43 45 48 50 65 75 87 90 99 112 2024 2026".split():
    NL_GLOSSES[_number] = _number

SYMBOLS = set("'s 0 00 06 07 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 24 25 28 29 30 31 32 40 42 43 45 48 50 65 75 87 90 99 112 500 2024 2026".split())
PROPER_NOUNS = {"België", "Duitsland", "Egypte", "Lotte", "Nederland", "Noor", "Omar",
                "Rotterdam", "Sander", "Fenna", "Jan", "Marieke", "Utrecht", "Amsterdam",
                "Bergsport", "Schoudertas", "Stad", "Centraal", "M"}
PRONOUNS = set("ik Ik je jij jou Jou me u Wij wij Mijn mijn Welke welke Wat wat Hoeveel hoeveel jouw haar hem iets zich we We Hij hij Deze deze die zij welk Waarmee Ze Zij Jij U Zijn wie mij uw".split())
PREPOSITIONS = set("aan bij in met na naar om Om op Op over te tot Tot uit voor vóór per naast tegenover achter tussen van vanaf In Na Bij boven Van tegen Met".split())
PARTICLES = set("behalve dan Dan dat Dat de De dit Dit dus een Een en En er Er geen Geen het Het Ja ja Nee nee Niet niet of ook wel maar nog Anders af eerst Eerst pas want als plus toe st O langs Als Maar omdat".split())
ADJECTIVES = set("Belgisch beleefd Duits Engels formeel Goed goed hele informeel laat Leuk leuk Nederlands nieuw normaal open oud slecht volgende elke Mooi gewone scheidbaar korte kort vriendelijk voltooide voltooid meeste sterke algemene blauwe andere ene lekker groot klein groter kleiner duur goedkoop duurder goedkoper bijvoeglijk gelijk mooi praktisch duurst beter best onregelmatig beste meer Veel meest dezelfde lange sterk lichter sterker grote nodig mooist licht beleefde ziek verkouden Ziek bijvoeglijke zelfstandige moe Elke Sommige benieuwd eigen extra vroeg fijn gezellig nieuwe welkom bewolkt koud warm zonnig Fijn blauw blij boos verdrietig zenuwachtig trots lief zwart".split())
ADVERBS = set("avonds vandaan halverwege hier hoe Hoe hoeveelste middags nachts ochtends terug vandaag Vandaag waar Waar wanneer Wanneer graag vaak natuurlijk links rechts linksaf rechtsaf rechtdoor Rechtdoor Graag achteraan daarna Daarna eruit samen meestal gisteren vanmorgen Gisteren Vanmorgen Daar daar liever Liever zo net minder Precies precies al veel steeds Nog nu eigenlijk later altijd snel binnen Hier Natuurlijk Waarom alleen echt eerlijk heel vast apart contant".split())
VERBS = set("begint ben Ben bent Bent heb Heb heet inschrijven is Is kom Kom komt Komt kost krijgen leer moet ontmoeten spreek wil wilt woon wonen Wonen woont zijn zitten Kun kun herhalen gaat drinken eten Mag mag Zie hebben neem kan Kan pinnen Kijk ga sla loop Ga Sla Loop gedaan opstaan sta aankleden kleed ontbijten ontbijt werken werk eet afwassen was slapen slaap staat ziet gaan Zullen zullen stellen maakt afspreken geeft staan spreken gebruik gedronken gegaan Denk gebruiken gegeten gewerkt kopen gekocht komen gekomen vinden vind Vind fietsen wandelen winkelen doen Houden drukt houd Zeg Wil zien kiest houdt voeg Gebruik vergelijken werkt heeft koop Koop koopt Wilt vertrekt moeten Let stappen voel scheelt Gaat helpen Heeft Neem Rust drink Voel genomen rusten begin denk doe krijgt maak stop zeggen klinkt Laten blijven kijken maken regent Maak Past Spreek afrekenen bel bellen belt betaalt betalen betekent dacht delen geholpen gezegd ging hebt helpt hoor horen neemt nemen passen past spreekt stuur vertellen voelt vragen zoek Betaald kunt denken".split())
PHRASES = {"Aangenaam", "Goedemiddag", "Goedemorgen", "Goedenavond", "Hallo", "Hoi", "Prima", "ziens",
           "alstublieft", "alsjeblieft", "eraan", "Bedankt", "Sorry", "Groet", "Beterschap", "Perfect"}
NOUNS = set("Achtenveertig Dagen Inleverdatum Maanden Medewerker Nul Pauze Taalcafé Twaalf Welkom Workshop acht achtentwintig achtentwintigste achtenveertig achtste achttien achttiende april augustus avond bibliotheek bijdrage boek boeken cent dag dank datum december derde dertien dertiende dertig dertigste dinsdag donderdag drie drieëntwintigste drieënveertig eenendertigste eenentwintig eenentwintigste eenheid eerste elf elfde euro februari groep half hoofdletter huisnummer inleverdatum jaar januari juli juni keer kwart kwartier maand maandag maart mei mensen middag naam nacht negen negende negenennegentig negenentwintigste negentien negentiende negentig november nul nummer ochtend oktober rooster september stoelen taalcafé tachtig tafel telefoonnummer tien tiende tiental tijd twaalf twaalfde twee tweede tweeëndertig tweeëntwintig tweeëntwintigste tweeënveertig twintig twintigste uur veertien veertiende veertig vier vierde vierentwintigste vijf vijfde vijfentwintigste vijfenzestig vijfenzeventig vijftien vijftiende vijftig vrijdag vrijdagmiddag week woensdag workshop zaal zaterdag zes zesde zesentwintigste zestien zestiende zestig zeven zevende zevenentachtig zevenentwintigste zeventien zeventiende zeventig zondag één "
              "vader moeder ouders broer zus kind kinderen opa oma oom tante neef nicht gezin maand familie broers zussen "
              "koffie thee water melk sap brood broodje kaas appel appelsap Menukaart Koffie Thee Broodje Appelsap "
              "markt winkel kraam appels peren tomaten paprika's Appels Peren Tomaten Paprika's kilo honderd gram pond stuk stuks "
              "prijskaartje Verkoper Twee "
              "station supermarkt ziekenhuis bank postkantoor bushalte buurt kaart buurtkaart BUURTKAART "
              "Bibliotheek Ziekenhuis Postkantoor Supermarkt Bank Bushalte "
              "route Route START DOEL "
              "hoofdzin deel einde werkwoord "
              "film activiteit manier zin idee plan reden afwijzing afspraak bericht uitnodiging Vrijdag "
              "gesprekken gebeurtenis deelwoord eindpositie werkwoorden "
              "tomatensoep activiteiten voorkeur muziek films smaak trui optie park "
              "naamwoord rugzak tas vijfenveertig dingen superlatief keuze treinreis ruimte reis vorm schoudertas vergelijkingen "
              "kaartje retour balie perron trein vertraging plaats minuten ingang uitgang wachtruimte "
              "Kaartje Vertrek Aankomst Retour Prijs bord probleem Perron enkele "
              "hoofdpijn buikpijn keelpijn koorts Koorts naamwoorden apotheek tablet Advies dagen huisarts Dank morgen "
              "baan beroep kantoor kok pauze restaurant ritme uren verpleegkundige "
              "appartement Appartement badkamer balkon kamers keuken slaapkamer slaapkamers tuin woonkamer "
              "Morgen Weerbericht Zaterdag Zondag wandeling weekend weer weerbericht "
              "Rekening Totaal Winterjas broek dienst hoofdgerechten jas kleur koffies maat pin rekening schoenen sms totaal vijfendertig vijfentwintig wisselgeld zorgen beetje".split())

# A2 units 24-28 (gemeente/meningen/bankrekening/huisarts/probleem melden),
# added 2026-07-07 alongside UNIT_FILES_A2 above.
SYMBOLS.update({"s"})
PROPER_NOUNS.update({"BSN", "DigiD"})
PRONOUNS.update({"Alles", "Uw", "ze", "waarmee"})
PREPOSITIONS.update({"Sinds", "sinds", "Volgens", "Aan", "Tussen"})
PARTICLES.update({"indien"})
ADJECTIVES.update({
    "geldig", "vorige", "persoonlijke", "gevaarlijk", "smal", "eens",
    "veiliger", "breder", "weinig", "mobiel", "ernstig", "scheidbare",
    "vervelend", "Geweldig",
})
ADVERBS.update({
    "online", "vooraf", "Misschien", "helemaal", "mee", "erg",
    "waarschijnlijk", "morgenochtend", "thuis", "gisteravond", "gedeeltelijk",
})
VERBS.update({
    "schrijven", "Zou", "schikken", "Moet", "meenemen", "ontvangt", "regelen",
    "ingeschreven", "stort", "Storten", "storten", "bankieren", "gebruikt",
    "geopend", "Heeft", "openen", "snap", "bespaart", "wordt", "vindt",
    "Maakt", "schrijf", "rust", "innemen", "terugkomen", "voorgeschreven",
    "Voelt", "ontvangen", "sturen", "Bel",
})
PHRASES.update({"Alstublieft"})
NOUNS.update({
    "paspoort", "huurcontract", "geboorteakte", "adres", "overheid", "zaken",
    "gemeente", "documenten", "toepassing", "inschrijving", "post",
    "Ambtenaar", "orde", "paar", "hulp", "fietspad", "mening", "kant",
    "voetgangers", "fietsers", "pad", "auto", "straat", "bankrekening",
    "betaalrekening", "salaris", "werkgever", "infinitief",
    "identiteitsbewijs", "bankpas", "app", "klachten", "pijn", "griepje",
    "recept", "pillen", "infinitieven", "Diagnose", "dokter", "verwarming",
    "monteur", "melding", "contact", "Bevestiging", "woningcorporatie",
    "Woningcorporatie", "bezoek", "Huisarts", "vierentwintig",
})

# A2 unit 73 (sollicitatiegesprek/job interview), added 2026-07-10 alongside
# the new realization file picked up by UNIT_FILES_A2's broad glob.
PROPER_NOUNS.update({"Kantoor", "Bloem"})
ADJECTIVES.update({
    "administratief", "belangrijke", "goede", "beschikbaar",
})
ADVERBS.update({"pre"})
VERBS.update({
    "solliciteren", "zoekt", "langskomen", "Typen", "Vertelt", "had",
    "gesolliciteerd",
})
NOUNS.update({
    "vacature", "medewerker", "sollicitatiegesprek", "ervaring",
    "vrijwilliger", "vaardigheid", "vaardigheden", "werktijden",
    "klantcontact", "gesprek",
    "Ervaring", "Werktijden",
})

# A2 unit 74 (reisvertraging/travel disruption), added 2026-07-11.
PROPER_NOUNS.update({"Arnhem", "Amersfoort", "NS"})
PREPOSITIONS.update({"door", "via", "Over"})
ADJECTIVES.update({"alternatieve", "Belangrijke"})
ADVERBS.update({"ongeveer", "inderdaad", "even"})
VERBS.update({
    "valt", "mis", "rijden", "kunnen", "omreizen", "duurt", "adviseren",
    "raadplegen", "uitgevallen", "weten", "Kunt",
})
NOUNS.update({
    "seinstoring", "aansluiting", "servicebalie", "verbinding", "intercity",
    "mededeling", "treinen", "Reizigers", "reizigers", "reisplanner", "spoor",
})

# A2 unit 75 (schermtijd/screen time and online habits), added 2026-07-11.
PRONOUNS.update({"hun"})
PARTICLES.update({"Jawel"})
ADJECTIVES.update({"sociale", "Sociale", "gezond"})
ADVERBS.update({"Eigenlijk"})
VERBS.update({
    "chat", "doorbrengen", "brengen", "kijk", "wegleggen", "probeer", "Probeer",
})
NOUNS.update({"scherm", "telefoon", "media", "schermtijd", "gewoonte", "apps"})

# A2 unit 76 (drukke week/describing a weekly schedule), added 2026-07-11.
PREPOSITIONS.update({"Door"})
ADJECTIVES.update({"doordeweekse", "vol", "Volgende", "druk", "vrij"})
ADVERBS.update({"Ten", "slotte", "Best", "gewoon"})
VERBS.update({"zit", "leest"})
NOUNS.update({
    "cursus", "volgorde", "avondeten", "verschil", "agenda", "woensdagavond",
    "taalcursus", "lekkers",
})

# A2 unit 77 (iets terugbrengen/shopping complaint and returns), added
# 2026-07-11.
ADJECTIVES.update({"kapot", "defect"})
ADVERBS.update({"geleden"})
VERBS.update({
    "ruilen", "terugkrijgen", "terugbrengen", "regel", "teruggekregen",
})
NOUNS.update({
    "koptelefoon", "linkerkant", "geld", "bonnetje", "retourbeleid",
    "artikel", "Retourbeleid", "aankoop", "exemplaar",
})

# Units 29-33 (hobbies, appearance, animals, sports, transportation), added
# 2026-07-09 alongside UNIT_FILES' extended range above -- still the same
# "Dutch A1" course, not a new course boundary (see UNIT_FILES' own comment).
PROPER_NOUNS.update({"Opa", "Nina", "Pico"})
PHRASES.update({"Oké"})
PRONOUNS.update({"Je", "Die", "beiden", "ons", "Welk"})
PREPOSITIONS.update({"zonder"})
PARTICLES.update({"zoals"})
ADJECTIVES.update({
    "vrije", "ontspannend", "elk", "lang", "jong", "Oud", "blond", "bruin",
    "grijs", "groen", "bruine", "groene", "langer", "anders", "onbepaald",
    "zelfstandig", "eerdere", "alle", "specifieke", "Beide", "dicht",
    "rustig", "ver",
})
ADVERBS.update({
    "soms", "nooit", "buiten", "allebei", "hard", "bijna", "dichtbij",
})
VERBS.update({
    "lezen", "sporten", "koken", "sport", "kook", "lees", "luisteren",
    "tekenen", "teken", "gamen", "luister", "game", "Kook", "kookt", "Game",
    "weet", "zie", "betekenen", "blijft", "herken", "kent", "ontkent",
    "ken", "uitlaten", "Uitlaten", "geven", "geef", "spelen", "speelt",
    "verdubbelt", "Laat", "houden", "doet", "Doen", "noemt", "loopt",
    "bewegen", "zwemt", "proberen", "reist", "lopen", "reizen", "fietst",
    "rijdt", "rijd",
})
NOUNS.update({
    "vrienden", "de-woorden", "het-woorden", "hobby's", "aantal", "jaren",
    "indruk", "getal", "Haar", "woord", "lidwoord", "ogen", "meervoud",
    "meisje", "patroon", "dier", "huisdier", "hond", "kat", "vis", "vogel",
    "les", "Meervoud", "honden", "dieren", "klinker", "medeklinker",
    "katten", "vissen", "vogels", "voetbal", "yoga", "hardlopen", "zwemmen",
    "Hardlopen", "huis", "fiets", "lessen", "woorden", "vervoer", "loket",
    "onbekende", "centrum", "Fietsen",
})

# Units 43-48 (seasons, emergencies, lost items, appointments, library
# borrowing, waste sorting), added 2026-07-12 alongside UNIT_FILES' extended
# range above.
PROPER_NOUNS.update({"GFT"})
PRONOUNS.update({"iedereen", "Iedereen"})
PREPOSITIONS.update({"Voor"})
ADJECTIVES.update({
    "kwijt", "gevonden", "spannend", "grijze", "Rustig", "gescheiden",
})
ADVERBS.update({"allemaal", "genoeg"})
VERBS.update({
    "schaatsen", "help", "herinneren", "lenen", "leent", "geleend", "leen",
    "scheiden",
})
NOUNS.update({
    "seizoen", "lente", "zomer", "herfst", "winter", "eigenschap",
    "tulpen", "seizoenen", "Vier", "favorieten", "brand", "alarmnummer",
    "nooduitgang", "politie", "Politie", "ambulance", "brandweer",
    "portemonnee", "Telefoon", "Woensdag", "computerhulp", "Waarvoor",
    "bevestigd", "bibliotheekpas", "weken", "leenbon", "Leenbon",
    "afval", "bak", "Restafval", "Papier", "container", "glasbak",
    "glas", "papier", "ophaaldag", "Maandag", "Afvalkalender",
    "Donderdag", "restafval", "bakken", "regels",
})


# B1 units 01-11, added 2026-07-11. Grouped by unit for traceability, same
# convention as every prior round's POS-set additions. Case-dup/homograph
# tokens whose gloss is reused/distinct per the NL_GLOSSES comments above
# still need their OWN exact-string POS-set membership here, since
# nl_part_of_speech() keys on the exact token too.

# Unit 01.
PROPER_NOUNS.update({"Spanje", "Anouk"})
ADJECTIVES.update({"rijk", "geweldig"})
ADVERBS.update({"vaker", "misschien", "meteen", "opnieuw", "toch", "Toch", "Soms"})
VERBS.update({
    "zou", "zouden", "Stel", "winnen", "stoppen", "rondreizen", "kon",
    "kiezen", "willen", "denkt", "studeren", "worden", "kosten", "bezoeken",
})
NOUNS.update({"loterij", "wereld"})
PRONOUNS.update({"jullie"})

# Unit 02.
ADJECTIVES.update({"sommige", "makkelijk", "kleine"})
ADVERBS.update({"echter", "vooral", "enerzijds", "anderzijds", "Steeds"})
VERBS.update({"veranderen"})
NOUNS.update({"vlees", "milieu", "stap", "groente", "gezondheid"})
PRONOUNS.update({"daarmee", "Sommigen", "Anderen"})
PREPOSITIONS.update({"ondanks"})
PARTICLES.update({"hoewel"})

# Unit 03.
ADJECTIVES.update({"vriendelijke", "mogelijk"})
NOUNS.update({
    "rapport", "vergadering", "punt", "cijfers", "gang", "jaarverslag",
    "collega's", "opmerkingen",
})
VERBS.update({
    "nakijken", "voorstellen", "beginnen", "bespreken", "afronden",
    "lukken", "ontvang", "hoop", "lukt",
})
PROPER_NOUNS.update({"Jasper"})
ADJECTIVES.update({"Beste"})
NOUNS.update({"groet"})

# Unit 04.
NOUNS.update({
    "collega", "stad", "vrouw", "wereldje", "vriendin", "universiteit",
    "bedrijf",
})
ADJECTIVES.update({"aardig", "interessant", "toevallig"})
VERBS.update({"praat", "Ken", "Bedoel", "geboren", "drinkt"})
PRONOUNS.update({"waarover"})
PROPER_NOUNS.update({"Sara"})
ADVERBS.update({"vlak"})

# Unit 05.
VERBS.update({"zei", "gehoord", "ophalen", "belde", "konden"})
ADVERBS.update({"Later"})

# Unit 06.
VERBS.update({
    "schoonmaken", "opruimen", "hoef", "hoeft", "roken", "wist",
    "geregeld", "brengt",
})
ADVERBS.update({"eerder", "vanavond", "Trouwens", "gelukkig"})
NOUNS.update({"kamer", "cadeau", "gebouw", "vriend"})
ADJECTIVES.update({"rookvrij"})
PRONOUNS.update({"niets", "alles", "zelf"})

# Unit 07.
VERBS.update({"moest"})
ADJECTIVES.update({"Vorige"})
NOUNS.update({"mogelijkheid"})

# Unit 08.
VERBS.update({"geweten"})
NOUNS.update({"feest", "voorwaarde"})
ADJECTIVES.update({"Vorig"})
VERBS.update({"hoorde"})
ADVERBS.update({"Nu"})

# Unit 09.
PRONOUNS.update({"ermee"})
ADJECTIVES.update({"vierdaagse", "gelukkiger", "sceptisch"})
NOUNS.update({"werkweek", "bedrijven"})
VERBS.update({"zegt", "blijf", "praten"})

# Unit 10.
ADJECTIVES.update({"verantwoordelijk", "klaar"})
NOUNS.update({
    "medicatie", "patiënten", "planning", "meneer", "taak",
})
VERBS.update({"gepland", "vraagt"})
PRONOUNS.update({"ergens"})
PROPER_NOUNS.update({"Bakker"})

# Unit 11.
PARTICLES.update({"Terwijl", "Toen"})
VERBS.update({"nam", "opnam", "deed", "gebeurde", "lachten"})
ADJECTIVES.update({"jammer", "grappigs", "grappig"})
ADVERBS.update({"Uiteindelijk"})
NOUNS.update({"verhaal"})


# ---------------------------------------------------------------------------
# A1 volume batch: units 34-42 and 49-72, added 2026-07-22.
#
# 33 previously-unclassified A1 units (34-42: technology, education,
# birthdays, household chores, the neighbourhood, post, cooking, personality,
# colours; 49-72: the "errand + outing" service-encounter arc from booking a
# room through the pet shop). Every gloss below was read off that unit's OWN
# en-nl overlay `gloss`/`example_gloss` field -- none is guessed, and no
# vocabulary the units do not teach was invented.
#
# THREE deliberate departures from how earlier rounds in this file did it:
#
# 1. SENTENCE-INITIAL CAPITALS ARE FOLDED, NOT REGISTERED (defect 1.25).
#    Earlier rounds registered the capitalized variant as its own lexeme
#    ("Kan", "Typen", "Vertelt", "Van", "Zij", "Ervaring", "Werktijden",
#    "Medewerker", ...). Typed answers are graded by exact string match and a
#    case-only mismatch is hard-blocked to `incorrect` (never "almost"), so a
#    learner who correctly types the lowercase citation form of such a lexeme
#    is marked wrong. `NL_CITATION_FORMS` below maps every token these 33
#    units capitalize only because of sentence/sign-line position onto its
#    lowercase citation form, and `_classify_nl()` applies it BEFORE the gloss
#    lookup, so no capitalized-by-position lexeme is created at all. Genuine
#    proper nouns (people, cities, business/venue names, the language name
#    "Spaans") are deliberately NOT folded -- Dutch capitalizes those
#    mid-sentence too, so their capital IS the citation form.
#    The map is keyed on tokens introduced ONLY by these 33 units, so it
#    cannot retroactively change any already-shipped lexeme.
#
# 2. GENDER AND NUMBER ARE RECORDED. Dutch de/het gender is not recoverable
#    from an English gloss, and a practice-pack author cannot pick a
#    grammatical frame without it. `NL_A1_VOLUME_ARTICLES` /
#    `NL_A1_VOLUME_PLURALS` surface it as `agreement_tags["article"]` /
#    `["number"]`. Every value was cross-checked against the article the
#    unit's own Dutch text actually uses ("de aap", "het internet"); the
#    handful of nouns the corpus never shows with an article are marked from
#    standard Dutch (all diminutives -> het, per the -je/-tje rule).
#
# 3. SEMANTIC SLOT TAGS ARE PROVIDED UP FRONT, not deferred. The A2 74-77 and
#    B1 rounds deliberately deferred fine-grained tags until a practice pack
#    existed. That is reversed here on purpose: unit checkpoints are a
#    publish gate and `generate_checkpoint()` needs BOTH templates and
#    lexemes scoped to the unit's own lessons, so these units are blocked on
#    tags existing first. Each unit gets a broad `<slug>_vocab` (content
#    words: noun/verb/adjective/adverb/phrase, never function words or proper
#    nouns, so no self-glossing distractor and no snake_case leak), a
#    `<slug>_noun` for matching_pairs pools, and exactly one single-member
#    `<slug>_<token>_single` anchor for a fixed-frame fill_in_blank /
#    render_frame slot (single by construction -- an exact `t == "..."`
#    test).
#
# Known homograph merges, checked by hand and accepted (same class as the
# "zijn" (are/his) limitation in this module's docstring -- this file keys
# specs by bare token, so one spelling gets exactly one classification):
#   Nodig  (u36, imperative of uitnodigen) -> existing adjective "nodig" = needed
#   Regel  (u54 sign, "Rule:")             -> existing verb "regel" = arrange
#   Duur   (u63/u64 sign, "Duration:")     -> existing adjective "duur" = expensive
#   Begin  (u64 sign, "Start:")            -> existing verb "begin" = start (ik)
#   Was    (u55-58, past of zijn)          -> existing verb "was" = do the dishes (ik)
# In each case folding is still strictly better than the alternative: a
# capitalized second lexeme would be a live typed-answer grading trap, while
# the merged sense is merely absent (and is never a slot candidate, because
# these tokens are excluded from the `_vocab`/`_noun` tags below).
#
# One genuine CONTENT defect surfaced and is worked around here rather than
# silently propagated: nl.a1.unit35.lesson06.teach.sander_interessant_zullen_we
# lists `taalcafe` in `introduced_tokens` while its own Dutch text says
# `taalcafé`. Registering the unaccented spelling would create a lexeme whose
# token is not the Dutch word, and (as a typed answer) an unwinnable item. It
# is folded onto the existing `taalcafé` lexeme; the realization's
# introduced_tokens entry should be corrected by the content lane.
# ---------------------------------------------------------------------------

# Unit 34 (technologie/technology and devices).
NL_GLOSSES.update({
    "boodschap": "the message", "computer": "the computer",
    "internet": "the internet", "opzoeken": "to look up (separable: zoekt ... op)",
    "stuurt": "sends (with hij/zij/u)", "zwem": "swim (with ik)",
})
NOUNS.update({"boodschap", "computer", "internet"})
VERBS.update({"opzoeken", "stuurt", "zwem"})

# Unit 35 (opleiding/study and courses).
NL_GLOSSES.update({
    "algemeen": "general", "gezondheidszorg": "healthcare",
    "hogeschool": "the college; university of applied sciences",
    "leert": "learns (with hij/zij)", "leren": "to learn",
    "nieuws": "new (in 'iets nieuws' = something new)", "oefenen": "to practise",
    "opleiding": "the study programme", "school": "the school",
    "Spaans": "Spanish", "specifiek": "specific",
    "studeer": "study (with ik)", "studeert": "studies (with hij/zij)",
    "volg": "take (a course) (with ik)", "volgen": "to take (a course)",
    "volgt": "takes (a course) (with hij/zij)",
    "volksuniversiteit": "the community college",
})
NOUNS.update({"gezondheidszorg", "hogeschool", "opleiding", "school",
              "volksuniversiteit"})
VERBS.update({"leert", "leren", "oefenen", "studeer", "studeert", "volg",
              "volgen", "volgt"})
ADJECTIVES.update({"algemeen", "nieuws", "Spaans", "specifiek"})

# Unit 36 (verjaardag/birthdays and parties).
NL_GLOSSES.update({
    "gefeliciteerd": "congratulations", "laten": "let (in 'laten we' = let's)",
    "nodigt": "invites (with hij/zij, part of uitnodigen)",
    "uitnodigen": "to invite (separable: nodigt ... uit)",
    "verjaardag": "the birthday", "vieren": "to celebrate",
    "viert": "celebrates (with hij/zij)",
})
NOUNS.update({"verjaardag"})
VERBS.update({"laten", "nodigt", "uitnodigen", "vieren", "viert"})
PHRASES.update({"gefeliciteerd"})

# Unit 37 (huishouden/household chores).
NL_GLOSSES.update({
    "huishouden": "the household chores", "rommel": "the mess",
    "ruim": "tidy up (with ik, part of opruimen)",
    "ruimen": "tidy up (with wij, part of opruimen)",
    "ruimt": "tidies up (with hij/zij, part of opruimen)",
    "stofzuig": "vacuum (with ik)", "stofzuigen": "to vacuum",
    "stofzuigt": "vacuums (with hij/zij)",
})
NOUNS.update({"huishouden", "rommel"})
VERBS.update({"ruim", "ruimen", "ruimt", "stofzuig", "stofzuigen", "stofzuigt"})

# Unit 38 (buurt/the neighbourhood and neighbours).
NL_GLOSSES.update({
    "Anna": "Anna", "buur": "the neighbour", "buurman": "the (male) neighbour",
    "buurvrouw": "the (female) neighbour", "groeten": "to greet",
    "kennen": "to know (a person)", "leuke": "nice (inflected)", "Peter": "Peter",
})
PROPER_NOUNS.update({"Anna", "Peter"})
NOUNS.update({"buur", "buurman", "buurvrouw"})
VERBS.update({"groeten", "kennen"})
ADJECTIVES.update({"leuke"})

# Unit 39 (post/sending letters and packages).
NL_GLOSSES.update({
    "aankomen": "to arrive (separable: komt ... aan)", "brief": "the letter",
    "duren": "to take (time); to last", "pakket": "the package",
    "postzegel": "the stamp", "schrijft": "writes (with hij/zij)",
})
NOUNS.update({"brief", "pakket", "postzegel"})
VERBS.update({"aankomen", "duren", "schrijft"})

# Unit 40 (koken/cooking together).
NL_GLOSSES.update({
    "bakt": "fries (with hij/zij)", "klaarmaken": "to prepare (separable: maakt ... klaar)",
    "pan": "the pan", "proef": "taste (with ik; also the imperative)",
    "proeft": "tastes (with hij/zij)", "proeven": "to taste",
    "smakelijk": "tasty (in 'eet smakelijk' = enjoy your meal)",
    "snijd": "cut (with ik)", "snijden": "to cut",
    "snijdt": "cuts (with hij/zij)", "tomaat": "the tomato", "ui": "the onion",
})
NOUNS.update({"pan", "tomaat", "ui"})
VERBS.update({"bakt", "klaarmaken", "proef", "proeft", "proeven", "snijd",
              "snijden", "snijdt"})
ADJECTIVES.update({"smakelijk"})

# Unit 41 (persoonlijkheid/describing people's character).
NL_GLOSSES.update({
    "anderen": "the others", "elkaar": "each other", "geduldig": "patient",
    "iemand": "someone", "nieuwsgierig": "curious", "persoon": "the person",
    "verlegen": "shy", "vertelt": "tells (with hij/zij)",
})
PRONOUNS.update({"anderen", "elkaar", "iemand"})
NOUNS.update({"persoon"})
VERBS.update({"vertelt"})
ADJECTIVES.update({"geduldig", "nieuwsgierig", "verlegen"})

# Unit 42 (kleuren/colours).
NL_GLOSSES.update({
    "bloemenmarkt": "the flower market", "geel": "yellow", "oranje": "orange",
    "paars": "purple", "rood": "red", "roze": "pink", "wit": "white",
})
NOUNS.update({"bloemenmarkt"})
ADJECTIVES.update({"geel", "oranje", "paars", "rood", "roze", "wit"})

# Unit 49 (accommodatie/checking in to a room).
NL_GLOSSES.update({
    "bevestiging": "the confirmation",
    "gereserveerd": "reserved (past participle of reserveren)",
    "hadden": "had (with wij/zij, past of hebben)", "heerlijk": "delicious",
    "inbegrepen": "included", "inchecken": "to check in", "Maastricht": "Maastricht",
    "mooie": "beautiful (inflected)", "nachten": "nights",
    "receptionist": "the receptionist", "reservering": "the reservation",
    "sleutel": "the key", "uitchecken": "to check out",
    "vanmiddag": "this afternoon", "wifiwachtwoord": "the wifi password",
})
PROPER_NOUNS.update({"Maastricht"})
NOUNS.update({"bevestiging", "nachten", "receptionist", "reservering", "sleutel",
              "wifiwachtwoord"})
VERBS.update({"gereserveerd", "hadden", "inchecken", "uitchecken"})
ADJECTIVES.update({"heerlijk", "inbegrepen", "mooie"})
ADVERBS.update({"vanmiddag"})

# Unit 50 (apotheek/at the pharmacy).
NL_GLOSSES.update({
    "apotheker": "the pharmacist",
    "daartegen": "for that (in 'iets daartegen' = something for it)",
    "doos": "the box", "dosering": "the dosage", "etiket": "the label",
    "medicijn": "the medicine", "paracetamol": "paracetamol",
    "pijnstiller": "the painkiller", "pijnstillers": "painkillers",
    "tabletten": "tablets", "uitrusten": "to rest (separable: rust ... uit)",
})
NOUNS.update({"apotheker", "doos", "dosering", "etiket", "medicijn",
              "paracetamol", "pijnstiller", "pijnstillers", "tabletten"})
VERBS.update({"uitrusten"})
ADVERBS.update({"daartegen"})

# Unit 51 (kapper/at the hairdresser).
NL_GLOSSES.update({
    "betaal": "pay (with ik)", "geweest": "been (past participle of zijn)",
    "hetzelfde": "the same", "hé": "hey", "kapper": "the hairdresser",
    "kapsel": "the hairstyle", "knipbeurt": "the haircut (service)",
    "knippen": "to cut (hair)", "korter": "shorter", "prijslijst": "the price list",
})
NOUNS.update({"kapper", "kapsel", "knipbeurt", "prijslijst"})
VERBS.update({"betaal", "geweest", "knippen"})
ADJECTIVES.update({"korter"})
PRONOUNS.update({"hetzelfde"})
PHRASES.update({"hé"})

# Unit 52 (fiets_huren/renting a bike).
NL_GLOSSES.update({
    "borg": "the deposit", "breng": "bring (with ik, part of terugbrengen)",
    "Daan": "Daan", "elektrische": "electric (inflected)",
    "fietsenwinkel": "the bike shop", "huren": "to rent", "huur": "rent (with ik)",
    "huurprijs": "the rental price", "huurprijzen": "rental prices",
})
PROPER_NOUNS.update({"Daan"})
NOUNS.update({"borg", "fietsenwinkel", "huurprijs", "huurprijzen"})
VERBS.update({"breng", "huren", "huur"})
ADJECTIVES.update({"elektrische"})

# Unit 53 (wasserette/at the launderette).
NL_GLOSSES["60"] = "60"
SYMBOLS.add("60")
NL_GLOSSES.update({
    "draag": "carry (with ik)", "droger": "the dryer", "graden": "degrees",
    "haal": "pick up (with ik, part of ophalen)", "kies": "choose (with ik)",
    "kleren": "clothes", "munten": "coins", "Sanne": "Sanne",
    "wasbeurt": "the wash (service)", "wasmand": "the laundry basket",
    "wasprogramma": "the wash programme", "wassen": "to wash",
    "wasserette": "the launderette", "zwaar": "heavy",
})
PROPER_NOUNS.update({"Sanne"})
NOUNS.update({"droger", "graden", "kleren", "munten", "wasbeurt", "wasmand",
              "wasprogramma", "wasserette"})
VERBS.update({"draag", "haal", "kies", "wassen"})
ADJECTIVES.update({"zwaar"})

# Unit 54 (zwembad/at the swimming pool).
NL_GLOSSES.update({
    "douche": "shower (with ik)", "douchen": "to shower", "Femke": "Femke",
    "kluisje": "the locker", "openingstijden": "the opening hours",
    "sluit": "closes (with hij/zij)", "zwembad": "the swimming pool",
    "zwemtas": "the swim bag",
})
PROPER_NOUNS.update({"Femke"})
NOUNS.update({"kluisje", "openingstijden", "zwembad", "zwemtas"})
VERBS.update({"douche", "douchen", "sluit"})

# Unit 55 (restaurant/ordering a meal).
NL_GLOSSES.update({
    "bestellen": "to order", "bioscoop": "the cinema", "Bram": "Bram",
    "dagmenu": "the day menu", "dranken": "the drinks",
    "gekozen": "chosen (past participle of kiezen)", "menukaart": "the menu",
    "soep": "the soup",
})
PROPER_NOUNS.update({"Bram"})
NOUNS.update({"bioscoop", "dagmenu", "dranken", "menukaart", "soep"})
VERBS.update({"bestellen", "gekozen"})

# Unit 56 (bioscoop/at the cinema).
NL_GLOSSES.update({
    "Iris": "Iris", "kindervoorstelling": "the children's showing",
    "museum": "the museum", "popcorn": "the popcorn",
    "programma": "the programme; schedule", "voorstelling": "the show; screening",
})
PROPER_NOUNS.update({"Iris"})
NOUNS.update({"kindervoorstelling", "museum", "popcorn", "programma",
              "voorstelling"})

# Unit 57 (museum/at the museum).
NL_GLOSSES.update({
    "concert": "the concert", "gids": "the guide", "schilderij": "the painting",
    "schilderijen": "paintings", "sluiten": "to close",
    "tentoonstelling": "the exhibition", "Tessa": "Tessa",
})
PROPER_NOUNS.update({"Tessa"})
NOUNS.update({"concert", "gids", "schilderij", "schilderijen", "tentoonstelling"})
VERBS.update({"sluiten"})

# Unit 58 (concert/at a concert).
NL_GLOSSES.update({
    "band": "the band", "podium": "the stage", "publiek": "the audience",
    "Sven": "Sven", "Wandelaars": "the Wanderers (band name)",
})
PROPER_NOUNS.update({"Sven", "Wandelaars"})
NOUNS.update({"band", "podium", "publiek"})

# Unit 59 (park/an afternoon in the park).
NL_GLOSSES.update({
    "bankje": "the bench", "boom": "the tree", "eend": "the duck",
    "eenden": "ducks", "fruit": "the fruit", "gras": "the grass",
    "lijn": "the leash", "onder": "under", "picknick": "the picnic",
    "Zonnehof": "Zonnehof (park name)",
})
PROPER_NOUNS.update({"Zonnehof"})
NOUNS.update({"bankje", "boom", "eend", "eenden", "fruit", "gras", "lijn",
              "picknick"})
PREPOSITIONS.update({"onder"})

# Unit 60 (sportschool/at the gym).
NL_GLOSSES.update({
    "abonnement": "the membership", "dagpas": "the day pass",
    "FitNL": "FitNL (gym name)", "gewichten": "the weights",
    "instructeur": "the instructor", "loopband": "the treadmill",
    "ren": "run (with ik)", "sportschool": "the gym", "strand": "the beach",
    "til": "lift (with ik)", "yogales": "the yoga class",
})
PROPER_NOUNS.update({"FitNL"})
NOUNS.update({"abonnement", "dagpas", "gewichten", "instructeur", "loopband",
              "sportschool", "strand", "yogales"})
VERBS.update({"ren", "til"})

# Unit 61 (strand/a day at the beach).
NL_GLOSSES.update({
    "dierentuin": "the zoo", "Duinzicht": "Duinzicht (beach name)",
    "golf": "the wave", "parasol": "the beach umbrella",
    "parasols": "beach umbrellas", "zand": "the sand", "zee": "the sea",
})
PROPER_NOUNS.update({"Duinzicht"})
NOUNS.update({"dierentuin", "golf", "parasol", "parasols", "zand", "zee"})

# Unit 62 (dierentuin/at the zoo).
NL_GLOSSES.update({
    "aap": "the monkey", "giraffe": "the giraffe", "kaartjes": "tickets",
    "leeuw": "the lion", "leeuwen": "lions",
    "leeuwenverblijf": "the lion enclosure", "olifant": "the elephant",
    "rondvaart": "the boat tour", "voederen": "the feeding",
    "waren": "were (with wij/zij, past of zijn)", "Wildpark": "Wildpark (zoo name)",
})
PROPER_NOUNS.update({"Wildpark"})
NOUNS.update({"aap", "giraffe", "kaartjes", "leeuw", "leeuwen",
              "leeuwenverblijf", "olifant", "rondvaart", "voederen"})
VERBS.update({"waren"})

# Unit 63 (rondvaart/a canal boat tour).
NL_GLOSSES.update({
    "boot": "the boat", "brug": "the bridge", "gracht": "the canal",
    "steiger": "the pier", "Watertocht": "Watertocht (boat-tour company name)",
    "wedstrijd": "the match",
})
PROPER_NOUNS.update({"Watertocht"})
NOUNS.update({"boot", "brug", "gracht", "steiger", "wedstrijd"})

# Unit 64 (voetbalwedstrijd/at a football match).
NL_GLOSSES.update({
    "doelpunt": "the goal", "pretpark": "the amusement park",
    "scorebord": "the scoreboard", "speler": "the player",
    "stadion": "the stadium", "stand": "the score", "supporter": "the fan",
    "team": "the team", "thuisteam": "the home team", "uitteam": "the away team",
    "winnaar": "the winner",
})
NOUNS.update({"doelpunt", "pretpark", "scorebord", "speler", "stadion", "stand",
              "supporter", "team", "thuisteam", "uitteam", "winnaar"})

# Unit 65 (pretpark/at the amusement park).
NL_GLOSSES.update({
    "achtbaan": "the roller coaster", "attractie": "the ride",
    "hoog": "high; tall", "kassa": "the ticket counter",
    "lengte": "the height", "meter": "metre", "minimale": "minimum (inflected)",
    "plattegrond": "the map", "reuzenrad": "the Ferris wheel", "rij": "the queue",
    "theater": "the theatre", "Zonneland": "Zonneland (amusement-park name)",
})
PROPER_NOUNS.update({"Zonneland"})
NOUNS.update({"achtbaan", "attractie", "kassa", "lengte", "meter",
              "plattegrond", "reuzenrad", "rij", "theater"})
ADJECTIVES.update({"hoog", "minimale"})

# Unit 66 (theater/at the theatre).
NL_GLOSSES.update({
    "acteurs": "the actors", "gordijn": "the curtain", "populair": "popular",
    "Ster": "Ster (theatre name)", "stoel": "the seat", "tevreden": "satisfied",
    "toneelstuk": "the play",
})
PROPER_NOUNS.update({"Ster"})
NOUNS.update({"acteurs", "gordijn", "stoel", "toneelstuk"})
ADJECTIVES.update({"populair", "tevreden"})

# Unit 67 (markt/at the market).
NL_GLOSSES.update({
    "bakker": "the bakery", "Jansen": "Jansen (business name)",
    "marktkoopman": "the market vendor", "vers": "fresh",
})
PROPER_NOUNS.update({"Jansen"})
NOUNS.update({"bakker", "marktkoopman"})
ADJECTIVES.update({"vers"})

# Unit 68 (bakker/at the bakery).
NL_GLOSSES.update({
    "bakkerij": "the bakery (shop)", "croissant": "the croissant",
    "croissants": "croissants", "gebak": "the pastry",
    "gebakken": "baked (past participle of bakken)",
    "ijssalon": "the ice cream parlour", "Peters": "Peters (business name)",
    "toonbank": "the counter", "zak": "the bag", "zoet": "sweet",
})
PROPER_NOUNS.update({"Peters"})
NOUNS.update({"bakkerij", "croissant", "croissants", "gebak", "ijssalon",
              "toonbank", "zak"})
VERBS.update({"gebakken"})
ADJECTIVES.update({"zoet"})

# Unit 69 (ijssalon/at the ice cream parlour).
NL_GLOSSES.update({
    "bakje": "the cup (of ice cream)", "bloemist": "the flower shop",
    "bolletje": "the scoop", "bolletjes": "scoops", "hoorntje": "the cone",
    "ijs": "the ice cream", "smaken": "flavours", "Smit": "Smit (business name)",
    "verse": "fresh (inflected)", "vitrine": "the display case",
})
PROPER_NOUNS.update({"Smit"})
NOUNS.update({"bakje", "bloemist", "bolletje", "bolletjes", "hoorntje", "ijs",
              "smaken", "vitrine"})
ADJECTIVES.update({"verse"})

# Unit 70 (bloemist/at the flower shop).
NL_GLOSSES.update({
    "bloem": "the flower", "bloemen": "flowers", "boeket": "the bouquet",
    "boekwinkel": "the bookshop", "lint": "the ribbon", "roos": "the rose",
    "rozen": "roses", "tulp": "the tulip",
})
NOUNS.update({"bloem", "bloemen", "boeket", "boekwinkel", "lint", "roos",
              "rozen", "tulp"})

# Unit 71 (boekwinkel/at the bookshop).
NL_GLOSSES.update({
    "bekend": "well-known", "bladwijzer": "the bookmark",
    "dierenwinkel": "the pet shop", "kinderboek": "the children's book",
    "kinderboeken": "children's books", "roman": "the novel",
    "schrijver": "the author", "titel": "the title",
})
NOUNS.update({"bladwijzer", "dierenwinkel", "kinderboek", "kinderboeken",
              "roman", "schrijver", "titel"})
ADJECTIVES.update({"bekend"})

# Unit 72 (dierenwinkel/at the pet shop).
NL_GLOSSES.update({
    "mand": "the basket", "riem": "the leash", "slaapt": "sleeps (with hij/zij)",
    "speeltje": "the toy", "voer": "the pet food", "vogelvoer": "the bird food",
    "Vrolik": "Vrolik (business name)",
})
PROPER_NOUNS.update({"Vrolik"})
NOUNS.update({"mand", "riem", "speeltje", "voer", "vogelvoer"})
VERBS.update({"slaapt"})

# --- 2026-08-02: Dutch B2 tier tokens (units 01-08) ---
# 168 tokens introduced by docs/content/realizations/nl/b2_unit0*.yaml
# that were absent from NL_GLOSSES. Glosses are the atomic English
# meaning of each token's TAUGHT sense, taken from the en-nl b2 overlay
# teaching gloss/note for the card that introduces it. Capitalized
# sentence-initial forms reuse their lowercase gloss (Dat=dat, De=de,
# Nee=nee), matching this file's older capitalized-variant convention.
# DRAFT B2 content pending native-Dutch review.
NL_GLOSSES.update({
    "aankleedde": "got dressed",
    "aankwam": "arrived",
    "absoluut": "absolutely",
    "Afgesproken": "agreed; it's a deal",
    "afwast": "do the dishes; wash up (with jij)",
    "afwegend": "weighing up; considering",
    "akkoord": "agreed; in agreement",
    "autovrij": "car-free (base form)",
    "autovrije": "car-free (inflected)",
    "baas": "the boss",
    "bedoel": "mean (with ik)",
    "begonnen": "begun; started",
    "beide": "both (the two)",
    "belangrijk": "important",
    "bespaar": "save (time/money)",
    "besparen": "to save (time, money)",
    "beweert": "claims (with hij/zij)",
    "beweren": "to claim",
    "bijvoorbeeld": "for example",
    "blijken": "to appear; to turn out",
    "blijkt": "appears; shows (with uit ... dat)",
    "boodschappen": "the groceries; the shopping",
    "bron": "the source",
    "bronnen": "sources",
    "daardoor": "as a result; because of that",
    "daarentegen": "by contrast; on the other hand",
    "daarnaast": "in addition; besides",
    "Dat": "that",
    "De": "the",
    "degelijk": "most certainly (in 'wel degelijk')",
    "ding": "thing",
    "donker": "dark",
    "duurzaamheid": "sustainability",
    "enigszins": "somewhat; slightly",
    "erop": "at it; on it (in 'het lijkt erop dat')",
    "ervan": "of it; about it (in 'ervan overtuigd')",
    "ervoor": "before that; beforehand (in 'de avond ervoor')",
    "etentje": "dinner party",
    "file": "the traffic jam",
    "Geachte": "dear (formal salutation)",
    "gebeurd": "happened",
    "gebeuren": "to happen",
    "gemist": "missed",
    "gevallen": "cases (in 'in veel gevallen')",
    "gezet": "set (put)",
    "gezonder": "healthier",
    "gok": "guess (with ik)",
    "gokken": "to guess",
    "groetjes": "cheers; take care (informal sign-off)",
    "haast": "hurry; haste",
    "hangen": "to depend (in 'afhangen'); to hang",
    "hangt": "depends (in 'hangt ervan af')",
    "heer": "sir; gentleman",
    "helaas": "unfortunately",
    "Helemaal": "completely; totally",
    "helft": "half",
    "hoi": "hi",
    "Hoogachtend": "yours faithfully (most formal sign-off)",
    "hoogte": "extent (in 'tot op zekere hoogte'); height",
    "juist": "precisely; exactly",
    "kloppen": "to be right; to check out",
    "klopt": "is right; is correct",
    "komedie": "a comedy",
    "kortom": "in short",
    "langzaam": "slow; slowly",
    "lijkt": "seems; looks like",
    "mail": "e-mail (with ik)",
    "mailen": "to e-mail",
    "mevrouw": "madam",
    "missen": "to miss",
    "mist": "miss (with je)",
    "miste": "missed",
    "mits": "provided that",
    "moeite": "effort; trouble",
    "nadat": "after (conjunction)",
    "nadeel": "the disadvantage; drawback",
    "nadelen": "disadvantages; drawbacks",
    "Nee": "no",
    "negatief": "negative",
    "netjes": "properly; neatly; politely",
    "nogal": "rather; fairly",
    "nou": "well (in 'nou juist': exactly)",
    "onderbouwd": "backed up; well-supported",
    "onderbouwen": "to back up; to support with evidence",
    "onderweg": "on the way; en route",
    "onderzoek": "research",
    "ongetwijfeld": "undoubtedly",
    "ontwikkeling": "development",
    "ontzettend": "incredibly; tremendously",
    "onze": "our",
    "overtuigd": "convinced",
    "overtuigend": "convincing",
    "Pauw": "Pauw (restaurant name, 'De Pauw')",
    "pizza": "pizza",
    "positief": "positive",
    "prijs": "the price",
    "productief": "productive",
    "productiever": "more productive",
    "recensie": "the review",
    "recensies": "reviews",
    "redden": "to save; to rescue",
    "redt": "saves; rescues",
    "regende": "rained; was raining",
    "regenen": "to rain",
    "reistijd": "commute; travel time",
    "samenleving": "society",
    "schikt": "suits; is convenient",
    "se": "(in 'per se') necessarily; as such",
    "snappen": "to understand; to get",
    "sommigen": "some people",
    "spitsuur": "rush hour",
    "sprak": "spoke",
    "standpunt": "a position; point of view",
    "steden": "cities",
    "stel": "propose (with ik, in 'stel voor')",
    "stelt": "states; asserts (with hij/zij)",
    "succes": "a success",
    "tegenstelling": "contrast (in 'in tegenstelling tot')",
    "tellen": "to count; to matter",
    "telt": "counts; matters",
    "ten": "(in 'ten eerste/tweede') firstly/secondly; at the",
    "tenzij": "unless",
    "terwijl": "while; whereas",
    "Thomas": "Thomas",
    "thuiswerken": "working from home",
    "thuiswerkers": "people who work from home; teleworkers",
    "toen": "when (past); then",
    "traag": "slow",
    "uiteindelijk": "in the end; eventually",
    "vanochtend": "this morning",
    "verantwoordelijkheid": "responsibility",
    "vergeten": "to forget; forgotten",
    "verschillen": "to differ; to disagree",
    "verschilt": "differs; disagrees",
    "verslapen": "to oversleep",
    "vertrekken": "to leave; to depart",
    "vertrok": "left; departed",
    "vertrokken": "left; departed",
    "vervolgens": "next; subsequently",
    "verwacht": "expect (with ik); expects",
    "verwachten": "to expect",
    "verwarrend": "confusing",
    "verzetten": "to reschedule; to move (an appointment)",
    "videobellen": "to video-call",
    "volgens": "according to",
    "vond": "thought; found (with je)",
    "voordat": "before (conjunction)",
    "voordeel": "the advantage",
    "voordelen": "advantages",
    "voorspelbaar": "predictable",
    "voorstel": "proposal",
    "Vries": "Vries (surname, 'Lotte de Vries')",
    "vrijheid": "freedom",
    "waard": "worth (in 'de moeite waard')",
    "waarom": "why",
    "wakker": "awake",
    "weegt": "weighs; carries weight",
    "weg": "away; gone",
    "wegen": "to weigh; to carry weight",
    "wekker": "the alarm clock",
    "wellicht": "perhaps; possibly",
    "werd": "became",
    "zag": "saw",
    "zal": "will; shall (with hij/zij)",
    "zeker": "certainly; for sure",
    "zekere": "certain (inflected)",
    "zetten": "to set; to put",
    "zwaarder": "heavier",
})
# Part-of-speech for the same tokens (Dat/De/Nee already classified).
PROPER_NOUNS.update({"Pauw", "Thomas", "Vries"})
PRONOUNS.update({"beide", "onze", "sommigen"})
PREPOSITIONS.update({"ten", "volgens"})
PARTICLES.update({"Afgesproken", "groetjes", "hoi", "mits", "nadat", "nou", "se", "tenzij", "terwijl", "toen", "voordat"})
ADJECTIVES.update({"akkoord", "autovrij", "autovrije", "belangrijk", "donker", "Geachte", "gezonder", "langzaam", "negatief", "onderbouwd", "overtuigd", "overtuigend", "positief", "productief", "productiever", "traag", "verwarrend", "voorspelbaar", "waard", "wakker", "zekere", "zwaarder"})
ADVERBS.update({"absoluut", "bijvoorbeeld", "daardoor", "daarentegen", "daarnaast", "degelijk", "enigszins", "erop", "ervan", "ervoor", "helaas", "Helemaal", "Hoogachtend", "juist", "kortom", "netjes", "nogal", "onderweg", "ongetwijfeld", "ontzettend", "uiteindelijk", "vanochtend", "vervolgens", "waarom", "weg", "wellicht", "zeker"})
VERBS.update({"aankleedde", "aankwam", "afwast", "afwegend", "bedoel", "begonnen", "bespaar", "besparen", "beweert", "beweren", "blijken", "blijkt", "gebeurd", "gebeuren", "gemist", "gezet", "gok", "gokken", "hangen", "hangt", "kloppen", "klopt", "lijkt", "mail", "mailen", "missen", "mist", "miste", "onderbouwen", "redden", "redt", "regende", "regenen", "schikt", "snappen", "sprak", "stel", "stelt", "tellen", "telt", "vergeten", "verschillen", "verschilt", "verslapen", "vertrekken", "vertrok", "vertrokken", "verwacht", "verwachten", "verzetten", "videobellen", "vond", "weegt", "wegen", "werd", "zag", "zal", "zetten"})
NOUNS.update({"baas", "boodschappen", "bron", "bronnen", "ding", "duurzaamheid", "etentje", "file", "gevallen", "haast", "heer", "helft", "hoogte", "komedie", "mevrouw", "moeite", "nadeel", "nadelen", "onderzoek", "ontwikkeling", "pizza", "prijs", "recensie", "recensies", "reistijd", "samenleving", "spitsuur", "standpunt", "steden", "succes", "tegenstelling", "thuiswerken", "thuiswerkers", "verantwoordelijkheid", "voordeel", "voordelen", "voorstel", "vrijheid", "wekker"})



# --- 2026-10-10: Dutch C1 tier (units 01-08) ---------------------------------
# C1 capitals are folded onto their lowercase citation form (the same data-
# quality reasoning as NL_CITATION_FORMS: a sentence-initial "Terzijde" or
# "Desalniettemin" would otherwise display capitalized as a matching_pairs left
# and in the "correct answer" line). Scoped to the C1 course only, so no
# A1-B2 lexeme can change. Genuine capitals -- names, the language/nationality
# adjectives and the letter salutations -- are kept.
NL_C1_KEEP_CAPITALIZED = frozenset({
    "Amsterdam", "Lotte", "Omar", "Vries",
    "Engels", "Engelse", "Nederlands",
    "Beste", "Geachte",
})


def nl_c1_citation_form(token: str) -> str:
    # c1_unit06 lists the casefold "eén" of its sentence-initial "Eén" as an
    # introduced token; the citation spelling is "één".
    if token in {"Eén", "eén"}:
        return "één"
    if token[:1].isupper() and token not in NL_C1_KEEP_CAPITALIZED:
        return token[:1].lower() + token[1:]
    return token


# C1 glosses are shown alone as the prompt of bare-word typed translations,
# which accept only the bare Dutch token. A gloss written "the problem" makes
# the natural answer "het probleem" fail (defect 1.40), and in word_order hints
# it renders as "de the ball". C1 therefore drops a leading English article from
# every gloss alternative of a noun ("the answer; the reply" -> "answer; reply"). Scoped
# to the C1 course only, so no A1-B2 lexeme changes.
_NL_C1_LEADING_ARTICLE = re.compile(r"(^|;\s*)the\s+", re.IGNORECASE)


def nl_c1_bare_gloss(gloss: str) -> str:
    return _NL_C1_LEADING_ARTICLE.sub(r"\1", gloss)


# Extra C1-only semantic tags, keyed by (folded) token: single-member anchors
# (`*_single`) for fill_in_blank / fixed-sentence frames, and curated content
# groups for matching_pairs. Applied only to tokens introduced in a C1 lesson.
NL_C1_EXTRA_TAGS: dict[str, list[str]] = {
    'druk': ['c1u01_druk_single'],
    'hoofdgedachte': ['c1u01_hoofdgedachte_single'],
    'levert': ['c1u01_levert_single'],
    'namelijk': ['c1u01_namelijk_single', 'c1u01_punten_vertaal'],
    'noemen': ['c1u01_noemen_single'],
    'pleit': ['c1u01_pleit_single', 'c1u01_samenhang_vertaal'],
    "auto's": ['c1u01_samenhang_vertaal'],
    'geleidelijke': ['c1u01_samenhang_vertaal'],
    'maakt': ['c1u01_samenhang_vertaal'],
    'minder': ['c1u01_samenhang_vertaal'],
    'ontstaat': ['c1u01_samenhang_vertaal'],
    'voorstel': ['c1u01_samenhang_vertaal'],
    'schets': ['c1u01_schets_single', 'c1u01_koers_vertaal'],
    'begrijpelijke': ['c1u01_uitstapje_vertaal'],
    'bezwaar': ['c1u01_uitstapje_vertaal'],
    'maak': ['c1u01_uitstapje_vertaal'],
    'nu': ['c1u01_uitstapje_vertaal'],
    'omzetverlies': ['c1u01_uitstapje_vertaal'],
    'vrezen': ['c1u01_uitstapje_vertaal'],
    'weg': ['c1u01_weg_single', 'c1u01_terugkeren_vertaal'],
    'afwijzing': ['c1u02_kern', 'c1u02_afwijzing_single', 'c1u02_vert'],
    'bedoeling': ['c1u02_kern', 'c1u02_bedoeling_single'],
    'bepaald': ['c1u02_kern', 'c1u02_bepaald_single'],
    'genoeg': ['c1u02_kern', 'c1u02_genoeg_single'],
    'alleen': ['c1u02_kern'],
    'antwoordde': ['c1u02_kern', 'c1u02_vert'],
    'begon': ['c1u02_kern', 'c1u02_vert'],
    'begrijp': ['c1u02_kern'],
    'behoorlijk': ['c1u02_kern'],
    'beleefd': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'beleefdheid': ['c1u02_kern', 'c1u02_vert'],
    'betekent': ['c1u02_kern', 'c1u02_vert'],
    'blijkt': ['c1u02_kern'],
    'chaotisch': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'dia': ['c1u02_kern', 'c1u02_vert'],
    'directeur': ['c1u02_kern', 'c1u02_vert'],
    'duidelijk': ['c1u02_kern', 'c1u02_paar_adj'],
    'echter': ['c1u02_kern', 'c1u02_vert'],
    'enthousiast': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'ernstig': ['c1u02_kern', 'c1u02_paar_adj'],
    'ging': ['c1u02_kern', 'c1u02_vert'],
    'impliceren': ['c1u02_kern', 'c1u02_vert'],
    'ingehouden': ['c1u02_kern', 'c1u02_paar_adj'],
    'klonken': ['c1u02_kern', 'c1u02_vert'],
    'kon': ['c1u02_kern', 'c1u02_vert'],
    'kritiek': ['c1u02_kern', 'c1u02_vert'],
    'kritische': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'laatste': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'letterlijk': ['c1u02_kern', 'c1u02_vert'],
    'letterlijke': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'lezen': ['c1u02_kern', 'c1u02_vert'],
    'microfoon': ['c1u02_kern', 'c1u02_microfoon_single', 'c1u02_vert'],
    'minuten': ['c1u02_kern', 'c1u02_vert'],
    'misging': ['c1u02_kern'],
    'negatieve': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'ontevreden': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'ontevredenheid': ['c1u02_kern'],
    'ontkent': ['c1u02_kern', 'c1u02_vert'],
    'positief': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'presentatie': ['c1u02_kern', 'c1u02_presentatie_single', 'c1u02_vert'],
    'problemen': ['c1u02_kern', 'c1u02_vert'],
    'ramp': ['c1u02_kern', 'c1u02_vert'],
    'rampzalig': ['c1u02_kern', 'c1u02_paar_adj'],
    'rechtstreeks': ['c1u02_kern'],
    'regels': ['c1u02_kern', 'c1u02_vert'],
    'samen': ['c1u02_kern', 'c1u02_vert'],
    'soepel': ['c1u02_kern', 'c1u02_paar_adj'],
    'spreken': ['c1u02_kern'],
    'stilte': ['c1u02_kern', 'c1u02_vert'],
    'suggereert': ['c1u02_kern', 'c1u02_vert'],
    'teleurgesteld': ['c1u02_kern', 'c1u02_teleurgesteld_single', 'c1u02_vert'],
    'toon': ['c1u02_kern', 'c1u02_vert'],
    'uitgedrukt': ['c1u02_kern'],
    'verbergen': ['c1u02_kern'],
    'verbetering': ['c1u02_kern', 'c1u02_vert'],
    'verliep': ['c1u02_kern', 'c1u02_vert'],
    'viel': ['c1u02_kern', 'c1u02_vert'],
    'vlakke': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_vert'],
    'vlekkeloos': ['c1u02_kern', 'c1u02_paar_adj'],
    'voorbehoud': ['c1u02_kern', 'c1u02_vert'],
    'waren': ['c1u02_kern', 'c1u02_vert'],
    'wijzen': ['c1u02_kern'],
    'woorden': ['c1u02_kern', 'c1u02_vert'],
    'woordkeus': ['c1u02_kern'],
    'zacht': ['c1u02_kern', 'c1u02_paar_adj', 'c1u02_zacht_single'],
    'zegt': ['c1u02_kern', 'c1u02_vert'],
    'zei': ['c1u02_kern', 'c1u02_vert'],
    'milde': ['c1u02_milde_single'],
    'antwoorden': ['c1u03_verb_core', 'c1u03_antwoorden_single'],
    'benadrukken': ['c1u03_verb_core', 'c1u03_benadrukken_single'],
    'bepalen': ['c1u03_verb_core', 'c1u03_bepalen_single'],
    'beschermt': ['c1u03_verb_core', 'c1u03_beschermt_single', 'c1u03_verb_tr'],
    'gelijk': ['c1u03_mod_core', 'c1u03_gelijk_single', 'c1u03_mod_core_b'],
    'mislukt': ['c1u03_verb_core', 'c1u03_mislukt_single'],
    'absoluut': ['c1u03_mod_core', 'c1u03_mod_tr', 'c1u03_mod_core_a', 'c1u03_mod_tr_a'],
    'alweer': ['c1u03_mod_core', 'c1u03_mod_core_b'],
    'diplomatieke': ['c1u03_mod_core', 'c1u03_mod_tr', 'c1u03_mod_core_a', 'c1u03_mod_tr_a'],
    'direct': ['c1u03_mod_core', 'c1u03_mod_core_a'],
    'doeltreffend': ['c1u03_mod_core', 'c1u03_mod_core_b'],
    'formeel': ['c1u03_mod_core', 'c1u03_mod_tr', 'c1u03_mod_core_a', 'c1u03_mod_tr_a'],
    'gewenste': ['c1u03_mod_core', 'c1u03_mod_tr', 'c1u03_mod_core_a', 'c1u03_mod_tr_a'],
    'herhaald': ['c1u03_mod_core', 'c1u03_mod_tr', 'c1u03_mod_core_b', 'c1u03_mod_tr_b'],
    'ironisch': ['c1u03_mod_core', 'c1u03_mod_tr', 'c1u03_mod_core_b', 'c1u03_mod_tr_b'],
    'noodzakelijk': ['c1u03_mod_core', 'c1u03_noodzakelijk_single', 'c1u03_mod_core_a'],
    'ongepast': ['c1u03_mod_core', 'c1u03_mod_core_b'],
    'oprecht': ['c1u03_mod_core', 'c1u03_mod_tr', 'c1u03_mod_core_b', 'c1u03_mod_tr_b'],
    'passende': ['c1u03_mod_core', 'c1u03_mod_core_b'],
    'positieve': ['c1u03_mod_core', 'c1u03_mod_tr', 'c1u03_mod_core_b', 'c1u03_mod_tr_b'],
    'uitstekend': ['c1u03_mod_core', 'c1u03_mod_core_a'],
    'vandaag': ['c1u03_mod_core', 'c1u03_mod_tr', 'c1u03_mod_core_a', 'c1u03_mod_tr_a'],
    'voortreffelijk': ['c1u03_voortreffelijk_single', 'c1u03_mod_core_b'],
    'vriendelijk': ['c1u03_mod_core', 'c1u03_mod_core_a'],
    'wellicht': ['c1u03_mod_core', 'c1u03_mod_core_a'],
    'werkelijk': ['c1u03_mod_core', 'c1u03_mod_core_a'],
    'afstand': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'ambtenaar': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'antwoord': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_a', 'c1u03_noun_tr_a'],
    'diplomatie': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'directheid': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'doel': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'focuszin': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_a', 'c1u03_noun_tr_a'],
    'formulering': ['c1u03_noun_core', 'c1u03_noun_core_a'],
    'gemeente': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_a', 'c1u03_noun_tr_a'],
    'groet': ['c1u03_noun_core', 'c1u03_noun_core_a'],
    'heer': ['c1u03_noun_core', 'c1u03_noun_core_a'],
    'inhoud': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'intensiteit': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'ironie': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'levering': ['c1u03_noun_core', 'c1u03_noun_core_b'],
    'lezing': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b'],
    'lof': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'nadruk': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'optie': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_a', 'c1u03_noun_tr_a'],
    'prijs': ['c1u03_noun_core', 'c1u03_prijs_single', 'c1u03_noun_tr', 'c1u03_noun_core_a', 'c1u03_noun_tr_a'],
    'relatie': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'termijn': ['c1u03_noun_core', 'c1u03_noun_core_a'],
    'uitstel': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_a', 'c1u03_noun_tr_a'],
    'versie': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'voorrang': ['c1u03_noun_core', 'c1u03_noun_core_a'],
    'vriend': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_b', 'c1u03_noun_tr_b'],
    'waardering': ['c1u03_noun_core', 'c1u03_noun_tr', 'c1u03_noun_core_a', 'c1u03_noun_tr_a'],
    'bekijken': ['c1u03_verb_core'],
    'blijft': ['c1u03_verb_core', 'c1u03_verb_tr'],
    'blokkeert': ['c1u03_verb_core', 'c1u03_verb_tr'],
    'falen': ['c1u03_verb_core'],
    'geregeld': ['c1u03_verb_core'],
    'meen': ['c1u03_verb_core'],
    'omkeren': ['c1u03_verb_core'],
    'opgelost': ['c1u03_verb_core', 'c1u03_verb_tr'],
    'schrijft': ['c1u03_verb_core', 'c1u03_verb_tr'],
    'stellen': ['c1u03_verb_core'],
    'veranderen': ['c1u03_verb_core'],
    'verhogen': ['c1u03_verb_core'],
    'verkleint': ['c1u03_verb_core'],
    'versterkt': ['c1u03_verb_core', 'c1u03_verb_tr'],
    'verzwijgen': ['c1u03_verb_core', 'c1u03_verb_tr'],
    'afweging': ['c1u04_afwegen_kern', 'c1u04_afwegen_vert'],
    'anderzijds': ['c1u04_afwegen_kern'],
    'conclusie': ['c1u04_afwegen_kern'],
    'enerzijds': ['c1u04_afwegen_kern'],
    'groeit': ['c1u04_afwegen_kern', 'c1u04_afwegen_vert'],
    'stijgen': ['c1u04_afwegen_kern', 'c1u04_afwegen_vert'],
    'toegankelijkheid': ['c1u04_afwegen_kern', 'c1u04_afwegen_vert'],
    'uiteindelijk': ['c1u04_afwegen_kern', 'c1u04_afwegen_vert'],
    'voorkeur': ['c1u04_afwegen_kern', 'c1u04_afwegen_vert'],
    'weegt': ['c1u04_afwegen_kern', 'c1u04_afwegen_vert'],
    'zichtbaar': ['c1u04_afwegen_kern', 'c1u04_afwegen_vert'],
    'zwaarder': ['c1u04_afwegen_kern', 'c1u04_zwaarder_single', 'c1u04_afwegen_vert'],
    'afwegend': ['c1u04_afwegend_single'],
    'baat': ['c1u04_tegenbewijs_kern', 'c1u04_baat_single'],
    'bibliotheek': ['c1u04_ontleden_kern', 'c1u04_bibliotheek_single', 'c1u04_ontleden_vert'],
    'doorslaggevend': ['c1u04_reikwijdte_kern', 'c1u04_doorslaggevend_single'],
    'gewicht': ['c1u04_toegeven_kern', 'c1u04_gewicht_single', 'c1u04_toegeven_vert'],
    'meebrengen': ['c1u04_toegeven_kern', 'c1u04_meebrengen_single'],
    'nadeel': ['c1u04_ontleden_kern', 'c1u04_nadeel_single', 'c1u04_ontleden_vert'],
    'begrenzing': ['c1u04_ontleden_kern'],
    'beweegt': ['c1u04_ontleden_kern', 'c1u04_ontleden_vert'],
    'centrale': ['c1u04_ontleden_kern', 'c1u04_ontleden_vert'],
    'daarom': ['c1u04_ontleden_kern'],
    'eindoordeel': ['c1u04_ontleden_kern', 'c1u04_ontleden_vert'],
    'financiële': ['c1u04_ontleden_kern', 'c1u04_ontleden_vert'],
    'gemotiveerd': ['c1u04_ontleden_kern'],
    'personeelskosten': ['c1u04_ontleden_kern', 'c1u04_ontleden_vert'],
    'tegenbewijs': ['c1u04_ontleden_kern', 'c1u04_ontleden_vert'],
    'tekst': ['c1u04_ontleden_kern', 'c1u04_ontleden_vert'],
    'toch': ['c1u04_ontleden_kern'],
    'wegen': ['c1u04_ontleden_kern', 'c1u04_ontleden_vert'],
    'openblijft': ['c1u04_reikwijdte_kern', 'c1u04_openblijft_single'],
    'proef': ['c1u04_tegenbewijs_kern', 'c1u04_proef_single'],
    'avond': ['c1u04_reikwijdte_kern', 'c1u04_reikwijdte_vert'],
    'beperkt': ['c1u04_reikwijdte_kern'],
    'filiaal': ['c1u04_reikwijdte_kern'],
    'geldt': ['c1u04_reikwijdte_kern', 'c1u04_reikwijdte_vert'],
    'hoogte': ['c1u04_reikwijdte_kern'],
    'kwalificatie': ['c1u04_reikwijdte_kern'],
    'omstandigheden': ['c1u04_reikwijdte_kern', 'c1u04_reikwijdte_vert'],
    'onbetaalbaar': ['c1u04_reikwijdte_kern', 'c1u04_reikwijdte_vert'],
    'vooral': ['c1u04_reikwijdte_kern'],
    'waar': ['c1u04_reikwijdte_kern', 'c1u04_reikwijdte_vert'],
    'waarin': ['c1u04_reikwijdte_kern', 'c1u04_reikwijdte_vert'],
    'wanneer': ['c1u04_reikwijdte_kern'],
    'zekere': ['c1u04_reikwijdte_kern'],
    'aantoonbaar': ['c1u04_tegenbewijs_kern', 'c1u04_tegenbewijs_vert'],
    'beantwoordt': ['c1u04_tegenbewijs_kern'],
    'beperkte': ['c1u04_tegenbewijs_kern', 'c1u04_tegenbewijs_vert'],
    'bereik': ['c1u04_tegenbewijs_kern'],
    'desalniettemin': ['c1u04_tegenbewijs_kern'],
    'maatschappelijk': ['c1u04_tegenbewijs_kern', 'c1u04_tegenbewijs_vert'],
    'nut': ['c1u04_tegenbewijs_kern'],
    'rechtvaardigt': ['c1u04_tegenbewijs_kern', 'c1u04_tegenbewijs_vert'],
    'studenten': ['c1u04_tegenbewijs_kern', 'c1u04_tegenbewijs_vert'],
    'tegenargument': ['c1u04_tegenbewijs_kern', 'c1u04_tegenbewijs_vert'],
    'werkenden': ['c1u04_tegenbewijs_kern', 'c1u04_tegenbewijs_vert'],
    'benoemt': ['c1u04_toegeven_kern'],
    'concessie': ['c1u04_toegeven_kern'],
    'daarvoor': ['c1u04_toegeven_kern'],
    'echte': ['c1u04_toegeven_kern'],
    'klopt': ['c1u04_toegeven_kern'],
    'kosten': ['c1u04_toegeven_kern', 'c1u04_toegeven_vert'],
    'kracht': ['c1u04_toegeven_kern', 'c1u04_toegeven_vert'],
    'nodig': ['c1u04_toegeven_kern'],
    'openingstijden': ['c1u04_toegeven_kern', 'c1u04_toegeven_vert'],
    'personeel': ['c1u04_toegeven_kern', 'c1u04_toegeven_vert'],
    'ruimere': ['c1u04_toegeven_kern'],
    'serieus': ['c1u04_toegeven_kern'],
    'verdient': ['c1u04_toegeven_kern', 'c1u04_toegeven_vert'],
    'volgt': ['c1u04_toegeven_kern', 'c1u04_toegeven_vert'],
    'afgewezen': ['c1u05_inhoud', 'c1u05_afgewezen_single', 'c1u05_verb_b'],
    'gegrepen': ['c1u05_inhoud', 'c1u05_gegrepen_single', 'c1u05_verb_a'],
    'gezien': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_gezien_single', 'c1u05_verb_a'],
    'heden': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_heden_single'],
    'aangeboden': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_verb_a'],
    'aangenomen': ['c1u05_inhoud', 'c1u05_verb_a'],
    'achteraf': ['c1u05_inhoud', 'c1u05_vertaal'],
    'anders': ['c1u05_inhoud', 'c1u05_vertaal'],
    'baan': ['c1u05_inhoud'],
    'beide': ['c1u05_inhoud'],
    'ben': ['c1u05_inhoud', 'c1u05_verb_b'],
    'beter': ['c1u05_inhoud', 'c1u05_vertaal'],
    'blijven': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_verb_b'],
    'feit': ['c1u05_inhoud', 'c1u05_vertaal'],
    'gehad': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_verb_a'],
    'geleden': ['c1u05_inhoud', 'c1u05_vertaal'],
    'gemengde': ['c1u05_inhoud', 'c1u05_vertaal'],
    'gevolg': ['c1u05_inhoud'],
    'heb': ['c1u05_inhoud', 'c1u05_verb_b'],
    'heel': ['c1u05_inhoud'],
    'hier': ['c1u05_inhoud', 'c1u05_vertaal'],
    'jaar': ['c1u05_inhoud', 'c1u05_vertaal'],
    'jou': ['c1u05_inhoud'],
    'jullie': ['c1u05_inhoud'],
    'kans': ['c1u05_inhoud', 'c1u05_vertaal'],
    'kennen': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_kennen_single', 'c1u05_verb_b'],
    'keten': ['c1u05_inhoud', 'c1u05_vertaal'],
    'kiezen': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_verb_a'],
    'kort': ['c1u05_inhoud', 'c1u05_vertaal'],
    'kreeg': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_verb_a'],
    'kun': ['c1u05_inhoud', 'c1u05_verb_a'],
    'leren': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_leren_single', 'c1u05_verb_b'],
    'leven': ['c1u05_inhoud', 'c1u05_vertaal'],
    'loopt': ['c1u05_inhoud', 'c1u05_verb_b'],
    'misschien': ['c1u05_inhoud', 'c1u05_misschien_single'],
    'moeten': ['c1u05_inhoud', 'c1u05_verb_a'],
    'naast': ['c1u05_inhoud'],
    'nadenken': ['c1u05_inhoud', 'c1u05_verb_a'],
    'nooit': ['c1u05_inhoud', 'c1u05_vertaal'],
    'ontmoet': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_ontmoet_single', 'c1u05_verb_a'],
    'onwerkelijke': ['c1u05_inhoud', 'c1u05_vertaal'],
    'over': ['c1u05_inhoud'],
    'spijt': ['c1u05_inhoud', 'c1u05_vertaal'],
    'staan': ['c1u05_inhoud', 'c1u05_verb_a'],
    'taalcafé': ['c1u05_inhoud', 'c1u05_vertaal'],
    'tijd': ['c1u05_inhoud', 'c1u05_vertaal'],
    'tijdlijn': ['c1u05_inhoud', 'c1u05_vertaal'],
    'uitdrukken': ['c1u05_inhoud', 'c1u05_verb_a'],
    'ver': ['c1u05_inhoud', 'c1u05_vertaal'],
    'verbindt': ['c1u05_inhoud', 'c1u05_verb_a'],
    'verhuisd': ['c1u05_inhoud', 'c1u05_vertaal', 'c1u05_verhuisd_single', 'c1u05_verb_a'],
    'verleden': ['c1u05_inhoud', 'c1u05_vertaal'],
    'voltooid': ['c1u05_inhoud'],
    'voorwaarde': ['c1u05_inhoud', 'c1u05_vertaal'],
    'vrienden': ['c1u05_inhoud', 'c1u05_vertaal'],
    'want': ['c1u05_inhoud'],
    'werkelijkheid': ['c1u05_inhoud'],
    'wilde': ['c1u05_inhoud', 'c1u05_verb_b'],
    'wonen': ['c1u05_inhoud', 'c1u05_verb_a'],
    'woonde': ['c1u05_inhoud', 'c1u05_woonde_single', 'c1u05_verb_a'],
    'zat': ['c1u05_inhoud', 'c1u05_zat_single', 'c1u05_verb_b'],
    'zinnen': ['c1u05_inhoud', 'c1u05_vertaal'],
    'bal': ['c1u06_beeld_noun', 'c1u06_bal_single', 'c1u06_tr_noun'],
    'aap': ['c1u06_beeld_noun', 'c1u06_tr_noun'],
    'handdoek': ['c1u06_beeld_noun', 'c1u06_handdoek_single', 'c1u06_tr_noun'],
    'hart': ['c1u06_beeld_noun', 'c1u06_tr_noun'],
    'huis': ['c1u06_beeld_noun', 'c1u06_tr_noun'],
    'kleren': ['c1u06_beeld_noun'],
    'mand': ['c1u06_beeld_noun', 'c1u06_mand_single', 'c1u06_tr_noun'],
    'mug': ['c1u06_beeld_noun', 'c1u06_tr_noun'],
    'olifant': ['c1u06_beeld_noun', 'c1u06_tr_noun'],
    'deur': ['c1u06_deur_single'],
    'Engels': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'Nederlands': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'eindelijk': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'figuurlijk': ['c1u06_kern_mod'],
    'gewoon': ['c1u06_kern_mod'],
    'goed': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'hoe': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'informeel': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'koude': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'levendig': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'natuurlijk': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'precies': ['c1u06_kern_mod'],
    'streng': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'vaste': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'vertaald': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'weinig': ['c1u06_kern_mod', 'c1u06_tr_mod'],
    'beslissen': ['c1u06_kern_verb'],
    'besprak': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'bracht': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'combineren': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'dacht': ['c1u06_kern_verb'],
    'draagt': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'ga': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'gaat': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'geeft': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'gooide': ['c1u06_kern_verb'],
    'gooien': ['c1u06_kern_verb'],
    'gooit': ['c1u06_kern_verb'],
    'houd': ['c1u06_kern_verb'],
    'klinkt': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'klopten': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'komt': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'kwam': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'kwamen': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'ligt': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'nemen': ['c1u06_kern_verb', 'c1u06_nemen_single'],
    'slaat': ['c1u06_kern_verb'],
    'sloeg': ['c1u06_kern_verb'],
    'vermijd': ['c1u06_kern_verb'],
    'vertalen': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'weet': ['c1u06_kern_verb'],
    'werkt': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'zie': ['c1u06_kern_verb', 'c1u06_tr_verb'],
    'zitten': ['c1u06_kern_verb'],
    'knie': ['c1u06_knie_single'],
    'koffiedik': ['c1u06_koffiedik_single'],
    'pet': ['c1u06_pet_single'],
    'spijker': ['c1u06_spijker_single'],
    'beeldspraak': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'beslissing': ['c1u06_taal_noun'],
    'bestuur': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'betekenis': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'buurthuis': ['c1u06_taal_noun'],
    'chef': ['c1u06_taal_noun'],
    'cijfers': ['c1u06_taal_noun'],
    'controle': ['c1u06_taal_noun'],
    'fouten': ['c1u06_taal_noun'],
    'gesprek': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'gevoel': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'lid': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'maand': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'onderwerp': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'uitdrukking': ['c1u06_taal_noun'],
    'verhaal': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'vertaling': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'vertalingen': ['c1u06_taal_noun', 'c1u06_tr_noun'],
    'behoudens': ['c1u07_behoudens_single', 'c1u07_l05_mc'],
    'bewezen': ['c1u07_bewezen_single', 'c1u07_l03_mc'],
    'hard': ['c1u07_hard_single', 'c1u07_match_modifiers', 'c1u07_l04_mc'],
    'helder': ['c1u07_helder_single', 'c1u07_match_modifiers', 'c1u07_l06_mc'],
    'artikel': ['c1u07_l01_mc', 'c1u07_l01_tr'],
    'bemiddelen': ['c1u07_match_verbs', 'c1u07_l01_mc', 'c1u07_l01_tr'],
    'bemiddelt': ['c1u07_l01_mc', 'c1u07_l01_tr'],
    'bouwen': ['c1u07_match_verbs', 'c1u07_l01_mc', 'c1u07_l01_tr'],
    'bron': ['c1u07_match_nouns', 'c1u07_l01_mc', 'c1u07_l01_tr'],
    'bronnen': ['c1u07_l01_mc', 'c1u07_l01_tr'],
    'buurtonderzoek': ['c1u07_l01_mc', 'c1u07_l01_tr'],
    'eerlijk': ['c1u07_match_modifiers', 'c1u07_l01_mc', 'c1u07_l01_tr'],
    'eigen': ['c1u07_match_modifiers', 'c1u07_l01_mc', 'c1u07_l01_tr'],
    'kernpunt': ['c1u07_l01_mc'],
    'klein': ['c1u07_match_modifiers', 'c1u07_l01_mc', 'c1u07_l01_tr'],
    'leg': ['c1u07_l01_mc'],
    'overlast': ['c1u07_l01_mc'],
    'samenvatten': ['c1u07_match_verbs', 'c1u07_l01_mc', 'c1u07_l01_tr'],
    'schrijver': ['c1u07_match_nouns', 'c1u07_l01_mc'],
    'standpunt': ['c1u07_l01_mc'],
    'twee': ['c1u07_l01_mc', 'c1u07_l01_tr'],
    'vat': ['c1u07_vat_single', 'c1u07_l01_mc'],
    'verdedigt': ['c1u07_match_verbs', 'c1u07_l01_mc', 'c1u07_l01_tr'],
    'volgens': ['c1u07_l01_mc', 'c1u07_l01_tr'],
    'vreest': ['c1u07_match_verbs', 'c1u07_l01_mc', 'c1u07_l01_tr'],
    'windmolenpark': ['c1u07_match_nouns', 'c1u07_l01_mc'],
    'andere': ['c1u07_match_modifiers', 'c1u07_l02_mc'],
    'bewoners': ['c1u07_match_nouns', 'c1u07_l02_mc'],
    'bezorgdheid': ['c1u07_match_nouns', 'c1u07_l02_mc'],
    'ene': ['c1u07_l02_mc'],
    'energie': ['c1u07_match_nouns', 'c1u07_l02_mc', 'c1u07_l02_tr'],
    'geluidsoverlast': ['c1u07_l02_mc'],
    'kant': ['c1u07_match_nouns', 'c1u07_l02_mc'],
    'minimaal': ['c1u07_l02_mc', 'c1u07_l02_tr'],
    'molens': ['c1u07_l02_mc'],
    'schone': ['c1u07_match_modifiers', 'c1u07_l02_mc', 'c1u07_l02_tr'],
    'spreekt': ['c1u07_l02_mc'],
    'stelt': ['c1u07_stelt_single', 'c1u07_l02_mc'],
    'tegenstrijdig': ['c1u07_match_modifiers', 'c1u07_l02_mc', 'c1u07_l02_tr'],
    'veel': ['c1u07_match_modifiers', 'c1u07_l02_mc', 'c1u07_l02_tr'],
    'verschil': ['c1u07_l02_mc', 'c1u07_l02_tr'],
    'behouden': ['c1u07_match_verbs', 'c1u07_l03_mc'],
    'bepaal': ['c1u07_l03_mc'],
    'gemeentelijk': ['c1u07_match_modifiers', 'c1u07_l03_mc', 'c1u07_l03_tr'],
    'hinder': ['c1u07_l03_mc'],
    'legt': ['c1u07_l03_mc'],
    'moet': ['c1u07_l03_mc', 'c1u07_l03_tr'],
    'onderzoek': ['c1u07_l03_mc'],
    'publiek': ['c1u07_match_nouns', 'c1u07_l03_mc', 'c1u07_l03_tr'],
    'rapport': ['c1u07_match_nouns', 'c1u07_l03_mc'],
    'uitgesloten': ['c1u07_l03_mc', 'c1u07_l03_tr'],
    'uitleggen': ['c1u07_match_verbs', 'c1u07_l03_mc'],
    'vakterm': ['c1u07_match_nouns', 'c1u07_l03_mc', 'c1u07_l03_tr'],
    'weglaten': ['c1u07_match_verbs', 'c1u07_l03_mc', 'c1u07_l03_tr'],
    'begrijpt': ['c1u07_match_verbs', 'c1u07_l04_mc'],
    'eens': ['c1u07_l04_mc'],
    'geluid': ['c1u07_l04_mc'],
    'gewone': ['c1u07_match_modifiers', 'c1u07_l04_mc'],
    'kiest': ['c1u07_match_verbs', 'c1u07_l04_mc', 'c1u07_l04_tr'],
    'kortom': ['c1u07_match_modifiers', 'c1u07_l04_mc', 'c1u07_l04_tr'],
    'leek': ['c1u07_match_nouns', 'c1u07_l04_mc', 'c1u07_l04_tr'],
    'leken': ['c1u07_l04_mc', 'c1u07_l04_tr'],
    'luistert': ['c1u07_match_verbs', 'c1u07_l04_mc', 'c1u07_l04_tr'],
    'maat': ['c1u07_match_nouns', 'c1u07_l04_mc'],
    'taal': ['c1u07_match_nouns', 'c1u07_l04_mc', 'c1u07_l04_tr'],
    'vaktermen': ['c1u07_l04_mc', 'c1u07_l04_tr'],
    'zeggen': ['c1u07_match_verbs', 'c1u07_l04_mc', 'c1u07_l04_tr'],
    'zet': ['c1u07_l04_mc'],
    'bevestigd': ['c1u07_l05_mc', 'c1u07_l05_tr'],
    'beweert': ['c1u07_match_verbs', 'c1u07_l05_mc', 'c1u07_l05_tr'],
    'gebeuren': ['c1u07_match_verbs', 'c1u07_l05_mc', 'c1u07_l05_tr'],
    'gemeten': ['c1u07_l05_mc', 'c1u07_l05_tr'],
    'noemt': ['c1u07_l05_mc', 'c1u07_l05_tr'],
    'punt': ['c1u07_l05_mc', 'c1u07_l05_tr'],
    'tegenspraak': ['c1u07_match_nouns', 'c1u07_l05_mc'],
    'uitzondering': ['c1u07_match_nouns', 'c1u07_l05_mc', 'c1u07_l05_tr'],
    'verluidt': ['c1u07_verluidt_single', 'c1u07_l05_mc'],
    'vermeld': ['c1u07_l05_mc'],
    'wijst': ['c1u07_match_verbs', 'c1u07_l05_mc', 'c1u07_l05_tr'],
    'Beste': ['c1u07_l06_mc'],
    'buren': ['c1u07_l06_mc', 'c1u07_l06_tr'],
    'situatie': ['c1u07_match_nouns', 'c1u07_l06_mc', 'c1u07_l06_tr'],
    'allemaal': ['c1u08_allemaal_single', 'c1u08_mc_l05'],
    'beroep': ['c1u08_beroep_single'],
    'degelijk': ['c1u08_degelijk_single', 'c1u08_mc_l04'],
    'handelen': ['c1u08_handelen_single', 'c1u08_match_verbs', 'c1u08_mc_l05', 'c1u08_tr_l05'],
    'behoud': ['c1u08_match_nouns', 'c1u08_mc_l03', 'c1u08_tr_l03'],
    'boodschap': ['c1u08_match_nouns', 'c1u08_mc_l04'],
    'buurtbijeenkomst': ['c1u08_match_nouns', 'c1u08_mc_l03'],
    'kinderen': ['c1u08_match_nouns', 'c1u08_mc_l03', 'c1u08_tr_l03'],
    'luisteraar': ['c1u08_match_nouns', 'c1u08_mc_l02', 'c1u08_tr_l02'],
    'middelen': ['c1u08_match_nouns', 'c1u08_mc_l01', 'c1u08_tr_l01'],
    'parallellisme': ['c1u08_mc_l01', 'c1u08_tr_l01'],
    'parkeerterrein': ['c1u08_parkeerterrein_single', 'c1u08_match_nouns', 'c1u08_mc_l01'],
    'ritme': ['c1u08_match_nouns', 'c1u08_mc_l02', 'c1u08_tr_l02'],
    'rust': ['c1u08_match_nouns', 'c1u08_mc_l01', 'c1u08_tr_l01'],
    'steun': ['c1u08_steun_single', 'c1u08_match_nouns', 'c1u08_mc_l03', 'c1u08_tr_l03'],
    'stukje': ['c1u08_match_nouns', 'c1u08_mc_l03', 'c1u08_tr_l03'],
    'toespraak': ['c1u08_match_nouns', 'c1u08_mc_l02'],
    'vraag': ['c1u08_match_nouns', 'c1u08_mc_l01', 'c1u08_tr_l01'],
    'waarde': ['c1u08_match_nouns', 'c1u08_mc_l04', 'c1u08_tr_l04'],
    'eindigt': ['c1u08_match_verbs', 'c1u08_mc_l03', 'c1u08_tr_l03'],
    'gebruikt': ['c1u08_match_verbs', 'c1u08_mc_l01', 'c1u08_tr_l01'],
    'houden': ['c1u08_match_verbs', 'c1u08_mc_l01'],
    'mogen': ['c1u08_match_verbs', 'c1u08_mc_l02', 'c1u08_tr_l02'],
    'opgeven': ['c1u08_opgeven_single', 'c1u08_match_verbs', 'c1u08_mc_l02', 'c1u08_tr_l02'],
    'overtuigen': ['c1u08_match_verbs', 'c1u08_mc_l01', 'c1u08_tr_l01'],
    'spelen': ['c1u08_match_verbs', 'c1u08_mc_l02', 'c1u08_tr_l02'],
    'verdwijnt': ['c1u08_match_verbs', 'c1u08_mc_l02', 'c1u08_tr_l02'],
    'versterken': ['c1u08_match_verbs', 'c1u08_mc_l04', 'c1u08_tr_l04'],
    'verzachten': ['c1u08_verzachten_single', 'c1u08_match_verbs', 'c1u08_mc_l04', 'c1u08_tr_l04'],
    'vraagt': ['c1u08_match_verbs', 'c1u08_mc_l05', 'c1u08_tr_l05'],
    'zorgt': ['c1u08_match_verbs', 'c1u08_mc_l03'],
    'appèl': ['c1u08_mc_l01'],
    'buurt': ['c1u08_mc_l01'],
    'doen': ['c1u08_mc_l01', 'c1u08_tr_l01'],
    'doet': ['c1u08_mc_l01', 'c1u08_tr_l01'],
    'groen': ['c1u08_mc_l01', 'c1u08_tr_l01'],
    'groenstrook': ['c1u08_mc_l01', 'c1u08_tr_l01'],
    'maken': ['c1u08_mc_l01', 'c1u08_tr_l01'],
    'retorische': ['c1u08_mc_l01', 'c1u08_tr_l01'],
    'vier': ['c1u08_mc_l01', 'c1u08_tr_l01'],
    'doe': ['c1u08_mc_l02', 'c1u08_tr_l02'],
    'krachtiger': ['c1u08_mc_l02', 'c1u08_tr_l02'],
    'laten': ['c1u08_mc_l02', 'c1u08_tr_l02'],
    'oproep': ['c1u08_mc_l02'],
    'plek': ['c1u08_mc_l02'],
    'roept': ['c1u08_mc_l02'],
    'terrein': ['c1u08_mc_l02'],
    'alle': ['c1u08_mc_l03', 'c1u08_tr_l03'],
    'betogende': ['c1u08_mc_l03'],
    'dezelfde': ['c1u08_mc_l03', 'c1u08_tr_l03'],
    'einde': ['c1u08_mc_l03'],
    'frisse': ['c1u08_mc_l03', 'c1u08_tr_l03'],
    'herken': ['c1u08_mc_l03', 'c1u08_tr_l03'],
    'kom': ['c1u08_mc_l03', 'c1u08_tr_l03'],
    'mooi': ['c1u08_mc_l03'],
    'steeds': ['c1u08_mc_l03'],
    'stem': ['c1u08_stem_single', 'c1u08_mc_l03', 'c1u08_tr_l03'],
    'beste': ['c1u08_mc_l04', 'c1u08_tr_l04'],
    'betoog': ['c1u08_mc_l04'],
    'ongezonder': ['c1u08_mc_l04', 'c1u08_tr_l04'],
    'sterker': ['c1u08_mc_l04', 'c1u08_tr_l04'],
    'bouw': ['c1u08_mc_l05', 'c1u08_tr_l05'],
    'slot': ['c1u08_mc_l05'],
    'beginnen': ['c1u01_koers_vertaal'],
    'bespreek': ['c1u01_koers_vertaal'],
    'eerst': ['c1u01_koers_vertaal'],
    'lijnen': ['c1u01_koers_vertaal'],
    'probleem': ['c1u01_koers_vertaal'],
    'voordelen': ['c1u01_koers_vertaal'],
    'voordeel': ['c1u01_punten_vertaal'],
    'schonere': ['c1u01_punten_vertaal'],
    'lucht': ['c1u01_punten_vertaal'],
    'meer': ['c1u01_punten_vertaal'],
    'voetgangers': ['c1u01_punten_vertaal'],
    'terug': ['c1u01_terugkeren_vertaal'],
    'komen': ['c1u01_terugkeren_vertaal'],
    'aantrekkelijker': ['c1u01_terugkeren_vertaal'],
    'wordt': ['c1u01_terugkeren_vertaal'],
    'aantrekkelijke': ['c1u01_terugkeren_vertaal'],
    'bezoekers': ['c1u01_terugkeren_vertaal'],
}

# C1 tokens absent from NL_GLOSSES (362 after capital folding). Each gloss is the
# atomic English meaning of the sense the C1 unit actually teaches (from the
# card text and the en-nl c1 overlay), with a form cue where the unit pools
# several forms of one lemma. DRAFT pending native-Dutch review, like the units.
NL_GLOSSES.update({
    'aangeboden': 'offered (past participle)',
    'aangenomen': 'accepted; took (a job) (past participle)',
    'aantoonbaar': 'demonstrably',
    'aantrekkelijke': 'attractive (inflected)',
    'aantrekkelijker': 'more attractive',
    'achteraf': 'in retrospect; after the fact',
    'afgewezen': 'rejected; turned down (an offer) (past participle)',
    'afgewogen': 'weighed (up) (past participle)',
    'afstand': 'the distance (also social distance)',
    'afweging': 'the weighing-up; the trade-off',
    'alweer': 'yet again; once again',
    'ambtenaar': 'the civil servant; the official',
    'ander': "other (as in 'the other person')",
    'antwoord': 'the answer; the reply',
    'antwoordde': 'answered; replied (with hij/zij)',
    'antwoorden': 'to answer; to reply',
    'appèl': 'the appeal (rhetorical device)',
    "auto's": 'cars',
    'autoluwe': 'low-traffic (inflected)',
    'baat': "benefit (in 'to benefit from it')",
    'bal': 'the ball',
    'beantwoordt': 'answers; responds to (with hij/zij/het)',
    'bedoeling': 'the intention',
    'beeldspraak': 'figurative language; imagery',
    'begon': 'began (with hij/zij)',
    'begrenzing': 'the delimitation; the limiting',
    'begrijp': 'understand (with ik; with je when inverted)',
    'begrijpelijke': 'understandable (inflected)',
    'begrijpt': 'understands (with hij/zij)',
    'behoorlijk': 'quite; considerably',
    'behoud': 'the preservation; the conservation',
    'behouden': 'to retain; to keep',
    'behoudens': 'except for; barring (formal)',
    'bekijken': 'to look at; to examine',
    'belangrijkste': 'most important (inflected)',
    'beleefdheid': 'the politeness',
    'bemiddelen': 'to mediate',
    'bemiddelt': 'mediates (with hij/zij)',
    'benadrukken': 'to emphasize; to stress',
    'benoemt': 'identifies; pins down (with hij/zij/het)',
    'bepaal': 'determine; decide (with ik, or inverted with je)',
    'bepaald': "exactly (in the negated 'not exactly')",
    'bepalen': 'to determine',
    'beperkt': 'limits; restricts (with hij/zij/het)',
    'beperkte': 'limited (inflected)',
    'bereik': 'the reach (how far something extends)',
    'beschermt': 'protects (with hij/zij/het)',
    'beslissen': 'to decide',
    'beslissing': 'the decision',
    'besprak': 'discussed (with hij/zij)',
    'bespreek': 'discuss (with ik)',
    'bestuur': 'the board; the executive committee',
    'betekenis': 'the meaning',
    'betogende': 'argumentative; persuasive (inflected)',
    'betoog': 'the argument (persuasive text or speech)',
    'beweegt': 'moves (with hij/zij/het)',
    'bewezen': 'proven',
    'bewoners': 'residents',
    'bezoekers': 'visitors',
    'bezorgdheid': 'concern; worry',
    'bezwaar': 'the objection',
    'binnenstad': 'city centre; town centre',
    'blokkeert': 'blocks (with hij/zij/het)',
    'bouw': 'build (with ik; inverted with je)',
    'bouwen': 'to build',
    'bracht': 'brought (with hij/zij)',
    'buren': 'neighbours',
    'bus': "the tin (in an idiom for 'it adds up perfectly')",
    'buurtbijeenkomst': 'the neighbourhood meeting',
    'buurthuis': 'the community centre',
    'buurtonderzoek': 'neighbourhood study',
    'calque': 'the calque; the loan translation',
    'centrale': 'central (inflected)',
    'chaotisch': 'chaotic; chaotically',
    'chef': 'the boss',
    'combineren': 'to combine',
    'concessie': 'the concession',
    'conclusie': 'the conclusion',
    'context': 'the context',
    'controle': 'checks; supervision',
    'daarbij': 'in addition (to that); with that',
    'daarom': "that's why",
    'daarvoor': 'for that; for this purpose',
    'decibel': 'the decibel',
    'desalniettemin': 'nonetheless (formal)',
    'deur': 'the door (in an idiom for coming straight to the point)',
    'dia': 'the slide (in a presentation)',
    'diplomatie': 'diplomacy',
    'diplomatieke': 'diplomatic (inflected)',
    'direct': 'directly; straightforwardly',
    'directeur': 'director (of an organisation)',
    'directheid': 'directness',
    'doel': 'the goal; the aim',
    'doeltreffend': 'effective (achieving its aim)',
    'doorslaggevend': 'decisive',
    'draagt': 'carries (with hij/zij/het)',
    'duidelijk': 'clear; evident (plain to see)',
    'echte': 'real; genuine (inflected)',
    'eindelijk': 'at last (after a long wait)',
    'eindigt': 'ends (with hij/zij/het)',
    'eindoordeel': 'final judgement',
    'energie': 'energy',
    'Engelse': 'English (inflected)',
    'enthousiast': 'enthusiastic',
    'falen': "to fail; failing (as in 'upon repeated failure')",
    'feit': 'the fact',
    'figuurlijk': 'figurative',
    'filiaal': 'the branch (of a chain)',
    'financiële': 'financial (inflected)',
    'focuszin': 'the focus sentence (a cleft sentence)',
    'formulering': 'the phrasing; the formulation',
    'fouten': 'mistakes; errors',
    'frisse': 'fresh (inflected; as in fresh air)',
    'gaten': 'holes (in an idiom for keeping an eye on something)',
    'gegrepen': 'seized (a chance) (past participle)',
    'gehad': 'had (past participle of hebben)',
    'geldt': 'applies; holds (with hij/zij/het)',
    'geleidelijke': 'gradual (inflected)',
    'geluid': 'the sound; noise',
    'geluidsoverlast': 'noise nuisance',
    'gemeentelijk': 'municipal',
    'gemengde': 'mixed (inflected)',
    'gemeten': 'measured (past participle)',
    'gemotiveerd': 'reasoned; well-argued',
    'gevoel': 'the feeling',
    'gevolg': 'the consequence; the result',
    'gewenste': 'desired (inflected)',
    'gewicht': 'the weight',
    'gezien': 'seen (past participle)',
    'gooide': 'threw (with hij/zij)',
    'gooien': 'to throw',
    'gooit': 'throws (with hij/zij)',
    'groeit': 'grows (with hij/zij/het)',
    'groenstrook': 'the green strip (strip of green space)',
    'hand': "the hand (in idioms for 'to be going on' and 'to encourage')",
    'handdoek': 'the towel',
    'handelen': 'to act; to take action',
    'hart': 'the heart',
    'heden': 'the present (time)',
    'helder': 'clear; lucid',
    'herhaald': 'repeated',
    'hinder': 'the hindrance; the bother',
    'hoofdgedachte': 'the main idea; the central point',
    'hoort': 'belongs (with bij) (with hij/zij)',
    'impliceren': 'to imply',
    'ingehouden': 'restrained; suppressed',
    'inhoud': 'content (of a message); substance',
    'intensiteit': 'the intensity',
    'ironie': 'irony',
    'ironisch': 'ironic; ironically',
    'kans': 'chance',
    'keert': 'turns (with hij/zij; with om = reverses)',
    'kernpunt': 'the key point; the crux',
    'keten': 'the chain (of events or reasoning)',
    'klonken': 'sounded (with plural subject)',
    'klopten': 'were correct; added up (plural, past)',
    'knie': 'the knee (in an idiom for having mastered something)',
    'koffiedik': 'coffee grounds (in an idiom for pure guesswork)',
    'kop': "the head (of a nail, in 'to hit the nail on the head')",
    'koude': 'cold (inflected)',
    'kracht': 'force (of an argument)',
    'krachtiger': 'more powerful; more forceful',
    'kreeg': 'got, was given (past, with ik/hij/zij)',
    'kritiek': 'criticism',
    'kritische': 'critical (inflected)',
    'kwalificatie': 'the qualification (limiting statement)',
    'kwam': 'came (with hij/zij)',
    'kwamen': 'came (with we/zij plural)',
    'laatste': 'last; final (inflected)',
    'leek': 'the layperson',
    'leg': "lay; put (imperative; also the first part of the separable verb for 'explain')",
    'legt': "lays; puts (with hij/zij; also the first part of the separable verb for 'explains')",
    'leken': 'laypeople',
    'letterlijk': 'literally',
    'letterlijke': 'literal (inflected)',
    'leven': 'the life',
    'levendig': 'lively; vivid',
    'leveren': 'yield; produce (with zij, plural; separable, with op)',
    'levering': 'the delivery',
    'levert': 'yields; produces (with hij/zij; separable, with op)',
    'lezing': 'the reading (one way of reading a remark)',
    'lid': 'the member',
    'ligt': 'lies (is located; with hij/zij/het)',
    'lijnen': "lines (in 'in broad terms')",
    'lof': 'praise',
    'lucht': 'the air',
    'luisteraar': 'the listener',
    'luistert': 'listens (with hij/zij)',
    'maatschappelijk': 'societal (uninflected)',
    'maatschappelijke': 'societal (inflected)',
    'meebrengen': 'to entail; to bring with it',
    'meen': "mean (with ik; as in 'I mean it')",
    'microfoon': 'the microphone',
    'middelen': 'means (as in rhetorical devices)',
    'mild': 'mild',
    'milde': 'mild (inflected)',
    'minimaal': 'minimal',
    'misging': 'went wrong (past, in a subordinate clause)',
    'mislukt': 'failed; gone wrong (past participle)',
    'mogen': 'to be allowed to; may',
    'molens': 'mills; windmills',
    'mouw': "the sleeve (in 'the monkey comes out of the sleeve')",
    'mug': 'the mosquito; the gnat',
    'nadenken': 'to think (about); to reflect',
    'nadruk': 'the emphasis',
    'namelijk': 'namely; that is',
    'negatieve': 'negative (inflected)',
    'niemand': 'nobody; no one',
    'noemen': 'to mention; to name',
    'noodzakelijk': 'necessary; essential',
    'nut': 'the usefulness',
    'omkeren': 'to reverse; to turn around',
    'omstandigheden': 'circumstances',
    'omzetverlies': 'the loss of revenue; lost sales',
    'onbetaalbaar': 'unaffordable',
    'onderwerp': 'the subject; the topic',
    'ongepast': 'inappropriate; unsuitable',
    'ongezond': 'unhealthy',
    'ongezonder': 'unhealthier',
    'ontevreden': 'dissatisfied',
    'ontevredenheid': 'the dissatisfaction',
    'ontmoet': 'met (past participle)',
    'ontstaat': 'arises; comes into being (with hij/zij/het)',
    'onwerkelijke': 'unreal; not real (inflected)',
    'openblijft': 'stays open (with hij/zij/het)',
    'opgelost': 'solved; resolved (past participle)',
    'opgeven': 'to give up',
    'oprecht': 'sincerely; in earnest',
    'oproep': 'the call (to action)',
    'overlast': 'the nuisance; the disturbance',
    'overtuigen': 'to persuade; to convince',
    'parallellisme': 'the parallelism (repeated structure)',
    'parkeerterrein': 'the car park; the parking lot',
    'passende': 'fitting; appropriate (inflected)',
    'personeel': 'the staff; personnel',
    'personeelskosten': 'staff costs; personnel costs',
    'pet': 'the cap (in an idiom for doing something half-heartedly)',
    'pleit': 'makes the case (for) (with hij/zij)',
    'plek': 'the place; the spot',
    'positieve': 'positive (inflected)',
    'presentatie': 'the presentation',
    'problemen': 'problems',
    'raad': "the council; advice (in an idiom for 'to be at a loss')",
    'ramp': 'the disaster',
    'rampzalig': 'disastrous',
    'reageert': 'responds; reacts (with u or hij/zij)',
    'rechtstreeks': 'straight out; directly (explicitly)',
    'rechtvaardigt': 'justifies (with hij/zij/het)',
    'relatie': 'the relationship',
    'retorische': 'rhetorical (inflected)',
    'ring': 'the ring',
    'roept': 'calls (with hij/zij/het; with op: calls on)',
    'ruimere': 'more extensive; wider (inflected)',
    'samenvatten': 'to summarize; to sum up',
    'schets': 'sketch; outline (with ik)',
    'schone': 'clean (inflected)',
    'schonere': 'cleaner (inflected)',
    'serieus': 'serious',
    'situatie': 'the situation',
    'slaat': 'hit; strike (present, with je)',
    'sloeg': 'struck; hit (past, with ik/hij)',
    'slot': "close; conclusion (in the phrase meaning 'finally')",
    'soepel': 'smooth; smoothly',
    'spijker': "the nail (in 'to hit the nail on the head')",
    'spijt': 'regret',
    'sprake': "mention (in 'to bring up a topic')",
    'stem': "vote (imperative, as in 'vote for ...')",
    'steun': 'the support; the backing',
    'stijgen': 'rise (with plural subject)',
    'stilte': 'the silence',
    'streng': 'strict; stern',
    'studenten': 'students',
    'stukje': 'the little piece; the bit',
    'suggereert': 'suggests; hints at (with hij/zij)',
    'taal': 'the language',
    'tegenargument': 'the counterargument',
    'tegenbewijs': 'the counterevidence',
    'tegenfeitelijke': 'counterfactual; against the facts (inflected)',
    'tegenspraak': 'the contradiction',
    'tegenstrijdig': 'contradictory; conflicting',
    'tekst': 'the text',
    'teleurgesteld': 'disappointed',
    'ter': "to; at (fixed old form, in 'to bring up a topic')",
    'term': 'the term',
    'termijn': 'the time frame; the term',
    'terrein': 'the site; the plot of land',
    'terzijde': 'as an aside',
    'tijdlijn': 'the timeline',
    'toegankelijkheid': 'the accessibility',
    'toespraak': 'the speech',
    'toon': 'the tone',
    'trekt': 'draws (with hij/zij)',
    'uitdrukken': 'to express (put into words)',
    'uitdrukking': 'the expression; the idiom',
    'uitgedrukt': 'expressed; put (past participle)',
    'uitgesloten': 'ruled out; excluded',
    'uitleggen': 'to explain',
    'uitstapje': 'the digression (lit. the little outing)',
    'uitstekend': 'excellent; excellently',
    'uitstel': 'the postponement (putting something off)',
    'uitzondering': 'the exception',
    'vakterm': 'the technical term',
    'vaktermen': 'technical terms',
    'vaste': 'fixed; set (inflected)',
    'vat': 'grasps; sums up (with hij/zij; separable, the particle goes to the end)',
    'verbergen': 'to conceal',
    'verbetering': 'the improvement',
    'verbindt': 'connects; links (with hij/zij/het)',
    'verdedigt': 'defends (with hij/zij)',
    'verdient': 'deserves (with hij/zij/het)',
    'verdwijnt': 'disappears (with hij/zij/het)',
    'vergelijk': "the settlement; the compromise (in 'to reach a compromise')",
    'verhogen': 'to raise; to increase',
    'verhoogt': 'raises; increases (with hij/zij/het)',
    'verhuisd': 'moved house (past participle)',
    'verkleint': 'reduces; makes smaller (with hij/zij/het)',
    'verleden': 'past (noun: time gone by)',
    'verliep': 'proceeded; unfolded (past, with het)',
    'verluidt': "is reported (in the fixed phrase for 'reportedly')",
    'vermeld': 'mention; state (with ik, or inverted with je)',
    'vermijd': 'avoid (imperative; with ik)',
    'versie': 'the version',
    'versterken': 'to strengthen; to reinforce',
    'versterkt': 'strengthens; reinforces (with hij/zij/het)',
    'vertaald': 'translated',
    'vertalen': 'to translate',
    'vertaling': 'the translation',
    'vertalingen': 'translations',
    'verzachten': 'to soften',
    'verzwijgen': 'to keep quiet about',
    'viel': 'fell (with hij/zij; with uit: cut out)',
    'vlakke': 'flat (inflected; of a tone)',
    'vlekkeloos': 'flawless',
    'voorbehoud': 'the reservation; qualification',
    'voorrang': "priority; precedence (as in 'as a priority')",
    'voortreffelijk': "superb; first-rate (more elevated than 'excellent')",
    'vraag': 'the question',
    'vreest': 'fears (with hij/zij)',
    'vrezen': 'to fear',
    'waarde': 'the value; the worth',
    'waardering': 'the appreciation',
    'waarin': 'in which',
    'weglaten': 'to leave out; to omit',
    'werkelijk': 'really; truly',
    'werkelijkheid': 'reality',
    'werkenden': 'working people; people in work',
    'wijst': 'points (with hij/zij)',
    'wijzen': 'to point; to indicate (with op: to point to)',
    'wilde': 'wanted (past, with ik/hij/zij)',
    'windmolenpark': 'the wind farm',
    'winkeliers': 'shopkeepers',
    'woonde': 'lived, resided (past, with ik/hij/zij)',
    'woordkeus': 'the choice of words; wording',
    'zacht': "soft (in the idiom 'to put it mildly')",
    'zat': 'sat; was (past of zitten, with ik/hij/zij)',
    'zet': "put; set (with ik; also the first part of the separable verb for 'convert')",
    'zichtbaar': 'visible',
    'zinnen': 'sentences; clauses',
    "zo'n": 'such a',
    'zorg': 'concern; worry (noun)',
    'zorgt': "takes care of; provides (with hij/zij, followed by 'voor')",
})
ADJECTIVES.update({'aantrekkelijke', 'aantrekkelijker', 'autoluwe', 'begrijpelijke', 'belangrijkste', 'beperkte', 'betogende', 'centrale', 'chaotisch', 'diplomatieke', 'doeltreffend', 'doorslaggevend', 'duidelijk', 'echte', 'Engelse', 'enthousiast', 'figuurlijk', 'financiële', 'frisse', 'geleidelijke', 'gemeentelijk', 'gemengde', 'gemotiveerd', 'gewenste', 'helder', 'herhaald', 'ingehouden', 'ironisch', 'koude', 'krachtiger', 'kritische', 'laatste', 'letterlijke', 'levendig', 'maatschappelijk', 'maatschappelijke', 'mild', 'milde', 'minimaal', 'negatieve', 'noodzakelijk', 'onbetaalbaar', 'ongepast', 'ongezond', 'ongezonder', 'ontevreden', 'onwerkelijke', 'passende', 'positieve', 'rampzalig', 'retorische', 'ruimere', 'schone', 'schonere', 'serieus', 'soepel', 'streng', 'tegenfeitelijke', 'tegenstrijdig', 'teleurgesteld', 'uitstekend', 'vaste', 'vertaald', 'vlakke', 'vlekkeloos', 'voortreffelijk', 'zacht', 'zichtbaar'})
ADVERBS.update({'aantoonbaar', 'achteraf', 'alweer', 'behoorlijk', 'bepaald', 'daarbij', 'daarom', 'daarvoor', 'desalniettemin', 'direct', 'eindelijk', 'letterlijk', 'namelijk', 'oprecht', 'rechtstreeks', 'terzijde', 'waarin', 'werkelijk'})
NOUNS.update({'afstand', 'afweging', 'ambtenaar', 'antwoord', 'appèl', "auto's", 'baat', 'bal', 'bedoeling', 'beeldspraak', 'begrenzing', 'behoud', 'beleefdheid', 'bereik', 'beslissing', 'bestuur', 'betekenis', 'betoog', 'bewoners', 'bezoekers', 'bezorgdheid', 'bezwaar', 'binnenstad', 'buren', 'bus', 'buurtbijeenkomst', 'buurthuis', 'buurtonderzoek', 'calque', 'chef', 'concessie', 'conclusie', 'context', 'controle', 'decibel', 'deur', 'dia', 'diplomatie', 'directeur', 'directheid', 'doel', 'eindoordeel', 'energie', 'feit', 'filiaal', 'focuszin', 'formulering', 'fouten', 'gaten', 'geluid', 'geluidsoverlast', 'gevoel', 'gevolg', 'gewicht', 'groenstrook', 'hand', 'handdoek', 'hart', 'heden', 'hinder', 'hoofdgedachte', 'inhoud', 'intensiteit', 'ironie', 'kans', 'kernpunt', 'keten', 'knie', 'koffiedik', 'kop', 'kracht', 'kritiek', 'kwalificatie', 'leek', 'leken', 'leven', 'levering', 'lezing', 'lid', 'lijnen', 'lof', 'lucht', 'luisteraar', 'microfoon', 'middelen', 'molens', 'mouw', 'mug', 'nadruk', 'nut', 'omstandigheden', 'omzetverlies', 'onderwerp', 'ontevredenheid', 'oproep', 'overlast', 'parallellisme', 'parkeerterrein', 'personeel', 'personeelskosten', 'pet', 'plek', 'presentatie', 'problemen', 'raad', 'ramp', 'relatie', 'ring', 'situatie', 'slot', 'spijker', 'spijt', 'sprake', 'steun', 'stilte', 'studenten', 'stukje', 'taal', 'tegenargument', 'tegenbewijs', 'tegenspraak', 'tekst', 'term', 'termijn', 'terrein', 'tijdlijn', 'toegankelijkheid', 'toespraak', 'toon', 'uitdrukking', 'uitstapje', 'uitstel', 'uitzondering', 'vakterm', 'vaktermen', 'verbetering', 'vergelijk', 'verleden', 'versie', 'vertaling', 'vertalingen', 'voorbehoud', 'voorrang', 'vraag', 'waarde', 'waardering', 'werkelijkheid', 'werkenden', 'windmolenpark', 'winkeliers', 'woordkeus', 'zinnen', 'zorg'})
PREPOSITIONS.update({'behoudens', 'ter'})
PRONOUNS.update({'ander', 'niemand', "zo'n"})
VERBS.update({'aangeboden', 'aangenomen', 'afgewezen', 'afgewogen', 'antwoordde', 'antwoorden', 'beantwoordt', 'begon', 'begrijp', 'begrijpt', 'behouden', 'bekijken', 'bemiddelen', 'bemiddelt', 'benadrukken', 'benoemt', 'bepaal', 'bepalen', 'beperkt', 'beschermt', 'beslissen', 'besprak', 'bespreek', 'beweegt', 'bewezen', 'blokkeert', 'bouw', 'bouwen', 'bracht', 'combineren', 'draagt', 'eindigt', 'falen', 'gegrepen', 'gehad', 'geldt', 'gemeten', 'gezien', 'gooide', 'gooien', 'gooit', 'groeit', 'handelen', 'hoort', 'impliceren', 'keert', 'klonken', 'klopten', 'kreeg', 'kwam', 'kwamen', 'leg', 'legt', 'leveren', 'levert', 'ligt', 'luistert', 'meebrengen', 'meen', 'misging', 'mislukt', 'mogen', 'nadenken', 'noemen', 'omkeren', 'ontmoet', 'ontstaat', 'openblijft', 'opgelost', 'opgeven', 'overtuigen', 'pleit', 'reageert', 'rechtvaardigt', 'roept', 'samenvatten', 'schets', 'slaat', 'sloeg', 'stem', 'stijgen', 'suggereert', 'trekt', 'uitdrukken', 'uitgedrukt', 'uitgesloten', 'uitleggen', 'vat', 'verbergen', 'verbindt', 'verdedigt', 'verdient', 'verdwijnt', 'verhogen', 'verhoogt', 'verhuisd', 'verkleint', 'verliep', 'verluidt', 'vermeld', 'vermijd', 'versterken', 'versterkt', 'vertalen', 'verzachten', 'verzwijgen', 'viel', 'vreest', 'vrezen', 'weglaten', 'wijst', 'wijzen', 'wilde', 'woonde', 'zat', 'zet', 'zorgt'})


# Sentence-initial / sign-line capitals folded onto their lowercase citation
# form -- see departure (1) in the block comment above. Applied in
# `_classify_nl()` BEFORE the gloss lookup, so the capitalized spelling never
# becomes a Lexeme.token and can never be handed to a learner as a typed
# answer. Keys are tokens introduced ONLY by units 34-42/49-72 (verified: all
# 116 were absent from NL_GLOSSES before this round), so this cannot alter any
# lexeme that already shipped.
NL_CITATION_FORMS = {
    # Sentence-initial in dialogue or a grammar note.
    "Aankomen": "aankomen", "Beiden": "beiden", "Begin": "begin",
    "Begint": "begint", "Breng": "breng", "Eet": "eet", "Eén": "één",
    "Gefeliciteerd": "gefeliciteerd", "Hebben": "hebben", "Hebt": "hebt",
    "Heel": "heel", "Hé": "hé", "Interessant": "interessant",
    "Jullie": "jullie", "Klaarmaken": "klaarmaken", "Lees": "lees",
    "Lekker": "lekker", "Leren": "leren", "Neemt": "neemt", "Nodig": "nodig",
    "Nieuwe": "nieuwe", "Open": "open", "Opruimen": "opruimen",
    "Opzoeken": "opzoeken", "Proef": "proef", "Uitchecken": "uitchecken",
    "Uitnodigen": "uitnodigen", "Vieren": "vieren", "Voederen": "voederen",
    "Was": "was", "Wassen": "wassen", "Wie": "wie", "Zestig": "zestig",
    # Speaker labels in a dialogue transcript ("Apotheker: ...").
    "Apotheker": "apotheker", "Kapper": "kapper", "Receptionist": "receptionist",
    # First word of a sign, price list, menu or notice.
    "Bakkerij": "bakkerij", "Band": "band", "Bloemist": "bloemist",
    "Boekwinkel": "boekwinkel", "Bolletje": "bolletje", "Brood": "brood",
    "Concert": "concert", "Croissants": "croissants", "Dagmenu": "dagmenu",
    "Dagpas": "dagpas", "Dierentuin": "dierentuin", "Dierenwinkel": "dierenwinkel",
    "Droger": "droger", "Duur": "duur", "Elektrische": "elektrische",
    "Etiket": "etiket", "Fiets": "fiets", "Film": "film", "Honden": "honden",
    "Hoorntje": "hoorntje", "Huurprijzen": "huurprijzen", "IJssalon": "ijssalon",
    "Kamer": "kamer", "Kinderboek": "kinderboek",
    "Kindervoorstelling": "kindervoorstelling", "Knipbeurt": "knipbeurt",
    "Kraam": "kraam", "Minimale": "minimale", "Museum": "museum",
    "Openingstijden": "openingstijden", "Paracetamol": "paracetamol",
    "Parasols": "parasols", "Park": "park", "Popcorn": "popcorn",
    "Pretpark": "pretpark", "Prijslijst": "prijslijst", "Programma": "programma",
    "Regel": "regel", "Reis": "reis", "Roman": "roman", "Rondvaart": "rondvaart",
    "Roos": "roos", "Soep": "soep", "Sportschool": "sportschool",
    "Strand": "strand", "Tentoonstelling": "tentoonstelling", "Theater": "theater",
    "Thuisteam": "thuisteam", "Toneelstuk": "toneelstuk", "Tulp": "tulp",
    "Uitteam": "uitteam", "Voer": "voer", "Vogelvoer": "vogelvoer",
    "Voorstelling": "voorstelling", "Wasbeurt": "wasbeurt", "Wedstrijd": "wedstrijd",
    "Yogales": "yogales",
    # Already glossed by an earlier round (as A2/B1 case variants) but never
    # yet an A1 lexeme, because the only A1 units introducing them are in
    # this batch: unit51 "Kunt", unit49 "Volgende", unit50 "Moet". Folding
    # them here is therefore still a no-op for shipped data and keeps the
    # batch free of capitalized-by-position typed answers.
    "Kunt": "kunt", "Volgende": "volgende", "Moet": "moet",
    # DELIBERATELY NOT FOLDED, even though they are the same defect class:
    # "Nu" (a1_unit44/48) and "Iedereen" (a1_unit44) are ALSO introduced by
    # already-backfilled units, so folding them would silently rewrite
    # lexemes that have already shipped. Left for a separate, deliberate
    # data-migration decision rather than smuggled into this batch.
    # Not a capitalization fix: nl.a1.unit35.lesson06's introduced_tokens
    # spells the word without its accent while its own Dutch text writes
    # "taalcafé". Folded onto the real word rather than shipping a lexeme
    # whose token is a misspelling. Content-lane fix pending.
    "taalcafe": "taalcafé",
}

# de/het gender for every noun these 33 units introduce -- see departure (2).
# Cross-checked against the article each unit's own Dutch text uses; the
# entries the corpus never shows with an article are marked from standard
# Dutch (diminutives in -je/-tje are always het).
NL_A1_VOLUME_ARTICLES = {
    "boodschap": "de", "computer": "de", "internet": "het",
    "gezondheidszorg": "de", "hogeschool": "de", "opleiding": "de",
    "school": "de", "volksuniversiteit": "de", "verjaardag": "de",
    "huishouden": "het", "rommel": "de", "buur": "de", "buurman": "de",
    "buurvrouw": "de", "brief": "de", "pakket": "het", "postzegel": "de",
    "pan": "de", "tomaat": "de", "ui": "de", "persoon": "de",
    "bloemenmarkt": "de", "bevestiging": "de", "receptionist": "de",
    "reservering": "de", "sleutel": "de", "wifiwachtwoord": "het",
    "apotheker": "de", "doos": "de", "dosering": "de", "etiket": "het",
    "medicijn": "het", "paracetamol": "de", "pijnstiller": "de",
    "kapper": "de", "kapsel": "het", "knipbeurt": "de", "prijslijst": "de",
    "borg": "de", "fietsenwinkel": "de", "huurprijs": "de", "droger": "de",
    "wasbeurt": "de", "wasmand": "de", "wasprogramma": "het",
    "wasserette": "de", "kluisje": "het", "zwembad": "het", "zwemtas": "de",
    "bioscoop": "de", "dagmenu": "het", "menukaart": "de", "soep": "de",
    "kindervoorstelling": "de", "museum": "het", "popcorn": "de",
    "programma": "het", "voorstelling": "de", "concert": "het", "gids": "de",
    "schilderij": "het", "tentoonstelling": "de", "band": "de",
    "podium": "het", "publiek": "het", "bankje": "het", "boom": "de",
    "eend": "de", "fruit": "het", "gras": "het", "lijn": "de",
    "picknick": "de", "abonnement": "het", "dagpas": "de",
    "instructeur": "de", "loopband": "de", "sportschool": "de",
    "strand": "het", "yogales": "de", "dierentuin": "de", "golf": "de",
    "parasol": "de", "zand": "het", "zee": "de", "aap": "de",
    "giraffe": "de", "leeuw": "de", "leeuwenverblijf": "het",
    "olifant": "de", "rondvaart": "de", "voederen": "het", "boot": "de",
    "brug": "de", "gracht": "de", "steiger": "de", "wedstrijd": "de",
    "doelpunt": "het", "pretpark": "het", "scorebord": "het", "speler": "de",
    "stadion": "het", "stand": "de", "supporter": "de", "team": "het",
    "thuisteam": "het", "uitteam": "het", "winnaar": "de", "achtbaan": "de",
    "attractie": "de", "kassa": "de", "lengte": "de", "meter": "de",
    "plattegrond": "de", "reuzenrad": "het", "rij": "de", "theater": "het",
    "gordijn": "het", "stoel": "de", "toneelstuk": "het", "bakker": "de",
    "marktkoopman": "de", "bakkerij": "de", "croissant": "de", "gebak": "het",
    "ijssalon": "het", "toonbank": "de", "zak": "de", "bakje": "het",
    "bloemist": "de", "bolletje": "het", "hoorntje": "het", "ijs": "het",
    "vitrine": "de", "bloem": "de", "boeket": "het", "boekwinkel": "de",
    "lint": "het", "roos": "de", "tulp": "de", "bladwijzer": "de",
    "dierenwinkel": "de", "kinderboek": "het", "roman": "de",
    "schrijver": "de", "titel": "de", "mand": "de", "riem": "de",
    "speeltje": "het", "voer": "het", "vogelvoer": "het",
}

# Plural nouns these units introduce (all Dutch plurals take "de"). Kept
# separate so a practice slot can require a singular -- pairing e.g.
# "de roos"/"de rozen" in one matching_pairs set is a legitimate
# singular/plural discrimination, but a fixed singular frame must not sample
# the plural.
NL_A1_VOLUME_PLURALS = {
    "nachten", "pijnstillers", "tabletten", "huurprijzen", "graden", "kleren",
    "munten", "openingstijden", "dranken", "schilderijen", "parasols",
    "kaartjes", "leeuwen", "eenden", "gewichten", "acteurs", "croissants",
    "bolletjes", "smaken", "bloemen", "rozen", "kinderboeken",
}

# Per-unit slot-preset tag prefixes, keyed by "<level>.<unit>" so an A1 unit
# number can never collide with the B1 course's own unit01-11 -- see
# departure (3). The slug is the realization filename's own topic slug.
NL_A1_VOLUME_UNIT_SLUGS = {
    "a1.unit34": "technologie", "a1.unit35": "opleiding",
    "a1.unit36": "verjaardag", "a1.unit37": "huishouden",
    "a1.unit38": "buurt", "a1.unit39": "post", "a1.unit40": "koken",
    "a1.unit41": "persoonlijkheid", "a1.unit42": "kleuren",
    "a1.unit49": "accommodatie", "a1.unit50": "apotheek",
    "a1.unit51": "kapper", "a1.unit52": "fietshuren",
    "a1.unit53": "wasserette", "a1.unit54": "zwembad",
    "a1.unit55": "restaurant", "a1.unit56": "bioscoop",
    "a1.unit57": "museum", "a1.unit58": "concert", "a1.unit59": "park",
    "a1.unit60": "sportschool", "a1.unit61": "strand",
    "a1.unit62": "dierentuin", "a1.unit63": "rondvaart",
    "a1.unit64": "voetbalwedstrijd", "a1.unit65": "pretpark",
    "a1.unit66": "theater", "a1.unit67": "markt", "a1.unit68": "bakker",
    "a1.unit69": "ijssalon", "a1.unit70": "bloemist",
    "a1.unit71": "boekwinkel", "a1.unit72": "dierenwinkel",
}

# One single-member fill_in_blank / render_frame anchor per unit. Single by
# construction (an exact token test), which is what makes it safe inside a
# fixed multi-word frame without the §17 multi-candidate ambiguity check.
# Each token was checked to have no capitalized sibling that casefolding could
# pull in -- guaranteed here anyway, since NL_CITATION_FORMS folds every
# sentence-initial variant these units contain into the same single lexeme.
NL_A1_VOLUME_SINGLE_ANCHORS = {
    "internet": "technologie", "hogeschool": "opleiding",
    "verjaardag": "verjaardag", "huishouden": "huishouden",
    "buurman": "buurt", "postzegel": "post", "tomaat": "koken",
    "persoon": "persoonlijkheid", "bloemenmarkt": "kleuren",
    "bevestiging": "accommodatie", "dosering": "apotheek",
    "kapsel": "kapper", "borg": "fietshuren", "wasserette": "wasserette",
    "kluisje": "zwembad", "dagmenu": "restaurant", "popcorn": "bioscoop",
    "tentoonstelling": "museum", "podium": "concert", "picknick": "park",
    "loopband": "sportschool", "parasol": "strand",
    "leeuwenverblijf": "dierentuin", "steiger": "rondvaart",
    "scorebord": "voetbalwedstrijd", "reuzenrad": "pretpark",
    "gordijn": "theater", "marktkoopman": "markt", "toonbank": "bakker",
    "vitrine": "ijssalon", "boeket": "bloemist", "bladwijzer": "boekwinkel",
    "speeltje": "dierenwinkel",
}

# Content parts of speech eligible for a `<slug>_vocab` slot. Function words
# (particles/prepositions/pronouns), bare numerals and proper nouns are
# excluded on purpose: proper nouns self-gloss ("Smit" -> "Smit"), which makes
# a nonsense multiple_choice item, and function words are not testable
# vocabulary.
NL_A1_VOLUME_VOCAB_POS = frozenset({"noun", "verb", "adjective", "adverb", "phrase"})

# Capitalized tokens that may still enter a `<slug>_vocab` pool, because the
# capital is the real Dutch citation form rather than a sentence position.
# Everything else starting with a capital is kept OUT of these pools even when
# its part of speech qualifies -- `Nu` (unit35) and `Iedereen` (unit36) are
# sentence-initial variants that could not be folded away (they are ALSO
# introduced by already-backfilled units 44/48, see NL_CITATION_FORMS), and a
# typed answer sampled from them would be graded `incorrect` for a learner who
# correctly types the lowercase form.
NL_A1_VOLUME_ALWAYS_CAPITALIZED = frozenset({"Spaans"})

# Tokens whose ONE course-wide classification carries a different unit's sense
# (this file keys specs by bare token, so a homograph gets a single gloss --
# see the "zijn" note in the module docstring). They are kept out of the
# affected unit's slot pools so no pack can build an item whose answer gloss
# contradicts the unit it is testing. Checked by reading each unit's pool by
# hand, not guessed:
#   koken/bak + bakken   -> classified as the unit48 waste bins ("bin"/"bins"),
#                           not unit40's bakken = "to fry"
#   post/schrijven       -> classified as unit03's "part of inschrijven, to
#                           register", not unit39's schrijven = "to write"
#   zwembad/regel        -> classified as the verb "arrange (part of regelen)",
#                           not unit54's sign heading "Regel:" = "Rule:"
NL_A1_VOLUME_TAG_EXCLUSIONS = {
    ("koken", "bak"), ("koken", "bakken"),
    ("post", "schrijven"),
    ("zwembad", "regel"),
}


def nl_part_of_speech(token: str) -> str:
    for pos, members in (
        ("symbol", SYMBOLS), ("proper_noun", PROPER_NOUNS), ("pronoun", PRONOUNS),
        ("preposition", PREPOSITIONS), ("particle", PARTICLES), ("adjective", ADJECTIVES),
        ("adverb", ADVERBS), ("verb", VERBS), ("phrase", PHRASES), ("noun", NOUNS),
    ):
        if token in members:
            return pos
    raise ValueError(f"missing explicit Dutch part of speech for {token!r}")


# BEGIN volume practice singleton tags (generated 2026-07-13)
VOLUME_PRACTICE_SINGLETON_TAGS = {'België': ['volume_en_nl_a1_unit01_item_10_single'], 'Hoi': ['volume_en_nl_a1_unit01_item_05_single'], 'Jan': ['volume_en_nl_a1_unit01_item_07_single'], 'Je': ['volume_en_nl_a1_unit01_item_02_single', 'volume_en_nl_a1_unit01_item_12_single'], 'Retourbeleid': ['volume_en_nl_a2_unit77_item_03_single'], 'agenda': ['volume_en_nl_a2_unit76_item_11_single'], 'koptelefoon': ['volume_en_nl_a2_unit77_item_06_single', 'volume_en_nl_a2_unit77_item_08_single'], 'ruilen': ['volume_en_nl_a2_unit77_item_04_single'], 'terugkrijgen': ['volume_en_nl_a2_unit77_item_01_single'], 'volgorde': ['volume_en_nl_a2_unit76_item_09_single']}
# END volume practice singleton tags

def nl_agreement_tags(token: str, lesson_key: str) -> dict[str, object]:
    t = token.casefold()
    semantic: list[str] = []
    for tag in VOLUME_PRACTICE_SINGLETON_TAGS.get(token, ()):
        semantic.append(tag)
    unit_lesson = lesson_key.split(".")[-1]
    lesson_categories = {
        "jij_je_en_u": "register_language", "groeten_en_welzijn": "wellbeing",
        "namen": "name_exchange", "herkomst_en_taal": "origin_language",
        "taalcafe": "cafe_small_talk", "eerste_ontmoeting": "first_meeting_dialogue",
        "nul_tot_twaalf": "number", "vanaf_dertien": "number",
        "telefoon_en_huisnummer": "contact_number", "leeftijd_en_aantallen": "age_quantity",
        "prijzen": "price", "inschrijven_bij_de_bibliotheek": "library_registration",
        "weekdagen": "weekday", "maanden": "month", "rangtelwoorden": "ordinal_number",
        "datum_vragen": "date_expression", "bibliotheekdatum": "library_date",
        "taalcafe_afspraak": "cafe_appointment", "hele_en_halve_uren": "clock_time",
        "kwartieren": "quarter_hour", "hoe_laat": "time_question",
        "digitale_tijd_en_dagdelen": "time_of_day", "rooster_lezen": "schedule",
        "afspreken_bij_het_taalcafe": "cafe_meetup_time",
        "direct_family": "family_member", "extended_family": "extended_family_member",
        "mijn_je": "possessive_pronoun", "zijn_haar": "possessive_pronoun",
        "lotte_profiel": "family_profile", "taalcafe_familie_dialoog": "family_dialogue",
        "dranken": "drink", "ik_wil_graag": "food_request",
        "aantallen_bestellen": "polite_request", "wat_wilt_u": "food_request",
        "menukaart": "menu_item", "taalcafe_bestelling": "food_dialogue",
        "op_de_markt": "market_place", "prijs_vragen": "price_question",
        "hoeveelheden": "quantity_phrase", "prijskaartjes": "price_label",
        "kopen_en_betalen": "buying_paying", "marktgesprek": "market_dialogue",
        "plaatsen": "common_place", "naast_en_tegenover": "location_position",
        "achter_en_voor": "location_position", "waar_en_meer_plaatswoorden": "location_question",
        "eenvoudige_kaart": "map_reading", "waar_is_de_bushalte": "place_dialogue",
        "richtingswoorden": "direction_word", "bevelsvormen": "imperative_direction",
        "de_weg_vragen": "route_question", "korte_route": "short_route",
        "route_op_de_kaart": "route_map", "vanaf_het_taalcafe": "route_dialogue",
        "dagelijkse_activiteiten": "daily_activity", "scheidbare_werkwoorden": "separable_verb_lesson",
        "activiteiten_en_tijden": "routine_time", "eerst_dan_daarna": "sequence_lesson",
        "omars_routine_lezen": "routine_reading", "een_dag_bij_het_taalcafe": "routine_dialogue",
        "een_activiteit_voorstellen": "activity_proposal", "ja_of_nee": "accept_decline",
        "dag_en_tijd_afspreken": "schedule_time", "een_bericht_lezen": "invitation_reading",
        "een_plan_schrijven": "plan_writing", "lotte_en_omar_maken_een_plan": "plan_dialogue",
        "voltooide_tijd": "past_tense_intro", "met_hebben": "hebben_perfect",
        "met_zijn": "zijn_perfect", "wanneer_gebeurde_het": "past_event_time",
        "een_kort_verslag_lezen": "past_reading", "lotte_en_omar_gisteren": "past_dialogue",
        "eten_en_drinken": "taste_preference", "activiteiten": "activity_lesson",
        "houden_van": "strong_preference", "kiezen": "preference_choice",
        "voorkeur_lezen": "preference_reading", "lotte_en_omar_kiezen": "preference_dialogue",
        "grootte_vergelijken": "size_comparison", "prijzen_vergelijken": "price_comparison",
        "net_zo_als": "equal_comparison", "de_beste_keuze": "superlative_choice",
        "advertentie_lezen": "comparison_reading", "lotte_en_omar_kiezen_tas": "comparison_dialogue",
        "een_kaartje_kopen": "ticket_purchase", "vertrektijd_en_perron": "departure_time",
        "vertraging": "delay_announcement", "de_weg_op_het_station": "station_directions",
        "een_kaartje_lezen": "ticket_reading", "lotte_en_omar_op_reis": "travel_dialogue",
        "niet_lekker_voelen": "feeling_unwell", "wat_scheelt_eraan": "symptom_question",
        "koorts_en_verkouden": "fever_cold", "bij_de_apotheek": "pharmacy_visit",
        "advies_lezen": "health_reading", "lotte_checkt_omar": "health_dialogue",
        "wat_doe_je_voor_werk": "job_question", "waar_werk_je": "workplace_question",
        "mijn_werkdag": "work_schedule", "collegas_beschrijven": "colleague_description",
        "werkprofielen_lezen": "work_profile_reading", "werk_gesprek": "work_dialogue",
        "mijn_appartement": "apartment_description", "hoeveel_kamers": "room_count_question",
        "balkon_en_tuin": "housing_feature", "groot_of_klein": "room_size",
        # NOTE: unit18's lesson05 real content_key is
        # nl.a1.unit18.lesson05.advertentie_lezen -- its bare lesson-name
        # segment ("advertentie_lezen") is IDENTICAL to unit14's own
        # lesson05 ("nl.a1.unit14.lesson05.advertentie_lezen"), and this
        # dict is keyed by that bare segment alone (see the "zijn"
        # homograph note in this file's module docstring for the same
        # class of same-string/different-context limitation). No new
        # entry is added here for it -- unit18 lesson05's tokens simply
        # inherit unit14's existing "comparison_reading" value by
        # coincidence. Harmless: no practice template anywhere keys a
        # slot_preset on that literal string, it is purely descriptive
        # metadata. Flagging so a future editor doesn't mistake this for
        # a missing entry and add a duplicate "advertentie_lezen" key,
        # which would silently overwrite (and corrupt) unit14's mapping
        # instead, since Python dict literals keep only the last value
        # for a repeated key with no error.
        "nieuw_appartement": "apartment_dialogue",
        "wat_voor_weer": "weather_question", "koud_of_warm": "temperature_description",
        "het_weerbericht": "weather_forecast", "plannen_maken_bij_weer": "weather_plan",
        "weerbericht_lezen": "weather_reading", "weekend_plannen": "weekend_plan_dialogue",
        "ik_zoek_een_jas": "clothing_item_request", "welke_maat": "clothing_size",
        "welke_kleur": "clothing_color", "past_het": "clothing_fit",
        # unit20's lesson05 AND unit23's lesson05 both use the exact same
        # bare content_key suffix "bonnetje_lezen" (one unit reads a
        # clothing receipt, the other a restaurant bill) -- same dict-
        # keyed-by-bare-suffix collision already documented above for
        # unit14/unit18's "advertentie_lezen". A single shared, honestly
        # generic value ("receipt_reading") is correct for BOTH lessons
        # (both really are "read a receipt" comprehension exercises), so
        # this is not a corruption risk like the advertentie_lezen case --
        # deliberately reused, not accidental.
        "bonnetje_lezen": "receipt_reading", "winterjas_passen": "clothing_dialogue",
        "blij_verdrietig_boos": "basic_feeling", "waarom_ben_je_blij": "feeling_reason",
        "zenuwachtig_voor_iets": "nervous_about", "naar_gevoelens_vragen": "feeling_question",
        "bericht_lezen": "feeling_message_reading", "eerste_dienst_gesprek": "feeling_dialogue",
        "ik_bel_je": "phone_call_intro", "met_wie_spreek_ik": "phone_identity",
        "kun_je_dat_herhalen": "phone_clarification", "een_sms_sturen": "text_message",
        "sms_gesprek_lezen": "text_exchange_reading", "telefoontje_na_dienst": "phone_call_dialogue",
        "hoeveel_kost_het": "total_price_question", "pinnen_of_contant": "payment_method",
        "de_rekening_delen": "bill_splitting", "wisselgeld": "change_handling",
        "rekening_vragen": "bill_dialogue",
        # A2 unit 24 (gemeente/bureaucracy), added 2026-07-07.
        "een_afspraak_maken": "appointment_scheduling",
        "wat_heb_je_nodig": "document_requirements",
        "bij_de_balie": "counter_interaction", "je_bsn_nummer": "bsn_explanation",
        "brief_lezen": "registration_letter_reading",
        "gemeente_afspraak": "gemeente_dialogue",
        # A2 unit 25 (meningen/opinions), added 2026-07-07.
        "wat_vind_je_daarvan": "opinion_question", "volgens_mij": "opinion_phrase",
        "eens_of_niet_eens": "agreement_disagreement",
        "aan_de_andere_kant": "counterargument",
        "forumbericht_lezen": "opinion_reading", "fietspad_gesprek": "opinion_dialogue",
        # A2 unit 26 (bankrekening/banking), added 2026-07-07.
        "rekening_openen": "account_opening",
        "betaalrekening_voor_salaris": "salary_account",
        "bij_de_bank": "bank_counter_interaction", "mijn_bankpas": "bank_card_info",
        "folder_lezen": "banking_reading", "bank_afspraak": "bank_dialogue",
        # A2 unit 27 (huisarts/health), added 2026-07-07.
        "afspraak_bij_huisarts": "doctor_appointment",
        "wat_zijn_de_klachten": "symptom_question", "de_diagnose": "diagnosis",
        "recept_en_advies": "prescription_advice",
        "samenvatting_lezen": "health_summary_reading",
        "huisarts_consult": "doctor_dialogue",
        # A2 unit 28 (probleem melden/housing), added 2026-07-07.
        "er_is_een_probleem": "housing_problem_report",
        "de_verwarming_werkt_niet": "heating_problem",
        "wanneer_komt_de_monteur": "technician_scheduling",
        "een_melding_doen": "issue_report",
        "bevestiging_lezen": "confirmation_reading",
        "verwarming_melden": "housing_report_dialogue",
        # Unit 29 (hobbies), added 2026-07-09.
        "lezen_sporten_koken": "hobby_verbs_set1",
        "muziek_tekenen_gamen": "hobby_verbs_set2",
        "vrije_tijd_vraag": "free_time_question",
        "taalcafe_hobbies": "hobby_dialogue",
        "hobbys_vergelijken": "hobby_reading",
        "weekend_plan": "hobby_weekend_dialogue",
        # Unit 30 (appearance), added 2026-07-09.
        "lang_klein_oud_jong": "appearance_size_age",
        "haar_beschrijven": "appearance_hair",
        "ogen_en_eruitzien": "appearance_eyes",
        "taalcafe_nina": "appearance_dialogue",
        "sander_fenna_vergelijken": "appearance_reading",
        "taalcafe_herkenning": "appearance_recognition_dialogue",
        # Unit 31 (animals and pets), added 2026-07-09.
        "huisdieren_woorden": "pet_noun_lesson",
        "zorg_voor_huisdieren": "pet_care",
        "van_dieren_houden": "pet_plural_preference",
        "taalcafe_lottes_hond": "pet_dialogue",
        "omar_fenna_sander_dieren": "pet_reading",
        "taalcafe_ninas_vogel": "pet_wrapup_dialogue",
        # Unit 32 (sports and exercise), added 2026-07-09.
        "sport_woorden": "sport_noun_lesson",
        "hoe_vaak_sport_je": "sport_frequency",
        "ik_sport_graag": "sport_preference",
        "taalcafe_sander_hardlopen": "sport_dialogue",
        "lotte_fenna_sport": "sport_reading",
        "taalcafe_samen_sporten": "sport_wrapup_dialogue",
        # Unit 33 (transportation), added 2026-07-09. "een_kaartje_kopen" is
        # deliberately NOT re-added here -- this unit's lesson03 (buying a
        # train ticket) reuses the exact same bare content_key suffix as
        # unit15's own "een_kaartje_kopen" lesson (also a ticket-purchase
        # scenario), same dict-keyed-by-bare-suffix collision already
        # documented above for advertentie_lezen/bonnetje_lezen -- unit15's
        # existing "ticket_purchase" value is honestly generic enough to
        # cover both, and this is purely descriptive metadata no template
        # keys a slot_preset on directly, so reusing it is safe, not a bug.
        "vervoer_woorden": "transport_noun_lesson",
        "iedereen_reist_anders": "transport_habit",
        "taalcafe_fenna_omar": "transport_dialogue",
        "wie_reist_hoe": "transport_reading",
        "taalcafe_samen_fietsen": "transport_wrapup_dialogue",
        # Unit 43 (seasons), added 2026-07-12.
        "lente_en_zomer": "season_noun_lesson",
        "herfst_en_winter": "season_noun_lesson",
        "gesprek_bij_het_taalcafe": "season_dialogue",
        "lezen_seizoenen": "season_reading",
        "sander_komt_erbij": "season_wrapup_dialogue",
        # Unit 44 (emergencies), added 2026-07-12.
        "hulp_en_brand": "emergency_help",
        "alarmnummer_en_nooduitgang": "emergency_safety_noun_lesson",
        "politie_ambulance_brandweer": "emergency_service_noun_lesson",
        "brand_bij_het_taalcafe": "emergency_dialogue",
        "lezen_over_de_brand": "emergency_reading",
        "sander_komt_aan": "emergency_wrapup_dialogue",
        # Unit 45 (lost items), added 2026-07-12.
        "kwijt_en_gevonden": "lost_found_status",
        "telefoon_rugzak_portemonnee": "lost_item_noun_lesson",
        "nina_vraagt_bij_de_balie": "lost_item_dialogue",
        "bericht_gevonden_telefoon": "lost_item_reading",
        "sander_checkt_zijn_portemonnee": "lost_item_wrapup_dialogue",
        # Unit 46 (appointments), added 2026-07-12.
        "afspraak_maken": "appointment_scheduling",
        "tijd_beschikbaar": "appointment_time_availability",
        "computerhulp": "appointment_purpose",
        "omar_helpt_herinneren": "appointment_wrapup_dialogue",
        # Unit 47 (library borrowing), added 2026-07-12.
        "lenen_en_terugbrengen": "library_borrow_return",
        "bibliotheekpas": "library_card",
        "inleverdatum": "due_date",
        "balie_lenen": "library_borrow_dialogue",
        "leenbon_lezen": "library_receipt_reading",
        "terug_bij_taalcafe": "library_wrapup_dialogue",
        # Unit 48 (waste sorting), added 2026-07-12.
        "afval_scheiden": "waste_sorting",
        "de_bakken": "waste_bin_lesson",
        "papier_en_glas": "recyclable_material_lesson",
        "omar_helpt_nina": "waste_sorting_dialogue",
        "afvalkalender_lezen": "waste_calendar_reading",
        "lotte_hoort_het": "waste_sorting_wrapup_dialogue",
        # A2 unit 73 (sollicitatiegesprek/job interview), added 2026-07-10.
        "ik_wil_solliciteren": "job_application_interest",
        "ik_bel_over_de_vacature": "job_interview_appointment",
        "mijn_ervaring_en_vaardigheden": "experience_and_skills",
        "ben_ik_beschikbaar": "availability_and_hours",
        "een_vacature_lezen": "job_ad_reading",
        "het_sollicitatiegesprek": "job_interview_dialogue",
        # A2 unit 74 (reisvertraging/travel disruption), added 2026-07-11.
        "er_is_een_vertraging": "delay_report",
        "de_trein_valt_uit": "cancellation_report",
        "ik_mis_mijn_aansluiting": "missed_connection",
        "bij_de_servicebalie": "service_desk_request",
        "mededeling_lezen": "disruption_notice_reading",
        "lotte_bij_de_balie": "disruption_dialogue",
        # A2 unit 75 (schermtijd/screen time and online habits), added
        # 2026-07-11.
        "ik_gebruik_mijn_telefoon_vaak": "phone_use_frequency",
        "ik_chat_met_vrienden": "chat_habit",
        "te_veel_schermtijd": "screen_time_opinion",
        "minder_tijd_op_je_telefoon": "reduce_screen_time_opinion",
        "blog_lezen": "screen_time_reading",
        "omar_en_lotte_praten": "screen_time_dialogue",
        # A2 unit 76 (drukke week/describing a weekly schedule), added
        # 2026-07-11.
        "op_maandag_en_woensdag": "weekly_schedule_days",
        "eerst_werken_dan_sporten": "sequencing_activities",
        "door_de_week_versus_weekend": "weekday_weekend_contrast",
        "een_drukke_agenda": "busy_schedule",
        "ninas_week_lezen": "weekly_schedule_reading",
        "lotte_en_omar_over_de_week": "weekly_schedule_dialogue",
        # A2 unit 77 (iets terugbrengen/shopping complaint and returns),
        # added 2026-07-11.
        "deze_koptelefoon_is_kapot": "broken_item_report",
        "ik_wil_mijn_geld_terug": "refund_request",
        "heeft_u_het_bonnetje_nog": "receipt_question",
        "het_retourbeleid": "return_policy_statement",
        "beleid_lezen": "return_policy_reading",
        "omar_brengt_de_koptelefoon_terug": "return_dialogue",
        # B1 unit 01 (hypothetische situaties/hypothetical situations),
        # added 2026-07-11.
        "ik_zou_graag": "hypothetical_wish_singular",
        "wij_zouden": "hypothetical_wish_plural",
        "als_had_was": "unreal_conditional_als",
        "de_loterij": "lottery_hypothetical",
        "opnieuw_kiezen": "redo_choice_hypothetical",
        # B1 unit 02 (mening en nuance/opinion and nuance), added
        # 2026-07-11.
        "hoewel": "concession_hoewel",
        "ondanks_dat": "concession_ondanks_dat",
        "toch_echter": "contrast_toch_echter",
        "gesprek_vlees": "opinion_dialogue_meat",
        "artikel_minder_vlees": "opinion_article_reading",
        # B1 unit 03 (werkoverleg/workplace meetings), added 2026-07-11.
        "zou_u": "polite_request_zou_u",
        "voorstellen": "meeting_proposal",
        "agenda_vragen": "meeting_agenda_question",
        "overleg_met_bakker": "meeting_dialogue",
        "email_lezen": "meeting_email_reading",
        # B1 unit 04 (ingewikkelde zinnen/relative clauses), added
        # 2026-07-11. "die"/"dat"/"waar" are single-word bare lesson-key
        # suffixes -- verified no collision with any existing
        # lesson_categories key (every other key in this dict is a
        # multi-word snake_case string).
        "die": "relative_clause_die",
        "dat": "relative_clause_dat",
        "waar": "relative_clause_waar",
        "klein_wereldje": "small_world_dialogue",
        "sara_lezen": "relative_clause_reading",
        # B1 unit 05 (indirecte rede/indirect speech), added 2026-07-11.
        "zei_dat": "reported_speech_statement",
        "zei_dat_zou": "reported_speech_future",
        "vroeg_of": "reported_speech_question",
        "omar_belde": "reported_speech_dialogue",
        "omar_belde_lezen": "reported_speech_reading",
        # B1 unit 06 (verplichtingen/obligations), added 2026-07-11.
        "moet_schoonmaken": "obligation_moet",
        "had_moeten_opruimen": "past_regret_had_moeten",
        "hoef_niet_koken": "no_obligation_hoeven",
        "mag_niet_roken": "prohibition_mag_niet",
        "omar_bezoek_lezen": "obligation_reading",
        # B1 unit 07 (kunnen en konden/ability, present and past), added
        # 2026-07-11.
        "kan_paspoort_ophalen": "present_ability_kan",
        "kon_niet_komen": "past_ability_kon",
        "had_kunnen_ophalen": "past_regret_had_kunnen",
        "zou_kunnen_afspraak": "hypothetical_ability_zou_kunnen",
        "paspoort_lezen": "ability_reading",
        # B1 unit 08 (reële en irreële situaties/real and unreal
        # conditionals), added 2026-07-11.
        "reele_conditie_park": "real_conditional",
        "onreele_heden_studeren": "unreal_present_conditional",
        "onreele_verleden_feest": "unreal_past_conditional",
        "weekend_dialoog": "conditional_dialogue",
        "sara_feest_lezen": "conditional_reading",
        # B1 unit 09 (eens en oneens/agreement and disagreement), added
        # 2026-07-11.
        "eens_werkweek": "agreement_eens",
        "oneens_werkweek": "disagreement_oneens",
        "jij_zegt_dat": "restating_opinion",
        "debat_dialoog": "debate_dialogue",
        "werkweek_lezen": "debate_reading",
        # B1 unit 10 (werkverantwoordelijkheden/work responsibilities),
        # added 2026-07-11.
        "verantwoordelijk_medicatie": "job_responsibility_statement",
        "bijna_klaar_rapport": "work_status_update",
        "zou_u_kunnen_helpen": "polite_help_request",
        "bakker_dialoog": "workplace_dialogue",
        "werkdag_lezen": "workday_reading",
        # B1 unit 11 (een verhaal vertellen/telling a story), added
        # 2026-07-11.
        "terwijl_koken": "background_action_terwijl",
        "eerst_later": "sequencing_eerst_later",
        "toen_opnam": "past_narrative_toen",
        "sara_dialoog": "storytelling_dialogue",
        "verhaal_lezen": "storytelling_reading",
        # B1's own review lesson (unit 01-11's "wrapup_production" bare
        # suffix, identical across all 11 units) -- same intentional
        # bare-suffix-collision-reuse precedent already established for
        # advertentie_lezen/bonnetje_lezen/een_kaartje_kopen elsewhere in
        # this dict: every one of these 11 lessons really is the same kind
        # of generic unit-review production wrapup, so one shared
        # descriptive value is correct, not a missing-entry bug.
        "wrapup_production": "b1_unit_review",
        # ------------------------------------------------------------------
        # A1 volume batch: units 34-42 and 49-72, added 2026-07-22.
        # 198 lessons, 190 new keys. THREE bare suffixes already exist in
        # this dict and are deliberately NOT re-added -- a repeated key in a
        # Python dict literal silently keeps only the last value and would
        # corrupt the earlier unit's mapping (same trap already documented
        # for "advertentie_lezen" above):
        #   unit49.lesson05 "bevestiging_lezen"  -> reuses a2 unit74's
        #       "confirmation_reading" (both are read-a-confirmation lessons)
        #   unit50.lesson04 "bij_de_apotheek"    -> reuses a1 unit16's
        #       "pharmacy_visit" (both are a pharmacy counter visit)
        #   unit51.lesson03 "een_afspraak_maken" -> reuses a2 unit24's
        #       "appointment_scheduling" (both are booking an appointment)
        # FIVE more suffixes repeat WITHIN this batch and get one shared,
        # honestly generic value each (all really are the same lesson kind):
        # "de_prijslijst_lezen" (u51/u53), "het_programma_lezen" (u56/u58),
        # "ik_wil_een_kaartje_kopen" (u57/u58), "het_bord_bij_de_ingang"
        # (u59/u64/u65).
        # ------------------------------------------------------------------
        # Unit 34 (technologie).
        "telefoon_computer_internet": "device_vocabulary",
        "de_app_bericht": "app_message", "iets_opzoeken": "looking_something_up",
        "taalcafe_lotte_bericht": "tech_message_dialogue",
        "wie_gebruikt_wat": "tech_habits_reading",
        "taalcafe_tot_zaterdag": "tech_plan_dialogue",
        # Unit 35 (opleiding).
        "studeren_opleiding": "study_programme", "cursus_leren": "course_learning",
        "universiteit_hogeschool": "education_institution",
        "taalcafe_sander_cursus": "study_dialogue",
        "wie_studeert_wat": "study_profile_reading",
        "taalcafe_spaans_oefenen": "study_plan_dialogue",
        # Unit 36 (verjaardag).
        "de_verjaardag": "birthday_date", "vieren_feest": "party_celebration",
        "uitnodigen": "invitation_verb",
        "taalcafe_planning": "party_planning_dialogue",
        "wie_doet_wat_feest": "party_reading", "taalcafe_feest": "party_dialogue",
        # Unit 37 (huishouden).
        "opruimen": "tidying_up", "rommel_stofzuigen": "cleaning_task",
        "kun_je_helpen": "chore_help_request",
        "zondag_huishouden": "chores_dialogue",
        "wie_doet_wat_huishouden": "chores_reading",
        "appartement_klaar": "chores_wrapup_dialogue",
        # Unit 38 (buurt).
        "de_buurt": "neighbourhood_place", "buurman_buurvrouw": "neighbour_person",
        "vriendelijk_groeten": "greeting_neighbours",
        "lotte_ontmoet_peter": "neighbour_dialogue",
        "wie_is_wie_in_de_buurt": "neighbour_reading",
        "koffie_met_de_buren": "neighbour_wrapup_dialogue",
        # Unit 39 (post).
        "de_brief_het_pakket": "mail_item",
        "postzegel_adres_schrijven": "stamp_and_address",
        "aankomen_duren": "delivery_time",
        "bij_het_postkantoor": "post_office_dialogue",
        "lotte_stuurt_pakket": "mail_reading",
        "naar_huis": "mail_wrapup_dialogue",
        # Unit 40 (koken).
        "de_ui_de_tomaat_snijden": "ingredient_cutting",
        "de_pan_bakken": "frying_pan", "klaarmaken_proeven": "preparing_tasting",
        "in_de_keuken_bij_omar": "cooking_dialogue",
        "lotte_omar_koken_samen": "cooking_reading",
        "sander_komt_eten": "meal_wrapup_dialogue",
        # Unit 41 (persoonlijkheid).
        "aardig_en_grappig": "trait_kind_funny",
        "rustig_en_geduldig": "trait_calm_patient",
        "nieuwsgierig_verlegen": "trait_curious_shy",
        "nina_vraagt_bij_taalcafe": "personality_dialogue",
        "nina_hoort_over_iedereen": "personality_reading",
        "nina_beschrijft_zichzelf": "self_description_dialogue",
        # Unit 42 (kleuren).
        "rood_en_geel": "colour_red_yellow", "wit_en_oranje": "colour_white_orange",
        "roze_en_paars": "colour_pink_purple",
        "nina_en_lotte_bloemenmarkt": "colour_dialogue",
        "nina_en_lotte_kopen_tulpen": "colour_reading",
        "tulpen_voor_het_taalcafe": "colour_wrapup_dialogue",
        # Unit 49 (accommodatie). lesson05 reuses "bevestiging_lezen".
        "kamer_boeken": "room_booking", "ontbijt_inbegrepen": "breakfast_included",
        "sleutel_wifi": "key_and_wifi", "inchecken_bij_de_balie": "checkin_dialogue",
        "lotte_belt": "accommodation_wrapup_dialogue",
        # Unit 50 (apotheek). lesson04 reuses "bij_de_apotheek".
        "ik_heb_hoofdpijn": "symptom_statement",
        "een_tablet_innemen": "taking_medicine",
        "de_dosering_lezen": "dosage_instruction",
        "het_etiket_lezen": "medicine_label_reading",
        "omar_vraagt_hoe_het_gaat": "pharmacy_wrapup_dialogue",
        # Unit 51 (kapper). lesson03 reuses "een_afspraak_maken".
        "mijn_haar_is_te_lang": "haircut_need",
        "kunt_u_mijn_haar_knippen": "haircut_request",
        "bij_de_kapper": "hairdresser_dialogue",
        "de_prijslijst_lezen": "price_list_reading",
        "lotte_ziet_het_nieuwe_kapsel": "haircut_wrapup_dialogue",
        # Unit 52 (fiets huren).
        "ik_wil_een_fiets_huren": "bike_rental_request",
        "hoeveel_kost_het_per_dag": "daily_rate_question",
        "ik_wil_de_fiets_voor_het_weekend": "rental_duration",
        "bij_de_fietsenwinkel": "bike_rental_dialogue",
        "de_huurprijzen_lezen": "rental_price_reading",
        "omar_ziet_de_nieuwe_fiets": "bike_rental_wrapup_dialogue",
        # Unit 53 (wasserette). lesson05 reuses "de_prijslijst_lezen".
        "ik_wil_mijn_kleren_wassen": "laundry_request",
        "hoeveel_kost_een_wasbeurt": "wash_price_question",
        "wanneer_is_de_was_klaar": "laundry_ready_time",
        "bij_de_wasserette": "launderette_dialogue",
        "lotte_bij_de_wasserette": "laundry_wrapup_dialogue",
        # Unit 54 (zwembad).
        "ik_wil_naar_het_zwembad": "pool_visit_request",
        "hoeveel_kost_een_kaartje": "ticket_price_question",
        "hoe_laat_gaat_het_zwembad_open": "pool_opening_time_question",
        "bij_het_zwembad": "pool_dialogue",
        "de_openingstijden_lezen": "opening_hours_reading",
        "omar_bij_het_zwembad": "pool_wrapup_dialogue",
        # Unit 55 (restaurant).
        "ik_wil_naar_het_restaurant": "restaurant_visit_request",
        "wat_wilt_u_eten": "food_order_question",
        "mag_ik_de_rekening": "bill_request",
        "bij_het_restaurant": "restaurant_dialogue",
        "het_dagmenu_lezen": "day_menu_reading",
        "lotte_bij_het_restaurant": "restaurant_wrapup_dialogue",
        # Unit 56 (bioscoop).
        "ik_wil_een_film_kijken": "cinema_visit_request",
        "welke_film_wilt_u_zien": "film_choice_question",
        "hoe_laat_begint_de_voorstelling": "showtime_question",
        "bij_de_bioscoop": "cinema_dialogue",
        "het_programma_lezen": "programme_reading",
        "omar_bij_de_bioscoop": "cinema_wrapup_dialogue",
        # Unit 57 (museum).
        "ik_wil_naar_het_museum": "museum_visit_request",
        "ik_wil_een_kaartje_kopen": "ticket_purchase_request",
        "hoe_laat_sluit_het_museum": "closing_time_question",
        "bij_het_museum": "museum_dialogue",
        "het_informatiebord_lezen": "information_board_reading",
        "omar_nina_en_lotte_bij_het_museum": "museum_wrapup_dialogue",
        # Unit 58 (concert). lesson02/05 reuse unit57/unit56's keys.
        "ik_wil_naar_het_concert": "concert_visit_request",
        "hoe_laat_begint_het_concert": "concert_start_question",
        "bij_de_kassa": "box_office_dialogue",
        "omar_nina_en_lotte_bij_het_concert": "concert_wrapup_dialogue",
        # Unit 59 (park).
        "zullen_we_naar_het_park_gaan": "park_outing_proposal",
        "de_bomen_en_het_gras": "park_nature_vocabulary",
        "de_eenden_bij_het_water": "park_animals",
        "het_bord_bij_de_ingang": "entrance_sign_reading",
        "een_picknick_in_het_park": "park_picnic_dialogue",
        "omar_nina_en_lotte_na_het_park": "park_wrapup_dialogue",
        # Unit 60 (sportschool).
        "zullen_we_naar_de_sportschool_gaan": "gym_outing_proposal",
        "de_apparaten_in_de_sportschool": "gym_equipment",
        "de_yogales": "yoga_class",
        "het_rooster_bij_de_balie": "gym_schedule_reading",
        "bij_de_balie_van_de_sportschool": "gym_desk_dialogue",
        "omar_en_nina_na_de_sportschool": "gym_wrapup_dialogue",
        # Unit 61 (strand).
        "zullen_we_naar_het_strand_gaan": "beach_outing_proposal",
        "het_zand_en_de_golven": "beach_nature_vocabulary",
        "zwemmen_in_de_zee": "sea_swimming",
        "het_bord_bij_het_strand": "beach_sign_reading",
        "een_middag_op_het_strand": "beach_dialogue",
        "omar_en_lotte_na_het_strand": "beach_wrapup_dialogue",
        # Unit 62 (dierentuin).
        "zullen_we_naar_de_dierentuin_gaan": "zoo_outing_proposal",
        "de_leeuw_en_de_olifant": "zoo_animal_lion_elephant",
        "de_aap_en_de_giraffe": "zoo_animal_monkey_giraffe",
        "het_bord_bij_de_dierentuin": "zoo_sign_reading",
        "bij_de_kassa_van_de_dierentuin": "zoo_ticket_dialogue",
        "nina_en_omar_na_de_dierentuin": "zoo_wrapup_dialogue",
        # Unit 63 (rondvaart).
        "zullen_we_vandaag_een_rondvaart_maken": "boat_tour_proposal",
        "de_gracht_en_de_brug": "canal_scenery",
        "de_steiger_en_de_gids": "pier_and_guide",
        "het_bord_bij_de_rondvaart": "boat_tour_sign_reading",
        "bij_de_kassa_van_de_rondvaart": "boat_tour_ticket_dialogue",
        "omar_en_lotte_na_de_rondvaart": "boat_tour_wrapup_dialogue",
        # Unit 64 (voetbalwedstrijd). lesson04 reuses unit59's key.
        "zullen_we_vanavond_naar_de_wedstrijd_gaan": "match_outing_proposal",
        "het_team_en_de_speler": "football_people",
        "het_doelpunt_en_de_stand": "football_score",
        "bij_de_kassa_van_het_stadion": "stadium_ticket_dialogue",
        "omar_en_nina_na_de_wedstrijd": "match_wrapup_dialogue",
        # Unit 65 (pretpark). lesson04 reuses unit59's key.
        "zullen_we_vandaag_naar_het_pretpark_gaan": "amusement_park_proposal",
        "de_achtbaan_en_de_rij": "ride_and_queue",
        "het_reuzenrad_en_de_kassa": "ferris_wheel_and_counter",
        "bij_de_kassa_van_het_pretpark": "amusement_park_ticket_dialogue",
        "lotte_hoort_over_het_pretpark": "amusement_park_wrapup_dialogue",
        # Unit 66 (theater).
        "zullen_we_vandaag_naar_het_theater_gaan": "theatre_outing_proposal",
        "het_podium_en_het_gordijn": "stage_and_curtain",
        "de_acteurs_en_de_kassa": "actors_and_counter",
        "het_programma_van_de_voorstelling": "theatre_programme_reading",
        "bij_de_kassa_van_het_theater": "theatre_ticket_dialogue",
        "nina_hoort_over_het_theater": "theatre_wrapup_dialogue",
        # Unit 67 (markt).
        "zullen_we_naar_de_markt_gaan": "market_outing_proposal",
        "de_groente_en_het_fruit": "market_produce",
        "de_appels_en_de_marktkoopman": "market_vendor",
        "de_prijzen_op_de_markt": "market_price_reading",
        "bij_de_kraam_op_de_markt": "market_stall_dialogue",
        "lotte_hoort_over_de_markt": "market_wrapup_dialogue",
        # Unit 68 (bakker).
        "zullen_we_naar_de_bakker_gaan": "bakery_outing_proposal",
        "het_brood_en_het_gebak": "bakery_product",
        "de_croissant_en_de_medewerker": "bakery_counter_staff",
        "de_prijzen_bij_de_bakker": "bakery_price_reading",
        "bij_de_toonbank_bij_de_bakker": "bakery_counter_dialogue",
        "nina_hoort_over_de_bakker": "bakery_wrapup_dialogue",
        # Unit 69 (ijssalon).
        "zullen_we_naar_het_ijssalon_gaan": "ice_cream_outing_proposal",
        "het_ijs_en_de_smaak": "ice_cream_flavour",
        "het_bolletje_en_de_medewerker": "ice_cream_serving",
        "de_prijzen_in_het_ijssalon": "ice_cream_price_reading",
        "bij_de_vitrine_in_het_ijssalon": "ice_cream_counter_dialogue",
        "lotte_hoort_over_het_ijssalon": "ice_cream_wrapup_dialogue",
        # Unit 70 (bloemist).
        "zullen_we_naar_de_bloemist_gaan": "florist_outing_proposal",
        "het_boeket_en_de_kleur": "bouquet_and_colour",
        "de_roos_en_de_medewerker": "florist_counter_staff",
        "de_prijzen_bij_de_bloemist": "florist_price_reading",
        "bij_de_toonbank_bij_de_bloemist": "florist_counter_dialogue",
        "nina_hoort_over_de_bloemist": "florist_wrapup_dialogue",
        # Unit 71 (boekwinkel).
        "zullen_we_naar_de_boekwinkel_gaan": "bookshop_outing_proposal",
        "de_roman_en_de_titel": "book_and_title",
        "de_schrijver_en_de_medewerker": "bookshop_counter_staff",
        "de_prijzen_in_de_boekwinkel": "bookshop_price_reading",
        "bij_de_toonbank_in_de_boekwinkel": "bookshop_counter_dialogue",
        "lotte_hoort_over_de_boekwinkel": "bookshop_wrapup_dialogue",
        # Unit 72 (dierenwinkel).
        "zullen_we_naar_de_dierenwinkel_gaan": "pet_shop_outing_proposal",
        "het_voer_en_de_riem": "pet_supplies",
        "de_medewerker_en_de_mand": "pet_shop_counter_staff",
        "de_prijzen_in_de_dierenwinkel": "pet_shop_price_reading",
        "bij_de_toonbank_in_de_dierenwinkel": "pet_shop_counter_dialogue",
        "nina_hoort_over_de_dierenwinkel": "pet_shop_wrapup_dialogue",
        # Dutch B2 tier lessons (units 01-08), added 2026-08-02. Additive
        # semantic tags only; none match the number/weekday/month special
        # cases. "verhaal_lezen" already exists (storytelling_reading).
        "een_standpunt": "argument_claim",
        "argumenten_geven": "argument_support",
        "de_andere_kant": "argument_concession",
        "weerleggen": "argument_rebuttal",
        "een_betoog_lezen": "argument_reading",
        "een_standpunt_verdedigen": "argument_defense_production",
        "hoe_zeker": "certainty_degree",
        "deductie": "deduction",
        "mogelijkheid": "possibility_guess",
        "het_verleden": "past_speculation",
        "een_tekst_lezen": "speculation_reading",
        "speculeren_in_gesprek": "speculation_dialogue",
        "afzwakken": "hedging_softening",
        "voorzichtig": "cautious_phrasing",
        "benadrukken": "emphasis",
        "focus": "focus_marking",
        "recensie": "review_reading",
        "in_gesprek": "opinion_nuance_dialogue",
        "achtergrond": "narrative_background",
        "gebeurtenis": "narrative_event_sequence",
        "toen_terwijl": "narrative_time_conjunctions",
        "plusquamperfectum": "past_perfect",
        "verhaal_vertellen": "narrative_production",
        "jij_of_u": "register_choice_address",
        "aanhef_afsluiting": "salutation_signoff",
        "directheid": "directness_politeness",
        "de_afspraak": "reschedule_request",
        "twee_berichten": "register_two_messages",
        "register_kiezen": "register_selection",
        "wat_vind_jij": "opinion_prompt",
        "genuanceerd": "nuanced_opinion",
        "reageren": "counterargument_response",
        "voor_en_tegen": "pros_and_cons",
        "een_mening_lezen": "opinion_reading",
        "een_voorstel": "negotiation_proposal",
        "beleefd_weigeren": "polite_refusal",
        "een_voorwaarde": "condition_setting",
        "tot_een_afspraak": "reaching_agreement",
        "een_afspraak_lezen": "agreement_reading",
        "onderhandelen_in_gesprek": "negotiation_dialogue",
        "wie_zegt_wat": "source_attribution",
        "vergelijken": "source_comparison",
        "overeenkomst": "source_agreement",
        "conflict": "source_conflict",
        "twee_recensies": "two_reviews_reading",
        "synthese_in_gesprek": "synthesis_dialogue",
    }
    # Grammar-note METALABELS (native review 2026-07-27): these tokens are
    # introduced INSIDE the number/weekday/month lessons only to EXPLAIN the
    # system (eenheid "unit", tiental "multiple of ten", behalve "except",
    # hoofdletter "capital letter", dag/Dagen, Maanden, jaar "year"), so the
    # blanket lesson-category tag below wrongly marked them as number/weekday/
    # month candidates -- a matching/MC/translate slot then served nonsense
    # like "hoofdletter is the month you heard" (checkpoint-scope, in-unit).
    # Hold them out of those counting/calendar categories; they keep POS-only.
    if lesson_key.startswith("nl.c1."):
        # C1 lesson slugs are not unique across units ("publiek" is both
        # c1_unit03 lesson01 and c1_unit07 lesson04), so the C1 tier derives
        # one tag per (unit, lesson) instead of extending the slug-keyed dict:
        # nl.c1.unit03.lesson01.publiek -> "c1u03_publiek".
        _cat = f"c1u{lesson_key.split('.')[2][len('unit'):]}_{unit_lesson}"
        semantic.extend(NL_C1_EXTRA_TAGS.get(token, ()))
    else:
        _cat = lesson_categories[unit_lesson]
    _METALABELS = {"eenheid", "tiental", "behalve", "hoeveel", "hoofdletter",
                   "dag", "dagen", "maanden", "jaar"}
    if not (_cat in {"number", "weekday", "month", "ordinal_number"}
            and t in _METALABELS):
        semantic.append(_cat)
    if t in {"jij", "je"}: semantic.append("informal_address")
    if t == "u": semantic.append("polite_address")
    if token in {"Hallo", "Hoi", "Goedemorgen", "Goedemiddag", "Goedenavond"}: semantic.append("greeting")
    if t in {"goed", "prima", "slecht"}: semantic.append("wellbeing_answer")
    if token in {"Lotte", "Noor", "Omar", "Sander", "Fenna", "Jan", "Marieke"}: semantic.append("person_name")
    if token in {"Nederland", "België", "Duitsland", "Egypte"}: semantic.append("place_name")
    if token in {"Rotterdam", "Utrecht", "Amsterdam"}: semantic.append("place_name")
    if t in {"nederland", "belgië", "duitsland", "egypte"}: semantic.append("country")
    if t in {"nederlands", "belgisch", "engels", "duits"}: semantic.append("language_or_nationality")
    # Unit 5 (family): narrower tags so practice-template slots only ever
    # combine grammatically valid words -- see the homograph note in this
    # file's module docstring for why "zijn" (his) is deliberately excluded.
    if t in {"broer", "zus"}: semantic.append("sibling")
    if t in {"vader", "moeder", "broer", "zus", "kind", "opa", "oma", "oom", "tante"}:
        semantic.append("family_singular")
    if t in {"opa", "oma", "oom", "tante"}: semantic.append("extended_only")
    # Exact-case check (not casefolded): the capitalized "Mijn" variant is a
    # separate lexeme (sentence-initial only, from units 2-4) and must NOT
    # be eligible here -- every practice-template slot using this tag places
    # the word mid-sentence, where a capital would render as a real
    # capitalization error (e.g. "Dit is Mijn broer.").
    if token in {"mijn", "je", "jouw"}: semantic.append("possessive_flexible")
    # Narrower than place_name: only Dutch city names (spelled identically in
    # English), safe for a translation-frame slot with default token
    # rendering. place_name also includes country names whose english_gloss
    # differs from the raw token (Nederland -> "the Netherlands"), which
    # would leak an untranslated Dutch word into an English frame if used
    # the same way -- narrow this instead of reusing place_name there.
    if token in {"Rotterdam", "Utrecht", "Amsterdam"}: semantic.append("city_name")
    number_words = set("nul één twee drie vier vijf zes zeven acht negen tien elf twaalf dertien veertien vijftien zestien zeventien achttien negentien twintig dertig veertig vijftig zestig zeventig tachtig negentig eenentwintig tweeëntwintig tweeëndertig tweeënveertig achtenveertig vijfenzeventig negenennegentig drieënveertig vijfenzestig zevenentachtig achtentwintig vijfentwintig vijfendertig vierentwintig".split())
    if t in number_words or token in SYMBOLS and token != "'s": semantic.append("number")
    # Extended 2026-07-06 (unit17: negen/twaalf/vijf/elf are the real
    # clock-hour numbers this unit's schedule content actually uses --
    # "Ik begin om negen uur."/"Ik heb pauze om twaalf uur."/"Ik stop om
    # vijf uur."/"Ik begin later, om elf uur.").
    if t in {"twee", "drie", "zeven", "acht", "veertien", "achttien", "twintig", "negen", "twaalf", "vijf", "elf"} or token in {"2", "3", "7", "8", "14", "18", "20"}: semantic.append("hour_number")
    if t in set("maandag dinsdag woensdag donderdag vrijdag zaterdag zondag".split()): semantic.append("weekday")
    # "weekday" above is contaminated for matching_pairs use: the
    # lesson_categories catch-all tags EVERY token introduced in the
    # "weekdagen" lesson (including "hoofdletter"/"dag"/"Dagen", which are
    # NOT weekday names) with the same "weekday" string, and the casefold
    # comparison above also folds in the capitalized sentence-initial
    # "Vrijdag" as a case-duplicate of "vrijdag" -- both already documented
    # as a real, unfixed bug in docs/content/practice/en-nl/a1_unit11.yaml's
    # review notes. Added here (additive only, does not change "weekday"
    # itself, so every existing template that already reads "weekday" keeps
    # its current behavior) so a matching_pairs preset can request a clean,
    # exact-case, case-deduplicated 7-member pool instead.
    if token in {"maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"}:
        semantic.append("weekday_pure")
    if t in set("januari februari maart april mei juni juli augustus september oktober november december".split()): semantic.append("month")
    if t.endswith(("de", "ste")) and t not in {"de", "zelfde"}: semantic.append("ordinal_number")
    if t in {"ochtend", "middag", "avond", "nacht", "ochtends", "middags", "avonds", "nachts", "vrijdagmiddag"}: semantic.append("time_of_day")
    if t in {"ochtend", "middag", "avond", "nacht"}: semantic.append("day_period")
    # Unit 7 (shopping at the market): produce items are the same 4-member
    # group across every lesson (they're literally what's for sale) --
    # a single reusable tag, safe as both a bare-word recognition slot and
    # embedded in "een kilo {item}" / "Dan neem ik een kilo {item},
    # alstublieft." frames, since every member is a plural mass/count noun
    # that collocates naturally with "kilo".
    if t in {"appels", "peren", "tomaten", "paprika's"}: semantic.append("produce")
    # "produce" above is casefolded, so it also matches the capitalized
    # sentence-initial variants ("Appels", "Peren", "Tomaten", "Paprika's")
    # as case-duplicates of the same word -- harmless for the existing
    # bare-word/translation slots that already use "produce" (each draw is
    # independent), but a matching_pairs slot could draw both cases of the
    # same word into two different "pairs". Additive exact-case tag for
    # matching_pairs use only.
    if token in {"appels", "peren", "tomaten", "paprika's"}: semantic.append("produce_pure")
    # Narrower than a generic "quantity" tag: only kilo/pond are directly
    # attested with "tomaten" in this unit's real content ("Een pond
    # tomaten, alstublieft."); "gram" always collocates with "honderd" (never
    # bare "een gram"), and "stuk" pairs with a count context, not a weight
    # phrase -- excluded to avoid an unnatural-sounding generated sentence.
    if t in {"kilo", "pond"}: semantic.append("market_quantity")
    # Unit 8 (locating places): a 7-member "place" tag (both lowercase and
    # the capitalized map-label variants) for bare-word recognition, plus a
    # narrower "place_non_station" tag excluding "station" -- every
    # generated sentence in this unit fixes "het station" as the anchor
    # place ("De {item} is naast het station."), so including "station"
    # itself in the fillable slot would risk a self-referential sentence
    # ("The station is next to the station."), same bug class as nl-en
    # unit09's hospital self-reference catch earlier this session.
    if t in {"station", "supermarkt", "bibliotheek", "ziekenhuis", "bank", "postkantoor", "bushalte"}:
        semantic.append("place")
    if t in {"supermarkt", "bibliotheek", "ziekenhuis", "bank", "postkantoor", "bushalte"}:
        semantic.append("place_non_station")
    # All 4 are freely interchangeable in "De X is {item} het station."/
    # "Het X is {item} de Y." location frames -- verified against this
    # unit's real content, which uses all 4 with the same "is ... het
    # station" sentence shape.
    if t in {"naast", "tegenover", "achter", "voor"}: semantic.append("position")
    # position_no_voor: excludes 'voor', whose canonical gloss is the unit01 purpose
    # sense 'for; about' — wrong for unit08's positional 'in front of' drill. Used only
    # by u08 lesson03.translate.004 (bare-word translate, where the gloss IS the prompt);
    # the word_order position templates keep 'voor' since their frame gives the
    # positional context and the gloss is never shown. 2026-07-30.
    if t in {"naast", "tegenover", "achter"}: semantic.append("position_no_voor")
    # Unit 9 (directions): the 5 core direction words, safe as a group for
    # bare-word recognition only (not a single shared generative frame --
    # "sla" idiomatically only pairs with linksaf/rechtsaf, never rechtdoor,
    # see turn_direction below).
    if t in {"links", "rechts", "linksaf", "rechtsaf", "rechtdoor"}:
        semantic.append("direction_word")
    # Casefolded above, so "Rechtdoor" (capitalized sentence-initial variant)
    # is a case-duplicate of "rechtdoor" under this tag -- harmless for
    # existing bare-word slots, but unsafe for a matching_pairs slot (could
    # draw both cases as if they were two different pairs). Additive
    # exact-case tag for matching_pairs use only.
    if token in {"links", "rechts", "linksaf", "rechtsaf", "rechtdoor"}:
        semantic.append("direction_word_pure")
    # Narrower: only these two are attested after "Sla ___." in this unit's
    # real content ("Sla linksaf."/"Sla rechtsaf.") -- "rechtdoor" pairs with
    # "ga", not "sla" ("Sla rechtdoor" is not idiomatic Dutch), so it is
    # deliberately excluded from this tag.
    if t in {"linksaf", "rechtsaf"}: semantic.append("turn_direction")
    # Unit 10 (daily routine): all 7 routine-verb INFINITIVES (both
    # separable and non-separable) are safe together for bare-word
    # recognition only -- there's no shared sentence frame here (each
    # conjugated ik-form is irregular/differently-structured: sta/kleed/
    # ontbijt/werk/eet/was/slaap), so this tag is never used to fill a
    # generative frame, only to test infinitive-to-meaning recognition.
    if t in {"opstaan", "aankleden", "ontbijten", "werken", "eten", "afwassen", "slapen"}:
        semantic.append("routine_verb_infinitive")
    # Only 3 members -- kept out of multiple_choice/listen_select (which
    # need >=4 real candidates), used only in translation/fill_in_blank
    # templates below.
    if t in {"eerst", "dan", "daarna"}: semantic.append("sequence_word")
    # Unit 11 (making simple plans): 4-member bare-word recognition set
    # spanning adverb/verb/noun -- deliberately recognition-only (no shared
    # frame), since these words don't collocate uniformly (e.g. "samen"
    # is an adverb modifying a whole proposal, "afspreken" a verb, "bericht"/
    # "uitnodiging" nouns for different concrete things).
    if t in {"samen", "afspreken", "bericht", "uitnodiging"}:
        semantic.append("plan_vocab")
    # Unit 12 (perfect tense): the two auxiliary groups must NEVER be mixed
    # in one tag -- "Ik heb gegaan" is ungrammatical (gaan/komen take zijn,
    # not hebben). 4-member hebben-participle group is safe for bare-word
    # recognition (their infinitives are also tagged separately below).
    if t in {"gedronken", "gegeten", "gewerkt", "gekocht"}: semantic.append("participle_hebben")
    if t in {"drinken", "eten", "werken", "kopen"}: semantic.append("infinitive_hebben")
    # Only 2 members (gaan/komen take zijn) -- kept out of multiple_choice/
    # listen_select, used only in translation templates below.
    if t in {"gegaan", "gekomen"}: semantic.append("participle_zijn")
    # Only 2 members -- same reasoning, translation-only.
    if t in {"gisteren", "vanmorgen"}: semantic.append("recent_time")
    # Unit 13 (expressing preferences): "lekker" (food/drink) and "leuk"
    # (activities) are grammatically distinct registers in Dutch and must
    # never be mixed into one generative frame (real content explicitly
    # teaches this contrast) -- kept as two separate 3-member tags, each
    # verified safe in its own "Ik vind {item} lekker/leuk." frame.
    if t in {"koffie", "thee", "tomatensoep"}: semantic.append("lekker_food")
    if t in {"fietsen", "wandelen", "winkelen"}: semantic.append("activity_leuk")
    # Broader 6-member bare-word recognition tag spanning both groups
    # (mixed noun/verb) -- safe since recognition doesn't require shared
    # collocation, only the two frame-specific tags above are used
    # generatively.
    if t in {"koffie", "thee", "tomatensoep", "fietsen", "wandelen", "winkelen"}:
        semantic.append("preference_item")
    # Exact-case sibling (2026-07-29): excludes the capitalized Fietsen (unit28
    # grammar note) / Koffie / Thee (unit06 sentence-initial) variants that surfaced
    # as reworded-gloss MC/listen ambiguity in unit13's recognition templates.
    if token in {"koffie", "thee", "tomatensoep", "fietsen", "wandelen", "winkelen"}:
        semantic.append("preference_item_pure")
    # Unit 14 (making comparisons): 6-member regular comparative tag, all
    # verified safe in "De rugzak is {item} dan de tas." (each -er/-der
    # form takes "dan" grammatically; the real content's own advertisement
    # actually uses lichter/sterker to describe the bag, but the frame's
    # own subject/object choice here is a drill sentence, not a factual
    # claim, so reversed pairings are still grammatically valid).
    if t in {"groter", "kleiner", "duurder", "goedkoper", "lichter", "sterker"}:
        semantic.append("comparative_adj")
    # Only 2 members ("net zo {item} als" doesn't take -er/-st at all) --
    # kept out of multiple_choice/listen_select, translation/fill_in_blank
    # only.
    # Exact-case (token, not casefolded t): the pack intends the 2-member
    # {mooi, praktisch}; a casefold check also swept in the capitalized "Mooi"
    # (unit08's standalone interjection "Nice.", gloss "nice; good"), which made
    # u14 translate.001 underdetermined (Mooi/goed both "nice; good"). 2026-07-30.
    if token in {"mooi", "praktisch"}: semantic.append("equal_adj")
    # 4-member bare-word recognition only -- these superlatives are
    # structurally too different to share one generative frame (duurst/
    # mooist are predicative -st forms, beste is attributive, meest
    # modifies ruimte differently) -- same discipline as this unit's
    # sibling tags above.
    if t in {"duurst", "mooist", "beste", "meest"}: semantic.append("superlative_word")
    # Unit 15 (traveling by train): 6-member bare-word recognition tag
    # spanning station/travel nouns -- no shared generative frame needed,
    # recognition-only.
    if t in {"kaartje", "perron", "vertraging", "ingang", "uitgang", "wachtruimte"}:
        semantic.append("travel_noun")
    # Casefolded above, so "Kaartje"/"Perron" (capitalized sentence-initial
    # variants) are case-duplicates under this tag -- harmless for existing
    # bare-word slots, unsafe for matching_pairs. Additive exact-case tag
    # for matching_pairs use only.
    if token in {"kaartje", "perron", "vertraging", "ingang", "uitgang", "wachtruimte"}:
        semantic.append("travel_noun_pure")
    # Narrower 3-member subset (just the station places), safe for "Waar
    # is de {item}?" -- verified all three take "de" and fit this exact
    # question shape, directly attested for wachtruimte in the real
    # content.
    if t in {"ingang", "uitgang", "wachtruimte"}: semantic.append("station_place")
    # Unit 16 (describing a basic health problem): the core grammar point
    # is that symptom NOUNS take hebben (Ik heb hoofdpijn.) while symptom
    # ADJECTIVES take zijn (Ik ben ziek.) -- the real content's own
    # zijn_note lesson makes this contrast explicit, so these two tags
    # must NEVER be mixed (mixing would generate "Ik heb ziek."/"Ik ben
    # hoofdpijn.", both ungrammatical), same discipline as unit12's
    # participle_hebben/participle_zijn split.
    if t in {"hoofdpijn", "buikpijn", "keelpijn", "koorts"}: semantic.append("symptom_hebben")
    # Casefolded above, so "Koorts" (capitalized sentence-initial variant) is
    # a case-duplicate of "koorts" under this tag -- harmless for existing
    # bare-word slots, unsafe for matching_pairs. Additive exact-case tag
    # for matching_pairs use only.
    if token in {"hoofdpijn", "buikpijn", "keelpijn", "koorts"}: semantic.append("symptom_hebben_pure")
    # Only 2 members -- kept out of multiple_choice/listen_select (which
    # need >=4), used only in word_order/fill_in_blank/translation.
    if t in {"ziek", "verkouden"}: semantic.append("symptom_zijn")
    # Exact-case sibling (excludes the capitalized "Ziek" grammar-note token from
    # unit16 lesson03's zijn_note) so word_order/translate slots don't bake a wrong
    # mid-sentence capital into the answer. Mirrors symptom_hebben_pure above.
    if token in {"ziek", "verkouden"}: semantic.append("symptom_zijn_pure")
    # Unit 17 (work and occupation): broad 8-member recognition-only tag
    # (bare-word MC/listen_select/translation), safe because it's never
    # used to fill one shared generative sentence -- restaurant/
    # ziekenhuis/kantoor each take a different article/preposition
    # combination (een restaurant / het ziekenhuis / op kantoor with no
    # article at all), verified directly from this unit's real content.
    if t in {"beroep", "kok", "verpleegkundige", "restaurant", "ziekenhuis", "kantoor", "baan", "pauze"}:
        semantic.append("work_vocab")
    # Exact-case variant for matching_pairs (avoids a casefold case-dup
    # drawing e.g. both "Pauze" and "pauze" as if they were two different
    # pairs), same convention as every other _pure tag in this file.
    if token in {"beroep", "kok", "verpleegkundige", "restaurant", "ziekenhuis", "kantoor", "baan", "pauze"}:
        semantic.append("work_vocab_pure")
    # Narrower 2-member generative tag: kok/verpleegkundige both take
    # "werken als" + the bare occupation noun with no article --
    # verified ("Ik werk als kok."/"Ik werk als verpleegkundige."),
    # unlike the workplace nouns above which are deliberately excluded
    # from any shared generative frame.
    if t in {"kok", "verpleegkundige"}: semantic.append("occupation")
    # Narrower 2-member generative tag: begin/stop are both regular
    # ik-form verbs sharing the identical "Ik {verb} om {hour} uur."
    # frame shape (verified: "Ik begin om negen uur."/"Ik stop om vijf
    # uur."). "pauze" is deliberately excluded -- its real sentence is
    # "Ik heb pauze om {hour} uur.", built around a different verb
    # ("heb", not the {verb} slot itself), so mixing it in would drop
    # "heb" and generate an ungrammatical sentence.
    if t in {"begin", "stop"}: semantic.append("schedule_verb")
    # Unit 18 (housing): 5-member generative room tag. "een" is Dutch's
    # single invariant indefinite article (unlike "de"/"het" for
    # definites), so "Ik heb een {item}." is grammatically safe for all
    # 5 members regardless of each noun's own gender -- verified: real
    # content uses "een appartement"/"een woonkamer"/"een slaapkamer"/
    # "een keuken"/"een badkamer".
    if t in {"appartement", "woonkamer", "slaapkamer", "keuken", "badkamer"}:
        semantic.append("room_word")
    if token in {"appartement", "woonkamer", "slaapkamer", "keuken", "badkamer"}:
        semantic.append("room_word_pure")
    # Broader 7-member recognition-only tag (adds balkon/tuin) -- safe
    # for bare-word MC/listen_select/translation, NOT a shared
    # generative frame: balkon/tuin use the "Er is (geen) {item}."
    # existential pattern, a different sentence shape from the room
    # words' "Ik heb een {item}."
    if t in {"appartement", "woonkamer", "slaapkamer", "keuken", "badkamer", "balkon", "tuin"}:
        semantic.append("housing_vocab")
    if token in {"appartement", "woonkamer", "slaapkamer", "keuken", "badkamer", "balkon", "tuin"}:
        semantic.append("housing_vocab_pure")
    # 3-member recognition-only tag -- groot/klein/gezellig each attach
    # to a different subject in the real content (De woonkamer is
    # groot./De keuken is klein./Het appartement is klein maar
    # gezellig.), so kept out of any single shared generative frame,
    # translation/word_order only.
    if t in {"groot", "klein", "gezellig"}: semantic.append("home_adjective")
    # Unit 19 (weather): 4-member generative adjective tag -- all four
    # attach to the impersonal "Het is {item}." pattern (verified: "Het
    # is zonnig."/"Het is bewolkt."/"Het is koud (vandaag)."/"Het is
    # warm (vandaag)." -- dropping the optional "vandaag" leaves a
    # still-valid standalone sentence for koud/warm).
    if t in {"zonnig", "bewolkt", "koud", "warm"}: semantic.append("weather_adj")
    if token in {"zonnig", "bewolkt", "koud", "warm"}: semantic.append("weather_adj_pure")
    # Broader 8-member recognition-only tag (adds regent, a verb, plus
    # weer/weerbericht/wandeling nouns) -- safe for bare-word MC/
    # listen_select/translation only, NOT a shared generative frame:
    # "regent" is impersonal "Het regent." with no adjective slot at
    # all, a different sentence shape from the weather_adj members.
    if t in {"zonnig", "bewolkt", "koud", "warm", "regent", "weer", "weerbericht", "wandeling"}:
        semantic.append("weather_vocab")
    if token in {"zonnig", "bewolkt", "koud", "warm", "regent", "weer", "weerbericht", "wandeling"}:
        semantic.append("weather_vocab_pure")
    # Unit 20 (buying clothes): broad 6-member recognition-only tag
    # (bare-word MC/listen_select/matching_pairs) -- "schoenen" is always
    # plural with no article, "maat"/"kleur" don't collocate with the
    # other 4's "Ik zoek een {item}." shape, so this stays recognition-
    # only, never a shared generative frame.
    if t in {"jas", "trui", "broek", "schoenen", "maat", "kleur"}:
        semantic.append("clothing_noun")
    # Narrower 3-member generative tag: jas/trui/broek are each
    # grammatical after "een" as a singular countable noun -- verified
    # directly ("Ik zoek een jas."); "schoenen" is excluded (always
    # plural, "Ik zoek een schoenen" is ungrammatical).
    if t in {"jas", "trui", "broek"}: semantic.append("clothing_item_singular")
    # Only 2 real colors taught in this unit -- kept out of
    # multiple_choice/listen_select/matching_pairs (need >=3 distinct),
    # used only in word_order/translation/fill_in_blank. Both take the
    # identical "in het {item}" pattern regardless of the color word's
    # own gender, per this unit's own teaching note.
    if t in {"zwart", "blauw"}: semantic.append("color")
    # "klein"/"groot" are already-existing unit14 comparative-lesson
    # adjectives (small/big), reused here bare (not comparative) in this
    # unit's own "Het is te {item}." pattern -- verified directly
    # ("Het is te klein."/"Het is te groot."). Only 2 members, translation/
    # word_order only, same discipline as several sibling 2-member tags
    # above (equal_adj, symptom_zijn, etc.).
    if t in {"klein", "groot"}: semantic.append("size_too_adj")
    # Unit 21 (expressing feelings): 5-member generative adjective tag --
    # all five are verified safe in BOTH "Ik ben {item}." and "Hij voelt
    # zich {item}." (the real content uses "zenuwachtig"/"blij" in both
    # shapes, and "trots" is grammatically identical: "Ik ben trots."/
    # "Hij voelt zich trots." are both natural Dutch), plus the question
    # frame "Waarom ben je {item}?" (real content's own lesson02 teaches
    # exactly this shape for "blij").
    if t in {"blij", "verdrietig", "boos", "zenuwachtig", "trots"}:
        semantic.append("feeling_adj")
    # Unit 22 (calling and texting): 4-member recognition-only tag
    # spanning noun/verb ("sms" is a noun, the rest are verb infinitives)
    # -- no shared generative frame (each collocates differently: "Ik bel
    # je."/"Ik stuur een sms."/"Ik hoor je niet goed."/"Ik moet je iets
    # vertellen." are all structurally different), same discipline as
    # unit11's plan_vocab and unit17's work_vocab.
    if t in {"bellen", "sms", "horen", "vertellen"}: semantic.append("communication_word")
    # Unit 23 (money and paying): 5-member recognition-only verb tag
    # (bare infinitives), also verified safe together in the polite
    # request frame "Mag ik {item}?" -- every member is a natural answer
    # to "what would you like to do" after "mag ik" (verified: "Mag ik
    # pinnen?"/"Mag ik apart afrekenen?" are both real content; "betalen"/
    # "delen"/"vragen" are grammatically identical bare-infinitive slots
    # in the same "Mag ik ...?" shape even where not the literal unit
    # text).
    if t in {"betalen", "pinnen", "afrekenen", "delen", "vragen"}:
        semantic.append("payment_verb")
    # 3-member noun tag -- rekening/wisselgeld/totaal are the three core
    # money nouns taught in this unit, recognition-only (each takes a
    # different article/context: "de rekening", "het wisselgeld", "in
    # totaal"), safe for bare-word MC/listen_select (exactly meets the
    # >=3 distinct-gloss floor).
    if t in {"rekening", "wisselgeld", "totaal"}: semantic.append("payment_noun")
    # Exact-case _pure siblings (2026-07-29 en-nl _pure wave) so recognition slots
    # never surface a capitalized sentence-initial variant (Rekening/Totaal from
    # unit23's bill-reading label) as a second correct-looking MC option, and the
    # blanket-_cat-derived clothing_fit / room_count_question pools shed their
    # contaminants (the cap "Past"; the unit02 numbers drie/twee). token = exact case.
    if token in {"rekening", "wisselgeld", "totaal"}: semantic.append("payment_noun_pure")
    if token in {"is", "past"}: semantic.append("clothing_fit_pure")
    if token in {"appartement", "kamers", "slaapkamers"}: semantic.append("room_count_question_pure")
    # unit22 phone-call _pure tags: exact-case unit22 forms only, so match_union's
    # [noun,verb,pronoun,preposition] filter can't pull the unit01 homographs
    # met(with)/ik/spreek(speak) or unit01-14 function words (Ik/Kun/herhalen/je)
    # into the matching pool alongside their unit22 senses. 2026-07-29.
    if token in {"Met", "U", "spreekt", "wie"}: semantic.append("phone_identity_pure")
    if token in {"Spreek", "hoor"}: semantic.append("phone_clarification_pure")
    # route_map_pure: the real route-map labels only. route_map is a blanket _cat
    # tag on unit09's route_op_de_kaart lesson, so it also stamps unit01/08 place
    # nouns (station/bibliotheek/buurtkaart/bank/supermarkt) and function words onto
    # the pool feeding unit09's 5 route MC/listen templates → false "route word"
    # feedback + ambiguous options. Exact-token narrow to {route, START, DOEL}
    # (drops the cap-dup 'Route' too). 2026-07-30.
    if token in {"route", "START", "DOEL"}: semantic.append("route_map_pure")
    # A2 unit 27 (huisarts/health: a doctor's visit), added 2026-07-07 by the
    # practice-template authoring pass. Narrow generative tags, each verified
    # against the real lesson content before use in a shared frame:
    # - medical_professional (2 members: huisarts, dokter) is safe in "Ik wil
    #   graag een afspraak maken bij de {item}." -- "bij de huisarts" is the
    #   real unit text; "bij de dokter" is equally natural informal Dutch
    #   (same register as "bij de tandarts").
    if t in {"huisarts", "dokter"}: semantic.append("medical_professional")
    # - symptom_word (3 members: hoofdpijn, koorts, pijn) is safe in "Ik heb
    #   {item}." -- all three are singular/mass nouns for a specific
    #   complaint, verified natural in this exact frame ("Ik heb hoofdpijn."/
    #   "Ik heb koorts."/"Ik heb pijn." are all idiomatic). "klachten" is
    #   deliberately excluded -- it's the plural umbrella term the doctor
    #   asks about (Wat zijn uw klachten?), not something a patient states
    #   this way.
    if t in {"hoofdpijn", "koorts", "pijn"}: semantic.append("symptom_word")
    # - visit_noun (9 members, mixed concrete nouns from across this unit) is
    #   recognition-only (bare-word multiple_choice/listen_select/
    #   matching_pairs) -- no shared generative frame needed, same discipline
    #   as unit11's plan_vocab/unit17's work_vocab/unit22's
    #   communication_word.
    if t in {"huisarts", "afspraak", "reden", "bezoek", "klachten", "griepje", "recept", "pillen", "dokter"}:
        semantic.append("visit_noun")
    # Casefolded above, so "Huisarts" (the capitalized dialogue-speaker-label
    # variant introduced in lesson06) is a case-duplicate of "huisarts" under
    # this tag -- harmless for existing bare-word MC/listen_select slots, but
    # unsafe for matching_pairs (could draw both cases as if they were two
    # different pairs). Additive exact-case tag for matching_pairs use only,
    # same convention as every other _pure tag in this file.
    if token in {"huisarts", "afspraak", "reden", "bezoek", "klachten", "griepje", "recept", "pillen", "dokter"}:
        semantic.append("visit_noun_pure")
    # - reassurance_adj (2 members: ernstig, vervelend) is safe in both
    #   "Het is niet {item}." and "Is het {item}?" -- verified: "Het is niet
    #   ernstig."/"Is het ernstig?" are the real unit text; "Het is niet
    #   vervelend."/"Is het vervelend?" are equally grammatical standalone
    #   sentences (a different but coherent meaning, "it's not
    #   annoying"/"is it annoying?"), not a factual claim this drill needs to
    #   preserve. Only 2 members -- kept out of multiple_choice/listen_select
    #   (need >=3), translation/word_order only.
    if t in {"ernstig", "vervelend"}: semantic.append("reassurance_adj")
    # - separable_health_verb (2 members: innemen, terugkomen, both real
    #   infinitives from this unit's own grammar-note teaching card) is
    #   recognition-only; kept out of multiple_choice/listen_select (need
    #   >=3), used only in matching_pairs (exactly meets the >=2
    #   distinct-token floor).
    if t in {"innemen", "terugkomen"}: semantic.append("separable_health_verb")
    # A2 unit 28 (probleem melden/housing: reporting a maintenance issue),
    # added 2026-07-07 by the same practice-template authoring pass.
    # - housing_report_noun (6 members) is recognition-only (bare-word
    #   multiple_choice/listen_select/matching_pairs), same discipline as
    #   visit_noun above -- these six don't share one generative frame
    #   (verwarming/appartement especially must never be mixed into the same
    #   fillable slot, see heating_word below).
    if t in {"probleem", "verwarming", "monteur", "melding", "contact", "woningcorporatie"}:
        semantic.append("housing_report_noun")
    # Casefolded above, so "Woningcorporatie" (the capitalized dialogue-
    # speaker-label variant introduced in lesson06) is a case-duplicate of
    # "woningcorporatie" under this tag -- same convention as visit_noun_pure
    # above, additive exact-case tag for matching_pairs use only.
    if token in {"probleem", "verwarming", "monteur", "melding", "contact", "woningcorporatie"}:
        semantic.append("housing_report_noun_pure")
    # - heating_word (1 member: verwarming) is the ONLY noun from this unit
    #   safe in "De {item} werkt niet." -- "appartement" is also a noun
    #   taught in the same lesson (de_verwarming_werkt_niet) but "De
    #   appartement werkt niet" is nonsensical (an apartment doesn't "work"),
    #   so it is deliberately excluded from this narrower tag even though
    #   both share the broader housing_report_noun/lesson-category tags.
    if t == "verwarming": semantic.append("heating_word")
    # - technician_word (1 member: monteur) is safe in "Wanneer komt de
    #   {item} langs?" -- the only noun this question can take.
    if t == "monteur": semantic.append("technician_word")
    # - arrival_time_word (1 member: morgenochtend) is safe in "De monteur
    #   komt {item} langs." -- "gisteravond" (yesterday evening) is
    #   grammatically parseable there but temporally contradicts the present-
    #   tense near-future "komt", so it is deliberately excluded.
    if t == "morgenochtend": semantic.append("arrival_time_word")
    # - housing_time_adverb (3 members: morgenochtend, gisteravond, thuis) is
    #   recognition-only (bare-word MC/listen_select/matching_pairs) --
    #   mixed time/location adverbs with no shared frame, same discipline as
    #   unit22's communication_word.
    if t in {"morgenochtend", "gisteravond", "thuis"}: semantic.append("housing_time_adverb")
    # - duration_number (5 members: drie, twee, negen, elf, vierentwintig --
    #   every number token actually introduced across units 27-28's own
    #   realization files) is safe in "Wij nemen binnen {item} uur contact
    #   met u op." (within X hours) and as a bare-word MC/listen_select tag
    #   (5 distinct glosses). Deliberately NOT the broader shared "number"
    #   tag: that pool also includes a same-course token "s" (a genuine,
    #   unrelated pre-existing tagging quirk from unit25's auto's/possessive
    #   marker, still being authored by a parallel session as of this
    #   writing) whose gloss is nonsensical here -- this narrower, unit
    #   27/28-local tag avoids depending on that pool's correctness.
    if t in {"drie", "twee", "negen", "elf", "vierentwintig"}: semantic.append("duration_number")
    # "april" is introduced in the same lesson as the ordinal-number teaching
    # cards (the lesson combines "de vijfde april" -- ordinal + month), so
    # the blanket lesson_categories["rangtelwoorden"] tag above wrongly also
    # marks the month noun itself as an ordinal_number candidate. Every
    # ordinal_number-slot frame in this unit is literally "... {item}
    # april." -- if "item" could resolve to "april", that generates
    # self-referential output ("Het is de april april."), same bug class as
    # the station/hospital self-reference catches elsewhere in this file.
    # Strip the blanket tag from any genuine month noun.
    if "month" in semantic and "ordinal_number" in semantic:
        semantic = [s for s in semantic if s != "ordinal_number"]

    # A2 units 24-26 (gemeente/meningen/bankrekening) practice-template
    # tags, added 2026-07-07. Each tag below is a brand-new, uniquely-named
    # string assigned to exactly the listed tokens -- unlike the blanket
    # lesson_categories tags above (contaminated across every token in a
    # lesson, including unrelated pronouns/particles), these are narrow and
    # safe to use directly as a generative-frame or fill_in_blank slot
    # constraint. Every generative frame below was checked against this
    # unit's real realization content for grammaticality (reversed-pairing
    # convention already established by unit14's comparative_adj/unit21's
    # feeling_adj: a member need not be literally combined with the frame
    # in the source text as long as it's grammatically identical there).
    #
    # Unit 24 (gemeente/bureaucracy).
    if t in {"paspoort", "huurcontract", "geboorteakte", "afspraak", "adres",
             "gemeente", "documenten", "overheid"}:
        semantic.append("gemeente_vocab_noun")
    # 3-member subset verified safe in "Mag ik uw {item} zien?" -- directly
    # attested for paspoort in the real content's own matching_pairs pair
    # ("Mag ik uw paspoort zien?" -> "May I see your passport?"); huurcontract/
    # geboorteakte are grammatically identical objects of the same verb.
    if t in {"paspoort", "huurcontract", "geboorteakte"}:
        semantic.append("gemeente_doc_noun")
    if t in {"inschrijven", "schikken", "regelen", "ontvangt"}:
        semantic.append("gemeente_verb")
    # Single-member tags (exactly one token each, by construction) -- always
    # safe for a fill_in_blank slot regardless of the rest of the course's
    # lexeme pool, matching this unit's own real fill_in_blank exercises.
    if t == "schikken":
        semantic.append("gemeente_schikken_single")
    # Exact-case check (not casefolded): unit27's own realization separately
    # introduces the capitalized sentence-initial "Huisarts" (a different
    # lexeme, same case-duplicate class documented throughout this file --
    # see "weekday"/"weekday_pure") -- casefolding here would silently widen
    # this tag to 2 members and break the single-candidate guarantee.
    if token == "huisarts":
        semantic.append("gemeente_huisarts_single")
    if t == "regelen":
        semantic.append("gemeente_regelen_single")

    # Unit 25 (meningen/opinions).
    if t in {"fietspad", "mening", "idee", "kant", "voetgangers", "fietsers",
             "auto", "straat", "ruimte"}:
        semantic.append("opinion_noun")
    # 5-member generative adjective tag verified safe in "Volgens mij is het
    # fietspad {item}." -- gevaarlijk/smal are directly attested there;
    # veiliger/breder/duur are grammatically identical predicate adjectives
    # in the same slot (reversed-pairing convention, see module note above).
    if t in {"gevaarlijk", "smal", "veiliger", "breder", "duur"}:
        semantic.append("opinion_adj")
    # Exact-case (not casefolded): unrelated earlier units already introduce
    # capitalized "Denk" (unit12, "Denk aan de eindpositie") and "Vind"
    # (unit13, "Vind je dit lekker?") as separate lexemes -- casefolding
    # would silently pull those in as case-duplicates of this unit's own
    # lowercase "denk"/"vind", same class as the huisarts fix above.
    if token in {"vind", "snap", "moeten", "wordt", "denk", "vindt", "bespaart"}:
        semantic.append("opinion_verb")
    if t == "gedeeltelijk":
        semantic.append("opinion_gedeeltelijk_single")
    if t == "veiliger":
        semantic.append("opinion_veiliger_single")

    # Unit 26 (bankrekening/banking).
    if t in {"bankrekening", "betaalrekening", "salaris", "werkgever",
             "identiteitsbewijs", "bankpas", "app"} or token == "Medewerker":
        semantic.append("bank_vocab_noun")
    # 2-member generative tag verified safe in "Ik wil graag een {item}
    # openen." -- both are directly attested opening this way in the real
    # content (lesson01/lesson02).
    if t in {"bankrekening", "betaalrekening"}:
        semantic.append("bank_account_noun")
    # Exact-case (not casefolded): this unit's own lesson02 grammar note
    # separately introduces capitalized sentence-initial "Storten" ("Storten
    # is de infinitief van stort.") as a case-duplicate of lowercase
    # "storten" -- same class as the huisarts/opinion_verb fixes above;
    # casefolding would give this tag a near-duplicate-gloss ("To deposit"
    # vs "to deposit") second member, confusing in a multiple_choice option
    # list even though it's technically the same word.
    if token in {"openen", "storten", "gebruikt", "geopend", "bankieren"}:
        semantic.append("bank_verb")
    if t == "openen":
        semantic.append("bank_openen_single")
    if t == "nodig":
        semantic.append("bank_nodig_single")

    # Unit 29 (hobbies) practice-template tags, added 2026-07-09. 6-member
    # bare-infinitive recognition-only tag (no shared generative frame --
    # each collocates differently, same discipline as unit10's
    # routine_verb_infinitive/unit17's work_vocab).
    if t in {"lezen", "sporten", "koken", "luisteren", "tekenen", "gamen"}:
        semantic.append("hobby_verb")
    # 4-member frequency-adverb tag, verified safe generatively in
    # "Ik lees {item} een boek."/"Ik sport {item} op zaterdag."/"Ik kook
    # {item} voor vrienden." (all four grammatical in each frame -- this is
    # NOT the fill_in_blank ambiguity trap the real unit29 realization
    # flagged, since every practice template here uses translation/
    # word_order with the ENGLISH side disambiguating which word is meant,
    # never a bare Dutch fill_in_blank on this pool).
    if t in {"altijd", "vaak", "soms", "nooit"}: semantic.append("freq_adverb")
    # Single-member tags (by construction, exactly one token each) -- safe
    # fill_in_blank slots regardless of the rest of the course's pool,
    # matching this unit's own real fill_in_blank resolutions (blanking
    # boek/vrienden/vrije rather than the interchangeable hobby verbs/
    # frequency adverbs, per its own review.notes).
    if t == "boek": semantic.append("hobby_boek_single")
    if t == "vrienden": semantic.append("hobby_vrienden_single")
    if t == "vrije": semantic.append("hobby_vrije_single")

    # Unit 30 (appearance) practice-template tags, added 2026-07-09. 4-member
    # hair-color tag (bare form, reusing unit20's "zwart"), verified safe in
    # "Lotte heeft lang {item} haar." -- all four grammatical there ("lang
    # blond/bruin/grijs/zwart haar").
    if t in {"blond", "bruin", "grijs", "zwart"}: semantic.append("hair_color_adj")
    # 3-member eye-color tag (INFLECTED -e forms, since "ogen" is plural and
    # takes agreement per this unit's own ogen_agreement_note), verified safe
    # in "Lotte heeft {item} ogen." -- reuses unit13's already-classified
    # "blauwe".
    if t in {"blauwe", "bruine", "groene"}: semantic.append("eye_color_adj")
    # 2-member tags -- kept out of multiple_choice/listen_select (need >=3),
    # translation/word_order only, matching this unit's own review.notes
    # (blanking lang/kort or oud/jong directly is genuinely ambiguous with
    # no in-frame disambiguation, the same risk class already resolved for
    # unit14/unit20's sibling 2-member tags).
    if t in {"lang", "klein"}: semantic.append("height_adj")
    # Exact-case (not casefolded): this unit's own lesson01 grammar note
    # separately introduces capitalized sentence-initial "Oud" ("Oud kan een
    # precies aantal jaren betekenen...") as a case-duplicate of lowercase
    # "oud" -- same class as the huisarts/opinion_verb fixes elsewhere in
    # this file; casefolding would give this tag a near-duplicate-gloss
    # ("Old" vs "old") second member of the same word, not a real 3rd
    # candidate.
    if token in {"oud", "jong"}: semantic.append("age_adj")
    if t == "ogen": semantic.append("appearance_ogen_single")
    if t == "eruit": semantic.append("appearance_eruit_single")
    # Widen the already-established "person_name" tag (unit01 area) to
    # include this unit's two new named characters -- additive only, does
    # not change what "person_name" already matched, same convention as the
    # weekday_pure/travel_noun_pure "_pure" tags elsewhere in this file.
    if token in {"Nina", "Opa"}: semantic.append("person_name")

    # Unit 31 (animals) practice-template tags, added 2026-07-09. 4-member
    # pet-noun tag, verified safe generatively in "Ik heb een {item}." (all
    # four grammatical there -- safe for translation, where the ENGLISH side
    # disambiguates; NOT used in any bare Dutch fill_in_blank, matching this
    # unit's own review.notes resolution of the identical risk).
    if t in {"hond", "kat", "vis", "vogel"}: semantic.append("pet_noun")
    # 4-member plural tag, verified safe in "Ik houd van {item}." (all four
    # grammatical: "Ik houd van honden/katten/vissen/vogels.").
    if t in {"honden", "katten", "vissen", "vogels"}: semantic.append("pet_noun_plural")
    # 3-member bare-infinitive recognition-only tag (different collocations
    # per this unit's own doc: uitlaten/eten geven/spelen met each take
    # different objects/prepositions) -- same discipline as hobby_verb above.
    # Exact-case (not casefolded): this unit's own lesson02 grammar note
    # separately introduces capitalized sentence-initial "Uitlaten" as a
    # case-duplicate of lowercase "uitlaten", same class as the age_adj fix
    # above.
    if token in {"uitlaten", "geven", "spelen"}: semantic.append("pet_care_verb")
    # Single-member tags, reusing already-classified tokens (elke/van) --
    # additive, does not disturb either token's existing semantic tags.
    # Exact-case (not casefolded): earlier units already introduce
    # capitalized sentence-initial "Elke" (unit14 area) and "Van" (unit14
    # area) as separate lexemes -- casefolding would silently widen each
    # tag to 2 members, same class as the age_adj/pet_care_verb fixes above.
    if token == "elke": semantic.append("animal_elke_single")
    if token == "van": semantic.append("animal_van_single")

    # Unit 32 (sports) practice-template tags, added 2026-07-09. 4-member
    # sport-noun tag (hardlopen/zwemmen classified as nouns -- see their
    # NL_GLOSSES comment), verified safe generatively in "Ik houd van
    # {item}."/"Ik doe aan {item}." (all four grammatical in both frames,
    # translation-only per this unit's own review.notes, which explicitly
    # avoided any bare Dutch fill_in_blank on this exact pool).
    # Exact-case (not casefolded): this unit's own lesson04 grammar note
    # separately introduces capitalized subject-position "Hardlopen"
    # ("Hardlopen is niet scheidbaar...") as a case-duplicate of lowercase
    # "hardlopen", same class as the age_adj/pet_care_verb fixes above.
    if token in {"voetbal", "yoga", "hardlopen", "zwemmen"}: semantic.append("sport_noun")
    if t == "dicht": semantic.append("sport_dicht_single")

    # Unit 33 (transportation) practice-template tags, added 2026-07-09.
    # 3-member transport-noun tag, verified safe in "Ik reis met de
    # {item}." (all three grammatical: "met de trein/fiets/auto").
    if t in {"trein", "fiets", "auto"}: semantic.append("transport_noun")
    # 3-member conjugated-verb recognition-only tag (different subjects,
    # no shared frame) -- same discipline as pet_care_verb above.
    if t in {"fietst", "rijdt", "reist"}: semantic.append("transport_verb")
    # Broader mixed noun/verb recognition-only pool for a bigger
    # matching_pairs finale, same combined-slot-preset technique as
    # a2_unit24's gemeente_noun_or_verb.
    if t in {"trein", "fiets", "auto", "fietst", "rijdt", "reist", "lopen", "reizen"}:
        semantic.append("transport_vocab")
    # Exact-case (not casefolded): "alstublieft" is also introduced in A2
    # unit24 (gemeente) as both lowercase and a capitalized sentence-initial
    # "Alstublieft" -- casefolding here would pull in both the a2-course
    # capitalized variant AND (harmlessly, since A1/A2 are separate courses
    # per AUTHORING_GUIDE #18) widen the a1-course pool with a same-course
    # case-duplicate if this unit's own dialogue ever capitalizes it.
    if token == "alstublieft": semantic.append("vervoer_alstublieft_single")

    # A2 unit 73 (sollicitatiegesprek/job interview), added 2026-07-10.
    # Recognition-only employment vocabulary spanning nouns/adjectives/verbs
    # from the job-ad and interview lessons. The narrower tags below carry
    # any shared-frame assumptions.
    if t in {"vacature", "solliciteren", "medewerker", "sollicitatiegesprek",
             "ervaring", "vrijwilliger", "vaardigheid", "vaardigheden",
             "beschikbaar", "werktijden", "klantcontact", "gesprek"}:
        semantic.append("job_interview_vocab")
    # Exact-case tag for matching_pairs: Ervaring/Werktijden appear as
    # sentence-initial/heading variants in the reading lesson and should not
    # be drawn alongside their lowercase case-duplicates.
    if token in {"vacature", "solliciteren", "medewerker", "sollicitatiegesprek",
                 "ervaring", "vrijwilliger", "vaardigheid", "vaardigheden",
                 "beschikbaar", "werktijden", "klantcontact", "gesprek"}:
        semantic.append("job_interview_vocab_pure")
    # Two singular role/position nouns safe after "een" in the application
    # context: "een administratief medewerker" and "een vrijwilliger".
    if t in {"medewerker", "vrijwilliger"}:
        semantic.append("job_role_noun")
    # Skills/experience nouns used in "Ik heb {item}" frames. "ervaring" is
    # mass-singular; "vaardigheden" is plural, but both are directly attested
    # in this unit's "Ik heb ..." sentences.
    if t in {"ervaring", "vaardigheden"}:
        semantic.append("job_have_noun")
    # Availability/time vocabulary is recognition-only; beschikbaar is an
    # adjective while werktijden is a plural noun.
    if t in {"beschikbaar", "werktijden"}:
        semantic.append("availability_vocab")
    if t == "beschikbaar":
        semantic.append("job_beschikbaar_single")
    if t == "klantcontact":
        semantic.append("job_klantcontact_single")

    # A2 unit 74 (reisvertraging/travel disruption), added 2026-07-11.
    # Recognition-only travel-disruption vocabulary; no practice-template
    # pack exists yet for this unit (only through a2_unit28.yaml), so no
    # finer generative-frame tags are added -- add those alongside a future
    # practice-template authoring pass instead, same discipline as this
    # file's own note for unit73 above.
    if t in {"seinstoring", "aansluiting", "servicebalie", "verbinding",
             "intercity", "mededeling", "reisplanner", "spoor"}:
        semantic.append("travel_disruption_vocab")
    if t in {"rijden", "omreizen", "adviseren", "raadplegen", "weten"}:
        semantic.append("travel_disruption_verb")

    # A2 unit 75 (schermtijd/screen time and online habits), added
    # 2026-07-11. Recognition-only, same discipline as unit74 above.
    if t in {"scherm", "telefoon", "media", "schermtijd", "gewoonte", "apps"}:
        semantic.append("screen_time_vocab")
    if t in {"chat", "doorbrengen", "wegleggen", "probeer"}:
        semantic.append("screen_time_verb")

    # A2 unit 76 (drukke week/describing a weekly schedule), added
    # 2026-07-11. Recognition-only, same discipline as unit74 above.
    if t in {"rooster", "cursus", "volgorde", "agenda", "verschil"}:
        semantic.append("weekly_schedule_vocab")
    # 3-member sequencing-connector tag, verified safe generatively in
    # "{item} werk ik, {item2} sport ik." style chaining -- kept
    # recognition-only here since no practice-template pack exists yet to
    # consume it as a generative frame (see the module-docstring note).
    if t in {"eerst", "daarna", "slotte"}: semantic.append("sequence_connector")

    # A2 unit 77 (iets terugbrengen/shopping complaint and returns), added
    # 2026-07-11. Recognition-only, same discipline as unit74 above.
    if t in {"koptelefoon", "linkerkant", "bonnetje", "retourbeleid",
             "artikel", "aankoop", "exemplaar"}:
        semantic.append("shopping_complaint_vocab")
    # Exact-case (not casefolded) sibling for matching_pairs, added
    # 2026-07-11 alongside the practice-template pass: the casefolded
    # "shopping_complaint_vocab" pool above genuinely contains both
    # lowercase "retourbeleid" (lesson04 vocab card) and capitalized
    # "Retourbeleid" (lesson05 reading's heading), both meaning "the
    # return policy" with an identical English gloss -- fine for
    # bare-word multiple_choice/listen_select (one word shown at a
    # time), but a real risk for matching_pairs, which could sample
    # both as two simultaneous cards that look like duplicate pairs.
    # Restricting to the exact-case lowercase token excludes the
    # capitalized duplicate, same class of fix as this file's existing
    # job_interview_vocab_pure/housing_report_noun_pure precedent.
    if token in {"koptelefoon", "linkerkant", "bonnetje", "retourbeleid",
                 "artikel", "aankoop", "exemplaar"}:
        semantic.append("shopping_complaint_vocab_pure")
    if t in {"ruilen", "terugkrijgen", "terugbrengen", "regel"}:
        semantic.append("shopping_complaint_verb")

    # Single-member render_frame-safe tags for units 74-77, added 2026-07-11
    # alongside the first docs/content/practice/en-nl/a2_unit7[4-7].yaml
    # practice-template pass (the four broader recognition-only tags just
    # above were deliberately left bare-word-only when this file was first
    # extended for these units, per this module's own docstring note -- this
    # is that deferred follow-up). Each tag below has EXACTLY one member, so
    # it can safely anchor a fixed multi-word frame (word_order/translation/
    # fill_in_blank via render_frame/slot_text) without the multi-candidate
    # ambiguity §17 warns about -- no grammaticality-across-candidates
    # judgment call is needed when there is only one candidate. Casefold
    # matching (`t == ...`) is used throughout, deliberately unifying a
    # token with its own sentence-initial capitalized variant where one
    # exists in this unit (verified by hand, not guessed): "daarna"/"Daarna"
    # (unit76 lesson02 mid-sentence vs. lesson06 grammar-note sentence-
    # initial, identical meaning) and "retourbeleid"/"Retourbeleid" (unit77
    # lesson04 vocab card vs. lesson05 reading's heading, identical
    # meaning) -- same safe-reuse pattern as this file's existing Ervaring/
    # Werktijden precedent, not a new risk class. Every other token below
    # was grepped against the full NL_GLOSSES dict to confirm no unrelated
    # capitalized homograph exists that casefolding could accidentally pull
    # in.
    if t == "vertraging": semantic.append("reisvertraging_vertraging_single")
    if t == "seinstoring": semantic.append("reisvertraging_seinstoring_single")
    if t == "aansluiting": semantic.append("reisvertraging_aansluiting_single")
    if t == "verbinding": semantic.append("reisvertraging_verbinding_single")
    if t == "spoor": semantic.append("reisvertraging_spoor_single")

    if t == "scherm": semantic.append("schermtijd_scherm_single")
    if t == "telefoon": semantic.append("schermtijd_telefoon_single")
    if t == "chat": semantic.append("schermtijd_chat_single")
    if t == "schermtijd": semantic.append("schermtijd_schermtijd_single")
    if t == "doorbrengen": semantic.append("schermtijd_doorbrengen_single")
    if t == "gewoonte": semantic.append("schermtijd_gewoonte_single")
    if t == "wegleggen": semantic.append("schermtijd_wegleggen_single")

    if t == "rooster": semantic.append("drukkeweek_rooster_single")
    if t == "daarna": semantic.append("drukkeweek_daarna_single")
    if t == "slotte": semantic.append("drukkeweek_slotte_single")
    if t == "verschil": semantic.append("drukkeweek_verschil_single")
    if t == "agenda": semantic.append("drukkeweek_agenda_single")
    if t == "volgorde": semantic.append("drukkeweek_volgorde_single")

    if t == "koptelefoon": semantic.append("terugbrengen_koptelefoon_single")
    if t == "bonnetje": semantic.append("terugbrengen_bonnetje_single")
    if t == "retourbeleid": semantic.append("terugbrengen_retourbeleid_single")
    if t == "ruilen": semantic.append("terugbrengen_ruilen_single")
    if t == "artikel": semantic.append("terugbrengen_artikel_single")
    if t == "terugkrijgen": semantic.append("terugbrengen_terugkrijgen_single")

    # A1 volume batch (units 34-42 / 49-72), added 2026-07-22. Unlike the
    # per-token `if t == ...` blocks above, these are derived from the
    # lesson_key + part of speech, because 33 units x ~25 content words is
    # far past the point where hand-listing every token stays reviewable --
    # and the pools these produce are exactly "the content words THIS unit
    # introduces", which is the one scope `generate_checkpoint()` can use
    # (it calls `_material()` with only the unit's own lesson ids).
    # Proper nouns, numerals and function words are excluded by
    # NL_A1_VOLUME_VOCAB_POS; sentence-initial capitals cannot appear at all,
    # because NL_CITATION_FORMS folds them away before classification.
    volume_slug = NL_A1_VOLUME_UNIT_SLUGS.get(".".join(lesson_key.split(".")[1:3]))
    if (
        volume_slug is not None
        and (volume_slug, token) not in NL_A1_VOLUME_TAG_EXCLUSIONS
        and (not token[:1].isupper() or token in NL_A1_VOLUME_ALWAYS_CAPITALIZED)
    ):
        volume_pos = nl_part_of_speech(token)
        if volume_pos in NL_A1_VOLUME_VOCAB_POS:
            semantic.append(f"{volume_slug}_vocab")
        if volume_pos == "noun":
            semantic.append(f"{volume_slug}_noun")
    anchor_slug = NL_A1_VOLUME_SINGLE_ANCHORS.get(token)
    if anchor_slug is not None:
        semantic.append(f"{anchor_slug}_{token}_single")

    tags: dict[str, object] = {"semantic": list(dict.fromkeys(semantic))}
    if t in {"jij", "je"}: tags["register"] = "informal"
    elif t == "u": tags["register"] = "polite"
    # de/het gender and singular/plural for the A1 volume batch's nouns --
    # not recoverable from the English gloss, and required before a pack
    # author can write a grammatical frame around a slot.
    if token in NL_A1_VOLUME_ARTICLES:
        tags["article"] = NL_A1_VOLUME_ARTICLES[token]
        tags["number"] = "singular"
    elif token in NL_A1_VOLUME_PLURALS:
        tags["article"] = "de"
        tags["number"] = "plural"
    return tags


# Per-(unit, token) gloss / POS overrides -- the homograph-disambiguation
# mechanism ported 2026-08-01 from the sibling `backfill_lexemes_nl_en.py`
# (its NL_UNIT_GLOSS_OVERRIDES / NL_UNIT_POS_OVERRIDES, applied the same way).
#
# WHY this exists (and why the module's older "no second gloss" doctrine is
# superseded only HERE, deliberately): `NL_GLOSSES` / `nl_part_of_speech()`
# key a Dutch token to ONE global (gloss, POS). A genuine homograph re-taught
# in a later unit in a different sense (e.g. `regel` = the verb "arrange"
# everywhere, but the NOUN "the rule" in b1_unit06) therefore ships the wrong
# unit's sense as the learner-facing gloss -- which, via slot_gloss, becomes
# the graded MC/translate answer. The prior fix pattern (exclude the token
# from the generative tag, or bake it literally) cannot help a slot where the
# homograph is the SOLE candidate -- b1_unit06 `regel` in translate.002 -- so
# a per-occurrence override is the only non-destructive fix. Keyed by
# (realization_path.stem, token); the stem is the unit file's basename, e.g.
# "b1_unit06_verplichtingen". Overrides win over the global maps; every other
# token is untouched, so this is additive and each entry is a hand-verified,
# unit-scoped decision. English-gloss values are authorable here (the learner
# is an English speaker); Dutch-side sense confirmation is not needed.
NL_UNIT_GLOSS_OVERRIDES: dict[tuple[str, str], str] = {
    # b1_unit06 teaches the noun "de regel" (nl.b1.unit06.lesson06.teach.de_regel);
    # global `regel` = verb "arrange (with ik, part of regelen)". Without this,
    # translate.002 cued "the rule" and graded the correct answer "regel" wrong.
    ("b1_unit06_verplichtingen", "regel"): "the rule",
    # --- 2026-08-01 homograph sweep (each verified against the unit's own
    #     teaching text; keyed to the FIRST sorted introducer per course, which
    #     is where the single course-scoped lexeme is created). ---
    # a1_unit54 "de regel" sign ("Ik lees de regel", matching_pair regel->rule);
    # global says verb "arrange".
    ("a1_unit54_zwembad", "regel"): "the rule",
    # b1_unit01 teaches the past/unreal copula ("Als ik rijk was, zou ik..."),
    # not the household "was" (afwassen); global says "do the dishes (with ik)".
    ("b1_unit01_hypothetische_situaties", "was"): "was; were (past tense of zijn)",
    # b1_unit05 (reported speech) teaches "asked" ("Hij vroeg of ik kon helpen");
    # global adjective gloss is "early".
    ("b1_unit05_indirecte_rede", "vroeg"): "asked (past tense of vragen)",
    # b1_unit09 teaches the noun ("mensen meer rust nodig hebben" = need more
    # rest); global says verb "rest (imperative, with u)".
    ("b1_unit09_eens_en_oneens", "rust"): "rest; calm",
    # a2_unit25 teaches "true" ("Dat is waar"); global adverb gloss is "where".
    ("a2_unit25_meningen", "waar"): "true",
    # b1 introduces `werk` only as the NOUN (b1_unit01 "Anouk is blij met haar
    # werk", b1_unit06 "druk met werk"); global says verb "work (with ik)". The
    # verb "ik werk" in b1_unit04 is embedded in a relative-clause example, NOT
    # an introduced token, so the b1 lexeme (provenance unit01) is noun-only.
    ("b1_unit01_hypothetische_situaties", "werk"): "work; job",
    # b2_unit08 (synthese) teaches the NOUN "het eten" = the food/meal (its own
    # matching_pair glosses eten->food); global `eten` = verb "to eat". Surfaced
    # by the dictation "Beide bronnen vinden het eten lekker".
    ("b2_unit08_synthese", "eten"): "the food; meal",
    # b2_unit03 (nuance) teaches `best` as a downtoner ADVERB in lesson
    # "afzwakken" ("De film is best goed" = quite good; its own matching_pair
    # glosses best->"quite / pretty"); global `best` = superlative adjective.
    ("b2_unit03_nuance", "best"): "quite; pretty",
# C1 per-unit homograph / sense overrides (first C1 introducer of each token).
    # Card 'Een aantrekkelijke binnenstad trekt juist bezoekers.' = 'actually draws visitors'; overlay note: juist marks the result as contrary to the feare
    ('c1_unit01_betoogstructuur', 'juist'): 'actually; on the contrary (contrastive); precisely',
    # Card 'Minder auto's leveren schonere lucht op' = 'Fewer cars ...'; with a countable plural noun English needs 'fewer', global gloss has only 'less'.
    ('c1_unit01_betoogstructuur', 'minder'): 'less; fewer',
    # Card 'Eerst schets ik het probleem; daarna ...' uses eerst as a sequencing adverb (it triggers inversion like daarna/vervolgens); global POS 'particle
    ('c1_unit01_betoogstructuur', 'eerst'): 'first (adverb: before something else)',
    # Card 'tussen de regels door' (overlay: between the lines) uses regels = lines of text, not 'rules'.
    ('c1_unit02_tussen_de_regels', 'regels'): "lines (in 'between the lines')",
    # Unit uses zijn only possessively: 'dat zijn stilte afwijzing betekent', 'Zijn woorden klonken beleefd'; global is the verb 'are'.
    ('c1_unit02_tussen_de_regels', 'zijn'): 'his',
    # Card 'Hij was behoorlijk ontevreden' = past of zijn; global 'do the dishes (with ik)' is the verb wassen, a different word.
    ('c1_unit02_tussen_de_regels', 'was'): 'was (with hij/zij, past of zijn)',
    # Card 'Letterlijk ontkent ze alleen dat het rampzalig was' = only, not 'alone'.
    ('c1_unit02_tussen_de_regels', 'alleen'): 'only; alone',
    # Card 'ontkent ze alleen dat het rampzalig was' (overlay: 'only literally denies'); 'negates' is not the sense taught.
    ('c1_unit02_tussen_de_regels', 'ontkent'): 'denies (with hij/zij)',
    # Card overlay: 'his silence means rejection'; global 'decline' is ambiguous (could read as 'decrease').
    ('c1_unit02_tussen_de_regels', 'afwijzing'): 'rejection',
    # Card 'zonder die rechtstreeks uit te spreken' = uitspreken (voice openly); global cue 'part of afspreken' points to the wrong verb.
    ('c1_unit02_tussen_de_regels', 'spreken'): 'to speak (with uit: to voice, say outright)',
    # Card 'Op zich was het geen ramp' teaches the fixed expression op zich = in itself / as such.
    ('c1_unit02_tussen_de_regels', 'zich'): 'oneself; itself (with op: in itself)',
    # Card weer_voortreffelijk 'Nou, dat is weer voortreffelijk geregeld.' and cue card 'Weer en nou kunnen bij herhaald falen...' teach the adverb 'again' 
    ('c1_unit03_registerbeheersing', 'weer'): 'again',
    # Card ik_zou_het_waarderen 'Ik zou het op prijs stellen als u vandaag reageert.' uses stellen in the fixed expression 'op prijs stellen'; global 'to pr
    ('c1_unit03_registerbeheersing', 'stellen'): "to put; to set (part of a set phrase meaning 'to appreciate')",
    # Same card: prijs occurs only inside the idiom 'op prijs stellen'; literal gloss kept, idiom cue added per idiom-component convention.
    ('c1_unit03_registerbeheersing', 'prijs'): "the price (also in a set phrase meaning 'to appreciate')",
    # Card wellicht 'Wellicht kunt u dit met voorrang bekijken.' uses kunt with formal u; global 'can (with je/jij)' omits the form this unit teaches.
    ('c1_unit03_registerbeheersing', 'kunt'): 'can (with u or jij)',
    # Unit uses the plural noun: 'extra kosten meebrengen', 'een proef de kosten beperkt', 'Enerzijds stijgen de kosten'; global gloss is the verb 'to cost'
    ('c1_unit04_toegeven_en_wegen', 'kosten'): 'costs',
    # Unit uses the noun: 'dat een proef de kosten beperkt', 'een beperkte proef'; global gloss is the verb 'taste (with ik)'.
    ('c1_unit04_toegeven_en_wegen', 'proef'): 'the trial; the pilot',
    # Card 'Dat is tot op zekere hoogte waar.' uses predicative 'waar' = true; global gloss is the adverb 'where'.
    ('c1_unit04_toegeven_en_wegen', 'waar'): 'true',
    # Cards 'voordat het antwoord volgt' and 'voordat de conclusie volgt' mean 'follows / comes next'; global gloss 'takes (a course)' is a different sense.
    ('c1_unit04_toegeven_en_wegen', 'volgt'): 'follows (with hij/zij/het)',
    # Reading text 'wegen ... zwaarder dan het financiële nadeel' uses comparative 'dan' = than; global gloss is 'then'.
    ('c1_unit04_toegeven_en_wegen', 'dan'): 'than (in comparisons)',
    # Global gloss 'stay (with we)' pins a finite plural form; leestekst card uses the infinitive: 'want ik wilde hier blijven'.
    ('c1_unit05_contrafeitelijk_redeneren', 'blijven'): 'to stay; to remain',
    # Card ik_had_beter teaches 'er ... over nadenken' = think about it; the global gloss omits the 'about' sense.
    ('c1_unit05_contrafeitelijk_redeneren', 'over'): 'about; past; after; in (a duration)',
    # Cards use it adverbially: 'Achteraf gezien had ik anders moeten kiezen' (differently) and 'Anders zat ik nu in Amsterdam' (otherwise); global is adjec
    ('c1_unit05_contrafeitelijk_redeneren', 'anders'): 'differently; otherwise',
    # Card voltooid_verleden: 'in de voltooid verleden tijd' = the pluperfect tense; realization pairs gloss it 'pluperfect tense'.
    ('c1_unit05_contrafeitelijk_redeneren', 'tijd'): 'time; tense (grammar)',
    # Card gaten: 'Ik houd het goed in de gaten' (in de gaten houden = keep an eye on); global 'love; am fond of' is the houden van sense, wrong here.
    ('c1_unit06_idioom_en_beeldspraak', 'houd'): 'keep; hold (with ik)',
    # Card koffiedik: 'Dat is koffiedik kijken' uses the infinitive; global 'watch (with we)' pins a finite form and the wrong sense.
    ('c1_unit06_idioom_en_beeldspraak', 'kijken'): 'to look (in an idiom for pure guesswork)',
    # Card collocatie: 'Sommige woorden horen vast bij elkaar' = belong firmly together; global 'surely; definitely' is the modal sense, wrong here.
    ('c1_unit06_idioom_en_beeldspraak', 'vast'): 'firmly; fixed',
    # Card collocatie: 'woorden horen vast bij elkaar' = belong together; global 'to hear' alone misleads.
    ('c1_unit06_idioom_en_beeldspraak', 'horen'): 'to belong (with bij); to hear',
    # Leestekst: 'dat binnen een maand moet beslissen' = within a month; global 'inside' (adverb) is the spatial sense.
    ('c1_unit06_idioom_en_beeldspraak', 'binnen'): 'within (time)',
    # Card register: 'is idioom heel gewoon' = very common/normal; global 'just; simply' (adverb) is the particle sense.
    ('c1_unit06_idioom_en_beeldspraak', 'gewoon'): 'normal; common',
    # Card twee_uitdrukkingen: 'klinkt je verhaal levendig en natuurlijk'; card calque_note: 'natuurlijk Nederlands' — adjective 'natural', not 'of course'.
    ('c1_unit06_idioom_en_beeldspraak', 'natuurlijk'): 'natural',
    # Card collocatie: 'zo'n paar heet een vaste verbinding' = fixed word combination; plain 'the connection' obscures the taught sense.
    ('c1_unit06_idioom_en_beeldspraak', 'verbinding'): 'the combination (a fixed combination = collocation); the connection',
    # Card onderzoek_tegen: 'Het buurtonderzoek spreekt dat tegen' — the unit teaches separable tegenspreken (to contradict); bare 'speaks' misleads.
    ('c1_unit07_bronnen_bemiddelen', 'spreekt'): "speaks (with hij/zij; also the first part of the separable verb for 'contradicts')",
    # Card dat_wil_zeggen: 'Een decibel is een maat voor geluid' — sense is 'measure', not 'size'.
    ('c1_unit07_bronnen_bemiddelen', 'maat'): 'the measure; the size',
    # Card dat_wil_zeggen: 'hoe hard iets klinkt' = how loud something sounds; global 'hard; fast' lacks the loudness sense.
    ('c1_unit07_bronnen_bemiddelen', 'hard'): 'loud (of sound)',
    # Card samenvatting_note: 'dat iets niet bevestigd is' — past participle in a passive; global POS 'noun' is wrong.
    ('c1_unit07_bronnen_bemiddelen', 'bevestigd'): 'confirmed (past participle)',
    # Card volgens_onderzoek/leestekst: 'het onderzoek' refers to a specific study/survey (the buurtonderzoek), countable with article; optional, global 're
    ('c1_unit07_bronnen_bemiddelen', 'onderzoek'): 'the study; research',
    # Unit uses the noun: 'Meer groen, meer lucht, meer rust', 'het groen te houden', 'het laatste stukje groen'; global gloss is the adjective 'green'.
    ('c1_unit08_retorisch_overtuigen', 'groen'): 'greenery; green space',
    # Unit uses the noun: 'meer lucht, meer rust'; 'zorgt voor frisse lucht, rust'; global gloss is the imperative verb 'rest (with u)'.
    ('c1_unit08_retorisch_overtuigen', 'rust'): 'peace and quiet; rest',
    # Card 'een beroep doen op' / 'Ik doe een beroep op u' teaches the idiom sense; global 'the occupation' alone is not the taught sense. Wording keeps it 
    ('c1_unit08_retorisch_overtuigen', 'beroep'): 'appeal (to call upon someone)',
    # Scenario card: 'Omar wil de buurt overtuigen om het groen te houden' = to keep; global leads with 'to love' (which is 'houden van').
    ('c1_unit08_retorisch_overtuigen', 'houden'): 'to keep; to hold',
    # Reading text: 'De buurt heeft steeds minder ruimte'; global 'still (part of nog steeds)' is a different sense.
    ('c1_unit08_retorisch_overtuigen', 'steeds'): 'increasingly; more and more (with minder: less and less)',
    # C1 practice-review gloss fixes (2026-10-10): pin typed answers / drop self-quoting Dutch.
    ('c1_unit01_betoogstructuur', 'maak'): 'make (with ik)',
    ('c1_unit01_betoogstructuur', 'maakt'): 'makes (with hij/zij/het)',
    ('c1_unit01_betoogstructuur', 'druk'): 'busy (of a place)',
    ('c1_unit02_tussen_de_regels', 'door'): "through; because of; during (as in 'during the week')",
    ('c1_unit02_tussen_de_regels', 'nou'): 'well (with juist: exactly)',
    ('c1_unit02_tussen_de_regels', 'ernstig'): 'grave; serious (of problems)',
    ('c1_unit02_tussen_de_regels', 'ging'): 'went (with hij/zij)',
    ('c1_unit02_tussen_de_regels', 'zei'): 'said (with hij/zij)',
    ('c1_unit02_tussen_de_regels', 'kon'): 'could (with hij/zij)',
    ('c1_unit03_registerbeheersing', 'gelijk'): 'the same; unchanged (of something staying as it is)',
    ('c1_unit03_registerbeheersing', 'Vries'): 'a Dutch surname',
    ('c1_unit03_registerbeheersing', 'heer'): 'Mr (in a salutation); gentleman',
    ('c1_unit04_toegeven_en_wegen', 'hoogte'): "extent (in 'to a certain extent'); height",
    ('c1_unit04_toegeven_en_wegen', 'anderzijds'): 'on the other hand (second half of a pair)',
    ('c1_unit04_toegeven_en_wegen', 'zwaarder'): 'heavier',
    ('c1_unit05_contrafeitelijk_redeneren', 'loopt'): 'runs (of a route or chain) (with hij/zij/het)',
    ('c1_unit06_idioom_en_beeldspraak', 'ga'): 'go (with ik)',
    ('c1_unit06_idioom_en_beeldspraak', 'dacht'): 'thought (past, with ik/hij/zij)',
    ('c1_unit07_bronnen_bemiddelen', 'eens'): "agreed; in agreement (in the phrase for 'to agree')",
    ('c1_unit07_bronnen_bemiddelen', 'gewone'): 'ordinary (inflected)',
    ('c1_unit07_bronnen_bemiddelen', 'moet'): 'must; has to (with ik/hij/zij)',
    ('c1_unit07_bronnen_bemiddelen', 'artikel'): 'the article (piece of writing)',
    ('c1_unit07_bronnen_bemiddelen', 'noemt'): 'names; calls (with hij/zij)',
    ('c1_unit07_bronnen_bemiddelen', 'kiest'): 'chooses (with hij/zij)',
    ('c1_unit07_bronnen_bemiddelen', 'punt'): 'the point (of discussion)',
    ('c1_unit08_retorisch_overtuigen', 'doe'): 'do (with ik)',
    ('c1_unit08_retorisch_overtuigen', 'dezelfde'): 'the same (with de-words or plural nouns)',
    ('c1_unit08_retorisch_overtuigen', 'allemaal'): "all (of us), as in 'for all of us'",
    ('c1_unit08_retorisch_overtuigen', 'alle'): 'all (before a plural noun)',
    ('c1_unit08_retorisch_overtuigen', 'laten'): "let (as in 'let's ...', with we)",
    ('c1_unit08_retorisch_overtuigen', 'degelijk'): "most certainly (after 'wel')",
    ('c1_unit08_retorisch_overtuigen', 'kom'): 'come (imperative)',
    # 2026-10-11 second C1 review: senses narrowed so a gloss has one typed answer.
    ('c1_unit01_betoogstructuur', 'beginnen'): 'to begin',
    ('c1_unit01_betoogstructuur', 'om'): '(in order) to (om ... te)',
    ('c1_unit02_tussen_de_regels', 'betekent'): 'means; signifies (with hij/zij/het)',
    ('c1_unit03_registerbeheersing', 'vriend'): 'friend (male, or in general)',
    ('c1_unit03_registerbeheersing', 'aan'): 'to (as in writing to someone); at; on',
    ('c1_unit03_registerbeheersing', 'stuur'): 'send (command form; also with ik)',
    ('c1_unit03_registerbeheersing', 'vriendelijk'): "friendly; kind (as in 'so kind as to')",
    ('c1_unit04_toegeven_en_wegen', 'klopt'): 'is correct (of a claim)',
    ('c1_unit04_toegeven_en_wegen', 'vooral'): 'especially; above all',
    ('c1_unit04_toegeven_en_wegen', 'tot'): 'until; up to',
    ('c1_unit04_toegeven_en_wegen', 'toe'): "particle of the separable verb meaning 'to concede'",
    ('c1_unit04_toegeven_en_wegen', 'tegenover'): "opposite; against (as in 'on the other hand')",
    ('c1_unit04_toegeven_en_wegen', 'tegen'): 'against',
    ('c1_unit05_contrafeitelijk_redeneren', 'voorwaarde'): 'condition (if-clause; prerequisite)',
    ('c1_unit06_idioom_en_beeldspraak', 'valt'): 'falls (with hij/zij/het)',
    ('c1_unit06_idioom_en_beeldspraak', 'schrijf'): 'write (with ik; or jij when inverted)',
    ('c1_unit07_bronnen_bemiddelen', 'eerlijk'): 'honest(ly); fair(ly)',
    ('c1_unit01_betoogstructuur', 'terug'): 'back (adverb: returning)',
    ('c1_unit02_tussen_de_regels', 'laat'): 'late',
    ('c1_unit03_registerbeheersing', 'blijft'): "remains; stays (as in 'stays the same'; with hij/zij/het)",
    ('c1_unit04_toegeven_en_wegen', 'geef'): 'give (with ik; with toe: concede)',
    ('c1_unit04_toegeven_en_wegen', 'daar'): "there (also in the set phrase for 'on the other hand')",
    ('c1_unit04_toegeven_en_wegen', 'wanneer'): 'when (conjunction)',
    ('c1_unit05_contrafeitelijk_redeneren', 'jou'): 'you (informal singular, object form)',
    ('c1_unit07_bronnen_bemiddelen', 'deze'): 'this; these',
    # HELD (see docs/EN_NL_HOMOGRAPH_OVERRIDE_CANDIDATES.md): b1 `waar` is taught
    # in BOTH senses -- "true" (b1_unit02/09) and relative "where" (b1_unit04) --
    # but a single course-scoped lexeme can carry only one gloss, so overriding
    # b1_unit02 to "true" would misgloss unit04's "where". Needs a finer
    # (per-occurrence) mechanism than this one; left as-is for now.
}

NL_UNIT_POS_OVERRIDES: dict[tuple[str, str], str] = {
    ("b1_unit06_verplichtingen", "regel"): "noun",
    ("a1_unit54_zwembad", "regel"): "noun",
    ("b1_unit05_indirecte_rede", "vroeg"): "verb",
    ("b1_unit09_eens_en_oneens", "rust"): "noun",
    ("a2_unit25_meningen", "waar"): "adjective",
    ("b1_unit01_hypothetische_situaties", "werk"): "noun",
    ("b2_unit08_synthese", "eten"): "noun",
    ("b2_unit03_nuance", "best"): "adverb",
    # C1 per-unit POS overrides (sense evidence in NL_UNIT_GLOSS_OVERRIDES).
    ('c1_unit01_betoogstructuur', 'eerst'): 'adverb',
    ('c1_unit02_tussen_de_regels', 'zijn'): 'pronoun',
    ('c1_unit03_registerbeheersing', 'weer'): 'adverb',
    ('c1_unit04_toegeven_en_wegen', 'kosten'): 'noun',
    ('c1_unit04_toegeven_en_wegen', 'proef'): 'noun',
    ('c1_unit04_toegeven_en_wegen', 'waar'): 'adjective',
    ('c1_unit05_contrafeitelijk_redeneren', 'anders'): 'adverb',
    ('c1_unit06_idioom_en_beeldspraak', 'vast'): 'adverb',
    ('c1_unit06_idioom_en_beeldspraak', 'binnen'): 'preposition',
    ('c1_unit06_idioom_en_beeldspraak', 'gewoon'): 'adjective',
    ('c1_unit06_idioom_en_beeldspraak', 'natuurlijk'): 'adjective',
    ('c1_unit07_bronnen_bemiddelen', 'bevestigd'): 'verb',
    ('c1_unit08_retorisch_overtuigen', 'groen'): 'noun',
    ('c1_unit08_retorisch_overtuigen', 'rust'): 'noun',
    ('c1_unit04_toegeven_en_wegen', 'wanneer'): 'particle',
    # ("b1_unit01…", "was") stays a verb -- gloss-only override, no POS change.
}


def _classify_nl(unit_files, level):
    # A FRESH specs dict per level/course -- Lexeme uniqueness is scoped by
    # `Lexeme.course_id`, and "Dutch A1"/"Dutch A2" are two entirely separate
    # course rows (see UNIT_FILES_A2's comment), so a token re-taught in A2
    # needs its own A2-scoped Lexeme row rather than silently reusing A1's.
    specs: dict[str, dict] = {}
    for unit_order, realization_path in enumerate(unit_files, 1):
        unit_stem = realization_path.stem
        realization = yaml.safe_load(realization_path.read_text(encoding="utf-8"))
        # NL_CITATION_FORMS is applied ONLY to the 2026-07-22 A1 volume batch
        # (units 34-42 / 49-72). Scoping it to those lessons is load-bearing,
        # not cosmetic: a few of its keys ("Kunt", "Volgende", "Moet") are ALSO
        # introduced by already-backfilled A2 units, and folding them there
        # would silently delete three shipped A2 lexemes that A2 practice packs
        # may already resolve against. Fixing those is a separate, deliberate
        # data-migration decision -- it does not get smuggled in here.
        in_volume_batch = (
            ".".join(realization["units"][0]["content_key"].split(".")[1:3])
            in NL_A1_VOLUME_UNIT_SLUGS
        )
        for lesson_order, lesson in enumerate(realization["units"][0]["lessons"], 1):
            lesson_key = lesson["content_key"]
            for item in lesson["teaching"]:
                for token in item.get("introduced_tokens", []):
                    token = str(token)
                    # Fold sentence-initial / sign-line capitals onto their
                    # lowercase citation form BEFORE anything else, so a
                    # capitalized-by-position spelling never becomes a
                    # Lexeme.token (defect 1.25 -- typed answers are graded
                    # by exact string match and a case-only mismatch is
                    # hard-blocked to `incorrect`).
                    if in_volume_batch:
                        token = NL_CITATION_FORMS.get(token, token)
                    elif level == "c1":
                        token = nl_c1_citation_form(token)
                    if token not in NL_GLOSSES:
                        raise ValueError(f"missing explicit Dutch gloss for {token!r}")
                    tags = nl_agreement_tags(token, lesson_key)
                    existing = specs.get(token)
                    if existing is None:
                        gloss = NL_UNIT_GLOSS_OVERRIDES.get(
                            (unit_stem, token), NL_GLOSSES[token]
                        )
                        pos = NL_UNIT_POS_OVERRIDES.get(
                            (unit_stem, token), nl_part_of_speech(token)
                        )
                        if level == "c1" and pos == "noun":
                            gloss = nl_c1_bare_gloss(gloss)
                        specs[token] = {
                            "level": level,
                            "unit_order": unit_order, "lesson_order": lesson_order,
                            "lesson_content_key": lesson_key, "content_key": item["content_key"],
                            "token": token, "language_code": "nl",
                            "part_of_speech": pos,
                            "english_gloss": gloss, "agreement_tags": tags,
                        }
                    else:
                        prior = existing["agreement_tags"].setdefault("semantic", [])
                        prior.extend(value for value in tags["semantic"] if value not in prior)
    yield from specs.values()


def iter_specs():
    yield from _classify_nl(UNIT_FILES, "a1")
    yield from _classify_nl(UNIT_FILES_A2, "a2")
    yield from _classify_nl(UNIT_FILES_B1, "b1")
    yield from _classify_nl(UNIT_FILES_B2, "b2")
    yield from _classify_nl(UNIT_FILES_C1, "c1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    specs = list(iter_specs())
    if args.dry_run:
        a1_count = sum(spec["level"] == "a1" for spec in specs)
        a2_count = sum(spec["level"] == "a2" for spec in specs)
        b1_count = sum(spec["level"] == "b1" for spec in specs)
        b2_count = sum(spec["level"] == "b2" for spec in specs)
        c1_count = sum(spec["level"] == "c1" for spec in specs)
        print(
            f"Lexeme backfill dry run: {len(specs)} nl ({a1_count} a1, {a2_count} a2, "
            f"{b1_count} b1, {b2_count} b2, {c1_count} c1)."
        )
        return 0

    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models import Course, Lesson, Lexeme, Unit

    with SessionLocal() as db:
        courses_by_level = {}
        for level, title in (("a1", "Dutch A1"), ("a2", "Dutch A2"), ("b1", "Dutch B1"), ("b2", "Dutch B2"), ("c1", "Dutch C1")):
            needed = any(spec["level"] == level for spec in specs)
            course = db.scalar(
                select(Course).where(
                    Course.source_language == "en",
                    Course.target_language == "nl",
                    Course.title == title,
                )
            )
            if course is None:
                if needed:
                    print(f"ERROR: en-nl {title!r} course must be imported first", file=sys.stderr)
                    return 1
                continue
            courses_by_level[level] = course

        lessons_by_level = {
            level: {
                (unit.order, lesson.order): lesson
                for unit in db.scalars(select(Unit).where(Unit.course_id == course.id))
                for lesson in db.scalars(select(Lesson).where(Lesson.unit_id == unit.id))
            }
            for level, course in courses_by_level.items()
        }
        created = updated = 0
        for raw_spec in specs:
            spec = dict(raw_spec)
            level = spec.pop("level")
            course = courses_by_level[level]
            lesson = lessons_by_level[level].get(
                (spec.pop("unit_order"), spec.pop("lesson_order"))
            )
            if lesson is None:
                print(f"ERROR: imported course is missing {spec['lesson_content_key']}", file=sys.stderr)
                db.rollback(); return 1
            existing = db.scalar(select(Lexeme).where(Lexeme.course_id == course.id, Lexeme.language_code == "nl", Lexeme.token == spec["token"], Lexeme.part_of_speech == spec["part_of_speech"]))
            if existing:
                existing.english_gloss = spec["english_gloss"]
                existing.agreement_tags = spec["agreement_tags"]
                updated += 1
                continue
            # No exact (token, part_of_speech) row. A per-unit POS override
            # (NL_UNIT_POS_OVERRIDES) can flip a token's POS. Creating a new
            # (token, new-POS) row would orphan the old (token, old-POS) row --
            # and that row can NOT be deleted once a practice_item /
            # user_lexeme_srs references it via FK (the live-DB case). Instead
            # MIGRATE the existing row IN PLACE (same lexeme id -> FKs stay
            # valid). Safe because `specs` holds exactly one spec per
            # (course, token) (keyed by token, first sight wins), so at most one
            # other-POS row exists; the exact-POS SELECT above already ruled out
            # a same-POS row, so migrating can't collide with the unique
            # (course, language, token, part_of_speech) constraint.
            others = db.scalars(
                select(Lexeme).where(
                    Lexeme.course_id == course.id,
                    Lexeme.language_code == "nl",
                    Lexeme.token == spec["token"],
                )
            ).all()
            if len(others) == 1:
                row = others[0]
                row.part_of_speech = spec["part_of_speech"]
                row.english_gloss = spec["english_gloss"]
                row.agreement_tags = spec["agreement_tags"]
                updated += 1
                continue
            db.add(Lexeme(course_id=course.id, provenance_lesson_id=lesson.id, provenance_lesson_content_key=spec.pop("lesson_content_key"), provenance_content_key=spec.pop("content_key"), **spec))
            created += 1
        db.commit()
    print(
        f"Lexeme backfill complete: {created} created, {updated} updated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
