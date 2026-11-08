"""Quick smoke test against a running API — does not print secrets."""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("FL_API_BASE", "http://127.0.0.1:5000").rstrip("/")


def main() -> int:
    try:
        with urllib.request.urlopen(f"{BASE}/api/health", timeout=10) as resp:
            data = json.loads(resp.read().decode())
        print(json.dumps(data, indent=2))
        if data.get("database") != "connected":
            print("Database not connected — set DATABASE_URL in .env and run migrations.", file=sys.stderr)
            return 1
        if data.get("storage") != "configured":
            print("Storage not configured — set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.", file=sys.stderr)
            return 1
        return 0
    except Exception as exc:
        print(f"Health check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
