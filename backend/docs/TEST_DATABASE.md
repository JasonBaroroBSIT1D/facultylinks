# Pytest database isolation

Pytest **must not** use the live `facultylinks` application database.

1. Create database `facultylinks_test` on the same Supabase project (SQL: `CREATE DATABASE facultylinks_test;` — or use a separate local Postgres).
2. Copy `backend/.env.test.example` and set `TEST_DATABASE_URL` to that database (different path/name than `DATABASE_URL`).
3. Run tests:

```powershell
cd backend
$env:FACULTYLINK_PYTEST = "1"
$env:TEST_DATABASE_URL = "postgresql+psycopg://.../facultylinks_test?sslmode=require"
python -m pytest
```

If `TEST_DATABASE_URL` is missing or points at `facultylinks`, pytest exits before any test runs.

## Production test-account inventory (read-only)

```powershell
python scripts/inventory_suspected_test_accounts.py
python scripts/cleanup_test_accounts.py --dry-run
```

Review `scripts/output/test_account_manifest.json` before any deletion.