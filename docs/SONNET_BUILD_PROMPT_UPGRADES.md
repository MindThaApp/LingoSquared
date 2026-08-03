# Lingo² upgrade program — build prompt for the executing Claude Sonnet 5 session

Written 2026-07-05 by Fable, following the architecture review in
`docs/APP_SPEC_FOR_FABLE_REVIEW.md`. This document is your work order.
It assumes the app as it exists today (see CLAUDE.md at repo root) and
upgrades it to a pedagogically serious product. Do the phases in order —
Phase A is the architectural centerpiece and later phases depend on it.

---

## 0. Before you write anything

Read, in this order:

1. `CLAUDE.md` (repo root) — full project state, every known footgun.
2. `docs/CONTRACT.md` — the API/schema contract. Any API change in this
   program must be written into CONTRACT.md **before** implementation,
   and Codex builds against the updated contract, never against chat.
3. `docs/APP_SPEC_FOR_FABLE_REVIEW.md` — what the app is and why.
4. `docs/content/AUTHORING_GUIDE.md` — binding rules for all content.
5. Memory files `project-lingosquared-roadmap` and
   `project_lingosquared_endless_practice` if available.

**Division of labor (unchanged, it works):** Codex authors all backend
code (`backend/app/**`, alembic migrations, `scripts/compile_content.py`)
and every word of language content. You own `frontend/src/**`,
orchestration of Codex (extract → validate → apply), CONTRACT.md edits,
and ALL verification. Delegate to Codex with explicit
`--cwd "$LINGO_REPO"`; Codex has no Docker and no
network — you verify everything it produces against the real local stack.

**Working with the Codex plugin (mechanics + known failure modes):**
Delegate via the openai-codex plugin's companion script, always in the
background and always with an explicit `--cwd` (Codex's sandbox
defaults to the Claude session's cwd, which may be a different project
entirely — without this it cannot write files at all):

```bash
node "/Users/raminazizi/.claude/plugins/cache/openai-codex/codex/1.0.5/scripts/codex-companion.mjs" task \
  --cwd "$LINGO_REPO" --background --write --resume "…prompt…"
# then: status <job-id> --cwd ... --json   /   result <job-id> --cwd ...
```

