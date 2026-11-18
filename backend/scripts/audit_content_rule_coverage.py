"""Audit published catalog indicators against general content-validation coverage."""

from collections import Counter

from app import create_app
from app.services.catalog import get_published_catalog_and_weights
from app.services.document_validation_config import coverage_for_indicator


def main() -> None:
    app = create_app()
    with app.app_context():
        cat, _ = get_published_catalog_and_weights()
        print("catalog version", (cat or {}).get("version"))
        rows = []
        for kra in (cat or {}).get("kras") or []:
            for crit in kra.get("criteria") or []:
                for ind in crit.get("indicators") or []:
                    cov = coverage_for_indicator(ind, indicator_id=ind.get("id"), kra_id=kra.get("id"))
                    rows.append(
                        {
                            "kra": kra.get("id"),
                            "criterion": crit.get("id"),
                            "indicator": ind.get("id"),
                            "name": (ind.get("name") or "")[:80],
                            "status": cov["status"],
                            "docType": cov.get("document_type"),
                            "ocrFields": cov.get("ocr_fields") or [],
                            "formOnly": cov.get("form_only_fields") or [],
                        }
                    )
        print("indicator count", len(rows))
        print("by coverage", Counter(r["status"] for r in rows))
        print("--- UNCONFIGURED (remaining gaps) ---")
        for r in rows:
            if r["status"] == "unconfigured":
                print(
                    " | ".join(
                        [
                            r["kra"] or "",
                            r["criterion"] or "",
                            r["indicator"] or "",
                            "formOnly=" + ",".join(r["formOnly"]),
                            r["name"],
                        ]
                    )
                )
        print("--- SET/SEF PIPELINE ---")
        for r in rows:
            if r["status"] == "set_sef_pipeline":
                print(r["indicator"], r["name"])
        print("--- SPECIAL STATUS ---")
        for r in rows:
            if r["status"] == "special_status_support":
                print(r["indicator"], r["ocrFields"])


if __name__ == "__main__":
    main()
