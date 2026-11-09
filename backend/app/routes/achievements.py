from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Notification, User, UserRole
from app.services.portal_state import parse_portal_user_id
from app.services.achievement_rules import expected_points_for_achievement
from app.services.achievements_store import (
    create_achievement,
    get_achievement,
    list_achievements,
    review_achievement,
    submit_achievement,
    update_achievement_draft,
)
from app.services.auth_context import current_user, faculty_may_access_document, require_roles
from app.services.catalog import CatalogValidationError, get_catalog_for_assessment
from app.services.activity import log_activity

bp = Blueprint("achievements", __name__)


def _catalog_for_faculty(user_id: int):
    from app.models import FacultyAssessment

    row = FacultyAssessment.query.get(user_id)
    data = row.data if row else {}
    return get_catalog_for_assessment(data)


@bp.get("/api/faculty/achievements")
@require_roles(UserRole.faculty)
def faculty_list_achievements():
    user = current_user()
    criterion_id = request.args.get("criterionId")
    indicator_id = request.args.get("indicatorId")
    catalog, _ = _catalog_for_faculty(user.id)
    items = list_achievements(user.id, criterion_id=criterion_id, indicator_id=indicator_id)
    return jsonify({"achievements": items, "catalogVersion": (catalog or {}).get("version")})


@bp.post("/api/faculty/achievements")
@require_roles(UserRole.faculty)
def faculty_create_achievement():
    user = current_user()
    catalog, _ = _catalog_for_faculty(user.id)
    if not catalog:
        return jsonify({"error": "Assessment configuration is not published."}), 400
    body = request.get_json(silent=True) or {}
    try:
        ach = create_achievement(user.id, body, catalog=catalog)
    except CatalogValidationError as e:
        return jsonify({"error": str(e)}), 400
    db.session.commit()
    return jsonify({"achievement": ach}), 201


@bp.put("/api/faculty/achievements/<achievement_id>")
@require_roles(UserRole.faculty)
def faculty_update_achievement(achievement_id: str):
    user = current_user()
    catalog, _ = _catalog_for_faculty(user.id)
    if not catalog:
        return jsonify({"error": "Assessment configuration is not published."}), 400
    body = request.get_json(silent=True) or {}
    try:
        ach = update_achievement_draft(user.id, achievement_id, body, catalog=catalog)
    except CatalogValidationError as e:
        return jsonify({"error": str(e)}), 400
    db.session.commit()
    return jsonify({"achievement": ach})


@bp.post("/api/faculty/achievements/<achievement_id>/submit")
@require_roles(UserRole.faculty)
def faculty_submit_achievement(achievement_id: str):
    user = current_user()
    catalog, _ = _catalog_for_faculty(user.id)
    if not catalog:
        return jsonify({"error": "Assessment configuration is not published."}), 400
    body = request.get_json(silent=True) or {}
    try:
        ach = submit_achievement(user.id, achievement_id, catalog=catalog, patch=body)
    except CatalogValidationError as e:
        return jsonify({"error": str(e)}), 400
    db.session.commit()
    return jsonify({"achievement": ach})


@bp.post("/api/faculty/achievements/preview-rule")
@require_roles(UserRole.faculty)
def faculty_preview_rule():
    user = current_user()
    catalog, _ = _catalog_for_faculty(user.id)
    if not catalog:
        return jsonify({"error": "Assessment configuration is not published."}), 400
    body = request.get_json(silent=True) or {}
    indicator_id = body.get("indicatorId")
    if not indicator_id:
        return jsonify({"error": "indicatorId is required."}), 400
    from app.models import FacultyAssessment

    row = FacultyAssessment.query.get(user.id)
    ctx = {"achievements": (row.data or {}).get("achievements") or []} if row else {}
    try:
        rule = expected_points_for_achievement(catalog, indicator_id, body, context=ctx)
    except CatalogValidationError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(rule)


@bp.get("/api/portal/faculty/<faculty_portal_id>/achievements")
@require_roles(UserRole.admin, UserRole.reviewer)
def portal_list_achievements(faculty_portal_id: str):
    actor = current_user()
    uid = parse_portal_user_id(faculty_portal_id)
    if not uid:
        return jsonify({"error": "Invalid faculty id."}), 400
    faculty = User.query.filter_by(id=uid, role=UserRole.faculty).first()
    if not faculty:
        return jsonify({"error": "Not found."}), 404
    if actor.role == UserRole.reviewer and not faculty_may_access_document(actor, faculty.id):
        return jsonify({"error": "Forbidden."}), 403
    criterion_id = request.args.get("criterionId")
    indicator_id = request.args.get("indicatorId")
    submitted_only = request.args.get("submitted", "").lower() in ("1", "true", "yes")
    catalog, _ = _catalog_for_faculty(faculty.id)
    items = list_achievements(faculty.id, criterion_id=criterion_id, indicator_id=indicator_id)
    if submitted_only:
        items = [a for a in items if a.get("submissionStatus") == "submitted"]
    return jsonify({"achievements": items, "facultyId": faculty.portal_id(), "catalogVersion": (catalog or {}).get("version")})


@bp.patch("/api/portal/achievements/<achievement_id>/review")
@require_roles(UserRole.admin, UserRole.reviewer)
def portal_review_achievement(achievement_id: str):
    actor = current_user()
    body = request.get_json(silent=True) or {}
    owner_portal_id = body.get("facultyId")
    if not owner_portal_id:
        return jsonify({"error": "facultyId is required."}), 400
    uid = parse_portal_user_id(owner_portal_id)
    faculty = User.query.filter_by(id=uid, role=UserRole.faculty).first() if uid else None
    if not faculty:
        return jsonify({"error": "Faculty not found."}), 404
    if actor.role == UserRole.reviewer and not faculty_may_access_document(actor, faculty.id):
        return jsonify({"error": "Forbidden."}), 403

    status = body.get("reviewStatus")
    try:
        ach = review_achievement(
            faculty.id,
            achievement_id,
            actor=actor,
            review_status=status,
            reviewer_verified_points=body.get("reviewerVerifiedPoints"),
            remarks=body.get("remarks"),
            score_change_reason=body.get("scoreChangeReason"),
        )
    except CatalogValidationError as e:
        return jsonify({"error": str(e)}), 400

    title = {
        "approved": "Achievement approved",
        "rejected": "Achievement rejected",
        "correction_requested": "Achievement — changes requested",
    }.get(status, "Achievement updated")
    db.session.add(
        Notification(
            user_id=faculty.id,
            title=title,
            body=body.get("remarks") or f"Indicator {ach.get('indicatorId')}: {status}",
            read=False,
        )
    )
    db.session.commit()
    log_activity(actor.email, f"{status} achievement {achievement_id} for {faculty.full_name}")
    return jsonify({"achievement": ach})


@bp.get("/api/faculty/achievements/<achievement_id>")
@require_roles(UserRole.faculty)
def faculty_get_achievement(achievement_id: str):
    user = current_user()
    ach = get_achievement(user.id, achievement_id)
    if not ach:
        return jsonify({"error": "Not found."}), 404
    return jsonify({"achievement": ach})
