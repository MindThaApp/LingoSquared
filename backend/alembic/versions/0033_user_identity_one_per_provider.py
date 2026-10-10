"""one social identity per provider per account

user_identities itself shipped in 0023. Social sign-in now links accounts
by verified email and lets a guest account adopt a provider identity, and
both paths rely on an account holding at most one identity per provider.
This enforces that with a unique index. Fresh 0001 schemas already create
it from the ORM model, so the DDL is guarded; an existing database that
somehow already holds duplicates is left untouched (and reported) rather
than failing the deploy.
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
            "SELECT count(*) FROM (SELECT user_id, provider FROM user_identities "
            "GROUP BY user_id, provider HAVING count(*) > 1) AS d"
        )
    ).scalar()
    if duplicates:
        print(
            f"0033: {duplicates} account(s) hold several identities of one provider; "
            f"{_INDEX} not created. Resolve them, then run alembic downgrade 0032 and upgrade head."
        )
        return
    op.create_index(_INDEX, _TABLE, ["user_id", "provider"], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in inspector.get_table_names():
        return
    if _INDEX in {index["name"] for index in inspector.get_indexes(_TABLE)}:
        op.drop_index(_INDEX, table_name=_TABLE)
