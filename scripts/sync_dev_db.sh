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
API="${1:-http://localhost:8000}"
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

echo "== logging in =="
TOKEN=$(curl -sf "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
  | $PY -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
unset ADMIN_PASSWORD
[ -n "$TOKEN" ] || { echo "login failed"; exit 1; }

TMPDIR_SYNC=$(mktemp -d)
trap 'rm -rf "$TMPDIR_SYNC"' EXIT

echo "== 1/3 content import =="
grep -v '^\s*#' "$REPO_ROOT/scripts/content_manifest.txt" | grep -v '^\s*$' | \
while IFS='|' read -r COURSE REALS OVERLAYS; do
  echo "-- $COURSE"
  # shellcheck disable=SC2086
  (cd "$REPO_ROOT" && $PY scripts/compile_content.py compile \
      --realization $REALS --overlay $OVERLAYS \
      --output "$TMPDIR_SYNC/content.json")
  HTTP=$(curl -s -o "$TMPDIR_SYNC/resp.json" -w '%{http_code}' \
      "$API/admin/content/import" \
      -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
      --data-binary @"$TMPDIR_SYNC/content.json")
  if [ "$HTTP" != "200" ]; then
    echo "   IMPORT FAILED ($HTTP): $(cat "$TMPDIR_SYNC/resp.json")"; exit 1
  fi
  $PY -c 'import json,sys; d=json.load(open(sys.argv[1])); print("   ", {k:v for k,v in d.items() if k!="warnings"}); w=d.get("warnings") or []; [print("    warn:", x) for x in w[:5]]' "$TMPDIR_SYNC/resp.json"
done

echo "== 2/3 lexeme backfills (docker, full-repo mount) =="
cd "$REPO_ROOT/backend"
for BF in "$REPO_ROOT"/scripts/backfill_lexemes*.py; do
  NAME=$(basename "$BF")
  echo "-- $NAME"
  docker compose run --rm -v "$REPO_ROOT:/repo" -e PYTHONPATH=/repo/backend \
    --entrypoint python api "/repo/scripts/$NAME"
done
cd "$REPO_ROOT"

echo "== 3/3 practice import =="
COURSES_JSON="$TMPDIR_SYNC/courses.json"
curl -sf "$API/courses" -H "Authorization: Bearer $TOKEN" > "$COURSES_JSON"
grep -v '^\s*#' "$REPO_ROOT/scripts/practice_manifest.txt" | grep -v '^\s*$' | \
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
    CID=$($PY -c '
import json,sys
src,tgt,lvl=sys.argv[2],sys.argv[3],sys.argv[4].upper()
data=json.load(open(sys.argv[1]))
courses=data if isinstance(data,list) else data.get("courses",[])
for c in courses:
    if c.get("source_language")==src and c.get("target_language")==tgt and str(c.get("level","")).upper()==lvl:
        print(c["id"]); break' "$COURSES_JSON" "$SRC" "$TGT" "$LEVEL")
    if [ -z "$CID" ]; then echo "   $LEVEL: no $DIRECTION course at this level -- skipping"; continue; fi
    # shellcheck disable=SC2086
    (cd "$REPO_ROOT" && $PY scripts/compile_content.py practice-compile \
        --pack $LEVEL_PACKS --content-root docs/content/realizations \
        --output "$TMPDIR_SYNC/practice.json")
    HTTP=$(curl -s -o "$TMPDIR_SYNC/presp.json" -w '%{http_code}' \
        "$API/admin/courses/$CID/practice/import" \
        -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
        --data-binary @"$TMPDIR_SYNC/practice.json")
    echo "   $LEVEL -> course $CID -> $HTTP: $(head -c 200 "$TMPDIR_SYNC/presp.json")"
  done
done

echo "== done =="
