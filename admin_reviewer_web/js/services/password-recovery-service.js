import { getApiBase } from '../core/api-config.js';

export const RECOVERY_CHANNEL_EMAIL = 'email';
export const RECOVERY_CHANNEL_SMS = 'sms';

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

export function validateEmail(email) {
  const em = email?.trim() ?? '';
  if (!em) return 'Email address is required.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) return 'Enter a valid email address.';
  return null;
}

export function validatePhone(phone) {
  const compact = String(phone ?? '')
    .trim()
    .replace(/[\s\-()]/g, '');
  if (!compact) return 'Mobile number is required.';
  if (!/^09\d{9}$/.test(compact) && !/^\+639\d{9}$/.test(compact)) {
    return 'Enter a valid Philippine mobile number (09XXXXXXXXX or +639XXXXXXXXX).';
  }
  return null;
}

/** @param {'email'|'sms'} channel */
export function buildRecoveryRequestPayload(channel, { email = '', phone = '' } = {}) {
  if (channel === RECOVERY_CHANNEL_SMS) {
    return { channel: RECOVERY_CHANNEL_SMS, phone: String(phone).trim() };
  }
  return { channel: RECOVERY_CHANNEL_EMAIL, email: String(email).trim() };
}

/** @param {'email'|'sms'} channel */
export function buildRecoveryVerifyPayload(channel, { email = '', phone = '', code = '' } = {}) {
  const base = { channel, code: String(code).trim() };
  if (channel === RECOVERY_CHANNEL_SMS) {
    return { ...base, phone: String(phone).trim() };
  }
  return { ...base, email: String(email).trim() };
}

export const PasswordRecoveryService = {
  isAvailable() {
    return true;
  },

  validateEmail,
  validatePhone,
  buildRecoveryRequestPayload,
  buildRecoveryVerifyPayload,

  async requestCode(channel, { email = '', phone = '' } = {}) {
    const body = buildRecoveryRequestPayload(channel, { email, phone });
    return post('/api/auth/password-recovery/request', body);
  },

  async verifyCode(channel, { email = '', phone = '', code = '' } = {}) {
    const body = buildRecoveryVerifyPayload(channel, { email, phone, code });
    return post('/api/auth/password-recovery/verify', body);
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