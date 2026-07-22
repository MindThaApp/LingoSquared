#!/usr/bin/env bash
# sync_dev_db.sh — one-command sync of all on-disk content into the LOCAL dev
# backend (http://localhost:8000 by default). Prompts for the admin password
# interactively; the credential is never written to disk or shell history.
#
# Order matters (documented in docs/PRE_DEPLOY_RUNBOOK.md and CLAUDE.md):
#   1. content import   (POST /admin/content/import, per content_manifest.txt)
#   2. lexeme backfills (docker compose run with full-repo mount)
#   3. practice import  (POST /admin/courses/{id}/practice/import, per practice_manifest.txt)
#
# Usage:  ./scripts/sync_dev_db.sh [API_BASE]
#         API_BASE defaults to http://localhost:8000
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_PORT="$(grep -m1 '^API_PORT=' "$REPO_ROOT/backend/.env" 2>/dev/null | cut -d= -f2)"
API="${1:-http://localhost:${DEFAULT_PORT:-8000}}"
PY="$REPO_ROOT/.content-venv/bin/python"
[ -x "$PY" ] || PY=python3

# Non-interactive mode (same convention as trigger_streak_notifications.sh):
# set LINGO_ADMIN_EMAIL and LINGO_ADMIN_PASSWORD_FILE (a chmod-600 file
# containing ONLY the password, e.g. ~/.lingo_admin_pw). Falls back to
# interactive prompts when unset. The password never appears in argv,
# shell history, or any file this script writes.
if [ -n "${LINGO_ADMIN_EMAIL:-}" ] && [ -r "${LINGO_ADMIN_PASSWORD_FILE:-}" ]; then
  ADMIN_EMAIL="$LINGO_ADMIN_EMAIL"
  ADMIN_PASSWORD="$(cat "$LINGO_ADMIN_PASSWORD_FILE")"
else
  read -r -p "Admin email: " ADMIN_EMAIL
  read -r -s -p "Admin password: " ADMIN_PASSWORD; echo
fi

TMPDIR_SYNC=""
cleanup() {
  unset ADMIN_PASSWORD
  [ -z "$TMPDIR_SYNC" ] || rm -rf "$TMPDIR_SYNC"
}
trap cleanup EXIT

login() {
  local new_token
  if ! new_token=$(
    {
      printf '%s\n' "$ADMIN_EMAIL"
      printf '%s' "$ADMIN_PASSWORD"
    } | "$PY" -c '
import json
import sys

email = sys.stdin.readline().rstrip("\n")
password = sys.stdin.read()
print(json.dumps({"email": email, "password": password}))
' | curl -sf "$API/auth/login" -H 'Content-Type: application/json' --data-binary @- \
      | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
  ); then
    return 1
  fi
  [ -n "$new_token" ] || return 1
  TOKEN="$new_token"
}

api_request() {
  local output="$1"
  shift
  local http
  http=$(curl -s -o "$output" -w '%{http_code}' "$@" -H "Authorization: Bearer $TOKEN")
  if [ "$http" = "401" ]; then
    echo "   token expired; re-authenticating and retrying" >&2
    if ! login; then
      echo "   re-authentication failed" >&2
      printf '%s' "$http"
      return 0
    fi
    http=$(curl -s -o "$output" -w '%{http_code}' "$@" -H "Authorization: Bearer $TOKEN")
  fi
  printf '%s' "$http"
}

echo "== logging in =="
TOKEN=""
login || { echo "login failed"; exit 1; }
[ -n "$TOKEN" ] || { echo "login failed"; exit 1; }

TMPDIR_SYNC=$(mktemp -d)

echo "== 1/3 content import =="
while IFS='|' read -r COURSE REALS OVERLAYS; do
  echo "-- $COURSE"
  # A failing course must not abort the whole sync (e.g. another lane's
  # course with open validation errors) — skip it loudly and continue.
  # shellcheck disable=SC2086
  # ^ intentional ONLY for $REALS/$OVERLAYS, which must word-split into
  # separate --realization/--overlay args. Everything else stays quoted:
  # the repo path contains a space (iCloud 'Mobile Documents'), so an
  # unquoted "$PY" silently split and skipped EVERY course.
  if ! (cd "$REPO_ROOT" && "$PY" scripts/compile_content.py compile \
      --realization $REALS --overlay $OVERLAYS \
      --output "$TMPDIR_SYNC/content.json"); then
    echo "   COMPILE FAILED for $COURSE — SKIPPED (fix its validation errors separately)"
    FAILED_COURSES="${FAILED_COURSES:-} $COURSE"; continue
  fi
  HTTP=$(api_request "$TMPDIR_SYNC/resp.json" \
      "$API/admin/content/import" \
      -H 'Content-Type: application/json' \
      --data-binary @"$TMPDIR_SYNC/content.json")
  if [ "$HTTP" != "200" ]; then
    echo "   IMPORT FAILED ($HTTP) for $COURSE — SKIPPED: $(head -c 300 "$TMPDIR_SYNC/resp.json")"
    FAILED_COURSES="${FAILED_COURSES:-} $COURSE"; continue
  fi
  "$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); print("   ", {k:v for k,v in d.items() if k!="warnings"}); w=d.get("warnings") or []; [print("    warn:", x) for x in w[:5]]' "$TMPDIR_SYNC/resp.json"
