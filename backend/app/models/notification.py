from datetime import datetime, timezone

from app.extensions import db


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    event_type = db.Column(db.String(64), nullable=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    subject_faculty_user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    target_type = db.Column(db.String(32), nullable=True)
    target_document_public_id = db.Column(db.String(64), nullable=True)
    target_achievement_id = db.Column(db.String(64), nullable=True)
    kra_id = db.Column(db.String(32), nullable=True)
    criterion_id = db.Column(db.String(64), nullable=True)
    indicator_id = db.Column(db.String(64), nullable=True)
    dedupe_key = db.Column(db.String(200), nullable=True)

    __table_args__ = (db.UniqueConstraint("user_id", "dedupe_key", name="uq_notification_user_dedupe"),)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "title": self.title,
            "body": self.body,
            "read": self.read,
            "at": self.created_at.isoformat() if self.created_at else None,
        }