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
    assert classify_faculty_identity("Jason Baroro", "Baroro, Jason") == "match"


def test_faculty_name_header_ocr_label():
    from app.services.set_sef_faculty_name import extract_faculty_name_from_text

    assert extract_faculty_name_from_text("Faculty: Baroro, Jason Department: IT") == "Baroro, Jason"


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


JASON_OCR_NOISY_TEXT = """
--- Page 1 ---
SUMMARY OF INDIVIDUAL FACULTY RATIN G
Faculty: Baroro, Jason Department: IT Department
Position: Temporary (Instructor I) Designation: None

1°" SEM., SY 2025-2026
STUDENTS (60 % 98.80 57.66
SUPERVISOR (40% X .40 39.47
AVERAGE OB a a aie ON tee
ADJECTIVAL RATING
"""


BARORO_SIDE_BY_SIDE_2025 = """
--- Page 1 ---
SUMMARY OF INDIVIDUAL FACULTY RATING
Faculty: Baroro, Jason Department: IT Department
--- SET/SEF table band OCR ---
RATINGS 1st SEM., SY 2025-2026 2nd SEM., SY 2025-2026
STUDENTS (60 % 98.80 59.20 96.10 57.66
SUPERVISOR (40% 100.00 40.00 98.67 39.47
OVER-ALL AVERAGE 98.60
"""


def test_extract_ustp_side_by_side_two_semesters_four_ratings():
    """Horizontal two-column AY row must not pair 1st SET with 2nd SEF."""
    pdf = PdfExtractionResult(
        pages=[PageText(page_number=1, text=BARORO_SIDE_BY_SIDE_2025, source="ocr")],
        full_text=BARORO_SIDE_BY_SIDE_2025,
    )
    records = extract_set_sef_semesters(pdf)
    assert len(records) == 2
    by_sem = {r.semester: r for r in records}
    assert by_sem["1st Sem"].set_rating == 98.80
    assert by_sem["1st Sem"].sef_rating == 100.00
    assert by_sem["2nd Sem"].set_rating == 96.10
    assert by_sem["2nd Sem"].sef_rating == 98.67
    assert all(r.academic_year == "2025-2026" for r in records)


def test_preserve_reviewer_only_when_extracted_unchanged():
    from app.services.set_sef_processor import _preserve_reviewer_fields

    prev = SetSefSemesterRecord(
        document_id=1,
        owner_user_id=1,
        set_rating_extracted=98.80,
        sef_rating_extracted=98.67,
        set_rating_confirmed=98.80,
        sef_rating_confirmed=98.67,
        set_verification_status="verified",
        sef_verification_status="verified",
    )
    unchanged = SetSefSemesterRecord(
        document_id=1,
        owner_user_id=1,
        set_rating_extracted=98.80,
        sef_rating_extracted=98.67,
    )
    _preserve_reviewer_fields(unchanged, prev)
    assert unchanged.set_verification_status == "verified"
    assert unchanged.sef_verification_status == "verified"

    corrected = SetSefSemesterRecord(
        document_id=1,
        owner_user_id=1,
        set_rating_extracted=98.80,
        sef_rating_extracted=100.00,
    )
    _preserve_reviewer_fields(corrected, prev)
    assert corrected.set_verification_status != "verified"
    assert corrected.sef_verification_status != "verified"
    assert corrected.sef_rating_confirmed is None


def test_extract_ustp_ocr_noisy_summary_original_ratings():
    """OCR noise must yield original SET; infer SEF from contribution when original is missing (ambiguous)."""
    pdf = PdfExtractionResult(
        pages=[PageText(page_number=1, text=JASON_OCR_NOISY_TEXT, source="ocr")],
        full_text=JASON_OCR_NOISY_TEXT,
    )
    records = extract_set_sef_semesters(pdf)
    assert len(records) == 1
    rec = records[0]
    assert rec.academic_year == "2025-2026"
    assert rec.semester == "1st Sem"
    assert rec.faculty_name == "Baroro, Jason"
    assert rec.set_rating == 98.80
    assert rec.sef_rating in (98.67, 98.68)
    assert rec.ambiguous is True
    assert rec.set_rating != 57.66


BARORO_COLUMNAR_2023 = """
--- Page 1 ---
RATINGS
1st SEM., SY 2023-2024
2nd SEM., SY 2023-2024
STUDENTS (60%)
96
X .60
57.6
96
X .60
57.6
SUPERVISOR (40%)
97
X .40
38.8
98
X .40
39.2
AVERAGE
96.4
96.8
OVER-ALL AVERAGE
96.6
ADJECTIVAL RATING
Outstanding
"""


BARORO_COLUMNAR_2024_UPDATED = """
--- Page 1 ---
RATINGS
STUDENTS (60%)
SUPERVISOR (40%)
AVERAGE
OVER-ALL AVERAGE
ADJECTIVAL RATING
1st SEM., SY 2024-2025
2nd SEM., SY 2024-2025
90
X .60
54
97
X .60
58.2
95
X .40
38
98
X .40
39.2
92
97.4
94.7
Very satisfactory
"""


def test_extract_baroro_columnar_clear_layout():
    pdf = PdfExtractionResult(
        pages=[PageText(page_number=1, text=BARORO_COLUMNAR_2023, source="pdf_text")],
        full_text=BARORO_COLUMNAR_2023,
    )
    records = extract_set_sef_semesters(pdf)
    assert len(records) == 2
    assert records[0].set_rating == 96.0 and records[0].sef_rating == 97.0
    assert records[1].set_rating == 96.0 and records[1].sef_rating == 98.0


def test_extract_baroro_columnar_trailing_headers_layout():
    pdf = PdfExtractionResult(
        pages=[PageText(page_number=1, text=BARORO_COLUMNAR_2024_UPDATED, source="pdf_text")],
        full_text=BARORO_COLUMNAR_2024_UPDATED,
    )
    records = extract_set_sef_semesters(pdf)
    assert len(records) == 2
    assert records[0].set_rating == 90.0 and records[0].sef_rating == 95.0
    assert records[1].set_rating == 97.0 and records[1].sef_rating == 98.0


def test_incomplete_scoring():
    rec = SetSefSemesterRecord(
        document_id=1,
        owner_user_id=1,
        set_rating_extracted=90,
        set_rating_confirmed=90,
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
