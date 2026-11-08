from flask import Blueprint, current_app
from sqlalchemy import text

from app.extensions import db
from app.services.database_check import assert_expected_database, current_database_name
from app.services.mail_service import smtp_configured
from app.services.storage import storage_configured

bp = Blueprint("health", __name__)


@bp.get("/api/health")
def health():
    payload = {
        "status": "ok",
        "service": "facultylinks-api",
        "database": "not_configured",
        "databaseName": None,
        "storage": "configured" if storage_configured() else "not_configured",
        "storageProvider": "supabase",
        "mail": "configured" if smtp_configured() else "not_configured",
    }
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
    if not uri:
        payload["status"] = "degraded"
        return payload, 503

    try:
        db.session.execute(text("SELECT 1"))
        payload["database"] = "connected"
        payload["databaseName"] = current_database_name()
        try:
            assert_expected_database()
        except Exception as exc:
            payload["status"] = "degraded"
            payload["database"] = "wrong_database"
            payload["databaseMessage"] = str(exc)
            return payload, 503
    except Exception:
        payload["status"] = "degraded"
        payload["database"] = "unavailable"
        return payload, 503

    if payload["storage"] == "not_configured" or payload["mail"] == "not_configured":
        payload["status"] = "degraded"

    return payload
