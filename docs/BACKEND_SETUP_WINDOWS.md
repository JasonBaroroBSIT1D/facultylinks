# FacultyLink backend — Windows setup

## Prerequisites

- Python 3.11+ (`python --version`)
- Git
- Supabase project with database `facultylinks` and private bucket `facultylinks-documents` ([CLOUD_SETUP.md](./CLOUD_SETUP.md))

## 1. Virtual environment

```powershell
cd C:\Users\gumat\OneDrive\Desktop\facultylinks\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Environment

```powershell
copy .env.example .env
# Edit .env — set DATABASE_URL, SECRET_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
```

Never commit `.env`.

## 3. Database migrations

```powershell
$env:FLASK_APP = "wsgi:app"
flask db init
flask db migrate -m "initial auth documents"
flask db upgrade
```

If `flask db init` says migrations already exist, skip `init` and run `migrate` + `upgrade` only.

Confirm `GET /api/health` returns `"databaseName":"facultylinks"` (not merely the Supabase project display name).

## 4. Create administrator (no auto-seed)

```powershell
flask create-admin admin@yourinstitution.edu "YourSecurePass1!"
```

Optional test accounts:

```powershell
flask create-user reviewer reviewer@yourinstitution.edu "ReviewPass1!" --name "Demo Reviewer"
flask create-user faculty faculty@yourinstitution.edu "FacultyPass1!" --name "Demo Faculty"
flask assign-reviewer reviewer@yourinstitution.edu faculty@yourinstitution.edu
```

## 5. Run API

```powershell
python run.py
```

Health check (no secrets):

```powershell
curl http://127.0.0.1:5000/api/health
```

Expect `"database":"connected"`, `"databaseName":"facultylinks"`, and `"storage":"configured"` when `.env` is complete.

## 6. Run web against API

Terminal 1 — API (port 5000). Terminal 2 — static web:

```powershell
cd ..\admin_reviewer_web
python serve.py 5173
```

Optional: before loading login, set API base in browser console or in `login.html`:

```html
<script>window.__FACULTYLINK_API_BASE__ = 'http://127.0.0.1:5000';</script>
```

(Default is already `http://127.0.0.1:5000`.)

Sign in with the **admin** account you created—not demo emails unless you created matching users.

## 7. Flutter

```powershell
cd ..\faculty_mobile
flutter pub get
flutter run --dart-define=FACULTYLINK_API_BASE=http://127.0.0.1:5000
```

On a physical device, use your PC’s LAN IP instead of `127.0.0.1`, and add that origin to `CORS_ORIGINS` if needed.

## 8. Smoke tests (manual)

| Check | How |
|--------|-----|
| DB name | Health shows `databaseName` = `facultylinks` |
| Migrations | `flask db upgrade` succeeds |
| Login / logout | Web admin; `GET /api/auth/me` with cookie |
| Role gate | Faculty token cannot access admin-only routes |
| Upload | Faculty `POST /api/documents` with PDF |
| Private access | `GET /api/documents/{id}/view-url` returns short-lived URL |
| Deny other faculty | Second faculty user gets 403 on another’s document |
| Secrets | No passwords in repo, JS bundles, or Flutter assets |

## 9. Verification script (optional)

```powershell
python scripts/verify_backend.py
```

Runs health check only when `DATABASE_URL` is set.
