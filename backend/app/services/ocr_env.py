"""Tesseract / Python OCR dependency checks (worker + API health)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

_DEFAULT_WIN_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def resolve_tesseract_cmd() -> str | None:
    """Return path to tesseract executable if available."""
    raw = (os.environ.get("TESSERACT_CMD") or "").strip()
    if raw:
        p = Path(raw)
        if p.is_file():
            return str(p)
    which = shutil.which("tesseract") or shutil.which("tesseract.exe")
    if which:
        return which
    if _DEFAULT_WIN_TESSERACT.is_file():
        return str(_DEFAULT_WIN_TESSERACT)
    return None


def configure_pytesseract() -> str | None:
    """Point pytesseract at [resolve_tesseract_cmd]. Returns command path or None."""
    cmd = resolve_tesseract_cmd()
    if not cmd:
        return None
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = cmd
    except ImportError:
        return None
    return cmd


def tesseract_version() -> str | None:
    cmd = resolve_tesseract_cmd()
    if not cmd:
        return None
    try:
        out = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if out.returncode == 0 and out.stdout:
            return out.stdout.split("\n", 1)[0].strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        import pytesseract

        configure_pytesseract()
        return str(pytesseract.get_tesseract_version())
    except Exception:
        return None


def python_ocr_deps() -> dict[str, str]:
    status: dict[str, str] = {}
    for name, mod in (("pymupdf", "fitz"), ("pytesseract", "pytesseract"), ("Pillow", "PIL")):
        try:
            __import__(mod)
            status[name] = "installed"
        except ImportError:
            status[name] = "missing"
    return status


def ocr_environment_status() -> dict:
    cmd = resolve_tesseract_cmd()
    langs: list[str] = []
    if cmd:
        try:
            out = subprocess.run(
                [cmd, "--list-langs"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if out.returncode == 0:
                langs = [ln.strip() for ln in out.stdout.splitlines()[1:] if ln.strip()]
        except (OSError, subprocess.TimeoutExpired):
            pass
    deps = python_ocr_deps()
    ready = cmd is not None and all(v == "installed" for v in deps.values()) and "eng" in langs
    return {
        "ready": ready,
        "tesseractCmd": cmd,
        "tesseractVersion": tesseract_version(),
        "languages": langs,
        "pythonDependencies": deps,
    }
