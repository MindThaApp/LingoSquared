#!/usr/bin/env bash
# Restore a dump made by backup_db.sh into a NEW scratch database (drill).
#
# Usage:
#   restore_db.sh DUMP.sql.gz [--target-db NAME] [--cleanup]
#   restore_db.sh DUMP.sql.gz --overwrite-live --confirm-live NAME
#
# Default mode creates a brand-new database (default name
# lingosquared_restore_<UTC stamp>), restores into it, prints table/row
# sanity counts, and leaves it in place for inspection. It refuses if the
# target already exists or equals the live DB name. --cleanup drops the
# scratch DB THIS RUN created, when done.
#
# --overwrite-live (disaster recovery only): the API must be stopped. It takes
# a safety backup first, then RENAMES the live DB to <live>_pre_restore_<stamp>
# (nothing is dropped), creates a fresh live DB and restores into it. It also
# needs --confirm-live <live db name>.
#
# Config env: COMPOSE_DIR, DB_SERVICE, DB_USER, DB_NAME (same as backup_db.sh).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_DIR="${COMPOSE_DIR:-$REPO_ROOT/backend}"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${DB_USER:-lingosquared}"
DB_NAME="${DB_NAME:-lingosquared}"

usage() { sed -n '2,20p' "${BASH_SOURCE[0]}"; exit 2; }
[ $# -ge 1 ] || usage
DUMP="$1"; shift
TARGET=""; CLEANUP=0; LIVE=0; CONFIRM=""
while [ $# -gt 0 ]; do
  case "$1" in
    --target-db) TARGET="${2:-}"; shift 2 ;;
    --cleanup) CLEANUP=1; shift ;;
    --overwrite-live) LIVE=1; shift ;;
    --confirm-live) CONFIRM="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

[ -f "$DUMP" ] || { echo "ERROR: dump not found: $DUMP" >&2; exit 2; }
gunzip -t "$DUMP" || { echo "ERROR: dump fails gzip check" >&2; exit 1; }

stamp="$(date -u +%Y%m%dt%H%M%Sz)"  # lowercase: used in DB names
valid_name() { [[ "$1" =~ ^[a-z][a-z0-9_]{0,62}$ ]]; }

cd "$COMPOSE_DIR"
psql_admin() { docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -tA "$@"; }
db_exists() { [ "$(psql_admin -c "SELECT 1 FROM pg_database WHERE datname='$1'")" = "1" ]; }
load_into() {
  gunzip -c "$DUMP" | docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$1" -v ON_ERROR_STOP=1 -q -o /dev/null
}

if [ "$LIVE" -eq 1 ]; then
  [ "$CONFIRM" = "$DB_NAME" ] || { echo "ERROR: --overwrite-live needs --confirm-live $DB_NAME" >&2; exit 2; }
  others="$(psql_admin -c "SELECT count(*) FROM pg_stat_activity WHERE datname='$DB_NAME' AND pid <> pg_backend_pid()")"
  [ "$others" = "0" ] || { echo "ERROR: $others open connection(s) to $DB_NAME; stop the api first" >&2; exit 1; }
  echo "Taking safety backup first ..."
  "$SCRIPT_DIR/backup_db.sh"
  old="${DB_NAME}_pre_restore_${stamp}"
  valid_name "$old" || { echo "ERROR: bad name $old" >&2; exit 1; }
  psql_admin -c "ALTER DATABASE \"$DB_NAME\" RENAME TO \"$old\""
  psql_admin -c "CREATE DATABASE \"$DB_NAME\""
  load_into "$DB_NAME"
  echo "Live DB restored. Previous live data kept as database: $old (drop it by hand when satisfied)."
  exit 0
fi

TARGET="${TARGET:-${DB_NAME}_restore_${stamp}}"
valid_name "$TARGET" || { echo "ERROR: invalid database name: $TARGET" >&2; exit 2; }
[ "$TARGET" != "$DB_NAME" ] || { echo "ERROR: target equals the live DB; use --overwrite-live deliberately" >&2; exit 2; }
if db_exists "$TARGET"; then
  echo "ERROR: database $TARGET already exists; refusing to touch it" >&2
  exit 1
fi

psql_admin -c "CREATE DATABASE \"$TARGET\""
echo "Created scratch database $TARGET; restoring ..."
load_into "$TARGET"
echo "Restore finished. Sanity check:"
docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$TARGET" -tA -c \
  "SELECT 'public tables: ' || count(*) FROM information_schema.tables WHERE table_schema='public'"
docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$TARGET" -tA -c \
  "SELECT 'users: ' || count(*) FROM users" 2>/dev/null || echo "(no users table)"
docker compose exec -T "$DB_SERVICE" psql -U "$DB_USER" -d "$TARGET" -tA -c \
  "SELECT 'alembic version: ' || version_num FROM alembic_version" 2>/dev/null || true

if [ "$CLEANUP" -eq 1 ]; then
  psql_admin -c "DROP DATABASE \"$TARGET\""   # only the scratch DB this run created
  echo "Dropped scratch database $TARGET"
else
  echo "Scratch database kept: $TARGET (drop: docker compose exec -T $DB_SERVICE psql -U $DB_USER -d postgres -c 'DROP DATABASE \"$TARGET\"')"
fi
