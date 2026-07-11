# Lingo² — project state (read this first)

Local-first language-learning app, Duolingo/Babbel-caliber, 18 directed
en↔X learning paths (nl, fr, de, it, es, ru, zh, fa, prs). **Lanes:**
backend code + alembic migrations + `scripts/compile_content.py` are
**Codex**'s lane (dispatched and verified by Claude); frontend,
orchestration, verification, and CONTRACT.md are the executing
**Claude** session's; language content is authored by **both** (Codex
from-scratch, Claude adapting public-domain source material). This file
is the current state, standing invariants, and cross-cutting footguns
only — full chronological history and every incident narrative behind the
rules below is in `docs/BUILD_LOG.md`.

## QUICK MAP — where to find what (read this when…)

**This root file** carries project identity, current state, cross-lane
policies, cross-cutting footguns, and the verification bar. **Area-specific
rules live in per-directory `CLAUDE.md` files that Claude Code loads only
when you work under that directory:**

- **`docs/content/CLAUDE.md`** — ALL content-authoring/review rules
  (sourcing policy, dispatch requirements, content footguns, seeded-course
  state, known content limitations). Read before authoring/reviewing
  content; `docs/content/AUTHORING_GUIDE.md` stays binding.
- **`backend/CLAUDE.md`** — migrations, docker/env footguns, isolated-DB
  recipe, backfill/`test_content_answer_shapes` mounting, secrets/TTS
  state, deploy runbook + live-server (192.168.4.4) rules. Read before
  running/testing/deploying backend or touching migrations.
- **`frontend/CLAUDE.md`** — build rule, answer-payload-shape contract,
  exercise-type registration check, RTL `dir` rule, `speak()`/STT notes,
  `localStorage` preference patterns, `VITE_FEEDBACK_API_URL` gap. Read
  before changing any `frontend/src/**` UI.

Other maps within this file: **CURRENT STATE** (plan of record, what's
shipped, scope/publish-gate) · **POLICIES** (division of labor & Codex
dispatch; tiered review) · **FOOTGUNS (cross-cutting)** (git/worktree/
agent/credential/safety/browser/DB-isolation — read before multi-agent
dispatch, worktree cleanup, staging, credential handling, concurrent
tests) · **OPERATIONS** (verification tooling + the non-negotiable
VERIFICATION BAR).

**Binding external docs:** `docs/SONNET_BUILD_PROMPT_UPGRADES.md` (active work order, phases A–G) · `docs/content/AUTHORING_GUIDE.md` (all content authoring) · `docs/CONTRACT.md` (API/schema contract) · `docs/APP_SPEC_FOR_FABLE_REVIEW.md` (architecture "why") · `docs/PRE_DEPLOY_RUNBOOK.md` (deploy) · `docs/CONTENT_DEFECT_REGISTRY.md` (per-lane review-yield ledger) · `docs/BUILD_LOG.md` (full history).

## How this documentation set works

- **Four-file layout + loading mechanic.** This root `CLAUDE.md` ALWAYS
  loads. The three area files — `docs/content/CLAUDE.md`, `backend/CLAUDE.md`,
  `frontend/CLAUDE.md` — auto-load ONLY when an agent works with files
  under that directory. That's deliberate token economy: a frontend
  worker never pays for backend/content rules, and vice-versa. **Do NOT
  merge them back into root.**
- **Maintenance rule — CLAUDE.md files hold RULES, not stories.** A new
  cross-cutting rule (applies to every worker regardless of area) goes in
  root; an area-specific rule goes in that area's file; incident
  narratives go in `docs/BUILD_LOG.md`; per-bug-class defect records go in
  `docs/CONTENT_DEFECT_REGISTRY.md`.
- **Dispatching workers:** still inline the 3–5 task-critical rules
  directly in the dispatch prompt — don't rely on auto-loaded context to
  carry the rules that matter most for that specific task.
- **Keep root lean:** if it grows past ~400 lines, something is in the
  wrong file.

