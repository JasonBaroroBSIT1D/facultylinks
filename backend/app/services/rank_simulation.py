"""Rank upgrade simulation — JC3 Table 2.2 (KRA weights) and Table 3.1 (sub-rank brackets).

Uses faculty *current* rank category only (not target/potential rank) for weights.
Inputs are unweighted KRA raw totals from scoring_engine (after rule caps).
"""
from __future__ import annotations

import math
import re
from typing import Any

KRA_IDS = ("kra-I", "kra-II", "kra-III", "kra-IV")

RANK_CATEGORY_META = {
    "instructor": {
        "label": "Instructor I–III",
        "sourceRef": "JC3 Table 2.2",
    },
    "assistant_professor": {
        "label": "Assistant Professor I–IV",
        "sourceRef": "JC3 Table 2.2",
    },
    "associate_professor": {
        "label": "Associate Professor I–V",
        "sourceRef": "JC3 Table 2.2",
    },
    "professor": {
        "label": "Professor I–VI",
        "sourceRef": "JC3 Table 2.2",
    },
    "college_university_professor": {
        "label": "College/University Professor",
        "sourceRef": "JC3 Table 2.2",
    },
}

DEFAULT_WEIGHT_MATRIX = {
    "instructor": {"kra-I": 0.6, "kra-II": 0.1, "kra-III": 0.2, "kra-IV": 0.1},
    "assistant_professor": {"kra-I": 0.5, "kra-II": 0.2, "kra-III": 0.2, "kra-IV": 0.1},
    "associate_professor": {"kra-I": 0.4, "kra-II": 0.3, "kra-III": 0.2, "kra-IV": 0.1},
    "professor": {"kra-I": 0.3, "kra-II": 0.4, "kra-III": 0.2, "kra-IV": 0.1},
    "college_university_professor": {"kra-I": 0.2, "kra-II": 0.5, "kra-III": 0.2, "kra-IV": 0.1},
}

DEFAULT_SCORE_BRACKETS = [
    {"minInclusive": 41, "maxInclusive": 50, "subRankIncrements": 1},
    {"minInclusive": 51, "maxInclusive": 60, "subRankIncrements": 2},
    {"minInclusive": 61, "maxInclusive": 70, "subRankIncrements": 3},
    {"minInclusive": 71, "maxInclusive": 80, "subRankIncrements": 4},
    {"minInclusive": 81, "maxInclusive": 90, "subRankIncrements": 5},
    {"minInclusive": 91, "maxInclusive": 100, "subRankIncrements": 6},
]

DEFAULT_RANK_SIMULATION_CONFIG = {
    "status": "published",
    "version": "jc3-table-2.2-3.1",
    "sourceRef": "DBM–CHED Joint Circular No. 3 (9th Cycle) Tables 2.2 and 3.1",
    "weightMatrixByCategory": DEFAULT_WEIGHT_MATRIX,
    "scoreBrackets": DEFAULT_SCORE_BRACKETS,
    "decimalBracketPolicy": "unresolved",
    "decimalBracketPolicyNote": (
        "Table 3.1 lists whole-number brackets only. Fractional overall weighted scores "
        "(e.g. 78.02) require an institution-published decimal bracket rule before sub-rank increments are authoritative."
    ),
    "belowMinimumNote": "Table 3.1 does not define sub-rank increments for overall weighted scores below 41.",
    "categoryEligibilityNotes": {
        "college_university_professor": (
            "Appointment as College/University Professor requires eligibility beyond cumulative "
            "weighted points — confirm institutional requirements."
        ),
        "category_crossing": (
            "Advancing across rank categories may require additional eligibility criteria beyond sub-rank increments."
        ),
    },
}

_CATEGORY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("college_university_professor", re.compile(r"^college\s*/\s*university\s+professor", re.I)),
    ("college_university_professor", re.compile(r"^college\s+university\s+professor", re.I)),
    ("assistant_professor", re.compile(r"^assistant\s+professor", re.I)),
    ("associate_professor", re.compile(r"^associate\s+professor", re.I)),
    ("instructor", re.compile(r"^instructor", re.I)),
    ("professor", re.compile(r"^professor", re.I)),
]


def resolve_rank_category(rank_label: str | None) -> str | None:
    """Map a faculty rank label to a stable category id (longest-prefix / ordered patterns)."""
    if not rank_label or not str(rank_label).strip():
        return None
    text = str(rank_label).strip()
    for cat_id, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return cat_id
    return None


