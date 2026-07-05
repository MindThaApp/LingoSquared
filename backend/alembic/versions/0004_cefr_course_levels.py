"""validate course levels as CEFR values"""
from alembic import op
import sqlalchemy as sa

revision="0004"
down_revision="0003"
branch_labels=None
depends_on=None

LEVELS="'A1','A2','B1','B2','C1','C2'"

def upgrade():
    bind=op.get_bind()
    op.execute(sa.text(f"UPDATE courses SET level='A1' WHERE level IS NULL OR level NOT IN ({LEVELS})"))
    op.alter_column("courses","level",existing_type=sa.String(length=50),type_=sa.String(length=2),nullable=False,server_default="A1")
    names={constraint.get("name") for constraint in sa.inspect(bind).get_check_constraints("courses")}
    if "ck_courses_cefr_level" not in names:
        op.create_check_constraint("ck_courses_cefr_level","courses",f"level IN ({LEVELS})")

def downgrade():
    bind=op.get_bind()
    names={constraint.get("name") for constraint in sa.inspect(bind).get_check_constraints("courses")}
    if "ck_courses_cefr_level" in names: op.drop_constraint("ck_courses_cefr_level","courses",type_="check")
    op.alter_column("courses","level",existing_type=sa.String(length=2),type_=sa.String(length=50),nullable=False,server_default=None)