---

# CURRENT STATE

## Plan of record

`docs/SONNET_BUILD_PROMPT_UPGRADES.md` is the active work order (phases
A–G: lexeme-level SRS, in-lesson error recycling, feedback quality,
recorded fa/prs audio, retention loop, unit checkpoints, integrity
fixes) — **read it before starting any new work.** It also defines the
up-to-three-parallel-session ownership map (CODE / CONTENT / INFRA).
`docs/APP_SPEC_FOR_FABLE_REVIEW.md` is the architecture snapshot behind
the upgrade program (the "why" of Phase A's SRS redesign).

## What's shipped (all live-verified; full detail per phase in BUILD_LOG)

Phases A–F all shipped and live-verified. One line each; the *Invariants*
are standing rules, not history:

- **Phase A (lexeme-level SRS)** — SRS schedules lexemes not exercise
  instances; `user_lexeme_srs`, `GET /me/reviews/due`,
  `POST /reviews/session`, `POST /reviews/items/{id}/retry`; adaptive
  recognition→structured→production ladder by mastery. *Invariant:* every
  migration after 0001 must be fresh-migrate-safe (see backend/CLAUDE.md).
- **Phase B (in-lesson error recycling)** — `LessonRunnerPage` recycles
  misses to queue end; 2 misses → non-blocking "copy it" pass; ≤2 due
  reviews prepend when `courseId` is known (via route `state`). Frontend-only.
- **Phase E1 (HomePage review CTA)** — primary CTA "Review — N due" when
  due; `ReviewPage.tsx` moved off dead `/me/reviews` onto `/reviews/session`.
- **Phase C (typo tolerance + feedback_by_option)** —
  `result: correct|almost|incorrect`, Damerau-Levenshtein distance-1,
  per-language strictness via `Language.script`, `orthography_strict`
  override, Arabic/Persian script-confusion never forgiven;
  `feedback_by_option` JSON-encoded into `Exercise.feedback`.
- **Phase C follow-up (`case_sensitive` flag)** — default `False` sibling
  of `orthography_strict`; a case-only mismatch is hard-blocked to
  `incorrect`, never the "almost" path (else it counts correct for
  XP/SRS). Exercise-level only, not yet in Endless Practice.
- **Phase E2 (timezone-aware streaks)** — `User.timezone` (migration
  0009); `record_activity()`/`activity_day_bounds()` take a
  `user_timezone` param (UTC fallback). *Invariant:* grading success is
  `quality >= 3`, never a truthiness check on `correct` (now can be the
  string `"incorrect"`).
- **Phase E3 (streak freeze + daily quests)** — one earned/auto-consumed
  freeze (migration 0010); `GET /me/quests` = 3 live-computed quests,
  `QuestCompletion` (migration 0011) pays XP once per user/quest/day.
- **Phase D (recorded audio)** — `POST /admin/media/upload` +
  `GET /media/{key}` serving `backend/media_assets/{key}.mp3` (404 for
  unrecorded keys is expected); compiler rejects NEW embedded-"Name:"
  dialogue cards (`TextBlock.speaker` for splits); `speak()`/`SpeakButton`
  chain (see frontend/CLAUDE.md). *Not done:* re-authoring existing
  dialogue cards (CONTENT lane).
- **Phase F (unit checkpoint / test-out)** — `POST /units/{id}/checkpoint`
  = 12–15 items (not gated on completion), `orthography_strict` forced
  `True`, never touch per-item SRS; `.../checkpoint/result` scores once
  (≥80% passes), consolidates SRS only for untracked lexemes (0.5, +3d),
  idempotent, 1-hr retake delay (advisory lock + `429`);
  `GET /courses/{id}/units` returns `checkpoint_passed`. Migration 0012.
- **E4 (web push)** — 2026-07-07 (`784da03`, migration 0016): VAPID
  subscribe/unsubscribe + admin-triggerable notify-due-reviews. No cron.
- **Mic-based speaking + STT** — `speak_response`/`speak_repeat` capture +
  STT via the free-text path; client-side WASM Whisper primary (zero audio
  leaves device), self-hosted `faster-whisper` (`POST /stt/transcribe`)
  fallback, never a cloud STT API. *Invariant:* Whisper runs
  `dtype: "fp32"` (see frontend/CLAUDE.md).
- **Per-language TTS speech-speed** — `/tts` optional `speaking_rate`
  (1.0, 0.25–2.0); per-device per-language `localStorage` pref (see
  frontend/CLAUDE.md). *Open:* a live-tab slider click-through was never
  done — visual close-out next live browser session.

*Still remaining from the upgrade program:* D2's dialogue-content
re-authoring and C1's feedback_by_option content pass (both CONTENT
lane). The mechanism is fully built across every phase; the real
remaining path to launch is full-depth content for en-nl/en-fa/en-prs.

