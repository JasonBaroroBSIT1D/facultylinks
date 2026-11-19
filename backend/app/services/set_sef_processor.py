"""Process SET/SEF combined PDF documents (OCR + validation + persistence)."""

from __future__ import annotations

import hashlib
import io
import logging
import re
from datetime import datetime, timezone

from app.extensions import db
from app.models import (
    Document,
    DocumentProcessingJob,
    DocumentValidationFinding,
    FacultyAssessment,
    SetSefSemesterRecord,
    User,
)
from app.services.catalog import get_published_catalog_and_weights
from app.services.document_text import IMAGE_MIME
from app.services.ocr_env import resolve_tesseract_cmd
from app.services.pdf_text import PdfExtractionResult, extract_image_bytes_text, extract_pdf_text
from app.services.set_sef_extractor import (
    DUAL_SEM_HEADER_LINE_RE,
    SET_SEF_TABLE_BAND_MARKER,
    STUDENTS_COMPONENT_LINE_RE,
    SUMMARY_TABLE_MARKER,
    SUPERVISOR_COMPONENT_LINE_RE,
    _original_ratings_paired_line,
    extract_set_sef_semesters,
)
from app.services.set_sef_faculty_name import resolve_faculty_name_for_set_sef
from app.services.set_sef_aggregation import SET_SEF_DOCUMENT_KINDS
from app.services.set_sef_validation import ValidationFinding, run_set_sef_validations, semester_key
from app.services.infrastructure_errors import (
    faculty_safe_processing_error,
    infrastructure_error_faculty_message,
    is_transient_infrastructure_error,
)
from app.services.storage import download_private_file

_log = logging.getLogger(__name__)


_CONTINUATION_SHEET_RE = re.compile(r"(?i)continu(?:e|a).*sep\s+sheet|sep\s+sheet\s+if")
_SET_SEF_TABLE_BAND_CROPS = (
    (0.10, 0.42),
    (0.15, 0.48),
    (0.18, 0.52),
    (0.20, 0.50),
)


def _score_set_sef_table_band_text(band: str) -> int:
    score = 0
    if DUAL_SEM_HEADER_LINE_RE.search(band):
        score += 20
    for line in band.splitlines():
        if STUDENTS_COMPONENT_LINE_RE.search(line):
            score += 5 * len(_original_ratings_paired_line(line, 60))
        if SUPERVISOR_COMPONENT_LINE_RE.search(line):
            score += 5 * len(_original_ratings_paired_line(line, 40))
    return score


def _append_set_sef_table_band_ocr(result: PdfExtractionResult, raw: bytes) -> PdfExtractionResult:
    """High-resolution OCR on the ratings band when full-page OCR drops the second semester column."""
    text = result.full_text or ""
    if not SUMMARY_TABLE_MARKER.search(text):
        return result
    if DUAL_SEM_HEADER_LINE_RE.search(text):
        return result
    if not _CONTINUATION_SHEET_RE.search(text) and not re.search(
        r"(?i)students?\s*\(?\s*60", text
    ):
        return result
    if SET_SEF_TABLE_BAND_MARKER in text:
        return result
    if resolve_tesseract_cmd() is None:
        return result
    try:
        import fitz
        import pytesseract
        from PIL import Image

        from app.services.pdf_text import configure_pytesseract
    except ImportError:
        return result

    configure_pytesseract()
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        if doc.page_count < 1:
            doc.close()
            return result
        page = doc.load_page(0)
        rect = page.rect
        best_band = ""
        best_score = 0
        for y0_frac, y1_frac in _SET_SEF_TABLE_BAND_CROPS:
            clip = fitz.Rect(
                rect.x0,
                rect.y0 + rect.height * y0_frac,
                rect.x1,
                rect.y0 + rect.height * y1_frac,
            )
            pix = page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            band = (pytesseract.image_to_string(img, lang="eng") or "").strip()
            score = _score_set_sef_table_band_text(band)
            if score > best_score:
                best_score = score
                best_band = band
        band_text = best_band
        doc.close()
    except Exception:
        return result

    if not band_text.strip():
        return result
    merged = f"{text.rstrip()}\n\n{SET_SEF_TABLE_BAND_MARKER}\n{band_text}"
    return PdfExtractionResult(
        pages=result.pages,
        full_text=merged,
        error=result.error,
        ocr_required=result.ocr_required,
    )


