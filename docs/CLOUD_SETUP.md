# Cloud setup — Supabase (PostgreSQL + Storage)

**Nothing in this repository creates a Supabase project for you.** Put secrets only in `backend/.env` (never in Git, web JS, or Flutter).

FacultyLink uses **one Supabase project** for:

| Piece | Supabase service | FacultyLink setting |
|--------|------------------|---------------------|
| **PostgreSQL** | Hosted Postgres | `DATABASE_URL` → database name **`facultylinks`** |
| **Private files** | Storage | Bucket **`facultylinks-documents`** + `SUPABASE_*` in `.env` |

**We do not use Supabase Auth.** Login stays on the Flask API (Argon2, cookies, bearer tokens).

---

## Project name vs database name

| Name | What it is | Can you set it to `facultylinks`? |
|------|------------|-----------------------------------|
| **Supabase project name** | Label in the dashboard (e.g. “FacultyLink”) | Yes, at creation — cosmetic only |
| **Default Postgres database** | Always **`postgres`** on a new project | Supabase does not let you rename this default DB |
| **Database `facultylinks`** | A **second** database you create with SQL | Yes — Flask should connect to **`/facultylinks`** in the connection string |

Renaming the **project** in the dashboard does **not** change any Postgres database name.

If you create `facultylinks` with `CREATE DATABASE`, it works for direct SQLAlchemy connections, but that database is **not** the same as Supabase’s integrated `postgres` DB (Auth/Storage metadata still use `postgres`). That is fine for FacultyLink: we only use Postgres for our own tables and use the Storage API for files.

Official notes:

- [Connecting to Postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Manually created databases and the dashboard](https://supabase.com/kb/troubleshooting/manually-created-databases-are-not-visible-in-the-supabase-dashboard-4415aa)

---

## Payment / free tier (read before enabling paid features)

- **Free plan** includes a hosted Postgres instance, Storage, and API keys — enough for development and small pilots.
- Limits apply (database size, egress, Storage size, etc.). Check [Supabase pricing](https://supabase.com/pricing) before production.
- **Do not add a payment method or upgrade** unless you explicitly choose to.
- Pausing: inactive free projects may be paused per Supabase policy — restore from the dashboard if that happens.

---

## Step 1 — Create a Supabase account and project

1. Open [https://supabase.com/dashboard](https://supabase.com/dashboard) and sign in (or sign up).
2. **New project**
   - **Name:** e.g. `FacultyLink` (any display name).
   - **Database password:** generate a strong password and **save it locally** (password manager). You will put it only in `backend/.env`.
   - **Region:** choose one close to you.
3. Wait until the project status is **Healthy**.

You do **not** have a usable `facultylinks` database yet — only the default `postgres` database exists.

---

## Step 2 — Create the PostgreSQL database `facultylinks`

1. Dashboard → **SQL Editor** → **New query**.
2. Run:

```sql
CREATE DATABASE facultylinks;
```

3. If this succeeds, Postgres now has a database named exactly `facultylinks`.

**Verify (optional):** SQL Editor — connect using the default connection, then:

```sql
SELECT datname FROM pg_database WHERE datname = 'facultylinks';
```

You should see one row. Tables for FacultyLink are created later with `flask db upgrade` **after** `DATABASE_URL` points at `facultylinks`.

---

## Step 3 — Copy a connection string for `facultylinks`

1. Dashboard → **Connect** (or **Project Settings → Database**).
2. Prefer **Session pooler** (IPv4-friendly) or **Direct connection** for a long-running Flask app on your PC.
3. Choose the connection that lets you set the **database** (or edit the URI path) to **`facultylinks`**, not `postgres`.
4. Copy the URI and adapt it for SQLAlchemy in `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/facultylinks?sslmode=require
```

If the dashboard shows `postgresql://`, our config accepts it and normalizes to `postgresql+psycopg://`. Passwords with special characters must be **URL-encoded**.

5. Set:

```env
EXPECTED_DATABASE_NAME=facultylinks
```

The API health check compares `SELECT current_database()` to this value.

**Transaction pooler (port 6543):** supported; `app/config.py` sets `prepare_threshold=None` for psycopg when port `6543` is detected.

---

## Step 4 — API keys (backend only)

1. **Project Settings → API**
2. Copy **Project URL** → `SUPABASE_URL` in `.env`
3. Copy **service_role** key (secret) → `SUPABASE_SERVICE_ROLE_KEY` in `.env`

Never put the service role key in the web app, Flutter app, or Git. The anon key is not required for this phase.

---

## Step 5 — Private Storage bucket

1. Dashboard → **Storage** → **New bucket**
2. **Name:** `facultylinks-documents` (must match `SUPABASE_STORAGE_BUCKET` in `.env.example`).
3. **Public bucket:** **OFF** (private).
4. Create the bucket.

Flask uploads with the **service role** and returns **short-lived signed URLs** only after your existing role/assignment checks pass.

Optional: under **Storage → Policies**, you can leave default RLS; backend access uses the service role. Do not make the bucket public.

---

## Step 6 — Fill `backend/.env`

```powershell
cd backend
copy .env.example .env
```

Set at minimum:

- `SECRET_KEY` (long random string)
- `DATABASE_URL` (path ends with `/facultylinks`)
- `EXPECTED_DATABASE_NAME=facultylinks`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET=facultylinks-documents`

Do not paste these values into chat.

---

## Step 7 — After `.env` is saved (on your machine)

Follow [BACKEND_SETUP_WINDOWS.md](./BACKEND_SETUP_WINDOWS.md):

1. `pip install -r requirements.txt`
2. `flask db upgrade`
3. `flask create-admin ...`
4. `python run.py`
5. `GET /api/health` — expect `"database":"connected"`, `"databaseName":"facultylinks"`, `"storage":"configured"`, `"storageProvider":"supabase"`

Until you complete the steps above, **no cloud resources are verified from this repo**.

---

## Removed providers

Neon, Cloudflare R2, and Backblaze B2 are no longer used. Delete any old `S3_*` entries from your local `.env` if they remain from an earlier setup.
