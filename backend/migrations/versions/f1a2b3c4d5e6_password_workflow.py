"""password workflow — must_change, recovery, credential delivery status

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-11-08 21:45:00

"""
from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("credential_email_status", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("credential_email_error", sa.String(length=500), nullable=True))

    op.create_table(
        "password_recovery_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("code_hmac", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_ip", sa.String(length=64), nullable=True),
        sa.Column("verify_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("password_recovery_challenges", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_password_recovery_challenges_user_id"), ["user_id"], unique=False)

    op.create_table(
        "password_reset_grants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["challenge_id"], ["password_recovery_challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("password_reset_grants", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_password_reset_grants_token_hash"), ["token_hash"], unique=True)
        batch_op.create_index(batch_op.f("ix_password_reset_grants_user_id"), ["user_id"], unique=False)


def downgrade():
    op.drop_table("password_reset_grants")
    op.drop_table("password_recovery_challenges")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("credential_email_error")
        batch_op.drop_column("credential_email_status")
        batch_op.drop_column("must_change_password")
