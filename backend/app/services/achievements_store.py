"""Achievement CRUD stored in faculty_assessments.data['achievements']."""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm.attributes import flag_modified

from app.extensions import db
from app.models import Document, FacultyAssessment, User
from app.services.achievement_rules import (
    achievement_dedupe_key,
    expected_points_for_achievement,
    is_active_achievement,
    validate_claimed_points,
)
from app.services.catalog import (
    CatalogValidationError,
    find_indicator,
    get_catalog_for_assessment,
    pin_assessment_config_version_if_needed,
)

# KRA IV and other indicator-specific payload fields (not review metadata).
_ACHIEVEMENT_INDICATOR_FIELDS = (
    "qualificationType",
    "attendanceScope",
    "awardLevel",
    "academicServiceRole",
    "industryCategory",
    "serviceYears",
    "newlyAppointedEligible",
)


def _indicator_fields_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in _ACHIEVEMENT_INDICATOR_FIELDS:
        if key in payload:
            out[key] = payload[key]
    return out


def _row(user_id: int) -> FacultyAssessment:
    row = FacultyAssessment.query.get(user_id)
    if not row:
        row = FacultyAssessment(user_id=user_id, data=_empty_assessment())
        db.session.add(row)
        db.session.flush()
    return row


def _persist_assessment_row(row: FacultyAssessment, data: dict) -> None:
    """JSON columns do not detect in-place dict mutation; always replace and flag."""
    row.data = copy.deepcopy(data)
    flag_modified(row, "data")


def _empty_assessment() -> dict:
    return {"setSef": {"SET": [], "SEF": []}, "entries": {}, "achievements": []}


def _achievements(data: dict) -> list[dict]:
    raw = data.get("achievements")
    if not isinstance(raw, list):
        return []
    return raw


def merge_achievements_preserve_submitted(prev_data: dict, incoming: list | None) -> list:
    """Legacy assessment PUT must not downgrade submitted achievements to draft."""
    prev_list = prev_data.get("achievements") or []
    if not isinstance(incoming, list):
        return prev_list
    prev_by_id = {a.get("id"): a for a in prev_list if a.get("id")}
    merged: list[dict] = []
    seen: set[str] = set()
    for a in incoming:
        if not isinstance(a, dict):
            continue
        aid = a.get("id")
        if not aid:
            merged.append(a)
            continue
        seen.add(aid)
        prev = prev_by_id.get(aid)
        if (
            prev
            and prev.get("submissionStatus") == "submitted"
            and a.get("submissionStatus") != "submitted"
        ):
            merged.append(prev)
        else:
            merged.append(a)
    for a in prev_list:
        aid = a.get("id")
        if aid and aid not in seen:
            merged.append(a)
    return merged


def list_achievements(
    user_id: int,
    *,
    criterion_id: str | None = None,
    indicator_id: str | None = None,
) -> list[dict]:
    data = _row(user_id).data or _empty_assessment()
    out = [a for a in _achievements(data) if is_active_achievement(a)]
    if criterion_id:
        from app.services.achievement_rules import resolve_achievement_criterion_id

        out = [a for a in out if resolve_achievement_criterion_id(a) == criterion_id]
    if indicator_id:
        out = [a for a in out if a.get("indicatorId") == indicator_id]
    return out


def get_achievement(user_id: int, achievement_id: str) -> dict | None:
    for a in _achievements((_row(user_id).data or {})):
        if a.get("id") == achievement_id and is_active_achievement(a):
            return a
    return None


def _ensure_owned_documents(user_id: int, document_ids: list[str]) -> None:
    for did in document_ids:
        doc = Document.query.filter_by(public_id=did, owner_user_id=user_id, upload_status="stored").first()
        if not doc:
            raise CatalogValidationError(f"Document {did} not found or not owned by faculty.")


def _ensure_documents_not_linked_elsewhere(
    data: dict, document_ids: list[str], *, exclude_achievement_id: str | None
) -> None:
    for ach in _achievements(data):
        if not is_active_achievement(ach):
            continue
        if exclude_achievement_id and ach.get("id") == exclude_achievement_id:
            continue
        other_ids = set(ach.get("documentIds") or [])
        overlap = other_ids.intersection(document_ids)
        if overlap:
            raise CatalogValidationError(
                f"Document(s) already linked to another achievement: {', '.join(sorted(overlap))}"
            )


def _duplicate_exists(data: dict, key: str, exclude_id: str | None) -> bool:
    for a in _achievements(data):
        if not is_active_achievement(a):
            continue
        if exclude_id and a.get("id") == exclude_id:
            continue
        if achievement_dedupe_key(a) == key:
            return True
    return False


