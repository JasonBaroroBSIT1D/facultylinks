"""Reviewer review window (Manila calendar days)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.evaluation_period import first_allowed_review_day, reviewer_review_window

MANILA = ZoneInfo("Asia/Manila")

PERIOD = {
    "start": "2026-01-15",
    "end": "2026-06-30",
    "reviewerAvailableFrom": "2026-02-01",
}


def _at(y, m, d, h=12, mi=0, sec=0):
    return datetime(y, m, d, h, mi, sec, tzinfo=MANILA)


def test_first_allowed_day_is_later_of_start_and_reviewer_start():
    assert first_allowed_review_day(PERIOD) == "2026-02-01"


def test_before_reviewer_start_is_upcoming():
    w = reviewer_review_window(PERIOD, now=_at(2026, 1, 20))
    assert not w["allowed"]
    assert w["state"] == "upcoming"
    assert "Review opens" in w["message"]


def test_first_allowed_day_open():
    w = reviewer_review_window(PERIOD, now=_at(2026, 2, 1, 8, 0))
    assert w["allowed"]
    assert w["state"] == "open"


def test_last_end_day_inclusive_until_manila_midnight_boundary():
    w = reviewer_review_window(PERIOD, now=_at(2026, 6, 30, 23, 59))
    assert w["allowed"]


def test_midnight_after_end_closes_window():
    w = reviewer_review_window(PERIOD, now=_at(2026, 7, 1, 0, 0, 1))
    assert not w["allowed"]
    assert w["state"] == "closed"
    assert w["message"] == "Review period has ended."


def test_when_reviewer_start_after_eval_start_only():
    period = {"start": "2026-03-01", "end": "2026-05-31", "reviewerAvailableFrom": "2026-04-01"}
    assert first_allowed_review_day(period) == "2026-04-01"
    w = reviewer_review_window(period, now=_at(2026, 3, 15))
    assert not w["allowed"] and w["state"] == "upcoming"