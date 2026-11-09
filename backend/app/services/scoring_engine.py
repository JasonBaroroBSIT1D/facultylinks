from __future__ import annotations

import re
from typing import Any

from app.services.achievement_rules import DEFAULT_KRA_IV_SCORING_POLICY


def _cap(sum_pts: float, cap: float | None) -> float:
    if cap is None:
        return sum_pts
    return min(sum_pts, cap)


def _parse_cap_note(note: str | None) -> float | None:
    if not note:
        return None
    m = re.search(r"Max\s*=\s*(\d+)", note, re.I)
    return float(m.group(1)) if m else None


def _is_supporting_evidence_indicator(indicator: dict) -> bool:
    if indicator.get("id") == "kra-I-A-special":
        return True
    if indicator.get("role") == "supporting_evidence":
        return True
    return (indicator.get("calculation") or {}).get("kind") == "supporting_evidence"


def _estimate_entry_points(indicator: dict, entry: dict) -> float:
    if _is_supporting_evidence_indicator(indicator):
        return 0.0
    if entry.get("reviewStatus") == "replaced":
        return 0.0
    if entry.get("verifiedPoints") is not None and entry.get("reviewStatus") == "approved":
        return float(entry.get("verifiedPoints"))
    if entry.get("reviewerVerifiedPoints") is not None and entry.get("reviewStatus") == "approved":
        return float(entry["reviewerVerifiedPoints"])
    est = entry.get("estimatedPoints")
    if est is not None:
        return float(est)
    calc = indicator.get("calculation") or {}
    max_pts = indicator.get("maxPoints") or calc.get("maxPoints")
    if max_pts is not None:
        pct = entry.get("contributionPercent") or 100
        return float(max_pts) * float(pct) / 100.0
    return 0.0


def _self_assessed_achievement_indicator(indicator_id: str) -> bool:
    if not indicator_id:
        return False
    if indicator_id.startswith("kra-I-B") or indicator_id.startswith("kra-I-C"):
        return True
    return (
        indicator_id.startswith("kra-II-")
        or indicator_id.startswith("kra-III-")
        or indicator_id.startswith("kra-IV-")
    )


def _achievement_points_for_mode(ach: dict, *, verified: bool) -> float:
    if verified:
        if ach.get("submissionStatus") != "submitted":
            return 0.0
        if ach.get("reviewStatus") != "approved":
            return 0.0
        val = ach.get("reviewerVerifiedPoints")
        if val is None:
            val = ach.get("claimedPoints")
        return float(val or 0)
    if ach.get("submissionStatus") not in ("submitted", "draft"):
        return 0.0
    if ach.get("claimedPoints") is not None:
        return float(ach["claimedPoints"])
    return 0.0


def _sum_self_assessed_indicator(indicator: dict, achievements: list[dict], *, verified: bool) -> float:
    calc = indicator.get("calculation") or {}
    kind = calc.get("kind")
    ind_id = indicator.get("id") or ""
    ach_for_ind = [
        a
        for a in achievements
        if a.get("indicatorId") == ind_id
        and (a.get("submissionStatus") == "submitted" if verified else a.get("submissionStatus") in ("submitted", "draft"))
    ]

    if kind == "tiered_option" and calc.get("tierCaps"):
        options = calc.get("options") or indicator.get("points") or {}
        tier_field = calc.get("tierField") or "tier"
        tier_caps = calc.get("tierCaps") or {}
        total = 0.0
        for tier, cap in tier_caps.items():
            tier_sum = 0.0
            for ach in ach_for_ind:
                if (ach.get(tier_field) or ach.get("tier") or "").strip().lower() != tier:
                    continue
                tier_sum += _achievement_points_for_mode(ach, verified=verified)
            total += _cap(tier_sum, float(cap))
        return total

    ind_sum = sum(_achievement_points_for_mode(a, verified=verified) for a in ach_for_ind)
    agg_cap = calc.get("aggregateCap") or indicator.get("aggregateCap")
    if agg_cap is not None and not calc.get("aggregateGroup"):
        ind_sum = _cap(ind_sum, float(agg_cap))
    return ind_sum


