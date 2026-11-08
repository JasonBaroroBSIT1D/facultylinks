from __future__ import annotations

import re
from typing import Any


def _cap(sum_pts: float, cap: float | None) -> float:
    if cap is None:
        return sum_pts
    return min(sum_pts, cap)


def _parse_cap_note(note: str | None) -> float | None:
    if not note:
        return None
    m = re.search(r"Max\s*=\s*(\d+)", note, re.I)
    return float(m.group(1)) if m else None


def _estimate_entry_points(indicator: dict, entry: dict) -> float:
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


def _verified_entry_points(indicator: dict, entry: dict) -> float:
    if entry.get("reviewStatus") not in ("approved",):
        return 0.0
    if entry.get("reviewerVerifiedPoints") is not None:
        return float(entry["reviewerVerifiedPoints"])
    if entry.get("verifiedPoints") is not None:
        return float(entry["verifiedPoints"])
    return 0.0


def _set_sef_raw(ratings: list, factor: float) -> float:
    filled = [float(r) for r in ratings if r is not None]
    if not filled:
        return 0.0
    avg = sum(filled) / len(filled)
    return avg * factor


def compute_kra_summaries(
    assessment_data: dict,
    catalog: dict,
    kra_weights: dict,
    *,
    verified: bool = False,
) -> dict[str, Any]:
    summaries = {}
    set_sef = assessment_data.get("setSef") or {}
    entries = assessment_data.get("entries") or {}

    for kra in catalog.get("kras", []):
        raw_sum = 0.0
        weight = float(kra_weights.get(kra["id"], kra.get("weight") or 0))

        for crit in kra.get("criteria", []):
            crit_cap = crit.get("capMaxPoints") or crit.get("maxPoints") or _parse_cap_note(crit.get("capNote"))
            crit_sum = 0.0

            set_sef_inds = [i for i in crit.get("indicators", []) if i.get("type") == "set_sef" or i.get("subType") in ("SET", "SEF")]
            if set_sef_inds:
                set_ind = next((i for i in crit.get("indicators", []) if i.get("subType") == "SET"), None)
                sef_ind = next((i for i in crit.get("indicators", []) if i.get("subType") == "SEF"), None)
                set_factor = (set_ind or {}).get("calculation", {}).get("factor") or 0.36
                sef_factor = (sef_ind or {}).get("calculation", {}).get("factor") or 0.24
                set_pts = _set_sef_raw(set_sef.get("SET") or [], set_factor)
                sef_pts = _set_sef_raw(set_sef.get("SEF") or [], sef_factor)
                crit_sum = _cap(set_pts + sef_pts, crit_cap)
            else:
                for ind in crit.get("indicators", []):
                    if ind.get("type") == "set_sef":
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
            raw_sum += crit_sum

        summaries[kra["id"]] = {
            "kraId": kra["id"],
            "name": kra.get("name"),
            "rawTotal": round(raw_sum, 4),
            "weightedContribution": round(raw_sum * weight, 4),
            "weight": weight,
        }

    overall = sum(s["weightedContribution"] for s in summaries.values())
    return {"byKra": summaries, "overallWeighted": round(overall, 4)}


def compute_faculty_scores(assessment_data: dict, catalog: dict, kra_weights: dict) -> dict:
    return {
        "estimated": compute_kra_summaries(assessment_data, catalog, kra_weights, verified=False),
        "verified": compute_kra_summaries(assessment_data, catalog, kra_weights, verified=True),
    }
