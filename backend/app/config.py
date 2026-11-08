import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from dotenv import load_dotenv

# Load backend/.env before class attributes read os.environ (import-time).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"


def load_backend_env() -> None:
    # Prefer backend/.env over inherited empty shell variables (common on Windows).
    load_dotenv(_ENV_FILE, override=True)


def apply_mail_config_from_env(app) -> None:
    """Refresh SMTP settings on the running app from os.environ (after load_dotenv)."""
    app.config["SMTP_HOST"] = os.environ.get("SMTP_HOST", "").strip() or None
    app.config["SMTP_PORT"] = int(os.environ.get("SMTP_PORT", "587") or "587")
    app.config["SMTP_USE_TLS"] = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    app.config["SMTP_USERNAME"] = os.environ.get("SMTP_USERNAME", "").strip() or None
    raw_pw = os.environ.get("SMTP_PASSWORD", "") or ""
    app.config["SMTP_PASSWORD"] = "".join(raw_pw.split()) or None
    app.config["MAIL_FROM"] = os.environ.get("MAIL_FROM", "").strip() or None
    app.config["MAIL_FROM_NAME"] = (os.environ.get("MAIL_FROM_NAME", "FacultyLink") or "FacultyLink").strip()


load_backend_env()


def _database_url() -> str | None:
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        return None
    # Supabase / managed Postgres: TLS required
    parsed = urlparse(raw)
    qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if parsed.scheme.startswith("postgresql") and "sslmode" not in qs:
        qs["sslmode"] = "require"
    # Normalize sqlalchemy scheme
    if parsed.scheme == "postgres":
        parsed = parsed._replace(scheme="postgresql+psycopg")
    elif parsed.scheme == "postgresql" and "+" not in parsed.scheme:
        parsed = parsed._replace(scheme="postgresql+psycopg")
    new_query = urlencode(qs)
    return urlunparse(parsed._replace(query=new_query))


def _engine_options(url: str | None) -> dict:
    opts: dict = {
        "pool_pre_ping": True,
        "pool_size": int(os.environ.get("SQLALCHEMY_POOL_SIZE", "5")),
        "max_overflow": int(os.environ.get("SQLALCHEMY_MAX_OVERFLOW", "10")),
    }
    if url and ":6543" in url:
        # Supabase transaction pooler: disable prepared statements (official guidance)
        opts["connect_args"] = {"prepare_threshold": None}
    return opts


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options(SQLALCHEMY_DATABASE_URI)

    # Verify connection targets this database name (not the Supabase project display name).
    EXPECTED_DATABASE_NAME = os.environ.get("EXPECTED_DATABASE_NAME", "facultylinks").strip()

    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5000,http://localhost:5000",
        ).split(",")
        if o.strip()
    ]

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")

    SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/") or None
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip() or None
    SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "facultylinks-documents").strip()

    MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
    ALLOWED_UPLOAD_MIME = frozenset(
        m.strip()
        for m in os.environ.get(
            "ALLOWED_UPLOAD_MIME",
            "application/pdf,image/jpeg,image/png,image/webp",
        ).split(",")
        if m.strip()
    )

    API_TOKEN_TTL_HOURS = int(os.environ.get("API_TOKEN_TTL_HOURS", "168"))

    # SMTP (Gmail: smtp.gmail.com, port 587, TLS on, App Password)
    SMTP_HOST = os.environ.get("SMTP_HOST", "").strip() or None
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip() or None
    SMTP_PASSWORD = "".join((os.environ.get("SMTP_PASSWORD", "") or "").split()) or None
    MAIL_FROM = os.environ.get("MAIL_FROM", "").strip() or None
    MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "FacultyLink").strip()

    RECOVERY_HMAC_SECRET = os.environ.get("RECOVERY_HMAC_SECRET", "").strip() or None


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