def _sum_criterion_self_assessed_indicators(
    indicators: list[dict], achievements: list[dict], *, verified: bool
) -> float:
    """Sum self-assessed indicator points in one criterion, honoring shared aggregateGroup caps."""
    from collections import defaultdict

    ind_sums: dict[str, float] = {}
    for ind in indicators:
        iid = ind.get("id") or ""
        if not _self_assessed_achievement_indicator(iid):
            continue
        ind_sums[iid] = _sum_self_assessed_indicator(ind, achievements, verified=verified)

    group_members: dict[str, list[str]] = defaultdict(list)
    group_caps: dict[str, float] = {}
    standalone = 0.0
    for ind in indicators:
        iid = ind.get("id") or ""
        if iid not in ind_sums:
            continue
        calc = ind.get("calculation") or {}
        grp = calc.get("aggregateGroup")
        if grp:
            group_members[grp].append(iid)
            cap = calc.get("aggregateCap") or ind.get("aggregateCap")
            if cap is not None:
                group_caps[grp] = float(cap)
        else:
            standalone += ind_sums[iid]

    total = standalone
    for grp, members in group_members.items():
        raw = sum(ind_sums[mid] for mid in members)
        total += _cap(raw, group_caps.get(grp))
    return total


def _active_achievements(assessment_data: dict, indicator_ids: set[str]) -> list[dict]:
    from app.services.achievement_rules import is_active_achievement

    achievements = assessment_data.get("achievements") or []
    return [
        a
        for a in achievements
        if is_active_achievement(a) and a.get("indicatorId") in indicator_ids
    ]


def _claimed_achievement_points(ach: dict) -> float:
    if ach.get("reviewStatus") == "replaced":
        return 0.0
    return float(ach.get("claimedPoints") or 0)


def _verified_achievement_points(ach: dict) -> float:
    if ach.get("reviewStatus") != "approved":
        return 0.0
    if ach.get("submissionStatus") != "submitted":
        return 0.0
    vp = ach.get("reviewerVerifiedPoints")
    return float(vp) if vp is not None else 0.0


def _verified_entry_points(indicator: dict, entry: dict) -> float:
    if _is_supporting_evidence_indicator(indicator):
        return 0.0
    if entry.get("reviewStatus") not in ("approved",):
        return 0.0
    if entry.get("reviewerVerifiedPoints") is not None:
        return float(entry["reviewerVerifiedPoints"])
    if entry.get("verifiedPoints") is not None:
        return float(entry["verifiedPoints"])
    return 0.0


def _ocr_criterion_a_scoring(
    faculty_user_id: int,
    *,
    verified: bool,
    assessment_data: dict | None,
    catalog: dict | None,
) -> dict[str, Any] | None:
    """Faculty-level SET/SEF PDF aggregation (deduplicated across document uploads)."""
    from app.services.set_sef_aggregation import criterion_a_scoring_inputs
    from app.services.teaching_effectiveness import compute_criterion_a_from_records

    proxies, docs, _conflicts, _findings, needs_selection, blocked, window_msg = criterion_a_scoring_inputs(
        faculty_user_id, assessment_data
    )
    if not docs:
        return None
    config_version = (assessment_data or {}).get("configVersionId") or (docs[0].config_version if docs else None)
    return compute_criterion_a_from_records(
        proxies,
        verified_only=verified,
        config_version=config_version,
        catalog=catalog,
        slot_window_blocked=blocked,
        window_needs_selection=needs_selection,
        window_message=window_msg,
    )


