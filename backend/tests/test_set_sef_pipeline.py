from app.services.pdf_text import PdfExtractionResult, PageText
from app.services.set_sef_extractor import extract_set_sef_semesters
from app.services.set_sef_identity import classify_faculty_identity
from app.services.teaching_effectiveness import compute_criterion_a_from_records
from app.models import SetSefSemesterRecord


def _synthetic_pdf_text() -> PdfExtractionResult:
    text = """
--- Page 1 ---
Academic Year 2022-2023
1st Semester
Faculty Name: Maria Santos Cruz
Student Evaluation of Teachers (SET)
Overall Rating: 92.5 / 100

--- Page 2 ---
Academic Year 2022-2023
2nd Semester
Faculty Name: Maria Santos Cruz
Supervisor's Evaluation of Faculty (SEF)
Overall Rating: 88 / 100
"""
    return PdfExtractionResult(
        pages=[PageText(page_number=1, text=text, source="pdf_text")],
        full_text=text,
    )


def test_extract_semesters_from_synthetic_text():
    records = extract_set_sef_semesters(_synthetic_pdf_text())
    assert len(records) >= 1
    assert any(r.set_rating is not None or r.sef_rating is not None for r in records)


def test_faculty_identity_match():
    assert classify_faculty_identity("Maria Santos Cruz", "Maria Santos Cruz") == "match"
    assert classify_faculty_identity("Maria Santos Cruz", "M. Santos Cruz") in ("needs_confirmation", "match")
    assert classify_faculty_identity("Maria Santos Cruz", "John Dela Cruz") == "mismatch"


JASON_SUMMARY_TEXT = """
--- Page 1 ---
UNIVERSITY OF SCIENCE AND TECHNOLOGY OF SOUTHERN PHILIPPINES
SUMMARY OF INDIVIDUAL FACULTY RATING
Faculty: Jason Baroro
Semester / School Year
Students Rating
Supervisor Rating
1st Sem., SY 2023-2024
92.00
55.20
94.00
37.60
92.80
2nd Sem., SY 2023-2024
96.00
57.60
97.00
38.80
96.40
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
1st Sem., SY 2025-2026
94.00
56.40
93.00
37.20
93.60
2nd Sem., SY 2025-2026
98.00
58.80
99.00
39.60
98.40
"""


def test_extract_ustp_summary_table_six_semesters():
    pdf = PdfExtractionResult(
        pages=[PageText(page_number=1, text=JASON_SUMMARY_TEXT, source="pdf_text")],
        full_text=JASON_SUMMARY_TEXT,
    )
    records = extract_set_sef_semesters(pdf)
    assert len(records) == 6
    assert records[0].faculty_name == "Jason Baroro"
    assert records[0].set_rating == 92.0
    assert records[0].sef_rating == 94.0
    assert records[0].academic_year == "2023-2024"
    assert records[0].semester == "1st Sem"
    assert records[5].set_rating == 98.0
    assert records[5].sef_rating == 99.0


def test_incomplete_scoring():
    rec = SetSefSemesterRecord(
        document_id=1,
        owner_user_id=1,
        set_rating_extracted=90,
        set_verification_status="verified",
        faculty_identity_status="match",
    )
    from app.services.catalog import CRITERION_A_POLICY_FLEXIBLE

    flex_cat = {
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
    out = compute_criterion_a_from_records([rec], verified_only=True, catalog=flex_cat)
    assert out["incomplete"] is True
    assert out["setPoints"] == 32.4
    assert out["criterionAPoints"] is None
