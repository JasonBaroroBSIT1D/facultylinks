"""General OCR classification + catalog-driven content validation."""

from __future__ import annotations

import io

from app.extensions import db
from app.models import (
    Document,
    DocumentClassification,
    DocumentExtractedField,
    DocumentExtraction,
    DocumentValidationFinding,
    User,
    UserRole,
)
from app.services.catalog import find_indicator, get_published_catalog_and_weights
from app.services.document_classification import classify_document_kra
from app.services.document_content_validation import validate_document_content
from app.services.document_ocr_processor import enqueue_general_ocr_job, process_general_ocr_document
from app.services.document_text import extract_document_text
from app.services.document_validation_config import coverage_for_indicator
from app.services.pdf_text import PageText


def test_classify_clear_research_keywords():
    text = "This Journal article has an ISSN and DOI reference."
    r = classify_document_kra(text, selected_kra_id="kra-II")
    assert r.outcome == "clear"
    assert r.suggested_kra_id == "kra-II"


def test_classify_mismatch_does_not_reassign():
    text = "Certificate of training seminar workshop attendance."
    r = classify_document_kra(text, selected_kra_id="kra-I")
    assert r.suggested_kra_id == "kra-IV"
    assert r.outcome == "mismatch_selected"


def test_classify_absent():
    r = classify_document_kra("xyz abc unrelated content only.", selected_kra_id="kra-II")
    assert r.outcome == "absent"
    assert r.suggested_kra_id is None


def test_content_date_requires_label_not_any_date(app, app_ctx):
    text = "Leadership Certificate\nSome body text mentions 01/15/2024 somewhere.\n"
    result = validate_document_content(
        full_text=text,
        pages=[{"page": 1, "text": text}],
        indicator_id="kra-IV-A-1",
        kra_id="kra-IV",
    )
    date_fields = [f for f in result.fields if f.field_name == "event_date"]
    assert date_fields, "catalog should map achievementDate/date to event_date for KRA IV"
    assert date_fields[0].status == "missing"


def test_content_labeled_date_ok(app, app_ctx):
    text = (
        "Title: Leadership Seminar\n"
        "Achievement date: January 15, 2024\n"
        "Issued on: January 15, 2024\n"
    )
    result = validate_document_content(
        full_text=text,
        pages=[{"page": 1, "text": text}],
        indicator_id="kra-IV-A-1",
        kra_id="kra-IV",
    )
    by_name = {f.field_name: f for f in result.fields}
    assert "title" in by_name
    assert by_name["title"].status in ("ok", "ambiguous")
    assert by_name["event_date"].status == "ok"
    # Do not invent recipient/author requirements for KRA IV catalog fields
    assert "subject_name" not in by_name
    assert "author_name" not in by_name


def test_set_sef_indicator_uses_dedicated_pipeline_coverage(app, app_ctx):
    result = validate_document_content(
        full_text="hello",
        pages=[{"page": 1, "text": "hello"}],
        indicator_id="kra-I-A-setsef-eval",
        kra_id="kra-I",
    )
    assert result.coverage_status == "set_sef_pipeline"
    assert any(f["rule_id"] == "coverage_set_sef_pipeline" for f in result.findings)
    assert result.fields == []


def test_special_status_requires_readable_text(app, app_ctx):
    empty = validate_document_content(
        full_text="",
        pages=[],
        indicator_id="kra-I-A-special",
        kra_id="kra-I",
    )
    assert empty.coverage_status == "special_status_support"
    assert any(f["rule_id"] == "special_status_supporting_text" for f in empty.findings)

    ok = validate_document_content(
        full_text="Official Study Leave approval memorandum for faculty member with details.",
        pages=[{"page": 1, "text": "Official Study Leave approval memorandum for faculty member with details."}],
        indicator_id="kra-I-A-special",
        kra_id="kra-I",
    )
    assert any(f.field_name == "supporting_text" and f.status == "ok" for f in ok.fields)


