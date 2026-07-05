"""associate ordered teaching content with lessons"""
from alembic import op
import sqlalchemy as sa

revision="0003"
down_revision="0002"
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind(); inspector=sa.inspect(bind)
    columns={column["name"] for column in inspector.get_columns("content_items")}
    if "lesson_id" not in columns: op.add_column("content_items",sa.Column("lesson_id",sa.String(length=36),nullable=True))
    if "teaching_order" not in columns: op.add_column("content_items",sa.Column("teaching_order",sa.Integer(),nullable=True))
    inspector=sa.inspect(bind)
    foreign_keys={fk.get("name") for fk in inspector.get_foreign_keys("content_items")}
    if "fk_content_items_lesson_id" not in foreign_keys:
        op.create_foreign_key("fk_content_items_lesson_id","content_items","lessons",["lesson_id"],["id"],ondelete="CASCADE")
    unique_names={constraint.get("name") for constraint in sa.inspect(bind).get_unique_constraints("content_items")}
    if "uq_content_items_lesson_teaching_order" not in unique_names:
        op.create_unique_constraint("uq_content_items_lesson_teaching_order","content_items",["lesson_id","teaching_order"])

def downgrade():
    bind=op.get_bind(); inspector=sa.inspect(bind)
    unique_names={constraint.get("name") for constraint in inspector.get_unique_constraints("content_items")}
    if "uq_content_items_lesson_teaching_order" in unique_names: op.drop_constraint("uq_content_items_lesson_teaching_order","content_items",type_="unique")
    foreign_keys={fk.get("name") for fk in sa.inspect(bind).get_foreign_keys("content_items")}
    if "fk_content_items_lesson_id" in foreign_keys: op.drop_constraint("fk_content_items_lesson_id","content_items",type_="foreignkey")
    columns={column["name"] for column in sa.inspect(bind).get_columns("content_items")}
    if "teaching_order" in columns: op.drop_column("content_items","teaching_order")
    if "lesson_id" in columns: op.drop_column("content_items","lesson_id")
