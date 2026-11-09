"""Criterion A (Teaching Effectiveness) scoring from verified SET/SEF semester records."""

from __future__ import annotations

from typing import Any

from flask import has_app_context

from app.models import SetSefSemesterRecord
from app.services.catalog import (
    CRITERION_A_POLICY_FLEXIBLE,
    CRITERION_A_POLICY_LEGACY,
    criterion_a_calculation_params,
    get_catalog_by_version_label,
)

SET_FACTOR = 0.36
SEF_FACTOR = 0.24
SET_MAX = 36.0
SEF_MAX = 24.0
CRIT_A_MAX = 60.0
MAX_SEMESTER_SLOTS = 6

_IDENTITY_BLOCKS_VERIFIED = frozenset({"mismatch", "missing", "needs_confirmation"})


def _blocks_identity(rec: SetSefSemesterRecord) -> bool:
    return rec.faculty_identity_status in _IDENTITY_BLOCKS_VERIFIED


def _approved_set_rating(rec: SetSefSemesterRecord) -> float | None:
    if _blocks_identity(rec):
        return None
    if rec.set_verification_status != "verified":
        return None
    if rec.set_rating_confirmed is not None:
        return float(rec.set_rating_confirmed)
    if rec.set_rating_extracted is not None:
        return float(rec.set_rating_extracted)
    return None


def _approved_sef_rating(rec: SetSefSemesterRecord) -> float | None:
    if _blocks_identity(rec):
        return None
    if rec.sef_verification_status != "verified":
        return None
    if rec.sef_rating_confirmed is not None:
        return float(rec.sef_rating_confirmed)
    if rec.sef_rating_extracted is not None:
        return float(rec.sef_rating_extracted)
    return None


def _estimated_set(rec: SetSefSemesterRecord) -> float | None:
    if _blocks_identity(rec):
        return None
    if rec.set_rating_confirmed is not None:
        return float(rec.set_rating_confirmed)
    if rec.set_rating_extracted is not None:
        return float(rec.set_rating_extracted)
    return None


def _estimated_sef(rec: SetSefSemesterRecord) -> float | None:
    if _blocks_identity(rec):
        return None
    if rec.sef_rating_confirmed is not None:
        return float(rec.sef_rating_confirmed)
    if rec.sef_rating_extracted is not None:
        return float(rec.sef_rating_extracted)
    return None


def _flexible_component_score(values: list[float], factor: float, cap: float) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    avg = sum(values) / len(values)
    points = min(round(avg * factor, 4), cap)
    return points, round(avg, 4)


def _legacy_component_score(
    values: list[float], factor: float, cap: float, required_slots: int
) -> tuple[float | None, float | None]:
    if len(values) < required_slots:
        return None, None
    sample = values[:required_slots]
    avg = sum(sample) / required_slots
    points = min(round(avg * factor, 4), cap)
    return points, round(avg, 4)


