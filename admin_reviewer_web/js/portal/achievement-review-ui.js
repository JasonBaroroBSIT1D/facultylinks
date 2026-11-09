/**
 * KRA I Criterion B/C — folder tables and per-achievement inline review (Criterion A layout).
 */
import { PortalApi } from '../services/portal-api.js';
import { mountDocumentPdfViewer } from './document-pdf-viewer.js?v=3';
import { statusBadgeHtml } from '../core/copy.js';
import { MockStore, revalidatePortalInBackground } from '../repositories/mock-store.js';
import { showAppToast } from './account-modals.js';
import { pageIntro, SCREEN_INTRO } from '../core/copy.js';
import {
  formatFileSize,
  fileTypeLabel,
  indicatorDisplayName,
  groupAchievementsByIndicator,
  formatCompactUploadDate,
  achievementReviewStatusLabel,
  formatAchievementContextLine,
  criterionBackLabel,
  criterionReviewPageTitle,
  rulePermittedPoints,
} from './achievement-review-format.js';
import {
  WS_FOLDER_CRITERION,
  WS_FOLDER_FACULTY,
  WS_FOLDER_KRA_I,
  WS_FOLDER_KRA_II,
  WS_FOLDER_KRA_III,
  WS_FOLDER_KRA_IV,
  bindWorkspaceBreadcrumbNav,
  buildAchievementReviewBreadcrumb,
} from './workspace-folder-nav.js';
import {
  ACH_LOAD_ERROR,
  achievementsForCriterion,
  ensureFacultyAchievementsLoaded,
  patchAchievementInCache,
  resolveAchievementCriterionId,
} from './workspace-achievements-cache.js';
import { bootstrapPortal } from '../repositories/mock-store.js';
import { resolveSupportingDocuments } from './achievement-attachment-display.js';

export {
  formatFileSize,
  fileTypeLabel,
  indicatorDisplayName,
  groupAchievementsByIndicator,
  formatCompactUploadDate,
  achievementReviewStatusLabel,
};

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

/**
 * Folder-style workspace block for one criterion (B or C).
 */
export function buildCriterionAchievementsFolderHtml({ list, facId, store, catalog, meta, expandedIndicators = {} }) {
  if (!list.length) return '';
  const byInd = groupAchievementsByIndicator(list);
  const sections = [...byInd.entries()].map(([indicatorId, achievements]) => {
    const indName = indicatorDisplayName(catalog, indicatorId);
    const open = expandedIndicators[indicatorId] !== false;
    const rows = achievements
      .map((a) => {
        const docs = (a.documentIds || []).length;
        const ver = a.reviewerVerifiedPoints;
        const submitted = a.submittedAt ? String(a.submittedAt).slice(0, 10) : '—';
        return `<tr class="ach-folder-row" data-ach-open="${esc(a.id)}" data-ach-crit="${esc(meta.criterionId || '')}" tabindex="0" role="button">
          <td class="ach-folder-title" title="${esc(a.title || 'Untitled')}">${esc(a.title || 'Untitled')}</td>
          <td class="ach-folder-ind" title="${esc(indName)}">${esc(indName)}</td>
          <td>${docs}</td>
          <td>${a.claimedPoints ?? '—'}</td>
          <td>${ver != null ? ver : '—'}</td>
          <td>${statusBadgeHtml(a.reviewStatus || 'pending')}</td>
          <td>${submitted}</td>
        </tr>`;
      })
      .join('');
    return `<details class="ach-indicator-folder" data-ind-folder="${esc(indicatorId)}" ${open ? 'open' : ''}>
      <summary class="ach-indicator-folder__summary"><strong>${esc(indName)}</strong> <span class="muted">(${achievements.length} achievement${achievements.length === 1 ? '' : 's'})</span></summary>
      <div class="table-wrap ach-folder-table-wrap">
        <table class="ach-folder-table">
          <thead><tr>
            <th>Achievement</th><th>Indicator</th><th>Files</th><th>Claimed</th><th>Verified</th><th>Status</th><th>Submitted</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <ul class="ach-folder-cards" aria-label="${esc(indName)} achievements">
        ${achievements
          .map(
            (a) => `<li class="ach-folder-card" data-ach-open="${esc(a.id)}" data-ach-crit="${esc(meta.criterionId || '')}" role="button" tabindex="0">
              <strong>${esc(a.title || 'Untitled')}</strong>
              <p class="muted" style="margin:0.25rem 0;font-size:0.85rem">${docsCount(a)} file(s) · claimed ${a.claimedPoints ?? '—'} · ${submittedShort(a)}</p>
              ${statusBadgeHtml(a.reviewStatus || 'pending')}
            </li>`
          )
          .join('')}
      </ul>
    </details>`;
  });
  return `<div class="ach-criterion-folder" data-criterion-folder="${esc(meta.criterionId)}">${sections.join('')}</div>`;
}

