#!/usr/bin/env python3
"""
Read-only inventory of users that match pytest fixture fingerprints on the APPLICATION database.

Usage (dry-run only — no writes):
  cd backend
  python scripts/inventory_suspected_test_accounts.py --dry-run

Does not print DATABASE_URL, passwords, or tokens.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# Application DB only — never TEST_DATABASE_URL
os.environ.pop("FACULTYLINK_PYTEST", None)
os.environ.pop("TEST_DATABASE_URL", None)

from sqlalchemy import create_engine, text

from app.config import Config, load_backend_env
from app.test_db_guard import database_identity, fingerprint

FIXTURE_NAMES = frozenset({"Rev One", "Rev Two", "Fac One", "Fac Two", "Owner", "Rev"})
PLACEHOLDER_HASH = "x"


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory suspected pytest-created accounts (read-only).")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Default; no database writes.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable manifest.")
    args = parser.parse_args()
    if not args.dry_run:
        print("This script is inventory-only. Use cleanup_test_accounts.py --dry-run for deletion preview.")
        return 1

    load_backend_env()
    url = Config.SQLALCHEMY_DATABASE_URI
    if not url:
        print("DATABASE_URL is not configured.", file=sys.stderr)
        return 2
    host, dbname = database_identity(url)
    if dbname != "facultylinks":
        print(f"Refusing: connected database name is '{dbname}', expected application DB 'facultylinks'.", file=sys.stderr)
        return 2

    engine = create_engine(url, pool_pre_ping=True)
    candidates = []
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT u.id, u.email, u.role::text, u.full_name, u.password_hash,
                       u.created_at, u.employee_id, u.is_active,
                       (SELECT count(*) FROM reviewer_assignments ra
                        WHERE ra.reviewer_user_id = u.id OR ra.faculty_user_id = u.id) AS assignment_rows,
                       (SELECT count(*) FROM documents d WHERE d.owner_user_id = u.id) AS document_rows,
                       (SELECT count(*) FROM notifications n
                        WHERE n.user_id = u.id OR n.actor_user_id = u.id
                           OR n.subject_faculty_user_id = u.id) AS notification_rows
                FROM users u
                WHERE u.email ILIKE '%@test.local'
                   OR (u.full_name = ANY(:names) AND u.password_hash = :ph)
                ORDER BY u.id
                """
            ),
            {"names": list(FIXTURE_NAMES), "ph": PLACEHOLDER_HASH},
        ).mappings().all()

        for r in rows:
            reasons = []
            email = (r["email"] or "").lower()
            if email.endswith("@test.local"):
                reasons.append("email_domain_test_local")
            if r["password_hash"] == PLACEHOLDER_HASH:
                reasons.append("placeholder_password_hash")
            if (r["full_name"] or "") in FIXTURE_NAMES:
                reasons.append("fixture_display_name")
            if len(reasons) < 2 and not email.endswith("@test.local"):
                continue
            if email.endswith("@test.local") and r["password_hash"] == PLACEHOLDER_HASH:
                reasons.append("pytest_fixture_signature")
            candidates.append(
                {
                    "userId": r["id"],
                    "emailRedacted": email.split("@")[0][:12] + "@test.local" if email.endswith("@test.local") else "[redacted]",
                    "role": r["role"],
                    "fullName": r["full_name"],
                    "createdAt": r["created_at"].isoformat() if r["created_at"] else None,
                    "employeeId": r["employee_id"],
                    "isActive": r["is_active"],
                    "assignmentRows": int(r["assignment_rows"] or 0),
                    "documentRows": int(r["document_rows"] or 0),
                    "notificationRows": int(r["notification_rows"] or 0),
                    "evidence": reasons,
                }
            )

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "applicationDbFingerprint": fingerprint(url),
        "applicationDbHost": host,
        "applicationDbName": dbname,
        "suspectedTestUserCount": len(candidates),
        "candidates": candidates,
    }

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Application DB fingerprint: {out['applicationDbFingerprint']} (host={host}, name={dbname})")
        print(f"Suspected pytest-created users: {len(candidates)}")
        by_role = {}
        for c in candidates:
            by_role[c["role"]] = by_role.get(c["role"], 0) + 1
        print(f"By role: {by_role}")
        for c in candidates[:50]:
            print(
                f"  id={c['userId']} role={c['role']} name={c['fullName']!r} "
                f"email={c['emailRedacted']} evidence={','.join(c['evidence'])} "
                f"assignments={c['assignmentRows']} docs={c['documentRows']} notifs={c['notificationRows']}"
            )
        if len(candidates) > 50:
            print(f"  ... and {len(candidates) - 50} more (use --json for full manifest)")

    manifest_path = BACKEND_ROOT / "scripts" / "output" / "test_account_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Manifest written: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())