def compute_manual_set_sef_points(
    set_ratings: list,
    sef_ratings: list,
    *,
    catalog: dict | None,
) -> dict[str, Any]:
    """Manual SET/SEF arrays in assessment.data — same policy dispatch as OCR records."""
    params = criterion_a_calculation_params(catalog)
    policy_error = params.get("calculation_policy_error")
    if policy_error:
        return _configuration_error_result(
            policy_error,
            config_version=(catalog or {}).get("version"),
            catalog=catalog,
            params=params,
        )
    policy = params["calculation_policy"]
    set_factor = params["set_factor"]
    sef_factor = params["sef_factor"]
    required = params["required_slots"]
    set_max = params["set_max"]
    sef_max = params["sef_max"]
    crit_max = params["criterion_a_max"]

    set_vals = [float(r) for r in (set_ratings or []) if r is not None]
    sef_vals = [float(r) for r in (sef_ratings or []) if r is not None]

    if policy == CRITERION_A_POLICY_FLEXIBLE:
        set_points, set_avg = _flexible_component_score(set_vals[:required], set_factor, set_max)
        sef_points, sef_avg = _flexible_component_score(sef_vals[:required], sef_factor, sef_max)
    else:
        set_points, set_avg = _legacy_component_score(set_vals, set_factor, set_max, required)
        sef_points, sef_avg = _legacy_component_score(sef_vals, sef_factor, sef_max, required)

    combined_complete = set_points is not None and sef_points is not None
    criterion_a_points = None
    partial_subtotal = None
    if combined_complete:
        criterion_a_points = round(min(set_points + sef_points, crit_max), 4)
    elif policy == CRITERION_A_POLICY_FLEXIBLE:
        if set_points is not None:
            partial_subtotal = set_points
        elif sef_points is not None:
            partial_subtotal = sef_points

    coverage_complete = len(set_vals) >= required and len(sef_vals) >= required
    if policy == CRITERION_A_POLICY_FLEXIBLE:
        coverage_complete = max(len(set_vals), len(sef_vals)) >= required

    calculation_available = set_points is not None or sef_points is not None
    return {
        "calculationPolicy": policy,
        "setPoints": set_points,
        "sefPoints": sef_points,
        "partialSubtotal": partial_subtotal,
        "criterionAPoints": criterion_a_points,
        "combinedComplete": combined_complete,
        "coverageComplete": coverage_complete,
        "incomplete": not coverage_complete,
        "calculationUnavailable": not calculation_available,
        "setAverage": set_avg,
        "sefAverage": sef_avg,
        "setCount": len(set_vals),
        "sefCount": len(sef_vals),
        "requiredSlots": required,
    }


def compute_criterion_a_from_records(
    records: list[SetSefSemesterRecord],
    *,
    verified_only: bool = False,
    config_version: str | None = None,
    catalog: dict | None = None,
    max_semester_slots: int | None = None,
    slot_window_blocked: bool = False,
    window_needs_selection: bool = False,
    window_message: str | None = None,
) -> dict[str, Any]:
    if catalog is None:
        if config_version or has_app_context():
            catalog = get_catalog_by_version_label(config_version)
        else:
            catalog = None
    params = criterion_a_calculation_params(catalog)
    policy_error = params.get("calculation_policy_error")
    if policy_error:
        return _configuration_error_result(
            policy_error,
            config_version=config_version,
            catalog=catalog,
            params=params,
        )

    policy = params["calculation_policy"]
    set_factor = params["set_factor"]
    sef_factor = params["sef_factor"]
    max_slots = max_semester_slots if max_semester_slots is not None else params.get("required_slots", MAX_SEMESTER_SLOTS)
    set_max = params["set_max"]
    sef_max = params["sef_max"]
    crit_max = params["criterion_a_max"]

    active = [r for r in records if r.superseded_by_id is None]
    distinct_slots = len(active)

    if slot_window_blocked or window_needs_selection:
        return _empty_result(
            config_version=config_version,
            catalog=catalog,
            policy=policy,
            max_slots=max_slots,
            set_factor=set_factor,
            sef_factor=sef_factor,
            crit_max=crit_max,
            distinct_slots=distinct_slots,
            window_message=window_message
            or (
                f"More than {max_slots} semester slots; select up to {max_slots} for scoring."
                if window_needs_selection
                else f"More than {max_slots} semester slots; resolve assessment window."
            ),
            window_needs_selection=window_needs_selection,
        )

    if verified_only:
        set_vals = [_approved_set_rating(r) for r in active]
        sef_vals = [_approved_sef_rating(r) for r in active]
    else:
        set_vals = [_estimated_set(r) for r in active]
        sef_vals = [_estimated_sef(r) for r in active]

    set_available = [v for v in set_vals if v is not None]
    sef_available = [v for v in sef_vals if v is not None]

    if policy == CRITERION_A_POLICY_FLEXIBLE:
        return _build_flexible_result(
            policy=policy,
            set_available=set_available,
            sef_available=sef_available,
            distinct_slots=distinct_slots,
            max_slots=max_slots,
            set_factor=set_factor,
            sef_factor=sef_factor,
            set_max=set_max,
            sef_max=sef_max,
            crit_max=crit_max,
            config_version=config_version,
            catalog=catalog,
        )

    return _build_legacy_result(
        policy=policy,
        set_available=set_available,
        sef_available=sef_available,
        distinct_slots=distinct_slots,
        max_slots=max_slots,
        set_factor=set_factor,
        sef_factor=sef_factor,
        set_max=set_max,
        sef_max=sef_max,
        crit_max=crit_max,
        config_version=config_version,
        catalog=catalog,
    )


