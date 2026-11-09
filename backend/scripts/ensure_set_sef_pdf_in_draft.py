"""Fork a draft from published rules (if needed) and merge SET/SEF PDF indicators — does not publish."""

from __future__ import annotations

import copy
import sys
import time
from datetime import datetime, timezone

from app import create_app
from app.services.catalog_merge import catalog_has_set_sef_pdf_indicators, merge_set_sef_pdf_indicators
from app.services.settings_store import ASSESSMENT_CONFIG_KEY, get_json, set_json


def main() -> int:
    app = create_app()
    with app.app_context():
        meta = copy.deepcopy(get_json(ASSESSMENT_CONFIG_KEY, {"activePublishedId": None, "versions": [], "draftId": None}))
        versions = meta.get("versions") or []
        active_id = meta.get("activePublishedId")
        active = next((v for v in versions if v.get("id") == active_id and v.get("status") == "published"), None)
        if not active:
            active = next((v for v in reversed(versions) if v.get("status") == "published"), None)
        if not active or not active.get("catalog"):
            print("No published assessment configuration with catalog found.", file=sys.stderr)
            return 1

        draft = next((v for v in versions if v.get("id") == meta.get("draftId") and v.get("status") == "draft"), None)
        if not draft:
            draft_id = f"cfg-draft-{int(time.time() * 1000)}"
            draft = {
                "id": draft_id,
                "label": f"{active.get('label', active_id)}-draft",
                "status": "draft",
                "catalog": copy.deepcopy(active["catalog"]),
                "kraWeights": copy.deepcopy(active.get("kraWeights") or {}),
                "changeHistory": [
                    *(active.get("changeHistory") or []),
                    {
                        "at": datetime.now(timezone.utc).isoformat(),
                        "actor": "ensure_set_sef_pdf_in_draft.py",
                        "summary": "Draft forked for SET/SEF PDF indicator integration.",
                    },
                ],
            }
            versions.append(draft)
            meta["draftId"] = draft_id
            print(f"Forked draft {draft_id} from published {active.get('id')}")

        before = catalog_has_set_sef_pdf_indicators(draft["catalog"])
        draft["catalog"], report = merge_set_sef_pdf_indicators(draft["catalog"])
        after = catalog_has_set_sef_pdf_indicators(draft["catalog"])
        if report:
            draft.setdefault("changeHistory", []).append(
                {
                    "at": datetime.now(timezone.utc).isoformat(),
                    "actor": "ensure_set_sef_pdf_in_draft.py",
                    "summary": f"Merged SET/SEF PDF indicators: {', '.join(report)}",
                }
            )
        meta["versions"] = versions[-50:]
        set_json(ASSESSMENT_CONFIG_KEY, meta)
        print("merged:", report or ["(already present)"])
        print("draftId:", meta.get("draftId"))
        print("pdf_indicators_in_draft:", after)
        print("Published rules unchanged until admin Review & Publish.")
        return 0 if after else 1


if __name__ == "__main__":
    sys.exit(main())
