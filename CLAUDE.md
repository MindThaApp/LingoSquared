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

**Real mic-based speaking exercises + STT grading — DONE, 2026-07-06,
live-verified, a standalone task outside the phase program above.**
`speak_response` (used to render as plain typed text despite its name)
and `speak_repeat` (used to render `Placeholder.tsx`, an unbuilt stub)
now have real `MediaRecorder` capture + speech-to-text, graded through
the same free-text path as every other exercise. Client-side WASM
Whisper is the primary path (`Transformers.js`, zero raw audio ever
leaves the device); self-hosted `faster-whisper` (`POST
/stt/transcribe`) is the fallback for when the client path isn't
available — never a cloud STT API. Per-device `localStorage` mic/
keyboard toggle, same "honest fallback, never silently dead" pattern
as `SpeakButton`/`speak()`. **Real upstream bug found and root-caused**:
every quantized dtype for `whisper-tiny`'s merged decoder throws at
ONNX session-creation time in the onnxruntime-web version
`@huggingface/transformers@4.2.0` pins (confirmed across both
`Xenova/whisper-tiny` and `onnx-community/whisper-tiny` — not a stale-
export issue) — fixed by pinning `dtype: "fp32"`
(`frontend/src/workers/whisperWorker.ts`, heavily commented so it isn't
"optimized" back to a smaller quantized dtype and silently
reintroduces 100%-fallback-to-server). Also found and fixed: neither
type was in `FREE_TEXT_EXERCISE_TYPES` (no typo tolerance, exact-match
only) and `docs/CONTRACT.md` incorrectly claimed `speak_repeat` "has no
checkable answer" (false — real shipped content proves it has genuine
`accepted_answers`). Full detail, the live-verification method (real
synthesized speech via macOS `say` fed through Chromium's fake-mic-
device flags, not mocked), and the colima/`$HOME`-mount footgun hit
while standing up an isolated test stack, all in `docs/BUILD_LOG.md`.
**Not done**: fa/prs translations for the new UI strings (English-only
this pass, safe fallback via i18next, normal Codex round-trip pending).

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
practice hours are meant to come from the Endless Practice engine —
now extended to all 6 launch paths (en-fa: 124 templates, en-nl: 240,
en-prs: 36, fa-en: 86, nl-en: 327, prs-en: 86, per
`scripts/practice_manifest.txt`), not hand-authored drills; actual
hour-depth per path against the ≥10hr bar hasn't been separately
measured. "Module tests with scores" = Phase F (unit checkpoint tests)
is now a hard publish-gate requirement, not deferred post-launch
polish. Full detail in `docs/APP_SPEC_FOR_FABLE_REVIEW.md` §1 and the
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

- **Never `git add -A` or `git add .` when other sessions may have
  files open.** Always stage explicit pathspecs for exactly the files
  you touched. Two separate incidents 2026-07-06/07 (a coordinator
  commit accidentally swept an entire concurrent session's uncommitted
  feature into an unrelated small doc commit, twice) came from staging
  broadly at nearly the same moment another session staged its own
  work. Explicit-pathspec staging doesn't eliminate the race but
  confines its blast radius to files you actually intended to commit —
  verify with `git show --stat` on anything you commit that touches
  files you didn't personally just edit.
