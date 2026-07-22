# Backend, migrations, docker & deploy — rules for `backend/**`

This file auto-loads when you work under `backend/`. Backend code +
alembic migrations + `scripts/compile_content.py` are **Codex's lane**
(dispatched and verified by Claude — see root `CLAUDE.md` → POLICIES →
Division of labor). Root `CLAUDE.md` still governs cross-cutting footguns
(git/worktree/agent, the DB-isolation-for-concurrent-workers rule) and
the non-negotiable verification bar.

## Standing invariants (these used to live in root's shipped-phases list —
## they are RULES, so they live here now, where they auto-load for you)

- **Every migration after 0001 must be fresh-migrate-safe** — a fresh
  `alembic upgrade head` on an empty DB must succeed, not just an incremental
  upgrade from the previous revision.
- **Grading success is `quality >= 3`, NEVER a truthiness check on `correct`.**
  Since Phase C, `correct` can be the STRING `"incorrect"` — which is truthy.
  Any `if correct:` in a grading/SRS path is a live bug.
- **`content_key` is unique PER COURSE, never globally** (migration 0015):
  fa-en/nl-en/prs-en share one English realization, so content_keys repeat
  across courses. A global unique index 500s the second course's import.
- **Phase F checkpoints must never touch per-item SRS**, force
  `orthography_strict = True`, and stay idempotent.

## Migrations

- **Every migration after 0001 must defensively check existence before
  `op.add_column`/`create_table`/`create_foreign_key`/`create_index`**
  (`sa.inspect(bind)` or `checkfirst=True`). `0001_initial.py` runs
  `Base.metadata.create_all()` against the LIVE ORM models, so a fresh
  migrate creates every table at its CURRENT shape at 0001 — an
  unguarded later `ADD COLUMN` then crashes on a genuinely fresh
  deploy/CI while looking fine on any migrated stack. `0008`–`0012` were
  fixed after such a crash. Detail: BUILD_LOG Phase A closeout.
- **`alembic upgrade head` can fail with a confusing `DuplicateColumn`
  when `alembic_version` doesn't exist as a table** (Alembic has no
  history, re-runs an early `ADD COLUMN`). Fix: `alembic stamp <version
  the schema actually reflects>` before `upgrade head`. Detail: BUILD_LOG.

## Docker / env / seeding

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
  (below). Detail: BUILD_LOG.
- **A direct-DB shortcut faking "lesson completed" bypasses the real
  endpoint's side effects** (`SkillProgress`/`user_lexeme_srs`/streak) —
  always verify through `POST /lessons/{id}/complete`, not a DB shortcut,
  even when slower. Detail: BUILD_LOG.
- **Content seeding is create-missing-only, not delete-and-recreate** (an
  earlier version wiped user progress via cascade every deploy — don't
  regress it). Detail: BUILD_LOG.

## Isolated-DB test recipe (never `--env-file`)

```bash
ssh ramin@192.168.4.4 "cd /home/ramin/LingoSquared/backend && \
  docker compose exec -T db dropdb -U lingosquared --if-exists lingosquared_test && \
  docker compose exec -T db createdb -U lingosquared lingosquared_test && \
  docker compose run --rm api sh -c 'DATABASE_URL=\$(python3 -c \"import os,re; print(re.sub(r\\\"lingosquared\$\\\", \\\"lingosquared_test\\\", os.environ[\\\"DATABASE_URL\\\"]))\") python -m pytest -q'"
```

(When many workers run concurrently, name a uniquely-named test DB per
worker — see the DB-isolation footgun in root `CLAUDE.md`.)

## Content / lexeme scripts (repo-mount invocations)

- **`backfill_lexemes.py` needs the full repo mounted** (the backend
  image only has `backend/`): `docker compose run --rm -v "$(cd .. &&
  pwd):/repo" -e PYTHONPATH=/repo/backend --entrypoint python api
  /repo/scripts/backfill_lexemes.py`. Detail: script docstring.
- **`backend/tests/test_content_answer_shapes.py` self-skips (`1
  skipped`) under the standard docker pytest** (the image lacks repo-root
  `docs/content/`). Run it with the full repo mounted per its docstring:
  `docker compose run --rm -v "$(cd .. && pwd):/repo" -e
  LINGO_REPO_ROOT=/repo api sh -c '...pytest tests/
  test_content_answer_shapes.py'`. **With the corpus reachable it shows
  ~226 known FAILING cases — expected, not a regression** (they're real
  content bugs; the enumeration and "don't weaken the test" rule are in
  `docs/content/CLAUDE.md`). Detail: BUILD_LOG 2026-07-10.

## Performance

- **Keep reusing `_generate_prioritized()`'s per-template
  `slot_candidate_cache` — don't reintroduce a per-attempt course-wide
  lexeme-pool scan.** `lexeme_matches()` is pure, so per-slot candidates
  are identical across attempts within one batch request; memoizing gave
  ~25x–60x speedup (a live-QA pass measured 77s → fast on prs-en). Detail: BUILD_LOG 2026-07-07.

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
  `speechSynthesis` is its only fallback, and its quality is uncertain
  (`fa-AF` approximation; may be silent or wrong-accent).
- ElevenLabs is no longer the live provider (superseded 2026-07-04);
  gotchas in BUILD_LOG if revisited.
