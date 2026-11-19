#!/usr/bin/env python3
"""
Dry-run-first cleanup for suspected pytest accounts (application DB).

Default: --dry-run (no DELETE). Live delete requires --execute and --i-have-reviewed-manifest.

Review manifest from inventory_suspected_test_accounts.py before any execute.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = BACKEND_ROOT / "scripts" / "output" / "test_account_manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true", help="Perform deletion (requires manifest review flag).")
    parser.add_argument("--i-have-reviewed-manifest", action="store_true")
    args = parser.parse_args()

    if args.execute:
        if not args.i_have_reviewed_manifest:
            print("Refusing: pass --i-have-reviewed-manifest after reviewing the manifest.", file=sys.stderr)
            return 1
        print("EXECUTE mode is not enabled in this build. Run SQL from the generated plan manually after backup.")
        return 1

    if not MANIFEST.is_file():
        print(f"Run inventory first: python scripts/inventory_suspected_test_accounts.py", file=sys.stderr)
        return 2

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = [c["userId"] for c in data.get("candidates", [])]
    print(f"DRY RUN — would delete {len(ids)} users and dependent rows (notifications, assignments, documents, assessments).")
    print("Backup: pg_dump facultylinks (or Supabase backup) before any execute.")
    print("User IDs in manifest:", ids[:20], ("..." if len(ids) > 20 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())