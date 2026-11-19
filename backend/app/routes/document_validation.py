"""API for general document OCR extraction, classification, and content findings."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import (
    Document,
    DocumentClassification,
    DocumentExtractedField,
    DocumentExtraction,
    DocumentValidationFinding,
    FacultyAssessment,
    UserRole,
)
from app.services.auth_context import current_user, faculty_may_access_document, require_roles
from app.services.catalog import (
    catalog_for_version_label_strict,
    find_indicator,
    get_catalog_for_assessment,
    get_published_catalog_and_weights,
)
from app.services.document_ocr_processor import enqueue_general_ocr_job
from app.services.document_validation_config import coverage_for_indicator
from app.services.set_sef_document import is_set_sef_document

bp = Blueprint("document_validation", __name__)


def _load_doc(public_id: str) -> Document | None:
    return Document.query.filter_by(public_id=public_id).first()


def _active_extraction(doc_id: int) -> DocumentExtraction | None:
    return (
        DocumentExtraction.query.filter_by(document_id=doc_id, superseded_by_id=None)
        .order_by(DocumentExtraction.id.desc())
        .first()
    )


def _active_classification(doc_id: int) -> DocumentClassification | None:
    return (
        DocumentClassification.query.filter_by(document_id=doc_id, superseded_by_id=None)
        .order_by(DocumentClassification.id.desc())
        .first()
    )


def _faculty_safe_error(doc: Document) -> str:
    """Avoid exposing raw OCR/tooling errors to faculty clients."""
    if doc.processing_status == "failed" or doc.ocr_status == "failed":
        return (
            "We could not read text from this file. Try a clearer scan or PDF, "
            "or ask your reviewer for help."
        )
    if doc.processing_status in ("queued", "processing") or doc.ocr_status in (
        "pending",
        "processing",
    ):
        return "Document text is still being processed."
    if doc.ocr_status == "review_required":
        return "Extracted text is ready for reviewer checks."
    if doc.ocr_status == "completed":
        return "Text extraction completed."
    return ""


@bp.get("/api/documents/<public_id>/validation")
def get_document_validation(public_id: str):
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401
    doc = _load_doc(public_id)
    if not doc:
        return jsonify({"error": "Not found."}), 404
    if not faculty_may_access_document(user, doc.owner_user_id):
        return jsonify({"error": "Forbidden."}), 403

    if is_set_sef_document(doc):
        return jsonify({"error": "Use /api/documents/<id>/set-sef for SET/SEF documents."}), 400

    extraction = _active_extraction(doc.id)
    classification = _active_classification(doc.id)
    fields = (
        DocumentExtractedField.query.filter_by(document_id=doc.id, active=True)
        .order_by(DocumentExtractedField.field_name.asc())
        .all()
    )
    findings = (
        DocumentValidationFinding.query.filter_by(document_id=doc.id, pipeline="general")
        .order_by(DocumentValidationFinding.id.asc())
        .all()
    )

    assess = db.session.get(FacultyAssessment, doc.owner_user_id)
    assessment_data = assess.data if assess else {}
    catalog, _weights = get_catalog_for_assessment(assessment_data)
    if not catalog:
        catalog, _ = get_published_catalog_and_weights()

    config_resolution = {
        "requestedVersion": doc.config_version or assessment_data.get("configVersionId") or "",
        "usedVersion": (catalog or {}).get("version") or doc.config_version or "",
        "resolved": True,
        "source": "assessment_pin_or_published",
        "warning": None,
    }
    if doc.config_version:
        strict = catalog_for_version_label_strict(doc.config_version)
        if strict:
            catalog = strict
            config_resolution["source"] = "document_config_version"
            config_resolution["usedVersion"] = doc.config_version
        else:
            config_resolution["resolved"] = False
            config_resolution["warning"] = (
                f"Stored document config version {doc.config_version!r} could not be resolved. "
                "Display uses assessment-pinned or published catalog; re-run OCR after configuration is restored."
            )
            config_resolution["source"] = "assessment_pin_or_published_fallback"

    found = find_indicator(catalog, doc.indicator_id) if catalog and doc.indicator_id else None
    ind = (found or {}).get("indicator") if found else None
    kra_meta = (found or {}).get("kra") if found else None
    crit_meta = (found or {}).get("criterion") if found else None
    coverage = coverage_for_indicator(ind, indicator_id=doc.indicator_id, kra_id=doc.kra_id)
    snapshot = next((f for f in findings if f.rule_id == "validation_configuration_snapshot"), None)
    if snapshot and snapshot.explanation:
        try:
            snap = json.loads(snapshot.explanation)
            if snap.get("coverageStatus"):
                coverage = {**coverage, "status": snap["coverageStatus"], "rules_version": snap.get("contentRulesVersion")}
        except json.JSONDecodeError:
            pass

    processing_pending = doc.processing_status in ("queued", "processing", "pending") or doc.ocr_status in (
        "pending",
        "processing",
    )
    checks_completed = not processing_pending and extraction is not None and extraction.status == "completed"
    validation_complete = checks_completed and doc.ocr_status in ("completed", "review_required", "failed")

    payload = {
        "document": doc.to_dict(),
        "hierarchy": {
            "kraId": doc.kra_id or (kra_meta or {}).get("id") or "",
            "kraName": (kra_meta or {}).get("name") or "",
            "criterionId": doc.criterion_id or (crit_meta or {}).get("id") or "",
            "criterionName": (crit_meta or {}).get("name") or "",
            "indicatorId": doc.indicator_id or "",
            "indicatorName": (ind or {}).get("name") or "",
            "configVersion": doc.config_version or (catalog or {}).get("version") or "",
        },
        "extraction": extraction.to_dict() if extraction else None,
        "classification": classification.to_dict() if classification else None,
        "fields": [f.to_dict() for f in fields],
        "validationFindings": [f.to_dict() for f in findings],
        "coverage": {
            "status": coverage.get("status"),
            "documentType": coverage.get("document_type"),
            "ocrFields": coverage.get("ocr_fields") or [],
            "formOnlyFields": coverage.get("form_only_fields") or [],
            "fieldRequirements": coverage.get("field_requirements") or {},
            "automaticChecks": coverage.get("automatic_checks") or [],
            "manualReviewGaps": coverage.get("manual_review_gaps") or [],
            "fullyValidated": False,
            "reason": coverage.get("reason") or "",
            "source": coverage.get("source") or "",
            "rulesVersion": extraction.rules_version if extraction else coverage.get("rules_version") or "",
        },
        "configuration": config_resolution,
        "processing": {
            "pending": processing_pending,
            "checksCompleted": checks_completed,
            "validationComplete": validation_complete,
            "fullyValidated": False,
            "validationPassed": False if processing_pending else None,
            "message": (
                "Waiting for document processing. Validation has not completed."
                if processing_pending and doc.ocr_status == "pending"
                else "Reading and checking the document. Validation has not completed."
                if processing_pending
                else None
            ),
        },
        "awardsPoints": False,
        "autoApproves": False,
        "authenticityClaimed": False,
    }
    if user.role == UserRole.faculty:
        payload["facultyStatusMessage"] = _faculty_safe_error(doc)
        # Hide raw processing error from faculty
        if payload["document"]:
            payload["document"] = {
                **payload["document"],
                "processingError": "",
            }
        if payload.get("extraction"):
            payload["extraction"] = {
                **payload["extraction"],
                "errorMessage": "",
                # Keep short text preview for faculty? Prefer status only — omit full text dump
                "fullText": "",
            }
    return jsonify(payload)


@bp.post("/api/documents/<public_id>/validation/retry-ocr")
@require_roles(UserRole.faculty, UserRole.admin, UserRole.reviewer)
def retry_general_ocr(public_id: str):
    user = current_user()
    doc = _load_doc(public_id)
    if not doc:
        return jsonify({"error": "Not found."}), 404
    if user.role == UserRole.faculty and doc.owner_user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403
    if user.role == UserRole.reviewer and not faculty_may_access_document(user, doc.owner_user_id):
        return jsonify({"error": "Forbidden."}), 403
    if is_set_sef_document(doc):
        return jsonify({"error": "Use SET/SEF retry-ocr for this document."}), 400
    job = enqueue_general_ocr_job(doc, force=True)
    if not job:
        return jsonify({"error": "This file type does not support OCR processing."}), 400
    return jsonify({"ok": True, "jobId": job.id, "status": job.status})


@bp.patch("/api/documents/<public_id>/validation/fields/<int:field_id>")
@require_roles(UserRole.reviewer, UserRole.admin)
def patch_extracted_field(public_id: str, field_id: int):
    actor = current_user()
    doc = _load_doc(public_id)
    if not doc:
        return jsonify({"error": "Not found."}), 404
    if not faculty_may_access_document(actor, doc.owner_user_id):
        return jsonify({"error": "Forbidden."}), 403
    row = DocumentExtractedField.query.filter_by(id=field_id, document_id=doc.id, active=True).first()
    if not row:
        return jsonify({"error": "Field not found."}), 404
    body = request.get_json(silent=True) or {}
    if "valueConfirmed" in body:
        val = body.get("valueConfirmed")
        row.value_confirmed = None if val is None else str(val)
        row.confirmed_by_user_id = actor.id
        row.confirmed_at = datetime.now(timezone.utc)
        if row.value_confirmed and str(row.value_confirmed).strip():
            row.field_status = "ok"
    db.session.commit()
    return jsonify({"field": row.to_dict()})
