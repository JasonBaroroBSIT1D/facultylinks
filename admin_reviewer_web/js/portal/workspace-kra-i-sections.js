/**
 * Reviewer workspace — KRA I Criterion A / B / C sections (Check Documents).
 */
import { SUPPORTING_EVIDENCE_INDICATOR_ID } from '../core/assessment-definitions.js';
import { formatCriterionAEstimateHtml } from '../core/criterion-a-display.js';
import { statusBadgeHtml } from '../core/copy.js';
import {
  attachmentReviewStatusHtml,
  collectUnlinkedBcEvidence,
  dedupeDocumentsById,
  enrichPortalDocuments,
  parentLinkForDocument,
  processingStatusNote,
} from './achievement-attachment-display.js';

const SET_SEF_PDF_KINDS = new Set(['set_sef_unified', 'set_sef_combined', 'set_sef_set_only', 'set_sef_sef_only']);
const SET_SEF_PDF_INDICATORS = new Set([
  'kra-I-A-setsef-eval',
  'kra-I-A-setsef-combined',
  'kra-I-A-set-pdf',
  'kra-I-A-sef-pdf',
]);

export const WORKSPACE_CRITERION_ORDER = ['kra-I-A', 'kra-I-B', 'kra-I-C'];
export const WORKSPACE_CRITERION_ORDER_II = ['kra-II-A', 'kra-II-B', 'kra-II-C'];
export const WORKSPACE_CRITERION_ORDER_III = ['kra-III-A', 'kra-III-B', 'kra-III-C', 'kra-III-D'];
export const WORKSPACE_CRITERION_ORDER_IV = ['kra-IV-A', 'kra-IV-B', 'kra-IV-C', 'kra-IV-D'];

const WORKSPACE_CRITERION_HEADINGS = {
  'kra-I-A': { letter: 'A', fallback: 'Teaching Effectiveness' },
  'kra-I-B': { letter: 'B', fallback: 'Instructional Materials Development' },
  'kra-I-C': { letter: 'C', fallback: 'Research Advising and Mentorship Services' },
  'kra-II-A': { letter: 'A', fallback: 'Research Outputs Published' },
  'kra-II-B': { letter: 'B', fallback: 'Inventions' },
  'kra-II-C': { letter: 'C', fallback: 'Creative Works' },
  'kra-III-A': { letter: 'A', fallback: 'Service to the Institution' },
  'kra-III-B': { letter: 'B', fallback: 'Service to the Community' },
  'kra-III-C': { letter: 'C', fallback: 'Relevance and Quality of Extension Services' },
  'kra-III-D': { letter: 'D', fallback: 'Bonus — Administrative Designations' },
  'kra-IV-A': { letter: 'A', fallback: 'Involvement in Professional Organizations' },
  'kra-IV-B': { letter: 'B', fallback: 'Continuing Development' },
  'kra-IV-C': { letter: 'C', fallback: 'Awards and Recognition' },
  'kra-IV-D': { letter: 'D', fallback: 'Additional Points for Newly Appointed Faculty' },
};

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

export function isSetSefTeachingDoc(d) {
  return SET_SEF_PDF_KINDS.has(d.documentKind) || SET_SEF_PDF_INDICATORS.has(d.indicatorId);
}

export function isSpecialStatusTeachingDoc(d) {
  if (!d) return false;
  if (d.indicatorId === SUPPORTING_EVIDENCE_INDICATOR_ID) return true;
  if (d.documentKind === 'special_status_evidence') return true;
  return d.role === 'supporting_evidence';
}

export function isSetSefEvaluationDoc(d) {
  return isSetSefTeachingDoc(d) && !isSpecialStatusTeachingDoc(d);
}

export function kraCriterionFromCatalog(catalog, criterionId) {
  const kraId = criterionId?.startsWith('kra-IV')
    ? 'kra-IV'
    : criterionId?.startsWith('kra-III')
      ? 'kra-III'
      : criterionId?.startsWith('kra-II')
        ? 'kra-II'
        : 'kra-I';
  const kra = catalog?.kras?.find((k) => k.id === kraId);
  return kra?.criteria?.find((c) => c.id === criterionId) || null;
}

export function kraICriterionFromCatalog(catalog, criterionId) {
  return kraCriterionFromCatalog(catalog, criterionId);
}

export function workspaceCriterionHeading(catalog, criterionId) {
  const meta = WORKSPACE_CRITERION_HEADINGS[criterionId];
  if (!meta) return criterionId;
  const crit = kraICriterionFromCatalog(catalog, criterionId);
  let name = meta.fallback;
  if (crit?.name) {
    name = crit.name.replace(/^Criterion\s+[A-C]\s*[–—-]\s*/i, '').trim() || crit.name;
  }
  return `${meta.letter}. ${name}`;
}

