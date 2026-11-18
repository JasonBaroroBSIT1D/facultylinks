"""General document OCR, classification, and content-field persistence

Revision ID: h3c4d5e6f7g8
Revises: g2b3c4d5e6f7
Create Date: 2026-11-18 13:20:00

"""
from alembic import op
import sqlalchemy as sa


revision = "h3c4d5e6f7g8"
down_revision = "g2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("document_validation_findings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pipeline", sa.String(length=32), nullable=False, server_default="set_sef"))
        batch_op.add_column(sa.Column("rule_version", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("severity", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("excerpt", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("source_pages", sa.JSON(), nullable=True))

    op.create_table(
        "document_extractions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("pages_json", sa.JSON(), nullable=True),
        sa.Column("extraction_method", sa.String(length=64), nullable=False),
        sa.Column("ocr_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("rules_version", sa.String(length=64), nullable=True),
        sa.Column("classification_version", sa.String(length=64), nullable=True),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["document_extractions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("document_extractions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_document_extractions_document_id"), ["document_id"], unique=False)

    op.create_table(
        "document_classifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("extraction_id", sa.Integer(), nullable=True),
        sa.Column("selected_kra_id", sa.String(length=32), nullable=True),
        sa.Column("suggested_kra_id", sa.String(length=32), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("matched_rules_json", sa.JSON(), nullable=True),
        sa.Column("supporting_excerpts_json", sa.JSON(), nullable=True),
        sa.Column("ambiguity_notes", sa.Text(), nullable=True),
        sa.Column("classification_version", sa.String(length=64), nullable=False),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extraction_id"], ["document_extractions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["document_classifications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("document_classifications", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_document_classifications_document_id"), ["document_id"], unique=False)

    op.create_table(
        "document_extracted_fields",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("extraction_id", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("value_extracted", sa.Text(), nullable=True),
        sa.Column("value_confirmed", sa.Text(), nullable=True),
        sa.Column("field_status", sa.String(length=32), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("source_pages", sa.JSON(), nullable=True),
        sa.Column("rule_id", sa.String(length=64), nullable=True),
        sa.Column("rule_version", sa.String(length=32), nullable=True),
        sa.Column("confirmed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["extraction_id"], ["document_extractions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["confirmed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("document_extracted_fields", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_document_extracted_fields_document_id"), ["document_id"], unique=False)


def downgrade():
    op.drop_table("document_extracted_fields")
    op.drop_table("document_classifications")
    op.drop_table("document_extractions")
    with op.batch_alter_table("document_validation_findings", schema=None) as batch_op:
        batch_op.drop_column("source_pages")
        batch_op.drop_column("excerpt")
        batch_op.drop_column("severity")
        batch_op.drop_column("rule_version")
        batch_op.drop_column("pipeline")
