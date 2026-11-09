"""Rule-based validation for SET/SEF semester extractions."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import Document, SetSefSemesterRecord, User
from app.services.set_sef_identity import classify_faculty_identity

SET_SEF_COMBINED_INDICATOR = "kra-I-A-setsef-combined"
EXPECTED_SEMESTER_SLOTS = 6


@dataclass
class ValidationFinding:
    rule_id: str
    outcome: str
    affected_field: str | None
    semester_key: str | None
    explanation: str


def semester_key(ay: str | None, sem: str | None) -> str:
    return f"{ay or '?'}|{sem or '?'}"


def run_set_sef_validations(
    *,
    document: Document,
    owner: User,
    records: list[SetSefSemesterRecord],
    prior_hash: str | None,
    document_kind: str | None = None,
) -> list[ValidationFinding]:
    kind = document_kind or document.document_kind or "set_sef_combined"
    unified = kind == "set_sef_unified"
    expect_set = not unified and kind != "set_sef_sef_only"
    expect_sef = not unified and kind != "set_sef_set_only"
    findings: list[ValidationFinding] = []
    profile_name = owner.full_name or ""

    if document.file_sha256 and prior_hash and document.file_sha256 == prior_hash:
        findings.append(
            ValidationFinding(
                rule_id="duplicate_file_hash",
                outcome="fail",
                affected_field="file",
                semester_key=None,
                explanation="An identical file was already uploaded.",
            )
        )

    for rec in records:
        sk = rec.semester_key or semester_key(rec.academic_year, rec.semester)
        identity = classify_faculty_identity(profile_name, rec.faculty_name_extracted)
        rec.faculty_identity_status = identity
        if identity == "mismatch":
            findings.append(
                ValidationFinding(
                    rule_id="faculty_identity_mismatch",
                    outcome="fail",
                    affected_field="facultyName",
                    semester_key=sk,
                    explanation=f"Extracted name does not match profile ({profile_name}).",
                )
            )
        elif identity == "needs_confirmation":
            findings.append(
                ValidationFinding(
                    rule_id="faculty_identity_uncertain",
                    outcome="review",
                    affected_field="facultyName",
                    semester_key=sk,
                    explanation="Faculty name requires reviewer confirmation.",
                )
            )
        elif identity == "missing":
            findings.append(
                ValidationFinding(
                    rule_id="faculty_identity_missing",
                    outcome="review",
                    affected_field="facultyName",
                    semester_key=sk,
                    explanation="Faculty name missing or unreadable in the PDF.",
                )
            )

        if not rec.academic_year:
            findings.append(
                ValidationFinding(
                    rule_id="missing_academic_year",
                    outcome="review",
                    affected_field="academicYear",
                    semester_key=sk,
                    explanation="Academic year not identified.",
                )
            )
        if not rec.semester:
            findings.append(
                ValidationFinding(
                    rule_id="missing_semester",
                    outcome="review",
                    affected_field="semester",
                    semester_key=sk,
                    explanation="Semester not identified.",
                )
            )
        if expect_set and rec.set_rating_extracted is None:
            findings.append(
                ValidationFinding(
                    rule_id="missing_set_rating",
                    outcome="review",
                    affected_field="setRating",
                    semester_key=sk,
                    explanation="SET overall rating not found for this semester.",
                )
            )
        if expect_sef and rec.sef_rating_extracted is None:
            findings.append(
                ValidationFinding(
                    rule_id="missing_sef_rating",
                    outcome="review",
                    affected_field="sefRating",
                    semester_key=sk,
                    explanation="SEF overall rating not found for this semester.",
                )
            )
        if kind == "set_sef_set_only" and rec.sef_rating_extracted is not None:
            findings.append(
                ValidationFinding(
                    rule_id="content_type_mismatch",
                    outcome="review",
                    affected_field="sefRating",
                    semester_key=sk,
                    explanation="SEF content detected in a SET-only upload.",
                )
            )
        if kind == "set_sef_sef_only" and rec.set_rating_extracted is not None:
            findings.append(
                ValidationFinding(
                    rule_id="content_type_mismatch",
                    outcome="review",
                    affected_field="setRating",
                    semester_key=sk,
                    explanation="SET content detected in a SEF-only upload.",
                )
            )
        for label, rating, scale in (
            ("SET", rec.set_rating_extracted, rec.set_scale_extracted),
            ("SEF", rec.sef_rating_extracted, rec.sef_scale_extracted),
        ):
            if rating is None:
                continue
            r = float(rating)
            max_scale = 100.0
            if scale and "0-5" in scale:
                max_scale = 5.0
            elif scale and re_scale_max(scale):
                max_scale = re_scale_max(scale)
            if r < 0 or r > max_scale:
                findings.append(
                    ValidationFinding(
                        rule_id="rating_out_of_scale",
                        outcome="fail",
                        affected_field=f"{label}Rating",
                        semester_key=sk,
                        explanation=f"{label} rating {r} is outside scale {scale or '0-100'}.",
                    )
                )

    keys = [r.semester_key or semester_key(r.academic_year, r.semester) for r in records]
    if len(keys) != len(set(keys)):
        findings.append(
            ValidationFinding(
                rule_id="duplicate_semester_records",
                outcome="fail",
                affected_field="semester",
                semester_key=None,
                explanation="Duplicate semester records were extracted.",
            )
        )

    if len(records) < EXPECTED_SEMESTER_SLOTS:
        findings.append(
            ValidationFinding(
                rule_id="incomplete_semester_count",
                outcome="review",
                affected_field=None,
                semester_key=None,
                explanation=f"Only {len(records)} of {EXPECTED_SEMESTER_SLOTS} semester slots were extracted.",
            )
        )

    if unified:
        has_set = any(r.set_rating_extracted is not None for r in records)
        has_sef = any(r.sef_rating_extracted is not None for r in records)
        if not records or (not has_set and not has_sef):
            findings.append(
                ValidationFinding(
                    rule_id="extraction_content_unclear",
                    outcome="review",
                    affected_field=None,
                    semester_key=None,
                    explanation="Could not identify SET or SEF ratings in this PDF. A reviewer will confirm the document type.",
                )
            )
        elif has_set and has_sef:
            findings.append(
                ValidationFinding(
                    rule_id="content_detected_set_and_sef",
                    outcome="review",
                    affected_field=None,
                    semester_key=None,
                    explanation="Both SET and SEF ratings were detected. Reviewer verification applies to each semester.",
                )
            )
        elif has_set:
            findings.append(
                ValidationFinding(
                    rule_id="content_detected_set_only",
                    outcome="review",
                    affected_field=None,
                    semester_key=None,
                    explanation="SET ratings detected. Missing SEF for some semesters is tracked at assessment level, not as a document error.",
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    rule_id="content_detected_sef_only",
                    outcome="review",
                    affected_field=None,
                    semester_key=None,
                    explanation="SEF ratings detected. Missing SET for some semesters is tracked at assessment level, not as a document error.",
                )
            )

    return findings


def re_scale_max(scale: str) -> float:
    parts = scale.replace("0-", "").strip()
    try:
        return float(parts)
    except ValueError:
        return 100.0
