# Practice-pack authoring recipe (Endless Practice + unit checkpoints)

**Status: authoritative. Written 2026-07-22 to be the single source every
practice-pack authoring agent follows.** It is self-contained: an agent with no
other context can author a correct pack from this file alone. `docs/content/
AUTHORING_GUIDE.md` stays binding for everything it covers (§13, §16, §17, §18 are
the practice-relevant sections and are restated here); this file is the operational
recipe.

Proven by a real pilot: **`docs/content/practice/en-nl/a2_unit73.yaml`** — authored
against this recipe, 0 compiler errors, and a faithful offline port of
`generate_checkpoint()` returns 15/15 distinct items on 5 different RNG seeds.

> ### CORRECTIONS — 2026-07-22 (read this if you already read an earlier version)
>
> Eight defects were found by the first agent to author a full wave against this
> recipe, and each was re-verified against the code before being written in here.
> If you already started a pack on the earlier text, re-check these:
>
> 1. **§6.6 / DO-NOT #9 REVERSED. The case-sensitivity ban was factually wrong.**
>    Practice and checkpoint answers **are** casefolded — a sentence-initial
>    capitalized lexeme is a **safe** typed answer. Lowercase citation forms are
>    still preferred, but for DATA-QUALITY reasons only. See §6.6.
> 2. **§0 and §9 step 4 diagnostics had a unit-number collision bug.** They filtered
>    on `f'.{UNIT}.'`, which matches the same unit number at *every* CEFR level (for
>    en-nl `unit01` that reported 154 lexemes instead of 79). Both snippets now
>    filter on `f'.{LEVEL}.{UNIT}.'`. **Re-run any capacity measurement you took
>    with the old snippet.**
> 3. **§8 gained a grammar-unit section (§8.1).** The "one broad template per lesson,
>    using that lesson's own tag" pattern is a *vocabulary-unit* recipe; applied
>    literally to a B1 grammar unit it puts 27 of 65 en-nl B1 lessons under the
>    3-option `multiple_choice` floor and 47 of 65 under the 6-pair
>    `matching_pairs` floor.
> 4. **§3.1 is new: semantic-tag UNIONS and untagged slots.** `semantic: [a, b, c]`
>    is OR-matched and a slot may legally omit `semantic` entirely. This is the
>    single most important technique for reaching the floors in a thin unit, and
>    the only way to *exclude* one bad lexeme from a pool.
> 5. **§1.1 is new: unit scope vs course scope.** Satisfiability is unit-scoped;
>    self-reference and "every pool member must be grammatical in the frame" are
>    COURSE-scoped. Three word_order frames passed at unit scope and were
>    ungrammatical at course scope.
> 6. **§0 gained a mandatory gloss-reading step.** Mis-glossed lexemes are not an
>    fa/prs-only problem (old §7 framing) — en-nl B1 alone has five whose gloss
>    would be *shown to the learner as the correct answer* while meaning something
>    else. Read every gloss; do not just count tokens.
> 7. **§9: `practice-validate` costs ~55 s per invocation** regardless of pack
>    count. Pass **all** your packs to a single `--pack` (it is `nargs='+'`).
> 8. **§9 step 2's acceptance test was impractical.** The integrity check prints
>    ~44 lines of pre-existing flags; pipe it through `grep <yourfile>` and expect
>    empty. **Also new:** both corpus checks glob `a*_unit*.yaml`, so they silently
>    skip every `b1_`/`b2_` pack — see §9.

---

## 0. STOP. Do the prerequisite check before you write a single line.

**A practice pack is NOT sufficient to make a unit checkpoint work.** The checkpoint
needs BOTH practice templates AND lexemes for that unit. Lexemes are produced by
`scripts/backfill_lexemes*.py`, not by your pack. If the unit's lessons produce zero
lexemes, your pack will validate green at 0 errors and still return
`checkpoint_unavailable` forever.

Run this first (from the repo root). It prints the unit's real lexeme pool:

```bash
.content-venv/bin/python - <<'EOF'
import sys, collections; sys.path.insert(0, 'scripts')
DIRECTION = 'en-nl'     # <-- your direction
LEVEL     = 'a2'        # <-- your CEFR level: a1 | a2 | b1 | b2
UNIT      = 'unit73'    # <-- your unit, e.g. 'unit05'
MODULES = {'en-fa':'backfill_lexemes','fa-en':'backfill_lexemes_fa_en',
           'en-prs':'backfill_lexemes_en_prs','prs-en':'backfill_lexemes_prs_en',
           'en-nl':'backfill_lexemes_en_nl','nl-en':'backfill_lexemes_nl_en'}
# NOTE the '.{LEVEL}.{UNIT}.' filter: unit numbers RESTART at every CEFR level,
# so the old '.{UNIT}.' form merged A1+A2+B1 (en-nl 'unit01' -> 154 lexemes
# instead of the real 79) and every capacity number downstream was wrong.
specs = [s for s in __import__(MODULES[DIRECTION]).iter_specs()
         if f'.{LEVEL}.{UNIT}.' in s['lesson_content_key']]
print(f'{len(specs)} lexemes for {DIRECTION} {LEVEL} {UNIT}')
by = collections.defaultdict(list)
for s in specs: by[s['lesson_content_key']].append(s)
for k, v in by.items():
    print('---', k, f'({len(v)})')
    for s in v:
        print('   ', s['token'], '|', s['english_gloss'], '|', s['part_of_speech'],
              '|', s['agreement_tags'].get('semantic'))
EOF
```

* **0 lexemes → STOP and report back to the coordinator.** This unit is BLOCKED: it
  needs a `backfill_lexemes*.py` extension (glosses, part-of-speech set membership,
  `lesson_categories`, semantic tags) before any pack can help. Do not author a pack
  and do not edit the backfill script yourself unless your dispatch explicitly
  assigns you that script.
* **≥1 lexeme in ≥1 lesson → proceed.** Note which lessons have lexemes; a lesson
  with zero lexemes cannot be represented in the checkpoint no matter what you do.

### 0.1 READ every gloss in that dump. Do not just count tokens.

The dump above is not only a capacity measurement — it is the **only** place a
mis-glossed lexeme is visible to you. `backfill_lexemes*.py` keys glosses by **bare
token**, one entry per token for the whole direction, so a token your unit
re-introduces in a *new sense* still carries whichever sense some earlier unit
registered. `slot_gloss` and `matching_pairs` then show that wrong gloss to the
learner **as the correct answer**.

This is not an fa/prs homograph problem (defect 1.29 is written up that way in §7
because that is where it was first found). en-nl B1 alone, measured 2026-07-22:

| Token | Gloss the lexeme carries | What the B1 unit actually teaches |
|---|---|---|
| `was` (b1 unit01) | "do the dishes (with ik)" | *was* — `Als ik rijk was, …` |
| `waar` (b1 unit02) | "where" | *true* — the unit's own pair is `waar → "true"` |
| `vroeg` (b1 unit05) | "early" | *asked* — `Hij vroeg of …` |
| `rust` (b1 unit09) | "rest (imperative, with u)" | the **noun** *rest* — `meer rust nodig hebben` |
| `regel` (b1 unit06) | "arrange (with ik, part of regelen)" | *de regel* = the rule |

**Rule: read every gloss in the pool of every slot you author, in every direction,
and check it against what the unit's realization file actually teaches.** A wrong
gloss cannot be caught by any validator, by a green compile, or by the capacity
script. Keep the mis-glossed token out of your pools (§3.1 shows how to exclude one)
and list it in your `review.notes` so the coordinator can route a backfill fix.

