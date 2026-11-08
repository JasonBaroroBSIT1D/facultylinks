import { AuthRepository } from './services/auth-repository.js';
import { getApiBase } from './core/api-config.js';

const form = document.getElementById('changePwForm');
const err = document.getElementById('pwErr');
const btn = document.getElementById('savePwBtn');

document.getElementById('toggleNp')?.addEventListener('click', () => {
  const input = document.getElementById('np');
  input.type = input.type === 'password' ? 'text' : 'password';
});
document.getElementById('toggleNp2')?.addEventListener('click', () => {
  const input = document.getElementById('np2');
  input.type = input.type === 'password' ? 'text' : 'password';
});

document.getElementById('signOutBtn')?.addEventListener('click', async () => {
  try {
    await AuthRepository.logout();
  } catch {
    AuthRepository.clearClientSession();
  }
  window.location.replace('/login.html');
});

void (async () => {
  try {
    const user = await AuthRepository.fetchMe();
    if (!user) {
      window.location.replace('/login.html');
      return;
    }
    if (!user.mustChangePassword) {
      window.location.replace('/app.html');
    }
  } catch {
    window.location.replace('/login.html');
  }
})();

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  err.textContent = '';
  if (btn.disabled) return;
  const newPassword = document.getElementById('np').value;
  const confirmPassword = document.getElementById('np2').value;
  btn.disabled = true;
  btn.textContent = 'Saving…';
  try {
    const res = await fetch(`${getApiBase()}/api/auth/change-password`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-Client-Type': 'web' },
      body: JSON.stringify({ newPassword, confirmPassword }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || 'Could not save password.');
    }
    AuthRepository.syncSessionFromApiUser(data.user);
    window.location.replace('/app.html');
  } catch (ex) {
    err.textContent = ex.message || 'Could not save password.';
    btn.disabled = false;
    btn.textContent = 'Save New Password';
  }
});
