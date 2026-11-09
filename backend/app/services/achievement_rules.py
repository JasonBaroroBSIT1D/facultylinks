"""JC3 workbook rule resolution for self-assessed achievements (KRA I B/C and similar indicators)."""

from __future__ import annotations

from typing import Any

from app.services.catalog import CatalogValidationError, find_indicator


KRA_I_BC_CRITERIA = frozenset({"kra-I-B", "kra-I-C"})
KRA_II_CRITERIA = frozenset({"kra-II-A", "kra-II-B", "kra-II-C"})
KRA_III_CRITERIA = frozenset({"kra-III-A", "kra-III-B", "kra-III-C", "kra-III-D"})
KRA_IV_CRITERIA = frozenset({"kra-IV-A", "kra-IV-B", "kra-IV-C", "kra-IV-D"})

# Workbook A23 / B23 — used when published catalog still has `pending` for kra-III-D-1 only.
WORKBOOK_KRA_III_D_DESIGNATION_MATRIX = {
    "institutional": {
        "president": 20,
        "vice_president": 15,
        "chancellor": 10,
        "vice_chancellor": 8,
        "campus_director": 8,
        "faculty_trustee": 8,
        "office_director": 6,
        "university_secretary": 6,
        "project_head": 4,
        "inst_committee_chair": 3,
        "inst_committee_member": 2,
        "inst_coordinator": 2,
    },
    "college_department": {
        "dean": 6,
        "associate_dean": 5,
        "college_secretary": 3,
        "department_head": 4,
        "program_chair": 3,
        "dept_committee_chair": 2,
        "dept_committee_member": 1,
        "dept_coordinator": 1,
    },
}

KRA_III_C_LINKED_ISR = {
    "indicatorId": "kra-III-B-2-1",
    "linkField": "linkedIsrProjectId",
}

KRA_IV_B1_QUALIFICATION_OPTIONS = {
    "post_master_diploma": 10,
    "post_doctorate_diploma": 10,
    "additional_masters": 20,
    "doctorate": 40,
}

KRA_IV_B2_ATTENDANCE_OPTIONS = {"local": 1, "international": 2}

KRA_IV_C1_AWARD_OPTIONS = {"institutional": 2, "local_regional": 3, "national": 4}

KRA_IV_D1_ACADEMIC_RATES = {
    "president": 5,
    "vp_dean_director": 4,
    "dept_program_head": 3,
    "faculty_member": 2,
}

KRA_IV_D2_INDUSTRY_RATES = {
    "managerial_supervisory": 4,
    "technical_skilled": 3,
    "support_admin": 2,
}

DEFAULT_KRA_IV_SCORING_POLICY = {
    "coreCriteria": ["kra-IV-A", "kra-IV-B", "kra-IV-C"],
    "additionalCriteria": ["kra-IV-D"],
    "coreMaxSum": 100,
    "additionalMax": 20,
    "kraListedMax": 100,
    "applyKraEnvelopeCap": False,
    "unresolvedNote": (
        "Workbook B5 lists KRA max 100 while F5 sums Criteria A+B+C+D (up to 120 raw) before ×10%. "
        "Confirm whether D stacks beyond the 100-point envelope."
    ),
}


def resolve_achievement_criterion_id(achievement: dict) -> str | None:
    """Stable criterion id for filtering; falls back to indicator id prefix for legacy rows."""
    cid = (achievement.get("criterionId") or "").strip()
    if cid:
        return cid
    ind = (achievement.get("indicatorId") or "").strip()
    if ind.startswith("kra-I-B"):
        return "kra-I-B"
    if ind.startswith("kra-I-C"):
        return "kra-I-C"
    if ind.startswith("kra-II-A"):
        return "kra-II-A"
    if ind.startswith("kra-II-B"):
        return "kra-II-B"
    if ind.startswith("kra-II-C"):
        return "kra-II-C"
    if ind.startswith("kra-III-A"):
        return "kra-III-A"
    if ind.startswith("kra-III-B"):
        return "kra-III-B"
    if ind.startswith("kra-III-C"):
        return "kra-III-C"
    if ind.startswith("kra-III-D"):
        return "kra-III-D"
    if ind.startswith("kra-IV-A"):
        return "kra-IV-A"
    if ind.startswith("kra-IV-B"):
        return "kra-IV-B"
    if ind.startswith("kra-IV-C"):
        return "kra-IV-C"
    if ind.startswith("kra-IV-D"):
        return "kra-IV-D"
    return None