def create_achievement(user_id: int, payload: dict[str, Any], *, catalog: dict) -> dict:
    indicator_id = (payload.get("indicatorId") or "").strip()
    if not indicator_id:
        raise CatalogValidationError("indicatorId is required.")
    found = find_indicator(catalog, indicator_id)
    if not found:
        raise CatalogValidationError("Indicator is not in the published configuration.")
    kra_id = payload.get("kraId") or found["kra"].get("id") or "kra-I"
    criterion_id = payload.get("criterionId") or found["criterion"].get("id") or ""

    row = _row(user_id)
    data_pre = row.data or _empty_assessment()
    rule = expected_points_for_achievement(
        catalog,
        indicator_id,
        payload,
        context={"achievements": _achievements(data_pre)},
    )
    claimed = payload.get("claimedPoints")
    if claimed is not None:
        claimed = float(claimed)
    err = validate_claimed_points(claimed=claimed, rule=rule) if claimed is not None else None
    if err:
        raise CatalogValidationError(err)

    data = pin_assessment_config_version_if_needed(user_id, data_pre)
    ach_id = payload.get("id") or f"ach-{uuid.uuid4().hex[:12]}"
    doc_ids = list(dict.fromkeys(str(d) for d in (payload.get("documentIds") or []) if d))
    if doc_ids:
        _ensure_owned_documents(user_id, doc_ids)
        _ensure_documents_not_linked_elsewhere(data, doc_ids, exclude_achievement_id=None)

    body = {
        "id": ach_id,
        "kraId": kra_id,
        "criterionId": criterion_id,
        "indicatorId": indicator_id,
        "title": (payload.get("title") or "").strip(),
        "description": (payload.get("description") or "").strip(),
        "achievementDate": payload.get("achievementDate") or payload.get("date"),
        "academicPeriod": payload.get("academicPeriod"),
        "achievementType": payload.get("achievementType"),
        "role": payload.get("role"),
        "thesisType": payload.get("thesisType"),
        "quantity": int(payload.get("quantity") or 1),
        "patentStage": payload.get("patentStage") or payload.get("patent_stage"),
        "commercializationScope": payload.get("commercializationScope"),
        "softwareVersionType": payload.get("softwareVersionType"),
        "incomeRole": payload.get("incomeRole"),
        "incomeAmount": payload.get("incomeAmount"),
        "incomeTier": payload.get("incomeTier"),
        "serviceScope": payload.get("serviceScope"),
        "judgeServiceType": payload.get("judgeServiceType"),
        "hours": payload.get("hours"),
        "extensionRole": payload.get("extensionRole"),
        "projectPeriod": payload.get("projectPeriod"),
        "linkedIsrProjectId": payload.get("linkedIsrProjectId"),
        "clientSatisfactionRating": payload.get("clientSatisfactionRating"),
        "designationLevel": payload.get("designationLevel"),
        "designationRole": payload.get("designationRole"),
        "claimedPoints": claimed,
        "claimExplanation": payload.get("claimExplanation"),
        "ruleExpectedPoints": rule.get("ruleExpectedPoints"),
        "rulePermittedMax": rule.get("permittedMax"),
        "ruleUnresolved": rule.get("unresolved"),
        "ruleSummary": rule.get("ruleSummary"),
        "documentIds": doc_ids,
        "submissionStatus": "draft",
        "submittedAt": None,
        "submittedSnapshot": None,
        "reviewStatus": None,
        "reviewerVerifiedPoints": None,
        "originalClaimedPoints": claimed,
        "reviewRemarks": None,
        "reviewedByUserId": None,
        "reviewedAt": None,
        "reviewHistory": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "dedupeKey": achievement_dedupe_key(payload),
        **_indicator_fields_from_payload(payload),
    }
    dkey = achievement_dedupe_key(body)
    if _duplicate_exists(data, dkey, None):
        raise CatalogValidationError("A duplicate achievement with the same details already exists.")

    data.setdefault("achievements", []).append(body)
    _persist_assessment_row(row, data)
    return body


def update_achievement_draft(user_id: int, achievement_id: str, patch: dict[str, Any], *, catalog: dict) -> dict:
    row = _row(user_id)
    data = row.data or _empty_assessment()
    target = get_achievement(user_id, achievement_id)
    if not target:
        raise CatalogValidationError("Achievement not found.")
    if target.get("submissionStatus") == "submitted" and target.get("reviewStatus") != "correction_requested":
        raise CatalogValidationError("Submitted achievements cannot be edited; wait for reviewer action or withdraw.")

    merged = {**target, **{k: v for k, v in patch.items() if k not in ("id", "reviewHistory", "submittedSnapshot")}}
    rule = expected_points_for_achievement(
        catalog,
        merged["indicatorId"],
        merged,
        context={"achievements": _achievements(data)},
    )
    claimed = patch.get("claimedPoints", merged.get("claimedPoints"))
    if claimed is not None:
        claimed = float(claimed)
        err = validate_claimed_points(claimed=claimed, rule=rule)
        if err:
            raise CatalogValidationError(err)
        merged["claimedPoints"] = claimed
        if merged.get("submissionStatus") == "draft":
            merged["originalClaimedPoints"] = claimed

    merged["ruleExpectedPoints"] = rule.get("ruleExpectedPoints")
    merged["rulePermittedMax"] = rule.get("permittedMax")
    merged["ruleUnresolved"] = rule.get("unresolved")
    merged["ruleSummary"] = rule.get("ruleSummary")
    merged["updatedAt"] = datetime.now(timezone.utc).isoformat()
    merged["dedupeKey"] = achievement_dedupe_key(merged)

    doc_ids = patch.get("documentIds")
    if doc_ids is not None:
        doc_ids = list(dict.fromkeys(str(d) for d in doc_ids if d))
        _ensure_owned_documents(user_id, doc_ids)
        _ensure_documents_not_linked_elsewhere(data, doc_ids, exclude_achievement_id=achievement_id)
        merged["documentIds"] = doc_ids

    if _duplicate_exists(data, merged["dedupeKey"], achievement_id):
        raise CatalogValidationError("A duplicate achievement with the same details already exists.")

    achievements = _achievements(data)
    for i, a in enumerate(achievements):
        if a.get("id") == achievement_id:
            achievements[i] = merged
            break
    data["achievements"] = achievements
    _persist_assessment_row(row, data)
    return merged