**Measured 2026-07-22 across the 6 launch directions:** of the 292 units missing a
pack, only **45** currently have lexemes (en-nl 12, en-fa 19, en-prs 14). The other
**247** are backfill-blocked. fa-en / nl-en / prs-en have **zero** ready units — every
one of their 52 missing packs is blocked on the shared English realization's lexeme
classification.

---

## 1. How the runtime actually consumes your pack (read this — the rules below all
## follow from it)

`backend/app/practice/service.py`:

| Function | What it does | Consequence for you |
|---|---|---|
| `_material(db, course, lesson_ids)` | selects `PracticeTemplate` rows whose `provenance_lesson_id` ∈ `lesson_ids` **and** `Lexeme` rows whose `provenance_lesson_id` ∈ `lesson_ids` | your template only exists for a checkpoint if its `lesson_content_key` names a lesson **of that unit** |
| `generate_checkpoint()` (:1557) | calls `_material()` with **only the unit's own lesson ids** | **THE load-bearing rule: every slot must be satisfiable by lexemes THIS UNIT introduces.** A slot tagged with vocabulary taught in an earlier unit has ZERO candidates at checkpoint scope and can never generate. |
| `generate_batch()` / `generate_review_batch()` | calls `_material()` with **every completed lesson** in the course | the same template CAN legitimately draw on earlier units in Endless Practice — that is why so many existing packs look fine there and still fail the checkpoint |
| `_material()` TTS filter | drops **all `listen_select` templates** when `tts_actually_configured(target_language)` is false | see §6.6 — `listen_select` is dead weight for `en-fa` and `en-prs` today |
| `_generate_target_item()` | picks a **target lexeme** first, then forces it into a slot it matches | a template can only ever serve targets that match one of its slots. Narrow single-member slots serve exactly 1 lexeme. **Target coverage matters as much as template count.** |
| `_tier_order(mastery)` | checkpoint cycles fixed bands 0.0 / 0.5 / 0.8 → recognition-first / structured-first / production-first | you need real capacity in **all three tiers**, or the mix collapses into whichever tier has depth |
| `build_prompt()` | rejects `multiple_choice`/`listen_select` with `< 3` distinct options; rejects `fill_in_blank` whose blanked frame has no other visible text; rejects `matching_pairs` whose filled slots collapse to fewer distinct tokens than declared | these are silent rejections — they cost you items with no error anywhere |
| router `:1480` | `if len(items) < 12: 409 checkpoint_unavailable` | the hard bar |

`fill_slots()` returns `None` immediately if **any** declared slot has zero
candidates — one dead slot kills the whole template, not just that slot.

### 1.1 Every rule below has a SCOPE. Check which one, every time.

Your template is executed against **two different lexeme pools**, and a rule that is
safe in one is not automatically safe in the other. Three shipped `word_order` frames
were fine at unit scope and ungrammatical at course scope purely because this was
left implicit.

| Scope | Pool | Which calls use it |
|---|---|---|
| **UNIT** | only the lexemes the unit's own lessons introduce | `generate_checkpoint()` |
| **COURSE** | every lexeme in every lesson of this `Course` the learner has completed. A `Course` is **one CEFR level** — A1/A2/B1 never mix. | `generate_batch()` (Endless Practice), `generate_review_batch()` |

Rule-by-rule:

* **Satisfiability (every slot has ≥1 candidate; MC/listen_select ≥3; matching_pairs
  ≥ slot count) — UNIT-scoped.** These are the bars that decide whether the
  checkpoint reaches 12 items. Measure them on the unit's lexemes only (§9 step 4).
