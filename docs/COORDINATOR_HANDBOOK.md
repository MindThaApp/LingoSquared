# Coordinator Handbook

Standing operating knowledge for whichever AI session (or human) is
coordinating this project. This file is the canonical, version-controlled
copy — per Ramin's call (2026-07-11), ALL durable project knowledge lives
in this repo, not in any machine-local memory store. If you learn a
durable routine or rule, record it here (or in the file the
"How this documentation set works" section of CLAUDE.md directs you to),
commit, and push.

## Pipeline model (Ramin's standing instruction)

- Keep roughly 4-5 workers running at all times; the coordinator manages,
  verifies, and merges — it does not author content or write feature code
  itself. Launch-gate work (en-nl, en-fa, en-prs directions) always
  outranks post-launch drip content.
- Model selection: Sonnet for authoring/analysis, Opus for fresh-context
  review and precision fixes; never a stronger model than the task needs.
  Codex (gpt-5.5 high for compiler/backend surgery, medium for routine
  round-trips) carries backend/compiler work and large language-content
  fixes — deliberately load-balance toward Codex when Claude budget is
  constrained (Ramin tracks weekly usage; ~40% by day 2 prompted this).
  gpt-5.6 is NOT available on ChatGPT-account Codex regardless of
  usage resets — re-confirmed 2026-07-13 with gpt-5.6, gpt-5.6-codex,
  and gpt-5.6-codex-high (identical server-side 400 "not supported when
  using Codex with a ChatGPT account"; the ChatGPT WEBSITE offering 5.6
  is a different product surface). Only paths: gpt-5.5, or an API key
  with per-token billing. Do not re-probe.
  Budget snapshot 2026-07-13 00:18: Claude at 80% used (resets Fri
  17:00), Codex 95% LEFT (resets ~6.5d) — route aggressively to Codex:
  mechanical content repair, validators, backend; keep Opus reviews for
  launch-gate only; coordinator stays lean.
- Every worker dispatch: isolated worktree, verified with
  `git worktree list` after dispatch; explicit-pathspec commits; unique
  Docker DB/compose-project names named IN the dispatch prompt; inline
  the 3-5 task-critical rules in the prompt itself.
- Verify every worker's diff against its self-report before merging.
  After merge rounds: `git merge-base --is-ancestor` per branch, full
  content validation, then push.

## GitHub backup routine

- Private remote: https://github.com/ramin-azizi/LingoSquared
  (created 2026-07-11 by Ramin himself after the coordinator's attempt
  was safety-blocked — that block-then-hand-to-owner pattern is correct;
  keep it).
- The coordinator runs `git push origin master` after EVERY verified
  merge round. Workers never push. Keep the repo PRIVATE — the content
  corpus is the core asset.
- History was secret-swept before first push (clean). Never commit real
  credentials; `.env` files stay untracked (only `.env.example`).

## Documentation structure (see also CLAUDE.md's own section on this)

- Four CLAUDE.md files: root (always loads, cross-cutting rules only) +
  docs/content/, backend/, frontend/ (each auto-loads only for agents
  working under that directory — deliberate token economy, never merge
  back into root).
- Filing rule: rules → the right CLAUDE.md; incident narratives →
  docs/BUILD_LOG.md; per-bug-class records with per-language ledger →
  docs/CONTENT_DEFECT_REGISTRY.md (every fresh-context review appends
  its findings there, including zero-defect results — that data drives
  the tiered review policy).
- Rationale: loaded tokens bill uniformly regardless of relevance, and
  context re-sends on every tool call (prompt-cached ~10% after first).
  Loading less is the only real lever.

## Review economics (tiered policy — details in CLAUDE.md)

- Automate known bug classes into validators first (the two 2026-07-11
  compiler validators caught 20 real bugs across es/de on day one);
  sample mature lanes (3 consecutive zero-defect reviews → 1-in-3);
  full review only for new territory, grading changes, and launch-gate
  content until launch.

## Research tooling

- Default: free built-ins (WebSearch, WebFetch, curl + pdftotext).
  Firecrawl is the fallback for JS-heavy sites and bulk site-mapping
  (`firecrawl map`) — do not top up credits just for routine research
  (its account ran dry 2026-07-11 and the free stack produced the same
  quality source map). Best sources (FSI/DLI) are scanned-image PDFs
  anyway, which no crawler fixes — page-by-page image reading by the
  authoring worker is the workhorse there.

