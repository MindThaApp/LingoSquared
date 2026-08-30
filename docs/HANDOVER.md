# HANDOVER — read this first, then act

> **UPDATE 2026-08-30 — for now, work directly IN the iCloud copy; do NOT migrate out.**
> Ramin retired his other Mac and synced the latest project (including an
> uncommitted Dutch C1 tier that exists nowhere else) to iCloud. The canonical
> working copy is now this repo at
> `~/Library/Mobile Documents/com~apple~CloudDocs/dev/LingoSquared`.
> **Skip PART 1 / Step 2 below — do NOT re-clone to `~/dev`.** The `~/dev` copies
> were deleted 2026-08-30 to end the two-copies confusion.
> The git-in-iCloud corruption risk documented in Step 2 is a known, re-accepted
> trade-off: **push to `origin` (GitHub, private) often** — that push is the real
> off-machine backup and the recovery point if iCloud ever mangles `.git`.
> If files look "missing" right after launching, iCloud may still be downloading:
> wait until `find . -name '*.icloud' | wc -l` returns `0` before concluding
> anything is lost. (Everything below this banner is retained for future machines.)

**You are the Claude session taking over LingoSquared on Ramin's new primary
Mac.** This file is written to YOU, not to Ramin. It is self-contained: do
not ask him what to do next, and do not make him relay instructions. Work
through Part 1 in order, then pick up Part 2.

Written 2026-07-22, at the tip of `master` on
`origin/master` (`github.com/ramin-azizi/LingoSquared`, **private**).

**Read root `CLAUDE.md` before any work.** It always loads and it overrides
this file wherever they disagree.

Almost everything here you do autonomously. The only things you must ask
Ramin for are two files in step 4b — and even those can be deferred.

---

# PART 1 — Get this machine working (do these in order)

## Step 1. Work out where you are

```bash
pwd && git log --oneline -1 2>/dev/null
```

- **Path contains `Mobile Documents`** → you are in the iCloud copy. Per the
  2026-08-30 banner above, THIS is now the canonical copy — work here and do NOT
  run step 2's migration. Skip to step 3.
- **Path is `~/dev/LingoSquared`** → historical (pre-2026-08-30) location; those
  `~/dev` copies were removed. Switch to the iCloud copy above.
- **No repo at all** → iCloud may still be downloading (check
  `find . -name '*.icloud' | wc -l`); only if the repo is genuinely absent,
  clone from `origin` into the iCloud path.

## Step 2. Migrate out of iCloud (clone — never copy the folder)

```bash
mkdir -p ~/dev
git clone https://github.com/ramin-azizi/LingoSquared.git ~/dev/LingoSquared
cd ~/dev/LingoSquared && git log --oneline -1   # newest commit dated 2026-07-22 or later
```

**Why cloning, not copying** — hosting this git repo in iCloud caused four
real failures, and copying the folder would carry them across:

1. **2,204 committed files appeared deleted.** iCloud never materialized
   them and left ZERO `.icloud` placeholders, so `git status` showed a wall
   of `D` entries that looked exactly like data loss.
2. **`.git/index 2`** — iCloud made a *conflict copy of the binary git
   index*. `.git/index`, `refs` and `objects` are state git rewrites
   constantly; a conflict there means lost commits or an unopenable repo.
3. **`.content-venv` broke** — a virtualenv hardcodes absolute interpreter
   paths, so one shared across machines is broken by design.
4. **The space in `Mobile Documents` silently turned the entire dev-DB sync
   into a no-op** (details in Part 3). `~/dev/LingoSquared` has no space,
   which retires that whole bug class and matches the path the deploy
   runbook originally assumed.

If the old copy has anything unpushed, rescue it first — both of these must
come back empty before you abandon it:

```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/dev/LingoSquared 2>/dev/null \
  && git status --porcelain && git log --oneline origin/master..HEAD
```

## Step 3. Install prerequisites

```bash
xcode-select --install 2>/dev/null      # no-op if present
brew install colima docker docker-compose node
```

What worked on the previous machine (not hard requirements): Python
**3.9.6** from `/usr/bin/python3` (no Homebrew python — the content compiler
runs fine on 3.9), Node **26**, Postgres 16 + nginx via Docker.

## Step 4. Secrets — get most of them yourself, ask for two

A clone brings all code and content but **no secrets** — they are gitignored.
Most of them, however, you can get yourself.

