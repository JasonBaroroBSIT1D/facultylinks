/**
 * Admin Faculty Assessment and Evidence Report — loads independently from backend snapshot.
 */
import { SCREEN_INTRO, pageIntro } from '../core/copy.js';

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

function fmtScore(scoreObj) {
  if (!scoreObj || scoreObj.available === false || scoreObj.value == null) {
    return `<span class="rep-unavailable">Unavailable</span>`;
  }
  return esc(Number(scoreObj.value).toFixed(2));
}

function fmtNum(n) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toFixed(2);
}

function fmtDate(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return esc(iso);
  }
}

function kraRowsHtml(summary, order) {
  const byKra = summary?.byKra || {};
  return (order || Object.keys(byKra))
    .map((id) => {
      const k = byKra[id];
      if (!k) {
        return `<tr><td>${esc(id)}</td><td colspan="4" class="muted">No data</td></tr>`;
      }
      const note = k.criterionAUnavailable
        ? `<div class="muted rep-note">${esc(k.availabilityNote || 'Calculation unavailable')}</div>`
        : k.kraCapPolicyUnresolved
          ? `<div class="muted rep-note">${esc(k.kraCapPolicyNote || 'Unresolved KRA cap policy')}</div>`
          : '';
      return `<tr>
        <td>${esc(k.name || id)}</td>
        <td class="rep-num">${fmtScore(k.rawScore)}</td>
        <td class="rep-num">${k.weight != null ? Number(k.weight).toFixed(2) : '—'}</td>
        <td class="rep-num">${fmtScore(k.weightedScore)}</td>
        <td>${note}</td>
      </tr>`;
    })
    .join('');
}

function achievementTreeHtml(tree) {
  if (!tree?.length) return '<p class="muted">No achievements on record.</p>';
  return tree
    .map((kra) => {
      if (!kra.criteria?.length) {
        return `<section class="rep-block"><h4>${esc(kra.kraName)}</h4><p class="muted">No achievements in this KRA.</p></section>`;
      }
      const critHtml = kra.criteria
        .map((crit) => {
          const indHtml = (crit.indicators || [])
            .map((ind) => {
              const rows = (ind.achievements || [])
                .map((a) => {
                  const docs = (a.linkedDocuments || [])
                    .map(
                      (d) =>
                        `<li><a class="rep-app-link" href="${esc(d.appPath)}">${esc(d.fileName)}</a> <span class="muted">(${esc(d.reviewStatus || '—')})</span></li>`
                    )
                    .join('');
                  return `<article class="rep-ach" id="ach-${esc(a.id)}">
                    <h6>${esc(a.title || 'Untitled')}</h6>
                    <dl class="rep-dl">
                      <div><dt>Indicator</dt><dd>${esc(ind.indicatorName || a.indicatorId)}</dd></div>
                      <div><dt>Submitted</dt><dd>${fmtDate(a.submittedAt)}</dd></div>
                      <div><dt>Status</dt><dd>${esc(a.submissionStatus || '—')} / ${esc(a.reviewStatus || 'pending')}</dd></div>
                      <div><dt>Claimed points</dt><dd>${a.claimedPoints != null ? fmtNum(a.claimedPoints) : '—'}</dd></div>
                      <div><dt>Reviewer-verified points</dt><dd>${a.reviewerVerifiedPoints != null ? fmtNum(a.reviewerVerifiedPoints) : '—'}</dd></div>
                      <div><dt>Reviewer</dt><dd>${esc(a.reviewerName || '—')}</dd></div>
                      <div><dt>Decision date</dt><dd>${fmtDate(a.reviewedAt)}</dd></div>
                      <div><dt>Remarks</dt><dd class="rep-wrap">${esc(a.reviewRemarks || '—')}</dd></div>
                      <div><dt>Score-change reason</dt><dd class="rep-wrap">${esc(a.scoreChangeReason || '—')}</dd></div>
                    </dl>
                    ${docs ? `<div class="rep-linked"><strong>Supporting documents</strong><ul>${docs}</ul></div>` : '<p class="muted">No linked documents.</p>'}
                  </article>`;
                })
                .join('');
              return `<div class="rep-indicator"><h5>${esc(ind.indicatorName || ind.indicatorId)}</h5>${rows || '<p class="muted">No achievements.</p>'}</div>`;
            })
            .join('');
          return `<div class="rep-criterion"><h4>${esc(crit.criterionName || crit.criterionId)}</h4>${indHtml}</div>`;
        })
        .join('');
      return `<section class="rep-block"><h3>${esc(kra.kraName)}</h3>${critHtml}</section>`;
    })
    .join('');
}

