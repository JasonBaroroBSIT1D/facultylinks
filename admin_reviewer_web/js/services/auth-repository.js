const SESSION_KEY = 'facultylink_session';
const PASSWORD_OVERRIDES_KEY = 'fl_password_overrides';

const DEMO_USERS = [
  { email: 'admin@ustp.demo', password: 'Admin@2026', role: 'admin', name: 'System Administrator' },
  { email: 'reviewer@ustp.demo', password: 'Review@2026', role: 'reviewer', name: 'Elena Mendoza', reviewerId: 'rev-001' },
];

export const DEMO_USER_EMAILS = DEMO_USERS.map((u) => u.email.toLowerCase());

export function setPasswordOverride(email, password) {
  const map = JSON.parse(localStorage.getItem(PASSWORD_OVERRIDES_KEY) || '{}');
  map[email.trim().toLowerCase()] = password;
  localStorage.setItem(PASSWORD_OVERRIDES_KEY, JSON.stringify(map));
}

export function getPasswordForUser(email) {
  const key = email.trim().toLowerCase();
  const overrides = JSON.parse(localStorage.getItem(PASSWORD_OVERRIDES_KEY) || '{}');
  if (overrides[key]) return overrides[key];
  const user = DEMO_USERS.find((u) => u.email.toLowerCase() === key);
  return user?.password ?? null;
}

export class AuthRepository {
  static login(email, password) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const key = email.trim().toLowerCase();
        const user = DEMO_USERS.find((u) => u.email.toLowerCase() === key);
        if (!user) {
          reject(new Error('Invalid email or password.'));
          return;
        }
        const expected = getPasswordForUser(email);
        if (expected !== password) {
          reject(new Error('Invalid email or password.'));
          return;
        }
        const session = { email: user.email, role: user.role, name: user.name, reviewerId: user.reviewerId, at: Date.now() };
        sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
        resolve(session);
      }, 600);
    });
  }

  static logout() {
    sessionStorage.removeItem(SESSION_KEY);
  }

  static getSession() {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  static requireRole(roles) {
    const s = AuthRepository.getSession();
    if (!s || !roles.includes(s.role)) {
      window.location.href = '/login.html';
      return null;
    }
    return s;
  }

  static facultyLoginBlocked(email) {
    return /@ustp\.demo$/i.test(email) && /faculty|maria\.santos|ana\.reyes/i.test(email);
  }
}
