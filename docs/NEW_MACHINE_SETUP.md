# Setting up LingoSquared on a new primary Mac

Written 2026-07-22, when the repo moved off the iCloud-hosted machine.
Follow this top to bottom. **Read root `CLAUDE.md` before doing any work** —
this file is setup only.

If you are the Claude session on the new Mac: do the steps in order, run the
verification block, and do NOT start feature work until it passes.

---

## 0. Why this file exists (the failure modes it prevents)

The repo previously lived at
`~/Library/Mobile Documents/com~apple~CloudDocs/dev/LingoSquared` — inside
iCloud Drive. That caused four real, costly failures:

1. **2,204 committed files appeared deleted.** iCloud never materialized
   them, and left ZERO `.icloud` placeholders, so `git status` showed a wall
   of `D` entries that looked like genuine data loss.
2. **`.git/index 2`** — iCloud made a *conflict copy of the binary git
   index*. `.git/index`, `refs`, and `objects` are state git rewrites
   constantly; a conflict there means lost commits or an unopenable repo.
3. **`.content-venv` broke** — a virtualenv hardcodes absolute interpreter
   paths, so one shared across machines is broken by design.
4. **The space in `Mobile Documents` silently made the entire dev-DB sync a
   no-op** — an unquoted `$PY` split into two arguments, every course
   "failed to compile", and the content import did nothing while printing
   plausible per-course error messages.

**The new location has no space in the path and is not synced by anything
except git.** Keep it that way.

---

## 1. Prerequisites

```bash
xcode-select --install 2>/dev/null   # git, clang; no-op if present
brew install colima docker docker-compose node
```

Version notes from the last machine (not requirements, just what worked):
Python **3.9.6** from `/usr/bin/python3` (no Homebrew python — the compiler
runs fine on 3.9), Node **26**, Postgres 16 + nginx via Docker.

---

## 2. Clone from GitHub — do NOT copy the folder from iCloud

```bash
mkdir -p ~/dev
git clone https://github.com/ramin-azizi/LingoSquared.git ~/dev/LingoSquared
cd ~/dev/LingoSquared
git log --oneline -1        # expect c158b1a3 or later
```

Cloning is faster than waiting for iCloud to materialize the tree, it is
deterministic, and it cannot reproduce failure #1 above. The repo is a
**private** GitHub repo (`ramin-azizi/LingoSquared`).

`~/dev/LingoSquared` is deliberate: it is the path the deploy runbook
originally assumed, so those references are correct again.

---

## 3. Secrets — these are NOT in git and must be moved by hand

A clone gives you all code and content but **none of these**. The app will
not start without them.

| File | Contains |
|---|---|
| `backend/.env` | DB URL + password, JWT secret, `ADMIN_EMAILS`, `CORS_ORIGINS`, Google Cloud TTS service-account JSON |
| `frontend/.env` | `VITE_API_BASE_URL` etc. |
| `frontend/.env.faqa` | QA-variant frontend config |
| `~/.lingo_admin_pw` | admin password for `sync_dev_db.sh` non-interactive mode (chmod 600) |
| `~/.ssh/id_ed25519` | SSH key for the live server `ramin@192.168.4.4` |

**Move them directly machine-to-machine** — AirDrop, `scp`, or a password
manager. Do **not** put them in the repo, a gist, a shared folder, or a chat
message. `backend/.env` holds a live service-account private key.

After copying:

```bash
chmod 600 ~/.lingo_admin_pw ~/.ssh/id_ed25519
chmod 600 ~/dev/LingoSquared/backend/.env
```

`backend/.env.example` documents every variable if you would rather
regenerate than copy. If you regenerate the JWT secret, **every existing
session and refresh token is invalidated** — fine for dev, and note the dev
DB's user accounts still work (passwords are hashed separately).

