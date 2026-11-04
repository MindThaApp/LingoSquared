# Key and secret rotation checklist

No values here, ever. Locations are paths and variable names only. Server = `ramin@192.168.4.4`, app dir `/home/ramin/LingoSquared`. Rotate after any suspected leak, when a person with access leaves, and on the schedule below. After every rotation, record the date in `.local/logs/` (not the value).

| Secret | Lives in | Used by | Schedule |
|---|---|---|---|
| `JWT_SECRET` | server `backend/.env` (chmod 600); dev `backend/.env` | signs access tokens (HS256); app refuses to start under 32 chars | 12 months or on leak |
| `POSTGRES_PASSWORD` (+ the password inside `DATABASE_URL`) | server `backend/.env` | db container, API | 12 months or on leak |
| `SENTRY_DSN` / `VITE_SENTRY_DSN` | `secrets/sentry/*.txt` (git-ignored, chmod 600); server `backend/.env`; web build env `frontend/.env.production.lan.local` | event ingest (write-only, low risk, but spam-able) | on leak |
| `SENTRY_AUTH_TOKEN` | build shell only, never committed | source-map upload | 6 months, minimum scope |
| `GOOGLE_CLOUD_TTS_CREDENTIALS_JSON` | server `backend/.env`; render host for `scripts/render_audio.py` | TTS | 90 days (service-account key) or on leak |
| `AZURE_SPEECH_KEY` (+ `AZURE_SPEECH_REGION`) | `backend/.env` | TTS | 12 months; Azure has key1/key2 for no-downtime swap |
| `GEMINI_API_KEY` | `backend/.env` / render shell | content/audio tooling | 12 months |
| `ELEVENLABS_API_KEY` | server `backend/.env` | TTS (budget-capped) | 12 months |
| Social sign-in client IDs (`GOOGLE_OAUTH_CLIENT_IDS`, `APPLE_AUDIENCE_IDS`) | `backend/.env`, build env | public identifiers, not secrets; Apple private key (if used) stays off-repo | n/a |
| Server SSH key | `secrets/ssh/id_ed25519` (git-ignored); public half in server `~/.ssh/authorized_keys` | deploys | 12 months or on leak |
| Server cron secrets | server `~/.cron_secrets` (chmod 600; media-server, not LingoSquared) | arr API keys | owner of that stack |
| GitHub access | `gh` auth on the dev machine; commits use the noreply address | push/PRs | use fine-grained tokens, 90 days |

## Steps

### JWT_SECRET (invalidates all access tokens; users re-login via refresh token, which is independent of this secret)
1. Generate 48+ random bytes (`python3 -c "import secrets;print(secrets.token_urlsafe(48))"`) and write it straight into the server `backend/.env` (never into chat, logs or a commit).
2. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d api` (a restart is enough; `.env` is read via `env_file`).
3. Check `/health/ready` and log in once.

### POSTGRES_PASSWORD
1. Take a backup first (`scripts/backup_db.sh`).
2. `ALTER USER lingosquared PASSWORD '...'` inside the db container (read the new value from a file, do not type it on a shared terminal history).
3. Update `POSTGRES_PASSWORD` and the password in `DATABASE_URL` in `.env` together, recreate `api`, check `/health/ready`.

### Sentry DSN
1. Sentry project settings, Client Keys: create a new key, delete the old one after the swap.
2. Update `secrets/sentry/*.txt`, the server `.env` (`SENTRY_DSN`) and rebuild the web with the new `VITE_SENTRY_DSN` (needs a deploy; old key works until deleted).

### TTS / API keys (Google, Azure, Gemini, ElevenLabs)
1. Create the new key in the provider console (Azure: regenerate key2, switch, then regenerate key1; Google: new service-account key, then delete the old key id).
2. Update `.env` on the server and the render host; recreate `api`.
3. Test one TTS request; delete the old key at the provider.

### SSH key
1. `ssh-keygen -t ed25519` to a new file, append the public half to the server `authorized_keys` using the old key, test the new key, then remove the old line.
2. Replace `secrets/ssh/id_ed25519*`.

## After any rotation
- Confirm `git ls-files secrets .env*` lists no secret file; `git log -S` for the old value only if you suspect it was committed (then also rewrite history or treat it as burned).
- Old DB backups contain no env secrets, but they contain user data: keep them off shared storage.
- Open items (2026-11-04): social-sign-in and email-provider keys do not exist yet; add rows when they are created.
