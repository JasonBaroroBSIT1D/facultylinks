"""Philippine mobile normalization and verified-SMS eligibility for accounts."""

import re

from app.models import User, UserRole


def normalize_ph_mobile_e164(value: str | None) -> str | None:
    """Return +639XXXXXXXXX for valid PH mobiles, else None."""
    if not value:
        return None
    compact = re.sub(r"[\s\-()]", "", str(value).strip())
    if re.fullmatch(r"09\d{9}", compact):
        return f"+63{compact[1:]}"
    if re.fullmatch(r"\+639\d{9}", compact):
        return compact
    return None


def verified_mobile_e164_for_user(user: User | None) -> str | None:
    """
    SMS destination from the account record only (never from a reset request).

    Requires phone_verified_at on the user row. Accounts with phone but no verification
    timestamp use email OTP instead.
    """
    if not user or not getattr(user, "phone_verified_at", None):
        return None
    raw = user.phone or ""
    if not raw.strip():
        return None
    return normalize_ph_mobile_e164(raw)


def _eligible_phone_candidates() -> list[User]:
    return (
        User.query.filter(
            User.is_active.is_(True),
            User.phone_verified_at.isnot(None),
            User.phone.isnot(None),
            User.role.in_((UserRole.admin, UserRole.reviewer, UserRole.faculty)),
        ).all()
    )


def eligible_users_by_verified_phone(phone: str | None) -> list[User]:
    """Users whose verified on-file mobile matches the normalized input."""
    target = normalize_ph_mobile_e164(phone)
    if not target:
        return []
    return [u for u in _eligible_phone_candidates() if normalize_ph_mobile_e164(u.phone) == target]


def unique_eligible_user_by_verified_phone(phone: str | None) -> User | None:
    """Single match only; None when zero or multiple accounts share the number."""
    matches = eligible_users_by_verified_phone(phone)
    if len(matches) == 1:
        return matches[0]
    return None