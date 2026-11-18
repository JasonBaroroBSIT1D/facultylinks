"""Unified text extraction for PDFs and supported images (general OCR pipeline)."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import BinaryIO

from app.services.ocr_env import configure_pytesseract, resolve_tesseract_cmd
from app.services.pdf_text import (
    MIN_CHARS_FOR_TEXT_PAGE,
    PdfExtractionResult,
    PageText,
    TESSERACT_RETRY_HINT,
    _embedded_text_usable,
    extract_pdf_text,
)

_log = logging.getLogger(__name__)

IMAGE_MIME = frozenset({"image/jpeg", "image/png", "image/webp", "image/jpg"})


@dataclass
class DocumentTextResult:
    pages: list[PageText] = field(default_factory=list)
    full_text: str = ""
    error: str | None = None
    ocr_required: bool = False
    extraction_method: str = "none"

    def pages_payload(self) -> list[dict]:
        return [
            {
                "page": p.page_number,
                "text": p.text,
                "source": p.source,
                "meanConfidence": p.mean_confidence,
            }
            for p in self.pages
        ]


def _from_pdf(result: PdfExtractionResult) -> DocumentTextResult:
    methods = {p.source for p in result.pages if p.text.strip()}
    if "tesseract" in methods or "tesseract+pdf" in methods:
        method = "tesseract+pdf" if "pdf_text" in methods else "tesseract"
    elif "pdf_text" in methods:
        method = "pdf_text"
    else:
        method = "none"
    return DocumentTextResult(
        pages=result.pages,
        full_text=result.full_text,
        error=result.error,
        ocr_required=result.ocr_required,
        extraction_method=method,
    )


def extract_image_text(stream: BinaryIO) -> DocumentTextResult:
    if resolve_tesseract_cmd() is None:
        return DocumentTextResult(
            error=TESSERACT_RETRY_HINT,
            ocr_required=True,
            extraction_method="none",
        )
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        return DocumentTextResult(
            error=f"OCR Python dependencies missing: {exc}",
            ocr_required=True,
            extraction_method="none",
        )

    configure_pytesseract()
    try:
        data = stream.read()
        img = Image.open(io.BytesIO(data))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        text = (pytesseract.image_to_string(img, lang="eng") or "").strip()
        confidences = [
            int(c)
            for c in ocr_data.get("conf", [])
            if str(c).lstrip("-").isdigit() and int(c) >= 0
        ]
        mean_conf = (sum(confidences) / len(confidences)) if confidences else None
    except Exception as exc:
        return DocumentTextResult(
            error=f"Image OCR failed: {exc}",
            ocr_required=True,
            extraction_method="tesseract",
        )

    if not text or not _embedded_text_usable(text):
        return DocumentTextResult(
            pages=[PageText(page_number=1, text=text, source="tesseract", mean_confidence=mean_conf)],
            full_text=text,
            error="No readable text could be extracted from this image.",
            ocr_required=True,
            extraction_method="tesseract",
        )

    page = PageText(page_number=1, text=text, source="tesseract", mean_confidence=mean_conf)
    return DocumentTextResult(
        pages=[page],
        full_text=f"--- Page 1 ---\n{text}",
        extraction_method="tesseract",
        ocr_required=False,
    )


def extract_document_text(stream: BinaryIO, mime_type: str) -> DocumentTextResult:
    mime = (mime_type or "").split(";")[0].strip().lower()
    if mime == "application/pdf":
        return _from_pdf(extract_pdf_text(stream))
    if mime in IMAGE_MIME or mime == "image/jpg":
        return extract_image_text(stream)
    return DocumentTextResult(
        error=f"Unsupported MIME type for text extraction: {mime}",
        extraction_method="none",
    )


def supports_general_ocr(mime_type: str | None) -> bool:
    mime = (mime_type or "").split(";")[0].strip().lower()
    return mime == "application/pdf" or mime in IMAGE_MIME
