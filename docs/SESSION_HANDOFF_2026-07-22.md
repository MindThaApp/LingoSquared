# Session handoff — 2026-07-22 (publish-gate push)

Read root `CLAUDE.md` first. This doc is "what happened / what's next" —
reference, not rules.

---

## ⚠️ READ THIS BEFORE OPENING THE REPO ON THE OTHER MAC

**iCloud is syncing this repo's `.git` directory.** The cleanup this session
found and removed `.git/index 2` — a sync-conflict copy of the binary git
index. `.git/index`, `.git/refs` and `.git/objects` are state git rewrites
constantly; if iCloud resolves a conflict there you get a corrupted index,
lost commits, or refs pointing at objects that never synced.

**Therefore: move this work between machines via `git`, NOT via iCloud.**

Everything is pushed to `origin/master` at **`24229756`**. On the other Mac:

```bash
cd <repo>
git fetch origin && git status        # confirm clean BEFORE pulling
git pull --ff-only origin master
```

**Do not have both Macs open on this repo at once.** If `git status` ever
shows a mass of deleted files with no `.icloud` placeholders, that's iCloud
failing to materialize — recover with
`git ls-files --deleted -z | xargs -0 git checkout --`, don't panic.

Worth doing properly at some point: move the repo out of iCloud Drive and
sync via the remote, or append `.nosync` to `.git` and `.content-venv`.

### Second environment gotcha: the repo path contains a space

The repo lives at `~/Library/Mobile Documents/com~apple~CloudDocs/dev/
LingoSquared`. **Always quote paths.** An unquoted `$VAR` holding the repo
root splits into two arguments. This already caused a silent, total failure
(see "The sync bug" below), and it bites in zsh in another way: zsh does NOT
word-split unquoted variables, so the compiler's `--realization $REALS`
pattern **must be run under `bash`**, not the session's zsh.

---

## State

- **Git:** all work committed and pushed. `origin/master` = `24229756`.
  19 commits this session. Working tree clean except two files that were
  already dirty at session start and are NOT this session's
  (`.claude/settings.json`, a `__pycache__` `.pyc`).
- **Docker stack:** up and healthy (`backend-api-1` :8020, `backend-db-1`,
  `backend-web-1` :8011). `backend/web_dist` is EMPTY, which is why :8011
  returns 403 — that's the deploy copy, not the dev path. Use the vite dev
  server for live verification.
- **Dev DB:** fully re-synced in runbook order (content → lexemes →
  practice). 53 courses, ~18.9k lexemes, templates +680.
- **Verification:** content compiler 0 errors corpus-wide; frontend clean
  build exit 0; backend pytest green (see "flaky test" below).
- **NOT DONE: live browser verification.** Nothing this session has been
  played in a browser. Per root `CLAUDE.md` that is the non-negotiable bar
  for anything user-facing, and this project's worst bugs were ALL found
  only by playing a lesson. **Treat everything below as verified-by-test,
  not verified-in-use.**

---

## Publish-gate scorecard

| Gate item | Start of session | Now |
|---|---|---|
| Teaching ≥10h — en→nl/fa/prs | 11.2 / 13.8 / 15.3h ✅ | unchanged ✅ |
| Teaching ≥10h — nl/fa/prs→en | **9.50h ❌** | **10.26h ✅** |
| Practice ≥10h — all 6 | ✅ | ✅ |
| Launch-path code blockers | 5 | **0** |
| **Working checkpoints** | 253 units (45.3%) | **304 units (52.7%)** ⚠️ |

Checkpoint coverage measured by calling the real `generate_checkpoint()`
on all 577 launch units against the synced DB:

| direction | ok / total | % |
|---|---|---|
| en-fa | 51 / 86 | 59.3 |
| en-nl | 54 / 88 | 61.4 |
| en-prs | 56 / 84 | 66.7 |
| fa-en | 48 / 106 | 45.3 |
| nl-en | 48 / 106 | 45.3 |
| prs-en | 47 / 107 | 43.9 |
| **total** | **304 / 577** | **52.7** |

**All 273 remaining failures have the same single cause: no practice pack
authored for that unit.** Not code, not lexemes — both are now solved.

---

## What shipped (19 commits)

**Code / correctness**
- `5daf7ca8` **grading: ZWNJ + harakat**. fa grades strict (no typo
  tolerance), and `_normalize()` only casefolded — so 296 of 912 en-fa
  free-text exercises (32%) required an invisible character to match, and
  **49 `speak_response` items were literally unpassable** (STT never emits
  U+200C). Now stripped/flexibly matched, landing on `correct` not
  `almost`, ahead of every strictness branch. Script confusion (ي/ی, ك/ک…)
  still never forgiven and in fact hardened.
