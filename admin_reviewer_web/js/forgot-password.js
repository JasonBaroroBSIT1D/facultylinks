import {
  PasswordRecoveryService,
  RECOVERY_CHANNEL_EMAIL,
  RECOVERY_CHANNEL_SMS,
} from './services/password-recovery-service.js';

const steps = () => document.querySelectorAll('.recovery-step');
let currentStep = 1;
let savedChannel = RECOVERY_CHANNEL_EMAIL;
let savedEmail = '';
let savedPhone = '';
let resetToken = '';
let resendCooldown = 0;
let resendTimer = null;

const $ = (id) => document.getElementById(id);

const getSelectedChannel = () => ($('chSms')?.checked ? RECOVERY_CHANNEL_SMS : RECOVERY_CHANNEL_EMAIL);

const showStep = (n) => {
  currentStep = n;
  steps().forEach((s) => s.classList.toggle('active', Number(s.dataset.step) === n));
  $('stepLabel').textContent = `Step ${n} of 3`;
  const headings = ['Forgot Password?', 'Enter Verification Code', 'Set Your New Password'];
  $('recoveryHeading').textContent = headings[n - 1] || 'Forgot Password?';
};

const setFieldError = (id, message) => {
  const el = $(id);
  if (el) el.textContent = message || '';
};

const STEP1_REQUEST_ERROR = 'Could not send verification code. Please try again.';

const clearStep1Errors = () => {
  setFieldError('emError', '');
  setFieldError('phoneError', '');
  setFieldError('step1FormError', '');
};

const setStep1Error = (message) => {
  const msg = message || '';
  setFieldError('step1FormError', msg);
  return msg;
};

/** Show exactly one Step 1 identifier field; disable the hidden control so validation cannot block SMS. */
function syncChannelFields() {
  const channel = getSelectedChannel();
  const isEmail = channel === RECOVERY_CHANNEL_EMAIL;
  const fieldEmail = $('fieldEmail');
  const fieldPhone = $('fieldPhone');
  const em = $('em');
  const phone = $('phone');

  if (fieldEmail) {
    fieldEmail.classList.toggle('recovery-field--hidden', !isEmail);
    fieldEmail.setAttribute('aria-hidden', String(!isEmail));
  }
  if (fieldPhone) {
    fieldPhone.classList.toggle('recovery-field--hidden', isEmail);
    fieldPhone.setAttribute('aria-hidden', String(isEmail));
  }

  if (em) {
    em.disabled = !isEmail;
    em.toggleAttribute('aria-disabled', !isEmail);
    if (!isEmail) {
      em.removeAttribute('required');
    }
  }
  if (phone) {
    phone.disabled = isEmail;
    phone.toggleAttribute('aria-disabled', isEmail);
    if (isEmail) {
      phone.removeAttribute('required');
    }
  }

  clearStep1Errors();
}

const step1IdentifierValues = () => {
  const channel = getSelectedChannel();
  if (channel === RECOVERY_CHANNEL_EMAIL) {
    return { channel, email: $('em')?.value ?? '', phone: '' };
  }
  return { channel, email: '', phone: $('phone')?.value ?? '' };
};

const setLoading = (button, loading, idleLabel, loadingLabel = 'Sending…') => {
  if (!button) return;
  button.disabled = loading;
  button.textContent = loading ? loadingLabel : idleLabel;
};

