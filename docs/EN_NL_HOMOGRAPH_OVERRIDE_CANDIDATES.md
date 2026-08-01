# en-nl homograph gloss overrides — sweep + verified outcome (2026-08-01)

Direction: **en→nl** (English speakers learning Dutch). A Dutch token has ONE
global `NL_GLOSSES` english-gloss + `nl_part_of_speech()`; a token re-taught in a
later unit in a DIFFERENT sense therefore ships the wrong unit's English gloss
(which `slot_gloss` derives into the graded MC/translate answer).

**Mechanism** (`scripts/backfill_lexemes_en_nl.py`): `NL_UNIT_GLOSS_OVERRIDES` /
`NL_UNIT_POS_OVERRIDES`, keyed by `(unit_stem, token)` where `unit_stem =
realization_path.stem`. **Footgun:** the override only fires at the FIRST
sorted-order unit that introduces the token *per course* (a1/a2/b1 are separate
specs dicts, one lexeme per token per course, created on first sight). Keying to
any later unit silently no-ops. Every key below was confirmed to be the first
introducer for its course (verified against the dev DB — one nl lexeme per token
per course, at the keyed unit).

## APPLIED — 5 overrides, each verified against the unit's own teaching text

| unit_stem | token | global (wrong here) | unit teaches | evidence | override |
|---|---|---|---|---|---|
| `a1_unit54_zwembad` | regel | verb "arrange (with ik…)" | noun "the rule" | `target: "de regel"`, matching-pair `regel→rule` | **"the rule" [noun]** |
| `b1_unit01_hypothetische_situaties` | was | verb "do the dishes (with ik)" | past/unreal copula | *"Als ik rijk was, zou ik een huis kopen"* | **"was; were (past tense of zijn)" [verb]** |
| `b1_unit05_indirecte_rede` | vroeg | adj "early" | verb "asked" | *"Hij vroeg of ik kon helpen"* (reported speech) | **"asked (past tense of vragen)" [verb]** |
| `b1_unit09_eens_en_oneens` | rust | verb "rest (imperative, with u)" | noun "rest" | *"mensen meer rust nodig hebben"* | **"rest; calm" [noun]** |
| `a2_unit25_meningen` | waar | adverb "where" | adj "true" | *"Dat is waar"* (only a2 use) | **"true" [adjective]** |

Plus the pre-existing `("b1_unit06_verplichtingen","regel") → "the rule" [noun]`
(the first sweep's exemplar). Non-collision occurrences (`regel`/a2u77,
`rust`/a2u27, `vroeg`/a1u17+a2u76, `was`/a1u10, `waar`/a1u08) were verified to
teach the SAME sense as the global gloss and correctly left untouched.

## HELD — 1, a real mechanism limitation

`("b1_unit02_mening_en_nuance","waar")` → "true" was **NOT applied**. B1 teaches
`waar` in two senses — "true" (unit02/09) and relative "where" (unit04) — but a
single course-scoped lexeme carries one gloss, so overriding b1 `waar` to "true"
would misgloss unit04's "where". This needs a finer per-occurrence mechanism than
`(unit, token)`; left as-is (currently "where", so unit04 is correct and
unit02/09 imperfect). Same structural class: A1 `was` (correct "do the dishes" at
its A1 first-introducer unit10, but ~20 later A1 units reuse it as past-tense and
can't be reached by a first-introducer-keyed override).

## Deploy note — orphan prune (added this session)

A POS-changing override CREATES the new-(token,pos) row while the upsert (keyed on
token+POS) leaves the old-POS row orphaned. `main()` now reconciles: for every
(course, token) this run wrote, it deletes lexeme rows sharing that (course,token)
with a POS not in the current specs (safe — exactly one spec per (course,token)).
Verified on the dev DB: `4 created, 4 stale-POS pruned`, final state one row per
(course,token), zero orphans. Fresh imports prune nothing.

**DEPLOY-GATED** — verified against the local dev DB only; not applied to the live
server.
