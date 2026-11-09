from __future__ import annotations

from datetime import datetime, timezone

from app.services.settings_store import ASSESSMENT_CONFIG_KEY, CATALOG_PUBLISHED_KEY, get_json


class CatalogValidationError(ValueError):
    pass


def get_assessment_config() -> dict:
    return get_json(ASSESSMENT_CONFIG_KEY, {"activePublishedId": None, "versions": [], "draftId": None, "previewDraft": False}) or {}


def filter_config_for_non_admin(cfg: dict | None) -> dict:
    if not cfg:
        return {"activePublishedId": None, "versions": [], "draftId": None, "previewDraft": False}
    versions = [v for v in cfg.get("versions", []) if v.get("status") == "published"]
    active = cfg.get("activePublishedId")
    if active and not any(v.get("id") == active for v in versions):
        active = versions[-1]["id"] if versions else None
    return {
        "activePublishedId": active,
        "draftId": None,
        "previewDraft": False,
        "versions": versions,
    }


def get_published_catalog_and_weights() -> tuple[dict | None, dict | None]:
    cfg = get_assessment_config()
    active_id = cfg.get("activePublishedId")
    version = None
    for v in cfg.get("versions", []):
        if v.get("id") == active_id and v.get("status") == "published":
            version = v
            break
    if not version:
        for v in cfg.get("versions", []):
            if v.get("status") == "published":
                version = v
                break
    if version:
        return version.get("catalog"), version.get("kraWeights")
    pub = get_json(CATALOG_PUBLISHED_KEY)
    if isinstance(pub, dict) and pub.get("kras"):
        return pub, pub.get("kraWeights")
    return None, None


def _kra_i_criterion_a(catalog: dict) -> tuple[dict | None, dict | None]:
    for kra in catalog.get("kras", []):
        if kra.get("id") == "kra-I":
            for crit in kra.get("criteria", []):
                if crit.get("id") == "kra-I-A":
                    return kra, crit
    return None, None


def find_indicator(catalog: dict, indicator_id: str) -> dict | None:
    for kra in catalog.get("kras", []):
        for crit in kra.get("criteria", []):
            for ind in crit.get("indicators", []):
                if ind.get("id") == indicator_id:
                    return {"kra": kra, "criterion": crit, "indicator": ind}
    for alias in catalog.get("documentIntakeAliases") or []:
        if not isinstance(alias, dict) or alias.get("id") != indicator_id:
            continue
        kra, crit = _kra_i_criterion_a(catalog)
        if kra and crit:
            return {"kra": kra, "criterion": crit, "indicator": alias, "intakeOnly": True}
    return None


SET_SEF_UNIFIED_INDICATOR = "kra-I-A-setsef-eval"
SET_SEF_COMBINED_INDICATOR = "kra-I-A-setsef-combined"
SET_SEF_SET_PDF_INDICATOR = "kra-I-A-set-pdf"
SET_SEF_SEF_PDF_INDICATOR = "kra-I-A-sef-pdf"

SET_SEF_PDF_INDICATORS: dict[str, str] = {
    SET_SEF_UNIFIED_INDICATOR: "set_sef_unified",
    SET_SEF_COMBINED_INDICATOR: "set_sef_combined",
    SET_SEF_SET_PDF_INDICATOR: "set_sef_set_only",
    SET_SEF_SEF_PDF_INDICATOR: "set_sef_sef_only",
}

SET_SEF_OCR_INDICATOR_IDS = frozenset(SET_SEF_PDF_INDICATORS.keys())

CRITERION_A_POLICY_FLEXIBLE = "average_available_max_six"
CRITERION_A_POLICY_LEGACY = "legacy_six_semester_required"

_LEGACY_POLICY_ALIASES = frozenset(
    {
        CRITERION_A_POLICY_LEGACY,
        "fixed_six_semester_average",
        "six_semester_average",
        "six_semester_required",
    }
)


def normalize_criterion_a_policy(raw: str | None) -> str | None:
    """Return canonical policy id, or None if unknown."""
    if not raw:
        return CRITERION_A_POLICY_LEGACY
    key = str(raw).strip()
    if key == CRITERION_A_POLICY_FLEXIBLE:
        return CRITERION_A_POLICY_FLEXIBLE
    if key in _LEGACY_POLICY_ALIASES:
        return CRITERION_A_POLICY_LEGACY
    return None


