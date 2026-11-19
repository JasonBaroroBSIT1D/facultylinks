"""Add documents.criterion_id for KRA→criterion→indicator hierarchy

Revision ID: i4d5e6f7g8h9
Revises: h3c4d5e6f7g8
Create Date: 2026-11-19 01:20:00

"""
from alembic import op
import sqlalchemy as sa


revision = "i4d5e6f7g8h9"
down_revision = "h3c4d5e6f7g8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("criterion_id", sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_column("criterion_id")