def merge_rank_simulation_config(institution_config: dict | None) -> dict:
    base = dict(DEFAULT_RANK_SIMULATION_CONFIG)
    if not institution_config:
        return base
    rs = institution_config.get("rankSimulation")
    if not isinstance(rs, dict):
        return base
    out = {**base, **{k: v for k, v in rs.items() if v is not None}}
    if isinstance(rs.get("weightMatrixByCategory"), dict):
        merged_w = {}
        for cat, default_row in DEFAULT_WEIGHT_MATRIX.items():
            custom = rs["weightMatrixByCategory"].get(cat) or {}
            merged_w[cat] = {**default_row, **custom}
        out["weightMatrixByCategory"] = merged_w
    if isinstance(rs.get("scoreBrackets"), list) and rs["scoreBrackets"]:
        out["scoreBrackets"] = rs["scoreBrackets"]
    return out


def _extract_raw_by_kra(score_summary: dict | None) -> dict[str, float]:
    if not score_summary:
        return {k: 0.0 for k in KRA_IDS}
    by_kra = score_summary.get("byKra") or {}
    out: dict[str, float] = {}
    for kid in KRA_IDS:
        row = by_kra.get(kid) or {}
        out[kid] = float(row.get("rawTotal") or 0.0)
    return out


def _scoring_authoritative(score_summary: dict | None) -> bool:
    if not score_summary:
        return True
    for note in score_summary.get("notes") or []:
        if "Provisional" in str(note) or "not authoritative" in str(note):
            return False
    by_kra = score_summary.get("byKra") or {}
    for row in by_kra.values():
        if isinstance(row, dict) and row.get("kraCapPolicyUnresolved"):
            return False
    return True


def apply_rank_weights(raw_by_kra: dict[str, float], weights: dict[str, float]) -> tuple[list[dict], float]:
    lines: list[dict] = []
    total = 0.0
    for kid in KRA_IDS:
        raw = float(raw_by_kra.get(kid) or 0.0)
        w = float(weights.get(kid) or 0.0)
        contrib = raw * w
        lines.append(
            {
                "kraId": kid,
                "rawTotal": round(raw, 4),
                "weight": w,
                "weightPercent": round(w * 100, 2),
                "weightedContribution": round(contrib, 4),
            }
        )
        total += contrib
    return lines, round(total, 4)


def _classify_score_for_bracket(score: float, policy: str) -> tuple[float, bool]:
    """Return (classification_score, has_fractional_component)."""
    if abs(score - round(score)) < 1e-9:
        return float(int(round(score))), False
    frac = True
    p = (policy or "unresolved").strip().lower()
    if p == "floor_to_bracket":
        return math.floor(score + 1e-9), frac
    if p == "truncate_toward_zero":
        return float(int(score)) if score >= 0 else float(-int(-score)), frac
    if p == "round_half_up":
        return float(int(score + 0.5)) if score >= 0 else float(-int(-score + 0.5)), frac
    return score, frac


DOCUMENTED_DECIMAL_CANDIDATES = (
    ("floor_to_bracket", "Floor to lower whole number"),
    ("round_half_up", "Round half up to nearest whole number"),
)


def _match_bracket_row(classify_score: float, brackets: list[dict]) -> dict | None:
    for b in sorted(brackets, key=lambda x: x.get("minInclusive", 0)):
        lo = float(b.get("minInclusive", 0))
        hi = float(b.get("maxInclusive", lo))
        if lo <= classify_score <= hi:
            return b
    return None


def _bracket_projection(classify_score: float, brackets: list[dict], policy_key: str, policy_label: str) -> dict | None:
    matched = _match_bracket_row(classify_score, brackets)
    if not matched:
        return None
    inc = int(matched.get("subRankIncrements", 0))
    return {
        "policyKey": policy_key,
        "policyLabel": policy_label,
        "classificationScore": classify_score,
        "minInclusive": matched["minInclusive"],
        "maxInclusive": matched["maxInclusive"],
        "subRankIncrements": inc,
        "bracketLabel": f"{matched['minInclusive']}–{matched['maxInclusive']} → {inc} sub-rank(s)",
    }