const startResendCooldown = (seconds = 60) => {
  resendCooldown = seconds;
  const btn = $('resendCode');
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

const sendCode = async () => {
  syncChannelFields();
  savedChannel = getSelectedChannel();
  const { email, phone } = step1IdentifierValues();

  let err = null;
  if (savedChannel === RECOVERY_CHANNEL_EMAIL) {
    err = PasswordRecoveryService.validateEmail(email);
    setFieldError('emError', err);
    setFieldError('phoneError', '');
  } else {
    err = PasswordRecoveryService.validatePhone(phone);
    setFieldError('phoneError', err);
    setFieldError('emError', '');
  }
  if (err) return;

  const btn = $('step1Continue');
  clearStep1Errors();
  setLoading(btn, true, 'Send Code', 'Sending…');
  try {
    const data = await PasswordRecoveryService.requestCode(savedChannel, { email, phone });
    if (savedChannel === RECOVERY_CHANNEL_EMAIL) {
      savedEmail = email.trim();
      savedPhone = '';
    } else {
      savedPhone = phone.trim();
      savedEmail = '';
    }
    clearStep1Errors();
    const neutral = $('neutralMsg');
    if (neutral) {
      neutral.textContent =
        data.message || 'If recovery is available through your selected method, a code will be sent.';
    }
    showStep(2);
    $('code').value = '';
    $('code').focus();
    startResendCooldown();
  } catch {
    setStep1Error(STEP1_REQUEST_ERROR);
  } finally {
    setLoading(btn, false, 'Send Code');
  }
};

showStep(1);
syncChannelFields();

const channelGroup = $('recoveryChannelLegend')?.closest('.recovery-channel-group');
channelGroup?.addEventListener('input', (e) => {
  if (e.target?.name === 'recoveryChannel') syncChannelFields();
});
channelGroup?.addEventListener('change', (e) => {
  if (e.target?.name === 'recoveryChannel') syncChannelFields();
});
channelGroup?.addEventListener('click', () => {
  requestAnimationFrame(syncChannelFields);
});
document.querySelectorAll('input[name="recoveryChannel"]').forEach((radio) => {
  radio.addEventListener('change', syncChannelFields);
  radio.addEventListener('input', syncChannelFields);
});

$('code')?.addEventListener('input', (e) => {
  const v = e.target.value.replace(/\D/g, '').slice(0, 6);
  e.target.value = v;
});

$('step1Continue')?.addEventListener('click', () => void sendCode());

$('resendCode')?.addEventListener('click', async () => {
  if (resendCooldown > 0) return;
  if (savedChannel === RECOVERY_CHANNEL_EMAIL && !savedEmail) return;
  if (savedChannel === RECOVERY_CHANNEL_SMS && !savedPhone) return;
  const btn = $('resendCode');
  btn.disabled = true;
  try {
    await PasswordRecoveryService.requestCode(savedChannel, {
      email: savedEmail,
      phone: savedPhone,
    });
    startResendCooldown();
    setFieldError('codeError', '');
  } catch (ex) {
    setFieldError('codeError', ex.message || 'Could not resend code.');
    btn.disabled = false;
  }
});

$('changeMethod')?.addEventListener('click', (e) => {
  e.preventDefault();
  setFieldError('codeError', '');
  if (savedChannel === RECOVERY_CHANNEL_EMAIL && savedEmail) {
    $('em').value = savedEmail;
    $('chEmail').checked = true;
  } else if (savedChannel === RECOVERY_CHANNEL_SMS && savedPhone) {
    $('phone').value = savedPhone;
    $('chSms').checked = true;
  }
  syncChannelFields();
  showStep(1);
});

$('step2Verify')?.addEventListener('click', async () => {
  const btn = $('step2Verify');
  setLoading(btn, true, 'Verify Code');
  try {
    const data = await PasswordRecoveryService.verifyCode(savedChannel, {
      email: savedEmail,
      phone: savedPhone,
      code: $('code').value,
    });
    resetToken = data.resetToken;
    setFieldError('codeError', '');
    showStep(3);
    $('np').focus();
  } catch (ex) {
    setFieldError('codeError', ex.message || 'Invalid or expired verification code.');
  } finally {
    setLoading(btn, false, 'Verify Code');
  }
});

$('toggleNp')?.addEventListener('click', () => {
  const input = $('np');
  input.type = input.type === 'password' ? 'text' : 'password';
});

$('toggleNp2')?.addEventListener('click', () => {
  const input = $('np2');
  input.type = input.type === 'password' ? 'text' : 'password';
});

$('finishRec')?.addEventListener('click', async () => {
  const btn = $('finishRec');
  const np = $('np').value;
  const np2 = $('np2').value;
  const err = PasswordRecoveryService.validateNewPassword(np, np2);
  setFieldError('recErr', err);
  if (err) return;
  setLoading(btn, true, 'Save New Password');
  try {
    await PasswordRecoveryService.completeReset(resetToken, np, np2);
    $('recoveryFlow').setAttribute('hidden', '');
    const success = $('recoverySuccess');
    success.removeAttribute('hidden');
    success.querySelector('[data-success-msg]').textContent =
      'Your password has been updated. Please sign in.';
  } catch (ex) {
    setFieldError('recErr', ex.message || 'Could not update password.');
  } finally {
    setLoading(btn, false, 'Save New Password');
  }
});