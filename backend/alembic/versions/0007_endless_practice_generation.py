"""add Endless Practice templates, generated items, and attempts"""

from alembic import op

from app.models import PracticeAttempt, PracticeItem, PracticeTemplate


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Additive only. Templates are stable reviewed content, items are
    # short-lived server-held answer keys, and attempts are history.
    for table in (
        PracticeTemplate.__table__,
        PracticeItem.__table__,
        PracticeAttempt.__table__,
    ):
        table.create(bind=bind, checkfirst=True)


def downgrade():
    raise RuntimeError(
        "0007 downgrade is intentionally unsupported because it would remove "
        "reviewed practice content and append-only attempt history. Restore a "
        "verified pre-upgrade backup instead."
    )
