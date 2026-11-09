/**
 * Reviewer Check Documents — folder hierarchy (faculty → KRA I → criterion).
 */
import {
  isSetSefEvaluationDoc,
  isSpecialStatusTeachingDoc,
  workspaceCriterionHeading,
  WORKSPACE_CRITERION_ORDER_II,
  WORKSPACE_CRITERION_ORDER_III,
  WORKSPACE_CRITERION_ORDER_IV,
} from './workspace-kra-i-sections.js';
import { enrichPortalDocuments, documentCountsTowardLegacyPending } from './achievement-attachment-display.js';
import {
  ACH_LOAD_ERROR,
  ACH_LOAD_IDLE,
  ACH_LOAD_LOADED,
  ACH_LOAD_LOADING,
  countAchievementsList,
} from './workspace-achievements-cache.js';

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

export const WS_FOLDER_FACULTY = 'faculty-root';
export const WS_FOLDER_KRA_I = 'kra-i';
export const WS_FOLDER_KRA_II = 'kra-ii';
export const WS_FOLDER_KRA_III = 'kra-iii';
export const WS_FOLDER_KRA_IV = 'kra-iv';
export const WS_FOLDER_CRITERION = 'criterion';

const CRITERION_ORDER = ['kra-I-A', 'kra-I-B', 'kra-I-C'];

export function workspaceScrollKey(ui) {
  const folder = ui?.folder || WS_FOLDER_FACULTY;
  if (folder === WS_FOLDER_CRITERION && ui?.criterionId) return `criterion-${ui.criterionId}`;
  if (folder === WS_FOLDER_KRA_II) return WS_FOLDER_KRA_II;
  if (folder === WS_FOLDER_KRA_III) return WS_FOLDER_KRA_III;
  if (folder === WS_FOLDER_KRA_IV) return WS_FOLDER_KRA_IV;
  return folder;
}

export function kraIIIExtensionCounts(achEntry) {
  const loadState = achEntry?.state ?? ACH_LOAD_IDLE;
  let a;
  let b;
  let c;
  let d;
  if (loadState === ACH_LOAD_LOADED) {
    const list = achEntry.achievements || [];
    a = { ...countAchievementsList(list, 'kra-III-A'), loadState };
    b = { ...countAchievementsList(list, 'kra-III-B'), loadState };
    c = { ...countAchievementsList(list, 'kra-III-C'), loadState };
    d = { ...countAchievementsList(list, 'kra-III-D'), loadState };
  } else {
    const stub = { total: null, pending: null, loadState, error: achEntry?.error };
    a = b = c = d = stub;
  }
  const items = (a.total ?? 0) + (b.total ?? 0) + (c.total ?? 0) + (d.total ?? 0);
  const pending = (a.pending ?? 0) + (b.pending ?? 0) + (c.pending ?? 0) + (d.pending ?? 0);
  return {
    items: loadState === ACH_LOAD_LOADED ? items : null,
    pending: loadState === ACH_LOAD_LOADED ? pending : null,
    achLoadState: loadState,
    byCriterion: { 'kra-III-A': a, 'kra-III-B': b, 'kra-III-C': c, 'kra-III-D': d },
  };
}

function kraIiiRootMeta(counts) {
  if (counts.achLoadState !== ACH_LOAD_LOADED) {
    return counts.achLoadState === ACH_LOAD_ERROR ? 'Achievements unavailable' : 'Loading achievements…';
  }
  return folderMetaLine({ items: counts.items, pending: counts.pending });
}

