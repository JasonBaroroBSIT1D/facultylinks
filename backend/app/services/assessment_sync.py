from __future__ import annotations

import uuid
from decimal import Decimal

from app.extensions import db
from app.models import Document, FacultyAssessment


def _assessment_row(user_id: int) -> FacultyAssessment:
    row = FacultyAssessment.query.get(user_id)
    if not row:
        row = FacultyAssessment(user_id=user_id, data={"setSef": {"SET": [], "SEF": []}, "entries": {}})
        db.session.add(row)
        db.session.flush()
    return row


def supersede_prior_documents(owner_user_id: int, indicator_id: str, new_public_id: str) -> None:
    prior = (
        Document.query.filter_by(owner_user_id=owner_user_id, indicator_id=indicator_id)
        .filter(Document.public_id != new_public_id)
        .filter(Document.superseded_by_public_id.is_(None))
        .filter(Document.review_status != "replaced")
        .all()
    )
    for old in prior:
        old.review_status = "replaced"
        old.superseded_by_public_id = new_public_id


def attach_upload_to_assessment(
    doc: Document,
    *,
    title: str | None = None,
    estimated_points: float | None = None,
) -> None:
    row = _assessment_row(doc.owner_user_id)
    data = row.data or {"setSef": {"SET": [], "SEF": []}, "entries": {}}
    entries = data.setdefault("entries", {})
    indicator_entries = entries.setdefault(doc.indicator_id or "", [])

    entry_id = doc.entry_id or f"ent-{doc.public_id.replace('-', '')[:12]}"
    doc.entry_id = entry_id

    payload = {
        "id": entry_id,
        "indicatorId": doc.indicator_id,
        "title": title or doc.original_filename,
        "estimatedPoints": float(estimated_points or 0),
        "verifiedPoints": None,
        "reviewerVerifiedPoints": None,
        "reviewStatus": "pending",
        "linkedDocumentId": doc.public_id,
    }

    idx = next((i for i, e in enumerate(indicator_entries) if e.get("linkedDocumentId") == doc.public_id), None)
    if idx is None:
        idx = next((i for i, e in enumerate(indicator_entries) if e.get("id") == entry_id), None)
    if idx is not None:
        prev = indicator_entries[idx]
        payload["estimatedPoints"] = prev.get("estimatedPoints", payload["estimatedPoints"])
        indicator_entries[idx] = {**prev, **payload}
    else:
        indicator_entries.append(payload)

    row.data = data


def sync_review_to_assessment(doc: Document) -> None:
    if not doc.indicator_id or not doc.entry_id:
        return
    row = _assessment_row(doc.owner_user_id)
    data = row.data or {"setSef": {"SET": [], "SEF": []}, "entries": {}}
    entries = data.setdefault("entries", {})
    indicator_entries = entries.get(doc.indicator_id) or []
    target = None
    for e in indicator_entries:
        if e.get("id") == doc.entry_id or e.get("linkedDocumentId") == doc.public_id:
            target = e
            break
    if not target:
        attach_upload_to_assessment(doc)
        row = _assessment_row(doc.owner_user_id)
        data = row.data
        indicator_entries = data["entries"].get(doc.indicator_id) or []
        target = next((e for e in indicator_entries if e.get("linkedDocumentId") == doc.public_id), None)
        if not target:
            return

    status = doc.review_status
    target["reviewStatus"] = status
    if doc.verified_points is not None and status == "approved":
        vp = float(doc.verified_points)
        target["verifiedPoints"] = vp
        target["reviewerVerifiedPoints"] = vp
    elif status in ("rejected", "replaced"):
        target["verifiedPoints"] = 0
        target["reviewerVerifiedPoints"] = 0
    elif status == "correction_requested":
        target["verifiedPoints"] = None
        target["reviewerVerifiedPoints"] = None

    target["linkedDocumentId"] = doc.public_id
    row.data = data
