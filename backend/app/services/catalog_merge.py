"""Merge stable JC3 reference indicators into an assessment catalog (preserves existing edits)."""

from __future__ import annotations

import copy

SET_SEF_UNIFIED_INDICATOR = "kra-I-A-setsef-eval"

SET_SEF_PDF_REFERENCE_INDICATORS = [
    {
        "id": SET_SEF_UNIFIED_INDICATOR,
        "name": "SET / SEF Evaluation (PDF)",
        "maxPoints": 60,
        "description": (
            "Faculty upload one evaluation PDF. The system detects SET, SEF, or both from document content "
            "and extracts semester ratings for reviewer verification."
        ),
        "type": "set_sef_unified_pdf",
        "fields": ["pdf"],
        "conditions": ["PDF only; one or more semesters per file."],
        "pointRule": "Routes to SET and SEF scoring components (not a separate scored row).",
        "kraId": "kra-I",
        "criterionId": "kra-I-A",
        "intakeOnly": True,
    },
    {
        "id": "kra-I-A-setsef-combined",
        "name": "Combined SET–SEF PDF",
        "maxPoints": 60,
        "description": "Legacy combined PDF upload.",
        "type": "set_sef_combined_pdf",
        "fields": ["pdf"],
        "conditions": ["PDF only; up to six semester slots."],
        "pointRule": "Intake alias for existing documents.",
        "kraId": "kra-I",
        "criterionId": "kra-I-A",
        "intakeOnly": True,
    },
    {
        "id": "kra-I-A-set-pdf",
        "name": "SET PDF (OCR)",
        "maxPoints": 36,
        "description": "Legacy SET-only PDF upload.",
        "type": "set_sef_set_pdf",
        "fields": ["pdf"],
        "conditions": ["PDF only; one or more semesters per file."],
        "pointRule": "Intake alias for existing documents.",
        "kraId": "kra-I",
        "criterionId": "kra-I-A",
        "intakeOnly": True,
    },
    {
        "id": "kra-I-A-sef-pdf",
        "name": "SEF PDF (OCR)",
        "maxPoints": 24,
        "description": "Legacy SEF-only PDF upload.",
        "type": "set_sef_sef_pdf",
        "fields": ["pdf"],
        "conditions": ["PDF only; one or more semesters per file."],
        "pointRule": "Intake alias for existing documents.",
        "kraId": "kra-I",
        "criterionId": "kra-I-A",
        "intakeOnly": True,
    },
]

SET_SEF_PDF_INDICATOR_IDS = frozenset(i["id"] for i in SET_SEF_PDF_REFERENCE_INDICATORS)
INTAKE_PDF_TYPES = frozenset(
    {
        "set_sef_unified_pdf",
        "set_sef_combined_pdf",
        "set_sef_set_pdf",
        "set_sef_sef_pdf",
    }
)


def catalog_has_set_sef_pdf_indicators(catalog: dict | None) -> bool:
    """True when PDF upload IDs are available (aliases or legacy indicator rows)."""
    from app.services.catalog import find_indicator

    if not catalog:
        return False
    aliases = catalog.get("documentIntakeAliases") or []
    alias_ids = {a.get("id") for a in aliases if isinstance(a, dict)}
    if SET_SEF_PDF_INDICATOR_IDS.issubset(alias_ids):
        return True
    if not find_indicator(catalog, SET_SEF_UNIFIED_INDICATOR):
        return False
    for iid in SET_SEF_PDF_INDICATOR_IDS:
        if iid == SET_SEF_UNIFIED_INDICATOR:
            continue
        if not find_indicator(catalog, iid):
            return False
    return True


def merge_set_sef_pdf_indicators(catalog: dict) -> tuple[dict, list[str]]:
    """Ensure documentIntakeAliases exist for SET/SEF PDF uploads (does not add scored rows)."""
    report: list[str] = []
    if not catalog or not isinstance(catalog, dict):
        catalog = {"kras": []}
    aliases = catalog.setdefault("documentIntakeAliases", [])
    existing_ids = {a.get("id") for a in aliases if isinstance(a, dict)}
    for ref in SET_SEF_PDF_REFERENCE_INDICATORS:
        if ref["id"] in existing_ids:
            continue
        aliases.append(copy.deepcopy(ref))
        existing_ids.add(ref["id"])
        report.append(f"intake {ref['id']}")
    return catalog, report
