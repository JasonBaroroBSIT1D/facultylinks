/**
 * Shared evaluation period contract (Admin, Reviewer, Faculty, future API).
 * Stored at `institutionConfig.preparationPeriod` in the demo (name kept for backward-compatible JSON).
 */

/** Institution calendar used for period status (matches Manila formatting elsewhere in the portal). */
export const EVALUATION_PERIOD_TIMEZONE = 'Asia/Manila';

export const EVALUATION_PERIOD_CONTRACT = {
  version: 1,
  /** JSON path under institution config */
  storagePath: 'institutionConfig.preparationPeriod',
  fields: {
    start: { type: 'date', required: true, label: 'Start Date' },
    end: { type: 'date', required: true, label: 'End Date' },
    reviewerAvailableFrom: { type: 'date', required: false, label: 'Reviewer Available From' },
  },
  statusValues: ['Upcoming', 'Open', 'Closed'],
  timeZone: EVALUATION_PERIOD_TIMEZONE,
};

/** Calendar YYYY-MM-DD in the configured institution timezone. */
export function calendarDateInTimeZone(date = new Date(), timeZone = EVALUATION_PERIOD_TIMEZONE) {
  try {
    return new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(date);
  } catch {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}

export function parsePeriodDate(iso) {
  if (!iso) return null;
  const day = String(iso).slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  // Noon Manila avoids DST edge cases for date-only fields.
  return new Date(`${day}T12:00:00+08:00`);
}

export function formatEvaluationDate(iso) {
  if (!iso) return '—';
  const d = parsePeriodDate(iso);
  if (!d || Number.isNaN(d.getTime())) return '—';
  try {
    return new Intl.DateTimeFormat('en-PH', {
      timeZone: EVALUATION_PERIOD_TIMEZONE,
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }).format(d);
  } catch {
    return d.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  }
}

export function formatEvaluationDateRange(start, end) {
  if (!start && !end) return '—';
  return `${formatEvaluationDate(start)} – ${formatEvaluationDate(end)}`;
}

/** @param {{ start: string, end: string, reviewerAvailableFrom?: string }} period */
export function computeEvaluationPeriodStatus(period, now = new Date()) {
  const start = period?.start ? String(period.start).slice(0, 10) : '';
  const end = period?.end ? String(period.end).slice(0, 10) : '';
  if (!start || !end) return 'Upcoming';
  const today = calendarDateInTimeZone(now);
  if (today < start) return 'Upcoming';
  if (today > end) return 'Closed';
  return 'Open';
}

export function validateEvaluationPeriodDates({ start, end }) {
  if (!start || !end) return 'Start and end dates are required.';
  const s = String(start).slice(0, 10);
  const e = String(end).slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || !/^\d{4}-\d{2}-\d{2}$/.test(e)) {
    return 'Enter valid start and end dates.';
  }
  if (e < s) return 'End date cannot be before the start date.';
  return null;
}

/**
 * Reviewer start after evaluation end is permitted by the current workflow
 * (client and API only require end ≥ start). Surface it as guidance, not an error.
 */
export function reviewerScheduleNote(period) {
  const end = period?.end ? String(period.end).slice(0, 10) : '';
  const ra = period?.reviewerAvailableFrom ? String(period.reviewerAvailableFrom).slice(0, 10) : '';
  if (!end || !ra) return null;
  if (ra > end) {
    return `Reviewers can start after the evaluation period ends (${formatEvaluationDate(ra)}). Checking of submitted evidence begins then.`;
  }
  return null;
}

