/**
 * Achievement-linked evidence: display status derived from parent achievement (not per-file approval).
 */
import { statusBadgeHtml } from '../core/copy.js';
function asDocumentsArray(documents, context = 'portal documents') {
  if (documents == null) return [];
  if (Array.isArray(documents)) return documents;
  if (typeof documents === 'object' && Array.isArray(documents.documents)) return documents.documents;
  throw new TypeError(`${context}: expected documents array, got ${typeof documents}`);
}

export function isKraIAchievementIndicator(indicatorId) {
  if (!indicatorId) return false;
  if (indicatorId.startsWith('kra-I-B') || indicatorId.startsWith('kra-I-C')) return true;
  return (
    indicatorId.startsWith('kra-II-') ||
    indicatorId.startsWith('kra-III-') ||
    indicatorId.startsWith('kra-IV-')
  );
}

export function dedupeDocumentsById(documents) {
  const seen = new Set();
  const out = [];
  for (const d of documents || []) {
    if (!d?.id || seen.has(d.id)) continue;
    seen.add(d.id);
    out.push(d);
  }
  return out;
}

/** @returns {Map<string, { achievement: object, facultyId: string }>} */
export function buildDocumentAchievementIndex(assessments) {
  const index = new Map();
  if (!assessments || typeof assessments !== 'object') return index;
  for (const [facultyId, ass] of Object.entries(assessments)) {
    for (const ach of ass?.achievements || []) {
      if (!ach?.id) continue;
      for (const docId of ach.documentIds || []) {
        if (!docId) continue;
        index.set(docId, { achievement: ach, facultyId });
      }
    }
  }
  return index;
}

export function parentLinkForDocument(doc, assessments) {
  if (!doc?.id) return null;
  const idx = buildDocumentAchievementIndex(assessments);
  return idx.get(doc.id) || null;
}

const PARENT_REVIEW_DISPLAY = {
  approved: { label: 'Part of approved achievement', badge: 'badge-approved' },
  pending: { label: 'Awaiting achievement review', badge: 'badge-pending' },
  correction_requested: { label: 'Achievement needs changes', badge: 'badge-correction' },
  rejected: { label: 'Part of rejected achievement', badge: 'badge-rejected' },
};

export function parentReviewStatusLabel(reviewStatus) {
  return PARENT_REVIEW_DISPLAY[reviewStatus] || {
    label: `Achievement: ${reviewStatus || 'unknown'}`,
    badge: 'badge-muted',
  };
}

export function parentReviewBadgeHtml(reviewStatus) {
  const d = parentReviewStatusLabel(reviewStatus);
  return `<span class="badge-status ${d.badge}">${d.label}</span>`;
}

export function attachmentReviewStatusHtml(doc, link) {
  const ach = link?.achievement;
  if (!ach) {
    if ((doc.reviewStatus || '') === 'evidence') {
      return statusBadgeHtml('evidence');
    }
    return statusBadgeHtml(doc.reviewStatus || 'pending');
  }
  const sub = ach.submissionStatus || 'draft';
  if (sub !== 'submitted') {
    return `<span class="badge-status badge-muted">On faculty draft achievement</span>`;
  }
  const parts = [parentReviewBadgeHtml(ach.reviewStatus || 'pending')];
  if (doc.reviewStatus === 'evidence') {
    parts.push(`<span class="muted" style="font-size:0.82rem">File queue: supporting evidence</span>`);
  } else if (doc.reviewStatus && !['pending', 'evidence'].includes(doc.reviewStatus)) {
    parts.push(
      `<span class="muted" style="font-size:0.82rem" title="Legacy per-file status preserved">File record: ${doc.reviewStatus}</span>`
    );
  }
  return parts.join(' ');
}

export function processingStatusNote(doc) {
  const p = doc?.processingStatus;
  if (!p || p === 'none' || p === 'completed') return '';
  return `<span class="muted" style="font-size:0.8rem;display:block">Processing: ${p}</span>`;
}

/**
 * Mirror backend review_queue.document_counts_toward_legacy_pending
 */
export function documentCountsTowardLegacyPending(doc, achievements) {
  if (doc.uploadStatus && doc.uploadStatus !== 'stored') return false;
  if ((doc.reviewStatus || 'pending') !== 'pending') return false;
  if (isKraIAchievementIndicator(doc.indicatorId)) return false;
  return true;
}

/** Enrich portal documents with parent achievement fields (client fallback when API omits). */
export function enrichPortalDocuments(documents, assessments) {
  const list = dedupeDocumentsById(asDocumentsArray(documents, 'enrichPortalDocuments'));
  const index = buildDocumentAchievementIndex(assessments);
  return list.map((d) => {
    const link = index.get(d.id);
    if (!link) return d;
    const ach = link.achievement;
    return {
      ...d,
      linkedAchievementId: ach.id,
      parentSubmissionStatus: ach.submissionStatus,
      parentReviewStatus: ach.reviewStatus,
      parentAchievementTitle: ach.title,
    };
  });
}

/**
 * Resolve achievement.documentIds to portal document rows (by public id).
 */
export function resolveSupportingDocuments(store, facultyId, documentIds) {
  const ids = (documentIds || []).filter(Boolean);
  if (!ids.length) return { docs: [], missing: [] };
  const pool = enrichPortalDocuments(store?.documents || [], store?.assessments || {});
  const docs = [];
  const missing = [];
  for (const id of ids) {
    const d = pool.find((row) => row.id === id && (!facultyId || !row.facultyId || row.facultyId === facultyId));
    if (d) docs.push(d);
    else missing.push(id);
  }
  return { docs, missing };
}

export function collectUnlinkedBcEvidence(store, facId) {
  const achievements = store.assessments?.[facId]?.achievements || [];
  const linked = new Set();
  for (const a of achievements) for (const id of a.documentIds || []) linked.add(id);
  return enrichPortalDocuments(store.documents, store.assessments).filter(
    (d) =>
      d.facultyId === facId &&
      isKraIAchievementIndicator(d.indicatorId) &&
      !linked.has(d.id)
  );
}
