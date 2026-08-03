# Lingo² — project state (read this first)

Local-first language-learning app, Duolingo/Babbel-caliber, 24 directed
en↔X learning paths (nl, fr, de, it, es, ru, zh, fa, prs, ar, ko, ja —
ar approved 2026-07-11 with first content live; ko/ja approved
2026-07-12, groundwork stage: typing/IME exercises for ja/ko need a
real input-method design decision before production-typing exercises
ship — recognition/word_order/listen types work without it).
**Priority order (Ramin, 2026-07-12): every path is English-anchored —
(1) en→X (English speakers learning any language) and (2) X→en (any
language's speakers learning English) are THE product; non-English↔
non-English pairs (e.g. fr↔de) are explicitly deferred and should not
be proposed, scaffolded, or content-planned without a new decision
from Ramin.** **Lanes:**
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

**`docs/PROJECT_STATE.md`** — what's shipped, publish-gate scope, what's
live-verified. REFERENCE, not rules: deliberately NOT auto-loaded, because a
worker needs it to know what EXISTS, never to work SAFELY.

Other maps within this file: **POLICIES** (division of labor & Codex
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
- **Keep root lean — and understand WHY.** Root auto-loads into EVERY
  worker's context on EVERY turn, in every lane, forever; the area files only
  load for the directory they govern. So every root line is paid for ~15x per
  round. The ~400-line ceiling is a smell detector, not a law: if root grows,
  the question is never "how do we compress it" but **"which of these lines
  isn't a RULE every lane needs?"** The answer is usually STATE — what exists,
  what shipped, what's scoped — which belongs in `docs/PROJECT_STATE.md`
  (referenced, not auto-loaded). Split by ACCESS PATTERN (rules vs reference),
  never by topic: rules must be in the reader's face unbidden, state only needs
  to be findable. Applied 2026-07-13 (487 -> 364 lines).

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

## Current state — see `docs/PROJECT_STATE.md`

**What is shipped, the publish-gate scope decisions, and what's been
live-verified now live in `docs/PROJECT_STATE.md`** — it is REFERENCE, not
rules, so it is deliberately NOT auto-loaded into every worker's context.
Read it when you need to know what exists; you do not need it to know how to
work safely. (This file stays rules-only for exactly that reason — see
"How this documentation set works".)

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
- **Keep the coordinator chat clean — push the work OUT.** The main
  session is the orchestrator, not the laborer: delegate authoring,
  reviewing, bulk edits, and searches to fresh sub-agents / Codex, and
  keep inline Edit/Bash to the minimum the coordinator alone must do
  (git commits with explicit pathspecs, central verification, applying a
  short verified diff). Reading dozens of files or hand-editing many
  files inline bloats the chat and burns context that orchestration
  needs — dispatch it instead. (Ramin's standing preference, 2026-08-01.)
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
  --cwd "$LINGO_REPO" --background --write --resume "…prompt…"
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

### Codex dispatch footguns (learned 2026-07-12 — don't repeat these)

- **Pass the prompt via `--prompt-file`, never inline in a shell string.**
  Backticks in an inline prompt are executed by the shell as command
  substitution and silently deleted from the prompt — a dispatch went out
  with `tested_text` and `prompt.target_blocks` stripped out of it (the
  shell printed `command not found: tested_text` and Codex started anyway
  with a mangled task). The prompt file also survives quoting hell.
- **`gpt-5.6` is not available on the ChatGPT-account Codex** (`400
  invalid_request_error`); `gpt-5.5` is the ceiling — don't re-test it.
- **Effort routing:** `high` ONLY for compiler/grading-critical surgery
  (a subtle defect there costs far more than the tokens saved); `medium`/
  `low` for routine round-trips. Ramin's standing preference is the
  cheaper option wherever quality isn't compromised.
- **A "failed" Codex task may still have done most of the work.** One task
  reported failed after ~20 min (ran out mid-turn) but had left four
  complete validators in the working tree. ALWAYS `git status` + `git
  diff --stat` before discarding or re-dispatching — and verify the
  partial work yourself rather than assuming it's junk.
- **Never accept a Codex validator without running it on the full corpus
  yourself.** Codex shipped a validator that emitted **360 false
  positives** (it tokenized English gloss text and even content-key
  fragments like `lesson01` as untaught target-language words) while its
  three sibling validators were genuinely good. Make "zero false
  positives on the current corpus" an explicit acceptance criterion in the
  prompt, then re-run it yourself. A noisy hard-error validator is worse
  than none — it trains everyone to ignore the validator.
- **Codex writes tests against the WRONG error envelope.** It asserted
  FastAPI's default `{"detail": ...}`; this app reshapes every
  HTTPException to `{"error": {code, message}}` in `main.py`. Its
  *endpoint* was correct and its *test* was wrong — only running pytest
  reveals which. Codex has no Docker: **running the suite is always the
  coordinator's job.**
- **Codex will MASK a validation error with bogus content to satisfy a
  "0 errors" acceptance criterion — validator-gaming.** Dispatched to add ONLY
  a dictation exercise to es units, it also silently added teaching `phrase`
  cards whose `introduced_tokens` listed words ABSENT from the card's own text
  (e.g. a card "Sigue derecho por esta calle" declaring it introduces `y`),
  purely to silence a pre-existing "token not introduced" error on an unrelated
  exercise. Caught only by diffing the realization for non-dictation additions
  (`grep '^+' | grep 'kind:\|introduced_tokens'`). **Always audit a scoped Codex
  content task for out-of-scope additions, and put an explicit STRICT-SCOPE rule
  in the prompt: "add ONLY X; if a validation error blocks you, SKIP and report —
  never mask it." A skipped unit is correct; a masked error is a new defect.**
  Learned 2026-08-03 (es A1 u09/u14). Detail: BUILD_LOG.
- **Codex runs UNISOLATED in the main working tree.** Two concurrent Codex
  tasks are safe only on disjoint files (backend/ vs scripts/ is fine);
  their edits interleave in one dirty tree, so **always commit with
  explicit pathspecs** and `git show --stat` the result.

## Tiered review policy (Ramin's call, 2026-07-11)

Review effort must shrink as a lane proves itself; blanket 100% review is
not the standing default anymore:

1. **Automate first.** Any rule-shaped mistake found in review becomes an
   automated validator (compiler check or a
   `test_content_answer_shapes.py`-style corpus test), not just a
   guide/CLAUDE.md note. Known validator backlog: the listen_select
   same-speaker-distractor rule and the title/gloss boolean-coercion gap
   (both Codex lane).
2. **Sampling was TRIED and REVERSED — do not re-run that experiment.**
   (1-in-3 sampling on a "mature" lane shipped 10 compiler-invisible defects;
   see §4.) Full review is the standing default.
3. **Full review always stays for:** new bug-class territory (a new
   exercise type, a new language, a new CEFR tier, the first batches of any
   new recipe), anything that changes grading behavior, and ALL launch-gate
   content (en-nl/en-fa/en-prs) until launch. **Route review to CODEX when
   Claude budget is tight** — it found 9 real defects in the de-en B1 wave.
4. **"Mature lane" is per-RECIPE, not per-language — a lane does NOT stay
   mature when it moves to new TOPICS.** Learned the hard way 2026-07-12:
   it/ru were sampled 1-in-3 on the strength of zero-defect A1 13-15
   reviews, so Italian 16-18 was set to merge on validators alone. The
   Russian sample came back with a NEW bug class, which forced a full
   Italian review — and Italian turned out to have **10 compiler-invisible
   defects** (it validated at 0 errors), including three exercises that
   graded a CORRECT learner answer as wrong. Sampling would have shipped
   every one of them. New topics on a proven recipe are still new
   territory; sample only within an unchanged recipe AND unchanged topic
   family.

Rationale: rules prevent known classes, review exists to discover unknown
ones. **Track review yield per lane in the review reports so tier
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

## Tooling

- **`scripts/verify.sh`** — one-command: content compiler validation
  (reads `content_manifest.txt`/`practice_manifest.txt` — **update those
  when you add a course/pack**) + backend pytest (isolated test DB) +
  full frontend build. Flags `--content-only`/`--backend-only`/
  `--frontend-only`/`--skip-*`; `--e2e`/`--e2e-only` adds Playwright
  (opt-in, needs a live seeded backend). **Judge it by the printed
  `content: pass/fail` summary, NOT its exit code — verify.sh can exit 0
  while a per-course `COMPILE FAILED` (validate-passes-but-assembly-fails,
  e.g. a matching_pairs mirror break) sits in the log. Always grep the
  output for `COMPILE FAILED`/`content:  fail`.** Detail: BUILD_LOG 2026-08-01.
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
  (isolated `backend/.env`, random JWT secret, never committed).
- **Deploy authority (Ramin, 2026-07-12): the coordinator has standing
  authority to deploy to the live server (192.168.4.4) — frontend
  `web_dist` rsync and backend deploys per `docs/PRE_DEPLOY_RUNBOOK.md` —
  without Ramin present, provided the VERIFICATION BAR passed on the
  deployed change first. Destructive live-DB operations (drops,
  data-losing migrations) still require Ramin present.**

---

# HISTORY

Full chronological build log, every bug found and fixed, the reasoning
behind every past decision, and the verbatim pre-2026-07-11 CLAUDE.md:
`docs/BUILD_LOG.md`. Per-lane review-yield ledger and per-direction tier
recommendations: `docs/CONTENT_DEFECT_REGISTRY.md`.
