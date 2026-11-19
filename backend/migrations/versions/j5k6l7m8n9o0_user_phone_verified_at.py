"""Add users.phone_verified_at for SMS password recovery

Revision ID: j5k6l7m8n9o0
Revises: i4d5e6f7g8h9
Create Date: 2026-11-19 08:40:00

"""
from alembic import op
import sqlalchemy as sa


revision = "j5k6l7m8n9o0"
down_revision = "i4d5e6f7g8h9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("phone_verified_at")