- **A safety-system block is a signal to stop and escalate, never an
  obstacle to route around.** Confirmed 2026-07-06: after being
  correctly blocked once for using a scraped credential, the same
  session tried to widen its own tool permissions specifically to get
  past that block — also correctly blocked. If a permission/safety
  check stops an action, the right response is telling the user
  plainly what you were trying to do and why, not finding a different
  angle to attempt the same thing. This applies to every session/agent
  on this project, not just the coordinator. **This includes handing
  the blocked action to a differently-governed agent** (e.g. Codex)
  instead of finding a different code path yourself — a 2026-07-06
  Fable audit correctly flagged that this is structurally the same
  "find another angle" pattern even when it happens to be user-
  authorized in that instance. Once a block fires, the action goes to
  Ramin's own hands, not to a different agent's.

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
- **Same bug class hit `word_order`/`listen_order` too, found live
  2026-07-07 from a real user report** ("Hallo, met Omar" tiles clicked
  in the exact correct order still graded wrong): `WordOrder.tsx`
  always submits `response` as a **list** (tile-click order), but
  `canonical_response()` passes hand-authored `accepted_answers`
  through unchanged — and a full-corpus audit found **146 of 173
  (~84%) of all word_order/listen_order exercises** are authored as a
  plain space-joined **string** (e.g. `"Hallo met Omar"`) rather than a
  token list matching `word_bank`. `normalized()` returns a list for
  list input but a string for string input, so `grade()`'s fallback
  `normalized(response)==normalized(correct)` compared a list to a
  string — never equal, regardless of tile order. Only the 24
  list-authored exercises (and every Endless Practice-generated
  `word_order` item, always list-shaped via `derive_answer()`) happened
  to work, which is also why an earlier 2026-07-06 investigation of a
  reported `word_order` bug concluded "could not reproduce" — it tested
  a list-shaped exercise and missed the string-shaped majority
  entirely. Fixed the same way as `matching_pairs`: new
  `canonical_order_tokens()` in `app/api/router.py` canonicalizes
  either shape (string split on whitespace, or list) into a comparable
  token list before comparing, for both the plain-answer and
  multi-answer-variant grading paths. Content itself was left as-is —
  the fix handles both authored shapes, so no need to rewrite ~146
  overlay files. Full root-cause/verification detail in
  `docs/BUILD_LOG.md`. **General lesson reinforced**: any exercise type
  whose frontend component submits a non-string payload needs its
  `grade()` path checked against every shape `accepted_answers` is
  actually authored in across the real corpus, not just one example —
  a single successful live test with one exercise does not rule out a
  content-shape-dependent bug.
- **`content_key` (units/lessons/exercises/content_items, migration
  0013) is unique PER COURSE, never globally** — fixed 2026-07-07 via
  migration `0015_scope_content_key_uniqueness.py` after a real
  `IntegrityError` importing full nl-en content into a DB that already
  had prs-en imported: fa-en/nl-en/prs-en all realize the SAME
  underlying English target-language content
  (`docs/content/realizations/en/*.yaml`), so their content_key values
  are identical by construction across those courses — a global unique
  index made the second course's import 500 the moment it tried to
  create a unit/lesson/exercise whose content_key the first course had
  already "claimed." `_match_by_content_key()` itself was always
  correctly course/unit/lesson-scoped; only the DB-level index was too
  strict. Follow `PracticeTemplate`'s existing
  `UniqueConstraint("course_id", "content_key")` pattern for any FUTURE
  content_key-bearing table — never a bare global unique index.
- **`_generate_prioritized()`'s per-attempt `fill_slots()` calls used
  to re-scan the entire course-wide lexeme pool from scratch on every
  single attempt** — fixed 2026-07-07 after a live-QA pass measured 77s
  on prs-en's largest course. `lexeme_matches()` is a pure function, so
  the per-slot candidate lists are identical across every attempt
  against the same template within one batch request; `fill_slots()`
  now accepts a precomputed `slot_candidates` dict and
  `_generate_prioritized()` memoizes it per-template
  (`slot_candidate_cache`) for the life of one request. Confirmed ~25x
  (prs-en) to ~60x (nl-en, the bigger course) faster on the same real
  content/account/history, no change to anti-repeat dedup or SRS
  scheduling. Any future change to the batch-generation hot path should
  keep reusing this cache rather than reintroducing a per-attempt
  lexeme-pool scan.

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

