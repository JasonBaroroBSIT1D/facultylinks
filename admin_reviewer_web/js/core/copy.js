/** Plain-language labels shared across Admin / Reviewer UI */

export const DOC_STATUS = {
  pending: { label: 'Waiting for review', badge: 'badge-pending' },
  evidence: { label: 'Supporting evidence', badge: 'badge-muted' },
  approved: { label: 'Approved', badge: 'badge-approved' },
  rejected: { label: 'Not accepted', badge: 'badge-rejected' },
  correction_requested: { label: 'Needs changes', badge: 'badge-correction' },
  active: { label: 'Active', badge: 'badge-approved' },
  inactive: { label: 'Inactive', badge: 'badge-pending' },
};

export function statusBadgeHtml(status) {
  const d = DOC_STATUS[status] || { label: status, badge: 'badge-pending' };
  return `<span class="badge-status ${d.badge}" aria-label="Status: ${d.label}">${d.label}</span>`;
}

export function pageIntro(html) {
  return `<p class="page-intro" role="doc-subtitle">${html}</p>`;
}

export const SCREEN_INTRO = {
  dashboardAdmin: 'See how many faculty and documents need attention today.',
  dashboardReviewer: 'See the faculty assigned to you and what needs your review.',
  faculty: 'Add or update faculty records and assign a reviewer.',
  reviewers: 'Manage who can review faculty documents.',
  config: 'Set scoring rules and point values. Changes are saved as a draft until you publish.',
  simulationCfg: 'Set the official evaluation period and when reviewers may begin checking documents.',
  reports: 'Generate a detailed report of faculty evidence, reviewer feedback, and assessment progress.',
  activity: 'Recent actions in this demonstration system.',
  assigned: 'Choose a faculty member to check their documents.',
  workspace: 'Open documents by assessment area. Faculty scores stay tied to the rules version they started with.',
  review: 'Check this document. OCR text is for help only—you decide approve or needs changes.',
  rules: 'Read the active scoring rules. Reviewers cannot edit these.',
  notifications: 'Messages about document reviews and feedback.',
};
