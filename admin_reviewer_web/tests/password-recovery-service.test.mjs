import test from 'node:test';
import assert from 'node:assert/strict';
import {
  RECOVERY_CHANNEL_EMAIL,
  RECOVERY_CHANNEL_SMS,
  buildRecoveryRequestPayload,
  buildRecoveryVerifyPayload,
  validateEmail,
  validatePhone,
} from '../js/services/password-recovery-service.js';

test('validatePhone accepts PH formats', () => {
  assert.equal(validatePhone('09171234567'), null);
  assert.equal(validatePhone('+639171234567'), null);
  assert.match(validatePhone('08171234567') || '', /valid Philippine/);
  assert.match(validatePhone('') || '', /required/i);
});

test('buildRecoveryRequestPayload email channel', () => {
  assert.deepEqual(buildRecoveryRequestPayload(RECOVERY_CHANNEL_EMAIL, { email: ' a@b.edu ' }), {
    channel: 'email',
    email: 'a@b.edu',
  });
  assert.equal(buildRecoveryRequestPayload(RECOVERY_CHANNEL_EMAIL, { email: 'a@b.edu' }).phone, undefined);
});

test('buildRecoveryRequestPayload sms channel without email', () => {
  assert.deepEqual(buildRecoveryRequestPayload(RECOVERY_CHANNEL_SMS, { phone: ' 09171234567 ' }), {
    channel: 'sms',
    phone: '09171234567',
  });
  assert.equal(buildRecoveryRequestPayload(RECOVERY_CHANNEL_SMS, { phone: '09171234567' }).email, undefined);
});

test('buildRecoveryVerifyPayload binds channel identifier', () => {
  assert.deepEqual(
    buildRecoveryVerifyPayload(RECOVERY_CHANNEL_SMS, { phone: '09998887766', code: '123456' }),
    { channel: 'sms', phone: '09998887766', code: '123456' }
  );
  assert.deepEqual(
    buildRecoveryVerifyPayload(RECOVERY_CHANNEL_EMAIL, { email: 'x@y.edu', code: '123456' }),
    { channel: 'email', email: 'x@y.edu', code: '123456' }
  );
});

test('validateEmail unchanged', () => {
  assert.equal(validateEmail('user@school.edu'), null);
  assert.match(validateEmail('bad') || '', /valid email/i);
});

test('email and sms payloads are mutually exclusive', () => {
  const emailBody = buildRecoveryRequestPayload(RECOVERY_CHANNEL_EMAIL, {
    email: 'a@b.edu',
    phone: '09171234567',
  });
  assert.equal(emailBody.channel, 'email');
  assert.equal(emailBody.email, 'a@b.edu');
  assert.equal('phone' in emailBody, false);

  const smsBody = buildRecoveryRequestPayload(RECOVERY_CHANNEL_SMS, {
    email: 'a@b.edu',
    phone: '09171234567',
  });
  assert.equal(smsBody.channel, 'sms');
  assert.equal(smsBody.phone, '09171234567');
  assert.equal('email' in smsBody, false);
});