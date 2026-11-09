"""Regression tests for SET/SEF semester merge and Criterion A scoring proxies."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import Document, SetSefSemesterRecord
from app.services.set_sef_aggregation import (
    AggregationConflict,
    MergedSemesterSlot,
    _pick_best,
    aggregate_set_sef_for_faculty,
    merged_slots_to_scoring_records,
)
from app.services.teaching_effectiveness import compute_criterion_a_from_records


def _doc(doc_id: int, *, public_id: str | None = None) -> Document:
    d = Document(
        object_key=f"key-{doc_id}",
        original_filename=f"f{doc_id}.pdf",
        mime_type="application/pdf",
        size_bytes=1,
        owner_user_id=1,
        document_kind="set_sef_combined",
    )
    d.id = doc_id
    d.public_id = public_id or f"doc-{doc_id}"
    d.created_at = datetime(2024, 1, doc_id, tzinfo=timezone.utc)
    return d


def _rec(
    doc_id: int,
    *,
    semester_key: str = "2022-2023|1st",
    set_rating=None,
    sef_rating=None,
    set_confirmed=None,
    sef_confirmed=None,
    set_verified: str = "pending",
    sef_verified: str = "pending",
) -> SetSefSemesterRecord:
    return SetSefSemesterRecord(
        document_id=doc_id,
        owner_user_id=1,
        academic_year="2022-2023",
        semester="1st",
        semester_key=semester_key,
        faculty_name_extracted="Test Faculty",
        faculty_identity_status="match",
        set_rating_extracted=set_rating,
        set_rating_confirmed=set_confirmed,
        set_verification_status=set_verified,
        sef_rating_extracted=sef_rating,
        sef_rating_confirmed=sef_confirmed,
        sef_verification_status=sef_verified,
    )


def test_merged_semester_slot_accepts_partial_init():
    """Constructor must not require unset rating/source fields (regression for TypeError)."""
    slot = MergedSemesterSlot(
        semester_key="2022-2023|1st",
        academic_year="2022-2023",
        semester="1st",
        faculty_name_extracted="A. Faculty",
        faculty_identity_status="match",
    )
    assert slot.set_rating_extracted is None
    assert slot.sef_rating_extracted is None
    assert slot.set_source_document_public_id is None
    assert slot.set_verification_status is None


def test_set_only_slot_preserves_none_on_sef_side():
    slot = MergedSemesterSlot(
        semester_key="k",
        academic_year="2022-2023",
        semester="1st",
        faculty_name_extracted=None,
        faculty_identity_status="match",
        set_rating_extracted=92.0,
        set_verification_status="pending",
        set_source_document_public_id="doc-set",
    )
    proxies = merged_slots_to_scoring_records([slot])
    assert len(proxies) == 1
    p = proxies[0]
    assert p.set_rating_extracted == 92.0
    assert p.sef_rating_extracted is None
    assert p.sef_verification_status == "pending"
    assert p.set_verification_status == "pending"


def test_sef_only_slot_preserves_none_on_set_side():
    slot = MergedSemesterSlot(
        semester_key="k",
        academic_year="2022-2023",
        semester="1st",
        faculty_name_extracted=None,
        faculty_identity_status="match",
        sef_rating_extracted=88.0,
        sef_verification_status="pending",
        sef_source_document_public_id="doc-sef",
    )
    proxies = merged_slots_to_scoring_records([slot])
    p = proxies[0]
    assert p.sef_rating_extracted == 88.0
    assert p.set_rating_extracted is None


def test_combined_set_and_sef_slot():
    slot = MergedSemesterSlot(
        semester_key="k",
        academic_year="2022-2023",
        semester="1st",
        faculty_name_extracted="Name",
        faculty_identity_status="match",
        set_rating_extracted=90.0,
        set_verification_status="verified",
        set_source_document_public_id="combined",
        sef_rating_extracted=85.0,
        sef_verification_status="verified",
        sef_source_document_public_id="combined",
    )
    proxies = merged_slots_to_scoring_records([slot])
    p = proxies[0]
    assert p.set_rating_extracted == 90.0
    assert p.sef_rating_extracted == 85.0
    assert p.set_verification_status == "verified"
    assert p.sef_verification_status == "verified"


def test_no_records_incomplete_assessment():
    out = compute_criterion_a_from_records([], verified_only=False)
    assert out["incomplete"] is True
    assert out["criterionAPoints"] is None


def test_pick_best_reports_conflicting_set_values():
    d1, d2 = _doc(1), _doc(2)
    r1 = _rec(1, set_rating=90.0)
    r2 = _rec(2, set_rating=95.0)
    winner, conflicts = _pick_best([(r1, d1), (r2, d2)], "set")
    assert winner is not None
    assert len(conflicts) == 1
    assert isinstance(conflicts[0], AggregationConflict)
    assert conflicts[0].field == "SET rating"


def _flex_catalog():
    from app.services.catalog import CRITERION_A_POLICY_FLEXIBLE

    return {
        "version": "flex",
        "kras": [
            {
                "id": "kra-I",
                "criteria": [
                    {
                        "id": "kra-I-A",
                        "indicators": [
                            {
                                "id": "kra-I-A-set",
                                "subType": "SET",
                                "calculation": {"factor": 0.36, "policy": CRITERION_A_POLICY_FLEXIBLE},
                            },
                            {
                                "id": "kra-I-A-sef",
                                "subType": "SEF",
                                "calculation": {"factor": 0.24, "policy": CRITERION_A_POLICY_FLEXIBLE},
                            },
                        ],
                    }
                ],
            }
        ],
    }


def test_reviewer_confirmed_values_win_for_scoring():
    slot = MergedSemesterSlot(
        semester_key="k",
        academic_year="2022-2023",
        semester="1st",
        faculty_name_extracted=None,
        faculty_identity_status="match",
        set_rating_extracted=80.0,
        set_rating_confirmed=91.0,
        set_verification_status="verified",
        set_source_document_public_id="doc-1",
    )
    proxies = merged_slots_to_scoring_records([slot])
    cat = _flex_catalog()
    est = compute_criterion_a_from_records(proxies, verified_only=False, catalog=cat)
    ver = compute_criterion_a_from_records(proxies, verified_only=True, catalog=cat)
    assert est["incomplete"] is True
    assert ver["incomplete"] is True
    assert est["setCount"] == 1
    assert ver["setCount"] == 1
    assert est["setPoints"] == 32.76
    assert ver["setPoints"] == 32.76


def _faculty_user_2():
    from app.extensions import db
    from app.models import User, UserRole

    faculty = db.session.get(User, 2)
    if not faculty or faculty.role != UserRole.faculty:
        return None
    return faculty


def test_faculty_criterion_a_endpoint_json(app, app_ctx):
    from flask import current_app

    from app.services.auth_context import issue_api_token

    faculty = _faculty_user_2()
    if not faculty:
        return
    client = app.test_client()
    token = issue_api_token(faculty, current_app.config["API_TOKEN_TTL_HOURS"])
    res = client.get(
        "/api/faculty/teaching-effectiveness/criterion-a",
        headers={"Authorization": f"Bearer {token}", "X-Client-Type": "faculty_mobile"},
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert body is not None
    assert "scoring" in body or body.get("message")


def test_portal_criterion_a_endpoint_json(app, app_ctx):
    from flask import current_app

    from app.extensions import db
    from app.models import ReviewerAssignment, User, UserRole
    from app.services.auth_context import issue_api_token

    faculty = _faculty_user_2()
    if not faculty:
        return
    assignment = ReviewerAssignment.query.filter_by(faculty_user_id=faculty.id).first()
    actor = (
        db.session.get(User, assignment.reviewer_user_id)
        if assignment
        else User.query.filter_by(role=UserRole.admin).first()
    )
    assert actor is not None
    client = app.test_client()
    token = issue_api_token(actor, current_app.config["API_TOKEN_TTL_HOURS"])
    res = client.get(
        f"/api/portal/faculty/{faculty.portal_id()}/teaching-effectiveness/criterion-a",
        headers={"Authorization": f"Bearer {token}", "X-Client-Type": "web"},
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert body is not None
    assert "scoring" in body or body.get("message")


def test_aggregate_for_faculty_user_2_does_not_crash(app_ctx):
    """Hits real facultylinks data for user id 2 (portal u-2)."""
    slots, docs, conflicts = aggregate_set_sef_for_faculty(2)
    assert isinstance(slots, list)
    assert isinstance(docs, list)
    assert isinstance(conflicts, list)
    for slot in slots:
        assert isinstance(slot, MergedSemesterSlot)
        assert slot.semester_key
        if slot.set_rating_extracted is None and slot.set_rating_confirmed is None:
            assert slot.set_source_document_public_id is None
        if slot.sef_rating_extracted is None and slot.sef_rating_confirmed is None:
            assert slot.sef_source_document_public_id is None
    # Scoring path used by both criterion-a endpoints must not raise.
    merged_slots_to_scoring_records(slots)