(If the plugin version/path has changed, find the current one under
`~/.claude/plugins/cache/openai-codex/` rather than trusting this path.
If Codex auth fails with a revoked refresh token, Ramin must run
`codex login` — stop and tell him, don't retry.)

Rules learned from real incidents this project:
- Codex has no Docker and no outbound network — it writes and
  static-checks code; ALL build/test/browser verification is yours.
- Never trust Codex's self-report. When it rewrites a whole file, diff
  against the prior version before applying — a full-file rewrite once
  silently introduced an unrelated one-line query regression
  (`Unit.id==u.id` for `Lesson.unit_id==u.id`) alongside a correct fix.
- Every content-authoring prompt to Codex must include, up front: the
  recognition→drag→production pacing rule, and — when authoring a
  source overlay against an existing realization — the STRONG form of
  the sibling-file rule ("treat the sibling-direction overlay as if it
  does not exist; do not open it"), not "for reference only", which
  demonstrably fails.
- Point every content task at `docs/content/AUTHORING_GUIDE.md`, and
  route every content deliverable through a separate fresh-context
  review task (zero access to the authoring reasoning) before import.
- Tests Codex writes that import `scripts/compile_content.py` belong in
  `scripts/tests/` (run via `.content-venv`), not `backend/tests/` —
  the backend container doesn't mount repo-root `scripts/`.

**Verification bar (non-negotiable, per phase):**
- Compiler validation green (`scripts/compile_content.py` via `.content-venv/`).
- Backend pytest green — real Postgres via docker compose, isolated test
  DB, `python -m pytest` (never bare `pytest`), never
  `docker compose --env-file` (it does NOT set container env; this once
  wiped the live DB).
- Frontend: full `npm run build`, not `tsc --noEmit` (the full build has
  twice caught errors noEmit missed).
- Live browser verification with a fresh test account for anything
  user-facing. Reading a diff is not verification. This project's
  documented history: the worst bugs (unregistered exercise types,
  permanently-disabled Respond button, distractors drawn from the whole
  course) were ALL found only in the browser.
- Local stack only (`colima start`, `cd backend && docker compose up -d`,
  isolated `backend/.env`). Never touch the live server (192.168.4.4)
  unattended; deploys happen with Ramin present.
- `docker compose restart` does not reload `.env`; use `up -d`.

**Standing constraints — do not violate, do not re-propose:**
- No runtime-LLM content generation, ever. Every learner-facing string
  passes deterministic validators + a fresh-context review before import.
- No hearts/lives, leagues, gems/currency. (The `hearts`/`gems` columns
  in `UserStats` are dead scope — leave them, add a comment.)
- Additive-only migrations. Never delete or reassign exercise/content
  UUIDs; users are pinned to content releases.
- Content authoring: recognition → drag → production pacing within every
  lesson; never open sibling-direction files while authoring; every unit
  needs a fresh-context review before `review: status: reviewed`; sweep
  for internal-jargon leaks (bare snake_case in options/distractors,
  words like "reviewed" in learner-facing feedback) after every content
  round.

**Parallel-session ownership map (when Ramin runs multiple Claude
instances):** Up to three Claude sessions may work this repo
concurrently. Identify which session YOU are from how Ramin launched
you, stay in your lane, and hand off anything outside it rather than
touching another session's territory.

| | Session 1 — CODE | Session 2 — CONTENT | Session 3 — INFRA |
|---|---|---|---|
| Owns | `frontend/src/**`, `docs/CONTRACT.md`, all backend/migration coordination with Codex (phases A–G) | Codex content dispatch + fresh-context reviews, compiler validation, Ramin's nl native-review loop, `docs/content/**` | `e2e/**` (Playwright), `scripts/verify.sh` + tooling, audio-manifest/pipeline scaffolding (D1/D3), prompt templates, CLAUDE.md restructure |
| Docker stack | **Sole owner** (compose up/down, migrations, imports, pytest, browser verification) | Never touches it — compiler validation needs only `.content-venv` | Hands live-stack steps to Session 1, or runs its own compose project on different ports if Playwright work gets too chatty |
| Codex jobs | Backend code tasks | Content authoring/review tasks (3–4 in parallel, disjoint language dirs) | Script/tooling tasks |

Singletons regardless of session count: ONE owner for the Docker stack
at any time; ONE owner for alembic migration numbering (Session 1 —
never ask Codex for a new migration from any other session); ONE
editor for CLAUDE.md's build log per day (Session 1 by default; others
queue their entries as notes for it). If sessions commit, use one
branch or worktree per session — never two sessions committing to the
same checkout. Post-fan-out, Session 3's tooling work will be done;
its slot gets repurposed as a second content orchestrator split by
language cohort.

**Content-mutation vs. live-verification race (found live, 2026-07-05):**
the table above covers Docker *infrastructure* ownership (compose
up/down, migrations, pytest) but originally said nothing about
*content* re-imports racing against browser-based verification —
both write to the same shared local DB. Real incident: Session 3's
e2e suite kept failing against `en-prs` "Dari Foundations" with
Playwright reporting elements detaching from the DOM mid-click;
root cause was Session 2 actively re-importing/recreating that exact
course (new ID every few seconds) while Session 3 tested against it —
no locator fix survives a page whose underlying data is rewritten out
from under it. Rule: **don't destructively re-import/reseed a course
on the shared local stack while another session might be running
browser-based (e2e or manual) verification against it** — announce it
first, or do it on an isolated stack (see below). If you hit
mid-test course-ID churn like this, don't waste cycles debugging your
own test code first — poll the course endpoint twice a few seconds
apart to confirm before assuming it's a real app or test bug.

**Session 3's isolated-stack escape hatch, exercised for real:** when
shared-stack content churn makes verification unreliable, stand up a
second, fully isolated `docker compose` project on different host
ports (separate `-p`/`--project-name`, separate `POSTGRES_*`/`API_PORT`
in an env override) rather than keep retrying against the contended
shared stack. This is slower to set up but produces a result that
doesn't depend on nobody else touching the DB at that exact moment —
worth it the moment shared-stack retries stop being conclusive.

---

## 1. The problem this program fixes

The content factory is excellent; the runtime learning loop is not. The
central defect: **SRS schedules exercises, not knowledge.** `ReviewItem`
is keyed to `exercise_id`, so review re-shows the identical exercise
forever — learners memorize the test item, not the lexeme. Compounding
it: every in-lesson answer advances SM-2 intervals (so initial learning
and lesson replays fake "spaced recall"), review items duplicate per
overlapping exercise, and `VocabularyProgress`/`GrammarProgress` are
returned by `/me/progress` but never written anywhere — permanently
empty tables.

The fix is cheap because the hard parts exist: the `lexemes` table
(migration 0006, with per-lesson provenance) and the practice-template
engine (migration 0007) can already render a fresh, reviewed, gradeable
exercise for any lexeme on demand. SRS should schedule **lexemes** and
the practice engine should **generate a novel exercise** each time one
comes due. Review and Endless Practice converge into one system.

---

## Phase A — Lexeme-level SRS unified with the practice engine

### A1. Schema (Codex, additive migration)

New table `user_lexeme_srs`:
- `user_id`, `lexeme_id` (unique together), `course_id`
- SM-2 state: `ease_factor` (default 2.5), `interval_days` (0),
  `repetitions` (0), `mastery` (0.0), `due_at`, `last_reviewed_at`
- `introduced_at` (when the lesson introducing it was first completed)
- `suspended` bool default false (admin/content-issue escape hatch)

Later: a parallel `user_grammar_srs` keyed to grammar-point content
items — design the service so adding it is mechanical, but do NOT build
it in this phase. Lexemes first, prove the loop.

### A2. Population rules

- On **first completion** of a lesson (the existing
  `POST /lessons/{id}/complete` first-completion branch), create
  `user_lexeme_srs` rows for every lexeme whose
  `provenance_lesson_id` is that lesson, `due_at = now + 1 day`.
- In-lesson exercise answers NO LONGER create or advance any SRS state.
  Keep writing `ExerciseAttempt` and `LessonProgress` exactly as today.
- Legacy `ReviewItem`: stop creating new rows; keep the table and the
  old endpoints functional (users may have due items), but the frontend
  review surface switches entirely to the new flow. Document the
  deprecation in CONTRACT.md. Do not drop the table.

### A3. Review generation and grading

- `GET /me/reviews/due` → `{due_count, by_course: [...]}` (cheap count
  for the home screen, Phase E depends on it).
- `POST /reviews/session` (course_id, size≤20) → generates a batch via
  the EXISTING practice engine, but the sampler is **due-lexeme-first**:
  each item must test a due lexeme (template slot filled with it, or a
  template whose fixed tested_text contains it). Fall back to
  low-mastery, then random reinforcement if fewer due than `size`.
  Response shape must match the existing `ExercisePrompt` so
  `ExerciseRenderer` needs zero changes (this exact trick worked for
  the practice feed).
- Answering a review item: reuse the practice-item answer flow
  (server-held answer, 24h expiry, 404/409/410 semantics), plus: on
  grade, call `schedule()` against the lexeme's SRS row.
- **Same-session retries never advance the interval**: only the FIRST
  answer for a given due lexeme in a session updates SM-2 state; a
  failed lexeme is re-queued within the session (frontend, Phase B
  pattern) and that retry is cosmetic. A failed lexeme's SM-2 state:
  repetitions=0, interval=1 day (existing `schedule()` behavior is fine).
- Keep binary quality mapping for now, but isolate the
  quality-derivation in one function so partial credit (typo-tolerant
  "almost", Phase C) can later map to quality 3–4 without surgery.

### A4. Adaptive format ladder (sampler weighting, not a new system)

When generating an item for a lexeme, choose exercise type by mastery:
- mastery < 0.3 → recognition (`multiple_choice`, `listen_select` where
  audio exists)
- 0.3–0.7 → structured recall (`word_order`, `matching_pairs`,
  `fill_in_blank`)
- > 0.7 → production (`translation`, free-text types)

If no template of the preferred tier can be filled for that lexeme,
fall back down the ladder rather than skipping the lexeme. Respect the
existing ≥3-option rule and the zero-`listen_select`-for-fa/prs rule
(until Phase D lands recorded audio).

### A5. Endless Practice convergence

The practice feed's sampler gains the same weighting: due lexemes
first, then low-mastery, then the existing seeded random. Feed answers
DO advance lexeme SRS (they are genuine delayed retrieval), with the
same first-answer-per-lexeme-per-day rule to prevent interval pumping
by scrolling. Diminishing-XP rules unchanged.

### A6. Verification (you, live browser, fresh accounts)

- Fresh user: complete lesson 1 → confirm SRS rows appear only for that
  lesson's lexemes, due tomorrow. Replay the lesson 3× → confirm zero
  SRS movement (this is the exact regression the old system had).
- Force a lexeme due (SQL in the local dev DB is fine for test setup),
  run a review session → confirm the exercise is freshly generated (run
  twice, confirm different surface forms), answer wrong → confirm
  repetitions reset AND the item re-queues in-session, answer the retry
  right → confirm the interval did NOT advance from the retry.
- Confirm ladder behavior: set mastery low/high on two lexemes, verify
  recognition vs production formats.
- Backend tests: population idempotency, first-answer-only interval
  rule, due-first sampling, ladder fallback.

---

## Phase B — Lesson-runner learning flow (frontend only)

### B1. In-lesson error recycling

`LessonRunnerPage` keeps a retry queue: a missed exercise is re-appended
after the remaining exercises. Lesson completion requires every exercise
answered correctly at least once. Cap: after the 2nd miss of the same
exercise, show the correct answer prominently, re-queue once more as a
"copy it" confirmation, then move on regardless (never hard-block a
beginner). Progress bar reflects the growing queue honestly.

### B2. Review warm-up

If the user has due lexemes for the lesson's course, prepend up to 2
review items (from `POST /reviews/session`) before the teaching cards,
labeled as review ("Quick review before we start"). Skip silently when
nothing is due or the endpoint fails — never block a lesson on the
review system.

### B3. End-of-lesson summary

The completion screen lists the words the learner missed this session
(from the local retry queue — no new API), each with its translation
and a speak button where audio exists. Frame it as "worth another look",
not failure.

### B4. Verification

Play a full lesson in the browser deliberately missing 2 exercises →
confirm both recycle, the 2-miss cap works, completion fires only after
all-correct, and the summary lists exactly the missed items. Confirm a
lesson with zero misses shows no summary section and no behavior change.
RTL check in fa: the retry flow renders correctly.

---

## Phase C — Feedback quality and grading honesty

### C1. Distractor-specific feedback

The overlays' whole point is interference-error distractors; make them
pay off at the moment of error. Compiler + content change (Codex):
optional `feedback_by_option` map (option-string → explanation) on
choice-type exercises, compiled into the schema-less `feedback` JSON —
zero DB migration. Frontend: when the learner picks a mapped wrong
option, show its specific explanation INSTEAD of generic feedback
("You picked ك — that's Arabic kaf; Persian uses ک").

Content pass (Codex, fresh-context reviewed like all content): add
`feedback_by_option` to existing fa/prs/en units' deliberate
interference distractors. Update AUTHORING_GUIDE: every authored
interference distractor in NEW content should carry an explanation.
After the content round, run the standing jargon-leak sweep.

### C2. Typo tolerance ("almost" state)

Free-text grading gains Damerau-Levenshtein distance-1 acceptance with
a distinct third result state: `almost` — counts as correct for XP and
SRS quality (map to quality 4 via the isolated function from A3), but
the UI shows "Almost — watch the spelling:" with a character-level
diff highlight, amber not green.

**Strictness is per-language and per-exercise, never global:**
- Default tolerant for Latin-script answers.
- Default STRICT for fa/prs and any non-Latin script (single letters
  are frequently the tested content), except where the compiler flag
  says otherwise.
- New compiler flag `orthography_strict: true|false` per exercise for
  author override; script-introduction lessons are always strict.
- Never tolerate edits that cross the script-purity boundary
  (ي→ی is not a typo to forgive silently — but DO detect it and show
  the specific Arabic-vs-Persian letter explanation, which is the C1
  mechanism).

CONTRACT.md: `AnswerOut` gains `result: correct|almost|incorrect`
(additive; keep the `correct` bool for compatibility).

### C3. Verification

Browser: pick a mapped distractor → see its specific explanation; typo
one Latin letter in a translation → amber "almost" + diff + XP awarded;
typo one Persian letter in a strict exercise → incorrect; type Arabic
kaf where Persian expected → the script explanation appears. Backend
tests for the distance function's script-boundary and strictness rules.

---

## Phase D — Recorded human audio for fa/prs (+ dialogue fix for all languages)

Recorded human audio beats any TTS for A1 scope: a few hundred short
clips, cacheable static assets, zero runtime cost, and it unblocks
listening exercises for exactly the two languages with zero TTS coverage
anywhere. Ramin records; you build the pipeline. Piper stays on the
roadmap for scale, NOT as this phase.

### D1. Recording manifest (Codex, script)

`scripts/audio_manifest.py`: walks compiled course content and emits a
deduplicated CSV/JSON of every string needing audio for a course
(tested_text of listen exercises, teaching-card vocab/phrases, dialogue
turns), each with a stable `media_asset_key` derived from content_key +
normalized text hash. Idempotent; re-running after content edits shows
only NEW strings needing recording.

### D2. Dialogue per-speaker-turn split (Codex, content pattern — ALL languages)

The known "TTS choking" bug: dialogue teaching cards store a whole
multi-speaker exchange as one `text_block` with embedded "Name:" labels
and literal newlines, sent verbatim to TTS. `text_blocks` is already a
list — re-author every dialogue card to one block per speaker turn,
with speaker name as structured metadata (`speaker` field per block),
not inline text. Frontend renders speaker labels itself and speaks each
turn separately. This fixes TTS-based languages too, independent of
recorded audio. Compiler validator: reject any new dialogue card whose
single text_block contains a newline + "Name:" pattern.

### D3. Asset storage and serving (Codex)

Static-file approach, no new infra: assets live under a served
directory keyed by `media_asset_key` (backend `StaticFiles` mount or
nginx later; local dev = a mounted folder). Admin endpoint
`POST /admin/media/upload` (key + file) for getting Ramin's recordings
in. `GET /media/{key}` serves with long cache headers.

### D4. Frontend audio priority chain

`SpeakButton`/audio playback resolves: recorded asset (if
`media_asset_key` present and resolves) → Google TTS (supported
languages, existing quota logic) → browser speechSynthesis → the
existing honest "no voice available" message. Once fa/prs A1 assets
exist, lift the zero-`listen_select`-for-fa restriction in the practice
engine FOR EXERCISES WHOSE tested_text HAS a recorded asset (check at
generation time), not globally.

### D5. Verification

Import a real recorded clip locally; browser-verify the chain: fa
exercise with asset plays the recording (network tab shows /media/, not
/tts); fa exercise without asset still shows the honest fallback;
English still uses Google TTS; a dialogue card speaks turn-by-turn with
no name-reading and no mid-line choke.

---

## Phase E — The retention loop

### E1. Home screen leads with due reviews

`HomePage` primary CTA becomes "Review — N due" (from
`GET /me/reviews/due`) whenever N > 0; "Continue lesson" second.
Zero-due state keeps the current layout. SRS only works if the app
pulls people back at the right moment.

### E2. User-timezone streaks (bug fix, do first in this phase)

Streaks currently flip at the SERVER's local midnight
(`date.today()` in `progress.py`) — wrong for any user elsewhere.
Additive migration: `User.timezone` (IANA string, nullable). Frontend
sends `Intl.DateTimeFormat().resolvedOptions().timeZone` at
register/login; streak day computed in the user's zone, UTC fallback.
Codex must audit every `date.today()`/`activity_day_bounds()` caller
(streaks, diminishing-XP daily window) in the same pass — same bug
class, fix it everywhere at once, the way the options-producing-paths
audit worked.

### E3. Streak freeze (already accepted scope) + daily quests

- One streak freeze, EARNED (e.g. at 7-day streak), auto-consumed on
  the first missed day, visibly shown ("Streak freeze used!"), re-earnable.
  Server-side in `record_activity`'s streak branch.
- Daily quests, server-authoritative, 3/day from a small pool
  ("Clear your due reviews", "Complete a lesson", "5 correct in
  practice"), small XP bonus. New table + `GET /me/quests`. Deliberately
  light — this is a nudge system, not a game economy.

### E4. Web push (PWA) — LAST, and only after E1–E3 verify clean

Service worker exists. Add push subscription + a scheduled server job
for "reviews due" and "streak at risk" (respecting user timezone from
E2). If effort balloons, stop and ship E1–E3 alone; push is
enhancement, not core.

### E5. Verification

Timezone: register a user with a non-server timezone, complete
activity 23:30 user-local, confirm the streak day boundary is theirs
not the server's. Freeze: build a 7-day streak in the dev DB, skip a
day, confirm consumption + display. Quests: complete one, confirm
server-side award and no double-award on repeat.

---

## Phase F — Unit checkpoint tests (test-out)

NOT the rejected placement-quiz enrollment system — this is assembled
entirely from existing reviewed exercises + practice templates, graded
by the existing `grade()`.

- `POST /units/{unit_id}/checkpoint` → 12–15 mixed items sampled across
  the unit's lexemes/exercises (practice-engine generation, all ladder
  tiers, strict grading — no typo tolerance), server-held answers,
  one attempt per item.
- Pass at ≥80%: marks the unit checkpoint-passed; its lexemes enter SRS
  as consolidated (mastery floor 0.5, first due +3 days) if not already
  tracked; converts `LevelCheckPage`'s honor-system "Recommended for
  you" into a demonstrated skip — "Test out of Unit 1" button next to
  the recommendation.
- Failing is cheap and kind: show which outcomes were weak, suggest the
  unit's lessons, allow retake after 1 hour (server-enforced).
- Frontend: `CheckpointPage` reusing `ExerciseRenderer` (same trick as
  practice/reviews), distinct visual framing (no teaching cards, no
  retry recycling — a test is a test).
- Verify: fresh user tests out of unit 1 → SRS rows exist consolidated,
  recommendation updates; fail path shows weak outcomes and enforces
  the retake delay.

---

## Phase G — Integrity fixes (small, fold into whichever phase touches the file first)

1. **XP grind exploit**: lesson exercise re-answers currently grant
   full XP every time. Full XP on first-correct per (user, exercise);
   1 XP trickle after. Mirrors the practice feed's diminishing rule.
2. `POST /lessons/{id}/complete` returns cumulative lifetime
   `xp_earned` as that completion's award — return this session's delta.
3. `router.py` reviews endpoint: remove the dead
   `lesson(r.exercise_id,db) if False else` expression and the
   double `db.get(Exercise)` per item.
4. Comment `hearts`/`gems` in `UserStats` as rejected scope so nobody
   "finishes" them.

---

## Phase H — Dictation exercise type (new modality)

Full spec + a self-contained context-cleared build prompt live in
**`docs/DICTATION_EXERCISE_SPEC.md`** — read it before starting. Summary:
hear a TTS target-language sentence (no source text) → type it →
orthography-strict grading. Reuses `Translation.tsx` verbatim; it is
`listen_type` with strict grading forced by type. Net work = register the
type in 9 places (4 backend rows have no automated guard) + force
strict-by-type grading. Course-content only in v1 (not Endless Practice).
**nl-first — NOT prs** (Dari has no TTS; a dictation there is an unanswerable
silent play button). Lanes: Codex = enum + Alembic constraint migration +
`VALID_EXERCISE_TYPES` + compile audio block + `FREE_TEXT_EXERCISE_TYPES` +
strict grading; Claude = shared union + renderer case + `PROMPTS` test entry +
CONTRACT.md. Motivation: the one modality lingua.com leans on that we lack;
plays into our orthography-strict grading + on-screen keyboard strengths.
(Related: a graded reading/"stories" track is now specced — see Phase I;
skill-targeted practice still gated behind the fa/prs TTS fix.)

---

## Phase I — Graded reading track (new modality)

Full spec + a context-cleared build prompt: **`docs/READING_TRACK_SPEC.md`**.
Summary: an in-lesson reading experience — a `reading` teaching card (passage +
TTS narration, both ALREADY exist) upgraded with **tap-any-word-to-gloss** (the
one net-new capability), then `reading_comprehension` questions. Research found
~70% already ships: the `reading` card kind holds multi-sentence passages (320
files), narration is free (SpeakButton on every text block), comprehension type
exists. So: NOT a new exercise type, NOT a new screen, NOT a new progress path.
Gloss data = author-controlled `glosses:` map (token→gloss) in the en-nl overlay,
compile-time-embedded + served (NOT auto-from-Lexeme — homograph/inflection
risk). Lanes: Codex = compiler emit/serve `glosses` + validator; Claude =
`GlossableText` component + wire into TeachingCardView + CONTRACT. nl-first (TTS).
Deferred: dedicated Stories screen, recorded narration, passage+question-set
object.

---

## Content program (Codex, parallel to code phases — never blocks them)

Continue the roadmap fan-out (Phase 3 Latin cohort es/fr in progress)
under the existing AUTHORING_GUIDE rules, PLUS these additions from
this program:

- Every new unit's interference distractors carry `feedback_by_option`
  entries (C1) once the compiler supports it.
- All new dialogue cards use per-speaker-turn blocks (D2) once the
  pattern lands; re-author existing dialogues in the same pass.
- **Dutch (nl) is the reference language — build it to full polish
  first.** Ramin is fluent in Dutch, making nl the only language with a
  genuine native-speaker review gate (the project's biggest accepted
  risk, closed for this one language). Priority order within the
  content program:
  1. Author the nl realization (unit 1 onward) + `en-nl` overlay.
  2. Author the `nl-en` overlay against the EXISTING English
     realization (2 units already exist — only the overlay is new;
     same reuse that worked for prs-en, and the strong sibling-file
     rule applies).
  3. Every nl unit gets BOTH reviews: the standard fresh-context AI
     review first, then Ramin's native review. Convert his corrections
     into compiler validators or AUTHORING_GUIDE rules wherever
     generalizable — that's how nl polish transfers to de and the rest
     of the Latin cohort.
  4. nl has full Google TTS support: polish the complete experience —
     audio included — on nl without waiting for Phase D. nl is the
     primary live-browser verification target for Phases A–G's UX.
- **fa/prs remain the machinery testbed, not deprioritized into rot:**
  every upgrade phase must ALSO be browser-verified against fa (RTL,
  virtual keyboard, script-strict grading, recorded-audio chain) — nl
  exercises none of those paths. Phase D's recorded audio stays
  fa/prs-scoped.
- The es/fr realizations already in progress: finish the units
  currently in flight through their review cycle, then park es/fr
  until nl is complete — don't discard work, don't split focus.
- The known `good_wish` lexeme-coverage gap (the خوش آمدید template can
  never satisfy the ≥3-option rule): add reviewed `good_wish` lexemes
  next time unit-1 fa content is touched.
- **FSI/Tatoeba policy, REVISED 2026-07-05** (now §10 of AUTHORING_GUIDE,
  superseding the original reference-only line below for FSI/Peace Corps
  specifically): FSI and Peace Corps material (public domain, no
  attribution burden — confirmed available for nl, fa, AND prs/Dari via
  Live Lingua / archive.org, including recorded audio) may now be used as
  a real scaffold — vocab progression, grammar sequencing, dialogue
  scenarios — with a MANDATORY modernization pass, never verbatim import.
  This is specifically to accelerate content velocity toward the ≥10hr
  publish-gate target for the launch languages. Tatoeba remains
  reference-only (CC-BY attribution not tracked, unreviewed) — original
  policy unchanged for Tatoeba: reference for sequencing and patterns,
  NEVER copy sentences.
- **Division of labor, REVISED 2026-07-05**: Claude may now also author
  content directly (not just Codex) — specifically the FSI/Peace-Corps
  adaptation lane above, since it's a different task shape (adapting
  real source material vs. generating from scratch) and Ramin's Claude
  Max usage has headroom to spare. Codex continues from-scratch
  generation and all backend work unchanged. Both routes go through the
  same fresh-context review + compiler validation — no shortcut on the
  quality bar for adapted content.