function docsCount(a) {
  return (a.documentIds || []).length;
}
function submittedShort(a) {
  return a.submittedAt ? String(a.submittedAt).slice(0, 10) : '—';
}

export function bindCriterionFolderNavigation(host, { facId, onExpandChange }) {
  host.querySelectorAll('.ach-indicator-folder').forEach((det) => {
    det.addEventListener('toggle', () => {
      const id = det.dataset.indFolder;
      onExpandChange?.(id, det.open);
    });
  });
  const openReview = (el) => {
    const achId = el.dataset.achOpen;
    const criterionId = el.dataset.achCrit;
    if (!achId) return;
    el.dispatchEvent(
      new CustomEvent('fl-open-achievement-review', {
        bubbles: true,
        detail: { facultyId: facId, achievementId: achId, criterionId },
      })
    );
  };
  host.querySelectorAll('[data-ach-open]').forEach((el) => {
    el.addEventListener('click', () => openReview(el));
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openReview(el);
      }
    });
  });
}

function isImageMime(mime) {
  const m = (mime || '').toLowerCase();
  return m.startsWith('image/');
}

function mountMediaPreview(mountEl, doc, { onDestroyRef }) {
  if (!mountEl || !doc) return null;
  const fetchViewUrl = () => PortalApi.fetchDocumentViewUrl(doc.id);
  const mime = doc.mimeType || '';
  if ((mime || '').includes('pdf') || (doc.fileName || '').toLowerCase().endsWith('.pdf')) {
    const viewer = mountDocumentPdfViewer(mountEl, { documentId: doc.id, fetchViewUrl });
    onDestroyRef.current = () => viewer?.destroy?.();
    return viewer;
  }
  if (isImageMime(mime) || /\.(png|jpe?g|webp)$/i.test(doc.fileName || '')) {
    mountEl.innerHTML = `<div class="doc-pdf-viewer__footer ach-img-preview__toolbar">
        <button type="button" class="btn-ghost btn-sm" data-ach-img-open>Open in new tab</button>
        <button type="button" class="btn-ghost btn-sm" data-ach-img-dl>Download</button>
      </div>
      <div class="ach-img-preview"><p class="muted" data-ach-img-status>Loading…</p><img alt="" class="ach-img-preview__img" hidden /></div>`;
    const status = mountEl.querySelector('[data-ach-img-status]');
    const img = mountEl.querySelector('.ach-img-preview__img');
    const openBtn = mountEl.querySelector('[data-ach-img-open]');
    const dlBtn = mountEl.querySelector('[data-ach-img-dl]');
    let lastUrl = null;
    const load = async () => {
      try {
        const { url } = await fetchViewUrl();
        lastUrl = url;
        img.src = url;
        img.onload = () => {
          status.hidden = true;
          img.hidden = false;
        };
        img.onerror = () => {
          status.textContent = 'Could not display image.';
        };
      } catch (e) {
        status.textContent = e.message || 'Could not load image.';
      }
    };
    openBtn?.addEventListener('click', async () => {
      try {
        const { url } = lastUrl ? { url: lastUrl } : await fetchViewUrl();
        window.open(url, '_blank', 'noopener,noreferrer');
      } catch (e) {
        showAppToast(e.message || 'Could not open image.');
      }
    });
    dlBtn?.addEventListener('click', async () => {
      try {
        const { url } = lastUrl ? { url: lastUrl } : await fetchViewUrl();
        const a = document.createElement('a');
        a.href = url;
        a.download = doc.fileName || 'download';
        a.rel = 'noopener';
        a.click();
      } catch (e) {
        showAppToast(e.message || 'Could not download image.');
      }
    });
    void load();
    onDestroyRef.current = () => {
      mountEl.innerHTML = '';
      lastUrl = null;
    };
    return { destroy: onDestroyRef.current };
  }
  mountEl.innerHTML = `<p class="muted">Preview not available for this file type. Use Open in new tab.</p>`;
  onDestroyRef.current = () => {
    mountEl.innerHTML = '';
  };
  return null;
}

