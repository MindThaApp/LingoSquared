# Lingo² — project state (read this first)

Local-first language-learning app, Duolingo/Babbel-caliber, 18 directed
en↔X learning paths (nl, fr, de, it, es, ru, zh, fa, prs). **Lanes:**
backend code + alembic migrations + `scripts/compile_content.py` are
**Codex**'s lane (dispatched and verified by Claude); frontend,
orchestration, verification, and CONTRACT.md are the executing
**Claude** session's; language content is authored by **both** (Codex
from-scratch, Claude adapting public-domain source material). This file
is the current state, standing invariants, and footguns only — full
chronological history and every incident narrative behind the rules
below is in `docs/BUILD_LOG.md`.

## QUICK MAP — where to find what (read this when…)

- **CURRENT STATE** — plan of record, what's shipped (per-phase, compressed), scope/publish-gate decisions, seeded-course counts. Read when planning new work or checking if something already exists.
- **KNOWN LIMITATIONS / ACCEPTED SCOPE** — deliberate gaps, rejected ideas, pre-deploy checklist items. Read before "fixing" something that may be intentional or before proposing a rejected feature.
- **POLICIES → Division of labor & Codex dispatch** — who owns what, how to dispatch/verify Codex. Read before delegating.
- **POLICIES → Tiered review** — how much fresh-context review a lane needs. Read before deciding review effort or skipping review.
- **POLICIES → Content sourcing** — Firecrawl-first, public-domain vs CC licensing gates. Read before authoring content from external sources.
- **FOOTGUNS** — hard-won failure modes (git/worktree/agent, migrations, docker, grading-shape, RTL, credentials). Read before: multi-agent dispatch, worktree cleanup, a migration, staging commits, credential handling, any grading/answer-shape change.
- **OPERATIONS** — where things run, deploy runbook + skeleton, isolated-DB test recipe, TTS/secrets state, the non-negotiable VERIFICATION BAR. Read before running/testing/deploying.
- **Binding external docs:** `docs/SONNET_BUILD_PROMPT_UPGRADES.md` (active work order, phases A–G) · `docs/content/AUTHORING_GUIDE.md` (all content authoring) · `docs/CONTRACT.md` (API/schema contract) · `docs/APP_SPEC_FOR_FABLE_REVIEW.md` (architecture "why") · `docs/PRE_DEPLOY_RUNBOOK.md` (deploy) · `docs/CONTENT_DEFECT_REGISTRY.md` (per-lane review-yield ledger) · `docs/BUILD_LOG.md` (full history).

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

Phases A–F are all shipped and live-verified. Compressed:

- **Phase A (lexeme-level SRS)** — SRS schedules lexemes (not exercise
  instances), generating a fresh reviewed exercise each time one comes
  due. New: `user_lexeme_srs` table, `GET /me/reviews/due`,
  `POST /reviews/session`, `POST /reviews/items/{id}/retry`; adaptive
  recognition→structured→production ladder by per-lexeme mastery.
  *Invariant:* every migration after 0001 must be fresh-migrate-safe
  (see Footguns). Detail: BUILD_LOG Phase A.
- **Phase B (in-lesson error recycling)** — `LessonRunnerPage` recycles
  missed exercises to queue end; 2 misses trigger a "copy it"
  confirmation pass that never hard-blocks; up to 2 due reviews prepend
  before teaching cards when `courseId` is known (threaded via route
  `state`), skip silently otherwise. Frontend-only. Detail: BUILD_LOG Phase B.
- **Phase E1 (HomePage review CTA)** — primary CTA becomes "Review — N
  due" when due. Also rewrote `ReviewPage.tsx` off the dead legacy
  `/me/reviews` onto `/reviews/session` per-course. Detail: BUILD_LOG.
- **Phase C (typo tolerance + feedback_by_option)** —
  `result: correct|almost|incorrect` on every answer endpoint,
  Damerau-Levenshtein distance-1, per-language strictness via
  `Language.script`, `orthography_strict` compiler override,
  Arabic/Persian script-confusion pairs never forgiven;
  `feedback_by_option` JSON-encoded into `Exercise.feedback`. Detail: BUILD_LOG Phase C.