function criterionAHtml(ca) {
  if (!ca) return '<p class="muted">No Criterion A data.</p>';
  const est = ca.estimated;
  const ver = ca.verified;
  const semRows = (ca.semesters || [])
    .map(
      (s) => `<tr>
      <td>${esc(s.academicYear || '—')}</td>
      <td>${esc(s.semester || '—')}</td>
      <td class="rep-num">${s.setRatingExtracted != null ? fmtNum(s.setRatingExtracted) : '—'}</td>
      <td class="rep-num">${s.sefRatingExtracted != null ? fmtNum(s.sefRatingExtracted) : '—'}</td>
      <td>${esc(s.setVerificationStatus || 'pending')}${s.setRatingConfirmed != null ? ` (confirmed ${fmtNum(s.setRatingConfirmed)})` : ''}</td>
      <td>${esc(s.sefVerificationStatus || 'pending')}${s.sefRatingConfirmed != null ? ` (confirmed ${fmtNum(s.sefRatingConfirmed)})` : ''}</td>
    </tr>`
    )
    .join('');
  const block = (label, scoring) => {
    if (!scoring) return `<p><strong>${label}:</strong> —</p>`;
    if (scoring.calculationUnavailable) {
      return `<p><strong>${label}:</strong> <span class="rep-unavailable">Unavailable</span> <span class="muted">${esc(scoring.incompleteReason || '')}</span></p>`;
    }
    return `<p><strong>${label}:</strong> ${scoring.criterionAPoints != null ? fmtNum(scoring.criterionAPoints) : scoring.partialSubtotal != null ? `Partial ${fmtNum(scoring.partialSubtotal)}` : '—'}
      · SET ${scoring.setPoints != null ? fmtNum(scoring.setPoints) : '—'} · SEF ${scoring.sefPoints != null ? fmtNum(scoring.sefPoints) : '—'}
      · ${esc(scoring.coverageSummary || scoring.availabilitySummary || '')}
      · Policy: ${esc(scoring.calculationPolicy || ca.policy || '—')}</p>`;
  };
  return `
    ${block('Estimated', est)}
    ${block('Reviewer-verified', ver)}
    <p class="muted">Under average_available_max_six, missing semesters are coverage information and do not by themselves block calculation.</p>
    <div class="table-wrap rep-table-wrap"><table class="rep-table">
      <thead><tr><th>Academic year</th><th>Semester</th><th>SET extracted</th><th>SEF extracted</th><th>SET verification</th><th>SEF verification</th></tr></thead>
      <tbody>${semRows || '<tr><td colspan="6" class="muted">No semester rows.</td></tr>'}</tbody>
    </table></div>`;
}

