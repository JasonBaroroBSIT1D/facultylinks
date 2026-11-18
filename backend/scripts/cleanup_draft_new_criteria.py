"""Remove confirmed accidental 'New criterion' placeholders from the editable draft only.

Does not publish, does not touch published catalog/pins, does not reset the catalog.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app import create_app
from app.services.settings_store import ASSESSMENT_CONFIG_KEY, get_json, set_json

# Confirmed accidental placeholders from inspection (draft cfg-draft-1794991525437).
TARGET_DRAFT_ID = "cfg-draft-1794991525437"
TARGET_KRA_ID = "kra-I"
PLACEHOLDER_CRITERION_IDS = {
    "crit-1794991525441",  # New criterion + 3 New indicator stubs
    "crit-1794991526675",
    "crit-1794991529251",
    "crit-1794991529547",
}
OFFICIAL_CRITERION_IDS = {"kra-I-A", "kra-I-B", "kra-I-C"}


def is_confirmed_placeholder(crit: dict) -> bool:
    cid = str(crit.get("id") or "")
    if cid in OFFICIAL_CRITERION_IDS:
        return False
    if cid not in PLACEHOLDER_CRITERION_IDS:
        return False
    name = (crit.get("name") or "").strip().lower()
    if name != "new criterion":
        return False
    # Extra safety: only remove timestamp crit-* stubs.
    if not cid.startswith("crit-"):
        return False
    # Indicators under these stubs must themselves be empty/new-indicator stubs if present.
    for ind in crit.get("indicators") or []:
        iname = (ind.get("name") or "").strip().lower()
        iid = str(ind.get("id") or "")
        if iname not in ("new indicator", "") or not iid.startswith("ind-"):
            return False
    return True


def main() -> None:
    app = create_app()
    with app.app_context():
        meta = get_json(ASSESSMENT_CONFIG_KEY, {}) or {}
        draft_id = meta.get("draftId")
        if draft_id != TARGET_DRAFT_ID:
            raise SystemExit(
                f"Refusing to clean: draftId is {draft_id!r}, expected {TARGET_DRAFT_ID!r}."
            )
        versions = meta.get("versions") or []
        draft = next((v for v in versions if v.get("id") == draft_id), None)
        if not draft or draft.get("status") != "draft":
            raise SystemExit("Editable draft not found or not status=draft.")

        kra = next((k for k in (draft.get("catalog") or {}).get("kras") or [] if k.get("id") == TARGET_KRA_ID), None)
        if not kra:
            raise SystemExit("kra-I missing from draft.")

        before_count = len(kra.get("criteria") or [])
        removed = []
        kept = []
        new_criteria = []
        for crit in kra.get("criteria") or []:
            if is_confirmed_placeholder(crit):
                removed.append(
                    {
                        "criterionId": crit.get("id"),
                        "name": crit.get("name"),
                        "indicatorsRemoved": [
                            {"id": i.get("id"), "name": i.get("name")}
                            for i in (crit.get("indicators") or [])
                        ],
                    }
                )
            else:
                new_criteria.append(crit)
                kept.append(crit.get("id"))

        if not removed:
            print("Nothing to remove.")
            return

        kra["criteria"] = new_criteria
        draft.setdefault("changeHistory", []).append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "actor": "cleanup_draft_new_criteria.py",
                "summary": (
                    "Removed accidental New criterion placeholders from draft "
                    f"({', '.join(r['criterionId'] for r in removed)}). "
                    "Published catalog unchanged."
                ),
            }
        )
        set_json(ASSESSMENT_CONFIG_KEY, meta)

        active = meta.get("activePublishedId")
        print(
            json.dumps(
                {
                    "draftId": draft_id,
                    "activePublishedId": active,
                    "kraI_criteria_before": before_count,
                    "kraI_criteria_after": len(kra["criteria"]),
                    "kraI_criteria_kept": kept,
                    "removed": removed,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        print(
            "official_present",
            all(cid in {c["id"] for c in kra["criteria"]} for cid in OFFICIAL_CRITERION_IDS),
        )


if __name__ == "__main__":
    main()
