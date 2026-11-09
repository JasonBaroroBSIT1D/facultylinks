/** Shared Criterion A (SET/SEF) display helpers for admin/reviewer UI. */

function slotLine(scoring) {
  const max = scoring?.maxSemesterSlots ?? scoring?.requiredSlots ?? 6;
  const setN = scoring?.setCount ?? 0;
  const sefN = scoring?.sefCount ?? 0;
  return `SET: ${setN}/${max} available · SEF: ${sefN}/${max} available`;
}

export function formatCriterionAEstimateHtml(scoring) {
  if (!scoring) return '<span class="muted">—</span>';
  const max = scoring.maxima?.criterionA ?? 60;
  const lines = [];
  if (scoring.calculationUnavailable) {
    lines.push(`<span class="doc-score-incomplete">Unavailable</span> <span class="muted">${scoring.incompleteReason || ''}</span>`);
    return lines.join('');
  }
  const pts = scoring.criterionAPoints;
  if (pts != null) {
    lines.push(`<strong>${Number(pts).toFixed(2)}</strong> <span class="muted">/ ${max}</span>`);
  } else if (scoring.partialSubtotal != null) {
    lines.push(
      `<strong>Partial ${Number(scoring.partialSubtotal).toFixed(2)}</strong> <span class="muted">(not a full combined score)</span>`
    );
  } else if (scoring.setPoints != null || scoring.sefPoints != null) {
    const partial = (scoring.setPoints ?? 0) + (scoring.sefPoints ?? 0);
    lines.push(`<strong>Partial ${Number(partial).toFixed(2)}</strong>`);
  } else {
    lines.push('<span class="muted">Not available yet</span>');
  }
  lines.push(`<div class="muted" style="font-size:0.85rem;margin-top:0.25rem">${slotLine(scoring)}</div>`);
  if (scoring.coverageNote) {
    lines.push(`<div class="muted" style="font-size:0.82rem">${scoring.coverageNote}</div>`);
  }
  if (scoring.incomplete && scoring.incompleteReason) {
    lines.push(`<div class="muted" style="font-size:0.82rem">Coverage: ${scoring.incompleteReason}</div>`);
  }
  return lines.join('');
}

export function formatCriterionAWorkspaceBlock(est, ver) {
  if (!est) return '<p class="muted">No processed SET/SEF data yet.</p>';
  const parts = [];
  parts.push(`<p><strong>Estimated:</strong> ${formatCriterionAEstimateHtml(est).replace(/<\/?strong>/g, '')}</p>`);
  if (ver) {
    parts.push(`<p><strong>Reviewer-verified:</strong> ${formatCriterionAEstimateHtml(ver).replace(/<\/?strong>/g, '')}</p>`);
    if (ver.combinedComplete === false && ver.coverageComplete === false) {
      parts.push('<p class="muted" style="font-size:0.85rem">Verified totals may be partial; not a final official evaluation until coverage is complete.</p>');
    }
  }
  return parts.join('');
}
