#!/usr/bin/env bash
# Real-browser CSP check. Builds the frontend, serves it through backend/nginx.web.conf
# (the enforcing CSP) next to the API + Postgres in an ISOLATED compose project, seeds the
# demo courses, then drives headless Chromium (official Playwright image) through sign-up,
# a lesson, audio, a speaking exercise (whisper worker -> onnxruntime-web from jsDelivr),
# profile, change password, Privacy/Terms and an RTL course, collecting every CSP violation
# (securitypolicyviolation events + console errors). Exit 0 only with zero violations.
# Needs: docker, internet (jsDelivr + Hugging Face model, ~150 MB, for the speaking step).
# Usage: scripts/csp_browser_check.sh        Keeps nothing: stack is `down -v --rmi local`.
#   CSP_KEEP=1 keeps the stack up; CSP_WORK=<dir> keeps the work dir; CSP_OUT=<dir> copies report + screenshots;
#   CSP_SKIP_BUILD=1 reuses $CSP_WORK/dist.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PW_VERSION="${PW_VERSION:-1.56.1}"
PROJ="lscsp$$"
if [ -n "${CSP_WORK:-}" ]; then WORK="$CSP_WORK"; OWN_WORK=0; else WORK="$(mktemp -d "${TMPDIR:-/tmp}/lscsp.XXXXXX")"; OWN_WORK=1; fi
mkdir -p "$WORK/dist" "$WORK/out"
DC=(docker compose -p "$PROJ" -f "$WORK/compose.yml")
cleanup() {
  [ "${CSP_KEEP:-0}" = 1 ] && { echo "kept: ${DC[*]}"; return; }
  "${DC[@]}" down -v --rmi local --remove-orphans >/dev/null 2>&1
  # Keep out/ (report + screenshots) in $CSP_OUT if asked; node_modules are root-owned from the container.
  if [ "$OWN_WORK" = 1 ]; then
    [ -n "${CSP_OUT:-}" ] && { mkdir -p "$CSP_OUT"; cp -r "$WORK/out/." "$CSP_OUT/"; echo "report copied to $CSP_OUT"; }
    docker run --rm -v "$(dirname "$WORK"):/t" alpine rm -rf "/t/$(basename "$WORK")" >/dev/null 2>&1
  fi
}
trap cleanup EXIT

# 1. Frontend build (API on http://api:8010, matches the policy's http://*:8010; dummy Sentry DSN on an allowed host).
if [ "${CSP_SKIP_BUILD:-0}" != 1 ]; then
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e CI=1 \
    -e VITE_API_BASE_URL=http://api:8010 -e VITE_AUDIO_BASE_URL=/media/audio \
    -e VITE_SENTRY_DSN=https://0000000000000000@o0.ingest.de.sentry.io/0 -e VITE_SENTRY_ENVIRONMENT=csp-check \
    -v "$ROOT:/repo" -v "$WORK/dist:/out" -w /repo node:22-slim \
    sh -c 'npm ci --no-audit --no-fund >/dev/null && npm --workspace frontend exec -- vite build --outDir /out --emptyOutDir' \
    || { echo "frontend build failed" >&2; exit 2; }
fi

# 2. Isolated stack: db, api (port 8010), web (nginx with the real conf + built dist).
mkdir -p "$WORK/audio"
cat > "$WORK/compose.yml" <<YML
services:
  db:
    image: postgres:16-alpine
    environment: {POSTGRES_DB: ls, POSTGRES_USER: ls, POSTGRES_PASSWORD: csp-local}
    healthcheck: {test: ["CMD-SHELL","pg_isready -U ls -d ls"], interval: 2s, retries: 30}
  api:
    build: {context: $ROOT/backend, target: dev}
    image: ${PROJ}-api
    environment:
      APP_ENV: dev
      DATABASE_URL: postgresql+psycopg://ls:csp-local@db:5432/ls
      JWT_SECRET: csp-local-not-a-secret
      CORS_ORIGINS: http://web
      REGISTER_RATE_LIMIT_MAX: "1000"
      LOGIN_RATE_LIMIT_MAX: "1000"
      TTS_RATE_LIMIT_MAX: "1000"
      STT_RATE_LIMIT_MAX: "1000"
    depends_on: {db: {condition: service_healthy}}
    volumes: ["$ROOT/backend:/app:ro", "$WORK/audio:/srv/media/audio:ro"]
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

# 3a. Seed: a throwaway admin account (admins bypass the speaking-unit lock, so the speaking exercise is reachable).
ADMIN_EMAIL="csp-admin@example.com"; ADMIN_PW="csp-admin-pass-1"
"${DC[@]}" exec -T api python -c "
import json,urllib.request
r=urllib.request.Request('http://127.0.0.1:8010/auth/register',json.dumps({'email':'$ADMIN_EMAIL','password':'$ADMIN_PW','display_name':'CSP Admin'}).encode(),{'Content-Type':'application/json'})
urllib.request.urlopen(r)" >/dev/null && "${DC[@]}" exec -T api python -m app.scripts.promote_admin "$ADMIN_EMAIL" >/dev/null \
  || { echo "admin seed failed" >&2; exit 2; }

# 3b. Drive the browser (same compose network, so the origin is http://web).
cp "$ROOT/scripts/csp_browser/check.mjs" "$WORK/check.mjs"
docker run --rm --network "${PROJ}_default" --ipc=host -v "$WORK:/work" -w /work \
  -e ADMIN_EMAIL=$ADMIN_EMAIL -e ADMIN_PW=$ADMIN_PW -e BASE=http://web -e API=http://api:8010 -e OUT=/work/out \
  "mcr.microsoft.com/playwright:v${PW_VERSION}-jammy" \
  sh -c "npm i --no-audit --no-fund --silent playwright@${PW_VERSION} >/dev/null 2>&1; node check.mjs"
RC=$?
echo "report: $WORK/out/report.json (removed on exit unless CSP_OUT=<dir> or CSP_WORK is set)"
exit $RC
