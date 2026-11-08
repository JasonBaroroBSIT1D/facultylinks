from __future__ import annotations

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


def find_indicator(catalog: dict, indicator_id: str) -> dict | None:
    for kra in catalog.get("kras", []):
        for crit in kra.get("criteria", []):
            for ind in crit.get("indicators", []):
                if ind.get("id") == indicator_id:
                    return {"kra": kra, "criterion": crit, "indicator": ind}
    return None


def validate_indicator_kra(catalog: dict, indicator_id: str, kra_id: str) -> dict:
    if not indicator_id or not kra_id:
        raise CatalogValidationError("indicatorId and kraId are required.")
    found = find_indicator(catalog, indicator_id)
    if not found:
        raise CatalogValidationError("Indicator is not in the published configuration.")
    if found["kra"].get("id") != kra_id:
        raise CatalogValidationError("Indicator does not belong to the supplied KRA.")
    return found