done < <(grep -v '^\s*#' "$REPO_ROOT/scripts/content_manifest.txt" | grep -v '^\s*$')

echo "== 2/3 lexeme backfills (docker, full-repo mount) =="
# When syncing a REMOTE deployment, set LINGO_BACKFILL_SSH (e.g.
# ramin@192.168.4.4) and LINGO_REMOTE_REPO (default /home/ramin/LingoSquared):
# backfills must run against THAT host's DB, not the local one.
if [ -n "${LINGO_BACKFILL_SSH:-}" ]; then
  RREPO="${LINGO_REMOTE_REPO:-/home/ramin/LingoSquared}"
  for BF in "$REPO_ROOT"/scripts/backfill_lexemes*.py; do
    NAME=$(basename "$BF")
    echo "-- $NAME (remote: $LINGO_BACKFILL_SSH)"
    ssh "$LINGO_BACKFILL_SSH" "cd $RREPO/backend && docker compose run --rm -v $RREPO:/repo -e PYTHONPATH=/repo/backend --entrypoint python api /repo/scripts/$NAME"
  done
else
  cd "$REPO_ROOT/backend"
  for BF in "$REPO_ROOT"/scripts/backfill_lexemes*.py; do
    NAME=$(basename "$BF")
    echo "-- $NAME"
    docker compose run --rm -v "$REPO_ROOT:/repo" -e PYTHONPATH=/repo/backend \
      --entrypoint python api "/repo/scripts/$NAME"
  done
  cd "$REPO_ROOT"
fi

echo "== 3/3 practice import =="
COURSES_JSON="$TMPDIR_SYNC/courses.json"
HTTP=$(api_request "$COURSES_JSON" "$API/courses")
if [ "$HTTP" != "200" ]; then
  echo "   COURSE LIST FAILED ($HTTP): $(head -c 300 "$COURSES_JSON")"
  exit 1
fi
while IFS='|' read -r DIRECTION PACKS; do
  echo "-- $DIRECTION"
  SRC=${DIRECTION%%-*}; TGT=${DIRECTION##*-}
  # Courses are split per CEFR level (e.g. "Farsi A1" vs "Farsi A2"), and the
  # practice importer 422s on templates whose lessons aren't in the target
  # course — so group packs by level prefix and import each group only into
  # the matching-level course.
  for LEVEL in a1 a2 b1 c1 c2; do
    LEVEL_PACKS=""
    for P in $PACKS; do
      case "$(basename "$P")" in "$LEVEL"_*) LEVEL_PACKS="$LEVEL_PACKS $P";; esac
    done
    [ -n "$LEVEL_PACKS" ] || continue
    CID=$("$PY" -c '
import json,sys
src,tgt,lvl=sys.argv[2],sys.argv[3],sys.argv[4].upper()
data=json.load(open(sys.argv[1]))
courses=data if isinstance(data,list) else data.get("courses",[])
matches=[c for c in courses
         if c.get("source_language")==src and c.get("target_language")==tgt
         and str(c.get("level","")).upper()==lvl]
# bootstrap demo courses share language pairs with real ones — pick the
# course with the most units, which is always the real imported course
if matches:
    print(max(matches, key=lambda c: c.get("unit_count") or 0)["id"])' "$COURSES_JSON" "$SRC" "$TGT" "$LEVEL")
    if [ -z "$CID" ]; then echo "   $LEVEL: no $DIRECTION course at this level -- skipping"; continue; fi
    # shellcheck disable=SC2086
    (cd "$REPO_ROOT" && "$PY" scripts/compile_content.py practice-compile \
        --pack $LEVEL_PACKS --content-root docs/content/realizations \
        --output "$TMPDIR_SYNC/practice.json")
    HTTP=$(api_request "$TMPDIR_SYNC/presp.json" \
        "$API/admin/courses/$CID/practice/import" \
        -H 'Content-Type: application/json' \
        --data-binary @"$TMPDIR_SYNC/practice.json")
    echo "   $LEVEL -> course $CID -> $HTTP: $(head -c 200 "$TMPDIR_SYNC/presp.json")"
  done
done < <(grep -v '^\s*#' "$REPO_ROOT/scripts/practice_manifest.txt" | grep -v '^\s*$')

echo "== done =="
