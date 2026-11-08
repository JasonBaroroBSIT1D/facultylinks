from datetime import datetime, timezone
import uuid

from app.extensions import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(
        db.String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    owner_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    object_key = db.Column(db.String(512), unique=True, nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(127), nullable=False)
    size_bytes = db.Column(db.BigInteger, nullable=False)
    upload_status = db.Column(db.String(32), nullable=False, default="stored")
    indicator_id = db.Column(db.String(64), nullable=True)
    kra_id = db.Column(db.String(32), nullable=True)
    review_status = db.Column(db.String(32), nullable=False, default="pending")
    review_remarks = db.Column(db.Text, nullable=True)
    verified_points = db.Column(db.Numeric(10, 2), nullable=True)
    reviewed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    entry_id = db.Column(db.String(64), nullable=True)
    superseded_by_public_id = db.Column(db.String(36), nullable=True)
    estimated_points = db.Column(db.Numeric(10, 2), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    owner = db.relationship("User", back_populates="documents", foreign_keys=[owner_user_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_user_id])

    def to_dict(self) -> dict:
        return {
            "id": self.public_id,
            "filename": self.original_filename,
            "fileName": self.original_filename,
            "mimeType": self.mime_type,
            "sizeBytes": self.size_bytes,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "indicatorId": self.indicator_id or "",
            "kraId": self.kra_id or "",
            "reviewStatus": self.review_status,
            "remarks": self.review_remarks or "",
            "verifiedPoints": float(self.verified_points) if self.verified_points is not None else None,
            "ownerUserId": self.owner_user_id,
            "uploadStatus": self.upload_status,
            "ocrStatus": "pending",
            "ocrText": "",
        }

    def to_portal_dict(self, owner_public_id: str, reviewer_email: str | None = None) -> dict:
        return {
            "id": self.public_id,
            "facultyId": owner_public_id,
            "fileName": self.original_filename,
            "indicatorId": self.indicator_id or "",
            "kraId": self.kra_id or "",
            "reviewStatus": self.review_status,
            "remarks": self.review_remarks or "",
            "verifiedPoints": float(self.verified_points) if self.verified_points is not None else None,
            "ocrStatus": "pending",
            "ocrText": "",
            "uploadedAt": self.created_at.isoformat() if self.created_at else None,
            "history": [],
        }
