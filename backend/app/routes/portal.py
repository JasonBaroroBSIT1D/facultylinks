from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Document, FacultyAssessment, Notification, ReviewerAssignment, User, UserRole
from app.services.activity import log_activity
from app.services.auth_context import current_user, faculty_may_access_document, logout_user_all, require_roles
from app.services.passwords import hash_password
from app.services.assessment_sync import sync_review_to_assessment
from app.services.portal_state import build_portal_state, parse_portal_user_id
from app.services.settings_store import (
    ASSESSMENT_CONFIG_KEY,
    CATALOG_DRAFT_KEY,
    CATALOG_PUBLISHED_KEY,
    INSTITUTION_KEY,
    get_json,
    set_json,
)

bp = Blueprint("portal", __name__)


@bp.get("/api/portal/state")
def portal_state():
    user = current_user()
    if not user or user.role not in (UserRole.admin, UserRole.reviewer):
        return jsonify({"error": "Forbidden"}), 403
    try:
        return jsonify(build_portal_state(user))
    except Exception:
        return jsonify({"error": "Failed to load portal state."}), 500


@bp.post("/api/admin/faculty")
@require_roles(UserRole.admin)
def create_faculty():
    user = current_user()
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or "@" not in email:
        return jsonify({"error": "Valid email is required."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 409
    if password and len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    first = (data.get("firstName") or "").strip()
    last = (data.get("lastName") or "").strip()
    full_name = f"{first} {last}".strip() or email.split("@")[0]

    faculty = User(
        email=email,
        password_hash=hash_password(password or secrets_token()),
        role=UserRole.faculty,
        full_name=full_name,
        is_active=(data.get("status") or "active") == "active",
        employee_id=(data.get("employeeId") or "").strip() or None,
        department=(data.get("department") or "").strip() or None,
        rank=(data.get("rank") or "").strip() or None,
        phone=(data.get("phone") or "").strip() or None,
    )
    db.session.add(faculty)
    db.session.flush()
    db.session.add(FacultyAssessment(user_id=faculty.id))
    reviewer_pid = data.get("reviewerId")
    reviewer_uid = parse_portal_user_id(reviewer_pid)
    if reviewer_uid:
        rev = User.query.filter_by(id=reviewer_uid, role=UserRole.reviewer).first()
        if rev:
            db.session.add(ReviewerAssignment(reviewer_user_id=rev.id, faculty_user_id=faculty.id))
    db.session.commit()
    log_activity(user.email, f"Faculty record added: {full_name}")
    return jsonify({"faculty": faculty.to_faculty_dict(reviewer_id_for(faculty.id))}), 201


def secrets_token() -> str:
    import secrets

    return secrets.token_urlsafe(16) + "Aa1!"


def reviewer_id_for(faculty_user_id: int) -> str | None:
    from app.services.portal_state import reviewer_id_for_faculty

    return reviewer_id_for_faculty(faculty_user_id)


@bp.put("/api/admin/faculty/<portal_id>")
@require_roles(UserRole.admin)
def update_faculty(portal_id: str):
    actor = current_user()
    uid = parse_portal_user_id(portal_id)
    if not uid:
        return jsonify({"error": "Invalid id."}), 400
    faculty = User.query.filter_by(id=uid, role=UserRole.faculty).first()
    if not faculty:
        return jsonify({"error": "Not found."}), 404
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or faculty.email).strip().lower()
    if email != faculty.email and User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 409

    first = (data.get("firstName") or "").strip()
    last = (data.get("lastName") or "").strip()
    if first or last:
        faculty.full_name = f"{first} {last}".strip() or faculty.full_name
    faculty.email = email
    faculty.employee_id = (data.get("employeeId") or faculty.employee_id or "").strip() or None
    faculty.department = (data.get("department") or faculty.department or "").strip() or None
    faculty.rank = (data.get("rank") or faculty.rank or "").strip() or None
    faculty.phone = (data.get("phone") or faculty.phone or "").strip() or None
    if "status" in data:
        faculty.is_active = data.get("status") == "active"

    rev_pid = data.get("reviewerId")
    ReviewerAssignment.query.filter_by(faculty_user_id=faculty.id).delete()
    rev_uid = parse_portal_user_id(rev_pid)
    if rev_uid:
        rev = User.query.filter_by(id=rev_uid, role=UserRole.reviewer).first()
        if rev:
            db.session.add(ReviewerAssignment(reviewer_user_id=rev.id, faculty_user_id=faculty.id))
    db.session.commit()
    log_activity(actor.email, f"Faculty record updated: {faculty.full_name}")
    return jsonify({"faculty": faculty.to_faculty_dict(reviewer_id_for(faculty.id))})


@bp.post("/api/admin/reviewers")
@require_roles(UserRole.admin)
def create_reviewer():
    actor = current_user()
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email:
        return jsonify({"error": "Email required."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 409
    if password and len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    first = (data.get("firstName") or "").strip()
    last = (data.get("lastName") or "").strip()
    full_name = f"{first} {last}".strip() or email.split("@")[0]
    reviewer = User(
        email=email,
        password_hash=hash_password(password or secrets_token()),
        role=UserRole.reviewer,
        full_name=full_name,
        is_active=(data.get("status") or "active") == "active",
        employee_id=(data.get("employeeId") or "").strip() or None,
        department=(data.get("department") or "").strip() or None,
    )
    db.session.add(reviewer)
    db.session.commit()
    log_activity(actor.email, f"Reviewer added: {full_name}")
    return jsonify({"reviewer": reviewer.to_reviewer_dict([])}), 201


@bp.put("/api/admin/reviewers/<portal_id>")
@require_roles(UserRole.admin)
def update_reviewer(portal_id: str):
    actor = current_user()
    uid = parse_portal_user_id(portal_id)
    reviewer = User.query.filter_by(id=uid, role=UserRole.reviewer).first() if uid else None
    if not reviewer:
        return jsonify({"error": "Not found."}), 404
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or reviewer.email).strip().lower()
    if email != reviewer.email and User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 409
    first = (data.get("firstName") or "").strip()
    last = (data.get("lastName") or "").strip()
    if first or last:
        reviewer.full_name = f"{first} {last}".strip() or reviewer.full_name
    reviewer.email = email
    reviewer.employee_id = (data.get("employeeId") or reviewer.employee_id or "").strip() or None
    reviewer.department = (data.get("department") or reviewer.department or "").strip() or None
    if "status" in data:
        reviewer.is_active = data.get("status") == "active"
    db.session.commit()
    log_activity(actor.email, f"Reviewer updated: {reviewer.full_name}")
    from app.services.portal_state import assigned_faculty_ids

    return jsonify({"reviewer": reviewer.to_reviewer_dict(assigned_faculty_ids(reviewer.id))})


@bp.put("/api/admin/reviewers/<portal_id>/assignments")
@require_roles(UserRole.admin)
def set_assignments(portal_id: str):
    actor = current_user()
    uid = parse_portal_user_id(portal_id)
    reviewer = User.query.filter_by(id=uid, role=UserRole.reviewer).first() if uid else None
    if not reviewer:
        return jsonify({"error": "Not found."}), 404
    data = request.get_json(silent=True) or {}
    faculty_ids = data.get("assignedFacultyIds") or []
    faculty_uids = [parse_portal_user_id(pid) for pid in faculty_ids]
    faculty_uids = [x for x in faculty_uids if x]

    ReviewerAssignment.query.filter_by(reviewer_user_id=reviewer.id).delete()
    for fid in faculty_uids:
        fac = User.query.filter_by(id=fid, role=UserRole.faculty).first()
        if not fac:
            continue
        ReviewerAssignment.query.filter_by(faculty_user_id=fac.id).delete()
        db.session.add(ReviewerAssignment(reviewer_user_id=reviewer.id, faculty_user_id=fac.id))
    db.session.commit()
    log_activity(actor.email, f"Assignments updated for {reviewer.full_name}")
    from app.services.portal_state import assigned_faculty_ids

    return jsonify({"reviewer": reviewer.to_reviewer_dict(assigned_faculty_ids(reviewer.id))})


@bp.put("/api/config/institution")
@require_roles(UserRole.admin)
def put_institution():
    actor = current_user()
    data = request.get_json(silent=True) or {}
    set_json(INSTITUTION_KEY, data)
    log_activity(actor.email, "Updated evaluation period settings")
    return jsonify({"ok": True, "institutionConfig": data})


@bp.get("/api/config/institution")
def get_institution():
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401
    cfg = get_json(INSTITUTION_KEY)
    if not cfg:
        return jsonify({"institutionConfig": None, "configured": False})
    return jsonify({"institutionConfig": cfg, "configured": True})


@bp.get("/api/config/catalog")
def get_catalog():
    user = current_user()
    if not user:
        return jsonify({"error": "Not authenticated."}), 401
    pub = get_json(CATALOG_PUBLISHED_KEY)
    meta = get_json(ASSESSMENT_CONFIG_KEY, {"activePublishedId": None, "versions": []})
    draft = get_json(CATALOG_DRAFT_KEY) if user.role == UserRole.admin else None
    if user.role != UserRole.admin:
        from app.services.catalog import filter_config_for_non_admin

        meta = filter_config_for_non_admin(meta)
        draft = None
    if not pub and not draft:
        return jsonify({"configured": False, "catalogPublished": None, "configDraft": None, "assessmentConfig": meta})
    return jsonify(
        {
            "configured": bool(pub),
            "catalogPublished": pub,
            "configDraft": draft,
            "assessmentConfig": meta,
            "configPublished": pub.get("version") if isinstance(pub, dict) else None,
        }
    )


@bp.put("/api/config/catalog/draft")
@require_roles(UserRole.admin)
def put_catalog_draft():
    actor = current_user()
    data = request.get_json(silent=True) or {}
    if data.get("assessmentConfig"):
        set_json(ASSESSMENT_CONFIG_KEY, data["assessmentConfig"])
        log_activity(actor.email, "Saved scoring rules draft")
    elif data.get("catalog"):
        set_json(CATALOG_DRAFT_KEY, data)
    return jsonify({"ok": True})


@bp.put("/api/config/assessment-meta")
@require_roles(UserRole.admin)
def put_assessment_meta():
    data = request.get_json(silent=True) or {}
    set_json(ASSESSMENT_CONFIG_KEY, data)
    return jsonify({"ok": True})


@bp.post("/api/config/catalog/publish")
@require_roles(UserRole.admin)
def publish_catalog():
    actor = current_user()
    data = request.get_json(silent=True) or {}
    meta = data.get("assessmentConfig")
    if meta:
        set_json(ASSESSMENT_CONFIG_KEY, meta)
        active = meta.get("activePublishedId")
        published = next((v for v in meta.get("versions", []) if v.get("id") == active), None)
        if published and published.get("catalog"):
            set_json(CATALOG_PUBLISHED_KEY, published["catalog"])
        log_activity(actor.email, f"Published assessment configuration {active or ''}")
        set_json(CATALOG_DRAFT_KEY, None)
        return jsonify({"ok": True, "version": active})
    catalog = data.get("catalog")
    if not catalog:
        return jsonify({"error": "Catalog body required."}), 400
    set_json(CATALOG_PUBLISHED_KEY, catalog)
    meta = get_json(ASSESSMENT_CONFIG_KEY, {"activePublishedId": None, "versions": []})
    version = catalog.get("version") or f"v-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    meta["activePublishedId"] = version
    versions = meta.get("versions") or []
    versions.append({"id": version, "publishedAt": datetime.now(timezone.utc).isoformat(), "catalog": catalog})
    meta["versions"] = versions[-20:]
    set_json(ASSESSMENT_CONFIG_KEY, meta)
    set_json(CATALOG_DRAFT_KEY, None)
    log_activity(actor.email, f"Published assessment configuration {version}")
    return jsonify({"ok": True, "version": version})


@bp.patch("/api/documents/<public_id>/review")
@require_roles(UserRole.admin, UserRole.reviewer)
def review_document(public_id: str):
    actor = current_user()
    doc = Document.query.filter_by(public_id=public_id, upload_status="stored").first()
    if not doc:
        return jsonify({"error": "Not found."}), 404
    if not faculty_may_access_document(actor, doc.owner_user_id):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True) or {}
    status = data.get("reviewStatus")
    if status not in ("approved", "rejected", "correction_requested", "pending"):
        return jsonify({"error": "Invalid review status."}), 400
    doc.review_status = status
    doc.review_remarks = (data.get("remarks") or doc.review_remarks or "").strip() or None
    if data.get("verifiedPoints") is not None:
        doc.verified_points = data.get("verifiedPoints")
    doc.reviewed_by_user_id = actor.id
    doc.reviewed_at = datetime.now(timezone.utc)
    sync_review_to_assessment(doc)
    db.session.commit()

    owner = User.query.get(doc.owner_user_id)
    if owner:
        title = {
            "approved": "Document approved",
            "rejected": "Document rejected",
            "correction_requested": "Correction requested",
        }.get(status, "Document updated")
        db.session.add(
            Notification(
                user_id=owner.id,
                title=title,
                body=doc.review_remarks or f"Status: {status}",
                read=False,
            )
        )
        db.session.commit()
    log_activity(actor.email, f"{status} document {doc.original_filename}")
    pid = owner.portal_id() if owner else ""
    return jsonify({"document": doc.to_portal_dict(pid)})


@bp.patch("/api/admin/faculty/<portal_id>/status")
@require_roles(UserRole.admin)
def patch_faculty_status(portal_id: str):
    actor = current_user()
    uid = parse_portal_user_id(portal_id)
    faculty = User.query.filter_by(id=uid, role=UserRole.faculty).first() if uid else None
    if not faculty:
        return jsonify({"error": "Not found."}), 404
    status = (request.get_json(silent=True) or {}).get("status")
    active = status == "active"
    faculty.is_active = active
    if not active:
        logout_user_all(faculty)
    db.session.commit()
    log_activity(actor.email, f"Faculty {'activated' if active else 'deactivated'}: {faculty.full_name}")
    return jsonify({"faculty": faculty.to_faculty_dict(reviewer_id_for(faculty.id))})


@bp.patch("/api/admin/reviewers/<portal_id>/status")
@require_roles(UserRole.admin)
def patch_reviewer_status(portal_id: str):
    actor = current_user()
    uid = parse_portal_user_id(portal_id)
    reviewer = User.query.filter_by(id=uid, role=UserRole.reviewer).first() if uid else None
    if not reviewer:
        return jsonify({"error": "Not found."}), 404
    status = (request.get_json(silent=True) or {}).get("status")
    active = status == "active"
    reviewer.is_active = active
    if not active:
        logout_user_all(reviewer)
    db.session.commit()
    log_activity(actor.email, f"Reviewer {'activated' if active else 'deactivated'}: {reviewer.full_name}")
    from app.services.portal_state import assigned_faculty_ids

    return jsonify({"reviewer": reviewer.to_reviewer_dict(assigned_faculty_ids(reviewer.id))})
