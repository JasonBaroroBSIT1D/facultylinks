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
    scoring_est = compute_criterion_a_from_records(records, verified_only=False, config_version=doc.config_version)
    scoring_ver = compute_criterion_a_from_records(records, verified_only=True, config_version=doc.config_version)
    return {
        "scoring": {"estimated": scoring_est, "verified": scoring_ver},
        "verifyCounts": {
            "setVerified": sum(1 for r in records if r.set_verification_status == "verified"),
            "sefVerified": sum(1 for r in records if r.sef_verification_status == "verified"),
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

    return jsonify(
        {
            "document": doc.to_dict(),
            "semesterRecords": [r.to_dict(profile_name=owner.full_name if owner else "") for r in records],
            "validationFindings": [f.to_dict() for f in findings],
            **bundle,
        }
    )


@bp.post("/api/documents/<public_id>/set-sef/retry-ocr")
@require_roles(UserRole.faculty, UserRole.admin)
def retry_ocr(public_id: str):
    user = current_user()
    doc = _load_set_sef_doc(public_id) or Document.query.filter_by(public_id=public_id).first()
    if not doc:
        return jsonify({"error": "Not found."}), 404
    if user.role == UserRole.faculty and doc.owner_user_id != user.id:
        return jsonify({"error": "Forbidden."}), 403
    if not is_set_sef_document(doc):
        return jsonify({"error": "Not a SET/SEF OCR document."}), 400
    job = enqueue_set_sef_job(doc)
    return jsonify({"ok": True, "jobId": job.id, "status": job.status})


@bp.patch("/api/documents/<public_id>/set-sef/semesters/<int:record_id>")
@require_roles(UserRole.reviewer, UserRole.admin)
def patch_semester_record(public_id: str, record_id: int):
    actor = current_user()
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

    if data.get("setVerificationStatus") == "verified":
        if rec.set_rating_confirmed is None and rec.set_rating_extracted is None:
            return jsonify({"error": "Cannot verify SET: no rating was extracted or confirmed."}), 400
        if rec.faculty_identity_status in ("missing", "mismatch"):
            return jsonify({"error": "Cannot verify SET until faculty identity is resolved."}), 400
        rec.set_verification_status = "verified"
    elif "setVerificationStatus" in data:
        rec.set_verification_status = data["setVerificationStatus"]

    if data.get("sefVerificationStatus") == "verified":
        if rec.sef_rating_confirmed is None and rec.sef_rating_extracted is None:
            return jsonify({"error": "Cannot verify SEF: no rating was extracted or confirmed."}), 400
        if rec.faculty_identity_status in ("missing", "mismatch"):
            return jsonify({"error": "Cannot verify SEF until faculty identity is resolved."}), 400
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


@bp.post("/api/documents/<public_id>/set-sef/semesters")
@require_roles(UserRole.reviewer, UserRole.admin)
def add_semester_record(public_id: str):
    actor = current_user()
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
