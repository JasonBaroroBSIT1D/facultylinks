"""Rule-based parsing of SET/SEF combined PDF text into semester records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.pdf_text import PdfExtractionResult

SEMESTER_RE = re.compile(
    r"(?i)(?:1st|first|1[°\"'*]+|1)\s*sem(?:ester)?|(?:2nd|second|2[°\"'*]+|2)\s*sem(?:ester)?|summer"
)
AY_RE = re.compile(r"(?:(?:AY|Academic\s*Year|SY)\s*[:\-]?\s*)?((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2})")
SET_OVERALL_RE = re.compile(
    r"(?i)student\s+evaluation\s+of\s+teachers?|\bSET\b.*?(?:overall|mean|rating)",
)
SEF_OVERALL_RE = re.compile(
    r"(?i)supervisor(?:'?s)?\s+evaluation\s+of\s+faculty|\bSEF\b.*?(?:overall|mean|rating)",
)
RATING_RE = re.compile(r"(?:(?:overall|mean|rating|score)\s*[:\-]?\s*)(\d{1,3}(?:\.\d{1,2})?)\s*(?:/\s*(\d{2,3}))?")
NAME_RE = re.compile(
    r"(?i)(?:faculty\s+name|name\s+of\s+faculty|faculty\s+evaluated|ratee|\bfaculty)\s*[:\-]\s*([A-Za-z][A-Za-z\s.\-',]+)"
)
SCALE_100_RE = re.compile(r"/\s*100\b")

BLOCK_SPLIT = re.compile(r"\n{2,}|(?=--- Page \d+ ---)")

# USTP-style combined summary table (Students Rating × 60% / Supervisor Rating × 40%).
SUMMARY_TABLE_MARKER = re.compile(
    r"(?i)summary\s+of\s+individual\s+faculty\s+ratin|students?\s*\(?\s*60\s*%|students\s*\n\s*rating"
)
FACULTY_COLON_RE = re.compile(
    r"(?i)\bfaculty\s*:\s*([A-Za-z][A-Za-z\s.\-',]+?)(?:\n|Department|Position|Designation|$)"
)
SEMESTER_TABLE_ROW_RE = re.compile(
    r"(?i)(1st|2nd)\s*Sem\.?\s*,\s*SY\s*((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2})\s*"
    r"[\s\n]+"
    r"(\d{2,3}(?:\.\d+)?)\s+"
    r"(\d{2,3}(?:\.\d+)?)\s+"
    r"(\d{2,3}(?:\.\d+)?)\s+"
    r"(\d{2,3}(?:\.\d+)?)\s+"
    r"(\d{2,3}(?:\.\d+)?)",
    re.MULTILINE,
)
STUDENT_SUPERVISOR_PAIR_RE = re.compile(
    r"(?i)students?\s+rating|supervisor\s+rating|students?\s*\(?\s*60\s*%|supervisor\s*\(?\s*40\s*%"
)
# OCR-tolerant USTP semester heading, e.g. 1°" SEM., SY 2025-2026
OCR_SEM_HEADING_RE = re.compile(
    r"(?i)(1|2)\s*(?:st|nd|[°\"'*]+)?[^\w\n]{0,4}\s*sem\.?\s*[,\.]?\s*(?:SY|AY)?\s*"
    r"((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2})"
)
COLUMNAR_SEM_HEADER_RE = re.compile(
    r"(?i)(1st|2nd|first|second)\s*sem\.?\s*,?\s*(?:sy\s*)?((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2})"
)
WEIGHTED_CONTRIB_RE = re.compile(r"(?i)x\s*\.\s*(\d{1,2})\s+(\d+(?:\.\d+)?)")
STUDENTS_COMPONENT_LINE_RE = re.compile(
    r"(?i)students?\s*(?:\([^)\n]{0,24}60[^)\n]{0,12}\)|\(?\s*60\s*%?)[^\n]{0,80}"
)
SUPERVISOR_COMPONENT_LINE_RE = re.compile(
    r"(?i)supervisor\s*(?:\([^)\n]{0,24}40[^)\n]{0,12}\)|\(?\s*40\s*%?)[^\n]{0,80}"
)
DUAL_SEM_HEADER_LINE_RE = re.compile(
    r"(?i)(?:1|first|1[°\"'*]+|15\b)[^\d\n]{0,40}sem"
    r".{0,160}"
    r"(?:2|second|2nd|9\s*nd|2[°\"'*]+)[^\d\n]{0,40}sem"
)
SET_SEF_TABLE_BAND_MARKER = "--- SET/SEF table band OCR ---"


@dataclass
class ExtractedSemester:
    academic_year: str | None = None
    semester: str | None = None
    faculty_name: str | None = None
    set_rating: float | None = None
    set_scale: str | None = None
    sef_rating: float | None = None
    sef_scale: str | None = None
    set_pages: list[int] = field(default_factory=list)
    sef_pages: list[int] = field(default_factory=list)
    set_excerpt: str = ""
    sef_excerpt: str = ""
    raw_fragment: str = ""
    ambiguous: bool = False


def _norm_semester(raw: str) -> str | None:
    t = raw.lower()
    if "summer" in t:
        return "Summer"
    if "2nd" in t or "second" in t or re.search(r"\b2[°\"'*]*\b", t):
        return "2nd Sem"
    if "1st" in t or "first" in t or re.search(r"\b1[°\"'*]*\b", t):
        return "1st Sem"
    if re.search(r"(?i)\b2\b.*sem", t):
        return "2nd Sem"
    if re.search(r"(?i)\b1\b.*sem", t):
        return "1st Sem"
    return None


def _contrib_matches_original(original: float, contrib: float, weight_pct: int) -> bool:
    expected = original * weight_pct / 100.0
    return abs(contrib - expected) <= max(0.35, expected * 0.025)


def _original_ratings_paired_line(line: str, weight_pct: int) -> list[float]:
    """Original 0–100 ratings from one horizontal row (one value per semester column)."""
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", line)]
    skip = {
        float(weight_pct),
        weight_pct / 100.0,
        round(weight_pct / 100.0, 2),
        round(weight_pct / 100.0, 1),
    }
    originals: list[float] = []
    i = 0
    while i < len(nums):
        n = nums[i]
        if n in skip:
            i += 1
            continue
        if i + 1 < len(nums) and nums[i + 1] not in skip:
            if _contrib_matches_original(n, nums[i + 1], weight_pct):
                if 0.0 <= n <= 100.0:
                    originals.append(n)
                i += 2
                continue
        if 50.0 <= n <= 100.0:
            originals.append(n)
        i += 1
    return originals


def _original_rating_from_weighted_line(line: str, weight_pct: int) -> tuple[float | None, bool]:
    """Pick the original 0–100 rating, not the 60%/40% contribution column.

    Returns (rating, inferred_from_contribution). When the text layer only
    preserved ``X .40 39.47`` without the original, recover from contribution
  with inferred=True (ambiguous).
    """
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", line)]
    skip = {float(weight_pct), round(weight_pct / 100.0, 2), round(weight_pct / 100.0, 1)}
    candidates = [n for n in nums if n not in skip]
    scores = [n for n in candidates if 0.0 <= n <= 100.0 and (n >= 50.0 or n == 0.0)]
    if scores:
        return scores[0], False
    contribution_match = [m for m in WEIGHTED_CONTRIB_RE.finditer(line) if int(m.group(1)) == weight_pct]
    if not contribution_match and weight_pct == 40:
        contribution_match = list(WEIGHTED_CONTRIB_RE.finditer(line))
    for m in contribution_match:
        pct = int(m.group(1))
        if pct not in (60, 40):
            continue
        contrib = float(m.group(2))
        if contrib <= 0 or contrib >= 100:
            continue
        if pct != weight_pct:
            continue
        return round(contrib / (pct / 100.0), 2), True
    return None, False


def _parse_rating_near(context: str) -> tuple[float | None, str | None]:
    for m in RATING_RE.finditer(context):
        val = float(m.group(1))
        scale = m.group(2)
        if scale:
            return val, f"0-{scale}"
        if SCALE_100_RE.search(context[m.start() : m.end() + 12]):
            return val, "0-100"
        if val <= 5:
            return val, "0-5"
        return val, "0-100"
    nums = re.findall(r"\b(\d{2,3}(?:\.\d+)?)\b", context)
    for n in nums:
        v = float(n)
        if 50 <= v <= 100:
            return v, "0-100"
    return None, None


def _page_number_at_offset(pdf: PdfExtractionResult, char_offset: int) -> int:
    text = pdf.full_text or ""
    if char_offset <= 0:
        return pdf.pages[0].page_number if pdf.pages else 1
    prefix = text[:char_offset]
    markers = [int(x) for x in re.findall(r"--- Page (\d+) ---", prefix)]
    if markers:
        return markers[-1]
    return pdf.pages[0].page_number if pdf.pages else 1


def _parse_ustp_ocr_summary_sheet(pdf: PdfExtractionResult, faculty_name: str | None) -> list[ExtractedSemester]:
    """Parse OCR-noisy USTP 'Summary of Individual Faculty Rating' sheets.

    Uses Students (60%) / Supervisor (40%) lines and keeps the original rating
    (first 50–100 value), never the already-weighted contribution.
    """
    text = pdf.full_text or ""
    if not text.strip():
        return []
    if not (
        SUMMARY_TABLE_MARKER.search(text)
        or STUDENTS_COMPONENT_LINE_RE.search(text)
        or SUPERVISOR_COMPONENT_LINE_RE.search(text)
    ):
        return []

    records: list[ExtractedSemester] = []
    for m in OCR_SEM_HEADING_RE.finditer(text):
        sem_label = _norm_semester(f"{m.group(1)} sem") or f"{m.group(1)} Sem"
        academic_year = f"{m.group(2)}-{m.group(3)}"
        window = text[m.start() : min(len(text), m.end() + 500)]
        set_line = STUDENTS_COMPONENT_LINE_RE.search(window)
        sef_line = SUPERVISOR_COMPONENT_LINE_RE.search(window)
        student_rating, set_inferred = (
            _original_rating_from_weighted_line(set_line.group(0), 60) if set_line else (None, False)
        )
        supervisor_rating, sef_inferred = (
            _original_rating_from_weighted_line(sef_line.group(0), 40) if sef_line else (None, False)
        )
        if student_rating is None and supervisor_rating is None:
            continue
        ambiguous = set_inferred or sef_inferred
        if sef_line and supervisor_rating is None:
            ambiguous = True
        page_no = _page_number_at_offset(pdf, m.start())
        records.append(
            ExtractedSemester(
                academic_year=academic_year,
                semester=sem_label,
                faculty_name=faculty_name,
                set_rating=student_rating,
                set_scale="0-100" if student_rating is not None else None,
                sef_rating=supervisor_rating,
                sef_scale="0-100" if supervisor_rating is not None else None,
                set_pages=[page_no] if student_rating is not None else [],
                sef_pages=[page_no] if supervisor_rating is not None else [],
                set_excerpt=(set_line.group(0)[:500] if set_line else ""),
                sef_excerpt=(sef_line.group(0)[:500] if sef_line else ""),
                raw_fragment=window[:2000],
                ambiguous=ambiguous,
            )
        )
    return records


def _parse_ustp_side_by_side_semester_columns(
    pdf: PdfExtractionResult, faculty_name: str | None
) -> list[ExtractedSemester]:
    """Two semester columns on one row (same AY), typical on CS FORM 212 camera scans."""
    text = pdf.full_text or ""
    if not text.strip():
        return []
    if not (
        SUMMARY_TABLE_MARKER.search(text)
        or DUAL_SEM_HEADER_LINE_RE.search(text)
        or SET_SEF_TABLE_BAND_MARKER in text
    ):
        return []

    if faculty_name is None:
        fm = FACULTY_COLON_RE.search(text)
        if fm:
            faculty_name = fm.group(1).strip()

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    header_indices: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if not DUAL_SEM_HEADER_LINE_RE.search(line):
            continue
        ay_m = AY_RE.search(line)
        if not ay_m:
            continue
        academic_year = f"{ay_m.group(1)}-{ay_m.group(2)}"
        header_indices.append((i, academic_year))

    if not header_indices:
        return []

    records: list[ExtractedSemester] = []
    page_no = pdf.pages[0].page_number if pdf.pages else 1
    for hi, academic_year in header_indices:
        window = lines[hi : min(len(lines), hi + 18)]
        if academic_year.endswith("-"):
            ay_fix = AY_RE.search("\n".join(window))
            if ay_fix:
                academic_year = f"{ay_fix.group(1)}-{ay_fix.group(2)}"
        set_line = next((ln for ln in window if STUDENTS_COMPONENT_LINE_RE.search(ln)), None)
        sef_line = next((ln for ln in window if SUPERVISOR_COMPONENT_LINE_RE.search(ln)), None)
        if not set_line and not sef_line:
            continue
        set_vals = _original_ratings_paired_line(set_line or "", 60)
        sef_vals = _original_ratings_paired_line(sef_line or "", 40)
        if len(set_vals) + len(sef_vals) < 3:
            continue
        sem_labels = ("1st Sem", "2nd Sem")
        for idx, sem in enumerate(sem_labels):
            set_r = set_vals[idx] if idx < len(set_vals) else None
            sef_r = sef_vals[idx] if idx < len(sef_vals) else None
            if set_r is None and sef_r is None:
                continue
            ambiguous = len(set_vals) != 2 or len(sef_vals) != 2
            records.append(
                ExtractedSemester(
                    academic_year=academic_year,
                    semester=sem,
                    faculty_name=faculty_name,
                    set_rating=set_r,
                    set_scale="0-100" if set_r is not None else None,
                    sef_rating=sef_r,
                    sef_scale="0-100" if sef_r is not None else None,
                    set_pages=[page_no] if set_r is not None else [],
                    sef_pages=[page_no] if sef_r is not None else [],
                    set_excerpt=(set_line or "")[:500],
                    sef_excerpt=(sef_line or "")[:500],
                    raw_fragment="\n".join(window)[:2000],
                    ambiguous=ambiguous,
                )
            )
    return records


def _parse_summary_rating_table(pdf: PdfExtractionResult) -> list[ExtractedSemester]:
    text = pdf.full_text or ""
    if not text.strip():
        return []
    if not (SUMMARY_TABLE_MARKER.search(text) or SEMESTER_TABLE_ROW_RE.search(text) or STUDENT_SUPERVISOR_PAIR_RE.search(text)):
        return []

    faculty_name: str | None = None
    fm = FACULTY_COLON_RE.search(text)
    if fm:
        faculty_name = fm.group(1).strip()
        if re.search(r"(?i)sample\s+data|for\s+system\s+testing", faculty_name):
            faculty_name = re.sub(r"(?i)\s*sample.*$", "", faculty_name).strip() or fm.group(1).strip()

    records: list[ExtractedSemester] = []
    for m in SEMESTER_TABLE_ROW_RE.finditer(text):
        sem_label = _norm_semester(m.group(1) + " sem") or f"{m.group(1)} Sem"
        academic_year = f"{m.group(2)}-{m.group(3)}"
        # Groups 4/6 are original student/supervisor ratings; 5/7 are weighted contributions.
        student_rating = float(m.group(4))
        supervisor_rating = float(m.group(6))
        excerpt = text[m.start() : min(len(text), m.end() + 120)]
        page_no = _page_number_at_offset(pdf, m.start())
        records.append(
            ExtractedSemester(
                academic_year=academic_year,
                semester=sem_label,
                faculty_name=faculty_name,
                set_rating=student_rating,
                set_scale="0-100",
                sef_rating=supervisor_rating,
                sef_scale="0-100",
                set_pages=[page_no],
                sef_pages=[page_no],
                set_excerpt=f"Students rating: {student_rating} (from semester summary row)\n{excerpt[:400]}",
                sef_excerpt=f"Supervisor rating: {supervisor_rating} (from semester summary row)\n{excerpt[:400]}",
                raw_fragment=excerpt[:2000],
            )
        )
    if records:
        return records
    side_by_side = _parse_ustp_side_by_side_semester_columns(pdf, faculty_name)
    if side_by_side:
        return side_by_side
    ocr_records = _parse_ustp_ocr_summary_sheet(pdf, faculty_name)
    if ocr_records and any(r.set_rating is not None or r.sef_rating is not None for r in ocr_records):
        return ocr_records
    columnar = _parse_ustp_columnar_rating_sheet(pdf, faculty_name)
    if columnar:
        return columnar
    return ocr_records


def _line_is_table_noise(line: str) -> bool:
    return bool(
        re.search(
            r"(?i)^(?:students?|supervisor|average|over-?all|adject|ratings?|percentage)\b",
            line,
        )
    )


def _parse_triplet_originals(lines: list[str], start: int, end: int) -> list[float]:
    """Collect original ratings from ``value → X .weight → contribution`` triplets."""
    originals: list[float] = []
    i = start
    while i < end:
        line = lines[i]
        if _line_is_table_noise(line) or COLUMNAR_SEM_HEADER_RE.search(line):
            i += 1
            continue
        if re.match(r"^\d{1,3}(?:\.\d+)?\s*$", line):
            val = float(line)
            if i + 1 < end and re.search(r"(?i)^x\s*\.", lines[i + 1]):
                originals.append(val)
                i += 3
                continue
        i += 1
    return originals


def _parse_column_originals(lines: list[str], start: int, end: int, weight_pct: int) -> list[float]:
    """Parse vertical USTP column groups: original → X .weight → contribution."""
    originals: list[float] = []
    i = start
    while i < end:
        line = lines[i]
        if _line_is_table_noise(line):
            i += 1
            continue
        if re.match(r"^\d{1,3}(?:\.\d+)?\s*$", line):
            val = float(line)
            if i + 1 < end and re.search(r"(?i)^x\s*\.", lines[i + 1]):
                wm = re.search(r"x\s*\.\s*(\d{1,2})", lines[i + 1], re.I)
                if wm and int(wm.group(1)) == weight_pct:
                    originals.append(val)
                    i += 3
                    continue
            if weight_pct == 60 and 0 <= val <= 100 and i + 1 < end and re.search(r"(?i)^x\s*\.", lines[i + 1]):
                originals.append(val)
                i += 3
                continue
        i += 1
    return originals


def _parse_ustp_columnar_rating_sheet(
    pdf: PdfExtractionResult, faculty_name: str | None
) -> list[ExtractedSemester]:
    """CS FORM–style sheets with semester headers as columns and vertical SET/SEF rows."""
    text = pdf.full_text or ""
    if not text.strip():
        return []
    if SEMESTER_TABLE_ROW_RE.search(text):
        return []

    headers = list(COLUMNAR_SEM_HEADER_RE.finditer(text))
    if not headers:
        return []

    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("--- Page")]
    students_i = next((i for i, ln in enumerate(lines) if re.search(r"(?i)^students", ln)), None)
    supervisor_i = next((i for i, ln in enumerate(lines) if re.search(r"(?i)^supervisor", ln)), None)
    average_i = next(
        (i for i, ln in enumerate(lines) if re.search(r"(?i)^(average|over-?all)", ln)),
        len(lines),
    )

    header_line_indices = [i for i, ln in enumerate(lines) if COLUMNAR_SEM_HEADER_RE.search(ln)]

    if faculty_name is None:
        fm = FACULTY_COLON_RE.search(text)
        if fm:
            faculty_name = fm.group(1).strip()

    sem_specs: list[tuple[str, str]] = []
    seen_keys: set[str] = set()
    for m in headers:
        sem = _norm_semester(m.group(1) + " sem") or f"{m.group(1)} Sem"
        ay = f"{m.group(2)}-{m.group(3)}"
        key = f"{ay}|{sem}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        sem_specs.append((ay, sem))

    set_vals: list[float] = []
    sef_vals: list[float] = []
    n_sem = len(sem_specs)

    # Layout A: semester headers, then Students block, then Supervisor block (clear scans).
    if (
        students_i is not None
        and supervisor_i is not None
        and supervisor_i > students_i
        and header_line_indices
        and min(header_line_indices) < students_i
    ):
        set_vals = _parse_column_originals(lines, students_i + 1, supervisor_i, 60)
        sef_vals = _parse_column_originals(lines, supervisor_i + 1, average_i, 40)
    # Layout B: row labels first, semester headers, then one numeric block (SET cols then SEF cols).
    elif header_line_indices:
        data_start = max(header_line_indices) + 1
        data_end = average_i if average_i > data_start else len(lines)
        all_orig = _parse_triplet_originals(lines, data_start, data_end)
        if n_sem and len(all_orig) >= n_sem * 2:
            set_vals = all_orig[:n_sem]
            sef_vals = all_orig[n_sem : n_sem * 2]
        elif n_sem and len(all_orig) >= n_sem:
            set_vals = all_orig[:n_sem]
            sef_vals = all_orig[n_sem:] if len(all_orig) > n_sem else []

    if not set_vals and not sef_vals:
        return []

    records: list[ExtractedSemester] = []
    page_no = pdf.pages[0].page_number if pdf.pages else 1
    for idx, (ay, sem) in enumerate(sem_specs):
        set_r = set_vals[idx] if idx < len(set_vals) else None
        sef_r = sef_vals[idx] if idx < len(sef_vals) else None
        if set_r is None and sef_r is None:
            continue
        ambiguous = len(set_vals) != len(sem_specs) or len(sef_vals) != len(sem_specs)
        records.append(
            ExtractedSemester(
                academic_year=ay,
                semester=sem,
                faculty_name=faculty_name,
                set_rating=set_r,
                set_scale="0-100" if set_r is not None else None,
                sef_rating=sef_r,
                sef_scale="0-100" if sef_r is not None else None,
                set_pages=[page_no] if set_r is not None else [],
                sef_pages=[page_no] if sef_r is not None else [],
                set_excerpt=f"Students column {idx + 1}: {set_r}" if set_r is not None else "",
                sef_excerpt=f"Supervisor column {idx + 1}: {sef_r}" if sef_r is not None else "",
                raw_fragment="\n".join(lines[max(0, students_i - 2) : min(len(lines), average_i + 2)])[:2000],
                ambiguous=ambiguous,
            )
        )
    return records


def _dedupe_extracted(records: list[ExtractedSemester]) -> list[ExtractedSemester]:
    deduped: list[ExtractedSemester] = []
    seen: set[str] = set()
    for rec in records:
        key = f"{rec.academic_year or '?'}|{rec.semester or '?'}"
        if key in seen:
            for d in deduped:
                if f"{d.academic_year or '?'}|{d.semester or '?'}" == key:
                    if rec.set_rating is not None and d.set_rating is None:
                        d.set_rating = rec.set_rating
                        d.set_scale = rec.set_scale or d.set_scale
                    if rec.sef_rating is not None and d.sef_rating is None:
                        d.sef_rating = rec.sef_rating
                        d.sef_scale = rec.sef_scale or d.sef_scale
                    if rec.faculty_name:
                        d.faculty_name = rec.faculty_name
            continue
        seen.add(key)
        deduped.append(rec)
    return deduped


def extract_set_sef_semesters(pdf: PdfExtractionResult) -> list[ExtractedSemester]:
    if pdf.error:
        return []
    table_records = _parse_summary_rating_table(pdf)
    if table_records:
        return _dedupe_extracted(table_records)
    columnar = _parse_ustp_columnar_rating_sheet(pdf, None)
    if columnar:
        return _dedupe_extracted(columnar)
    text = pdf.full_text
    blocks = [b.strip() for b in BLOCK_SPLIT.split(text) if b.strip()]
    records: list[ExtractedSemester] = []
    current: ExtractedSemester | None = None

    for block in blocks:
        page_nums = [int(x) for x in re.findall(r"--- Page (\d+) ---", block)]
        body = re.sub(r"--- Page \d+ ---", "", block).strip()
        if not body:
            continue

        ay_m = AY_RE.search(body)
        sem_m = SEMESTER_RE.search(body)
        if ay_m or sem_m:
            if current and (current.set_rating is not None or current.sef_rating is not None):
                records.append(current)
            current = ExtractedSemester()
            if ay_m:
                current.academic_year = f"{ay_m.group(1)}-{ay_m.group(2)}"
            if sem_m:
                current.semester = _norm_semester(sem_m.group(0))
            current.raw_fragment = body[:2000]

        if current is None:
            current = ExtractedSemester(raw_fragment=body[:2000])

        name_m = NAME_RE.search(body)
        if name_m:
            name = name_m.group(1).strip()
            if len(name) > 3 and not re.search(r"(?i)dean|chair|director|evaluator", name):
                if not current.faculty_name or len(name) > len(current.faculty_name):
                    current.faculty_name = name

        is_set = bool(SET_OVERALL_RE.search(body) or re.search(r"(?i)\bSET\b", body[:120]))
        is_sef = bool(SEF_OVERALL_RE.search(body) or re.search(r"(?i)\bSEF\b", body[:120]))
        if is_set and not is_sef:
            r, scale = _parse_rating_near(body)
            if r is not None:
                if current.set_rating is not None and current.set_rating != r:
                    current.ambiguous = True
                current.set_rating = r
                current.set_scale = scale
                current.set_excerpt = body[:500]
                current.set_pages.extend(page_nums or [])
        elif is_sef and not is_set:
            r, scale = _parse_rating_near(body)
            if r is not None:
                if current.sef_rating is not None and current.sef_rating != r:
                    current.ambiguous = True
                current.sef_rating = r
                current.sef_scale = scale
                current.sef_excerpt = body[:500]
                current.sef_pages.extend(page_nums or [])
        elif is_set and is_sef:
            ratings = list(RATING_RE.finditer(body))
            if len(ratings) >= 2:
                r1 = float(ratings[0].group(1))
                r2 = float(ratings[1].group(1))
                current.set_rating = r1
                current.sef_rating = r2
                current.set_excerpt = body[:400]
                current.sef_excerpt = body[400:800]
            elif len(ratings) == 1:
                current.ambiguous = True

    if current and (current.academic_year or current.semester or current.set_rating or current.sef_rating):
        records.append(current)

    return _dedupe_extracted(records)
