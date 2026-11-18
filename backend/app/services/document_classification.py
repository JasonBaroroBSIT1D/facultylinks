"""Keyword-based KRA suggestion (non-authoritative)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.document_validation_config import CLASSIFICATION_VERSION, KRA_KEYWORD_RULES


@dataclass
class ClassificationResult:
    suggested_kra_id: str | None
    outcome: str
    matched_rules: list[dict[str, Any]] = field(default_factory=list)
    supporting_excerpts: list[dict[str, Any]] = field(default_factory=list)
    ambiguity_notes: str = ""
    classification_version: str = CLASSIFICATION_VERSION


def _excerpt_for_keyword(text: str, keyword: str, *, window: int = 80) -> str | None:
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    m = pattern.search(text or "")
    if not m:
        return None
    start = max(0, m.start() - window)
    end = min(len(text), m.end() + window)
    return text[start:end].replace("\n", " ").strip()


def classify_document_kra(
    full_text: str,
    *,
    selected_kra_id: str | None,
    pages: list[dict] | None = None,
) -> ClassificationResult:
    """
    Suggest a KRA from documented keyword rules.

    Does not invent probability scores. Outcomes:
    clear | conflicting | absent | uncertain | mismatch_selected
    """
    text = full_text or ""
    lower = text.lower()
    hits: list[dict[str, Any]] = []
    excerpts: list[dict[str, Any]] = []

    for rule in sorted(KRA_KEYWORD_RULES, key=lambda r: int(r.get("priority") or 99)):
        matched_kw = [kw for kw in (rule.get("keywords") or []) if kw.lower() in lower]
        if not matched_kw:
            continue
        page_refs: list[int] = []
        for p in pages or []:
            ptext = (p.get("text") or "").lower()
            if any(kw.lower() in ptext for kw in matched_kw):
                page_refs.append(int(p.get("page") or 0))
        hit = {
            "ruleId": rule["rule_id"],
            "suggestedKra": rule["suggested_kra"],
            "matchedKeywords": matched_kw,
            "priority": rule.get("priority"),
            "source": rule.get("source"),
            "pages": [p for p in page_refs if p],
        }
        hits.append(hit)
        for kw in matched_kw[:2]:
            ex = _excerpt_for_keyword(text, kw)
            if ex:
                excerpts.append(
                    {
                        "ruleId": rule["rule_id"],
                        "keyword": kw,
                        "excerpt": ex,
                        "pages": hit["pages"],
                    }
                )

    if not hits:
        return ClassificationResult(
            suggested_kra_id=None,
            outcome="absent",
            ambiguity_notes="No configured KRA keyword rules matched the extracted text.",
        )

    kra_set = {h["suggestedKra"] for h in hits}
    if len(kra_set) > 1:
        # Prefer highest-priority (lowest number) only when unique top; else conflicting
        best_priority = min(int(h.get("priority") or 99) for h in hits)
        top = [h for h in hits if int(h.get("priority") or 99) == best_priority]
        top_kras = {h["suggestedKra"] for h in top}
        if len(top_kras) == 1 and len(kra_set) > 1:
            # Lower-priority secondary matches → still flag ambiguity but suggest top
            suggested = next(iter(top_kras))
            notes = (
                f"Primary suggestion {suggested} from priority-{best_priority} rule(s); "
                f"also matched other KRAs: {', '.join(sorted(kra_set - {suggested}))}."
            )
            outcome = "uncertain"
        else:
            suggested = None
            notes = f"Conflicting KRA keyword matches: {', '.join(sorted(kra_set))}."
            outcome = "conflicting"
        result = ClassificationResult(
            suggested_kra_id=suggested,
            outcome=outcome,
            matched_rules=hits,
            supporting_excerpts=excerpts,
            ambiguity_notes=notes,
        )
    else:
        suggested = next(iter(kra_set))
        result = ClassificationResult(
            suggested_kra_id=suggested,
            outcome="clear",
            matched_rules=hits,
            supporting_excerpts=excerpts,
        )

    selected = (selected_kra_id or "").strip()
    if (
        result.suggested_kra_id
        and selected
        and result.suggested_kra_id != selected
        and result.outcome in ("clear", "uncertain")
    ):
        result.outcome = "mismatch_selected"
        note = (
            f"Suggested {result.suggested_kra_id} differs from faculty-selected {selected}. "
            "Selected KRA was not changed."
        )
        result.ambiguity_notes = f"{result.ambiguity_notes} {note}".strip()

    return result
