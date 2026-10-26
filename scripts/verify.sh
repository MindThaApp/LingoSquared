#!/usr/bin/env bash
# One-command local verification: compiler validation + backend pytest +
# full frontend build. Built by Session 3 (INFRA) per
# docs/SONNET_BUILD_PROMPT_UPGRADES.md so every session gets the same
# pass/fail summary instead of re-deriving the recipe (and its footguns)
# from CLAUDE.md each time.
#
# Ownership note: the backend-test stage touches the LOCAL Docker stack's
# test database. Per the parallel-session ownership map in
# docs/SONNET_BUILD_PROMPT_UPGRADES.md, the Docker stack has ONE owner at
# a time (Session 1/CODE by default) -- if you are not that owner, run
# with --content-only or --frontend-only instead of the full suite.
#
# Usage:
#   scripts/verify.sh                 # content + backend + frontend (default; fast, no browser)
#   scripts/verify.sh --content-only  # compiler validation only (no Docker)
#   scripts/verify.sh --backend-only  # backend pytest only
#   scripts/verify.sh --frontend-only # npm run build only
#   scripts/verify.sh --skip-backend  # content + frontend, skip Docker
#   scripts/verify.sh --e2e           # ALSO run the e2e/ Playwright suite
#   scripts/verify.sh --e2e-only      # ONLY the e2e suite
#
# The e2e stage is opt-in, not part of the default run: it needs a
# live seeded backend (a precondition it doesn't provision, see
# e2e/README.md) and `npm install`/browser install in e2e/ the first
# time, so it's slower and more environment-dependent than the other
# three stages -- keeping it out of the default run means a missing
# Playwright install never fails the fast checks sessions run constantly.
#
# Deliberately does NOT use `docker compose --env-file` anywhere -- that
# flag only affects docker-compose.yml variable substitution, not the
# container's actual environment, and using it for tests once ran the
# suite against the LIVE database. See CLAUDE.md footguns.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RUN_CONTENT=1
RUN_BACKEND=1
RUN_FRONTEND=1
RUN_E2E=0

for arg in "$@"; do
  case "$arg" in
    --content-only)  RUN_BACKEND=0; RUN_FRONTEND=0 ;;
    --backend-only)  RUN_CONTENT=0; RUN_FRONTEND=0 ;;
    --frontend-only) RUN_CONTENT=0; RUN_BACKEND=0 ;;
    --skip-backend)  RUN_BACKEND=0 ;;
    --skip-content)  RUN_CONTENT=0 ;;
    --skip-frontend) RUN_FRONTEND=0 ;;
    --e2e)           RUN_E2E=1 ;;
    --e2e-only)      RUN_CONTENT=0; RUN_BACKEND=0; RUN_FRONTEND=0; RUN_E2E=1 ;;
    -h|--help)
      grep '^#' "${BASH_SOURCE[0]}" | sed 's/^#//'; exit 0 ;;
    *)
      echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

CONTENT_STATUS="skipped"
BACKEND_STATUS="skipped"
FRONTEND_STATUS="skipped"
E2E_STATUS="skipped"

