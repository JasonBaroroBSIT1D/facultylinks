from datetime import datetime, timezone

from app.extensions import db


class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)
    actor_email = db.Column(db.String(320), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": f"act-{self.id}",
            "at": self.created_at.isoformat() if self.created_at else None,
            "actor": self.actor_email,
            "text": self.text,
        }