function evidenceHtml(rows) {
  if (!rows?.length) return '<p class="muted">No uploaded documents.</p>';
  return `<div class="table-wrap rep-table-wrap"><table class="rep-table">
    <thead><tr><th>Filename</th><th>KRA / indicator</th><th>Linked achievement</th><th>Uploaded</th><th>Display status</th><th>OCR / processing</th></tr></thead>
    <tbody>${rows
      .map((d) => {
        const parents = (d.parentAchievements || [])
          .map((p) => `<a class="rep-app-link" href="#ach-${esc(p.achievementId)}">${esc(p.title)}</a>`)
          .join('<br/>') || '—';
        return `<tr id="doc-${esc(d.id)}">
          <td class="rep-wrap"><a class="rep-app-link" href="${esc(d.appPath)}">${esc(d.fileName)}</a><div class="muted" style="font-size:0.75rem">${esc(d.id)}</div></td>
          <td>${esc(d.kraName || d.kraId || '—')}<div class="muted">${esc(d.indicatorName || d.indicatorId || '')}</div></td>
          <td>${parents}</td>
          <td>${fmtDate(d.uploadedAt)}</td>
          <td>${esc(d.displayStatus || d.reviewStatus)}</td>
          <td>${esc(d.ocrStatus || '—')} / ${esc(d.processingStatus || '—')}</td>
        </tr>`;
      })
      .join('')}</tbody>
  </table></div>`;
}