Also not in git (regenerable, don't bother copying):
`.content-venv/`, `node_modules/`, `backend/media_assets/*.mp3`,
`backend/feedback_uploads/`, `backend/backups/`.

---

## 4. Build the environment

```bash
cd ~/dev/LingoSquared

# Python toolchain for the content compiler
/usr/bin/python3 -m venv .content-venv
.content-venv/bin/pip install pyyaml

# JS workspace — MUST be run at the repo root (npm workspaces).
# Running it only inside frontend/ silently resolves @lingo/shared UP to a
# stale copy and your builds "verify" against the wrong code.
npm install

# Docker stack
colima start
cd backend && docker compose up -d && cd ..
```

---

## 5. Verify before doing anything else

```bash
cd ~/dev/LingoSquared

# 1. containers healthy
docker ps --format '{{.Names}}\t{{.Status}}'
curl -s -o /dev/null -w 'api:%{http_code}\n' http://localhost:8020/health   # expect 200

# 2. the full bar
./scripts/verify.sh          # content compiler + backend pytest + frontend build
```

`verify.sh` must end with `content: pass / backend: pass / frontend: pass`.

Known-acceptable noise:
- Many compiler **warnings** (matching_pairs pool-size, missing
  `example_gloss` on schema-1.0 overlays). **Zero errors** is the bar.
- `test_feedback_attachments.py::test_feedback_attachment_admin_retrieval_
  requires_admin_and_streams_bytes` is **flaky** — it fails occasionally in
  a full run and passes in isolation (process-wide rate-limiter state,
  register is capped 5/hr per IP). Re-run before believing a red suite.
- `backend/web_dist` is empty, so `http://localhost:8011` returns 403. That
  is the *deploy* copy, not the dev path. Use the vite dev server.

Then populate the dev DB (~25 min for the content phase):

```bash
LINGO_ADMIN_EMAIL=admin@example.com \
LINGO_ADMIN_PASSWORD_FILE="$HOME/.lingo_admin_pw" \
  ./scripts/sync_dev_db.sh http://localhost:8020
```

Order is content → lexemes → practice and it matters. Resume a partial run
with `--practice-only` / `--lexemes-only` / `--skip-content`.

**Sanity-check that it actually imported.** A sync can print per-course
`COMPILE FAILED … fix its validation errors separately` and still be a pure
path/quoting bug rather than a content problem — that exact thing wiped a
whole import silently. Expect zero `COMPILE FAILED` lines, and confirm the
counts move:

```bash
cd backend && docker compose exec -T db psql -U lingosquared -d lingosquared -t \
  -c "select 'courses='||count(*) from courses
      union all select 'lexemes='||count(*) from lexemes
      union all select 'templates='||count(*) from practice_templates;"
```

Roughly expected: 53 courses, ~18.9k lexemes, ~3.6k templates.

---

## 6. Retire the iCloud copy (do this once the new Mac is verified)

The old Mac stays in use for side projects, so the old copy must be made
**impossible to open by accident** — otherwise two machines can write to one
repo again and you are back to failure #2.

On the OLD Mac, only after the new Mac passes §5:

```bash
OLD=~/Library/Mobile\ Documents/com~apple~CloudDocs/dev/LingoSquared

# 1. prove nothing is unpushed — BOTH must come back empty
cd "$OLD" && git status --porcelain && git log --oneline origin/master..HEAD

# 2. mark it so nobody (human or agent) mistakes it for the live repo
echo "RETIRED $(date +%F). Canonical repo is ~/dev/LingoSquared on the new Mac.
Do NOT edit or commit here. Kept read-only as a temporary safety net." \
  > "$OLD/RETIRED_DO_NOT_USE.txt"
```

Keep it for ~1 week as a safety net, then delete it. Do **not** delete it
before the new Mac has run §5 successfully.

Optional belt-and-braces while it still exists: `chmod -R a-w "$OLD"`.

---

## 7. Rules for the occasional-use (old) Mac

- **Never open `~/dev/LingoSquared`-equivalent work there.** The canonical
  repo is on the new Mac only.
- If you genuinely must work on LingoSquared from the old Mac, do it as a
  **fresh clone outside iCloud** (`~/dev/LingoSquared`), push before you
  stop, and pull on the other machine before resuming. Never two at once.
- Keep side projects out of iCloud too if they are git repos — same
  reasoning. iCloud duplicates what git already does, and adds failure
  modes git does not have.

---

## 8. First things to do once set up

1. **Read `docs/SESSION_HANDOFF_2026-07-22.md`** — current state, the
   prioritized next board, and the traps that will otherwise be re-hit.
2. **Read root `CLAUDE.md`** (always loads), plus the per-directory
   `CLAUDE.md` for whatever area you touch.
3. **Live browser verification is owed.** Nothing from the 2026-07-22
   session has been played in a browser — only compiler/test/build verified.
   Root `CLAUDE.md` is explicit that reading a diff is not verification, and
   this project's worst bugs were all found by actually playing a lesson.
   Start there:

```bash
cd ~/dev/LingoSquared/frontend && npm run dev
# fresh test account, play a lesson + a checkpoint + practice on en-nl and en-fa
```

---

## 9. Environment gotchas that survive the move

- **zsh does not word-split unquoted variables.** The compiler's
  `--realization $REALS --overlay $OVERLAYS` pattern REQUIRES splitting, so
  manifest-chain commands must be run under `bash -c`. Under zsh they fail
  with a misleading `[Errno 63] File name too long`.
- **`docker compose restart` does not reload `.env`** — only `up -d` or
  `--force-recreate` does.
- **A backend code change needs `docker compose up -d --force-recreate
  api`** — the bind mount syncs source but uvicorn has no `--reload`.
- **Never use `docker compose --env-file` for tests.** It only affects
  compose variable substitution, not the container env, and once ran the
  suite against the live database. Use the isolated dropdb/createdb recipe
  in `backend/CLAUDE.md`.
- **Use `python -m pytest`, not bare `pytest`**, inside the container —
  bare pytest does not put `/app` on `sys.path`.
- **Frontend verification is the FULL `npm run build`** (`tsc -b && vite
  build`), never `tsc --noEmit` — the full build has twice caught type
  errors noEmit missed.
