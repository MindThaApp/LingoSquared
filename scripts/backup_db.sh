#!/usr/bin/env bash
# Nightly database backup for the Docker Compose Postgres service.
#
# Manual activation step on the live server: run
# `./scripts/install_backup_cron.sh` (idempotent, preserves existing cron
# entries) after this script has been deployed — or install the entry by
# hand with `crontab -e`:
# 0 3 * * * cd /home/ramin/LingoSquared && ./scripts/backup_db.sh >> backend/backup.log 2>&1
#
# Manual run from the repo root:
# ./scripts/backup_db.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
BACKUP_DIR="$BACKEND_DIR/backups"
COMPOSE_FILE="$BACKEND_DIR/docker-compose.yml"

DB_SERVICE="db"
DB_USER="lingosquared"
DB_NAME="lingosquared"
RETENTION_DAYS=14

timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
backup_file="$BACKUP_DIR/${DB_NAME}_${timestamp}.sql.gz"
tmp_file="${backup_file}.tmp"

mkdir -p "$BACKUP_DIR"
rm -f "$tmp_file"

if ! docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE" pg_dump -U "$DB_USER" "$DB_NAME" | gzip -c > "$tmp_file"; then
  rm -f "$tmp_file"
  echo "ERROR: pg_dump failed; no backup was written" >&2
  exit 1
fi

if [ ! -s "$tmp_file" ]; then
  rm -f "$tmp_file"
  echo "ERROR: backup file is empty; refusing to save it" >&2
  exit 1
fi

mv "$tmp_file" "$backup_file"
find "$BACKUP_DIR" -type f -name "${DB_NAME}_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete

echo "Wrote database backup: $backup_file"
