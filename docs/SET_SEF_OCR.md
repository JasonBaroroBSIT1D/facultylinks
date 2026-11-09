# SET/SEF combined PDF — OCR pipeline

## Dependencies

- **Python packages** (in `backend/requirements.txt`): `pymupdf`, `pytesseract`, `Pillow`
- **Tesseract OCR** (optional for scanned PDFs): install [Tesseract 5.x](https://github.com/tesseract-ocr/tesseract) and ensure `tesseract` is on `PATH`
- **Supabase Storage** configured in `backend/.env` (uploads download through the service role)

## Worker

From `backend/` with the virtual environment active:

```bash
python -m app.worker
```

The worker polls `document_processing_jobs` every 5 seconds and runs SET/SEF OCR for `job_type = set_sef_ocr`.

Keep Flask (`python run.py`) and the worker running in separate terminals during development.

## Faculty upload

- Indicator id: `kra-I-A-setsef-combined`
- KRA id: `kra-I-A`
- MIME: `application/pdf` only

## APIs

- `GET /api/documents/<id>/set-sef` — extraction, validation findings, scoring
- `POST /api/documents/<id>/set-sef/retry-ocr` — safe OCR retry (no duplicate active job)
- `PATCH /api/documents/<id>/set-sef/semesters/<record_id>` — reviewer corrections / per-rating verification

## Migration

```bash
flask db upgrade
```

Target database must be **facultylinks** (`EXPECTED_DATABASE_NAME`).

## Extraction behavior

- Each PDF page uses embedded text when it is readable; otherwise the page is rendered and passed to Tesseract.
- Mixed PDFs choose the better of embedded vs OCR text per page (not filename).
- **Summary tables** (e.g. “Students Rating” / “Supervisor Rating” rows per semester) map student column → SET and supervisor column → SEF.
- Separate SET/SEF form layouts still use the block parser (academic year, semester, overall rating phrases).

Jobs finish with `processing_status=completed`, but `ocr_status` is **`failed`** when no ratings are parsed, or **`review_required`** when validation needs a human. Completion is not treated as successful extraction when fields are blank.

## Safe reprocess (no re-upload)

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\reprocess_set_sef_doc.py <document-public-id>
```

Or `POST /api/documents/<id>/set-sef/retry-ocr` and ensure the worker is running. Reprocessing **supersedes** prior semester rows and **preserves** reviewer-confirmed ratings and verified flags per semester key.