- `4f3f44eb` **auth: 4 guest-account data-loss paths**. Guest passwords are
  generated and never shown, so each was total unrecoverable loss: a
  non-401 `/auth/me` failure bounced a signed-in user to /login (→ new
  guest account, orphaning the real one); `client.ts` cleared a live
  session when refresh was merely *unavailable*; `getFile` 401'd straight
  to logout with no refresh; guest logout had no confirmation.
- `d9de86a1` **6 lying/dead screens** + i18n gaps. Worst: HomePage rendered
  "0 XP, 0 streak, nothing due" on a dead backend — a plausible lie about
  the user's own progress.
- `3c512676` **seed: demo courses no longer shipped on deploy** (they were
  live, shadowing real fa/prs courses; for prs→en the Latin-titled stub
  sorted ABOVE the real course). Cleanup SQL written, dry-run verified,
  **NOT YET RUN** — see "Open items".
- `7eb01316` **compiler: 3 backend constraints now hard errors**
  (teaching `kind`, exercise `type`, title/content_key length).
- `2ada3697` **checkpoint scoping** + two pre-existing latency bugs
  (one unit took 289s and never finished; now 0.3s).
- `75882bfe` **the sync bug** — see below.

**Content**
- `e5a56486` + `b81dfdd0` **prs-en Dari repair**: the lane was authored in
  Iranian Persian, partly copy-identical to fa-en (944 byte-identical
  strings), worst in A1 01–02 — the first two units a Dari learner sees.
  ~1,820 values re-registered across 45 files. Detector: 129 findings → **0**.
- `abcee77b` **lexemes +7,030 specs across 137 units** — the real
  checkpoint bottleneck. All three X→en directions were 100% blocked
  because the shared English corpus's classification stopped at 48 units.
- `885f3061` / `c6d7769b` / `b0053f55` **45 practice packs, 620 templates**.
- `5c45c90e` **6 new English A2 units** — clears the teaching gate for
  three directions at once (9.50 → 10.26h).
- `f466d760` **prs feedback widget was in Pashto**, not Dari — wrong
  language on every page.

---

## The sync bug (most important operational find)

`scripts/sync_dev_db.sh` used an **unquoted `$PY`**, which embeds the repo
root. The path contains a space → the command split → **every course failed
to compile and the content import was a complete no-op.**

It printed `COMPILE FAILED for en-fa — SKIPPED (fix its validation errors
separately)` per course, which reads like a content defect and is nothing of
the kind. Meanwhile the lexeme backfills (docker, quoted) DID run — so the
DB looked alive while content and templates stayed stale.

Only caught because 45 new packs didn't move the template count. **Anyone
measuring against the dev DB before this fix was measuring stale data.**

Same root cause fixed in 15 hardcoded `/Users/raminazizi/dev/LingoSquared`
references across the runbook and CLAUDE.md files → now a quoted
`$LINGO_REPO`, defined at the top of `docs/PRE_DEPLOY_RUNBOOK.md`. **That
old directory still exists** but holds only `.claude/worktrees` — a deploy
following the old runbook would have failed, and the frontend step's
`rsync --delete` pointed at a source not containing the site.

`sync_dev_db.sh` now takes `--content-only` / `--lexemes-only` /
`--practice-only` / `--skip-*` so an interrupted sync can be resumed
without redoing the ~25-minute content import.

---

## Next board (priority order)

1. **Live browser verification.** Nothing here has been played. Use the
   vite dev server (`cd frontend && npm run dev`), fresh test account,
   en-nl and en-fa. Play a lesson, a checkpoint, and practice. This is
   where this project's real bugs surface.
2. **Practice packs for the remaining 273 units** — the only thing between
   here and the checkpoint gate. **Highest leverage: the 3 X→en directions
   (~160 packs) all share one English corpus**, so one push lifts three
   directions from ~45% to ~85%+. Follow `docs/content/PRACTICE_PACK_RECIPE.md`
   (corrected this session — see below).
3. **Fresh-context review backlog.** ~150 unreviewed files, INCLUDING the
   48 Dari files repaired this session. I set those to
   `status: unreviewed` / `required_next_reviewer: fresh_context` because
   they still claimed `reviewed` with notes asserting things the repair
   disproved ("Afghan Dari register consistent") — they would have passed a
   ship gate as already-reviewed. This is launch-gate content on Full
   review tier.