def _extract_set_sef_source(raw: bytes, mime_type: str | None) -> PdfExtractionResult:
    """Text PDF uses embedded text + OCR fallback; camera/scanned images use OCR directly.

    Multi-page camera scans are archived as image-only PDFs. extract_pdf_text OCRs
    those pages; if still empty, embedded page images are OCR'd as raw blobs so
    PDF wrapping alone is never treated as successful extraction.
    """
    mime = (mime_type or "").split(";")[0].strip().lower()
    if mime == "application/pdf":
        result = extract_pdf_text(io.BytesIO(raw))
        if (result.full_text or "").strip():
            return _append_set_sef_table_band_ocr(result, raw)
        try:
            import fitz

            doc = fitz.open(stream=raw, filetype="pdf")
            blobs: list[bytes] = []
            try:
                for page in doc:
                    extracted_blob = None
                    for img in page.get_images(full=True):
                        xref = img[0]
                        extracted = doc.extract_image(xref)
                        if extracted and extracted.get("image"):
                            extracted_blob = extracted["image"]
                            break
                    if extracted_blob is None:
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                        extracted_blob = pix.tobytes("png")
                    blobs.append(extracted_blob)
            finally:
                doc.close()
            if blobs:
                ocr = extract_image_bytes_text(blobs)
                if (ocr.full_text or "").strip() or ocr.pages:
                    return _append_set_sef_table_band_ocr(ocr, raw)
        except Exception:
            pass
        return _append_set_sef_table_band_ocr(result, raw)
    if mime in IMAGE_MIME or mime == "image/jpg":
        return extract_image_bytes_text([raw])
    return PdfExtractionResult(error=f"Unsupported SET/SEF source type: {mime or 'unknown'}")


def _file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extracted_ratings_unchanged(
    new_rec: SetSefSemesterRecord, prev: SetSefSemesterRecord
) -> bool:
    def _eq(a, b) -> bool:
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        return float(a) == float(b)

    return _eq(new_rec.set_rating_extracted, prev.set_rating_extracted) and _eq(
        new_rec.sef_rating_extracted, prev.sef_rating_extracted
    )


