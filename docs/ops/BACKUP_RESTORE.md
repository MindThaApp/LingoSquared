# Database backup and restore

Scripts: `scripts/ops/backup_db.sh` and `scripts/ops/restore_db.sh`. Nothing here is installed on the server; Ramin approves that separately. (The older `scripts/backup_db.sh` and `scripts/install_backup_cron.sh` are unchanged and separate; do not run both schedules.)

## Backup

```bash
cd /home/ramin/LingoSquared && scripts/ops/backup_db.sh
```

It runs `pg_dump` through `docker compose exec -T db`, gzips to `backend/backups/ops/lingosquared_<UTC stamp>.sql.gz`, then verifies the file (`gunzip -t`, minimum size, pg_dump completion marker). Only after verification does it rotate. If the server runs the prod override, export `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml` first.

Settings (environment variables): `BACKUP_DIR`, `KEEP` (default 14), `MIN_BYTES`, `COMPOSE_DIR`, `DB_SERVICE`, `DB_USER`, `DB_NAME`, `OFFSITE_DEST`, `OFFSITE_SSH_KEY`.

### Retention
The newest `KEEP` dumps are kept (default 14, so two weeks of nightly dumps). The script deletes only regular files in its own `BACKUP_DIR` whose name matches `lingosquared_<YYYYMMDDTHHMMSSZ>.sql.gz`, and only after a new dump verified. Other files in the folder (notes, pre-deploy dumps, anything renamed) are never touched. It never overwrites an existing dump.

### Off-box copy (off by default)
Set `OFFSITE_DEST=user@host:/path/lingosquared-db/` (and optionally `OFFSITE_SSH_KEY`). It uses `rsync -a --partial` without `--delete`, so the remote copy keeps everything and the remote side needs its own pruning. A failed rsync exits 3 but the local dump stays. A dump contains user data: use a destination you control, not shared storage. `scripts/ops/pull_backups.sh` (run from the dev PC) is an alternative pull model.

### Proposed cron line (NOT installed)
```
15 3 * * * cd /home/ramin/LingoSquared && OFFSITE_DEST= KEEP=14 scripts/ops/backup_db.sh >> backend/backups/ops/backup.log 2>&1
```
Add `OFFSITE_DEST=...` once a destination exists. Check `backup.log` after the first night, and set up a "no new dump in 26 hours" alert (Sentry cron monitor or a mail-on-failure) so silent failure is noticed.

## Restore drill (do this before launch, then monthly)
The drill never touches the live database. It restores into a new scratch database in the same Postgres container.

1. `scripts/ops/restore_db.sh backend/backups/ops/<newest>.sql.gz` creates `lingosquared_restore_<stamp>`, loads the dump and prints table count, user count and the alembic version. It refuses if that database exists.
2. Compare the user count and alembic head with the live values (`docker compose exec -T db psql -U lingosquared -tA -c "select count(*) from users"`).
3. Optional deeper check: point a throwaway API at the scratch DB (`DATABASE_URL` on a copy of `.env`, different port) and log in.
4. Drop it: re-run with `--cleanup` (drops the scratch DB that run created), or drop it by hand (`DROP DATABASE`). Note the date and the result in `.local/logs/`.
Disk needed is roughly the size of the database again while the scratch copy exists.

## Disaster recovery (live database lost or corrupt)
Only with Ramin's go-ahead. Stop the API (`docker compose stop api`), then
`scripts/ops/restore_db.sh <dump> --overwrite-live --confirm-live lingosquared`.
The script takes a safety backup first, refuses while other connections are open, renames the current live DB to `lingosquared_pre_restore_<stamp>` (nothing is dropped), creates a fresh DB and restores into it. Start the API, check `/health/ready`, and drop the renamed database by hand later. Anything written after the dump's timestamp is lost, so restore the newest good dump.