* **Self-reference, defect 1.14 (the frame's literal text must not contain one of its
  own slot's candidate values) — COURSE-scoped.** A word that is not a candidate in
  your unit becomes one in Endless Practice.
  `scripts/_practice_content_integrity_check.py` already checks it at that scope
  (it loads the direction's **entire** `iter_specs()` pool).
* **"Every pool member must be grammatical / sensible in the frame" (§6.4
  `word_order`, §6.6(b) fixed-sentence `translation`) — COURSE-scoped.** This is the
  one that bites. `Kunt u {weekday} om tien uur langskomen?` is safe only if every
  *course-wide* member of the slot's pool is a weekday. Concretely, for en-nl B1: a
  slot with a single lesson tag pools ~2–20 lexemes at unit scope; the same slot with
  a 6-tag union pools 21 at unit scope but **44 at course scope**; and a slot with no
  `semantic:` constraint at all pools **293** course-wide content words. Widen the
  slot, then re-read the frame against the *widened* pool.
* **`fill_in_blank` single-candidate ambiguity (§6.5) — checked even wider than
  course scope:** the compiler pools every level of the direction at once. It is
  deliberately stricter than runtime; satisfy it as written.
* **TTS availability, RTL/`direction`, script purity, register — pack-wide.** They
  do not depend on which pool is loaded.

---

## 2. Where the file goes, and what it is called

```
docs/content/practice/<direction>/<level>_unit<NN>.yaml
```

* `<direction>` — one of `en-nl`, `nl-en`, `en-fa`, `fa-en`, `en-prs`, `prs-en`.
* `<level>` — `a1`, `a2`, `b1`, `b2`; must match the level in the unit's own
  `content_key`, because **A1 / A2 / B1 are separate `Course` rows** and lexemes never
  cross a course boundary (AUTHORING_GUIDE §18).
* `<NN>` — the unit number, zero-padded to 2 digits, exactly as in the realization
  filename. Examples: `docs/content/practice/en-nl/a2_unit73.yaml`,
  `docs/content/practice/en-fa/b1_unit04.yaml`.

**One file per unit. Never put two units in one file.**

**Do NOT edit `scripts/manifest.d/practice/*.txt`.** Many agents author packs
concurrently and that file is a known concurrency hazard. Report the pack path to
the coordinator; the coordinator appends it to the direction's manifest line.

---

## 3. The complete YAML schema

Every field below is required unless marked optional. The compiler
(`scripts/compile_content.py`) and the import Pydantic schema
(`backend/app/schemas/api.py` `PracticeTemplateImport`) both enforce this.

```yaml
schema_version: '1.0'                  # literal string, always '1.0' (quoted!)
pack_key: practice.en-nl.a2.unit73     # practice.<direction>.<level>.unit<NN>
source_language: en                    # must match the direction's first half
target_language: nl                    # must match the direction's second half
unit_content_key: nl.a2.unit73.sollicitatiegesprek   # the unit's own content_key,
                                       # copied verbatim from the realization file
review:
  status: unreviewed                   # every new pack starts unreviewed
  fresh_context: 'false'               # QUOTED string, never a bare boolean
  notes: >-
    What you authored, which tags you used and why, what you measured
    (capacity + coverage), and anything a reviewer must double-check.

tag_schema:                            # the vocabulary your slots are allowed to use
  part_of_speech:                      # copy this list verbatim; it is the standard set
  - symbol
  - noun
  - proper_noun
  - pronoun
  - verb
  - adjective
  - adverb
  - preposition
  - particle
  - phrase
  agreement_tags:                      # optional, but needed for any `semantic:` slot
    semantic:
    - job_interview_vocab_pure         # EVERY semantic tag any slot uses must be listed
    - weekday_pure                     # here, or the compiler hard-fails

templates:
- content_key: practice.en-nl.nl.a2.unit73.lesson01.choose.001
  lesson_content_key: nl.a2.unit73.lesson01.ik_wil_solliciteren
  type: multiple_choice
  frame:
    text: '{item}'                     # literal text + {snake_case} slot placeholders
    language_code: nl
    direction: ltr                     # MUST be rtl for fa/prs/ar, ltr otherwise
    slot_rendering:                    # optional; per-slot: token | english_gloss
      item: english_gloss              #   default is `token`
  slots:                               # non-empty mapping; slot names are snake_case
    item:
      language_code: nl                # the LEXEME's language (target for most types)
      part_of_speech: [noun, verb]     # scalar or list; OR-matched; every value must
                                       #   appear in tag_schema.part_of_speech
      agreement_tags:                  # optional
        semantic: job_interview_vocab_pure   # scalar or list; OR-matched
  slot_relations:                      # optional list
  - kind: distinct                     # distinct | same_tag
    slots: [first, second, third]      # >= 2 names, all declared in `slots`
    # tag: semantic                    # required only when kind == same_tag
  answer_derivation:
    kind: slot_gloss                   # see §5
    slot: item
  feedback_frame:                      # REQUIRED (not optional at import)
    text: '{item} belongs to this unit''s job-application vocabulary.'
    language_code: en
    direction: ltr
```

Field notes that bite people:

* **`frame.text` placeholders** must be `{snake_case}` and every referenced name must
  exist in `slots`. Declaring a slot the frame does **not** reference is legal
  (`require_all=False`) — but `fill_slots()` still requires it to have ≥1 candidate,
  and `_generate_target_item()` will use it to decide which target lexemes this
  template can serve. Never declare a decorative slot "just to widen coverage": the
  item then records the wrong target lexeme against the learner's SRS.
* **`direction`** is validated against `language_code` for *every* mapping in the file
  that has both a `text` and a `language_code` key (`validate_text_block_directions`).
  `fa`, `prs`, `ar` → `rtl`. Everything else → `ltr`.
* **`frame.text_blocks`** appears in some older packs. It is **ignored by
  `build_prompt()`** — the backend builds its own instruction block. Don't add it.
* **No bare `yes`/`no`/`true`/`false`/`on`/`off`** anywhere as a string value; PyYAML
  silently coerces them to booleans and the compiler hard-fails
  (`validate_no_practice_yaml_booleans`). Quote them: `"Yes"`.

### `content_key` convention

```
practice.<direction>.<target_lang>.<level>.unit<NN>.lesson<NN>.<verb>.<seq>
       practice.en-nl.nl.a2.unit73.lesson01.choose.001
       practice.fa-en.en.a1.unit30.lesson02.match.003
```

* `<verb>` by type: `choose` (multiple_choice), `listen` (listen_select), `match`
  (matching_pairs), `order` (word_order), `fill` (fill_in_blank), `translate`
  (translation).
* `<seq>` is a 3-digit counter **restarting at 001 within each lesson**.
* `content_key` must be globally unique across the whole practice corpus AND must not
  collide with any realization/overlay `content_key` (the compiler checks both).
* `lesson_content_key` is copied **verbatim** from the realization's
  `units[0].lessons[].content_key`. Do not invent it; typos here produce a template
  that silently never imports.

### 3.1 Slot constraints: unions, untagged slots, single-member anchors

Everything above shows a slot with **one scalar** `semantic:` tag. That is the
*narrowest* of three legal forms, and it is why thin units look impossible. All three
matter; the union is the most important technique in this file.

`lexeme_matches()` (`service.py:64`) is the whole contract, and the compiler states
it explicitly at `compile_content.py:2381`: *"a requested list is an OR query"*.

**(a) A semantic tag may be a LIST, and it is OR-matched.**

```yaml
    item:
      language_code: nl
      part_of_speech: [noun, verb, adjective]
      agreement_tags:
        semantic: [reported_speech_statement, reported_speech_question,
                   reported_speech_dialogue, reported_speech_reading]
```

A lexeme matches if it carries **any one** of those values. This is how a unit whose
individual lessons hold 2–3 content words each reaches the `multiple_choice` 3-option
floor and the `matching_pairs` 6-pair floor: **union the unit's lesson tags.** In
en-nl B1, the per-lesson tag alone leaves 27 of 65 lessons under the MC floor and 47
under the matching_pairs floor; the union of a unit's own lesson tags yields 12–54
distinct content tokens per unit — every unit clears both floors.

Every value you list must appear in `tag_schema.agreement_tags.semantic` or the
compiler hard-fails.

**(b) Union is also how you EXCLUDE one lexeme.** There is no "not" operator. To keep
a mis-glossed token (§0.1), a proper noun, or a case-duplicate out of a pool, **union
the sibling lesson tags and simply omit the tag that carries it.** Narrowing
`part_of_speech` is the other exclusion lever (it is what keeps `proper_noun` out of
`multiple_choice` pools).

**(c) A slot may declare NO `semantic:` tag at all** — `agreement_tags` defaults to
`{}` and `all()` over an empty mapping is `True`, so `language_code` +
`part_of_speech` alone is a legal, fully-supported constraint. Use it deliberately,
not casually:

* **Safe** for `word_order` / bare-word `translation` where the prompt varies with the
  answer and the frame imposes no semantic requirement.
* **Dangerous** for any frame with literal text, because at COURSE scope (§1.1) it
  matches every content word in the level — 293 of them in en-nl B1. Every one of
  them must be grammatical in your frame.
* Never combine it with a fixed-English-sentence `translation` (§6.6(b)).

**(d) A narrow lexical tag is a single-member ANCHOR — for `word_order` too, not just
`fill_in_blank`.** The `*_single` / `*_pure` tags exist to pin a slot to exactly one
token. That makes a multi-word frame deterministic and therefore safe: the hero
sentence renders one way, forever. `fill_in_blank` *requires* this (§6.5); `word_order`
and fixed-sentence `translation` merely benefit from it. Single-member anchors serve
exactly one target lexeme each, so keep them a minority of your templates (§8).

**Combining the four:** a healthy pack usually has broad union-tagged slots for the
recognition and production tiers (volume + target coverage) and single-member anchors
for the structured tier (precision), with `part_of_speech` doing the fine filtering in
both.

---

## 4. Legal exercise types

`PRACTICE_EXERCISE_TYPES` (`scripts/compile_content.py:107`) — **exactly six**:

`multiple_choice` · `fill_in_blank` · `word_order` · `translation` ·
`matching_pairs` · `listen_select`

Anything else (including `writing_prompt`, `dialogue_response`, `listen_type`,
`reading_comprehension`, `speak_repeat`) is hand-authored lesson content only and is
rejected by the compiler in a practice pack.

Tier membership (`service.py:46-48`), which is what the checkpoint's difficulty bands
cycle through:

| Tier | Types | Band that tries it first |
|---|---|---|
| recognition | `multiple_choice`, `listen_select` | mastery 0.0 |
| structured | `word_order`, `matching_pairs`, `fill_in_blank` | mastery 0.5 |
| production | `translation` | mastery 0.8 |

---

## 5. `answer_derivation` kinds

`PRACTICE_ANSWER_KINDS` — exactly five:

| kind | Shape | Produces | Use with |
|---|---|---|---|
| `slot_text` | `{kind: slot_text, slot: item}` | the lexeme's `token` | `translation` (bare-word), `fill_in_blank` (**mandatory**) |
| `slot_gloss` | `{kind: slot_gloss, slot: item}` | the lexeme's `english_gloss` | `multiple_choice`, `listen_select` |
| `render_frame` | `{kind: render_frame, frame: {text, language_code, direction}}` | the rendered sentence | `word_order`, sentence `translation` |
| `ordered_slot_texts` | `{kind: ordered_slot_texts, slots: [a, b, c]}` | list of tokens | `word_order` (rare; prefer `render_frame`) |
| `matching_pairs` | `{kind: matching_pairs, slots: [first, ...]}` | `{token: english_gloss}` | `matching_pairs` (**mandatory**) |

Additive flag: `interchangeable: true` on a `fill_in_blank`'s `slot_text` derivation
accepts every candidate still matching that slot. **Only** set it when you have
confirmed by hand that every pool member is a true synonym in that exact frame
(je/jij, alsjeblieft/alstublieft). Never use it to paper over an open-vocabulary slot.

Hard compiler rules:

* `fill_in_blank` **must** use `slot_text`, and the blanked slot **must** appear as a
  placeholder in `frame.text`.
* `translation`'s answer language must deterministically be the pack's
  `target_language` — i.e. `slot_text` on a slot whose `language_code` is the target,
  or `render_frame` whose frame's `language_code` is the target.

---

## 6. Per-type rules and the defects each type is prone to

### 6.1 `multiple_choice` — recognition

```yaml
  type: multiple_choice
  frame: {text: '{item}', language_code: nl, direction: ltr}
  slots:
    item: {language_code: nl, part_of_speech: [noun, verb, adjective],
           agreement_tags: {semantic: job_interview_vocab_pure}}
  answer_derivation: {kind: slot_gloss, slot: item}
```

* **≥3 distinct answer values within the UNIT's own lexemes.** `build_prompt()`
  returns `None` below 3 options and distractors come only from the same slot's
  constraints (`_distractor_values`) — there is no language-only fallback.
* Avoid `proper_noun` in the pool: `Nina → "Nina"` / `Bloem → "Bloem"` are self-glosses
  and make a nonsense question.
* Duplicate `english_gloss` values inside one pool collapse via `dict.fromkeys` and
  can drop you below 3 options. Check the glosses, not just the token count.
* **Defect classes:** 1.18 (cross-course-level tag reuse silently under-counts
  candidates — filter by `level` before trusting a pool), 1.5 (never let an internal
  snake_case token reach `options`).

### 6.2 `listen_select` — recognition, audio

Same shape as `multiple_choice`, `type: listen_select`. The rendered frame becomes
`audio_text`.

* **`tts_actually_configured(target_language)` must be true or `_material()` deletes
  the template entirely.** Right now: `nl` ✅ and `en` ✅ (Google credentials live);
  **`fa` ❌** (Azure is wired but `AZURE_SPEECH_KEY` is UNSET) and **`prs` ❌** (no
  provider at all). **Author ZERO `listen_select` for `en-fa` and `en-prs`** — it is
  pure dead weight that steals recognition-tier budget. `fa-en` / `prs-en` / `nl-en`
  target English, so `listen_select` is fine there.
* **Defect 1.22 (CONFIRMED-RECURRING, ≥52 instances):** a distractor must never be
  something the tested speaker says anywhere in that audio. In a generated pack the
  audio is a single rendered frame, so the practical form of the rule is: **no
  distractor may be a substring/other word of the rendered frame.** Bare-word frames
  (`'{item}'`) are inherently safe; sentence frames are not — check every literal word
  in the frame against the slot's candidate pool.
* Defect 1.3 / AUTHORING_GUIDE §14: never ship an audio-only prompt with no working
  audio.

### 6.3 `matching_pairs` — structured

```yaml
  type: matching_pairs
  frame: {text: '{first} · {second} · {third} · {fourth} · {fifth} · {sixth}', ...}
  slots: {first: &w {...}, second: *w, third: *w, fourth: *w, fifth: *w, sixth: *w}
  slot_relations: [{kind: distinct, slots: [first, second, third, fourth, fifth, sixth]}]
  answer_derivation: {kind: matching_pairs, slots: [first, second, third, fourth, fifth, sixth]}
```

* **6 slots is the standard; 6–12 is the AUTHORING_GUIDE §16 range. Never 2–4.**
  (Defect 1.19.) Every slot must be listed in `answer_derivation.slots` and in a
  `distinct` relation, or `build_prompt()` rejects the instance when two slots sample
  the same lexeme.
* The pool needs **≥ (number of slots) distinct tokens among the UNIT's lexemes**, or
  the template never generates.
* **Left = target-language token, right = `english_gloss`.** Duplicate RIGHT values
  are legal and fine (many→one is valid pedagogy). **Confusable rights are not:** if
  two pool members have interchangeable glosses ("a polite way to ask…" / "a polite way
  to request…") the exercise is unanswerable. Singular/plural pairs
  (`vaardigheid` "skill" / `vaardigheden` "skills") are acceptable discriminations;
  true paraphrases are not.
* **Case-duplicate trap (real, found in en-nl a2_unit77):** a course-wide tag can
  contain both `retourbeleid` and `Retourbeleid` with the same gloss — two effectively
  identical cards in one exercise. Prefer a `*_pure` tag when one exists; otherwise
  check the pool for case duplicates by hand.
* **Defect classes:** 1.8 (left/right mismatch — n/a for generated packs but the
  reason the rule exists), 1.19, 1.7.

### 6.4 `word_order` — structured

```yaml
  type: word_order
  frame: {text: Ik wil graag {item} voor deze vacature., language_code: nl, direction: ltr}
  slots: {item: {language_code: nl, part_of_speech: verb, agreement_tags: {semantic: job_interview_vocab_pure}}}
  answer_derivation:
    kind: render_frame
    frame: {text: Ik wil graag {item} voor deze vacature., language_code: nl, direction: ltr}
```

* The learner sees the frame rendered with **`english_gloss`** substituted for each
  slot (the backend's hint line, asterisk-emphasised), and a shuffled word bank built
  from the `render_frame` answer. So: **every literal word in the frame stays in the
  target language and every slot becomes English.**
* **No candidate floor** — `word_order` and `translation` are the two safe types when
  a tag crosses the A1/A2 boundary (AUTHORING_GUIDE §18).
* **Every pool member must be grammatical in the frame — judged at COURSE scope, not
  unit scope (§1.1).** `Kunt u {weekday} om tien uur langskomen?` is safe because
  every weekday fits; `afspraak voor een {any noun}?` is not. Three shipped frames
  were checked at unit scope only and turned out ungrammatical once Endless Practice
  widened the pool to the whole course. If you widened a slot with a tag union
  (§3.1a), re-read the frame against the **widened** pool, then again at course scope.
* **Defect 1.14 (self-reference):** the frame's literal text must not contain any of
  its own slot's candidate values ("It's ten past {item}" where `ten` is a candidate).
  Also COURSE-scoped. `scripts/_practice_content_integrity_check.py` detects this —
  run it (§9), **but it skips `b1_`/`b2_` packs entirely** (§9 step 2), so on a B1/B2
  pack you must do this check by hand.
* Defect 1.11: RTL tile assembly — see §7.

### 6.5 `fill_in_blank` — structured

```yaml
  type: fill_in_blank
  frame: {text: Ik ben {item} op maandag, woensdag en vrijdag., language_code: nl, direction: ltr}
  slots: {item: {language_code: nl, part_of_speech: adjective,
                 agreement_tags: {semantic: job_beschikbaar_single}}}
  answer_derivation: {kind: slot_text, slot: item}
```

* **The compiler HARD-FAILS a single-slot `fill_in_blank` whose real course-wide
  candidate pool has more than one distinct token** unless
  `interchangeable: true` (AUTHORING_GUIDE §17, defects 1.16/1.17). Note **course-wide**,
  not unit-scoped — the check pools every level. In practice this means: use a
  single-member anchor tag (the `*_single` convention), or narrow with `part_of_speech`
  until exactly one token matches.
* **The frame must have visible text besides the blank** (AUTHORING_GUIDE §13, defect
  class shipped across six packs). `frame: {text: '{item}'}` masks to a bare `___`.
  `build_prompt()` rejects it at runtime, but don't author it.
* Because a single-member slot serves exactly one target lexeme, `fill_in_blank`
  templates fire rarely in a checkpoint. Use them for precision, not for volume — and
  never as your only structured type.

### 6.6 `translation` — production

Two safe shapes, and only two:

**(a) Bare-word — high variety, the production workhorse.**
```yaml
  frame: {text: '{item}', language_code: en, direction: ltr,
          slot_rendering: {item: english_gloss}}
  slots: {item: {language_code: nl, part_of_speech: [noun, adjective],
                 agreement_tags: {semantic: experience_and_skills}}}
  answer_derivation: {kind: slot_text, slot: item}
```
The learner sees the English gloss and types the target word. Safe with a broad pool
because the prompt varies with the answer.

**(b) Fixed sentence — deterministic, one item.**
```yaml
  frame: {text: I have experience with customer contact., language_code: en, direction: ltr}
  slots: {item: {language_code: nl, part_of_speech: noun,
                 agreement_tags: {semantic: job_klantcontact_single}}}
  answer_derivation:
    kind: render_frame
    frame: {text: Ik heb ervaring met {item}., language_code: nl, direction: ltr}
```
**Only valid when the slot has exactly one candidate.** With a multi-member slot the
fixed English prompt says "volunteer" while the answer may render "employee" —
that is the *underdetermined production prompt* defect (marks correct learners wrong).

* **Typed answers are graded by exact string match after normalization** (Phase C adds
  distance-1 typo tolerance for some languages; fa/prs grade STRICT). Therefore:
  * **CORRECTED 2026-07-22 — this REVERSES the previous instruction. Capitalization
    is NOT a grading hazard in a practice pack.** The old rule said a typed-answer
    slot must never sample a sentence-initial capitalized form because a learner
    typing the lowercase form would be marked wrong. **That is false for practice and
    checkpoint items.** Verified in the code:
    * `grade()` (`backend/app/review/grading.py:612`) takes `case_sensitive=False` by
      default, and `_normalize()` (`:158`) casefolds both sides unless it is True.
    * The practice/checkpoint submit path (`backend/app/api/router.py:2062`) passes
      only `script` and `orthography_strict` — it **never passes `case_sensitive`**.
      Practice and checkpoint answers are therefore always casefolded.
    * `Stel`, `Soms`, `Toch`, `Beste`, `Graag`, `Kun`, `Natuurlijk` and the other
      capitalized-by-position en-nl B1 lexemes are **safe** typed answers. The old
      rule excluded them for no reason and made several thin units look unauthorable.
  * **Still prefer a lowercase citation form — for DATA QUALITY, not for grading.**
    A capitalized citation form displays wrong wherever the token is *shown* rather
    than typed: as a `matching_pairs` left, in the post-answer "correct answer" line,
    and in any frame that renders it mid-sentence. The `backfill_lexemes*.py` scripts
    now fold sentence-initial capitals onto their lowercase citation form
    (`NL_CITATION_FORMS` and its siblings), so in a well-backfilled unit the question
    mostly does not arise. Where a capitalized token *does* survive in your pool,
    check whether the capital is real (proper nouns, `Spaans`, German nouns) — if it
    is, keep it; if it is only sentence position, prefer a `*_pure` tag or a
    `part_of_speech` narrowing, and note it in `review.notes` so the coordinator can
    route a backfill fold. **Do not drop an otherwise-good lexeme over this.**
  * **Known quirk, worth knowing:** `case_sensitive` is a real per-exercise flag, set
    by authors via `feedback_meta` and honoured on the *lesson* exercise paths
    (`router.py:399`, `:912` — it exists for German's `Sie`/`sie`). It is simply not
    wired into the practice path. So the same word can grade case-sensitively in a
    lesson and case-insensitively in Endless Practice. Nothing for you to author
    around; just don't infer practice behaviour from a lesson exercise.
  * **Defect 1.30 (fa/prs harakat) — same correction, found while verifying the
    above.** The old wording said "normalization does not strip short-vowel
    diacritics". It does: `ARABIC_DIACRITIC_CHARS` (U+064B–U+0652 plus superscript
    alef) is in `STRIPPED_FORMATTING_CHARS` (`grading.py:130-139`) and
    `is_invisible_formatting_only_difference()` runs **ahead of every strictness
    branch**, so a harakat-only difference grades `correct` even on an
    `orthography_strict` checkpoint item. Tatweel and the bidi/zero-width marks are
    stripped the same way; ZWNJ is separately allowed to match a space or nothing.
    **Still avoid a diacritized canonical form** — it displays wrong wherever it is
    shown, and Arabic/Persian look-alike letters (ي/ی, ك/ک, ة/ه, ۀ/ه, ى/ی) are
    deliberately *not* forgiven (`is_script_confusion()`), so §7's codepoint-purity
    rules remain hard requirements.
* Defect 1.21 / AUTHORING_GUIDE §12 — multi-clause phrasing variants — does not apply
  to generated packs (there is exactly one derived answer), which is precisely why
  sentence translations must be deterministic.

---

## 7. RTL and script rules (`en-fa`, `fa-en`, `en-prs`, `prs-en`)

* **`direction: rtl` on every block whose `language_code` is `fa`, `prs`, or `ar`;
  `ltr` on `en`.** In an `en-fa` pack the frame is usually `fa`/`rtl` and the
  `feedback_frame` is `en`/`ltr` — they differ within the same template. The compiler
  hard-fails a mismatch.
* **Persian-script codepoint purity (`fa`, `prs` only), compiler-enforced:**
  * Arabic Yeh `ي` U+064A is FORBIDDEN → use Persian Yeh `ی` U+06CC.
  * Arabic Kaf `ك` U+0643 is FORBIDDEN → use Persian Keheh `ک` U+06A9.
  * (Arabic `ar` is the opposite convention and is deliberately not checked.)
* **Dari (`prs`) dialect, defect 1.28:** the register is **Afghan**. 2pl verb endings
  are `-ین` (استین), never the Iranian `-ید`. Cross-check every verb form you write
  into a frame against the unit's own `register_policy`. ~756 replacements across 37
  files were needed the last time this drifted.
* **Register pins:** `fa-en` overlay lane = colloquial spoken Persian
  (می‌شه/می‌کنه/اینجاست, polite شما to the learner). `prs-en` = colloquial Dari
  (می‌تانین/استه). `nl-en` = informal jij. Match the lane you are authoring in.
* **`listen_select`: do not author any for `en-fa` or `en-prs`** (§6.2).
* **Defect 1.30 (harakat) — CORRECTED 2026-07-22.** The old text said normalization
  does not strip short-vowel diacritics; it does (§6.6), so a harakat-only difference
  grades `correct` even under `orthography_strict`. Avoid a diacritized canonical form
  (کِی) anyway — it displays wrong wherever the token is *shown*. What is genuinely
  unforgiving is the letter set: the Arabic/Persian look-alike pairs above are never
  forgiven, so the codepoint-purity rules are hard requirements.
* **Defect 1.29 (homograph collision) — NOT an fa/prs-only problem.** A token with two
  senses (تو = "you" / "in") carries one flat classifier entry, so its tags/gloss leak
  into unrelated frames. The identical failure exists in Latin-script directions
  (en-nl B1 has five, listed in §0.1). **§0.1's rule — read every gloss in the pool —
  is the general form and applies to every direction.** This bullet is only the
  Persian-script instance of it.
* Defect 1.11: RTL word-order tiles — the frontend handles direction; just make sure
  `direction: rtl` is set so it can.

---

## 8. How much is enough — the minimum bars, and why

These are the bars. They are derived from the runtime, then calibrated against a
measurement of all 262 existing packs (2026-07-22).

| Bar | Value | Why |
|---|---|---|
| **Templates per unit** | **≥ 12**, spread over **every lesson that has lexemes** | The checkpoint round-robins targets across lesson buckets; a lesson with no template anchored to it is invisible. 18–19 units currently have <8 templates and produce visibly format-repetitive checkpoints. |
| **Templates per tier** | **≥ 3 recognition, ≥ 3 structured, ≥ 3 production** | `CHECKPOINT_MASTERY_BANDS` cycles 0.0/0.5/0.8, so a 15-item checkpoint asks for 5 recognition-first, 5 structured-first, 5 production-first. A missing tier silently degrades into whichever tier has depth. 77 of 262 existing packs have a tier with <4 distinct items. |
| **Distinct items per tier** | **≥ 12 each** (recognition / structured / production) | 12 is the hard `checkpoint_unavailable` floor and also the point at which a full checkpoint can be drawn from one tier without repeating a prompt. |
| **Distinct items per pack** | **≥ 40** | Gives an honest retake (the recent-signature window holds the previous attempt's 50 items) plus Endless Practice headroom. |
| **Variants per template** | **≥ 5 for at least half your templates** | ~80% of existing templates are "thin" (<20 variants). A template whose slot has 1 candidate yields exactly 1 item forever. Single-member anchors are fine as a minority. |
| **Target-lexeme coverage** | **≥ 60% of the unit's lexemes hostable, and ≥1 hostable lexeme in EVERY lesson, in EVERY tier** | `_generate_target_item()` forces the target into a slot; an unhostable lexeme wastes the attempt and unbalances the lesson stratification. **Corpus median today is 33%** — this is the single biggest quality gap. |
| **`multiple_choice`/`listen_select` pool** | **≥ 3 distinct answer values among the UNIT's lexemes** | `build_prompt()` hard rejection. |
| **`matching_pairs` slots** | **6** (range 6–12) | AUTHORING_GUIDE §16. |

The pilot (`en-nl/a2_unit73.yaml`) hits: 18 templates, 6/6 lessons in all three
tiers, 85% target coverage, capacity R49 / S40726 / P33.

**How to get breadth cheaply — VOCABULARY units:** one broad recognition template +
one broad bare-word translation per lesson, using that lesson's own semantic tag, plus
2–3 `matching_pairs` over a curated content-word tag. That alone reaches ~12
templates, high coverage, and both the recognition and production tiers. Add
`word_order` / `fill_in_blank` on the unit's hero sentences for the structured tier.

**This is a VOCABULARY-unit pattern. It does not survive contact with a grammar
unit — see §8.1 before you apply it.**

### 8.1 Grammar units (most of B1/B2): the per-lesson-tag pattern DOES NOT WORK

A vocabulary unit's lesson teaches ~10–20 content words that share one semantic tag. A
grammar unit's lesson teaches a *structure*, so its per-lesson tag is dominated by
function words (`de`, `een`, `het`, `dat`, `niet`, `als`, `zou`) and carries only 1–3
content words. Measured across all 65 en-nl B1 lessons, 2026-07-22, using the lesson's
own dominant tag with `part_of_speech: [noun, verb, adjective, adverb, phrase]`:

* **27 of 65 lessons yield fewer than 3 distinct glosses** → `build_prompt()` silently
  rejects every `multiple_choice` / `listen_select` instance.
* **47 of 65 yield fewer than 6 distinct tokens** → no `matching_pairs` can generate.
* The `wrapup_production` lesson that closes most B1 units has **1–5 lexemes total**.
* Worst cases are single-lexeme lessons (`past_ability_kon`, `real_conditional`,
  `unreal_present_conditional`, `past_narrative_toen`, `sequencing_eerst_later`).

**None of that is a blocked unit. It is a slot-design problem.** Do this instead:

1. **Union the unit's lesson tags for every recognition and production template**
   (§3.1a). The union of a unit's own lesson tags gives 12–54 distinct content tokens
   for every en-nl B1 unit — comfortably over both floors. Keep the template's
   `lesson_content_key` anchored to a single lesson (that is what the checkpoint's
   lesson stratification round-robins over); it is only the SLOT that widens.
2. **Anchor templates per lesson, pool across the unit.** One template per lesson,
   each `lesson_content_key`-anchored to its own lesson, each with the same
   union-tagged slot. Every lesson stays represented and every slot clears its floor.
3. **Put the grammar itself in the frame, not in the pool.** The point of a grammar
   unit is the structure, so `word_order` and `fill_in_blank` earn their keep here:
   frame the unit's hero construction literally (`Als ik rijk {item}, zou ik een huis
   kopen.`) and let a single-member anchor tag fill the one variable position (§3.1d).
   These two types have **no candidate floor**, so a 1–2 lexeme lesson can still carry
   a real structured-tier template.
4. **`matching_pairs` goes over the unit-wide union, not a lesson tag.** Six pairs is
   the floor; almost no grammar lesson has six content words of its own. Anchor it to
   the richest lesson (the dialogue/reading lesson — those consistently hold 8–20
   lexemes) and pool the union.
5. **Exclude function words with `part_of_speech`, not by hand.** `pronoun`,
   `particle`, `preposition` and `proper_noun` are the noise in a grammar unit's pool;
   `[noun, verb, adjective, adverb, phrase]` is the working content set. Then re-read
   the survivors' glosses (§0.1) — grammar units re-introduce known tokens in new
   senses more often than vocabulary units do, which is exactly how the five en-nl B1
   mis-glosses arose.
6. **Re-check every frame against the WIDENED pool (§1.1).** Unioning tags is what
   makes a frame's grammaticality requirement bite, and Endless Practice widens it
   again to course scope. This is the step the three broken `word_order` frames
   skipped.

Expect a grammar-unit pack to lean structured-heavy and to use more single-member
anchors than the §11 vocabulary pilot does. That is correct, not a shortfall — as long
as each of the three tiers still clears its own bar in the table above.

---

## 9. Self-validation — run ALL of these, report the output

From the repo root (`.content-venv/` has PyYAML):

**1. Compiler validation — must be `0 error(s)`. This is the gate.**

**`--pack` is `nargs='+'`. Pass EVERY pack you authored in ONE invocation.** A single
run costs **~55 s** no matter how many packs you give it (measured 2026-07-22: 53 s
for one pack, 62 s for four) because it re-globs and re-parses the whole realization
tree every time. Eleven sequential runs is ten wasted minutes.

```bash
.content-venv/bin/python scripts/compile_content.py practice-validate \
  --pack docs/content/practice/en-nl/b1_unit01.yaml \
         docs/content/practice/en-nl/b1_unit02.yaml \
         docs/content/practice/en-nl/b1_unit03.yaml \
  --content-root docs/content/realizations
```

* **All packs in one invocation must be the SAME direction.** Mixing them fails with
  `language pair ('en', 'fa') does not match ('en', 'nl')`. One run per direction.
* This also runs the AUTHORING_GUIDE §17 `fill_in_blank` ambiguity hard-fail against
  the real backfill lexeme data. Warnings are not fatal but must be explained in your
  report.

**2. Content-integrity sweep — `grep` for your own file and expect EMPTY output.**

The script prints ~44 lines, most of them pre-existing flags in other packs, so "your
file must not appear" is not something you can eyeball. Pipe it:

```bash
.content-venv/bin/python scripts/_practice_content_integrity_check.py \
  | grep b1_unit01.yaml          # <-- your file(s); expect NO output
```
It takes ~2¼ minutes (it loads all six directions' lexeme pools), so run it once at
the end over all your packs rather than per pack. Catches defect 1.14 (self-reference,
at COURSE scope — see §1.1) and 1.15 (anchor lesson with zero `introduced_tokens`).

* **KNOWN GAP — it globs `a*_unit*.yaml`, so it never reads a `b1_`/`b2_` pack.**
  Confirmed 2026-07-22: 28 B1 packs are already in the corpus and none has ever been
  checked. If your pack is B1/B2 **an empty grep proves nothing** — the file was
  skipped. Until the glob is fixed (not your lane; report it), check defect 1.14 by
  hand: for every `word_order` / fixed-sentence `translation`, list the literal words
  of the frame and confirm none of them is a course-wide candidate value of one of
  that same frame's slots.

**3. `fill_in_blank` ambiguity audit (corpus-wide second opinion).**
```bash
.content-venv/bin/python scripts/_fill_in_blank_ambiguity_check.py
```
Same `a*_unit*.yaml` glob and therefore the same B1/B2 blind spot. The compiler's own
§17 hard-fail in step 1 *does* run on your pack whatever its level, so this step is a
second opinion, not the gate.

**4. Capacity + coverage — the check nothing else does.** `practice-validate` is
*purely static YAML checking*; it never touches a lexeme, so a pack can validate
clean and be completely inert. Run this (paste into the scratchpad and run it) and
report the numbers:

```bash
.content-venv/bin/python - <<'EOF'
import sys, re, random, collections, yaml; sys.path.insert(0, 'scripts')
PACK = 'docs/content/practice/en-nl/a2_unit73.yaml'   # <-- your pack
MODULE = 'backfill_lexemes_en_nl'                     # <-- your direction's backfill
LEVEL = 'a2'                                          # <-- your CEFR level
UNIT = 'unit73'                                       # <-- your unit
TTS = True   # True for target nl/en; False for target fa/prs
R=('multiple_choice','listen_select'); S=('word_order','matching_pairs','fill_in_blank'); P=('translation',)
def av(v): return set(v) if isinstance(v,list) else {v}
def lm(l,c):
    if l['language_code']!=c.get('language_code'): return False
    if not (av(c.get('part_of_speech'))&av(l['part_of_speech'])): return False
    at=l.get('agreement_tags') or {}
    return all(t in at and (av(r)&av(at[t])) for t,r in (c.get('agreement_tags') or {}).items())
# '.{LEVEL}.{UNIT}.', NOT '.{UNIT}.' -- unit numbers repeat at every CEFR level and
# the loose filter silently merges them (en-nl unit01: 154 lexemes instead of 79).
lex=[s for s in __import__(MODULE).iter_specs() if f'.{LEVEL}.{UNIT}.' in s['lesson_content_key']]
pack=yaml.safe_load(open(PACK)); T=[t for t in pack['templates'] if TTS or t['type']!='listen_select']
lessons={s['lesson_content_key'] for s in lex}
print(f'{len(T)} live templates, {len(lex)} unit lexemes, {len(lessons)} lessons with lexemes')
for label,tier in (('ALL',None),('recognition',R),('structured',S),('production',P)):
    ts=[t for t in T if tier is None or t['type'] in tier]
    hosted={s['token'] for s in lex if any(any(lm(s,c) for c in t['slots'].values()) for t in ts)}
    les={s['lesson_content_key'] for s in lex if any(any(lm(s,c) for c in t['slots'].values()) for t in ts)}
    print(f'  {label:12s} templates={len(ts):2d} hosts {len(hosted):3d}/{len(lex)} lexemes '
          f'({(len(hosted)/len(lex) if lex else 0):.0%}), lessons {len(les)}/{len(lessons)}')
for t in T:
    n=[sum(1 for l in lex if lm(l,c)) for c in t['slots'].values()]
    if min(n)==0: print(f'  !! DEAD TEMPLATE (zero unit-scoped candidates): {t["content_key"]}')
    elif t['type'] in R and min(n)<3: print(f'  !! <3 candidates for {t["type"]}: {t["content_key"]}')
EOF
```

Acceptance: **no `!!` lines**, `ALL` coverage **≥60%**, each of
recognition/structured/production **≥40%**, and **every tier covering every lesson
that has lexemes** (the `lessons N/N` column). The pilot scores ALL 85% /
recognition 83% / structured 61% / production 54%, 6/6 lessons in every tier.

**5. Course-scope frame re-read — by hand, nothing automates it.** This script
measures UNIT scope only, which is the right scope for the floors but the wrong one
for grammaticality (§1.1). For every `word_order` frame and every fixed-sentence
`translation`, drop the `f'.{LEVEL}.{UNIT}.'` filter from the `lex=` line above (keep
`.{LEVEL}.`, so you stay inside the one `Course`), re-list that slot's candidates, and
confirm **every** one of them is grammatical in the frame and is not a literal word of
the frame. Report the course-scope candidate count per sentence frame.

**Do NOT run `scripts/verify.sh` and do NOT edit `scripts/manifest.d/practice/*.txt`** —
`verify.sh` reads the manifest, and the manifest belongs to the coordinator.

---

## 10. DO NOT — the historical defects, in one list

1. **DO NOT** author a pack for a unit with zero lexemes. Green compile, dead
   checkpoint. (§0)
2. **DO NOT** constrain a slot to vocabulary taught in an *earlier* unit. It works in
   Endless Practice and is invisible to the checkpoint. This is the #1 cause of the
   current ~48% checkpoint coverage — 7 shipped packs are *guaranteed* to 409 today
   (`fa-en`/`prs-en`/`nl-en` a1_unit14 & a1_unit17, `fa-en` a1_unit39) purely from
   this.
3. **DO NOT** author `listen_select` for `en-fa` or `en-prs`. `AZURE_SPEECH_KEY` is
   unset and Dari has no voice at all; `_material()` deletes those templates. (1.3)
4. **DO NOT** let a `listen_select` distractor be a word the audio itself contains.
   (1.22 — ≥52 confirmed instances, still unprevented by tooling.)
5. **DO NOT** ship a `matching_pairs` with fewer than 6 pairs, or with two pool
   members whose English glosses are interchangeable, or with a case-duplicate pair
   (`retourbeleid`/`Retourbeleid`). (1.19, §16)
6. **DO NOT** author a `fill_in_blank` whose slot has >1 course-wide candidate without
   `interchangeable: true` (compiler hard-fail), and never `frame: {text: '{item}'}` —
   masking leaves a bare `___`. (1.16, 1.17, §13)
7. **DO NOT** put a slot's own candidate value in the literal text of the same frame,
   **judged at COURSE scope, not unit scope** ("It's ten past {item}" with `ten` in
   the pool). Same for "every pool member must be grammatical in the frame". (1.14,
   §1.1)
8. **DO NOT** anchor `lesson_content_key` to a lesson with zero `introduced_tokens`.
   (1.15)
9. ~~DO NOT let a typed-answer slot sample a sentence-initial capitalized form.~~
   **WITHDRAWN 2026-07-22 — this rule was factually wrong.** Practice and checkpoint
   answers are casefolded (`grade()` defaults `case_sensitive=False`; the practice
   submit path never passes it), and harakat/tatweel/bidi marks are stripped from both
   sides before comparison. A capitalized or diacritized form is a **safe** typed
   answer. Prefer the lowercase, undiacritized citation form for DISPLAY quality, and
   never drop an otherwise-good lexeme over it. What *is* still unforgiving: the
   Arabic/Persian look-alike letters (§7). (§6.6)
10. **DO NOT** author a slot pool without reading every member's `english_gloss`
    against what the unit actually teaches. A stale gloss is shown to the learner as
    the correct answer and no validator can see it. (1.29 generalized, §0.1)
11. **DO NOT** write a fixed-English-sentence `translation` over a multi-member slot —
    that is the underdetermined-production-prompt defect that marks correct learners
    wrong.
12. **DO NOT** reuse a tag across the A1/A2/B1 course boundary for
    `multiple_choice`/`listen_select`. Separate `Course` rows; the pool is smaller than
    it looks. `word_order`/`translation` are floor-free and safe. (1.18, §18)
13. **DO NOT** leak internal snake_case tokens (`null_subject`, `both_speakers`) or
    the word "reviewed" into any learner-facing string. (1.5)
14. **DO NOT** write bare `yes`/`no`/`true`/`false` as a YAML string value. (1.12)
15. **DO NOT** mismatch `direction` and `language_code`, or use Arabic Yeh/Kaf in
    fa/prs. (§7)
16. **DO NOT** mix Iranian and Afghan verb endings inside one `prs` pack. (1.28)
17. **DO NOT** edit `scripts/manifest.d/practice/*.txt`, `scripts/backfill_lexemes*.py`,
    or any file outside your own pack. Many agents are running concurrently.
18. **DO NOT** declare a decorative slot the frame never uses just to inflate target
    coverage — the item then credits the wrong lexeme in the learner's SRS.
19. **DO NOT** measure a unit's lexeme pool with a bare `f'.{UNIT}.'` filter — unit
    numbers repeat at every CEFR level and the loose form merges them. Always
    `f'.{LEVEL}.{UNIT}.'`. (§0, §9)
20. **DO NOT** apply §8's per-lesson-tag breadth pattern to a grammar unit. Union the
    unit's lesson tags instead. (§3.1, §8.1)

---

## 11. Worked example

The complete pilot pack is **`docs/content/practice/en-nl/a2_unit73.yaml`** (18
templates, all 6 lessons, every type, 0 compiler errors). Read it as the canonical
example — but note it is a **vocabulary** unit (a job-application topic with 41
lexemes across 6 lessons), so every slot below uses a single scalar semantic tag. A
grammar unit cannot be authored this way; see §8.1 and §3.1. Its structure:

| Lesson | Templates |
|---|---|
| lesson01 `ik_wil_solliciteren` | `choose.001` MC (broad, 6 candidates) · `order.002` word_order (hero sentence, single-member verb slot) · `translate.003` bare-word translation (6) · `match.004` matching_pairs ×6 |
| lesson02 `ik_bel_over_de_vacature` | `choose.001` MC (4) · `order.002` word_order over `weekday_pure` (3 grammatical variants) · `translate.003` bare-word (2) |
| lesson03 `mijn_ervaring_en_vaardigheden` | `match.001` matching_pairs ×6 over the curated `job_interview_vocab_pure` (10 nouns) · `choose.002` MC (8) · `translate.003` bare-word (7) |
| lesson04 `ben_ik_beschikbaar` | `fill.001` fill_in_blank (`job_beschikbaar_single`, exactly 1 course-wide candidate) · `listen.002` listen_select (12) · `translate.003` bare-word (5) |
| lesson05 `een_vacature_lezen` | `fill.001` fill_in_blank (`job_klantcontact_single`) · `translate.002` fixed-sentence translation (single-member ⇒ deterministic) · `translate.003` bare-word (12) |
| lesson06 `het_sollicitatiegesprek` | `choose.001` MC (19) · `match.002` matching_pairs ×6 (15) |

Minimal skeleton to copy:

```yaml
schema_version: '1.0'
pack_key: practice.<dir>.<level>.unit<NN>
source_language: <src>
target_language: <tgt>
unit_content_key: <tgt>.<level>.unit<NN>.<slug>
review:
  status: unreviewed
  fresh_context: 'false'
  notes: >-
    What you authored, which tags you used and why, the measured
    capacity/coverage numbers, and what a reviewer must double-check.
tag_schema:
  part_of_speech: [symbol, noun, proper_noun, pronoun, verb, adjective, adverb,
                   preposition, particle, phrase]
  agreement_tags:
    semantic: [<every semantic tag any slot below uses>]
templates:
- content_key: practice.<dir>.<tgt>.<level>.unit<NN>.lesson01.choose.001
  lesson_content_key: <tgt>.<level>.unit<NN>.lesson01.<slug>
  type: multiple_choice
  frame: {text: '{item}', language_code: <tgt>, direction: <ltr|rtl>}
  slots:
    item:
      language_code: <tgt>
      part_of_speech: [noun, verb, adjective]
      # Vocabulary unit: one broad lesson tag. Grammar unit: a LIST unioning the
      # unit's lesson tags (OR-matched) -- see §3.1/§8.1. Omitting `semantic:`
      # entirely is also legal, but pools the whole course at Endless-Practice
      # scope (§1.1) -- only for frames with no literal text.
      agreement_tags: {semantic: <a broad lesson/unit tag, or a list of them>}
  answer_derivation: {kind: slot_gloss, slot: item}
  feedback_frame:
    text: '{item} is from this lesson.'
    language_code: <src>
    direction: <ltr|rtl>
```

---

## 12. What to report back to the coordinator

1. The pack path(s).
2. The exact `practice-validate` output (must be `0 error(s)`) — one invocation
   covering all your packs (§9 step 1).
3. The capacity/coverage numbers from §9 step 4 (templates per tier, coverage per
   tier, lessons covered). Confirm you used the `f'.{LEVEL}.{UNIT}.'` filter.
4. The `grep`-ed `_practice_content_integrity_check.py` result (§9 step 2) — and, if
   your pack is `b1_`/`b2_`, an explicit statement that the script's `a*_unit*.yaml`
   glob **skipped** your file plus your by-hand defect-1.14 check.
5. The §9 step 5 course-scope frame re-read: per sentence frame, the course-scope
   candidate count and your confirmation that every candidate is grammatical.
6. **Any mis-glossed lexeme you found (§0.1)** — token, the gloss it carries, the
   sense the unit actually teaches, and whether you excluded it or worked around it.
   The coordinator routes these to the backfill lane.
7. **The manifest line the coordinator must add** — the pack path appended to the
   existing `<direction>|…` line in `scripts/manifest.d/practice/*.txt`. Do not edit it
   yourself.
8. Anything you had to leave undone (e.g. a lesson with no usable tag, a unit that
   turned out to be backfill-blocked).
