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

## Deploy note — orphan prune (en_nl) + ⚠️ DEPLOY-SAFETY CAVEAT

A POS-changing override CREATES the new-(token,pos) row while the upsert (keyed on
token+POS) leaves the old-POS row orphaned. `backfill_lexemes_en_nl.py:main()`
reconciles by deleting, for every (course,token) it wrote, lexeme rows with a POS
not in the current specs. Verified on the dev DB: `4 created, 4 stale-POS pruned`,
one row per (course,token), zero orphans.

**⚠️ NOT DEPLOY-SAFE AS WRITTEN — must be fixed before any LIVE re-backfill.** The
prune's `DELETE` fails with a ForeignKeyViolation once any `practice_items`
(`fk_practice_items_target_lexeme_id`) or `user_lexeme_srs` row references the
old-POS lexeme — which is exactly the live case with real users (proven this
session: a played unit40 checkpoint pinned the old `order` lexeme and blocked its
deletion). The deploy-correct implementation is **migrate-in-place**: look up the
existing row by (course,token) and update its `part_of_speech`+gloss+tags on the
SAME row (preserving the lexeme id, so FKs stay valid), instead of create-new +
delete-old. Attempted this session but it needs an exact-POS-first lookup to avoid
a `uq_lexemes_course_language_token_pos` collision on tokens that already carry two
POS rows — a careful backfill-upsert change (Codex lane) worth doing as part of
deploy prep. Until then these overrides are dev-verified only.

## nl_en A2 homograph GLOSS fixes (gloss-only, deploy-safe) — 2026-08-02

The X→en (`backfill_lexemes_nl_en.py`) direction has the same class; three A2
tokens carried the wrong-sense Dutch gloss (which slot_gloss renders as the graded
answer). Fixed **gloss-only** so the existing exact-(course,token,POS) upsert
updates the row IN PLACE (no new row, no orphan, FK-safe — verified `0 created,
2927 updated`):

| unit | token | was | now | overlay evidence |
|---|---|---|---|---|
| a2_unit36_document_correction | correct | "juist; kloppend" | **"corrigeren; verbeteren"** | "*correct* is hier een werkwoord" |
| a2_unit37_video_calls | meeting | "afspraak" | **"vergadering"** | overlay uses *vergadering* for the work-meeting sense |
| a2_unit40_online_order_problem | order | "bestellen; de volgorde" | **"de bestelling"** | "*order* is de bestelling zelf" |

**Deferred:** the grammatical POS still lags the sense (order=verb, correct=adj) —
the fully-correct fix (order→noun, correct→verb) needs the same migrate-in-place
upsert as the en_nl caveat above; deferred to that Codex-lane change. `turn`
(a2_unit37) left excluded — bare "turn" is genuinely ambiguous (turn on=aanzetten
vs turn off=sla af), the author's exclusion stands.

**DEPLOY-GATED** — dev DB only, not on the live server.

## BROADER SWEEP (remaining corpus)

Second pass (2026-08-01, READ-ONLY analysis) over the en-nl units **not** covered by
the first sweep: all `UNIT_FILES` (a1) and `UNIT_FILES_A2` (a2), plus `UNIT_FILES_B1`
units 03/04/07/08/10–19 (b1_01/02/05/06/09 already done). No b2 en-nl files exist.

**Method.** Imported `backfill_lexemes_en_nl.py`, traced the FINAL global gloss/POS
per token (all `NL_GLOSSES.update`/assignments folded, last-wins; `NL_CITATION_FORMS`
folding replicated for the A1 volume batch), then, per course, listed every unit that
introduces each token in sorted order. Primary filter = tokens whose global gloss is a
specific-sense verb marker (`(with …`, `imperative`, `part of `, `separable prefix`,
`conditional of`) — the high-risk class. Secondary filter = first-introducer taught as
a bare `de/het` noun while global POS ≠ noun. Each hit was checked against the unit's
own realization `target`/`example`/`content_key`.

### NEW APPLICABLE — 1 (high confidence)

