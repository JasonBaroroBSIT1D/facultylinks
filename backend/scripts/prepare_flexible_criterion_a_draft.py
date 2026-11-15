"""Prepare current DRAFT only: set Criterion A SET/SEF policy to average_available_max_six.

Does not publish and does not reassign faculty. Admin must Publish, then reassign.
"""
from __future__ import annotations

from app import create_app
from app.services.catalog import CRITERION_A_POLICY_FLEXIBLE, get_assessment_config
from app.services.settings_store import ASSESSMENT_CONFIG_KEY, set_json


def _patch_catalog(catalog: dict) -> list[str]:
    changed: list[str] = []
    for kra in catalog.get("kras") or []:
        if kra.get("id") != "kra-I":
            continue
        for crit in kra.get("criteria") or []:
            if crit.get("id") != "kra-I-A":
                continue
            for ind in crit.get("indicators") or []:
                if ind.get("id") not in ("kra-I-A-set", "kra-I-A-sef") and ind.get("subType") not in (
                    "SET",
                    "SEF",
                ):
                    continue
                calc = dict(ind.get("calculation") or {})
                calc.setdefault("kind", "set_sef_average")
                calc.setdefault("semesterCount", 6)
                before = calc.get("policy")
                calc["policy"] = CRITERION_A_POLICY_FLEXIBLE
                ind["calculation"] = calc
                changed.append(f"{ind.get('id')}: {before!r} -> {CRITERION_A_POLICY_FLEXIBLE!r}")
    return changed


def main() -> None:
    app = create_app()
    with app.app_context():
        cfg = get_assessment_config()
        draft_id = cfg.get("draftId")
        if not draft_id:
            raise SystemExit("No draftId — open Assessment Configuration and create/save a draft first.")
        draft = None
        for v in cfg.get("versions") or []:
            if v.get("id") == draft_id:
                draft = v
                break
        if not draft or draft.get("status") != "draft":
            raise SystemExit(f"Draft {draft_id!r} not found or not editable.")
        catalog = draft.get("catalog")
        if not isinstance(catalog, dict):
            raise SystemExit("Draft has no catalog.")
        changed = _patch_catalog(catalog)
        if not changed:
            raise SystemExit("No SET/SEF indicators found under KRA I Criterion A.")
        set_json(ASSESSMENT_CONFIG_KEY, cfg)
        print("Updated draft", draft_id)
        for line in changed:
            print(" ", line)
        print()
        print("Next admin UI steps:")
        print("  1. Assessment Configuration → open SET and SEF indicators → confirm policy")
        print("     'Average available ratings (max 6 slots)' → Save Draft")
        print("  2. Publish the draft (Publish flow). Faculty pins stay unchanged.")
        print("  3. Faculty profile → Scoring rules version → select the new published")
        print("     version → confirm → Apply reassignment")


if __name__ == "__main__":
    main()
