# Graded reading track — spec & self-contained build prompt

Status: **SPEC / not yet built** (written 2026-08-03). §1–§9 are the spec; **§10
is a context-cleared build prompt.** File:line pointers mapped 2026-08-03 —
re-verify before editing.

---

## 1. What it is
A leveled **reading** experience: the learner reads a short passage (a few
sentences → a paragraph, growing with CEFR), can **hear it narrated**, can **tap
any glossed word to see its meaning in context**, then answers a few
**comprehension questions**. The reading modality lingua.com leans on that we
under-serve (we have `reading_comprehension` items but no first-class *reading*
surface with in-passage word help).

## 2. The key finding: ~70% already exists
Do NOT build a new exercise type, a new screen, or a new progress path for the
MVP. Three primitives already ship and are corpus-proven:
- **Passage:** the `reading` teaching-card kind already holds a full multi-
  sentence paragraph (`kind: reading`, `target.text`), authored in **320 files**,
  registered in `VALID_TEACHING_KINDS` (`compile_content.py:269`),
  `TeachingCardKind` (`packages/shared/src/api/types.ts:129`), rendered by
  `TeachingCardView.tsx`.
- **Narration:** every text block renders a `SpeakButton` → `speak()`
  (`TextBlock.tsx:37`, `frontend/src/api/tts.ts:92`) — a passage narrates by TTS
  of its own text, **no media asset needed**. Same TTS gate as dictation (nl/8
  langs Google, fa Azure, **prs browser-only/degraded**).
- **Questions:** `reading_comprehension` (passage + question + options + one
  answer) already exists and renders (`ReadingComprehension.tsx`,
  `ExerciseRenderer.tsx:47`). It is **one-question-per-item**.

**The one genuine gap = tap-any-word-to-gloss.** No per-word tap/hover gloss
exists anywhere in the frontend today.

## 3. Scope & key decisions (MVP)
- **In-lesson, not a new screen.** A reading track lesson = a `reading` teaching
  card (passage + narration + tap-gloss) immediately followed by 2–4
  `reading_comprehension` questions on that passage. Flows through the existing
  `LessonRunnerPage` (teaching cards → exercises). **No new route, no new
  `UnitSection`, no new exercise type, no new progress path** — completion is
  earned through the comprehension questions' `ExerciseAttempt` rows exactly as
  today (`router.py:734,762`). A dedicated Duolingo-Stories surface is deferred
  (§11).
- **Tap-gloss data = author-controlled, compile-time-embedded.** The `reading`
  card gets an optional authored **`glosses:` map (`token → English gloss`)** in
  the **overlay** (glosses are source-language). The compiler embeds it into the
  served card payload. The frontend makes only glossed tokens tappable.
  - **Why authored, not auto-from-`Lexeme`:** `Lexeme.english_gloss` is one
    beginner-sense gloss per `token+POS`, course-scoped — a passage word may be a
    homograph, an inflected form with no matching lexeme token, or never
    introduced → tap yields nothing or a WRONG sense. Author-controlled
    sense-in-context is correct by construction and needs no DB at compile time.
    (Auto-from-lexeme with author overrides is a v2 option.)
  - Authors gloss the **content/hard words** a learner might not know — not every
    function word. Un-glossed tokens simply aren't tappable.
- **nl-first** (TTS + the reference language). fa when Azure key is set; prs
  narration is degraded (browser-only) — same known limitation as dictation.
- **Comprehension:** author 2–4 `reading_comprehension` items after the reading
  card, each repeating the (short) passage in its own `prompt` per the type's
  one-Q-per-item shape — OR keep questions terse and passage-referencing. A
  passage-plus-question-set object is deferred (§11); MVP reuses the shipped type.

