import json
from datetime import datetime, timezone
import pytest

from app.models import User, UserRole
from app.services.password_recovery import (
    RECOVERY_NEUTRAL,
    _deliver_recovery_code,
    request_recovery_code,
    verify_recovery_code,
)
from app.services.phone_numbers import normalize_ph_mobile_e164, verified_mobile_e164_for_user
from app.services.textbee_service import send_recovery_sms_otp


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("09171234567", "+639171234567"),
        ("+639171234567", "+639171234567"),
        (" 0917 123 4567 ", "+639171234567"),
        ("08171234567", None),
        ("", None),
    ],
)
def test_normalize_ph_mobile_e164(raw, expected):
    assert normalize_ph_mobile_e164(raw) == expected


def test_verified_mobile_requires_timestamp():
    user = User(
        email="a@test.edu",
        password_hash="x",
        role=UserRole.faculty,
        full_name="Test",
        phone="09171234567",
    )
    assert verified_mobile_e164_for_user(user) is None
    user.phone_verified_at = datetime.now(timezone.utc)
    assert verified_mobile_e164_for_user(user) == "+639171234567"


def test_send_recovery_sms_otp_posts_textbee(app, app_ctx, monkeypatch):
    app.config["TEXTBEE_API_KEY"] = "test-key-secret"
    captured = {}

    class FakeResp:
        status = 200

        def read(self):
            return b'{"ok":true}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr("app.services.textbee_service.urllib.request.urlopen", fake_urlopen)

    send_recovery_sms_otp(
        e164_recipient="+639171234567",
        code="123456",
        ttl_minutes=10,
        user_id=42,
    )

    assert captured["url"] == "https://api.textbee.dev/api/v1/gateway/send-sms"
    assert captured["headers"].get("X-api-key") or captured["headers"].get("X-Api-Key")
    key_header = captured["headers"].get("X-api-key") or captured["headers"].get("X-Api-Key")
    assert key_header == "test-key-secret"
    assert captured["body"]["recipients"] == ["+639171234567"]
    assert "123456" in captured["body"]["message"]
    assert "test-key-secret" not in captured["body"]["message"]
    assert captured["timeout"] == 15


def test_deliver_uses_sms_when_verified(app, app_ctx, monkeypatch):
    app.config["TEXTBEE_API_KEY"] = "key"
    user = User(
        id=1,
        email="faculty@test.edu",
        password_hash="x",
        role=UserRole.faculty,
        full_name="Faculty User",
        phone="09171234567",
        phone_verified_at=datetime.now(timezone.utc),
    )
    sms_calls = []
    email_calls = []

    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_sms_otp",
        lambda **kw: sms_calls.append(kw),
    )
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_code",
        lambda **kw: email_calls.append(kw),
    )

    assert _deliver_recovery_code(user, "654321", "sms") is True
    assert len(sms_calls) == 1
    assert sms_calls[0]["e164_recipient"] == "+639171234567"
    assert sms_calls[0]["code"] == "654321"
    assert email_calls == []


def test_deliver_email_when_phone_not_verified(app, app_ctx, monkeypatch):
    app.config["TEXTBEE_API_KEY"] = "key"
    user = User(
        id=2,
        email="noreply@test.edu",
        password_hash="x",
        role=UserRole.faculty,
        full_name="No Verify",
        phone="09171234567",
    )
    sms_calls = []
    email_calls = []

    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_sms_otp",
        lambda **kw: sms_calls.append(kw),
    )
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_code",
        lambda **kw: email_calls.append(kw),
    )

    assert _deliver_recovery_code(user, "111111", "email") is True
    assert sms_calls == []
    assert len(email_calls) == 1
    assert email_calls[0]["email"] == "noreply@test.edu"


def test_explicit_sms_does_not_fallback_to_email(app, app_ctx, monkeypatch):
    app.config["TEXTBEE_API_KEY"] = "key"
    user = User(
        id=3,
        email="user@test.edu",
        password_hash="x",
        role=UserRole.faculty,
        full_name="User",
        phone="09171234567",
        phone_verified_at=datetime.now(timezone.utc),
    )
    sms_calls = []
    email_calls = []

    def fail_sms(**kw):
        sms_calls.append(kw)
        raise Exception("provider down")

    monkeypatch.setattr("app.services.password_recovery.send_recovery_sms_otp", fail_sms)
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_code",
        lambda **kw: email_calls.append(kw),
    )

    assert _deliver_recovery_code(user, "222222", "sms") is False
    assert len(sms_calls) == 1
    assert email_calls == []


