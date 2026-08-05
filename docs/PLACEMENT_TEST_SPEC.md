> **Status: APPROVED (CEO sign-off, 2026-08-05).** MVP scope = 3 stateless backend endpoints + one new frontend page, ZERO database migrations, recommendation persisted in `localStorage` (reusing the existing per-course level-preference mechanism). One growth step (server-side persistence + progress/SRS seeding) requires ONE small migration and is explicitly deferred. This document is the buildable spec; it goes to build agents verbatim. Contract changes land in `docs/CONTRACT.md` BEFORE implementation.

# Placement Test — Feature Design (MVP + one growth step)

## 0. Executive summary

The app already ships a **self-report** level picker (`LevelCheckPage`, 3 buttons → `localStorage` → highlights one "recommended for you" unit). Ramin's read that "the answer is unused" is *almost* right: it drives only a soft highlight from a coarse self-assessment. This design **replaces the self-report with a real, adaptive, laddered test** that samples **existing lesson exercises**, grades them server-side with the existing grading engine, and produces a **recommended starting unit** — reusing the *exact same* highlight UI the self-report already feeds.

**MVP is ZERO migrations.** It adds 3 stateless backend endpoints and one new page, persisting the recommendation in `localStorage` exactly like the current level preference. The growth step adds **one** small table to persist results server-side and actually seed progress/SRS.

---

## 1. Discovery findings (concrete)

### 1.1 The current "self-assessment" and where it lives
- **Entry gate:** route `/courses/:courseId/level` → `frontend/src/pages/LevelCheckPage.tsx`. Reached automatically the first time a user opens a course from `CoursePickerPage` (the course card links to `/courses/${course.id}/level`).
- **What it asks:** 3 buttons — `beginner | some_basics | conversational` (`SelfReportedLevel`).
- **What it stores:** `frontend/src/lib/levelPreferences.ts` → `setLevelPreference(courseId, level)` → `localStorage["course-level-<courseId>"]`. **Client-only, per course, per device. No backend field exists.**
- **Where it's consumed (NOT fully dead, but weak):** `frontend/src/pages/CourseUnitsPage.tsx` lines 204-211 call `recommendedUnitIndex(level, readingWriting.map(u => u.content_key))` → renders a `border: 2px solid var(--accent)` on one `PathNode`, a `"recommended_for_you"` badge, and a **"test out" link** to `/units/:id/checkpoint`. That is the *entire* payoff of the self-report today.
- **No backend `User` field, no `user_course_state` table, no JSONB prefs** — searched `entities.py`; user proficiency is nowhere server-side.

### 1.2 Reusable machinery
- **Grading (pure, DB-free):** `backend/app/review/grading.py` → `grade(response, correct, exercise_type, *, script=None, orthography_strict=None, case_sensitive=False)` returns `"correct"|"almost"|"incorrect"`. **Choice types (`multiple_choice`, `matching_pairs`, `word_order`, `listen_select`) resolve straight to correct/incorrect** (never "almost", no typo/script pitfalls). `resolve_script(db, language_code)` + `decode_feedback(e.feedback)` in `router.py` give the per-exercise strictness inputs (only needed for free-text types, which the MVP avoids).
- **Exercise rows are universal.** `Exercise`: `id, lesson_id, type, order, prompt (JSON — carries `options`/`target_blocks`), correct_response (JSON, server-only secret), content_key`. Every course has them; the lesson endpoint already serves `{id, type, order, prompt}` (answer withheld) at `router.py:667`.
- **CEFR is derivable from `Unit.content_key`** (`nl.a1.unit01.greetings` → A1). `parseCefrLevel()` already exists in `levelPreferences.ts` and the block comment confirms the `{lang}.{cefr}.unit{NN}.{slug}` convention holds across all shipped languages.
- **Unit locking is minimal.** `router.py` `units()` (602) marks `locked = section=="speaking" and not speaking_unlocked(...)`. **Reading/writing units are never locked** — freely navigable. So a "starting unit" is a *highlight/recommendation*, not an unlock gate. **Mid-course entry needs no unlock mechanism at all for MVP.**
- **Existing checkpoint ("test out") infra** (`generate_checkpoint` in `practice/service.py:1654`, `CheckpointAttempt`, `PracticeItem`, `POST /units/{id}/checkpoint`) is **deliberately NOT reused**: it depends on `PracticeTemplate` + lexeme backfill (per the code, only ~48% of units can even produce one), is unit-scoped, and writes SRS. Placement needs course-wide, template-free, side-effect-free sampling → **sample raw `Exercise` rows instead.**
- **Error envelope:** `app/core/errors.py` `fail(status, code, message, **details)` raises `HTTPException(detail={"code", "message", ...})`, but `app/main.py`'s `HTTPException` handler re-wraps it, so the wire body is `{"error": {"code", "message", ...}}` (NOT `{"detail": ...}` — tests assert `r.json()["error"]["code"]`; see `test_rate_limiting.py`). Frontend `ApiError` exposes `.code` / `.details` (see `CheckpointPage.tsx:69`).
- **Frontend reuse:** `ExerciseRenderer` (`components/exercises/ExerciseRenderer.tsx`) renders any type from `{id, type, order, prompt}` + `onAnswer(AnswerResponse)` + `gradedResult`. `CheckpointPage.tsx` is a near-perfect template for the runner UI (progress bar, per-item feedback, quit confirm). Shared API layer: `packages/shared/src/api/{client,endpoints,types}.ts` with `get<T>`/`post<T>` helpers and the `CatalogApi`-style object pattern.