## 4. Content authoring shape
**Realization** (target-language) — the passage as a `reading` teaching card
(this already works today; the only new thing is the paired glosses live in the
overlay):
```yaml
- content_key: nl.b1.unitNN.lessonMM.teach.reading_<slug>
  kind: reading
  target:
    text: "Kasia verandert van baan omdat ze naar Utrecht verhuist. Eerst zocht ze online. Volgende maand begint ze."
    language_code: nl
    direction: ltr
  introduced_tokens: ["verhuist", "zocht"]   # existing convention (mints lexemes)
```
**Overlay** (source-direction, e.g. `en-nl`) — whole-passage gloss (existing)
PLUS the new per-word `glosses` map:
```yaml
  nl.b1.unitNN.lessonMM.teach.reading_<slug>:
    gloss: "Kasia is changing jobs because she's moving to Utrecht. First she searched online. She starts next month."   # existing whole-passage translation block
    glosses:                       # NEW — token → in-context English gloss
      verandert: "changes"
      baan: "job"
      verhuist: "is moving"
      zocht: "searched (past of zoeken)"
      begint: "starts / begins"
```
Rules: keys are the **exact surface tokens** as they appear in `target.text`
(including capitalization/inflection); glosses are short, sense-in-context; gloss
only content words worth helping with. NOT every token needs a gloss.

Then author 2–4 `reading_comprehension` exercises in the same lesson (existing
shape: `prompt.target_blocks` = short passage-ref + question, `options`,
`correct_response`).

## 5. Tap-to-gloss mechanism
- **Compiler (Codex):** `compile_teaching_item()` (`compile_content.py:3450`)
  already turns a `reading` card's `target`(+overlay `gloss`) into `text_blocks`.
  Extend it to also emit the overlay's `glosses` map onto the compiled teaching
  item (e.g. `teaching_item["glosses"] = {token: gloss}`), and thread it through
  the lesson-serve payload (`router.py:662-667` teaching serialization) so the
  client receives it. Validate: glosses keys should be tokens that actually occur
  in `target.text` (warn on a gloss key absent from the passage — likely a typo).
- **Frontend (Claude):** a new **`GlossableText`** component. Given a
  `TextBlock` + a `glosses` map: tokenize `block.text` (must match the app's
  `tokenize()`/grading token semantics; handle non-Latin — Arabic/Persian RTL,
  no-whitespace Han/Japanese, Hangul), render each token; tokens present in
  `glosses` get a tappable affordance + a popover showing the gloss; others render
  plain. Respect the RTL container `dir` rule (`frontend/CLAUDE.md`). Wire it into
  the `reading`-card render path in `TeachingCardView.tsx` (only when a `glosses`
  map is present; otherwise fall back to today's plain `TextBlockList`, so all 320
  existing reading cards are unaffected). Keep the existing `SpeakButton`.

## 6. Audio narration — free
No work for MVP. The `reading` card's text block already renders a `SpeakButton`
that TTS-narrates the passage. (Recorded human narration via a threaded
`media_asset_key` is a deferred enhancement — §11.)

## 7. Integration checklist (much smaller than a new exercise type)
No `ExerciseType`/enum/DB-constraint/`ExerciseRenderer` changes — this is NOT a
new exercise type. Register/touch only:

| # | File (≈line 2026-08-03) | Change | Lane |
|---|---|---|---|
| 1 | `scripts/compile_content.py:3450` `compile_teaching_item()` | emit overlay `glosses` onto the compiled `reading` teaching item | Codex |
| 2 | `scripts/compile_content.py` (validators) | warn if a `glosses` key isn't a token in `target.text` | Codex |
| 3 | `backend/app/api/router.py:662-667` lesson-serve teaching serialization | include `glosses` in the served teaching item | Codex |
| 4 | `packages/shared/src/api/types.ts` `TeachingItem`/card type (~:129) | add optional `glosses?: Record<string,string>` | Claude |
| 5 | `frontend/src/components/GlossableText.tsx` (new) | tokenize + tappable gloss popover, RTL-aware | Claude |
| 6 | `frontend/src/components/teaching/TeachingCardView.tsx:13,36` | use `GlossableText` for `reading` cards that have `glosses` | Claude |
| 7 | `docs/CONTRACT.md` | document the `glosses` teaching-item field | Claude |

## 8. Build order & lane split
1. **Codex (compiler + serve):** #1,#2,#3 — embed + serve `glosses`; validator.
   Coordinator diffs, imports a pilot, confirms the field reaches `GET /lessons/{id}`.
2. **Claude (frontend + contract):** #4,#5,#6,#7 — `GlossableText` + wire-in +
   CONTRACT. Full `npm run build`.
3. **Content (both):** author a **pilot nl reading lesson** — one `reading` card
   with a `glosses` map + 2–4 `reading_comprehension` questions — fresh-context
   review, compile.
