const SESSION_KEY = 'facultylink_session';

const DEMO_USERS = [
  { email: 'admin@ustp.demo', password: 'Admin@2026', role: 'admin', name: 'System Administrator' },
  { email: 'reviewer@ustp.demo', password: 'Review@2026', role: 'reviewer', name: 'Elena Mendoza', reviewerId: 'rev-001' },
];

export class AuthRepository {
  static login(email, password) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const user = DEMO_USERS.find((u) => u.email.toLowerCase() === email.trim().toLowerCase());
        if (!user || user.password !== password) {
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