def test_request_explicit_sms_only_queues_sms(app, app_ctx, monkeypatch):
    sms_calls = []
    email_calls = []
    verified_user = User(
        id=11,
        email="sms-only@test.edu",
        password_hash="x",
        role=UserRole.faculty,
        full_name="Faculty",
        phone="09181234567",
        phone_verified_at=datetime.now(timezone.utc),
        is_active=True,
    )
    monkeypatch.setattr(
        "app.services.phone_numbers.eligible_users_by_verified_phone",
        lambda phone: [verified_user]
        if normalize_ph_mobile_e164(phone) == "+639181234567"
        else [],
    )
    monkeypatch.setattr("app.services.password_recovery._rate_limit_ok", lambda user, ip: True)
    monkeypatch.setattr("app.services.password_recovery._resend_allowed", lambda user: True)
    monkeypatch.setattr("app.services.password_recovery._supersede_active_challenges", lambda user: None)
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_sms_otp",
        lambda **kw: sms_calls.append(kw),
    )
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_code",
        lambda **kw: email_calls.append(kw),
    )

    added = []

    class FakeSession:
        def add(self, obj):
            added.append(obj)

        def commit(self):
            pass

    monkeypatch.setattr("app.services.password_recovery.db.session", FakeSession())
    app.config["TEXTBEE_API_KEY"] = "key"

    with app.test_request_context("/"):
        out = request_recovery_code(channel="sms", phone="09181234567")
    assert out["message"] == RECOVERY_NEUTRAL
    assert len(sms_calls) == 1
    assert sms_calls[0]["e164_recipient"] == "+639181234567"
    assert email_calls == []
    assert len(added) == 1


def test_request_explicit_email_only_smtp(app, app_ctx, monkeypatch):
    email_calls = []
    sms_calls = []
    user = User(
        id=12,
        email="email-only@test.edu",
        password_hash="x",
        role=UserRole.faculty,
        full_name="Faculty",
        phone="09181234567",
        phone_verified_at=datetime.now(timezone.utc),
        is_active=True,
    )
    monkeypatch.setattr(
        "app.services.password_recovery._eligible_user",
        lambda email: user if email == "email-only@test.edu" else None,
    )
    monkeypatch.setattr("app.services.password_recovery._rate_limit_ok", lambda user, ip: True)
    monkeypatch.setattr("app.services.password_recovery._resend_allowed", lambda user: True)
    monkeypatch.setattr("app.services.password_recovery._supersede_active_challenges", lambda user: None)
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_code",
        lambda **kw: email_calls.append(kw),
    )
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_sms_otp",
        lambda **kw: sms_calls.append(kw),
    )

    added = []

    class FakeSession:
        def add(self, obj):
            added.append(obj)

        def commit(self):
            pass

    monkeypatch.setattr("app.services.password_recovery.db.session", FakeSession())
    app.config["TEXTBEE_API_KEY"] = "key"

    with app.test_request_context("/"):
        out = request_recovery_code(channel="email", email="email-only@test.edu")
    assert out["message"] == RECOVERY_NEUTRAL
    assert len(email_calls) == 1
    assert sms_calls == []
    assert len(added) == 1


def test_request_sms_without_verified_phone_neutral_no_challenge(app, app_ctx, monkeypatch):
    monkeypatch.setattr("app.services.phone_numbers.eligible_users_by_verified_phone", lambda _phone: [])
    monkeypatch.setattr("app.services.password_recovery._rate_limit_ok", lambda user, ip: True)
    monkeypatch.setattr("app.services.password_recovery._resend_allowed", lambda user: True)
    monkeypatch.setattr("app.services.password_recovery._supersede_active_challenges", lambda user: None)
    sms_calls = []
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_sms_otp",
        lambda **kw: sms_calls.append(kw),
    )
    added = []

    class FakeSession:
        def add(self, obj):
            added.append(obj)

        def commit(self):
            pass

    monkeypatch.setattr("app.services.password_recovery.db.session", FakeSession())
    app.config["TEXTBEE_API_KEY"] = "key"

    with app.test_request_context("/"):
        out = request_recovery_code(channel="sms", phone="09181234567")
    assert out["message"] == RECOVERY_NEUTRAL
    assert sms_calls == []
    assert added == []


