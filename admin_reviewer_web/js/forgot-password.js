import { PasswordRecoveryService } from './services/password-recovery-service.js';

const steps = () => document.querySelectorAll('.recovery-step');
let currentStep = 1;
let savedEmail = '';

const showStep = (n) => {
  currentStep = n;
  steps().forEach((s) => s.classList.toggle('active', Number(s.dataset.step) === n));
  document.getElementById('stepLabel').textContent = `Step ${n} of 3`;
};

const setFieldError = (id, message) => {
  const el = document.getElementById(id);
  if (el) el.textContent = message || '';
};

const setLoading = (button, loading, idleLabel) => {
  if (!button) return;
  button.disabled = loading;
  button.textContent = loading ? 'Please wait…' : idleLabel;
};

if (!PasswordRecoveryService.isAvailable()) {
  document.getElementById('recoveryUnavailable')?.removeAttribute('hidden');
  document.getElementById('recoveryFlow')?.setAttribute('hidden', '');
} else {
  showStep(1);
}

document.getElementById('step1Continue')?.addEventListener('click', () => {
  const email = document.getElementById('em').value;
  const err = PasswordRecoveryService.validateEmail(email);
  setFieldError('emError', err);
  if (err) return;
  savedEmail = email.trim();
  PasswordRecoveryService.prepareVerification(savedEmail);
  showStep(2);
  document.getElementById('code').focus();
});

document.getElementById('changeEmail')?.addEventListener('click', (e) => {
  e.preventDefault();
  setFieldError('codeError', '');
  showStep(1);
});

document.getElementById('step2Verify')?.addEventListener('click', () => {
  const btn = document.getElementById('step2Verify');
  setLoading(btn, true, 'Verify Code');
  const result = PasswordRecoveryService.verifyCode(document.getElementById('code').value);
  setLoading(btn, false, 'Verify Code');
  if (!result.ok) {
    setFieldError('codeError', result.error);
    return;
  }
  setFieldError('codeError', '');
  showStep(3);
  document.getElementById('np').focus();
});

document.getElementById('toggleNp')?.addEventListener('click', () => {
  const input = document.getElementById('np');
  input.type = input.type === 'password' ? 'text' : 'password';
});

document.getElementById('toggleNp2')?.addEventListener('click', () => {
  const input = document.getElementById('np2');
  input.type = input.type === 'password' ? 'text' : 'password';
});

document.getElementById('finishRec')?.addEventListener('click', () => {
  const btn = document.getElementById('finishRec');
  const np = document.getElementById('np').value;
  const np2 = document.getElementById('np2').value;
  const err = PasswordRecoveryService.validateNewPassword(np, np2);
  setFieldError('recErr', err);
  if (err) return;
  setLoading(btn, true, 'Save New Password');
  const result = PasswordRecoveryService.updatePassword(savedEmail, np, np2);
  setLoading(btn, false, 'Save New Password');
  if (!result.ok) {
    setFieldError('recErr', result.error);
    return;
  }
  document.getElementById('recoveryFlow').setAttribute('hidden', '');
  const success = document.getElementById('recoverySuccess');
  success.removeAttribute('hidden');
  success.querySelector('[data-success-msg]').textContent =
    'Your password has been updated. Sign in with your new password.';
});
