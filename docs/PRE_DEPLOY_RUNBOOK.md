# Pre-deploy runbook — live server (192.168.4.4)

**Read this in full before touching the live server.** This is the
consolidated checklist for the FIRST real deploy of current work to
192.168.4.4, assembled 2026-07-07 from landmines scattered across
~10 separate `docs/BUILD_LOG.md` entries (a 2026-07-07 Fable audit
flagged this scatter as the largest unaddressed risk in the repo).
`CLAUDE.md`'s "Deploying a backend change" section has the quick-
reference command skeleton; this file is the full checklist around it
— pre-flight checks, required env vars, ordered steps, and post-deploy
verification. Standing rule, unchanged: **deploys happen with Ramin
present, never unattended.**

## FIRST: set `$LINGO_REPO` (every command below depends on it)

```bash
export LINGO_REPO="$HOME/Library/Mobile Documents/com~apple~CloudDocs/dev/LingoSquared"
[ -d "$LINGO_REPO/backend" ] || { echo "WRONG PATH — stop"; }
```

**Always quote it.** The repo lives in iCloud Drive, so its path contains a
space (`Mobile Documents`). An unquoted `$LINGO_REPO` splits into two
arguments and the command silently does the wrong thing.

This bit for real on 2026-07-22: `scripts/sync_dev_db.sh` used an unquoted
`$PY` (which embeds the repo root), so **every single course failed to
compile and the dev-DB content import was a complete no-op** — while the
script printed a plausible "COMPILE FAILED … fix its validation errors
separately" for each one, which reads like a content problem and is not.
Fixed by quoting; the `shellcheck disable=SC2086` there is narrow and
applies ONLY to `$REALS`/`$OVERLAYS`, which must word-split.

These commands previously hardcoded `/Users/raminazizi/dev/LingoSquared`.
**That directory still exists but is an empty leftover** (it holds only
`.claude/worktrees`) — so a deploy run against the old paths would fail,
and the `rsync --delete` in the frontend step would be pointed at a source
that does not contain the site. Re-verify `$LINGO_REPO` if the repo ever
moves again.

## Load-bearing fact: the live server has never been deployed to

Every mention of 192.168.4.4 in `docs/BUILD_LOG.md`'s entire history
(2026-07-02 → 2026-07-07) is either the deploy recipe itself, a
read-only SSH check (`grep` on `.env`), or an explicit "was NOT
touched" / "never touched the live server" statement. No entry
describes an actual rsync/build/migrate/seed/restart cycle executed
against it. **Treat this as a from-scratch-equivalent first deploy,
not an incremental one** — don't assume any prior migration/seed state
beyond whatever was there from original box setup (Debian, Docker,
`docker-compose.yml`, an empty or near-empty Postgres). If you find
evidence during pre-flight (below) that contradicts this — e.g.
`alembic_version` already has real rows — stop and reconcile before
proceeding; don't silently pick one story.

## Pre-flight checks (BEFORE touching anything)

Run these first, in order. All are read-only — none of them modify
the live server.

1. **Check `alembic_version` on the live DB directly.**
   ```bash
   ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose exec -T db psql -U lingosquared -d lingosquared -c 'SELECT * FROM alembic_version;'"
   ```
   - If the table **doesn't exist**: this matches the dev-DB footgun
     found 2026-07-05 (dev DB's schema was created via
     `Base.metadata.create_all()` instead of a real `alembic upgrade`,
     so alembic's own version table was never created even though the
     schema itself matched migrations through 0008). **This has never
     been checked on live before — it is a genuine unknown, not an
     assumed-safe case.** If it's missing and the schema already has
     tables/columns from a prior partial setup, do NOT run `alembic
     upgrade head` blind — first inspect what tables/columns actually
     exist (`\dt` inside the same psql session) and `alembic stamp
     <the real matching revision>` before upgrading, exactly like the
     dev-DB fix. If the live DB is genuinely empty (no tables at all,
     consistent with "never deployed to"), a fresh `alembic upgrade
     head` from empty is the normal, safe path (verified repeatedly
     against isolated empty DBs this project's history — 0001's
     `create_all()` builds every table with its current shape in one
     shot, migrations 0002+ are individually guarded to no-op safely
     against an already-matching schema).
   - If the table **exists with rows**: stop and figure out why —
     this would contradict "never deployed to" and needs a real
     explanation before proceeding, not an assumption.
   - If this command fails outright because no `db` container is even
     running: that's itself informative (consistent with "never
     deployed to"). Move to step 2 to confirm, bring up just the `db`
     service (`docker compose up -d db`) if it isn't running at all,
     then re-run this check before doing anything else.