export function kraIVProfessionalCounts(achEntry) {
  const loadState = achEntry?.state ?? ACH_LOAD_IDLE;
  let a;
  let b;
  let c;
  let d;
  if (loadState === ACH_LOAD_LOADED) {
    const list = achEntry.achievements || [];
    a = { ...countAchievementsList(list, 'kra-IV-A'), loadState };
    b = { ...countAchievementsList(list, 'kra-IV-B'), loadState };
    c = { ...countAchievementsList(list, 'kra-IV-C'), loadState };
    d = { ...countAchievementsList(list, 'kra-IV-D'), loadState };
  } else {
    const stub = { total: null, pending: null, loadState, error: achEntry?.error };
    a = b = c = d = stub;
  }
  const items = (a.total ?? 0) + (b.total ?? 0) + (c.total ?? 0) + (d.total ?? 0);
  const pending = (a.pending ?? 0) + (b.pending ?? 0) + (c.pending ?? 0) + (d.pending ?? 0);
  return {
    items: loadState === ACH_LOAD_LOADED ? items : null,
    pending: loadState === ACH_LOAD_LOADED ? pending : null,
    achLoadState: loadState,
    byCriterion: { 'kra-IV-A': a, 'kra-IV-B': b, 'kra-IV-C': c, 'kra-IV-D': d },
  };
}

function kraIvRootMeta(counts) {
  if (counts.achLoadState !== ACH_LOAD_LOADED) {
    return counts.achLoadState === ACH_LOAD_ERROR ? 'Achievements unavailable' : 'Loading achievements…';
  }
  return folderMetaLine({ items: counts.items, pending: counts.pending });
}

export function kraIIResearchCounts(achEntry) {
  const loadState = achEntry?.state ?? ACH_LOAD_IDLE;
  let a;
  let b;
  let c;
  if (loadState === ACH_LOAD_LOADED) {
    const list = achEntry.achievements || [];
    a = { ...countAchievementsList(list, 'kra-II-A'), loadState };
    b = { ...countAchievementsList(list, 'kra-II-B'), loadState };
    c = { ...countAchievementsList(list, 'kra-II-C'), loadState };
  } else {
    const stub = { total: null, pending: null, loadState, error: achEntry?.error };
    a = b = c = stub;
  }
  const items = (a.total ?? 0) + (b.total ?? 0) + (c.total ?? 0);
  const pending = (a.pending ?? 0) + (b.pending ?? 0) + (c.pending ?? 0);
  return {
    items: loadState === ACH_LOAD_LOADED ? items : null,
    pending: loadState === ACH_LOAD_LOADED ? pending : null,
    achLoadState: loadState,
    byCriterion: { 'kra-II-A': a, 'kra-II-B': b, 'kra-II-C': c },
  };
}

function kraIiRootMeta(counts) {
  if (counts.achLoadState !== ACH_LOAD_LOADED) {
    return counts.achLoadState === ACH_LOAD_ERROR ? 'Achievements unavailable' : 'Loading achievements…';
  }
  return folderMetaLine({ items: counts.items, pending: counts.pending });
}

export function countCriterionADocs(store, facId) {
  const docs = enrichPortalDocuments(store?.documents, store?.assessments).filter((d) => d.facultyId === facId);
  const setSef = docs.filter(isSetSefEvaluationDoc);
  const special = docs.filter(isSpecialStatusTeachingDoc);
  const pending = setSef.filter((d) => documentCountsTowardLegacyPending(d, [])).length;
  return { setSef: setSef.length, special: special.length, pending, total: setSef.length + special.length };
}

function folderMetaLine(counts) {
  const parts = [];
  const items = counts.items ?? counts.total;
  if (items != null && items > 0) parts.push(`${items} achievement${items === 1 ? '' : 's'}`);
  if (counts.pending > 0) parts.push(`${counts.pending} pending`);
  return parts.length ? parts.join(' · ') : 'No submitted achievements';
}

export function folderMetaForBcCounts(bcCounts) {
  const state = bcCounts.loadState;
  if (state === ACH_LOAD_IDLE || state === ACH_LOAD_LOADING) return 'Loading…';
  if (state === ACH_LOAD_ERROR) return 'Could not load · Retry in folder';
  return folderMetaLine(bcCounts);
}

