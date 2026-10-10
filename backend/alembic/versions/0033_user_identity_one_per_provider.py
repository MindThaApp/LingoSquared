"""one social identity per provider per account

user_identities itself shipped in 0023. Social sign-in now links accounts
by verified email and lets a guest account adopt a provider identity, and
both paths rely on an account holding at most one identity per provider.
This enforces that with a unique index. Fresh 0001 schemas already create
it from the ORM model, so the DDL is guarded. If an existing database
already holds duplicates the migration fails, naming the affected accounts,
instead of stamping 0033 without the index: the code relies on it.
"""

import sqlalchemy as sa
from alembic import op


revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


_TABLE = "user_identities"
_INDEX = "uq_user_identities_user_provider"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return
    if _INDEX in {index["name"] for index in inspector.get_indexes(_TABLE)}:
        return
    duplicates = bind.execute(
        sa.text(
            "SELECT user_id, provider, count(*) FROM user_identities "
            "GROUP BY user_id, provider HAVING count(*) > 1 ORDER BY user_id, provider"
        )
    ).all()
    if duplicates:
        listed = ", ".join(f"{row[0]} ({row[1]} x{row[2]})" for row in duplicates[:20])
        raise RuntimeError(
            f"0033: {len(duplicates)} account(s) hold several identities of one provider: "
            f"{listed}. Decide which identity each account keeps, delete the others from "
            f"user_identities, then run alembic upgrade head again."
        )
    op.create_index(_INDEX, _TABLE, ["user_id", "provider"], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return
    if _INDEX in {index["name"] for index in inspector.get_indexes(_TABLE)}:
        op.drop_index(_INDEX, table_name=_TABLE)
