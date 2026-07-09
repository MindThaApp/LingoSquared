"""allow Devanagari language script

Widen the languages.script check constraint so Hindi can be seeded as a
new Devanagari-script language. Guarded so a fresh 0001-created schema,
which already reflects current models, does not fail when this migration
reaches head.
"""

import sqlalchemy as sa
from alembic import op


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

_TABLE = "languages"
_OLD_CHECK_NAME = "languages_script_check"
_NEW_CHECK_NAME = "ck_languages_script"
_NEW_CHECK_SQL = "script IN ('latin','cyrillic','han','arabic','devanagari')"


def _check_names(bind):
    return {
        constraint.get("name")
        for constraint in sa.inspect(bind).get_check_constraints(_TABLE)
    }


def upgrade():
    bind = op.get_bind()
    if _TABLE not in sa.inspect(bind).get_table_names():
        return

    check_names = _check_names(bind)
    if _OLD_CHECK_NAME in check_names:
        op.drop_constraint(_OLD_CHECK_NAME, _TABLE, type_="check")
        check_names = _check_names(bind)

    if _NEW_CHECK_NAME not in check_names:
        op.create_check_constraint(_NEW_CHECK_NAME, _TABLE, _NEW_CHECK_SQL)


def downgrade():
    raise RuntimeError(
        "0018 downgrade is intentionally unsupported: existing Hindi rows "
        "with script='devanagari' would violate the previous languages.script "
        "check constraint. Restore a verified pre-upgrade backup instead."
    )
