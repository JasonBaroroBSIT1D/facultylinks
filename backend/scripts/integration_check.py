"""Integration checks against live DB config (no secrets printed)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.models import User, UserRole
from app.services.database_check import current_database_name
from app.services.settings_store import ASSESSMENT_CONFIG_KEY, get_json, set_json
from wsgi import app


def main() -> int:
    results: list[tuple[str, bool, str]] = []
    with app.app_context():
        db_name = current_database_name()
        results.append(("database_name_postgres", db_name == "postgres", db_name))

        admin = User.query.filter_by(role=UserRole.admin, is_active=True).first()
        results.append(("admin_user_exists", admin is not None, "found" if admin else "missing"))

        marker = f"integration-draft-{db_name}"
        cfg = get_json(ASSESSMENT_CONFIG_KEY, {"activePublishedId": None, "versions": [], "draftId": None})
        cfg.setdefault("versions", [])
        cfg["draftId"] = "cfg-draft-test"
        cfg["versions"] = [v for v in cfg["versions"] if v.get("id") != "cfg-draft-test"]
        cfg["versions"].append(
            {
                "id": "cfg-draft-test",
                "status": "draft",
                "catalog": {"version": marker, "kras": []},
                "kraWeights": {},
                "changeHistory": [],
            }
        )
        set_json(ASSESSMENT_CONFIG_KEY, cfg)
        reread = get_json(ASSESSMENT_CONFIG_KEY)
        draft_ok = any(v.get("id") == "cfg-draft-test" for v in reread.get("versions", []))
        results.append(("draft_persist_roundtrip", draft_ok, marker))

        from app.services.catalog import filter_config_for_non_admin

        filtered = filter_config_for_non_admin(reread)
        reviewer_sees_draft = any(v.get("status") == "draft" for v in filtered.get("versions", []))
        results.append(("reviewer_hides_draft", not reviewer_sees_draft, str(len(filtered.get("versions", [])))))

        from app.services.scoring_engine import compute_kra_summaries

        sample = {
            "setSef": {"SET": [90, 92], "SEF": [91]},
            "entries": {
                "kra-II-A-3": [
                    {
                        "id": "e1",
                        "reviewStatus": "approved",
                        "estimatedPoints": 10,
                        "reviewerVerifiedPoints": 8,
                        "linkedDocumentId": "doc-1",
                    },
                    {
                        "id": "e2",
                        "reviewStatus": "replaced",
                        "estimatedPoints": 99,
                        "linkedDocumentId": "doc-old",
                    },
                ]
            },
        }
        catalog = {
            "kras": [
                {
                    "id": "kra-II",
                    "weight": 0.2,
                    "criteria": [
                        {
                            "id": "c1",
                            "indicators": [{"id": "kra-II-A-3", "maxPoints": 50}],
                        }
                    ],
                }
            ]
        }
        weights = {"kra-II": 0.2}
        verified = compute_kra_summaries(sample, catalog, weights, verified=True)
        est = compute_kra_summaries(sample, catalog, weights, verified=False)
        v_total = verified["overallWeighted"]
        e_total = est["overallWeighted"]
        results.append(
            (
                "scoring_verified_uses_approved_only",
                v_total == round(8 * 0.2, 4) and e_total >= v_total,
                f"verified={v_total} estimated={e_total}",
            )
        )

        cfg["versions"] = [v for v in cfg.get("versions", []) if v.get("id") != "cfg-draft-test"]
        if cfg.get("draftId") == "cfg-draft-test":
            cfg["draftId"] = None
        set_json(ASSESSMENT_CONFIG_KEY, cfg)

    failed = [r for r in results if not r[1]]
    print(json.dumps({"checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in results]}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
