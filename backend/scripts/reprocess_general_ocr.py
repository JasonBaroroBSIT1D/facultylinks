"""
Scoped backfill / reprocess for general (non–SET/SEF) document OCR.

Examples (from backend/, venv active):
  python scripts/reprocess_general_ocr.py --public-id <uuid>
  python scripts/reprocess_general_ocr.py --owner-email someone@example.com --limit 20
  python scripts/reprocess_general_ocr.py --public-id <uuid> --run-now

Does NOT process the entire database unless you pass an explicit filter.
Preserves document IDs, storage keys, review decisions, and confirmed field corrections.
"""

from __future__ import annotations

import argparse
import sys

from app import create_app
from app.extensions import db
from app.models import Document, DocumentProcessingJob, User
from app.services.document_ocr_processor import JOB_TYPE, enqueue_general_ocr_job, process_general_ocr_document
from app.services.document_text import supports_general_ocr
from app.services.set_sef_document import is_set_sef_document


def main() -> int:
    parser = argparse.ArgumentParser(description="Enqueue or run general OCR for scoped documents.")
    parser.add_argument("--public-id", help="Single document public UUID")
    parser.add_argument("--owner-email", help="Limit to one faculty email")
    parser.add_argument("--limit", type=int, default=25, help="Max documents (default 25)")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Process jobs immediately in this process (otherwise enqueue for worker)",
    )
    parser.add_argument(
        "--include-completed",
        action="store_true",
        help="Also requeue documents that already completed OCR",
    )
    args = parser.parse_args()

    if not args.public_id and not args.owner_email:
        print("Refusing unscoped run. Pass --public-id and/or --owner-email.", file=sys.stderr)
        return 2

    app = create_app()
    with app.app_context():
        q = Document.query.filter(Document.upload_status == "stored")
        if args.public_id:
            q = q.filter(Document.public_id == args.public_id)
        if args.owner_email:
            owner = User.query.filter_by(email=args.owner_email.strip().lower()).first()
            if not owner:
                print("Owner not found", file=sys.stderr)
                return 1
            q = q.filter(Document.owner_user_id == owner.id)
        docs = q.order_by(Document.id.asc()).limit(max(1, args.limit)).all()
        selected = []
        for doc in docs:
            if is_set_sef_document(doc):
                continue
            if not supports_general_ocr(doc.mime_type):
                continue
            if not args.include_completed and doc.processing_status == "completed":
                continue
            selected.append(doc)

        print(f"Selected {len(selected)} document(s)")
        for doc in selected:
            job = enqueue_general_ocr_job(doc)
            if not job:
                print(doc.public_id, "skip")
                continue
            print(doc.public_id, "job", job.id, job.status)
            if args.run_now:
                # Ensure a pending job row for process function
                if job.status != "pending":
                    job = DocumentProcessingJob(
                        document_id=doc.id, job_type=JOB_TYPE, status="pending"
                    )
                    db.session.add(job)
                    db.session.commit()
                process_general_ocr_document(doc.id, job.id)
                db.session.refresh(doc)
                print("  ->", doc.ocr_status, doc.processing_status, (doc.processing_error or "")[:80])
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