## Local models (Ollama on the M4 Pro) — assessed 2026-07-12, don't re-test without new models

- Installed: qwen3:14b (9.3GB, the only one that fits alongside the Docker
  stack on 24GB RAM), qwen3-coder:30b + deepseek-r1:32b (18-19GB — will
  swap unless Docker is stopped first; don't use casually).
- Benchmarked qwen3:14b on the §16 matching_pairs retrofit (the most
  local-model-friendly backlog we have): YAML format compliance and
  constraint-following were good (no invented vocabulary), speed 17-49s
  per exercise, but **content judgment fails in exactly the ways that
  create unanswerable exercises** — it collapsed two distinct exercises
  into identical pair lists, and on a register-labeling exercise emitted
  the same left item twice with BOTH labels (duplicate-left, contradictory
  answers) plus dubious formal/informal labels.
- **Standing verdict: local models must not author or modify learner-facing
  content, even "mechanical" expansions.** Acceptable uses: pure-format
  transforms verifiable 100% programmatically, throwaway scaffolding, or
  bulk classification where a validator is the sole consumer. Ramin's
  operating rule: ask him before running local AI; overnight runs allowed
  only while on AC power or battery >= 60% (check `pmset -g batt`).
- MLX is installed (can be ~10-30% faster than Ollama on the same model);
  only worth revisiting if a materially stronger small model lands.

## Known multi-agent footguns (full list in root CLAUDE.md)

The ones that have actually bitten coordinators: broad `git add` sweeping
concurrent sessions' files; worktree removal destroying uncommitted work
(check `git status` in the worktree first, always); workers pointing
tests at the shared `lingosquared` dev DB (name a unique DB in every
dispatch); concurrent workers editing shared files
(`scripts/_en_target_lexeme_common.py`, manifests) — serialize or
reconcile by semantic comparison with validators as arbiter; Codex tasks
run unisolated in the main working tree — never run two Codex tasks that
touch the same file concurrently, and commit each task's output with
explicit pathspecs.

## Current strategic state (update as it changes)

- Launch gate: en↔nl + en↔fa/prs, ≥10hr teaching + ≥10hr practice per
  pair + working checkpoints + "minimum bugs" live verification.
  Teaching hours PASS everywhere (measured 2026-07-11); practice depth
  was the gap and 245 reviewed templates were added same day — re-measure
  after the next DB sync.
- Arabic (MSA) approved as a new path 2026-07-11: backend groundwork
  shipped; first authoring wave sources from FSI Modern Written Arabic
  Vol 1 (see docs/content/SOURCES_ARABIC_MSA.md); dialect track later.
- Dev-DB sync: `scripts/sync_dev_db.sh` (prompts for admin password,
  stores nothing). The shared dev DB reflects imports only — git is the
  source of truth.

## Coordinator judgment heuristics (written by the Fable coordinator, 2026-07-12 — for any successor model)

The pipeline is mature; your job is verification and routing, not
cleverness. The failures that actually cost time today were all
"trusted a report." Mechanical rules that substitute for judgment:

1. **Never act on a worker/Codex self-report.** Before merging or
   committing anything: `git show --stat <hash>` and confirm the file
   list matches the task scope EXACTLY; run the task's acceptance
   command yourself (put the verbatim command in every dispatch prompt
   so "run it yourself" is copy-paste). Two fixers and Codex (twice)
   self-reported success today on work that failed my re-run.
2. **After every merge/dispatch batch:** `git log --oneline -5` (agents
   sometimes commit straight to master when worktree isolation fails),
   `git worktree list`, and `git merge-base --is-ancestor <branch> master`
   per branch.
3. **Shared-artifact checklist before committing content changes:** the
   en realization has FOUR overlay consumers (nl-en/fa-en/prs-en/de-en);
   manifests and `_en_target_lexeme_common.py` are single-writer; grep
   manifest.d/content/ for every consumer of a changed file.
4. **Escalate, don't improvise, on launch-gate design questions**
   (register norms, bar interpretations, anything Ramin owns). A
   reviewer who says "this needs a human call" is right — route it to
   Ramin, park the wave, keep other lanes moving.
5. **Every new bug class → validator (Codex) or pinned rule (CLAUDE.md)
   + registry Section 4 entry, same session.** This is why review
   yields fell all day; keep the flywheel turning.
6. **Quote register pins and the 3-5 task-critical rules VERBATIM in
   every dispatch prompt.** Auto-loaded context is not enough; the one
   dispatch that omitted the register pin cost a 5-file conversion.
7. **Cadence:** merge → validate → registry/manifest → sync (never
   mid-conflict) → push, after every round. Background-run syncs with
   full logs (no tail pipes); grep logs for `"-> 401"` and `Traceback`.
8. **Budget routing:** Codex for authoring/backend/compiler surgery,
   Sonnet for scoped fixes/frontend, Opus ONLY for fresh-context review
   and precision judgment. Launch-gate lanes stay full review until
   launch, no exceptions. **Sampling was tried on it/ru 2026-07-12 and
   REVERSED** — see heuristic 10.

9. **Prevention is cheaper than detection — spend on the prompt, not the
   reviewer.** 2026-07-12: three Sonnet-authored waves produced 23 defects,
   and every one was a class the dispatch prompt did NOT mention. The one
   class quoted VERBATIM in those same prompts came back with ZERO findings
   in two independent reviews (it had needed 5 fixes the wave before).
   Sonnet's capability was never the binding constraint — the prompt was.
   So: paste `docs/content/AUTHORING_PREFLIGHT.md` verbatim into every
   authoring dispatch, and make the author self-report per item.
   Cost order, cheapest first: **validator → checklist → review.** A
   validator costs tokens once and catches its class forever (three new
   ones found 3 real bugs on their first corpus run, one of them in a unit
   Opus had already "reviewed"); an Opus review costs 160–216k tokens
   EVERY wave. Reserve review for what neither can reach — character canon,
   "is this answerable by a human," genuine judgment. Review's real job is
   discovering NEW classes (it found 4 that day → 4 permanent validators),
   not re-finding known ones.

10. **"Mature lane" is per-RECIPE, not per-language.** A lane does not stay
    mature when it moves to new TOPICS. it/ru were sampled 1-in-3 on the
    strength of zero-defect A1 13-15 reviews; Italian 16-18 was set to merge
    on validators alone and turned out to carry **10 compiler-invisible
    defects** (it validated at 0 errors), three of which graded a CORRECT
    learner answer as WRONG. Both lanes reset to full review.

11. **Live-play the app — the compiler cannot see UI-logic bugs.** The worst
    bug of 2026-07-12 (`MatchingPairs.tsx` keyed option tiles by TEXT VALUE,
    so an exercise mapping many lefts onto one right disabled every matching
    tile on the first pick → Check never enabled → **the lesson was
    impossible to complete**, in the en-nl launch pair) compiled clean,
    validated at 0 errors, and was found ONLY by playing the lesson. Reading
    a diff is not verification.

12. **Codex can REVIEW, not just author.** Fresh-context content review on
    Codex found 9 real defects in the de-en B1 wave (2026-07-13) at a
    fraction of an Opus review's ~200k tokens. Route review there whenever
    Claude budget is the constraint; keep Opus for launch-gate content only.

13. **Never accept a validator on its own armed test.** A Codex word_order
    validator passed the armed test IT wrote and still had a real gap (it
    only rejected answers matching the word-BANK order; any other wrong
    permutation passed silently). Write your OWN adversarial test every time.
    Corollary, from the same day: Codex cannot run pytest or Docker — its
    "verified" means `py_compile`. **Running the suite is always the
    coordinator's job.**

14. **Check diff SHAPE, not just validation-green.** A template-expansion task
    touched 101 files / 29k lines to add 249 templates (it had round-tripped
    every file through a YAML dumper). Green validation did not prove nothing
    was lost — a SEMANTIC comparison did (parse old vs new, compare every
    template key: 0 lost, 0 altered). Do this for any suspiciously large diff.

15. **Watch background work with ONE backgrounded until-loop, never by
    polling.** Each status check is a full context re-send — the dominant
    token cost. `until <check>; do sleep 90; done` with run_in_background
    costs one call and wakes you exactly once.

16. **The coordinator OWNS expert decisions (Ramin, 2026-07-13).** Curriculum
    design, architecture, review policy, budget routing, what to build next —
    decide and report, do NOT ask. Ramin owns only: money, legal, commercial
    "done", launch timing, anything touching real users/credentials, and taste
    calls on his own languages. Asking him to approve expert work is a failure
    mode he explicitly corrected. (I designed the entire B2 spine tier
    unilaterally on that instruction — that was the right call.)