### 4a. Copy these from the old iCloud folder — NO transfer needed

`backend/.env` and `frontend/.env` live INSIDE the repo, which was in iCloud,
so **this Mac already has them.** Just copy them into the new location:

```bash
OLD=~/Library/Mobile\ Documents/com~apple~CloudDocs/dev/LingoSquared
cp "$OLD/backend/.env"  ~/dev/LingoSquared/backend/.env
cp "$OLD/frontend/.env" ~/dev/LingoSquared/frontend/.env
```

If they are missing or zero-length, iCloud has not finished materializing —
wait for it, then retry. Do NOT ask Ramin for them until you have tried this.

| File | Contains |
|---|---|
| `backend/.env` | DB URL + password, JWT secret, `ADMIN_EMAILS`, `CORS_ORIGINS`, Google Cloud TTS service-account JSON |
| `frontend/.env` | `VITE_API_BASE_URL` |

### 4b. ASK RAMIN for these two — they are NOT in iCloud

They sit at the home-directory root, which iCloud does not sync (only
`~/Desktop` and `~/Documents` are symlinked into iCloud Drive).

| File | Contains |
|---|---|
| `~/.lingo_admin_pw` | admin password for `sync_dev_db.sh` non-interactive mode |
| `~/.ssh/id_ed25519` (+ `.pub`) | SSH key for the live server `ramin@192.168.4.4` |

Ask him to move them by **AirDrop or `scp`**. Do not suggest routing an SSH
private key through iCloud Desktop, a gist, or a chat message.

**You can defer both.** `~/.lingo_admin_pw` only gates the non-interactive
dev-DB sync — `sync_dev_db.sh` will prompt for the password interactively
without it. The SSH key is only needed to reach the live server, which is
not required for any local work. So do steps 5 and 6 first and unblock
yourself.

**Optional QA/test variants** — copy only if you need those workflows; the
core dev loop does not:

`backend/.env.e2e` · `backend/.env.qa` · `backend/.env.faqa` ·
`backend/.env.fib` · `backend/.env.play` · `frontend/.env.e2e.local` ·
`frontend/.env.faqa` · `frontend/.env.backup-live-server`

**Do NOT hand-carry these — they are tracked and arrive with the clone:**
`backend/.env.example`, `frontend/.env.example`,
`frontend/.env.production.lan`, `frontend/.env.qa`.

Verify the untracked set yourself rather than trusting this list — it is
generated, not curated:

```bash
find . -name ".env*" -not -path "./node_modules/*" -not -path "*/node_modules/*" \
     -not -path "./.git/*" | sort | while read f; do f="${f#./}"
  git ls-files --error-unmatch "$f" >/dev/null 2>&1 \
    || echo "MUST hand-carry: $f"; done
```

Then:

```bash
chmod 600 ~/.lingo_admin_pw ~/.ssh/id_ed25519 ~/dev/LingoSquared/backend/.env
chmod 700 ~/.ssh
```

`backend/.env.example` documents every variable if regenerating is easier
than copying. Regenerating the JWT secret invalidates all existing sessions
(fine for dev; hashed user passwords are unaffected).

**Never write any of these values into the repo, a scratch file, or a
message.** Re-derive them inline in each command that needs them.

Not in git and NOT worth copying (regenerable): `.content-venv/`,
`node_modules/`, `backend/media_assets/*.mp3`, `backend/feedback_uploads/`,
`backend/backups/`.

## Step 5. Build the environment

```bash
cd ~/dev/LingoSquared

/usr/bin/python3 -m venv .content-venv
.content-venv/bin/pip install pyyaml

npm install          # MUST be at the repo root — npm workspaces.
                     # Running it only in frontend/ silently resolves
                     # @lingo/shared UP to a stale copy, so builds
                     # "verify" against the wrong code.

colima start
cd backend && docker compose up -d && cd ..
```

## Step 6. Verify — do not start feature work until this passes

```bash
cd ~/dev/LingoSquared
docker ps --format '{{.Names}}\t{{.Status}}'
curl -s -o /dev/null -w 'api:%{http_code}\n' http://localhost:8020/health   # expect 200
./scripts/verify.sh          # content compiler + backend pytest + frontend build
```

Must end `content: pass / backend: pass / frontend: pass`.

**Known-acceptable noise — do not "fix" these:**
- Many compiler **warnings** (matching_pairs pool-size, missing
  `example_gloss` on schema-1.0 overlays). **Zero errors** is the bar.
