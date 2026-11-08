from __future__ import annotations

from collections import defaultdict

from app.models import (
    ActivityLog,
    Document,
    FacultyAssessment,
    Notification,
    ReviewerAssignment,
    User,
    UserRole,
)
from app.services.catalog import filter_config_for_non_admin, get_published_catalog_and_weights
from app.services.scoring_engine import compute_faculty_scores
from app.services.settings_store import (
    ASSESSMENT_CONFIG_KEY,
    CATALOG_DRAFT_KEY,
    CATALOG_PUBLISHED_KEY,
    INSTITUTION_KEY,
    get_json,
)

_PORTAL_DOC_LIMIT = 200
_PORTAL_NOTIF_LIMIT = 100
_PORTAL_ACTIVITY_LIMIT = 50


def parse_portal_user_id(pid: str | None) -> int | None:
    if not pid:
        return None
    if pid.startswith("u-"):
        try:
            return int(pid[2:])
        except ValueError:
            return None
    return None


def _slim_assessment_meta(meta: dict | None) -> dict:
    if not meta:
        return {"activePublishedId": None, "versions": [], "draftId": None, "previewDraft": False}
    versions = []
    for v in meta.get("versions", []):
        if not isinstance(v, dict):
            continue
        slim = {k: val for k, val in v.items() if k != "catalog"}
        versions.append(slim)
    return {
        "activePublishedId": meta.get("activePublishedId"),
        "draftId": meta.get("draftId"),
        "previewDraft": meta.get("previewDraft", False),
        "versions": versions,
    }


def _config_draft_for_client(meta: dict | None, catalog_draft_row) -> dict | None:
    if catalog_draft_row:
        return catalog_draft_row
    if not meta:
        return None
    draft_id = meta.get("draftId")
    if not draft_id:
        return None
    for v in meta.get("versions", []):
        if v.get("id") == draft_id and v.get("catalog"):
            return {"catalog": v["catalog"], "kraWeights": v.get("kraWeights") or {}}
    return None


def _assignment_maps():
    by_faculty: dict[int, ReviewerAssignment] = {}
    by_reviewer: dict[int, list[int]] = defaultdict(list)
    for a in ReviewerAssignment.query.all():
        by_faculty[a.faculty_user_id] = a
        by_reviewer[a.reviewer_user_id].append(a.faculty_user_id)
    return by_faculty, by_reviewer


def _users_by_id(user_ids: set[int]) -> dict[int, User]:
    if not user_ids:
        return {}
    rows = User.query.filter(User.id.in_(user_ids)).all()
    return {u.id: u for u in rows}


def build_assessments_map(faculty_users: list[User], faculty_ids: list[int]) -> dict:
    out = {}
    catalog, weights = get_published_catalog_and_weights()
    if not faculty_ids:
        return out
    rows = FacultyAssessment.query.filter(FacultyAssessment.user_id.in_(faculty_ids)).all()
    by_uid = {r.user_id: r for r in rows}
    id_to_user = {u.id: u for u in faculty_users}
    for uid in faculty_ids:
        u = id_to_user.get(uid)
        if not u:
            continue
        row = by_uid.get(uid)
        data = row.data if row else {"setSef": {"SET": [], "SEF": []}, "entries": {}}
        payload = {**data}
        if catalog and weights:
            payload["scoreSummary"] = compute_faculty_scores(data, catalog, weights)
        out[u.portal_id()] = payload
    return out


