import hmac
import hashlib

from app.services.password_recovery import hash_recovery_code, generate_six_digit_code
from app.services.passwords import generate_provision_password
from app.services.password_policy import validate_new_password


def test_generate_provision_password_length():
    pw = generate_provision_password()
    assert len(pw) >= 14


def test_six_digit_code_format():
    code = generate_six_digit_code()
    assert len(code) == 6
    assert code.isdigit()


def test_password_policy():
    assert validate_new_password("short", "short") is not None
    assert validate_new_password("abcdefgh", "abcdefgh") is not None
    assert validate_new_password("abcd1234", "abcd1234") is None
    assert validate_new_password("abcd1234", "abcd1235") is not None


def test_recovery_code_hmac_stable(app_ctx):
    a = hash_recovery_code("042516")
    b = hash_recovery_code("042516")
    assert a == b
    assert a != hash_recovery_code("042517")
