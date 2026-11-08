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
});

document.getElementById('contactBtn').addEventListener('click', () => {
  const p = document.getElementById('contactPanel');
  p.hidden = !p.hidden;
});

if (AuthRepository.getSession()) {
  window.location.href = '/app.html';
}

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
  if (em.includes('faculty') || em.includes('maria.santos') || em.includes('ana.reyes')) {
    err.textContent = 'Faculty accounts sign in via the FacultyLink mobile app.';
    return;
  }
  btn.disabled = true;
  btn.textContent = 'Signing in…';
  try {
    await AuthRepository.login(em, pw);
    if (document.getElementById('remember').checked) localStorage.setItem('fl_remember_email', em);
    else localStorage.removeItem('fl_remember_email');
    window.location.href = '/app.html';
  } catch (ex) {
    err.textContent = ex.message || 'Sign in failed.';
    btn.disabled = false;
    btn.textContent = 'Sign in';
  }
});
