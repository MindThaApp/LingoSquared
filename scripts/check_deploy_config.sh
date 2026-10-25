#!/usr/bin/env bash
# check_deploy_config.sh — automated pre-deploy .env sanity check.
#
# Automates the two pre-deploy/pre-beta-invite checklist items from
# CLAUDE.md "Known limitations" and docs/PRE_DEPLOY_RUNBOOK.md's
# "Required environment variables" table, which until now were manual
# grep-and-eyeball steps (runbook pre-flight step 4):
#
#   FAIL  The .env file is group/world accessible (mode must be 600; it
#         holds JWT_SECRET, the DB password and cloud keys).
#   FAIL  APP_ENV is unset or dev/development/test on a deploy (the app
#         treats anything else as production; dev/test skips the startup
#         safety checks and labels Sentry events "development").
#   FAIL  JWT_SECRET is unset/empty, shorter than 32 characters, the
#         app-code default ("development-only-secret",
#         backend/app/core/config.py), or the .env.example placeholder
#         ("replace-with-a-long-random-secret"). The app itself refuses to
#         start in a production-like APP_ENV in these cases.
#   FAIL  POSTGRES_PASSWORD or DATABASE_URL still carries the
#         .env.example placeholder password ("change-me") — runbook table
#         row "confirm they're real values, not .env.example placeholders."
#   WARN  CORS_ORIGINS consists ONLY of localhost/127.0.0.1 origins (or is
#         empty). Fails safe (requests rejected) but breaks the app for
#         every real beta user until the real frontend origin is added — a
#         product decision for Ramin, so WARN not FAIL.
#   WARN  SENTRY_DSN is empty (crash reporting off; optional).
#   WARN  GOOGLE_CLOUD_TTS_CREDENTIALS_JSON is empty — /tts degrades
#         gracefully to browser speechSynthesis, so not a deploy blocker,
#         but the 8 Google-covered languages get no cloud TTS.
#   WARN  AZURE_SPEECH_KEY is empty — same graceful degradation; fa TTS
#         won't actually work until Ramin provisions an Azure Speech
#         resource (runbook: NOT a deploy blocker).
#
# Usage:
#   scripts/check_deploy_config.sh <path-to-.env>
#   scripts/check_deploy_config.sh backend/.env
#
# For the live server, pull the file locally first (read-only) rather than
# giving this script SSH access, e.g.:
#   ssh ramin@192.168.4.4 cat /home/ramin/LingoSquared/backend/.env > /tmp/live.env
#   scripts/check_deploy_config.sh /tmp/live.env && rm /tmp/live.env
#
# Exits non-zero if any FAIL-level check trips. WARN-level findings are
# printed but never fail the run. Secret VALUES are never printed — only
# non-sensitive values (ADMIN_EMAILS, CORS_ORIGINS) appear in output.

set -u

if [ $# -ne 1 ]; then
  echo "usage: $0 <path-to-.env>" >&2
  exit 2
fi

ENV_FILE="$1"
if [ ! -f "$ENV_FILE" ]; then
  echo "error: env file not found: $ENV_FILE" >&2
  exit 2
fi

FAILS=0
WARNS=0

fail() { echo "FAIL  $1"; FAILS=$((FAILS + 1)); }
warn() { echo "WARN  $1"; WARNS=$((WARNS + 1)); }
ok()   { echo "ok    $1"; }

# Read a var from the env file: last occurrence wins (matches how docker
# compose's env_file treats duplicates), optional "export " prefix allowed,
# surrounding single/double quotes stripped, CR stripped (in case the file
# was ever edited on/for another platform). Values may themselves contain
# '=' (the Google credential is raw JSON) — split on the FIRST '=' only.
get_var() {
  local key="$1"
  grep -E "^[[:space:]]*(export[[:space:]]+)?${key}=" "$ENV_FILE" \
    | tail -n 1 \
    | sed -E "s/^[[:space:]]*(export[[:space:]]+)?${key}=//" \
    | tr -d '\r' \
    | sed -E "s/^[\"']//; s/[\"']\$//" \
    | sed -E 's/[[:space:]]+$//'
}

echo "Pre-deploy config check: $ENV_FILE"
echo "(FAIL = must fix before deploy; WARN = degrades gracefully, fix when decided)"
echo

# --- File mode ----------------------------------------------------------------
MODE="$(stat -c %a "$ENV_FILE" 2>/dev/null || stat -f %Lp "$ENV_FILE" 2>/dev/null || echo unknown)"
if [ "$MODE" = "600" ] || [ "$MODE" = "400" ]; then
  ok   ".env file mode is $MODE"
else
  fail ".env file mode is $MODE, must be 600 (chmod 600 <file>). It holds JWT_SECRET, the DB password and cloud keys. NOTE: a copy pulled over ssh gets your local umask, so run this check on the server file itself or compare 'stat -c %a' there."
fi

# --- APP_ENV ------------------------------------------------------------------
APP_ENV="$(get_var APP_ENV)"
case "$(printf '%s' "$APP_ENV" | tr 'A-Z' 'a-z')" in
  "")
    fail "APP_ENV is unset — the app defaults to production, but set it explicitly (APP_ENV=production) so the deploy is unambiguous." ;;
  dev|development|test)
    fail "APP_ENV=$APP_ENV on a deploy — dev/test skips the startup safety checks (JWT secret strength, DB password). Use APP_ENV=production." ;;
  *)
    ok   "APP_ENV=$APP_ENV (production-like)" ;;
esac

# --- SENTRY_DSN (optional) ----------------------------------------------------
SENTRY_DSN="$(get_var SENTRY_DSN)"
if [ -z "$SENTRY_DSN" ]; then
  warn "SENTRY_DSN is empty — server crash reporting is off (optional; see docs/SENTRY.md)."
