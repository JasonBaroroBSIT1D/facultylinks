"""HTTP tests for general document validation API."""

from __future__ import annotations

import uuid

from flask import current_app

from app.extensions import db
from app.models import (
    Document,
    DocumentExtractedField,
    DocumentExtraction,
    DocumentValidationFinding,
    User,
    UserRole,
)
from app.services.auth_context import issue_api_token
from app.services.document_ocr_processor import enqueue_general_ocr_job, process_general_ocr_document
from app.services.pdf_text import PageText


def _faculty():
    return User.query.filter_by(role=UserRole.faculty).order_by(User.id.asc()).first()


def _reviewer_for(faculty: User) -> User | None:
    from app.models import ReviewerAssignment

    link = ReviewerAssignment.query.filter_by(faculty_user_id=faculty.id).first()
    if link:
        return db.session.get(User, link.reviewer_user_id)
    return User.query.filter_by(role=UserRole.admin).first()


def test_get_validation_forbidden_without_auth(app, app_ctx):
    faculty = _faculty()
    assert faculty
    doc = Document(
        owner_user_id=faculty.id,
        object_key=f"test/val-{uuid.uuid4().hex}.pdf",
        original_filename="x.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        upload_status="stored",
        indicator_id="kra-IV-A-1",
        kra_id="kra-IV",
        criterion_id="kra-IV-A",
        ocr_status="completed",
        processing_status="completed",
    )
    db.session.add(doc)
    db.session.commit()
    client = app.test_client()
    res = client.get(f"/api/documents/{doc.public_id}/validation")
    assert res.status_code == 401


