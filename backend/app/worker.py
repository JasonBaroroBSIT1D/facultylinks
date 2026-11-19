"""
Background worker for document OCR jobs (SET/SEF + general).

Usage (from backend/, with venv active):
  python -m app.worker

Requires Tesseract on PATH (or TESSERACT_CMD) for scanned PDFs and images.
Keep Flask (`python run.py`) running separately.
"""

from __future__ import annotations

import logging
import time

from app import create_app
from app.extensions import db
from app.models import DocumentProcessingJob
from app.services.database_check import assert_expected_database
from app.services.document_ocr_processor import process_general_ocr_document
from app.services.ocr_job_dispatch import recover_stale_jobs
from app.services.set_sef_processor import process_set_sef_document

_log = logging.getLogger(__name__)
POLL_SECONDS = 5


def _claim_next_job() -> DocumentProcessingJob | None:
    job = (
        DocumentProcessingJob.query.filter(
            DocumentProcessingJob.status == "pending",
            DocumentProcessingJob.job_type.in_(("set_sef_ocr", "general_ocr")),
        )
        .order_by(DocumentProcessingJob.created_at.asc())
        .first()
    )
    return job


def run_once(app) -> int:
    processed = 0
    with app.app_context():
        assert_expected_database()
        recover_stale_jobs()
        job = _claim_next_job()
        if not job:
            return 0
        # Skip if another dispatcher already claimed this job.
        if job.status != "pending":
            return 0
        try:
            if job.job_type == "set_sef_ocr":
                process_set_sef_document(job.document_id, job.id)
            elif job.job_type == "general_ocr":
                process_general_ocr_document(job.document_id, job.id)
            else:
                job.status = "failed"
                job.last_error = f"Unknown job_type: {job.job_type}"
                db.session.commit()
            processed = 1
        except Exception:
            _log.exception("Job %s failed", job.id)
    return processed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = create_app()
    _log.info("Document OCR worker started (SET/SEF + general; poll every %ss)", POLL_SECONDS)
    while True:
        try:
            n = run_once(app)
            if n:
                _log.info("Processed %s job(s)", n)
        except Exception:
            _log.exception("Worker loop error")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
