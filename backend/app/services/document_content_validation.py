"""Extract and validate OCR-applicable content fields from catalog-driven rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.catalog import find_indicator, get_published_catalog_and_weights
from app.services.document_validation_config import (
    CONTENT_RULES_VERSION,
    build_content_rules_for_indicator,
    coverage_for_indicator,
)


@dataclass
class FieldExtraction:
    field_name: str
    value: str | None
    status: str
    excerpt: str | None = None
    source_pages: list[int] = field(default_factory=list)
    rule_id: str | None = None
    rule_version: str | None = None
    explanation: str | None = None
    severity: str | None = None
    source: str | None = None
    catalog_field: str | None = None


@dataclass
class ContentValidationResult:
    document_type: str | None
    rules_version: str
    coverage_status: str
    fields: list[FieldExtraction] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    form_only_fields: list[str] = field(default_factory=list)


_TITLE_LABEL = re.compile(
    r"(?im)^(?:title|program|course|activity|certificate(?:\s+of)?|award|"
    r"software(?:\s+title)?|product(?:\s+name)?)\s*[:\-]\s*(.+)$"
)
_DATE_LABEL = re.compile(
    r"(?im)^(?:date|dated|issued(?:\s+on)?|held(?:\s+on)?|conducted(?:\s+on)?|"
    r"publication date|published|achievement date)\s*[:\-]\s*(.+)$"
)
_DATE_VALUE = re.compile(
    r"(?i)\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+\d{1,2},?\s+\d{4}|\d{4})\b"
)
_DOI_ISSN_LINE = re.compile(r"(?im)^(?:doi|issn|isbn)\s*[:\-]\s*(.+)$")
_DOI_ISSN_INLINE = re.compile(r"(?i)\b(?:doi|issn|isbn)\s*[:\s]+([A-Za-z0-9./\-]+)")
_PATENT_LABEL = re.compile(
    r"(?im)^(?:patent(?:\s+no\.?|\s+number)?|application(?:\s+no\.?)?)\s*[:\-]\s*(.+)$"
)
_PRODUCT_LABEL = re.compile(r"(?im)^(?:product(?:\s+name)?)\s*[:\-]\s*(.+)$")
_SOFTWARE_LABEL = re.compile(r"(?im)^(?:software(?:\s+title|\s+name)?|title)\s*[:\-]\s*(.+)$")


def _pages_for_span(pages: list[dict], needle: str) -> list[int]:
    if not needle:
        return []
    out = []
    for p in pages or []:
        if needle.lower() in (p.get("text") or "").lower():
            out.append(int(p.get("page") or 0))
    return [x for x in out if x]


def _first_group(pattern: re.Pattern[str], text: str) -> tuple[str | None, str | None]:
    m = pattern.search(text or "")
    if not m:
        return None, None
    # Prefer first capturing group with content
    value = ""
    for g in m.groups():
        if g and str(g).strip():
            value = str(g).strip()
            break
    excerpt = m.group(0).strip()
    return (value or None), excerpt


def _extract_by_format(
    fmt: str, text: str, pages: list[dict]
) -> tuple[str | None, str | None, list[int], str]:
    if fmt == "readable_text":
        usable = (text or "").strip()
        # Strip page banners
        compact = re.sub(r"(?m)^--- Page \d+ ---\s*", "", usable).strip()
        if len(compact) >= 40:
            excerpt = compact[:160]
            return "readable", excerpt, _pages_for_span(pages, excerpt[:40]), "ok"
        if compact:
            return compact, compact[:160], _pages_for_span(pages, compact[:40]), "ambiguous"
        return None, None, [], "missing"

    if fmt == "nonempty_line":
        value, excerpt = _first_group(_TITLE_LABEL, text)
        if value:
            return value, excerpt, _pages_for_span(pages, excerpt or value), "ok"
        for line in (text or "").splitlines():
            s = line.strip()
            if len(s) < 8 or len(s) > 180:
                continue
            if _DATE_VALUE.fullmatch(s):
                continue
            if s.lower().startswith("--- page"):
                continue
            return s, s, _pages_for_span(pages, s), "ambiguous"
        return None, None, [], "missing"

    if fmt == "labeled_date":
        value, excerpt = _first_group(_DATE_LABEL, text)
        if value:
            if not _DATE_VALUE.search(value):
                return value, excerpt, _pages_for_span(pages, excerpt or value), "invalid"
            return value, excerpt, _pages_for_span(pages, excerpt or value), "ok"
        return None, None, [], "missing"

    if fmt == "identifier_label":
        value, excerpt = _first_group(_DOI_ISSN_LINE, text)
        if not value:
            value, excerpt = _first_group(_DOI_ISSN_INLINE, text)
        if value:
            return value, excerpt, _pages_for_span(pages, excerpt or value), "ok"
        return None, None, [], "missing"

    if fmt == "patent_label":
        value, excerpt = _first_group(_PATENT_LABEL, text)
        if value:
            return value, excerpt, _pages_for_span(pages, excerpt or value), "ok"
        return None, None, [], "missing"

    if fmt == "product_label":
        value, excerpt = _first_group(_PRODUCT_LABEL, text)
        if value:
            return value, excerpt, _pages_for_span(pages, excerpt or value), "ok"
        return None, None, [], "missing"

    if fmt == "software_label":
        value, excerpt = _first_group(_SOFTWARE_LABEL, text)
        if value:
            return value, excerpt, _pages_for_span(pages, excerpt or value), "ok"
        return None, None, [], "missing"

    return None, None, [], "missing"


def validate_document_content(
    *,
    full_text: str,
    pages: list[dict],
    indicator_id: str | None,
    kra_id: str | None,
    extraction_failed: bool = False,
    catalog: dict | None = None,
) -> ContentValidationResult:
    if catalog is None:
        catalog, _ = get_published_catalog_and_weights()
    found = find_indicator(catalog, indicator_id) if catalog and indicator_id else None
    indicator = (found or {}).get("indicator") if found else None
    coverage = coverage_for_indicator(indicator, indicator_id=indicator_id, kra_id=kra_id)
    rules = build_content_rules_for_indicator(indicator, indicator_id=indicator_id, kra_id=kra_id)

    result = ContentValidationResult(
        document_type=coverage.get("document_type"),
        rules_version=CONTENT_RULES_VERSION,
        coverage_status=coverage["status"],
        form_only_fields=list(coverage.get("form_only_fields") or []),
    )

    # Always record coverage finding so reviewers see why checks did/didn't run.
    if coverage["status"] == "set_sef_pipeline":
        result.findings.append(
            {
                "rule_id": "coverage_set_sef_pipeline",
                "outcome": "info",
                "affected_field": None,
                "severity": "info",
                "rule_version": CONTENT_RULES_VERSION,
                "explanation": coverage["reason"],
                "excerpt": None,
                "source_pages": [],
            }
        )
        return result

    if extraction_failed:
        result.findings.append(
            {
                "rule_id": "extraction_failed",
                "outcome": "review",
                "affected_field": None,
                "severity": "review",
                "rule_version": CONTENT_RULES_VERSION,
                "explanation": (
                    "Text extraction failed. Content field checks were not applied. "
                    "This does not reject the evidence automatically."
                ),
                "excerpt": None,
                "source_pages": [],
            }
        )
        return result

    if coverage["status"] == "unconfigured":
        result.findings.append(
            {
                "rule_id": "content_rules_not_configured",
                "outcome": "info",
                "affected_field": None,
                "severity": "info",
                "rule_version": CONTENT_RULES_VERSION,
                "explanation": coverage["reason"],
                "excerpt": None,
                "source_pages": [],
            }
        )
        return result

    if coverage.get("form_only_fields"):
        result.findings.append(
            {
                "rule_id": "form_only_fields_noted",
                "outcome": "info",
                "affected_field": None,
                "severity": "info",
                "rule_version": CONTENT_RULES_VERSION,
                "explanation": (
                    "Catalog also lists achievement-form fields that are not OCR-validated on the file: "
                    + ", ".join(coverage["form_only_fields"])
                    + "."
                ),
                "excerpt": None,
                "source_pages": [],
            }
        )

    text = full_text or ""
    for rule in rules:
        formats = rule.get("accepted_formats") or ["nonempty_line"]
        value = None
        excerpt = None
        pages_hit: list[int] = []
        status = "missing"
        for fmt in formats:
            value, excerpt, pages_hit, status = _extract_by_format(fmt, text, pages)
            if status in ("ok", "ambiguous", "invalid"):
                break

        field = FieldExtraction(
            field_name=rule["field"],
            value=None if value == "readable" else value,
            status=status,
            excerpt=excerpt,
            source_pages=pages_hit,
            rule_id=rule["rule_id"],
            rule_version=str(rule.get("version") or "1"),
            explanation=rule.get("explanation"),
            severity=rule.get("severity") or "review",
            source=rule.get("source"),
            catalog_field=rule.get("catalog_field"),
        )
        # For supporting_text, store a short marker when ok
        if rule["field"] == "supporting_text" and status == "ok":
            field.value = "readable_text_present"
        result.fields.append(field)

        if status == "ok":
            continue
        if status == "ambiguous":
            explanation = (
                f"{rule.get('explanation')} Extracted value is ambiguous and needs reviewer confirmation."
            )
        elif status == "invalid":
            explanation = f"{rule.get('explanation')} Extracted value did not match an accepted format."
        else:
            explanation = rule.get("explanation") or f"Required field {rule['field']} is missing."
        result.findings.append(
            {
                "rule_id": rule["rule_id"],
                "outcome": "review",
                "affected_field": rule["field"],
                "severity": rule.get("severity") or "review",
                "rule_version": str(rule.get("version") or "1"),
                "explanation": explanation,
                "excerpt": excerpt,
                "source_pages": pages_hit,
            }
        )

    return result
