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

test('reviewer availability follows review window (start/end inclusive)', () => {
  const period = { start: '2026-01-15', end: '2026-06-30', reviewerAvailableFrom: '2026-02-01' };

  const open = reviewerAvailabilityDetail(period, new Date('2026-06-01T04:00:00Z'));
  assert.equal(open.available, true);
  assert.equal(open.statusLabel, 'Available now');

  const future = reviewerAvailabilityDetail(period, new Date('2026-01-20T04:00:00Z'));
  assert.equal(future.available, false);
  assert.match(future.statusLabel, /^Opens /);

  const closed = reviewerAvailabilityDetail(period, new Date('2026-07-01T04:00:00Z'));
  assert.equal(closed.available, false);
  assert.equal(closed.statusLabel, 'Closed');

  const missing = reviewerAvailabilityDetail({}, new Date('2026-06-01T04:00:00Z'));
  assert.equal(missing.configured, false);
  assert.equal(missing.statusLabel, 'Not configured');
});

test('reviewer access closes day after evaluation end (Manila)', () => {
  const period = { start: '2026-10-01', end: '2026-11-18', reviewerAvailableFrom: '2026-10-15' };
  const lastDay = reviewerAvailabilityDetail(period, new Date('2026-11-18T15:00:00Z'));
  assert.equal(lastDay.statusLabel, 'Available now');
  const afterEnd = reviewerAvailabilityDetail(period, new Date('2026-11-19T15:00:00Z'));
  assert.equal(afterEnd.statusLabel, 'Closed');
});

test('calendarDateInTimeZone returns YYYY-MM-DD', () => {
  assert.match(calendarDateInTimeZone(new Date('2026-03-09T20:00:00Z')), /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(calendarDateInTimeZone(new Date('2026-03-09T20:00:00Z')), '2026-03-10');
});
