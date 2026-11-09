"""SET/SEF combined PDF OCR pipeline tables

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-11-09 04:55:00

"""
from alembic import op
import sqlalchemy as sa


revision = "g2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("file_sha256", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("ocr_status", sa.String(length=32), nullable=False, server_default="none"))
        batch_op.add_column(sa.Column("processing_status", sa.String(length=32), nullable=False, server_default="none"))
        batch_op.add_column(sa.Column("processing_error", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("document_kind", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("config_version", sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f("ix_documents_file_sha256"), ["file_sha256"], unique=False)

    op.create_table(
        "document_processing_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("document_processing_jobs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_document_processing_jobs_document_id"), ["document_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_document_processing_jobs_status"), ["status"], unique=False)

    op.create_table(
        "set_sef_semester_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("academic_year", sa.String(length=32), nullable=True),
        sa.Column("semester", sa.String(length=32), nullable=True),
        sa.Column("semester_key", sa.String(length=64), nullable=True),
        sa.Column("faculty_name_extracted", sa.String(length=200), nullable=True),
        sa.Column("faculty_identity_status", sa.String(length=32), nullable=False, server_default="missing"),
        sa.Column("set_rating_extracted", sa.Numeric(10, 2), nullable=True),
        sa.Column("set_scale_extracted", sa.String(length=64), nullable=True),
        sa.Column("set_rating_confirmed", sa.Numeric(10, 2), nullable=True),
        sa.Column("set_verification_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("set_source_pages", sa.JSON(), nullable=True),
        sa.Column("set_excerpt", sa.Text(), nullable=True),
        sa.Column("sef_rating_extracted", sa.Numeric(10, 2), nullable=True),
        sa.Column("sef_scale_extracted", sa.String(length=64), nullable=True),
        sa.Column("sef_rating_confirmed", sa.Numeric(10, 2), nullable=True),
        sa.Column("sef_verification_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("sef_source_pages", sa.JSON(), nullable=True),
        sa.Column("sef_excerpt", sa.Text(), nullable=True),
        sa.Column("ocr_raw_fragment", sa.Text(), nullable=True),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["set_sef_semester_records.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("set_sef_semester_records", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_set_sef_semester_records_document_id"), ["document_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_set_sef_semester_records_owner_user_id"), ["owner_user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_set_sef_semester_records_semester_key"), ["semester_key"], unique=False)

    op.create_table(
        "document_validation_findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("affected_field", sa.String(length=64), nullable=True),
        sa.Column("semester_key", sa.String(length=64), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("document_validation_findings", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_document_validation_findings_document_id"), ["document_id"], unique=False)


def downgrade():
    op.drop_table("document_validation_findings")
    op.drop_table("set_sef_semester_records")
    op.drop_table("document_processing_jobs")
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_documents_file_sha256"))
        batch_op.drop_column("config_version")
        batch_op.drop_column("document_kind")
        batch_op.drop_column("processing_error")
        batch_op.drop_column("processing_status")
        batch_op.drop_column("ocr_status")
        batch_op.drop_column("file_sha256")