def _preserve_reviewer_fields(new_rec: SetSefSemesterRecord, prev: SetSefSemesterRecord) -> None:
    """Keep reviewer confirmation only when extracted ratings are unchanged for that semester_key."""
    if not _extracted_ratings_unchanged(new_rec, prev):
        return
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
    job = (
        DocumentProcessingJob.query.filter_by(id=job_id, status="pending")
        .with_for_update()
        .first()
    )
    doc = db.session.get(Document, document_id)
    if not job or not doc:
        db.session.rollback()
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
    prior_ocr_status = doc.ocr_status
    prior_processing_status = doc.processing_status
    doc.processing_status = "processing"
    doc.ocr_status = "processing"
    db.session.commit()

    try:
        raw = download_private_file(doc.object_key)
        doc.file_sha256 = _file_hash(raw)
        pdf = _extract_set_sef_source(raw, doc.mime_type)
        if pdf.error and not pdf.pages:
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
        DocumentValidationFinding.query.filter_by(document_id=doc.id, pipeline="set_sef").delete(
            synchronize_session=False
        )
        # Legacy rows (pre-pipeline column) — remove unscoped findings for this document.
        DocumentValidationFinding.query.filter(
            DocumentValidationFinding.document_id == doc.id,
            DocumentValidationFinding.pipeline.is_(None),
        ).delete(synchronize_session=False)

        extracted = extract_set_sef_semesters(pdf)
        parsed_name = next((ex.faculty_name for ex in extracted if ex.faculty_name), None)
        faculty_name, _name_source = resolve_faculty_name_for_set_sef(
            pdf_bytes=raw,
            full_text=pdf.full_text,
            parsed_name=parsed_name,
        )
        if faculty_name:
            for ex in extracted:
                ex.faculty_name = faculty_name

        from app.services.catalog import find_indicator, get_catalog_for_assessment

        assess = db.session.get(FacultyAssessment, doc.owner_user_id)
        assessment_data = assess.data if assess else {}
        catalog, _ = get_catalog_for_assessment(assessment_data)
        if not catalog:
            catalog, _ = get_published_catalog_and_weights()
        pinned = (assessment_data or {}).get("configVersionId") or (catalog or {}).get("version")
        if pinned:
            doc.config_version = str(pinned)
        if not doc.criterion_id and catalog and doc.indicator_id:
            found = find_indicator(catalog, doc.indicator_id)
            if found and (found.get("criterion") or {}).get("id"):
                doc.criterion_id = found["criterion"]["id"]

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

        # Deactivate prior active rows for this document so Retry OCR cannot
        # leave duplicate active semester records.
        if records:
            for prev in existing_active.values():
                if prev.superseded_by_id is not None:
                    continue
                match = next((r for r in records if r.semester_key == prev.semester_key), None)
                prev.superseded_by_id = match.id if match is not None else records[0].id

        findings = run_set_sef_validations(
            document=doc,
            owner=owner,
            records=records,
            prior_hash=prior.file_sha256 if prior else None,
            document_kind=doc.document_kind,
            catalog=catalog,
        )

        if not _extraction_is_meaningful(records):
            findings.append(
                ValidationFinding(
                    rule_id="extraction_empty",
                    outcome="fail",
                    affected_field=None,
                    semester_key=None,
                    explanation=(
                        "Text was extracted but no semester SET/SEF ratings were parsed. "
                        "The scan may be unclear, or the layout may need reviewer confirmation."
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
                    pipeline="set_sef",
                    severity=f.outcome,
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
        doc.processing_error = None if meaningful else "No ratings parsed from document content."
        doc.review_status = "pending"
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception as exc:
        technical = str(exc)[:480]
        infra = is_transient_infrastructure_error(exc)
        _log.exception(
            "SET/SEF OCR failed for document_id=%s job_id=%s (%s)",
            document_id,
            job_id,
            "infrastructure" if infra else "processing",
        )
        db.session.rollback()
        job = db.session.get(DocumentProcessingJob, job_id)
        doc = db.session.get(Document, document_id)
        if not job or not doc:
            return
        job.status = "failed"
        job.last_error = technical
        job.finished_at = datetime.now(timezone.utc)
        if infra:
            doc.processing_error = infrastructure_error_faculty_message()
            doc.ocr_status = prior_ocr_status
            doc.processing_status = prior_processing_status or "queued"
        else:
            doc.processing_error = faculty_safe_processing_error(technical, technical_for_logs=technical)
            doc.ocr_status = "failed"
            doc.processing_status = "failed"
        db.session.commit()
        raise


def enqueue_set_sef_job(document: Document, *, force: bool = False) -> DocumentProcessingJob:
    """Enqueue at most one active SET/SEF OCR job per document.

    ``force=True`` (Retry OCR) re-queues a long-running/abandoned job for the
    same document instead of creating a second active job.
    """
    from app.services.ocr_job_dispatch import recover_stale_jobs, schedule_ocr_job

    # Explicit retry recovers abandoned "running" rows sooner so the same job
    # is reused rather than stacking duplicates.
    recover_stale_jobs(older_than_minutes=1 if force else None)
    existing = (
        DocumentProcessingJob.query.filter_by(document_id=document.id, job_type="set_sef_ocr")
        .filter(DocumentProcessingJob.status.in_(("pending", "running")))
        .first()
    )
    if existing:
        if existing.status == "pending":
            schedule_ocr_job(existing.id, "set_sef_ocr")
        return existing
    job = DocumentProcessingJob(document_id=document.id, job_type="set_sef_ocr", status="pending")
    document.processing_status = "queued"
    document.ocr_status = "pending"
    document.processing_error = None
    db.session.add(job)
    db.session.commit()
    schedule_ocr_job(job.id, "set_sef_ocr")
    return job
