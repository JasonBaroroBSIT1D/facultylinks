from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Document, FacultyAssessment, Notification, ReviewerAssignment, SetSefSemesterRecord, User, UserRole
from app.services.auth_context import current_user, require_roles
from app.services.portal_state import reviewer_id_for_faculty
from app.services.catalog import filter_config_for_non_admin, get_catalog_for_assessment, get_published_catalog_and_weights
from app.services.scoring_engine import compute_faculty_scores
from app.services.teaching_effectiveness import compute_criterion_a_from_records
from app.services.rank_simulation import compute_faculty_rank_simulation
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
    from app.services.catalog import pin_assessment_config_version_if_needed

    prev = row.data or {}
    payload = data.get("assessment") or data
    if "achievements" not in payload and prev.get("achievements"):
        payload = {**payload, "achievements": prev["achievements"]}
    elif "achievements" in payload and prev.get("achievements"):
        from app.services.achievements_store import merge_achievements_preserve_submitted

        payload = {
            **payload,
            "achievements": merge_achievements_preserve_submitted(prev, payload.get("achievements")),
        }
    from app.services.achievements_store import _persist_assessment_row

    pinned = pin_assessment_config_version_if_needed(user.id, payload)
    _persist_assessment_row(row, pinned)
    db.session.commit()
    return jsonify({"assessment": row.data})


@bp.get("/api/faculty/scores")
@require_roles(UserRole.faculty)
def faculty_scores():
    user = current_user()
    row = FacultyAssessment.query.get(user.id)
    data = row.data if row else {"setSef": {"SET": [], "SEF": []}, "entries": {}}
    catalog, weights = get_catalog_for_assessment(data)
    if not catalog or not weights:
        return jsonify({"configured": False, "scores": None, "rankSimulation": None}), 200
    scores = compute_faculty_scores(data, catalog, weights, faculty_user_id=user.id)
    institution = get_json(INSTITUTION_KEY) or {}
    rank_simulation = compute_faculty_rank_simulation(
        faculty_rank=user.rank,
        faculty_scores=scores,
        institution_config=institution,
    )
    return jsonify(
        {
            "configured": True,
            "scores": scores,
            "rankSimulation": rank_simulation,
            "configVersionId": data.get("configVersionId"),
        }
    )


@bp.get("/api/faculty/config/catalog")
@require_roles(UserRole.faculty)
def faculty_catalog():
    user = current_user()
    row = FacultyAssessment.query.get(user.id)
    assessment_data = row.data if row else {}
    catalog, kra_weights = get_catalog_for_assessment(assessment_data)
    meta = filter_config_for_non_admin(get_json(ASSESSMENT_CONFIG_KEY, {"versions": []}))
    return jsonify(
        {
            "assessmentConfig": meta,
            "configured": bool(catalog),
            "catalog": catalog,
            "kraWeights": kra_weights,
        }
    )


@bp.get("/api/faculty/teaching-effectiveness/criterion-a")
@require_roles(UserRole.faculty)
def faculty_criterion_a():
    from app.services.set_sef_aggregation import (
        MAX_SEMESTER_SLOTS,
        aggregate_set_sef_for_faculty,
        apply_semester_slot_window,
        merged_slots_to_scoring_records,
    )

    user = current_user()
    from app.services.catalog import scoring_window_semester_keys

    row = FacultyAssessment.query.get(user.id)
    assessment_data = row.data if row else {}
    slots, docs, conflicts = aggregate_set_sef_for_faculty(user.id)
    selected = scoring_window_semester_keys(assessment_data)
    scoring_slots, excluded_slots, window_findings, window_needs_selection = apply_semester_slot_window(
        slots, selected_semester_keys=selected
    )
    window_blocked = bool(window_findings) and not window_needs_selection
    if not docs:
        return jsonify(
            {
                "documents": [],
                "mergedSemesters": [],
                "scoring": None,
                "aggregationConflicts": [],
                "message": "No SET/SEF PDF uploads yet (combined, SET-only, or SEF-only).",
            }
        )
    config_version = docs[0].config_version if docs else None
    catalog, _weights = get_catalog_for_assessment(assessment_data)
    pinned_version = assessment_data.get("configVersionId")
    proxy_records = merged_slots_to_scoring_records(scoring_slots, conflicts)
    window_msg = window_findings[0]["message"] if window_findings else None
    est = compute_criterion_a_from_records(
        proxy_records,
        verified_only=False,
        config_version=pinned_version or config_version,
        catalog=catalog,
        slot_window_blocked=window_blocked,
        window_needs_selection=window_needs_selection,
        window_message=window_msg,
    )
    ver = compute_criterion_a_from_records(
        proxy_records,
        verified_only=True,
        config_version=pinned_version or config_version,
        catalog=catalog,
        slot_window_blocked=window_blocked,
        window_needs_selection=window_needs_selection,
        window_message=window_msg,
    )
    return jsonify(
        {
            "documents": [d.to_dict() for d in docs],
            "mergedSemesters": [s.to_dict() for s in slots],
            "scoringSlots": [s.to_dict() for s in scoring_slots],
            "excludedSemesterSlots": [s.to_dict() for s in excluded_slots],
            "slotWindowFindings": window_findings,
            "aggregationConflicts": [
                {
                    "semesterKey": c.semester_key,
                    "field": c.field,
                    "documentIds": c.document_ids,
                    "explanation": c.explanation,
                }
                for c in conflicts
            ],
            "scoring": {"estimated": est, "verified": ver},
        }
    )


@bp.put("/api/faculty/assessment/scoring-window")
@require_roles(UserRole.faculty)
def faculty_set_scoring_window():
    from app.services.catalog import CatalogValidationError, set_scoring_window_semester_keys

    user = current_user()
    body = request.get_json(silent=True) or {}
    keys = body.get("semesterKeys") or []
    row = FacultyAssessment.query.get(user.id)
    if not row:
        row = FacultyAssessment(user_id=user.id, data={"setSef": {"SET": [], "SEF": []}, "entries": {}})
        db.session.add(row)
    data = row.data or {"setSef": {"SET": [], "SEF": []}, "entries": {}}
    try:
        row.data = set_scoring_window_semester_keys(data, keys, actor_email=user.email)
    except CatalogValidationError as e:
        return jsonify({"error": str(e)}), 400
    db.session.commit()
    return jsonify({"assessment": row.data})


@bp.get("/api/faculty/notifications")
@require_roles(UserRole.faculty)
def faculty_notifications():
    user = current_user()
    rows = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return jsonify({"notifications": [n.to_dict() for n in rows]})