def _achievement_by_id(context: dict | None, ach_id: str | None) -> dict | None:
    if not ach_id or not context:
        return None
    for ach in context.get("achievements") or []:
        if ach.get("id") == ach_id and is_active_achievement(ach):
            return ach
    return None


def _tier_from_income_amount(amount: float, tiers: list[dict]) -> dict | None:
    for tier in tiers:
        if not tier.get("resolved", True):
            continue
        mn = tier.get("minAmount")
        mx = tier.get("maxAmount")
        if mn is not None and amount < float(mn):
            continue
        if mx is not None and amount > float(mx):
            continue
        if mn is None and mx is not None and amount <= float(mx):
            return tier
        if mn is not None and mx is None and amount >= float(mn):
            return tier
        if mn is not None and mx is not None and float(mn) <= amount <= float(mx):
            return tier
    return None


def _income_tier_unresolved_band_note() -> str:
    return (
        "Income amount falls in the workbook-ambiguous band (around 500,001–6,000,000). "
        "Tier t3 is not confirmed in the published catalog — resolve in Admin before claiming."
    )


def _patent_stage_map(indicator: dict) -> dict:
    calc = indicator.get("calculation") or {}
    stages = calc.get("stages")
    if isinstance(stages, dict) and stages:
        return stages
    pts = calc.get("points") if calc.get("kind") == "structured_points" else None
    if isinstance(pts, dict) and pts:
        if {str(k).upper() for k in pts}.issubset({"A", "P", "G"}):
            return {str(k).upper(): v for k, v in pts.items()}
    pts = indicator.get("points")
    if isinstance(pts, dict) and {str(k).upper() for k in pts}.issubset({"A", "P", "G"}) and pts:
        return {str(k).upper(): v for k, v in pts.items()}
    if isinstance(pts, dict) and any(str(k).upper() in ("A", "P", "G") for k in pts):
        return {str(k).upper(): v for k, v in pts.items() if str(k).upper() in ("A", "P", "G")}
    return {}


_SCOPE_KEYS = frozenset({"local", "international"})
_JUDGE_CANONICAL = {
    "researchaward": "research_award",
    "research_award": "research_award",
    "academiccompetition": "academic_competition",
    "academic_competition": "academic_competition",
}
_EXTENSION_KEYS = frozenset({"lead", "participant"})


def _indicator_id(indicator: dict) -> str:
    return (indicator.get("id") or "").strip()


def _legacy_points(indicator: dict) -> dict:
    calc = indicator.get("calculation") or {}
    pts = calc.get("points") if calc.get("kind") == "structured_points" else None
    if isinstance(pts, dict) and pts:
        return pts
    pts = indicator.get("points")
    return pts if isinstance(pts, dict) else {}


def _tiered_options_map(indicator: dict) -> dict:
    calc = indicator.get("calculation") or {}
    opts = calc.get("options")
    if isinstance(opts, dict) and opts:
        return opts
    if calc.get("kind") == "structured_points":
        pts = calc.get("points")
        if isinstance(pts, dict) and any(k in pts for k in ("local", "international", "new", "updated")):
            return pts
    pts = indicator.get("points")
    if isinstance(pts, dict) and any(k in pts for k in ("local", "international", "new", "updated")):
        return pts
    return {}


def _scope_options_map(indicator: dict) -> dict:
    pts = _legacy_points(indicator)
    if not pts:
        return {}
    out = {}
    for k, v in pts.items():
        lk = str(k).lower()
        if lk in _SCOPE_KEYS:
            out[lk] = v
    return out if out else {}


def _judge_options_map(indicator: dict) -> dict:
    pts = _legacy_points(indicator)
    if not pts:
        return {}
    out: dict = {}
    for k, v in pts.items():
        lk = str(k).lower().replace("-", "_")
        canon = _JUDGE_CANONICAL.get(lk.replace("_", "")) or _JUDGE_CANONICAL.get(lk)
        if canon:
            out[canon] = v
        elif lk in ("research_award", "academic_competition"):
            out[lk] = v
    return out


