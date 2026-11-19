"""Dispatch OCR jobs without relying solely on a separate worker process.

The dedicated ``python -m app.worker`` loop remains supported for batch/stale
recovery. Enqueue paths also schedule a short-lived daemon thread so uploads
do not sit forever at queued/pending when no worker terminal is open.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone

from flask import current_app

_log = logging.getLogger(__name__)
_STALE_RUNNING_MINUTES = 15


def recover_stale_jobs(*, older_than_minutes: int | None = None) -> int:
    """Re-queue jobs stuck in ``running`` (crashed worker / abandoned thread)."""
    from app.extensions import db
    from app.models import Document, DocumentProcessingJob

    minutes = _STALE_RUNNING_MINUTES if older_than_minutes is None else max(0, int(older_than_minutes))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    stale = (
        DocumentProcessingJob.query.filter(
            DocumentProcessingJob.status == "running",
            DocumentProcessingJob.started_at.isnot(None),
            DocumentProcessingJob.started_at < cutoff,
        ).all()
    )
    for job in stale:
        job.status = "pending"
        prior = (job.last_error or "").strip()
        note = f"Recovered stale running job after {minutes}m."
        job.last_error = f"{prior} | {note}"[:480] if prior else note
        doc = db.session.get(Document, job.document_id)
        if doc and doc.processing_status == "processing":
            doc.processing_status = "queued"
            if doc.ocr_status == "processing":
                doc.ocr_status = "pending"
        _log.warning("Re-queued stale OCR job %s (document %s)", job.id, job.document_id)
    if stale:
        db.session.commit()
    return len(stale)


def schedule_ocr_job(job_id: int, job_type: str) -> None:
    """Run one pending job in a daemon thread using the current Flask app."""
    app = current_app._get_current_object()

    def _run() -> None:
        with app.app_context():
            try:
                from app.extensions import db
                from app.models import DocumentProcessingJob
                from app.services.document_ocr_processor import process_general_ocr_document
                from app.services.set_sef_processor import process_set_sef_document

                job = db.session.get(DocumentProcessingJob, job_id)
                if not job or job.status != "pending":
                    return
                if job.job_type == "set_sef_ocr":
                    process_set_sef_document(job.document_id, job.id)
                elif job.job_type == "general_ocr":
                    process_general_ocr_document(job.document_id, job.id)
                else:
                    job.status = "failed"
                    job.last_error = f"Unknown job_type: {job.job_type}"
                    db.session.commit()
            except Exception:
                _log.exception("Inline OCR job %s (%s) failed", job_id, job_type)

    threading.Thread(
        target=_run,
        name=f"ocr-{job_type}-{job_id}",
        daemon=True,
    ).start()
