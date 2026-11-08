# Backend Integration Guide

## Live stack (phase 1 — see `backend/`)
- **API:** Flask 3.x REST (`backend/run.py`, port 5000 by default)
- **Database:** PostgreSQL (`facultylinks`) via Supabase
- **Storage:** Private Supabase Storage bucket `facultylinks-documents` (signed URLs from Flask)

## Target stack (manuscript / later)
- **Database:** PostgreSQL 18
- **OCR:** Tesseract 5.5 (server-side)
- **Auth:** Institution-issued accounts (JWT or session); replace `MockAuthRepository`

## Replace mock layers
| Frontend module | Future endpoint (illustrative) |
|-----------------|--------------------------------|
| `MockAuthRepository` | `POST /api/auth/login`, `POST /api/auth/forgot-password` |
| `MockFacultyRepository` | `/api/admin/faculty`, `/api/reviewer/assignments` |
| `MockDocumentRepository` | `/api/documents`, upload multipart |
| `MockAssessmentRepository` | `/api/assessments`, `/api/entries` |
| `MockConfigRepository` | `/api/config/assessment-rules` (versioned) |
| `institutionConfig.preparationPeriod` (web) / `InstitutionConfigRepository` (Flutter) | `GET/PUT /api/institution/evaluation-period` — see `docs/EVALUATION_PERIOD.md` |
| `assessment-definitions.js` / Dart `assessment_catalog.dart` | Load from `GET /api/config/catalog` with same stable IDs |

## Stable IDs
Keep `kra-*`, `crit-*`, `ind-*` IDs identical across web, mobile, and API payloads.

## OCR & review
- `ocrStatus`: `pending` | `completed` | `failed` | `simulated`
- `reviewStatus`: separate from OCR; reviewer actions only via authenticated reviewer role.

## Sync
Web and mobile currently use **independent** `localStorage` / SharedPreferences mock stores. Admin and Reviewer on the **same origin** share one `localStorage` key and refresh via the `storage` event. Flutter keeps a matching **demonstration** schedule only — **no automatic web-to-mobile sync** in this phase. After integration, all clients consume the same evaluation-period API.