## Scope & publish-gate decisions (2026-07-05)

- **End goal is genuine fluency (full CEFR A1→C2), but publish is a much
  earlier, separate gate.** Publish-gate language set: **en↔nl and
  en↔fa/prs only** (6 directed paths) — the languages Ramin can
  personally verify. The other 15 paths keep building as post-launch
  drip content, not blocked.
- **Publish-gate quality bar: "very usable, minimum bugs," not a phase
  checklist.** Beta users on the 3 launch pairs must hit essentially no
  functional breakage. The Claude session earns this via the full
  VERIFICATION BAR (below) on the actual lesson/review/practice flows
  BEFORE any user sees it — the report-button → triage loop is the next
  layer, not a substitute for pre-launch verification.
- **Publish-gate content depth: ≥10 hrs new teaching + ≥10 hrs practice
  + working scored module checkpoints, per launch pair.** Practice hours
  come from the Endless Practice engine (built for all 6 launch
  directions — en-fa 124, en-nl 240, en-prs 36, fa-en 86, nl-en 327,
  prs-en 86 templates per `scripts/practice_manifest.txt`); actual
  hour-depth vs the bar hasn't been separately measured. Phase F unit
  checkpoints are a hard publish-gate requirement. Detail:
  APP_SPEC_FOR_FABLE_REVIEW.md §1 + `project-lingosquared-roadmap` memory.

## Reference-language priorities

- **Reference language: Dutch (nl).** Ramin is fluent in Dutch, so nl is
  built to full polish first (native review) and is the primary UX
  verification target.
- **fa/prs remain the mandatory RTL / virtual-keyboard /
  script-strict-grading verification target for every phase regardless
  — don't let them rot.**
- **es/fr:** finish in-flight units, then park until nl is done.
- **`docs/content/AUTHORING_GUIDE.md` is binding for all content
  authoring.** **`docs/CONTRACT.md` is the API/schema contract both
  sides build against — update it before implementing any contract
  change, never after.**

## What's built and verified live

Auth; all 10 languages (fa/prs fully separate, correct RTL + script
metadata); courses → units → lessons → all 19 exercise types; SM-2 review
(being replaced by lexeme-level SRS); gamification (XP/streak/achievements);
reading/writing vs. speaking sections with server-enforced unlock; CEFR
A1–C2; teaching phase before exercises; in-app content-issue reporting +
admin triage + coverage dashboard; Endless Practice generative feed (all 6
launch directions, zero runtime LLM calls); on-screen virtual keyboard for
non-Latin scripts; self-reported level check with recommended-unit badge
(not a placement system — rejected); mic-based speaking with client-side
WASM Whisper STT.

(Area-specific known limitations live in each area's CLAUDE.md:
seeded-course counts + content limits → content; deploy/backend →
backend; STT/frontend → frontend.)

### Cross-cutting known limitations & rejected scope

- No password reset or email verification. **Refresh tokens ARE built**
  (2026-07-10, `565f66c`, migration 0021): 30-min access + rotating
  refresh tokens with reuse-detection revocation, `POST /auth/refresh`/`logout`.
