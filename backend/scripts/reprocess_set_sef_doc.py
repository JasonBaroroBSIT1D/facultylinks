"""Re-run SET/SEF OCR pipeline for one document (idempotent; preserves verified fields)."""
import sys

from app import create_app
from app.extensions import db
from app.models import Document, DocumentProcessingJob, SetSefSemesterRecord
from app.services.set_sef_processor import process_set_sef_document

public_id = sys.argv[1] if len(sys.argv) > 1 else "4dbd48ca-a190-4579-87aa-ca251f16b35c"

app = create_app()
with app.app_context():
    doc = Document.query.filter_by(public_id=public_id).first()
    if not doc:
        print("not found")
        sys.exit(1)
    job = DocumentProcessingJob(document_id=doc.id, job_type="set_sef_ocr", status="pending")
    db.session.add(job)
    db.session.commit()
    process_set_sef_document(doc.id, job.id)
    db.session.refresh(doc)
    recs = SetSefSemesterRecord.query.filter_by(document_id=doc.id, superseded_by_id=None).all()
    print("ocr", doc.ocr_status, "proc", doc.processing_status, "err", doc.processing_error)
    print("active records", len(recs))
    for r in recs:
        print(r.semester_key, r.faculty_name_extracted, r.set_rating_extracted, r.sef_rating_extracted)
