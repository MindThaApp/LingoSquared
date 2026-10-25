"""Scheduled housekeeping: ``python -m app.maintenance [job ...]``.

The app has no job scheduler for these (only the in-process push loop), so
this is a plain CLI meant to be run daily from cron. See
docs/PRE_DEPLOY_RUNBOOK.md ("Scheduled housekeeping"). Jobs:

- refresh_tokens: delete expired / long-revoked refresh tokens
- attachments:    delete expired orphan feedback attachments (rows + files)
- practice_items: delete expired, unanswered practice items nothing references
- nonces:         delete expired social sign-in nonces

With no arguments all jobs run. Each job commits on its own, so one failing
job does not roll back the others; the exit code is 1 if any job failed.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, exists, select

from app.db.session import SessionLocal
from app.models import PracticeAttempt, PracticeItem, SocialLoginNonce
from app.models.entities import ContentIssueReport
from app.scripts.prune_refresh_tokens import prune_refresh_tokens
from app.services.feedback_attachments import sweep_expired_orphan_attachments

logger = logging.getLogger("app.maintenance")

# Items are only useful until they expire; keep them a while longer for
# debugging and late client retries before deleting.
PRACTICE_ITEM_GRACE = timedelta(days=7)
PRACTICE_PRUNE_CHUNK = 5000


def prune_practice_items(db, now_value: datetime | None = None) -> int:
    """Delete expired items that were never answered and are not referenced
    by an attempt or a content report (both FKs are RESTRICT)."""
    now_value = now_value or datetime.now(timezone.utc)
    cutoff = now_value - PRACTICE_ITEM_GRACE
    total = 0
    while True:
        ids = list(
            db.scalars(
                select(PracticeItem.id)
                .where(
                    PracticeItem.expires_at < cutoff,
                    PracticeItem.answered_at.is_(None),
                    ~exists().where(PracticeAttempt.practice_item_id == PracticeItem.id),
                    ~exists().where(ContentIssueReport.practice_item_id == PracticeItem.id),
                )
                .limit(PRACTICE_PRUNE_CHUNK)
            )
        )
        if not ids:
            break
        db.execute(delete(PracticeItem).where(PracticeItem.id.in_(ids)))
        db.commit()
        total += len(ids)
    return total


def prune_social_nonces(db, now_value: datetime | None = None) -> int:
    now_value = now_value or datetime.now(timezone.utc)
    result = db.execute(delete(SocialLoginNonce).where(SocialLoginNonce.expires_at <= now_value))
    db.commit()
    return result.rowcount or 0


def sweep_attachments(db) -> int:
    count = sweep_expired_orphan_attachments(db)
    db.commit()
    return count


JOBS = {
    "refresh_tokens": prune_refresh_tokens,
    "attachments": sweep_attachments,
    "practice_items": prune_practice_items,
    "nonces": prune_social_nonces,
}


def run(names: list[str] | None = None) -> dict[str, int]:
    results: dict[str, int] = {}
    for name in names or list(JOBS):
        with SessionLocal() as db:
            results[name] = JOBS[name](db)
    return results


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    names = list(sys.argv[1:] if argv is None else argv)
    unknown = [n for n in names if n not in JOBS]
    if unknown:
        print(f"unknown job(s): {', '.join(unknown)}; choose from {', '.join(JOBS)}", file=sys.stderr)
        return 2
    failed = 0
    for name in names or list(JOBS):
        try:
            with SessionLocal() as db:
                count = JOBS[name](db)
            logger.info("%s: removed %d", name, count)
        except Exception:
            failed += 1
            logger.exception("%s: failed", name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
