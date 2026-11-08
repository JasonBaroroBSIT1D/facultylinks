from flask import g

from app.extensions import db
from app.models import AppSetting

INSTITUTION_KEY = "institution_config"
CATALOG_DRAFT_KEY = "catalog_draft"
CATALOG_PUBLISHED_KEY = "catalog_published"
ASSESSMENT_CONFIG_KEY = "assessment_config_meta"

_CACHE_ATTR = "_app_settings_cache"


def _load_settings_cache() -> dict[str, object]:
    cached = getattr(g, _CACHE_ATTR, None)
    if cached is not None:
        return cached
    rows = db.session.execute(db.select(AppSetting)).scalars().all()
    cached = {row.key: row.value for row in rows}
    setattr(g, _CACHE_ATTR, cached)
    return cached


def _invalidate_settings_cache() -> None:
    if hasattr(g, _CACHE_ATTR):
        delattr(g, _CACHE_ATTR)


def get_json(key: str, default=None):
    cache = _load_settings_cache()
    if key in cache:
        return cache[key]
    return default


def set_json(key: str, value) -> None:
    row = db.session.get(AppSetting, key)
    if not row:
        row = AppSetting(key=key, value=value)
        db.session.add(row)
    else:
        row.value = value
    db.session.commit()
    _invalidate_settings_cache()
