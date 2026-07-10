#!/usr/bin/env bash
# Install the nightly database-backup cron job (scripts/backup_db.sh).
#
# *** MEANT TO BE RUN MANUALLY, BY A HUMAN, ON THE TARGET MACHINE. ***
# This script modifies the invoking user's crontab. It exists so Ramin can
# run it himself on whatever machine should actually take the nightly
# backups (the home server, 192.168.4.4) — it should NOT be executed
# automatically by an agent, a deploy script, or CI against any machine,
# and never against the live server unattended. Run it as the user whose
# crontab should own the job (e.g. `ramin` on the server), from any
# directory:
#
#   /home/ramin/LingoSquared/scripts/install_backup_cron.sh
#
# What it does:
#   - Derives the repo root from this script's own location, so the
#     installed cron line points at the real path on THIS machine (no
#     hardcoded /home/ramin/... assumption).
#   - Checks the current user's crontab (`crontab -l`) for an existing
#     line that already invokes scripts/backup_db.sh. If found, prints it
#     and exits without changing anything (idempotent — safe to re-run).
#   - Otherwise appends the cron line below via the standard safe
#     read-modify-write pattern (dump existing crontab to a temp file,
#     append, `crontab <tempfile>`) — existing cron entries are preserved,
#     never overwritten.
#
# Schedule installed (same line documented in scripts/backup_db.sh):
#   0 3 * * *  — daily at 03:00 server-local time.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_SCRIPT="$REPO_ROOT/scripts/backup_db.sh"

if [ ! -x "$BACKUP_SCRIPT" ]; then
  echo "ERROR: $BACKUP_SCRIPT not found or not executable; refusing to install a cron job pointing at it" >&2
  exit 1
fi

CRON_LINE="0 3 * * * cd $REPO_ROOT && ./scripts/backup_db.sh >> backend/backup.log 2>&1"

# `crontab -l` exits non-zero when the user has no crontab at all; that is
# a normal starting state, not an error, so capture it without tripping
# `set -e`.
existing_crontab="$(crontab -l 2>/dev/null || true)"

# Idempotency check: look for any active (non-comment) line that invokes
# scripts/backup_db.sh, not just an exact match on $CRON_LINE — a manually
# tweaked schedule on the same script still counts as "already installed"
# and must not be duplicated.
existing_entry="$(printf '%s\n' "$existing_crontab" | grep -F 'scripts/backup_db.sh' | grep -v '^[[:space:]]*#' || true)"

if [ -n "$existing_entry" ]; then
  echo "Backup cron job already present; nothing to do:"
  printf '  %s\n' "$existing_entry"
  exit 0
fi

# Read-modify-write: never `crontab` a bare new line over the existing
# crontab — always append to a dump of what is already there.
tmp_file="$(mktemp)"
trap 'rm -f "$tmp_file"' EXIT

if [ -n "$existing_crontab" ]; then
  printf '%s\n' "$existing_crontab" > "$tmp_file"
fi
printf '%s\n' "$CRON_LINE" >> "$tmp_file"

crontab "$tmp_file"

echo "Installed backup cron job:"
printf '  %s\n' "$CRON_LINE"
if [ -n "$existing_crontab" ]; then
  echo "Existing crontab entries were preserved."
else
  echo "(No prior crontab existed for this user; this is now the only entry.)"
fi
