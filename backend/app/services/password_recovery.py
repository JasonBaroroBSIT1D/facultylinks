import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app, request

from app.extensions import db
from app.models import PasswordRecoveryChallenge, PasswordResetGrant, User, UserRole
from app.services.account_provisioning import invalidate_recovery_for_user
from app.services.auth_context import _hash_token, logout_user_all
from app.services.mail_service import MailConfigurationError, send_password_changed_notice, send_recovery_code, _sanitized_error
from app.services.password_policy import validate_new_password
from app.services.passwords import hash_password, verify_password

RECOVERY_NEUTRAL = "If an eligible account exists, a verification code will be sent."

CODE_TTL_MINUTES = 10
GRANT_TTL_MINUTES = 15
RESEND_COOLDOWN_SECONDS = 60
MAX_REQUESTS_PER_EMAIL_PER_HOUR = 5
MAX_REQUESTS_PER_IP_PER_HOUR = 30
MAX_VERIFY_ATTEMPTS = 5


def _recovery_secret() -> bytes:
    raw = current_app.config.get("RECOVERY_HMAC_SECRET") or current_app.config.get("SECRET_KEY") or ""
    return raw.encode("utf-8")


def hash_recovery_code(code: str) -> str:
    normalized = code.strip()
    return hmac.new(_recovery_secret(), normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_six_digit_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or (request.remote_addr or "unknown")[:64]


def _hour_ago() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=1)


def _eligible_user(email: str) -> User | None:
    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user or not user.is_active:
        return None
    if user.role not in (UserRole.admin, UserRole.reviewer, UserRole.faculty):
        return None
    return user


def _rate_limit_ok(user: User, ip: str) -> bool:
    since = _hour_ago()
    email_count = (
        PasswordRecoveryChallenge.query.filter(
            PasswordRecoveryChallenge.user_id == user.id,
            PasswordRecoveryChallenge.created_at >= since,
        ).count()
    )
    if email_count >= MAX_REQUESTS_PER_EMAIL_PER_HOUR:
        return False
    ip_count = (
        PasswordRecoveryChallenge.query.filter(
            PasswordRecoveryChallenge.request_ip == ip,
            PasswordRecoveryChallenge.created_at >= since,
        ).count()
    )
    return ip_count < MAX_REQUESTS_PER_IP_PER_HOUR


def _resend_allowed(user: User) -> bool:
    latest = (
        PasswordRecoveryChallenge.query.filter_by(user_id=user.id)
        .order_by(PasswordRecoveryChallenge.created_at.desc())
        .first()
    )
    if not latest:
        return True
    delta = datetime.now(timezone.utc) - latest.created_at
    return delta.total_seconds() >= RESEND_COOLDOWN_SECONDS


def _supersede_active_challenges(user: User) -> None:
    now = datetime.now(timezone.utc)
    (
        PasswordRecoveryChallenge.query.filter(
            PasswordRecoveryChallenge.user_id == user.id,
            PasswordRecoveryChallenge.consumed_at.is_(None),
            PasswordRecoveryChallenge.superseded_at.is_(None),
        ).update({PasswordRecoveryChallenge.superseded_at: now}, synchronize_session=False)
    )


def request_recovery_code(email: str) -> dict:
    """Always returns neutral message; sends mail only when eligible."""
    em = email.strip().lower()
    ip = _client_ip()
    user = _eligible_user(em)
    if user and _rate_limit_ok(user, ip) and _resend_allowed(user):
        _supersede_active_challenges(user)
        code = generate_six_digit_code()
        now = datetime.now(timezone.utc)
        challenge = PasswordRecoveryChallenge(
            user_id=user.id,
            purpose="forgot_password",
            code_hmac=hash_recovery_code(code),
            created_at=now,
            expires_at=now + timedelta(minutes=CODE_TTL_MINUTES),
            request_ip=ip,
        )
        db.session.add(challenge)
        db.session.commit()
        try:
            send_recovery_code(
                full_name=user.full_name,
                email=user.email,
                code=code,
                ttl_minutes=CODE_TTL_MINUTES,
            )
        except MailConfigurationError:
            pass
        except Exception:
            pass
    return {"message": RECOVERY_NEUTRAL}


def _active_challenge(user: User) -> PasswordRecoveryChallenge | None:
    now = datetime.now(timezone.utc)
    return (
        PasswordRecoveryChallenge.query.filter(
            PasswordRecoveryChallenge.user_id == user.id,
            PasswordRecoveryChallenge.consumed_at.is_(None),
            PasswordRecoveryChallenge.superseded_at.is_(None),
            PasswordRecoveryChallenge.expires_at > now,
        )
        .order_by(PasswordRecoveryChallenge.created_at.desc())
        .first()
    )


def verify_recovery_code(email: str, code: str) -> dict:
    em = email.strip().lower()
    user = _eligible_user(em)
    if not user:
        return {"ok": False, "error": "Invalid or expired verification code."}
    challenge = _active_challenge(user)
    if not challenge:
        return {"ok": False, "error": "Invalid or expired verification code."}
    if challenge.verify_attempts >= MAX_VERIFY_ATTEMPTS:
        return {"ok": False, "error": "Too many attempts. Request a new verification code."}
    normalized = (code or "").strip()
    if not normalized.isdigit() or len(normalized) != 6:
        challenge.verify_attempts += 1
        db.session.commit()
        return {"ok": False, "error": "Enter the 6-digit verification code."}
    if not hmac.compare_digest(challenge.code_hmac, hash_recovery_code(normalized)):
        challenge.verify_attempts += 1
        db.session.commit()
        return {"ok": False, "error": "Invalid or expired verification code."}

    raw_grant = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    grant = PasswordResetGrant(
        user_id=user.id,
        challenge_id=challenge.id,
        token_hash=_hash_token(raw_grant),
        created_at=now,
        expires_at=now + timedelta(minutes=GRANT_TTL_MINUTES),
    )
    db.session.add(grant)
    db.session.commit()
    return {"ok": True, "resetToken": raw_grant}


def complete_password_reset(reset_token: str, password: str, confirm: str) -> dict:
    policy_err = validate_new_password(password, confirm)
    if policy_err:
        return {"ok": False, "error": policy_err}
    h = _hash_token((reset_token or "").strip())
    now = datetime.now(timezone.utc)
    grant = (
        PasswordResetGrant.query.filter(
            PasswordResetGrant.token_hash == h,
            PasswordResetGrant.consumed_at.is_(None),
            PasswordResetGrant.expires_at > now,
        )
        .first()
    )
    if not grant:
        return {"ok": False, "error": "Reset authorization is invalid or expired. Start again."}
    user = db.session.get(User, grant.user_id)
    if not user or not user.is_active:
        return {"ok": False, "error": "Reset authorization is invalid or expired. Start again."}
    if verify_password(user.password_hash, password):
        return {"ok": False, "error": "Choose a new password that is different from your current one."}

    user.password_hash = hash_password(password)
    user.must_change_password = False
    grant.consumed_at = now
    challenge = db.session.get(PasswordRecoveryChallenge, grant.challenge_id)
    if challenge:
        challenge.consumed_at = now
    invalidate_recovery_for_user(user)
    logout_user_all(user)
    db.session.commit()

    try:
        send_password_changed_notice(full_name=user.full_name, email=user.email)
    except Exception:
        pass

    return {"ok": True, "message": "Your password has been updated. Please sign in."}
