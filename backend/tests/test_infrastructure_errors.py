import errno

import pytest

from app.services.infrastructure_errors import (
    FACULTY_PROCESSING_INTERRUPTED,
    faculty_safe_processing_error,
    is_transient_infrastructure_error,
)


def test_winerror_10035_is_transient():
    exc = OSError(errno.EWOULDBLOCK, "[WinError 10035] A non-blocking socket operation could not be completed immediately")
    assert is_transient_infrastructure_error(exc) is True


def test_faculty_safe_replaces_technical():
    raw = "[WinError 10035] A non-blocking socket operation could not be completed immediately"
    assert faculty_safe_processing_error(raw) == FACULTY_PROCESSING_INTERRUPTED


def test_faculty_safe_keeps_content_message():
    msg = "No ratings parsed from document content."
    assert faculty_safe_processing_error(msg) == msg