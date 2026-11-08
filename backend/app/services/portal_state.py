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
    CATALOG_DRAFT_KEY,
    CATALOG_PUBLISHED_KEY,
    INSTITUTION_KEY,
    ASSESSMENT_CONFIG_KEY,
    get_json,
)


def parse_portal_user_id(pid: str | None) -> int | None:
    if not pid:
        return None
    if pid.startswith("u-"):
        try:
            return int(pid[2:])
        except ValueError:
            return None
    return None


def reviewer_id_for_faculty(faculty_user_id: int) -> str | None:
    row = ReviewerAssignment.query.filter_by(faculty_user_id=faculty_user_id).first()
    if not row:
        return None
    return User.query.get(row.reviewer_user_id).portal_id()


def assigned_faculty_ids(reviewer_user_id: int) -> list[str]:
    rows = ReviewerAssignment.query.filter_by(reviewer_user_id=reviewer_user_id).all()
    return [User.query.get(r.faculty_user_id).portal_id() for r in rows if User.query.get(r.faculty_user_id)]


def build_assessments_map(faculty_users: list[User]) -> dict:
    out = {}
    catalog, weights = get_published_catalog_and_weights()
    for u in faculty_users:
        row = FacultyAssessment.query.get(u.id)
        data = row.data if row else {"setSef": {"SET": [], "SEF": []}, "entries": {}}
        payload = {**data}
        if catalog and weights:
            payload["scoreSummary"] = compute_faculty_scores(data, catalog, weights)
        out[u.portal_id()] = payload
    return out


def build_portal_state(user: User) -> dict:
    institution_config = get_json(INSTITUTION_KEY)
    catalog_published = get_json(CATALOG_PUBLISHED_KEY)
    assessment_meta = get_json(ASSESSMENT_CONFIG_KEY, {"activePublishedId": None, "versions": []})
    if user.role == UserRole.admin:
        catalog_draft = get_json(CATALOG_DRAFT_KEY)
    else:
        assessment_meta = filter_config_for_non_admin(assessment_meta)
        catalog_draft = None

    faculty_users = User.query.filter_by(role=UserRole.faculty).order_by(User.id).all()
    reviewer_users = User.query.filter_by(role=UserRole.reviewer).order_by(User.id).all()

    faculty = []
    for u in faculty_users:
        if user.role == UserRole.reviewer:
            if not ReviewerAssignment.query.filter_by(
                reviewer_user_id=user.id, faculty_user_id=u.id
            ).first():
                continue
        faculty.append(u.to_faculty_dict(reviewer_id_for_faculty(u.id)))

    reviewers = []
    for r in reviewer_users:
        if user.role == UserRole.reviewer and r.id != user.id:
            continue
        reviewers.append(r.to_reviewer_dict(assigned_faculty_ids(r.id)))

    owner_ids = {u.id for u in faculty_users}
    if user.role == UserRole.reviewer:
        owner_ids = {
            a.faculty_user_id
            for a in ReviewerAssignment.query.filter_by(reviewer_user_id=user.id).all()
        }
    elif user.role == UserRole.faculty:
        owner_ids = {user.id}

    if user.role == UserRole.admin:
        docs_query = Document.query.order_by(Document.created_at.desc()).limit(500)
    elif owner_ids:
        docs_query = (
            Document.query.filter(Document.owner_user_id.in_(owner_ids))
            .order_by(Document.created_at.desc())
            .limit(500)
        )
    else:
        docs_query = None
    documents = []
    doc_rows = docs_query.all() if docs_query is not None else []
    for d in doc_rows:
        owner = User.query.get(d.owner_user_id)
        if owner:
            documents.append(d.to_portal_dict(owner.portal_id()))

    assessments = build_assessments_map(
        [u for u in faculty_users if u.id in owner_ids or user.role == UserRole.admin]
    )

    notif_query = Notification.query
    if user.role == UserRole.faculty:
        notif_query = notif_query.filter_by(user_id=user.id)
    elif user.role == UserRole.reviewer:
        fac_ids = [a.faculty_user_id for a in ReviewerAssignment.query.filter_by(reviewer_user_id=user.id)]
        notif_query = Notification.query.filter(Notification.user_id.in_(fac_ids)) if fac_ids else Notification.query.filter_by(user_id=-1)
    else:
        notif_query = Notification.query

    notifications = [
        {**n.to_dict(), "facultyId": User.query.get(n.user_id).portal_id() if User.query.get(n.user_id) else None}
        for n in notif_query.order_by(Notification.created_at.desc()).limit(100).all()
    ]

    activity = [a.to_dict() for a in ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(50).all()]

    return {
        "faculty": faculty,
        "reviewers": reviewers,
        "documents": documents,
        "assessments": assessments,
        "activity": activity,
        "notifications": notifications,
        "institutionConfig": institution_config,
        "catalogPublished": catalog_published,
        "configDraft": catalog_draft,
        "assessmentConfig": assessment_meta,
        "configPublished": catalog_published.get("version") if isinstance(catalog_published, dict) else None,
    }