- `test_feedback_attachments.py::test_feedback_attachment_admin_retrieval_
  requires_admin_and_streams_bytes` is **flaky** — fails occasionally in a
  full run, passes in isolation (process-wide rate-limiter state; register
  is capped 5/hr per IP). Re-run before believing a red suite.
- `http://localhost:8011` returns **403** because `backend/web_dist` is
  empty. That is the *deploy* copy, not the dev path. Use the vite dev
  server.

## Step 7. Populate the dev DB (~25 min for the content phase)

```bash
LINGO_ADMIN_EMAIL=admin@example.com \
LINGO_ADMIN_PASSWORD_FILE="$HOME/.lingo_admin_pw" \
  ./scripts/sync_dev_db.sh http://localhost:8020
```

Order is content → lexemes → practice and it matters. Resume a partial run
with `--practice-only` / `--lexemes-only` / `--skip-content`.

**Then CONFIRM it actually imported** — do not trust the exit code:

```bash
cd backend && docker compose exec -T db psql -U lingosquared -d lingosquared -t \
  -c "select 'courses='||count(*) from courses
      union all select 'lexemes='||count(*) from lexemes
      union all select 'templates='||count(*) from practice_templates;"
```

Expect roughly **53 courses, ~18.9k lexemes, ~3.6k templates**. Zero
`COMPILE FAILED` lines in the output. A sync can print per-course
`COMPILE FAILED … fix its validation errors separately` and be a pure
path/quoting bug rather than a content problem — that exact thing silently
wiped an entire import (Part 3).

## Step 8. Retire the old iCloud copy — ONLY after step 6 passes

Ramin keeps the old Mac for side projects, so the old copy must be made
impossible to open by accident; otherwise two machines can write to one repo
and you are back to failure #2.

```bash
OLD=~/Library/Mobile\ Documents/com~apple~CloudDocs/dev/LingoSquared
cd "$OLD" && git status --porcelain && git log --oneline origin/master..HEAD
# BOTH must be empty. Then:
echo "RETIRED $(date +%F). Canonical repo is ~/dev/LingoSquared.
Do NOT edit or commit here. Read-only safety net; delete after ~1 week." \
  > "$OLD/RETIRED_DO_NOT_USE.txt"
```

Tell Ramin to delete it after about a week. Do not delete it yourself.

---

# PART 2 — What to actually work on

## Do this first: live browser verification

**Nothing from the 2026-07-22 session has ever been played in a browser.**
It is all verified by compiler, test suite and build only. Root `CLAUDE.md`
is explicit that reading a diff is not verification, and every one of this
project's worst bugs — six unregistered exercise types, a permanently
disabled Respond button, distractors drawn from the whole course, a deleted
logout button — was found ONLY by playing a lesson.

```bash
cd ~/dev/LingoSquared/frontend && npm run dev
```

Fresh test account. Play **en-nl and en-fa**: a full lesson, a unit
checkpoint, and Endless Practice. Specifically exercise what changed:

- **Persian typing** — the ZWNJ/harakat grading fix. Type `میکنم` where the
  answer is `می‌کنم`; it must grade **correct**, not "almost".
- **Guest logout** — must now show a confirmation warning about
  unrecoverable progress.
- **Backend-unreachable state** — stop the api container mid-session; you
  must get a "can't reach the server" screen with Retry, NOT the login page.
- **A unit checkpoint** on a unit that has one (52.7% do).
- **matching_pairs** — its Check button was hardcoded English; confirm it is
  translated.

## Then: the only open publish-gate item

| Gate item | Status |
|---|---|
| Teaching ≥10h, all 6 directions | ✅ |
| Practice ≥10h, all 6 | ✅ |
| Launch-path code blockers | ✅ 0 |
| **Working checkpoints** | ⚠️ **304/577 (52.7%)** |

Measured by calling the real `generate_checkpoint()` on every launch unit:
en-fa 51/86 · en-nl 54/88 · en-prs 56/84 · fa-en 48/106 · nl-en 48/106 ·
prs-en 47/107.

**All 273 failures have one cause: no practice pack authored for that
unit.** Code and lexemes are both solved. Follow
`docs/content/PRACTICE_PACK_RECIPE.md` (corrected 2026-07-22).

**Highest leverage: the three X→en directions (~160 packs) all consume one
shared English corpus**, so a single push lifts nl-en, fa-en and prs-en
together from ~45% to ~85%+.

