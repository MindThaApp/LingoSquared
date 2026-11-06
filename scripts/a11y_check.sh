#!/usr/bin/env bash
# Accessibility check: axe-core (WCAG 2.0/2.1 A + AA rules, colour contrast ON) driven by Playwright in
# Docker against an ISOLATED local stack (db + api + nginx serving the production build, same recipe as
# scripts/csp_browser_check.sh). Covers landing, login/register, onboarding, course list, course/unit pages,
# every exercise type reachable in the demo courses, review, practice, vocabulary, profile, legal and an RTL
# (fa / ar) course, at desktop and 360px widths, in light and dark colour schemes. Also checks empty / error
# / offline states and horizontal overflow at 360px.
# Exit 1 on any serious or critical axe violation (moderate/minor are reported, not fatal), 2 on setup failure.
# Usage: scripts/a11y_check.sh      Keeps nothing: the stack is `down -v --rmi local`.
#   A11Y_KEEP=1 keeps the stack up; A11Y_WORK=<dir> keeps the work dir; A11Y_OUT=<dir> copies report + screenshots;
#   A11Y_SKIP_BUILD=1 reuses $A11Y_WORK/dist.  Needs docker + internet (npm, Playwright image).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PW_VERSION="${PW_VERSION:-1.56.1}"
PROJ="lsa11y$$"
if [ -n "${A11Y_WORK:-}" ]; then WORK="$A11Y_WORK"; OWN_WORK=0; else WORK="$(mktemp -d "${TMPDIR:-/tmp}/lsa11y.XXXXXX")"; OWN_WORK=1; fi
mkdir -p "$WORK/dist" "$WORK/out"
DC=(docker compose -p "$PROJ" -f "$WORK/compose.yml")
cleanup() {
  [ "${A11Y_KEEP:-0}" = 1 ] && { echo "kept: ${DC[*]}"; return; }
  "${DC[@]}" down -v --rmi local --remove-orphans >/dev/null 2>&1
  if [ "$OWN_WORK" = 1 ]; then
    [ -n "${A11Y_OUT:-}" ] && { mkdir -p "$A11Y_OUT"; cp -r "$WORK/out/." "$A11Y_OUT/"; echo "report copied to $A11Y_OUT"; }
    docker run --rm -v "$(dirname "$WORK"):/t" alpine rm -rf "/t/$(basename "$WORK")" >/dev/null 2>&1
  fi
}
trap cleanup EXIT

# 1. Frontend build (API on http://api:8010, matches the policy's http://*:8010; dummy Sentry DSN on an allowed host).
if [ "${A11Y_SKIP_BUILD:-0}" != 1 ]; then
  docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e CI=1 \
    -e VITE_API_BASE_URL=http://api:8010 -e VITE_AUDIO_BASE_URL=/media/audio \
    -e VITE_SENTRY_DSN=https://0000000000000000@o0.ingest.de.sentry.io/0 -e VITE_SENTRY_ENVIRONMENT=a11y-check \
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
    environment: {POSTGRES_DB: ls, POSTGRES_USER: ls, POSTGRES_PASSWORD: a11y-local}
    healthcheck: {test: ["CMD-SHELL","pg_isready -U ls -d ls"], interval: 2s, retries: 30}
  api:
    build: {context: $ROOT/backend, target: dev}
    image: ${PROJ}-api
    environment:
      APP_ENV: dev
      DATABASE_URL: postgresql+psycopg://ls:a11y-local@db:5432/ls
      JWT_SECRET: a11y-local-not-a-secret
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

# 3a. Seed: a throwaway admin account (admins bypass the speaking-unit lock, so every lesson is reachable).
ADMIN_EMAIL="a11y-admin@example.com"; ADMIN_PW="a11y-admin-pass-1"
"${DC[@]}" exec -T api python -c "
import json,urllib.request
r=urllib.request.Request('http://127.0.0.1:8010/auth/register',json.dumps({'email':'$ADMIN_EMAIL','password':'$ADMIN_PW','display_name':'A11y Admin'}).encode(),{'Content-Type':'application/json'})
urllib.request.urlopen(r)" >/dev/null && "${DC[@]}" exec -T api python -m app.scripts.promote_admin "$ADMIN_EMAIL" >/dev/null \
  || { echo "admin seed failed" >&2; exit 2; }

# 3a2. Extra fixture course (matching_pairs etc.).
"${DC[@]}" exec -T api python - < "$ROOT/scripts/a11y_browser/extra_course.py" || echo "WARN extra course seed failed" >&2

# 3b. Drive the browser (same compose network, so the origin is http://web).
cp "$ROOT/scripts/a11y_browser/check.mjs" "$WORK/check.mjs"
docker run --rm --network "${PROJ}_default" --ipc=host -v "$WORK:/work" -w /work \
  -e ADMIN_EMAIL=$ADMIN_EMAIL -e ADMIN_PW=$ADMIN_PW -e BASE=http://web -e API=http://api:8010 -e OUT=/work/out \
  "mcr.microsoft.com/playwright:v${PW_VERSION}-jammy" \
  sh -c "npm i --no-audit --no-fund --silent playwright@${PW_VERSION} axe-core@4.13.0 >/dev/null 2>&1; node check.mjs"
RC=$?
echo "report: $WORK/out/report.json (removed on exit unless A11Y_OUT=<dir> or A11Y_WORK is set)"
exit $RC