def resolve_sub_rank_bracket(overall_weighted: float, rs_config: dict) -> dict[str, Any]:
    brackets = rs_config.get("scoreBrackets") or DEFAULT_SCORE_BRACKETS
    policy = rs_config.get("decimalBracketPolicy") or "unresolved"
    if overall_weighted < 41:
        return {
            "status": "below_minimum",
            "subRankIncrements": 0,
            "label": "Below Table 3.1 minimum (41)",
            "unresolvedReason": rs_config.get("belowMinimumNote"),
            "overallWeightedScore": round(overall_weighted, 4),
        }
    has_frac = abs(overall_weighted - round(overall_weighted)) > 1e-9
    policy_resolved = policy not in (None, "", "unresolved")

    if has_frac and not policy_resolved:
        floor_score = math.floor(overall_weighted + 1e-9)
        round_score = float(int(round(overall_weighted)))
        candidates = []
        for pk, pl in DOCUMENTED_DECIMAL_CANDIDATES:
            if pk == "floor_to_bracket":
                cls = floor_score
            elif pk == "round_half_up":
                cls = round_score
            else:
                continue
            row = _bracket_projection(cls, brackets, pk, pl)
            if row:
                candidates.append(row)
        if not candidates:
            return {
                "status": "unresolved",
                "subRankIncrements": None,
                "label": f"Decimal score {overall_weighted:.2f} between Table 3.1 brackets",
                "unresolvedReason": (
                    f"Score {overall_weighted:.2f} has a fractional part and does not align with an integer "
                    "bracket boundary until decimal bracket policy is published."
                ),
                "conditionalProjections": [],
                "overallWeightedScore": round(overall_weighted, 4),
            }
        primary = candidates[0]
        note = rs_config.get("decimalBracketPolicyNote")
        return {
            "status": "conditional",
            "subRankIncrements": None,
            "provisionalIncrements": primary["subRankIncrements"],
            "minInclusive": primary["minInclusive"],
            "maxInclusive": primary["maxInclusive"],
            "label": (
                f"Decimal score {overall_weighted:.2f} — integer bracket {primary['bracketLabel']} "
                "if floor-to-bracket policy applies"
            ),
            "unresolvedReason": note,
            "conditionalProjections": candidates,
            "primaryPolicyCandidate": primary["policyKey"],
            "overallWeightedScore": round(overall_weighted, 4),
        }

    classify_score, _ = _classify_score_for_bracket(overall_weighted, policy)
    matched = _match_bracket_row(classify_score, brackets)
    if not matched:
        if classify_score > 100:
            return {
                "status": "above_table",
                "subRankIncrements": None,
                "label": "Above Table 3.1 maximum (100)",
                "unresolvedReason": "Score exceeds published bracket table — confirm institutional policy.",
                "overallWeightedScore": round(overall_weighted, 4),
            }
        return {
            "status": "unresolved",
            "subRankIncrements": None,
            "label": f"No Table 3.1 bracket for classification score {classify_score}",
            "unresolvedReason": (
                f"After applying decimal policy '{policy}', score {overall_weighted:.4f} "
                f"classifies as {classify_score}, which is outside configured brackets."
            ),
            "overallWeightedScore": round(overall_weighted, 4),
        }
    inc = int(matched.get("subRankIncrements", 0))
    label = f"{matched['minInclusive']}–{matched['maxInclusive']} → {inc} sub-rank(s)"
    return {
        "status": "resolved",
        "subRankIncrements": inc,
        "minInclusive": matched["minInclusive"],
        "maxInclusive": matched["maxInclusive"],
        "label": label,
        "unresolvedReason": None,
        "overallWeightedScore": round(overall_weighted, 4),
    }


def build_rank_ladder(rank_options: list[str]) -> list[dict]:
    ladder = []
    for i, label in enumerate(rank_options or []):
        cat = resolve_rank_category(label)
        ladder.append({"index": i, "label": label, "categoryId": cat})
    return ladder


DISPLAY_ELIGIBILITY_LABEL = "Projected rank — eligibility subject to verification"
DISPLAY_PROVISIONAL_SCORING = "Projected rank — provisional scoring"


def _movement_label(current_rank: str, destination: str | None) -> str | None:
    if not destination:
        return None
    return f"{current_rank} → {destination}"


