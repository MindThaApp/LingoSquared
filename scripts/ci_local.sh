#!/usr/bin/env bash
# One-command local CI: runs every gate in docs/GATE_BASELINES.md and tears down.
#
#   scripts/ci_local.sh                 # all gates
#   scripts/ci_local.sh --skip-backend  # no Docker (content + frontend only)
#   scripts/ci_local.sh --skip-frontend
#   scripts/ci_local.sh --skip-content
#   scripts/ci_local.sh --with-build    # also frontend lint + `npm run build`
#
# Env: CI_WARN_MAX=<n>   fail if full-run WARN lines exceed n (the baseline is a
#                         formula in GATE_BASELINES.md; compute it for the commit and pass it)
#      CI_CONTENT_VENV=<dir>  python venv with scripts/requirements-content.txt + pytest
#      CI_KEEP=1          leave the compose project and temp files for debugging
#
# Backend tests run in an isolated compose project (lsci_<pid>: own db container,
# own network and volumes, no published ports), so the dev stack and its data are
# never touched. Everything it created is removed on exit, even on failure.
# Needs docker for the backend gate; ~10+ minutes in total.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
RUN_CONTENT=1; RUN_BACKEND=1; RUN_FRONTEND=1; WITH_BUILD=0
for a in "$@"; do case "$a" in
  --skip-backend) RUN_BACKEND=0;; --skip-frontend) RUN_FRONTEND=0;; --skip-content) RUN_CONTENT=0;;
  --with-build) WITH_BUILD=1;; -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
  *) echo "unknown arg $a" >&2; exit 2;; esac; done

PROJECT="lsci_$$"; TMP="$(mktemp -d)"; LOG="$TMP/logs"; mkdir -p "$LOG"
CREATED_ENV=0; CREATED_VENV_LINK=0; COMPOSE_UP=0
declare -a NAMES=() RESULTS=()
dc() { docker compose -p "$PROJECT" -f backend/docker-compose.yml -f "$TMP/override.yml" "$@"; }
cleanup() {
  [ "$COMPOSE_UP" = 1 ] && [ -z "${CI_KEEP:-}" ] && dc down -v --rmi local --remove-orphans >/dev/null 2>&1
  [ "$CREATED_ENV" = 1 ] && [ -z "${CI_KEEP:-}" ] && rm -f backend/.env
  [ "$CREATED_VENV_LINK" = 1 ] && rm -f .content-venv
  [ -z "${CI_KEEP:-}" ] && rm -rf "$TMP" || echo "kept: $TMP project $PROJECT"
}
trap cleanup EXIT
gate() { # gate <name> <cmd...>; full output goes to $LOG/<name>.log
  local n="$1"; shift; echo "== $n"
  if "$@" >"$LOG/$n.log" 2>&1; then NAMES+=("$n"); RESULTS+=("pass"); else
    NAMES+=("$n"); RESULTS+=("FAIL"); echo "-- tail of $n:"; tail -15 "$LOG/$n.log"; fi
}

if [ "$RUN_CONTENT" = 1 ]; then
  VENV="${CI_CONTENT_VENV:-}"
  [ -z "$VENV" ] && [ -d .content-venv ] && VENV="$ROOT/.content-venv"
  if [ -z "$VENV" ]; then # reuse the main checkout's venv when running from a worktree
    MAIN="$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')"
    [ -d "$MAIN/.content-venv" ] && VENV="$MAIN/.content-venv"
  fi
  if [ -z "$VENV" ]; then
    echo "== creating content venv"; python3 -m venv "$TMP/venv" && "$TMP/venv/bin/pip" -q install -r scripts/requirements-content.txt pytest >/dev/null 2>&1; VENV="$TMP/venv"
  fi
  [ -e .content-venv ] || { ln -s "$VENV" .content-venv; CREATED_VENV_LINK=1; }  # verify.sh sources ./.content-venv
  PY="$VENV/bin/python3"
  gate verify-content-only scripts/verify.sh --content-only
  WARNS="$(grep -c '^WARN' "$LOG/verify-content-only.log" || true)"
  echo "   WARN lines (baseline formula in GATE_BASELINES.md): $WARNS"
  if [ -n "${CI_WARN_MAX:-}" ] && [ "$WARNS" -gt "$CI_WARN_MAX" ]; then NAMES+=("warn-count"); RESULTS+=("FAIL ($WARNS > $CI_WARN_MAX)"); fi
  echo "== answer-leakage"
  "$PY" scripts/_answer_leakage_check.py >"$LOG/leakage.log" 2>&1
  HITS="$(sed -n 's/^answer-leakage: \([0-9]*\) hit.*/\1/p' "$LOG/leakage.log" | head -1)"
  if [ -n "$HITS" ] && [ "$HITS" -le 36 ]; then NAMES+=("answer-leakage"); RESULTS+=("pass ($HITS <= 36)"); else NAMES+=("answer-leakage"); RESULTS+=("FAIL (hits=${HITS:-?}, max 36)"); fi
  gate scripts-pytest "$PY" -m pytest scripts/tests -q
fi

if [ "$RUN_BACKEND" = 1 ]; then
  if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; CREATED_ENV=1; fi
  cat >"$TMP/override.yml" <<YML
services:
  api:
    ports: !reset []
    volumes:
      - ${ROOT}:/repo:ro
    environment:
      LINGO_REPO_ROOT: /repo
  web:
    profiles: ["never"]
YML
  COMPOSE_UP=1
  echo "== backend pytest (compose project $PROJECT)"
  gate backend-pytest bash -c "
    set -e
    $(declare -f dc) ; PROJECT=$PROJECT TMP=$TMP
    dc up -d --wait db
    dc exec -T db createdb -U \"\${POSTGRES_USER:-lingosquared}\" lingosquared_test
    dc run --rm --no-deps api sh -c 'DATABASE_URL=\$(python3 -c \"import os,re; print(re.sub(r\\\"lingosquared\$\\\", \\\"lingosquared_test\\\", os.environ[\\\"DATABASE_URL\\\"]))\") python -m pytest -q --deselect tests/test_content_answer_shapes.py'
  "
  # project down happens in the trap
fi

if [ "$RUN_FRONTEND" = 1 ]; then
  [ -d node_modules ] || gate npm-ci npm ci
  pushd frontend >/dev/null
  if [ "$WITH_BUILD" = 1 ]; then gate lint npm run lint; gate build npm run build; fi
  VITE_API_BASE_URL=http://localhost:8000 gate vitest npx vitest run
  popd >/dev/null
fi

echo; echo "================ ci_local summary (logs: $LOG) ================"
RC=0
for i in "${!NAMES[@]}"; do printf '  %-22s %s\n' "${NAMES[$i]}" "${RESULTS[$i]}"; case "${RESULTS[$i]}" in FAIL*) RC=1;; esac; done
echo "==============================================================="
rm -rf "${TMPDIR:-/tmp}/ci_local_last"; cp -r "$LOG" "${TMPDIR:-/tmp}/ci_local_last" 2>/dev/null && echo "logs copied to ${TMPDIR:-/tmp}/ci_local_last"
exit $RC