2. **Check what's actually running.**
   ```bash
   ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose ps && cat backend/.env 2>/dev/null | grep -v SECRET"
   ```
   (Or `.env` at whatever path it actually lives — confirm the path
   first.) Confirms whether `docker-compose.yml`/`.env` exist at all,
   what image/tag is currently running, and gives you the current
   values of every env var below in one shot.

3. **Take a database backup before any migration**, even against a
   possibly-empty DB — there is no documented backup/rollback step
   anywhere in this project's history (BUILD_LOG.md only ever says
   live-server backups are "denied in unattended mode," never that one
   was actually taken). This is a new step, not previously documented:
   ```bash
   ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose exec -T db pg_dump -U lingosquared lingosquared > ~/lingosquared_pre_deploy_$(date +%Y%m%d).sql"
   ```
   Keep this file until the post-deploy verification below passes.

4. **Confirm current env var values** (from step 2's `.env` dump, or
   individually):
   ```bash
   ssh ramin@192.168.4.4 "grep -E 'ADMIN_EMAILS|CORS_ORIGINS|AZURE_SPEECH|GOOGLE_CLOUD_TTS|JWT_SECRET' /home/ramin/LingoSquared/backend/.env"
   ```
   **Automated version of this check** (added 2026-07-10):
   `scripts/check_deploy_config.sh <path-to-.env>` — checks every row of
   the "Required environment variables" table below against a `.env`
   file and exits non-zero on any FAIL-level finding (placeholder
   `ADMIN_EMAILS`/`JWT_SECRET`/`POSTGRES_PASSWORD`; localhost-only
   `CORS_ORIGINS` and missing TTS credentials are WARN-level, matching
   the table's "not a deploy blocker" calls). For the live server, pull
   the file locally first rather than SSHing from the script:
   ```bash
   ssh ramin@192.168.4.4 cat /home/ramin/LingoSquared/backend/.env > /tmp/live.env
   scripts/check_deploy_config.sh /tmp/live.env && rm /tmp/live.env
   ```
   It only inspects the file — it cannot confirm the admin account is
   actually registered (post-deploy step 4) or that a non-empty Google
   credential isn't the corrupted key (open question #1 below).
   As of the last read-only check (2026-07-05), `ADMIN_EMAILS` was
   still the `.env.example` placeholder (`admin@example.com`) and
   `CORS_ORIGINS` was `http://localhost:5173, http://localhost:5174`
   — confirm these haven't changed since, they almost certainly
   haven't been touched given no entry since claims otherwise. See
   "Required environment variables" below for what each needs to
   become before deploy.

5. **Confirm no other session is mid-deploy.** Check for an
   in-progress `git worktree`/uncommitted changes on your own working
   tree, and ask Ramin directly if any other Claude/Codex instance
   might be touching the live server right now — this project runs up
   to 3 parallel sessions, and the standing rule is deploys happen
   with Ramin present specifically to avoid two people deploying at
   once.

## Required environment variables (set/confirm before deploy)

Pull the current live `.env` (step 4 above) and reconcile against this
list before running anything. Do not guess values — anything marked
"needs Ramin" is a real decision, not something to fill in
unilaterally.

| Variable | Current live state (last confirmed) | What it needs to be |
|---|---|---|
| `ADMIN_EMAILS` | `admin@example.com` (placeholder, confirmed 2026-07-05) | **Needs Ramin's real private email**, and his account must be registered under it. No email verification exists — whoever registers first with the literal listed address becomes admin, so set this *before* any beta invite goes out, and register Ramin's account immediately after. |
| `CORS_ORIGINS` | `http://localhost:5173, http://localhost:5174` (confirmed 2026-07-05) | **Needs the real origin(s) beta users' browsers will load the frontend from** (a real domain or the LAN IP + port). Fails safe (rejects) if wrong, but breaks the app for every real user until fixed — a product decision (what the origin actually is), not something to infer. **If deploying the LAN web bundle (see "Frontend (LAN web)" section below), must also include `http://192.168.4.4:8011`.** |
| `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` | unset (never provisioned anywhere, dev or live) | **Needs Ramin to provision an Azure Speech resource** (Azure Portal → Cognitive Services → Speech), then set both here. Without it, `fa` TTS degrades gracefully to `provider_error`/browser fallback (no crash — `tts_actually_configured()` in `backend/app/services/tts.py` already gates the Endless Practice `listen_select` generator on real credentials, not just language support) — so this is NOT a deploy blocker, just a "fa audio won't actually work" gap until provided. |
| `GOOGLE_CLOUD_TTS_CREDENTIALS_JSON` | presumed already set on live (predates this session) — genuinely unconfirmed whether it's present, unset, or the corrupted key from the 2026-07-04 incident (see open question #1 below) | Confirm it's present and non-empty. If TTS for the 8 Google-covered languages is silently falling back to browser speech, re-verify via the debug path in `CLAUDE.md`'s Footguns section (`json.loads` → `Credentials.from_service_account_info()` → `creds.refresh()`) rather than trusting `/tts`'s silent exception-swallowing fallback. |
| `JWT_SECRET` | presumably already set from original setup | Confirm it's a real random secret, not the `.env.example` placeholder (`replace-with-a-long-random-secret`) — never regenerate it on a running deploy without warning Ramin first (invalidates every existing session token). |
| `POSTGRES_PASSWORD` / `DATABASE_URL` | presumably already set | Confirm they're real values, not `.env.example` placeholders, and that `DATABASE_URL` actually matches `POSTGRES_PASSWORD`. |

## Ordered deploy steps

Matches `CLAUDE.md`'s existing skeleton, made complete with the
correct step ordering and the pre/post steps above folded in.

**Load-bearing correction vs. an earlier draft of this runbook**: `python
-m app.content.seed` (step 4 below) is bootstrap-only — it creates the
`Language` rows and the 2 starter `Achievement`s, and **as of 2026-07-22
nothing else**. **It is NOT the real content pipeline and does NOT create
the actual ~131-unit en-nl/en-fa/en-prs/etc. courses.** Confirmed by
reading `scripts/backfill_lexemes*.py` directly:
every backfill script queries the DB for the real `Course`/`Unit`/
`Lesson` rows and hard-errors (`"ERROR: imported course is missing
{lesson_content_key}"`) if they aren't there — so skipping the real
content-import step (new step 7 below) leaves backfill with nothing to
match against. The real pipeline is: compile each course direction
locally with `scripts/compile_content.py`, then `POST` the compiled
JSON to `/admin/content/import` (admin-authenticated). This gap wasn't
documented anywhere in `CLAUDE.md`/`BUILD_LOG.md` — it's a finding from
reading `backend/app/content/seed.py` and the backfill scripts' own
DB queries directly while assembling this runbook, not a synthesis of
an existing landmine entry.

**Demo courses are no longer seeded on deploy (launch blocker, fixed
2026-07-22).** `app/content/seed.py` used to ALSO import 4 small hardcoded
placeholder courses (`FARSI`/`EN_TO_DARI`/`DARI_TO_EN`/`DARI_A2` →
"Farsi Foundations", "Dari Foundations", "Dari Elementary", "English
Foundations for Dari Speakers"). On the live server those sat in the course
picker *beside* the real launch courses, and because
`api/router.py`'s `/courses` orders by `Course.level, Course.title`, the
Latin-titled "English Foundations for Dari Speakers" sorted **before** the
real Arabic-titled "انگلیسی A1" — so `CoursePickerPage.tsx`, which pins its
"start here" hint to index 0, actively pointed a Dari speaker at a 2-lesson
stub. Those courses are dev/test fixtures only (`backend/tests/conftest.py`,
`test_backend.py`, and the `e2e/` Playwright suite assert on them).

- **Command-line default is now OFF.** `python -m app.content.seed` seeds
  languages + achievements ONLY. It prints
  `Demo courses: SKIPPED (…)` so the deploy log proves it.
- **Opt back in explicitly** (dev/CI only, never a real deployment):
  `python -m app.content.seed --with-demo-courses`, or
  `LINGO_SEED_DEMO_COURSES=1 python -m app.content.seed`.
  `--no-demo-courses` forces them off even when the env var is set.
- **In-process `main()` still defaults to demo-courses-ON** so the pytest
  session fixture and e2e suite keep working unchanged — only the CLI
  default flipped.
- **This does not remove courses that already exist.** Seeding is
  create-missing-only by design (an earlier delete-and-recreate version
  cascade-wiped user progress — see `backend/CLAUDE.md`). The 4 demo
  courses already present on live (and on the dev DB) need the one-off
  cleanup script — see "Removing the already-seeded demo courses" below.

**Also corrected**: `docker compose up -d api` must happen BEFORE the
content-import/practice-import steps, not after — this is a
from-scratch deploy with no previously-running container to serve
those HTTP calls against. `docker compose run --rm` (migrate, seed,
backfill) spins up its own ephemeral container and doesn't need the
persistent `api` service to be up, but `curl`-ing `/admin/content/import`
or `/admin/courses/{id}/practice/import` does.

```bash
# 1. Sync code (never syncs .env — never overwrites live secrets)
rsync -az --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
  "$LINGO_REPO"/backend/ ramin@192.168.4.4:/home/ramin/LingoSquared/backend/
rsync -az "$LINGO_REPO"/docs/ ramin@192.168.4.4:/home/ramin/LingoSquared/docs/

# 2. Build the new image
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose build api"

# 3. Migrate — after the alembic_version pre-flight check above.
#    If alembic_version was missing and you had to stamp a revision, do that
#    stamp here first, THEN run upgrade head.
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose run --rm api alembic upgrade head"

# 4. Bootstrap languages + achievements ONLY (create-missing-only, safe to
#    re-run — does NOT wipe existing user progress; this was a real bug fixed
#    2026-07-05, don't regress it). This does NOT create the real course
#    content — see step 7. As of 2026-07-22 it also does NOT create the demo
#    courses: NEVER add --with-demo-courses / LINGO_SEED_DEMO_COURSES on a
#    real deployment. Expect the output to end with "Demo courses: SKIPPED".
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose run --rm api python -m app.content.seed"

# 5. Bring the server up NOW, on the new image + migrated DB — required
#    before any of the HTTP-based admin steps below can be called at all.
#    Requires ADMIN_EMAILS/CORS_ORIGINS/etc. already correct in the synced
#    .env (rsync never touches .env — set these directly on the server
#    BEFORE this step, see "Required environment variables" above).
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose up -d api"

# 6. Register Ramin's real admin account (requires ADMIN_EMAILS to already
#    list this email — see above) and log in to get a bearer token for every
#    admin call below:
curl -X POST http://192.168.4.4:8010/auth/register -H "Content-Type: application/json" \
  -d '{"email":"<ramins-real-email>","password":"<a-real-password>"}'
TOKEN=$(curl -s -X POST http://192.168.4.4:8010/auth/login -H "Content-Type: application/json" \
  -d '{"email":"<ramins-real-email>","password":"<a-real-password>"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

# 7. Compile + import the REAL course content, per direction, per
#    scripts/content_manifest.txt (decide with Ramin which directions are
#    in scope for this first deploy — at minimum the 6 publish-gate
#    directions: en-fa, en-nl, en-prs, fa-en, nl-en, prs-en). For each line
#    of content_manifest.txt in scope:
python scripts/compile_content.py compile --realization <realizations for that course> \
  --overlay <overlays for that course> --out /tmp/<course>.json
curl -X POST http://192.168.4.4:8010/admin/content/import \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data @/tmp/<course>.json
# Repeat for every course direction in scope. Note the en-nl-a2 manifest
# entry is an EXTENSION of the en-nl course (same course title, later
# units) — import the base entry first so import_content()'s append-by-
# unit-order logic (fixed 2026-07-05) has an existing course to append to.

# 8. Backfill lexemes — MUST run after step 7 (needs the real lessons to
#    exist) and before practice-template import (step 9). Needs the full
#    repo mounted, not just backend/ (the image only contains backend/).
#    Run the correct backfill script(s) for every course direction actually
#    imported in step 7: backfill_lexemes.py (en-fa, original),
#    backfill_lexemes_en_nl.py, backfill_lexemes_en_prs.py,
#    backfill_lexemes_fa_en.py, backfill_lexemes_nl_en.py, backfill_lexemes_prs_en.py.
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose run --rm -v \"\$(cd .. && pwd):/repo\" -e PYTHONPATH=/repo/backend --entrypoint python api /repo/scripts/backfill_lexemes.py"
# repeat per launch-pair backfill script as needed

# 9. Import practice templates — ONLY after step 8. Importing before backfill
#    fails every template with "lesson key ... was not found in the course"
#    (found live 2026-07-06; CLAUDE.md's own recipe had this backwards once,
#    already corrected there — this file states the corrected order explicitly).
#    Per scripts/practice_manifest.txt entry in scope, compile the pack and
#    POST it to /admin/courses/{course_id}/practice/import (get course_id
#    from step 7's import response or GET /courses) with the same $TOKEN.

# 10. If ADMIN_EMAILS/CORS_ORIGINS/any other .env value changed AFTER step 5
#     (e.g. you fixed a placeholder mid-deploy instead of before), re-run:
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose up -d api"
#     `docker compose restart` does NOT reload .env — only `up -d`/
#     `--force-recreate` does. If nothing changed since step 5, this is a
#     harmless no-op.
```

Test suite on the server (isolated DB, never `--env-file` — that flag
only affects `docker-compose.yml` variable substitution, not the
container's real environment, and once caused the test suite to run
against the live database):

```bash
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && \
  docker compose exec -T db dropdb -U lingosquared --if-exists lingosquared_test && \
  docker compose exec -T db createdb -U lingosquared lingosquared_test && \
  docker compose run --rm api sh -c 'DATABASE_URL=\$(python3 -c \"import os,re; print(re.sub(r\\\"lingosquared\$\\\", \\\"lingosquared_test\\\", os.environ[\\\"DATABASE_URL\\\"]))\") python -m pytest -q'"
```

## Removing the already-seeded demo courses (one-off, live + dev)

Turning the seed default off (above) stops NEW demo courses appearing; it
cannot remove the 4 that every prior deploy already created, because
seeding is deliberately create-missing-only and **there is no
delete-course endpoint**. The one-off cleanup is
`backend/scripts/remove_demo_courses.sql`.

**This is a destructive live-DB operation — it requires Ramin present
(root `CLAUDE.md`, "Deploy authority"). Do not run it unattended.**

The script is idempotent and ships **wrapped in a rolled-back
transaction by default**: as written it prints before/after counts and
then `ROLLBACK`s, so running it as-is is a dry run. Committing for real
means editing the final `ROLLBACK;` to `COMMIT;` — a deliberate, visible
two-character edit, never a flag.

```bash
# Dry run first — prints exactly what WOULD be deleted, then rolls back.
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && \
  docker compose exec -T db psql -U lingosquared -d lingosquared -v ON_ERROR_STOP=1" \
  < backend/scripts/remove_demo_courses.sql

# Back up BEFORE the real run (scripts/backup_db.sh, or pg_dump directly).
# Then edit the trailing ROLLBACK; -> COMMIT; and re-run the same command.
```

Reconcile the dry-run output against the known live IDs before committing:
`683a90fe…` Farsi Foundations, `c9bacfb5…` Dari Foundations, `a2af2c0a…`
Dari Elementary, `138e9b66…` English Foundations for Dari Speakers. If the
"courses matched" count is not exactly 4, or the guard raises, **stop** —
something differs from the audited state.

## Post-deploy verification

Confirm the deploy actually landed and works, using the same
live-smoke-test pattern used for the shared dev stack's FastAPI/
Starlette CVE fix deploy (2026-07-06) — pointed at the live URL this
time.

1. **Confirm the right image is actually running** (not just built):
   ```bash
   ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose exec -T api pip show fastapi | grep Version"
   ```
   Expect `0.139.0` (the CVE fix — confirmed on the shared dev stack
   via this exact command, never yet confirmed live). If it still
   shows `0.115.12`, step 5 (or the re-run in step 10) above (`docker
   compose up -d api`) either didn't run or didn't actually recreate
   the container — `docker compose restart` does NOT pick up a new
   image, only `up -d` / `--force-recreate` does.

2. **Smoke-test the real HTTP surface**, same pattern as the dev-stack
   CVE verification:
   - Register a fresh account against the live URL, then log in
     separately with the same credentials (both auth paths).
   - List courses (`GET /courses` or equivalent) — confirm the
     expected launch-gate courses appear (en-nl, en-fa, en-prs and
     their reverse directions).
   - Drill into a real course → unit → lesson → a real exercise.
   - Submit one **correct** and one **incorrect** answer on a graded
     exercise — confirm `result`/`xp_awarded`/`feedback` are correct
     for both, not just a 200.
   - Confirm a due-review or practice-feed item generates cleanly for
     at least one launch-gate course (proves the backfill actually
     populated lexemes — Endless Practice items can't generate
     without them).
   - Trigger a 404 and a 422 (e.g. a bad exercise id, a malformed
     register payload) — confirm the generic error-shape handlers
     still respond correctly, no stack-trace leakage.

3. **Confirm `alembic_version` now reflects the real head revision**
   (currently `0014`) via the same psql check as pre-flight step 1 —
   confirms the migration actually applied, not just that the command
   exited 0.

4. **Confirm ADMIN_EMAILS/CORS_ORIGINS were actually updated** (not
   just planned) if this deploy included that decision — re-run the
   step-4 pre-flight grep and confirm the values changed, then
   register Ramin's real admin account and confirm `is_admin: true`
   comes back from a real authenticated request.

5. **If this deploy includes new content**, spot-check RTL rendering
   and script-strict grading on a real fa/prs exercise in the browser
   — this project's established bar is that reading a diff has never
   caught its worst bugs; only playing a real lesson has.

## Frontend (LAN web)

The live server (192.168.4.4) runs only the backend — nothing serves the
frontend there today. This section stands up a static-hosting path so
the app is reachable from a phone on the LAN tonight: an `nginx:alpine`
`web` service (host port **8011**; 8010 is the api, 8000 is the
unrelated `audiobookrequest` service) serving a prebuilt
`frontend/dist`, added additively to `backend/docker-compose.yml`
(`backend/nginx.web.conf` is its mounted config — SPA fallback via
`try_files ... /index.html`, long-cache on hashed assets, no-cache on
`index.html`). This is separate from, and does not replace, any future
plan to deploy the frontend to a real hosted domain — it's the fastest
path to "open it from a phone right now."

**Build with the LAN mode, on the Mac** (bakes `VITE_API_BASE_URL` in
at build time — there is no runtime config for this, a rebuild +
re-deploy is required if the API origin ever changes):

```bash
cd "$LINGO_REPO"/frontend
npm install   # only if node_modules is missing/stale for this checkout
npm run build -- --mode production.lan
```

This picks up `frontend/.env.production.lan`
(`VITE_API_BASE_URL=http://192.168.4.4:8010`) via Vite's `.env.[mode]`
convention — `--mode production.lan` loads `.env.production.lan` in
addition to the base `.env`/`.env.[mode].local` if present. Confirm
`frontend/dist/index.html` references hashed asset filenames (e.g.
`/assets/index-XXXXXXXX.js`) before deploying — that's the signal the
build actually ran, not a stale copy.

**Deploy the built bundle and bring the `web` service up:**

```bash
rsync -az --delete "$LINGO_REPO"/frontend/dist/ \
  ramin@192.168.4.4:/home/ramin/LingoSquared/backend/web_dist/

# nginx.web.conf and docker-compose.yml's new `web` service are already
# synced by the normal backend rsync step (step 1) above, if that step
# already ran this deploy. If deploying the frontend on its own, sync
# just those two files first:
rsync -az "$LINGO_REPO"/backend/docker-compose.yml \
  "$LINGO_REPO"/backend/nginx.web.conf \
  ramin@192.168.4.4:/home/ramin/LingoSquared/backend/

ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && docker compose up -d web"
```

`docker compose up -d web` (not `restart`) both on first bring-up and on
any later re-deploy of a new `dist/` — the bind-mounted directory content
changes on every `rsync`, but if the compose file/nginx conf themselves
changed too, `up -d` is what actually picks that up (same
`.env`-vs-`up -d` distinction as elsewhere in this runbook, applies to
compose-file/mount changes too, not just `.env`).

**CORS — required, or every request from the phone fails:** the backend
`.env`'s `CORS_ORIGINS` must include `http://192.168.4.4:8011` (the
origin the phone's browser actually loads the app from), added to
whatever origins are already there, not replacing them. This is on top
of — not instead of — the existing "confirm `CORS_ORIGINS` matches the
real beta-user origin" pre-flight/required-env-vars items above. After
editing `.env` on the server, `docker compose up -d api` (not
`restart`) to actually reload it.

**Phone URL**: `http://192.168.4.4:8011` (LAN only, no HTTPS — expect a
"not secure" browser warning, which is expected/fine for LAN
phone-testing, not a bug).

**What this worker verified vs. did not:**
- Verified: `npm run build -- --mode production.lan` succeeds in an
  isolated worktree (after `npm install` at the worktree root — the
  npm-workspace footgun in `CLAUDE.md`); `dist/index.html` references
  hashed assets; the built JS bundle contains the expected
  `192.168.4.4:8010` API origin (confirms the env file is actually
  picked up by this mode, not silently ignored); `nginx -t` syntax-checks
  `backend/nginx.web.conf` cleanly via a throwaway, unpublished
  `docker run --rm nginx:alpine nginx -t` container (no shared stack/
  volumes/ports touched).
- **Not verified** (out of scope for a worktree-isolated prep worker,
  per the standing "never touch the live server / any running stack"
  rule): the actual `docker compose up -d web` bring-up on
  192.168.4.4, whether port 8011 is reachable through any router/
  firewall between the phone and the LAN, and an actual phone-browser
  load of the app end-to-end. Do these live, with Ramin present, per
  the rest of this runbook's conventions.

## Contradictions / open questions found while synthesizing this (need Ramin's input)

1. **`GOOGLE_CLOUD_TTS_CREDENTIALS_JSON` on live was never explicitly
   re-confirmed after the 2026-07-04 corruption incident** (a GUI
   copy-paste mangled the key once, on whatever environment that was
   — the entry doesn't specify live vs. dev). Since the live server
   has apparently never been deployed to since, it's unclear whether
   live's copy of this credential (if one was ever set there at all,
   e.g. during original box setup) is the working one or the corrupted
   one, or unset entirely. **Recommend explicitly testing Google TTS
   live during post-deploy verification**, not assuming it works.
2. **No entry ever describes the live server's *original* setup** —
   BUILD_LOG.md starts mid-project (2026-07-02) with the live server
   already existing (`ramin@192.168.4.4`, port 8010, `audiobookrequest`
   on 8000). What's actually running there today (empty DB? some
   earlier build? a stale `docker-compose.yml`?) is genuinely unknown
   from the documentation alone — pre-flight step 2 above is the way
   to find out for real, not an assumption this runbook can resolve on
   paper.
3. **No live-server rollback plan exists anywhere in this project's
   history.** The pg_dump step above is new (added by this runbook,
   not previously documented) — there's no prior precedent for how a
   bad live deploy would actually be rolled back (restore from dump?
   revert the image tag and re-run migrations down?). Worth deciding
   explicitly with Ramin before the first real deploy, not improvised
   under pressure if something breaks.
4. **Whether all 6 launch-gate backfill scripts need to run on this
   first deploy, or only the subset for content actually being
   imported**, depends on exactly which courses/units this deploy
   ships — not something this runbook can resolve without knowing the
   deploy's actual content scope on the day. Confirm against
   `scripts/practice_manifest.txt` and the actual `/admin/content/
   import` payload being sent.
5. **Which course directions actually get imported on this first
   deploy is an open product decision, not something this runbook
   picks.** `scripts/content_manifest.txt` currently has 9 entries (the
   6 publish-gate directions plus `en-es`/`en-fr`, both explicitly
   "park until nl is done" per `CLAUDE.md`, plus an `en-nl-a2`
   extension). Decide with Ramin whether the first live deploy imports
   only the 6 publish-gate directions or everything currently compiled
   — importing extra non-launch-gate content doesn't functionally
   break anything, but it does mean es/fr becomes visible/reachable on
   the live server before it's meant to be beta-facing.
6. **Real gap found while writing this runbook, not previously
   documented anywhere**: `CLAUDE.md`'s prior "Deploying a backend
   change" skeleton (and an earlier draft of this file) treated `python
   -m app.content.seed` as if it were the content-seeding step. Reading
   `backend/app/content/seed.py` directly shows it only creates
   `Language`/`Achievement` rows (plus, until 2026-07-22, 4 tiny hardcoded
   placeholder demo courses) — never the real ~131-unit courses. The real pipeline
   (`scripts/compile_content.py` → `POST /admin/content/import`) was
   never in the deploy skeleton at all before this runbook. Worth
   double-checking on deploy day that this runbook's step 7 is actually
   followed and not skipped by habit in favor of the old, insufficient
   `app.content.seed` step.
