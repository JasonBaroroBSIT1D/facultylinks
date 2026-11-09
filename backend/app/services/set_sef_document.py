"""Identify SET/SEF OCR documents (unified and legacy indicators/kinds)."""

from __future__ import annotations

from app.models import Document
from app.services.catalog import SET_SEF_OCR_INDICATOR_IDS
from app.services.set_sef_aggregation import SET_SEF_DOCUMENT_KINDS


def is_set_sef_document(doc: Document | None) -> bool:
    if doc is None:
        return False
    if doc.document_kind in SET_SEF_DOCUMENT_KINDS:
        return True
    if doc.indicator_id in SET_SEF_OCR_INDICATOR_IDS:
        return True
    return False
