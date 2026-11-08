from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import FacultyAssessment, Notification, ReviewerAssignment, User, UserRole
from app.services.auth_context import current_user, require_roles
from app.services.portal_state import reviewer_id_for_faculty
from app.services.catalog import filter_config_for_non_admin, get_published_catalog_and_weights
from app.services.scoring_engine import compute_faculty_scores
from app.services.settings_store import ASSESSMENT_CONFIG_KEY, INSTITUTION_KEY, get_json

bp = Blueprint("faculty_portal", __name__)


@bp.get("/api/faculty/me")
@require_roles(UserRole.faculty)
def faculty_me():
    user = current_user()
    assert user
    rev_assignment = ReviewerAssignment.query.filter_by(faculty_user_id=user.id).first()
    reviewer_name = ""
    reviewer_role = "Assigned Evaluator"
    status = "Unassigned"
    if rev_assignment:
        rev = User.query.get(rev_assignment.reviewer_user_id)
        if rev:
            reviewer_name = rev.full_name
            status = "Active" if rev.is_active else "Inactive"
    return jsonify(
        {
            "profile": {
                "id": user.portal_id(),
                "userId": user.id,
                "name": user.full_name,
                "email": user.email,
                "rank": user.rank or "",
                "department": user.department or "",
                "reviewerName": reviewer_name,
                "reviewerRole": reviewer_role,
                "reviewerAssignmentStatus": status,
            }
        }
    )


@bp.get("/api/faculty/assessment")
@require_roles(UserRole.faculty)
def faculty_assessment():
    user = current_user()
    row = FacultyAssessment.query.get(user.id)
    if not row:
        row = FacultyAssessment(user_id=user.id)
        db.session.add(row)
        db.session.commit()
    return jsonify({"assessment": row.data})


@bp.put("/api/faculty/assessment")
@require_roles(UserRole.faculty)
def put_faculty_assessment():
    user = current_user()
    data = request.get_json(silent=True) or {}
    row = FacultyAssessment.query.get(user.id)
    if not row:
        row = FacultyAssessment(user_id=user.id)
        db.session.add(row)
    row.data = data.get("assessment") or data
    db.session.commit()
    return jsonify({"assessment": row.data})


@bp.get("/api/faculty/scores")
@require_roles(UserRole.faculty)
def faculty_scores():
    user = current_user()
    catalog, weights = get_published_catalog_and_weights()
    if not catalog or not weights:
        return jsonify({"configured": False, "scores": None}), 200
    row = FacultyAssessment.query.get(user.id)
    data = row.data if row else {"setSef": {"SET": [], "SEF": []}, "entries": {}}
    return jsonify({"configured": True, "scores": compute_faculty_scores(data, catalog, weights)})


@bp.get("/api/faculty/config/catalog")
@require_roles(UserRole.faculty)
def faculty_catalog():
    meta = filter_config_for_non_admin(get_json(ASSESSMENT_CONFIG_KEY, {"versions": []}))
    return jsonify({"assessmentConfig": meta, "configured": bool(meta.get("versions"))})


@bp.get("/api/faculty/notifications")
@require_roles(UserRole.faculty)
def faculty_notifications():
    user = current_user()
    rows = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return jsonify({"notifications": [n.to_dict() for n in rows]})
