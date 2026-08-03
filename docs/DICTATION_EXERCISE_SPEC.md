# Dictation exercise type — spec & self-contained build prompt

Status: **SPEC / not yet built** (written 2026-08-02). Owner to schedule.
This doc is self-contained: §1–§9 are the spec; **§10 is a build prompt a
fresh-context Claude can execute if this conversation is gone.** File:line
pointers were mapped against the repo at 2026-08-02 — re-verify them before
editing (code moves).

---

## 1. What it is (pedagogy)

A **dictation** exercise: the learner **hears a TTS-spoken target-language
sentence** (no source text, no word bank — just a play button), **types what
they heard**, and is graded **orthography-strict** (exact spelling; for fa/prs,
script-strict). It trains listening + spelling + orthography simultaneously —
the one modality lingua.com leans on that we lack, and it plays directly into
our existing strengths (orthography-strict grading, script-purity validators,
the custom Perso-Arabic on-screen keyboard).

It is **not** a new UI: it reuses the existing `Translation` component (audio
button + typed input + virtual keyboard). Mechanically it is the existing
`listen_type` exercise (audio prompt → typed target answer) **with strict
grading forced on by type**.

## 2. Scope & key decisions (v1)

- **Course content only, NOT Endless Practice** in v1. Keeping it out of the
  practice engine avoids a much larger surface (`PRACTICE_EXERCISE_TYPES`, the
  practice Literals/gates). Revisit later.
- **Grading is strict-by-TYPE, not merely by an author flag** (recommended). On
  a Latin language like nl, `listen_type` defaults to *typo-tolerant* — which
  would forgive a wrong-spelling and defeat dictation. Force strict by type
  (the same pattern Phase F checkpoints use), so authors can't silently ship a
  tolerant dictation. fa/prs are already strict via `script == "arabic"`.
  - *Alternative considered:* don't add a type at all — author `listen_type`
    with `orthography_strict: true`. Rejected for v1: it loses type-enforced
    strictness (one missing flag ships a broken dictation) and the semantic/
    analytics distinction. A distinct `dictation` type + a compiler check is
    safer. (If the owner prefers zero new type, that's a valid smaller build —
    call it out.)
- **nl-first. Do NOT author dictation for prs (or any language where
  `tts_actually_configured()` is False).** Dari has zero TTS from any provider,
  so a dictation item there is an unanswerable silent play button — the exact
  "unanswerable audio" class the codebase has been bitten by twice. fa only once
  a real `AZURE_SPEECH_KEY` is provisioned. See §5.

## 3. Authoring shape (content YAML)

Authored identically to `listen_type`. **Realization** (target-language,
declares the audio + the sentence):

```yaml
# in docs/content/realizations/nl/<unit>.yaml, inside a lesson's exercises:
- content_key: nl.b1.unitNN.lessonMM.exerciseKK.dictation_afspraak
  type: dictation
  tested_text: "Ik heb morgen een afspraak bij de dokter."   # the spoken+typed sentence
  media_asset_key: nl.b1.audio.afspraak_dokter.01            # optional; TTS'd from tested_text if absent
  prompt: {target_blocks: []}                                # NO source text — only the audio button shows
```

Declare the audio in the realization's `media_assets:` block (same as
`listen_select`), `status: pending_generation` (runtime TTS covers it until a
human clip is uploaded):

```yaml
media_assets:
  - {content_key: nl.b1.audio.afspraak_dokter.01, language: nl,
     text: "Ik heb morgen een afspraak bij de dokter.", voice_hint: neutral_adult,
     status: pending_generation}
```

**Overlay** (source-direction, e.g. `en-nl`): supplies the **accepted typed
answer** and MUST set strict + MUST NOT carry `options`/`distractors`.
**NOTE (corrected 2026-08-03): the en-nl overlay file is a MAPPING keyed by
`content_key`, not a list** — nest these fields directly under the content_key
(no leading `- content_key:`), matching the neighboring entries in that file:

```yaml
- content_key: nl.b1.unitNN.lessonMM.exerciseKK.dictation_afspraak
  instruction: ""                       # keep empty so nothing but audio shows
  correct_response: "Ik heb morgen een afspraak bij de dokter."   # == tested_text for true dictation
  orthography_strict: true              # belt-and-suspenders even with type-forced strict
  feedback: "..."                       # optional post-answer explanation
```

- Accepted answer == the spoken sentence. Multiple accepted variants are
  possible via `accepted_answers` (compiles to `{canonical, accepted}`), but a
  true dictation should accept exactly one spelling.