- No functional mobile app yet; an Expo scaffold exists (`mobile/`,
  2026-07-10, Phase 0 proof-of-concept only — proves Metro resolves
  `@lingo/shared` through the monorepo). Reuses the existing JWT/JSON API.
- **Rejected, don't re-propose without a strong new reason:** hearts/lives,
  leagues/leaderboards, gems/currency, runtime-LLM content generation, a
  placement-quiz enrollment system (self-report + checkpoint test-out is
  the accepted alternative).

---

# POLICIES

## Division of labor & delegating to Codex

- **Codex owns `backend/app/**`, alembic migrations, and
  `scripts/compile_content.py`. Claude owns `frontend/src/**`,
  CONTRACT.md, orchestration (extract → validate → apply Codex's
  output), and ALL verification.** **Never trust Codex's self-report;
  diff full-file rewrites against the prior version before applying** (a
  rewrite once silently introduced an unrelated one-line query bug
  alongside a correct fix).
- **Content authorship is now both Codex (from-scratch generation) and
  Claude (adapting public-domain source material into spine-compliant
  drafts — see AUTHORING_GUIDE §10).** Both routes go through the
  identical fresh-context review + compiler pipeline — **content Claude
  authors gets zero quality-bar exception** for being the same session
  that builds the frontend. (Content-authoring dispatch requirements —
  pacing rule, sibling isolation, review routing — are in `docs/content/CLAUDE.md`.)
- **Always pass `--cwd` explicitly** — Codex's sandbox defaults to the
  Claude session's cwd (often a different project):

```bash
node "/Users/raminazizi/.claude/plugins/cache/openai-codex/codex/1.0.5/scripts/codex-companion.mjs" task \
  --cwd /Users/raminazizi/dev/LingoSquared --background --write --resume "…prompt…"
```

  Status/result: `status <job-id> --cwd ... --json` / `result <job-id>
  --cwd ...`. If the plugin path/version changed, look under
  `~/.claude/plugins/cache/openai-codex/`. Codex has no Docker/network —
  real build/test/deploy verification is always Claude's job. **If Codex
  auth fails with a revoked refresh token, stop and tell Ramin to run
  `codex login` rather than retrying.**
- **Codex's `--resume` continues whatever thread was last active
  (including a stale "still running" one that blocks it); use `--fresh`
  when a prior dispatch might still be mid-flight** and this one must not
  collide. Detail: BUILD_LOG.

## Tiered review policy (Ramin's call, 2026-07-11)

Review effort must shrink as a lane proves itself; blanket 100% review is
not the standing default anymore:

1. **Automate first.** Any rule-shaped mistake found in review becomes an
   automated validator (compiler check or a
   `test_content_answer_shapes.py`-style corpus test), not just a
   guide/CLAUDE.md note. Known validator backlog: the listen_select
   same-speaker-distractor rule and the title/gloss boolean-coercion gap
   (both Codex lane).
2. **Sample mature lanes.** A lane = same content type + same recipe +
   same authoring model. After ~3 consecutive zero-defect fresh-context
   reviews in a lane, drop to reviewing 1 in 3 deliverables (chosen by
   the reviewer, not the author). If ANY review then finds a genuinely
   new bug class: add the validator/rule AND reset that lane to full review.
3. **Full review always stays for:** new bug-class territory (a new
   exercise type, a new language, the first batches of any new recipe),
   anything that changes grading behavior, and ALL launch-gate content
   (en-nl/en-fa/en-prs) until launch.

Rationale: rules prevent known classes, review exists to discover unknown
ones (the day this was adopted, mature pack-authoring reviews were at 0
defects while nl-en overlay reviews surfaced a brand-new systemic bug
class). **Track review yield per lane in the review reports so tier
decisions are data, not vibes.** **`docs/CONTENT_DEFECT_REGISTRY.md` is
the per-lane yield ledger — consult it before any tier decision, and
append every future fresh-context review's findings (zero-defect included)
to its Section 4 log.**

