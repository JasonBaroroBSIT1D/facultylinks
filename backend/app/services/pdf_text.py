"""Extract text from PDFs: embedded text layer + optional Tesseract OCR per page."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import BinaryIO

from app.services.ocr_env import configure_pytesseract, resolve_tesseract_cmd

_log = logging.getLogger(__name__)

MIN_CHARS_FOR_TEXT_PAGE = 40

TESSERACT_RETRY_HINT = (
    "Scanned pages require Tesseract OCR. On Windows, install Tesseract OCR and set "
    "TESSERACT_CMD in backend/.env (for example C:\\Program Files\\Tesseract-OCR\\tesseract.exe), "
    "then retry processing."
)


@dataclass
class PageText:
    page_number: int  # 1-based
    text: str
    source: str  # "pdf_text" | "tesseract" | "tesseract+pdf"
    mean_confidence: float | None = None


@dataclass
class PdfExtractionResult:
    pages: list[PageText] = field(default_factory=list)
    full_text: str = ""
    error: str | None = None
    ocr_required: bool = False

    def text_by_page(self) -> dict[int, str]:
        return {p.page_number: p.text for p in self.pages}


def _tesseract_available() -> bool:
    return resolve_tesseract_cmd() is not None


def _embedded_text_usable(text: str) -> bool:
    stripped = (text or "").strip()
    if len(stripped) < MIN_CHARS_FOR_TEXT_PAGE:
        return False
    letters = sum(1 for c in stripped if c.isalpha())
    if letters < 15:
        return False
    if stripped.count("\ufffd") > 2:
        return False
    return True


def _ocr_page_image(page, pytesseract, Image) -> tuple[str, float | None]:
    import fitz

    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    ocr_text = (pytesseract.image_to_string(img, lang="eng") or "").strip()
    confidences = [int(c) for c in ocr_data.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) >= 0]
    mean_conf = (sum(confidences) / len(confidences)) if confidences else None
    return ocr_text, mean_conf


def extract_pdf_text(stream: BinaryIO) -> PdfExtractionResult:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        return PdfExtractionResult(error=f"PyMuPDF not installed: {exc}")

    try:
        data = stream.read()
        doc = fitz.open(stream=io.BytesIO(data), filetype="pdf")
    except Exception as exc:
        return PdfExtractionResult(error=f"Could not open PDF: {exc}")

    pages: list[PageText] = []
    use_ocr = _tesseract_available()
    ocr_required_pages: list[int] = []
    pytesseract = None
    Image = None
    try:
        import pytesseract as pt
        from PIL import Image as PILImage

        pytesseract = pt
        Image = PILImage
    except ImportError:
        use_ocr = False

    if use_ocr:
        configure_pytesseract()

    for i in range(doc.page_count):
        page_no = i + 1
        page = doc.load_page(i)
        embedded = (page.get_text("text") or "").strip()
        chosen = embedded
        source = "pdf_text"
        mean_conf = None

        embedded_ok = _embedded_text_usable(embedded)
        if use_ocr and pytesseract and Image:
            try:
                if not embedded_ok or len(embedded) < MIN_CHARS_FOR_TEXT_PAGE:
                    ocr_text, mean_conf = _ocr_page_image(page, pytesseract, Image)
                    if _embedded_text_usable(ocr_text) and (
                        not embedded_ok or len(ocr_text) > len(embedded) * 1.05
                    ):
                        chosen = ocr_text
                        source = "tesseract" if not embedded_ok else "tesseract+pdf"
                    elif not embedded_ok and not _embedded_text_usable(ocr_text):
                        ocr_required_pages.append(page_no)
                        chosen = ocr_text or embedded
                elif not embedded_ok:
                    ocr_required_pages.append(page_no)
            except Exception as exc:
                _log.warning("OCR failed page %s: %s", page_no, exc)
                if not embedded_ok:
                    ocr_required_pages.append(page_no)
        elif not embedded_ok:
            ocr_required_pages.append(page_no)

        pages.append(
            PageText(
                page_number=page_no,
                text=chosen,
                source=source,
                mean_confidence=mean_conf,
            )
        )

    readable = [p for p in pages if p.text.strip() and _embedded_text_usable(p.text)]
    if not readable:
        if ocr_required_pages and not use_ocr:
            return PdfExtractionResult(
                pages=pages,
                full_text="",
                error=f"{TESSERACT_RETRY_HINT} (pages: {', '.join(map(str, ocr_required_pages))})",
                ocr_required=True,
            )
        return PdfExtractionResult(
            pages=pages,
            full_text="",
            error="No readable text could be extracted from this PDF.",
            ocr_required=bool(ocr_required_pages),
        )

    if ocr_required_pages and not use_ocr:
        _log.warning("Some pages lack readable text and OCR is unavailable: %s", ocr_required_pages)

    full = "\n\n".join(f"--- Page {p.page_number} ---\n{p.text}" for p in pages if p.text.strip())
    return PdfExtractionResult(
        pages=pages,
        full_text=full,
        ocr_required=bool(ocr_required_pages),
    )
