"""
One-time copy: facultylinks DB → same host's postgres DB (Supabase default).
Does not print secrets. Aborts without touching .env on failure.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg import sql

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import load_backend_env  # noqa: E402

APP_TABLES = (
    "users",
    "user_sessions",
    "documents",
    "reviewer_assignments",
    "alembic_version",
)

COPY_ORDER = (
    "users",
    "user_sessions",
    "documents",
    "reviewer_assignments",
    "alembic_version",
)

SOURCE_DB = "facultylinks"
TARGET_DB = "postgres"


def _swap_db_name(dsn: str, db_name: str) -> str:
    parsed = urlparse(dsn)
    return urlunparse(parsed._replace(path=f"/{db_name}"))


def _to_psycopg_dsn(sqlalchemy_url: str) -> str:
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _connect(sqlalchemy_url: str, db_name: str) -> psycopg.Connection:
    return psycopg.connect(_to_psycopg_dsn(_swap_db_name(sqlalchemy_url, db_name)))


def _table_counts(conn: psycopg.Connection, tables: tuple[str, ...]) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    with conn.cursor() as cur:
        for t in tables:
            cur.execute(
                """
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.tables
                  WHERE table_schema = 'public' AND table_name = %s
                )
                """,
                (t,),
            )
            if not cur.fetchone()[0]:
                out[t] = None
                continue
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(t)))
            out[t] = int(cur.fetchone()[0])
    return out


def _backup_tables(conn: psycopg.Connection, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    meta = {"at": datetime.now(timezone.utc).isoformat(), "source_db": SOURCE_DB, "tables": {}}
    with conn.cursor() as cur:
        for t in COPY_ORDER:
            cur.execute(
                """
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.tables
                  WHERE table_schema = 'public' AND table_name = %s
                )
                """,
                (t,),
            )
            if not cur.fetchone()[0]:
                meta["tables"][t] = {"rows": 0, "file": None}
                continue
            cur.execute(sql.SQL("SELECT row_to_json(t) FROM {} AS t").format(sql.Identifier(t)))
            rows = [r[0] for r in cur.fetchall()]
            fname = dest / f"{t}.json"
            fname.write_text(json.dumps(rows, default=str), encoding="utf-8")
            meta["tables"][t] = {"rows": len(rows), "file": fname.name}
    (dest / "manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _ensure_schema_on_target(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM pg_type t
              JOIN pg_namespace n ON n.oid = t.typnamespace
              WHERE t.typname = 'user_role' AND n.nspname = 'public'
            )
            """
        )
        if not cur.fetchone()[0]:
            cur.execute("CREATE TYPE user_role AS ENUM ('admin', 'reviewer', 'faculty')")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = 'users'
            )
            """
        )
        if cur.fetchone()[0]:
            return

    ddl = """
    CREATE TABLE users (
      id SERIAL PRIMARY KEY,
      email VARCHAR(320) NOT NULL UNIQUE,
      password_hash VARCHAR(255) NOT NULL,
      role user_role NOT NULL,
      full_name VARCHAR(200) NOT NULL,
      is_active BOOLEAN NOT NULL,
      created_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX ix_users_email ON users (email);

    CREATE TABLE documents (
      id SERIAL PRIMARY KEY,
      public_id VARCHAR(36) NOT NULL UNIQUE,
      owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      object_key VARCHAR(512) NOT NULL UNIQUE,
      original_filename VARCHAR(255) NOT NULL,
      mime_type VARCHAR(127) NOT NULL,
      size_bytes BIGINT NOT NULL,
      upload_status VARCHAR(32) NOT NULL,
      created_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX ix_documents_owner_user_id ON documents (owner_user_id);
    CREATE INDEX ix_documents_public_id ON documents (public_id);

    CREATE TABLE reviewer_assignments (
      id SERIAL PRIMARY KEY,
      reviewer_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      faculty_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      created_at TIMESTAMPTZ NOT NULL,
      CONSTRAINT uq_reviewer_faculty UNIQUE (reviewer_user_id, faculty_user_id)
    );
    CREATE INDEX ix_reviewer_assignments_reviewer_user_id ON reviewer_assignments (reviewer_user_id);
    CREATE INDEX ix_reviewer_assignments_faculty_user_id ON reviewer_assignments (faculty_user_id);

    CREATE TABLE user_sessions (
      id SERIAL PRIMARY KEY,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      token_hash VARCHAR(64) NOT NULL UNIQUE,
      expires_at TIMESTAMPTZ NOT NULL,
      created_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);
    CREATE INDEX ix_user_sessions_token_hash ON user_sessions (token_hash);

    CREATE TABLE alembic_version (
      version_num VARCHAR(32) NOT NULL PRIMARY KEY
    );
    """
    with conn.cursor() as cur:
        cur.execute(ddl)


def _copy_table(src: psycopg.Connection, tgt: psycopg.Connection, table: str) -> int:
    with src.cursor() as sc:
        sc.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table)))
        cols = [d.name for d in sc.description]
        rows = sc.fetchall()
    if not rows:
        return 0
    col_idents = sql.SQL(", ").join(sql.Identifier(c) for c in cols)
    placeholders = sql.SQL(", ").join(sql.Placeholder() * len(cols))
    insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table),
        col_idents,
        placeholders,
    )
    with tgt.cursor() as tc:
        tc.executemany(insert, rows)
    return len(rows)


def _fix_sequences(conn: psycopg.Connection) -> None:
    serial_tables = ("users", "user_sessions", "documents", "reviewer_assignments")
    with conn.cursor() as cur:
        for t in serial_tables:
            cur.execute(
                f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {t}), 1), true)"
            )


def _apply_api_lockdown(conn: psycopg.Connection) -> None:
    """Block Supabase Data API (anon/authenticated) on application tables."""
    with conn.cursor() as cur:
        for t in APP_TABLES:
            cur.execute(
                sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(sql.Identifier(t))
            )
            cur.execute(
                sql.SQL("REVOKE ALL ON TABLE {} FROM anon, authenticated").format(sql.Identifier(t))
            )


def _update_env_file() -> None:
    env_path = BACKEND_ROOT / ".env"
    text = env_path.read_text(encoding="utf-8")
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("DATABASE_URL="):
            val = line.split("=", 1)[1]
            if "/facultylinks" in val:
                line = line.replace("/facultylinks", "/postgres", 1)
        elif line.startswith("EXPECTED_DATABASE_NAME="):
            line = "EXPECTED_DATABASE_NAME=postgres"
        lines.append(line)
    env_path.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")


def main() -> int:
    load_backend_env()
    import os

    base_url = os.environ.get("DATABASE_URL", "").strip()
    if not base_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1
    if SOURCE_DB not in urlparse(base_url).path:
        print(
            "ERROR: DATABASE_URL does not target facultylinks — refusing to migrate "
            "(already switched or unexpected setup).",
            file=sys.stderr,
        )
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = BACKEND_ROOT / "backups" / f"facultylinks_{stamp}"

    with _connect(base_url, SOURCE_DB) as src:
        src_counts = _table_counts(src, APP_TABLES)
        _backup_tables(src, backup_dir)

    with _connect(base_url, TARGET_DB) as tgt:
        tgt_counts = _table_counts(tgt, APP_TABLES)

        conflicts = [
            t
            for t in APP_TABLES
            if tgt_counts.get(t) is not None and (tgt_counts[t] or 0) > 0
        ]
        if conflicts:
            print(f"ERROR: target postgres has data in {conflicts} — aborting.", file=sys.stderr)
            return 1

        _ensure_schema_on_target(tgt)
        tgt.commit()

        # Re-check after schema ensure (empty tables only)
        tgt_counts = _table_counts(tgt, APP_TABLES)
        conflicts = [
            t
            for t in APP_TABLES
            if tgt_counts.get(t) is not None and (tgt_counts[t] or 0) > 0
        ]
        if conflicts:
            print(f"ERROR: unexpected rows after schema create: {conflicts}", file=sys.stderr)
            return 1

    with _connect(base_url, SOURCE_DB) as src, _connect(base_url, TARGET_DB) as tgt:
        copied: dict[str, int] = {}
        try:
            for t in COPY_ORDER:
                if src_counts.get(t) is None:
                    copied[t] = 0
                    continue
                copied[t] = _copy_table(src, tgt, t)
            _fix_sequences(tgt)
            _apply_api_lockdown(tgt)
            tgt.commit()
        except Exception:
            tgt.rollback()
            raise

    with _connect(base_url, TARGET_DB) as tgt:
        new_counts = _table_counts(tgt, APP_TABLES)

    for t in APP_TABLES:
        src_n = src_counts.get(t) or 0
        tgt_n = new_counts.get(t) or 0
        if src_n != tgt_n:
            print(f"ERROR: row count mismatch {t}: source={src_n} target={tgt_n}", file=sys.stderr)
            return 1

    _update_env_file()
    print("OK migrate")
    print(f"backup_dir {backup_dir.relative_to(BACKEND_ROOT.parent)}")
    print("source_counts", json.dumps({k: (v or 0) for k, v in src_counts.items()}))
    print("target_counts", json.dumps({k: (v or 0) for k, v in new_counts.items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