def set_scoring_window_semester_keys(data: dict, semester_keys: list[str], *, actor_email: str) -> dict:
    """Persist explicit semester selection (max six); does not delete uploads."""
    from datetime import datetime, timezone

    keys = list(dict.fromkeys(str(k) for k in (semester_keys or []) if k))
    if len(keys) > 6:
        raise CatalogValidationError("At most six semester keys may be selected for scoring.")
    window = dict(data.get("setSefScoringWindow") or {})
    history = list(window.get("history") or [])
    history.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "semesterKeys": keys,
            "actor": actor_email,
        }
    )
    data = {
        **data,
        "setSefScoringWindow": {
            **window,
            "semesterKeys": keys,
            "history": history[-20:],
        },
    }
    return data


def scoring_window_semester_keys(assessment_data: dict | None) -> list[str] | None:
    """Explicit admin/faculty pick of up to six semester keys when uploads exceed the window."""
    if not assessment_data:
        return None
    window = assessment_data.get("setSefScoringWindow") or {}
    keys = window.get("semesterKeys")
    if not keys:
        return None
    if not isinstance(keys, list):
        return None
    return [str(k) for k in keys if k]

def is_kra_i_achievement_indicator(indicator_id: str | None) -> bool:
    """Achievement-backed evidence (KRA I B/C and KRA II A/B/C) — scored on parent achievement."""
    if not indicator_id:
        return False
    if indicator_id.startswith("kra-I-B") or indicator_id.startswith("kra-I-C"):
        return True
    return indicator_id.startswith("kra-II-") or indicator_id.startswith("kra-III-")


def is_set_sef_pdf_upload(indicator_id: str | None, kra_id: str | None) -> bool:
    """Faculty uploads send parent KRA id ``kra-I`` (not criterion ``kra-I-A``)."""
    return bool(kra_id == "kra-I" and indicator_id in SET_SEF_PDF_INDICATORS)


def document_kind_for_set_sef_indicator(indicator_id: str) -> str | None:
    return SET_SEF_PDF_INDICATORS.get(indicator_id)


def get_version_record(version_id: str) -> dict | None:
    if not version_id:
        return None
    for v in get_assessment_config().get("versions", []):
        if v.get("id") == version_id:
            return v
    return None


def get_catalog_by_version_label(version_label: str | None) -> dict | None:
    """Resolve catalog by published version id or catalog.version string."""
    if not version_label:
        catalog, _ = get_published_catalog_and_weights()
        return catalog
    for v in get_assessment_config().get("versions", []):
        if v.get("id") == version_label:
            return v.get("catalog")
        cat = v.get("catalog") or {}
        if cat.get("version") == version_label:
            return cat
    pub = get_json(CATALOG_PUBLISHED_KEY)
    if isinstance(pub, dict) and pub.get("version") == version_label:
        return pub
    catalog, _ = get_published_catalog_and_weights()
    return catalog


def get_catalog_for_assessment(assessment_data: dict | None) -> tuple[dict | None, dict | None]:
    """Pinned faculty assessments keep their assigned published rule version."""
    pinned = (assessment_data or {}).get("configVersionId")
    if pinned:
        rec = get_version_record(pinned)
        if rec and rec.get("status") == "published" and rec.get("catalog"):
            return rec.get("catalog"), rec.get("kraWeights")
    return get_published_catalog_and_weights()


