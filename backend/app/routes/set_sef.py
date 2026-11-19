from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import (
    Document,
    DocumentValidationFinding,
    SetSefSemesterRecord,
    User,
    UserRole,
)
from app.services.auth_context import current_user, faculty_may_access_document, require_roles
from app.services.set_sef_processor import enqueue_set_sef_job
from app.services.set_sef_document import is_set_sef_document
from app.services.set_sef_identity import classify_faculty_identity
from app.services.set_sef_validation import run_set_sef_validations
from app.services.teaching_effectiveness import compute_criterion_a_from_records
from app.services.activity import log_activity

bp = Blueprint("set_sef", __name__)


def _load_set_sef_doc(public_id: str) -> Document | None:
    doc = Document.query.filter_by(public_id=public_id).first()
    return doc if is_set_sef_document(doc) else None


def _active_semester_records(document_id: int) -> list[SetSefSemesterRecord]:
    return (
        SetSefSemesterRecord.query.filter_by(document_id=document_id, superseded_by_id=None)
        .order_by(SetSefSemesterRecord.academic_year, SetSefSemesterRecord.semester)
        .all()
    )


def _scoring_bundle(doc: Document, records: list[SetSefSemesterRecord]) -> dict:
    from app.models import FacultyAssessment
    from app.services.catalog import get_catalog_for_assessment

    assess = db.session.get(FacultyAssessment, doc.owner_user_id)
    assessment_data = assess.data if assess else {}
    catalog, _weights = get_catalog_for_assessment(assessment_data)
    pinned_version = assessment_data.get("configVersionId")
    config_version = pinned_version or doc.config_version
    scoring_est = compute_criterion_a_from_records(
        records,
        verified_only=False,
        config_version=config_version,
        catalog=catalog,
    )
    scoring_ver = compute_criterion_a_from_records(
        records,
        verified_only=True,
        config_version=config_version,
        catalog=catalog,
    )
    return {
        "scoring": {"estimated": scoring_est, "verified": scoring_ver},
        "verifyCounts": {
            "setVerified": sum(
                1
                for r in records
                if r.set_verification_status == "verified" and r.set_rating_confirmed is not None
            ),
            "sefVerified": sum(
                1
                for r in records
                if r.sef_verification_status == "verified" and r.sef_rating_confirmed is not None
            ),
            "total": len(records),
        },
    }


@bp.get("/api/documents/<public_id>/set-sef")
def get_set_sef_extraction(public_id: str):
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401
    doc = _load_set_sef_doc(public_id) or Document.query.filter_by(public_id=public_id).first()
    if not doc:
        return jsonify({"error": "Not found."}), 404
    if not faculty_may_access_document(user, doc.owner_user_id):
        return jsonify({"error": "Forbidden."}), 403

    owner = db.session.get(User, doc.owner_user_id)
    records = _active_semester_records(doc.id)
    findings = DocumentValidationFinding.query.filter_by(document_id=doc.id).all()
    bundle = _scoring_bundle(doc, records)
    from app.services.catalog import find_indicator, get_catalog_by_version_label, get_published_catalog_and_weights

    catalog, _ = get_published_catalog_and_weights()
    if doc.config_version:
        pinned = get_catalog_by_version_label(doc.config_version)
        if pinned:
            catalog = pinned
    found = find_indicator(catalog, doc.indicator_id) if catalog and doc.indicator_id else None
    processing_pending = doc.processing_status in ("queued", "processing", "pending") or doc.ocr_status in (
        "pending",
        "processing",
    )

    return jsonify(
        {
            "document": doc.to_dict(),
            "hierarchy": {
                "kraId": doc.kra_id or ((found or {}).get("kra") or {}).get("id") or "",
                "kraName": ((found or {}).get("kra") or {}).get("name") or "",
                "criterionId": doc.criterion_id or ((found or {}).get("criterion") or {}).get("id") or "",
                "criterionName": ((found or {}).get("criterion") or {}).get("name") or "",
                "indicatorId": doc.indicator_id or "",
                "indicatorName": ((found or {}).get("indicator") or {}).get("name") or "",
                "configVersion": doc.config_version or (catalog or {}).get("version") or "",
            },
            "processing": {
                "pending": processing_pending,
                "validationPassed": False if processing_pending else None,
                "message": (
                    "Waiting for document processing. Validation has not completed."
                    if processing_pending and doc.ocr_status == "pending"
                    else "Reading and checking the document. Validation has not completed."
                    if processing_pending
                    else None
                ),
            },
            "semesterRecords": [r.to_dict(profile_name=owner.full_name if owner else "") for r in records],
            "validationFindings": [f.to_dict() for f in findings],
            **bundle,
        }
    )


