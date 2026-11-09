"""Compare extracted faculty names to server-side profile name."""

from __future__ import annotations

import re


def _tokens(name: str) -> list[str]:
    t = re.sub(r"[^a-zA-Z\s]", " ", name.lower())
    return [w for w in t.split() if len(w) > 1]


def _match_score(profile: str, extracted: str) -> float:
    pt = _tokens(profile)
    et = _tokens(extracted)
    if not pt or not et:
        return 0.0
    if profile.lower().strip() == extracted.lower().strip():
        return 1.0
    if set(pt) == set(et):
        return 0.95
    inter = len(set(pt) & set(et))
    if inter >= min(len(pt), len(et)) and inter >= 2:
        return 0.85
    if inter == 1 and len(pt) == 1:
        return 0.4
    if inter >= 2:
        return 0.7
    return inter / max(len(pt), len(et), 1)


def classify_faculty_identity(profile_full_name: str, extracted_name: str | None) -> str:
    """
    Returns: match | needs_confirmation | mismatch | missing
    """
    if not extracted_name or not extracted_name.strip():
        return "missing"
    score = _match_score(profile_full_name, extracted_name)
    if score >= 0.85:
        return "match"
    if score >= 0.55:
        return "needs_confirmation"
    return "mismatch"