def _extension_options_map(indicator: dict) -> dict:
    pts = _legacy_points(indicator)
    if not pts:
        return {}
    return {k: pts[k] for k in _EXTENSION_KEYS if k in pts}


def _hourly_rates_map(indicator: dict) -> dict:
    calc = indicator.get("calculation") or {}
    rates = calc.get("rates")
    if isinstance(rates, dict) and rates:
        return rates
    ind_id = _indicator_id(indicator)
    pts = _legacy_points(indicator)
    if ind_id == "kra-III-B-1-5" or (
        ind_id.startswith("kra-III-") and pts.get("local") == 2 and pts.get("international") == 3 and ind_id.endswith("B-1-5")
    ):
        return {"local": float(pts["local"]), "international": float(pts["international"])}
    return {}


def _default_tier_field(indicator_id: str, kind: str) -> str | None:
    if indicator_id.startswith("kra-IV-"):
        if indicator_id == "kra-IV-B-1":
            return "qualificationType"
        if indicator_id == "kra-IV-B-2":
            return "attendanceScope"
        if indicator_id == "kra-IV-C-1":
            return "awardLevel"
        return None
    if not indicator_id.startswith("kra-III-"):
        return None
    if kind == "hourly_tier" or indicator_id == "kra-III-B-1-5":
        return "serviceScope"
    if indicator_id == "kra-III-B-1-2":
        return "judgeServiceType"
    if indicator_id == "kra-III-B-2-1":
        return "extensionRole"
    if indicator_id in ("kra-III-B-1-1", "kra-III-B-1-3"):
        return "serviceScope"
    return None


def _resolve_tier_option_key(tier_raw: str, options: dict) -> str | None:
    if not tier_raw:
        return None
    t = tier_raw.strip().lower().replace("-", "_")
    if t in options:
        return t
    compact = t.replace("_", "")
    for key in options:
        if str(key).lower().replace("_", "") == compact:
            return str(key)
    canon = _JUDGE_CANONICAL.get(compact) or _JUDGE_CANONICAL.get(t)
    if canon and canon in options:
        return canon
    return None


