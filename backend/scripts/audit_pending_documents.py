"""One-off: list pending documents vs achievement links for reviewer dashboard debugging."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import Document, FacultyAssessment, ReviewerAssignment, User, UserRole
from app.services.achievement_rules import is_active_achievement, resolve_achievement_criterion_id
from app.services.catalog import is_kra_i_achievement_indicator


def main() -> None:
    app = create_app()
    with app.app_context():
        pending = (
            Document.query.filter_by(upload_status="stored", review_status="pending")
            .order_by(Document.owner_user_id, Document.created_at)
            .all()
        )
        print(f"Total pending stored documents: {len(pending)}")
        rows = []
        for d in pending:
            owner = User.query.get(d.owner_user_id)
            assign = ReviewerAssignment.query.filter_by(faculty_user_id=d.owner_user_id).first()
            rev = User.query.get(assign.reviewer_user_id) if assign else None
            assess = FacultyAssessment.query.get(d.owner_user_id)
            achievements = (assess.data or {}).get("achievements") or [] if assess else []
            linked = None
            for a in achievements:
                if not is_active_achievement(a):
                    continue
                if d.public_id in (a.get("documentIds") or []):
                    linked = a
                    break
            rows.append(
                {
                    "publicId": d.public_id,
                    "fileName": d.original_filename,
                    "owner": owner.email if owner else d.owner_user_id,
                    "reviewer": rev.email if rev else None,
                    "indicatorId": d.indicator_id,
                    "kraId": d.kra_id,
                    "bcEvidence": is_kra_i_achievement_indicator(d.indicator_id),
                    "linkedAchievementId": linked.get("id") if linked else None,
                    "achievementSubmission": linked.get("submissionStatus") if linked else None,
                    "achievementReview": linked.get("reviewStatus") if linked else None,
                    "criterionId": resolve_achievement_criterion_id(linked) if linked else None,
                }
            )
        print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