def advance_potential_rank(
    current_rank: str,
    increments: int | None,
    ladder: list[dict],
    rs_config: dict,
    *,
    authoritative: bool,
) -> dict[str, Any]:
    if increments is None:
        return {
            "status": "unresolved",
            "currentRank": current_rank,
            "increments": None,
            "potentialRank": None,
            "movement": None,
            "displayLabel": None,
            "notes": ["Sub-rank increment unresolved — projected destination cannot be computed."],
        }
    if increments <= 0:
        return {
            "status": "no_advancement",
            "currentRank": current_rank,
            "increments": 0,
            "potentialRank": current_rank,
            "movement": _movement_label(current_rank, current_rank),
            "displayLabel": None,
            "notes": [rs_config.get("belowMinimumNote") or "No sub-rank advancement for this score."],
        }
    if not ladder:
        return {
            "status": "unresolved",
            "currentRank": current_rank,
            "increments": increments,
            "potentialRank": None,
            "movement": None,
            "displayLabel": None,
            "notes": ["Rank ladder is not configured."],
        }
    cur_idx = next((s["index"] for s in ladder if s["label"] == current_rank), -1)
    if cur_idx < 0:
        cur_idx = next((s["index"] for s in ladder if s["label"].lower() == current_rank.lower()), -1)
    if cur_idx < 0:
        return {
            "status": "unresolved",
            "currentRank": current_rank,
            "increments": increments,
            "potentialRank": None,
            "movement": None,
            "displayLabel": None,
            "notes": ["Current rank is not on the configured rank ladder."],
        }
    new_idx = cur_idx + increments
    notes: list[str] = []
    display_label: str | None = None
    if not authoritative:
        display_label = DISPLAY_PROVISIONAL_SCORING
        notes.append("Scoring policy or KRA envelope rules are provisional.")
    if new_idx >= len(ladder):
        ceiling = ladder[-1]["label"]
        notes.append(f"Sub-rank increment ({increments}) exceeds ladder — ceiling at {ceiling}.")
        return {
            "status": "ceiling",
            "currentRank": current_rank,
            "increments": increments,
            "potentialRank": ceiling,
            "movement": _movement_label(current_rank, ceiling),
            "displayLabel": display_label,
            "notes": notes,
        }
    cur_cat = ladder[cur_idx].get("categoryId")
    new_cat = ladder[new_idx].get("categoryId")
    potential = ladder[new_idx]["label"]
    crosses_category = bool(cur_cat and new_cat and cur_cat != new_cat)
    if crosses_category:
        cat_note = rs_config.get("categoryEligibilityNotes", {}).get("category_crossing", "")
        if cat_note:
            notes.append(cat_note)
    if new_cat == "college_university_professor":
        notes.append(
            rs_config.get("categoryEligibilityNotes", {}).get(
                "college_university_professor",
                "College/University Professor eligibility requires verification beyond points.",
            )
        )
    if crosses_category or new_cat == "college_university_professor":
        if display_label is None:
            display_label = DISPLAY_ELIGIBILITY_LABEL
        status = "eligibility_required"
    elif not authoritative:
        status = "provisional"
    else:
        status = "determinate"
    return {
        "status": status,
        "currentRank": current_rank,
        "increments": increments,
        "potentialRank": potential,
        "movement": _movement_label(current_rank, potential),
        "displayLabel": display_label,
        "notes": [n for n in notes if n],
    }


