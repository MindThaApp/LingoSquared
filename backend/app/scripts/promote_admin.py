"""Promote an existing user to administrator access.

Run from ``backend/`` with ``python -m app.scripts.promote_admin EMAIL``.
"""

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import User


def promote_admin(db: Session, email: str) -> bool:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        return False
    user.is_admin = True
    db.commit()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant admin access to an existing account")
    parser.add_argument("email", help="email address of the existing account")
    args = parser.parse_args()

    with SessionLocal() as db:
        if not promote_admin(db, args.email):
            parser.error(f"No existing user found for {args.email!r}")
    print(f"Granted admin access to {args.email.strip().lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
