import re


def validate_new_password(password: str, confirm: str) -> str | None:
    if not password:
        return "New password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        return "Use at least one letter and one number."
    if password != confirm:
        return "Passwords do not match."
    return None