## Remaining board, in priority order

1. Live browser verification (above).
2. Practice packs — X→en first, then en→X.
3. **Fresh-context review backlog: ~150 unreviewed files**, including 48
   Dari files repaired on 2026-07-22. Those were set to
   `status: unreviewed` / `required_next_reviewer: fresh_context` because
   they still claimed `reviewed` with notes asserting things the repair
   disproved ("Afghan Dari register consistent") — they would have passed a
   ship gate as already-reviewed. Launch-gate content, Full review tier.
4. **Run `backend/scripts/remove_demo_courses.sql`** on dev and live. Dry
   run verified (4 matched, 165 real courses untouched). Committing takes a
   deliberate `ROLLBACK;`→`COMMIT;` edit. **Live DB needs Ramin present.**
5. **`ADMIN_EMAILS` on live is still `admin@example.com`** — must become
   Ramin's real address before any external beta invite. `register()` grants
   admin to whoever first registers under a listed email and there is no
   email verification.

---

# PART 3 — Reference: what happened on 2026-07-22

20 commits, all pushed. Summary of what changed and why it matters.

## Code / correctness

- `5daf7ca8` **grading: ZWNJ + harakat.** Persian grades strict (no typo
  tolerance) and `_normalize()` only casefolded — so 296 of 912 en-fa
  free-text exercises (32%) required an invisible character to match, and
  **49 `speak_response` items were literally unpassable** (STT never emits
  U+200C). Now normalized ahead of every strictness branch, landing on
  `correct` not `almost`. Script confusion (ي/ی, ك/ک…) still never forgiven,
  and in fact hardened.
- `4f3f44eb` **auth: four guest-account data-loss paths.** Guest passwords
  are generated and never shown, so each was total unrecoverable loss.
- `d9de86a1` **six lying or dead screens** + i18n gaps. Worst: HomePage
  rendered "0 XP, 0 streak, nothing due" on a dead backend.
- `3c512676` **demo courses no longer seeded on deploy** — they were live,
  shadowing the real fa/prs courses; for prs→en the Latin-titled stub sorted
  ABOVE the real course.
- `7eb01316` **compiler: three backend constraints now hard errors**
  (teaching `kind`, exercise `type`, title/content_key length).
- `2ada3697` **checkpoint scoping** + two pre-existing latency bugs (one
  unit took 289s and never finished; now 0.3s).

## Content

- `e5a56486` + `b81dfdd0` **prs-en Dari repair** — the lane was authored in
  Iranian Persian, partly copy-identical to fa-en (944 byte-identical
  strings), worst in A1 01–02, the first two units a Dari learner sees.
  ~1,820 values re-registered across 45 files. Detector: 129 findings → 0.
- `abcee77b` **lexemes +7,030 specs across 137 units** — the real checkpoint
  bottleneck. All three X→en directions were 100% blocked because the shared
  English corpus's classification stopped at 48 units.
- `885f3061` / `c6d7769b` / `b0053f55` **45 practice packs, 620 templates**.
- `5c45c90e` **6 new English A2 units** — cleared the teaching gate for
  three directions at once (9.50h → 10.26h).
- `f466d760` **the prs feedback widget was written in Pashto**, not Dari.

## The sync bug (most important operational lesson)

`scripts/sync_dev_db.sh` used an **unquoted `$PY`**, which embeds the repo
root. The iCloud path contains a space → the command split → **every course
failed to compile and the content import was a complete no-op.**

It printed `COMPILE FAILED for en-fa — SKIPPED (fix its validation errors
separately)` per course, which reads like a content defect and is nothing of
the kind. The lexeme backfills (docker, quoted) DID run, so the DB looked
alive while content and templates stayed stale. Caught only because 45 new
packs didn't move the template count.

**Lesson: when a measurement against the dev DB looks wrong, verify the sync
actually imported before believing the number.**

15 hardcoded `/Users/raminazizi/dev/LingoSquared` references were repointed
to a quoted `$LINGO_REPO`. On the old Mac that directory still existed but
held only `.claude/worktrees`, so a deploy following the runbook would have
failed and the frontend step's `rsync --delete` pointed at a source not
containing the site. **On the new Mac that path is now the real repo, so
those references are correct again.**

## Traps you will otherwise re-hit