- **Phase C follow-up (`case_sensitive` flag)** — new `case_sensitive:
  bool` (default `False`) sibling of `orthography_strict`; a case-only
  mismatch (e.g. "sie" vs "Sie") is hard-blocked to `incorrect`, never
  the distance-1 "almost" path (else it'd count correct for XP/SRS).
  Exercise-level only, not yet in Endless Practice. Detail: BUILD_LOG 2026-07-07.
- **Phase E2 (timezone-aware streaks)** — additive `User.timezone`
  (migration 0009); `record_activity()`/`activity_day_bounds()` take a
  `user_timezone` param (UTC fallback). *Invariant:* grading success is
  `quality >= 3`, never a truthiness check on `correct` (which can now
  be the string `"incorrect"`). Detail: BUILD_LOG Phase E2.
- **Phase E3 (streak freeze + daily quests)** — one earned/auto-consumed
  streak freeze (migration 0010); `GET /me/quests` = 3 quests computed
  LIVE each request, `QuestCompletion` row (migration 0011) pays XP once
  per user/quest/day. Detail: BUILD_LOG Phase E3.
- **Phase D (recorded audio)** — `POST /admin/media/upload` +
  `GET /media/{key}` serving flat `backend/media_assets/{key}.mp3` (real
  404 for not-yet-recorded keys is expected); compiler rejects NEW
  dialogue cards using the embedded-"Name:"-label anti-pattern
  (`TextBlock.speaker` field for split cards); `speak()`/`SpeakButton`
  priority chain recorded asset → Google TTS → browser speechSynthesis →
  honest fallback. *Not done:* re-authoring existing dialogue cards
  (CONTENT lane). Detail: BUILD_LOG Phase D.
- **Phase F (unit checkpoint / test-out)** — `POST /units/{id}/checkpoint`
  generates 12–15 items (not gated on lesson completion),
  `orthography_strict` forced `True`, never touch per-item SRS;
  `GET /units/{id}/checkpoint/result` scores once (≥80% passes),
  bulk-consolidates SRS only for untracked lexemes (mastery 0.5, +3d),
  idempotent, 1-hr retake delay via advisory lock + `429
  checkpoint_retake_delayed`; `GET /courses/{id}/units` returns
  `checkpoint_passed`. Frontend `CheckpointPage` + path-node badges.
  Migration 0012. Detail: BUILD_LOG Phase F.
- **E4 (web push)** — shipped 2026-07-07 (`784da03`, migration 0016):
  VAPID subscribe/unsubscribe + admin-triggerable notify-due-reviews. No
  autonomous scheduling (no cron infra). Detail: BUILD_LOG.
- **Mic-based speaking + STT** — `speak_response`/`speak_repeat` now do
  real `MediaRecorder` capture + STT, graded through the free-text path.
  Client-side WASM Whisper primary (zero audio leaves device);
  self-hosted `faster-whisper` (`POST /stt/transcribe`) fallback, never
  a cloud STT API. *Invariant:* Whisper must run `dtype: "fp32"` (see
  Known limitations). Detail: BUILD_LOG 2026-07-06.
- **Per-language TTS speech-speed** — `/tts` gained optional
  `speaking_rate` (default 1.0, 0.25–2.0); per-device, per-language
  `localStorage` preference (not an account field — `/tts` never caches
  audio across users). `SpeechSpeedSettings.tsx` on ProfilePage, wired
  via `api/tts.ts`'s `speak()` chokepoint. *Open:* a live-tab slider
  click-through was never completed — do a visual close-out next live
  browser session. Detail: BUILD_LOG 2026-07-07.

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
metadata); courses → units → lessons → all 19 exercise types; SM-2
review (being replaced by lexeme-level SRS); gamification
(XP/streak/achievements); reading/writing vs. speaking sections with
server-enforced unlock; CEFR A1–C2; teaching phase before exercises;
in-app content-issue reporting + admin triage + coverage dashboard;
Endless Practice generative feed (all 6 launch directions, lexeme pool +
reviewed sentence-frame templates, zero runtime LLM calls); on-screen
virtual keyboard for non-Latin scripts; self-reported level check with
recommended-unit badge (not a placement system — rejected as premature);
mic-based speaking (`speak_response`/`speak_repeat`) with client-side
WASM Whisper STT.

**Seeded courses** (re-check by `ls docs/content/realizations/<lang>/`
before quoting — grows fast; counts as of 2026-07-08): en→nl 37 units;
en→fa 26 A1/A2 + 1 B1; en→prs 28 A1/A2 + 1 B1; fa-en/nl-en/prs-en share
the same English realization, ~33 units; es/fr 3 units each (A1, parked);
de 10 units. New units are `status: unreviewed` drafts pending mandatory
fresh-context review.

