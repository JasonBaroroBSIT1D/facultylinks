"""Process SET/SEF combined PDF documents (OCR + validation + persistence)."""

from __future__ import annotations

import hashlib
import io
from datetime import datetime, timezone

from app.extensions import db
from app.models import Document, DocumentProcessingJob, DocumentValidationFinding, SetSefSemesterRecord, User
from app.services.catalog import get_published_catalog_and_weights
from app.services.pdf_text import extract_pdf_text
from app.services.set_sef_extractor import extract_set_sef_semesters
from app.services.set_sef_aggregation import SET_SEF_DOCUMENT_KINDS
from app.services.set_sef_validation import ValidationFinding, run_set_sef_validations, semester_key
from app.services.storage import download_private_file


def _file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _preserve_reviewer_fields(new_rec: SetSefSemesterRecord, prev: SetSefSemesterRecord) -> None:
    if prev.set_rating_confirmed is not None:
        new_rec.set_rating_confirmed = prev.set_rating_confirmed
    if prev.sef_rating_confirmed is not None:
        new_rec.sef_rating_confirmed = prev.sef_rating_confirmed
    if prev.set_verification_status == "verified":
        new_rec.set_verification_status = prev.set_verification_status
    if prev.sef_verification_status == "verified":
        new_rec.sef_verification_status = prev.sef_verification_status
    if prev.faculty_identity_status in ("match", "needs_confirmation") and prev.faculty_name_extracted:
        if new_rec.faculty_name_extracted is None:
            new_rec.faculty_name_extracted = prev.faculty_name_extracted


def _extraction_is_meaningful(records: list[SetSefSemesterRecord]) -> bool:
    return any(
        (r.set_rating_extracted is not None or r.sef_rating_extracted is not None)
        for r in records
    )


def process_set_sef_document(document_id: int, job_id: int) -> None:
    job = db.session.get(DocumentProcessingJob, job_id)
    doc = db.session.get(Document, document_id)
    if not job or not doc:
        return
    owner = db.session.get(User, doc.owner_user_id)
    if not owner:
        job.status = "failed"
        job.last_error = "Owner not found"
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        return

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job.attempts = (job.attempts or 0) + 1
    doc.processing_status = "processing"
    doc.ocr_status = "processing"
    db.session.commit()

    try:
        raw = download_private_file(doc.object_key)
        doc.file_sha256 = _file_hash(raw)
        pdf = extract_pdf_text(io.BytesIO(raw))
        if pdf.error:
            raise RuntimeError(pdf.error)

        prior = (
            Document.query.filter(
                Document.owner_user_id == doc.owner_user_id,
                Document.file_sha256 == doc.file_sha256,
                Document.id != doc.id,
                Document.document_kind.in_(SET_SEF_DOCUMENT_KINDS),
            ).first()
        )

        existing_active = {
            r.semester_key or semester_key(r.academic_year, r.semester): r
            for r in SetSefSemesterRecord.query.filter_by(document_id=doc.id, superseded_by_id=None).all()
        }
        DocumentValidationFinding.query.filter_by(document_id=doc.id).delete()

        extracted = extract_set_sef_semesters(pdf)
        catalog, _ = get_published_catalog_and_weights()
        doc.config_version = (catalog or {}).get("version") or doc.config_version

        records: list[SetSefSemesterRecord] = []
        for ex in extracted:
            sk = semester_key(ex.academic_year, ex.semester)
            rec = SetSefSemesterRecord(
                document_id=doc.id,
                owner_user_id=doc.owner_user_id,
                academic_year=ex.academic_year,
                semester=ex.semester,
                semester_key=sk,
                faculty_name_extracted=ex.faculty_name,
                set_rating_extracted=ex.set_rating,
                set_scale_extracted=ex.set_scale,
                sef_rating_extracted=ex.sef_rating,
                sef_scale_extracted=ex.sef_scale,
                set_source_pages=sorted(set(ex.set_pages)) or None,
                sef_source_pages=sorted(set(ex.sef_pages)) or None,
                set_excerpt=ex.set_excerpt,
                sef_excerpt=ex.sef_excerpt,
                ocr_raw_fragment=ex.raw_fragment,
            )
            prev = existing_active.get(sk)
            if prev:
                _preserve_reviewer_fields(rec, prev)
            db.session.add(rec)
            records.append(rec)
        db.session.flush()

        for rec in records:
            prev = existing_active.get(rec.semester_key)
            if prev and prev.id != rec.id:
                prev.superseded_by_id = rec.id

        findings = run_set_sef_validations(
            document=doc,
            owner=owner,
            records=records,
            prior_hash=prior.file_sha256 if prior else None,
            document_kind=doc.document_kind,
        )

        if not _extraction_is_meaningful(records):
            findings.append(
                ValidationFinding(
                    rule_id="extraction_empty",
                    outcome="fail",
                    affected_field=None,
                    semester_key=None,
                    explanation=(
                        "PDF text was extracted but no semester SET/SEF ratings were parsed. "
                        "Layout may be unsupported or OCR may be required."
                    ),
                )
            )

        for f in findings:
            db.session.add(
                DocumentValidationFinding(
                    document_id=doc.id,
                    rule_id=f.rule_id,
                    outcome=f.outcome,
                    affected_field=f.affected_field,
                    semester_key=f.semester_key,
                    explanation=f.explanation,
                )
            )

        has_fail = any(f.outcome == "fail" for f in findings)
        has_review = any(f.outcome == "review" for f in findings) or not extracted
        meaningful = _extraction_is_meaningful(records)

        if has_fail or not meaningful:
            doc.ocr_status = "failed"
        elif has_review:
            doc.ocr_status = "review_required"
        else:
            doc.ocr_status = "completed"

        doc.processing_status = "completed"
        doc.processing_error = None if meaningful else "No ratings parsed from PDF content."
        doc.review_status = "pending"
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception as exc:
        err = str(exc)[:480]
        doc.ocr_status = "failed"
        doc.processing_status = "failed"
        doc.processing_error = err
        job.status = "failed"
        job.last_error = err
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()
        raise


def enqueue_set_sef_job(document: Document) -> DocumentProcessingJob:
    existing = (
        DocumentProcessingJob.query.filter_by(document_id=document.id, job_type="set_sef_ocr")
        .filter(DocumentProcessingJob.status.in_(("pending", "running")))
        .first()
    )
    if existing:
        return existing
    job = DocumentProcessingJob(document_id=document.id, job_type="set_sef_ocr", status="pending")
    document.processing_status = "queued"
    document.ocr_status = "pending"
    db.session.add(job)
    db.session.commit()
    return job
