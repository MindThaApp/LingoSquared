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
UNIT      = 'unit73'    # <-- your unit, e.g. 'unit05'
MODULES = {'en-fa':'backfill_lexemes','fa-en':'backfill_lexemes_fa_en',
           'en-prs':'backfill_lexemes_en_prs','prs-en':'backfill_lexemes_prs_en',
           'en-nl':'backfill_lexemes_en_nl','nl-en':'backfill_lexemes_nl_en'}
specs = [s for s in __import__(MODULES[DIRECTION]).iter_specs()
         if f'.{UNIT}.' in s['lesson_content_key']]
print(f'{len(specs)} lexemes for {DIRECTION} {UNIT}')
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
| `generate_checkpoint()` (:1455) | calls `_material()` with **only the unit's own lesson ids** | **THE load-bearing rule: every slot must be satisfiable by lexemes THIS UNIT introduces.** A slot tagged with vocabulary taught in an earlier unit has ZERO candidates at checkpoint scope and can never generate. |
| `generate_batch()` / `generate_review_batch()` | calls `_material()` with **every completed lesson** in the course | the same template CAN legitimately draw on earlier units in Endless Practice — that is why so many existing packs look fine there and still fail the checkpoint |
| `_material()` TTS filter | drops **all `listen_select` templates** when `tts_actually_configured(target_language)` is false | see §6.6 — `listen_select` is dead weight for `en-fa` and `en-prs` today |
| `_generate_target_item()` | picks a **target lexeme** first, then forces it into a slot it matches | a template can only ever serve targets that match one of its slots. Narrow single-member slots serve exactly 1 lexeme. **Target coverage matters as much as template count.** |
| `_tier_order(mastery)` | checkpoint cycles fixed bands 0.0 / 0.5 / 0.8 → recognition-first / structured-first / production-first | you need real capacity in **all three tiers**, or the mix collapses into whichever tier has depth |
| `build_prompt()` | rejects `multiple_choice`/`listen_select` with `< 3` distinct options; rejects `fill_in_blank` whose blanked frame has no other visible text; rejects `matching_pairs` whose filled slots collapse to fewer distinct tokens than declared | these are silent rejections — they cost you items with no error anywhere |
| router `:1480` | `if len(items) < 12: 409 checkpoint_unavailable` | the hard bar |

`fill_slots()` returns `None` immediately if **any** declared slot has zero
candidates — one dead slot kills the whole template, not just that slot.

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

**Do NOT edit `scripts/practice_manifest.txt`.** Many agents author packs
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
* **Every pool member must be grammatical in the frame.** `Kunt u {weekday} om tien
  uur langskomen?` is safe because every weekday fits; `afspraak voor een {any noun}?`
  is not.
* **Defect 1.14 (self-reference):** the frame's literal text must not contain any of
  its own slot's candidate values ("It's ten past {item}" where `ten` is a candidate).
  `scripts/_practice_content_integrity_check.py` detects this — run it (§9).
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

* **Typed answers are graded by exact string match** (Phase C adds distance-1 typo
  tolerance for some languages; fa/prs grade STRICT). Therefore:
  * **Never let a typed-answer slot sample a sentence-initial capitalized form.**
    `Kan`, `Typen`, `Vertelt`, `Van`, `Zij`, `Daar`, `Mooi`, `Ervaring`, `Werktijden`
    are all real lexemes in one en-nl unit whose only capital comes from sentence
    position. A learner typing the lowercase form is marked wrong (defect 1.25 —
    case-sensitivity is not modelled). Narrow with `part_of_speech`, or use a `*_pure`
    tag, or check the pool by hand — **course-wide, not just unit-scoped**, because
    Endless Practice uses the whole course pool.
  * Defect 1.30 (fa/prs harakat): never make a diacritic-bearing form the canonical
    typed answer.
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
* **Defect 1.30 (harakat):** fa/prs grade strict and normalization does not strip
  short-vowel diacritics. Never make a diacritized form (کِی) the typed answer.
* **Defect 1.29 (homograph collision):** a token with two senses (تو = "you" /
  "in") carries one flat classifier entry, so its tags/gloss leak into unrelated
  frames. Before using a tag whose pool contains a known homograph, read the actual
  glosses in the §0 dump.
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

**How to get breadth cheaply:** one broad recognition template + one broad bare-word
translation per lesson, using that lesson's own semantic tag, plus 2–3
`matching_pairs` over a curated content-word tag. That alone reaches ~12 templates,
high coverage, and both the recognition and production tiers. Add `word_order` /
`fill_in_blank` on the unit's hero sentences for the structured tier.

---

## 9. Self-validation — run ALL of these, report the output

From the repo root (`.content-venv/` has PyYAML):

**1. Compiler validation — must be `0 error(s)`. This is the gate.**
```bash
.content-venv/bin/python scripts/compile_content.py practice-validate \
  --pack docs/content/practice/en-nl/a2_unit73.yaml \
  --content-root docs/content/realizations
```
This also runs the AUTHORING_GUIDE §17 `fill_in_blank` ambiguity hard-fail against
the real backfill lexeme data. Warnings are not fatal but must be explained in your
report.

