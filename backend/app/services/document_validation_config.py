"""
Document-validation configuration for FacultyLink general OCR.

Sources of truth for *which* fields apply:
  - Published assessment catalog indicator ``fields`` arrays
    (from workbook-backed definitions in admin_reviewer_web/js/core/*-catalog.js
    and assessment-definitions.js).
  - SET/SEF PDF indicators use the dedicated SET/SEF pipeline (not these rules).
  - Special-status supporting evidence uses documented documentaryRequirements.

These rules are **not** official DBM–CHED form mandates beyond what the project
catalog already records. Keyword KRA suggestions remain manuscript Table 5
heuristics and never reassign the faculty-selected KRA.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.services.document_content_identity import IDENTITY_SUPPORTED_DOCUMENT_TYPES

CONTENT_RULES_VERSION = "fl-doc-content-1.2"
CLASSIFICATION_VERSION = "fl-kra-suggest-1.0"

_FIELDS_JSON = Path(__file__).with_name("catalog_indicator_fields.json")


@lru_cache(maxsize=1)
def workbook_indicator_fields() -> dict[str, Any]:
    """Documented indicator fields from workbook-backed JS catalogs (fallback)."""
    if not _FIELDS_JSON.exists():
        return {}
    data = json.loads(_FIELDS_JSON.read_text(encoding="utf-8"))
    return data.get("indicators") or {}


def resolve_indicator_fields(indicator: dict | None, indicator_id: str | None) -> tuple[list[str], str]:
    """
    Prefer fields embedded on the published catalog indicator.
    Fall back to workbook catalog field map when the published JSON omitted them.
    If published fields are form-only but the workbook documents OCR-applicable
    fields (title/date/…), supplement those OCR fields without inventing new ones.
    """
    ind = indicator or {}
    iid = indicator_id or ind.get("id") or ""
    published = list(ind.get("fields") or [])
    wb = workbook_indicator_fields().get(iid) or {}
    workbook_fields = list(wb.get("fields") or [])

    if published:
        pub_ocr = [f for f in published if f in OCR_APPLICABLE_CATALOG_FIELDS]
        if pub_ocr:
            return published, "published_catalog_indicator.fields"
        wb_ocr = [f for f in workbook_fields if f in OCR_APPLICABLE_CATALOG_FIELDS]
        if wb_ocr:
            merged = list(dict.fromkeys([*wb_ocr, *published]))
            return merged, "workbook_ocr_fields+published_form_fields"
        return published, "published_catalog_indicator.fields"

    if workbook_fields:
        return workbook_fields, "workbook_catalog_js_fields_map"
    return [], "none"

# Manuscript Table 5 — keyword suggestion heuristics (not authoritative assignment).
KRA_KEYWORD_RULES: list[dict[str, Any]] = [
    {
        "rule_id": "kra_suggest_research_journal",
        "suggested_kra": "kra-II",
        "keywords": ["journal", "issn", "publication", "publications", "doi"],
        "priority": 1,
        "source": (
            "Manuscript Table 5 Document Classification Rules "
            "(project suggestion heuristics; not official DBM–CHED mandates)."
        ),
    },
    {
        "rule_id": "kra_suggest_instruction",
        "suggested_kra": "kra-I",
        "keywords": ["teaching", "course", "instruction", "syllabus", "instructional"],
        "priority": 2,
        "source": (
            "Manuscript Table 5 Document Classification Rules "
            "(project suggestion heuristics; not official DBM–CHED mandates)."
        ),
    },
    {
        "rule_id": "kra_suggest_extension",
        "suggested_kra": "kra-III",
        "keywords": ["community", "outreach", "extension", "extension service"],
        "priority": 3,
        "source": (
            "Manuscript Table 5 Document Classification Rules "
            "(project suggestion heuristics; not official DBM–CHED mandates)."
        ),
    },
    {
        "rule_id": "kra_suggest_professional_dev",
        "suggested_kra": "kra-IV",
        "keywords": ["training", "seminar", "certificate", "workshop", "webinar"],
        "priority": 4,
        "source": (
            "Manuscript Table 5 Document Classification Rules "
            "(project suggestion heuristics; not official DBM–CHED mandates)."
        ),
    },
]

# Catalog field names that are OCR/content-checkable on the uploaded file.
# Form-only achievement fields (role, description, tiers, quantities, etc.) are excluded.
OCR_APPLICABLE_CATALOG_FIELDS: dict[str, dict[str, Any]] = {
    "title": {
        "field": "title",
        "accepted_formats": ["nonempty_line"],
        "severity": "review",
        "rule_suffix": "title",
        "explanation": "Document title was not detected near title/heading labels.",
    },
    "date": {
        "field": "event_date",
        "accepted_formats": ["labeled_date"],
        "severity": "review",
        "rule_suffix": "date",
        "explanation": "Date was not detected near date/issued/held/dated labels.",
    },
    "achievementDate": {
        "field": "event_date",
        "accepted_formats": ["labeled_date"],
        "severity": "review",
        "rule_suffix": "achievement_date",
        "explanation": "Achievement date was not detected near date/issued/held/dated labels.",
    },
    "publicationIdentifier": {
        "field": "publication_identifier",
        "accepted_formats": ["identifier_label"],
        "severity": "review",
        "rule_suffix": "publication_identifier",
        "explanation": "Publication identifier (DOI/ISSN/ISBN) was not detected near identifier labels.",
    },
    "patentNumber": {
        "field": "patent_number",
        "accepted_formats": ["patent_label"],
        "severity": "review",
        "rule_suffix": "patent_number",
        "explanation": "Patent number was not detected near patent/application labels.",
    },
    "productName": {
        "field": "product_name",
        "accepted_formats": ["product_label"],
        "severity": "review",
        "rule_suffix": "product_name",
        "explanation": "Product name was not detected near product labels.",
    },
    "softwareTitle": {
        "field": "software_title",
        "accepted_formats": ["software_label"],
        "severity": "review",
        "rule_suffix": "software_title",
        "explanation": "Software title was not detected near software/title labels.",
    },
}

# Achievement-form fields recorded in the catalog but not validated via document OCR.
FORM_ONLY_CATALOG_FIELDS = frozenset(
    {
        "description",
        "authorRole",
        "authorship",
        "role",
        "thesisType",
        "quantity",
        "duration",
        "hours",
        "presentationScope",
        "serviceScope",
        "extensionRole",
        "incomeRole",
        "incomeAmount",
        "incomeTier",
        "judgeServiceType",
        "linkedIsrProjectId",
        "clientSatisfactionRating",
        "designationLevel",
        "designationRole",
        "projectPeriod",
        "patentStage",
        "commercializationScope",
        "softwareVersionType",
        "designType",
        "translationOutcome",
        "citingWork",
        "citationContext",
        "specialStatus",
        "notes",
        "pdf",
        "academicYear",
        "semester",
        "rating",
    }
)

SET_SEF_INDICATOR_TYPES = frozenset(
    {
        "set_sef",
        "set_sef_unified_pdf",
        "set_sef_combined_pdf",
        "set_sef_set_pdf",
        "set_sef_sef_pdf",
    }
)


def _field_requirements(ocr_fields: list[str], form_only: list[str]) -> dict[str, str]:
    """Map catalog field → required|optional|conditional|reviewer_only|form_only.

    Catalog/workbook does not yet mark optional OCR fields; documented OCR-applicable
    fields are treated as review-severity checks (missing → review, not auto-reject).
    """
    req: dict[str, str] = {}
    for f in ocr_fields:
        req[f] = "required_review"  # must be considered; failure is review, not reject
    for f in form_only:
        req[f] = "form_only"
    return req


def _manual_review_gaps(
    *,
    status: str,
    form_only: list[str],
    ocr_fields: list[str],
    document_type: str | None = None,
) -> list[str]:
    gaps: list[str] = []
    if status == "unconfigured":
        gaps.append("No automatic content checks; reviewer must validate evidence manually.")
    if status == "catalog_fields":
        gaps.append(
            "Configured OCR checks are assistive only — passing them does not approve the document "
            "or prove authenticity/ownership."
        )
        if not ocr_fields:
            gaps.append("No OCR-applicable fields configured for this indicator.")
    identity_form = [f for f in form_only if f in ("authorRole", "authorship", "role", "extensionRole", "incomeRole")]
    if identity_form:
        gaps.append(
            "Identity/role fields are achievement-form only; no automatic OCR identity match is configured. "
            "Reviewer must confirm ownership manually. A name match (where extracted) is not proof of ownership."
        )
    scoring_form = [
        f
        for f in form_only
        if f
        in (
            "quantity",
            "hours",
            "duration",
            "incomeAmount",
            "incomeTier",
            "presentationScope",
            "serviceScope",
            "clientSatisfactionRating",
            "patentStage",
            "commercializationScope",
        )
    ]
    if scoring_form:
        gaps.append(
            "Scoring quantities/tiers/scopes are form-claimed and are not OCR-validated against the file."
        )
    if status == "special_status_support":
        gaps.append("Only readable-text presence is checked; special-status eligibility remains reviewer judgment.")
    if status == "set_sef_pipeline":
        gaps.append(
            "General OCR rules do not apply. SET/SEF ratings, identity, and semester checks use the dedicated pipeline; "
            "reviewer confirmation is still required before Criterion A awards."
        )
    if status == "catalog_fields" and document_type in IDENTITY_SUPPORTED_DOCUMENT_TYPES:
        gaps.append(
            "Advisory identity checks may compare extracted honoree/recipient names to the faculty profile when "
            "certificate-style labels are present. A match is not proof of ownership or authorship."
        )
    return gaps


def _automatic_checks(
    *, status: str, ocr_fields: list[str], document_type: str | None = None
) -> list[str]:
    if status == "set_sef_pipeline":
        return [
            "set_sef_ocr_extract",
            "faculty_identity",
            "semester_ay",
            "original_set_sef_ratings",
            "scale_and_missing_rating",
            "duplicate_hash_conflict",
        ]
    if status == "special_status_support":
        return ["supporting_text_readable"]
    if status == "catalog_fields":
        checks = [f"ocr_field:{f}" for f in ocr_fields]
        if document_type in IDENTITY_SUPPORTED_DOCUMENT_TYPES:
            checks.append("faculty_identity_advisory")
        checks.append("kra_keyword_suggestion_advisory")
        return checks
    return ["coverage_status_only"]


def coverage_for_indicator(indicator: dict | None, *, indicator_id: str | None, kra_id: str | None) -> dict[str, Any]:
    """
    Classify how general content validation applies to an indicator.

    Returns keys: status, document_type, ocr_fields, form_only_fields, reason, source,
    field_requirements, automatic_checks, manual_review_gaps, fully_validated (always False
    unless dedicated pipeline explicitly claims otherwise — currently never True).
    status: set_sef_pipeline | special_status_support | catalog_fields | unconfigured
    """
    ind = indicator or {}
    iid = indicator_id or ind.get("id") or ""
    itype = (ind.get("type") or "").strip()
    role = (ind.get("role") or "").strip()
    calc_kind = ((ind.get("calculation") or {}).get("kind") or "").strip()
    wb = workbook_indicator_fields().get(iid) or {}
    if not itype:
        itype = (wb.get("type") or "").strip()
    if not role:
        role = (wb.get("role") or "").strip()
    if not calc_kind:
        calc_kind = (wb.get("calculationKind") or "").strip()
    fields, fields_source = resolve_indicator_fields(ind, iid)

    def _pack(status: str, *, document_type, ocr_fields, form_only, reason, source) -> dict[str, Any]:
        return {
            "status": status,
            "document_type": document_type,
            "ocr_fields": ocr_fields,
            "form_only_fields": form_only,
            "reason": reason,
            "source": source,
            "rules_version": CONTENT_RULES_VERSION,
            "field_requirements": _field_requirements(ocr_fields, form_only),
            "automatic_checks": _automatic_checks(
                status=status, ocr_fields=ocr_fields, document_type=document_type
            ),
            "manual_review_gaps": _manual_review_gaps(
                status=status,
                form_only=form_only,
                ocr_fields=ocr_fields,
                document_type=document_type,
            ),
            # Coverage entry ≠ complete automatic validation for every claim on the form.
            "fully_validated": False,
        }

    if (
        itype in SET_SEF_INDICATOR_TYPES
        or calc_kind in ("set_sef_average",)
        or iid
        in {
            "kra-I-A-setsef-eval",
            "kra-I-A-setsef-combined",
            "kra-I-A-set-pdf",
            "kra-I-A-sef-pdf",
            "kra-I-A-set",
            "kra-I-A-sef",
        }
    ):
        return _pack(
            "set_sef_pipeline",
            document_type="set_sef_evaluation",
            ocr_fields=[],
            form_only=fields,
            reason="SET/SEF evaluation evidence uses the dedicated SET/SEF OCR and validation pipeline.",
            source="catalog SET/SEF indicator types + backend set_sef pipeline",
        )

    if iid == "kra-I-A-special" or role == "supporting_evidence" or calc_kind == "supporting_evidence":
        return _pack(
            "special_status_support",
            document_type="special_status_support",
            ocr_fields=["supporting_text"],
            form_only=[f for f in fields if f != "pdf"],
            reason=(
                "Special-status supporting evidence: catalog documentaryRequirements require "
                "supporting documentation; OCR checks that readable text was extracted."
            ),
            source="assessment-definitions.js kra-I-A-special documentaryRequirements",
        )

    ocr_fields = [f for f in fields if f in OCR_APPLICABLE_CATALOG_FIELDS]
    form_only = [f for f in fields if f in FORM_ONLY_CATALOG_FIELDS or f not in OCR_APPLICABLE_CATALOG_FIELDS]
    if ocr_fields:
        return _pack(
            "catalog_fields",
            document_type=_document_type_label(
                iid, kra_id, ind if ind.get("name") else {**ind, "name": wb.get("name")}
            ),
            ocr_fields=ocr_fields,
            form_only=form_only,
            reason="OCR content checks derived from documented catalog indicator fields.",
            source=f"{fields_source} for {iid}",
        )

    if fields:
        return _pack(
            "unconfigured",
            document_type=None,
            ocr_fields=[],
            form_only=fields,
            reason=(
                "Documented fields exist, but none are OCR-applicable document-content fields "
                "(they are achievement-form fields only)."
            ),
            source=f"{fields_source} for {iid}",
        )

    return _pack(
        "unconfigured",
        document_type=None,
        ocr_fields=[],
        form_only=[],
        reason="No documented OCR-applicable fields and no dedicated pipeline mapping for this indicator.",
        source="published catalog + workbook field map",
    )


def _document_type_label(indicator_id: str, kra_id: str | None, ind: dict) -> str:
    name = (ind.get("name") or "").lower()
    if (kra_id or "").startswith("kra-II") or indicator_id.startswith("kra-II"):
        return "research_output"
    if (kra_id or "").startswith("kra-III") or indicator_id.startswith("kra-III"):
        return "extension_activity"
    if (kra_id or "").startswith("kra-IV") or indicator_id.startswith("kra-IV"):
        return "professional_development"
    if indicator_id.startswith("kra-I-B"):
        return "instructional_material"
    if indicator_id.startswith("kra-I-C"):
        return "advising_mentorship"
    if "certificate" in name:
        return "certificate"
    return "catalog_evidence"


def build_content_rules_for_indicator(indicator: dict | None, *, indicator_id: str | None, kra_id: str | None) -> list[dict[str, Any]]:
    """Build OCR content-check rules from catalog coverage (may be empty)."""
    coverage = coverage_for_indicator(indicator, indicator_id=indicator_id, kra_id=kra_id)
    rules: list[dict[str, Any]] = []
    if coverage["status"] == "special_status_support":
        rules.append(
            {
                "rule_id": "special_status_supporting_text",
                "version": "1",
                "field": "supporting_text",
                "required": True,
                "severity": "review",
                "accepted_formats": ["readable_text"],
                "explanation": (
                    "Supporting documentation should contain readable extracted text for reviewer review."
                ),
                "source": coverage["source"],
                "catalog_field": "supporting_text",
            }
        )
        return rules

    if coverage["status"] != "catalog_fields":
        return []

    for catalog_field in coverage["ocr_fields"]:
        meta = OCR_APPLICABLE_CATALOG_FIELDS[catalog_field]
        rules.append(
            {
                "rule_id": f"catalog_{indicator_id or 'unknown'}_{meta['rule_suffix']}",
                "version": "1",
                "field": meta["field"],
                "required": True,  # documented OCR field; missing → review, never auto-reject
                "requirement": "required_review",
                "severity": meta["severity"],
                "accepted_formats": meta["accepted_formats"],
                "explanation": meta["explanation"],
                "source": coverage["source"],
                "catalog_field": catalog_field,
            }
        )
    return rules


# Backward-compatible helpers used by older tests / scripts
def infer_document_type(indicator_id: str | None, kra_id: str | None) -> str | None:
    from app.services.catalog import find_indicator, get_published_catalog_and_weights

    catalog, _ = get_published_catalog_and_weights()
    found = find_indicator(catalog, indicator_id) if catalog and indicator_id else None
    ind = (found or {}).get("indicator") if found else None
    coverage = coverage_for_indicator(ind, indicator_id=indicator_id, kra_id=kra_id)
    if coverage["status"] in ("set_sef_pipeline", "special_status_support", "catalog_fields"):
        return coverage.get("document_type")
    return None


def rules_for_document(*, indicator_id: str | None, kra_id: str | None) -> list[dict[str, Any]]:
    from app.services.catalog import find_indicator, get_published_catalog_and_weights

    catalog, _ = get_published_catalog_and_weights()
    found = find_indicator(catalog, indicator_id) if catalog and indicator_id else None
    ind = (found or {}).get("indicator") if found else None
    return build_content_rules_for_indicator(ind, indicator_id=indicator_id, kra_id=kra_id)