def compute_rank_simulation_bucket(
    *,
    score_summary: dict | None,
    current_rank: str | None,
    institution_config: dict | None,
    score_source: str,
) -> dict[str, Any]:
    rs_config = merge_rank_simulation_config(institution_config)
    category_id = resolve_rank_category(current_rank)
    if not category_id:
        return {
            "configured": False,
            "scoreSource": score_source,
            "status": "profile_incomplete",
            "message": "Current rank is missing or not recognized. Complete your profile with a supported rank label.",
            "currentRank": current_rank or "",
        }
    weights = (rs_config.get("weightMatrixByCategory") or {}).get(category_id) or DEFAULT_WEIGHT_MATRIX[category_id]
    wsum = sum(float(weights.get(k, 0)) for k in KRA_IDS)
    raw_by_kra = _extract_raw_by_kra(score_summary)
    kra_lines, overall = apply_rank_weights(raw_by_kra, weights)
    authoritative = _scoring_authoritative(score_summary)
    notes = list(score_summary.get("notes") or []) if score_summary else []
    bracket = resolve_sub_rank_bracket(overall, rs_config)
    ladder = build_rank_ladder((institution_config or {}).get("rankOptions") or [])
    effective_increments = bracket.get("subRankIncrements")
    if effective_increments is None:
        effective_increments = bracket.get("provisionalIncrements")
    potential = advance_potential_rank(
        current_rank or "",
        effective_increments,
        ladder,
        rs_config,
        authoritative=authoritative,
    )
    conditional_rank_projections: list[dict[str, Any]] = []
    for candidate in bracket.get("conditionalProjections") or []:
        alt_inc = candidate.get("subRankIncrements")
        alt_potential = advance_potential_rank(
            current_rank or "",
            alt_inc,
            ladder,
            rs_config,
            authoritative=authoritative,
        )
        conditional_rank_projections.append(
            {
                "policyKey": candidate.get("policyKey"),
                "policyLabel": candidate.get("policyLabel"),
                "classificationScore": candidate.get("classificationScore"),
                "bracketLabel": candidate.get("bracketLabel"),
                "subRankIncrements": alt_inc,
                "potentialRank": alt_potential,
            }
        )
    basis_label = "Reviewer-verified points" if score_source == "verified" else "Estimated points"
    cat_meta = RANK_CATEGORY_META.get(category_id, {})
    return {
        "configured": True,
        "scoreSource": score_source,
        "basisLabel": basis_label,
        "currentRank": current_rank,
        "rankCategory": {
            "id": category_id,
            "label": cat_meta.get("label", category_id),
            "sourceRef": cat_meta.get("sourceRef"),
        },
        "weightMatrixVersion": rs_config.get("version"),
        "weightsSumCheck": round(wsum, 4),
        "kras": kra_lines,
        "overallWeightedScore": overall,
        "scoringAuthoritative": authoritative,
        "notes": notes,
        "subRankBracket": bracket,
        "potentialRank": potential,
        "conditionalRankProjections": conditional_rank_projections,
    }


def compute_faculty_rank_simulation(
    *,
    faculty_rank: str | None,
    faculty_scores: dict,
    institution_config: dict | None,
) -> dict[str, Any]:
    rs_config = merge_rank_simulation_config(institution_config)
    category_id = resolve_rank_category(faculty_rank)
    return {
        "policyStatus": rs_config.get("status", "published"),
        "policyVersion": rs_config.get("version"),
        "sourceRef": rs_config.get("sourceRef"),
        "currentRank": faculty_rank or "",
        "rankCategory": (
            {
                "id": category_id,
                "label": RANK_CATEGORY_META.get(category_id, {}).get("label", category_id),
            }
            if category_id
            else None
        ),
        "profileComplete": category_id is not None,
        "estimated": compute_rank_simulation_bucket(
            score_summary=faculty_scores.get("estimated"),
            current_rank=faculty_rank,
            institution_config=institution_config,
            score_source="estimated",
        ),
        "verified": compute_rank_simulation_bucket(
            score_summary=faculty_scores.get("verified"),
            current_rank=faculty_rank,
            institution_config=institution_config,
            score_source="verified",
        ),
    }


def validate_rank_simulation_config(rs: dict) -> list[str]:
    errors: list[str] = []
    wmb = rs.get("weightMatrixByCategory") or {}
    for cat, row in wmb.items():
        if cat not in RANK_CATEGORY_META:
            errors.append(f"Unknown rank category: {cat}")
            continue
        s = sum(float(row.get(k, 0)) for k in KRA_IDS)
        if abs(s - 1.0) > 0.001:
            errors.append(f"Category {cat} weights sum to {s:.4f}, expected 1.0")
    brackets = rs.get("scoreBrackets") or []
    prev_hi = None
    for b in sorted(brackets, key=lambda x: x.get("minInclusive", 0)):
        lo = b.get("minInclusive")
        hi = b.get("maxInclusive")
        if lo is None or hi is None:
            errors.append("Bracket missing minInclusive or maxInclusive")
            continue
        if float(lo) > float(hi):
            errors.append(f"Bracket {lo}-{hi} is inverted")
        if prev_hi is not None and float(lo) <= prev_hi:
            errors.append(f"Overlapping brackets at {lo}")
        prev_hi = float(hi)
    return errors