## Known limitations / accepted scope

- **Hindi/Devanagari: `compile_content.py`'s `[\w‌]+` tokenizer doesn't
  cleanly match combining vowel signs/virama** (found 2026-07-10) — it
  fragments words (e.g. "नया"→"नय"). Consequences for Devanagari
  authoring: (1) an infinitive does NOT auto-cover its inflected surface
  forms — declare every tested literal string in `introduced_tokens`;
  (2) "already taught" doesn't reliably carry across files. Not yet
  fixed (Codex lane) — budget extra token-coverage validation
  iterations. Detail: BUILD_LOG 2026-07-10.
- **`backend/tests/test_content_answer_shapes.py` self-skips (`1
  skipped`) under the standard docker pytest** (the image lacks repo-root
  `docs/content/`). Run it with the full repo mounted per its docstring
  (`-v "$(cd .. && pwd):/repo" -e LINGO_REPO_ROOT=/repo`). **With the
  corpus reachable it shows ~226 known FAILING cases — expected, not a
  regression** (real learner-facing ungradeable exercises: 159 en-hi
  comprehension `correct_response`=Hindi-source bug, ~60 en-nl
  `matching_pairs` missing-right-entry, ~6 phrasing mismatches, 1 en-fa
  `grammar_check`, 1 en-fr `reading_comprehension`). **Do not "fix" this
  by weakening the test** — fix the content (CONTENT lane). Detail: BUILD_LOG 2026-07-10.
- **STT: client-side Whisper must run `dtype: "fp32"`** (~150MB, cached)
  — every quantized dtype throws an onnxruntime-web session-creation bug
  at the pinned `@huggingface/transformers` version. Whisper may
  transcribe number words as digits ("zeven"→"7"), missing word-form
  `accepted_answers` — accepted caveat, don't chase with digit tables.
  fa/prs UI strings for voice-answer not yet translated. Detail: BUILD_LOG 2026-07-06.
- **The spine outcome count moves fast — re-grep
  `docs/content/universal_spine.yaml` before trusting any number.** Grew
  19→24→26→28 across 2026-07-05/06. The English realization (all X→en
  directions) still only covers the first 26 outcomes;
  `banking`/second-`health` aren't realized anywhere yet. 10 of 18 paths
  have zero content; no path is past A2.
- Dari's browser-TTS fallback quality is uncertain (`fa-AF`
  approximation; may be silent or wrong-accent).
- No native-speaker review network in general — nl is the deliberate exception.
- Admin content import/export is API-only, no UI (intentional trim).
- Writing prompts graded by exact string match (Phase C adds distance-1
  typo tolerance, per-language strictness).
- **Pre-deploy/pre-beta checklist: confirm `ADMIN_EMAILS` on the live
  deployment is Ramin's real private email, not the `.env.example`
  placeholder, and his account is already registered under it.**
  `register()` grants `is_admin` to whoever registers first with a
  listed email; no email verification closes that race. Deployment step,
  not a code bug. Detail: BUILD_LOG security-audit entry.
- **Pre-deploy/pre-beta checklist: the live server's `CORS_ORIGINS` is
  currently localhost-only** — must list the real origin(s) beta users
  load the frontend from or their requests are rejected. A deployment
  decision, don't guess-and-fix. (An unbounded-`response`-field
  resource-exhaustion bug was found and fixed in the same pass.) Detail: BUILD_LOG.
- Starlette "BadHost" CVE (CVE-2026-48710) **fixed and deployed to the
  dev stack 2026-07-06** (`fastapi` 0.115.12→0.139.0, starlette→1.3.1);
  not yet on the live server (192.168.4.4). Detail: BUILD_LOG.
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
- **Fixed 2026-07-05:** `POST /admin/content/import` now appends new
  units to an existing course (diffed by unit `order`) instead of
  skipping the whole course — previously every unit beyond a course's
  seed was validated-on-disk but never live. Detail: BUILD_LOG.
