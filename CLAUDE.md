# Lingo² — project state (read this first)

Local-first language-learning app, Duolingo/Babbel-caliber, 18 directed
en↔X learning paths (nl, fr, de, it, es, ru, zh, fa, prs). Backend code
and alembic migrations stay **Codex**'s lane, dispatched and verified
by Claude; language content is now authored by **both** Codex
(from-scratch generation) and Claude (adapting public-domain FSI/Peace
Corps source material — see "Division of labor" below); frontend,
orchestration, and verification owned by the executing **Claude**
session(s). For the full chronological history behind every decision
and bug below, see `docs/BUILD_LOG.md` — this file is the current
state, standing invariants, and footguns only.

## Current plan of record

`docs/SONNET_BUILD_PROMPT_UPGRADES.md` is the active work order
(phases A–G: lexeme-level SRS, in-lesson error recycling, feedback
quality, recorded fa/prs audio, retention loop, unit checkpoints,
integrity fixes) — read it before starting any new work. It also
defines the up-to-three-parallel-session ownership map (CODE / CONTENT
/ INFRA) if multiple Claude instances are running.

**Phase A — DONE, 2026-07-05, live-verified.** SRS now schedules
lexemes (not exercise instances) and generates a fresh reviewed
exercise each time one comes due, converged with the Endless Practice
engine. New: `user_lexeme_srs` table, `GET /me/reviews/due`,
`POST /reviews/session`, `POST /reviews/items/{id}/retry`, adaptive
recognition→structured→production format ladder by per-lexeme
mastery. Folded in opportunistically: the XP-grind fix, the
completion-XP-delta fix, and the dead-code cleanup from Phase G. Full
detail, what was verified, and the real (non-Codex) test-fixture bugs
found along the way are in `docs/BUILD_LOG.md`. **Genuinely closed out
2026-07-05**: Instance 3 found that a fresh 0001→head migration
crashed (invisible on the shared, already-migrated dev stack this
phase was originally verified against) — fixed and re-verified against
a truly empty, isolated database, not the shared one. See the
Footguns entry below and `docs/BUILD_LOG.md` for the full root cause.