4. **Coordinator:** import to dev DB, **live-browser verify** (§9).

## 9. Verification bar (non-negotiable)
- Compiler green incl. the new `glosses`-key-in-passage validator.
- Backend pytest green on an **isolated test DB**.
- Full `npm run build` (`tsc -b && vite build`).
- **Live browser, fresh account:** the passage renders; the speak button narrates
  (nl); tapping a glossed word shows the correct in-context gloss; a non-glossed
  word is inert; RTL passage (if an fa pilot) lays out correctly; the trailing
  comprehension questions grade and the lesson completes. Reading a diff is not
  verification — this project's worst bugs surfaced only in live play.

---

## 10. BUILD PROMPT (paste to a fresh-context Claude)

> **Task: build the graded reading track (MVP) for Lingo²** (repo:
> `/Users/raminazizi/dev/LingoSquared`). Read `docs/READING_TRACK_SPEC.md` fully
> first, plus root/`backend`/`frontend`/`docs/content` `CLAUDE.md` and
> `docs/CONTRACT.md`.
>
> **What it is:** an in-lesson reading experience — a `reading` teaching card
> (passage + TTS narration, both already exist) upgraded with **tap-any-word-to-
> gloss** (the one new capability), followed by `reading_comprehension` questions.
> NOT a new exercise type, NOT a new screen, NOT a new progress path.
>
> **The gloss data is author-controlled and compile-time-embedded** — a `glosses:`
> `{token → English gloss}` map authored in the en-nl overlay for the reading
> card; the compiler embeds it and the lesson endpoint serves it; the frontend
> makes only glossed tokens tappable. Do NOT auto-derive glosses from `Lexeme`
> (homographs/inflections/untaught words → wrong or missing sense).
>
> **Lanes (CLAUDE.md):** `scripts/compile_content.py` + `backend/app/**` +
> migrations = **Codex** (dispatch, diff before applying, run pytest on an
> **isolated** DB yourself — Codex has no Docker). `frontend/src/**`,
> `packages/shared`, `docs/CONTRACT.md` = **yours**. Content = both, through a
> **fresh-context review**.
>
> **Do, in order:** (1) dispatch Codex for spec §7 rows #1–#3 (emit + serve
> `glosses`, plus the key-in-passage validator); diff + apply + verify the field
> reaches `GET /lessons/{id}`. (2) Build the frontend: §7 rows #4–#7 — a new
> `GlossableText.tsx` (tokenize the block text matching the app's token
> semantics, RTL-aware per frontend/CLAUDE.md; tappable popover only for tokens in
> the `glosses` map; keep the SpeakButton), wired into `TeachingCardView` for
> `reading` cards that carry glosses (fall back to plain `TextBlockList`
> otherwise so the 320 existing reading cards are unchanged); update CONTRACT.md;
> run the FULL `npm run build`. (3) Author a **pilot nl reading lesson** (one
> `reading` card + `glosses` + 2–4 `reading_comprehension` items) → fresh-context
> review → compile. (4) Import to the dev DB and **live-browser verify** (spec
> §9): passage renders, narration plays, tapping a glossed word shows the right
> gloss, non-glossed words inert, comprehension grades, lesson completes.
>
> **Verification bar is non-negotiable** (spec §9): compiler green, isolated-DB
> pytest, full `npm run build`, live browser. Biggest risk = gloss
> sense/coverage and tokenization for non-Latin scripts — verify in live play.

---

## 11. Deferred (post-MVP, spec separately if pursued)
- **Dedicated "Stories" surface** — a `ReadingRunnerPage` + route (+ possibly a
  new `UnitSection` at `entities.py:57` and its own progress/XP path) for a
  full-screen reader with inline questions. Larger; new progress path is the main
  cost.
- **Recorded human narration** — thread a `media_asset_key` through teaching-item
  serialization + `TextBlockList` (currently teaching cards pass none).
- **Passage-plus-question-set object** — if several questions per shared passage
  without repeating the passage text per item is wanted (the current
  `reading_comprehension` is one-question-per-item).
- **Auto-gloss from `Lexeme` with author overrides** — lower author burden than a
  full authored map, at the cost of homograph/inflection risk.
- All reading-track audio inherits the fa/prs TTS gap (prs narration is
  browser-only/possibly silent) — same as dictation.