function reviewHistoryHtml(ach) {
  const hist = ach.reviewHistory || [];
  if (!hist.length) return '<p class="muted">No prior review actions.</p>';
  return `<ul class="doc-review-history-list">${hist
    .map(
      (h) =>
        `<li><time>${esc((h.at || '').slice(0, 10))}</time> — ${esc(h.status)}${h.remarks ? `: ${esc(h.remarks)}` : ''}${h.reviewerVerifiedPoints != null ? ` (${h.reviewerVerifiedPoints} pts)` : ''}</li>`
    )
    .join('')}</ul>`;
}

function attachmentMetaLine(d) {
  return `${fileTypeLabel(d)} · ${formatFileSize(d.sizeBytes)} · ${formatCompactUploadDate(d.uploadedAt || d.submittedAt)}`;
}

function supportingDocumentsBlockHtml(docs, activeDocId, achievement, { missingIds = [] } = {}) {
  const linked = achievement?.documentIds || [];
  if (!docs.length && !linked.length) return '<p class="muted">No documents linked.</p>';
  if (!docs.length && linked.length) {
    return `<p class="fl-error" role="alert">Could not load ${linked.length} linked file(s). Refresh the portal or reopen from the workspace folder — links are stored on the achievement.</p>
      <p class="muted">Linked ids: ${missingIds.map((id) => esc(id)).join(', ')}</p>`;
  }
  const parentLabel = achievementReviewStatusLabel(achievement?.reviewStatus || 'pending');
  const parentBlock = `<div class="ach-att-parent-status" role="status">
      <p class="ach-att-parent-status__line"><strong>Achievement:</strong> ${esc(parentLabel)}</p>
      <p class="muted ach-att-parent-status__hint">These files support this achievement.</p>
    </div>`;
  const rows = docs
    .map((d) => {
      const active = d.id === activeDocId ? ' ach-att-row--active' : '';
      const fullName = d.fileName || 'Untitled';
      return `<tr class="ach-att-row${active}" data-ach-att="${esc(d.id)}">
        <td class="ach-att-file-cell">
          <div class="ach-att-file-name" title="${esc(fullName)}">${esc(fullName)}</div>
          <div class="ach-att-file-meta muted">${esc(attachmentMetaLine(d))}</div>
        </td>
        <td class="ach-att-action-cell">
          <button type="button" class="btn-ghost btn-sm ach-att-view-btn" data-ach-att-view="${esc(d.id)}" aria-label="View ${esc(fullName)}">View</button>
        </td>
      </tr>`;
    })
    .join('');
  const cards = docs
    .map((d) => {
      const fullName = d.fileName || 'Untitled';
      return `<li class="ach-att-card ach-att-card--compact ${d.id === activeDocId ? 'ach-att-card--active' : ''}" data-ach-att="${esc(d.id)}">
        <div class="ach-att-file-name" title="${esc(fullName)}">${esc(fullName)}</div>
        <div class="ach-att-file-meta muted">${esc(attachmentMetaLine(d))}</div>
        <button type="button" class="btn-ghost btn-sm ach-att-view-btn" data-ach-att-view="${esc(d.id)}">View</button>
      </li>`;
    })
    .join('');
  return `${parentBlock}
    <div class="ach-att-table-wrap ach-att-table-wrap--review">
      <table class="ach-att-table ach-att-table--compact" aria-label="Supporting documents">
        <tbody id="achAttTableBody">${rows}</tbody>
      </table>
    </div>
    <ul class="ach-att-cards ach-att-cards--review" id="achAttCards" aria-label="Supporting documents">${cards}</ul>`;
}