**Phase B — DONE, 2026-07-05, live-verified.** `LessonRunnerPage`
recycles missed exercises to the end of its queue instead of a linear
index; 2 misses caps a "copy it" confirmation pass that always
resolves regardless of correctness (never hard-blocks); up to 2 due
reviews (via Phase A's `/reviews/session`) prepend before teaching
cards when a `courseId` is known (threaded through route `state` from
`CourseUnitsPage` → `UnitLessonsPage`, since no backend field maps a
lesson to its course) and skip silently otherwise; the completion
screen lists missed words with a speak button. Frontend-only, no
backend/migration changes.

**Phase E1 also done alongside Phase B** (pulled forward since it's
frontend-only and uses an endpoint Phase A already shipped): HomePage's
primary CTA becomes "Review — N due" from `GET /me/reviews/due` when
due, demoting "Continue lesson" to secondary; zero-due keeps the old
layout. Discovered and fixed a real gap while wiring this up:
`ReviewPage.tsx` still used the legacy account-wide `/me/reviews`
flow, which Phase A no longer populates from in-lesson answers at all
— rewritten to use `/reviews/session` per-course (with a course-picker
when more than one course has due items) plus the retry endpoint for
an in-place "try again."

**Phase C — DONE, 2026-07-05 (mechanism only; content pass is Session
2/CONTENT's lane).** Typo tolerance (`result: correct|almost|incorrect`
on every answer endpoint, Damerau-Levenshtein distance-1, per-language
strictness via `Language.script`, `orthography_strict` compiler
override, Arabic/Persian script-confusion pairs never forgiven) and
`feedback_by_option` (per-wrong-option explanations, JSON-encoded into
the existing `Exercise.feedback` Text column — zero migration).
**Built directly by Claude, not Codex** — the Codex dispatch hit a
real usage-limit exhaustion (not a design gap) partway through this
phase; per Ramin's standing contingency instruction, implementation
continued directly rather than blocking. Revert to normal Codex
delegation once usage resets (checking periodically — Codex still
reported exhausted as of 04:49, stated reset ~5:16 AM). Full detail in
`docs/BUILD_LOG.md`.

**Phase E2 — DONE, 2026-07-05 (also built directly, same Codex-outage
window).** Timezone-aware streaks/daily-windows: additive `User.
timezone` (IANA string, nullable, migration 0009), `app/services/
progress.py`'s `record_activity()`/`activity_day_bounds()` now take a
`user_timezone` param (UTC fallback for missing/invalid values) instead
of `date.today()`/server-local `datetime.now()` — audited and fixed
every call site (5 total, all in `router.py`: the streak-updating
`record_activity()` calls in `exercise_answer()`/`review_answer()`/
`practice_answer()`, and both `activity_day_bounds()` calls gating
practice's diminishing-XP/per-lexeme-per-day windows). Frontend sends
`Intl.DateTimeFormat().resolvedOptions().timeZone` at register/login;
backend validates against the IANA database before persisting (login
also refreshes it if it changed). **Real bug caught while wiring this
in**: `schedule()`'s mastery-delta line used to truthiness-check the
`correct` parameter directly — once that parameter could be the
*string* `"incorrect"` (Phase C), that line would treat it as truthy
and wrongly award the success bonus. Fixed with an explicit `success =
quality >= 3` boolean (see Phase C notes in `docs/BUILD_LOG.md`).
**Also found while applying this migration**: the dev DB's
`alembic_version` table didn't exist at all despite the schema
correctly reflecting migrations through 0008 — `alembic upgrade head`
failed trying to re-run 0008's `ADD COLUMN` against a column that
already existed. Fixed by `alembic stamp 0008` before upgrading; see
`docs/BUILD_LOG.md` for what this might mean for the dev DB's history
and what to watch for.

**Phase E3 (streak-freeze half only) — DONE, 2026-07-05, same outage
window.** One earned, auto-consumed, re-earnable streak freeze: `user_
stats.streak_freezes_available`/`last_freeze_used_date` (migration
0010), earned at every 7-day streak milestone while none is banked,
silently covers exactly one missed day in `record_activity()` instead
of resetting the streak, surfaced via `GET /me/streak`'s new fields
and a ❄️ indicator + "Streak freeze used!" banner on `HomePage`.
**Daily quests (the other half of E3) intentionally NOT built** — a
properly separable, well-scoped new subsystem (new table, generation
logic, progress-tracking hooks into lesson/review/practice completion)
better suited to a fresh Codex dispatch once available than to
continuing the direct-build exception further.

Starting point once Codex usage resets: hand back Phase D (recorded
fa/prs audio), E3's daily quests, and E4 (web push) — this multi-phase
direct-build stretch (C, E1, E2, E3-half) was the outage exception, not
a standing change to the division of labor.

**Codex usage reset ~5:16 AM as stated — back to normal delegation.**
Probed successfully at 05:19.

**Phase D3 + D2 (compiler validator half) — DONE, 2026-07-05, back to
normal Codex delegation.** Recorded-audio mechanism: `POST /admin/
media/upload` (multipart, admin-auth) and `GET /media/{key}` (long-
cache, real 404 for not-yet-recorded keys — expected, not an error)
serving flat files from `backend/media_assets/{key}.mp3`, zero new DB
tables (explicitly avoided the dead `MediaAsset`/`Dialogue` scaffolding
discovered while scoping this — third instance of that pattern this
session, after `AnswerSpec` and `ExerciseAttempt.outcome`). Compiler
now rejects any NEW dialogue teaching card using the old single-block-
with-embedded-"Name:"-labels anti-pattern; `TextBlock` gained an
additive `speaker` field for properly-split cards. Frontend
`speak()`/`SpeakButton` gained the documented priority chain (recorded
asset → Google TTS → browser speechSynthesis → honest fallback),
wired into the 3 listen-type exercise components
(MultipleChoice/Translation/WordOrder) via each prompt's
`media_asset_key`. **Explicitly NOT done, Session 2/CONTENT's lane**:
re-authoring any EXISTING dialogue cards into the new per-speaker-turn
shape — the compiler validator only blocks new/edited cards using the
anti-pattern, it doesn't touch anything already compiled. D1 (recording
manifest) was already built by Session 3 earlier. D4's "lift the
zero-listen_select-for-fa restriction for exercises with a recorded
asset" (practice engine change) not yet done — no real fa/prs
recordings exist yet to make it meaningful. Full detail in `docs/
BUILD_LOG.md`.

**Phase E3 daily quests (the other half) — DONE, 2026-07-05, Codex,
normal delegation.** `GET /me/quests` — 3 hardcoded quests ("Clear your
due reviews," "Complete a lesson," "5 correct in practice"), progress
computed LIVE against existing state each request (due-lexeme count,
today's `LessonProgress`/`PracticeAttempt` rows, all in the user's own
timezone via E2's `activity_day_bounds()`) rather than tracked via
hooks into the answer endpoints — a new `QuestCompletion` row (migration
0011) records the award exactly once per user/quest/day so repeat
`GET`s never double-pay XP. Deliberately avoided two dead, pre-existing
`DailyQuest`/`UserDailyQuestProgress` models discovered while
implementing this (unreferenced anywhere in `app/`, fourth instance of
this exact pattern this session after `AnswerSpec`, `MediaAsset`/
`Dialogue*`, and the once-unused `ExerciseAttempt.outcome`) — built
fresh instead of forcing the new live-computed design onto that old
persisted-definition shape. Both halves of Phase E3 are now done; E3 as
a whole is complete. Live-verified against a real test user's actual
accumulated activity today (not just synthetic fixtures) — correctly
showed one quest already complete from earlier real activity, XP
confirmed unchanged across repeated calls.

**Phase F backend (unit checkpoint / test-out) — DONE, 2026-07-05,
Codex, normal delegation.** `POST /units/{unit_id}/checkpoint`
generates 12–15 items from the unit's own lessons via a new
`generate_checkpoint()` (reuses the practice engine's `_material()`/
`_generate_prioritized()`, `source="checkpoint"`, not gated on lesson
completion — "test out" means skipping the lessons); items are graded
via the shared `/practice/items/{id}/answer` endpoint but with
`orthography_strict` forced `True` (no typo tolerance for a pass/fail
assessment) and never touch per-item `UserLexemeSRS` scheduling.
`GET /units/{unit_id}/checkpoint/result` scores the session once all
items are answered (≥80% passes), consolidates SRS in bulk for
lexemes the checkpoint covered THAT AREN'T ALREADY TRACKED (mastery
floor 0.5, due +3 days — existing rows are never touched), reports
weak-outcome glosses on a fail, and is idempotent (repeat calls return
the same persisted result). A 1-hour retake delay is enforced via a
Postgres advisory lock + `429 checkpoint_retake_delayed` with
`retry_after_seconds`. `GET /courses/{course_id}/units` now also
returns `checkpoint_passed` per unit — the hook the frontend needs for
a future "Test out of Unit 1" button. New `CheckpointAttempt` table
(migration 0012). Live-verified against real en-fa content on the
actual running stack, including both the "leave already-tracked
lexemes alone" path (a long-lived test account) and the "consolidate
untracked lexemes" path (a brand-new account, 15 fresh SRS rows at
exactly mastery=0.5/interval=3), plus the retake-delay firing
correctly on a real second attempt. Full detail in `docs/BUILD_LOG.md`.

**Phase F frontend — DONE, 2026-07-05.** New `CheckpointPage`
(`/units/:unitId/checkpoint`) reusing `ExerciseRenderer` like Practice/
Review do, but deliberately distinct: no teaching cards, no B1-style
error-recycling (a wrong answer moves straight to the next item, "a
test is a test"), a persistent "Unit checkpoint" header banner instead
of the lesson XP counter. Handles all 4 backend states: starting
(`POST .../checkpoint`), the 429 retake-delay (shows a live countdown
from `ApiError`'s new `details` field — `ApiError`/`ApiErrorBody`
extended additively to carry error fields beyond `code`/`message`),
generation-unavailable (409, not enough material), and the scored
result (pass/fail, score %, weak-outcome list, links back to the
unit's lessons or the course list). `CourseUnitsPage`'s `PathNode`
gained a "Test out of this unit" button next to the existing
"Recommended for you" badge (shown only when recommended AND not yet
passed) and a standalone "Checkpoint passed ✓" badge (shown on ANY
passed unit, independent of the recommendation) using the new
`checkpoint_passed` field. `docs/CONTRACT.md`'s checkpoint section
rewritten to match the ACTUAL shipped shapes (it previously only had
the pre-implementation placeholder example) — also caught and fixed a
separate staleness bug while there: the `/me/streak` doc block still
showed the pre-E2/E3 shape, missing `streak_freezes_available`/
`freeze_used_today` added earlier this session. Small Codex round-trip
for fa/prs translations of the 22 new UI strings, same pattern as
every other phase this session. Live-verified end-to-end in the
browser on real en-fa content, not just curl: played a full 15-item
checkpoint through every exercise type it generated, got a genuine
73% fail result with the exact 4 wrong answers' glosses listed as
weak outcomes, confirmed the retake-block screen (both freshly and
after browser-back navigation), and confirmed both unit-path badges
render correctly and independently by toggling the local level
preference between two units (one already-passed, one not). Full
detail in `docs/BUILD_LOG.md`.

**Phases A through F are now all shipped and live-verified this
session.** Remaining from the original upgrade program: E4 (web push
— explicitly last-priority, its own spec says to skip if effort
balloons), and the two pieces explicitly left for other sessions'
lanes (D2's actual dialogue-content re-authoring, C1's feedback_by_
option content pass — both Session 2/CONTENT). Phase G's integrity
fixes were folded in opportunistically throughout (see each phase's
entry above). Next up for whoever continues this: E4, or start on
Session 2's content backlog if that's in scope for this session, or
begin the deeper content-authoring work needed to actually hit the
2026-07-05 publish-gate content-depth bar (≥10hr teaching + ≥10hr
practice per launch pair) — the mechanism is now fully built across
every phase, but real full-depth content for en-nl/en-fa/en-prs is
the actual remaining path to launch.

`docs/APP_SPEC_FOR_FABLE_REVIEW.md` is the architecture snapshot +
review that produced the upgrade program — read for the "why" behind
Phase A's SRS redesign and the content-architecture rationale.

**Scope decision, 2026-07-05: end goal is genuine fluency (full CEFR
A1→C2), but publish is a much earlier, separate gate.** Publish-gate
language set: **en↔nl and en↔fa/prs only** (6 directed paths) — the
languages Ramin can personally verify. The other 15 paths keep
building per the existing phase order as post-launch drip content, not
blocked.

**Publish-gate quality bar: "very usable, minimum bugs," not a phase
checklist.** Beta users on en-nl/en-fa/prs need to hit essentially no
functional breakage so their feedback is about content/pedagogy/UX,
not bug reports. **The Claude session does this verification BEFORE
any user sees it** — the existing non-negotiable verification bar
below (compiler + backend pytest + full frontend build + live browser
verification with a fresh account) applied specifically to the actual
lesson/review/practice flows on these three languages is what earns
"minimum bugs," not user reports. The report-button → triage-queue
loop is the NEXT layer, once the app is already solid — not a
substitute for pre-launch verification.

**Publish-gate content depth: ≥10 hrs new teaching content + ≥10 hrs
practice + working scored module checkpoints, per launch language
pair.** Enough for real day-to-day use in-country, not a demo. The ≥10
practice hours are meant to come from the Endless Practice engine
(currently fa→en-only — needs extending to all 6 launch paths), not
hand-authored drills. "Module tests with scores" = Phase F (unit
checkpoint tests) is now a hard publish-gate requirement, not
deferred post-launch polish. Full detail in
`docs/APP_SPEC_FOR_FABLE_REVIEW.md` §1 and the
`project-lingosquared-roadmap` memory file.

`docs/content/AUTHORING_GUIDE.md` is binding for all content authoring
(spine discipline, exercise pacing, dialect authenticity, jargon leaks,
YAML footguns, sibling-file isolation). `docs/CONTRACT.md` is the
API/schema contract both sides build against — update it before
implementing any contract change, never after.

**Reference language: Dutch (nl).** Ramin is fluent in Dutch, so nl is
being built to full polish first (native review, not just AI review)
and is the primary UX verification target for the upgrade phases.
fa/prs remain the mandatory RTL/virtual-keyboard/script-strict-grading
verification target for every phase regardless — don't let them rot.
es/fr: finish in-flight units, then park until nl is done.

## Division of labor and delegating to Codex

Codex owns `backend/app/**`, alembic migrations, and
`scripts/compile_content.py`. The Claude session owns `frontend/src/**`,
CONTRACT.md, orchestration (extract → validate → apply Codex's output),
and ALL verification — never trust Codex's self-report; diff full-file
rewrites against the prior version before applying (a rewrite once
silently introduced an unrelated one-line query bug alongside a correct
fix).

**Content authorship, REVISED 2026-07-05: Codex and Claude both author
language content now, in parallel.** Originally "every word of language
content" was Codex-only (Ramin's call, non-English generation strength).
That's now expanded, not reversed: Ramin has Claude Max headroom to
spare and wants it used. Claude's new lane specifically is adapting
public-domain FSI/Peace-Corps source material (see
`docs/content/AUTHORING_GUIDE.md` §10) into spine-compliant
realization/overlay drafts — a different task shape (adapt real source
material vs. generate from scratch) rather than head-to-head
competition on original-language generation, where Codex's strength was
the original reasoning. Codex keeps doing from-scratch generation and
all backend work unchanged. Both routes go through the identical
fresh-context review + compiler validation pipeline — content Claude
authors gets zero quality-bar exception for being "the same session
that also builds the frontend."

Codex's sandbox defaults to wherever the Claude session's cwd is
(often a different project) — always pass `--cwd` explicitly:

```bash
node "/Users/raminazizi/.claude/plugins/cache/openai-codex/codex/1.0.5/scripts/codex-companion.mjs" task \
  --cwd /Users/raminazizi/dev/LingoSquared --background --write --resume "…prompt…"
```

Check status/result the same way (`status <job-id> --cwd ... --json` /
`result <job-id> --cwd ...`). If the plugin path/version has changed,
look under `~/.claude/plugins/cache/openai-codex/` rather than trusting
the pinned path above. Codex has no Docker and no outbound network —
it writes and static-checks code only; real build/test/deploy
verification is always the Claude session's job. If Codex auth fails
with a revoked refresh token, stop and tell Ramin to run `codex login`
rather than retrying.

Content-authoring dispatches to Codex must always include, up front:
the recognition→drag→production pacing rule, and — when authoring a
source overlay against an existing target realization — the STRONG
form of the sibling-isolation rule ("treat the sibling-direction
overlay as if it does not exist, do not open it at all"; "for
reference only" has demonstrably failed twice). Point every content
task at `docs/content/AUTHORING_GUIDE.md` (and, once it exists,
`docs/content/AUTHORING_PROMPT_TEMPLATE.md`), and route every
deliverable through a SEPARATE fresh-context review task (zero access
to the authoring reasoning) before import.

## Tooling built by Session 3 (INFRA), 2026-07-05

- `scripts/verify.sh` — one-command check: content compiler validation
  (reads `scripts/content_manifest.txt`/`practice_manifest.txt`,
  update those when you add a course/pack) + backend pytest (isolated
  test DB, the exact safe recipe below) + full frontend build. Flags:
  `--content-only`/`--backend-only`/`--frontend-only`/`--skip-*`. Add
  `--e2e` (or `--e2e-only`) to also run the Playwright suite below —
  opt-in, not part of the default run, since it needs a live seeded
  backend.
- `e2e/` — Playwright suite covering auth, the two-step course picker,
  lesson teaching-card flow, practice-feed locked state, and nav
  smoke-testing. Runs its own dev server on port 5175 (inside the
  CORS_ORIGINS allowlist, away from 5173/5174) so it doesn't fight a
  human's manual-testing tab. Verified live, 8/8 passing — see
  `e2e/README.md` for what it does and does NOT cover (answering
  exercises through to completion needs a human; grading is real
  server truth with no test-only reveal endpoint).
- `docs/content/AUTHORING_PROMPT_TEMPLATE.md` — fill-in-the-blanks
  Codex dispatch templates (realization / overlay / fresh-context
  review) with every standing rule baked in.
- `scripts/audio_manifest.py` — aggregates the `media_assets:` block
  every realization file already declares (content_key/language/
  text/voice_hint/status) into one project-wide recording queue,
  cross-referenced against `backend/media_assets/` (Phase D
  scaffolding; the actual serving route is Phase D3, not built yet).

## Verification bar (non-negotiable)

- Compiler validation green (`.content-venv/` has PyYAML;
  `scripts/compile_content.py` — or `scripts/verify.sh` once built).
- Backend pytest green: real Postgres via docker compose, isolated
  test DB, `python -m pytest` (bare `pytest` doesn't put `/app` on
  `sys.path` in the container — imports fail).
- Frontend: the FULL `npm run build` (`tsc -b && vite build`), never
  just `tsc --noEmit` — the full build has twice caught type errors
  noEmit alone missed.
- Live browser verification with a fresh test account for anything
  user-facing. Reading a diff is not verification — this project's
  worst bugs (six unregistered exercise types, a permanently-disabled
  Respond button, distractors drawn from the whole course vocabulary,
  a deleted logout button) were ALL found only by actually playing a
  lesson in the browser.
- Local stack only: `colima start`; `cd backend && docker compose up
  -d` (isolated `backend/.env`, random JWT secret, never committed).
  Never touch the live server (192.168.4.4) unattended — deploys
  happen with Ramin present.

## Footguns (hard-won, do not relearn these)

- **Every migration after 0001 must defensively check existence
  before `op.add_column`/`op.create_table`/`op.create_foreign_key`/
  `op.create_index`.** `0001_initial.py` calls `Base.metadata.
  create_all()` against the LIVE ORM models (intentional, established
  convention — see `0005`'s own code comment) — since `app/models/
  __init__.py` imports everything, a genuinely fresh migrate creates
  every table with its CURRENT column set in one shot at 0001, not a
  historically frozen shape. `0002`-`0007` already guard correctly
  (`sa.inspect(bind)` before acting, or `checkfirst=True`); `0008`
  through `0012` didn't and were fixed 2026-07-05 after Instance 3
  caught a fresh-migrate crash — full root-cause writeup in
  `docs/BUILD_LOG.md`. Any NEW migration that adds a column/table/FK/
  index must follow this same guarded pattern or it will crash on the
  next genuinely fresh deploy/CI run while looking completely fine on
  any already-migrated stack.
- **`docker compose restart` does NOT reload `.env`** — only `up -d`
  (or `--force-recreate`) does. A stale-env CORS failure once looked
  like a code bug and wasn't.
- **Never use `docker compose --env-file` for tests** — it only
  affects `docker-compose.yml` variable substitution, not the
  container's actual environment (`env_file: .env` always wins). This
  mistake once ran the test suite against the LIVE database, wiping
  and reseeding production data repeatedly. Use the isolated
  dropdb/createdb recipe below instead.
- **`scripts/compile_content.py`'s `--realization`/`--overlay` flags
  are `nargs='+'`, not `action='append'`** — the interleaved form
  `--realization A --overlay A --realization B --overlay B` silently
  keeps only the LAST value with no error. Correct form: all
  realizations together, all overlays together, matched by position —
  `--realization A B --overlay A B`.
- **`backfill_lexemes.py` needs the full repo mounted** — the backend
  Docker image only contains `backend/`, not repo-root `docs/`/
  `scripts/`. Working invocation (documented in the script's own
  docstring): `docker compose run --rm -v "$(cd .. && pwd):/repo" -e
  PYTHONPATH=/repo/backend --entrypoint python api
  /repo/scripts/backfill_lexemes.py`.
- **Google Cloud TTS `RefreshError: invalid_grant: Invalid JWT
  Signature`** means the service-account private key content is
  corrupted (usually from a GUI-editor copy-paste mangling a
  multi-line string) — NOT a permissions/IAM/API-enablement problem
  (that shows as 403/different 401). Debug path: `json.loads` the key
  → `Credentials.from_service_account_info()` (structure only) →
  `creds.refresh()` (this is what actually surfaces the JWT error).
  The `/tts` route's `except Exception` swallows the real exception
  with no logging — call `tts_service.synthesize()` directly via a
  `docker compose run` one-off to see it. Never hand-copy a
  service-account JSON through a GUI text editor; read and write the
  file's exact bytes programmatically.
- **Content seeding is create-missing-only, not delete-and-recreate**
  (an earlier version wiped user progress via cascade on every
  deploy — fixed, don't regress it).
- **Exercise-type registration must be checked exhaustively, not
  one-at-a-time**: `comm` diff every `type:` used in
  `docs/content/realizations/` against every `case` in
  `ExerciseRenderer.tsx` after any content or exercise-type change —
  the compiler's actual output shape and the frontend's assumed shape
  aren't connected by the type system, so a mismatch compiles clean
  and only crashes a real lesson in the browser.
- **Sweep for internal-jargon leaks after every content round**: bare
  snake_case tokens in `options`/`distractors`/`correct_option`
  (`null_subject`, `both_speakers` have both shipped for real), and
  internal words like "reviewed" leaking into learner-facing feedback
  text. Grep `docs/content/` periodically, don't wait to trip over it.
- **Never write bare `yes`/`no`/`true`/`false`/`on`/`off` as a YAML
  string value** in content fields — PyYAML silently coerces these to
  booleans. Always quote (`"Yes"`). The compiler validates this now
  but don't rely on catching it after the fact.
- **A frontend exercise component's submitted answer shape must match
  what content is actually authored in, not what looks natural to
  code in React state.** Found live 2026-07-05: `MatchingPairs.tsx`
  kept its matches as a flat `Record<left,right>` and submitted that
  directly, but every `matching_pairs` exercise's `accepted_answers`
  across the whole content set is authored as an ARRAY of `{left,
  right}` pair objects — the two shapes never compared equal, so
  every matching_pairs exercise in every course/language was scored
  wrong regardless of what the learner picked, and the wrong-answer
  banner's `String(correct_response)` on that same array-of-objects
  shape rendered the literal text `[object Object],[object Object]`
  to real users. Neither half was caught by `tsc`/the build (both are
  untyped `unknown`/loose-union payloads) or by any existing test —
  only playing a real lesson in the browser and actually checking
  whether a correct match graded correct surfaced it. Fixed in
  `MatchingPairs.tsx` (submit `pairs.map(p => ({left, right}))`, same
  order content is authored in) and via a new shared
  `frontend/src/lib/formatAnswer.ts` used everywhere `correct_response`
  is displayed. Lesson: whenever an exercise component's answer
  payload shape isn't string/string[], go read what `accepted_answers`
  actually looks like in a real content file before trusting either
  end's assumption — don't infer the contract from one side only.
  **Second half, same day**: the frontend fix alone wasn't sufficient —
  the Endless Practice engine's `derive_answer()` (`app/practice/
  service.py`) independently produces a FLAT `{token: gloss}` dict as
  `PracticeItem.correct_response` for `matching_pairs`, and it renders/
  grades through the exact same `MatchingPairs.tsx`/`grade()` path as
  compiled lesson content. Fixed by making `grade()`
  (`app/api/router.py`) canonicalize either representation (flat dict
  or `{left,right}[]`, any order) for this exercise type before
  comparing, rather than picking one shape as canonical — the two
  content sources (hand-authored vs. generated) disagree on shape and
  both need to keep working.

## Where things run

- **Backend (live)**: `ramin@192.168.4.4` (SSH key-based), code at
  `/home/ramin/LingoSquared/backend`, API on **port 8010** (8000 is
  used by an unrelated service, `audiobookrequest`, on that box).
  `/docs` (OpenAPI) at `http://192.168.4.4:8010/docs`. `192.168.4.8` is
  a DIFFERENT machine (SMB-only NAS, no SSH/Docker) — don't confuse them.
- **Frontend (dev)**: `cd frontend && npm run dev`. Port 5173 is often
  taken by an unrelated project on this machine; Vite falls back to
  5174 — check actual terminal output. `.env`'s `VITE_API_BASE_URL`
  points at localhost or the live 192.168.4.4:8010 backend depending
  on what you're testing.
- Backend's `CORS_ORIGINS` in its `.env` must list whatever port the
  frontend is actually running on.

## Deploying a backend change

```bash
rsync -az --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
  /Users/raminazizi/dev/LingoSquared/backend/ ramin@192.168.4.4:/home/ramin/LingoSquared/backend/
rsync -az /Users/raminazizi/dev/LingoSquared/docs/ ramin@192.168.4.4:/home/ramin/LingoSquared/docs/

ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose build api"
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose run --rm api alembic upgrade head"
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose run --rm api python -m app.content.seed"
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose up -d api"   # easy to forget — without it the live container keeps serving the OLD image
```

Test suite on the server (isolated DB, never `--env-file`):

```bash
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && \
  docker compose exec -T db dropdb -U lingosquared --if-exists lingosquared_test && \
  docker compose exec -T db createdb -U lingosquared lingosquared_test && \
  docker compose run --rm api sh -c 'DATABASE_URL=\$(python3 -c \"import os,re; print(re.sub(r\\\"lingosquared\$\\\", \\\"lingosquared_test\\\", os.environ[\\\"DATABASE_URL\\\"]))\") python -m pytest -q'"
```

Practice-feature deploys additionally need the practice-template admin
import + the lexeme backfill, in that order, after migrations.

## Secrets

TTS is Google Cloud (service-account JSON via
`GOOGLE_CLOUD_TTS_CREDENTIALS_JSON` env var, raw JSON content not a
file path), proxied server-side only — never sent to the frontend.
Farsi/Dari have zero Google Cloud voices; browser `speechSynthesis` is
the fallback (see Known limitations). ElevenLabs is no longer the
live provider (superseded 2026-07-04) — historical account/voice
gotchas are in `docs/BUILD_LOG.md` if ElevenLabs is ever revisited.
**Investigated 2026-07-05 whether the public-domain FSI/Peace Corps
audio helps here: it doesn't, directly.** The Persian FSI tapes are 24
long, unsegmented per-unit recordings (~436 min total, one file per
half-tape's basic sentences + drills), not per-phrase clips — no
splicing into individual exercises without real manual editing. Only
real use: a pronunciation-calibration reference for a human doing an
actual fa/prs recording session, not a content or asset shortcut.
Don't re-investigate this without new information.

## What's built and verified live

Auth; all 10 languages (fa/prs fully separate, correct RTL + script
metadata); courses → units → lessons → all 13 exercise types; SM-2
review (being replaced by lexeme-level SRS, Phase A); gamification
(XP/streak/achievements); reading/writing vs. speaking course sections
with server-enforced unlock; CEFR levels A1–C2; teaching phase before
exercises; in-app content-issue reporting + admin triage + coverage
dashboard; Endless Practice generative feed (fa-en pilot, lexeme pool +
reviewed sentence-frame templates, zero runtime LLM calls); on-screen
virtual keyboard for non-Latin scripts; self-reported level check with
recommended-unit badge (not a placement system — that was explicitly
rejected as premature).

Seeded courses (structure + example, not full curricula): en→fa,
en→prs (A1 + A2), prs→en, plus es/fr (1 unit each, in progress).

## Known limitations / accepted scope

- Only ~2 of 19 A1 spine outcomes built, for a handful of 18 paths —
  the single biggest gap; content is a genuinely multi-month build.
- Dari's browser-TTS fallback quality is uncertain (falls back to
  `fa-AF` approximation; may produce no sound or wrong accent).
- No native-speaker review network in general — nl is the deliberate
  exception (Ramin reviews it directly).
- Admin content import/export is API-only, no UI (intentional trim).
- Writing prompts graded by exact string match (Phase C adds
  distance-1 typo tolerance, per-language strictness).
- **Pre-deploy/pre-beta-invite checklist item (found in the 2026-07-05
  security pass): confirm `ADMIN_EMAILS` on the live deployment is
  Ramin's actual private email, not the `.env.example` placeholder
  (`admin@example.com`), and that his account is already registered
  under it.** `register()` grants `is_admin` at signup to whoever
  registers first with an email literally listed in `ADMIN_EMAILS` —
  there's no email verification anywhere (an existing, accepted, unrelated
  limitation) closing that race. Not a code bug, a deployment step;
  full detail in `docs/BUILD_LOG.md`'s security-audit entry.
- No refresh tokens, password reset, or email verification.
- No mobile app (Expo React Native is the recommended future path,
  reusing the existing JWT/JSON API as-is).
- Rejected, don't re-propose without a strong new reason: hearts/lives,
  leagues/leaderboards, gems/currency, runtime-LLM content generation,
  a placement-quiz enrollment system (self-report + checkpoint test-out,
  Phase F, is the accepted alternative).
- **`POST /admin/content/import` only creates brand-new courses** — it
  skips any course that already exists by `(source_language,
  target_language, title)` rather than appending new units to it.
  Found 2026-07-05 while trying to get new fa units 3/4/5 live: an
  already-seeded course (e.g. "Farsi A1") silently no-ops on any
  further import, so every unit authored beyond a course's initial
  seed is currently stuck validated-on-disk but never live. Real
  blocking gap for the publish-gate content-depth goal, not yet fixed
  — needs either a new "append units" admin endpoint or documented
  guidance on an existing mechanism. See `docs/BUILD_LOG.md`.
- **Fixed 2026-07-05 (Session 2/CONTENT, Phase D2)**: the full fa
  course now compiles end-to-end. `fa/a1_unit01_greetings.yaml`
  lesson06 (6 combined two-speaker cards) and `fa/
  a1_unit02_introductions.yaml` lesson06's `exchange_origins` card (1
  combined card) used the old embedded-multi-speaker-label dialogue
  format the compiler's per-speaker-turn validator rejects — split
  into one `text_blocks` entry per speaker turn, with the speaker name
  moved to the new structured `target.speaker` field (propagates
  automatically into the compiled `text_block` — no compiler code
  change needed, `target` is passed through as-is) instead of being
  baked into the spoken `text` as a literal "Name:" prefix. Overlay
  glosses/notes split to match the new per-turn content_keys. All 5
  en-fa units (1-5) validate together, 0 errors/0 warnings. **Not yet
  done, a separate smaller polish item**: several OTHER already-
  existing single-turn dialogue cards (fa unit02's `arrival`/
  `meet_mina`/`sara_name`/`ask_origin`/`pleased`/`pleased_and_enter`,
  and all of units 04/05) still bake the speaker's name into `text`
  as a literal prefix instead of using the structured `speaker` field
  — they don't trip the compiler validator (single block, no newline)
  so they're not blocking, but a real recorded/TTS voice will still
  read the name aloud on those specific cards until they're migrated
  the same way. Low priority vs. new content, flagging for whenever a
  dialogue-audio pass touches those units.

## History

Full chronological build log, every bug found and fixed, and the
reasoning behind every past decision: `docs/BUILD_LOG.md`.
