"""Merge SET/SEF semester rows across combined, SET-only, and SEF-only PDF uploads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models import Document, SetSefSemesterRecord

SET_SEF_DOCUMENT_KINDS = ("set_sef_unified", "set_sef_combined", "set_sef_set_only", "set_sef_sef_only")
MAX_SEMESTER_SLOTS = 6


@dataclass
class AggregationConflict:
    semester_key: str
    field: str
    document_ids: list[int]
    explanation: str


@dataclass
class MergedSemesterSlot:
    semester_key: str
    academic_year: str | None
    semester: str | None
    faculty_name_extracted: str | None
    faculty_identity_status: str | None
    set_rating_extracted: float | None = None
    set_rating_confirmed: float | None = None
    set_verification_status: str | None = None
    set_source_document_id: int | None = None
    set_source_document_public_id: str | None = None
    sef_rating_extracted: float | None = None
    sef_rating_confirmed: float | None = None
    sef_verification_status: str | None = None
    sef_source_document_id: int | None = None
    sef_source_document_public_id: str | None = None
    source_record_ids: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "semesterKey": self.semester_key,
            "academicYear": self.academic_year,
            "semester": self.semester,
            "facultyNameExtracted": self.faculty_name_extracted,
            "facultyIdentityStatus": self.faculty_identity_status,
            "setRatingExtracted": self.set_rating_extracted,
            "setRatingConfirmed": self.set_rating_confirmed,
            "setVerificationStatus": self.set_verification_status,
            "setSourceDocumentId": self.set_source_document_public_id,
            "sefRatingExtracted": self.sef_rating_extracted,
            "sefRatingConfirmed": self.sef_rating_confirmed,
            "sefVerificationStatus": self.sef_verification_status,
            "sefSourceDocumentId": self.sef_source_document_public_id,
            "sourceRecordIds": self.source_record_ids,
        }


def _rating_score(rec: SetSefSemesterRecord, kind: str, *, verified: bool) -> float | None:
    if kind == "set":
        status = rec.set_verification_status
        confirmed = rec.set_rating_confirmed
        extracted = rec.set_rating_extracted
    else:
        status = rec.sef_verification_status
        confirmed = rec.sef_rating_confirmed
        extracted = rec.sef_rating_extracted
    if verified and status != "verified":
        return None
    if confirmed is not None:
        return float(confirmed)
    if not verified and extracted is not None:
        return float(extracted)
    return None


def _pick_best(
    candidates: list[tuple[SetSefSemesterRecord, Document]],
    kind: str,
) -> tuple[SetSefSemesterRecord | None, list[AggregationConflict]]:
    conflicts: list[AggregationConflict] = []
    if not candidates:
        return None, conflicts
    ranked = sorted(
        candidates,
        key=lambda pair: (
            0 if (pair[0].set_verification_status if kind == "set" else pair[0].sef_verification_status) == "verified"
            else 1,
            -(pair[1].created_at.timestamp() if pair[1].created_at else 0),
        ),
    )
    winner_rec, winner_doc = ranked[0]
    values = set()
    doc_ids: list[int] = []
    for rec, doc in candidates:
        val = _rating_score(rec, kind, verified=False)
        if val is not None:
            values.add(round(val, 4))
            doc_ids.append(doc.id)
    if len(values) > 1:
        sk = winner_rec.semester_key or ""
        conflicts.append(
            AggregationConflict(
                semester_key=sk,
                field=f"{kind.upper()} rating",
                document_ids=sorted(set(doc_ids)),
                explanation=f"Conflicting {kind.upper()} values for semester {sk}; reviewer must choose.",
            )
        )
    return winner_rec, conflicts


def aggregate_set_sef_for_faculty(
    owner_user_id: int,
) -> tuple[list[MergedSemesterSlot], list[Document], list[AggregationConflict]]:
    docs = (
        Document.query.filter_by(owner_user_id=owner_user_id)
        .filter(Document.document_kind.in_(SET_SEF_DOCUMENT_KINDS))
        .filter(Document.superseded_by_public_id.is_(None))
        .order_by(Document.created_at.desc())
        .all()
    )
    doc_by_id = {d.id: d for d in docs}
    records: list[SetSefSemesterRecord] = []
    if doc_by_id:
        records = (
            SetSefSemesterRecord.query.filter_by(owner_user_id=owner_user_id, superseded_by_id=None)
            .filter(SetSefSemesterRecord.document_id.in_(doc_by_id.keys()))
            .all()
        )
    if not doc_by_id:
        return [], [], []

    by_key: dict[str, list[tuple[SetSefSemesterRecord, Document]]] = {}
    for rec in records:
        doc = doc_by_id.get(rec.document_id)
        if not doc:
            continue
        key = rec.semester_key or f"{rec.academic_year}|{rec.semester}"
        by_key.setdefault(key, []).append((rec, doc))

    merged: list[MergedSemesterSlot] = []
    all_conflicts: list[AggregationConflict] = []
    for key, group in sorted(by_key.items()):
        set_candidates = [(r, d) for r, d in group if r.set_rating_extracted is not None or r.set_rating_confirmed is not None]
        sef_candidates = [(r, d) for r, d in group if r.sef_rating_extracted is not None or r.sef_rating_confirmed is not None]
        set_rec, c1 = _pick_best(set_candidates, "set")
        sef_rec, c2 = _pick_best(sef_candidates, "sef")
        all_conflicts.extend(c1)
        all_conflicts.extend(c2)
        base = set_rec or sef_rec or group[0][0]
        slot = MergedSemesterSlot(
            semester_key=key,
            academic_year=base.academic_year,
            semester=base.semester,
            faculty_name_extracted=base.faculty_name_extracted,
            faculty_identity_status=base.faculty_identity_status,
            source_record_ids=[r.id for r, _ in group],
        )
        if set_rec:
            sd = doc_by_id[set_rec.document_id]
            slot.set_rating_extracted = (
                float(set_rec.set_rating_extracted) if set_rec.set_rating_extracted is not None else None
            )
            slot.set_rating_confirmed = (
                float(set_rec.set_rating_confirmed) if set_rec.set_rating_confirmed is not None else None
            )
            slot.set_verification_status = set_rec.set_verification_status or "pending"
            slot.set_source_document_id = sd.id
            slot.set_source_document_public_id = sd.public_id
        if sef_rec:
            sd = doc_by_id[sef_rec.document_id]
            slot.sef_rating_extracted = (
                float(sef_rec.sef_rating_extracted) if sef_rec.sef_rating_extracted is not None else None
            )
            slot.sef_rating_confirmed = (
                float(sef_rec.sef_rating_confirmed) if sef_rec.sef_rating_confirmed is not None else None
            )
            slot.sef_verification_status = sef_rec.sef_verification_status or "pending"
            slot.sef_source_document_id = sd.id
            slot.sef_source_document_public_id = sd.public_id
        merged.append(slot)
    return merged, docs, all_conflicts


def _scoring_verification(status: str | None) -> str:
    """ORM proxies require a status string; never invent verified without an explicit status."""
    return status or "pending"


def apply_semester_slot_window(
    slots: list[MergedSemesterSlot],
    *,
    max_slots: int = MAX_SEMESTER_SLOTS,
    selected_semester_keys: list[str] | None = None,
) -> tuple[list[MergedSemesterSlot], list[MergedSemesterSlot], list[dict], bool]:
    """At most [max_slots] distinct semesters may be scored; excess requires explicit selection (no silent pick)."""
    ordered = sorted(slots, key=lambda s: (s.academic_year or "", s.semester or "", s.semester_key or ""))
    if len(ordered) <= max_slots:
        return ordered, [], [], False
    all_keys = [s.semester_key for s in ordered]
    if not selected_semester_keys:
        return (
            [],
            ordered,
            [
                {
                    "code": "semester_window_selection_required",
                    "message": (
                        f"{len(ordered)} semester slots found; select up to {max_slots} for scoring. "
                        "Uploads are preserved; unselected semesters are excluded from calculation only."
                    ),
                    "availableSemesterKeys": all_keys,
                }
            ],
            True,
        )
    keys = list(dict.fromkeys(str(k) for k in selected_semester_keys if k))
    if len(keys) > max_slots:
        return (
            [],
            ordered,
            [
                {
                    "code": "semester_window_selection_invalid",
                    "message": f"Select at most {max_slots} semester slots (got {len(keys)}).",
                    "availableSemesterKeys": all_keys,
                }
            ],
            True,
        )
    key_set = set(keys)
    scoring = [s for s in ordered if s.semester_key in key_set]
    unknown = key_set - {s.semester_key for s in scoring}
    if unknown:
        return (
            [],
            ordered,
            [
                {
                    "code": "semester_window_selection_invalid",
                    "message": f"Unknown semester keys in selection: {', '.join(sorted(unknown))}",
                    "availableSemesterKeys": all_keys,
                }
            ],
            True,
        )
    excluded = [s for s in ordered if s.semester_key not in key_set]
    return scoring, excluded, [], False


def conflict_blocks_component(conflicts: list[AggregationConflict], semester_key: str, kind: str) -> bool:
    field = f"{kind.upper()} rating"
    return any(c.semester_key == semester_key and c.field == field for c in conflicts)


def merged_slots_to_scoring_records(
    slots: list[MergedSemesterSlot],
    conflicts: list[AggregationConflict] | None = None,
) -> list[SetSefSemesterRecord]:
    """Lightweight proxy records for compute_criterion_a_from_records."""
    out: list[SetSefSemesterRecord] = []
    conflicts = conflicts or []
    for slot in slots:
        sk = slot.semester_key or ""
        set_blocked = conflict_blocks_component(conflicts, sk, "set")
        sef_blocked = conflict_blocks_component(conflicts, sk, "sef")
        rec = SetSefSemesterRecord(
            academic_year=slot.academic_year,
            semester=slot.semester,
            semester_key=slot.semester_key,
            faculty_identity_status=slot.faculty_identity_status or "missing",
            set_rating_extracted=None if set_blocked else slot.set_rating_extracted,
            set_rating_confirmed=None if set_blocked else slot.set_rating_confirmed,
            set_verification_status=_scoring_verification(slot.set_verification_status),
            sef_rating_extracted=None if sef_blocked else slot.sef_rating_extracted,
            sef_rating_confirmed=None if sef_blocked else slot.sef_rating_confirmed,
            sef_verification_status=_scoring_verification(slot.sef_verification_status),
            superseded_by_id=None,
        )
        out.append(rec)
    return out


def criterion_a_scoring_inputs(
    owner_user_id: int,
    assessment_data: dict | None = None,
) -> tuple[list[SetSefSemesterRecord], list[Document], list[AggregationConflict], list[dict], bool, bool, str | None]:
    """Merged slots → slot window → proxy records ready for Criterion A calculation."""
    from app.services.catalog import scoring_window_semester_keys

    slots, docs, conflicts = aggregate_set_sef_for_faculty(owner_user_id)
    selected = scoring_window_semester_keys(assessment_data)
    scoring_slots, excluded, findings, needs_selection = apply_semester_slot_window(
        slots, selected_semester_keys=selected
    )
    window_msg = findings[0]["message"] if findings else None
    proxies = merged_slots_to_scoring_records(scoring_slots, conflicts)
    return proxies, docs, conflicts, findings, needs_selection, bool(findings) and not needs_selection, window_msg

