# Lingo² — root rules (read this first)

Local-first language-learning app, Duolingo/Babbel-caliber, 24 directed en↔X learning paths
(nl, fr, de, it, es, ru, zh, fa, prs, ar, ko, ja — per-path approval status and the ja/ko IME
groundwork caveat are in `docs/PROJECT_STATE.md`). **Priority order (Ramin, 2026-07-12): every
path is English-anchored — en→X and X→en are THE product; non-English↔non-English pairs are
deferred — never propose, scaffold, or content-plan them without a new decision from Ramin.**
**Lanes:** backend code + alembic migrations + `scripts/compile_content.py` are **Codex**'s
(dispatched and verified by Claude); frontend, orchestration, verification, and CONTRACT.md are
**Claude**'s; language content is authored by both. This file is rules only — full history and
every incident narrative behind the rules below is in `docs/BUILD_LOG.md`.

## QUICK MAP — where to find what

Area rules live in per-directory `CLAUDE.md` files, auto-loaded only when you work under that directory:

- **`docs/content/CLAUDE.md`** — ALL content-authoring/review rules; `docs/content/AUTHORING_GUIDE.md` stays binding.
- **`backend/CLAUDE.md`** — migrations, docker/env footguns, isolated-DB recipe, secrets/TTS,
  deploy runbook + live-server (192.168.4.4) rules.
- **`frontend/CLAUDE.md`** — build rule, answer-payload-shape contract, exercise-type
  registration check, RTL `dir` rule, `speak()`/STT, `localStorage` preference patterns.

**`docs/PROJECT_STATE.md`** — what's shipped/live-verified + publish-gate scope. REFERENCE, not
rules — deliberately NOT auto-loaded; read it to know what EXISTS, never to work SAFELY.

**Binding external docs:** `docs/SONNET_BUILD_PROMPT_UPGRADES.md` (active work order, phases
A–G — **read it before starting any new work**; also defines the CODE/CONTENT/INFRA
parallel-session ownership map) · `docs/content/AUTHORING_GUIDE.md` (all content authoring) ·
`docs/CONTRACT.md` (API/schema contract — update it BEFORE implementing any contract change,
never after) · `docs/APP_SPEC_FOR_FABLE_REVIEW.md` (architecture "why") ·
`docs/PRE_DEPLOY_RUNBOOK.md` (deploy) · `docs/CONTENT_DEFECT_REGISTRY.md` (review-yield
ledger) · `docs/BUILD_LOG.md` (full history).

## How this documentation set works

- **Four-file layout:** root ALWAYS loads; the three area files auto-load only for their
  directory (token economy). **Do NOT merge them back into root.**
- **CLAUDE.md files hold RULES, not stories.** Cross-cutting rule → root; area rule → its area
  file; incident narrative → `docs/BUILD_LOG.md`; per-bug-class defect record →
  `docs/CONTENT_DEFECT_REGISTRY.md`; STATE (what exists/shipped) → `docs/PROJECT_STATE.md`.
- **Dispatching workers:** inline the 3–5 task-critical rules directly in the dispatch prompt —
  never rely on auto-loaded context to carry them.
- **Root is 200 lines MAX (Ramin, 2026-08-03)** — a hard rule: if an addition would exceed it,
  something else must move out first. Split by ACCESS PATTERN (rules vs reference), never by
  topic — rules must be in the reader's face unbidden; state only needs to be findable.

## Reference-language priorities

- **Reference language: Dutch (nl)** — full polish first (Ramin is fluent → native review); primary UX verification target.
- **fa/prs stay the mandatory RTL / virtual-keyboard / script-strict-grading verification target for every phase — don't let them rot.**
- **es/fr:** finish in-flight units, then park until nl is done.

# POLICIES

## Division of labor & delegating to Codex

- **Codex owns `backend/app/**`, alembic migrations, and `scripts/compile_content.py`. Claude
  owns `frontend/src/**`, CONTRACT.md, orchestration (extract → validate → apply), and ALL
  verification. Never trust Codex's self-report; diff full-file rewrites against the prior
  version before applying** (a rewrite once smuggled in an unrelated one-line query bug).
- **The coordinator does NO inline coding (Ramin, 2026-08-03).** ALL code/content edits go to
  sub-agents/Codex — coordinator scope is dispatch, diff-review, verification, and git commits
  (explicit pathspecs). The old "apply a short verified diff" carve-out is retired; a
  PreToolUse hook enforces this. Reading dozens of files or hand-editing inline burns context
  that orchestration needs — dispatch it instead.
- **Content authorship: Codex (from-scratch) AND Claude (adapting public-domain material,
  AUTHORING_GUIDE §10). Both routes go through the identical fresh-context review + compiler
  pipeline — Claude-authored content gets zero quality-bar exception.** (Dispatch
  requirements: `docs/content/CLAUDE.md`.)
