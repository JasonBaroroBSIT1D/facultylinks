"""Rule-based parsing of SET/SEF combined PDF text into semester records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.pdf_text import PdfExtractionResult

SEMESTER_RE = re.compile(
    r"(?i)(?:1st|first)\s*sem(?:ester)?|(?:2nd|second)\s*sem(?:ester)?|summer"
)
AY_RE = re.compile(r"(?:(?:AY|Academic\s*Year)\s*[:\-]?\s*)?((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2})")
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
    r"(?i)summary\s+of\s+individual\s+faculty\s+rating|students\s*\n\s*rating"
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
    r"(?i)students?\s+rating|supervisor\s+rating"
)


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
    if "1st" in t or "first" in t:
        return "1st Sem"
    if "2nd" in t or "second" in t:
        return "2nd Sem"
    if "summer" in t:
        return "Summer"
    return None


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
    return records


def extract_set_sef_semesters(pdf: PdfExtractionResult) -> list[ExtractedSemester]:
    if pdf.error:
        return []
    table_records = _parse_summary_rating_table(pdf)
    if table_records:
        return table_records
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

    deduped: list[ExtractedSemester] = []
    seen: set[str] = set()
    for rec in records:
        key = f"{rec.academic_year or '?'}|{rec.semester or '?'}"
        if key in seen:
            for d in deduped:
                if f"{d.academic_year}|{d.semester}" == key:
                    if rec.set_rating and not d.set_rating:
                        d.set_rating = rec.set_rating
                    if rec.sef_rating and not d.sef_rating:
                        d.sef_rating = rec.sef_rating
                    if rec.faculty_name:
                        d.faculty_name = rec.faculty_name
            continue
        seen.add(key)
        deduped.append(rec)
    return deduped