export function kraRootFolderMeta(kraCounts, achLoadState) {
  const a = kraCounts.byCriterion['kra-I-A'];
  const docPart =
    a.total > 0
      ? `${a.total} document${a.total === 1 ? '' : 's'}${a.pending ? ` · ${a.pending} pending` : ''}`
      : a.pending
        ? `${a.pending} pending review`
        : '';
  if (achLoadState !== ACH_LOAD_LOADED) {
    if (achLoadState === ACH_LOAD_ERROR) return docPart ? `${docPart} · achievements unavailable` : 'Achievements unavailable';
    return docPart ? `${docPart} · loading achievements…` : 'Loading achievements…';
  }
  const items = kraCounts.items;
  const pending = kraCounts.pending;
  if (!items && !docPart) return 'No submitted items yet';
  const parts = [];
  if (items) parts.push(`${items} item${items === 1 ? '' : 's'}`);
  if (pending) parts.push(`${pending} pending`);
  if (docPart && items !== a.total) parts.unshift(docPart);
  return parts.length ? parts.join(' · ') : 'No submitted items yet';
}

export function kraIInstructionCounts(store, facId, achEntry) {
  const a = countCriterionADocs(store, facId);
  const loadState = achEntry?.state ?? ACH_LOAD_IDLE;
  let b;
  let c;
  if (loadState === ACH_LOAD_LOADED) {
    const list = achEntry.achievements || [];
    b = { ...countAchievementsList(list, 'kra-I-B'), loadState };
    c = { ...countAchievementsList(list, 'kra-I-C'), loadState };
  } else {
    b = { total: null, pending: null, loadState, error: achEntry?.error };
    c = { total: null, pending: null, loadState, error: achEntry?.error };
  }
  const items = a.total + (b.total ?? 0) + (c.total ?? 0);
  const pending = a.pending + (b.pending ?? 0) + (c.pending ?? 0);
  return {
    items: loadState === ACH_LOAD_LOADED ? items : null,
    pending: loadState === ACH_LOAD_LOADED ? pending : null,
    achLoadState: loadState,
    byCriterion: { 'kra-I-A': a, 'kra-I-B': b, 'kra-I-C': c },
  };
}

export function patchWorkspaceFolderMetas(root, kraICounts, kraIICounts, kraIIICounts, kraIVCounts, catalog, folder) {
  if (!root) return;
  if (folder === WS_FOLDER_FACULTY) {
    const metaI = root.querySelector('[data-ws-nav="kra-i"] .ws-folder-row__meta');
    if (metaI) metaI.textContent = kraRootFolderMeta(kraICounts, kraICounts.achLoadState);
    const metaII = root.querySelector('[data-ws-nav="kra-ii"] .ws-folder-row__meta');
    if (metaII) metaII.textContent = kraIiRootMeta(kraIICounts);
    const metaIII = root.querySelector('[data-ws-nav="kra-iii"] .ws-folder-row__meta');
    if (metaIII) metaIII.textContent = kraIiiRootMeta(kraIIICounts);
    const metaIV = root.querySelector('[data-ws-nav="kra-iv"] .ws-folder-row__meta');
    if (metaIV) metaIV.textContent = kraIvRootMeta(kraIVCounts);
  } else if (folder === WS_FOLDER_KRA_I) {
    for (const critId of CRITERION_ORDER) {
      const row = root.querySelector(`[data-ws-criterion="${critId}"] .ws-folder-row__meta`);
      if (!row) continue;
      const c = kraICounts.byCriterion[critId];
      if (critId === 'kra-I-A') {
        row.textContent = `${c.setSef} SET/SEF · ${c.special} special${c.pending ? ` · ${c.pending} pending` : ''}`;
      } else {
        row.textContent = folderMetaForBcCounts(c);
      }
    }
  } else if (folder === WS_FOLDER_KRA_II) {
    for (const critId of WORKSPACE_CRITERION_ORDER_II) {
      const row = root.querySelector(`[data-ws-criterion="${critId}"] .ws-folder-row__meta`);
      if (!row) continue;
      const c = kraIICounts.byCriterion[critId];
      row.textContent = folderMetaForBcCounts(c);
    }
  } else if (folder === WS_FOLDER_KRA_III) {
    for (const critId of WORKSPACE_CRITERION_ORDER_III) {
      const row = root.querySelector(`[data-ws-criterion="${critId}"] .ws-folder-row__meta`);
      if (!row) continue;
      const c = kraIIICounts.byCriterion[critId];
      row.textContent = folderMetaForBcCounts(c);
    }
  } else if (folder === WS_FOLDER_KRA_IV) {
    for (const critId of WORKSPACE_CRITERION_ORDER_IV) {
      const row = root.querySelector(`[data-ws-criterion="${critId}"] .ws-folder-row__meta`);
      if (!row) continue;
      const c = kraIVCounts.byCriterion[critId];
      row.textContent = folderMetaForBcCounts(c);
    }
  }
}

