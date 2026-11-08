import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from dotenv import load_dotenv

# Load backend/.env before class attributes read os.environ (import-time).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_ROOT / ".env"


def load_backend_env() -> None:
    load_dotenv(_ENV_FILE)


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
    opts: dict = {"pool_pre_ping": True}
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


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