def _build_flexible_result(
    *,
    policy,
    set_available,
    sef_available,
    distinct_slots,
    max_slots,
    set_factor,
    sef_factor,
    set_max,
    sef_max,
    crit_max,
    config_version,
    catalog,
) -> dict[str, Any]:
    set_points, set_avg = _flexible_component_score(set_available, set_factor, set_max)
    sef_points, sef_avg = _flexible_component_score(sef_available, sef_factor, sef_max)

    combined_complete = set_points is not None and sef_points is not None
    criterion_a_points = None
    partial_subtotal = None
    if combined_complete:
        criterion_a_points = round(min(set_points + sef_points, crit_max), 4)
    elif set_points is not None:
        partial_subtotal = set_points
    elif sef_points is not None:
        partial_subtotal = sef_points

    coverage_complete = distinct_slots >= max_slots
    calculation_available = set_points is not None or sef_points is not None

    coverage_parts = []
    if not coverage_complete:
        coverage_parts.append(f"{distinct_slots} of {max_slots} semester slots in window")
    if not combined_complete and calculation_available:
        if set_points is None:
            coverage_parts.append("SEF component unavailable for combined total")
        if sef_points is None:
            coverage_parts.append("SET component unavailable for combined total")

    incomplete_reason = "; ".join(coverage_parts) if coverage_parts else None

    return {
        "configVersion": config_version or (catalog or {}).get("version") or "",
        "calculationPolicy": policy,
        "maxSemesterSlots": max_slots,
        "slotCount": distinct_slots,
        "setCount": len(set_available),
        "sefCount": len(sef_available),
        "setDenominator": len(set_available),
        "sefDenominator": len(sef_available),
        "requiredSlots": max_slots,
        "setComplete": set_points is not None,
        "sefComplete": sef_points is not None,
        "combinedComplete": combined_complete,
        "coverageComplete": coverage_complete,
        "setAverage": set_avg,
        "sefAverage": sef_avg,
        "setPoints": set_points,
        "sefPoints": sef_points,
        "partialSubtotal": partial_subtotal,
        "criterionAPoints": criterion_a_points,
        "incomplete": not coverage_complete,
        "calculationUnavailable": not calculation_available,
        "incompleteReason": incomplete_reason,
        "coverageNote": (
            "Based on available semesters; may change as ratings are added."
            if calculation_available and not coverage_complete
            else None
        ),
        "formula": _flexible_formula(set_factor, sef_factor, crit_max),
        "maxima": {"set": set_max, "sef": sef_max, "criterionA": crit_max},
        "parametersSource": "catalog" if catalog else "defaults",
    }


def _build_legacy_result(
    *,
    policy,
    set_available,
    sef_available,
    distinct_slots,
    max_slots,
    set_factor,
    sef_factor,
    set_max,
    sef_max,
    crit_max,
    config_version,
    catalog,
) -> dict[str, Any]:
    set_points, set_avg = _legacy_component_score(set_available, set_factor, set_max, max_slots)
    sef_points, sef_avg = _legacy_component_score(sef_available, sef_factor, sef_max, max_slots)

    combined_complete = set_points is not None and sef_points is not None
    criterion_a_points = round(min(set_points + sef_points, crit_max), 4) if combined_complete else None

    coverage_complete = distinct_slots >= max_slots and combined_complete
    calculation_available = combined_complete

    coverage_parts = []
    if distinct_slots < max_slots:
        coverage_parts.append(f"{distinct_slots} of {max_slots} semester slots in window")
    if len(set_available) < max_slots:
        coverage_parts.append(f"SET: {len(set_available)} of {max_slots} required ratings")
    if len(sef_available) < max_slots:
        coverage_parts.append(f"SEF: {len(sef_available)} of {max_slots} required ratings")

    incomplete_reason = "; ".join(coverage_parts) if coverage_parts else None

    return {
        "configVersion": config_version or (catalog or {}).get("version") or "",
        "calculationPolicy": policy,
        "maxSemesterSlots": max_slots,
        "slotCount": distinct_slots,
        "setCount": len(set_available),
        "sefCount": len(sef_available),
        "setDenominator": max_slots,
        "sefDenominator": max_slots,
        "requiredSlots": max_slots,
        "setComplete": set_points is not None,
        "sefComplete": sef_points is not None,
        "combinedComplete": combined_complete,
        "coverageComplete": coverage_complete,
        "setAverage": set_avg,
        "sefAverage": sef_avg,
        "setPoints": set_points,
        "sefPoints": sef_points,
        "partialSubtotal": None,
        "criterionAPoints": criterion_a_points,
        "incomplete": not coverage_complete,
        "calculationUnavailable": not calculation_available,
        "incompleteReason": incomplete_reason,
        "coverageNote": None,
        "formula": _legacy_formula(set_factor, sef_factor, crit_max, max_slots),
        "maxima": {"set": set_max, "sef": sef_max, "criterionA": crit_max},
        "parametersSource": "catalog" if catalog else "defaults",
    }