def _normalize_indicator_for_rules(indicator: dict) -> dict:
    """Align legacy structured_points / bare points objects with patent_stage and tiered_option."""
    ind = dict(indicator)
    calc = dict(ind.get("calculation") or {})
    kind = calc.get("kind")
    ind_id = _indicator_id(ind)
    stages = _patent_stage_map(ind)
    if kind in (None, "pending", "structured_points") and stages:
        calc = {
            **calc,
            "kind": "patent_stage",
            "stages": stages,
            "notCumulative": calc.get("notCumulative", True),
        }
        kind = "patent_stage"

    hourly_rates = _hourly_rates_map(ind)
    if hourly_rates and not stages and (
        ind_id == "kra-III-B-1-5" or kind in (None, "pending", "structured_points", "tiered_option")
    ):
        calc = {
            **calc,
            "kind": "hourly_tier",
            "rates": hourly_rates,
            "tierField": calc.get("tierField") or _default_tier_field(ind_id, "hourly_tier") or "serviceScope",
            "hoursField": calc.get("hoursField") or "hours",
        }
        kind = "hourly_tier"

    judge_opts = _judge_options_map(ind)
    if kind in (None, "pending", "structured_points") and judge_opts and not stages:
        calc = {
            **calc,
            "kind": "tiered_option",
            "options": judge_opts,
            "tierField": "judgeServiceType",
        }
        kind = "tiered_option"

    ext_opts = _extension_options_map(ind)
    if kind in (None, "pending", "structured_points") and ext_opts and not stages:
        calc = {
            **calc,
            "kind": "tiered_option",
            "options": ext_opts,
            "tierField": "extensionRole",
            "aggregateCap": calc.get("aggregateCap") or ind.get("aggregateCap"),
        }
        kind = "tiered_option"

    scope_opts = _scope_options_map(ind)
    if kind in (None, "pending", "structured_points") and scope_opts and not stages and not judge_opts and not ext_opts:
        tier_field = (
            calc.get("tierField")
            or indicator.get("tierField")
            or _default_tier_field(ind_id, "tiered_option")
        )
        if ind_id.startswith("kra-III-") or tier_field:
            calc = {
                **calc,
                "kind": "tiered_option",
                "options": scope_opts,
                "tierField": tier_field or "serviceScope",
                "tierCaps": calc.get("tierCaps"),
            }
            kind = "tiered_option"

    opts = _tiered_options_map(ind)
    if kind in (None, "pending", "structured_points") and opts and not stages and kind != "tiered_option":
        calc = {
            **calc,
            "kind": "tiered_option",
            "options": opts,
            "tierCaps": calc.get("tierCaps"),
            "tierField": calc.get("tierField") or indicator.get("tierField") or _default_tier_field(ind_id, "tiered_option"),
        }
        kind = "tiered_option"

    if kind == "patent_stage" and not calc.get("stages"):
        calc["stages"] = stages
    if kind == "tiered_option":
        if not calc.get("options"):
            calc["options"] = opts or judge_opts or ext_opts or scope_opts
        if not calc.get("tierField"):
            calc["tierField"] = _default_tier_field(ind_id, kind) or indicator.get("tierField") or "tier"
        if calc.get("aggregateCap") is None and ind.get("aggregateCap") is not None:
            calc["aggregateCap"] = ind.get("aggregateCap")
    if kind == "hourly_tier" and not calc.get("rates"):
        calc["rates"] = hourly_rates

    if ind_id == "kra-III-C-1" and kind in (None, "pending"):
        if not calc.get("requiresLinkedAchievement"):
            calc = {**calc, "kind": "pending", "requiresLinkedAchievement": dict(KRA_III_C_LINKED_ISR)}
        kind = "pending"
    elif ind_id == "kra-III-D-1" and kind in (None, "pending") and not calc.get("matrix"):
        calc = {
            **calc,
            "kind": "designation_matrix",
            "levelField": "designationLevel",
            "roleField": "designationRole",
            "matrix": WORKBOOK_KRA_III_D_DESIGNATION_MATRIX,
        }
        kind = "designation_matrix"
    elif indicator.get("pointRule") == "designation_table" and not calc.get("matrix"):
        calc = {
            **calc,
            "kind": "designation_matrix",
            "levelField": calc.get("levelField") or "designationLevel",
            "roleField": calc.get("roleField") or "designationRole",
            "matrix": WORKBOOK_KRA_III_D_DESIGNATION_MATRIX,
        }
        kind = "designation_matrix"
    elif ind_id == "kra-IV-B-1" and kind in (None, "pending", "structured_points"):
        calc = {
            **calc,
            "kind": "tiered_option",
            "options": KRA_IV_B1_QUALIFICATION_OPTIONS,
            "tierField": "qualificationType",
        }
        kind = "tiered_option"
    elif ind_id == "kra-IV-B-2" and kind in (None, "pending", "structured_points"):
        calc = {
            **calc,
            "kind": "tiered_option",
            "options": KRA_IV_B2_ATTENDANCE_OPTIONS,
            "tierField": "attendanceScope",
            "aggregateCap": 10,
        }
        kind = "tiered_option"
    elif ind_id == "kra-IV-B-3-1" and kind in (None, "pending", "fixed_per_entry", "structured_points"):
        calc = {
            **calc,
            "kind": "fixed_per_entry",
            "maxPoints": 3,
            "aggregateGroup": "kra-IV-B-presentations",
            "aggregateCap": 10,
        }
        kind = "fixed_per_entry"
    elif ind_id == "kra-IV-B-3-2" and kind in (None, "pending", "fixed_per_entry", "structured_points"):
        calc = {
            **calc,
            "kind": "fixed_per_entry",
            "maxPoints": 5,
            "aggregateGroup": "kra-IV-B-presentations",
            "aggregateCap": 10,
        }
        kind = "fixed_per_entry"
    elif ind_id == "kra-IV-C-1" and kind in (None, "pending", "structured_points"):
        calc = {
            **calc,
            "kind": "tiered_option",
            "options": KRA_IV_C1_AWARD_OPTIONS,
            "tierField": "awardLevel",
        }
        kind = "tiered_option"
    elif ind_id == "kra-IV-D-1" and kind in (None, "pending", "structured_points"):
        calc = {
            **calc,
            "kind": "yearly_rate",
            "roleField": "academicServiceRole",
            "yearsField": "serviceYears",
            "requiresNewlyAppointed": True,
            "newlyAppointedField": "newlyAppointedEligible",
            "fractionalYearPolicy": "unresolved",
            "rates": KRA_IV_D1_ACADEMIC_RATES,
        }
        kind = "yearly_rate"
    elif ind_id == "kra-IV-D-2" and kind in (None, "pending", "structured_points"):
        calc = {
            **calc,
            "kind": "yearly_rate",
            "roleField": "industryCategory",
            "yearsField": "serviceYears",
            "requiresNewlyAppointed": True,
            "newlyAppointedField": "newlyAppointedEligible",
            "fractionalYearPolicy": "unresolved",
            "rates": KRA_IV_D2_INDUSTRY_RATES,
        }
        kind = "yearly_rate"

    ind["calculation"] = calc
    return ind


