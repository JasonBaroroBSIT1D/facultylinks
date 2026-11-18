"""General document OCR extraction, classification, and field metadata."""

from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


class DocumentExtraction(db.Model):
    """Active text extraction snapshot for a document (non–SET/SEF and shared audit)."""

    __tablename__ = "document_extractions"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    full_text = db.Column(db.Text, nullable=True)
    pages_json = db.Column(db.JSON, nullable=True)  # [{page, text, source, meanConfidence}]
    extraction_method = db.Column(db.String(64), nullable=False, default="none")
    ocr_required = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(32), nullable=False, default="completed")  # completed|failed
    error_message = db.Column(db.String(500), nullable=True)
    rules_version = db.Column(db.String(64), nullable=True)
    classification_version = db.Column(db.String(64), nullable=True)
    superseded_by_id = db.Column(
        db.Integer, db.ForeignKey("document_extractions.id", ondelete="SET NULL"), nullable=True
    )
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    document = db.relationship("Document", backref=db.backref("extractions", lazy="dynamic"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "documentId": self.document_id,
            "fullText": self.full_text or "",
            "pages": self.pages_json or [],
            "extractionMethod": self.extraction_method,
            "ocrRequired": bool(self.ocr_required),
            "status": self.status,
            "errorMessage": self.error_message or "",
            "rulesVersion": self.rules_version or "",
            "classificationVersion": self.classification_version or "",
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "finishedAt": self.finished_at.isoformat() if self.finished_at else None,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class DocumentClassification(db.Model):
    """Keyword-based KRA suggestion (faculty-selected KRA remains authoritative)."""

    __tablename__ = "document_classifications"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    extraction_id = db.Column(
        db.Integer, db.ForeignKey("document_extractions.id", ondelete="SET NULL"), nullable=True
    )
    selected_kra_id = db.Column(db.String(32), nullable=True)
    suggested_kra_id = db.Column(db.String(32), nullable=True)
    outcome = db.Column(db.String(32), nullable=False, default="uncertain")
    # clear | conflicting | absent | uncertain | mismatch_selected
    matched_rules_json = db.Column(db.JSON, nullable=True)
    supporting_excerpts_json = db.Column(db.JSON, nullable=True)
    ambiguity_notes = db.Column(db.Text, nullable=True)
    classification_version = db.Column(db.String(64), nullable=False, default="")
    superseded_by_id = db.Column(
        db.Integer, db.ForeignKey("document_classifications.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "selectedKraId": self.selected_kra_id or "",
            "suggestedKraId": self.suggested_kra_id or "",
            "outcome": self.outcome,
            "matchedRules": self.matched_rules_json or [],
            "supportingExcerpts": self.supporting_excerpts_json or [],
            "ambiguityNotes": self.ambiguity_notes or "",
            "classificationVersion": self.classification_version,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class DocumentExtractedField(db.Model):
    """Machine-extracted content fields with optional reviewer corrections."""

    __tablename__ = "document_extracted_fields"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    extraction_id = db.Column(
        db.Integer, db.ForeignKey("document_extractions.id", ondelete="SET NULL"), nullable=True
    )
    field_name = db.Column(db.String(64), nullable=False)  # title | subject_name | event_date | ...
    value_extracted = db.Column(db.Text, nullable=True)
    value_confirmed = db.Column(db.Text, nullable=True)
    field_status = db.Column(db.String(32), nullable=False, default="missing")
    # missing|invalid|ambiguous|ok|not_applicable|not_configured|extraction_failed
    excerpt = db.Column(db.Text, nullable=True)
    source_pages = db.Column(db.JSON, nullable=True)
    rule_id = db.Column(db.String(64), nullable=True)
    rule_version = db.Column(db.String(32), nullable=True)
    confirmed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def effective_value(self) -> str | None:
        if self.value_confirmed is not None and str(self.value_confirmed).strip() != "":
            return self.value_confirmed
        return self.value_extracted

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fieldName": self.field_name,
            "valueExtracted": self.value_extracted or "",
            "valueConfirmed": self.value_confirmed if self.value_confirmed is not None else None,
            "effectiveValue": self.effective_value() or "",
            "fieldStatus": self.field_status,
            "excerpt": self.excerpt or "",
            "sourcePages": self.source_pages or [],
            "ruleId": self.rule_id or "",
            "ruleVersion": self.rule_version or "",
            "confirmedAt": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "active": bool(self.active),
        }
