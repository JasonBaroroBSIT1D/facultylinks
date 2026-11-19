"""TextBee gateway — outbound SMS (password recovery OTP only)."""

import json
import logging
import urllib.error
import urllib.request

from flask import current_app

from app.services.mail_service import _sanitized_error

_log = logging.getLogger(__name__)

TEXTBEE_SEND_URL = "https://api.textbee.dev/api/v1/gateway/send-sms"
TEXTBEE_REQUEST_TIMEOUT_SECONDS = 15


class TextBeeConfigurationError(Exception):
    """TEXTBEE_API_KEY is not set."""


class TextBeeDeliveryError(Exception):
    """Provider rejected or failed the request."""


def textbee_configured() -> bool:
    return bool((current_app.config.get("TEXTBEE_API_KEY") or "").strip())


def _recovery_sms_body(*, code: str, ttl_minutes: int) -> str:
    return (
        f"FacultyLink password reset code: {code}. "
        f"Valid for {ttl_minutes} minutes. Do not share this code."
    )


def send_recovery_sms_otp(*, e164_recipient: str, code: str, ttl_minutes: int, user_id: int) -> None:
    """
    Queue an OTP SMS via TextBee. Success means the API accepted the message (queued), not delivered.
    """
    api_key = (current_app.config.get("TEXTBEE_API_KEY") or "").strip()
    if not api_key:
        raise TextBeeConfigurationError("TEXTBEE_API_KEY is not configured.")

    payload = json.dumps(
        {
            "recipients": [e164_recipient],
            "message": _recovery_sms_body(code=code, ttl_minutes=ttl_minutes),
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        TEXTBEE_SEND_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TEXTBEE_REQUEST_TIMEOUT_SECONDS) as resp:
            if resp.status >= 400:
                raise TextBeeDeliveryError(f"unexpected HTTP status {resp.status}")
            resp.read()
    except urllib.error.HTTPError as exc:
        _log.warning(
            "TextBee send failed (HTTP %s) for user_id=%s",
            exc.code,
            user_id,
        )
        raise TextBeeDeliveryError("TextBee request failed.") from exc
    except urllib.error.URLError as exc:
        _log.warning(
            "TextBee send failed (network) for user_id=%s: %s",
            user_id,
            _sanitized_error(exc),
        )
        raise TextBeeDeliveryError("TextBee request failed.") from exc
    except TimeoutError as exc:
        _log.warning("TextBee send timed out for user_id=%s", user_id)
        raise TextBeeDeliveryError("TextBee request timed out.") from exc

    _log.info("TextBee SMS accepted (queued) for user_id=%s", user_id)