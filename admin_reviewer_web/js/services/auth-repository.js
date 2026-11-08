import { getApiBase } from '../core/api-config.js';

const SESSION_KEY = 'facultylink_session';

function sessionFromUser(user) {
  return {
    email: user.email,
    role: user.role,
    name: user.name,
    userId: user.id,
    mustChangePassword: !!user.mustChangePassword,
    reviewerId: user.role === 'reviewer' ? `u-${user.id}` : null,
    at: Date.now(),
  };
}

export class AuthRepository {
  static clearClientSession() {
    try {
      sessionStorage.removeItem(SESSION_KEY);
    } catch {
      /* ignore */
    }
  }

  /** Backend identity; null if unauthenticated or network failure (throws on non-401 HTTP errors). */
  static async fetchMe() {
    let res;
    try {
      res = await fetch(`${getApiBase()}/api/auth/me`, {
        method: 'GET',
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
    } catch (e) {
      const err = new Error(e.message || 'Could not reach the server.');
      err.name = 'NetworkError';
      throw err;
    }
    const data = await res.json().catch(() => ({}));
    if (res.status === 401) {
      return null;
    }
    if (!res.ok) {
      const err = new Error(data.error || `Session check failed (${res.status}).`);
      err.status = res.status;
      throw err;
    }
    return data.user || null;
  }

  /** Sync sessionStorage from /api/portal/state `user` (avoids duplicate /api/auth/me). */
  static syncSessionFromApiUser(user) {
    if (!user?.role) return null;
    const session = sessionFromUser(user);
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return session;
  }

  /** Validate Flask session and sync sessionStorage from the server. */
  static async ensureWebPortalSession(roles) {
    const user = await this.fetchMe();
    if (!user || !roles.includes(user.role)) {
      this.clearClientSession();
      return null;
    }
    const session = sessionFromUser(user);
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return session;
  }

  static async login(email, password) {
    let res;
    try {
      res = await fetch(`${getApiBase()}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Client-Type': 'web' },
        credentials: 'include',
        body: JSON.stringify({ email: email.trim(), password }),
      });
    } catch (e) {
      const err = new Error(e.message || 'Could not reach the server.');
      err.name = 'NetworkError';
      throw err;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || 'Sign in failed.');
    }
    const session = sessionFromUser(data.user);
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return session;
  }

  static async logout() {
    let res;
    try {
      res = await fetch(`${getApiBase()}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
    } catch (e) {
      const err = new Error(e.message || 'Could not reach the server.');
      err.name = 'NetworkError';
      throw err;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || 'Sign out failed.');
    }
    this.clearClientSession();
  }

  static getSession() {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  /** Client cache only — use ensureWebPortalSession before trusting access. */
  static requireRole(roles) {
    const s = AuthRepository.getSession();
    if (!s || !roles.includes(s.role)) {
      return null;
    }
    return s;
  }

  static facultyLoginBlocked(email) {
    return /@ustp\.demo$/i.test(email) && /faculty|maria\.santos|ana\.reyes/i.test(email);
  }
}

/** @deprecated Demo-only password overrides removed with backend auth. */
export function setPasswordOverride() {}
export function getPasswordForUser() {
  return null;
}
export const DEMO_USER_EMAILS = [];