- **Google Cloud TTS `RefreshError: invalid_grant: Invalid JWT Signature`
  means a corrupted service-account private key (usually GUI-editor
  copy-paste mangling), NOT an IAM/enablement problem** (which shows as
  403). Debug: `json.loads` → `from_service_account_info()` →
  `creds.refresh()` (surfaces it); the `/tts` route swallows the real
  exception, so call `tts_service.synthesize()` directly via `docker
  compose run`. **Never hand-copy a service-account JSON through a GUI
  editor — read/write its exact bytes programmatically.** Detail: BUILD_LOG.
- **The public-domain FSI/Peace Corps audio does NOT help as a content
  or asset shortcut** — the Persian FSI tapes are 24 long unsegmented
  per-unit recordings (no per-phrase splicing without manual editing);
  Peace Corps Persian/Dari has no recordings at all (PDF-only). Only use:
  a pronunciation reference for a human recording session. **Don't
  re-investigate either without new information.**

## Backend-side known limitations

- Admin content import/export is API-only, no UI (intentional trim).
- Starlette "BadHost" CVE (CVE-2026-48710) **fixed and deployed to the
  dev stack 2026-07-06** (`fastapi` 0.115.12→0.139.0, starlette→1.3.1);
  not yet on the live server (192.168.4.4). Detail: BUILD_LOG.

## Where the backend runs

- **Backend (live):** `ramin@192.168.4.4` (SSH key), code at
  `/home/ramin/LingoSquared/backend`, API on **port 8010** (8000 is
  `audiobookrequest`). OpenAPI at `http://192.168.4.4:8010/docs`.
  `192.168.4.8` is a DIFFERENT machine (SMB-only NAS) — don't confuse them.
- **Backend's `CORS_ORIGINS` (`.env`) must list whatever port the
  frontend is actually running on.** (Frontend dev-server ports: see
  `frontend/CLAUDE.md`.) **AND `https://localhost` — the Android APK's
  Capacitor WebView origin (`androidScheme: "https"`) — on any backend
  the APK targets.** Found live 2026-07-14: the deployed server rejected
  the APK's preflights, so every API call inside the APK failed before
  it started ("can't start a guest session" was just the first symptom).
  The web frontend is same-origin and masks this gap — probe with an
  OPTIONS request with `Origin: https://localhost` after every deploy.
- Local stack: `colima start`; `cd backend && docker compose up -d`
  (isolated `backend/.env`, random JWT secret, never committed). **Never
  touch the live server (192.168.4.4) unattended — deploys happen with
  Ramin present.**

## Deploying a backend change

**`docs/PRE_DEPLOY_RUNBOOK.md` is the full checklist — read it before any
deploy to 192.168.4.4.** It covers pre-flight, required env vars
(`ADMIN_EMAILS`, `CORS_ORIGINS`, `AZURE_SPEECH_KEY`/`_REGION`,
`GOOGLE_CLOUD_TTS_CREDENTIALS_JSON`), a backup step, the ordered deploy,
and post-deploy smoke tests.

**First real deploy COMPLETED 2026-07-12 (Ramin present).** Live state:
DB dropped fresh (old one only had demo data; backup at
`~/lingosquared_backup_20260711_2358.sql.gz` on the server) and migrated
0001→0023 via the fresh-create path (the 0004→0005 incremental path
FAILS — 0005 forward-references tables only 0001-with-current-models
creates; a historically-migrated DB below ~0005 must go fresh, not
incremental). Full content synced (42 course groups, 35 courses/596
units; German skipped pending its lane's validator fixes), backfills run
server-side, all practice packs imported. Frontend served by the `web`
nginx service on port 8011 (`http://192.168.4.4:8011` is the LAN app
URL); `CORS_ORIGINS` includes it; Google TTS credentials live and
smoke-verified (real MP3 returned). `ADMIN_EMAILS` is still
`admin@example.com` — MUST become Ramin's real email before any external
beta invite (standing pre-beta checklist item). Ongoing syncs:
`scripts/sync_dev_db.sh http://192.168.4.4:8010` with
`LINGO_BACKFILL_SSH=ramin@192.168.4.4`.

Quick-reference skeleton (see runbook for the complete ordered version):

```bash
rsync -az --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
  "$LINGO_REPO"/backend/ ramin@192.168.4.4:/home/ramin/LingoSquared/backend/
rsync -az "$LINGO_REPO"/docs/ ramin@192.168.4.4:/home/ramin/LingoSquared/docs/

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

## Pre-deploy / pre-beta checklist items

- **Confirm `ADMIN_EMAILS` on the live deployment is Ramin's real private
  email, not the `.env.example` placeholder, and his account is already
  registered under it.** `register()` grants `is_admin` to whoever
  registers first with a listed email; no email verification closes that
  race. Deployment step, not a code bug. Detail: BUILD_LOG security-audit entry.
- **The live server's `CORS_ORIGINS` is currently localhost-only** — must
  list the real origin(s) beta users load the frontend from or their
  requests are rejected. A deployment decision, don't guess-and-fix. (An
  unbounded-`response`-field resource-exhaustion bug was found and fixed
  in the same pass.) Detail: BUILD_LOG.