/** @param {{ start: string, end: string, reviewerAvailableFrom?: string }} period */
export function reviewerAvailabilityDetail(period, now = new Date()) {
  const ra = period?.reviewerAvailableFrom ? String(period.reviewerAvailableFrom).slice(0, 10) : '';
  if (!ra) {
    return {
      available: false,
      configured: false,
      statusLabel: 'Not configured',
      shortLabel: 'Not configured',
      scheduleLine: 'Reviewer access is not configured.',
      startDateLabel: null,
    };
  }
  const today = calendarDateInTimeZone(now);
  const available = today >= ra;
  const readable = formatEvaluationDate(ra);
  return {
    available,
    configured: true,
    statusLabel: available ? 'Available now' : 'Not yet open',
    shortLabel: available ? `Available now · from ${readable}` : `Opens ${readable}`,
    scheduleLine: available
      ? `Reviewers may check documents from ${readable}`
      : `Reviewer access opens ${readable}`,
    startDateLabel: readable,
  };
}

export function statusBadgeClass(status) {
  if (status === 'Open') return 'badge-approved';
  if (status === 'Upcoming') return 'badge-pending';
  return 'badge-correction';
}

export function reviewerAccessBadgeClass(detail) {
  if (!detail?.configured) return 'badge-pending';
  return detail.available ? 'badge-approved' : 'badge-pending';
}

/**
 * Reviewer submit window: max(start, reviewerAvailableFrom) … end (inclusive, Manila calendar days).
 * @returns {{ allowed: boolean, state: string, message: string|null, opensOn: string|null, endsOn: string|null }}
 */
export function computeReviewerReviewWindow(period, now = new Date()) {
  const start = period?.start ? String(period.start).slice(0, 10) : '';
  const end = period?.end ? String(period.end).slice(0, 10) : '';
  const ra = period?.reviewerAvailableFrom ? String(period.reviewerAvailableFrom).slice(0, 10) : '';
  const first = start && end ? (ra ? (ra > start ? ra : start) : start) : null;
  const today = calendarDateInTimeZone(now);
  if (!first || !end) {
    return {
      allowed: false,
      state: 'unconfigured',
      message: 'Evaluation schedule is not configured.',
      opensOn: first,
      endsOn: end || null,
    };
  }
  if (today < first) {
    return {
      allowed: false,
      state: 'upcoming',
      message: `Review opens ${formatEvaluationDate(first)}.`,
      opensOn: first,
      endsOn: end,
    };
  }
  if (today > end) {
    return {
      allowed: false,
      state: 'closed',
      message: 'Review period has ended.',
      opensOn: first,
      endsOn: end,
    };
  }
  return { allowed: true, state: 'open', message: null, opensOn: first, endsOn: end };
}

export function reviewerReviewWindowFromStore(store, now = new Date()) {
  const api = store?.reviewWindow;
  if (api && typeof api.allowed === 'boolean' && api.endsOn) {
    return {
      allowed: api.allowed,
      state: api.state || (api.allowed ? 'open' : 'closed'),
      message: api.message || null,
      opensOn: api.opensOn || null,
      endsOn: api.endsOn || null,
    };
  }
  const period = store?.institutionConfig?.preparationPeriod || {};
  return computeReviewerReviewWindow(period, now);
}

export function evaluationPeriodCardHtml(period, { compact = false } = {}) {
  const status = computeEvaluationPeriodStatus(period);
  const rev = reviewerAvailabilityDetail(period);
  const range = formatEvaluationDateRange(period.start, period.end);

  return `
    <div class="card fl-eval-period-card${compact ? ' fl-eval-period-card--compact' : ''}" aria-labelledby="eval-period-heading">
      <div class="fl-eval-period-card__head">
        <h3 id="eval-period-heading" style="margin:0">Evaluation Period</h3>
        <span class="badge-status ${statusBadgeClass(status)}" aria-label="Status: ${status}">${status}</span>
      </div>
      <dl class="fl-eval-period-dl">
        <div><dt>Start</dt><dd>${formatEvaluationDate(period.start)}</dd></div>
        <div><dt>End</dt><dd>${formatEvaluationDate(period.end)}</dd></div>
        <div><dt>Date range</dt><dd>${range}</dd></div>
        <div><dt>Reviewer availability</dt><dd>${rev.shortLabel}</dd></div>
      </dl>
    </div>`;
}