**2. Content-integrity sweep — your file must not appear in the output.**
```bash
.content-venv/bin/python scripts/_practice_content_integrity_check.py
```
Catches defect 1.14 (self-reference) and 1.15 (anchor lesson with zero
`introduced_tokens`). It globs the whole practice corpus, so ignore pre-existing
flags in other files; only your own file matters.

**3. `fill_in_blank` ambiguity audit (corpus-wide second opinion).**
```bash
.content-venv/bin/python scripts/_fill_in_blank_ambiguity_check.py
```

**4. Capacity + coverage — the check nothing else does.** `practice-validate` is
*purely static YAML checking*; it never touches a lexeme, so a pack can validate
clean and be completely inert. Run this (paste into the scratchpad and run it) and
report the numbers:

```bash
.content-venv/bin/python - <<'EOF'
import sys, re, random, collections, yaml; sys.path.insert(0, 'scripts')
PACK = 'docs/content/practice/en-nl/a2_unit73.yaml'   # <-- your pack
MODULE = 'backfill_lexemes_en_nl'                     # <-- your direction's backfill
UNIT = 'unit73'                                       # <-- your unit
TTS = True   # True for target nl/en; False for target fa/prs
R=('multiple_choice','listen_select'); S=('word_order','matching_pairs','fill_in_blank'); P=('translation',)
def av(v): return set(v) if isinstance(v,list) else {v}
def lm(l,c):
    if l['language_code']!=c.get('language_code'): return False
    if not (av(c.get('part_of_speech'))&av(l['part_of_speech'])): return False
    at=l.get('agreement_tags') or {}
    return all(t in at and (av(r)&av(at[t])) for t,r in (c.get('agreement_tags') or {}).items())
lex=[s for s in __import__(MODULE).iter_specs() if f'.{UNIT}.' in s['lesson_content_key']]
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

**Do NOT run `scripts/verify.sh` and do NOT edit `scripts/practice_manifest.txt`** —
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
7. **DO NOT** put a slot's own candidate value in the literal text of the same frame.
   ("It's ten past {item}" with `ten` in the pool.) (1.14)
8. **DO NOT** anchor `lesson_content_key` to a lesson with zero `introduced_tokens`.
   (1.15)
9. **DO NOT** let a typed-answer slot (`translation` `slot_text`, `fill_in_blank`)
   sample a sentence-initial capitalized form, or a fa/prs form carrying harakat.
   (1.25, 1.30)
10. **DO NOT** write a fixed-English-sentence `translation` over a multi-member slot —
    that is the underdetermined-production-prompt defect that marks correct learners
    wrong.
11. **DO NOT** reuse a tag across the A1/A2/B1 course boundary for
    `multiple_choice`/`listen_select`. Separate `Course` rows; the pool is smaller than
    it looks. `word_order`/`translation` are floor-free and safe. (1.18, §18)
12. **DO NOT** leak internal snake_case tokens (`null_subject`, `both_speakers`) or
    the word "reviewed" into any learner-facing string. (1.5)
13. **DO NOT** write bare `yes`/`no`/`true`/`false` as a YAML string value. (1.12)
14. **DO NOT** mismatch `direction` and `language_code`, or use Arabic Yeh/Kaf in
    fa/prs. (§7)
15. **DO NOT** mix Iranian and Afghan verb endings inside one `prs` pack. (1.28)
16. **DO NOT** edit `scripts/practice_manifest.txt`, `scripts/backfill_lexemes*.py`,
    or any file outside your own pack. Many agents are running concurrently.
17. **DO NOT** declare a decorative slot the frame never uses just to inflate target
    coverage — the item then credits the wrong lexeme in the learner's SRS.

---

## 11. Worked example

The complete pilot pack is **`docs/content/practice/en-nl/a2_unit73.yaml`** (18
templates, all 6 lessons, every type, 0 compiler errors). Read it as the canonical
example. Its structure:

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
      agreement_tags: {semantic: <a broad lesson/unit tag>}
  answer_derivation: {kind: slot_gloss, slot: item}
  feedback_frame:
    text: '{item} is from this lesson.'
    language_code: <src>
    direction: <ltr|rtl>
```

---

## 12. What to report back to the coordinator

1. The pack path.
2. The exact `practice-validate` output (must be `0 error(s)`).
3. The capacity/coverage numbers from §9 step 4 (templates per tier, coverage per
   tier, lessons covered).
4. Confirmation that `_practice_content_integrity_check.py` did **not** flag your
   file.
5. **The manifest line the coordinator must add** — the pack path appended to the
   existing `<direction>|…` line in `scripts/practice_manifest.txt`. Do not edit it
   yourself.
6. Anything you had to leave undone (e.g. a lesson with no usable tag, a unit that
   turned out to be backfill-blocked).
