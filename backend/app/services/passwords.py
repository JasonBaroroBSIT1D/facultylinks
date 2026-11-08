import secrets
import string

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher()

_ALPHABET = string.ascii_letters + string.digits


def generate_provision_password() -> str:
    """One-time provisioning password (never returned in API responses)."""
    core = "".join(secrets.choice(_ALPHABET) for _ in range(14))
    return f"Fl{core}1!"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False