function outstandingHtml(items) {
  if (!items?.length) return '<p class="muted">No outstanding reviewer actions recorded.</p>';
  return `<ul class="rep-actions">${items
    .map((it) => {
      const href =
        it.targetType === 'achievement' && it.targetId
          ? `#ach-${esc(it.targetId)}`
          : it.targetType === 'document' && it.targetId
            ? `#doc-${esc(it.targetId)}`
            : null;
      const title = href
        ? `<a class="rep-app-link" href="${href}">${esc(it.title)}</a>`
        : esc(it.title);
      return `<li><strong>${esc(it.kind.replace(/_/g, ' '))}</strong> — ${title}: <span class="rep-wrap">${esc(it.detail)}</span></li>`;
    })
    .join('')}</ul>`;
}

function rankSimHtml(sim) {
  if (!sim) return '<p class="muted">Rank simulation not available.</p>';
  const potLabel = (pot) => {
    if (pot == null || pot === '') return '—';
    if (typeof pot === 'string') return pot;
    return pot.label || pot.name || pot.rank || '—';
  };
  const bucket = (label, b) => {
    if (!b) return `<p><strong>${label}:</strong> —</p>`;
    if (b.configured === false) {
      return `<div class="rep-rank-bucket"><h4>${esc(label)}</h4><p class="rep-unavailable">${esc(b.reason || 'Unavailable')}</p></div>`;
    }
    const br = b.subRankBracket || {};
    const inc =
      br.subRankIncrements != null
        ? br.subRankIncrements
        : br.provisionalIncrements != null
          ? `${br.provisionalIncrements} (provisional)`
          : '—';
    const quals = (b.conditionalRankProjections || br.conditionalProjections || [])
      .map(
        (c) =>
          `<li>${esc(c.policyLabel || c.policyKey || 'Policy')}: ${esc(c.bracketLabel || '')} → potential ${esc(potLabel(c.potentialRank))} (${esc(String(c.subRankIncrements ?? '—'))} sub-rank)</li>`
      )
      .join('');
    const unresolved = br.unresolvedReason
      ? `<p class="muted rep-wrap">${esc(br.unresolvedReason)}</p>`
      : '';
    return `<div class="rep-rank-bucket">
      <h4>${esc(label)}</h4>
      <dl class="rep-dl">
        <div><dt>Current rank</dt><dd>${esc(b.currentRank || sim.currentRank || '—')}</dd></div>
        <div><dt>Weighted score</dt><dd>${b.overallWeightedScore != null ? fmtNum(b.overallWeightedScore) : '—'}</dd></div>
        <div><dt>Sub-rank increment</dt><dd>${esc(String(inc))}</dd></div>
        <div><dt>Bracket</dt><dd class="rep-wrap">${esc(br.label || '—')}</dd></div>
        <div><dt>Named potential rank</dt><dd>${esc(potLabel(b.potentialRank))}</dd></div>
        <div><dt>Notes</dt><dd class="rep-wrap">${esc((b.notes || []).join(' ') || 'Preparation only — not an official promotion.')}</dd></div>
      </dl>
      ${unresolved}
      ${quals ? `<p><strong>Conditional policy qualifications</strong></p><ul>${quals}</ul>` : ''}
    </div>`;
  };
  return `${bucket('Estimated projection', sim.estimated)}${bucket('Reviewer-verified projection', sim.verified)}
    <p class="muted">Projections use existing authoritative simulation rules. They are not an official promotion decision.</p>`;
}

export function renderReportDocument(report) {
  if (!report) return '<p class="muted">No report snapshot.</p>';
  const ex = report.executiveSummary || {};
  const kra = report.kraScoreSummary || {};
  const fac = report.faculty || {};
  const rev = report.reviewers || {};
  const sv = report.scoringVersion || {};
  const period = report.assessmentPeriod || {};
  const decisionDiff =
    rev.decisionMakers?.length &&
    (!rev.assigned || rev.decisionMakers.some((d) => d.id !== rev.assigned?.id))
      ? rev.decisionMakers.map((d) => esc(d.name || d.email)).join(', ')
      : null;

  return `<article class="rep-doc" data-report-id="${esc(report.reportId)}">
    <header class="rep-header">
      <div class="rep-brand">${esc(report.brand || 'FacultyLink')}</div>
      <h1>${esc(report.title)}</h1>
      <p class="rep-meta">Report ID: <strong>${esc(report.reportId)}</strong> · Generated ${fmtDate(report.generatedAt)}</p>
      <p class="rep-meta">Assessment period: <strong>${esc(period.label || '—')}</strong>
        ${period.start || period.end ? `(${esc(period.start || '—')} → ${esc(period.end || '—')})` : ''}</p>
      <p class="rep-meta">Scoring version: <strong>${esc(sv.versionLabel || '—')}</strong>
        ${sv.pinned ? '(pinned)' : '(active published)'} · Policy: ${esc(sv.criterionAPolicy || '—')}</p>
      <p class="rep-meta">Prepared by: <strong>${esc(report.preparedBy?.name || report.preparedBy?.email || '—')}</strong></p>
      <p class="rep-notice">${esc(report.preparationNotice)}</p>
    </header>

    <section class="rep-section" aria-labelledby="repFacHeading">
      <h2 id="repFacHeading">Faculty and reviewer details</h2>
      <dl class="rep-dl">
        <div><dt>Faculty</dt><dd>${esc(fac.name)}</dd></div>
        <div><dt>Department</dt><dd>${esc(fac.departmentDisplay || 'Unavailable')}</dd></div>
        <div><dt>Current rank</dt><dd>${esc(fac.rankDisplay || 'Unavailable')}</dd></div>
        <div><dt>Assigned reviewer</dt><dd>${esc(rev.assigned?.name || 'Unavailable')}</dd></div>
        <div><dt>Decision reviewers</dt><dd>${decisionDiff || esc(rev.assigned?.name || '—')}</dd></div>
        <div><dt>Latest update</dt><dd>${fmtDate(report.progress?.latestUpdateAt)}</dd></div>
      </dl>
    </section>

    <section class="rep-section" aria-labelledby="repExecHeading">
      <h2 id="repExecHeading">Executive summary</h2>
      <p class="muted">${esc(report.progress?.countingNote || '')}</p>
      <ul class="rep-stats">
        <li>Uploaded documents (unique IDs): <strong>${esc(ex.uploadedDocuments ?? 0)}</strong></li>
        <li>Submitted achievements: <strong>${esc(ex.submittedAchievements ?? 0)}</strong></li>
        <li>Approved: <strong>${esc(ex.approvedAchievements ?? 0)}</strong> · Pending: <strong>${esc(ex.pendingAchievements ?? 0)}</strong> · Needs changes: <strong>${esc(ex.needsChangesAchievements ?? 0)}</strong> · Rejected: <strong>${esc(ex.rejectedAchievements ?? 0)}</strong></li>
        <li>Drafts: <strong>${esc(ex.draftAchievements ?? 0)}</strong> · Unlinked evidence: <strong>${esc(ex.unlinkedEvidence ?? 0)}</strong></li>
        <li>Estimated overall weighted: <strong>${fmtScore(ex.estimatedOverall)}</strong></li>
        <li>Reviewer-verified overall weighted: <strong>${fmtScore(ex.verifiedOverall)}</strong></li>
      </ul>
      ${(ex.remainingWork || []).length ? `<p><strong>Remaining work:</strong> ${esc(ex.remainingWork.join(' '))}</p>` : '<p class="muted">No remaining work items flagged.</p>'}
    </section>

    <section class="rep-section" aria-labelledby="repKraHeading">
      <h2 id="repKraHeading">KRA score summary</h2>
      <p class="muted">${esc(kra.rawVsWeighted || '')}</p>
      <p class="muted">${esc(kra.weightBasis || '')}</p>
      <h3>Estimated</h3>
      <div class="table-wrap rep-table-wrap"><table class="rep-table">
        <thead><tr><th>KRA</th><th>Raw points</th><th>Weight</th><th>Weighted contribution</th><th>Notes</th></tr></thead>
        <tbody>${kraRowsHtml(kra.estimated, kra.kraOrder)}</tbody>
        <tfoot><tr><th colspan="3">Overall weighted total</th><th class="rep-num">${fmtScore(kra.estimated?.overallWeighted)}</th><th></th></tr></tfoot>
      </table></div>
      <h3>Reviewer-verified</h3>
      <div class="table-wrap rep-table-wrap"><table class="rep-table">
        <thead><tr><th>KRA</th><th>Raw points</th><th>Weight</th><th>Weighted contribution</th><th>Notes</th></tr></thead>
        <tbody>${kraRowsHtml(kra.verified, kra.kraOrder)}</tbody>
        <tfoot><tr><th colspan="3">Overall weighted total</th><th class="rep-num">${fmtScore(kra.verified?.overallWeighted)}</th><th></th></tr></tfoot>
      </table></div>
      ${(kra.estimated?.notes || []).concat(kra.verified?.notes || []).length
        ? `<ul class="muted">${[...new Set([...(kra.estimated?.notes || []), ...(kra.verified?.notes || [])])].map((n) => `<li>${esc(n)}</li>`).join('')}</ul>`
        : ''}
    </section>

    <section class="rep-section" aria-labelledby="repCaHeading">
      <h2 id="repCaHeading">KRA I Criterion A — SET / SEF</h2>
      ${criterionAHtml(report.criterionA)}
    </section>

    <section class="rep-section" aria-labelledby="repAchHeading">
      <h2 id="repAchHeading">Criterion and achievement details</h2>
      ${achievementTreeHtml(report.achievementTree)}
    </section>

    <section class="rep-section" aria-labelledby="repEvHeading">
      <h2 id="repEvHeading">Evidence register</h2>
      ${evidenceHtml(report.evidenceRegister)}
    </section>

    <section class="rep-section" aria-labelledby="repOutHeading">
      <h2 id="repOutHeading">Reviewer feedback and outstanding actions</h2>
      ${outstandingHtml(report.outstandingActions)}
    </section>

    <section class="rep-section" aria-labelledby="repRankHeading">
      <h2 id="repRankHeading">Rank simulation (preparation only)</h2>
      ${rankSimHtml(report.rankSimulation)}
    </section>

    <footer class="rep-footer">
      <span>${esc(report.brand)} · ${esc(report.reportId)}</span>
      <span class="rep-footer-page"></span>
    </footer>
  </article>`;
}

export function renderReportsPage(root, titleEl, { store, PortalApi, bootstrapPortal }) {
  titleEl.textContent = 'Reports';
  let faculty = [...(store.faculty || [])].sort((a, b) =>
    `${a.lastName || ''} ${a.firstName || ''}`.localeCompare(`${b.lastName || ''} ${b.firstName || ''}`)
  );
  const institution = store.institutionConfig || {};
  const prep = institution.preparationPeriod || {};
  const periodDefault =
    prep.start || prep.end ? `${prep.start || '—'} → ${prep.end || '—'}` : 'Current institution evaluation period';

  let snapshot = null;
  let loading = false;
  let lastError = null;

  root.innerHTML = `
    ${pageIntro('Generate a detailed report of faculty evidence, reviewer feedback, and assessment progress.')}
    <div class="rep-controls no-print">
      <label class="rep-field">
        <span>Faculty</span>
        <input type="search" id="repFacSearch" placeholder="Search faculty…" autocomplete="off" />
        <select id="repFac" size="8" class="rep-fac-select">
          ${
            faculty.length
              ? faculty
                  .map(
                    (f) =>
                      `<option value="${esc(f.id)}">${esc(f.lastName || '')}, ${esc(f.firstName || '')}${f.department ? ` — ${esc(f.department)}` : ''}</option>`
                  )
                  .join('')
              : '<option value="" disabled>Loading faculty list…</option>'
          }
        </select>
      </label>
      <label class="rep-field">
        <span>Assessment / evaluation period</span>
        <select id="repPeriod">
          <option value="${esc(periodDefault)}">${esc(periodDefault)}</option>
        </select>
      </label>
      <div class="rep-actions-bar">
        <button type="button" class="btn-primary-sm btn-sm" id="repGenerate">Generate report</button>
        <button type="button" class="btn-ghost btn-sm" id="repPrint" disabled>Print preview</button>
        <button type="button" class="btn-ghost btn-sm" id="repPdf" disabled>Download PDF</button>
      </div>
      <p id="repStatus" class="muted" role="status" aria-live="polite"></p>
    </div>
    <div id="repOut" class="rep-out" aria-live="polite"></div>
  `;

  const facSelect = root.querySelector('#repFac');
  const facSearch = root.querySelector('#repFacSearch');
  const periodSelect = root.querySelector('#repPeriod');
  const statusEl = root.querySelector('#repStatus');
  const out = root.querySelector('#repOut');
  const btnGen = root.querySelector('#repGenerate');
  const btnPrint = root.querySelector('#repPrint');
  const btnPdf = root.querySelector('#repPdf');

  if (facSelect.options.length && facSelect.value) facSelect.selectedIndex = 0;

  facSearch.addEventListener('input', () => {
    const q = facSearch.value.trim().toLowerCase();
    [...facSelect.options].forEach((opt) => {
      opt.hidden = q ? !opt.textContent.toLowerCase().includes(q) : false;
    });
  });

  const setExportEnabled = (on) => {
    btnPrint.disabled = !on;
    btnPdf.disabled = !on;
  };

  const showState = (html) => {
    out.innerHTML = html;
  };

  const fillFacultyOptions = (list) => {
    faculty = [...(list || [])].sort((a, b) =>
      `${a.lastName || ''} ${a.firstName || ''}`.localeCompare(`${b.lastName || ''} ${b.firstName || ''}`)
    );
    facSelect.innerHTML = faculty.length
      ? faculty
          .map(
            (f) =>
              `<option value="${esc(f.id)}">${esc(f.lastName || '')}, ${esc(f.firstName || '')}${f.department ? ` — ${esc(f.department)}` : ''}</option>`
          )
          .join('')
      : '<option value="" disabled>No faculty accounts found</option>';
    if (facSelect.options.length && facSelect.value) facSelect.selectedIndex = 0;
  };

  const ensureFacultyDirectory = async () => {
    if (faculty.length) return;
    statusEl.textContent = 'Loading faculty directory…';
    if (typeof bootstrapPortal === 'function') {
      const next = await bootstrapPortal({ full: true, force: true });
      fillFacultyOptions(next?.faculty || []);
    }
    if (!faculty.length) {
      throw new Error('Faculty directory is empty. Retry after portal data loads.');
    }
  };

  const generate = async () => {
    const fid = facSelect.value;
    if (!fid) {
      lastError = 'Select a faculty member.';
      statusEl.textContent = lastError;
      setExportEnabled(false);
      showState(`<p class="muted">${esc(lastError)}</p>`);
      return;
    }
    loading = true;
    lastError = null;
    snapshot = null;
    setExportEnabled(false);
    statusEl.textContent = 'Loading authoritative assessment report…';
    showState('<p class="muted">Loading report from the server…</p>');
    btnGen.disabled = true;
    try {
      await ensureFacultyDirectory();
      const selectedId = facSelect.value || fid;
      if (!selectedId) throw new Error('Select a faculty member.');
      const periodLabel = periodSelect.value;
      const data = await PortalApi.fetchFacultyAssessmentReport(selectedId, { periodLabel });
      snapshot = data.report;
      if (!snapshot) throw new Error('Report payload missing.');
      statusEl.textContent = `Report ${snapshot.reportId} ready.`;
      showState(renderReportDocument(snapshot));
      setExportEnabled(true);
    } catch (e) {
      lastError = e.message || 'Could not load report.';
      statusEl.textContent = lastError;
      setExportEnabled(false);
      showState(`<div class="rep-error"><p>${esc(lastError)}</p>
        <button type="button" class="btn-primary-sm btn-sm" id="repRetry">Retry</button></div>`);
      root.querySelector('#repRetry')?.addEventListener('click', () => void generate());
    } finally {
      loading = false;
      btnGen.disabled = false;
    }
  };

  if (!faculty.length) {
    void (async () => {
      try {
        await ensureFacultyDirectory();
        statusEl.textContent = faculty.length
          ? 'Select a faculty member and generate a report.'
          : 'No faculty accounts found.';
      } catch (e) {
        statusEl.textContent = e.message || 'Could not load faculty directory.';
        showState(`<div class="rep-error"><p>${esc(statusEl.textContent)}</p>
          <button type="button" class="btn-primary-sm btn-sm" id="repRetryDir">Retry</button></div>`);
        root.querySelector('#repRetryDir')?.addEventListener('click', () => void generate());
      }
    })();
  }

  const openPrintSnapshot = () => {
    if (!snapshot || loading || lastError) {
      statusEl.textContent = 'Generate a complete report before printing or exporting.';
      return;
    }
    const html = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
      <title>${esc(snapshot.reportId)} — FacultyLink Report</title>
      <link rel="stylesheet" href="./css/app.css"/>
      <link rel="stylesheet" href="./css/reports.css"/>
      <base href="${esc(window.location.href.replace(/[^/]*$/, ''))}"/>
      </head><body class="rep-print-root" data-report-id="${esc(snapshot.reportId)}">${renderReportDocument(snapshot)}
      <script>window.addEventListener('load',()=>setTimeout(()=>window.print(),250));<\/script>
      </body></html>`;
    const w = window.open('', '_blank');
    if (!w) {
      statusEl.textContent = 'Pop-up blocked. Allow pop-ups to print or save PDF.';
      return;
    }
    w.document.open();
    w.document.write(html);
    w.document.close();
  };

  btnGen.addEventListener('click', () => void generate());
  btnPrint.addEventListener('click', openPrintSnapshot);
  btnPdf.addEventListener('click', () => {
    statusEl.textContent = 'Use the system print dialog → Save as PDF. Values match this snapshot.';
    openPrintSnapshot();
  });
  facSelect.addEventListener('change', () => {
    snapshot = null;
    setExportEnabled(false);
    statusEl.textContent = 'Faculty changed — generate again for a fresh report.';
  });
}
