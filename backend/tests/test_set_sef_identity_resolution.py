"""SET/SEF identity resolution API and flexible semester-count findings."""

from __future__ import annotations

import uuid

from flask import current_app

from app.extensions import db
from app.models import Document, DocumentValidationFinding, SetSefSemesterRecord, User, UserRole
from app.services.auth_context import issue_api_token
from app.services.catalog import CRITERION_A_POLICY_FLEXIBLE
from app.services.set_sef_validation import run_set_sef_validations


def test_flexible_policy_incomplete_semester_is_info(app, app_ctx):
    flex_cat = {
        "version": "flex",
        "kras": [
            {
                "id": "kra-I",
                "criteria": [
                    {
                        "id": "kra-I-A",
                        "indicators": [
                            {
                                "id": "kra-I-A-set",
                                "calculation": {"factor": 0.36, "policy": CRITERION_A_POLICY_FLEXIBLE},
                            }
                        ],
                    }
                ],
            }
        ],
    }
    owner = User.query.filter_by(role=UserRole.faculty).first()
    doc = Document(
        owner_user_id=owner.id,
        object_key=f"test/identity-doc-{uuid.uuid4().hex}.pdf",
        original_filename="t.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        upload_status="stored",
        document_kind="set_sef_combined",
    )
    db.session.add(doc)
    db.session.flush()
    rec = SetSefSemesterRecord(
        document_id=doc.id,
        owner_user_id=owner.id,
        academic_year="2024-2025",
        semester="1st Sem",
        semester_key="2024-2025|1st Sem",
        set_rating_extracted=90,
        sef_rating_extracted=95,
        faculty_name_extracted="Baroro, Jason",
        faculty_identity_status="match",
    )
    db.session.add(rec)
    db.session.commit()
    findings = run_set_sef_validations(
        document=doc,
        owner=owner,
        records=[rec],
        prior_hash=None,
        document_kind="set_sef_combined",
        catalog=flex_cat,
    )
    inc = [f for f in findings if f.rule_id == "incomplete_semester_count"]
    assert inc and inc[0].outcome == "info"


def test_resolve_identity_endpoint(app, app_ctx):
    faculty = User.query.filter_by(role=UserRole.faculty).first()
    reviewer = User.query.filter_by(role=UserRole.reviewer).first()
    if not reviewer:
        reviewer = User.query.filter_by(role=UserRole.admin).first()
    assert faculty and reviewer

    doc = Document(
        owner_user_id=faculty.id,
        object_key=f"test/identity-api-{uuid.uuid4().hex}.pdf",
        original_filename="col.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        upload_status="stored",
        document_kind="set_sef_combined",
        indicator_id="kra-I-A-setsef-combined",
        kra_id="kra-I",
    )
    db.session.add(doc)
    db.session.flush()
    rec = SetSefSemesterRecord(
        document_id=doc.id,
        owner_user_id=faculty.id,
        academic_year="2024-2025",
        semester="1st Sem",
        semester_key="2024-2025|1st Sem",
        set_rating_extracted=90,
        sef_rating_extracted=95,
        faculty_name_extracted=faculty.full_name,
        faculty_identity_status="needs_confirmation",
    )
    db.session.add(rec)
    db.session.add(
        DocumentValidationFinding(
            document_id=doc.id,
            rule_id="faculty_identity_missing",
            outcome="review",
            explanation="stale",
            pipeline="set_sef",
        )
    )
    db.session.commit()
    public_id = doc.public_id

    client = app.test_client()
    token = issue_api_token(reviewer, current_app.config["API_TOKEN_TTL_HOURS"])
    res = client.post(
        f"/api/documents/{public_id}/set-sef/resolve-identity",
        json={"resolution": "match"},
        headers={"Authorization": f"Bearer {token}", "X-Client-Type": "web"},
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    db.session.expire_all()
    rec2 = SetSefSemesterRecord.query.filter_by(document_id=doc.id, superseded_by_id=None).first()
    assert rec2.faculty_identity_status == "match"
    findings = DocumentValidationFinding.query.filter_by(document_id=doc.id, pipeline="set_sef").all()
    assert not any(f.rule_id == "faculty_identity_missing" and f.outcome == "review" for f in findings)