export function ocrStatusLabel(s) {
  const map = {
    pending: 'OCR pending',
    queued: 'OCR queued',
    processing: 'OCR processing',
    completed: 'OCR complete',
    failed: 'OCR failed',
    review_required: 'OCR needs review',
  };
  return map[s] || s || '—';
}

function docDateLabel(d) {
  const raw = d.uploadedAt || d.submittedAt || '';
  return raw ? String(raw).slice(0, 10) : '—';
}

function wsDocStatusCell(d, assessments) {
  const link = parentLinkForDocument(d, assessments) || (d.linkedAchievementId
    ? { achievement: { reviewStatus: d.parentReviewStatus, submissionStatus: d.parentSubmissionStatus } }
    : null);
  const reviewPart =
    link || isKraIAttachmentDoc(d)
      ? attachmentReviewStatusHtml(d, link)
      : statusBadgeHtml(d.reviewStatus || 'pending');
  const parts = [reviewPart];
  if (d.ocrStatus) parts.push(`<span class="muted" style="font-size:0.82rem">${esc(ocrStatusLabel(d.ocrStatus))}</span>`);
  parts.push(processingStatusNote(d));
  return parts.join('');
}

function isKraIAttachmentDoc(d) {
  const ind = d?.indicatorId || '';
  return ind.startsWith('kra-I-B') || ind.startsWith('kra-I-C');
}

/**
 * Portal store / API must expose documents as an array.
 * @returns {unknown[]}
 */
export function coercePortalDocumentsList(documents, { context = 'portal store' } = {}) {
  if (documents == null) return [];
  if (Array.isArray(documents)) return documents;
  if (typeof documents === 'object' && Array.isArray(documents.documents)) {
    return documents.documents;
  }
  throw new TypeError(
    `${context}: expected documents array, got ${documents === null ? 'null' : typeof documents}`
  );
}

function wsDocumentTableRows(docs, assessments) {
  if (!docs.length) return '';
  return docs
    .map(
      (d) => `<tr class="ws-doc-row">
        <td class="ws-doc-filename" title="${esc(d.fileName)} · id ${esc(d.id)}">${esc(d.fileName)}</td>
        <td>${wsDocStatusCell(d, assessments)}</td>
        <td>${esc(docDateLabel(d))}</td>
        <td><button type="button" class="btn-ghost btn-sm" data-doc="${esc(d.id)}">Review</button></td>
      </tr>`
    )
    .join('');
}

function wsDocumentBlock(docs, emptyMsg, assessments) {
  if (!Array.isArray(docs)) {
    throw new TypeError(`wsDocumentBlock: docs must be an array, got ${typeof docs}`);
  }
  if (!docs.length) return `<p class="muted ws-doc-empty">${esc(emptyMsg)}</p>`;
  return `<div class="table-wrap ws-doc-table-wrap">
    <table class="ws-doc-table">
      <thead><tr><th>Filename</th><th>Status</th><th>Date</th><th></th></tr></thead>
      <tbody>${wsDocumentTableRows(docs, assessments)}</tbody>
    </table>
  </div>
  <ul class="ws-doc-cards">${docs
    .map(
      (d) => `<li class="ws-doc-card">
        <strong title="${esc(d.fileName)} · id ${esc(d.id)}">${esc(d.fileName)}</strong>
        <span class="muted">${esc(docDateLabel(d))}</span>
        ${wsDocStatusCell(d, assessments)}
        <button type="button" class="btn-ghost btn-sm" data-doc="${esc(d.id)}">Review</button>
      </li>`
    )
    .join('')}</ul>`;
}

/**
 * SET/SEF evaluation docs + Special Status subgroup (Criterion A only).
 */
export function buildCriterionADocumentsHtml(store, facId, catalog) {
  const allDocs = enrichPortalDocuments(store?.documents, store?.assessments);
  const facultyDocs = dedupeDocumentsById(allDocs).filter((d) => d && d.facultyId === facId);
  const setSefDocs = facultyDocs.filter(isSetSefEvaluationDoc).sort((a, b) => (a.uploadedAt || '').localeCompare(b.uploadedAt || ''));
  const specialDocs = facultyDocs.filter(isSpecialStatusTeachingDoc).sort((a, b) => (a.uploadedAt || '').localeCompare(b.uploadedAt || ''));
  const specialInd = kraICriterionFromCatalog(catalog, 'kra-I-A')?.indicators?.find((i) => i.id === SUPPORTING_EVIDENCE_INDICATOR_ID);
  const specialTitle = specialInd?.name || 'For Faculty with Special Status';

  return `
    <div class="ws-criterion-a-docs">
      <h4 class="ws-criterion-subhead">SET/SEF evaluation documents</h4>
      ${wsDocumentBlock(setSefDocs, 'No SET/SEF evaluation uploads yet.', store?.assessments)}
      <h4 class="ws-criterion-subhead ws-criterion-subhead--special">Special Status supporting documents</h4>
      <p class="muted ws-criterion-hint">${esc(specialTitle)} — supporting evidence only; does not change SET/SEF calculations automatically.</p>
      ${wsDocumentBlock(specialDocs, 'No special-status supporting documents uploaded.', store?.assessments)}
    </div>`;
}

