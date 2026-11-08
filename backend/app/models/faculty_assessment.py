from datetime import datetime, timezone

from app.extensions import db


class FacultyAssessment(db.Model):
    __tablename__ = "faculty_assessments"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    data = db.Column(db.JSON, nullable=False, default=lambda: {"setSef": {"SET": [], "SEF": []}, "entries": {}})
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
