/** Local frontend password recovery (see docs/DEMO_ACCOUNTS.md for test verification code). */

/** Backend phase 1: account recovery is admin-managed; this flow stays disabled. */

const VERIFICATION_CODE = '123456';

export const PasswordRecoveryService = {
  isAvailable() {
    return true;
  },

  validateEmail(email) {
    const em = email?.trim() ?? '';
    if (!em) return 'Email address is required.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) return 'Enter a valid email address.';
    return 'Password recovery is not enabled yet. Contact your institution administrator.';
  },

  /** Step 1 → 2 (no email-delivery messaging). */
  prepareVerification(_email) {
    return { ok: true };
  },

  verifyCode(code) {
    const c = (code ?? '').trim();
    if (!c) return { ok: false, error: 'Verification code is required.' };
    if (c !== VERIFICATION_CODE) return { ok: false, error: 'The code you entered is not valid.' };
    return { ok: true };
  },

  validateNewPassword(password, confirm) {
    if (!password) return 'New password is required.';
    if (password.length < 8) return 'Password must be at least 8 characters.';
    if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
      return 'Use at least one letter and one number.';
    }
    if (password !== confirm) return 'Passwords do not match.';
    return null;
  },

  updatePassword(_email, _password, _confirm) {
    return {
      ok: false,
      error: 'Password recovery is not enabled yet. Contact your institution administrator.',
    };
  },
};
