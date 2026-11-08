import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app

from app.models import UserRole
from app.services import mail_templates

_log = logging.getLogger(__name__)


class MailConfigurationError(Exception):
    """SMTP is not configured."""


def smtp_configured() -> bool:
    cfg = current_app.config
    return bool(
        cfg.get("SMTP_HOST")
        and cfg.get("SMTP_PORT")
        and cfg.get("SMTP_USERNAME")
        and cfg.get("SMTP_PASSWORD")
        and cfg.get("MAIL_FROM")
    )


def _sanitized_error(exc: Exception) -> str:
    msg = str(exc).strip() or exc.__class__.__name__
    if len(msg) > 400:
        msg = msg[:397] + "..."
    return msg


def send_email(*, to: str, subject: str, html_body: str, text_body: str) -> None:
    if not smtp_configured():
        raise MailConfigurationError(
            "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and MAIL_FROM in backend/.env."
        )
    cfg = current_app.config
    from_addr = cfg["MAIL_FROM"]
    from_name = cfg.get("MAIL_FROM_NAME") or "FacultyLink"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = to
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    use_tls = cfg.get("SMTP_USE_TLS", True)
    host = cfg["SMTP_HOST"]
    port = int(cfg["SMTP_PORT"])

    try:
        if use_tls:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(
                    cfg["SMTP_USERNAME"],
                    "".join(str(cfg.get("SMTP_PASSWORD") or "").split()),
                )
                smtp.sendmail(from_addr, [to], msg.as_string())
        else:
            with smtplib.SMTP_SSL(host, port, timeout=30, context=ssl.create_default_context()) as smtp:
                smtp.login(
                    cfg["SMTP_USERNAME"],
                    "".join(str(cfg.get("SMTP_PASSWORD") or "").split()),
                )
                smtp.sendmail(from_addr, [to], msg.as_string())
    except Exception as exc:
        _log.warning("SMTP send failed for %s: %s", to, _sanitized_error(exc))
        raise


def send_new_account_credentials(
    *,
    role: UserRole,
    full_name: str,
    email: str,
    temporary_password: str,
) -> None:
    subject = "Your FacultyLink sign-in credentials"
    if role == UserRole.faculty:
        html_body = mail_templates.credentials_faculty_html(full_name, email, temporary_password)
        text_body = mail_templates.credentials_faculty_text(full_name, email, temporary_password)
    elif role == UserRole.reviewer:
        html_body = mail_templates.credentials_reviewer_html(full_name, email, temporary_password)
        text_body = mail_templates.credentials_reviewer_text(full_name, email, temporary_password)
    else:
        raise ValueError("Credential email is only supported for faculty and reviewer roles.")
    send_email(to=email, subject=subject, html_body=html_body, text_body=text_body)


def send_recovery_code(*, full_name: str, email: str, code: str, ttl_minutes: int) -> None:
    subject = "Reset your FacultyLink password"
    html_body = mail_templates.recovery_code_html(full_name, code, ttl_minutes)
    text_body = mail_templates.recovery_code_text(full_name, code, ttl_minutes)
    send_email(to=email, subject=subject, html_body=html_body, text_body=text_body)


def send_password_changed_notice(*, full_name: str, email: str) -> None:
    subject = "Your FacultyLink password was changed"
    html_body = mail_templates.password_changed_html(full_name)
    text_body = mail_templates.password_changed_text(full_name)
    send_email(to=email, subject=subject, html_body=html_body, text_body=text_body)
