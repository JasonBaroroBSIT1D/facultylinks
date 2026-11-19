"""Audit published catalog indicators against general content-validation coverage.

Writes a machine-readable coverage report under backend/reports/ and prints a summary.
Coverage entry ≠ full automatic validation of every achievement claim.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app import create_app
from app.services.catalog import get_published_catalog_and_weights
from app.services.document_validation_config import CONTENT_RULES_VERSION, coverage_for_indicator


def main() -> None:
    app = create_app()
    with app.app_context():
        cat, _ = get_published_catalog_and_weights()
        catalog_version = (cat or {}).get("version")
        rows = []
        for kra in (cat or {}).get("kras") or []:
            for crit in kra.get("criteria") or []:
                for ind in crit.get("indicators") or []:
                    cov = coverage_for_indicator(ind, indicator_id=ind.get("id"), kra_id=kra.get("id"))
                    rows.append(
                        {
                            "kraId": kra.get("id"),
                            "kraName": kra.get("name"),
                            "criterionId": crit.get("id"),
                            "criterionName": crit.get("name"),
                            "indicatorId": ind.get("id"),
                            "indicatorName": ind.get("name"),
                            "indicatorType": ind.get("type"),
                            "coverageStatus": cov["status"],
                            "documentType": cov.get("document_type"),
                            "ocrFields": cov.get("ocr_fields") or [],
                            "formOnlyFields": cov.get("form_only_fields") or [],
                            "fieldRequirements": cov.get("field_requirements") or {},
                            "automaticChecks": cov.get("automatic_checks") or [],
                            "manualReviewGaps": cov.get("manual_review_gaps") or [],
                            "fullyValidated": bool(cov.get("fully_validated")),
                            "ruleSource": cov.get("source") or "",
                            "rulesVersion": cov.get("rules_version") or CONTENT_RULES_VERSION,
                            "reason": cov.get("reason") or "",
                        }
                    )

        report = {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "catalogVersion": catalog_version,
            "contentRulesVersion": CONTENT_RULES_VERSION,
            "indicatorCount": len(rows),
            "byCoverageStatus": dict(Counter(r["coverageStatus"] for r in rows)),
            "disclaimer": (
                "A coverage entry documents which automatic checks are configured. "
                "It does not mean the indicator is fully validated, authenticity-proven, "
                "or auto-approved. Form-only claims remain reviewer-confirmed."
            ),
            "indicators": rows,
        }

        out_dir = Path(__file__).resolve().parents[1] / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "ocr_validation_coverage.json"
        md_path = out_dir / "ocr_validation_coverage.md"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        lines = [
            f"# OCR / rule coverage audit",
            "",
            f"- Generated: `{report['generatedAt']}`",
            f"- Catalog version: `{catalog_version}`",
            f"- Content rules version: `{CONTENT_RULES_VERSION}`",
            f"- Indicators: **{len(rows)}**",
            f"- By status: `{report['byCoverageStatus']}`",
            "",
            report["disclaimer"],
            "",
            "| KRA | Criterion | Indicator | Coverage | OCR fields | Automatic checks | Manual gaps |",
            "|-----|-----------|-----------|----------|------------|------------------|-------------|",
        ]
        for r in rows:
            lines.append(
                "| {kra} | {crit} | `{ind}` | {status} | {ocr} | {auto} | {gaps} |".format(
                    kra=r["kraId"],
                    crit=r["criterionId"],
                    ind=r["indicatorId"],
                    status=r["coverageStatus"],
                    ocr=", ".join(r["ocrFields"]) or "—",
                    auto="; ".join(r["automaticChecks"]) or "—",
                    gaps="; ".join(r["manualReviewGaps"])[:120].replace("|", "/") or "—",
                )
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        print("catalog version", catalog_version)
        print("rules version", CONTENT_RULES_VERSION)
        print("indicator count", len(rows))
        print("by coverage", report["byCoverageStatus"])
        print("wrote", json_path)
        print("wrote", md_path)
        print("--- UNCONFIGURED (remaining gaps) ---")
        for r in rows:
            if r["coverageStatus"] == "unconfigured":
                print(r["kraId"], r["criterionId"], r["indicatorId"], r["formOnlyFields"])
        print("--- NOT fullyValidated (expected for all) ---")
        print("count", sum(1 for r in rows if not r["fullyValidated"]))


if __name__ == "__main__":
    main()
