import { getApiBase } from '../core/api-config.js';

async function post(path, body) {
  const res = await fetch(`${getApiBase()}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Client-Type': 'web' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const PasswordRecoveryService = {
  isAvailable() {
    return true;
  },

  validateEmail(email) {
    const em = email?.trim() ?? '';
    if (!em) return 'Email address is required.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) return 'Enter a valid email address.';
    return null;
  },

  async requestCode(email) {
    const data = await post('/api/auth/password-recovery/request', { email: email.trim() });
    return data;
  },

  async verifyCode(email, code) {
    const data = await post('/api/auth/password-recovery/verify', { email: email.trim(), code: String(code).trim() });
    return data;
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

  async completeReset(resetToken, password, confirm) {
    await post('/api/auth/password-recovery/complete', {
      resetToken,
      newPassword: password,
      confirmPassword: confirm,
    });
    return { ok: true };
  },
};
