from app.extensions import db
from app.models import AppSetting

INSTITUTION_KEY = "institution_config"
CATALOG_DRAFT_KEY = "catalog_draft"
CATALOG_PUBLISHED_KEY = "catalog_published"
ASSESSMENT_CONFIG_KEY = "assessment_config_meta"


def get_json(key: str, default=None):
    row = db.session.get(AppSetting, key)
    if not row:
        return default
    return row.value


def set_json(key: str, value) -> None:
    row = db.session.get(AppSetting, key)
    if not row:
        row = AppSetting(key=key, value=value)
        db.session.add(row)
    else:
        row.value = value
    db.session.commit()
