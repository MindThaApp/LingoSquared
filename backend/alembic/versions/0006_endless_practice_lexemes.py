"""add the reviewed lexeme pool for Endless Practice Phase 1"""

from alembic import op

from app.models import Lexeme


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Additive only. Course is part of lexical identity: the same surface form
    # may be introduced at a different lesson or with a different beginner-safe
    # sense in another course. POS also remains in the unique key so true
    # homographs can occupy different typed template slots.
    Lexeme.__table__.create(bind=bind, checkfirst=True)


def downgrade():
    raise RuntimeError(
        "0006 downgrade is intentionally unsupported because it would remove "
        "reviewed lexeme provenance consumed by Endless Practice. Restore a "
        "verified pre-upgrade backup instead."
    )
