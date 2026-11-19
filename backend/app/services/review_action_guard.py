"""HTTP helpers for reviewer seasonal review restrictions."""

from __future__ import annotations

from flask import jsonify

from app.models import User
from app.services.evaluation_period import reviewer_must_block_review_actions


def block_reviewer_review_response(user: User, *, now=None):
    blocked = reviewer_must_block_review_actions(user, now=now)
    if not blocked:
        return None
    return jsonify(blocked), 403