"""Fail-closed checks so pytest never targets the application database."""

from __future__ import annotations

import hashlib
import os
import re
from urllib.parse import parse_qsl, unquote, urlencode, urlparse, urlunparse


def _normalize_host(host: str) -> str:
    return (host or "").strip().lower()


def database_identity(url: str) -> tuple[str, str]:
    if not url or not url.strip():
        return ("", "")
    parsed = urlparse(url.strip())
    host = _normalize_host(parsed.hostname or "")
    dbname = unquote((parsed.path or "").lstrip("/").split("?")[0] or "")
    if "@" in dbname:
        dbname = dbname.split("@")[-1]
    return host, dbname


def fingerprint(url: str) -> str:
    host, dbname = database_identity(url)
    return hashlib.sha256(f"{host}|{dbname}".encode("utf-8")).hexdigest()[:16]


def required_test_database_name() -> str:
    name = (os.environ.get("TEST_DATABASE_NAME") or "facultylinks_test").strip()
    if not name or name == "facultylinks":
        raise RuntimeError(
            "TEST_DATABASE_NAME must name a dedicated test database (e.g. facultylinks_test), not 'facultylinks'."
        )
    return name


def production_database_url_sources() -> list[str]:
    sources: list[str] = []
    for key in (
        "FACULTYLINK_PRODUCTION_DATABASE_URL",
        "APPLICATION_DATABASE_URL",
        "DATABASE_URL",
    ):
        val = os.environ.get(key, "").strip()
        if val:
            sources.append(val)
    return sources


def assert_test_database_isolated(test_url: str) -> None:
    test_url = (test_url or "").strip()
    if not test_url:
        raise RuntimeError("TEST_DATABASE_URL is required for pytest.")

    test_host, test_db = database_identity(test_url)
    if not test_host or not test_db:
        raise RuntimeError("TEST_DATABASE_URL is not a valid PostgreSQL URL.")

    required_name = required_test_database_name()
    if test_db != required_name:
        raise RuntimeError(
            f"TEST_DATABASE_URL must connect to database '{required_name}' "
            f"(got '{test_db}'). Create a separate database for tests."
        )

    test_fp = fingerprint(test_url)
    for prod_url in production_database_url_sources():
        if fingerprint(prod_url) == test_fp:
            raise RuntimeError(
                "TEST_DATABASE_URL resolves to the same host and database name as a "
                "production/application DATABASE_URL. Refusing to run tests."
            )

    if test_db == "facultylinks":
        raise RuntimeError(
            "Tests must not use the 'facultylinks' application database. "
            "Use a dedicated database such as 'facultylinks_test'."
        )


def normalize_sqlalchemy_url(url: str) -> str:
    raw = url.strip()
    parsed = urlparse(raw)
    qs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if parsed.scheme.startswith("postgresql") and "sslmode" not in qs:
        qs["sslmode"] = "require"
    scheme = parsed.scheme
    if scheme == "postgres":
        scheme = "postgresql+psycopg"
    elif scheme == "postgresql" and "+" not in scheme:
        scheme = "postgresql+psycopg"
    return urlunparse(parsed._replace(scheme=scheme, query=urlencode(qs)))


def is_pytest_fixture_email(email: str | None) -> bool:
    if not email:
        return False
    return bool(re.fullmatch(r"[^@]+@test\.local", email.strip().lower()))