export function bindWorkspaceBreadcrumbNav(root, handlers) {
  root.querySelectorAll('[data-ws-crumb]').forEach((a) => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      handlers?.onCrumb?.(a.dataset.wsCrumb, a.dataset.wsCrit || null);
    });
  });
}

export function buildAchievementReviewBreadcrumb({ fac, criterionId, catalog, achievementTitle }) {
  const crumbs = [
    { id: 'assigned', label: 'Assigned Faculty' },
    { id: WS_FOLDER_FACULTY, label: `${fac.firstName} ${fac.lastName}` },
    {
      id: criterionId?.startsWith('kra-IV')
        ? WS_FOLDER_KRA_IV
        : criterionId?.startsWith('kra-III')
          ? WS_FOLDER_KRA_III
          : criterionId?.startsWith('kra-II')
            ? WS_FOLDER_KRA_II
            : WS_FOLDER_KRA_I,
      label: criterionId?.startsWith('kra-IV')
        ? 'KRA IV'
        : criterionId?.startsWith('kra-III')
          ? 'KRA III'
          : criterionId?.startsWith('kra-II')
            ? 'KRA II'
            : 'KRA I',
    },
    {
      id: 'criterion',
      label: workspaceCriterionHeading(catalog, criterionId),
      criterionId,
    },
    { id: 'achievement', label: achievementTitle || 'Achievement' },
  ];
  const html = crumbs
    .map((c, i) => {
      const isLast = i === crumbs.length - 1;
      const cls = isLast ? 'ws-crumb ws-crumb--current' : 'ws-crumb ws-crumb--link';
      const attrs = isLast
        ? `class="${cls}" aria-current="page"`
        : `class="${cls}" href="#" data-ws-crumb="${esc(c.id)}" data-ws-crit="${esc(c.criterionId || '')}"`;
      return isLast ? `<span ${attrs}>${esc(c.label)}</span>` : `<a ${attrs}>${esc(c.label)}</a>`;
    })
    .join('<span class="ws-crumb-sep" aria-hidden="true">→</span>');
  return `<nav class="ws-breadcrumb" aria-label="Breadcrumb">${html}</nav>`;
}