- **`PRACTICE_PACK_RECIPE.md` was WRONG about case sensitivity** and is now
  corrected. Practice/checkpoint grading **casefolds** —
  `router.py:2062-2070` never passes `case_sensitive`. The old rule
  needlessly banned capitalized lexemes. Lowercase citation forms are still
  preferred, for data quality, not grading.
- **`_practice_content_integrity_check.py` and
  `_fill_in_blank_ambiguity_check.py` glob `a*_unit*.yaml`** — so the 28+ B1
  packs in the corpus have NEVER been checked, and an empty grep on a B1
  pack proves nothing. Real tooling bug, unfixed.
- **`check_dari_register.py` is not sufficient acceptance on its own.** Its
  majority-Latin suppression hides ~29% of the defect in X→en lanes (where a
  mostly-English string is the normal shape), and `COPULA_MIN=5` with
  `iranian > dari` let a file with 15 formal copulas report clean.
  Uncovered: bare subjunctives, 3pl `-ند`, `دارد`, singular `واژه`, `طبق`.
- **zsh does not word-split unquoted variables.** The compiler's
  `--realization $REALS --overlay $OVERLAYS` pattern REQUIRES splitting, so
  manifest-chain commands must run under `bash -c`. Under zsh they fail with
  a misleading `[Errno 63] File name too long`.
- `docker compose restart` does **not** reload `.env` — only `up -d` /
  `--force-recreate` does.
- A backend code change needs `docker compose up -d --force-recreate api` —
  the bind mount syncs source but uvicorn has no `--reload`.
- **Never use `docker compose --env-file` for tests** — it only affects
  compose variable substitution, not container env, and once ran the suite
  against the live database. Use the isolated dropdb/createdb recipe in
  `backend/CLAUDE.md`.
- Inside the container use **`python -m pytest`**, not bare `pytest`.
- Frontend verification is the **FULL `npm run build`**, never
  `tsc --noEmit` — the full build has twice caught errors noEmit missed.

## Known content defects — found, logged, deliberately NOT fixed

- **5 en-nl B1 lexemes have wrong glosses that display as the CORRECT
  ANSWER**: `was`→"do the dishes" (means *was*), `waar`→"where" (means
  *true*), `vroeg`→"early" (means *asked*), `rust`→"rest" (is a noun),
  `regel`→"arrange" (teaches *de regel* = the rule).
- **A Pashto word (`پونډ`) sits in `prs-en/a1_unit08`'s GRADED values.**
- **`prs-en/a2_unit27` glosses "monthly fee" as `معاش`** — *salary*.
- **`realizations/prs/a1_unit36` teaches Iranian `هستم` as vocabulary**
  while the lane uses Dari `استم` 571× elsewhere. Left deliberately: it
  spans `introduced_tokens`, `target.text`, `tested_text`, a graded
  `pairs.left`, and the en-prs overlay mirror. Needs one coordinated task.
- **ru B1 registers grammatical metalanguage as learner vocabulary**, so 10
  exercises test formula strings rather than usage.
- **46 fa B1 lexemes embed their own Persian token in the English gloss**,
  so the correct option visibly contains the displayed token.
- **The en-fa backfill emits an English `source_gloss` pseudo-lexeme per
  gloss word** (`the`, `a`, `lot`) — 44–70% of each unit's "lexemes" are
  English tokens no template can host, and they pollute the learner's SRS.
- **`prs.json`: `login.submit` / `register.login_link` are still Iranian
  register** (`وارد شوید`, should be `وارد شوین`).
- **Latent duplicate-key 500**: `checkpoint_result()` computes
  `existing_lexeme_ids` only over `all_unit_lexeme_ids` while inserting SRS
  rows for every `covered_lexeme_id`. Unreachable today (prior-unit targets
  are stored NULL) but live if target attribution ever widens.

## How the 2026-07-22 session was run (reuse this)

Fan-out of fresh (non-fork) general-purpose agents, ~20 concurrent — the cap;
raising it needs `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`. Every dispatch
inlined the same rules: never `git add`/`commit`/`stash`; touch ONLY your
assigned files; do not run `npm run build` or the full pytest suite (the
coordinator verifies centrally); do not write to the shared dev DB. The
coordinator committed everything with explicit pathspecs. **Zero collisions
across ~35 agents.**

Shared rule-set files beat repeating rules in N prompts —
`docs/content/DARI_REGISTER_REPAIR.md` and `PRACTICE_PACK_RECIPE.md` were
each written once and read by 10+ agents.
