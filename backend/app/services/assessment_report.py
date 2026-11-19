"""Authoritative Faculty Assessment and Evidence Report snapshot (read-only)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.extensions import db
from app.models import Document, FacultyAssessment, ReviewerAssignment, User
from app.services.achievements_store import list_achievements
from app.services.catalog import (
    criterion_a_calculation_params,
    find_indicator,
    get_assessment_config,
    get_catalog_for_assessment,
    get_version_record,
)
from app.services.rank_simulation import compute_faculty_rank_simulation
from app.services.scoring_engine import compute_faculty_scores
from app.services.set_sef_aggregation import SET_SEF_DOCUMENT_KINDS, aggregate_set_sef_for_faculty
from app.services.settings_store import INSTITUTION_KEY, get_json
from app.services.teaching_effectiveness import compute_criterion_a_from_records
from app.services.set_sef_aggregation import (
    apply_semester_slot_window,
    merged_slots_to_scoring_records,
)
from app.services.catalog import scoring_window_semester_keys


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_value(val: Any, *, unavailable: bool = False) -> dict[str, Any]:
    """Never present failed/missing calculation as a genuine 0.00."""
    if unavailable or val is None:
        return {"available": False, "value": None, "display": "Unavailable"}
    try:
        num = float(val)
    except (TypeError, ValueError):
        return {"available": False, "value": None, "display": "Unavailable"}
    return {"available": True, "value": round(num, 4), "display": f"{num:.2f}"}


def _user_name(user: User | None) -> str | None:
    if not user:
        return None
    return user.full_name or user.email


def _indicator_label(catalog: dict | None, indicator_id: str | None) -> str:
    if not catalog or not indicator_id:
        return indicator_id or "—"
    found = find_indicator(catalog, indicator_id)
    if not found:
        return indicator_id
    ind = found.get("indicator") or {}
    return ind.get("name") or indicator_id


def _criterion_label(catalog: dict | None, criterion_id: str | None) -> str:
    if not catalog or not criterion_id:
        return criterion_id or "—"
    for kra in catalog.get("kras") or []:
        for crit in kra.get("criteria") or []:
            if crit.get("id") == criterion_id:
                return crit.get("name") or criterion_id
    return criterion_id


def _kra_label(catalog: dict | None, kra_id: str | None) -> str:
    if not catalog or not kra_id:
        return kra_id or "—"
    for kra in catalog.get("kras") or []:
        if kra.get("id") == kra_id:
            return kra.get("name") or kra_id
    return kra_id


def _presentation_scores(summary: dict | None, *, criterion_a: dict | None) -> dict[str, Any]:
    """Annotate engine summary so unavailable Criterion A is not shown as 0.00."""
    if not summary:
        return {
            "available": False,
            "overallWeighted": _score_value(None, unavailable=True),
            "byKra": {},
            "notes": ["Scoring configuration is not available for this assessment."],
        }
    ca_unavail = bool(
        criterion_a
        and (
            criterion_a.get("calculationUnavailable")
            or criterion_a.get("configurationError")
            or criterion_a.get("calculationPolicyError")
        )
    )
    by_kra_out: dict[str, Any] = {}
    for kra_id, kra in (summary.get("byKra") or {}).items():
        ca_meta = kra.get("criterionA") or (criterion_a if kra_id == "kra-I" else None)
        kra_ca_unavail = bool(
            ca_meta
            and (
                ca_meta.get("calculationUnavailable")
                or ca_meta.get("configurationError")
            )
        )
        raw = kra.get("rawTotal")
        weighted = kra.get("weightedContribution")
        # If Criterion A is unavailable and dominates an all-zero KRA I, mark unavailable.
        if kra_id == "kra-I" and kra_ca_unavail and (raw is None or float(raw) == 0.0):
            raw_score = _score_value(None, unavailable=True)
            weighted_score = _score_value(None, unavailable=True)
        else:
            raw_score = _score_value(raw)
            weighted_score = _score_value(weighted)
        by_kra_out[kra_id] = {
            **kra,
            "rawScore": raw_score,
            "weightedScore": weighted_score,
            "weight": kra.get("weight"),
            "criterionAUnavailable": kra_ca_unavail,
            "availabilityNote": (
                (ca_meta or {}).get("incompleteReason")
                or (ca_meta or {}).get("configurationError")
                or ("Criterion A calculation unavailable" if kra_ca_unavail else None)
            ),
        }
    overall = summary.get("overallWeighted")
    overall_score = _score_value(None, unavailable=True) if (ca_unavail and (overall is None or float(overall) == 0.0) and not any(
        (by_kra_out.get(k) or {}).get("rawScore", {}).get("available") for k in ("kra-II", "kra-III", "kra-IV")
    )) else _score_value(overall)
    return {
        "available": overall_score["available"] or any(
            (v.get("rawScore") or {}).get("available") for v in by_kra_out.values()
        ),
        "overallWeighted": overall_score,
        "byKra": by_kra_out,
        "notes": list(summary.get("notes") or []),
    }


def _achievement_counts(achievements: list[dict]) -> dict[str, int]:
    submitted = [a for a in achievements if a.get("submissionStatus") == "submitted"]
    drafts = [a for a in achievements if a.get("submissionStatus") == "draft"]
    by_status = defaultdict(int)
    for a in submitted:
        st = a.get("reviewStatus") or "pending"
        by_status[st] += 1
    return {
        "submitted": len(submitted),
        "drafts": len(drafts),
        "approved": by_status.get("approved", 0),
        "pending": by_status.get("pending", 0) + by_status.get(None, 0),
        "needsChanges": by_status.get("correction_requested", 0),
        "rejected": by_status.get("rejected", 0),
        "unit": "achievements",
    }


def _doc_parent_links(achievements: list[dict], docs_by_id: dict[str, Document]) -> dict[str, list[dict]]:
    links: dict[str, list[dict]] = defaultdict(list)
    for ach in achievements:
        for did in ach.get("documentIds") or []:
            did = str(did)
            links[did].append(
                {
                    "achievementId": ach.get("id"),
                    "title": ach.get("title") or "Untitled achievement",
                    "reviewStatus": ach.get("reviewStatus"),
                    "submissionStatus": ach.get("submissionStatus"),
                }
            )
    return links


def _evidence_display_status(doc: Document, parents: list[dict]) -> str:
    if parents:
        if any(p.get("reviewStatus") == "approved" for p in parents):
            return "Part of approved achievement"
        if any(p.get("submissionStatus") == "submitted" for p in parents):
            return "Linked to submitted achievement"
        return "Linked to draft achievement"
    return doc.review_status or "pending"


def _outstanding_actions(
    achievements: list[dict],
    documents: list[Document],
    criterion_a: dict | None,
    score_notes: list[str],
) -> list[dict]:
    items: list[dict] = []
    for ach in achievements:
        if ach.get("submissionStatus") != "submitted":
            continue
        st = ach.get("reviewStatus")
        if st == "correction_requested":
            items.append(
                {
                    "kind": "needs_changes",
                    "targetType": "achievement",
                    "targetId": ach.get("id"),
                    "title": ach.get("title") or "Achievement",
                    "detail": ach.get("reviewRemarks") or "Reviewer requested changes.",
                }
            )
        elif st == "rejected":
            items.append(
                {
                    "kind": "rejected",
                    "targetType": "achievement",
                    "targetId": ach.get("id"),
                    "title": ach.get("title") or "Achievement",
                    "detail": ach.get("reviewRemarks") or "Achievement was rejected.",
                }
            )
        elif st in (None, "pending"):
            items.append(
                {
                    "kind": "pending_review",
                    "targetType": "achievement",
                    "targetId": ach.get("id"),
                    "title": ach.get("title") or "Achievement",
                    "detail": "Awaiting reviewer decision.",
                }
            )
        if ach.get("ruleUnresolved"):
            items.append(
                {
                    "kind": "unresolved_policy",
                    "targetType": "achievement",
                    "targetId": ach.get("id"),
                    "title": ach.get("title") or "Achievement",
                    "detail": ach.get("ruleSummary") or "Scoring rule is unresolved for this indicator.",
                }
            )
    for doc in documents:
        if doc.review_status == "correction_requested":
            items.append(
                {
                    "kind": "needs_changes",
                    "targetType": "document",
                    "targetId": doc.public_id,
                    "title": doc.original_filename,
                    "detail": doc.review_remarks or "Document needs changes.",
                }
            )
        if (doc.document_kind or "") in SET_SEF_DOCUMENT_KINDS and doc.ocr_status in (
            "pending",
            "processing",
            "failed",
            "review_required",
        ):
            items.append(
                {
                    "kind": "pending_verification",
                    "targetType": "document",
                    "targetId": doc.public_id,
                    "title": doc.original_filename,
                    "detail": f"SET/SEF processing status: {doc.ocr_status}.",
                }
            )
    if criterion_a and criterion_a.get("calculationUnavailable"):
        items.append(
            {
                "kind": "pending_verification",
                "targetType": "criterion-a",
                "targetId": "kra-I-A",
                "title": "Criterion A (Teaching Effectiveness)",
                "detail": criterion_a.get("incompleteReason") or "No eligible ratings for calculation.",
            }
        )
    for note in score_notes or []:
        if "unresolved" in note.lower() or "provisional" in note.lower():
            items.append(
                {
                    "kind": "unresolved_policy",
                    "targetType": "scoring",
                    "targetId": None,
                    "title": "Scoring policy",
                    "detail": note,
                }
            )
    return items


def _group_achievements(catalog: dict | None, achievements: list[dict]) -> list[dict]:
    by_kra: dict[str, dict] = {}
    kra_order = [k.get("id") for k in (catalog or {}).get("kras") or []] or ["kra-I", "kra-II", "kra-III", "kra-IV"]
    for kra_id in kra_order:
        by_kra[kra_id] = {
            "kraId": kra_id,
            "kraName": _kra_label(catalog, kra_id),
            "criteria": {},
        }
    for ach in achievements:
        kra_id = ach.get("kraId") or "unknown"
        crit_id = ach.get("criterionId") or "unknown"
        ind_id = ach.get("indicatorId") or "unknown"
        if kra_id not in by_kra:
            by_kra[kra_id] = {"kraId": kra_id, "kraName": _kra_label(catalog, kra_id), "criteria": {}}
        crits = by_kra[kra_id]["criteria"]
        if crit_id not in crits:
            crits[crit_id] = {
                "criterionId": crit_id,
                "criterionName": _criterion_label(catalog, crit_id),
                "indicators": {},
            }
        inds = crits[crit_id]["indicators"]
        if ind_id not in inds:
            inds[ind_id] = {
                "indicatorId": ind_id,
                "indicatorName": _indicator_label(catalog, ind_id),
                "achievements": [],
            }
        inds[ind_id]["achievements"].append(ach)
    # stabilize list shape
    out = []
    for kra_id in kra_order:
        kra = by_kra.get(kra_id)
        if not kra:
            continue
        criteria_list = []
        for crit in kra["criteria"].values():
            criteria_list.append(
                {
                    **crit,
                    "indicators": list(crit["indicators"].values()),
                }
            )
        out.append({**kra, "criteria": criteria_list})
    for kra_id, kra in by_kra.items():
        if kra_id in kra_order:
            continue
        criteria_list = [{**c, "indicators": list(c["indicators"].values())} for c in kra["criteria"].values()]
        out.append({**kra, "criteria": criteria_list})
    return out


def build_assessment_report(
    *,
    faculty: User,
    actor: User,
    period_label: str | None = None,
) -> dict[str, Any]:
    """Build a read-only report snapshot. Does not mutate assessment, scores, or pins."""
    assess_row = db.session.get(FacultyAssessment, faculty.id)
    assessment_data = dict(assess_row.data or {}) if assess_row else {}
    catalog, kra_weights = get_catalog_for_assessment(assessment_data)
    configured = bool(catalog and kra_weights)
    pinned_id = assessment_data.get("configVersionId")
    version_rec = get_version_record(pinned_id) if pinned_id else None
    if not version_rec:
        cfg = get_assessment_config()
        active = cfg.get("activePublishedId")
        version_rec = get_version_record(active) if active else None

    institution = get_json(INSTITUTION_KEY) or {}
    prep = institution.get("preparationPeriod") or {}
    period = {
        "label": period_label
        or (
            f"{prep.get('start') or '—'} → {prep.get('end') or '—'}"
            if prep.get("start") or prep.get("end")
            else "Current institution evaluation period"
        ),
        "start": prep.get("start"),
        "end": prep.get("end"),
        "reviewerAvailableFrom": prep.get("reviewerAvailableFrom"),
        "source": "institution_config.preparationPeriod",
    }

    achievements = list_achievements(faculty.id) if configured else list_achievements(faculty.id)
    docs = (
        Document.query.filter_by(owner_user_id=faculty.id, upload_status="stored")
        .order_by(Document.created_at.desc())
        .all()
    )
    docs_by_id = {d.public_id: d for d in docs}
    parent_links = _doc_parent_links(achievements, docs_by_id)
    linked_ids = set(parent_links.keys())
    unlinked_docs = [d for d in docs if d.public_id not in linked_ids]

    assign = ReviewerAssignment.query.filter_by(faculty_user_id=faculty.id).first()
    assigned_reviewer = db.session.get(User, assign.reviewer_user_id) if assign else None

    decision_reviewer_ids = set()
    for ach in achievements:
        if ach.get("reviewedByUserId"):
            decision_reviewer_ids.add(int(ach["reviewedByUserId"]))
    for d in docs:
        if d.reviewed_by_user_id:
            decision_reviewer_ids.add(int(d.reviewed_by_user_id))
    decision_reviewers = []
    for rid in sorted(decision_reviewer_ids):
        u = db.session.get(User, rid)
        if u:
            decision_reviewers.append({"id": u.portal_id(), "name": _user_name(u), "email": u.email})

    scores = None
    rank_simulation = None
    criterion_a_est = None
    criterion_a_ver = None
    if configured:
        scores = compute_faculty_scores(
            assessment_data,
            catalog,
            kra_weights,
            faculty_user_id=faculty.id,
            faculty_rank=faculty.rank,
            institution_config=institution,
        )
        rank_simulation = compute_faculty_rank_simulation(
            faculty_rank=faculty.rank,
            faculty_scores=scores,
            institution_config=institution,
        )
        slots, set_docs, conflicts = aggregate_set_sef_for_faculty(faculty.id)
        selected = scoring_window_semester_keys(assessment_data)
        scoring_slots, excluded, window_findings, needs_selection = apply_semester_slot_window(
            slots, selected_semester_keys=selected
        )
        proxies = merged_slots_to_scoring_records(scoring_slots, conflicts)
        window_blocked = bool(window_findings) and not needs_selection
        window_msg = window_findings[0]["message"] if window_findings else None
        criterion_a_est = compute_criterion_a_from_records(
            proxies,
            verified_only=False,
            catalog=catalog,
            config_version=pinned_id,
            slot_window_blocked=window_blocked,
            window_needs_selection=needs_selection,
            window_message=window_msg,
        )
        criterion_a_ver = compute_criterion_a_from_records(
            proxies,
            verified_only=True,
            catalog=catalog,
            config_version=pinned_id,
            slot_window_blocked=window_blocked,
            window_needs_selection=needs_selection,
            window_message=window_msg,
        )
        semester_rows = []
        for slot in scoring_slots:
            semester_rows.append(
                {
                    "semesterKey": slot.semester_key,
                    "academicYear": slot.academic_year,
                    "semester": slot.semester,
                    "setRatingExtracted": slot.set_rating_extracted,
                    "sefRatingExtracted": slot.sef_rating_extracted,
                    "setRatingConfirmed": slot.set_rating_confirmed,
                    "sefRatingConfirmed": slot.sef_rating_confirmed,
                    "setVerificationStatus": slot.set_verification_status,
                    "sefVerificationStatus": slot.sef_verification_status,
                    "facultyIdentityStatus": slot.faculty_identity_status,
                }
            )
    else:
        semester_rows = []
        excluded = []
        set_docs = []

    est_present = _presentation_scores(
        (scores or {}).get("estimated"),
        criterion_a=criterion_a_est,
    )
    ver_present = _presentation_scores(
        (scores or {}).get("verified"),
        criterion_a=criterion_a_ver,
    )

    ach_counts = _achievement_counts(achievements)
    params = criterion_a_calculation_params(catalog) if catalog else {}

    # Enrich achievements for report detail
    reviewer_cache: dict[int, User | None] = {}
    ach_detail = []
    for ach in achievements:
        reviewer_name = None
        rid = ach.get("reviewedByUserId")
        if rid:
            if rid not in reviewer_cache:
                reviewer_cache[rid] = db.session.get(User, int(rid))
            reviewer_name = _user_name(reviewer_cache[rid])
        linked = []
        for did in ach.get("documentIds") or []:
            doc = docs_by_id.get(str(did))
            if doc:
                linked.append(
                    {
                        "id": doc.public_id,
                        "fileName": doc.original_filename,
                        "reviewStatus": doc.review_status,
                        "appPath": f"#review/{doc.public_id}",
                    }
                )
        ach_detail.append(
            {
                **ach,
                "indicatorName": _indicator_label(catalog, ach.get("indicatorId")),
                "criterionName": _criterion_label(catalog, ach.get("criterionId")),
                "kraName": _kra_label(catalog, ach.get("kraId")),
                "reviewerName": reviewer_name,
                "linkedDocuments": linked,
            }
        )

    evidence = []
    for doc in docs:
        parents = parent_links.get(doc.public_id) or []
        evidence.append(
            {
                "id": doc.public_id,
                "fileName": doc.original_filename,
                "kraId": doc.kra_id,
                "kraName": _kra_label(catalog, doc.kra_id),
                "indicatorId": doc.indicator_id,
                "indicatorName": _indicator_label(catalog, doc.indicator_id),
                "uploadedAt": doc.created_at.isoformat() if doc.created_at else None,
                "reviewStatus": doc.review_status,
                "displayStatus": _evidence_display_status(doc, parents),
                "ocrStatus": doc.ocr_status,
                "processingStatus": doc.processing_status,
                "documentKind": doc.document_kind,
                "parentAchievements": parents,
                "appPath": f"#review/{doc.public_id}",
            }
        )

    report_id = f"FL-RPT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    latest_update = None
    for ach in achievements:
        for key in ("reviewedAt", "updatedAt", "submittedAt", "createdAt"):
            if ach.get(key) and (latest_update is None or ach[key] > latest_update):
                latest_update = ach[key]
    for doc in docs:
        if doc.created_at:
            iso = doc.created_at.isoformat()
            if latest_update is None or iso > latest_update:
                latest_update = iso

    remaining = []
    if ach_counts["pending"]:
        remaining.append(f"{ach_counts['pending']} submitted achievement(s) awaiting review.")
    if ach_counts["needsChanges"]:
        remaining.append(f"{ach_counts['needsChanges']} achievement(s) need changes.")
    if ach_counts["drafts"]:
        remaining.append(f"{ach_counts['drafts']} draft achievement(s) not yet submitted.")
    if unlinked_docs:
        remaining.append(f"{len(unlinked_docs)} uploaded file(s) are not linked to an achievement.")
    if criterion_a_est and criterion_a_est.get("calculationUnavailable"):
        remaining.append("Criterion A has no eligible calculation yet.")
    elif criterion_a_ver and criterion_a_ver.get("calculationUnavailable") and criterion_a_est and not criterion_a_est.get("calculationUnavailable"):
        remaining.append("Criterion A estimated score exists; reviewer confirmation of ratings is still pending.")

    outstanding = _outstanding_actions(
        achievements,
        docs,
        criterion_a_ver or criterion_a_est,
        list(est_present.get("notes") or []) + list(ver_present.get("notes") or []),
    )

    return {
        "reportId": report_id,
        "generatedAt": _iso_now(),
        "title": "Faculty Assessment and Evidence Report",
        "brand": "FacultyLink",
        "preparationNotice": (
            "This report supports faculty preparation and reviewer verification. "
            "It is not an official reclassification or promotion decision."
        ),
        "preparedBy": {
            "id": actor.portal_id(),
            "name": _user_name(actor),
            "email": actor.email,
            "role": actor.role.value if hasattr(actor.role, "value") else str(actor.role),
        },
        "assessmentPeriod": period,
        "scoringVersion": {
            "configVersionId": pinned_id,
            "versionLabel": (version_rec or {}).get("label")
            or ((catalog or {}).get("version") if catalog else None)
            or pinned_id
            or "—",
            "status": (version_rec or {}).get("status"),
            "pinned": bool(pinned_id),
            "configured": configured,
            "kraWeights": kra_weights or {},
            "criterionAPolicy": params.get("calculation_policy"),
        },
        "faculty": {
            "id": faculty.portal_id(),
            "name": _user_name(faculty) or "—",
            "email": faculty.email,
            "department": faculty.department or None,
            "departmentDisplay": faculty.department or "Unavailable",
            "rank": faculty.rank or None,
            "rankDisplay": faculty.rank or "Unavailable",
            "employeeId": faculty.employee_id or None,
        },
        "reviewers": {
            "assigned": (
                {
                    "id": assigned_reviewer.portal_id(),
                    "name": _user_name(assigned_reviewer),
                    "email": assigned_reviewer.email,
                }
                if assigned_reviewer
                else None
            ),
            "decisionMakers": decision_reviewers,
        },
        "progress": {
            "latestUpdateAt": latest_update,
            "documentCount": len({d.public_id for d in docs}),
            "achievementCounts": ach_counts,
            "unlinkedEvidenceCount": len(unlinked_docs),
            "remainingWork": remaining,
            "countingNote": (
                "Document counts are unique files by ID. Achievement counts are achievement records "
                "(not supporting attachments). Supporting files linked to an approved achievement are "
                "shown as “Part of approved achievement,” not as separate approved achievements."
            ),
        },
        "executiveSummary": {
            "uploadedDocuments": len({d.public_id for d in docs}),
            "submittedAchievements": ach_counts["submitted"],
            "approvedAchievements": ach_counts["approved"],
            "pendingAchievements": ach_counts["pending"],
            "needsChangesAchievements": ach_counts["needsChanges"],
            "rejectedAchievements": ach_counts["rejected"],
            "draftAchievements": ach_counts["drafts"],
            "unlinkedEvidence": len(unlinked_docs),
            "estimatedOverall": est_present["overallWeighted"],
            "verifiedOverall": ver_present["overallWeighted"],
            "remainingWork": remaining,
        },
        "kraScoreSummary": {
            "estimated": est_present,
            "verified": ver_present,
            "weightBasis": (
                (scores or {}).get("estimated", {}).get("weightBasis")
                or (scores or {}).get("verified", {}).get("weightBasis")
                or "KRA weights from institution rank simulation (JC3 Table 2.2) for the faculty member’s current rank."
            ),
            "rankWeightResolution": (scores or {}).get("estimated", {}).get("rankWeightResolution"),
            "rawVsWeighted": (
                "Raw points are capped criterion totals within each KRA. "
                "Weighted contribution is raw total × that KRA’s rank-category weight (applied once)."
            ),
            "kraOrder": ["kra-I", "kra-II", "kra-III", "kra-IV"],
        },
        "criterionA": {
            "estimated": criterion_a_est,
            "verified": criterion_a_ver,
            "semesters": semester_rows,
            "excludedSemesterSlots": [s.to_dict() for s in (excluded or [])],
            "setSefDocuments": [
                {
                    "id": d.public_id,
                    "fileName": d.original_filename,
                    "documentKind": d.document_kind,
                    "ocrStatus": d.ocr_status,
                    "processingStatus": d.processing_status,
                    "reviewStatus": d.review_status,
                    "uploadedAt": d.created_at.isoformat() if d.created_at else None,
                    "appPath": f"#review/{d.public_id}",
                }
                for d in (set_docs or [])
            ],
            "policy": params.get("calculation_policy"),
        },
        "achievementTree": _group_achievements(catalog, ach_detail),
        "achievements": ach_detail,
        "evidenceRegister": evidence,
        "outstandingActions": outstanding,
        "rankSimulation": rank_simulation,
        "mutatesNothing": True,
    }
