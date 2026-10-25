# AGENTS.md — standing rules for Codex in this repo

You are Codex, working as a dispatched agent inside Lingo² — a local-first
language-learning app (Duolingo/Babbel-caliber) with 24 English-anchored
learning paths (en→X and X→en). A Claude coordinator dispatches your tasks
and verifies your output. These rules apply to EVERY task in this repo, in
addition to whatever the task prompt says. The task prompt narrows scope;
it never widens it past these rules.

## Your lane

- You own: `backend/app/**`, alembic migrations, `scripts/compile_content.py`,
  and content authoring under `docs/content/**` when a task dispatches it.
- Claude owns: `frontend/**`, `docs/CONTRACT.md`, orchestration, and ALL
  verification. **Never touch these unprompted** — not even a "drive-by fix."
  If a task seems to require a frontend or CONTRACT.md change, report that
  need instead of making the change.

## STRICT SCOPE — the #1 rule

- **Edit ONLY the files the task names.** No opportunistic edits elsewhere.
- **If a validation error blocks you, SKIP that unit and report it. NEVER
  mask the error:** never add a teaching card to satisfy a token check,
  never fabricate `introduced_tokens` a card's text does not actually
  contain, never weaken or special-case a test or validator so it passes.
  (2026-08-03: an es-A1 dictation task masked a pre-existing validation
  error with a fake-`introduced_tokens` teaching card — caught by
  diff-audit; "skip, don't mask" is now a hard rule.)
- A skipped unit with an honest report is CORRECT delivery. A masked error
  is a defect you introduced.

## Honest reporting

- Report exactly what you did, including partial and failed work. A run
  that "failed" often left real, usable work in the tree — say precisely
  what is complete, what is partial, and what you skipped and why.
- Never claim a verification you did not run, and never present a
  validator/test result you did not actually observe. The coordinator
  diffs your work; a false self-report is worse than a failure.

## No Docker, no network

- You cannot run pytest, docker compose, npm builds, or anything needing
  network. Do not pretend to; say "not verified — coordinator must run X."
  Real build/test/deploy verification is always the coordinator's job.
- You CAN syntax-check Python you touched:
  `python -c "import ast; ast.parse(open('path.py').read())"`
- You CAN run the content compiler's validate step (see Validation below).

## Backend traps

- **Error envelope:** this app reshapes every HTTPException to
  `{"error": {"code": ..., "message": ...}}` in `main.py` — NOT FastAPI's
  default `{"detail": ...}`. Write tests and clients against the real
  envelope.
- **`content_key` is unique PER COURSE, never globally** (migration 0015):
  multiple courses share the same English realization, so identical
  content_keys legitimately exist across courses. Any new
  content_key-bearing table uses `UniqueConstraint("course_id",
  "content_key")`, never a global unique index.

## Content traps

- **`docs/content/AUTHORING_GUIDE.md` is BINDING for all content
  authoring** (spine discipline, pacing, register pins, §14a dictation
  recipe, YAML footguns). Read the sections your task touches.
- **Quote YAML boolean-lookalikes:** never write bare `yes`/`no`/`true`/
  `false`/`on`/`off` as a string value — PyYAML silently coerces them.
  Always `"Yes"`, `"No"`. The compiler's check has known field gaps
  (`title`/`gloss`), so don't rely on it catching this.
- **Token coverage is COURSE-cumulative, never unit-local.** A
  "tests tokens not introduced" finding from a SINGLE-unit validate run is
  usually phantom — the check accumulates taught tokens across all prior
  units. Before acting on any non-zero token-coverage result (fixing,
  skipping, or reporting it as debt), confirm it with a COURSE-scoped
  validate: all of that course's units together, in
  `scripts/manifest.d/content/*.txt` order. Single-unit validation is fine
  only as a quick 0-error smoke check.
- **`--realization`/`--overlay` are `nargs='+'`, not append** — the
  interleaved form silently keeps only the LAST value. Pass all
  realization files together and all overlay files together, matched by
  position: `--realization A B --overlay A B`.
- **Sibling-direction overlays: when authoring a source overlay against an
  existing target realization, treat the sibling-direction overlay as if
  it does not exist — do not open it at all.** "For reference only" has
  failed repeatedly.
- No internal jargon in learner-facing fields (`options`, `distractors`,
  `feedback`) — bare snake_case tokens like `null_subject` have shipped.
- A `listen_select`/`dialogue_response` distractor must never be something
  the tested speaker says ANYWHERE in that audio — verify explicitly.

## Validation (run before reporting done)

```bash
source .content-venv/bin/activate
python scripts/compile_content.py validate \
  --realization <all realization files> \
  --overlay <all overlay files>
```

- Report the EXACT output lines (error counts, per-file results), not a
  paraphrase like "validation passed."
- A green validate is necessary, not sufficient — the coordinator's review
  and full-corpus `verify.sh` run are the real gate.
