from app.extensions import db
from app.models import ActivityLog


def log_activity(actor_email: str, text: str) -> None:
    db.session.add(ActivityLog(actor_email=actor_email, text=text))
    db.session.commit()
