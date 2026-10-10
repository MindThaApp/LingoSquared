"""server-issued nonces for Google/Apple sign-in

Each sign-in attempt now uses a nonce the server issued, stored (as its
SHA-256 digest) until it expires or a sign-in consumes it, so an intercepted
ID token plus nonce cannot be replayed. Fresh 0001 schemas already create
the table from the ORM model, so the DDL is guarded.
"""

import sqlalchemy as sa
from alembic import op


revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


_TABLE = "social_login_nonces"
_INDEX = "ix_social_login_nonces_expires_at"


def upgrade():
    bind = op.get_bind()
    if _TABLE in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        _TABLE,
        sa.Column("nonce_sha256", sa.String(length=64), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(_INDEX, _TABLE, ["expires_at"])


def downgrade():
    bind = op.get_bind()
    if _TABLE in sa.inspect(bind).get_table_names():
        op.drop_table(_TABLE)
