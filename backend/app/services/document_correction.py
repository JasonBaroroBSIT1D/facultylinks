"""Faculty document replace + resubmit after reviewer requests changes."""

from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db
from app.models import Document, Notification, ReviewerAssignment, User
from app.services.assessment_sync import attach_upload_to_assessment, sync_review_to_assessment

# Replacement uploaded; processing may still run — not in reviewer queue until resubmit.
REVIEW_CORRECTION_PREPARED = "correction_prepared"


def faculty_may_replace_document(doc: Document) -> bool:
    if doc.upload_status != "stored":
        return False
    if doc.superseded_by_public_id:
        return False
    return doc.review_status == "correction_requested"


def faculty_may_resubmit_document(doc: Document) -> bool:
    if doc.upload_status != "stored":
        return False
    if doc.superseded_by_public_id:
        return False
    if doc.review_status == REVIEW_CORRECTION_PREPARED:
        return True
    return False


def apply_document_replacement(*, old: Document, new: Document) -> None:
    """Mark [old] superseded; new row awaits faculty resubmit (correction_prepared)."""
    if not faculty_may_replace_document(old):
        raise ValueError("Document is not eligible for replacement.")
    if old.owner_user_id != new.owner_user_id:
        raise ValueError("Owner mismatch.")
    new.entry_id = old.entry_id or new.entry_id
    new.indicator_id = new.indicator_id or old.indicator_id
    new.kra_id = new.kra_id or old.kra_id
    new.criterion_id = new.criterion_id or old.criterion_id
    new.estimated_points = new.estimated_points if new.estimated_points is not None else old.estimated_points
    new.review_status = REVIEW_CORRECTION_PREPARED
    new.verified_points = None
    new.review_remarks = None
    new.reviewed_by_user_id = None
    new.reviewed_at = None

    old.review_status = "replaced"
    old.superseded_by_public_id = new.public_id


def finalize_replacement_assessment(new: Document, *, title: str | None = None) -> None:
    attach_upload_to_assessment(new, title=title, estimated_points=float(new.estimated_points or 0))
    from app.models import FacultyAssessment

    row = FacultyAssessment.query.get(new.owner_user_id)
    if not row or not new.indicator_id:
        return
    data = row.data or {}
    entries = (data.get("entries") or {}).get(new.indicator_id) or []
    for e in entries:
        if e.get("linkedDocumentId") == new.public_id or e.get("id") == new.entry_id:
            e["reviewStatus"] = REVIEW_CORRECTION_PREPARED
            e["verifiedPoints"] = None
            e["reviewerVerifiedPoints"] = None
            e["linkedDocumentId"] = new.public_id
            break
    row.data = data


def swap_achievement_document_reference(owner_user_id: int, old_public_id: str, new_public_id: str) -> None:
    from app.models import FacultyAssessment
    from app.services.achievements_store import get_achievement
    from sqlalchemy.orm.attributes import flag_modified

    row = FacultyAssessment.query.get(owner_user_id)
    if not row:
        return
    data = row.data or {}
    changed = False
    for ach in data.get("achievements") or []:
        if ach.get("reviewStatus") != "correction_requested":
            continue
        ids = list(ach.get("documentIds") or [])
        if old_public_id not in ids:
            continue
        ach["documentIds"] = [new_public_id if d == old_public_id else d for d in ids]
        changed = True
    if changed:
        row.data = data
        flag_modified(row, "data")


def resubmit_document_for_review(doc: Document, *, actor: User) -> Document:
    if doc.owner_user_id != actor.id:
        raise ValueError("Forbidden.")
    if not faculty_may_resubmit_document(doc):
        raise ValueError("This document is not ready to resubmit.")
    if doc.review_status != REVIEW_CORRECTION_PREPARED:
        raise ValueError("Invalid state for resubmit.")

    doc.review_status = "pending"
    doc.verified_points = None
    doc.reviewed_by_user_id = None
    doc.reviewed_at = None
    sync_review_to_assessment(doc)
    _notify_reviewers_document_resubmitted(doc)
    return doc


def _notify_reviewers_document_resubmitted(doc: Document) -> None:
    assignments = ReviewerAssignment.query.filter_by(faculty_user_id=doc.owner_user_id).all()
    title = "Document resubmitted for review"
    body = f"{doc.original_filename} was corrected and resubmitted."
    for a in assignments:
        db.session.add(
            Notification(
                user_id=a.reviewer_user_id,
                title=title,
                body=body,
                read=False,
            )
        )


def append_achievement_faculty_resubmit_history(ach: dict, *, user: User) -> None:
    hist = list(ach.get("reviewHistory") or [])
    hist.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "byUserId": user.id,
            "byEmail": user.email,
            "status": "resubmitted",
            "remarks": ach.get("reviewRemarks"),
            "reviewerVerifiedPoints": None,
            "claimedPoints": ach.get("claimedPoints"),
            "scoreChangeReason": None,
        }
    )
    ach["reviewHistory"] = hist[-30:]


def notify_reviewers_achievement_resubmitted(owner: User, ach: dict) -> None:
    assignments = ReviewerAssignment.query.filter_by(faculty_user_id=owner.id).all()
    title = "Achievement resubmitted for review"
    ind = ach.get("indicatorId") or ""
    body = f"{ach.get('title') or 'Achievement'} ({ind}) was resubmitted after corrections."
    for a in assignments:
        db.session.add(
            Notification(
                user_id=a.reviewer_user_id,
                title=title,
                body=body,
                read=False,
            )
        )