4. **Run `backend/scripts/remove_demo_courses.sql`** on dev and live. Dry-run
   verified (4 matched, 165 real courses untouched); committing takes a
   deliberate `ROLLBACK;`→`COMMIT;` edit. Needs Ramin for the live DB.
5. **`ADMIN_EMAILS` on live is still `admin@example.com`** — must become
   Ramin's real address before any external beta invite. Standing item.

---

## Traps a successor will otherwise re-hit

- **`docs/content/PRACTICE_PACK_RECIPE.md` was WRONG about case
  sensitivity** and is now corrected. It claimed practice grading is
  case-sensitive; `router.py:2062-2070` never passes `case_sensitive`, so
  practice answers ARE casefolded. The old rule needlessly banned
  capitalized lexemes. (Lowercase citation forms are still preferred — for
  DATA QUALITY, not grading.) Also fixed: both diagnostic snippets matched
  across CEFR levels and silently inflated lexeme pools.
- **`_practice_content_integrity_check.py` and
  `_fill_in_blank_ambiguity_check.py` glob `a*_unit*.yaml`** — so the 28+
  B1 packs in the corpus have NEVER been checked, and an empty grep on a
  B1 pack proves nothing. Real tooling bug, not fixed.
- **`check_dari_register.py` is not sufficient acceptance on its own.** Its
  majority-Latin suppression hides ~29% of the defect in X→en lanes (where
  a mostly-English string is the normal shape), and `COPULA_MIN=5` with
  `iranian > dari` let a file with 15 formal copulas report clean. Batches
  found real defects it missed. Uncovered: bare subjunctives, 3pl `-ند`,
  `دارد`, singular `واژه`, `طبق`.
- **One flaky backend test**:
  `test_feedback_attachments.py::test_feedback_attachment_admin_retrieval_
  requires_admin_and_streams_bytes` failed once in a full deterministic run,
  passed on re-run and in isolation. Process-wide rate-limiter state
  (register is capped 5/hr per IP). Pre-existing infrastructure issue, not
  a regression — but it means "the suite is green" needs a re-run to trust.

---

## Content defects found but deliberately NOT fixed

These are real and logged so they aren't lost:

- **5 en-nl B1 lexemes have wrong glosses that display as the CORRECT
  ANSWER**: `was`→"do the dishes" (means *was*), `waar`→"where" (means
  *true*), `vroeg`→"early" (means *asked*), `rust`→"rest" (is a noun),
  `regel`→"arrange" (teaches *de regel* = the rule).
- **A Pashto word (`پونډ`) sits in `prs-en/a1_unit08`'s GRADED values.**
- **`prs-en/a2_unit27` glosses "monthly fee" as `معاش`** — *salary*.
- **`realizations/prs/a1_unit36` teaches Iranian `هستم` as vocabulary**
  while the lane uses Dari `استم` 571× elsewhere. Deliberately left: it
  spans `introduced_tokens` + `target.text` + `tested_text` + a graded
  `pairs.left` + the en-prs overlay mirror. Needs one coordinated task.
- **ru B1 registers grammatical metalanguage as learner vocabulary**, so 10
  exercises test formula strings rather than usage.
- **46 fa B1 lexemes embed their own Persian token in the English gloss**,
  so the correct MC option visibly contains the displayed token.
- **en-fa backfill emits an English `source_gloss` pseudo-lexeme per gloss
  word** (`the`, `a`, `lot`) — 44–70% of each unit's "lexemes" are English
  tokens no template can host, and they pollute the learner's SRS.
- **`prs.json`: `login.submit` / `register.login_link` are still Iranian
  register** (`وارد شوید`, should be `وارد شوین`).
- **A latent duplicate-key 500**: `checkpoint_result()` computes
  `existing_lexeme_ids` only over `all_unit_lexeme_ids` while inserting SRS
  rows for every `covered_lexeme_id`. Not reachable today (prior-unit
  targets are stored NULL) but it's live if target attribution widens.

---

## How this session was run (worked well, reuse it)

Fan-out of fresh (non-fork) general-purpose agents, ~20 concurrent (the
cap; raising it needs `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`). Every
dispatch inlined: never `git add`/`commit`/`stash`; touch ONLY your
assigned files; don't run `npm run build` or the full pytest suite
(coordinator verifies centrally); don't write to the shared dev DB.
Coordinator committed everything with explicit pathspecs. Zero collisions
across ~35 agents.

Shared rule-set files beat repeating rules in N prompts —
`docs/content/DARI_REGISTER_REPAIR.md` and `PRACTICE_PACK_RECIPE.md` were
written once and read by 10+ agents.