- **No `options`/`distractors`** (that's the listen_select/MC path). The
  distractor/option validators correctly skip an option-less item.

## 4. Grading rules

- Route `dictation` through the free-text grader (`grade_answer`) → strict
  spelling. fa/prs: `script == "arabic"` → script-strict, script-confusion
  hard-block already applies. nl/Latin: **must be forced strict** (see §2).
- Recommended implementation: make `grade_answer` treat `dictation` as
  `orthography_strict = True` by default unless the author explicitly set
  `orthography_strict: false`. Mirror the checkpoint precedent
  (`router.py` forces strict for `source == "checkpoint"`).
- Grade call sites that must apply the strict-by-type rule: `exercise_answer()`
  and `review_answer()` in `backend/app/api/router.py` (practice too, but v1
  excludes practice).

## 5. TTS gating (unanswerable-audio guard)

- `tts_actually_configured(language_code)` (`backend/app/services/tts.py`)
  returns True only when the language has real provider credentials on this
  deploy. Client `speak()` degrades honestly: recorded MP3 → Google/Azure →
  browser → "no voice available" label.
- **nl:** Google TTS configured → works.
- **prs:** zero TTS anywhere → **do not author dictation for prs.** Add a
  compiler validator (or authoring rule) that rejects/omits a `dictation` item
  for any target language where TTS is unavailable, mirroring the listen_select
  generation gate. At minimum, the authoring guide entry must say "dictation
  requires a configured TTS voice for the target language; nl only for now."
- **fa:** eligible only after `AZURE_SPEECH_KEY` is provisioned; excluded until
  then.

## 6. UX

Reuses `frontend/src/components/exercises/Translation.tsx` **verbatim** — it
already renders a `SpeakButton` (tap to (re)hear), a typed `<input>` with RTL
`dir` derived from the answer script, and the `VirtualKeyboard` for non-Latin
scripts. With `target_blocks: []` and an empty instruction, only the audio
button shows — the desired "no source text" behavior. **No new component.**

## 7. Integration map — the registration checklist (highest-risk section)

A new exercise type must be registered in **every** row below or it breaks
somewhere the compiler/tsc cannot see (the project once shipped six
rendering-but-unregistered types). Re-verify each file:line before editing.

| # | File (≈line at 2026-08-02) | Add | Lane | Guarded? | Failure if missed |
|---|---|---|---|---|---|
| 1 | `backend/app/models/entities.py:34-53` — `ExerciseType` enum | `dictation = "dictation"` | Codex | ❌ | import 422 / can't persist |
| 2 | `backend/app/models/entities.py:280-288` — `ck_exercises_type` check constraint **+ Alembic migration** to alter it (fresh-migrate-safe) | new value in constraint | Codex | ❌ | Postgres rejects the row |
| 3 | `scripts/compile_content.py:280-300` — `VALID_EXERCISE_TYPES` | `"dictation"` | Codex | ✅ (compiler) | compiler hard error |
| 4 | `scripts/compile_content.py:3619-3623` — listen-type audio block in `compile_exercise` | add `"dictation"` | Codex | ❌ | no `audio_text` emitted → silent, unanswerable |
| 5 | `packages/shared/src/api/types.ts:74-93` — `ExerciseType` union | `\| "dictation"` | Claude | ✅ (tsc) | tsc break; drives #6/#7 |
| 6 | `frontend/src/components/exercises/ExerciseRenderer.tsx:18-52` — switch | `case "dictation":` → `<Translation/>` | Claude | ✅ (via #7) | falls to `unsupported_type` |
| 7 | `frontend/src/components/exercises/ExerciseRenderer.test.tsx:36-80` — `PROMPTS: Record<ExerciseType, ExercisePrompt>` | a `dictation:` prompt entry | Claude | ✅ (self) | **the guardrail** — #5 makes this fail to compile until an entry exists, then fail until #6 routes it |
| 8 | `backend/app/review/grading.py:31-48` — `FREE_TEXT_EXERCISE_TYPES` | `"dictation"` | Codex | ❌ | typed answer never runs strict/script grading (wrong grades) |
| 9 | `docs/CONTRACT.md:52-58` (+ note ~:70-81) | `dictation` (≈`listen_type`, strict) | Claude | ❌ | contract drift |

**The four with no automated guard — enumerate by hand, they are the risk:**
#1 (backend enum), #2 (DB constraint + migration), #4 (compiler audio-emit),
#8 (grading bucket). The frontend trio #5→#6→#7 is self-enforcing at
compile/test time (adding to the union forces the renderer case and the
`PROMPTS` test entry).

**Consciously NOT touched in v1** (course-only): `PRACTICE_EXERCISE_TYPES`
(`compile_content.py:107-114`), `PracticeTemplate/ItemExerciseType` Literals
(`backend/app/schemas/api.py:225-226`), `RECOGNITION_TYPES`/practice gate
(`backend/app/practice/service.py:47,497`). Touch only if dictation later joins
Endless Practice.

## 8. Build order & lane split

1. **Codex (backend + compiler, one dispatch):** #1 enum, #2 constraint +
   Alembic migration (fresh-migrate-safe), #3 `VALID_EXERCISE_TYPES`, #4
   compile audio block, #8 `FREE_TEXT_EXERCISE_TYPES` + the strict-by-type
   grading change. Coordinator applies + runs migration + pytest (isolated DB).
2. **Claude (frontend + contract):** #5 shared union, #6 renderer case, #7
   `PROMPTS` test entry, #9 CONTRACT.md. Run the full `npm run build`.
3. **Content (both):** author a **pilot nl unit** with 2–3 dictation items
   (realization + overlay + `media_assets`), fresh-context review, compile.
   Add a `docs/content/AUTHORING_GUIDE.md` entry (shape + the "TTS-configured
   target only / nl for now" rule).
4. **Coordinator:** import to dev DB, **live-browser verify with a fresh
   account** — the audio plays, typing the exact sentence grades correct, a
   one-char misspelling grades incorrect on nl (proves strict), and a prs
   dictation is absent/blocked (proves the TTS gate).

## 9. Verification bar (non-negotiable)

- Compiler green (incl. the new type validating, and the dictation-needs-TTS
  validator).
- Backend pytest green on an **isolated test DB** (never dev), incl. a grading
  test proving `dictation` is strict on a Latin target.
- Full `npm run build` (`tsc -b && vite build`) — not `--noEmit`.
- **Live browser**, fresh account: audio plays; exact answer ✓; 1-char typo ✗
  on nl; virtual keyboard + RTL correct if a fa pilot is ever added.

---

## 10. BUILD PROMPT (paste to a fresh-context Claude if this conversation is gone)

> **Task: build a `dictation` exercise type for Lingo²** (repo:
> `/Users/raminazizi/dev/LingoSquared`). Read `docs/DICTATION_EXERCISE_SPEC.md`
> in full first — it is the spec. Also read root `CLAUDE.md`, `backend/CLAUDE.md`,
> `frontend/CLAUDE.md`, `docs/content/CLAUDE.md`, and `docs/CONTRACT.md`.
>
> **What dictation is:** learner hears a TTS target-language sentence (no source
> text), types it, graded orthography-strict. It reuses `Translation.tsx`
> verbatim; it is `listen_type` with strict grading forced by type.
>
> **Lane rules (from CLAUDE.md):** backend/app/**, Alembic migrations, and
> `scripts/compile_content.py` are **Codex's lane** — dispatch those via the
> codex-companion, verify yourself (Codex has no Docker; you run the migration +
> pytest). Frontend/src/**, `docs/CONTRACT.md`, orchestration, and all
> verification are **yours**. Content is authored by both, through a **separate
> fresh-context review** before import.
>
> **Do this, in order:**
> 1. Dispatch **Codex** to make the backend/compiler changes — spec §7 rows
>    #1,#2,#3,#4,#8 and the strict-by-type grading change in §4. Row #2 needs a
>    **fresh-migrate-safe** Alembic migration altering `ck_exercises_type`.
>    Diff Codex's output before applying (never trust its self-report). Apply,
>    run `alembic upgrade head`, run pytest on an **isolated test DB** (recipe in
>    `backend/CLAUDE.md` — NEVER the dev DB; a prior session wiped it).
> 2. Make the **frontend/contract** changes yourself — spec §7 rows #5,#6,#7,#9.
>    Run the FULL `npm run build`. The `ExerciseRenderer.test.tsx` `PROMPTS`
>    record is the guardrail: it won't compile until #5+#6+#7 are all done.
> 3. Author a **pilot nl unit** with 2–3 dictation items (realization + overlay
>    + `media_assets`, shape in spec §3). Route it through a **fresh-context
>    review** agent. Add the authoring-guide entry incl. the **"dictation only
>    for TTS-configured target languages; nl only for now — NOT prs"** rule
>    (spec §5).
> 4. Import to the local dev DB and **verify in a live browser with a fresh
>    account** (spec §9): audio plays; exact answer grades correct; a one-char
>    misspelling grades **incorrect on nl** (proves strict-by-type); confirm no
>    dictation is authored/served for prs.
>
> **Registration footgun:** the four backend rows (#1,#2,#4,#8) have **no
> automated cross-check** — miss one and it breaks silently. Tick every row of
> the §7 table explicitly. **Verification bar is non-negotiable** (spec §9):
> compiler green, pytest green on an isolated DB, full `npm run build`, live
> browser. Reading a diff is not verification.

---

## 11. Related future work (specced separately if pursued)

From the same lingua.com comparison — not part of the dictation build:

- **Graded reading / "stories" track:** upgrade `reading_comprehension` (today
  embedded items) into a leveled long-form reading experience — audio narration
  + tap-any-word-to-gloss (reuse per-lexeme gloss data) + comprehension checks.
  Larger; needs its own spec.
- **Skill-targeted practice:** filter Endless Practice by skill/type, and route
  checkpoint `weak_outcomes` into targeted drills. Mostly a filter over data we
  already tag.

Both lean on audio too, so both are gated behind the same fa/prs TTS fix
(self-hosted Piper/XTTS or the Azure Farsi key) for the RTL pair.
