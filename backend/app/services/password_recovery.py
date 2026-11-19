import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app, request

from app.extensions import db
from app.models import PasswordRecoveryChallenge, PasswordResetGrant, User, UserRole
from app.services.account_provisioning import invalidate_recovery_for_user
from app.services.auth_context import _hash_token, logout_user_all
from app.services.mail_service import MailConfigurationError, send_password_changed_notice, send_recovery_code
from app.services.password_policy import validate_new_password
from app.services.passwords import hash_password, verify_password
from app.services.phone_numbers import (
    normalize_ph_mobile_e164,
    unique_eligible_user_by_verified_phone,
    verified_mobile_e164_for_user,
)
from app.services.textbee_service import (
    TextBeeConfigurationError,
    TextBeeDeliveryError,
    send_recovery_sms_otp,
    textbee_configured,
)

_log = logging.getLogger(__name__)

RECOVERY_NEUTRAL = "If an eligible account exists, a verification code will be sent."
RECOVERY_CHANNELS = frozenset({"email", "sms"})

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


def _resolve_recovery_user(
    *,
    channel: str | None,
    email: str | None = None,
    phone: str | None = None,
) -> User | None:
    ch = (channel or "").strip().lower() or None
    if ch == "sms":
        return unique_eligible_user_by_verified_phone(phone)
    if ch == "email":
        return _eligible_user(email or "") if email else None
    if email:
        return _eligible_user(email)
    return unique_eligible_user_by_verified_phone(phone)


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


def _send_recovery_email(user: User, code: str) -> bool:
    try:
        send_recovery_code(
            full_name=user.full_name,
            email=user.email,
            code=code,
            ttl_minutes=CODE_TTL_MINUTES,
        )
        return True
    except MailConfigurationError:
        return False
    except Exception:
        return False


def _send_recovery_sms(user: User, code: str) -> bool:
    sms_to = verified_mobile_e164_for_user(user)
    if not sms_to or not textbee_configured():
        return False
    try:
        send_recovery_sms_otp(
            e164_recipient=sms_to,
            code=code,
            ttl_minutes=CODE_TTL_MINUTES,
            user_id=user.id,
        )
        return True
    except (TextBeeConfigurationError, TextBeeDeliveryError):
        _log.warning("Password recovery SMS unavailable for user_id=%s", user.id)
        return False
    except Exception:
        _log.warning("Password recovery SMS failed for user_id=%s", user.id)
        return False


def _deliver_recovery_code(user: User, code: str, channel: str | None = None) -> bool:
    """
    Send OTP on the requested channel. ``channel`` is None for legacy clients (SMS then email).
    Returns True when the selected path reports acceptance/send success.
    """
    ch = (channel or "").strip().lower() or None

    if ch == "email":
        return _send_recovery_email(user, code)

    if ch == "sms":
        return _send_recovery_sms(user, code)

    if _send_recovery_sms(user, code):
        return True
    if _send_recovery_email(user, code):
        return True
    return False


def _supersede_active_challenges(user: User) -> None:
    now = datetime.now(timezone.utc)
    (
        PasswordRecoveryChallenge.query.filter(
            PasswordRecoveryChallenge.user_id == user.id,
            PasswordRecoveryChallenge.consumed_at.is_(None),
            PasswordRecoveryChallenge.superseded_at.is_(None),
        ).update({PasswordRecoveryChallenge.superseded_at: now}, synchronize_session=False)
    )


def _issue_challenge_if_allowed(user: User, *, channel: str | None) -> None:
    ip = _client_ip()
    if not (_rate_limit_ok(user, ip) and _resend_allowed(user)):
        return
    _supersede_active_challenges(user)
    code = generate_six_digit_code()
    ch = (channel or "").strip().lower() or None
    explicit = ch in RECOVERY_CHANNELS
    delivered = _deliver_recovery_code(user, code, ch if explicit else None)
    if explicit and not delivered:
        return
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


def request_recovery_code(
    *,
    channel: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> dict:
    """Always returns a neutral message; delivers OTP when eligible."""
    ch = (channel or "").strip().lower() or None

    if ch == "sms":
        if not normalize_ph_mobile_e164(phone):
            return {"message": RECOVERY_NEUTRAL}
        from app.services.phone_numbers import eligible_users_by_verified_phone

        matches = eligible_users_by_verified_phone(phone)
        if len(matches) != 1:
            return {"message": RECOVERY_NEUTRAL}
        _issue_challenge_if_allowed(matches[0], channel="sms")
        return {"message": RECOVERY_NEUTRAL}

    if ch == "email":
        user = _eligible_user(email or "")
        if user:
            _issue_challenge_if_allowed(user, channel="email")
        return {"message": RECOVERY_NEUTRAL}

    user = _eligible_user(email or "")
    if user:
        _issue_challenge_if_allowed(user, channel=None)
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


def verify_recovery_code(
    code: str,
    *,
    channel: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> dict:
    user = _resolve_recovery_user(channel=channel, email=email, phone=phone)
    if not user:
        return {"ok": False, "error": "Invalid or expired verification code."}
    challenge = _active_challenge(user)
    if not challenge:
        return {"ok": False, "error": "Invalid or expired verification code."}
    attempts = challenge.verify_attempts or 0
    if attempts >= MAX_VERIFY_ATTEMPTS:
        return {"ok": False, "error": "Too many attempts. Request a new verification code."}
    normalized = (code or "").strip()
    if not normalized.isdigit() or len(normalized) != 6:
        challenge.verify_attempts = attempts + 1
        db.session.commit()
        return {"ok": False, "error": "Enter the 6-digit verification code."}
    if not hmac.compare_digest(challenge.code_hmac, hash_recovery_code(normalized)):
        challenge.verify_attempts = attempts + 1
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