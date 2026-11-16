#!/usr/bin/env bash
# Database backup for the Docker Compose Postgres service `db`.
#
#   pg_dump (via `docker compose exec -T db`) -> gzip -> verify -> rotate
#   -> optional off-box rsync.
#
# NOT scheduled by anything. See docs/ops/BACKUP_RESTORE.md for the proposed
# cron line. Does not touch the legacy scripts/backup_db.sh.
#
# Safety:
#   * Only ever writes NEW files named lingosquared_<UTC stamp>.sql.gz inside
#     its own BACKUP_DIR; it refuses to overwrite an existing file.
#   * Retention deletes ONLY regular files in BACKUP_DIR whose name matches
#     that exact pattern, and only after the new dump has been verified.
#   * The only other delete is its own in-progress *.part file on failure.
#   * The off-box copy is rsync WITHOUT --delete.
#
# Config (environment variables, all optional):
#   COMPOSE_DIR     dir with the compose file   (default <repo>/backend)
#   DB_SERVICE      compose service name        (default db)
#   DB_USER / DB_NAME                           (default lingosquared)
#   BACKUP_DIR      where dumps go              (default <repo>/backend/backups/ops)
#   KEEP            number of dumps to keep     (default 14)
#   MIN_BYTES       smallest plausible gz dump  (default 2048)
#   OFFSITE_DEST    rsync destination, e.g. user@host:/path/ (default empty = off)
#   OFFSITE_SSH_KEY optional ssh identity for the rsync
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_DIR="${COMPOSE_DIR:-$REPO_ROOT/backend}"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${DB_USER:-lingosquared}"
DB_NAME="${DB_NAME:-lingosquared}"
BACKUP_DIR="${BACKUP_DIR:-$REPO_ROOT/backend/backups/ops}"
KEEP="${KEEP:-14}"
MIN_BYTES="${MIN_BYTES:-2048}"
OFFSITE_DEST="${OFFSITE_DEST:-}"
OFFSITE_SSH_KEY="${OFFSITE_SSH_KEY:-}"

case "$KEEP" in ''|*[!0-9]*) echo "ERROR: KEEP must be a positive integer" >&2; exit 2 ;; esac
[ "$KEEP" -ge 1 ] || { echo "ERROR: KEEP must be >= 1" >&2; exit 2; }

NAME_PREFIX="lingosquared_"
NAME_REGEX='^lingosquared_[0-9]{8}T[0-9]{6}Z\.sql\.gz$'

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
final="$BACKUP_DIR/${NAME_PREFIX}${stamp}.sql.gz"
part="${final}.part"

mkdir -p "$BACKUP_DIR"
if [ -e "$final" ] || [ -e "$part" ]; then
  echo "ERROR: $final (or its .part) already exists; refusing to overwrite" >&2
  exit 1
fi

cleanup_part() { [ -f "$part" ] && rm -f -- "$part"; return 0; }  # our own temp file only
trap cleanup_part EXIT

cd "$COMPOSE_DIR"
echo "Dumping $DB_NAME from service $DB_SERVICE ..."
if ! docker compose exec -T "$DB_SERVICE" pg_dump -U "$DB_USER" --no-owner --no-privileges "$DB_NAME" \
     | gzip -c > "$part"; then
  echo "ERROR: pg_dump failed; nothing saved" >&2
  exit 1
fi

# Verify: gzip integrity, size, and the pg_dump end marker (detects truncation).
gunzip -t "$part" || { echo "ERROR: gzip integrity check failed" >&2; exit 1; }
size="$(stat -c %s "$part")"
if [ "$size" -lt "$MIN_BYTES" ]; then
  echo "ERROR: dump is only $size bytes (< $MIN_BYTES); refusing to keep it" >&2
  exit 1
fi
if ! gunzip -c "$part" | tail -n 5 | grep -q "PostgreSQL database dump complete"; then
  echo "ERROR: dump has no completion marker (truncated?)" >&2
  exit 1
fi

mv -n -- "$part" "$final"   # -n: never overwrite
[ -f "$final" ] || { echo "ERROR: could not finalize backup" >&2; exit 1; }
echo "OK: wrote $final ($size bytes, verified)"

# Retention: newest KEEP survive; delete only own-pattern regular files in BACKUP_DIR.
# The glob expands in lexical order = oldest first (UTC stamps); collect matches, drop the oldest extras.
matches=()
for f in "$BACKUP_DIR"/"${NAME_PREFIX}"*.sql.gz; do
  base="$(basename "$f")"
  [[ "$base" =~ $NAME_REGEX ]] && [ -f "$f" ] && [ ! -L "$f" ] && matches+=("$f")
done
excess=$(( ${#matches[@]} - KEEP ))
for ((k = 0; k < excess; k++)); do
  rm -f -- "${matches[$k]}"
  echo "Retention: removed old backup $(basename "${matches[$k]}")"
done

# Optional off-box copy (additive; no --delete).
if [ -n "$OFFSITE_DEST" ]; then
  ssh_cmd="ssh -o BatchMode=yes"
  [ -n "$OFFSITE_SSH_KEY" ] && ssh_cmd="$ssh_cmd -i $OFFSITE_SSH_KEY"
  if rsync -a --partial -e "$ssh_cmd" "$final" "$OFFSITE_DEST"; then
    echo "Off-box copy OK -> $OFFSITE_DEST"
  else
    echo "WARNING: off-box rsync failed (local backup is fine)" >&2
    exit 3
  fi
else
  echo "Off-box copy: disabled (OFFSITE_DEST not set)"
fi
