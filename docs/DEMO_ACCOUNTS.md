# Test accounts (backend phase)

Authentication is served by the Flask API ([BACKEND_SETUP_WINDOWS.md](./BACKEND_SETUP_WINDOWS.md)). **Do not rely on hard-coded demo passwords** unless you recreate them with CLI commands.

## Create accounts

```powershell
cd backend
flask create-admin admin@yourinstitution.edu "YourSecurePass1!"
flask create-user reviewer reviewer@yourinstitution.edu "ReviewPass1!" --name "Reviewer"
flask create-user faculty faculty@yourinstitution.edu "FacultyPass1!" --name "Faculty"
flask assign-reviewer reviewer@yourinstitution.edu faculty@yourinstitution.edu
```

| Role    | Application        | Notes |
|---------|--------------------|--------|
| Admin   | Web `login.html`   | Institution-issued email |
| Reviewer| Web `login.html`   | Same |
| Faculty | Flutter mobile     | Not accepted on web login screen |

Remember-email stores only the address in `localStorage` (`fl_remember_email`).

Faculty accounts are rejected on the web login screen (client check + API role rules).

## Password recovery (local frontend testing)

Web (admin/reviewer) and Flutter (faculty) use a **local recovery adapter** only — no email is sent.

| Step | User-facing action | Test verification code |
|------|-------------------|-------------------------|
| 1 | Enter account email → **Continue** | — |
| 2 | Enter code → **Verify Code** | `123456` |
| 3 | Set new password → **Save New Password** | Min. 8 chars, one letter and one number |

Updated passwords are stored in browser `localStorage` (`fl_password_overrides`) or Flutter `SharedPreferences` for the same demo email only. They apply on the next sign-in on that device; they do **not** change a remote server account.
