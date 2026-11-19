"""notification target metadata

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0
Create Date: 2026-11-19 14:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "k6l7m8n9o0p1"
down_revision = "j5k6l7m8n9o0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("event_type", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("subject_faculty_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("target_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("target_document_public_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("target_achievement_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("kra_id", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("criterion_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("indicator_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("dedupe_key", sa.String(length=200), nullable=True))
        batch_op.create_foreign_key(
            "fk_notifications_actor_user_id_users",
            "users",
            ["actor_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_notifications_subject_faculty_user_id_users",
            "users",
            ["subject_faculty_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_notifications_dedupe", ["user_id", "dedupe_key"], unique=True)


def downgrade():
    with op.batch_alter_table("notifications", schema=None) as batch_op:
        batch_op.drop_index("ix_notifications_dedupe")
        batch_op.drop_constraint("fk_notifications_subject_faculty_user_id_users", type_="foreignkey")
        batch_op.drop_constraint("fk_notifications_actor_user_id_users", type_="foreignkey")
        batch_op.drop_column("dedupe_key")
        batch_op.drop_column("indicator_id")
        batch_op.drop_column("criterion_id")
        batch_op.drop_column("kra_id")
        batch_op.drop_column("target_achievement_id")
        batch_op.drop_column("target_document_public_id")
        batch_op.drop_column("target_type")
        batch_op.drop_column("subject_faculty_user_id")
        batch_op.drop_column("actor_user_id")
        batch_op.drop_column("event_type")