# Key rotation (names only, never values)

The detailed per-secret steps live in `docs/KEY_ROTATION.md`; this page is the ordered launch checklist. Server = `ramin@192.168.4.4`, app dir `/home/ramin/LingoSquared`. Never paste a value into chat, a log or a commit; write new secrets straight into the target file with mode 600.

## Secrets and where they live

| Name | Lives in | Used for | Rotate how (short) |
|---|---|---|---|
| `JWT_SECRET` | server `backend/.env` | signs access tokens; app refuses < 32 chars | `openssl rand -hex 32`, edit `.env`, recreate `api`. Access tokens die, refresh tokens survive |
| `POSTGRES_PASSWORD` and the password in `DATABASE_URL` | server `backend/.env` | db container, API | backup, `ALTER USER`, edit both values, recreate `api` |
| `SMTP_PASSWORD` (`SMTP_HOST`, `SMTP_USERNAME`, `EMAIL_FROM`) | `backend/.env` (not set yet) | password-reset email | new app password at the mail provider, edit `.env`, recreate `api`, send one test reset |
| `SENTRY_DSN` | `secrets/sentry/*.txt`, server `backend/.env` | backend error ingest | new client key in Sentry, swap, delete old key |
| `VITE_SENTRY_DSN` | web build env (`frontend/.env.production.lan.local`) | browser ingest | same, then rebuild and redeploy web |
| `SENTRY_AUTH_TOKEN` | build shell only | source-map upload | new minimal-scope token, revoke old |
| `GOOGLE_CLOUD_TTS_CREDENTIALS_JSON` | `backend/.env`, render host | TTS | new service-account key, delete the old key id |
| `AZURE_SPEECH_KEY` | `backend/.env` | TTS (Farsi) | regenerate key2, switch, regenerate key1 |
| `GEMINI_API_KEY` | `secrets/gemini/api-key.txt`, render host | Dari audio rendering | new key in console, delete old |
| `ELEVENLABS_API_KEY` | server `backend/.env` | legacy TTS | new key, delete old |
| `GOOGLE_OAUTH_CLIENT_IDS`, `APPLE_AUDIENCE_IDS` | `backend/.env`, build env | public identifiers, not secret | n/a |
| Server SSH key (`secrets/ssh/id_ed25519`) | dev machine; public half in server `authorized_keys` | deploys, backups pull | new key, add, test, remove old line |
| GitHub token / `gh` auth | dev machine | push, PRs | fine-grained, 90 days |
| Off-box backup SSH key (`OFFSITE_SSH_KEY`) | server, if backups go off-box | backup rsync | new key, add on target, test, remove old |
| Caddy / Cloudflare tunnel token (`TUNNEL_TOKEN`) | server compose env, if Option B | public ingress | roll token in the Cloudflare dashboard, update, restart `cloudflared` |

## Order for a launch rotation (do once, before opening to the public)
1. Take a verified backup (`scripts/ops/backup_db.sh`) and run one restore drill.
2. `POSTGRES_PASSWORD` + `DATABASE_URL` (needs the backup; brief API restart).
3. `JWT_SECRET` (all users re-authenticate through refresh tokens; do it off-peak).
4. Provider keys: TTS (Google, Azure, Gemini, ElevenLabs), one at a time, test one TTS call after each.
5. Sentry DSNs (backend, then web with a rebuild). Add `SMTP_*` once created.
6. SSH key and off-box backup key last, so you keep access while rotating the others.
7. Re-run `git ls-files secrets .env*` (must list no secret file) and record the date, never the value, in `.local/logs/`.

Why this order: the database and signing secrets protect user data and sessions, so they go first; the access paths you need to perform the rotation go last. After a leak, rotate the leaked secret first regardless of the order.