- **Codex CLI:** `node "/Users/raminazizi/.claude/plugins/cache/openai-codex/codex/1.0.5/scripts/codex-companion.mjs" task --cwd "$LINGO_REPO" --background --write --resume --prompt-file <file>`;
  then `status <job-id> --cwd ... --json` / `result <job-id> --cwd ...` (path moved? look under
  `~/.claude/plugins/cache/openai-codex/`). **Always pass `--cwd` explicitly** — the sandbox
  defaults to the Claude session's cwd. Codex has no Docker/network — real build/test/deploy
  verification is always Claude's job. **Auth failing with a revoked refresh token → stop and
  tell Ramin to run `codex login`; don't retry.** **`--resume` continues whatever thread was
  last active (a stale "still running" one blocks it) — use `--fresh` when a prior dispatch may
  still be mid-flight.** Detail: BUILD_LOG.

### Codex dispatch footguns (don't repeat these)

- **Prompt via `--prompt-file`, never inline in a shell string** — the shell executes backticks
  as command substitution and silently strips them from the prompt. Detail: BUILD_LOG 2026-08-03 relocated-detail §.
- **`gpt-5.6` is unavailable on ChatGPT-account Codex; `gpt-5.5` is the ceiling — don't
  re-test.** Effort: `high` ONLY for compiler/grading-critical surgery; `medium`/`low` for
  routine rounds (Ramin's standing preference: the cheaper option wherever quality holds).
- **A "failed" Codex task may have done most of the work** — always `git status` + `git diff
  --stat`, and verify the partial work yourself, before discarding or re-dispatching. Detail: BUILD_LOG relocated §.
- **Never accept a Codex validator without running it on the full corpus yourself** (one
  shipped 360 false positives). Make "zero false positives on the current corpus" an explicit
  acceptance criterion — a noisy hard-error validator is worse than none. Detail: BUILD_LOG relocated §.
- **Codex writes tests against the WRONG error envelope** (FastAPI's `{"detail"}` vs this app's
  `{"error": {code, message}}`) — only running pytest reveals which; that's always the
  coordinator's job. Detail: BUILD_LOG relocated §.
- **Codex will MASK a validation error with bogus content to satisfy a "0 errors" criterion
  (validator-gaming).** Put an explicit STRICT-SCOPE rule in every scoped content prompt —
  "add ONLY X; if a validation error blocks you, SKIP and report — never mask it" — and audit
  the diff for out-of-scope additions. A skipped unit is correct; a masked error is a new
  defect. Learned 2026-08-03 (es A1). Detail: BUILD_LOG relocated §.
- **Codex runs UNISOLATED in the main working tree** — concurrent tasks only on disjoint
  files; always commit with explicit pathspecs and `git show --stat` the result.

## Tiered review policy (Ramin's call, 2026-07-11)

1. **Automate first** — any rule-shaped review finding becomes an automated validator
   (compiler check or corpus test), not just a note.
2. **Sampling was TRIED and REVERSED — do not re-run that experiment.** Full review is the
   standing default: 1-in-3 sampling on a "mature" lane shipped 10 compiler-invisible defects,
   three of which graded a CORRECT learner answer as wrong. Detail: BUILD_LOG relocated §.
3. **Full review always for:** new bug-class territory (new exercise type/language/CEFR
   tier/first batches of a new recipe), anything changing grading behavior, and ALL
   launch-gate content (en-nl/en-fa/en-prs) until launch. Route review to CODEX when Claude
   budget is tight (it found 9 real defects in de-en B1).
4. **"Mature lane" is per-RECIPE and per-TOPIC-family, never per-language** — new topics on a
   proven recipe are new territory; sample only within an unchanged recipe AND topic family.

Rules prevent known classes; review discovers unknown ones. **Track review yield per lane;
`docs/CONTENT_DEFECT_REGISTRY.md` is the ledger — consult it before any tier decision and
append every fresh-context review's findings (zero-defect included) to its Section 4 log.**

# FOOTGUNS (cross-cutting — every worker, every lane; area footguns live in the area CLAUDE.md files)

- **Never `git add -A` / `git add .` when other sessions may have files open — stage explicit
  pathspecs only**, and `git show --stat` anything touching files you didn't personally edit
  (broad staging twice swept a concurrent session's work into an unrelated commit; on shared
  files like `content_manifest.txt`/`universal_spine.yaml`, stagger agents or use worktrees). Detail: BUILD_LOG 2026-07-06/07/08.
- **A safety-system block means stop and escalate to Ramin — never route around it, and never
  hand the blocked action to a differently-governed agent (e.g. Codex).** Detail: BUILD_LOG 2026-07-06.
- **Direct DB credential writes are blocked even with chat authorization.** Pattern: do the
  safe read-only half yourself (compute the hash via the app's `hash_password()`), hand Ramin
  the ready-to-paste `psql UPDATE`. Detail: BUILD_LOG 2026-07-08.
- **A live credential must never be written to any shared scratch location — even the
  scratchpad, even briefly.** Re-derive inline via command substitution per command. Detail: BUILD_LOG 2026-07-08.
- **Full-context forks mistake themselves for the coordinator (5+ incidents); "you are a
  worker" prompts don't reliably fix it. Use fresh (non-fork) agents for narrow scoped
  tasks**; reserve `subagent_type: fork` for tasks needing this conversation's context. Detail: BUILD_LOG 2026-07-08.
- **`isolation: "worktree"` is not always honored — verify with `git worktree list` after
  every dispatch batch.** Detail: BUILD_LOG 2026-07-08.
- **A confirmed worktree is NOT a sandbox — it only changes default cwd** (a fork once
  committed to master via a raw write to the real repo path). The only real backstop: the
  coordinator diffing `git log` after every dispatch batch. Detail: BUILD_LOG 2026-07-08.
- **Before removing ANY worktree, check `git log --oneline <branch> -1` against the branch's
  own STARTING base commit — "is an ancestor of master" is NOT "already merged"** (a
  never-committed branch is trivially an ancestor). `git worktree remove --force` silently
  discards uncommitted work (≥7 dispatches destroyed); when in doubt remove WITHOUT `--force`
  first — it refuses and names the work. Detail: BUILD_LOG 2026-07-10.
- **After ANY batch of merge attempts, verify `git merge-base --is-ancestor <branch> master`
  for every branch** — never trust a remembered "succeeded", especially after a permission
  interrupt or retry loop. Detail: BUILD_LOG 2026-07-10.
- **Never `git stash` during multi-session/worktree work** — the stash stack is repo-global; a
  `pop` races and grabs another worktree's WIP. Use a scratch commit or a diff file outside
  git. Detail: BUILD_LOG 2026-07-10.
- **Don't kill a live `claude` process holding a worktree lock** — `git worktree remove
  --force --force` detaches the worktree without terminating the process. Detail: BUILD_LOG 2026-07-08.
- **Worktree dispatches touching `frontend/`, `packages/shared/`, or `mobile/` must run `npm
  install` at the worktree root early** — else `@lingo/shared` silently resolves UP to the
  main repo's stale copy, "verifying" against stale code. Detail: BUILD_LOG 2026-07-10.
- **The claude-in-chrome / chrome-devtools MCP browser has ONE shared "selected page" across
  ALL sessions.** Open your OWN tab (`tabs_create_mcp`/`new_page`) and verify the URL before
  EVERY interaction, or use an isolated Playwright instance. Detail: BUILD_LOG 2026-07-10.
- **DB isolation: any dispatch running tests against Docker MUST name a uniquely-named test
  DB / compose project** (not just "the isolated-DB recipe" — that recipe is in
  `backend/CLAUDE.md`) when workers run concurrently — workers once schema-dropped the SHARED
  dev DB, wiping all content and progress. Detail: BUILD_LOG 2026-07-10.

# OPERATIONS

- **`scripts/verify.sh`** — content compiler validation (reads
  `content_manifest.txt`/`practice_manifest.txt` — update them when you add a course/pack) +
  backend pytest (isolated DB) + full frontend build; flags `--content-only`/`--backend-only`/
  `--frontend-only`/`--skip-*`; `--e2e`/`--e2e-only` adds Playwright (needs a live seeded
  backend). **Judge it by the printed summary, NOT its exit code — it can exit 0 with a
  per-course `COMPILE FAILED` in the log; always grep for `COMPILE FAILED`/`content:  fail`.** Detail: BUILD_LOG 2026-08-01.
- **`e2e/`** — Playwright smoke suites; runs its own dev server on port 5175; coverage
  boundaries in `e2e/README.md`.

## Verification bar (NON-NEGOTIABLE)

- Compiler validation green (`.content-venv/` has PyYAML; `scripts/compile_content.py` — or
  `scripts/verify.sh`).
- Backend pytest green: real Postgres via docker compose, isolated test DB, **`python -m
  pytest`** (bare `pytest` doesn't put `/app` on `sys.path` in-container — imports fail).
- Frontend: the FULL `npm run build` (`tsc -b && vite build`), never just `tsc --noEmit` — the
  full build has twice caught type errors noEmit missed.
- **Live browser verification with a fresh test account for anything user-facing — reading a
  diff is not verification** (this project's worst bugs — six unregistered exercise types, a
  dead Respond button, a deleted logout button — were ALL found only by playing a lesson).
- Local stack only: `colima start`; `cd backend && docker compose up -d` (isolated
  `backend/.env`, random JWT secret, never committed).
- **Deploy authority (Ramin, 2026-07-12): the coordinator may deploy to the live server
  (192.168.4.4) — frontend `web_dist` rsync and backend deploys per
  `docs/PRE_DEPLOY_RUNBOOK.md` — without Ramin present, provided the verification bar passed
  on the deployed change first. Destructive live-DB operations (drops, data-losing
  migrations) still require Ramin present.**

# HISTORY

Full chronological log, every incident narrative, and the relocated detail behind this file's
compressed bullets: `docs/BUILD_LOG.md`. Review-yield ledger: `docs/CONTENT_DEFECT_REGISTRY.md`.