def submit_achievement(
    user_id: int,
    achievement_id: str,
    *,
    catalog: dict,
    patch: dict[str, Any] | None = None,
) -> dict:
    ach = update_achievement_draft(user_id, achievement_id, patch or {}, catalog=catalog)
    if not (ach.get("title") or "").strip():
        raise CatalogValidationError("Title is required before submission.")
    if ach.get("claimedPoints") is None:
        raise CatalogValidationError("Claimed points are required before submission.")
    if ach.get("ruleUnresolved"):
        raise CatalogValidationError(ach["ruleUnresolved"])
    if not ach.get("documentIds"):
        raise CatalogValidationError("At least one supporting document is required.")

    snapshot = copy.deepcopy(ach)
    ach["submissionStatus"] = "submitted"
    ach["submittedAt"] = datetime.now(timezone.utc).isoformat()
    ach["submittedSnapshot"] = snapshot
    ach["reviewStatus"] = "pending"
    ach["originalClaimedPoints"] = ach.get("claimedPoints")
    ach["reviewerVerifiedPoints"] = None

    row = _row(user_id)
    data = copy.deepcopy(row.data or _empty_assessment())
    stored = copy.deepcopy(ach)
    for i, a in enumerate(_achievements(data)):
        if a.get("id") == achievement_id:
            data["achievements"][i] = stored
            break
    _persist_assessment_row(row, data)
    return stored


def review_achievement(
    owner_user_id: int,
    achievement_id: str,
    *,
    actor: User,
    review_status: str,
    reviewer_verified_points: float | None,
    remarks: str | None,
    score_change_reason: str | None,
) -> dict:
    if review_status not in ("approved", "rejected", "correction_requested"):
        raise CatalogValidationError("Invalid review status.")

    row = _row(owner_user_id)
    data = row.data or _empty_assessment()
    ach = get_achievement(owner_user_id, achievement_id)
    if not ach:
        raise CatalogValidationError("Achievement not found.")
    if ach.get("submissionStatus") != "submitted":
        raise CatalogValidationError("Only submitted achievements can be reviewed.")

    catalog, _ = get_catalog_for_assessment(data)
    if not catalog:
        raise CatalogValidationError("No published configuration.")

    claimed = float(ach.get("originalClaimedPoints") or ach.get("claimedPoints") or 0)
    rule = expected_points_for_achievement(
        catalog,
        ach["indicatorId"],
        ach,
        context={"achievements": _achievements(data)},
    )

    if review_status == "approved":
        doc_ids = [str(d) for d in (ach.get("documentIds") or []) if d]
        if not doc_ids:
            raise CatalogValidationError("Cannot approve: at least one supporting document must be linked to this achievement.")
        _ensure_owned_documents(owner_user_id, doc_ids)
        if reviewer_verified_points is None:
            raise CatalogValidationError("Reviewer-verified points are required for approval.")
        vp = float(reviewer_verified_points)
        err = validate_claimed_points(claimed=vp, rule=rule)
        if err:
            raise CatalogValidationError(err)
        if abs(vp - claimed) > 1e-6 and not (score_change_reason or "").strip():
            raise CatalogValidationError("Explain why the verified score differs from the faculty claim.")
    else:
        vp = None

    hist = list(ach.get("reviewHistory") or [])
    hist.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "byUserId": actor.id,
            "byEmail": actor.email,
            "status": review_status,
            "reviewerVerifiedPoints": vp,
            "claimedPoints": claimed,
            "remarks": remarks,
            "scoreChangeReason": score_change_reason,
        }
    )

    ach["reviewStatus"] = review_status
    ach["reviewerVerifiedPoints"] = vp if review_status == "approved" else None
    ach["reviewRemarks"] = remarks
    ach["reviewedByUserId"] = actor.id
    ach["reviewedAt"] = datetime.now(timezone.utc).isoformat()
    ach["reviewHistory"] = hist[-30:]
    ach["claimedPoints"] = ach.get("originalClaimedPoints") or ach.get("claimedPoints")

    for i, a in enumerate(_achievements(data)):
        if a.get("id") == achievement_id:
            data["achievements"][i] = ach
            break
    _persist_assessment_row(row, data)
    return ach
