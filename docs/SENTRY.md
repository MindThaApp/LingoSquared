# Sentry crash reporting

Sentry (org `mindtheapp`, EU region, https://de.sentry.io) collects server errors, learner-approved crash reports and "Report a problem" submissions. Projects: `lingosquared-backend` and `lingosquared-web`.

## Configuration

DSNs are secrets of the deployment, not of the repo. They live in `secrets/sentry/` (git-ignored) and reach the app through environment variables. Empty means Sentry is off.

| Variable | Where | Meaning |
|---|---|---|
| `SENTRY_DSN` | `backend/.env` (read through compose `env_file`) | Backend DSN. Unset: no events, ever. |
| `SENTRY_RELEASE` | `backend/.env` | Git sha or version. Set it on deploy, for example `git rev-parse --short HEAD`. |
| `SENTRY_ENVIRONMENT` | `backend/.env` | Optional. Defaults to `development` for `APP_ENV=dev/test`, otherwise `production.lan`. |
| `VITE_SENTRY_DSN` | `frontend/.env.production.lan.local` (build time, git-ignored) | Web DSN. Unset: Sentry off in the browser. |
| `VITE_SENTRY_RELEASE` | build shell | Optional. Defaults to the short git sha. |
| `VITE_SENTRY_ENVIRONMENT` | build shell | Optional. Defaults to `production.lan` for production builds, else `development`. |
| `SENTRY_AUTH_TOKEN` | build shell only | Optional, enables source-map upload (below). |

Tests never set a DSN, so no test can send an event. The frontend tests also mock the SDK.

## What gets sent

Backend: unhandled server errors, when `SENTRY_DSN` is set. `send_default_pii=False`, no local variables, no request bodies. A `before_send` hook (`backend/app/core/sentry.py`) removes cookies, query strings, auth headers and the user's email/IP, masks emails, JWTs, bearer tokens and `password=`/`token=` pairs, and strips learner free-text fields (answers, transcripts, descriptions).

Web: automatic crash events depend on a per-device learner setting (Profile, "Crash reports"): Never send, Ask me each time (default), Always send. Nothing is sent before consent: the SDK's own global handlers are disabled, and `beforeSend` drops any event the learner did not approve. In Ask mode a small "Send a crash report?" prompt appears after an unhandled error. The setting lives in localStorage (`crash-report-consent`); there is no per-user preferences store on the backend.

"Report a problem" (Profile) sends a Sentry user-feedback item with an optional email, whatever the consent setting. Tags: `route` (ids templated out), `lesson_id`, `unit_id`, `course_id`, `item_id` where known, `release`, `environment`. If the web build has no DSN, the report goes to the app's own `POST /feedback` endpoint instead.

Grouping: both sides set a fingerprint from the exception type plus a message with ids and numbers normalised (and the route template on the backend), so one bug is one issue across ids.

The older automatic reporter (`frontend/src/lib/crashReporter.ts`, `POST /feedback` with category `app_bug`) goes through the same consent gate: Never sends nothing, Ask uses the same prompt, Always sends.

## Source maps

`npm run build` always emits hidden source maps (`dist/**/*.map`, no `sourceMappingURL` comment). Uploading them needs an auth token with `project:releases` and `org:read`. When `SENTRY_AUTH_TOKEN` is set in the build shell, `@sentry/vite-plugin` uploads them for release `VITE_SENTRY_RELEASE` (default git sha) and deletes them from `dist`. Without the token nothing is uploaded and the build is otherwise identical. The deploy rsync excludes `*.map`.

```bash
cd frontend
SENTRY_AUTH_TOKEN=... npm run build -- --mode production.lan
```

## Triage agent

`.claude/agents/sentry-triage.md` is a Claude Code subagent. It needs the Sentry MCP server (tools named `mcp__sentry__*`) and an authenticated `gh`. It reads new or unresolved issues and feedback from both projects, groups them, writes `.local/reports/sentry-triage-<date>.md`, and opens GitHub issues on `MindThaApp/LingoSquared` with the label `sentry` for new actionable ones, skipping any whose Sentry issue id already appears in an existing issue body. It never edits code.

Run it from the repo root in Claude Code: ask "Use the sentry-triage agent to triage the last 7 days", or `claude --agent sentry-triage` for a dedicated session. Review the report, then decide which issues to fix.
