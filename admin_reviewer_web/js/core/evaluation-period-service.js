/**
 * Shared evaluation period contract (Admin, Reviewer, Faculty, future API).
 * Stored at `institutionConfig.preparationPeriod` in the demo (name kept for backward-compatible JSON).
 */

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
};

export function parsePeriodDate(iso) {
  if (!iso) return null;
  return new Date(`${iso}T12:00:00`);
}

export function formatEvaluationDate(iso) {
  if (!iso) return '—';
  const d = parsePeriodDate(iso);
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
}

/** @param {{ start: string, end: string, reviewerAvailableFrom?: string }} period */
export function computeEvaluationPeriodStatus(period, now = new Date()) {
  const s = parsePeriodDate(period?.start);
  const e = parsePeriodDate(period?.end);
  if (!s || !e) return 'Upcoming';
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startDay = new Date(s.getFullYear(), s.getMonth(), s.getDate());
  const endDay = new Date(e.getFullYear(), e.getMonth(), e.getDate());
  if (today < startDay) return 'Upcoming';
  if (today > endDay) return 'Closed';
  return 'Open';
}

export function validateEvaluationPeriodDates({ start, end }) {
  if (!start || !end) return 'Start and end dates are required.';
  const s = parsePeriodDate(start);
  const e = parsePeriodDate(end);
  if (e < s) return 'End date cannot be before the start date.';
  return null;
}

/** @param {{ start: string, end: string, reviewerAvailableFrom?: string }} period */
export function reviewerAvailabilityDetail(period, now = new Date()) {
  const ra = period?.reviewerAvailableFrom;
  if (!ra) {
    return { available: false, shortLabel: 'Not configured', scheduleLine: 'Not configured' };
  }
  const from = parsePeriodDate(ra);
  const available = now >= from;
  const readable = formatEvaluationDate(ra);
  return {
    available,
    shortLabel: available ? `From ${readable}` : `Opens ${readable}`,
    scheduleLine: available
      ? `Reviewers may check documents from ${readable}`
      : `Reviewer queue opens ${readable}`,
  };
}

export function statusBadgeClass(status) {
  if (status === 'Open') return 'badge-approved';
  if (status === 'Upcoming') return 'badge-pending';
  return 'badge-correction';
}

export function evaluationPeriodCardHtml(period, { compact = false } = {}) {
  const status = computeEvaluationPeriodStatus(period);
  const rev = reviewerAvailabilityDetail(period);
  const range = `${formatEvaluationDate(period.start)} – ${formatEvaluationDate(period.end)}`;

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
