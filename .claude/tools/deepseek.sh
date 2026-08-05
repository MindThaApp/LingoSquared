#!/usr/bin/env bash
# Delegate a self-contained task to DeepSeek (OpenAI-compatible API).
#
# Usage:
#   .claude/tools/deepseek.sh [--model deepseek-chat|deepseek-reasoner] [--system <file>] <prompt-file>
#   echo "prompt text" | .claude/tools/deepseek.sh [--model ...]        # prompt on stdin
#
# Models: deepseek-chat (V3, fast/general) | deepseek-reasoner (R1, deeper reasoning)
# Default: deepseek-chat.
#
# API key resolution (never commit a key; key lives OUTSIDE the repo):
#   1. $DEEPSEEK_API_KEY
#   2. ~/.deepseek_api_key   (chmod 600)
#
# Prints the model's message content to stdout; errors + HTTP status to stderr.
set -euo pipefail

MODEL="deepseek-chat"
SYSTEM_FILE=""
PROMPT_FILE=""
BASE_URL="${DEEPSEEK_BASE_URL:-https://api.deepseek.com}"

while [ $# -gt 0 ]; do
  case "$1" in
    --model)  MODEL="$2"; shift 2 ;;
    --system) SYSTEM_FILE="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) PROMPT_FILE="$1"; shift ;;
  esac
done

KEY="${DEEPSEEK_API_KEY:-}"
if [ -z "$KEY" ] && [ -f "$HOME/.deepseek_api_key" ]; then
  KEY="$(tr -d '\n' < "$HOME/.deepseek_api_key")"
fi
if [ -z "$KEY" ]; then
  echo "deepseek.sh: no API key. Set \$DEEPSEEK_API_KEY or create ~/.deepseek_api_key (chmod 600)." >&2
  exit 2
fi

command -v jq   >/dev/null || { echo "deepseek.sh: jq required" >&2; exit 3; }
command -v curl >/dev/null || { echo "deepseek.sh: curl required" >&2; exit 3; }

# Read the prompt from the given file or stdin.
if [ -n "$PROMPT_FILE" ]; then
  [ -f "$PROMPT_FILE" ] || { echo "deepseek.sh: prompt file not found: $PROMPT_FILE" >&2; exit 4; }
  PROMPT_SRC="$PROMPT_FILE"
else
  PROMPT_SRC="$(mktemp)"; trap 'rm -f "$PROMPT_SRC"' EXIT
  cat > "$PROMPT_SRC"
fi

# Build the request body safely with jq --rawfile (no shell-injection of prompt content).
if [ -n "$SYSTEM_FILE" ]; then
  BODY="$(jq -n --arg m "$MODEL" --rawfile sys "$SYSTEM_FILE" --rawfile usr "$PROMPT_SRC" \
    '{model:$m, stream:false, messages:[{role:"system",content:$sys},{role:"user",content:$usr}]}')"
else
  BODY="$(jq -n --arg m "$MODEL" --rawfile usr "$PROMPT_SRC" \
    '{model:$m, stream:false, messages:[{role:"user",content:$usr}]}')"
fi

RESP="$(curl -sS -w '\n%{http_code}' "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  --data "$BODY")"

STATUS="$(printf '%s' "$RESP" | tail -n1)"
PAYLOAD="$(printf '%s' "$RESP" | sed '$d')"

if [ "$STATUS" != "200" ]; then
  echo "deepseek.sh: HTTP $STATUS" >&2
  printf '%s\n' "$PAYLOAD" | jq -r '.error.message // .' >&2 2>/dev/null || printf '%s\n' "$PAYLOAD" >&2
  exit 5
fi

printf '%s' "$PAYLOAD" | jq -r '.choices[0].message.content'