def criterion_a_calculation_params(catalog: dict | None) -> dict:
    """SET/SEF factors, caps, and semester slots from published catalog indicators."""
    defaults = {
        "set_factor": 0.36,
        "sef_factor": 0.24,
        "required_slots": 6,
        "max_semester_slots": 6,
        "calculation_policy": CRITERION_A_POLICY_LEGACY,
        "set_max": 36.0,
        "sef_max": 24.0,
        "criterion_a_max": 60.0,
        "calculation_policy_error": None,
    }
    if not catalog:
        return defaults
    _kra, crit_a = _kra_i_criterion_a(catalog)
    if not crit_a:
        return defaults
    crit_cap = crit_a.get("capMaxPoints") or crit_a.get("maxPoints")
    if crit_cap is not None:
        defaults["criterion_a_max"] = float(crit_cap)

    set_ind = None
    sef_ind = None
    for ind in crit_a.get("indicators", []):
        if ind.get("id") == "kra-I-A-set" or ind.get("subType") == "SET":
            set_ind = ind
        if ind.get("id") == "kra-I-A-sef" or ind.get("subType") == "SEF":
            sef_ind = ind
    if set_ind:
        calc = set_ind.get("calculation") or {}
        if calc.get("factor") is not None:
            defaults["set_factor"] = float(calc["factor"])
        if calc.get("semesterCount") is not None:
            defaults["required_slots"] = int(calc["semesterCount"])
            defaults["max_semester_slots"] = int(calc["semesterCount"])
        if set_ind.get("maxPoints") is not None:
            defaults["set_max"] = float(set_ind["maxPoints"])
    if sef_ind:
        calc = sef_ind.get("calculation") or {}
        if calc.get("factor") is not None:
            defaults["sef_factor"] = float(calc["factor"])
        if sef_ind.get("maxPoints") is not None:
            defaults["sef_max"] = float(sef_ind["maxPoints"])

    set_policy_raw = (set_ind.get("calculation") or {}).get("policy") if set_ind else None
    sef_policy_raw = (sef_ind.get("calculation") or {}).get("policy") if sef_ind else None
    set_policy = normalize_criterion_a_policy(set_policy_raw) if set_policy_raw else None
    sef_policy = normalize_criterion_a_policy(sef_policy_raw) if sef_policy_raw else None
    if set_policy_raw and set_policy is None:
        defaults["calculation_policy_error"] = f"Unknown SET calculation policy: {set_policy_raw!r}"
    elif sef_policy_raw and sef_policy is None:
        defaults["calculation_policy_error"] = f"Unknown SEF calculation policy: {sef_policy_raw!r}"
    elif set_policy and sef_policy and set_policy != sef_policy:
        defaults["calculation_policy_error"] = (
            f"Mismatched SET/SEF policies ({set_policy_raw!r} vs {sef_policy_raw!r})."
        )
    elif set_policy:
        defaults["calculation_policy"] = set_policy
    elif sef_policy:
        defaults["calculation_policy"] = sef_policy
    return defaults


def pin_assessment_config_version_if_needed(user_id: int, data: dict) -> dict:
    """Set configVersionId once when faculty starts evidence (no silent upgrades on publish)."""
    if data.get("configVersionId"):
        return data
    active = get_assessment_config().get("activePublishedId")
    if not active:
        return data
    return {**data, "configVersionId": active}


def reassign_assessment_config_version(
    data: dict,
    *,
    new_version_id: str,
    actor_email: str,
    reason: str = "",
) -> dict:
    """Explicit admin action to move a faculty assessment to a different published rule version."""
    if not new_version_id:
        raise CatalogValidationError("configVersionId is required.")
    rec = get_version_record(new_version_id)
    if not rec or rec.get("status") != "published" or not rec.get("catalog"):
        raise CatalogValidationError("Target version must be a published configuration with a catalog.")
    prev = data.get("configVersionId")
    if prev == new_version_id:
        return data
    history = list(data.get("configVersionHistory") or [])
    history.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "from": prev,
            "to": new_version_id,
            "actor": actor_email,
            "reason": reason or "Admin reassigned scoring rules",
        }
    )
    return {**data, "configVersionId": new_version_id, "configVersionHistory": history}


def validate_indicator_kra(catalog: dict, indicator_id: str, kra_id: str) -> dict:
    if not indicator_id or not kra_id:
        raise CatalogValidationError("indicatorId and kraId are required.")
    found = find_indicator(catalog, indicator_id)
    if not found:
        raise CatalogValidationError("Indicator is not in the published configuration.")
    parent_kra = found["kra"].get("id")
    if parent_kra != kra_id:
        crit = found.get("criterion") or {}
        crit_id = crit.get("id")
        if kra_id and crit_id and kra_id == crit_id:
            raise CatalogValidationError(
                f"Supplied kraId must be parent KRA {parent_kra!r}, not criterion {crit_id!r}."
            )
        if kra_id and kra_id.startswith("kra-") and kra_id.count("-") >= 2 and parent_kra:
            raise CatalogValidationError(
                f"Indicator {indicator_id!r} belongs to {parent_kra!r}, not {kra_id!r}."
            )
        raise CatalogValidationError("Indicator does not belong to the supplied KRA.")
    return found