def test_request_sms_ambiguous_multiple_accounts(app, app_ctx, monkeypatch):
    u1 = User(id=21, email="a@test.edu", password_hash="x", role=UserRole.faculty, full_name="A", phone="09170000001", phone_verified_at=datetime.now(timezone.utc), is_active=True)
    u2 = User(id=22, email="b@test.edu", password_hash="x", role=UserRole.faculty, full_name="B", phone="09170000001", phone_verified_at=datetime.now(timezone.utc), is_active=True)
    monkeypatch.setattr(
        "app.services.phone_numbers.eligible_users_by_verified_phone",
        lambda _phone: [u1, u2],
    )
    sms_calls = []
    added = []
    monkeypatch.setattr("app.services.password_recovery.send_recovery_sms_otp", lambda **kw: sms_calls.append(kw))

    class FakeSession:
        def add(self, obj):
            added.append(obj)

        def commit(self):
            pass

    monkeypatch.setattr("app.services.password_recovery.db.session", FakeSession())
    with app.test_request_context("/"):
        out = request_recovery_code(channel="sms", phone="09170000001")
    assert out["message"] == RECOVERY_NEUTRAL
    assert sms_calls == []
    assert added == []


def test_recovery_request_neutral_response(app, app_ctx, monkeypatch):
    monkeypatch.setattr("app.services.password_recovery._eligible_user", lambda _email: None)
    monkeypatch.setattr(
        "app.services.password_recovery._deliver_recovery_code",
        lambda *a, **k: None,
    )
    with app.test_request_context("/"):
        out = request_recovery_code(channel="email", email="unknown@example.com")
    assert out["message"] == RECOVERY_NEUTRAL


def test_sms_request_and_verify_without_email(app, app_ctx, monkeypatch):
    fixed_code = "482910"
    verified_user = User(
        id=99,
        email="secure@test.edu",
        password_hash="x",
        role=UserRole.reviewer,
        full_name="Reviewer",
        phone="09998887766",
        phone_verified_at=datetime.now(timezone.utc),
        is_active=True,
    )
    monkeypatch.setattr("app.services.password_recovery.generate_six_digit_code", lambda: fixed_code)
    monkeypatch.setattr(
        "app.services.phone_numbers.eligible_users_by_verified_phone",
        lambda phone: [verified_user]
        if normalize_ph_mobile_e164(phone) == "+639998887766"
        else [],
    )
    monkeypatch.setattr("app.services.phone_numbers.unique_eligible_user_by_verified_phone", lambda phone: verified_user if normalize_ph_mobile_e164(phone) == "+639998887766" else None)
    monkeypatch.setattr("app.services.password_recovery._rate_limit_ok", lambda user, ip: True)
    monkeypatch.setattr("app.services.password_recovery._resend_allowed", lambda user: True)
    monkeypatch.setattr("app.services.password_recovery._supersede_active_challenges", lambda user: None)
    sms_calls = []
    email_calls = []
    monkeypatch.setattr(
        "app.services.password_recovery.send_recovery_sms_otp",
        lambda **kw: sms_calls.append(kw),
    )
    monkeypatch.setattr("app.services.password_recovery.send_recovery_code", lambda **kw: email_calls.append(kw))

    stored_challenge = {}

    class FakeSession:
        def add(self, obj):
            if hasattr(obj, "code_hmac"):
                stored_challenge["obj"] = obj
                stored_challenge["obj"].id = 7

        def commit(self):
            pass

        def get(self, *_a, **_k):
            return None

    monkeypatch.setattr("app.services.password_recovery.db.session", FakeSession())
    monkeypatch.setattr(
        "app.services.password_recovery._active_challenge",
        lambda user: stored_challenge.get("obj") if user.id == verified_user.id else None,
    )
    grants = []

    class FakeGrantSession(FakeSession):
        def add(self, obj):
            if hasattr(obj, "token_hash"):
                grants.append(obj)
            else:
                super().add(obj)

    monkeypatch.setattr("app.services.password_recovery.db.session", FakeGrantSession())
    app.config["TEXTBEE_API_KEY"] = "key"

    with app.test_request_context("/"):
        request_recovery_code(channel="sms", phone="09998887766")
    assert len(sms_calls) == 1
    assert sms_calls[0]["e164_recipient"] == "+639998887766"
    assert email_calls == []

    result = verify_recovery_code(fixed_code, channel="sms", phone="09998887766")
    assert result.get("ok") is True
    assert result.get("resetToken")
    assert len(grants) == 1

    client = app.test_client()
    resp = client.post(
        "/api/auth/password-recovery/request",
        json={"channel": "sms", "phone": "09170000000"},
    )
    assert resp.status_code == 200
    assert len(sms_calls) == 1