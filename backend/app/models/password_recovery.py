from datetime import datetime, timezone

from app.extensions import db


class PasswordRecoveryChallenge(db.Model):
    __tablename__ = "password_recovery_challenges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = db.Column(db.String(32), nullable=False, default="forgot_password")
    code_hmac = db.Column(db.String(64), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    superseded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    request_ip = db.Column(db.String(64), nullable=True)
    verify_attempts = db.Column(db.Integer, nullable=False, default=0)

    user = db.relationship("User", backref=db.backref("recovery_challenges", lazy="dynamic"))


class PasswordResetGrant(db.Model):
    __tablename__ = "password_reset_grants"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_id = db.Column(
        db.Integer,
        db.ForeignKey("password_recovery_challenges.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", backref=db.backref("reset_grants", lazy="dynamic"))
    challenge = db.relationship("PasswordRecoveryChallenge")