def test_get_validation_faculty_owner_payload(app, app_ctx, monkeypatch):
    faculty = _faculty()
    assert faculty
    sample = (
        "Title: Faculty Leadership Certificate\n"
        "Issued on: January 10, 2025\n"
        "This is to certify that Sample Faculty Member completed the program.\n"
    )

    doc = Document(
        owner_user_id=faculty.id,
        object_key=f"test/val-{uuid.uuid4().hex}.pdf",
        original_filename="cert.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        upload_status="stored",
        indicator_id="kra-IV-A-1",
        kra_id="kra-IV",
        criterion_id="kra-IV-A",
        review_status="pending",
        ocr_status="pending",
        processing_status="queued",
    )
    db.session.add(doc)
    db.session.commit()
    doc_id = doc.id
    public_id = doc.public_id

    def fake_download(_key):
        return b"%PDF-1.4"

    def fake_extract(stream, mime_type):
        from app.services.document_text import DocumentTextResult

        return DocumentTextResult(
            pages=[PageText(page_number=1, text=sample, source="pdf_text")],
            full_text=sample,
            extraction_method="pdf_text",
        )

    monkeypatch.setattr("app.services.document_ocr_processor.download_private_file", fake_download)
    monkeypatch.setattr("app.services.document_ocr_processor.extract_document_text", fake_extract)

    job = enqueue_general_ocr_job(doc)
    process_general_ocr_document(doc_id, job.id)

    client = app.test_client()
    token = issue_api_token(faculty, current_app.config["API_TOKEN_TTL_HOURS"])
    res = client.get(
        f"/api/documents/{public_id}/validation",
        headers={"Authorization": f"Bearer {token}", "X-Client-Type": "faculty_mobile"},
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert body["coverage"]["fullyValidated"] is False
    assert body["processing"]["validationComplete"] is True
    assert body["hierarchy"]["indicatorId"] == "kra-IV-A-1"
    assert body["configuration"]["source"]
    assert body["awardsPoints"] is False
    assert any(f["ruleId"] == "validation_configuration_snapshot" for f in body["validationFindings"])


def test_patch_field_confirmation_reviewer(app, app_ctx, monkeypatch):
    faculty = _faculty()
    reviewer = _reviewer_for(faculty)
    assert faculty and reviewer

    doc = Document(
        owner_user_id=faculty.id,
        object_key=f"test/val-{uuid.uuid4().hex}.pdf",
        original_filename="cert.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        upload_status="stored",
        indicator_id="kra-IV-A-1",
        kra_id="kra-IV",
        criterion_id="kra-IV-A",
        ocr_status="completed",
        processing_status="completed",
    )
    db.session.add(doc)
    db.session.flush()
    ext = DocumentExtraction(document_id=doc.id, full_text="Title: X", status="completed")
    db.session.add(ext)
    db.session.flush()
    field = DocumentExtractedField(
        document_id=doc.id,
        extraction_id=ext.id,
        field_name="title",
        value_extracted="Ambiguous title",
        field_status="ambiguous",
        active=True,
    )
    db.session.add(field)
    db.session.commit()
    field_id = field.id
    public_id = doc.public_id

    client = app.test_client()
    token = issue_api_token(reviewer, current_app.config["API_TOKEN_TTL_HOURS"])
    res = client.patch(
        f"/api/documents/{public_id}/validation/fields/{field_id}",
        json={"valueConfirmed": "Corrected Title"},
        headers={"Authorization": f"Bearer {token}", "X-Client-Type": "web"},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["field"]["valueConfirmed"] == "Corrected Title"
    assert body["field"]["fieldStatus"] == "ok"

    db.session.expire_all()
    row = db.session.get(DocumentExtractedField, field_id)
    assert row.value_confirmed == "Corrected Title"
    assert row.field_status == "ok"


def test_patch_field_forbidden_other_faculty(app, app_ctx):
    faculty = _faculty()
    other = User.query.filter(User.role == UserRole.faculty, User.id != faculty.id).first()
    assert faculty and other

    doc = Document(
        owner_user_id=other.id,
        object_key=f"test/val-{uuid.uuid4().hex}.pdf",
        original_filename="cert.pdf",
        mime_type="application/pdf",
        size_bytes=10,
        upload_status="stored",
        indicator_id="kra-IV-A-1",
        kra_id="kra-IV",
        ocr_status="completed",
        processing_status="completed",
    )
    db.session.add(doc)
    db.session.flush()
    field = DocumentExtractedField(
        document_id=doc.id,
        field_name="title",
        field_status="missing",
        active=True,
    )
    db.session.add(field)
    db.session.commit()

    client = app.test_client()
    token = issue_api_token(faculty, current_app.config["API_TOKEN_TTL_HOURS"])
    res = client.patch(
        f"/api/documents/{doc.public_id}/validation/fields/{field.id}",
        json={"valueConfirmed": "Nope"},
        headers={"Authorization": f"Bearer {token}", "X-Client-Type": "faculty_mobile"},
    )
    assert res.status_code == 403


def test_retry_preserves_config_snapshot(app, app_ctx, monkeypatch):
    from app.models import FacultyAssessment

    faculty = _faculty()
    assert faculty
    row = FacultyAssessment.query.get(faculty.id)
    pinned = (row.data or {}).get("configVersionId") if row else None

    sample = "Title: Workshop\nIssued on: May 1, 2024\n"

    doc = Document(
        owner_user_id=faculty.id,
        object_key=f"test/val-{uuid.uuid4().hex}.pdf",
        original_filename="w.pdf",
        mime_type="application/pdf",
        size_bytes=50,
        upload_status="stored",
        indicator_id="kra-IV-A-1",
        kra_id="kra-IV",
        criterion_id="kra-IV-A",
        config_version=str(pinned) if pinned else None,
        ocr_status="pending",
        processing_status="queued",
    )
    db.session.add(doc)
    db.session.commit()

    def fake_download(_key):
        return b"%PDF"

    def fake_extract(stream, mime_type):
        from app.services.document_text import DocumentTextResult

        return DocumentTextResult(
            pages=[PageText(page_number=1, text=sample, source="pdf_text")],
            full_text=sample,
            extraction_method="pdf_text",
        )

    monkeypatch.setattr("app.services.document_ocr_processor.download_private_file", fake_download)
    monkeypatch.setattr("app.services.document_ocr_processor.extract_document_text", fake_extract)

    job = enqueue_general_ocr_job(doc)
    process_general_ocr_document(doc.id, job.id)
    snap1 = DocumentValidationFinding.query.filter_by(
        document_id=doc.id, rule_id="validation_configuration_snapshot"
    ).first()
    assert snap1

    job2 = enqueue_general_ocr_job(doc, force=True)
    process_general_ocr_document(doc.id, job2.id)
    snaps = (
        DocumentValidationFinding.query.filter_by(
            document_id=doc.id, rule_id="validation_configuration_snapshot"
        )
        .order_by(DocumentValidationFinding.id.desc())
        .all()
    )
    assert len(snaps) >= 1
    db.session.refresh(doc)
    if pinned:
        assert doc.config_version == str(pinned)