@bp.post("/api/documents/<public_id>/set-sef/retry-ocr")
@require_roles(UserRole.faculty, UserRole.admin, UserRole.reviewer)
def retry_ocr(public_id: str):
    user = current_user()
    doc = _load_set_sef_doc(public_id) or Document.query.filter_by(public_id=public_id).first()
    if not doc:
        return jsonify({"error": "Not found."}), 404
    if user.role == UserRole.faculty and doc.owner_user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403
    if user.role == UserRole.reviewer and not faculty_may_access_document(user, doc.owner_user_id):
        return jsonify({"error": "Forbidden."}), 403
    if not is_set_sef_document(doc):
        return jsonify({"error": "Not a SET/SEF OCR document."}), 400
    job = enqueue_set_sef_job(doc, force=True)
    return jsonify({"ok": True, "jobId": job.id, "status": job.status})


@bp.patch("/api/documents/<public_id>/set-sef/semesters/<int:record_id>")
@require_roles(UserRole.reviewer, UserRole.admin)
def patch_semester_record(public_id: str, record_id: int):
    actor = current_user()
    from app.services.review_action_guard import block_reviewer_review_response

    denied = block_reviewer_review_response(actor)
    if denied:
        return denied
    rec = (
        SetSefSemesterRecord.query.join(Document)
        .options(joinedload(SetSefSemesterRecord.document).joinedload(Document.owner))
        .filter(SetSefSemesterRecord.id == record_id, Document.public_id == public_id)
        .first()
    )
    if not rec:
        return jsonify({"error": "Record not found."}), 404
    doc = rec.document
    if not faculty_may_access_document(actor, doc.owner_user_id):
        return jsonify({"error": "Forbidden."}), 403

    data = request.get_json(silent=True) or {}
    for field, col in (
        ("academicYear", "academic_year"),
        ("semester", "semester"),
        ("setRatingConfirmed", "set_rating_confirmed"),
        ("sefRatingConfirmed", "sef_rating_confirmed"),
        ("facultyNameExtracted", "faculty_name_extracted"),
    ):
        if field in data:
            val = data[field]
            if col.endswith("_confirmed") and val is not None:
                val = float(val)
            setattr(rec, col, val)

    if "facultyNameExtracted" in data:
        name = (data.get("facultyNameExtracted") or "").strip() or None
        rec.faculty_name_extracted = name
        profile = rec.document.owner.full_name if rec.document and rec.document.owner else ""
        rec.faculty_identity_status = classify_faculty_identity(profile, name)

    if data.get("setVerificationStatus") == "verified":
        if rec.set_rating_confirmed is None and rec.set_rating_extracted is None:
            return jsonify({"error": "Cannot verify SET: no rating was extracted or confirmed."}), 400
        if rec.faculty_identity_status not in ("match",):
            return jsonify({"error": "Cannot verify SET until faculty identity is resolved (confirmed match)."}), 400
        # Persist a confirmed value so verified scoring never falls back to extraction silently.
        if rec.set_rating_confirmed is None and rec.set_rating_extracted is not None:
            rec.set_rating_confirmed = float(rec.set_rating_extracted)
        rec.set_verification_status = "verified"
    elif "setVerificationStatus" in data:
        rec.set_verification_status = data["setVerificationStatus"]

    if data.get("sefVerificationStatus") == "verified":
        if rec.sef_rating_confirmed is None and rec.sef_rating_extracted is None:
            return jsonify({"error": "Cannot verify SEF: no rating was extracted or confirmed."}), 400
        if rec.faculty_identity_status not in ("match",):
            return jsonify({"error": "Cannot verify SEF until faculty identity is resolved (confirmed match)."}), 400
        if rec.sef_rating_confirmed is None and rec.sef_rating_extracted is not None:
            rec.sef_rating_confirmed = float(rec.sef_rating_extracted)
        rec.sef_verification_status = "verified"
    elif "sefVerificationStatus" in data:
        rec.sef_verification_status = data["sefVerificationStatus"]
    if "facultyIdentityStatus" in data and actor.role == UserRole.admin:
        rec.faculty_identity_status = data["facultyIdentityStatus"]
    elif "facultyIdentityResolution" in data:
        rec.faculty_identity_status = data["facultyIdentityResolution"]

    remarks = (data.get("remarks") or "").strip()
    rec.updated_at = datetime.now(timezone.utc)
    log_activity(
        actor.email,
        f"Updated SET/SEF semester record {record_id} for document {public_id}: {remarks[:120]}",
        commit=False,
    )
    db.session.commit()
    records = _active_semester_records(doc.id)
    bundle = _scoring_bundle(doc, records)
    profile_name = doc.owner.full_name if doc.owner else ""
    return jsonify({"record": rec.to_dict(profile_name=profile_name), **bundle})


def _refresh_set_sef_findings(doc: Document, owner: User, records: list[SetSefSemesterRecord]) -> None:
    from app.services.catalog import get_catalog_for_assessment
    from app.models import FacultyAssessment

    assess = db.session.get(FacultyAssessment, doc.owner_user_id)
    catalog, _ = get_catalog_for_assessment(assess.data if assess else {})
    DocumentValidationFinding.query.filter_by(document_id=doc.id, pipeline="set_sef").delete(
        synchronize_session=False
    )
    findings = run_set_sef_validations(
        document=doc,
        owner=owner,
        records=records,
        prior_hash=None,
        document_kind=doc.document_kind,
        catalog=catalog,
    )
    for f in findings:
        db.session.add(
            DocumentValidationFinding(
                document_id=doc.id,
                rule_id=f.rule_id,
                outcome=f.outcome,
                affected_field=f.affected_field,
                semester_key=f.semester_key,
                explanation=f.explanation,
                pipeline="set_sef",
                severity=f.outcome,
            )
        )


