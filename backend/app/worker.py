"""
Background worker for document OCR jobs.

Usage (from backend/, with venv active):
  python -m app.worker

Requires Tesseract on PATH for scanned PDFs (optional if PDFs have embedded text).
"""

from __future__ import annotations

import logging
import time

from app import create_app
from app.extensions import db
from app.models import DocumentProcessingJob
from app.services.database_check import assert_expected_database
from app.services.set_sef_processor import process_set_sef_document

_log = logging.getLogger(__name__)
POLL_SECONDS = 5


def run_once(app) -> int:
    processed = 0
    with app.app_context():
        assert_expected_database()
        job = (
            DocumentProcessingJob.query.filter_by(status="pending", job_type="set_sef_ocr")
            .order_by(DocumentProcessingJob.created_at.asc())
            .first()
        )
        if not job:
            return 0
        try:
            process_set_sef_document(job.document_id, job.id)
            processed = 1
        except Exception:
            _log.exception("Job %s failed", job.id)
    return processed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = create_app()
    _log.info("SET/SEF OCR worker started (poll every %ss)", POLL_SECONDS)
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
