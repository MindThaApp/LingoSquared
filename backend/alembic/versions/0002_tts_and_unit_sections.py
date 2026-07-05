"""add TTS usage tracking and course unit sections"""
from alembic import op
import sqlalchemy as sa

revision="0002"
down_revision="0001"
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind(); inspector=sa.inspect(bind)
    unit_columns={column["name"] for column in inspector.get_columns("units")}
    if "section" not in unit_columns:
        op.add_column("units",sa.Column("section",sa.String(length=15),server_default="reading_writing",nullable=False))
    if "tts_usage" not in inspector.get_table_names():
        op.create_table(
            "tts_usage",
            sa.Column("month",sa.String(length=7),primary_key=True),
            sa.Column("characters",sa.Integer(),nullable=False,server_default="0"),
            sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        )

def downgrade():
    bind=op.get_bind(); inspector=sa.inspect(bind)
    if "tts_usage" in inspector.get_table_names(): op.drop_table("tts_usage")
    unit_columns={column["name"] for column in sa.inspect(bind).get_columns("units")}
    if "section" in unit_columns: op.drop_column("units","section")
