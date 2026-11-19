# General document OCR and rule-based validation

SET/SEF teaching-effectiveness PDFs continue to use the dedicated pipeline in `docs/SET_SEF_OCR.md`. This document covers **all other** supported uploads (PDFs and images).

## What is stored where

| Data | Table / fields |
|------|----------------|
| Processing status / errors | `documents.ocr_status`, `documents.processing_status`, `documents.processing_error`, `documents.file_sha256` |
| Extracted full text + page sources | `document_extractions` (`full_text`, `pages_json`, `extraction_method`, timestamps, versions) |
| SET/SEF semester ratings | `set_sef_semester_records` (unchanged) |
| Generic extracted fields (title/name/date) | `document_extracted_fields` (`value_extracted` vs `value_confirmed`) |
| Validation findings | `document_validation_findings` with `pipeline` = `general` or `set_sef` |
| Suggested KRA | `document_classifications` |
| Job queue | `document_processing_jobs` (`job_type` = `general_ocr` or `set_sef_ocr`) |

## Worker

```bash
cd backend
# activate venv
python -m app.worker
```

Dependencies: `pymupdf`, `pytesseract`, `Pillow`, and Tesseract OCR (`TESSERACT_CMD` on Windows if needed). Check `/api/health` → `ocr.ready`.

## APIs

- `GET /api/documents/<id>/validation` — extraction, fields, classification, findings
- `POST /api/documents/<id>/validation/retry-ocr` — idempotent requeue
- `PATCH /api/documents/<id>/validation/fields/<fieldId>` — reviewer corrections

General OCR **does not** award points or approve evidence.

## Scoped reprocess

```bash
python scripts/reprocess_general_ocr.py --public-id <uuid> --run-now
python scripts/reprocess_general_ocr.py --owner-email faculty@example.com --limit 20
```

Refuses unscoped full-database runs.

## Rule coverage

OCR content checks are **catalog-driven** (`fl-doc-content-1.2`) and follow the
faculty-selected hierarchy **KRA → criterion → indicator** (plus the assessment’s
pinned catalog/rule version):

1. Prefer `fields` on the assessment/published catalog indicator.
2. If omitted in the published JSON, fall back to the workbook field map
   `app/services/catalog_indicator_fields.json` (generated from
   `admin_reviewer_web/js/core/*-catalog.js` + assessment definitions).
3. Only OCR-applicable fields are checked on the file:
   `title`, `date`/`achievementDate`, `publicationIdentifier`, `patentNumber`,
   `productName`, `softwareTitle`.
4. Achievement-form fields (`description`, `authorRole`, tiers, hours, …) are
   noted as form-only — not inventing title/author/date for every document.
5. SET/SEF indicators → dedicated SET/SEF pipeline (`coverage_set_sef_pipeline`).
6. `kra-I-A-special` → readable supporting-text check.
7. A coverage entry documents configured assistive checks; it does **not** mean
   the indicator is fully validated or auto-approved. Manual-review gaps are
   listed explicitly in the API (`coverage.manualReviewGaps`) and audit report.
8. Certificate-style KRA III/IV (and similar) documents may run **advisory**
   honoree/recipient name extraction (`faculty_identity_advisory`); a match is
   not ownership proof.
9. Each OCR run persists `validation_configuration_snapshot` (catalog/content
   rule versions used). Unresolved `documents.config_version` values surface a
   warning in `GET .../validation` (`configuration.warning`).

Uploads should send `indicatorId`, parent `kraId`, and `criterionId`. The server
validates that the indicator belongs to that criterion and KRA.

Regenerate the field map after workbook catalog edits:

```bash
cd admin_reviewer_web
node scripts/dump-indicator-fields.mjs
```

Audit coverage (writes `backend/reports/ocr_validation_coverage.{json,md}`):

```bash
cd backend
PYTHONPATH=. python scripts/audit_content_rule_coverage.py
```

KRA keyword suggestions follow manuscript Table 5 heuristics and never silently reassign the faculty-selected KRA.
