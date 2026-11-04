#!/usr/bin/env bash
# Browser-less CSP check: serves a built frontend/dist through the real
# backend/nginx.web.conf in a throwaway nginx container, then verifies
#   1. the enforcing Content-Security-Policy header is sent on /, a hashed asset and the SPA fallback;
#   2. index.html has no inline script/handler and every script/style/link/img it loads is same-origin;
#   3. every absolute URL in the built JS that this policy cannot reach is listed (informational).
# Usage: scripts/csp_check.sh [path-to-dist]   (default frontend/dist; build first)
# Only touches its own container (name csp-check-$$), removed on exit.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$(cd "${1:-$ROOT/frontend/dist}" && pwd)" || { echo "dist not found" >&2; exit 2; }
NAME="csp-check-$$"; PORT="${CSP_CHECK_PORT:-18099}"; FAIL=0
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1; }
trap cleanup EXIT
docker run -d --name "$NAME" -p "127.0.0.1:$PORT:80" \
  -v "$ROOT/backend/nginx.web.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$DIST:/usr/share/nginx/html:ro" nginx:alpine >/dev/null || exit 2
for _ in $(seq 20); do curl -fs "http://127.0.0.1:$PORT/" >/dev/null && break; sleep 0.5; done
ASSET="$(ls "$DIST/assets" | grep '\.js$' | head -1)"
for path in / "/assets/$ASSET" /some/spa/route; do
  h="$(curl -sI "http://127.0.0.1:$PORT$path" | tr -d '\r')"
  csp="$(printf '%s\n' "$h" | grep -i '^content-security-policy:' | grep -vi report-only)"
  if [ -z "$csp" ]; then echo "FAIL no enforcing CSP on $path"; FAIL=1; else echo "ok   enforcing CSP on $path"; fi
  if printf '%s\n' "$h" | grep -qi 'report-only'; then echo "FAIL report-only still sent on $path"; FAIL=1; fi
done
HTML="$(curl -s "http://127.0.0.1:$PORT/")"
# Inline script / event handler / inline javascript: URL are blocked by script-src 'self'.
if printf '%s' "$HTML" | python3 -c '
import re,sys
h=sys.stdin.read(); bad=[]
for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>",h,re.S|re.I):
    if "src=" not in m.group(1) and m.group(2).strip(): bad.append("inline <script>")
bad+=["inline handler "+m for m in re.findall(r"\son[a-z]+=",h)]
bad+=["javascript: url" for _ in re.findall(r"javascript:",h,re.I)]
refs=re.findall(r"(?:src|href)=[\"\x27](https?:)?//([^\"\x27/]+)",h)
bad+=["external ref "+r[1] for r in refs]
print("\n".join(bad)); sys.exit(1 if bad else 0)'; then echo "ok   index.html: no inline script/handler, no external refs"; else echo "FAIL index.html has CSP-incompatible content (above)"; FAIL=1; fi
echo "info absolute https origins referenced in built JS (must be covered by the policy or be dormant):"
grep -rhoE 'https://[a-zA-Z0-9.-]+' "$DIST/assets" --include='*.js' 2>/dev/null | sort | uniq -c | sort -rn | head -25
[ "$FAIL" = 0 ] && echo "CSP CHECK PASS" || { echo "CSP CHECK FAIL"; exit 1; }
