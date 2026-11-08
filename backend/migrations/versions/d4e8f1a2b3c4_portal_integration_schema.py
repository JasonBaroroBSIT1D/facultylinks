"""portal integration schema

Revision ID: d4e8f1a2b3c4
Revises: be344b3711de
Create Date: 2026-11-08 18:50:00

"""
from alembic import op
import sqlalchemy as sa


revision = "d4e8f1a2b3c4"
down_revision = "be344b3711de"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("employee_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("department", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("rank", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("phone", sa.String(length=40), nullable=True))

    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("indicator_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("kra_id", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("review_status", sa.String(length=32), server_default="pending", nullable=False))
        batch_op.add_column(sa.Column("review_remarks", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("verified_points", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_documents_reviewed_by_user_id_users",
            "users",
            ["reviewed_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_notifications_user_id"), ["user_id"], unique=False)

    op.create_table(
        "activity_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_email", sa.String(length=320), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "faculty_assessments",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade():
    op.drop_table("faculty_assessments")
    op.drop_table("activity_log")
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_notifications_user_id"))
    op.drop_table("notifications")
    op.drop_table("app_settings")
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_constraint("fk_documents_reviewed_by_user_id_users", type_="foreignkey")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by_user_id")
        batch_op.drop_column("verified_points")
        batch_op.drop_column("review_remarks")
        batch_op.drop_column("review_status")
        batch_op.drop_column("kra_id")
        batch_op.drop_column("indicator_id")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("phone")
        batch_op.drop_column("rank")
        batch_op.drop_column("department")
        batch_op.drop_column("employee_id")
