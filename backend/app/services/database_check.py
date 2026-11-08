from flask import current_app
from sqlalchemy import text

from app.extensions import db


class DatabaseNameMismatchError(RuntimeError):
    pass


def current_database_name() -> str:
    return db.session.execute(text("SELECT current_database()")).scalar_one()


def assert_expected_database() -> None:
    expected = (current_app.config.get("EXPECTED_DATABASE_NAME") or "").strip()
    if not expected:
        return
    actual = current_database_name()
    if actual != expected:
        raise DatabaseNameMismatchError(
            f"Connected to database '{actual}', but EXPECTED_DATABASE_NAME is '{expected}'. "
            "Update DATABASE_URL or create the database — see docs/CLOUD_SETUP.md."
        )
