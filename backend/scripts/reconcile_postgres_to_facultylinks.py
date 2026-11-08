"""
Reconcile application data from postgres -> facultylinks (same Supabase project).
Preserves primary keys. Reports email/id conflicts without auto-resolving destructive merges.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg import sql
from psycopg.types.json import Json

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import load_backend_env  # noqa: E402

SOURCE_DB = "postgres"
TARGET_DB = "facultylinks"

APP_TABLES = (
    "users",
    "user_sessions",
    "documents",
    "reviewer_assignments",
    "notifications",
    "activity_log",
    "faculty_assessments",
    "app_settings",
    "alembic_version",
)

COPY_ORDER = (
    "users",
    "user_sessions",
    "documents",
    "reviewer_assignments",
    "faculty_assessments",
    "notifications",
    "activity_log",
    "app_settings",
    "alembic_version",
)


def _swap_db_name(dsn: str, db_name: str) -> str:
    return urlunparse(urlparse(dsn)._replace(path=f"/{db_name}"))


def _to_psycopg_dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _connect(base_url: str, db_name: str) -> psycopg.Connection:
    return psycopg.connect(_to_psycopg_dsn(_swap_db_name(base_url, db_name)))


def _table_exists(conn: psycopg.Connection, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = %s
            )
            """,
            (table,),
        )
        return bool(cur.fetchone()[0])


