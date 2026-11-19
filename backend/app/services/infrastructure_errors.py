"""Classify transient infrastructure failures vs content/processing errors."""

from __future__ import annotations

import errno
import logging
import re

_log = logging.getLogger(__name__)

FACULTY_PROCESSING_INTERRUPTED = (
    "Document processing was interrupted. Please retry."
)


def is_transient_infrastructure_error(exc: BaseException) -> bool:
    """Network/storage/socket glitches that should be retried, not treated as bad PDF content."""
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    if isinstance(exc, OSError):
        winerr = getattr(exc, "winerror", None)
        if winerr in (10035, 10054, 10053, 10060):  # WSAEWOULDBLOCK, reset, abort, timed out
            return True
        if exc.errno in (errno.EWOULDBLOCK, errno.ECONNRESET, errno.ETIMEDOUT, errno.ECONNABORTED):
            return True
    msg = str(exc).lower()
    if "10035" in msg or "non-blocking socket" in msg:
        return True
    if "connection" in msg and ("reset" in msg or "aborted" in msg or "timed out" in msg):
        return True
    if "read timed out" in msg or "connect timed out" in msg:
        return True
    return False


_TECHNICAL_RE = re.compile(
    r"(winerror|traceback|socket|ssl|httpx|httpcore|connection reset|non-blocking socket)",
    re.I,
)


def faculty_safe_processing_error(stored: str | None, *, technical_for_logs: str | None = None) -> str:
    """Message safe for faculty/reviewer UI."""
    if not stored or not stored.strip():
        return ""
    if is_transient_infrastructure_error(Exception(stored)) or _TECHNICAL_RE.search(stored):
        if technical_for_logs:
            _log.debug("Sanitized processing error for UI (technical: %s)", technical_for_logs[:200])
        return FACULTY_PROCESSING_INTERRUPTED
    return stored


def infrastructure_error_faculty_message() -> str:
    return FACULTY_PROCESSING_INTERRUPTED