export function buildWorkspaceBreadcrumb({ fac, folder, criterionId, catalog, onNavigate }) {
  const crumbs = [];
  crumbs.push({ id: 'assigned', label: 'Assigned Faculty' });
  crumbs.push({ id: WS_FOLDER_FACULTY, label: `${fac.firstName} ${fac.lastName}` });
  if (folder === WS_FOLDER_KRA_I) {
    crumbs.push({ id: WS_FOLDER_KRA_I, label: 'KRA I' });
  } else if (folder === WS_FOLDER_KRA_II) {
    crumbs.push({ id: WS_FOLDER_KRA_II, label: 'KRA II' });
  } else if (folder === WS_FOLDER_KRA_III) {
    crumbs.push({ id: WS_FOLDER_KRA_III, label: 'KRA III' });
  } else if (folder === WS_FOLDER_KRA_IV) {
    crumbs.push({ id: WS_FOLDER_KRA_IV, label: 'KRA IV' });
  } else if (folder === WS_FOLDER_CRITERION && criterionId) {
    crumbs.push({
      id: criterionId.startsWith('kra-IV')
        ? WS_FOLDER_KRA_IV
        : criterionId.startsWith('kra-III')
          ? WS_FOLDER_KRA_III
          : criterionId.startsWith('kra-II')
            ? WS_FOLDER_KRA_II
            : WS_FOLDER_KRA_I,
      label: criterionId.startsWith('kra-IV')
        ? 'KRA IV'
        : criterionId.startsWith('kra-III')
          ? 'KRA III'
          : criterionId.startsWith('kra-II')
            ? 'KRA II'
            : 'KRA I',
    });
  }
  if (folder === WS_FOLDER_CRITERION && criterionId) {
    crumbs.push({
      id: 'criterion',
      label: workspaceCriterionHeading(catalog, criterionId),
      criterionId,
    });
  }
  const html = crumbs
    .map((c, i) => {
      const isLast = i === crumbs.length - 1;
      const cls = isLast ? 'ws-crumb ws-crumb--current' : 'ws-crumb ws-crumb--link';
      const attrs = isLast
        ? `class="${cls}" aria-current="page"`
        : `class="${cls}" href="#" data-ws-crumb="${esc(c.id)}" data-ws-crit="${esc(c.criterionId || '')}"`;
      return isLast ? `<span ${attrs}>${esc(c.label)}</span>` : `<a ${attrs}>${esc(c.label)}</a>`;
    })
    .join('<span class="ws-crumb-sep" aria-hidden="true">→</span>');
  return `<nav class="ws-breadcrumb" aria-label="Breadcrumb">${html}</nav>`;
}

export function buildFacultyRootFolderHtml(kraICounts, kraIICounts, kraIIICounts, kraIVCounts) {
  return `<div class="ws-folder-list" role="list">
    <button type="button" class="ws-folder-row" data-ws-nav="kra-i" role="listitem">
      <span class="ws-folder-row__icon" aria-hidden="true">📁</span>
      <span class="ws-folder-row__body">
        <strong class="ws-folder-row__title">KRA I — Instruction</strong>
        <span class="muted ws-folder-row__meta">${esc(kraRootFolderMeta(kraICounts, kraICounts.achLoadState))}</span>
      </span>
      <span class="ws-folder-row__chev" aria-hidden="true">›</span>
    </button>
    <button type="button" class="ws-folder-row" data-ws-nav="kra-ii" role="listitem">
      <span class="ws-folder-row__icon" aria-hidden="true">📁</span>
      <span class="ws-folder-row__body">
        <strong class="ws-folder-row__title">KRA II — Research, Innovation and/or Creative Work</strong>
        <span class="muted ws-folder-row__meta">${esc(kraIiRootMeta(kraIICounts))}</span>
      </span>
      <span class="ws-folder-row__chev" aria-hidden="true">›</span>
    </button>
    <button type="button" class="ws-folder-row" data-ws-nav="kra-iii" role="listitem">
      <span class="ws-folder-row__icon" aria-hidden="true">📁</span>
      <span class="ws-folder-row__body">
        <strong class="ws-folder-row__title">KRA III — Extension Services</strong>
        <span class="muted ws-folder-row__meta">${esc(kraIiiRootMeta(kraIIICounts))}</span>
      </span>
      <span class="ws-folder-row__chev" aria-hidden="true">›</span>
    </button>
    <button type="button" class="ws-folder-row" data-ws-nav="kra-iv" role="listitem">
      <span class="ws-folder-row__icon" aria-hidden="true">📁</span>
      <span class="ws-folder-row__body">
        <strong class="ws-folder-row__title">KRA IV — Professional Development</strong>
        <span class="muted ws-folder-row__meta">${esc(kraIvRootMeta(kraIVCounts))}</span>
      </span>
      <span class="ws-folder-row__chev" aria-hidden="true">›</span>
    </button>
  </div>`;
}