def _flexible_formula(set_factor, sef_factor, crit_max):
    return {
        "set": f"(average of available SET ratings) × {set_factor}",
        "sef": f"(average of available SEF ratings) × {sef_factor}",
        "criterionA": f"SET points + SEF points when both available (max {crit_max})",
        "policy": "Average available eligible ratings, maximum six semester slots",
    }


def _legacy_formula(set_factor, sef_factor, crit_max, required):
    return {
        "set": f"(sum of {required} SET ratings ÷ {required}) × {set_factor}",
        "sef": f"(sum of {required} SEF ratings ÷ {required}) × {sef_factor}",
        "criterionA": f"SET points + SEF points when both components have {required} ratings (max {crit_max})",
        "policy": f"Legacy: require {required} semester ratings per component (fixed denominator)",
    }


def _configuration_error_result(message: str, *, config_version, catalog, params) -> dict[str, Any]:
    max_slots = params.get("required_slots", MAX_SEMESTER_SLOTS)
    return {
        "configVersion": config_version or (catalog or {}).get("version") or "",
        "calculationPolicy": None,
        "configurationError": True,
        "configurationErrorMessage": message,
        "maxSemesterSlots": max_slots,
        "slotCount": 0,
        "setCount": 0,
        "sefCount": 0,
        "setComplete": False,
        "sefComplete": False,
        "combinedComplete": False,
        "coverageComplete": False,
        "setPoints": None,
        "sefPoints": None,
        "partialSubtotal": None,
        "criterionAPoints": None,
        "incomplete": True,
        "calculationUnavailable": True,
        "incompleteReason": message,
        "parametersSource": "catalog" if catalog else "defaults",
    }


def _empty_result(
    *,
    config_version,
    catalog,
    policy,
    max_slots,
    set_factor,
    sef_factor,
    crit_max,
    distinct_slots,
    window_message,
    window_needs_selection=False,
) -> dict[str, Any]:
    formula = _flexible_formula(set_factor, sef_factor, crit_max)
    if policy == CRITERION_A_POLICY_LEGACY:
        formula = _legacy_formula(set_factor, sef_factor, crit_max, max_slots)
    return {
        "configVersion": config_version or (catalog or {}).get("version") or "",
        "calculationPolicy": policy,
        "maxSemesterSlots": max_slots,
        "slotCount": distinct_slots,
        "setCount": 0,
        "sefCount": 0,
        "setDenominator": 0,
        "sefDenominator": 0,
        "requiredSlots": max_slots,
        "setComplete": False,
        "sefComplete": False,
        "combinedComplete": False,
        "coverageComplete": False,
        "setAverage": None,
        "sefAverage": None,
        "setPoints": None,
        "sefPoints": None,
        "partialSubtotal": None,
        "criterionAPoints": None,
        "incomplete": True,
        "calculationUnavailable": True,
        "incompleteReason": window_message,
        "coverageNote": None,
        "windowBlocked": not window_needs_selection,
        "windowNeedsSelection": window_needs_selection,
        "formula": formula,
        "maxima": {"set": 36.0, "sef": 24.0, "criterionA": crit_max},
        "parametersSource": "catalog" if catalog else "defaults",
    }