### 1.3 CONTRACT / architecture-why (relevant)
- Per root `CLAUDE.md`: **`docs/CONTRACT.md` must be updated BEFORE implementing any contract change** (new endpoints), and it is Claude's lane.
- `docs/APP_SPEC_FOR_FABLE_REVIEW.md` onboarding/course rationale: English-anchored directed paths; course = one CEFR-anchored path; content only ever *appends* higher levels (so a course's units walk complete CEFR levels in order — the basis for level-block sampling).
- **Historical note:** `CONTRACT.md`'s checkpoint section (line ~1274) records that a *placement-quiz enrollment system* was previously **rejected** in favor of the unit checkpoint. This MVP is materially different from what was rejected — it is recognition-only, side-effect-free (no enrollment/progress mutation in MVP), and reuses existing reviewed exercises — and it is now explicitly approved (CEO sign-off, 2026-08-05).

---

## 2. MVP design

### 2.1 Test mechanics
- **Probe source:** existing `Exercise` rows of the course, **restricted to `multiple_choice` and `matching_pairs`** (justification in §4).
- **Ladder:** group probes by the CEFR level of their owning unit (`Unit.content_key`). Administer **blocks in ascending order A1 → A2 → B1 → B2**, **4 items per level** (skip any level the course lacks). A course reaching B1 yields 12 items; through B2 yields 16 (inside the 12-18 target).
- **Adaptive early-exit (client-driven, using server per-item grading):**
  - Pass a level block = **≥ 3 of 4 correct** (≥ 75%).
  - **Stop at the first level block the learner FAILS** (< 3/4). Also stop after the highest available block passes.
  - This realizes Ramin's "consecutive fails ends" cleanly: one clear level-fail ends the test (a whole block is already the evidence unit). No need to slog an A1 learner through B2.
- **Scoring → recommendation (authoritative, server-side in `/result`):**

  | Outcome | Recommended level | Recommended unit |
  |---|---|---|
  | Fail A1 | A1 (start) | first reading/writing unit of the course |
  | Pass A1, fail A2 | A2 | first unit whose `content_key` level == A2 |
  | Pass A1+A2, fail B1 | B1 | first B1 unit |
  | Pass all available | highest present level | first unit of that level |

  "First unit of level L" = the reading/writing unit with the lowest `order` whose parsed CEFR == L.
- **Mid-course entry:** because reading/writing units never lock, the recommendation is applied as a **highlight** (reusing `CourseUnitsPage`'s existing `recommended` `PathNode` styling + badge + "test out" link). No unlock/progress mutation in MVP. (Growth step actually advances the learner — §3.)

### 2.2 API design (3 stateless endpoints, ZERO migration)

All authenticated (`current_user`) — placement is reached post-login (CoursePicker is behind `ProtectedRoute`). All rate-limited with the existing `ANSWER_RATE_LIMIT`. Correct answers **never** leave the server. Envelope is the standard `fail(...)` shape.

**A. `GET /courses/{course_id}/placement`**
Returns the laddered probe set (no answers). Deterministic per course (stable ordering — see §4) so results are reproducible/testable.
```jsonc
// 200
{
  "course_id": "…",
  "levels": ["A1","A2","B1","B2"],          // only levels the course actually has probes for
  "block_size": 4,
  "pass_threshold": 3,                        // correct-per-block to advance
  "items": [                                  // grouped/ordered A1→…, block by block
    { "id": "<exercise_id>", "level": "A1", "type": "multiple_choice", "order": 0, "prompt": { … } },
    …
  ]
}
```
- 404 `course_not_found`; 409 `placement_unavailable` if fewer than one full A1 block (< 4 usable probes) can be built.
- Reuses the lesson `ExerciseOut` shape `{id, type, order, prompt}` plus `level`.

**B. `POST /courses/{course_id}/placement/answer`** *(per-item live grading; enables adaptivity + immediate feedback)*
```jsonc
// body
{ "exercise_id": "<id>", "response": <AnswerResponse> }   // same union as AnswerIn
// 200
{ "correct": true, "result": "correct", "correct_response": <shown-answer> }
```
- **No persistence, no XP, no SRS, no LessonProgress** — pure `grade()` call. Distinct from `POST /exercises/{id}/answer` (which records attempts). Validates the `exercise_id` belongs to `course_id` (else 400 `exercise_not_in_placement`). Rate-limited.

**C. `POST /courses/{course_id}/placement/result`** *(authoritative recommendation)*
```jsonc
// body — the full set of answered probes (client sends what it administered)
{ "answers": [ { "exercise_id": "<id>", "response": <AnswerResponse> }, … ] }
// 200
{
  "recommended_level": "A2",
  "recommended_unit_id": "<unit_id>",
  "recommended_unit_content_key": "nl.a2.unit05.…",
  "recommended_unit_title": "…",
  "per_level": { "A1": {"correct": 4, "total": 4}, "A2": {"correct": 2, "total": 4} }
}
```
- Server **re-grades** every submitted answer (cheap, `grade()` is pure) so the thresholds live in one authoritative place and can't be gamed client-side. Maps per-level accuracy → recommended level (§2.1 table) → resolves the recommended unit by scanning the course's reading/writing units for the first of that level.
- 404 `course_not_found`; empty/short `answers` → recommend course start (never errors).

> Design note: B is used for live per-item feedback + client early-exit; C is the source of truth for the recommendation. Two grade passes is intentional and negligible.

### 2.3 Frontend flow

**New page:** `frontend/src/pages/PlacementTestPage.tsx`, route `/courses/:courseId/placement` (add to `App.tsx`, statically imported alongside `CheckpointPage` per the existing non-lazy note). Structurally a fork of `CheckpointPage.tsx`:
- On mount: `PlacementApi.start(courseId)` → renders block-by-block via `ExerciseRenderer`.
- Each answer → `PlacementApi.answer(courseId, exerciseId, response)` → show correct/incorrect banner (reuse `resultStatus`/feedback-banner). Accumulate `{exercise_id, response}` locally.
- After each block of 4: if `correctInBlock < pass_threshold` → stop; else advance to next level block (or finish if none left).
- On finish: `PlacementApi.result(courseId, answers)` → **result screen**: recommended level, a one-line rationale, and a primary CTA **"Start at <unit title>"** linking to `/units/<recommended_unit_id>` (state `{ courseId }`). Persist via `setPlacementRecommendation(courseId, { unitId, level })` (see below), then also `setLevelPreference` best-effort for backward-compat.

**Persistence (zero migration):** new module `frontend/src/lib/placementPreferences.ts`:
```ts
// localStorage["course-placement-<courseId>"] = JSON {unitId, level, ts}
getPlacementRecommendation(courseId): {unitId:string; level:string} | null
setPlacementRecommendation(courseId, rec): void
```

**Wire the highlight (reuse existing UI):** in `CourseUnitsPage.tsx`, before the current `getLevelPreference` heuristic, check `getPlacementRecommendation(courseId)`; if present, set `recommendedIndex` to the index of that `unitId` in `readingWriting`. The existing `PathNode recommended` border + `"recommended_for_you"` badge + "test out" link render unchanged. Placement takes precedence over the self-report heuristic.

**Entry points:**
1. **`LevelCheckPage.tsx` becomes a fork/choice** (replaces the unused self-report as the primary answer): add a prominent primary CTA **"Take a 2-minute placement test"** → navigate `/courses/:courseId/placement`. Keep the 3 self-report buttons demoted as a **"Skip — I'll pick myself"** fallback (preserves 100% of current behavior for anyone who skips). This directly implements "instead offer a quick test."
2. **`CoursePickerPage.tsx`:** on each course card add a small secondary link **"Not sure? Take the test"** → `/courses/:courseId/placement` (mirrors the existing "Change level" affordance pattern at lines 317-329).

**Skip path:** untouched self-report buttons + auto-skip logic in `LevelCheckPage` (single-unit / already-answered) all remain, so no regression.

**Shared layer additions:** `packages/shared/src/api/endpoints.ts` → new `PlacementApi` (`start`/`answer`/`result`, mirroring `CheckpointApi`); `packages/shared/src/api/types.ts` → `PlacementSet`, `PlacementProbe`, `PlacementRecommendation`. i18n keys under `placement.*` in `frontend/src/i18n/` (all locales, esp. nl/fa/prs — mandatory RTL target).

---

## 3. Growth step (ONE small migration)

**Goal:** persist the recommendation server-side and *actually advance* the learner instead of only highlighting.

- **Migration `00NN_placement_result.py`** (Codex's lane; must be fresh-migrate-safe + existence-guarded per `backend/CLAUDE.md`): table `placement_results(id, user_id FK, course_id FK, recommended_level, recommended_unit_id FK, per_level JSON, created_at)`, unique-ish on `(user_id, course_id)` latest-wins.
- `POST /courses/{id}/placement/result` gains a side effect: upsert the row; optionally, on an advanced recommendation, **seed `UserLexemeSRS` for all lexemes of units below the recommended level** and mark those units' checkpoints passed — reusing the *exact* SRS-seeding block already in `checkpoint_result()` (`router.py:1684-1753`), so the learner's home "continue", progress %, and review queue reflect the placement (mid-course entry becomes real, not cosmetic). **Must obey the standing invariant: never corrupt SRS — seed only, idempotent, `orthography_strict` unaffected.**
- Frontend reads server recommendation via a new `GET /me/placement/{course_id}` so it syncs across devices (localStorage becomes a cache). `CourseUnitsPage` prefers the server value when present.

This is deferred because it touches SRS/progress semantics and needs live-lesson verification of the seeding path.

---

## 4. Content-selection strategy (why these probes)

Placement users **have not learned anything**, so probes must be **recognition-based, self-contained, and grading-safe**:

- **`multiple_choice`** ✅ — options are in `prompt`; the correct choice is *visible among distractors*; grading is choice-based (correct/incorrect, no "almost"); no typing → **no orthography strictness, no RTL keyboard, no ZWNJ/harakat pitfalls**; no audio. Abundant at every level (confirmed in `nl/a1_unit01_greetings.yaml`).
- **`matching_pairs`** ✅ — pairs displayed; recognition; choice-graded via `canonical_pairs`; no production/typing. (Heed the frontend footgun: index-keyed tiles — already fixed in `MatchingPairs.tsx`.)

**Excluded and why:**
- **All `listen_*` (`listen_select`, `listen_type`, `listen_order`, `dictation`)** — audio-gated (`media_asset_key`); **`prs` has zero TTS coverage** (`backend/CLAUDE.md`), so audio probes would be unfair/broken for a launch-gate language. Excluded universally to keep one code path.
- **Production types (`translation`, `reverse_translation`, `writing_prompt`, `dialogue_response`, `speak_*`, free-text `fill_in_blank`)** — require *recall*, not recognition; a genuinely knowledgeable placement user would still fail on unfamiliar exact orthography (**fa/prs graded script-strict** per `grading.py`), inverting the measurement. Excluded from MVP; a later tier could add `word_order` (self-contained word bank) as a "harder" discriminator.

**Deterministic selection** (reproducible + unit-testable): for each level, collect all `multiple_choice`/`matching_pairs` exercises whose owning `Unit.content_key` parses to that level, sort by `(unit.order, lesson.order, exercise.order, exercise.id)`, and take the first `block_size` (4). Stable, no per-user RNG needed (placement isn't SRS). If a level yields < 4, either take what exists or drop the level from the ladder (drop A-tier only if A1 itself can't fill one block → 409 `placement_unavailable`). **Self-contained guarantee:** MC/matching prompts carry their own options/pairs and never reference prior lesson context, so "untaught-dependence traps" cannot occur.

---

## 5. Effort / build plan

**CONTRACT.md FIRST (before any code, Claude's lane):** document endpoints A/B/C — paths, request/response schemas, error codes (`course_not_found`, `placement_unavailable`, `exercise_not_in_placement`), auth (`current_user`), rate limit (`ANSWER_RATE_LIMIT`), and the **explicit statement that `/placement/answer` and `/placement/result` have no side effects** (no XP/SRS/LessonProgress) in the MVP.

**Backend (Codex's lane; dispatch + Claude-verify):**
1. `backend/app/schemas/api.py` — `PlacementProbeOut`, `PlacementSetOut`, `PlacementAnswerIn` (reuse `AnswerIn.response` union + `_bounded_payload_size`), `PlacementAnswerOut`, `PlacementResultIn`, `PlacementResultOut`.
2. `backend/app/api/router.py` — 3 endpoints. New helper `build_placement_set(db, course)` (level-grouped deterministic sampling); reuse `grade()` + `resolve_script()` + `decode_feedback()`; a `recommend_from_answers(...)` pure helper (the §2.1 table) — put it in `app/review/` so it's unit-testable without HTTP.
3. No migration (MVP).

**Frontend (Claude's lane):**
4. `frontend/src/lib/placementPreferences.ts` (new).
5. `frontend/src/pages/PlacementTestPage.tsx` (new; fork `CheckpointPage`).
6. `frontend/src/App.tsx` — add `/courses/:courseId/placement` route (static import).
7. `frontend/src/pages/LevelCheckPage.tsx` — add primary "Take the test" CTA, demote self-report to skip.
8. `frontend/src/pages/CoursePickerPage.tsx` — per-card "Not sure? Take the test" link.
9. `frontend/src/pages/CourseUnitsPage.tsx` — prefer placement recommendation for the highlight.
10. `packages/shared/src/api/endpoints.ts` (`PlacementApi`) + `types.ts` (types).
11. `frontend/src/i18n/*` — `placement.*` keys (all locales; nl/fa/prs required).

**Test plan:**
- **Backend pytest (isolated DB, `python -m pytest`):** deterministic set for a seeded course; `/placement/answer` grades correctly and writes **nothing** (assert no `ExerciseAttempt`/`LessonProgress`/`UserLexemeSRS` rows after); `recommend_from_answers` table-driven unit tests (fail-A1, pass-A1-fail-A2, pass-all); 409 when < 1 block; exercise-not-in-course → 400.
- **Frontend:** unit-test `placementPreferences` + `recommend`-to-index mapping; component test the block/early-exit logic.
- **Live browser (non-negotiable, fresh account):** run placement on **en-nl** (LTR) and **en-fa or en-prs** (RTL, no-audio) — the launch-gate pairs — verifying MC + matching render, early-exit fires on a failed block, the result CTA lands on the right unit, and `CourseUnitsPage` highlights it. Then `scripts/verify.sh` (full frontend build + backend) and grep for `COMPILE FAILED`.

**Risks / footguns (explicit):**
1. **Answer-key oracle:** `/placement/answer` reveals per-item correctness. Mitigate: require auth, rate-limit, validate exercise∈course, choice-types-only (options already visible). Acceptable; note in CONTRACT.
2. **Grading strictness:** avoided by choosing choice types only — no "almost", no fa/prs exact-match failures, no RTL typing. **Do not add free-text probes** without revisiting `grading.py` strictness (`docs/.../reference_grading-normalization-spec`).
3. **RTL lanes:** MC/matching need no RTL keyboard, but verify option rendering direction on fa/prs (`dir` inherited correctly by `MultipleChoice`/`MatchingPairs` — matching has fixed columns, no sequence-dir issue).
4. **`content_key` may be null** on legacy imported units → level unparseable. `parseCefrLevel` already returns null gracefully; such units are simply excluded from the ladder (don't crash).
5. **Course-level single-value `Course.level` is unreliable** (never updated as higher content appends — documented in `levelPreferences.ts`); **always derive level from `Unit.content_key`, never from `Course.level`.**
6. **Guest users:** N/A for MVP (placement is post-login); keep endpoints `current_user` so the growth step can attach results.
7. **Don't reuse `POST /exercises/{id}/answer`** for probes — it records attempts/XP/streak and would pollute a placement taker's real progress.