---

# FOOTGUNS (cross-cutting — apply to every worker regardless of area)

Each entry: the rule, brief why, BUILD_LOG pointer. **Area-specific
footguns live in the per-directory CLAUDE.md files** (content; migrations/
docker/DB/secrets → backend; grading-shape/RTL/build → frontend).

### Git / staging / worktrees / agents

- **Never `git add -A` or `git add .` when other sessions may have files
  open — always stage explicit pathspecs for exactly the files you
  touched**, and verify with `git show --stat` on anything touching files
  you didn't personally edit. Broad staging twice swept a concurrent
  session's uncommitted feature into an unrelated commit; also confirmed
  for concurrent unisolated agents on shared files (`content_manifest.txt`,
  `universal_spine.yaml` — stagger them or use worktrees). Detail: BUILD_LOG 2026-07-06/07/08.
- **A safety-system block is a signal to stop and escalate, never an
  obstacle to route around** — tell Ramin plainly what you were trying to
  do and why; don't find a different angle, and **don't hand the blocked
  action to a differently-governed agent (e.g. Codex)** — that's the same
  "find another angle" pattern. Detail: BUILD_LOG 2026-07-06.
- **Direct DB credential writes (raw SQL on `password_hash`,
  self-registering under an admin email) are correctly blocked even with
  chat authorization.** Productive pattern: do the safe read-only half
  yourself (compute the hash via the app's `hash_password()` in a
  `docker compose run` one-off), then hand Ramin the ready-to-paste `psql
  UPDATE` to run himself. Detail: BUILD_LOG 2026-07-08.
- **A live credential (bearer token etc.) must never be written to a
  shared scratch location — even the scratchpad, even briefly, even for
  your own reuse.** Re-derive inline via command substitution in each
  command that needs it. Detail: BUILD_LOG 2026-07-08.
- **Parallel-worker forks that inherit full context can mistake
  themselves for the coordinator** (5+ incidents, some resisting
  correction). Explicit "you are a worker" prompts do NOT reliably fix
  it. **The fix that worked: use fresh (non-fork) general-purpose agents
  for narrow scoped tasks** — zero inherited history makes the failure
  class structurally impossible. Reserve `subagent_type: fork` for tasks
  that genuinely need this conversation's context. Detail: BUILD_LOG 2026-07-08.
- **`isolation: "worktree"` is not always honored — verify with `git
  worktree list` after every dispatch batch**, don't assume. Two of ten
  forks once got no worktree and operated unsandboxed against the shared
  dir. Detail: BUILD_LOG 2026-07-08.
- **Even a confirmed worktree is not a hard sandbox — it only changes the
  default cwd, it does not revoke filesystem access outside it.** A
  verified-isolated fork once committed directly to master via a raw file
  write targeting the real repo path. **The only real backstop is the
  coordinator diffing `git log` after every dispatch batch.** Detail: BUILD_LOG 2026-07-08.
- **Before removing ANY worktree, check `git log --oneline <branch> -1`
  against the branch's own STARTING base commit — "is an ancestor of
  master" is NOT "already merged"** (a branch that never committed is
  trivially an ancestor once master moves on). `git worktree remove
  --force` discards uncommitted work with no separate warning; at least 7
  stalled dispatches with real uncommitted work were destroyed this way
  (recovered only from raw subagent JSONL transcripts). When in doubt,
  `git worktree remove` without `--force` first — it refuses and names
  the uncommitted work. Detail: BUILD_LOG 2026-07-10.
- **After ANY batch of merge attempts, verify with `git merge-base
  --is-ancestor <branch> master` for every branch** — don't trust a
  remembered "that one succeeded," especially right after a permission
  interrupt or a conflict-driven retry loop (two branches were silently
  dropped that way, caught only by a user UI report). Detail: BUILD_LOG 2026-07-10.
