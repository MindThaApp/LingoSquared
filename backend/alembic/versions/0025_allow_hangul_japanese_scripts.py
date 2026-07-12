"""allow Hangul and Japanese language scripts

Widen the languages.script check constraint so Korean (hangul) and
Japanese (japanese) can be seeded. Same shape as 0018 (Devanagari).
Guarded so a fresh 0001-created schema, which already reflects current
models, does not fail when this migration reaches head.
"""

import sqlalchemy as sa
from alembic import op


revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

_TABLE = "languages"
_CHECK_NAME = "ck_languages_script"
_NEW_CHECK_SQL = (
    "script IN ('latin','cyrillic','han','arabic','devanagari',"
    "'hangul','japanese')"
)


def upgrade():
    bind = op.get_bind()
    if _TABLE not in sa.inspect(bind).get_table_names():
        return

    existing = {
        c.get("name"): c.get("sqltext", "")
        for c in sa.inspect(bind).get_check_constraints(_TABLE)
    }
    if _CHECK_NAME in existing:
        # Already-current schemas (fresh 0001 create_all with the widened
        # model) contain the new values; skip if hangul is already allowed.
        if "hangul" in str(existing[_CHECK_NAME]):
            return
        op.drop_constraint(_CHECK_NAME, _TABLE, type_="check")
    op.create_check_constraint(_CHECK_NAME, _TABLE, _NEW_CHECK_SQL)


def downgrade():
    raise RuntimeError(
        "0025 downgrade is intentionally unsupported: existing ko/ja rows "
        "would violate the previous languages.script check constraint. "
        "Restore a verified pre-upgrade backup instead."
    )
