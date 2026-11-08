import enum
from datetime import datetime, timezone

from app.extensions import db


class UserRole(str, enum.Enum):
    admin = "admin"
    reviewer = "reviewer"
    faculty = "faculty"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole, name="user_role"), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    employee_id = db.Column(db.String(64), nullable=True)
    department = db.Column(db.String(200), nullable=True)
    rank = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    credential_email_status = db.Column(db.String(32), nullable=True)
    credential_email_error = db.Column(db.String(500), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    documents = db.relationship(
        "Document",
        back_populates="owner",
        foreign_keys="Document.owner_user_id",
        lazy="dynamic",
    )
    reviewer_assignments = db.relationship(
        "ReviewerAssignment",
        foreign_keys="ReviewerAssignment.reviewer_user_id",
        back_populates="reviewer",
        lazy="dynamic",
    )

    def portal_id(self) -> str:
        return f"u-{self.id}"

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role.value,
            "name": self.full_name,
            "mustChangePassword": bool(self.must_change_password),
        }

    def credential_delivery_dict(self) -> dict:
        return {
            "status": self.credential_email_status or "unknown",
            "error": self.credential_email_error or "",
        }

    def to_faculty_dict(self, reviewer_id: str | None = None) -> dict:
        parts = (self.full_name or "").split(" ", 1)
        return {
            "id": self.portal_id(),
            "userId": self.id,
            "employeeId": self.employee_id or "",
            "firstName": parts[0] if parts else self.full_name,
            "lastName": parts[1] if len(parts) > 1 else "",
            "email": self.email,
            "rank": self.rank or "",
            "department": self.department or "",
            "status": "active" if self.is_active else "inactive",
            "reviewerId": reviewer_id,
            "phone": self.phone or "",
            "credentialEmail": self.credential_delivery_dict(),
        }

    def to_reviewer_dict(self, assigned_faculty_ids: list[str]) -> dict:
        parts = (self.full_name or "").split(" ", 1)
        return {
            "id": self.portal_id(),
            "userId": self.id,
            "employeeId": self.employee_id or "",
            "firstName": parts[0] if parts else self.full_name,
            "lastName": parts[1] if len(parts) > 1 else "",
            "email": self.email,
            "department": self.department or "",
            "status": "active" if self.is_active else "inactive",
            "phone": self.phone or "",
            "assignedFacultyIds": assigned_faculty_ids,
            "credentialEmail": self.credential_delivery_dict(),
        }
