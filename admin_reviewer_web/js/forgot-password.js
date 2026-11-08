import { PasswordRecoveryService } from './services/password-recovery-service.js';

const steps = () => document.querySelectorAll('.recovery-step');
let currentStep = 1;
let savedEmail = '';
let resetToken = '';
let resendCooldown = 0;
let resendTimer = null;

const showStep = (n) => {
  currentStep = n;
  steps().forEach((s) => s.classList.toggle('active', Number(s.dataset.step) === n));
  document.getElementById('stepLabel').textContent = `Step ${n} of 3`;
  const headings = ['Forgot Password?', 'Check Your Email', 'Set Your New Password'];
  document.getElementById('recoveryHeading').textContent = headings[n - 1] || 'Forgot Password?';
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

const startResendCooldown = (seconds = 60) => {
  resendCooldown = seconds;
  const btn = document.getElementById('resendCode');
  if (!btn) return;
  const tick = () => {
    if (resendCooldown <= 0) {
      btn.disabled = false;
      btn.textContent = 'Resend Code';
      clearInterval(resendTimer);
      return;
    }
    btn.disabled = true;
    btn.textContent = `Resend Code (${resendCooldown}s)`;
    resendCooldown -= 1;
  };
  tick();
  resendTimer = setInterval(tick, 1000);
};

showStep(1);

document.getElementById('code')?.addEventListener('input', (e) => {
  const v = e.target.value.replace(/\D/g, '').slice(0, 6);
  e.target.value = v;
});

document.getElementById('step1Continue')?.addEventListener('click', async () => {
  const email = document.getElementById('em').value;
  const err = PasswordRecoveryService.validateEmail(email);
  setFieldError('emError', err);
  if (err) return;
  const btn = document.getElementById('step1Continue');
  setLoading(btn, true, 'Send Verification Code');
  try {
    const data = await PasswordRecoveryService.requestCode(email);
    savedEmail = email.trim();
    setFieldError('emError', '');
    document.getElementById('neutralMsg')?.removeAttribute('hidden');
    if (document.getElementById('neutralMsg')) {
      document.getElementById('neutralMsg').textContent = data.message || '';
    }
    showStep(2);
    document.getElementById('code').focus();
    startResendCooldown();
  } catch (ex) {
    setFieldError('emError', ex.message || 'Could not send verification code.');
  } finally {
    setLoading(btn, false, 'Send Verification Code');
  }
});

document.getElementById('resendCode')?.addEventListener('click', async () => {
  if (resendCooldown > 0 || !savedEmail) return;
  const btn = document.getElementById('resendCode');
  btn.disabled = true;
  try {
    await PasswordRecoveryService.requestCode(savedEmail);
    startResendCooldown();
  } catch (ex) {
    setFieldError('codeError', ex.message || 'Could not resend code.');
    btn.disabled = false;
  }
});

document.getElementById('changeEmail')?.addEventListener('click', (e) => {
  e.preventDefault();
  setFieldError('codeError', '');
  showStep(1);
});

document.getElementById('step2Verify')?.addEventListener('click', async () => {
  const btn = document.getElementById('step2Verify');
  setLoading(btn, true, 'Verify Code');
  try {
    const data = await PasswordRecoveryService.verifyCode(savedEmail, document.getElementById('code').value);
    resetToken = data.resetToken;
    setFieldError('codeError', '');
    showStep(3);
    document.getElementById('np').focus();
  } catch (ex) {
    setFieldError('codeError', ex.message || 'Invalid or expired verification code.');
  } finally {
    setLoading(btn, false, 'Verify Code');
  }
});

document.getElementById('toggleNp')?.addEventListener('click', () => {
  const input = document.getElementById('np');
  input.type = input.type === 'password' ? 'text' : 'password';
});

document.getElementById('toggleNp2')?.addEventListener('click', () => {
  const input = document.getElementById('np2');
  input.type = input.type === 'password' ? 'text' : 'password';
});

document.getElementById('finishRec')?.addEventListener('click', async () => {
  const btn = document.getElementById('finishRec');
  const np = document.getElementById('np').value;
  const np2 = document.getElementById('np2').value;
  const err = PasswordRecoveryService.validateNewPassword(np, np2);
  setFieldError('recErr', err);
  if (err) return;
  setLoading(btn, true, 'Save New Password');
  try {
    await PasswordRecoveryService.completeReset(resetToken, np, np2);
    document.getElementById('recoveryFlow').setAttribute('hidden', '');
    const success = document.getElementById('recoverySuccess');
    success.removeAttribute('hidden');
    success.querySelector('[data-success-msg]').textContent =
      'Your password has been updated. Please sign in.';
  } catch (ex) {
    setFieldError('recErr', ex.message || 'Could not update password.');
  } finally {
    setLoading(btn, false, 'Save New Password');
  }
});