- **Fixed 2026-07-05 (Phase D2):** the full fa course compiles
  end-to-end — the embedded-multi-speaker-label dialogue cards in fa
  units 01/02 were split into one `text_blocks` entry per speaker turn
  (name in `target.speaker`). *Not done:* several single-turn cards (fa
  unit02 misc + units 04/05) still bake the name into `text`; harmless
  to the compiler but a TTS voice reads the name aloud. Detail: BUILD_LOG.

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
  that builds the frontend.
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
- **Content-authoring dispatches to Codex must always include, up
  front:** the recognition→drag→production pacing rule; and — when
  authoring a source overlay against an existing target realization — the
  STRONG form of the sibling-isolation rule ("treat the sibling-direction
  overlay as if it does not exist, do not open it at all"; "for reference
  only" has failed twice). Point every content task at AUTHORING_GUIDE.md
  + AUTHORING_PROMPT_TEMPLATE.md, and **route every deliverable through a
  SEPARATE fresh-context review task (zero access to the authoring
  reasoning) before import.**

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

## Content sourcing policy

- **Try `firecrawl search`/`firecrawl scrape` for real public-domain
  source material FIRST** (FSI/Peace Corps/DLI or any public-domain
  course for the specific language), before falling back to
  established-conventions-only authoring — strictly better than manual
  `WebFetch`+`pdftotext` PDF-wrangling; this replaces the old default
  research step. A confirmed new source: the DLI Dari Basic Course
  (`fsi-languages.yojik.eu/languages/DLI/Dari/Books/`, cleanly
  text-extractable). Detail: BUILD_LOG 2026-07-09.
- **`FIRECRAWL_API_KEY`: never hardcode, persist to a committed file, or
  embed directly in a shell-command argument** (exposes it in shell
  history/process listings). Safe pattern: `firecrawl login --api-key
  ...` run once by Ramin, after which the CLI reads stored credentials.
  **`.firecrawl/` is gitignored — write scrape output there with `-o`.**
- **Disclose the actual source and its actual license in
  `generation_provenance`** — never one undifferentiated "found real
  material" bucket, whether you found usable content or genuinely nothing.
- **CC-licensed sources are a real but currently-BLOCKED tier**, not a
  live second option. Per AUTHORING_GUIDE §10 (authoritative):
  - **Tatoeba — reference-only in practice.** The CC0 subset is
    effectively empty for launch languages (fa 0, prs 0, nl 50); the
    CC-BY pool needs a learner-facing attribution surface (schema + UI)
    that doesn't exist yet. **Don't re-investigate pool sizes without new
    information.**
  - **Wikibooks / any CC BY-SA source — categorically excluded** until
    Ramin explicitly resolves the share-alike question (a real legal
    call), *before* first use, not after shipping derived content.
  - **University OER / other CC-BY courseware (e.g. COERLL) — usable only
    after a real attribution credit surface exists** (hard precondition
    of first import, per the COERLL Français interactif precedent).
  - See §10 for the categorical-exclusion list (DLI GLOSS/Headstart2,
    OpenSubtitles-derived corpora, Anki shared decks, commercial
    apps/textbooks).

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
- **`docs/content/AUTHORING_PROMPT_TEMPLATE.md`** — fill-in-the-blanks
  Codex dispatch templates with standing rules baked in.
- **`scripts/audio_manifest.py`** — aggregates realization
  `media_assets:` blocks into one recording queue.

---

# FOOTGUNS (hard-won — do not relearn these)

Each entry: the rule, brief why, pointer for the full incident. Verbatim
narratives are in BUILD_LOG (and the pre-2026-07-11 CLAUDE.md appended there).

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
- **Codex's `--resume` continues whatever thread was last active
  (including a stale "still running" one that blocks it); use `--fresh`
  when a prior dispatch might still be mid-flight** and this one must not
  collide. Detail: BUILD_LOG.
- **Parallel sessions authoring content collide on unit numbers because
  logs/notes lag real disk state — always `ls
  docs/content/realizations/<lang>/` immediately before claiming a new
  unit number.** Never trust a log/memory/self-report, only the files on
  disk right now. Detail: BUILD_LOG.

### Migrations / docker / DB

- **Every migration after 0001 must defensively check existence before
  `op.add_column`/`create_table`/`create_foreign_key`/`create_index`**
  (`sa.inspect(bind)` or `checkfirst=True`). `0001_initial.py` runs
  `Base.metadata.create_all()` against the LIVE ORM models, so a fresh
  migrate creates every table at its CURRENT shape at 0001 — an
  unguarded later `ADD COLUMN` then crashes on a genuinely fresh
  deploy/CI while looking fine on any migrated stack. `0008`–`0012` were
  fixed after such a crash. Detail: BUILD_LOG Phase A closeout.
- **`docker compose restart` does NOT reload `.env` — only `up -d` (or
  `--force-recreate`) does.** A stale-env CORS failure once looked like a
  code bug. Detail: BUILD_LOG.
- **`docker compose`'s `.:/app` bind mount syncs source live, but uvicorn
  has no `--reload` — a backend CODE change needs an explicit `docker
  compose up -d --force-recreate api`** to take effect (distinct from the
  `.env` footgun above). Detail: BUILD_LOG.
- **Never use `docker compose --env-file` for tests** — it only affects
  compose variable substitution, not the container env (`env_file: .env`
  always wins). This once ran the suite against the LIVE database,
  wiping/reseeding prod data. Use the isolated dropdb/createdb recipe
  (OPERATIONS). Detail: BUILD_LOG.
- **Any dispatch telling a worker to run tests against Docker MUST name a
  uniquely-named test DB / compose project** (not just "the isolated-DB
  recipe") when many workers run concurrently — several workers once
  schema-dropped the SHARED dev DB, wiping all content and progress. Detail: BUILD_LOG 2026-07-10.
- **`alembic upgrade head` can fail with a confusing `DuplicateColumn`
  when `alembic_version` doesn't exist as a table** (Alembic has no
  history, re-runs an early `ADD COLUMN`). Fix: `alembic stamp <version
  the schema actually reflects>` before `upgrade head`. Detail: BUILD_LOG.
- **A direct-DB shortcut faking "lesson completed" bypasses the real
  endpoint's side effects** (`SkillProgress`/`user_lexeme_srs`/streak) —
  always verify through `POST /lessons/{id}/complete`, not a DB shortcut,
  even when slower. Detail: BUILD_LOG.
- **Content seeding is create-missing-only, not delete-and-recreate** (an
  earlier version wiped user progress via cascade every deploy — don't
  regress it). Detail: BUILD_LOG.
- **Google Cloud TTS `RefreshError: invalid_grant: Invalid JWT Signature`
  means a corrupted service-account private key (usually GUI-editor
  copy-paste mangling), NOT an IAM/enablement problem** (which shows as
  403). Debug: `json.loads` → `from_service_account_info()` →
  `creds.refresh()` (surfaces it); the `/tts` route swallows the real
  exception, so call `tts_service.synthesize()` directly via `docker
  compose run`. **Never hand-copy a service-account JSON through a GUI
  editor — read/write its exact bytes programmatically.** Detail: BUILD_LOG.

### Content-authoring / compiler / grading-shape

- **`compile_content.py`'s `--realization`/`--overlay` are `nargs='+'`,
  not `action='append'`** — the interleaved form silently keeps only the
  LAST value. Correct: all realizations together, all overlays together,
  matched by position (`--realization A B --overlay A B`). Detail: BUILD_LOG.
- **`backfill_lexemes.py` needs the full repo mounted** (the backend
  image only has `backend/`): `docker compose run --rm -v "$(cd .. &&
  pwd):/repo" -e PYTHONPATH=/repo/backend --entrypoint python api
  /repo/scripts/backfill_lexemes.py`. Detail: script docstring.
- **Exercise-type registration must be checked exhaustively: `comm`-diff
  every `type:` in `docs/content/realizations/` against every `case` in
  `ExerciseRenderer.tsx` after any content or exercise-type change** — a
  mismatch compiles clean and only crashes a real lesson in the browser.
  Detail: BUILD_LOG.
- **Sweep for internal-jargon leaks after every content round** — bare
  snake_case tokens in `options`/`distractors`/`correct_option`
  (`null_subject`, `both_speakers` shipped for real) and internal words
  like "reviewed" in learner-facing feedback. Grep `docs/content/`
  periodically. Detail: BUILD_LOG.
- **A `listen_select`/`dialogue_response` distractor must never be
  something the tested speaker says ANYWHERE in that audio, full stop** —
  verify this explicitly (not just that it differs from the correct
  answer) when authoring/reviewing multi-turn dialogue-audio exercises. nl
  units 44-50 made 6/15 exercises unanswerable this way. Not yet enforced
  by the compiler (Codex lane) or AUTHORING_GUIDE. Detail: BUILD_LOG 2026-07-09.
- **Never write bare `yes`/`no`/`true`/`false`/`on`/`off` as a YAML
  string value in content fields — PyYAML silently coerces to booleans.
  Always quote (`"Yes"`).** The compiler validates this but has a gap
  (next bullet); don't rely on catching it after. Detail: BUILD_LOG.
- **The compiler's boolean-coercion validator does NOT cover every field
  — `title`/`gloss` on vocabulary teaching items passed clean while
  becoming Python booleans**, caught only by the import API's Pydantic
  schema. Until widened (Codex lane), manually grep/spot-check new content
  for this beyond a green compile. Detail: BUILD_LOG 2026-07-08.
- **Whenever an exercise component's answer payload isn't string/string[],
  read what `accepted_answers` actually looks like across the REAL corpus
  before trusting either end, and make `grade()` canonicalize every
  authored shape** — a single successful live test with one exercise does
  not rule out a content-shape-dependent bug. Confirmed twice:
  - `matching_pairs` — `MatchingPairs.tsx` submitted a flat
    `Record<left,right>` but content authors an array of `{left,right}`;
    every matching_pairs exercise scored wrong and rendered `[object
    Object]`. Fixed frontend submit + shared `formatAnswer.ts`; and
    `grade()` canonicalizes flat-dict OR `{left,right}[]` (Endless
    Practice's `derive_answer()` emits the flat dict). Detail: BUILD_LOG 2026-07-05.
  - `word_order`/`listen_order` — `WordOrder.tsx` always submits a list,
    but 146/173 (~84%) exercises author a space-joined string;
    list-vs-string never compared equal. New `canonical_order_tokens()`
    canonicalizes either shape. Detail: BUILD_LOG 2026-07-07.
- **Any frontend component that assembles a raw token array into a
  click-built sequence (word_bank, future letter/tile banks) needs an
  EXPLICIT `dir` on its own render container — it inherits direction from
  nowhere.** Farsi/Dari tiles assembled LTR on screen (grading was always
  correct; pure display bug); fixed via `answerDirectionForExercise()` on
  `WordOrder.tsx`'s containers. Applies to ANY future RTL/non-LTR
  language. `MatchingPairs.tsx` does NOT have this (two fixed columns,
  not a sequence). Detail: BUILD_LOG 2026-07-09.
- **`content_key` is unique PER COURSE, never globally** (migration 0015)
  — fa-en/nl-en/prs-en share the same English realization so content_keys
  are identical across them; a global unique index 500s the second
  course's import. Use `PracticeTemplate`'s `UniqueConstraint("course_id",
  "content_key")` pattern for any future content_key-bearing table. Detail: BUILD_LOG 2026-07-07.

### Performance

- **Keep reusing `_generate_prioritized()`'s per-template
  `slot_candidate_cache` — don't reintroduce a per-attempt course-wide
  lexeme-pool scan.** `lexeme_matches()` is pure, so per-slot candidates
  are identical across attempts within one batch request; memoizing gave
  ~25x–60x speedup (a live-QA pass measured 77s → fast on prs-en). Detail: BUILD_LOG 2026-07-07.

---

# OPERATIONS

## Where things run

- **Backend (live):** `ramin@192.168.4.4` (SSH key), code at
  `/home/ramin/LingoSquared/backend`, API on **port 8010** (8000 is
  `audiobookrequest`). OpenAPI at `http://192.168.4.4:8010/docs`.
  `192.168.4.8` is a DIFFERENT machine (SMB-only NAS) — don't confuse them.
- **Frontend (dev):** `cd frontend && npm run dev`. Port 5173 is often
  taken; Vite falls back to 5174 — check terminal output. `.env`'s
  `VITE_API_BASE_URL` points at localhost or 192.168.4.4:8010.
- **Backend's `CORS_ORIGINS` (`.env`) must list whatever port the
  frontend is actually running on.**

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

## Isolated-DB test recipe (never `--env-file`)

```bash
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && \
  docker compose exec -T db dropdb -U lingosquared --if-exists lingosquared_test && \
  docker compose exec -T db createdb -U lingosquared lingosquared_test && \
  docker compose run --rm api sh -c 'DATABASE_URL=\$(python3 -c \"import os,re; print(re.sub(r\\\"lingosquared\$\\\", \\\"lingosquared_test\\\", os.environ[\\\"DATABASE_URL\\\"]))\") python -m pytest -q'"
```

## Deploying a backend change

**`docs/PRE_DEPLOY_RUNBOOK.md` is the full checklist — read it before the
first real deploy to 192.168.4.4.** It covers pre-flight (incl. whether
`alembic_version` even exists on the live DB — never yet checked there),
required env vars (`ADMIN_EMAILS`, `CORS_ORIGINS`,
`AZURE_SPEECH_KEY`/`_REGION`, `GOOGLE_CLOUD_TTS_CREDENTIALS_JSON`), a
backup step, the ordered deploy, and post-deploy smoke tests. **As of
2026-07-07 the live server has never been deployed to beyond its original
setup — treat the next deploy as from-scratch-equivalent, don't skip the
pre-flight.**

Quick-reference skeleton (see runbook for the complete ordered version):

```bash
rsync -az --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
  /Users/raminazizi/dev/LingoSquared/backend/ ramin@192.168.4.4:/home/ramin/LingoSquared/backend/
rsync -az /Users/raminazizi/dev/LingoSquared/docs/ ramin@192.168.4.4:/home/ramin/LingoSquared/docs/

ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose build api"
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose run --rm api alembic upgrade head"
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose run --rm api python -m app.content.seed"   # bootstrap only — NOT the real content, see runbook
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose up -d api"   # BEFORE the HTTP steps, else the container serves the OLD image
# real content import (compile_content.py --> POST /admin/content/import, admin-auth),
# THEN lexeme backfill, THEN practice-template admin import — in that exact order
```

**Practice-feature deploys need the lexeme backfill THEN the
practice-template admin import, after migrations — in that order.**
`POST /admin/courses/{id}/practice/import`'s lesson-key resolution matches
via `Lexeme.provenance_lesson_content_key`, which only exists after
`backfill_lexemes*.py` runs — importing practice first fails every
template on a fresh stack. Detail: BUILD_LOG + runbook.

## Secrets / TTS state

- **TTS is Google Cloud** (service-account JSON via
  `GOOGLE_CLOUD_TTS_CREDENTIALS_JSON`, raw JSON content not a file path)
  for 8 languages, **proxied server-side only — never sent to the frontend.**
- **Azure Cognitive Services Speech is a second provider for Farsi**
  (Google has zero Persian/Dari voices): `fa-IR-DilaraNeural` default,
  `fa-IR-FaridNeural` male. Config `AZURE_SPEECH_KEY` +
  `AZURE_SPEECH_REGION`, same unset-by-default graceful-degradation as
  Google (empty → browser fallback, never a crash). **Built and tested
  but not yet set to a real key.** Implemented via the plain REST API
  (`synthesize_azure()`), reusing `httpx`, no new dependency.
- **Dari (`prs`) has zero coverage from either provider** — browser
  `speechSynthesis` is its only fallback.
- ElevenLabs is no longer the live provider (superseded 2026-07-04);
  gotchas in BUILD_LOG if revisited.
- **The public-domain FSI/Peace Corps audio does NOT help as a content
  or asset shortcut** — the Persian FSI tapes are 24 long unsegmented
  per-unit recordings (no per-phrase splicing without manual editing);
  Peace Corps Persian/Dari has no recordings at all (PDF-only). Only use:
  a pronunciation reference for a human recording session. **Don't
  re-investigate either without new information.**

## Feedback/issue-report collection (2026-07-09)

`POST /feedback` (unauthenticated, works from logged-out screens), a
`page_path` column on `ContentIssueReport`, and an every-page
`FeedbackWidget.tsx`. The multi-deployment fix: the frontend submits
feedback via a separate configurable base URL `VITE_FEEDBACK_API_URL`
(falls back to `VITE_API_BASE_URL` when unset), so a published
"clone-and-run-locally" build can point every install at one central
collector by default. REST-only, mobile-ready. Full spec: CONTRACT.md.

**Standing gap: `VITE_FEEDBACK_API_URL` has no real value set yet** — it
needs ONE stable internet-reachable collector URL. An infra/deployment
decision for Ramin (tunnel/DDNS/hosted domain), not for a Claude session
to invent unilaterally. **Flag this again before ever publishing a
"run-locally" distribution** — until then local-install feedback only
reaches whatever backend that install happens to run against.

---

# HISTORY

Full chronological build log, every bug found and fixed, the reasoning
behind every past decision, and the verbatim pre-2026-07-11 CLAUDE.md:
`docs/BUILD_LOG.md`. Per-lane review-yield ledger and per-direction tier
recommendations: `docs/CONTENT_DEFECT_REGISTRY.md`.