def _calculation_kind(indicator: dict) -> str:
    indicator = _normalize_indicator_for_rules(indicator)
    calc = indicator.get("calculation") or {}
    if calc.get("kind"):
        return str(calc["kind"])
    if indicator.get("matrix"):
        return "role_matrix"
    if indicator.get("maxPoints") is not None:
        return "fixed_per_entry"
    return "pending"


def expected_points_for_achievement(
    catalog: dict,
    indicator_id: str,
    fields: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return ruleExpectedPoints, permittedMax, and optional unresolved message."""
    found = find_indicator(catalog, indicator_id)
    if not found:
        raise CatalogValidationError("Indicator is not in the published configuration.")
    indicator = _normalize_indicator_for_rules(found["indicator"])
    kind = _calculation_kind(indicator)
    calc = indicator.get("calculation") or {}

    if kind == "pending":
        ind_id = _indicator_id(indicator)
        req = calc.get("requiresLinkedAchievement")
        is_client_satisfaction = ind_id == "kra-III-C-1" or bool(req)
        if not is_client_satisfaction:
            note = indicator.get("eligibilityUnresolved") or (
                "This indicator requires configuration review before points can be calculated."
            )
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": note,
                "ruleSummary": indicator.get("name") or indicator_id,
                "guidelinesNote": indicator.get("guidelinesRef"),
            }
        req = req or dict(KRA_III_C_LINKED_ISR)
        link_field = req.get("linkField") or "linkedIsrProjectId"
        required_ind = req.get("indicatorId") or "kra-III-B-2-1"
        link_id = (fields.get(link_field) or "").strip()
        link_msgs: list[str] = []
        if not link_id:
            link_msgs.append(f"Link the ISR extension project ({required_ind}) using {link_field}.")
        else:
            linked = _achievement_by_id(context, link_id)
            if not linked:
                link_msgs.append(f"Linked achievement {link_id!r} was not found in your assessment.")
            elif (linked.get("indicatorId") or "") != required_ind:
                link_msgs.append(
                    f"Linked achievement must be declared under {required_ind}, not {linked.get('indicatorId')}."
                )
        conv_note = indicator.get("eligibilityUnresolved") or (
            "Client satisfaction to points conversion is not defined in the published catalog "
            f"(external ref {indicator.get('externalFormulaRef') or 'n/a'})."
        )
        unresolved = " · ".join(link_msgs + [conv_note])
        return {
            "ruleExpectedPoints": None,
            "permittedMax": indicator.get("maxPoints"),
            "unresolved": unresolved,
            "ruleSummary": indicator.get("name") or "Client satisfaction (pending conversion)",
            "guidelinesNote": indicator.get("guidelinesRef"),
        }

    if kind == "role_matrix":
        matrix = calc.get("matrix") or indicator.get("matrix") or {}
        role = (fields.get("role") or "").strip().lower()
        thesis = (fields.get("thesisType") or fields.get("thesis_type") or "").strip()
        qty = max(1, int(fields.get("quantity") or 1))
        if not role or not thesis:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": "Select research role (adviser/panel) and thesis type.",
                "ruleSummary": "Matrix: adviser/panel × thesis type × quantity",
            }
        cell = (matrix.get(role) or {}).get(thesis)
        if cell is None:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": f"No workbook points for role={role!r}, thesisType={thesis!r}.",
                "ruleSummary": "Research advising matrix (workbook A22–B26)",
            }
        expected = float(cell) * qty
        ind_cap = float(indicator.get("maxPoints") or expected)
        expected = min(expected, ind_cap)
        return {
            "ruleExpectedPoints": round(expected, 4),
            "permittedMax": ind_cap,
            "unresolved": None,
            "ruleSummary": f"{cell} pts × {qty} ({role}/{thesis})",
        }

    if kind == "patent_stage":
        stages = calc.get("stages") or _patent_stage_map(indicator)
        stage = (fields.get("patentStage") or fields.get("patent_stage") or "").strip().upper()
        if not stage:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": max(stages.values()) if stages else None,
                "unresolved": "Select patent stage (A = Acceptance, P = Publication, G = Grant). One stage per achievement — stages do not accumulate.",
                "ruleSummary": "Patent stage points (workbook B16–B17)",
            }
        if stage not in stages:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": None,
                "unresolved": f"Unknown patent stage {stage!r}.",
                "ruleSummary": "Patent A/P/G",
            }
        pts = float(stages[stage])
        note = indicator.get("eligibilityUnresolved") or indicator.get("guidelinesRef")
        return {
            "ruleExpectedPoints": pts,
            "permittedMax": pts,
            "unresolved": None,
            "guidelinesNote": note,
            "ruleSummary": f"Stage {stage}: {pts} pts (not cumulative with other stages)",
        }

    if kind == "tiered_option":
        options = calc.get("options") or indicator.get("points") or {}
        tier_field = calc.get("tierField") or "tier"
        tier_raw = (fields.get(tier_field) or fields.get("tier") or "").strip()
        tier = _resolve_tier_option_key(tier_raw, options) if tier_raw else None
        if not tier:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": max(float(v) for v in options.values()) if options else None,
                "unresolved": f"Select {tier_field}.",
                "ruleSummary": indicator.get("name") or indicator_id,
            }
        if tier not in options:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": None,
                "unresolved": f"No workbook rate for {tier_field}={tier_raw!r}.",
                "ruleSummary": indicator.get("name") or indicator_id,
            }
        pts = float(options[tier])
        tier_caps = calc.get("tierCaps") or {}
        cap_note = f" (tier subcap {tier_caps[tier]} pts)" if tier in tier_caps else ""
        note = indicator.get("eligibilityUnresolved") or indicator.get("guidelinesRef")
        return {
            "ruleExpectedPoints": pts,
            "permittedMax": pts,
            "unresolved": None,
            "guidelinesNote": note,
            "ruleSummary": f"{tier}: {pts} pts{cap_note}",
        }

    if kind == "income_tier":
        tiers = calc.get("tiers") or []
        role_field = calc.get("roleField") or "incomeRole"
        tier_field = calc.get("tierField") or "incomeTier"
        amount_field = calc.get("amountField") or "incomeAmount"
        role = (fields.get(role_field) or fields.get("role") or "").strip().lower()
        if role not in ("lead", "contributor"):
            return {
                "ruleExpectedPoints": None,
                "permittedMax": max((t.get("lead") or 0) for t in tiers) if role == "lead" else None,
                "unresolved": "Select income role (lead or contributor).",
                "ruleSummary": "Income generation tiers (Section 31)",
            }
        tier_id = (fields.get(tier_field) or fields.get("tier") or "").strip().lower()
        tier_row = next((t for t in tiers if str(t.get("id", "")).lower() == tier_id), None)
        amount_raw = fields.get(amount_field) or fields.get("amount")
        amount = float(amount_raw) if amount_raw not in (None, "") else None
        if not tier_row and amount is not None:
            tier_row = _tier_from_income_amount(amount, tiers)
            if tier_row is None and 500_001 <= amount <= 6_000_000:
                return {
                    "ruleExpectedPoints": None,
                    "permittedMax": None,
                    "unresolved": _income_tier_unresolved_band_note(),
                    "ruleSummary": "Income amount tier",
                }
        if not tier_row:
            max_lead = max((float(t.get("lead") or 0) for t in tiers), default=None)
            max_contrib = max((float(t.get("contributor") or 0) for t in tiers), default=None)
            return {
                "ruleExpectedPoints": None,
                "permittedMax": max_lead if role == "lead" else max_contrib,
                "unresolved": "Select income tier or enter a resolvable income amount.",
                "ruleSummary": "Income generation tiers (Section 31)",
            }
        if not tier_row.get("resolved", True):
            return {
                "ruleExpectedPoints": None,
                "permittedMax": None,
                "unresolved": tier_row.get("workbookNote") or _income_tier_unresolved_band_note(),
                "ruleSummary": tier_row.get("label") or tier_id,
            }
        pts = float(tier_row.get("lead" if role == "lead" else "contributor") or 0)
        return {
            "ruleExpectedPoints": pts,
            "permittedMax": pts,
            "unresolved": None,
            "ruleSummary": f"{tier_row.get('label', tier_id)} · {role}: {pts} pts",
        }

    if kind == "hourly_tier":
        rates = calc.get("rates") or {}
        tier_field = calc.get("tierField") or "serviceScope"
        hours_field = calc.get("hoursField") or "hours"
        tier = (fields.get(tier_field) or fields.get("tier") or "").strip().lower()
        if not tier:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": max(float(v) for v in rates.values()) if rates else None,
                "unresolved": f"Select {tier_field} (local or international).",
                "ruleSummary": indicator.get("name") or indicator_id,
            }
        if tier not in rates:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": None,
                "unresolved": f"No hourly rate for {tier_field}={tier!r}.",
                "ruleSummary": indicator.get("name") or indicator_id,
            }
        try:
            hours = float(fields.get(hours_field) or fields.get("quantity") or 0)
        except (TypeError, ValueError):
            hours = 0.0
        if hours <= 0:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": None,
                "unresolved": "Enter hours (must be greater than zero).",
                "ruleSummary": f"{tier}: {rates[tier]} pts/hr",
            }
        rate = float(rates[tier])
        expected = round(rate * hours, 4)
        return {
            "ruleExpectedPoints": expected,
            "permittedMax": expected,
            "unresolved": None,
            "ruleSummary": f"{tier}: {rate} pts/hr × {hours} hr = {expected} pts",
        }

    if kind == "yearly_rate":
        rates = calc.get("rates") or {}
        role_field = calc.get("roleField") or "academicServiceRole"
        years_field = calc.get("yearsField") or "serviceYears"
        role = (fields.get(role_field) or fields.get("role") or "").strip().lower()
        years_raw = fields.get(years_field)
        newly_field = calc.get("newlyAppointedField") or "newlyAppointedEligible"
        if calc.get("requiresNewlyAppointed"):
            eligible = fields.get(newly_field)
            if eligible is not True and str(eligible).lower() not in ("true", "1", "yes"):
                note = indicator.get("eligibilityUnresolved") or (
                    "Criterion D applies only to newly appointed faculty — confirm eligibility before claiming points."
                )
                return {
                    "ruleExpectedPoints": None,
                    "permittedMax": indicator.get("maxPoints"),
                    "unresolved": note,
                    "ruleSummary": "Newly appointed faculty (Criterion D)",
                    "guidelinesNote": indicator.get("guidelinesRef"),
                }
        try:
            years = float(years_raw) if years_raw is not None and str(years_raw).strip() != "" else 0.0
        except (TypeError, ValueError):
            years = 0.0
        if years <= 0:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": "Enter years of service (must be greater than zero).",
                "ruleSummary": "Years × rate (Section 44)",
            }
        frac_policy = (calc.get("fractionalYearPolicy") or "whole_years_only").strip().lower()
        if frac_policy == "unresolved" and abs(years - round(years)) > 1e-6:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": calc.get("fractionalYearNote")
                or "Fractional-year scoring policy is not published — use whole years or wait for admin policy.",
                "ruleSummary": "Fractional years unresolved",
            }
        if frac_policy in ("whole_years_only", "unresolved"):
            years = float(int(round(years)))
        if not role:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": f"Select {role_field.replace('_', ' ')}.",
                "ruleSummary": "Years × rate (Section 44)",
            }
        rate = rates.get(role)
        if rate is None:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": f"No workbook rate for role/category {role!r}.",
                "ruleSummary": "Years × rate (Section 44)",
            }
        expected = round(float(rate) * years, 4)
        return {
            "ruleExpectedPoints": expected,
            "permittedMax": expected,
            "unresolved": None,
            "ruleSummary": f"{role}: {rate} pts/yr × {years} yr = {expected} pts",
            "guidelinesNote": indicator.get("guidelinesRef"),
        }

    if kind == "designation_matrix":
        matrix = calc.get("matrix") or {}
        level_field = calc.get("levelField") or "designationLevel"
        role_field = calc.get("roleField") or "designationRole"
        level = (fields.get(level_field) or "").strip().lower()
        role = (fields.get(role_field) or "").strip().lower()
        if not level:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": "Select designation level (institutional or college_department).",
                "ruleSummary": "Administrative designation matrix (A23)",
            }
        if not role:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": "Select administrative designation role.",
                "ruleSummary": "Administrative designation matrix (A23)",
            }
        cell = (matrix.get(level) or {}).get(role)
        if cell is None:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": indicator.get("maxPoints"),
                "unresolved": f"No workbook points for {level}/{role}.",
                "ruleSummary": "Administrative designation matrix (A23)",
            }
        pts = float(cell)
        note = indicator.get("eligibilityUnresolved")
        return {
            "ruleExpectedPoints": pts,
            "permittedMax": pts,
            "unresolved": None,
            "guidelinesNote": note,
            "ruleSummary": f"{level} · {role}: {pts} pts",
        }

    if kind == "structured_points":
        return {
            "ruleExpectedPoints": None,
            "permittedMax": None,
            "unresolved": "Structured points need patent stage or tier selection in the published catalog.",
            "ruleSummary": indicator.get("name") or indicator_id,
        }

    if kind in ("fixed_per_entry",):
        max_pts = indicator.get("maxPoints")
        if max_pts is None:
            max_pts = calc.get("maxPoints")
        contributor = indicator.get("contributorPoints")
        role = (fields.get("role") or "").strip().lower()
        per_service = calc.get("perService") or indicator.get("perService")
        qty = max(1, int(fields.get("quantity") or 1))

        permitted = float(max_pts) if max_pts is not None else None
        if contributor is not None and role:
            if role in ("contributor", "member", "co-developer"):
                permitted = float(contributor)
            elif role in ("lead", "sole", "primary", "lead_developer"):
                permitted = float(max_pts or contributor)

        if permitted is None:
            return {
                "ruleExpectedPoints": None,
                "permittedMax": None,
                "unresolved": "Indicator has no configured point maximum.",
                "ruleSummary": indicator.get("name") or indicator_id,
            }

        if per_service is not None:
            expected = min(float(per_service) * qty, permitted)
        else:
            expected = permitted

        return {
            "ruleExpectedPoints": round(expected, 4),
            "permittedMax": permitted,
            "unresolved": None,
            "ruleSummary": f"Up to {permitted} pts per achievement ({indicator.get('name', '')})",
        }

    return {
        "ruleExpectedPoints": None,
        "permittedMax": indicator.get("maxPoints"),
        "unresolved": f"Unsupported calculation kind {kind!r}.",
        "ruleSummary": kind,
    }


def validate_claimed_points(
    *,
    claimed: float | None,
    rule: dict[str, Any],
) -> str | None:
    if claimed is None:
        return "Claimed points are required."
    if claimed < 0:
        return "Claimed points cannot be negative."
    if rule.get("unresolved"):
        return rule["unresolved"]
    permitted = rule.get("permittedMax")
    if permitted is not None and claimed > float(permitted) + 1e-6:
        return f"Claim cannot exceed {permitted} points for this indicator."
    expected = rule.get("ruleExpectedPoints")
    if expected is not None and claimed > float(expected) + 1e-6:
        return f"Claim cannot exceed the rule result ({expected} pts)."
    return None


def achievement_dedupe_key(ach: dict[str, Any]) -> str:
    parts = [
        ach.get("indicatorId") or "",
        (ach.get("title") or "").strip().lower(),
        (ach.get("achievementDate") or ach.get("date") or "").strip(),
        (ach.get("role") or "").strip().lower(),
        (ach.get("thesisType") or "").strip(),
        (ach.get("academicPeriod") or "").strip(),
    ]
    return "|".join(parts)


def is_active_achievement(ach: dict[str, Any]) -> bool:
    return ach.get("reviewStatus") != "replaced" and not ach.get("supersededById")