else
  ok   "SENTRY_DSN is set (value not printed)"
fi

# --- CORS_ORIGINS ------------------------------------------------------------
CORS_ORIGINS="$(get_var CORS_ORIGINS)"
if [ -z "$CORS_ORIGINS" ]; then
  warn "CORS_ORIGINS is unset or empty — every browser request will be rejected."
else
  NON_LOCAL=""
  # Origins are comma-separated; a host is "local" if it is localhost,
  # 127.0.0.1, 0.0.0.0, or [::1] (any scheme, any port).
  OLD_IFS="$IFS"; IFS=','
  for origin in $CORS_ORIGINS; do
    origin="$(printf '%s' "$origin" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    [ -z "$origin" ] && continue
    host="$(printf '%s' "$origin" | sed -E 's#^[a-zA-Z][a-zA-Z0-9+.-]*://##; s#/.*$##; s#:[0-9]+$##')"
    case "$host" in
      localhost|127.0.0.1|0.0.0.0|\[::1\]) ;;
      *) NON_LOCAL="$NON_LOCAL $origin" ;;
    esac
  done
  IFS="$OLD_IFS"
  if [ -z "$NON_LOCAL" ]; then
    warn "CORS_ORIGINS is localhost/127.0.0.1 only — fine for local dev, but breaks the app for every real beta user on a live deploy. Needs the real frontend origin(s) (Ramin's call, don't guess). Current value: $CORS_ORIGINS"
  else
    ok   "CORS_ORIGINS includes non-localhost origin(s):$NON_LOCAL"
  fi
fi

# --- JWT_SECRET ---------------------------------------------------------------
JWT_SECRET="$(get_var JWT_SECRET)"
if [ -z "$JWT_SECRET" ]; then
  fail "JWT_SECRET is unset or empty — the app silently falls back to the hardcoded dev default ('development-only-secret', backend/app/core/config.py), so every token is forgeable."
elif [ "$JWT_SECRET" = "development-only-secret" ]; then
  fail "JWT_SECRET is the hardcoded app-code default ('development-only-secret') — every token is forgeable. Set a real random secret. (Never regenerate on a RUNNING deploy without warning Ramin — invalidates all sessions.)"
elif [ "${#JWT_SECRET}" -lt 32 ]; then
  fail "JWT_SECRET is shorter than 32 characters — the app refuses to start with it in a production-like APP_ENV. Generate one with: openssl rand -hex 32 (but never regenerate on a RUNNING deploy without warning Ramin — invalidates all sessions)."
elif [ "$JWT_SECRET" = "replace-with-a-long-random-secret" ]; then
  fail "JWT_SECRET is the .env.example placeholder — set a real random secret. (Never regenerate on a RUNNING deploy without warning Ramin — invalidates all sessions.)"
else
  ok   "JWT_SECRET is set and not a known default/placeholder (value not printed)"
fi

# --- POSTGRES_PASSWORD / DATABASE_URL ----------------------------------------
POSTGRES_PASSWORD="$(get_var POSTGRES_PASSWORD)"
DATABASE_URL="$(get_var DATABASE_URL)"
if [ "$POSTGRES_PASSWORD" = "change-me" ]; then
  fail "POSTGRES_PASSWORD is the .env.example placeholder ('change-me')."
elif [ -n "$POSTGRES_PASSWORD" ]; then
  ok   "POSTGRES_PASSWORD is set and not the placeholder (value not printed)"
fi
if printf '%s' "$DATABASE_URL" | grep -q 'change-me'; then
  fail "DATABASE_URL still carries the .env.example placeholder password ('change-me')."
fi

# --- TTS credentials (WARN only — graceful degradation by design) -------------
GOOGLE_TTS="$(get_var GOOGLE_CLOUD_TTS_CREDENTIALS_JSON)"
if [ -z "$GOOGLE_TTS" ]; then
  warn "GOOGLE_CLOUD_TTS_CREDENTIALS_JSON is empty — cloud TTS for the 8 Google-covered languages falls back to browser speechSynthesis. Not a blocker, but confirm this is intentional (and if set later, verify the key isn't the corrupted one from the 2026-07-04 incident — runbook open question #1)."
else
  ok   "GOOGLE_CLOUD_TTS_CREDENTIALS_JSON is non-empty (contents not printed or validated — a corrupted key still needs the CLAUDE.md debug path to detect)"
fi

AZURE_KEY="$(get_var AZURE_SPEECH_KEY)"
if [ -z "$AZURE_KEY" ]; then
  warn "AZURE_SPEECH_KEY is empty — fa (Farsi) TTS falls back to browser speechSynthesis. Not a blocker per the runbook; needs Ramin to provision an Azure Speech resource."
else
  ok   "AZURE_SPEECH_KEY is non-empty (value not printed)"
  AZURE_REGION="$(get_var AZURE_SPEECH_REGION)"
  if [ -z "$AZURE_REGION" ]; then
    warn "AZURE_SPEECH_KEY is set but AZURE_SPEECH_REGION is empty — Azure TTS needs both."
  fi
fi

# --- Summary -------------------------------------------------------------------
echo
if [ "$FAILS" -gt 0 ]; then
  echo "RESULT: $FAILS FAIL, $WARNS WARN — do NOT deploy this .env until every FAIL above is fixed."
  echo "See docs/PRE_DEPLOY_RUNBOOK.md 'Required environment variables' for what each value needs to be."
  exit 1
elif [ "$WARNS" -gt 0 ]; then
  echo "RESULT: 0 FAIL, $WARNS WARN — deployable, but review the warnings above (graceful degradations and product decisions, not blockers)."
  exit 0
else
  echo "RESULT: all checks passed."
  exit 0
fi
