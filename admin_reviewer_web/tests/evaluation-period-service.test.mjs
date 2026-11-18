import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calendarDateInTimeZone,
  computeEvaluationPeriodStatus,
  validateEvaluationPeriodDates,
  reviewerScheduleNote,
  reviewerAvailabilityDetail,
} from '../js/core/evaluation-period-service.js';

test('end before start is invalid; reviewer after end is not blocked', () => {
  assert.equal(validateEvaluationPeriodDates({ start: '2026-06-01', end: '2026-05-01' }), 'End date cannot be before the start date.');
  assert.equal(validateEvaluationPeriodDates({ start: '2026-01-15', end: '2026-06-30' }), null);
  assert.equal(
    reviewerScheduleNote({ start: '2026-01-15', end: '2026-06-30', reviewerAvailableFrom: '2026-07-15' }) != null,
    true
  );
  assert.match(
    reviewerScheduleNote({ start: '2026-01-15', end: '2026-06-30', reviewerAvailableFrom: '2026-07-15' }),
    /after the evaluation period ends/
  );
  assert.equal(
    reviewerScheduleNote({ start: '2026-01-15', end: '2026-06-30', reviewerAvailableFrom: '2026-02-01' }),
    null
  );
});

test('status uses Asia/Manila calendar day boundaries', () => {
  const period = { start: '2026-03-10', end: '2026-03-20' };
  // 2026-03-09 20:00 UTC = 2026-03-10 04:00 Manila → Open
  assert.equal(computeEvaluationPeriodStatus(period, new Date('2026-03-09T20:00:00Z')), 'Open');
  // 2026-03-09 15:00 UTC = 2026-03-09 23:00 Manila → Upcoming
  assert.equal(computeEvaluationPeriodStatus(period, new Date('2026-03-09T15:00:00Z')), 'Upcoming');
  // 2026-03-20 16:00 UTC = 2026-03-21 00:00 Manila → Closed
  assert.equal(computeEvaluationPeriodStatus(period, new Date('2026-03-20T16:00:00Z')), 'Closed');
});

test('reviewer availability distinguishes configured open vs not yet', () => {
  const open = reviewerAvailabilityDetail(
    { reviewerAvailableFrom: '2026-01-01' },
    new Date('2026-06-01T04:00:00Z')
  );
  assert.equal(open.available, true);
  assert.equal(open.statusLabel, 'Available now');

  const future = reviewerAvailabilityDetail(
    { reviewerAvailableFrom: '2026-12-01' },
    new Date('2026-06-01T04:00:00Z')
  );
  assert.equal(future.available, false);
  assert.equal(future.statusLabel, 'Not yet open');

  const missing = reviewerAvailabilityDetail({}, new Date('2026-06-01T04:00:00Z'));
  assert.equal(missing.configured, false);
  assert.equal(missing.statusLabel, 'Not configured');
});

test('calendarDateInTimeZone returns YYYY-MM-DD', () => {
  assert.match(calendarDateInTimeZone(new Date('2026-03-09T20:00:00Z')), /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(calendarDateInTimeZone(new Date('2026-03-09T20:00:00Z')), '2026-03-10');
});
