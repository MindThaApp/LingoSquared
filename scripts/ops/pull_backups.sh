#!/usr/bin/env bash
# Pull a copy of the live server's backups to this machine.
#
#   1. makes a fresh pg_dump on the server (same method as the pre-deploy
#      dumps: `docker compose exec -T db pg_dump | gzip`) into ~/backups
#   2. rsyncs dumps, media and env backups into <repo>/backups/ (no --delete)
#   3. keeps the 30 newest daily dumps locally (pre_deploy/pre_00* dumps are kept)
#   4. gzip -t the newest dump, append to backups/pull.log
#
# Does not install any scheduling. Never prints secrets.
# Usage: scripts/ops/pull_backups.sh   (run from anywhere)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# secrets/ is untracked and lives in the main checkout; fall back to a worktree's sibling.
SSH_KEY="${SSH_KEY:-$REPO_ROOT/secrets/ssh/id_ed25519}"
[ -f "$SSH_KEY" ] || SSH_KEY="$HOME/AI/Projects/LingoSquared/secrets/ssh/id_ed25519"
REMOTE="${REMOTE:-ramin@192.168.4.4}"
DEST="${DEST:-$REPO_ROOT/backups}"
KEEP_DAILY=30
STAMP="$(date +%Y%m%d_%H%M)"
DUMP_NAME="lingosquared_daily_${STAMP}.sql.gz"

SSH_OPTS=(-i "$SSH_KEY" -o BatchMode=yes -o StrictHostKeyChecking=accept-new)
ssh_r() { ssh "${SSH_OPTS[@]}" "$REMOTE" "$@"; }
RSYNC=(rsync -a --partial -e "ssh ${SSH_OPTS[*]}")

mkdir -p "$DEST"/{dumps,media,env,crontab}
LOG="$DEST/pull.log"
log() { printf '%s %s\n' "$(date -Is)" "$*" | tee -a "$LOG"; }
trap 'log "FAILED (line $LINENO)"' ERR
umask 077

log "start remote=$REMOTE"

# 1. fresh dump on the server (write to .tmp, move only if non-empty and valid)
ssh_r "set -e; cd ~/LingoSquared/backend && mkdir -p ~/backups \
  && docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db pg_dump -U lingosquared lingosquared | gzip -c > ~/backups/$DUMP_NAME.tmp \
  && [ -s ~/backups/$DUMP_NAME.tmp ] && gzip -t ~/backups/$DUMP_NAME.tmp \
  && mv ~/backups/$DUMP_NAME.tmp ~/backups/$DUMP_NAME"
log "remote dump created: $DUMP_NAME"

# 2. rsync (no --delete)
"${RSYNC[@]}" --include='lingosquared_*.sql.gz' --exclude='*' "$REMOTE:backups/" "$DEST/dumps/"
"${RSYNC[@]}" "$REMOTE:lingosquared-media/" "$DEST/media/"
"${RSYNC[@]}" --include='env_*.bak' --exclude='*' "$REMOTE:backups/" "$DEST/env/"
"${RSYNC[@]}" --include='crontab*' --exclude='*' "$REMOTE:backups/" "$DEST/crontab/"
# current .env (not stored in ~/backups), dated copy
ssh_r 'cat ~/LingoSquared/backend/.env' > "$DEST/env/env_live_$STAMP.bak"
chmod 600 "$DEST"/env/* "$DEST"/crontab/* 2>/dev/null || true
chmod 700 "$DEST/env" "$DEST/crontab"

# 3. retention: newest KEEP_DAILY daily dumps; pre_deploy / pre_00* are never pruned
# shellcheck disable=SC2012
ls -1t "$DEST"/dumps/lingosquared_daily_*.sql.gz 2>/dev/null | tail -n +$((KEEP_DAILY + 1)) | while read -r f; do
  rm -f -- "$f"; log "pruned $(basename "$f")"
done

# 4. verify newest dump
newest="$(ls -1t "$DEST"/dumps/lingosquared_*.sql.gz | head -n1)"
gzip -t "$newest"
log "verified gzip -t OK: $(basename "$newest")"

files="$(find "$DEST" -type f ! -name pull.log | wc -l)"
log "done files=$files size=$(du -sh "$DEST" | cut -f1) dumps=$(ls "$DEST"/dumps | wc -l) media=$(du -sh "$DEST/media" | cut -f1)"
