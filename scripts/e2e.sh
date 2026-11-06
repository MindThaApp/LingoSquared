#!/usr/bin/env bash
# Full-stack browser e2e of the main learner journeys (e2e/tests/journeys.spec.ts).
# Builds the frontend, serves it through backend/nginx.web.conf next to the
# API + Postgres in an ISOLATED compose project, seeds the demo courses plus a small de->ar cross
# pair (e2e/fixtures/de-ar.json), runs Playwright in the official image, tears everything down
# with `down -v --rmi local`. Same setup as scripts/csp_browser_check.sh.
# Sentry is not initialised (no DSN is built in) and TTS/audio requests are stubbed in the tests.
# The older e2e/tests specs (dari-course, refresh-tokens, desktop-layout) are not run by default.
# Needs: docker, internet (npm + Playwright image).
# Usage: scripts/e2e.sh [playwright args]   (default: tests/journeys.spec.ts; no retries, so flakes show)
#   E2E_KEEP=1 keeps the stack; E2E_WORK=<dir> keeps the work dir; E2E_OUT=<dir> copies the report;
#   E2E_SKIP_BUILD=1 reuses $E2E_WORK/dist.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PW_VERSION="${PW_VERSION:-1.56.1}"
PROJ="lse2e$$"
if [ -n "${E2E_WORK:-}" ]; then WORK="$E2E_WORK"; OWN_WORK=0; else WORK="$(mktemp -d "${TMPDIR:-/tmp}/lse2e.XXXXXX")"; OWN_WORK=1; fi
mkdir -p "$WORK/dist" "$WORK/out" "$WORK/audio"
DC=(docker compose -p "$PROJ" -f "$WORK/compose.yml")
cleanup() {
  [ "${E2E_KEEP:-0}" = 1 ] && { echo "kept: ${DC[*]}"; return; }
  "${DC[@]}" down -v --rmi local --remove-orphans >/dev/null 2>&1
  if [ "$OWN_WORK" = 1 ]; then
    [ -n "${E2E_OUT:-}" ] && { mkdir -p "$E2E_OUT"; cp -r "$WORK/out/." "$E2E_OUT/" 2>/dev/null; echo "report copied to $E2E_OUT"; }
    # node_modules / test-results are root-owned (written by the container).
    docker run --rm -v "$(dirname "$WORK"):/t" alpine rm -rf "/t/$(basename "$WORK")" >/dev/null 2>&1
  fi
}
trap cleanup EXIT

# 1. Frontend build (API on http://api:8010; no Sentry DSN, so Sentry never initialises).
if [ "${E2E_SKIP_BUILD:-0}" != 1 ]; then
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e CI=1 \
    -e VITE_API_BASE_URL=http://api:8010 -e VITE_AUDIO_BASE_URL=/media/audio \
    -v "$ROOT:/repo" -v "$WORK/dist:/out" -w /repo node:22-slim \
    sh -c 'npm ci --no-audit --no-fund >/dev/null && npm --workspace frontend exec -- vite build --outDir /out --emptyOutDir' \
    || { echo "frontend build failed" >&2; exit 2; }
fi

# 2. Isolated stack: db, api (port 8010), web (nginx with the real conf + built dist).
cat > "$WORK/compose.yml" <<YML
services:
  db:
    image: postgres:16-alpine
    environment: {POSTGRES_DB: ls, POSTGRES_USER: ls, POSTGRES_PASSWORD: e2e-local}
    healthcheck: {test: ["CMD-SHELL","pg_isready -U ls -d ls"], interval: 2s, retries: 30}
  api:
    build: {context: $ROOT/backend, target: dev}
    image: ${PROJ}-api
    environment:
      APP_ENV: dev
      DATABASE_URL: postgresql+psycopg://ls:e2e-local@db:5432/ls
      JWT_SECRET: e2e-local-not-a-secret
      CORS_ORIGINS: http://web
      REGISTER_RATE_LIMIT_MAX: "1000"
      LOGIN_RATE_LIMIT_MAX: "1000"
      TTS_RATE_LIMIT_MAX: "1000"
      STT_RATE_LIMIT_MAX: "1000"
    depends_on: {db: {condition: service_healthy}}
    volumes: ["$ROOT/backend:/app:ro", "$ROOT/e2e/fixtures:/fixtures:ro", "$WORK/audio:/srv/media/audio:ro"]
    command: sh -c "alembic upgrade head && python -m app.content.seed --with-demo-courses && uvicorn app.main:app --host 0.0.0.0 --port 8010"
    healthcheck: {test: ["CMD","python","-c","import urllib.request;urllib.request.urlopen('http://127.0.0.1:8010/health/ready',timeout=3)"], interval: 3s, retries: 60}
  web:
    image: nginx:alpine
    volumes:
      - $WORK/dist:/usr/share/nginx/html:ro
      - $ROOT/backend/nginx.web.conf:/etc/nginx/conf.d/default.conf:ro
      - $WORK/audio:/srv/media/audio:ro
YML
"${DC[@]}" up -d --build --wait --wait-timeout 300 api web || { "${DC[@]}" logs api | tail -30; exit 2; }

# 3. Seed the cross-pair fixture through the same import path as the admin import.
"${DC[@]}" exec -T -e PYTHONPATH=/app api python /fixtures/seed_fixtures.py || { echo "fixture seed failed" >&2; exit 2; }

# 4. Run Playwright (same compose network, so the origin is http://web). The e2e dir is copied so
#    the repo stays free of root-owned node_modules.
ARGS="tests/journeys.spec.ts"; [ $# -gt 0 ] && ARGS="$*"
mkdir -p "$WORK/e2e"
tar -C "$ROOT/e2e" --exclude=node_modules --exclude=test-results --exclude=playwright-report -cf - . | tar -C "$WORK/e2e" -xf -
docker run --rm --network "${PROJ}_default" --ipc=host -v "$WORK/e2e:/work" -w /work \
  -e CI=1 -e PLAYWRIGHT_BASE_URL=http://web -e E2E_API_BASE_URL=http://api:8010 \
  "mcr.microsoft.com/playwright:v${PW_VERSION}-jammy" \
  sh -c "npm i --no-save --no-package-lock --no-audit --no-fund --silent @playwright/test@${PW_VERSION} pg@8 >/dev/null 2>&1 && npx playwright test --retries=0 ${ARGS}"
RC=$?
mkdir -p "$WORK/out"; cp -r "$WORK/e2e/test-results/." "$WORK/out/" 2>/dev/null
exit $RC
