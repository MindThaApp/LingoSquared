# WSL2 setup (Windows + Ubuntu 24.04)

Supersedes the iCloud/brew instructions in `docs/HANDOVER.md` for environment
setup. The repo lives **inside the WSL filesystem** (any directory under your
WSL home) -- never under `/mnt/c` (slow, broken file watching and permissions; the
bootstrap script refuses to run there).

## 1. Windows side

1. Install WSL + Ubuntu (PowerShell, admin): `wsl --install -d Ubuntu-24.04`, reboot, create the Linux user.
2. Create `%UserProfile%\.wslconfig`:
   ```ini
   [wsl2]
   networkingMode=mirrored
   memory=12GB
   ```
   Mirrored networking is needed so WSL can reach the LAN server
   (192.168.4.4) and a Windows browser/phone can reach the dev ports. Size
   `memory` to the machine (docker + vite + pytest want 8GB+). Apply with `wsl --shutdown`.
3. Docker: install Docker Desktop and enable Settings -> Resources -> WSL
   integration for `Ubuntu-24.04`. Alternative: docker-ce + compose plugin
   inside WSL (`sudo usermod -aG docker $USER && sudo service docker start`).
4. Optional: VS Code with the "WSL" extension (`code .` from inside WSL).

## 2. Inside WSL

```bash
sudo apt-get update && sudo apt-get install -y git
# GitHub auth (gh: https://github.com/cli/cli/blob/trunk/docs/install_linux.md)
gh auth login
mkdir -p <parent-dir> && cd <parent-dir>   # any directory in the WSL filesystem
git clone <repo-url> LingoSquared     # directory MUST be named LingoSquared (hooks depend on it)
cd LingoSquared
git checkout fix/launch-gate-content-review-wave1   # or the branch you are working on
bash scripts/bootstrap_wsl.sh         # add --with-e2e for Playwright; --no-stack to skip docker
```

The script is idempotent: git `core.autocrlf=input`, apt packages, nvm + Node
22 (`.nvmrc`), `.content-venv` (`scripts/requirements-content.txt`), `npm ci`,
Docker check, a fresh `backend/.env` (random JWT secret + DB password; never
overwrites an existing one) and `frontend/.env`, then `docker compose up -d`
and `alembic upgrade head`. `jq` is installed because the `.claude` hooks need it.

The script does **not** create the reference data (languages, achievements);
run the language bootstrap in section 4 once after it finishes.

## 3. Secrets and local state to transfer by hand (names only)

Move these over a secure channel (USB, password manager). Never chat, email or cloud notes.

| Item | Notes |
|---|---|
| `backend/.env` | Keys: `JWT_SECRET`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` (must match the password), `GOOGLE_CLOUD_TTS_CREDENTIALS_JSON`, `TTS_MONTHLY_CHAR_BUDGET`, `ADMIN_EMAILS` (legacy, not read by the backend; see section 4), `CORS_ORIGINS`, rate-limit settings. Azure keys (`AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`) are not set yet. If you copy the Mac's file over the generated one, also copy the matching DB volume or reset the DB password. `chmod 600`. |
| `~/.lingo_admin_pw` | Admin password file, `chmod 600` (live admin is `admin@example.com`). |
| `~/.ssh/id_ed25519`, `id_ed25519.pub`, `config`, `known_hosts` | For `ramin@192.168.4.4`. `chmod 700 ~/.ssh; chmod 600 ~/.ssh/id_ed25519 ~/.ssh/config`. |
| `~/.deepseek_api_key` | DeepSeek worker key. |
| Codex login | `codex login` on the new machine. |
| GitHub | `gh auth login`. |

**Do NOT copy:** `node_modules`, `.content-venv`, `dist`, `web_dist` (darwin
binaries / build output; bootstrap and builds regenerate them).

## 4. Dev database

First bootstrap the reference rows (16 languages + achievements). Without
this every content import fails with 422 "language is unsupported":

```bash
cd backend
docker compose exec api python -m app.content.seed                       # languages + achievements only
docker compose exec api python -m app.content.seed --with-demo-courses   # dev/test box: also the 4 demo courses backend tests and e2e expect
```

Never pass `--with-demo-courses` on the live server.

Admin account (needed by `scripts/sync_dev_db.sh`): Admin rights come only from the `users.is_admin` DB column. `ADMIN_EMAILS` is not read by the backend and registering never grants admin. Register the account, then run `docker compose exec api python -m app.scripts.promote_admin <email>` from `backend/` (or an existing admin calls `POST /admin/users/{user_id}/admin`).

Then either:
- `scripts/sync_dev_db.sh` after the stack is up (about 25 min; imports all content), or
- restore a dump from the Mac: `pg_dump -Fc` there, then `pg_restore` into the
  compose `db` service here.

The live server is at alembic migration 0031; `alembic upgrade head` in the
bootstrap brings a fresh DB to head.

## 5. Claude Code on WSL

1. Install Claude Code (https://docs.claude.com/en/docs/claude-code) and log in.
2. Reinstall the OpenAI Codex plugin (`/plugin`), then `codex login`.
3. `.claude/settings.json` has two allow-rules with a hard-coded macOS path to
   `codex-companion.mjs`. Do not edit it; instead add equivalent rules to the
   gitignored `.claude/settings.local.json` using the WSL path
   (`/home/<you>/.claude/plugins/cache/openai-codex/codex/<version>/scripts/codex-companion.mjs`,
   `status *` and `result *`).
4. Hooks need `jq` (installed by bootstrap) and the checkout directory named `LingoSquared`.

## 6. Smoke-test checklist

- [ ] `ssh ramin@192.168.4.4 hostname`
- [ ] `bash scripts/verify.sh` -- judge by the printed summary and `grep COMPILE FAILED` in the log, not the exit code
- [ ] `.content-venv/bin/python -m pytest scripts/tests -q`
- [ ] `cd frontend && npm run build && npx vitest run`
- [ ] Backend CI-style pytest with the repo mounted (without the mount `test_content_answer_shapes` silently skips), against an isolated `*_test` DB:
      `cd backend && docker compose run --rm -v "$PWD/..:/repo" -w /repo/backend api python -m pytest -q`
- [ ] e2e route-mocked specs: `cd e2e && npm ci && npx playwright install --with-deps chromium`, then run the specs per `e2e/README.md`
- [ ] Dev server: `cd frontend && npm run dev -- --port 5180`, open http://localhost:5180 from Windows

## 7. Known WSL gotchas

- Files created by root containers in bind mounts are root-owned; fix with `sudo chown -R "$USER": <path>`.
- cron is not running by default: `scripts/install_backup_cron.sh` needs `sudo service cron start`, or `systemd=true` under `[boot]` in `/etc/wsl.conf` (then `wsl --shutdown`).
- Windows sleep/hibernate also stops WSL and its containers (the Mac sleep issues disappear, this replaces them).
- Keep the repo off `/mnt/c`; keep Docker bind mounts inside the WSL filesystem.