def compute_kra_summaries(
    assessment_data: dict,
    catalog: dict,
    kra_weights: dict,
    *,
    verified: bool = False,
    faculty_user_id: int | None = None,
) -> dict[str, Any]:
    summaries = {}
    set_sef = assessment_data.get("setSef") or {}
    entries = assessment_data.get("entries") or {}

    for kra_row in catalog.get("kras", []):
        kra = dict(kra_row)
        if kra.get("id") == "kra-IV" and not kra.get("scoringPolicy"):
            kra["scoringPolicy"] = dict(DEFAULT_KRA_IV_SCORING_POLICY)
        raw_sum = 0.0
        weight = float(kra_weights.get(kra["id"], kra.get("weight") or 0))
        criterion_a_meta = None
        criterion_totals: list[dict[str, Any]] = []

        for crit in kra.get("criteria", []):
            crit_cap = crit.get("capMaxPoints") or crit.get("maxPoints") or _parse_cap_note(crit.get("capNote"))
            crit_sum = 0.0

            from app.services.catalog import criterion_a_calculation_params

            set_sef_inds = [i for i in crit.get("indicators", []) if i.get("type") == "set_sef" or i.get("subType") in ("SET", "SEF")]
            if set_sef_inds:
                crit_a = (
                    _ocr_criterion_a_scoring(
                        faculty_user_id,
                        verified=verified,
                        assessment_data=assessment_data,
                        catalog=catalog,
                    )
                    if faculty_user_id
                    else None
                )
                if crit_a is not None:
                    criterion_a_meta = crit_a
                    if crit_a.get("configurationError"):
                        crit_sum = 0.0
                    else:
                        pts = crit_a.get("criterionAPoints")
                        if pts is None:
                            pts = crit_a.get("partialSubtotal")
                        crit_sum = float(pts or 0.0)
                        crit_sum = _cap(crit_sum, crit_cap)
                else:
                    from app.services.teaching_effectiveness import compute_manual_set_sef_points

                    manual = compute_manual_set_sef_points(
                        set_sef.get("SET") or [],
                        set_sef.get("SEF") or [],
                        catalog=catalog,
                    )
                    criterion_a_meta = manual
                    if manual.get("configurationError"):
                        crit_sum = 0.0
                    else:
                        pts = manual.get("criterionAPoints")
                        if pts is None:
                            pts = manual.get("partialSubtotal")
                        crit_sum = float(pts or 0.0)
                        crit_sum = _cap(crit_sum, crit_cap)
            else:
                from app.services.catalog import SET_SEF_OCR_INDICATOR_IDS
                from app.services.catalog_merge import INTAKE_PDF_TYPES

                ind_ids = {i["id"] for i in crit.get("indicators", []) if i.get("id")}
                bc_ids = {i for i in ind_ids if _self_assessed_achievement_indicator(i)}
                bc_achievements = _active_achievements(assessment_data, bc_ids) if bc_ids else []
                sa_inds = [
                    i
                    for i in crit.get("indicators", [])
                    if _self_assessed_achievement_indicator(i.get("id") or "")
                ]
                if sa_inds:
                    crit_sum += _sum_criterion_self_assessed_indicators(sa_inds, bc_achievements, verified=verified)

                for ind in crit.get("indicators", []):
                    if ind.get("type") == "set_sef":
                        continue
                    if _is_supporting_evidence_indicator(ind):
                        continue
                    if ind.get("id") in SET_SEF_OCR_INDICATOR_IDS or ind.get("type") in INTAKE_PDF_TYPES:
                        continue
                    if _self_assessed_achievement_indicator(ind.get("id") or ""):
                        continue
                    ind_list = entries.get(ind["id"]) or []
                    active = [
                        e
                        for e in ind_list
                        if e.get("reviewStatus") != "replaced"
                        and e.get("linkedDocumentId")  # skip orphan entries without doc when verified
                    ] or ind_list
                    if verified:
                        ind_sum = sum(_verified_entry_points(ind, e) for e in active)
                    else:
                        ind_sum = sum(_estimate_entry_points(ind, e) for e in active)
                    ind_cap = ind.get("maxPoints")
                    ind_sum = _cap(ind_sum, ind_cap)
                    crit_sum += ind_sum
                crit_sum = _cap(crit_sum, crit_cap)
            criterion_totals.append(
                {
                    "id": crit.get("id"),
                    "name": crit.get("name"),
                    "rawTotal": round(crit_sum, 4),
                    "capMaxPoints": crit_cap,
                }
            )
            raw_sum += crit_sum

        policy = kra.get("scoringPolicy") or {}
        kra_summary = {
            "kraId": kra["id"],
            "name": kra.get("name"),
            "criteria": criterion_totals,
            "weight": weight,
        }
        if kra.get("id") == "kra-III" and policy:
            core_ids = set(policy.get("coreCriteria") or [])
            bonus_id = policy.get("bonusCriterion")
            core_sum = sum(c["rawTotal"] for c in criterion_totals if c.get("id") in core_ids)
            bonus_sum = sum(c["rawTotal"] for c in criterion_totals if c.get("id") == bonus_id)
            raw_uncapped = core_sum + bonus_sum
            kra_summary["coreSubtotal"] = round(core_sum, 4)
            kra_summary["bonusSubtotal"] = round(bonus_sum, 4)
            kra_summary["rawTotalBeforeKraCap"] = round(raw_uncapped, 4)
            kra_summary["kraCapPolicyNote"] = policy.get("unresolvedNote")
            kra_cap = float(kra.get("maxPoints") or policy.get("coreMaxSum") or 100)
            if raw_uncapped > kra_cap:
                kra_summary["kraCapPolicyUnresolved"] = True
            raw_sum = raw_uncapped
            if policy.get("applyKraEnvelopeCap"):
                raw_sum = _cap(raw_sum, kra_cap)
        elif kra.get("id") == "kra-IV" and policy:
            core_ids = set(policy.get("coreCriteria") or [])
            add_ids = set(policy.get("additionalCriteria") or [])
            core_sum = sum(c["rawTotal"] for c in criterion_totals if c.get("id") in core_ids)
            add_sum = sum(c["rawTotal"] for c in criterion_totals if c.get("id") in add_ids)
            raw_uncapped = core_sum + add_sum
            kra_summary["coreSubtotal"] = round(core_sum, 4)
            kra_summary["additionalSubtotal"] = round(add_sum, 4)
            kra_summary["rawTotalBeforeKraCap"] = round(raw_uncapped, 4)
            kra_summary["kraCapPolicyNote"] = policy.get("unresolvedNote")
            kra_cap = float(kra.get("maxPoints") or policy.get("kraListedMax") or policy.get("coreMaxSum") or 100)
            if raw_uncapped > kra_cap:
                kra_summary["kraCapPolicyUnresolved"] = True
            raw_sum = raw_uncapped
            if policy.get("applyKraEnvelopeCap"):
                raw_sum = _cap(raw_sum, kra_cap)
        else:
            kra_cap = kra.get("maxPoints")
            if kra_cap is not None:
                raw_sum = _cap(raw_sum, float(kra_cap))
        kra_summary["rawTotal"] = round(raw_sum, 4)
        kra_summary["weightedContribution"] = round(raw_sum * weight, 4)
        if criterion_a_meta is not None:
            kra_summary["criterionA"] = criterion_a_meta
            kra_summary["criterionAIncomplete"] = bool(criterion_a_meta.get("incomplete"))
            kra_summary["criterionAIncompleteReason"] = criterion_a_meta.get("incompleteReason")
        summaries[kra["id"]] = kra_summary

    overall = sum(s["weightedContribution"] for s in summaries.values())
    notes: list[str] = []
    kra_i = summaries.get("kra-I", {})
    if kra_i.get("criterionAIncomplete"):
        reason = kra_i.get("criterionAIncompleteReason") or "Criterion A teaching effectiveness is incomplete."
        notes.append(reason)
    if not verified:
        draft_pts = 0.0
        for ach in assessment_data.get("achievements") or []:
            if ach.get("submissionStatus") == "draft" and _self_assessed_achievement_indicator(ach.get("indicatorId") or ""):
                draft_pts += _claimed_achievement_points(ach)
        if draft_pts > 0:
            notes.append(
                f"Faculty estimate includes {round(draft_pts, 2)} pts from unsubmitted draft achievements "
                "(self-assessed KRAs)."
            )
    for kra_id, kra_summary in summaries.items():
        if kra_summary.get("kraCapPolicyUnresolved"):
            note = kra_summary.get("kraCapPolicyNote") or f"{kra_id}: KRA envelope cap policy is unresolved."
            notes.append(f"Provisional scoring: {note} Weighted points are not authoritative for rank until resolved.")
    return {"byKra": summaries, "overallWeighted": round(overall, 4), "notes": notes}


def compute_faculty_scores(
    assessment_data: dict,
    catalog: dict,
    kra_weights: dict,
    *,
    faculty_user_id: int | None = None,
) -> dict:
    return {
        "estimated": compute_kra_summaries(
            assessment_data, catalog, kra_weights, verified=False, faculty_user_id=faculty_user_id
        ),
        "verified": compute_kra_summaries(
            assessment_data, catalog, kra_weights, verified=True, faculty_user_id=faculty_user_id
        ),
    }
