"""Institution evaluation schedule and reviewer review-action window (Asia/Manila calendar days)."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.models import User, UserRole
from app.services.settings_store import INSTITUTION_KEY, get_json

MANILA = ZoneInfo("Asia/Manila")


def _slice_date(value) -> str:
    if not value:
        return ""
    return str(value).strip()[:10]


def manila_calendar_date(when: datetime | None = None) -> str:
    dt = when or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MANILA).strftime("%Y-%m-%d")


def preparation_period(cfg: dict | None = None) -> dict:
    if cfg is None:
        institution = get_json(INSTITUTION_KEY) or {}
        cfg = institution.get("preparationPeriod") or {}
    return {
        "start": _slice_date(cfg.get("start")),
        "end": _slice_date(cfg.get("end")),
        "reviewerAvailableFrom": _slice_date(cfg.get("reviewerAvailableFrom")),
    }


def first_allowed_review_day(period: dict) -> str | None:
    start = period.get("start") or ""
    end = period.get("end") or ""
    if not start or not end:
        return None
    ra = period.get("reviewerAvailableFrom") or ""
    if ra:
        return max(start, ra)
    return start


def format_period_date_label_win(iso: str) -> str:
    if not iso or len(iso) < 10:
        return "—"
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d")
        return d.strftime(f"%B {d.day}, %Y")
    except ValueError:
        return iso


def reviewer_review_window(period: dict | None = None, *, now: datetime | None = None) -> dict:
    """Whether reviewers may submit review decisions (not admin)."""
    p = period or preparation_period()
    start = p.get("start") or ""
    end = p.get("end") or ""
    first = first_allowed_review_day(p)
    today = manila_calendar_date(now)

    if not start or not end or not first:
        return {
            "allowed": False,
            "state": "unconfigured",
            "code": "REVIEW_SCHEDULE_UNCONFIGURED",
            "message": "Evaluation schedule is not configured.",
            "opensOn": first,
            "endsOn": end or None,
            "todayManila": today,
        }

    if today < first:
        label = format_period_date_label_win(first)
        return {
            "allowed": False,
            "state": "upcoming",
            "code": "REVIEW_PERIOD_NOT_STARTED",
            "message": f"Review opens {label}.",
            "opensOn": first,
            "endsOn": end,
            "todayManila": today,
        }

    if today > end:
        return {
            "allowed": False,
            "state": "closed",
            "code": "REVIEW_PERIOD_ENDED",
            "message": "Review period has ended.",
            "opensOn": first,
            "endsOn": end,
            "todayManila": today,
        }

    return {
        "allowed": True,
        "state": "open",
        "code": None,
        "message": None,
        "opensOn": first,
        "endsOn": end,
        "todayManila": today,
    }


def reviewer_must_block_review_actions(user: User | None, *, now: datetime | None = None) -> dict | None:
    """Return error payload if reviewer cannot apply review mutations, else None."""
    if not user or user.role != UserRole.reviewer:
        return None
    window = reviewer_review_window(now=now)
    if window["allowed"]:
        return None
    return {
        "error": window["message"],
        "code": window["code"],
        "reviewWindow": window,
    }


def review_window_for_portal() -> dict:
    w = reviewer_review_window()
    return {
        "allowed": w["allowed"],
        "state": w["state"],
        "opensOn": w["opensOn"],
        "endsOn": w["endsOn"],
        "message": w["message"],
        "todayManila": w["todayManila"],
    }