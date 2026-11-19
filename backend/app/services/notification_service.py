"""Create, serialize, and authorize in-app notifications."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.extensions import db
from app.models import Document, Notification, ReviewerAssignment, User
from app.services.assessment_report import _indicator_label
from app.services.catalog import get_published_catalog_and_weights

MANILA = ZoneInfo("Asia/Manila")

FACULTY_EVENT_TYPES = frozenset(
    {
        "document_review_decision",
        "achievement_review_decision",
    }
)
REVIEWER_EVENT_TYPES = frozenset(
    {
        "document_resubmitted",
        "document_submitted",
        "achievement_submitted",
        "achievement_resubmitted",
    }
)


def _catalog():
    catalog, _ = get_published_catalog_and_weights()
    return catalog


def create_notification(
    *,
    recipient_user_id: int,
    event_type: str,
    title: str,
    body: str,
    actor_user_id: int | None = None,
    subject_faculty_user_id: int | None = None,
    target_type: str | None = None,
    target_document_public_id: str | None = None,
    target_achievement_id: str | None = None,
    kra_id: str | None = None,
    criterion_id: str | None = None,
    indicator_id: str | None = None,
    dedupe_key: str | None = None,
) -> Notification | None:
    if dedupe_key:
        existing = Notification.query.filter_by(user_id=recipient_user_id, dedupe_key=dedupe_key).first()
        if existing:
            return existing
    note = Notification(
        user_id=recipient_user_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        subject_faculty_user_id=subject_faculty_user_id,
        target_type=target_type,
        target_document_public_id=target_document_public_id,
        target_achievement_id=target_achievement_id,
        kra_id=kra_id,
        criterion_id=criterion_id,
        indicator_id=indicator_id,
        dedupe_key=dedupe_key,
        title=title,
        body=body,
        read=False,
    )
    db.session.add(note)
    db.session.flush()
    return note


def notify_faculty_document_review(*, owner: User, doc: Document, actor: User, status: str) -> None:
    status_labels = {
        "approved": "Document approved",
        "rejected": "Document declined",
        "correction_requested": "Correction requested",
        "pending": "Document updated",
    }
    title = status_labels.get(status, "Document updated")
    remarks = (doc.review_remarks or "").strip()
    body = remarks if remarks else f"Your file “{doc.original_filename}” was reviewed."
    dedupe = None
    if doc.reviewed_at:
        dedupe = f"doc_review:{doc.public_id}:{status}:{int(doc.reviewed_at.timestamp())}"
    create_notification(
        recipient_user_id=owner.id,
        event_type="document_review_decision",
        title=title,
        body=body,
        actor_user_id=actor.id,
        subject_faculty_user_id=owner.id,
        target_type="document",
        target_document_public_id=doc.public_id,
        kra_id=doc.kra_id,
        criterion_id=doc.criterion_id,
        indicator_id=doc.indicator_id,
        dedupe_key=dedupe,
    )


def notify_faculty_achievement_review(
    *,
    faculty: User,
    achievement_id: str,
    ach: dict,
    actor: User,
    status: str,
    remarks: str | None,
) -> None:
    status_labels = {
        "approved": "Achievement approved",
        "rejected": "Achievement declined",
        "correction_requested": "Changes requested on achievement",
    }
    title = status_labels.get(status, "Achievement updated")
    ach_title = (ach.get("title") or "Achievement").strip()
    note = (remarks or "").strip()
    body = note if note else f"“{ach_title}” was reviewed."
    dedupe = f"ach_review:{achievement_id}:{status}:{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    create_notification(
        recipient_user_id=faculty.id,
        event_type="achievement_review_decision",
        title=title,
        body=body,
        actor_user_id=actor.id,
        subject_faculty_user_id=faculty.id,
        target_type="achievement",
        target_achievement_id=achievement_id,
        kra_id=ach.get("kraId"),
        criterion_id=ach.get("criterionId"),
        indicator_id=ach.get("indicatorId"),
        dedupe_key=dedupe,
    )


def _assigned_reviewer_ids(faculty_user_id: int) -> list[int]:
    return [
        a.reviewer_user_id
        for a in ReviewerAssignment.query.filter_by(faculty_user_id=faculty_user_id).all()
    ]


def notify_reviewers_document_resubmitted(doc: Document) -> None:
    owner = User.query.get(doc.owner_user_id)
    title = "Document resubmitted"
    body = f"{owner.full_name if owner else 'Faculty'} corrected “{doc.original_filename}” and sent it back for review."
    dedupe = f"doc_resubmit:{doc.public_id}:{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    for rid in _assigned_reviewer_ids(doc.owner_user_id):
        create_notification(
            recipient_user_id=rid,
            event_type="document_resubmitted",
            title=title,
            body=body,
            actor_user_id=doc.owner_user_id,
            subject_faculty_user_id=doc.owner_user_id,
            target_type="document",
            target_document_public_id=doc.public_id,
            kra_id=doc.kra_id,
            criterion_id=doc.criterion_id,
            indicator_id=doc.indicator_id,
            dedupe_key=dedupe,
        )


def notify_reviewers_document_submitted(doc: Document, *, actor: User) -> None:
    """Non–achievement-evidence uploads that enter the reviewer queue as pending."""
    from app.services.catalog import is_kra_i_achievement_indicator

    if is_kra_i_achievement_indicator(doc.indicator_id):
        return
    if (doc.review_status or "pending") not in ("pending",):
        return
    title = "New document to review"
    body = f"{actor.full_name} submitted “{doc.original_filename}” for review."
    dedupe = f"doc_submit:{doc.public_id}"
    for rid in _assigned_reviewer_ids(doc.owner_user_id):
        create_notification(
            recipient_user_id=rid,
            event_type="document_submitted",
            title=title,
            body=body,
            actor_user_id=actor.id,
            subject_faculty_user_id=actor.id,
            target_type="document",
            target_document_public_id=doc.public_id,
            kra_id=doc.kra_id,
            criterion_id=doc.criterion_id,
            indicator_id=doc.indicator_id,
            dedupe_key=dedupe,
        )


def notify_reviewers_achievement_submitted(owner: User, ach: dict, *, resubmit: bool) -> None:
    ind = ach.get("indicatorId") or ""
    ach_title = (ach.get("title") or "Achievement").strip()
    event_type = "achievement_resubmitted" if resubmit else "achievement_submitted"
    title = "Achievement resubmitted" if resubmit else "Achievement submitted for review"
    body = f"{owner.full_name}: “{ach_title}”"
    submitted_at = ach.get("submittedAt") or datetime.now(timezone.utc).isoformat()
    dedupe = f"{event_type}:{ach.get('id')}:{submitted_at}"
    for rid in _assigned_reviewer_ids(owner.id):
        create_notification(
            recipient_user_id=rid,
            event_type=event_type,
            title=title,
            body=body,
            actor_user_id=owner.id,
            subject_faculty_user_id=owner.id,
            target_type="achievement",
            target_achievement_id=ach.get("id"),
            kra_id=ach.get("kraId"),
            criterion_id=ach.get("criterionId"),
            indicator_id=ind or None,
            dedupe_key=dedupe,
        )


def _users_by_id(ids: set[int]) -> dict[int, User]:
    if not ids:
        return {}
    return {u.id: u for u in User.query.filter(User.id.in_(ids)).all()}


def _format_at_manila_win(created_at: datetime | None) -> str | None:
    if not created_at:
        return None
    dt = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    local = dt.astimezone(MANILA)
    h = local.strftime("%I").lstrip("0") or "12"
    return local.strftime(f"%b {local.day}, %Y · {h}:%M %p")


def serialize_notification(n: Notification) -> dict:
    catalog = _catalog()
    user_ids = {n.user_id}
    if n.actor_user_id:
        user_ids.add(n.actor_user_id)
    if n.subject_faculty_user_id:
        user_ids.add(n.subject_faculty_user_id)
    users = _users_by_id(user_ids)
    actor = users.get(n.actor_user_id) if n.actor_user_id else None
    subject = users.get(n.subject_faculty_user_id) if n.subject_faculty_user_id else None
    ind_label = _indicator_label(catalog, n.indicator_id) if n.indicator_id else None
    document_name = None
    achievement_title = None
    if n.target_document_public_id:
        doc = Document.query.filter_by(public_id=n.target_document_public_id, upload_status="stored").first()
        if doc:
            document_name = doc.original_filename
        elif n.target_type == "document":
            document_name = n.body.split("“")[-1].split("”")[0] if "“" in n.body else None
    if n.target_achievement_id and n.subject_faculty_user_id:
        from app.services.achievements_store import get_achievement

        ach = get_achievement(n.subject_faculty_user_id, n.target_achievement_id)
        if ach:
            achievement_title = ach.get("title")
    return {
        "id": str(n.id),
        "title": n.title,
        "body": n.body,
        "read": n.read,
        "at": n.created_at.isoformat() if n.created_at else None,
        "atManila": _format_at_manila_win(n.created_at),
        "eventType": n.event_type,
        "targetType": n.target_type,
        "targetDocumentPublicId": n.target_document_public_id,
        "targetAchievementId": n.target_achievement_id,
        "facultyId": subject.portal_id() if subject else None,
        "actorName": actor.full_name if actor else None,
        "subjectFacultyName": subject.full_name if subject else None,
        "documentFileName": document_name,
        "achievementTitle": achievement_title,
        "kraId": n.kra_id,
        "criterionId": n.criterion_id,
        "indicatorId": n.indicator_id,
        "indicatorLabel": ind_label,
        "navigable": bool(
            (n.target_type == "document" and n.target_document_public_id)
            or (n.target_type == "achievement" and n.target_achievement_id and n.subject_faculty_user_id)
        ),
    }


def notifications_for_user(user: User, *, limit: int = 100) -> list[dict]:
    rows = (
        Notification.query.filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return [serialize_notification(n) for n in rows]


def unread_count_for_user(user_id: int) -> int:
    return Notification.query.filter_by(user_id=user_id, read=False).count()


def mark_notification_read(notification_id: int, user: User) -> Notification | None:
    note = Notification.query.filter_by(id=notification_id, user_id=user.id).first()
    if not note:
        return None
    if not note.read:
        note.read = True
    return note


def user_may_open_notification_target(user: User, payload: dict) -> tuple[bool, str | None]:
    """Check recipient can open the linked target (not for granting review actions)."""
    target = payload.get("targetType")
    if not payload.get("navigable"):
        return False, "This notification has no linked record. Open it from your documents or assessment list."
    if target == "document":
        doc = Document.query.filter_by(
            public_id=payload.get("targetDocumentPublicId"), upload_status="stored"
        ).first()
        if not doc:
            return False, "This document is no longer available."
        from app.models import UserRole

        if user.role == UserRole.faculty and doc.owner_user_id != user.id:
            return False, "You do not have access to this document."
        if user.role == UserRole.reviewer:
            from app.services.document_correction import faculty_may_access_document

            if not faculty_may_access_document(user, doc.owner_user_id):
                return False, "This document is not in your assigned faculty list."
        return True, None
    if target == "achievement":
        fid = payload.get("facultyId")
        from app.routes.portal import parse_portal_user_id

        uid = parse_portal_user_id(fid) if fid else None
        ach_id = payload.get("targetAchievementId")
        if not uid or not ach_id:
            return False, "Achievement link is incomplete."
        from app.services.achievements_store import get_achievement

        ach = get_achievement(uid, ach_id)
        if not ach:
            return False, "This achievement is no longer available."
        from app.models import UserRole

        if user.role == UserRole.faculty and user.id != uid:
            return False, "You do not have access to this achievement."
        if user.role == UserRole.reviewer:
            from app.services.document_correction import faculty_may_access_document

            if not faculty_may_access_document(user, uid):
                return False, "This achievement is not in your assigned faculty list."
        return True, None
    return False, "Unknown notification target."