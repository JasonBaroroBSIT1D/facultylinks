"""Advisory faculty identity checks for document types that name a recipient/honoree."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.services.set_sef_identity import classify_faculty_identity

# Document types where a named person on the file may be compared to the uploader (advisory only).
IDENTITY_SUPPORTED_DOCUMENT_TYPES = frozenset(
    {
        "professional_development",
        "extension_activity",
        "certificate",
        "advising_mentorship",
    }
)

_NAME_LINE = re.compile(
    r"(?im)^(?:name|recipient|awardee|participant|honoree|presented to|awarded to)\s*[:\-]\s*(.+)$"
)
_CERTIFY_BLOCK = re.compile(
    r"(?is)(?:certify|certifies|this is to certify(?:\s+that)?|is hereby (?:awarded|given) to)"
    r"\s*[:\-]?\s*(.+?)(?:\.|,|\n|$)"
)
_CERTIFICATE_CONTEXT = re.compile(
    r"(?i)\bcertificate\b|certify|certifies|participation|awarded to|presented to|this is to certify"
)


@dataclass
class IdentityExtraction:
    field_name: str
    value: str | None
    status: str
    excerpt: str | None
    source_pages: list[int]
    identity_status: str | None = None  # match | needs_confirmation | mismatch | missing


def _pages_for_span(pages: list[dict], needle: str) -> list[int]:
    if not needle:
        return []
    out = []
    for p in pages or []:
        if needle.lower() in (p.get("text") or "").lower():
            out.append(int(p.get("page") or 0))
    return [x for x in out if x]


def _clean_name(value: str) -> str:
    s = re.sub(r"\s+", " ", (value or "").strip())
    s = re.sub(r"^(?:mr\.?|mrs\.?|ms\.?|dr\.?|prof\.?)\s+", "", s, flags=re.I)
    return s.strip(" .,;")[:200]


def extract_subject_name(text: str, pages: list[dict]) -> IdentityExtraction:
    for pattern in (_NAME_LINE, _CERTIFY_BLOCK):
        m = pattern.search(text or "")
        if not m:
            continue
        raw = (m.group(1) or "").strip()
        if not raw or len(raw) < 3:
            continue
        # Drop trailing role/title clauses on the same line
        raw = re.split(r"(?i)\s+(?:for|in|during|on)\s+", raw, maxsplit=1)[0]
        name = _clean_name(raw)
        if len(name) < 3:
            continue
        excerpt = m.group(0).strip()[:200]
        return IdentityExtraction(
            field_name="subject_name",
            value=name,
            status="ok",
            excerpt=excerpt,
            source_pages=_pages_for_span(pages, name[:24]),
        )
    return IdentityExtraction(
        field_name="subject_name",
        value=None,
        status="missing",
        excerpt=None,
        source_pages=[],
    )


def identity_findings_for_document(
    *,
    document_type: str | None,
    profile_full_name: str | None,
    text: str,
    pages: list[dict],
    indicator_id: str | None,
) -> tuple[IdentityExtraction | None, list[dict[str, Any]]]:
    """Optional advisory identity extraction. Never auto-approves; mismatches → review only."""
    if document_type not in IDENTITY_SUPPORTED_DOCUMENT_TYPES:
        return None, []
    if not _CERTIFICATE_CONTEXT.search(text or ""):
        return None, []
    extracted = extract_subject_name(text, pages)
    findings: list[dict[str, Any]] = []
    if not profile_full_name or not str(profile_full_name).strip():
        return extracted, findings

    identity = classify_faculty_identity(profile_full_name, extracted.value)
    extracted.identity_status = identity

    if identity == "match":
        findings.append(
            {
                "rule_id": "faculty_identity_advisory_match",
                "outcome": "info",
                "affected_field": "subject_name",
                "severity": "info",
                "rule_version": "1",
                "explanation": (
                    "A name on the document is similar to the faculty profile. "
                    "This is advisory only and does not prove ownership or approve the evidence."
                ),
                "excerpt": extracted.excerpt,
                "source_pages": extracted.source_pages,
            }
        )
    elif identity == "needs_confirmation":
        findings.append(
            {
                "rule_id": "faculty_identity_advisory_uncertain",
                "outcome": "review",
                "affected_field": "subject_name",
                "severity": "review",
                "rule_version": "1",
                "explanation": (
                    "Extracted name may match the faculty profile but is ambiguous "
                    "(initials, ordering, or partial match). Reviewer must confirm identity."
                ),
                "excerpt": extracted.excerpt,
                "source_pages": extracted.source_pages,
            }
        )
    elif identity == "mismatch":
        findings.append(
            {
                "rule_id": "faculty_identity_advisory_mismatch",
                "outcome": "review",
                "affected_field": "subject_name",
                "severity": "review",
                "rule_version": "1",
                "explanation": (
                    "Extracted name does not closely match the faculty profile. "
                    "This does not auto-reject the file; reviewer must confirm the evidence applies."
                ),
                "excerpt": extracted.excerpt,
                "source_pages": extracted.source_pages,
            }
        )
    else:
        findings.append(
            {
                "rule_id": "faculty_identity_advisory_missing",
                "outcome": "review",
                "affected_field": "subject_name",
                "severity": "review",
                "rule_version": "1",
                "explanation": (
                    "No honoree/recipient name was detected near certificate labels "
                    f"for indicator {indicator_id!r}. Reviewer must confirm the document names the faculty member."
                ),
                "excerpt": None,
                "source_pages": [],
            }
        )
    return extracted, findings