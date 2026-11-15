"""Admin assessment report: unavailable vs zero; auth; independent snapshot."""

from flask import current_app

from app.models import User, UserRole
from app.services.assessment_report import _score_value, build_assessment_report
from app.services.auth_context import issue_api_token


def test_score_value_never_fakes_unavailable_as_zero():
    assert _score_value(None, unavailable=True)["display"] == "Unavailable"
    assert _score_value(None)["available"] is False
    zero = _score_value(0.0)
    assert zero["available"] is True
    assert zero["value"] == 0.0
    assert zero["display"] == "0.00"


def test_assessment_report_builds_for_existing_faculty(app, app_ctx):
    admin = User.query.filter_by(role=UserRole.admin).first()
    faculty = User.query.filter_by(role=UserRole.faculty).first()
    assert admin and faculty
    report = build_assessment_report(faculty=faculty, actor=admin)
    assert report["title"] == "Faculty Assessment and Evidence Report"
    assert report["mutatesNothing"] is True
    assert report["reportId"].startswith("FL-RPT-")
    assert report["preparedBy"]["email"] == admin.email
    assert report["faculty"]["id"] == faculty.portal_id()
    assert "countingNote" in report["progress"]
    assert "executiveSummary" in report
    assert "kraScoreSummary" in report
    assert "evidenceRegister" in report
    # Document IDs in evidence are unique
    ids = [e["id"] for e in report["evidenceRegister"]]
    assert len(ids) == len(set(ids))


def test_assessment_report_api_admin_only(app, app_ctx):
    admin = User.query.filter_by(role=UserRole.admin).first()
    faculty = User.query.filter_by(role=UserRole.faculty).first()
    assert admin and faculty
    client = app.test_client()
    pid = faculty.portal_id()

    res = client.get(f"/api/portal/faculty/{pid}/assessment-report")
    assert res.status_code in (401, 403)

    fac_token = issue_api_token(faculty, current_app.config["API_TOKEN_TTL_HOURS"])
    res = client.get(
        f"/api/portal/faculty/{pid}/assessment-report",
        headers={"Authorization": f"Bearer {fac_token}", "X-Client-Type": "web"},
    )
    assert res.status_code == 403

    admin_token = issue_api_token(admin, current_app.config["API_TOKEN_TTL_HOURS"])
    res = client.get(
        f"/api/portal/faculty/{pid}/assessment-report",
        headers={"Authorization": f"Bearer {admin_token}", "X-Client-Type": "web"},
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert body["report"]["reportId"]
    assert body["report"]["preparedBy"]["email"] == admin.email
    # No storage/signed URL leakage
    blob = res.get_data(as_text=True)
    assert "supabase" not in blob.lower()
    assert "service_role" not in blob.lower()
    assert "/view-url" not in blob


def test_assessment_report_aime_scores_not_fake_zero(app, app_ctx):
    """jasonbaroro4 (Aime) has approved evidence + flexible Criterion A — not 0.00."""
    admin = User.query.filter_by(role=UserRole.admin).first()
    faculty = User.query.filter_by(email="jasonbaroro4@gmail.com").first()
    if not faculty or not admin:
        return
    report = build_assessment_report(faculty=faculty, actor=admin)
    est = report["executiveSummary"]["estimatedOverall"]
    assert est["available"] is True
    assert est["value"] is not None
    assert float(est["value"]) > 0
    ca = (report.get("criterionA") or {}).get("estimated") or {}
    assert ca.get("calculationUnavailable") is not True
    assert float(ca.get("criterionAPoints") or 0) > 0
    ids = [e["id"] for e in report["evidenceRegister"]]
    assert len(ids) == len(set(ids))
    assert report["progress"]["countingNote"]