@bp.post("/api/documents/<public_id>/set-sef/resolve-identity")
@require_roles(UserRole.reviewer, UserRole.admin)
def resolve_set_sef_identity(public_id: str):
    """Audited reviewer action: confirm extracted identity for all active semester rows."""
    actor = current_user()
    from app.services.review_action_guard import block_reviewer_review_response

    denied = block_reviewer_review_response(actor)
    if denied:
        return denied
    doc = _load_set_sef_doc(public_id)
    if not doc:
        return jsonify({"error": "Not found or not a SET/SEF document."}), 404
    if not faculty_may_access_document(actor, doc.owner_user_id):
        return jsonify({"error": "Forbidden."}), 403

    data = request.get_json(silent=True) or {}
    resolution = (data.get("resolution") or data.get("facultyIdentityResolution") or "").strip()
    allowed = {"match", "needs_confirmation", "mismatch"}
    if resolution not in allowed:
        return jsonify({"error": "resolution must be match, needs_confirmation, or mismatch."}), 400

    owner = db.session.get(User, doc.owner_user_id)
    if not owner:
        return jsonify({"error": "Owner not found."}), 404
    profile = owner.full_name or ""

    name_override = (data.get("facultyNameExtracted") or "").strip() or None
    records = _active_semester_records(doc.id)
    if not records:
        return jsonify({"error": "No active semester records for this document."}), 400

    for rec in records:
        if name_override:
            rec.faculty_name_extracted = name_override
            if resolution == "match":
                rec.faculty_identity_status = classify_faculty_identity(profile, name_override)
                if rec.faculty_identity_status != "match":
                    return (
                        jsonify(
                            {
                                "error": (
                                    "Cannot record match: extracted/corrected name does not match "
                                    "the faculty profile under normalization rules."
                                )
                            }
                        ),
                        400,
                    )
            else:
                rec.faculty_identity_status = resolution
        else:
            if not rec.faculty_name_extracted:
                return jsonify({"error": "facultyNameExtracted is required when no name was extracted."}), 400
            if resolution == "match":
                rec.faculty_identity_status = classify_faculty_identity(profile, rec.faculty_name_extracted)
                if rec.faculty_identity_status != "match":
                    return (
                        jsonify(
                            {
                                "error": "Cannot record match: extracted name does not match faculty profile."
                            }
                        ),
                        400,
                    )
            else:
                rec.faculty_identity_status = resolution
        rec.updated_at = datetime.now(timezone.utc)

    _refresh_set_sef_findings(doc, owner, records)
    remarks = (data.get("remarks") or "").strip()
    log_activity(
        actor.email,
        (
            f"SET/SEF identity resolution for document {public_id}: {resolution}"
            + (f" name={name_override!r}" if name_override else "")
            + (f" — {remarks[:120]}" if remarks else "")
        ),
        commit=False,
    )
    db.session.commit()
    bundle = _scoring_bundle(doc, records)
    return jsonify(
        {
            "ok": True,
            "resolution": resolution,
            "semesterRecords": [r.to_dict(profile_name=profile) for r in records],
            **bundle,
        }
    )


@bp.post("/api/documents/<public_id>/set-sef/semesters")
@require_roles(UserRole.reviewer, UserRole.admin)
def add_semester_record(public_id: str):
    actor = current_user()
    from app.services.review_action_guard import block_reviewer_review_response

    denied = block_reviewer_review_response(actor)
    if denied:
        return denied
    doc = Document.query.filter_by(public_id=public_id).first()
    if not doc or not faculty_may_access_document(actor, doc.owner_user_id):
        return jsonify({"error": "Forbidden or not found."}), 403 if doc else 404
    data = request.get_json(silent=True) or {}
    rec = SetSefSemesterRecord(
        document_id=doc.id,
        owner_user_id=doc.owner_user_id,
        academic_year=(data.get("academicYear") or "").strip() or None,
        semester=(data.get("semester") or "").strip() or None,
        semester_key=f"{data.get('academicYear')}|{data.get('semester')}",
        faculty_name_extracted=(data.get("facultyNameExtracted") or "").strip() or None,
        set_rating_confirmed=float(data["setRating"]) if data.get("setRating") not in (None, "") else None,
        sef_rating_confirmed=float(data["sefRating"]) if data.get("sefRating") not in (None, "") else None,
        set_verification_status="pending",
        sef_verification_status="pending",
        faculty_identity_status="needs_confirmation",
    )
    db.session.add(rec)
    db.session.commit()
    owner = db.session.get(User, doc.owner_user_id)
    return jsonify({"record": rec.to_dict(profile_name=owner.full_name if owner else "")}), 201
