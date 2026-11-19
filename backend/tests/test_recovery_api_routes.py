"""HTTP-level recovery route contracts (email vs SMS payloads)."""

from datetime import datetime, timezone
import pytest

from app.models import User, UserRole
from app.services.password_recovery import RECOVERY_NEUTRAL


@pytest.fixture
def verified_user():
    return User(
        id=501,
        email="route@test.edu",
        password_hash="x",
        role=UserRole.faculty,
        full_name="Route Test",
        phone="09175551234",
        phone_verified_at=datetime.now(timezone.utc),
        is_active=True,
    )


def test_recovery_request_email_route_payload(app, app_ctx, monkeypatch, verified_user):
    email_calls = []
    monkeypatch.setattr(
        "app.services.password_recovery._eligible_user",
        lambda em: verified_user if em == "route@test.edu" else None,
    )

    class FakeSession:
        def add(self, _):
            pass

        def commit(self):
            pass

    monkeypatch.setattr("app.services.password_recovery.db.session", FakeSession())
    monkeypatch.setattr("app.services.password_recovery._rate_limit_ok", lambda u, ip: True)
    monkeypatch.setattr("app.services.password_recovery._resend_allowed", lambda u: True)
    monkeypatch.setattr("app.services.password_recovery._supersede_active_challenges", lambda u: None)
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_code",
        lambda **kw: email_calls.append(kw),
    )
    monkeypatch.setattr("app.services.password_recovery.send_recovery_sms_otp", lambda **kw: pytest.fail("SMS must not run"))

    client = app.test_client()
    res = client.post(
        "/api/auth/password-recovery/request",
        json={"channel": "email", "email": "route@test.edu"},
    )
    assert res.status_code == 200
    assert res.get_json()["message"] == RECOVERY_NEUTRAL
    assert len(email_calls) == 1


def test_recovery_request_sms_route_without_email(app, app_ctx, monkeypatch, verified_user):
    sms_calls = []
    monkeypatch.setattr(
        "app.services.phone_numbers.eligible_users_by_verified_phone",
        lambda phone: [verified_user] if phone and "917" in phone.replace(" ", "") else [],
    )

    class FakeSession:
        def add(self, _):
            pass

        def commit(self):
            pass

    monkeypatch.setattr("app.services.password_recovery.db.session", FakeSession())
    monkeypatch.setattr("app.services.password_recovery._rate_limit_ok", lambda u, ip: True)
    monkeypatch.setattr("app.services.password_recovery._resend_allowed", lambda u: True)
    monkeypatch.setattr("app.services.password_recovery._supersede_active_challenges", lambda u: None)
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_sms_otp",
        lambda **kw: sms_calls.append(kw),
    )
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_code",
        lambda **kw: pytest.fail("email must not run for explicit sms"),
    )
    app.config["TEXTBEE_API_KEY"] = "test"

    client = app.test_client()
    res = client.post(
        "/api/auth/password-recovery/request",
        json={"channel": "sms", "phone": "09175551234"},
    )
    assert res.status_code == 200
    assert res.get_json()["message"] == RECOVERY_NEUTRAL
    assert len(sms_calls) == 1
    assert "email" not in (res.get_json() or {})


def test_recovery_verify_sms_accepts_phone_only(app, app_ctx, monkeypatch):
    from app.services.password_recovery import hash_recovery_code

    user = User(
        id=77,
        email="hidden@test.edu",
        password_hash="x",
        role=UserRole.reviewer,
        full_name="Hidden",
        phone="09990001111",
        phone_verified_at=datetime.now(timezone.utc),
        is_active=True,
    )

    challenge = type("Ch", (), {"id": 3, "verify_attempts": 0, "code_hmac": hash_recovery_code("555111")})()

    monkeypatch.setattr(
        "app.services.password_recovery._resolve_recovery_user",
        lambda **kw: user if kw.get("channel") == "sms" else None,
    )
    monkeypatch.setattr("app.services.password_recovery._active_challenge", lambda u: challenge if u.id == user.id else None)

    grants = []

    class FakeSession:
        def add(self, obj):
            if getattr(obj, "token_hash", None):
                grants.append(obj)

        def commit(self):
            pass

        def get(self, *_a, **_k):
            return None

    monkeypatch.setattr("app.services.password_recovery.db.session", FakeSession())

    client = app.test_client()
    res = client.post(
        "/api/auth/password-recovery/verify",
        json={"channel": "sms", "phone": "09990001111", "code": "555111"},
    )
    assert res.status_code == 200
    assert res.get_json().get("resetToken")
    assert len(grants) == 1