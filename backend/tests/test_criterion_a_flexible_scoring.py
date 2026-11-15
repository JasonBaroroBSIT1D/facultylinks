"""Criterion A flexible policy: average available (max six), never fixed ÷6."""

from app.models import SetSefSemesterRecord
from app.services.catalog import CRITERION_A_POLICY_FLEXIBLE
from app.services.pdf_text import PageText, PdfExtractionResult
from app.services.set_sef_extractor import extract_set_sef_semesters
from app.services.teaching_effectiveness import compute_criterion_a_from_records

FLEX_CATALOG = {
    "version": "flex-test",
    "kras": [
        {
            "id": "kra-I",
            "criteria": [
                {
                    "id": "kra-I-A",
                    "maxPoints": 60,
                    "indicators": [
                        {
                            "id": "kra-I-A-set",
                            "subType": "SET",
                            "maxPoints": 36,
                            "calculation": {
                                "kind": "set_sef_average",
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
                                "kind": "set_sef_average",
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


def _rec(*, set_r=None, sef_r=None, verified=False, ay="2024-2025", sem="1st Sem", identity="match"):
    return SetSefSemesterRecord(
        document_id=1,
        owner_user_id=1,
        academic_year=ay,
        semester=sem,
        faculty_identity_status=identity,
        set_rating_extracted=set_r,
        sef_rating_extracted=sef_r,
        # Verified scoring requires persisted confirmed values (not extracted fallback).
        set_rating_confirmed=set_r if verified and set_r is not None else None,
        sef_rating_confirmed=sef_r if verified and sef_r is not None else None,
        set_verification_status="verified" if verified and set_r is not None else "pending",
        sef_verification_status="verified" if verified and sef_r is not None else "pending",
    )


def test_two_confirmed_ratings_example_57_24():
    records = [
        _rec(set_r=93, sef_r=94, verified=True, sem="1st Sem"),
        _rec(set_r=97, sef_r=98, verified=True, ay="2024-2025", sem="2nd Sem"),
    ]
    out = compute_criterion_a_from_records(records, verified_only=True, catalog=FLEX_CATALOG)
    assert out["calculationPolicy"] == CRITERION_A_POLICY_FLEXIBLE
    assert out["setAverage"] == 95.0
    assert out["sefAverage"] == 96.0
    assert out["setPoints"] == 34.2
    assert out["sefPoints"] == 23.04
    assert out["criterionAPoints"] == 57.24
    assert out["setDenominator"] == 2
    assert out["sefDenominator"] == 2
    assert "SET: 2 ratings available" in out["availabilitySummary"]
    assert "SEF: 2 ratings available" in out["availabilitySummary"]
    assert "required ratings" not in (out["incompleteReason"] or "").lower()


def test_counts_1_2_5_6_semesters():
    for n in (1, 2, 5, 6):
        records = [
            _rec(set_r=90.0, sef_r=90.0, verified=True, ay=f"202{i}-202{i + 1}", sem="1st Sem")
            for i in range(n)
        ]
        out = compute_criterion_a_from_records(records, verified_only=True, catalog=FLEX_CATALOG)
        assert out["setCount"] == n
        assert out["sefCount"] == n
        assert out["setPoints"] == 32.4
        assert out["sefPoints"] == 21.6
        assert out["criterionAPoints"] == 54.0
        assert out["coverageComplete"] is (n >= 6)


def test_unequal_set_sef_counts():
    records = [
        _rec(set_r=100.0, sef_r=None, verified=True, sem="1st Sem"),
        _rec(set_r=80.0, sef_r=90.0, verified=True, ay="2024-2025", sem="2nd Sem"),
    ]
    # mark first SEF unverified/absent
    records[0].sef_verification_status = "pending"
    out = compute_criterion_a_from_records(records, verified_only=True, catalog=FLEX_CATALOG)
    assert out["setCount"] == 2
    assert out["sefCount"] == 1
    assert out["setAverage"] == 90.0
    assert out["sefAverage"] == 90.0
    assert out["setPoints"] == 32.4
    assert out["sefPoints"] == 21.6
    assert out["criterionAPoints"] == 54.0


def test_valid_zero_counts():
    records = [_rec(set_r=0.0, sef_r=0.0, verified=True)]
    out = compute_criterion_a_from_records(records, verified_only=True, catalog=FLEX_CATALOG)
    assert out["setCount"] == 1
    assert out["sefCount"] == 1
    assert out["setPoints"] == 0.0
    assert out["sefPoints"] == 0.0
    assert out["criterionAPoints"] == 0.0


def test_estimated_vs_verified_not_auto_verified():
    records = [_rec(set_r=93, sef_r=94, verified=False)]
    est = compute_criterion_a_from_records(records, verified_only=False, catalog=FLEX_CATALOG)
    ver = compute_criterion_a_from_records(records, verified_only=True, catalog=FLEX_CATALOG)
    assert est["criterionAPoints"] == 56.04  # 93*0.36 + 94*0.24
    assert ver["calculationUnavailable"] is True
    assert ver["criterionAPoints"] is None


def test_verified_status_without_confirmed_does_not_score():
    rec = SetSefSemesterRecord(
        document_id=1,
        owner_user_id=1,
        academic_year="2024-2025",
        semester="1st Sem",
        faculty_identity_status="match",
        set_rating_extracted=93,
        sef_rating_extracted=94,
        set_rating_confirmed=None,
        sef_rating_confirmed=None,
        set_verification_status="verified",
        sef_verification_status="verified",
    )
    ver = compute_criterion_a_from_records([rec], verified_only=True, catalog=FLEX_CATALOG)
    assert ver["calculationUnavailable"] is True
    assert ver["setCount"] == 0
    assert ver["sefCount"] == 0


def test_four_semester_fixture_57_42():
    records = [
        _rec(set_r=93, sef_r=94, verified=False, sem="1st Sem"),
        _rec(set_r=97, sef_r=98, verified=False, sem="2nd Sem"),
        _rec(set_r=94, sef_r=93, verified=False, ay="2025-2026", sem="1st Sem"),
        _rec(set_r=98, sef_r=99, verified=False, ay="2025-2026", sem="2nd Sem"),
    ]
    est = compute_criterion_a_from_records(records, verified_only=False, catalog=FLEX_CATALOG)
    assert est["setAverage"] == 95.5
    assert est["sefAverage"] == 96.0
    assert est["setPoints"] == 34.38
    assert est["sefPoints"] == 23.04
    assert est["criterionAPoints"] == 57.42
    assert est["coverageSummary"] == "4 semesters, maximum 6"
    assert est["calculationUnavailable"] is False
    assert est["incomplete"] is True  # coverage short of 6, but calculation still runs


def test_set_only_partial_subtotal():
    records = [_rec(set_r=95, sef_r=None, verified=True)]
    out = compute_criterion_a_from_records(records, verified_only=True, catalog=FLEX_CATALOG)
    assert out["setPoints"] == 34.2
    assert out["sefPoints"] is None
    assert out["criterionAPoints"] is None
    assert out["partialSubtotal"] == 34.2
    assert "Missing SEF" in out["incompleteReason"]


def test_neither_component_unavailable():
    out = compute_criterion_a_from_records([], verified_only=True, catalog=FLEX_CATALOG)
    assert out["calculationUnavailable"] is True
    assert out["criterionAPoints"] is None
    assert out["setPoints"] is None
    assert out["sefPoints"] is None


def test_aime_summary_table_headers_original_ratings():
    text = """
--- Page 1 ---
SUMMARY OF INDIVIDUAL FACULTY RATING
Faculty: Aime Jean Gumatay
Semester / School Year
Students
Rating
Students
x 60%
Supervisor
Rating
Supervisor
x 40%
Semester
Average
1st Sem., SY 2024-2025
93.00
55.80
94.00
37.60
93.40
2nd Sem., SY 2024-2025
97.00
58.20
98.00
39.20
97.40
"""
    pdf = PdfExtractionResult(pages=[PageText(page_number=1, text=text, source="pdf_text")], full_text=text)
    records = extract_set_sef_semesters(pdf)
    assert len(records) == 2
    assert records[0].set_rating == 93.0
    assert records[0].sef_rating == 94.0
    assert records[1].set_rating == 97.0
    assert records[1].sef_rating == 98.0
    # Must not pick weighted columns (55.80 / 37.60)
    assert records[0].set_rating != 55.8
    assert records[0].sef_rating != 37.6


def test_duplicate_semester_rows_merged_by_key():
    text = """
--- Page 1 ---
SUMMARY OF INDIVIDUAL FACULTY RATING
Faculty: Dup Test
1st Sem., SY 2024-2025
93.00
55.80
94.00
37.60
93.40
1st Sem., SY 2024-2025
93.00
55.80
94.00
37.60
93.40
"""
    pdf = PdfExtractionResult(pages=[PageText(page_number=1, text=text, source="pdf_text")], full_text=text)
    records = extract_set_sef_semesters(pdf)
    assert len(records) == 1
