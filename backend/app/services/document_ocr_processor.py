"""Background processor for general (non–SET/SEF) document OCR + validation."""

from __future__ import annotations

import hashlib
import io
import json
import logging
from datetime import datetime, timezone

from app.extensions import db
from app.models import (
    Document,
    DocumentClassification,
    DocumentExtractedField,
    DocumentExtraction,
    DocumentProcessingJob,
    DocumentValidationFinding,
    FacultyAssessment,
    User,
)
from app.services.catalog import get_published_catalog_and_weights
from app.services.document_classification import classify_document_kra
from app.services.document_content_validation import validate_document_content
from app.services.document_text import extract_document_text, supports_general_ocr
from app.services.document_validation_config import CLASSIFICATION_VERSION, CONTENT_RULES_VERSION
from app.services.set_sef_document import is_set_sef_document
from app.services.infrastructure_errors import (
    faculty_safe_processing_error,
    infrastructure_error_faculty_message,
    is_transient_infrastructure_error,
)
from app.services.storage import download_private_file

_log = logging.getLogger(__name__)

JOB_TYPE = "general_ocr"


def _file_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def enqueue_general_ocr_job(
    document: Document, *, force: bool = False
) -> DocumentProcessingJob | None:
    if is_set_sef_document(document):
        return None
    if not supports_general_ocr(document.mime_type):
        document.ocr_status = "none"
        document.processing_status = "none"
        return None
    from app.services.ocr_job_dispatch import recover_stale_jobs, schedule_ocr_job

    recover_stale_jobs(older_than_minutes=1 if force else None)
    existing = (
        DocumentProcessingJob.query.filter_by(document_id=document.id, job_type=JOB_TYPE)
        .filter(DocumentProcessingJob.status.in_(("pending", "running")))
        .first()
    )
    if existing:
        if existing.status == "pending":
            schedule_ocr_job(existing.id, JOB_TYPE)
        return existing
    job = DocumentProcessingJob(document_id=document.id, job_type=JOB_TYPE, status="pending")
    document.processing_status = "queued"
    document.ocr_status = "pending"
    document.processing_error = None
    db.session.add(job)
    db.session.commit()
    schedule_ocr_job(job.id, JOB_TYPE)
    return job


def _active_extraction(document_id: int) -> DocumentExtraction | None:
    return (
        DocumentExtraction.query.filter_by(document_id=document_id, superseded_by_id=None)
        .order_by(DocumentExtraction.id.desc())
        .first()
    )


def _active_classification(document_id: int) -> DocumentClassification | None:
    return (
        DocumentClassification.query.filter_by(document_id=document_id, superseded_by_id=None)
        .order_by(DocumentClassification.id.desc())
        .first()
    )


def _preserve_confirmed_fields(document_id: int) -> dict[str, DocumentExtractedField]:
    rows = DocumentExtractedField.query.filter_by(document_id=document_id, active=True).all()
    return {r.field_name: r for r in rows if r.value_confirmed is not None and str(r.value_confirmed).strip()}


