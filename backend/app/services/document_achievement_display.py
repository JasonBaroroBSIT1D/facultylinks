"""Derived display status for B/C achievement evidence (faculty + shared API shape)."""

from __future__ import annotations

from app.models import FacultyAssessment
from app.services.achievement_rules import is_active_achievement
from app.services.catalog import is_kra_i_achievement_indicator


def criterion_id_from_indicator(indicator_id: str | None) -> str | None:
    if not indicator_id:
        return None
    if indicator_id.startswith("kra-I-B"):
        return "kra-I-B"
    if indicator_id.startswith("kra-I-C"):
        return "kra-I-C"
    if indicator_id.startswith("kra-II-A"):
        return "kra-II-A"
    if indicator_id.startswith("kra-II-B"):
        return "kra-II-B"
    if indicator_id.startswith("kra-II-C"):
        return "kra-II-C"
    if indicator_id.startswith("kra-III-A"):
        return "kra-III-A"
    if indicator_id.startswith("kra-III-B"):
        return "kra-III-B"
    if indicator_id.startswith("kra-III-C"):
        return "kra-III-C"
    if indicator_id.startswith("kra-III-D"):
        return "kra-III-D"
    return None


def achievement_links_for_user(user_id: int) -> dict[str, list[dict]]:
    """Map document public_id -> all achievements that reference it (active only)."""
    row = FacultyAssessment.query.filter_by(user_id=user_id).first()
    if not row or not row.data:
        return {}
    out: dict[str, list[dict]] = {}
    for ach in row.data.get("achievements") or []:
        if not is_active_achievement(ach):
            continue
        ach_id = ach.get("id")
        if not ach_id:
            continue
        ind = ach.get("indicatorId") or ""
        link = {
            "linkedAchievementId": ach_id,
            "criterionId": criterion_id_from_indicator(ind),
            "parentSubmissionStatus": ach.get("submissionStatus") or "draft",
            "parentReviewStatus": ach.get("reviewStatus") or "pending",
            "parentAchievementTitle": ach.get("title"),
            "achievementRemarks": ach.get("reviewRemarks") or ach.get("remarks"),
        }
        for doc_id in ach.get("documentIds") or []:
            if not doc_id:
                continue
            out.setdefault(str(doc_id), []).append(link)
    return out


def derive_achievement_display_status(links: list[dict], *, indicator_id: str | None) -> dict | None:
    """
    Effective badge for achievement evidence. Raw document reviewStatus is unchanged.
    Returns displayStatus + displayStatusLabel or None (use legacy document status).
    """
    if not is_kra_i_achievement_indicator(indicator_id):
        return None
    if not links:
        return None

    pairs = {
        (
            (link.get("parentSubmissionStatus") or "draft"),
            (link.get("parentReviewStatus") or "pending"),
        )
        for link in links
    }
    if len(pairs) > 1:
        return {
            "displayStatus": "achievement_multiple_parents",
            "displayStatusLabel": "Multiple achievement links",
        }

    sub, rev = next(iter(pairs))
    if sub != "submitted":
        return {"displayStatus": "draft_evidence", "displayStatusLabel": "Draft evidence"}

    if rev == "approved":
        return {
            "displayStatus": "part_of_approved_achievement",
            "displayStatusLabel": "Part of approved achievement",
        }
    if rev == "correction_requested":
        return {
            "displayStatus": "achievement_needs_changes",
            "displayStatusLabel": "Achievement needs changes",
        }
    if rev == "rejected":
        return {
            "displayStatus": "part_of_rejected_achievement",
            "displayStatusLabel": "Part of rejected achievement",
        }
    return {
        "displayStatus": "pending_achievement_review",
        "displayStatusLabel": "Pending achievement review",
    }


def enrich_document_dict_for_achievements(base: dict, links: list[dict]) -> dict:
    """Attach achievementLinks and derived display fields; preserve raw reviewStatus."""
    out = {**base, "achievementLinks": links}
    if links:
        primary = links[0]
        out["linkedAchievementId"] = primary.get("linkedAchievementId")
        out["criterionId"] = primary.get("criterionId")
        out["parentReviewStatus"] = primary.get("parentReviewStatus")
        out["parentSubmissionStatus"] = primary.get("parentSubmissionStatus")
        out["parentAchievementTitle"] = primary.get("parentAchievementTitle")
    display = derive_achievement_display_status(links, indicator_id=base.get("indicatorId"))
    if display:
        out.update(display)
    return out
