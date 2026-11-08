import { AuthRepository } from './services/auth-repository.js';

document.getElementById('yr').textContent = new Date().getFullYear();

const form = document.getElementById('loginForm');
const err = document.getElementById('formError');
const btn = document.getElementById('submitBtn');
const email = document.getElementById('email');
const password = document.getElementById('password');

const remembered = localStorage.getItem('fl_remember_email');
if (remembered) {
  email.value = remembered;
  document.getElementById('remember').checked = true;
}

document.getElementById('togglePw').addEventListener('click', () => {
  const isText = password.type === 'text';
  password.type = isText ? 'password' : 'text';
  document.getElementById('togglePw').setAttribute('aria-label', isText ? 'Show password' : 'Hide password');
});

document.getElementById('contactBtn').addEventListener('click', () => {
  const p = document.getElementById('contactPanel');
  p.hidden = !p.hidden;
});

void (async () => {
  try {
    const session = await AuthRepository.ensureWebPortalSession(['admin', 'reviewer']);
    if (session) {
      window.location.replace(session.mustChangePassword ? '/change-password.html' : '/app.html');
    }
  } catch {
    /* stay on login — user can sign in or refresh */
  }
})();

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  err.textContent = '';
  const em = email.value.trim();
  const pw = password.value;
  if (!em || !pw) {
    err.textContent = 'Email and password are required.';
    return;
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) {
    err.textContent = 'Enter a valid email address.';
    return;
  }
  if (btn.disabled) return;
  btn.disabled = true;
  btn.textContent = 'Signing in…';
  try {
    const session = await AuthRepository.login(em, pw);
    if (session.role === 'faculty') {
      try {
        await AuthRepository.logout();
      } catch {
        AuthRepository.clearClientSession();
      }
      err.textContent = 'Faculty accounts sign in via the FacultyLink mobile app.';
      btn.disabled = false;
      btn.textContent = 'Sign In';
      return;
    }
    if (document.getElementById('remember').checked) localStorage.setItem('fl_remember_email', em);
    else localStorage.removeItem('fl_remember_email');
    if (session.mustChangePassword) {
      window.location.replace('/change-password.html');
      return;
    }
    window.location.replace('/app.html');
  } catch (ex) {
    err.textContent = ex.message || 'Sign in failed.';
    btn.disabled = false;
    btn.textContent = 'Sign In';
  }
});
