"""
Pytest bootstrap: dedicated test database only (never application facultylinks DB).
"""

from __future__ import annotations

import os

# Must be set before any `app` import so backend/.env cannot override test URLs.
os.environ.setdefault("FACULTYLINK_PYTEST", "1")

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.test_db_guard import assert_test_database_isolated, is_pytest_fixture_email, normalize_sqlalchemy_url


def pytest_configure(config):
    test_url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not test_url:
        pytest.exit(
            "TEST_DATABASE_URL is not set. Create database 'facultylinks_test' (or set TEST_DATABASE_NAME) "
            "and export TEST_DATABASE_URL before running pytest. Tests must not use the live 'facultylinks' database.",
            returncode=2,
        )
    # Load production URL only for fingerprint comparison (never used as test target).
    if not os.environ.get("DATABASE_URL", "").strip():
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.isfile(env_path):
            for line in open(env_path, encoding="utf-8"):
                line = line.strip()
                if line.startswith("DATABASE_URL=") and not line.startswith("#"):
                    _, _, val = line.partition("=")
                    val = val.strip().strip('"').strip("'")
                    if val:
                        os.environ.setdefault("DATABASE_URL", val)
                    break
    try:
        assert_test_database_isolated(test_url)
    except RuntimeError as exc:
        pytest.exit(str(exc), returncode=2)


@pytest.fixture(scope="session")
def app():
    test_url = normalize_sqlalchemy_url(os.environ["TEST_DATABASE_URL"].strip())
    os.environ["TEST_DATABASE_URL"] = test_url
    application = create_app()
    assert application.config["TESTING"]
    return application


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app


@pytest.fixture(autouse=True)
def _cleanup_pytest_fixture_rows(request, app):
    """Remove @test.local rows created during the test (test DB only)."""
    yield
    if request.module and request.module.__name__.endswith("test_db_isolation_guard"):
        return
    with app.app_context():
        from app.models import (
            Document,
            FacultyAssessment,
            Notification,
            ReviewerAssignment,
            User,
        )

        users = User.query.filter(User.email.ilike("%@test.local")).all()
        suspect = [
            u
            for u in users
            if is_pytest_fixture_email(u.email)
            and (u.password_hash == "x" or (u.full_name or "") in ("Rev One", "Rev Two", "Fac One", "Fac Two", "Owner", "Rev"))
        ]
        if not suspect:
            return
        ids = [u.id for u in suspect]
        Notification.query.filter(
            (Notification.user_id.in_(ids))
            | (Notification.actor_user_id.in_(ids))
            | (Notification.subject_faculty_user_id.in_(ids))
        ).delete(synchronize_session=False)
        ReviewerAssignment.query.filter(
            (ReviewerAssignment.faculty_user_id.in_(ids)) | (ReviewerAssignment.reviewer_user_id.in_(ids))
        ).delete(synchronize_session=False)
        Document.query.filter(Document.owner_user_id.in_(ids)).delete(synchronize_session=False)
        FacultyAssessment.query.filter(FacultyAssessment.user_id.in_(ids)).delete(synchronize_session=False)
        User.query.filter(User.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()