def _columns(conn: psycopg.Connection, table: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [r[0] for r in cur.fetchall()]


def _backup(conn: psycopg.Connection, label: str, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    meta = {"db": label, "at": datetime.now(timezone.utc).isoformat(), "tables": {}}
    with conn.cursor() as cur:
        for t in COPY_ORDER:
            if not _table_exists(conn, t):
                meta["tables"][t] = {"rows": 0, "file": None}
                continue
            cur.execute(sql.SQL("SELECT row_to_json(x) FROM {} AS x").format(sql.Identifier(t)))
            rows = [r[0] for r in cur.fetchall()]
            fname = f"{t}.json"
            (dest / fname).write_text(json.dumps(rows, default=str), encoding="utf-8")
            meta["tables"][t] = {"rows": len(rows), "file": fname}
    (dest / "manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _bind_row(row: tuple, cols: list[str]) -> tuple:
    out = list(row)
    for i, val in enumerate(out):
        if isinstance(val, dict):
            out[i] = Json(val)
    return tuple(out)


def _user_email_index(conn: psycopg.Connection) -> dict[str, int]:
    if not _table_exists(conn, "users"):
        return {}
    with conn.cursor() as cur:
        cur.execute("SELECT id, email FROM users")
        return {r[1]: r[0] for r in cur.fetchall()}


def _merge_table(
    src: psycopg.Connection,
    tgt: psycopg.Connection,
    table: str,
    conflicts: list[str],
    *,
    skip_on_email_mismatch: bool = False,
    email_index_tgt: dict[str, int] | None = None,
) -> tuple[int, int, int]:
    if not _table_exists(src, table):
        return 0, 0, 0
    if not _table_exists(tgt, table):
        conflicts.append(f"{table}: missing on {TARGET_DB} (run migrations first)")
        return 0, 0, 0

    src_cols = set(_columns(src, table))
    tgt_cols = set(_columns(tgt, table))
    cols = [c for c in _columns(src, table) if c in tgt_cols]
    if not cols:
        return 0, 0, 0

    with src.cursor() as sc:
        sc.execute(sql.SQL("SELECT {} FROM {}").format(sql.SQL(", ").join(map(sql.Identifier, cols)), sql.Identifier(table)))
        src_rows = {r[0]: r for r in sc.fetchall()}  # assumes first col is PK

    pk = cols[0]
    with tgt.cursor() as tc:
        tc.execute(sql.SQL("SELECT {} FROM {}").format(sql.Identifier(pk), sql.Identifier(table)))
        tgt_ids = {r[0] for r in tc.fetchall()}

    inserted = updated = skipped = 0
    col_idents = sql.SQL(", ").join(sql.Identifier(c) for c in cols)
    placeholders = sql.SQL(", ").join(sql.Placeholder() * len(cols))

    with tgt.cursor() as tc:
        for row_id, row in src_rows.items():
            if skip_on_email_mismatch and table == "users" and email_index_tgt is not None:
                email = row[cols.index("email")]
                existing = email_index_tgt.get(email)
                if existing is not None and existing != row_id:
                    conflicts.append(f"user email {email}: id postgres={row_id} facultylinks={existing}")
                    skipped += 1
                    continue

            if row_id not in tgt_ids:
                insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                    sql.Identifier(table), col_idents, placeholders
                )
                tc.execute(insert, _bind_row(row, cols))
                inserted += 1
                if table == "users":
                    email_index_tgt[ row[cols.index("email")] ] = row_id
            else:
                # Same PK: update only if row differs; never change PK
                with tgt.cursor() as tc2:
                    tc2.execute(
                        sql.SQL("SELECT {} FROM {} WHERE {} = %s").format(
                            col_idents, sql.Identifier(table), sql.Identifier(pk)
                        ),
                        (row_id,),
                    )
                    existing = tc2.fetchone()
                if existing == row:
                    skipped += 1
                    continue
                if table == "users":
                    ex = dict(zip(cols, existing))
                    inc = dict(zip(cols, row))
                    if ex.get("password_hash") != inc.get("password_hash"):
                        conflicts.append(
                            f"user id={row_id} email={inc.get('email')}: password_hash differed — applied {SOURCE_DB} row (same id)"
                        )
                sets = sql.SQL(", ").join(
                    sql.SQL("{} = %s").format(sql.Identifier(c)) for c in cols if c != pk
                )
                vals = _bind_row(
                    tuple(row[cols.index(c)] for c in cols if c != pk) + (row_id,),
                    [c for c in cols if c != pk] + [pk],
                )
                tc.execute(
                    sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
                        sql.Identifier(table), sets, sql.Identifier(pk)
                    ),
                    vals,
                )
                updated += 1

    tgt.commit()
    return inserted, updated, skipped


def _update_env_to_facultylinks() -> None:
    env_path = BACKEND_ROOT / ".env"
    text = env_path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if line.startswith("DATABASE_URL="):
            dsn = line.split("=", 1)[1].strip()
            line = f"DATABASE_URL={_swap_db_name(dsn, TARGET_DB)}"
        elif line.startswith("EXPECTED_DATABASE_NAME="):
            line = "EXPECTED_DATABASE_NAME=facultylinks"
        lines.append(line)
    env_path.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")


def _upgrade_target_schema(base_url: str) -> None:
    import os
    import subprocess

    env = os.environ.copy()
    env["DATABASE_URL"] = _swap_db_name(
        base_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if base_url.startswith("postgresql://")
        else base_url,
        TARGET_DB,
    )
    env["EXPECTED_DATABASE_NAME"] = TARGET_DB
    env["FLASK_APP"] = "wsgi:app"
    subprocess.run(
        [sys.executable, "-m", "flask", "db", "upgrade"],
        cwd=str(BACKEND_ROOT),
        env=env,
        check=True,
    )


def main() -> int:
    load_backend_env()
    import os

    base_url = os.environ.get("DATABASE_URL", "").strip()
    if not base_url:
        print("ERROR: DATABASE_URL not set", file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = BACKEND_ROOT / "backups" / f"reconcile_{stamp}"

    conflicts: list[str] = []

    with _connect(base_url, SOURCE_DB) as src, _connect(base_url, TARGET_DB) as tgt:
        _backup(src, SOURCE_DB, backup_root / SOURCE_DB)
        _backup(tgt, TARGET_DB, backup_root / TARGET_DB)

        src_counts = {}
        tgt_counts = {}
        for t in APP_TABLES:
            src_counts[t] = 0 if not _table_exists(src, t) else _table_counts_one(src, t)
            tgt_counts[t] = 0 if not _table_exists(tgt, t) else _table_counts_one(tgt, t)

        print("inspection", json.dumps({"postgres": src_counts, "facultylinks": tgt_counts}))

    _upgrade_target_schema(base_url)

    with _connect(base_url, SOURCE_DB) as src, _connect(base_url, TARGET_DB) as tgt:
        email_idx = _user_email_index(tgt)
        stats = {}
        for table in COPY_ORDER:
            if table == "alembic_version":
                continue
            ins, upd, skip = _merge_table(
                src,
                tgt,
                table,
                conflicts,
                skip_on_email_mismatch=(table == "users"),
                email_index_tgt=email_idx if table == "users" else None,
            )
            stats[table] = {"inserted": ins, "updated": upd, "skipped": skip}

        # alembic: take postgres version if newer target
        if _table_exists(src, "alembic_version") and _table_exists(tgt, "alembic_version"):
            with src.cursor() as sc, tgt.cursor() as tc:
                sc.execute("SELECT version_num FROM alembic_version")
                s_ver = sc.fetchone()
                tc.execute("SELECT version_num FROM alembic_version")
                t_ver = tc.fetchone()
                if s_ver and (not t_ver or s_ver[0] != t_ver[0]):
                    tc.execute("DELETE FROM alembic_version")
                    tc.execute("INSERT INTO alembic_version (version_num) VALUES (%s)", (s_ver[0],))
                    tgt.commit()
                    stats["alembic_version"] = {"set": s_ver[0]}

    if conflicts:
        print("conflicts", json.dumps(conflicts, indent=2))

    _update_env_to_facultylinks()
    print("OK reconcile")
    print("backup_dir", str(backup_root.relative_to(BACKEND_ROOT.parent)))
    print("merge_stats", json.dumps(stats, indent=2))
    return 0


def _table_counts_one(conn: psycopg.Connection, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
        return int(cur.fetchone()[0])


if __name__ == "__main__":
    raise SystemExit(main())