export function buildKraIVCriterionFoldersHtml(catalog, kraCounts) {
  return `<div class="ws-folder-list" role="list">
    ${WORKSPACE_CRITERION_ORDER_IV.map((critId) => {
      const heading = workspaceCriterionHeading(catalog, critId);
      const c = kraCounts.byCriterion[critId];
      const meta = folderMetaForBcCounts(c);
      return `<button type="button" class="ws-folder-row" data-ws-nav="criterion" data-ws-criterion="${esc(critId)}" role="listitem">
        <span class="ws-folder-row__icon" aria-hidden="true">📁</span>
        <span class="ws-folder-row__body">
          <strong class="ws-folder-row__title">${esc(heading)}</strong>
          <span class="muted ws-folder-row__meta">${esc(meta)}</span>
        </span>
        <span class="ws-folder-row__chev" aria-hidden="true">›</span>
      </button>`;
    }).join('')}
  </div>`;
}

export function buildKraIIICriterionFoldersHtml(catalog, kraCounts) {
  return `<div class="ws-folder-list" role="list">
    ${WORKSPACE_CRITERION_ORDER_III.map((critId) => {
      const heading = workspaceCriterionHeading(catalog, critId);
      const c = kraCounts.byCriterion[critId];
      const meta = folderMetaForBcCounts(c);
      return `<button type="button" class="ws-folder-row" data-ws-nav="criterion" data-ws-criterion="${esc(critId)}" role="listitem">
        <span class="ws-folder-row__icon" aria-hidden="true">📁</span>
        <span class="ws-folder-row__body">
          <strong class="ws-folder-row__title">${esc(heading)}</strong>
          <span class="muted ws-folder-row__meta">${esc(meta)}</span>
        </span>
        <span class="ws-folder-row__chev" aria-hidden="true">›</span>
      </button>`;
    }).join('')}
  </div>`;
}

export function buildKraIICriterionFoldersHtml(catalog, kraCounts) {
  return `<div class="ws-folder-list" role="list">
    ${WORKSPACE_CRITERION_ORDER_II.map((critId) => {
      const heading = workspaceCriterionHeading(catalog, critId);
      const c = kraCounts.byCriterion[critId];
      const meta = folderMetaForBcCounts(c);
      return `<button type="button" class="ws-folder-row" data-ws-nav="criterion" data-ws-criterion="${esc(critId)}" role="listitem">
        <span class="ws-folder-row__icon" aria-hidden="true">📁</span>
        <span class="ws-folder-row__body">
          <strong class="ws-folder-row__title">${esc(heading)}</strong>
          <span class="muted ws-folder-row__meta">${esc(meta)}</span>
        </span>
        <span class="ws-folder-row__chev" aria-hidden="true">›</span>
      </button>`;
    }).join('')}
  </div>`;
}

export function buildKraICriterionFoldersHtml(catalog, kraCounts) {
  return `<div class="ws-folder-list" role="list">
    ${CRITERION_ORDER.map((critId) => {
      const heading = workspaceCriterionHeading(catalog, critId);
      const c = kraCounts.byCriterion[critId];
      let meta;
      if (critId === 'kra-I-A') {
        meta = `${c.setSef} SET/SEF · ${c.special} special${c.pending ? ` · ${c.pending} pending` : ''}`;
      } else {
        meta = folderMetaForBcCounts(c);
      }
      return `<button type="button" class="ws-folder-row" data-ws-nav="criterion" data-ws-criterion="${esc(critId)}" role="listitem">
        <span class="ws-folder-row__icon" aria-hidden="true">📁</span>
        <span class="ws-folder-row__body">
          <strong class="ws-folder-row__title">${esc(heading)}</strong>
          <span class="muted ws-folder-row__meta">${esc(meta)}</span>
        </span>
        <span class="ws-folder-row__chev" aria-hidden="true">›</span>
      </button>`;
    }).join('')}
  </div>`;
}

export function buildCriterionDetailShell(criterionId, heading) {
  return `<article class="card ws-criterion-card ws-criterion-card--open">
    <h2 class="ws-criterion-card__title">${esc(heading)}</h2>
    <div id="wsFolderContent" class="ws-folder-content" data-ws-criterion="${esc(criterionId)}"></div>
  </article>`;
}