# ---------------------------------------------------------------------------
# Stage 1: compiler validation (no Docker needed -- .content-venv only)
# ---------------------------------------------------------------------------
if [ "$RUN_CONTENT" = "1" ]; then
  echo "== Stage 1/3: content compiler validation =========================="
  if [ ! -d .content-venv ]; then
    echo "!! .content-venv not found -- run: python3 -m venv .content-venv && .content-venv/bin/pip install -r scripts/requirements-content.txt"
    CONTENT_STATUS="fail"
  else
    # shellcheck disable=SC1091
    source .content-venv/bin/activate
    CONTENT_OK=1

    if ! ls scripts/manifest.d/content/*.txt >/dev/null 2>&1; then
      echo "!! scripts/manifest.d/content/*.txt not found -- nothing to validate"
      CONTENT_OK=0
    else
      COMPILE_SCRATCH="$(mktemp -d)"
      trap 'rm -rf "$COMPILE_SCRATCH"' EXIT
      while IFS='|' read -r course realizations overlays; do
        [ -z "$course" ] && continue
        case "$course" in \#*) continue ;; esac
        echo "-- validating $course --"
        # shellcheck disable=SC2086
        if ! python scripts/compile_content.py validate \
              --realization $realizations \
              --overlay $overlays; then
          echo "!! validation FAILED for $course"
          CONTENT_OK=0
        fi
        # `validate` alone misses checks that only run during real assembly
        # (e.g. validate_dialogue_teaching_card) -- confirmed 2026-07-05 when
        # this exact gap let a compile-breaking dialogue-format bug through
        # "0 errors, 0 warnings" in every prior verify.sh run. Always also
        # run the real `compile` against scratch output so this class of bug
        # can't hide behind a clean validate pass again.
        echo "-- compiling $course (full assembly, not just validate) --"
        # shellcheck disable=SC2086
        if ! python scripts/compile_content.py compile \
              --realization $realizations \
              --overlay $overlays \
              --out "$COMPILE_SCRATCH/${course}.json"; then
          echo "!! COMPILE FAILED for $course (validate passed but real assembly did not)"
          CONTENT_OK=0
        fi
      done < <(LC_ALL=C cat scripts/manifest.d/content/*.txt)
    fi

    if ls scripts/manifest.d/practice/*.txt >/dev/null 2>&1; then
      while IFS='|' read -r pack_name packs; do
        [ -z "$pack_name" ] && continue
        case "$pack_name" in \#*) continue ;; esac
        echo "-- validating practice pack: $pack_name --"
        # shellcheck disable=SC2086
        if ! python scripts/compile_content.py practice-validate \
              --pack $packs \
              --content-root docs/content/realizations; then
          echo "!! practice validation FAILED for $pack_name"
          CONTENT_OK=0
        fi
      done < <(LC_ALL=C cat scripts/manifest.d/practice/*.txt)
    fi

    # German text left in a non-de learner-language overlay/pack (derive_direction
    # once treated every teaching-card title as English and shipped German ones).
    echo "-- german-leftover check (non-de learner-language overlays + packs) --"
    if ! python scripts/_german_leftover_check.py; then
      echo "!! german-leftover check FAILED"
      CONTENT_OK=0
    fi

    deactivate 2>/dev/null || true
    [ "$CONTENT_OK" = "1" ] && CONTENT_STATUS="pass" || CONTENT_STATUS="fail"
  fi
  echo
fi

# ---------------------------------------------------------------------------
# Stage 2: backend pytest (isolated test DB, real Postgres via docker compose)
# ---------------------------------------------------------------------------
if [ "$RUN_BACKEND" = "1" ]; then
  echo "== Stage 2/3: backend pytest (isolated test DB) ====================="
  if ! docker compose -f backend/docker-compose.yml ps db 2>/dev/null | grep -q Up; then
    echo "!! Local Docker stack isn't up. Start Docker first (Docker Desktop, 'sudo service docker start' on WSL, or 'colima start' on macOS), then:"
    echo "     cd backend && docker compose up -d"
    BACKEND_STATUS="fail"
  else
    ( cd backend && \
      docker compose exec -T db dropdb -U "${POSTGRES_USER:-lingosquared}" --if-exists lingosquared_test && \
      docker compose exec -T db createdb -U "${POSTGRES_USER:-lingosquared}" lingosquared_test && \
      docker compose run --rm api sh -c \
        'DATABASE_URL=$(python3 -c "import os,re; print(re.sub(r\"lingosquared\$\", \"lingosquared_test\", os.environ[\"DATABASE_URL\"]))") python -m pytest -q' )
    if [ $? -eq 0 ]; then BACKEND_STATUS="pass"; else BACKEND_STATUS="fail"; fi
  fi
  echo
fi

# ---------------------------------------------------------------------------
# Stage 3: frontend build (full build, never just tsc --noEmit -- the full
# build has twice caught type errors noEmit alone missed, per CLAUDE.md)
# ---------------------------------------------------------------------------
if [ "$RUN_FRONTEND" = "1" ]; then
  echo "== Stage 3/3: frontend build (npm run build) ========================"
  ( cd frontend && npm run build )
  if [ $? -eq 0 ]; then FRONTEND_STATUS="pass"; else FRONTEND_STATUS="fail"; fi
  echo
fi

# ---------------------------------------------------------------------------
# Stage 4 (opt-in): e2e/ Playwright suite against a live seeded backend.
# See e2e/README.md for preconditions and known coverage gaps.
# ---------------------------------------------------------------------------
if [ "$RUN_E2E" = "1" ]; then
  echo "== Stage 4/4: e2e (Playwright) ======================================="
  if [ ! -d e2e/node_modules ]; then
    echo "!! e2e/node_modules not found -- run: cd e2e && npm install && npx playwright install --with-deps chromium"
    E2E_STATUS="fail"
  else
    ( cd e2e && npx playwright test )
    if [ $? -eq 0 ]; then E2E_STATUS="pass"; else E2E_STATUS="fail"; fi
  fi
  echo
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "======================================================================"
echo "  content:  $CONTENT_STATUS"
echo "  backend:  $BACKEND_STATUS"
echo "  frontend: $FRONTEND_STATUS"
echo "  e2e:      $E2E_STATUS"
echo "======================================================================"

for s in "$CONTENT_STATUS" "$BACKEND_STATUS" "$FRONTEND_STATUS" "$E2E_STATUS"; do
  if [ "$s" = "fail" ]; then exit 1; fi
done
exit 0