| unit_stem (first introducer) | token | final global gloss[POS] | unit's taught sense + evidence | first-introducer? | proposed | conf |
|---|---|---|---|---|---|---|
| `b1_unit01_hypothetische_situaties` | werk | "work (with ik)" [verb] | NOUN "work; job" — b1_unit01 `tgt: "werk"`, *"Anouk is blij met haar werk."*; b1_unit06 *"Ik was druk met werk."* Both (and only) b1 uses are the noun. | **yes** (b1 first sees `werk` at unit01) | **"work; job" [noun]** | high |

`werk` is the documented verb/noun homograph (module docstring, unit17 note). In the
**B1** course it is taught *exclusively* as the noun, so the single b1-scoped lexeme —
created at b1_unit01 and currently carrying the verb gloss "work (with ik)" — is wrong
for every b1 occurrence. A first-introducer-keyed override cleanly fixes it (unlike the
A1/A2 cases below, where both senses coexist).

### HELD — 5 (structural; mechanism cannot cleanly fix)

Same class as the first sweep's `waar@b1_unit02` / A1 `was`: the token is taught in
**two senses within one course**, and a single course-scoped lexeme (keyed at the first
sorted introducer) can carry only one gloss. Overriding would just move the error.

| course | token | global[POS] | senses in course | why HELD |
|---|---|---|---|---|
| a1 | werk | "work (with ik)" [verb] | verb at first intro (unit10 `Ik werk`), NOUN later (unit17 `voor werk`, unit33 `naar werk`) | first introducer is the verb sense; override can't target the later noun units |
| a1 | ontbijt | "have breakfast (with ik)" [verb] | verb at first intro (unit10 `Ik ontbijt`), NOUN later (unit49 `het ontbijt`, `Is het ontbijt inbegrepen?`) | first introducer is the verb sense |
| a1 | begin | "start (with ik)" [verb] | verb at first intro (unit17 `Ik begin om negen uur`), NOUN later (unit64 sign `Begin: acht uur`) | first introducer is the verb sense |
| a1 | sport | "exercise; play sports (with ik)" [verb] | verb at first intro (unit29 `Ik sport op zaterdag`), NOUN later (unit32 `de sport`, `Voetbal is een sport`) | first introducer is the verb sense |
| a2 | werk | "work (with ik)" [verb] | NOUN at first intro (unit24 `voor werk`), VERB later (unit76 `werk ik`) | overriding unit24→noun would misgloss unit76's verb use |

### Everything else verified consistent

All other verb-marker-gloss tokens (`regel`/a2u77, `rust`/a2, `sport`/a2, `duurt`,
`stort`, `schrijf`, `vind`, `zit`, `toe`/b1, etc.) teach the SAME sense their global
gloss records at their first introducer — no collision, correctly left untouched. The
secondary noun-headword filter surfaced only item-headword false positives (the token
is an adjective/verb in an item whose `target` headword happens to be a noun) plus the
already-overridden `regel`.

### Ready-to-paste (APPLICABLE high-confidence only)

```python
# NL_UNIT_GLOSS_OVERRIDES — add:
    # b1 teaches `werk` only as the NOUN ("Anouk is blij met haar werk",
    # "Ik was druk met werk"); global `werk` = verb "work (with ik)".
    ("b1_unit01_hypothetische_situaties", "werk"): "work; job",

# NL_UNIT_POS_OVERRIDES — add:
    ("b1_unit01_hypothetische_situaties", "werk"): "noun",
```

**APPLIED + VERIFIED (2026-08-01).** The `werk`@b1_unit01 override was checked
against ground truth — DB confirmed b1 `werk` is a single lexeme at unit01 (verb
"work (with ik)"); b1 realizations introduce `werk` only at unit01 + unit06, both
the noun ("haar werk", "druk met werk"); the verb "ik werk" in b1_unit04 is
embedded in a relative-clause example, NOT an introduced token, so it never
becomes a graded `werk`-target. Applied to both override dicts; re-backfill:
`1 created, 1 stale-POS pruned`, final b1 `werk` = noun "work; job", a1u10/a2u24
unchanged (verb). The 5 HELD cases remain deploy-unfixable by this mechanism.
DEPLOY-GATED — dev DB only, not on the live server.
