# Sentry wiring (launch checklist)

Full behaviour and privacy rules are in `docs/SENTRY.md`. This page is the short "turn it on and prove it works" list. Org `mindtheapp`, EU region (`de.sentry.io`), projects `lingosquared-backend` and `lingosquared-web`. DSNs are secrets of the deployment: keep them in `secrets/sentry/` and never commit them.

## Where the DSN goes
- Backend: `SENTRY_DSN` in the server `backend/.env` (compose `env_file`), plus `SENTRY_RELEASE` (short git sha on deploy) and optionally `SENTRY_ENVIRONMENT` (defaults to `production.lan` unless `APP_ENV` is dev/test). Recreate the api container: `docker compose up -d api`.
- Frontend: `VITE_SENTRY_DSN` in `frontend/.env.production.lan.local` (build time, git-ignored), plus optional `VITE_SENTRY_RELEASE` / `VITE_SENTRY_ENVIRONMENT`. It is baked into the bundle, so rebuild and redeploy `web_dist`. The CSP already allows `https://*.ingest.de.sentry.io`.
- Optional source maps: `SENTRY_AUTH_TOKEN` in the build shell only.

An empty DSN means Sentry is off. Change `ENVIRONMENT` to something other than `production.lan` once the public domain is live if you want to separate LAN from public events.

## Verify
1. Backend: confirm the variable reached the container without printing it: `docker compose exec -T api python -c "import os;print(bool(os.environ.get('SENTRY_DSN')))"` prints `True`. Then raise one controlled test error from a shell inside the api container using `sentry_sdk.capture_message("launch check")` after the app's Sentry init in `backend/app/core/sentry.py`, and look in the `lingosquared-backend` project (or ask the Sentry MCP `search_issues`). Check the event has no email, IP, cookies or auth header (the `before_send` scrubber).
2. Web: open the built app, Profile, set "Crash reports" to Always send, and use "Report a problem". The feedback item should appear in `lingosquared-web` within a minute with route, release and environment tags. Then reset the setting.
3. Releases: events show the expected `release` (sha). If source maps were uploaded, stack frames show original file names.
4. Alerts: add an issue alert (new issue in production, mail to Ramin) so errors are noticed. A Sentry cron monitor can also watch the nightly backup.
5. Leave tests alone: tests never set a DSN, so no test can send events.

Rotating the DSN is in `docs/ops/KEY_ROTATION.md`.
