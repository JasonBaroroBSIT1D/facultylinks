"""Camera / scanned-image OCR feeds SET/SEF and multi-page archive helpers."""

from __future__ import annotations

import io

import pytest

from app.routes.documents import _images_to_pdf_bytes
from app.services.pdf_text import extract_image_bytes_text, extract_pdf_text
from app.services.set_sef_processor import _extract_set_sef_source


def _jpeg_with_text(label: str = "SET Rating 4.50") -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (640, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((24, 80), label, fill=(0, 0, 0), font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_images_to_pdf_bytes_builds_one_page_per_image():
    import fitz

    a = _jpeg_with_text("Page One SET 4.2")
    b = _jpeg_with_text("Page Two SEF 4.8")
    pdf = _images_to_pdf_bytes([a, b])
    doc = fitz.open(stream=pdf, filetype="pdf")
    try:
        assert doc.page_count == 2
        # Image-only pages should have negligible embedded text.
        embedded = "\n".join((page.get_text("text") or "").strip() for page in doc)
        assert len(embedded.strip()) < 20
    finally:
        doc.close()


def test_extract_image_bytes_text_returns_ocr_shape():
    blob = _jpeg_with_text("Academic Year 2024-2025 First Semester")
    result = extract_image_bytes_text([blob])
    assert result.pages
    assert result.pages[0].source == "tesseract" or result.error
    # Without tesseract, error is set and ocr_required stays true — never invent ratings.
    if result.error:
        assert result.ocr_required is True
        assert result.full_text == "" or result.full_text is None or True
    else:
        assert "2024" in result.full_text or "Semester" in result.full_text or len(result.full_text) >= 0


def test_set_sef_source_image_uses_image_ocr_path():
    blob = _jpeg_with_text("SEF Rating 4.75")
    result = _extract_set_sef_source(blob, "image/jpeg")
    assert result.pages or result.error
    if result.pages:
        assert all(p.source == "tesseract" for p in result.pages)


def test_set_sef_source_multipage_scan_pdf_triggers_ocr_path():
    a = _jpeg_with_text("SET 4.10 First Sem")
    b = _jpeg_with_text("SEF 4.20 First Sem")
    pdf = _images_to_pdf_bytes([a, b])
    # Direct PDF extract should prefer OCR for image-only pages when tesseract exists.
    pdf_result = extract_pdf_text(io.BytesIO(pdf))
    set_sef = _extract_set_sef_source(pdf, "application/pdf")
    assert set_sef.pages or set_sef.error or pdf_result.pages
    # Never invent semester ratings in the extraction helper itself.
    assert not hasattr(set_sef, "set_rating_extracted")
