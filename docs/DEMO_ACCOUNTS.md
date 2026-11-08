# Demonstration Accounts

**Warning:** These credentials are for local demonstration only. There is no server-side authentication, password hashing, or session hardening. Do not use in production.

| Role    | Email                      | Password    | Application        |
|---------|----------------------------|-------------|--------------------|
| Admin   | admin@ustp.demo            | Admin@2026  | Web (login.html)   |
| Reviewer| reviewer@ustp.demo         | Review@2026 | Web (login.html)   |
| Faculty | faculty@ustp.demo          | Faculty@2026| Flutter mobile app |
| Faculty (empty assessment) | maria.santos@ustp.demo | Faculty@2026 | Flutter |

Remember-email stores only the address in `localStorage` (`fl_remember_email`).

Faculty accounts are not accepted on the web login screen; use the Flutter app.

## Password recovery (local frontend testing)

Web (admin/reviewer) and Flutter (faculty) use a **local recovery adapter** only — no email is sent.

| Step | User-facing action | Test verification code |
|------|-------------------|-------------------------|
| 1 | Enter account email → **Continue** | — |
| 2 | Enter code → **Verify Code** | `123456` |
| 3 | Set new password → **Save New Password** | Min. 8 chars, one letter and one number |

Updated passwords are stored in browser `localStorage` (`fl_password_overrides`) or Flutter `SharedPreferences` for the same demo email only. They apply on the next sign-in on that device; they do **not** change a remote server account.