- **Never use `git stash` during multi-session/multi-worktree work — the
  stash stack is one shared repo-wide resource** and a `pop` races like a
  broad `git add -A`, silently grabbing another worktree's WIP. Use a
  scratch commit (`git reset --soft HEAD^` later) or a diff file outside
  git. Detail: BUILD_LOG 2026-07-10.
- **A live, running `claude` process holding a worktree lock should not be
  killed directly** — `git worktree remove --force --force` cleanly
  detaches the worktree (stops it writing to the repo) without terminating
  the process, the less destructive and sufficient option. Detail: BUILD_LOG 2026-07-08.
- **Any worktree-isolated dispatch touching `frontend/`,
  `packages/shared/`, or `mobile/` must run `npm install` at the worktree
  root early** — an npm-workspace worktree with no `node_modules` silently
  resolves `@lingo/shared` UP to the main repo's copy, so builds/tests
  "verify" against stale code. Detail: BUILD_LOG 2026-07-10.
- **The claude-in-chrome / chrome-devtools MCP browser has ONE shared
  "selected page" across all sessions — no per-session isolation.** A
  concurrent session can steal your current page (or navigate Ramin's live
  tab). Open your OWN tab (`tabs_create_mcp`/`new_page`) and verify the
  URL before EVERY interaction; or use an isolated Playwright instance. Detail: BUILD_LOG 2026-07-10.

### DB isolation (concurrent workers)

- **Any dispatch telling a worker to run tests against Docker MUST name a
  uniquely-named test DB / compose project** (not just "the isolated-DB
  recipe") when many workers run concurrently — several workers once
  schema-dropped the SHARED dev DB, wiping all content and progress. Detail: BUILD_LOG 2026-07-10.
  (The isolated-DB test recipe itself is in `backend/CLAUDE.md`.)

---

# OPERATIONS

## Tooling (built by INFRA, 2026-07-05)

- **`scripts/verify.sh`** — one-command: content compiler validation
  (reads `content_manifest.txt`/`practice_manifest.txt` — **update those
  when you add a course/pack**) + backend pytest (isolated test DB) +
  full frontend build. Flags `--content-only`/`--backend-only`/
  `--frontend-only`/`--skip-*`; `--e2e`/`--e2e-only` adds Playwright
  (opt-in, needs a live seeded backend).
- **`e2e/`** — Playwright (auth, course picker, teaching-card flow,
  practice locked state, nav smoke). Runs its own dev server on port 5175.
  See `e2e/README.md` for coverage boundaries.

## Verification bar (NON-NEGOTIABLE)

- Compiler validation green (`.content-venv/` has PyYAML;
  `scripts/compile_content.py` — or `scripts/verify.sh`).
- Backend pytest green: real Postgres via docker compose, isolated test
  DB, **`python -m pytest`** (bare `pytest` doesn't put `/app` on
  `sys.path` in the container — imports fail).
- Frontend: the FULL `npm run build` (`tsc -b && vite build`), never just
  `tsc --noEmit` — the full build has twice caught type errors noEmit missed.
- **Live browser verification with a fresh test account for anything
  user-facing. Reading a diff is not verification** — this project's
  worst bugs (six unregistered exercise types, a permanently-disabled
  Respond button, distractors from the whole course vocabulary, a deleted
  logout button) were ALL found only by actually playing a lesson.
- Local stack only: `colima start`; `cd backend && docker compose up -d`
  (isolated `backend/.env`, random JWT secret, never committed). **Never
  touch the live server (192.168.4.4) unattended — deploys happen with
  Ramin present.**

---

# HISTORY

Full chronological build log, every bug found and fixed, the reasoning
behind every past decision, and the verbatim pre-2026-07-11 CLAUDE.md:
`docs/BUILD_LOG.md`. Per-lane review-yield ledger and per-direction tier
recommendations: `docs/CONTENT_DEFECT_REGISTRY.md`.
