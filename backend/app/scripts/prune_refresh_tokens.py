"""Delete expired refresh tokens and tokens revoked over seven days ago."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_

from app.db.session import SessionLocal
from app.models import RefreshToken


def prune_refresh_tokens(db, now_value: datetime | None = None) -> int:
    now_value = now_value or datetime.now(timezone.utc)
    revoked_cutoff = now_value - timedelta(days=7)
    result = db.execute(
        delete(RefreshToken).where(
            or_(
                RefreshToken.expires_at <= now_value,
                RefreshToken.revoked_at <= revoked_cutoff,
            )
        )
    )
    db.commit()
    return result.rowcount or 0


def main() -> int:
    with SessionLocal() as db:
        deleted = prune_refresh_tokens(db)
    print(f"Pruned {deleted} refresh token rows.")
    return deleted


if __name__ == "__main__":
    main()
