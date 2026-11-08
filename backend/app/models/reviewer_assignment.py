from datetime import datetime, timezone

from app.extensions import db


class ReviewerAssignment(db.Model):
    __tablename__ = "reviewer_assignments"
    __table_args__ = (
        db.UniqueConstraint("reviewer_user_id", "faculty_user_id", name="uq_reviewer_faculty"),
    )

    id = db.Column(db.Integer, primary_key=True)
    reviewer_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    faculty_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    reviewer = db.relationship(
        "User",
        foreign_keys=[reviewer_user_id],
        back_populates="reviewer_assignments",
    )
    faculty = db.relationship("User", foreign_keys=[faculty_user_id])
