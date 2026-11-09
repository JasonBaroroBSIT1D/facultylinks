"""Reviewer queue: separate legacy document review from KRA I B/C achievement review."""

from __future__ import annotations

from collections import defaultdict

from app.models import Document, FacultyAssessment, ReviewerAssignment, User, UserRole
from app.services.achievement_rules import is_active_achievement
from app.services.catalog import is_kra_i_achievement_indicator

_ACHIEVEMENT_REVIEW_OPEN = frozenset({"pending", "correction_requested"})


def _achievement_index_by_owner() -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = defaultdict(list)
    for row in FacultyAssessment.query.all():
        data = row.data or {}
        for ach in data.get("achievements") or []:
            if is_active_achievement(ach):
                out[row.user_id].append(ach)
    return out


def _link_for_document(public_id: str, achievements: list[dict]) -> dict | None:
    for ach in achievements:
        if public_id in (ach.get("documentIds") or []):
            return ach
    return None


def document_counts_toward_legacy_pending(doc: Document, achievements: list[dict]) -> bool:
    """True when this row is reviewer work in the document (legacy / SET/SEF) queue."""
    if doc.upload_status != "stored":
        return False
    if (doc.review_status or "pending") != "pending":
        return False
    if is_kra_i_achievement_indicator(doc.indicator_id):
        return False
    return True


def classify_bc_evidence_file(doc: Document, achievements: list[dict]) -> str:
    """
    uploaded | draft_linked | submitted_for_review | reviewed
    """
    if not is_kra_i_achievement_indicator(doc.indicator_id):
        return "not_bc"
    linked = _link_for_document(doc.public_id, achievements)
    if not linked:
        return "uploaded_unlinked"
    sub = linked.get("submissionStatus") or "draft"
    rev = linked.get("reviewStatus") or "pending"
    if sub != "submitted":
        return "draft_linked"
    if rev in _ACHIEVEMENT_REVIEW_OPEN:
        return "submitted_for_review"
    return "reviewed"


def compute_review_queue(*, reviewer_user_id: int | None = None, admin: bool = False) -> dict:
    if admin:
        owner_ids = [u.id for u in User.query.filter_by(role=UserRole.faculty).all()]
    elif reviewer_user_id is not None:
        owner_ids = [
            a.faculty_user_id
            for a in ReviewerAssignment.query.filter_by(reviewer_user_id=reviewer_user_id).all()
        ]
    else:
        owner_ids = []

    ach_by_owner = _achievement_index_by_owner()
    documents_pending = 0
    achievements_pending = 0
    bc_evidence_unlinked = 0
    bc_evidence_draft_only = 0
    by_faculty: dict[str, dict] = {}

    owners = {u.id: u for u in User.query.filter(User.id.in_(owner_ids)).all()} if owner_ids else {}

    doc_query = Document.query.filter(
        Document.owner_user_id.in_(owner_ids),
        Document.upload_status == "stored",
    )
    for doc in doc_query:
        portal_id = owners[doc.owner_user_id].portal_id() if doc.owner_user_id in owners else None
        if not portal_id:
            continue
        slot = by_faculty.setdefault(
            portal_id,
            {
                "documentsPending": 0,
                "achievementsPending": 0,
                "awaitingReview": 0,
                "bcEvidenceUnlinked": 0,
            },
        )
        achievements = ach_by_owner.get(doc.owner_user_id, [])
        if document_counts_toward_legacy_pending(doc, achievements):
            documents_pending += 1
            slot["documentsPending"] += 1
        bc_class = classify_bc_evidence_file(doc, achievements)
        if bc_class == "uploaded_unlinked":
            bc_evidence_unlinked += 1
            slot["bcEvidenceUnlinked"] += 1
        elif bc_class == "draft_linked":
            bc_evidence_draft_only += 1

    counted_ach: set[tuple[int, str]] = set()
    for uid in owner_ids:
        portal_id = owners[uid].portal_id() if uid in owners else None
        if not portal_id:
            continue
        slot = by_faculty.setdefault(
            portal_id,
            {
                "documentsPending": 0,
                "achievementsPending": 0,
                "awaitingReview": 0,
                "bcEvidenceUnlinked": 0,
            },
        )
        for ach in ach_by_owner.get(uid, []):
            if ach.get("submissionStatus") != "submitted":
                continue
            if (ach.get("reviewStatus") or "pending") not in _ACHIEVEMENT_REVIEW_OPEN:
                continue
            key = (uid, ach.get("id") or "")
            if not key[1] or key in counted_ach:
                continue
            counted_ach.add(key)
            achievements_pending += 1
            slot["achievementsPending"] += 1

    for slot in by_faculty.values():
        slot["awaitingReview"] = slot["documentsPending"] + slot["achievementsPending"]

    return {
        "documentsPending": documents_pending,
        "achievementsPending": achievements_pending,
        "awaitingReview": documents_pending + achievements_pending,
        "bcEvidenceUnlinked": bc_evidence_unlinked,
        "bcEvidenceDraftOnly": bc_evidence_draft_only,
        "byFaculty": by_faculty,
    }


def reconcile_bc_evidence_review_status() -> int:
    """Stored KRA I B/C files are reviewed via achievements, not the legacy document queue."""
    changed = 0
    rows = Document.query.filter_by(upload_status="stored", review_status="pending").all()
    for doc in rows:
        if is_kra_i_achievement_indicator(doc.indicator_id):
            doc.review_status = "evidence"
            changed += 1
    return changed