def process_general_ocr_document(document_id: int, job_id: int) -> None:
    job = (
        DocumentProcessingJob.query.filter_by(id=job_id, status="pending")
        .with_for_update()
        .first()
    )
    doc = db.session.get(Document, document_id)
    if not job or not doc:
        db.session.rollback()
        return
    if is_set_sef_document(doc):
        job.status = "failed"
        job.last_error = "SET/SEF documents use the set_sef_ocr pipeline."
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        return

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job.attempts = (job.attempts or 0) + 1
    prior_ocr_status = doc.ocr_status
    prior_processing_status = doc.processing_status
    doc.processing_status = "processing"
    doc.ocr_status = "processing"
    db.session.commit()

    started = datetime.now(timezone.utc)
    try:
        raw = download_private_file(doc.object_key)
        doc.file_sha256 = _file_hash(raw)
        extracted = extract_document_text(io.BytesIO(raw), doc.mime_type)

        prior_fields = _preserve_confirmed_fields(doc.id)
        # Replace general findings only (preserve SET/SEF rows if any)
        DocumentValidationFinding.query.filter_by(document_id=doc.id, pipeline="general").delete()
        # Deactivate previous active fields (keep confirmed values for merge)
        for old in DocumentExtractedField.query.filter_by(document_id=doc.id, active=True).all():
            old.active = False

        prev_ext = _active_extraction(doc.id)
        ext = DocumentExtraction(
            document_id=doc.id,
            full_text=extracted.full_text or "",
            pages_json=extracted.pages_payload(),
            extraction_method=extracted.extraction_method,
            ocr_required=bool(extracted.ocr_required),
            status="failed" if extracted.error else "completed",
            error_message=(extracted.error or "")[:500] or None,
            rules_version=CONTENT_RULES_VERSION,
            classification_version=CLASSIFICATION_VERSION,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
        )
        db.session.add(ext)
        db.session.flush()
        if prev_ext:
            prev_ext.superseded_by_id = ext.id

        extraction_failed = bool(extracted.error)
        from app.services.catalog import get_catalog_for_assessment

        assess = db.session.get(FacultyAssessment, doc.owner_user_id)
        assessment_data = assess.data if assess else {}
        catalog, _ = get_catalog_for_assessment(assessment_data)
        if not catalog:
            catalog, _ = get_published_catalog_and_weights()
        pinned = (assessment_data or {}).get("configVersionId") or (catalog or {}).get("version")
        if pinned:
            doc.config_version = str(pinned)
        owner = db.session.get(User, doc.owner_user_id)
        profile_name = owner.full_name if owner else None
        content = validate_document_content(
            full_text=extracted.full_text or "",
            pages=extracted.pages_payload(),
            indicator_id=doc.indicator_id,
            kra_id=doc.kra_id,
            criterion_id=doc.criterion_id,
            extraction_failed=extraction_failed,
            catalog=catalog,
            profile_full_name=profile_name,
        )
        # Persist rule/coverage version on the extraction row before completion.
        ext.rules_version = content.rules_version or CONTENT_RULES_VERSION
        ext.classification_version = CLASSIFICATION_VERSION

        for fe in content.fields:
            prior = prior_fields.get(fe.field_name)
            row = DocumentExtractedField(
                document_id=doc.id,
                extraction_id=ext.id,
                field_name=fe.field_name,
                value_extracted=fe.value,
                value_confirmed=prior.value_confirmed if prior else None,
                field_status=fe.status if not prior else ("ok" if prior.value_confirmed else fe.status),
                excerpt=fe.excerpt,
                source_pages=fe.source_pages or [],
                rule_id=fe.rule_id,
                rule_version=fe.rule_version,
                confirmed_by_user_id=prior.confirmed_by_user_id if prior else None,
                confirmed_at=prior.confirmed_at if prior else None,
                active=True,
            )
            db.session.add(row)

        classification = classify_document_kra(
            extracted.full_text or "",
            selected_kra_id=doc.kra_id,
            pages=extracted.pages_payload(),
        )
        prev_cls = _active_classification(doc.id)
        cls_row = DocumentClassification(
            document_id=doc.id,
            extraction_id=ext.id,
            selected_kra_id=doc.kra_id,
            suggested_kra_id=classification.suggested_kra_id,
            outcome=classification.outcome,
            matched_rules_json=classification.matched_rules,
            supporting_excerpts_json=classification.supporting_excerpts,
            ambiguity_notes=classification.ambiguity_notes,
            classification_version=classification.classification_version,
        )
        db.session.add(cls_row)
        db.session.flush()
        if prev_cls:
            prev_cls.superseded_by_id = cls_row.id

        findings_payload = list(content.findings)
        findings_payload.insert(
            0,
            {
                "rule_id": "validation_configuration_snapshot",
                "outcome": "info",
                "affected_field": None,
                "severity": "info",
                "rule_version": content.rules_version,
                "explanation": json.dumps(
                    {
                        "contentRulesVersion": content.rules_version,
                        "coverageStatus": content.coverage_status,
                        "documentType": content.document_type,
                        "configVersion": doc.config_version,
                        "catalogVersion": (catalog or {}).get("version"),
                        "indicatorId": doc.indicator_id,
                        "kraId": doc.kra_id,
                        "criterionId": doc.criterion_id,
                    },
                    sort_keys=True,
                ),
                "excerpt": None,
                "source_pages": [],
            },
        )
        if classification.outcome == "mismatch_selected":
            findings_payload.append(
                {
                    "rule_id": "kra_selection_mismatch",
                    "outcome": "review",
                    "affected_field": "kraId",
                    "severity": "review",
                    "rule_version": CLASSIFICATION_VERSION,
                    "explanation": classification.ambiguity_notes
                    or "Suggested KRA differs from faculty-selected KRA. File was not moved.",
                    "excerpt": None,
                    "source_pages": [],
                }
            )
        elif classification.outcome == "conflicting":
            findings_payload.append(
                {
                    "rule_id": "kra_classification_conflict",
                    "outcome": "review",
                    "affected_field": "kraId",
                    "severity": "review",
                    "rule_version": CLASSIFICATION_VERSION,
                    "explanation": classification.ambiguity_notes or "Conflicting KRA keyword matches.",
                    "excerpt": None,
                    "source_pages": [],
                }
            )

        for f in findings_payload:
            db.session.add(
                DocumentValidationFinding(
                    document_id=doc.id,
                    rule_id=f["rule_id"],
                    outcome=f.get("outcome") or "review",
                    affected_field=f.get("affected_field"),
                    semester_key=None,
                    explanation=f.get("explanation") or "",
                    pipeline="general",
                    rule_version=f.get("rule_version"),
                    severity=f.get("severity"),
                    excerpt=f.get("excerpt"),
                    source_pages=f.get("source_pages") or [],
                )
            )

        # Status: extraction fail ≠ evidence reject
        review_findings = [f for f in findings_payload if f.get("outcome") in ("review", "fail")]
        if extraction_failed:
            doc.ocr_status = "failed"
            doc.processing_status = "failed"
            doc.processing_error = (extracted.error or "Extraction failed.")[:480]
        else:
            doc.processing_status = "completed"
            doc.processing_error = None
            if review_findings:
                doc.ocr_status = "review_required"
            else:
                doc.ocr_status = "completed"
        # Never auto-approve / auto-reject from general OCR
        if doc.review_status not in ("approved", "rejected", "correction_requested", "evidence"):
            doc.review_status = "pending"

        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        job.last_error = None
        db.session.commit()
    except Exception as exc:
        technical = str(exc)[:480]
        infra = is_transient_infrastructure_error(exc)
        _log.exception(
            "general OCR failed for document_id=%s job_id=%s (%s)",
            document_id,
            job_id,
            "infrastructure" if infra else "processing",
        )
        db.session.rollback()
        job = db.session.get(DocumentProcessingJob, job_id)
        doc = db.session.get(Document, document_id)
        if not job or not doc:
            return
        job.status = "failed"
        job.last_error = technical
        job.finished_at = datetime.now(timezone.utc)
        if infra:
            doc.processing_error = infrastructure_error_faculty_message()
            doc.ocr_status = prior_ocr_status
            doc.processing_status = prior_processing_status or "queued"
        else:
            doc.processing_error = faculty_safe_processing_error(technical, technical_for_logs=technical)
            doc.ocr_status = "failed"
            doc.processing_status = "failed"
        db.session.commit()
        raise
