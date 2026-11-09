"""Portal document list: dedupe by public id and attach parent achievement metadata."""

from __future__ import annotations


def _achievement_index(assessments: dict | None) -> dict[str, dict]:
    index: dict[str, dict] = {}
    if not assessments:
        return index
    for _fac_portal_id, ass in assessments.items():
        if not isinstance(ass, dict):
            continue
        for ach in ass.get("achievements") or []:
            if not isinstance(ach, dict):
                continue
            ach_id = ach.get("id")
            if not ach_id:
                continue
            for doc_id in ach.get("documentIds") or []:
                if not doc_id:
                    continue
                index[str(doc_id)] = {
                    "linkedAchievementId": ach_id,
                    "parentSubmissionStatus": ach.get("submissionStatus"),
                    "parentReviewStatus": ach.get("reviewStatus"),
                    "parentAchievementTitle": ach.get("title"),
                }
    return index


def enrich_portal_documents(documents: list[dict], assessments: dict | None) -> list[dict]:
    """Drop duplicate public ids; attach linked achievement review context."""
    index = _achievement_index(assessments)
    seen: set[str] = set()
    out: list[dict] = []
    for row in documents:
        doc_id = row.get("id")
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        extra = index.get(doc_id)
        if extra:
            row = {**row, **extra}
        out.append(row)
    return out
