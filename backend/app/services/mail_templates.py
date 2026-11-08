"""HTML + plain-text email bodies for FacultyLink (navy/blue branding)."""

NAVY = "#0B1F3A"
PANEL_BG = "#F4F7FB"
TEXT = "#1A2B3C"
MUTED = "#5A7089"


def _wrap_html(inner: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/></head>
<body style="margin:0;padding:0;background:#E8EEF5;font-family:Inter,Segoe UI,Arial,sans-serif;color:{TEXT};">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#E8EEF5;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:520px;background:#fff;border-radius:12px;overflow:hidden;
        box-shadow:0 4px 24px rgba(11,31,58,0.08);">
        <tr><td style="background:{NAVY};padding:20px 24px;">
          <span style="color:#fff;font-size:20px;font-weight:700;letter-spacing:0.02em;">FacultyLink</span>
        </td></tr>
        <tr><td style="padding:24px;">{inner}</td></tr>
        <tr><td style="padding:16px 24px;background:{PANEL_BG};font-size:12px;color:{MUTED};">
          This message was sent by FacultyLink on behalf of your institution.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def credentials_faculty_html(full_name: str, email: str, temporary_password: str) -> str:
    inner = f"""
      <p style="margin:0 0 12px;font-size:16px;line-height:1.5;">Hello {full_name},</p>
      <p style="margin:0 0 12px;font-size:15px;line-height:1.55;">Your institution created a <strong>Faculty</strong> account for you.</p>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.55;">
        Open the <strong>FacultyLink mobile app</strong> on your device and sign in with the credentials below.
      </p>
      <div style="background:{PANEL_BG};border:1px solid #D8E2EE;border-radius:8px;padding:16px;margin:0 0 16px;">
        <p style="margin:0 0 8px;font-size:14px;"><strong>Email:</strong> {email}</p>
        <p style="margin:0;font-size:14px;"><strong>Temporary password:</strong> {temporary_password}</p>
      </div>
      <p style="margin:0;font-size:14px;color:{MUTED};line-height:1.5;">
        You must change this temporary password after signing in before you can access your dashboard.
      </p>"""
    return _wrap_html(inner)


def credentials_faculty_text(full_name: str, email: str, temporary_password: str) -> str:
    return f"""FacultyLink

Hello {full_name},

Your institution created a Faculty account for you.

Open the FacultyLink mobile app on your device and sign in with the credentials below.

Email: {email}
Temporary password: {temporary_password}

You must change this temporary password after signing in before you can access your dashboard.
"""


def credentials_reviewer_html(full_name: str, email: str, temporary_password: str) -> str:
    inner = f"""
      <p style="margin:0 0 12px;font-size:16px;line-height:1.5;">Hello {full_name},</p>
      <p style="margin:0 0 12px;font-size:15px;line-height:1.55;">Your institution created a <strong>Reviewer</strong> account for you.</p>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.55;">
        Open the FacultyLink Reviewer Web portal and sign in with the credentials below.
      </p>
      <div style="background:{PANEL_BG};border:1px solid #D8E2EE;border-radius:8px;padding:16px;margin:0 0 16px;">
        <p style="margin:0 0 8px;font-size:14px;"><strong>Email:</strong> {email}</p>
        <p style="margin:0;font-size:14px;"><strong>Temporary password:</strong> {temporary_password}</p>
      </div>
      <p style="margin:0;font-size:14px;color:{MUTED};line-height:1.5;">
        You must change this temporary password after signing in before you can access your dashboard.
      </p>"""
    return _wrap_html(inner)


def credentials_reviewer_text(full_name: str, email: str, temporary_password: str) -> str:
    return f"""FacultyLink

Hello {full_name},

Your institution created a Reviewer account for you.

Open the FacultyLink Reviewer Web portal and sign in with the credentials below.

Email: {email}
Temporary password: {temporary_password}

You must change this temporary password after signing in before you can access your dashboard.
"""


def recovery_code_html(full_name: str, code: str, minutes: int) -> str:
    inner = f"""
      <p style="margin:0 0 12px;font-size:16px;line-height:1.5;">Hello {full_name or 'there'},</p>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.55;">
        Use this verification code to reset your FacultyLink password. It expires in <strong>{minutes} minutes</strong>.
      </p>
      <p style="margin:0 0 16px;font-size:28px;font-weight:700;letter-spacing:0.25em;color:{NAVY};text-align:center;">
        {code}
      </p>
      <p style="margin:0 0 8px;font-size:14px;color:{MUTED};">Do not share this code.</p>
      <p style="margin:0;font-size:14px;color:{MUTED};">If you did not request this, you can ignore this email.</p>"""
    return _wrap_html(inner)


def recovery_code_text(full_name: str, code: str, minutes: int) -> str:
    return f"""FacultyLink — Reset your password

Hello {full_name or 'there'},

Your verification code is: {code}

This code expires in {minutes} minutes.

Do not share this code.
If you did not request this, you can ignore this email.
"""


def password_changed_html(full_name: str) -> str:
    inner = f"""
      <p style="margin:0 0 12px;font-size:16px;line-height:1.5;">Hello {full_name or 'there'},</p>
      <p style="margin:0;font-size:15px;line-height:1.55;">
        Your FacultyLink password was changed successfully. If you did not make this change, contact your institution administrator immediately.
      </p>"""
    return _wrap_html(inner)


def password_changed_text(full_name: str) -> str:
    return f"""FacultyLink

Hello {full_name or 'there'},

Your FacultyLink password was changed successfully.

If you did not make this change, contact your institution administrator immediately.
"""
