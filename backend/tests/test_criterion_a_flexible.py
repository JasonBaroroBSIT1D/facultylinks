"""Flexible Criterion A: average of available ratings, max six semester slots."""

from app.models import SetSefSemesterRecord
from app.services.catalog import CRITERION_A_POLICY_FLEXIBLE
from app.services.set_sef_aggregation import (
    AggregationConflict,
    MergedSemesterSlot,
    apply_semester_slot_window,
    merged_slots_to_scoring_records,
)
from app.services.teaching_effectiveness import compute_criterion_a_from_records


def _flex_catalog():
    return {
        "version": "flex-test",
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
                                "maxPoints": 36,
                                "calculation": {
                                    "factor": 0.36,
                                    "semesterCount": 6,
                                    "policy": CRITERION_A_POLICY_FLEXIBLE,
                                },
                            },
                            {
                                "id": "kra-I-A-sef",
                                "subType": "SEF",
                                "maxPoints": 24,
                                "calculation": {
                                    "factor": 0.24,
                                    "semesterCount": 6,
                                    "policy": CRITERION_A_POLICY_FLEXIBLE,
                                },
                            },
                        ],
                    }
                ],
            }
        ],
    }


_FLEX = _flex_catalog()


def _rec(**kwargs) -> SetSefSemesterRecord:
    base = dict(
        document_id=1,
        owner_user_id=1,
        faculty_identity_status="match",
        set_verification_status="verified",
        sef_verification_status="verified",
        superseded_by_id=None,
    )
    base.update(kwargs)
    return SetSefSemesterRecord(**base)


def test_exact_user_example_values():
    records = [
        _rec(set_rating_confirmed=92.0, sef_rating_confirmed=None, sef_verification_status="pending"),
        _rec(set_rating_confirmed=96.0, sef_rating_confirmed=None, sef_verification_status="pending"),
        _rec(set_rating_confirmed=93.0, sef_rating_confirmed=None, sef_verification_status="pending"),
        _rec(set_rating_confirmed=90.0, sef_rating_confirmed=94.0),
        _rec(set_rating_confirmed=90.0, sef_rating_confirmed=97.0),
    ]
    # Isolate exact SET [92,96,93] and SEF [94,97] on distinct rows
    records = [
        _rec(set_rating_confirmed=92.0, sef_rating_confirmed=None, sef_verification_status="pending"),
        _rec(set_rating_confirmed=96.0, sef_rating_confirmed=None, sef_verification_status="pending"),
        _rec(set_rating_confirmed=93.0, sef_rating_confirmed=None, sef_verification_status="pending"),
        _rec(set_rating_confirmed=None, set_verification_status="pending", sef_rating_confirmed=94.0),
        _rec(set_rating_confirmed=None, set_verification_status="pending", sef_rating_confirmed=97.0),
    ]
    out = compute_criterion_a_from_records(records, verified_only=True, catalog=_FLEX)
    assert out["setPoints"] == 33.72
    assert out["sefPoints"] == 22.92
    assert out["criterionAPoints"] == 56.64


def test_valid_zero_rating_counts():
    records = [_rec(set_rating_confirmed=0.0, sef_rating_confirmed=100.0)]
    out = compute_criterion_a_from_records(records, verified_only=True, catalog=_FLEX)
    assert out["setPoints"] == 0.0
    assert out["sefPoints"] == 24.0
    assert out["criterionAPoints"] == 24.0
    assert out["combinedComplete"] is True


def test_one_component_only_partial():
    records = [_rec(set_rating_confirmed=90.0, sef_rating_confirmed=None, sef_verification_status="pending")]
    out = compute_criterion_a_from_records(records, verified_only=False, catalog=_FLEX)
    assert out["setPoints"] == 32.4
    assert out["sefPoints"] is None
    assert out["criterionAPoints"] is None
    assert out["partialSubtotal"] == 32.4


def test_six_semesters_full_coverage():
    records = []
    for i in range(6):
        records.append(_rec(set_rating_confirmed=100.0, sef_rating_confirmed=100.0, semester=f"S{i}"))
    out = compute_criterion_a_from_records(records, verified_only=True, catalog=_FLEX)
    assert out["coverageComplete"] is True
    assert out["criterionAPoints"] == 60.0


def test_no_ratings_unavailable():
    out = compute_criterion_a_from_records([], verified_only=False, catalog=_FLEX)
    assert out["calculationUnavailable"] is True
    assert out["setPoints"] is None
    assert out["criterionAPoints"] is None


def test_more_than_six_slots_needs_selection_then_scores():
    slots = [
        MergedSemesterSlot(
            semester_key=f"2020-2021|{i}",
            academic_year="2020-2021",
            semester=str(i),
            faculty_name_extracted="F",
            faculty_identity_status="match",
            set_rating_extracted=90.0,
            set_verification_status="verified",
        )
        for i in range(7)
    ]
    scoring, excluded, findings, needs_selection = apply_semester_slot_window(slots)
    assert needs_selection is True
    assert len(scoring) == 0
    assert len(excluded) == 7
    assert findings[0]["code"] == "semester_window_selection_required"

    pick = [f"2020-2021|{i}" for i in range(6)]
    scoring2, excluded2, findings2, needs2 = apply_semester_slot_window(slots, selected_semester_keys=pick)
    assert needs2 is False
    assert len(scoring2) == 6
    assert len(excluded2) == 1
    assert not findings2

    out = compute_criterion_a_from_records(
        merged_slots_to_scoring_records(scoring2),
        verified_only=False,
        catalog=_FLEX,
    )
    assert out["setPoints"] == 32.4
    assert out["calculationUnavailable"] is False


def test_conflict_excludes_component_from_average():
    slot = MergedSemesterSlot(
        semester_key="k",
        academic_year="2022-2023",
        semester="1st",
        faculty_name_extracted="Name",
        faculty_identity_status="match",
        set_rating_extracted=90.0,
        set_verification_status="verified",
    )
    conflicts = [
        AggregationConflict(
            semester_key="k",
            field="SET rating",
            document_ids=[1, 2],
            explanation="conflict",
        )
    ]
    proxies = merged_slots_to_scoring_records([slot], conflicts)
    out = compute_criterion_a_from_records(proxies, verified_only=False, catalog=_FLEX)
    assert out["setCount"] == 0
    assert out["setPoints"] is None
