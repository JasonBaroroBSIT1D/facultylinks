"""document assessment link

Revision ID: e5f6a7b8c9d0
Revises: d4e8f1a2b3c4
Create Date: 2026-11-08 19:05:00

"""
from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e8f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("entry_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("superseded_by_public_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("estimated_points", sa.Numeric(10, 2), nullable=True))


def downgrade():
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_column("estimated_points")
        batch_op.drop_column("superseded_by_public_id")
        batch_op.drop_column("entry_id")
