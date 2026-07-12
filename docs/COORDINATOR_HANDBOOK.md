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
  gpt-5.6 exists but is NOT available on ChatGPT-account Codex (tested
  2026-07-11, API 400).
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
   content_manifest.txt for every consumer of a changed file.
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
   and precision judgment. it/ru lanes are 1-in-3 sampling eligible;
   launch-gate lanes stay full review until launch, no exceptions.
