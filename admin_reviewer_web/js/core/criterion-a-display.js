/** Shared Criterion A (SET/SEF) display helpers for admin/reviewer UI. */

function coverageLine(scoring) {
  if (scoring?.coverageSummary) return `Coverage: ${scoring.coverageSummary}`;
  const slots = scoring?.slotCount ?? 0;
  const max = scoring?.maxSemesterSlots ?? scoring?.requiredSlots ?? 6;
  return `Coverage: ${slots} semesters, maximum ${max}`;
}

function componentLine(scoring) {
  const setPts = scoring?.setPoints;
  const sefPts = scoring?.sefPoints;
  return `SET: ${setPts != null ? Number(setPts).toFixed(2) : '—'} · SEF: ${sefPts != null ? Number(sefPts).toFixed(2) : '—'}`;
}

function pendingVerificationLine(scoring) {
  if (!scoring) return '';
  if (scoring.calculationUnavailable) {
    const pending =
      scoring.pendingVerificationNote ||
      scoring.incompleteReason ||
      'Reviewer confirmation still pending for eligible ratings.';
    return pending;
  }
  return '';
}

export function formatCriterionAEstimateHtml(scoring) {
  if (!scoring) return '<span class="muted">—</span>';
  const max = scoring.maxima?.criterionA ?? 60;
  const lines = [];
  const policy = scoring.calculationPolicy || '';
  const flexible = policy === 'average_available_max_six';

  if (scoring.calculationUnavailable) {
    lines.push(
      `<span class="doc-score-incomplete">Unavailable</span> <span class="muted">${
        pendingVerificationLine(scoring) || scoring.incompleteReason || ''
      }</span>`
    );
    lines.push(`<div class="muted" style="font-size:0.85rem;margin-top:0.25rem">${coverageLine(scoring)}</div>`);
    return lines.join('');
  }

  const pts = scoring.criterionAPoints;
  if (pts != null) {
    lines.push(`<strong>${Number(pts).toFixed(2)}</strong> <span class="muted">/ ${max}</span>`);
  } else if (scoring.partialSubtotal != null) {
    lines.push(
      `<strong>Partial ${Number(scoring.partialSubtotal).toFixed(2)}</strong> <span class="muted">(component subtotal only)</span>`
    );
  } else {
    lines.push('<span class="muted">Not available yet</span>');
  }

  lines.push(`<div class="muted" style="font-size:0.85rem;margin-top:0.25rem">${componentLine(scoring)}</div>`);
  lines.push(`<div class="muted" style="font-size:0.82rem">${coverageLine(scoring)}</div>`);

  if (!flexible && scoring.incomplete && scoring.incompleteReason) {
    lines.push(`<div class="muted" style="font-size:0.82rem">${scoring.incompleteReason}</div>`);
  } else if (flexible && scoring.incomplete && scoring.coverageNote == null) {
    // coverage line already shown; avoid duplicate availability chatter
  }
  return lines.join('');
}

export function formatCriterionAVerifiedHtml(scoring, { pendingCounts } = {}) {
  if (!scoring) return '<span class="muted">—</span>';
  if (scoring.calculationUnavailable) {
    const setN = pendingCounts?.setVerified ?? scoring.setCount ?? 0;
    const sefN = pendingCounts?.sefVerified ?? scoring.sefCount ?? 0;
    const total = pendingCounts?.total;
    const pendingMsg =
      total != null
        ? `Pending reviewer confirmation (${setN}/${total} SET · ${sefN}/${total} SEF verified with confirmed ratings).`
        : scoring.incompleteReason || 'Pending reviewer confirmation of extracted ratings.';
    return `<span class="doc-score-incomplete">Pending verification</span> <span class="muted">${pendingMsg}</span>`;
  }
  return formatCriterionAEstimateHtml(scoring);
}

export function formatCriterionAWorkspaceBlock(est, ver) {
  if (!est) return '<p class="muted">No processed SET/SEF data yet.</p>';
  const parts = [];
  parts.push(`<p><strong>Estimated:</strong> ${formatCriterionAEstimateHtml(est).replace(/<\/?strong>/g, '')}</p>`);
  if (ver) {
    parts.push(`<p><strong>Reviewer-verified:</strong> ${formatCriterionAVerifiedHtml(ver).replace(/<\/?strong>/g, '')}</p>`);
  }
  return parts.join('');
}