def build_portal_state(user: User, *, lite: bool = False) -> dict:
    institution_config = get_json(INSTITUTION_KEY)
    catalog_published = get_json(CATALOG_PUBLISHED_KEY)
    assessment_meta = get_json(ASSESSMENT_CONFIG_KEY, {"activePublishedId": None, "versions": []})
    catalog_draft_row = get_json(CATALOG_DRAFT_KEY) if user.role == UserRole.admin else None

    if user.role != UserRole.admin:
        assessment_meta = filter_config_for_non_admin(assessment_meta)
        catalog_draft_row = None

    by_faculty_assign, by_reviewer_assign = _assignment_maps()

    faculty_users = User.query.filter_by(role=UserRole.faculty).order_by(User.id).all()
    reviewer_users = User.query.filter_by(role=UserRole.reviewer).order_by(User.id).all()

    faculty = []
    for u in faculty_users:
        if user.role == UserRole.reviewer:
            if u.id not in by_reviewer_assign.get(user.id, []):
                continue
        assign = by_faculty_assign.get(u.id)
        reviewer_id = f"u-{assign.reviewer_user_id}" if assign else None
        faculty.append(u.to_faculty_dict(reviewer_id))

    reviewers = []
    for r in reviewer_users:
        if user.role == UserRole.reviewer and r.id != user.id:
            continue
        assigned = [f"u-{fid}" for fid in by_reviewer_assign.get(r.id, [])]
        reviewers.append(r.to_reviewer_dict(assigned))

    owner_ids: set[int]
    if user.role == UserRole.admin:
        owner_ids = {u.id for u in faculty_users}
    elif user.role == UserRole.reviewer:
        owner_ids = set(by_reviewer_assign.get(user.id, []))
    else:
        owner_ids = {user.id}

    if user.role == UserRole.admin:
        doc_rows = Document.query.order_by(Document.created_at.desc()).limit(_PORTAL_DOC_LIMIT).all()
    elif owner_ids:
        doc_rows = (
            Document.query.filter(Document.owner_user_id.in_(owner_ids))
            .order_by(Document.created_at.desc())
            .limit(_PORTAL_DOC_LIMIT)
            .all()
        )
    else:
        doc_rows = []

    owner_portal_ids = {uid: f"u-{uid}" for uid in owner_ids}
    doc_owner_ids = {d.owner_user_id for d in doc_rows}
    owners = _users_by_id(doc_owner_ids)

    documents = []
    for d in doc_rows:
        owner = owners.get(d.owner_user_id)
        if owner:
            documents.append(d.to_portal_dict(owner.portal_id()))

    assessment_faculty = faculty_users if user.role == UserRole.admin else [u for u in faculty_users if u.id in owner_ids]
    assessments = build_assessments_map(assessment_faculty, list(owner_ids) if user.role != UserRole.admin else [u.id for u in faculty_users])

    if user.role == UserRole.faculty:
        notif_rows = (
            Notification.query.filter_by(user_id=user.id)
            .order_by(Notification.created_at.desc())
            .limit(_PORTAL_NOTIF_LIMIT)
            .all()
        )
    elif user.role == UserRole.reviewer:
        fac_ids = by_reviewer_assign.get(user.id, [])
        if fac_ids:
            notif_rows = (
                Notification.query.filter(Notification.user_id.in_(fac_ids))
                .order_by(Notification.created_at.desc())
                .limit(_PORTAL_NOTIF_LIMIT)
                .all()
            )
        else:
            notif_rows = []
    else:
        notif_rows = (
            Notification.query.order_by(Notification.created_at.desc()).limit(_PORTAL_NOTIF_LIMIT).all()
        )

    notif_user_ids = {n.user_id for n in notif_rows}
    notif_users = _users_by_id(notif_user_ids)
    notifications = [
        {
            **n.to_dict(),
            "facultyId": notif_users[n.user_id].portal_id() if n.user_id in notif_users else None,
        }
        for n in notif_rows
    ]

    activity = [
        a.to_dict()
        for a in ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(_PORTAL_ACTIVITY_LIMIT).all()
    ]

    config_draft = None if lite else _config_draft_for_client(assessment_meta, catalog_draft_row)
    catalog_out = None if lite else catalog_published
    institution_out = institution_config if not lite or institution_config else None

    return {
        "user": user.to_public_dict(),
        "faculty": faculty,
        "reviewers": reviewers,
        "documents": documents,
        "assessments": assessments,
        "activity": activity,
        "notifications": notifications,
        "institutionConfig": institution_out,
        "catalogPublished": catalog_out,
        "configDraft": config_draft,
        "assessmentConfig": _slim_assessment_meta(assessment_meta),
        "configPublished": catalog_published.get("version") if isinstance(catalog_published, dict) else None,
        "configLite": lite,
    }


def reviewer_id_for_faculty(faculty_user_id: int) -> str | None:
    row = ReviewerAssignment.query.filter_by(faculty_user_id=faculty_user_id).first()
    if not row:
        return None
    return User.query.get(row.reviewer_user_id).portal_id()


def assigned_faculty_ids(reviewer_user_id: int) -> list[str]:
    rows = ReviewerAssignment.query.filter_by(reviewer_user_id=reviewer_user_id).all()
    out = []
    for r in rows:
        u = User.query.get(r.faculty_user_id)
        if u:
            out.append(u.portal_id())
    return out