export function buildWorkspaceRecoveryHtml(store, facId) {
  const unlinked = collectUnlinkedBcEvidence(store, facId);
  if (!unlinked.length) return '';
  return `<details class="ws-recovery card" id="wsRecoverySection">
    <summary class="ws-recovery__summary">Unlinked files (recovery) — ${unlinked.length}</summary>
    <p class="muted" style="font-size:0.85rem">These B/C evidence uploads are not on a submitted achievement. They stay here until the faculty links and submits them, or you use this list to open a file by id.</p>
    ${wsDocumentBlock(unlinked, 'None', store?.assessments)}
  </details>`;
}

export function formatCriterionAScoresHtml(critA, loadError) {
  if (loadError) {
    return `<p class="muted">${esc(loadError)}</p>`;
  }
  if (!critA) {
    return '<p class="muted">Loading SET/SEF totals…</p>';
  }
  if (critA.message && !critA.scoring) {
    return `<p class="muted">${esc(critA.message)}</p>`;
  }
  const est = critA.scoring?.estimated;
  const ver = critA.scoring?.verified;
  if (!est) return '<p class="muted">No processed SET/SEF data yet.</p>';

  const breakdownInner = (scoring) => {
    if (!scoring || scoring.calculationUnavailable) return '';
    const setP = scoring.setPoints;
    const sefP = scoring.sefPoints;
    if (setP == null && sefP == null) return '';
    return `<ul class="ws-criterion-a-breakdown">
      <li>SET component: <strong>${setP != null ? Number(setP).toFixed(2) : '—'}</strong> / 36</li>
      <li>SEF component: <strong>${sefP != null ? Number(sefP).toFixed(2) : '—'}</strong> / 24</li>
    </ul>`;
  };

  const breakdownBlock = (label, scoring) => {
    const inner = breakdownInner(scoring);
    if (!inner) return '';
    return `<details class="ws-score-breakdown"><summary>${esc(label)} score breakdown</summary>${inner}</details>`;
  };

  const parts = [];
  parts.push('<div class="ws-criterion-a-scores">');
  parts.push('<p class="ws-criterion-a-scoreline"><span class="ws-criterion-a-scorelabel">Estimated</span> ');
  parts.push(formatCriterionAEstimateHtml(est));
  parts.push('</p>');
  parts.push(breakdownBlock('Estimated', est));
  if (ver) {
    parts.push('<p class="ws-criterion-a-scoreline"><span class="ws-criterion-a-scorelabel">Reviewer-verified</span> ');
    parts.push(formatCriterionAEstimateHtml(ver));
    parts.push('</p>');
    parts.push(breakdownBlock('Reviewer-verified', ver));
    if (ver.criterionAPoints === 0 && est.criterionAPoints === 0) {
      parts.push('<p class="muted" style="font-size:0.85rem">Total is 0.00 from calculated ratings (not missing data).</p>');
    }
  }
  parts.push('</div>');
  return parts.join('');
}

export function workspaceKraICriterionCardsShell({ headings }) {
  return `
    <section class="ws-kra-i" aria-labelledby="wsKraIHeading">
      <h2 class="ws-kra-i__title" id="wsKraIHeading">KRA I — Instruction</h2>
      <article class="card ws-criterion-card" id="wsCriterionACard">
        <h3 class="ws-criterion-card__title">${esc(headings['kra-I-A'])}</h3>
        <div id="wsCritAScores" class="ws-criterion-card__body"><p class="muted">Loading SET/SEF totals…</p></div>
        <div id="wsCritADocs" class="ws-criterion-card__body ws-criterion-card__body--docs"></div>
      </article>
      <article class="card ws-criterion-card" id="wsCriterionBCard">
        <h3 class="ws-criterion-card__title">${esc(headings['kra-I-B'])}</h3>
        <div id="wsAchievementsB" class="ws-criterion-card__body"><p class="muted">Loading submitted achievements…</p></div>
      </article>
      <article class="card ws-criterion-card" id="wsCriterionCCard">
        <h3 class="ws-criterion-card__title">${esc(headings['kra-I-C'])}</h3>
        <div id="wsAchievementsC" class="ws-criterion-card__body"><p class="muted">Loading submitted achievements…</p></div>
      </article>
    </section>`;
}