def test_catalog_coverage_no_blind_author_on_kra_ii(app, app_ctx):
    catalog, _ = get_published_catalog_and_weights()
    found = find_indicator(catalog, "kra-II-A-3")
    ind = (found or {}).get("indicator")
    coverage = coverage_for_indicator(ind, indicator_id="kra-II-A-3", kra_id="kra-II")
    assert coverage["status"] == "catalog_fields"
    assert "title" in coverage["ocr_fields"]
    assert "achievementDate" in coverage["ocr_fields"]
    # authorRole is form-only, not OCR author_name
    assert "authorRole" in (coverage.get("form_only_fields") or []) or "authorRole" in (ind.get("fields") or [])
    result = validate_document_content(
        full_text="Title: Sample Article\nPublished: 2024\n",
        pages=[{"page": 1, "text": "Title: Sample Article\nPublished: 2024\n"}],
        indicator_id="kra-II-A-3",
        kra_id="kra-II",
        catalog=catalog,
    )
    assert all(f.field_name != "author_name" for f in result.fields)


def test_every_catalog_indicator_has_explicit_coverage(app, app_ctx):
    catalog, _ = get_published_catalog_and_weights()
    allowed = {"set_sef_pipeline", "special_status_support", "catalog_fields", "unconfigured"}
    gaps = []
    for kra in catalog.get("kras") or []:
        for crit in kra.get("criteria") or []:
            for ind in crit.get("indicators") or []:
                cov = coverage_for_indicator(ind, indicator_id=ind.get("id"), kra_id=kra.get("id"))
                if cov["status"] not in allowed:
                    gaps.append((ind.get("id"), cov["status"]))
                if cov["status"] == "unconfigured" and cov.get("ocr_fields"):
                    gaps.append((ind.get("id"), "unconfigured_with_ocr_fields"))
    assert not gaps


def test_image_extract_requires_tesseract_or_succeeds(app, app_ctx):
    result = extract_document_text(io.BytesIO(b"not-an-image"), "image/png")
    assert result.error
    assert result.extraction_method in ("none", "tesseract")


def test_persistence_fresh_session(app, app_ctx, monkeypatch):
    faculty = User.query.filter_by(role=UserRole.faculty).order_by(User.id.asc()).first()
    assert faculty
    import uuid

    doc = Document(
        owner_user_id=faculty.id,
        object_key=f"test/general-ocr-{faculty.id}-{uuid.uuid4().hex[:8]}.pdf",
        original_filename="certificate.pdf",
        mime_type="application/pdf",
        size_bytes=100,
        upload_status="stored",
        indicator_id="kra-IV-A-1",
        kra_id="kra-IV",
        review_status="pending",
        ocr_status="pending",
        processing_status="queued",
    )
    db.session.add(doc)
    db.session.commit()
    doc_id = doc.id
    public_id = doc.public_id

    sample_text = (
        "Title: Research Training Seminar\n"
        "Issued on: March 1, 2025\n"
        "This training seminar certificate.\n"
    )

    def fake_download(_key):
        return b"%PDF-1.4 fake"

    def fake_extract(stream, mime_type):
        from app.services.document_text import DocumentTextResult

        return DocumentTextResult(
            pages=[PageText(page_number=1, text=sample_text, source="pdf_text")],
            full_text=sample_text,
            extraction_method="pdf_text",
        )

    monkeypatch.setattr("app.services.document_ocr_processor.download_private_file", fake_download)
    monkeypatch.setattr("app.services.document_ocr_processor.extract_document_text", fake_extract)

    job = enqueue_general_ocr_job(doc)
    assert job is not None
    process_general_ocr_document(doc_id, job.id)

    db.session.expire_all()
    ext = (
        DocumentExtraction.query.filter_by(document_id=doc_id, superseded_by_id=None)
        .order_by(DocumentExtraction.id.desc())
        .first()
    )
    assert ext is not None
    assert ext.rules_version
    assert "Seminar" in (ext.full_text or "")
    cls = (
        DocumentClassification.query.filter_by(document_id=doc_id, superseded_by_id=None)
        .order_by(DocumentClassification.id.desc())
        .first()
    )
    assert cls is not None
    fields = DocumentExtractedField.query.filter_by(document_id=doc_id, active=True).all()
    assert fields
    findings = DocumentValidationFinding.query.filter_by(document_id=doc_id, pipeline="general").all()
    assert isinstance(findings, list)
    refreshed = Document.query.filter_by(public_id=public_id).first()
    assert refreshed.processing_status == "completed"
    assert refreshed.ocr_status in ("completed", "review_required")
    assert refreshed.review_status == "pending"