function setActiveAttachmentHighlight(root, activeDocId) {
  root.querySelectorAll('.ach-att-row').forEach((row) => {
    row.classList.toggle('ach-att-row--active', row.dataset.achAtt === activeDocId);
  });
  root.querySelectorAll('.ach-att-card').forEach((card) => {
    card.classList.toggle('ach-att-card--active', card.dataset.achAtt === activeDocId);
  });
  const mount = root.querySelector('#achReviewMediaMount');
  if (mount) mount.dataset.docId = activeDocId || '';
}

/**
 * Two-column achievement review (one score per achievement, attachment switcher on left).
 */
export async function renderAchievementReviewPage(root, title, ctx) {
  const { session, navigate, isActive, getStore } = ctx;
  const facId = ctx.params.facultyId || ctx.params.facId;
  let criterionId = ctx.params.criterionId || 'kra-I-B';
  const achievementId = ctx.params.achievementId;
  let docId = ctx.params.docId;

  let store = getStore();
  const catalog = ctx.catalog;
  const faculty = store.faculty.find((f) => f.id === facId);

  let achievement = null;
  try {
    const entry = await ensureFacultyAchievementsLoaded(facId);
    if (!isActive()) return;
    if (entry.state === ACH_LOAD_ERROR) throw entry.error || new Error('Could not load achievements.');
    achievement = achievementsForCriterion(entry.achievements, criterionId).find((a) => a.id === achievementId);
    if (!achievement) {
      achievement = (entry.achievements || []).find((a) => a.id === achievementId);
    }
    if (achievement) {
      const resolvedCrit = resolveAchievementCriterionId(achievement);
      if (resolvedCrit) criterionId = resolvedCrit;
    }
  } catch (e) {
    if (!isActive()) return;
    root.innerHTML = `<p class="fl-error">${esc(e.message || 'Could not load achievement.')}</p>
      <button type="button" class="btn-ghost btn-sm" id="achRevBack">Back</button>`;
    root.querySelector('#achRevBack')?.addEventListener('click', () =>
      navigate('workspace', { restore: true, wsFolder: WS_FOLDER_CRITERION, criterionId })
    );
    return;
  }

  if (!achievement) {
    root.innerHTML = `<p>Achievement not found or not submitted.</p>
      <button type="button" class="btn-ghost btn-sm" id="achRevBack">Back</button>`;
    root.querySelector('#achRevBack')?.addEventListener('click', () =>
      navigate('workspace', { restore: true, wsFolder: WS_FOLDER_CRITERION, criterionId })
    );
    return;
  }

  title.textContent = criterionReviewPageTitle(criterionId);
  ctx.params.criterionId = criterionId;

  const docIds = achievement.documentIds || [];
  if (!docId && docIds.length) docId = docIds[0];

  let { docs, missing } = resolveSupportingDocuments(store, facId, docIds);
  if (docIds.length && !docs.length) {
    try {
      await bootstrapPortal({ full: true, force: true });
      if (!isActive()) return;
      store = getStore();
      ({ docs, missing } = resolveSupportingDocuments(store, facId, docIds));
    } catch {
      /* show missing-id error below */
    }
  }

  const activeDoc = docId ? docs.find((d) => d.id === docId) || store.documents.find((d) => d.id === docId) : null;
  const indName = indicatorDisplayName(catalog, achievement.indicatorId);
  const contextLine = formatAchievementContextLine(achievement);
  const permittedPts = rulePermittedPoints(achievement);

  if (root._achFormDraftAchievementId !== achievementId) {
    root._achFormDraft = {};
    root._achFormDraftAchievementId = achievementId;
  }
  const formDraft = root._achFormDraft || {};
  const vpDefault = achievement.reviewerVerifiedPoints ?? achievement.claimedPoints ?? '';
  const remDefault = achievement.reviewRemarks || '';
  const claimed = achievement.originalClaimedPoints ?? achievement.claimedPoints;
  const facultyLabel = faculty ? `${faculty.firstName} ${faculty.lastName}` : '—';

  const achBreadcrumb =
    faculty &&
    buildAchievementReviewBreadcrumb({
      fac: faculty,
      criterionId,
      catalog,
      achievementTitle: achievement.title,
    });

  root.innerHTML = `
    <div class="doc-review-page ach-review-page" data-achievement-id="${esc(achievement.id)}">
      ${pageIntro(SCREEN_INTRO.workspace)}
      ${achBreadcrumb || ''}
      <header class="doc-review-header">
        <button type="button" class="btn-ghost btn-sm" id="achBackWs">← ${esc(criterionBackLabel(criterionId))}</button>
        <h2 class="doc-review-header__title">${esc(achievement.title || 'Achievement')}</h2>
        <p class="muted" style="font-size:0.9rem;margin:0">${esc(facultyLabel)} · ${esc(indName)}</p>
        ${contextLine ? `<p class="muted" style="font-size:0.88rem;margin:0.15rem 0 0">${esc(contextLine)}</p>` : ''}
        <p class="muted" style="font-size:0.85rem;margin:0.2rem 0 0">${esc(achievement.ruleSummary || '')}${permittedPts != null ? ` · Workbook allowance: <strong>${permittedPts}</strong> pts` : ''}${achievement.ruleUnresolved ? ` — ${esc(achievement.ruleUnresolved)}` : ''}</p>
      </header>
      <motion class="doc-review-workspace ach-review-workspace" id="achReviewWorkspace" data-panel="pdf">
        <div class="doc-review-mobile-tabs" role="tablist" aria-label="Review panels">
          <button type="button" role="tab" data-review-tab="pdf" aria-selected="true">Document</button>
          <button type="button" role="tab" data-review-tab="review" aria-selected="false">Review details</button>
        </div>
        <section class="doc-review-pdf-panel ach-review-pdf-panel" aria-label="Document preview">
          <motion class="doc-review-panel doc-review-panel--pdf ach-review-preview-panel">
            <div id="achReviewMediaMount" class="doc-review-pdf-mount" data-doc-id="${esc(docId || '')}"></div>
          </motion>
        </section>
        <section class="doc-review-detail-panel ach-review-detail-panel" aria-label="Achievement review">
          <div class="doc-review-detail-scroll ach-review-detail-scroll">
            <section class="doc-review-section ach-review-attachments" aria-label="Supporting documents">
              <h3 class="doc-review-section__title">Supporting documents</h3>
              ${supportingDocumentsBlockHtml(docs, docId, achievement, { missingIds: missing })}
            </section>
            <section class="doc-review-section doc-review-form ach-review-form">
              <motion class="ach-review-points-row">
                <div class="doc-review-field">
                  <span class="doc-review-field__label">Faculty-claimed points</span>
                  <p class="ach-review-claim-value" id="achClaimPts">${esc(claimed ?? '—')}</p>
                </div>
                <div class="doc-review-field">
                  <label class="doc-review-field__label" for="achVerPts">Reviewer-verified points</label>
                  <input type="number" step="0.01" class="doc-review-input" id="achVerPts" value="${esc(formDraft.vp ?? vpDefault)}" ${permittedPts != null ? `max="${permittedPts}"` : ''} />
                  ${permittedPts != null ? `<p class="muted doc-review-field__hint" style="margin:0.25rem 0 0">Matrix allowance for this designation: <strong>${permittedPts}</strong> points (not the criterion cap).</p>` : ''}
                </div>
              </motion>
              <div class="doc-review-field">
                <label class="doc-review-field__label" for="achRem">Remarks</label>
                <textarea class="doc-review-textarea" id="achRem" rows="4">${esc(formDraft.remarks ?? remDefault)}</textarea>
              </div>
              <div class="doc-review-field">
                <label class="doc-review-field__label" for="achReason">Score change reason (if different from claim)</label>
                <input type="text" class="doc-review-input" id="achReason" value="${esc(formDraft.reason ?? '')}" />
              </div>
              <div class="doc-review-actions">
                <button type="button" class="btn-primary-sm btn-sm" data-ach-decision="approved">Approve</button>
                <button type="button" class="btn-ghost btn-sm" data-ach-decision="correction_requested">Request changes</button>
                <button type="button" class="btn-ghost btn-sm doc-review-actions__reject" data-ach-decision="rejected">Reject</button>
              </div>
              <p id="achRevOk" class="success-banner doc-review-feedback" hidden role="status"></p>
              <p id="achRevErr" class="doc-review-feedback doc-review-feedback--error" role="alert"></p>
              <details class="doc-review-history ach-review-history"${achievement.reviewStatus === 'approved' ? ' open' : ''}>
                <summary>Review history (${(achievement.reviewHistory || []).length})</summary>
                <div id="achReviewHistory">${reviewHistoryHtml(achievement)}</div>
              </details>
            </section>
          </div>
        </section>
      </motion>
    </div>`;

  root.querySelectorAll('motion').forEach((m) => {
    const d = document.createElement(m.tagName === 'motion' ? 'div' : 'div');
    d.className = m.className;
    d.innerHTML = m.innerHTML;
    m.replaceWith(d);
  });

  const destroyRef = { current: null };
  let activeDocId = docId;
  if (root._achMediaDestroy) {
    root._achMediaDestroy();
    root._achMediaDestroy = null;
  }

  const mountPreview = (documentId) => {
    const doc = documentId
      ? docs.find((d) => d.id === documentId) || store.documents.find((d) => d.id === documentId)
      : null;
    const mountEl = root.querySelector('#achReviewMediaMount');
    if (!mountEl) return;
    if (root._achMediaDestroy) {
      root._achMediaDestroy();
      root._achMediaDestroy = null;
    }
    if (doc) {
      mountMediaPreview(mountEl, doc, { onDestroyRef: destroyRef });
      root._achMediaDestroy = destroyRef.current;
    } else {
      mountEl.innerHTML = '<p class="muted">Use View on a supporting document to preview.</p>';
    }
  };

  mountPreview(activeDocId);

  const workspace = root.querySelector('#achReviewWorkspace');
  workspace?.querySelectorAll('[data-review-tab]').forEach((tab) => {
    tab.addEventListener('click', () => {
      const panel = tab.dataset.reviewTab;
      if (workspace) workspace.dataset.panel = panel;
      workspace?.querySelectorAll('[data-review-tab]').forEach((t) => {
        t.setAttribute('aria-selected', t.dataset.reviewTab === panel ? 'true' : 'false');
      });
    });
  });

  const persistFormDraft = () => {
    root._achFormDraft = {
      vp: root.querySelector('#achVerPts')?.value,
      remarks: root.querySelector('#achRem')?.value,
      reason: root.querySelector('#achReason')?.value,
    };
  };

  const switchDoc = (nextDocId) => {
    if (!nextDocId || nextDocId === activeDocId) return;
    persistFormDraft();
    activeDocId = nextDocId;
    ctx.params.docId = nextDocId;
    mountPreview(nextDocId);
    setActiveAttachmentHighlight(root, nextDocId);
    if (workspace && window.matchMedia('(max-width: 966px)').matches) {
      workspace.dataset.panel = 'pdf';
      workspace.querySelectorAll('[data-review-tab]').forEach((t) => {
        t.setAttribute('aria-selected', t.dataset.reviewTab === 'pdf' ? 'true' : 'false');
      });
    }
  };

  root.querySelectorAll('[data-ach-att-view]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      switchDoc(btn.dataset.achAttView);
    });
  });

  document.getElementById('achBackWs')?.addEventListener('click', () => {
    persistFormDraft();
    if (root._achMediaDestroy) root._achMediaDestroy();
    ctx.stateRef.workspaceFacultyId = facId;
    navigate('workspace', { restore: true, wsFolder: WS_FOLDER_CRITERION, criterionId });
  });

  bindWorkspaceBreadcrumbNav(root, {
    onCrumb: (id, crit) => {
      persistFormDraft();
      if (root._achMediaDestroy) root._achMediaDestroy();
      ctx.stateRef.workspaceFacultyId = facId;
      if (id === 'assigned') {
        navigate('assigned');
        return;
      }
      if (id === WS_FOLDER_FACULTY) navigate('workspace', { restore: true, wsFolder: WS_FOLDER_FACULTY });
      else if (id === WS_FOLDER_KRA_I) navigate('workspace', { restore: true, wsFolder: WS_FOLDER_KRA_I });
      else if (id === WS_FOLDER_KRA_II) navigate('workspace', { restore: true, wsFolder: WS_FOLDER_KRA_II });
      else if (id === WS_FOLDER_KRA_III) navigate('workspace', { restore: true, wsFolder: WS_FOLDER_KRA_III });
      else if (id === WS_FOLDER_KRA_IV) navigate('workspace', { restore: true, wsFolder: WS_FOLDER_KRA_IV });
      else if (id === 'criterion') navigate('workspace', { restore: true, wsFolder: WS_FOLDER_CRITERION, criterionId: crit || criterionId });
    },
  });

  let saveInflight = false;
  const submitDecision = async (status) => {
    if (saveInflight) return;
    persistFormDraft();
    const errEl = document.getElementById('achRevErr');
    const okEl = document.getElementById('achRevOk');
    const vp = document.getElementById('achVerPts')?.value;
    const remarks = document.getElementById('achRem')?.value;
    const reason = document.getElementById('achReason')?.value;
    saveInflight = true;
    if (errEl) errEl.textContent = '';
    if (okEl) okEl.hidden = true;
    const linkedCount = (achievement.documentIds || []).length;
    const resolvedCount = docs.length;
    if (status === 'approved' && linkedCount > 0 && resolvedCount === 0) {
      if (errEl) {
        errEl.textContent =
          'Cannot approve: supporting documents are linked on the achievement but could not be loaded. Refresh the portal and confirm files open in the viewer.';
      }
      saveInflight = false;
      return;
    }
    if (status === 'approved' && linkedCount === 0) {
      if (errEl) errEl.textContent = 'Cannot approve: at least one supporting document must be linked to this achievement.';
      saveInflight = false;
      return;
    }
    if (status === 'approved') {
      const vpNum = Number(vp);
      const cap = rulePermittedPoints(achievement);
      if (cap != null && !Number.isNaN(vpNum) && vpNum > cap + 1e-6) {
        if (errEl) {
          errEl.textContent = `Verified points cannot exceed ${cap} for this indicator (workbook designation matrix).`;
        }
        saveInflight = false;
        return;
      }
      if (cap != null && !Number.isNaN(vpNum) && Math.abs(vpNum - Number(claimed)) > 1e-6 && !(reason || '').trim()) {
        if (errEl) errEl.textContent = 'Explain why the verified score differs from the faculty claim.';
        saveInflight = false;
        return;
      }
    }
    try {
      const updated = await PortalApi.reviewAchievement(achievement.id, {
        facultyId: facId,
        reviewStatus: status,
        reviewerVerifiedPoints: status === 'approved' ? Number(vp) : null,
        remarks,
        scoreChangeReason: reason,
      });
      if (updated?.achievement) {
        achievement = updated.achievement;
        patchAchievementInCache(facId, updated.achievement);
      }
      if (okEl) {
        okEl.hidden = false;
        okEl.textContent = `Saved: ${status}.`;
      }
      showAppToast('Achievement review saved.');
      void revalidatePortalInBackground();
    } catch (e) {
      if (errEl) errEl.textContent = e.message || 'Save failed.';
    } finally {
      saveInflight = false;
    }
  };

  root.querySelectorAll('[data-ach-decision]').forEach((btn) => {
    btn.addEventListener('click', () => void submitDecision(btn.dataset.achDecision));
  });
}
