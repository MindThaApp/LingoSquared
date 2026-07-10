#!/usr/bin/env bash
# Evening "your streak ends tonight" push trigger.
#
# The backend deliberately has no built-in scheduler (see the docstring on
# POST /admin/push/notify-streaks-at-risk in backend/app/api/router.py) —
# an external cron hits the admin trigger endpoint instead, same pattern
# as /admin/push/notify-due-reviews. This script logs in as the admin
# account and fires the trigger once.
#
# Manual activation step on the live server: install ONE cron entry with
# `crontab -e` after this script has been deployed:
#
#   0 19 * * * cd /home/ramin/LingoSquared && LINGO_ADMIN_EMAIL=... LINGO_ADMIN_PASSWORD_FILE=/home/ramin/.lingo_admin_pw ./scripts/trigger_streak_notifications.sh >> backend/streak_push.log 2>&1
#
# Why a single 19:00 UTC run, and the tradeoff:
#   - The endpoint itself is timezone-correct per user (it skips anyone
#     already active TODAY in their own timezone, using the same
#     activity_day_bounds() day boundary the streak bookkeeping uses), so
#     firing at any hour never falsely warns someone whose streak is safe.
#   - What a single UTC time can't do is make "tonight" feel like evening
#     for everyone: 19:00 UTC is 8-9pm in NL/UK (this app's current user
#     base), but morning in e.g. Australia. Good enough until there's a
#     real far-flung user population.
#   - Do NOT schedule this more than once per evening: the endpoint has no
#     per-day send dedup, so a second run re-notifies every user who is
#     STILL inactive — two pushes for the same missed day. If a second run
#     targeting another timezone population is ever wanted (e.g. 03:00 UTC
#     for Asia-Pacific evenings), per-user/per-day dedup must be added to
#     the endpoint first.
#
# Configuration (environment variables — never hardcode credentials here,
# this file is committed):
#   LINGO_API_BASE            backend base URL (default http://localhost:8010)
#   LINGO_ADMIN_EMAIL         admin account email (required)
#   LINGO_ADMIN_PASSWORD_FILE path to a file containing ONLY the admin
#                             password (required; a file rather than an env
#                             var so the secret never appears in `ps` output
#                             or crontab. chmod 600 it.)
#
# Manual run from the repo root:
#   LINGO_ADMIN_EMAIL=... LINGO_ADMIN_PASSWORD_FILE=... ./scripts/trigger_streak_notifications.sh

set -euo pipefail

API_BASE="${LINGO_API_BASE:-http://localhost:8010}"

if [ -z "${LINGO_ADMIN_EMAIL:-}" ] || [ -z "${LINGO_ADMIN_PASSWORD_FILE:-}" ]; then
  echo "ERROR: LINGO_ADMIN_EMAIL and LINGO_ADMIN_PASSWORD_FILE must be set" >&2
  exit 1
fi
if [ ! -r "$LINGO_ADMIN_PASSWORD_FILE" ]; then
  echo "ERROR: cannot read password file: $LINGO_ADMIN_PASSWORD_FILE" >&2
  exit 1
fi

# Login payload is fed to curl via stdin (-d @-) so the password never
# appears as a process argument. The token is used inline and never
# persisted to disk (standing project rule on credentials in scratch files).
token="$(
  python3 - "$LINGO_ADMIN_EMAIL" "$LINGO_ADMIN_PASSWORD_FILE" <<'PY' |
import json, sys
email = sys.argv[1]
with open(sys.argv[2]) as f:
    password = f.read().strip()
print(json.dumps({"email": email, "password": password}))
PY
  curl -sS -f -X POST "$API_BASE/auth/login" \
    -H "Content-Type: application/json" -d @- \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"

response="$(curl -sS -f -X POST "$API_BASE/admin/push/notify-streaks-at-risk" \
  -H "Authorization: Bearer $token")"

echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") notify-streaks-at-risk: $response"