- After EVERY content round: jargon-leak sweep (bare snake_case in
  learner-facing strings, internal words like "reviewed" in feedback),
  script-purity, spine-outcome discipline check.

---

## Ordering, scope discipline, and definition of done

- Order: A → B → C → D → E → F, G folded in opportunistically. A is the
  foundation; B and C are independent of each other after A; D can run
  in parallel with B/C once A is merged (different files); E2 (timezone)
  can be pulled earlier if convenient since it's a live bug.
- After each phase: update CLAUDE.md's build log and CONTRACT.md, all
  tests green, live-browser evidence noted. Nothing deploys to
  192.168.4.4 without Ramin present; when it does, remember the full
  recipe INCLUDING `docker compose up -d api` at the end, migrations
  before seed, and the practice-template import + lexeme backfill order
  documented in CLAUDE.md.
- If a phase turns out to need something rejected above (runtime LLM,
  hearts, a big new dependency), stop and ask Ramin — don't design
  around the constraint silently.
- Done means: a fresh user in the browser can complete a lesson with
  error recycling, come back "tomorrow" (dev-DB time shift) to a home
  screen leading with due reviews, get a freshly-generated review
  exercise for a lexeme they actually learned, be told exactly why
  their specific wrong answer was wrong, hear a real human voice on a
  Farsi listening exercise, and test out of a unit they already know —
  with every one of those observed live, not inferred from green tests.