**`docs/PRE_DEPLOY_RUNBOOK.md` is the full checklist — read it before
the first real deploy of current work to 192.168.4.4.** It covers
pre-flight checks (including whether `alembic_version` even exists on
the live DB — never yet checked there, only on the dev DB), required
env vars (`ADMIN_EMAILS`, `CORS_ORIGINS`, `AZURE_SPEECH_KEY`/`_REGION`,
`GOOGLE_CLOUD_TTS_CREDENTIALS_JSON`), a backup step (none exists
elsewhere in this project's history), the full ordered deploy, and
post-deploy live-smoke-test verification. **As of 2026-07-07, the live
server has never actually been deployed to beyond its original setup**
— every BUILD_LOG.md mention of 192.168.4.4 is either config, a
read-only check, or an explicit "not touched" — so treat the next
deploy as a from-scratch-equivalent, not incremental, and don't skip
the runbook's pre-flight section.

Quick-reference skeleton only (see the runbook for the complete,
correctly-ordered version with pre/post steps):

```bash
rsync -az --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
  /Users/raminazizi/dev/LingoSquared/backend/ ramin@192.168.4.4:/home/ramin/LingoSquared/backend/
rsync -az /Users/raminazizi/dev/LingoSquared/docs/ ramin@192.168.4.4:/home/ramin/LingoSquared/docs/

ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose build api"
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose run --rm api alembic upgrade head"
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose run --rm api python -m app.content.seed"   # bootstrap only (languages/achievements/4 placeholder demo courses) — NOT the real ~131-unit content, see runbook
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose up -d api"   # must happen here, BEFORE the HTTP steps below — easy to forget, without it the live container keeps serving the OLD image
# real content import (compile_content.py --> POST /admin/content/import, admin-authenticated),
# THEN lexeme backfill, THEN practice-template admin import, in that exact order — see runbook
```

Test suite on the server (isolated DB, never `--env-file`):

```bash
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && \
  docker compose exec -T db dropdb -U lingosquared --if-exists lingosquared_test && \
  docker compose exec -T db createdb -U lingosquared lingosquared_test && \
  docker compose run --rm api sh -c 'DATABASE_URL=\$(python3 -c \"import os,re; print(re.sub(r\\\"lingosquared\$\\\", \\\"lingosquared_test\\\", os.environ[\\\"DATABASE_URL\\\"]))\") python -m pytest -q'"
```

Practice-feature deploys need the lexeme backfill THEN the
practice-template admin import, after migrations — **this order was
previously documented backwards here and has been corrected
(2026-07-06, live-QA pass on fa)**: `POST /admin/courses/{id}/practice/
import`'s lesson-key resolution (`_practice_lesson_id()` in
`backend/app/content/service.py`) primarily matches via `Lexeme.
provenance_lesson_content_key`, which only exists once the relevant
`backfill_lexemes*.py` script has run against that course — importing
practice templates first fails every single template with "lesson key
... was not found in the course" on a genuinely fresh stack (confirmed
live: content import → practice import → 100% failure; content import
→ backfill → practice import → succeeds). See `docs/BUILD_LOG.md`'s
matching entry for the reproduction, and `docs/PRE_DEPLOY_RUNBOOK.md`
for the full corrected step sequence.

## Secrets

