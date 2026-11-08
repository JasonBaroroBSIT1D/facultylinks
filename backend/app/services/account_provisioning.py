from datetime import datetime, timezone

from app.extensions import db
from app.models import PasswordRecoveryChallenge, PasswordResetGrant, User, UserRole
from app.services.auth_context import logout_user_all
from app.services.mail_service import MailConfigurationError, send_new_account_credentials, _sanitized_error
from app.services.passwords import generate_provision_password, hash_password


def _set_credential_status(user: User, status: str, error: str | None = None) -> None:
    user.credential_email_status = status
    user.credential_email_error = (error or "")[:500] or None


def deliver_new_account_credentials(user: User, temporary_password: str) -> dict:
    """Send credential email; update delivery fields. Never logs the password."""
    try:
        send_new_account_credentials(
            role=user.role,
            full_name=user.full_name,
            email=user.email,
            temporary_password=temporary_password,
        )
        _set_credential_status(user, "sent", None)
        return {"ok": True, "status": "sent", "message": "Credential email was accepted by the mail server."}
    except MailConfigurationError as exc:
        _set_credential_status(user, "failed", str(exc))
        return {"ok": False, "status": "failed", "message": str(exc)}
    except Exception as exc:
        err = _sanitized_error(exc)
        _set_credential_status(user, "failed", err)
        return {
            "ok": False,
            "status": "failed",
            "message": "Credential email could not be sent. Check SMTP configuration and try Resend Credentials.",
        }


def provision_temporary_password(user: User) -> str:
    """Generate, hash, and flag must-change. Caller must commit after optional email."""
    temp = generate_provision_password()
    user.password_hash = hash_password(temp)
    user.must_change_password = True
    _set_credential_status(user, "pending", None)
    invalidate_recovery_for_user(user)
    return temp


def invalidate_recovery_for_user(user: User) -> None:
    now = datetime.now(timezone.utc)
    (
        PasswordRecoveryChallenge.query.filter(
            PasswordRecoveryChallenge.user_id == user.id,
            PasswordRecoveryChallenge.consumed_at.is_(None),
            PasswordRecoveryChallenge.superseded_at.is_(None),
        ).update({PasswordRecoveryChallenge.superseded_at: now}, synchronize_session=False)
    )
    (
        PasswordResetGrant.query.filter(
            PasswordResetGrant.user_id == user.id,
            PasswordResetGrant.consumed_at.is_(None),
        ).update({PasswordResetGrant.consumed_at: now}, synchronize_session=False)
    )


def resend_credentials(user: User) -> tuple[str, dict]:
    if user.role not in (UserRole.faculty, UserRole.reviewer):
        raise ValueError("Only faculty and reviewer accounts receive credential emails.")
    temp = provision_temporary_password(user)
    logout_user_all(user)
    delivery = deliver_new_account_credentials(user, temp)
    db.session.commit()
    return temp, delivery
