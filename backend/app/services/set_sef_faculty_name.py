"""Faculty name extraction for SET/SEF PDFs (text layer + targeted header OCR)."""

from __future__ import annotations

import io
import logging
import re

from app.services.pdf_text import configure_pytesseract, resolve_tesseract_cmd
from app.services.set_sef_extractor import FACULTY_COLON_RE, NAME_RE

_log = logging.getLogger(__name__)

# OCR-tolerant Faculty: label (extra spaces, minor noise).
FACULTY_LABEL_RE = re.compile(
    r"(?i)\bfaculty\s*:?\s*([A-Za-z][A-Za-z\s.'\-,]+?)(?:\s{2,}|\n|$|Department|Position|Designation|Sem\.|SEM\.)"
)


def _clean_name(raw: str) -> str | None:
    name = re.sub(r"\s+", " ", (raw or "").strip())
    name = re.sub(r"(?i)\s*department\b.*$", "", name).strip()
    if len(name) < 3:
        return None
    if re.search(r"(?i)sample\s+data|for\s+system\s+testing", name):
        return None
    return name[:200]


def extract_faculty_name_from_text(text: str | None) -> str | None:
    if not text:
        return None
    for pattern in (FACULTY_COLON_RE, FACULTY_LABEL_RE, NAME_RE):
        m = pattern.search(text)
        if m:
            cleaned = _clean_name(m.group(1))
            if cleaned:
                return cleaned
    return None


def extract_faculty_name_header_ocr(pdf_bytes: bytes, *, header_fraction: float = 0.55) -> str | None:
    """OCR the upper portion of page 1 when the text layer omitted the faculty header."""
    if resolve_tesseract_cmd() is None:
        return None
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        _log.warning("Header OCR unavailable: %s", exc)
        return None

    configure_pytesseract()
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count < 1:
            doc.close()
            return None
        page = doc.load_page(0)
        rect = page.rect
        clip = fitz.Rect(
            rect.x0,
            rect.y0,
            rect.x1,
            rect.y0 + max(rect.height * header_fraction, 200),
        )
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), clip=clip, alpha=False)
        doc.close()
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        text = (pytesseract.image_to_string(img, lang="eng") or "").strip()
    except Exception as exc:
        _log.warning("Header OCR failed: %s", exc)
        return None

    return extract_faculty_name_from_text(text)


def resolve_faculty_name_for_set_sef(
    *,
    pdf_bytes: bytes,
    full_text: str | None,
    parsed_name: str | None,
) -> tuple[str | None, str]:
    """
    Returns (name, source) where source is text_layer | header_ocr | none.
    Never uses filename or profile name.
    """
    if parsed_name and str(parsed_name).strip():
        return _clean_name(parsed_name), "text_layer"
    from_text = extract_faculty_name_from_text(full_text)
    if from_text:
        return from_text, "text_layer"
    header = extract_faculty_name_header_ocr(pdf_bytes)
    if header:
        return header, "header_ocr"
    return None, "none"