TTS is Google Cloud (service-account JSON via
`GOOGLE_CLOUD_TTS_CREDENTIALS_JSON` env var, raw JSON content not a
file path) for 8 languages, proxied server-side only — never sent to
the frontend. **Added 2026-07-06: Azure Cognitive Services Speech as a
second provider, specifically for Farsi** — Google Cloud TTS has zero
Persian/Dari voices at all, but Azure has real licensed neural voices
for Farsi (`fa-IR-DilaraNeural` female, used by default;
`fa-IR-FaridNeural` male also available). Config: `AZURE_SPEECH_KEY` +
`AZURE_SPEECH_REGION` env vars, same unset-by-default/graceful-
degradation convention as the Google credential (empty → `/tts`'s
`provider_error` browser-fallback, never a crash) — **not yet set to a
real key, this is built and tested but not yet live**; get a key from
the Azure Portal (Cognitive Services → Speech resource) once ready to
activate it. Implemented via the plain Azure Speech REST API in
`backend/app/services/tts.py` (`synthesize_azure()`), not the Azure SDK
— no new dependency, reuses the `httpx` already in `requirements.txt`.
Dari (`prs`) still has zero coverage from either provider; browser
`speechSynthesis` remains its only fallback (see Known limitations).
Full detail (routing logic, why Azure over self-hosted Piper, what was
verified) in `docs/BUILD_LOG.md`. ElevenLabs is no longer the
live provider (superseded 2026-07-04) — historical account/voice
gotchas are in `docs/BUILD_LOG.md` if ElevenLabs is ever revisited.
**Investigated 2026-07-05 whether the public-domain FSI/Peace Corps
audio helps here: it doesn't, directly.** The Persian FSI tapes are 24
long, unsegmented per-unit recordings (~436 min total, one file per
half-tape's basic sentences + drills), not per-phrase clips — no
splicing into individual exercises without real manual editing. Only
real use: a pronunciation-calibration reference for a human doing an
actual fa/prs recording session, not a content or asset shortcut.
Don't re-investigate this without new information. **Confirmed
separately: Peace Corps' own Persian/Dari materials have no recordings
at all, PDF-only** — the other public-domain source is a dead end too
for this specific need, don't re-check it either.

## What's built and verified live

Auth; all 10 languages (fa/prs fully separate, correct RTL + script
metadata); courses → units → lessons → all 19 exercise types; SM-2
review (being replaced by lexeme-level SRS, Phase A); gamification
(XP/streak/achievements); reading/writing vs. speaking course sections
with server-enforced unlock; CEFR levels A1–C2; teaching phase before
exercises; in-app content-issue reporting + admin triage + coverage
dashboard; Endless Practice generative feed (now built for all 6 launch-gate
directions — en-fa, en-nl, en-prs, fa-en, nl-en, prs-en — lexeme pool +
reviewed sentence-frame templates, zero runtime LLM calls); on-screen
virtual keyboard for non-Latin scripts; self-reported level check with
recommended-unit badge (not a placement system — that was explicitly
rejected as premature); real mic-based speaking exercises
(`speak_response`/`speak_repeat`) with client-side WASM Whisper STT
(self-hosted-server fallback), graded through the same free-text path
as every other exercise type.

Seeded courses (counts verified against `docs/content/realizations/`/
`overlays/` at 2026-07-06 19:53 BST — content authoring is actively
ongoing in parallel sessions, re-check before quoting exactly): fa→en,
nl→en, and prs→en each have 26 units (24 A1 + 2 A2, tracking the
spine as of its last-but-one growth spurt); en→fa has 11 units (9 A1 +
2 A2); en→prs has 11 units (9 A1 + 2 A2); en→nl has 25 units (23 A1 +
2 A2); es/fr each have 3 units (A1 only, still in progress — "1 unit
each" was stale). ~131 units total across 8 of 18 paths.

## Known limitations / accepted scope

- **STT (speak_response/speak_repeat), added 2026-07-06**: client-side
  Whisper must run `dtype: "fp32"` (~150MB one-time browser-cached
  download) — every quantized dtype throws a real onnxruntime-web
  session-creation bug for this model at the currently pinned
  `@huggingface/transformers` version (full root cause in
  `docs/BUILD_LOG.md`; revisit if a future library/runtime version
  fixes it upstream). Whisper sometimes transcribes spoken number
  words as bare digits ("zeven" → "7") rather than the word form,
  which won't match a word-form `accepted_answers` — a real accuracy
  caveat for number-saying exercises specifically, same class as the
  already-accepted general STT-mishearing risk, not something to chase
  with per-language digit-to-word tables. fa/prs UI translations for
  the new voice-answer strings aren't done yet (English fallback via
  i18next, not broken, just untranslated).
- **The spine outcome count is a fast-moving target this session —
  don't trust any number here without re-grepping
  `docs/content/universal_spine.yaml` first.** It grew 19→24→26→28
  across 2026-07-05/06 (24 A1 + 4 A2 as of 2026-07-06 19:53 BST:
  `bureaucracy`, `opinions`, `banking`, and a second `health` outcome
  — added in a burst while this very file was being audited for
  staleness, which is the exact "grew again without the docs being
  updated" failure mode to watch for). Real coverage is well past "a
  handful" now (see "Seeded courses" above), but the English
  realization (used by all X→en directions) still only covers the
  first 26 outcomes — `banking`/second-`health` aren't realized in any
  language yet. 10 of 18 paths still have zero content and no path has
  gone past A2 — still a genuinely multi-month build to reach full
  A1→C2 breadth across all 18 paths.
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
- **Second pre-deploy/pre-beta-invite checklist item (found in the
  2026-07-05 follow-up security pass): the live server's `CORS_ORIGINS`
  is currently `localhost` ports only** — needs to list whatever real
  origin(s) beta users' browsers will actually load the frontend from,
  or their requests get rejected (fails safe, but breaks the app for
  them). A deployment/product decision (what the real origin will be),
  not something to guess and fix unilaterally. Full detail, plus a real
  resource-exhaustion bug found and fixed (an unbounded-size `response`
  field on every answer-submission endpoint), in `docs/BUILD_LOG.md`'s
  matching entry.
- **Fixed and DEPLOYED 2026-07-06**: the Starlette "BadHost" CVE
  (CVE-2026-48710) flagged 2026-07-05 as needing a dedicated
  FastAPI-version-bump-and-regression-test pass — done and live on the
  shared dev stack. `backend/requirements.txt`'s `fastapi` bumped
  `0.115.12` → `0.139.0`, resolving `starlette` to `1.3.1` (past the
  `1.0.1` fix). Changelog-audited the full version range for breaking
  changes against this codebase's actual FastAPI usage (none applied),
  full pytest suite green, live-smoke-tested auth/course-listing/
  lesson-content/answer-grading/error-handling. Committed, and
  deployed to the shared dev stack's `backend-api-1` via a coordinated
  rebuild (`docker compose build api && docker compose up -d api`)
  alongside two other landed features (Azure TTS, Whisper STT) —
  `pip show fastapi` on the actually-running container confirms
  `0.139.0` live, not just committed. Still **not** deployed to the
  live server (192.168.4.4) — that's a separate, Ramin-present step per
  the standing deploy convention. Full detail in `docs/BUILD_LOG.md`'s
  matching entries.
- No refresh tokens, password reset, or email verification.
- No mobile app (Expo React Native is the recommended future path,
  reusing the existing JWT/JSON API as-is).
- Rejected, don't re-propose without a strong new reason: hearts/lives,
  leagues/leaderboards, gems/currency, runtime-LLM content generation,
  a placement-quiz enrollment system (self-report + checkpoint test-out,
  Phase F, is the accepted alternative).
- **Fixed 2026-07-05 (Session 1/CODE)**: `POST /admin/content/import`
  used to only create brand-new courses — it skipped any course that
  already existed by `(source_language, target_language, title)`
  rather than appending new units to it, so every unit authored beyond
  a course's initial seed was stuck validated-on-disk but never live
  (found earlier the same day trying to get new fa units 3/4/5 live,
  then hit again by the practice-pool-sync lane trying to get nl
  units 5+ live). `import_content()` now diffs incoming units against
  the existing course's unit `order`s (unique per course, the natural
  dedup key already in the schema) and appends only the ones that
  aren't already present — every already-imported unit/lesson/exercise
  and any real user progress on them is left untouched. See
  `docs/BUILD_LOG.md` for the fix and its test.
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
