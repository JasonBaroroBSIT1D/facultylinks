import { MockStore, bootstrapPortal, persistConfigDraft } from '../repositories/mock-store.js';
import { PortalApi } from '../services/portal-api.js';
import {
  ConfigRepository,
  findIndicatorInCatalog,
  validateCatalog,
  SOURCE_CIRCULAR,
  isCatalogWorkbookComplete,
} from '../repositories/config-repository.js';
import {
  isDocumentIntakeIndicator,
  isSupportingEvidenceIndicator,
  scoringIndicatorsForCriterion,
} from '../core/assessment-definitions.js';
import { SCREEN_INTRO, pageIntro } from '../core/copy.js';
import { computeKraSummaries } from '../core/scoring.js';
import { modalHost, bindModalShell, teardownModal, openCenteredModal, openDrawerModal } from './modal-access.js';

let _session = null;
let _onRefresh = null;

function persistDraftSafe(store) {
  return persistConfigDraft(store).catch((e) => toast(e.message, true));
}

const _ui = {
  kraTab: 0,
  search: '',
  needsOnly: false,
  expanded: new Set(),
  expandedKraId: null,
  dirty: false,
};

const OFFICIAL_KRA_IDS = ['kra-I', 'kra-II', 'kra-III', 'kra-IV'];
const SET_SEF_PDF_INDICATOR_IDS = [
  'kra-I-A-setsef-eval',
  'kra-I-A-setsef-combined',
  'kra-I-A-set-pdf',
  'kra-I-A-sef-pdf',
];

function catalogHasSetSefPdfIndicators(catalog) {
  if (!catalog?.kras?.length) return false;
  return SET_SEF_PDF_INDICATOR_IDS.every((id) => findIndicatorInCatalog(catalog, id));
}

function catalogHasSetSefIntakeSupport(catalog) {
  if (Array.isArray(catalog?.documentIntakeAliases) && catalog.documentIntakeAliases.length > 0) return true;
  return catalogHasSetSefPdfIndicators(catalog);
}

const KRA_TAB_LABELS = {
  'kra-I': 'KRA I · Instruction',
  'kra-II': 'KRA II · Research',
  'kra-III': 'KRA III · Extension',
  'kra-IV': 'KRA IV · Professional Development',
};

let _pendingWeights = null;
let _savedFingerprint = '';

const HOW_IT_WORKS = `
  <p>Set reference points and caps for each indicator under DBM–CHED JC No. 3, s. 2022. Faculty who already started an assessment keep the rule version they began with.</p>
  <ul>
    <li><strong>Save Draft</strong> stores draft rules on the server without affecting published rules.</li>
    <li><strong>Review &amp; Publish</strong> checks catalog validation (including stored KRA weight totals), then sets an effective date for new work.</li>
    <li><strong>Preview</strong> (inside Review &amp; Publish) runs what-if calculations only — it does not change saved faculty scores.</li>
    <li>Assessment weights by current faculty rank are managed under <strong>Evaluation Settings → Rank simulation</strong>.</li>
  </ul>
`;

export function initConfigUi(session, onRefresh) {
  _session = session;
  _onRefresh = onRefresh;
}

function requireDraft(store) {
  return ConfigRepository.getDraft(store) || ConfigRepository.forkDraftFromActive(store, _session.email);
}

function decimalToPct(d) {
  const n = Number(d);
  if (!Number.isFinite(n)) return '';
  const pct = Math.round(n * 10000) / 100;
  return Number.isInteger(pct) ? String(pct) : pct.toFixed(1);
}

function formatDate(d) {
  if (!d) return '—';
  try {
    const dt = new Date(d.includes('T') ? d : `${d}T12:00:00`);
    return dt.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
  } catch {
    return d;
  }
}

function fingerprintDraft(store) {
  const d = ConfigRepository.getDraft(store);
  if (!d) return '';
  return JSON.stringify({ w: d.kraWeights, c: d.catalog });
}

function syncWeightsFromDom() {
  // Weight editors were moved to Rank simulation settings; nothing to sync from Scoring Rules DOM.
}

function refreshDirtyFlag() {
  const store = MockStore.load();
  const d = ConfigRepository.getDraft(store);
  if (d && _pendingWeights) {
    const fp = JSON.stringify({ w: _pendingWeights, c: d.catalog });
    _ui.dirty = fp !== _savedFingerprint;
  }
}

function kraHasMeaningfulData(kra) {
  const hasCriteria = (kra.criteria?.length ?? 0) > 0;
  const hasIndicators = kra.criteria?.some((c) => (c.indicators?.length ?? 0) > 0);
  return hasCriteria || hasIndicators;
}

function isRemovablePlaceholder(kra) {
  if (OFFICIAL_KRA_IDS.includes(kra.id)) return false;
  if (kraHasMeaningfulData(kra)) return false;
  if (kra.id?.startsWith('kra-new-') || kra.id?.startsWith('kra-custom-')) return true;
  if (/^new kra$/i.test(kra.name?.trim() || '')) return true;
  return false;
}

/** Tab bar shows only the four JC3 main KRAs, in fixed order. */
function getNavigableKras(catalog) {
  return OFFICIAL_KRA_IDS.map((id) => {
    const catalogIndex = catalog.kras.findIndex((k) => k.id === id);
    if (catalogIndex < 0) return null;
    return { kra: catalog.kras[catalogIndex], catalogIndex };
  }).filter(Boolean);
}

function pruneEmptyPlaceholderKras(store) {
  const d = ConfigRepository.getDraft(store);
  if (!d) return;
  const removed = d.catalog.kras.filter((k) => isRemovablePlaceholder(k));
  if (!removed.length) return;
  d.catalog.kras = d.catalog.kras.filter((k) => !isRemovablePlaceholder(k));
  removed.forEach((k) => {
    delete d.kraWeights[k.id];
  });
  MockStore.save(store, { notify: false });
}

function ensureKraExpansion(kra) {
  if (_ui.expandedKraId === kra.id) return;
  _ui.expandedKraId = kra.id;
  _ui.expanded = new Set();
  const first = kra.criteria?.[0];
  if (first) _ui.expanded.add(first.id);
}

function effectiveWeights(weightsFromDraft) {
  if (_pendingWeights) return _pendingWeights;
  return weightsFromDraft;
}

function indicatorNeedsConfig(ind) {
  if (isSupportingEvidenceIndicator(ind)) return false;
  const k = ind.calculation?.kind;
  if (k === 'pending') return true;
  if (k === 'fixed_per_entry' && ind.maxPoints == null && ind.calculation?.maxPoints == null) return true;
  if (k === 'patent_stage') {
    const st = ind.calculation?.stages || ind.points;
    if (!st || !Object.keys(st).length) return true;
  }
  if (k === 'tiered_option') {
    const opts = ind.calculation?.options || ind.points;
    if (!opts || !Object.keys(opts).length) return true;
  }
  if (ind.pointRule === 'pending' || ind.pointRule === 'pending_external') return true;
  return false;
}

function indicatorPointsLabel(ind) {
  if (isSupportingEvidenceIndicator(ind)) return 'Supporting evidence';
  if (indicatorNeedsConfig(ind)) return 'Needs configuration';
  const k = ind.calculation?.kind || 'fixed_per_entry';
  if (k === 'set_sef_average') {
    const f = ind.calculation.factor ?? 0.36;
    const slots = ind.calculation.semesterCount ?? 6;
    const policy = ind.calculation.policy === 'average_available_max_six'
      ? 'avg available'
      : 'avg';
    return `${f} factor · ${policy} (max ${slots} slots)`;
  }
  if (k === 'fixed_per_entry') {
    const pts = ind.maxPoints ?? ind.calculation?.maxPoints ?? '—';
    if (ind.perService) return `${pts} pts per service`;
    return `${pts} pts per output`;
  }
  if (k === 'patent_stage') {
    const st = ind.calculation?.stages || ind.points || {};
    return `Patent A/${st.A ?? '—'} · P/${st.P ?? '—'} · G/${st.G ?? '—'}`;
  }
  if (k === 'tiered_option') {
    const opts = ind.calculation?.options || ind.points || {};
    const keys = Object.keys(opts);
    if (!keys.length) return 'Tiered options (needs values)';
    return keys.map((key) => `${key}: ${opts[key]}`).join(' · ');
  }
  if (k === 'structured_points' || ind.points) return 'Tiered reference points (legacy — select patent/tiered type)';
  if (k === 'role_matrix' || ind.matrix) return 'Role-based points';
  if (ind.maxPoints != null) return `${ind.maxPoints} pts max`;
  return 'Reference points configured';
}

export function renderConfig(root, title, { embedded = false } = {}) {
  if (!root) return;
  if (!embedded && title) title.textContent = 'Scoring Rules';
  void renderConfigBody(root, title, { embedded });
}

async function renderConfigBody(root, title, { embedded = false } = {}) {
  try {
    await renderConfigBodyInner(root, { embedded });
  } catch (e) {
    console.error(e);
    root.innerHTML = `<div class="card cfg-error" style="padding:1rem"><h3>Could not load scoring rules</h3>
      <p>${esc(e.message || 'Unknown error.')}</p>
      <button type="button" class="cfg-btn-secondary" id="cfgRenderRetry">Retry</button></div>`;
    root.querySelector('#cfgRenderRetry')?.addEventListener('click', () => renderConfig(root, title, { embedded }));
  }
}

async function renderConfigBodyInner(root, { embedded = false } = {}) {
  syncWeightsFromDom();

  const store = MockStore.load();
  ConfigRepository.loadContext(store);
  if (_session?.role !== 'reviewer') pruneEmptyPlaceholderKras(store);

  const readOnly = _session?.role === 'reviewer';
  const view = ConfigRepository.resolveRulesView(store, { readOnly });

  if (view.mode === 'no_published') {
    root.innerHTML = `${embedded ? pageIntro(SCREEN_INTRO.rules) : ''}
      <div class="card" style="padding:1rem"><p class="muted">No published scoring rules are available yet. Your administrator must publish a configuration.</p></div>`;
    return;
  }

  if (view.mode === 'uninitialized') {
    root.innerHTML = `${embedded ? pageIntro(SCREEN_INTRO.config) : ''}
      <div class="card" style="padding:1rem">
        <h3 style="margin-top:0">Initialize scoring rules</h3>
        <p class="muted">No draft or published configuration is stored yet. Start a draft from the official DBM–CHED JC3 workbook reference mapping. Nothing is published until you review and publish.</p>
        <p class="muted" style="font-size:0.9rem">${esc(SOURCE_CIRCULAR)}</p>
        <button type="button" class="cfg-btn-primary" id="cfgInitDraft">Initialize draft from reference catalog</button>
        <p id="cfgInitErr" class="fl-account-field-error" role="alert" hidden></p>
      </div>`;
    root.querySelector('#cfgInitDraft')?.addEventListener('click', async () => {
      const errEl = root.querySelector('#cfgInitErr');
      const btn = root.querySelector('#cfgInitDraft');
      errEl.hidden = true;
      btn.disabled = true;
      try {
        ConfigRepository.initializeDraftFromReference(store, _session?.email || 'admin');
        await persistConfigDraft(store);
        _onRefresh?.();
        renderConfig(root, null, { embedded });
      } catch (ex) {
        errEl.textContent = ex.message || 'Could not initialize draft.';
        errEl.hidden = false;
        btn.disabled = false;
      }
    });
    return;
  }

  const active = view.active;
  let draft = view.draft;
  let catalog = view.catalog;
  let weights = effectiveWeights(view.weights);

  if (!readOnly && (!isCatalogWorkbookComplete(catalog) || !catalogHasSetSefIntakeSupport(catalog))) {
    root.innerHTML = `<p class="muted" style="padding:1rem">Loading workbook reference catalog…</p>`;
    try {
      const repair = ConfigRepository.ensureDraftCatalogComplete(store, _session?.email || 'admin');
      draft = repair.draft;
      catalog = draft.catalog;
      weights = effectiveWeights(draft.kraWeights);
      if (repair.changed) {
        toast(`Restored ${repair.report.length} missing workbook reference item(s). Use Save Draft to persist.`);
      }
    } catch (ex) {
      root.innerHTML = `<div class="card cfg-error" style="padding:1rem"><h3>Could not load scoring rules</h3>
        <p>${esc(ex.message || 'Request failed.')}</p>
        <button type="button" class="cfg-btn-secondary" id="cfgCatalogRetry">Retry</button></div>`;
      root.querySelector('#cfgCatalogRetry')?.addEventListener('click', () => renderConfig(root, null, { embedded }));
      return;
    }
  }

  if (!_savedFingerprint && draft) _savedFingerprint = fingerprintDraft(store);

  const navigable = getNavigableKras(catalog);
  if (_ui.kraTab >= navigable.length) _ui.kraTab = 0;

  const draftStatus =
    readOnly || !draft
      ? readOnly
        ? ''
        : '<span class="muted">No open draft</span>'
      : '<span class="badge-status badge-submitted">Draft in progress</span>';
  const hiddenPlaceholders = catalog.kras.filter((k) => isRemovablePlaceholder(k)).length;

  root.innerHTML = `
    <section class="cfg-page${embedded ? ' cfg-page--embedded' : ''}" id="cfgPage" aria-labelledby="${embedded ? 'tab-btn-rules' : 'cfgHeading'}">
      ${
        embedded
          ? ''
          : `<header class="cfg-page-header cfg-page-header--compact">
        <h2 id="cfgHeading">Scoring Rules</h2>
        <p class="cfg-page-sub">Manage how faculty assessment points are calculated.</p>
      </header>`
      }
      ${embedded ? pageIntro(readOnly ? SCREEN_INTRO.rules : SCREEN_INTRO.config) : ''}
      <div class="cfg-sticky-stack" id="cfgStickyStack"></div>
      <div id="cfgKraPanel" role="tabpanel" class="cfg-kra-panel"></div>
      <div id="cfgToast" class="cfg-toast" role="status" aria-live="polite" hidden></div>
      <div id="cfgModalRoot"></div>
    </section>
  `;

  const sticky = root.querySelector('#cfgStickyStack');
  const publishedLabel = active
    ? `${esc(active.label || 'Active')} · ${esc(formatDate(active.effectiveDate))}`
    : 'Not published yet';
  sticky.innerHTML = `
    <div class="cfg-summary-strip">
      <div class="cfg-summary-main">
        <span><strong>Published:</strong> ${publishedLabel}</span>
        ${
          readOnly
            ? ''
            : `<span class="cfg-summary-sep" aria-hidden="true">|</span><span><strong>Editing:</strong> ${draftStatus}</span>`
        }
        ${readOnly ? '<span class="badge-status badge-approved cfg-readonly-tag">Read-only</span>' : ''}
      </div>
      <details class="cfg-details-block">
        <summary>Details</summary>
        <div class="cfg-details-body">
          ${readOnly ? '' : `<section><h4>How this works</h4>${HOW_IT_WORKS}</section>`}
          <section><h4>Version details</h4>
            <dl class="cfg-dl">
              <dt>Published ID</dt><dd>${active ? esc(active.id) : '—'}</dd>
              ${draft && !readOnly ? `<dt>Draft ID</dt><dd>${esc(draft.id)}</dd>` : ''}
              <dt>Catalog</dt><dd>${esc(catalog.version || '—')}</dd>
            </dl>
          </section>
          <section><h4>View source</h4><p class="muted">${esc(SOURCE_CIRCULAR)}</p></section>
        </div>
      </details>
    </div>
    ${readOnly ? '' : `
    <div class="cfg-toolbar" role="toolbar" aria-label="Scoring rules actions">
      <button type="button" class="cfg-btn-secondary" id="cfgSaveDraft">Save Draft</button>
      <button type="button" class="cfg-btn-primary" id="cfgReviewPublish">Review &amp; Publish</button>
      <button type="button" class="cfg-btn-menu" id="cfgMoreBtn" aria-haspopup="menu" aria-expanded="false">More actions ▾</button>
      <span id="cfgDirtyChip" class="cfg-dirty-chip" ${_ui.dirty ? '' : 'hidden'}>Unsaved changes</span>
      <div id="cfgMoreMenu" class="cfg-more-menu" role="menu" hidden>
        <button type="button" id="cfgHistBtn" role="menuitem">Version history</button>
        <button type="button" id="addKra" role="menuitem">Add KRA</button>
        ${hiddenPlaceholders ? `<button type="button" id="cfgPruneKra" role="menuitem">Remove empty draft KRAs (${hiddenPlaceholders})</button>` : ''}
      </div>
    </div>`}
  `;

  renderKraPanel(catalog, weights, readOnly, root);

  if (!readOnly) bindAdminActions(store, root);
  updateDirtyChip();
}

function kraTabLabel(kra) {
  if (KRA_TAB_LABELS[kra.id]) return KRA_TAB_LABELS[kra.id];
  return kra.name.replace(/^KRA [IVX]+ –\s*/i, '') || kra.name;
}

function readWeightsPct() {
  // Scoring Rules no longer edits KRA weights in the UI. Preserve stored draft/published weights.
  if (_pendingWeights) return { ..._pendingWeights };
  const store = MockStore.load();
  const d = ConfigRepository.getDraft(store);
  const active = ConfigRepository.getActivePublished(store);
  return { ...(d?.kraWeights || active?.kraWeights || {}) };
}

function updateDirtyChip() {
  const chip = document.getElementById('cfgDirtyChip');
  if (chip) chip.hidden = !_ui.dirty;
}

function toast(text, isErr) {
  const el = document.getElementById('cfgToast');
  if (!el) return;
  el.textContent = text;
  el.classList.toggle('cfg-toast--err', !!isErr);
  el.hidden = false;
  clearTimeout(el._hideTimer);
  el._hideTimer = setTimeout(() => {
    el.hidden = true;
  }, 4200);
}

function selectKraTab(navIndex, readOnly) {
  syncWeightsFromDom();
  _ui.kraTab = navIndex;
  const store = MockStore.load();
  const activePub = ConfigRepository.getActivePublished(store);
  const d = ConfigRepository.getDraft(store);
  const cat = d?.catalog || activePub?.catalog;
  if (!cat) return;
  const weights = effectiveWeights(d?.kraWeights || activePub?.kraWeights || {});
  const cfgRoot = document.getElementById('cfgPage') || document;
  renderKraPanel(cat, weights, readOnly, cfgRoot);
}

function criterionMaxPoints(crit) {
  if (crit.capMaxPoints != null) return crit.capMaxPoints;
  if (crit.maxPoints != null) return crit.maxPoints;
  return null;
}

function criterionMaxLabel(crit) {
  const n = criterionMaxPoints(crit);
  return n != null ? `Maximum ${n} points` : 'No maximum set';
}

function renderKraNav(navigable) {
  const host = document.getElementById('cfgKraNavHost');
  if (!host) return;
  const tabs = navigable
    .map(({ kra }, i) => {
      const selected = i === _ui.kraTab;
      const label = KRA_TAB_LABELS[kra.id] || kraTabLabel(kra);
      return `<button type="button" class="cfg-kra-tab" role="tab" aria-selected="${selected}" data-kra-tab="${i}">${esc(label)}</button>`;
    })
    .join('');
  const options = navigable
    .map(({ kra }, i) => {
      const label = KRA_TAB_LABELS[kra.id] || kraTabLabel(kra);
      return `<option value="${i}" ${i === _ui.kraTab ? 'selected' : ''}>${esc(label)}</option>`;
    })
    .join('');

  host.innerHTML = `
    <div class="cfg-kra-tabs" role="tablist" aria-label="Key result areas">${tabs}</div>
    <label class="cfg-kra-select-wrap">KRA
      <select id="cfgKraSelect" class="cfg-kra-select" aria-label="Select KRA">${options}</select>
    </label>`;

  const readOnly = _session?.role === 'reviewer';
  host.querySelectorAll('[data-kra-tab]').forEach((btn) => {
    btn.addEventListener('click', () => selectKraTab(Number(btn.dataset.kraTab), readOnly));
  });
  host.querySelector('#cfgKraSelect')?.addEventListener('change', (e) => {
    selectKraTab(Number(e.target.value), readOnly);
  });
}

function renderKraPanel(catalog, weights, readOnly, root = document) {
  const navigable = getNavigableKras(catalog);
  const entry = navigable[_ui.kraTab];
  const kra = entry ? catalog.kras[entry.catalogIndex] : null;
  const panel = root.querySelector ? root.querySelector('#cfgKraPanel') : document.getElementById('cfgKraPanel');
  if (!panel) return;
  if (!kra || !navigable.length) {
    panel.innerHTML = `<div class="card" style="padding:1rem"><p class="muted">Workbook reference catalog is incomplete.</p>
      <button type="button" class="cfg-btn-secondary" id="cfgKraRepairRetry">Retry load</button></div>`;
    panel.querySelector('#cfgKraRepairRetry')?.addEventListener('click', () => {
      const cfgRoot = panel.closest('#cfgPage') || document.getElementById('evalTabRules');
      if (cfgRoot) renderConfig(cfgRoot, null, { embedded: !!cfgRoot.closest('.fl-eval-settings') });
    });
    return;
  }

  ensureKraExpansion(kra);
  const q = _ui.search.trim().toLowerCase();
  const criteriaHtml = kra.criteria
    .map((crit) => {
      const scoringPool = scoringIndicatorsForCriterion(crit);
      const indicators = scoringPool.filter((ind) => {
        if (_ui.needsOnly && !indicatorNeedsConfig(ind)) return false;
        if (q && !ind.name.toLowerCase().includes(q) && !crit.name.toLowerCase().includes(q)) return false;
        return true;
      });
      if (_ui.needsOnly && !indicators.length) return '';

      const expanded = _ui.expanded.has(crit.id);
      const indCount = scoringPool.length;
      const countLabel = `${indCount} indicator${indCount === 1 ? '' : 's'}`;

      const indRows = indicators
        .map(
          (ind) => `<div class="cfg-ind-row">
            <span style="flex:1;min-width:10rem">${esc(ind.name)}</span>
            <span class="cfg-ind-points ${isSupportingEvidenceIndicator(ind) ? 'badge-supporting' : indicatorNeedsConfig(ind) ? 'badge-required' : ''}">${esc(indicatorPointsLabel(ind))}</span>
            ${readOnly ? '' : `<button type="button" class="cfg-btn-ghost btn-sm" data-edit-ind="${escAttr(ind.id)}" data-crit="${escAttr(crit.id)}" data-kra="${escAttr(kra.id)}">Edit</button>`}
          </div>`
        )
        .join('');

      return `<article class="cfg-criterion-card" data-crit-card="${escAttr(crit.id)}">
        <div class="cfg-criterion-head${readOnly ? ' cfg-criterion-head--readonly' : ''}" data-toggle-crit="${escAttr(crit.id)}" role="button" tabindex="0" aria-expanded="${expanded}">
          <span class="cfg-chevron" aria-hidden="true">${expanded ? '▾' : '▸'}</span>
          <h4 class="cfg-crit-title">${esc(crit.name)}</h4>
          <span class="cfg-crit-max">${esc(criterionMaxLabel(crit))}</span>
          <span class="cfg-crit-count">${esc(countLabel)}</span>
          ${readOnly ? '' : `<button type="button" class="cfg-btn-ghost btn-sm cfg-crit-edit" data-edit-crit="${escAttr(crit.id)}" data-kra="${escAttr(kra.id)}">Edit</button>`}
        </div>
        ${expanded ? `<div class="cfg-criterion-body">${indRows || '<p class="muted">No matching indicators.</p>'}
          ${readOnly ? '' : `<button type="button" class="cfg-btn-ghost btn-sm" data-add-ind="${escAttr(crit.id)}" data-kra="${escAttr(kra.id)}">Add indicator</button>`}
        </div>` : ''}
      </article>`;
    })
    .filter(Boolean)
    .join('');

  const policyBtn =
    readOnly || !['kra-III', 'kra-IV'].includes(kra.id)
      ? ''
      : `<button type="button" class="cfg-btn-ghost btn-sm" id="cfgKraScoringPolicy" data-kra="${escAttr(kra.id)}">KRA scoring policy</button>`;

  panel.innerHTML = `
    <div class="cfg-kra-workspace">
      <div class="cfg-kra-nav-slot" id="cfgKraNavHost"></div>
      <div class="cfg-kra-heading">
        <h3>${esc(kra.name)}</h3>
        <div class="cfg-kra-heading-actions">
          ${policyBtn}
        </div>
      </div>
      <p class="muted cfg-kra-weight-hint">Assessment weights by current faculty rank are set in Rank simulation.</p>
      <div class="cfg-ind-toolbar">
        <input type="search" id="cfgIndSearch" class="cfg-search" placeholder="Search indicators" value="${escAttr(_ui.search)}" aria-label="Search indicators"/>
        <label class="cfg-filter-check"><input type="checkbox" id="cfgNeedsFilter" ${_ui.needsOnly ? 'checked' : ''}/> Needs configuration</label>
        ${readOnly ? '' : `<button type="button" class="cfg-btn-ghost btn-sm" id="addCrit" data-kra="${escAttr(kra.id)}">Add criterion</button>`}
      </div>
      <div class="cfg-criteria-list">${criteriaHtml || '<p class="muted">No criteria match your filters.</p>'}</div>
    </div>
  `;

  renderKraNav(navigable);

  panel.querySelector('#cfgKraScoringPolicy')?.addEventListener('click', (e) => {
    openKraScoringPolicyEditor(e.currentTarget.dataset.kra);
  });

  panel.querySelector('#cfgIndSearch')?.addEventListener('input', (e) => {
    const val = e.target.value;
    _ui.search = val;
    const needle = val.trim().toLowerCase();
    if (needle) {
      kra.criteria.forEach((c) => {
        const match =
          c.name.toLowerCase().includes(needle) ||
          c.indicators.some((ind) => ind.name.toLowerCase().includes(needle));
        if (match) _ui.expanded.add(c.id);
      });
    }
    renderKraPanel(catalog, weights, readOnly);
  });
  panel.querySelector('#cfgNeedsFilter')?.addEventListener('change', (e) => {
    _ui.needsOnly = e.target.checked;
    renderKraPanel(catalog, weights, readOnly);
  });

  panel.querySelectorAll('[data-toggle-crit]').forEach((head) => {
    const toggle = () => {
      const id = head.dataset.toggleCrit;
      if (_ui.expanded.has(id)) _ui.expanded.delete(id);
      else _ui.expanded.add(id);
      renderKraPanel(catalog, weights, readOnly);
    };
    head.addEventListener('click', (e) => {
      if (e.target.closest('button')) return;
      toggle();
    });
    head.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggle();
      }
    });
  });

  panel.querySelectorAll('[data-edit-ind]').forEach((btn) =>
    btn.addEventListener('click', () => openIndicatorEditor(btn.dataset.kra, btn.dataset.crit, btn.dataset.editInd))
  );
  panel.querySelectorAll('[data-edit-crit]').forEach((btn) =>
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      openCriterionEditor(btn.dataset.kra, btn.dataset.crit);
    })
  );
  panel.querySelectorAll('[data-add-ind]').forEach((btn) =>
    btn.addEventListener('click', () => addIndicator(btn.dataset.kra, btn.dataset.addInd))
  );
  document.getElementById('addCrit')?.addEventListener('click', (e) => addCriterion(e.currentTarget.dataset.kra));
}

function bindAdminActions(store, root = document) {
  const moreBtn = root.querySelector('#cfgMoreBtn');
  const moreMenu = root.querySelector('#cfgMoreMenu');
  moreBtn?.addEventListener('click', () => {
    const open = moreMenu.hidden;
    moreMenu.hidden = !open;
    moreBtn.setAttribute('aria-expanded', String(open));
  });
  moreMenu?.addEventListener('click', (e) => e.stopPropagation());

  root.querySelector('#cfgSaveDraft')?.addEventListener('click', () => saveDraft(store));
  root.querySelector('#cfgReviewPublish')?.addEventListener('click', () => openPublishPanel(store));
  root.querySelector('#cfgHistBtn')?.addEventListener('click', () => {
    moreMenu.hidden = true;
    openHistoryModal(store);
  });
  root.querySelector('#addKra')?.addEventListener('click', () => {
    moreMenu.hidden = true;
    openAddKraForm(store);
  });
  root.querySelector('#cfgPruneKra')?.addEventListener('click', () => {
    moreMenu.hidden = true;
    pruneEmptyPlaceholderKras(store);
    toast('Removed empty draft KRAs.');
    _onRefresh?.();
  });
}

async function saveDraft(store) {
  try {
    const w = readWeightsPct();
    const d = requireDraft(store);
    ConfigRepository.saveDraft(store, {
      catalog: d.catalog,
      kraWeights: w,
      actor: _session.email,
      summary: 'Draft saved from configuration UI',
    });
    await persistConfigDraft(store);
    _pendingWeights = null;
    _savedFingerprint = fingerprintDraft(store);
    _ui.dirty = false;
    toast('Draft saved.');
    updateDirtyChip();
    _onRefresh?.();
  } catch (e) {
    toast(e.message, true);
  }
}

function slugKraId(name) {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 24);
  return `kra-custom-${base || 'item'}-${Date.now().toString(36).slice(-4)}`;
}

function openAddKraForm(store) {
  const d = requireDraft(store);
  const opener = document.getElementById('addKra');
  const modal = openCenteredModal({
    title: 'Add KRA',
    lede: 'Saved to the draft catalog; main tabs remain the four JC3 KRAs.',
    size: 'md',
    bodyHtml: `
      <form id="addKraForm" class="cfg-form">
        <label>Official KRA name<input name="name" required placeholder="e.g. KRA V – Community Engagement" minlength="3" data-autofocus/></label>
        <p id="addKraErr" class="cfg-field-error" role="alert"></p>
      </form>`,
    footerHtml: `
      <button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Cancel</button>
      <button type="submit" form="addKraForm" class="cfg-btn-primary">Save KRA</button>`,
    opener,
  });
  if (!modal) return;

  const form = modal.dialog.querySelector('#addKraForm');
  form?.addEventListener('submit', (e) => {
    e.preventDefault();
    const err = modal.dialog.querySelector('#addKraErr');
    err.textContent = '';
    const name = new FormData(e.target).get('name').toString().trim();
    if (d.catalog.kras.some((k) => k.name.toLowerCase() === name.toLowerCase())) {
      err.textContent = 'A KRA with this name already exists.';
      return;
    }
    const id = slugKraId(name);
    if (d.catalog.kras.some((k) => k.id === id)) {
      err.textContent = 'Generated ID conflict — try a slightly different name.';
      return;
    }
    d.catalog.kras.push({ id, name, maxPoints: 100, weight: 0, criteria: [] });
    d.kraWeights[id] = 0;
    persistConfigDraft(store)
      .then(() => {
        modal.close();
      })
      .catch((err) => {
        err = err;
        toast(err?.message || 'Could not save draft.', true);
      });
    toast('KRA saved to draft catalog. Main tabs remain the four JC3 KRAs until you add criteria.');
    _onRefresh?.();
  });
}

function slugCriterionId(name) {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 28);
  return `crit-${base || 'item'}-${Date.now().toString(36).slice(-5)}`;
}

function slugIndicatorId(name) {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 28);
  return `ind-${base || 'item'}-${Date.now().toString(36).slice(-5)}`;
}

/**
 * Temporary creation form — nothing is written to the draft until Save.
 * Cancel / dismiss leaves no placeholder criterion.
 */
function addCriterion(kraId) {
  const store = MockStore.load();
  const d = requireDraft(store);
  const kra = d.catalog.kras.find((k) => k.id === kraId);
  if (!kra) return toast('KRA not found.', true);

  const opener = document.querySelector(`#addCrit[data-kra="${CSS.escape(kraId)}"]`) || document.getElementById('addCrit');
  const modal = openCenteredModal({
    title: 'Add criterion',
    lede: 'Saved only when you confirm. Cancel leaves the draft unchanged.',
    size: 'md',
    bodyHtml: `
      <form id="addCritForm" class="cfg-form">
        <label>Criterion name
          <input name="name" required minlength="3" maxlength="160" data-autofocus
            placeholder="e.g. Criterion D – …" autocomplete="off" />
        </label>
        <label>Maximum points (optional)
          <input type="number" name="cap" min="0" step="0.01" />
        </label>
        <p id="addCritErr" class="cfg-field-error" role="alert"></p>
      </form>`,
    footerHtml: `
      <button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Cancel</button>
      <button type="submit" form="addCritForm" class="cfg-btn-primary" id="addCritSave">Save criterion</button>`,
    opener,
  });
  if (!modal) return;

  let saving = false;
  const form = modal.dialog.querySelector('#addCritForm');
  form?.addEventListener('submit', (e) => {
    e.preventDefault();
    if (saving) return;
    const err = modal.dialog.querySelector('#addCritErr');
    const saveBtn = modal.dialog.querySelector('#addCritSave');
    err.textContent = '';
    const fd = new FormData(e.target);
    const name = String(fd.get('name') || '').trim();
    if (name.length < 3) {
      err.textContent = 'Enter a criterion name (at least 3 characters).';
      return;
    }
    if (/^new criterion$/i.test(name)) {
      err.textContent = 'Choose a specific criterion name — placeholders are not saved.';
      return;
    }
    if ((kra.criteria || []).some((c) => (c.name || '').trim().toLowerCase() === name.toLowerCase())) {
      err.textContent = 'A criterion with this name already exists in this KRA.';
      return;
    }
    const capRaw = String(fd.get('cap') || '').trim();
    const capMaxPoints = capRaw === '' ? null : Number(capRaw);
    if (capRaw !== '' && (!Number.isFinite(capMaxPoints) || capMaxPoints < 0)) {
      err.textContent = 'Maximum points must be a number ≥ 0.';
      return;
    }
    let id = slugCriterionId(name);
    if ((kra.criteria || []).some((c) => c.id === id)) {
      id = `crit-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
    }
    saving = true;
    if (saveBtn) saveBtn.disabled = true;
    kra.criteria = kra.criteria || [];
    kra.criteria.push({ id, name, capMaxPoints, indicators: [] });
    _ui.expanded.add(id);
    persistDraftSafe(store)
      .then(() => {
        modal.close();
        const w = readWeightsPct();
        renderKraPanel(d.catalog, w, false);
        toast('Criterion saved to draft.');
        _ui.dirty = true;
        updateDirtyChip();
      })
      .catch((ex) => {
        // Roll back in-memory insert if server persist failed.
        kra.criteria = kra.criteria.filter((c) => c.id !== id);
        _ui.expanded.delete(id);
        saving = false;
        if (saveBtn) saveBtn.disabled = false;
        err.textContent = ex?.message || 'Could not save criterion.';
      });
  });
}

/**
 * Temporary creation form — Cancel leaves no saved indicator placeholder.
 */
function addIndicator(kraId, critId) {
  const store = MockStore.load();
  const d = requireDraft(store);
  const kra = d.catalog.kras.find((k) => k.id === kraId);
  const crit = kra?.criteria.find((c) => c.id === critId);
  if (!crit) return toast('Criterion not found.', true);

  const opener = document.querySelector(`[data-add-ind="${CSS.escape(critId)}"]`);
  const modal = openCenteredModal({
    title: 'Add indicator',
    lede: 'Saved only when you confirm. Cancel leaves the draft unchanged.',
    size: 'md',
    bodyHtml: `
      <form id="addIndForm" class="cfg-form">
        <label>Indicator name
          <input name="name" required minlength="3" maxlength="200" data-autofocus
            placeholder="e.g. Membership in …" autocomplete="off" />
        </label>
        <label>Reference / max points (optional)
          <input type="number" name="maxPoints" min="0" step="0.01" />
        </label>
        <p id="addIndErr" class="cfg-field-error" role="alert"></p>
      </form>`,
    footerHtml: `
      <button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Cancel</button>
      <button type="submit" form="addIndForm" class="cfg-btn-primary" id="addIndSave">Save indicator</button>`,
    opener,
  });
  if (!modal) return;

  let saving = false;
  modal.dialog.querySelector('#addIndForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    if (saving) return;
    const err = modal.dialog.querySelector('#addIndErr');
    const saveBtn = modal.dialog.querySelector('#addIndSave');
    err.textContent = '';
    const fd = new FormData(e.target);
    const name = String(fd.get('name') || '').trim();
    if (name.length < 3) {
      err.textContent = 'Enter an indicator name (at least 3 characters).';
      return;
    }
    if (/^new indicator$/i.test(name)) {
      err.textContent = 'Choose a specific indicator name — placeholders are not saved.';
      return;
    }
    if ((crit.indicators || []).some((i) => (i.name || '').trim().toLowerCase() === name.toLowerCase())) {
      err.textContent = 'An indicator with this name already exists in this criterion.';
      return;
    }
    const maxRaw = String(fd.get('maxPoints') || '').trim();
    const maxPoints = maxRaw === '' ? 0 : Number(maxRaw);
    if (maxRaw !== '' && (!Number.isFinite(maxPoints) || maxPoints < 0)) {
      err.textContent = 'Max points must be a number ≥ 0.';
      return;
    }
    let indId = slugIndicatorId(name);
    if ((crit.indicators || []).some((i) => i.id === indId)) {
      indId = `ind-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
    }
    const ind = {
      id: indId,
      name,
      description: '',
      maxPoints,
      sourceRef: '',
      conditions: [],
      documentaryRequirements: [],
      calculation: { kind: 'fixed_per_entry', maxPoints },
      contributionAllocation: { mode: 'percent', defaultPercent: 100 },
    };
    saving = true;
    if (saveBtn) saveBtn.disabled = true;
    crit.indicators = crit.indicators || [];
    crit.indicators.push(ind);
    _ui.expanded.add(critId);
    persistDraftSafe(store)
      .then(() => {
        modal.close();
        openIndicatorEditor(kraId, critId, indId);
      })
      .catch((ex) => {
        crit.indicators = crit.indicators.filter((i) => i.id !== indId);
        saving = false;
        if (saveBtn) saveBtn.disabled = false;
        err.textContent = ex?.message || 'Could not save indicator.';
      });
  });
}

function diffDraftVsActive(active, draft, weights) {
  if (!active?.catalog) {
    return ['First publication — no prior published configuration.'];
  }
  const lines = [];
  Object.keys(weights).forEach((kid) => {
    const a = active.kraWeights[kid] ?? 0;
    const b = weights[kid] ?? 0;
    if (Math.abs(a - b) > 0.0001) {
      lines.push(`Weight ${kid}: ${decimalToPct(a)}% → ${decimalToPct(b)}%`);
    }
  });
  const countInd = (cat) =>
    cat.kras.reduce((n, k) => n + k.criteria.reduce((m, c) => m + c.indicators.length, 0), 0);
  const aCount = countInd(active.catalog);
  const dCount = countInd(draft.catalog);
  if (aCount !== dCount) lines.push(`Indicator count: ${aCount} → ${dCount}`);
  if (!lines.length) lines.push('No structural weight changes detected; review indicator edits before publishing.');
  return lines;
}

function openPublishPanel(store) {
  const opener = document.getElementById('cfgReviewPublish');
  const active = ConfigRepository.getActivePublished(store);
  const draft = requireDraft(store);
  const weights = readWeightsPct();
  const validation = validateCatalog(draft.catalog, weights);
  const ctx = store.assessmentConfig;
  const changes = diffDraftVsActive(active, draft, weights);

  const sample = store.assessments['fac-001'];
  let previewHtml = '<p class="muted">No sample faculty assessment loaded for preview.</p>';
  if (sample && active?.catalog) {
    const estActive = computeKraSummaries(sample, active.catalog, active.kraWeights).overallWeighted;
    const estDraft = computeKraSummaries(sample, draft.catalog, weights).overallWeighted;
    previewHtml = `<p class="muted">Sample faculty weighted total — published: <strong>${estActive.toFixed(2)}</strong> · draft rules: <strong>${estDraft.toFixed(2)}</strong>. Preview only; pinned assessments stay unchanged.</p>`;
  } else if (sample) {
    const estDraft = computeKraSummaries(sample, draft.catalog, weights).overallWeighted;
    previewHtml = `<p class="muted">Sample faculty weighted total under draft rules: <strong>${estDraft.toFixed(2)}</strong>. Preview only.</p>`;
  }

  const host = modalHost();
  if (!host) return;

  host.innerHTML = `
    <div class="fl-modal-overlay" id="cfgPublishOverlay" role="presentation">
      <div class="fl-modal-dialog fl-modal-dialog--lg" role="dialog" aria-modal="true" aria-labelledby="cfgPubTitle" id="cfgPublishDialog">
        <header class="fl-modal-dialog__header">
          <h2 id="cfgPubTitle">Review &amp; Publish</h2>
          <button type="button" class="fl-modal-close" id="cfgPubDismiss" aria-label="Close dialog">×</button>
        </header>
        <div class="fl-modal-dialog__body">
          <section class="fl-publish-section" aria-labelledby="cfgPubSecChanges">
            <h3 id="cfgPubSecChanges">Changes</h3>
            <ul>${changes.map((c) => `<li>${esc(c)}</li>`).join('')}</ul>
          </section>
          <section class="fl-publish-section" aria-labelledby="cfgPubSecValidation">
            <h3 id="cfgPubSecValidation">Validation</h3>
            <p id="cfgPubValidationMsg" class="${validation.ok ? 'cfg-validation-ok' : 'cfg-field-error'}">${
              validation.ok ? 'All checks passed.' : esc(validation.message)
            }</p>
          </section>
          <section class="fl-publish-section" aria-labelledby="cfgPubSecDate">
            <h3 id="cfgPubSecDate">Effective date</h3>
            <label class="fl-date-label" for="cfgEffDate">Applies starting
              <input type="date" id="cfgEffDate" required data-autofocus/>
            </label>
          </section>
          <section class="fl-publish-section" aria-labelledby="cfgPubSecPreview">
            <h3 id="cfgPubSecPreview">Calculation preview</h3>
            <label class="fl-publish-preview-toggle">
              <input type="checkbox" id="cfgPreviewPub" ${ctx.previewDraft ? 'checked' : ''}/>
              Preview draft in calculations (does not alter saved faculty assessments)
            </label>
            ${previewHtml}
          </section>
        </div>
        <footer class="fl-modal-dialog__footer">
          <p id="cfgPubFooterErr" class="fl-modal-footer-err" role="alert" aria-live="polite"></p>
          <button type="button" class="cfg-btn-secondary" id="cfgPubClose">Cancel</button>
          <button type="button" class="cfg-btn-primary" id="cfgPublishConfirm" disabled>Publish</button>
        </footer>
      </div>
    </div>
  `;

  const overlay = host.querySelector('#cfgPublishOverlay');
  const dialog = host.querySelector('#cfgPublishDialog');
  const closeDialog = () => teardownModal(host, opener);

  bindModalShell({
    host,
    overlay,
    dialog,
    onRequestClose: closeDialog,
    restoreFocusEl: opener,
  });

  const publishBtn = document.getElementById('cfgPublishConfirm');
  const footerErr = document.getElementById('cfgPubFooterErr');
  const dateInput = document.getElementById('cfgEffDate');

  const refreshPublishState = () => {
    const eff = dateInput?.value;
    const w = readWeightsPct();
    const d = ConfigRepository.getDraft(store) || draft;
    const v = validateCatalog(d.catalog, w);
    const validationEl = document.getElementById('cfgPubValidationMsg');
    if (validationEl) {
      validationEl.className = v.ok ? 'cfg-validation-ok' : 'cfg-field-error';
      validationEl.textContent = v.ok ? 'All checks passed.' : v.message;
    }
    const problems = [];
    if (!v.ok) problems.push(v.message);
    if (!eff) problems.push('Choose an effective date.');
    footerErr.textContent = problems.join(' ');
    publishBtn.disabled = problems.length > 0;
  };

  dateInput?.addEventListener('input', refreshPublishState);
  dateInput?.addEventListener('change', refreshPublishState);
  refreshPublishState();

  document.getElementById('cfgPubClose')?.addEventListener('click', closeDialog);
  document.getElementById('cfgPubDismiss')?.addEventListener('click', closeDialog);

  document.getElementById('cfgPreviewPub')?.addEventListener('change', (e) => {
    ConfigRepository.setPreviewDraft(store, e.target.checked);
    MockStore.save(store);
  });

  publishBtn?.addEventListener('click', async () => {
    footerErr.textContent = '';
    try {
      const eff = dateInput?.value;
      if (!eff) {
        footerErr.textContent = 'Choose an effective date.';
        dateInput?.focus();
        return;
      }
      const w = readWeightsPct();
      const d = requireDraft(store);
      const v = validateCatalog(d.catalog, w);
      if (!v.ok) {
        footerErr.textContent = v.message;
        return;
      }
      ConfigRepository.saveDraft(store, { catalog: d.catalog, kraWeights: w, actor: _session.email, summary: 'Pre-publish save' });
      ConfigRepository.publishDraft(store, { effectiveDate: eff, actor: _session.email, summary: 'Published via admin UI' });
      await PortalApi.publishCatalog({ assessmentConfig: store.assessmentConfig });
      await bootstrapPortal({ full: true, force: true });
      _pendingWeights = null;
      _savedFingerprint = '';
      _ui.dirty = false;
      teardownModal(host, opener);
      toast('Published. Faculty assessments keep their pinned version.');
      _onRefresh?.();
    } catch (e) {
      footerErr.textContent = e.message;
    }
  });
}

function openHistoryModal(store) {
  const versions = [...store.assessmentConfig.versions].sort((a, b) =>
    (b.publishedAt || b.changeHistory?.[0]?.at || '').localeCompare(a.publishedAt || a.changeHistory?.[0]?.at || '')
  );
  const rows = versions
    .map((v) => {
      const last = v.changeHistory?.[v.changeHistory.length - 1];
      return `<tr><td class="muted">${esc(v.id)}</td><td>${esc(v.status)}</td><td>${esc(formatDate(v.effectiveDate))}</td><td>${v.publishedAt ? esc(new Date(v.publishedAt).toLocaleString()) : '—'}</td>
        <td style="font-size:0.85rem">${last ? esc(`${last.summary} (${last.actor})`) : '—'}</td></tr>`;
    })
    .join('');

  const opener = document.getElementById('cfgHistBtn');
  openCenteredModal({
    title: 'Version history',
    size: 'lg',
    bodyHtml: `<div class="table-wrap"><table><thead><tr><th>ID</th><th>Status</th><th>Effective</th><th>Published</th><th>Changes</th></tr></thead>
        <tbody>${rows}</tbody></table></div>`,
    footerHtml: `<button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Close</button>`,
    opener,
  });
}

function openCriterionEditor(kraId, critId) {
  const store = MockStore.load();
  const draft = requireDraft(store);
  const kra = draft.catalog.kras.find((k) => k.id === kraId);
  const crit = kra?.criteria.find((c) => c.id === critId);
  if (!crit) return;

  const modal = openDrawerModal({
    opener: null,
    panelHtml: `
      <aside class="cfg-side-panel" role="dialog" aria-labelledby="critEditTitle">
        <h3 id="critEditTitle">Edit criterion</h3>
        <p class="muted">${esc(kra.name)}</p>
        <form id="critForm" class="cfg-form">
          <section class="cfg-form-section"><h4>Basic information</h4>
            <label>Name<input required name="name" value="${escAttr(crit.name)}" data-autofocus/></label>
          </section>
          <section class="cfg-form-section"><h4>Points &amp; limits</h4>
            <label>Maximum points (criterion cap)<input type="number" min="0" step="0.01" name="cap" value="${crit.capMaxPoints ?? ''}"/>
            <span class="muted" style="font-size:0.85rem;font-weight:400">Caps total points counted in this criterion.</span></label>
          </section>
          <details style="margin-bottom:1rem"><summary>Technical details</summary>
            <p class="muted" style="font-size:0.85rem">ID: ${esc(crit.id)}</p>
          </details>
          <div style="display:flex;gap:0.75rem">
            <button type="button" class="cfg-btn-secondary" id="closeCrit">Cancel</button>
            <button type="submit" class="cfg-btn-primary">Save changes</button>
          </div>
        </form>
      </aside>`,
  });
  if (!modal) return;

  modal.dialog?.querySelector('#closeCrit')?.addEventListener('click', () => modal.close());
  modal.dialog?.querySelector('#critForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    crit.name = fd.get('name').trim();
    crit.capMaxPoints = fd.get('cap') === '' ? null : Number(fd.get('cap'));
    persistDraftFromEditor(store);
    modal.close();
    _onRefresh?.();
  });
}

function openIndicatorEditor(kraId, critId, indId) {
  const store = MockStore.load();
  const draft = requireDraft(store);
  const found = findIndicatorInCatalog(draft.catalog, indId);
  if (!found) return;
  const { kra, crit, ind } = found;

  if (isSupportingEvidenceIndicator(ind)) {
    openSupportingEvidenceEditor(kra, crit, ind);
    return;
  }

  const optSource = ind.calculation?.options || ind.points || {};
  const tierKeys = Object.keys(optSource);
  const defaultTiers = ['local', 'international', 'new', 'updated'];
  const tiersForForm = tierKeys.length ? tierKeys : defaultTiers;
  const tierInputsHtml = tiersForForm
    .map((t) => {
      const val = optSource[t] ?? '';
      return `<label>${esc(t)} points<input type="number" step="0.01" min="0" name="tierPts_${escAttr(t)}" value="${val}"/></label>`;
    })
    .join('');
  const rateSource = ind.calculation?.rates || {};
  const rateKeys = Object.keys(rateSource);
  const rateInputsHtml = (rateKeys.length ? rateKeys : ['role_a', 'role_b'])
    .map((t) => {
      const val = rateSource[t] ?? '';
      return `<label>${esc(t)} (pts/year)<input type="number" step="0.01" min="0" name="ratePts_${escAttr(t)}" value="${val}"/></label>`;
    })
    .join('');

  const modal = openDrawerModal({
    opener: null,
    panelHtml: `
      <aside class="cfg-side-panel" role="dialog" aria-labelledby="indEditTitle">
        <h3 id="indEditTitle">Edit scoring rule</h3>
        <p class="muted">${esc(kra.name)} → ${esc(crit.name)}</p>
        <form id="indForm" class="cfg-form">
          <section class="cfg-form-section"><h4>Basic information</h4>
            <label>Name<input required name="name" value="${escAttr(ind.name)}"/></label>
            <label>Description<textarea name="description" rows="2">${escAttr(ind.description || '')}</textarea></label>
          </section>
          <section class="cfg-form-section"><h4>Points &amp; limits</h4>
            <p class="muted" style="font-size:0.85rem;margin:0 0 0.5rem">Reference points count toward faculty totals until a criterion cap applies. Maximum points limits what this indicator can contribute.</p>
            <label>Reference / max points<input type="number" step="0.01" min="0" name="maxPoints" value="${ind.maxPoints ?? ''}" id="indMaxPts"/></label>
            <label>Criterion cap<input type="number" min="0" name="critCap" value="${crit.capMaxPoints ?? ''}"/></label>
          </section>
          <section class="cfg-form-section"><h4>Calculation settings</h4>
            <label>Calculation type<select name="calcKind">
              ${['fixed_per_entry', 'set_sef_average', 'role_matrix', 'patent_stage', 'tiered_option', 'yearly_rate', 'designation_matrix', 'income_tier', 'hourly_tier', 'structured_points', 'pending'].map((k) => `<option value="${k}" ${ind.calculation?.kind === k ? 'selected' : ''}>${labelCalcKind(k)}</option>`).join('')}
            </select></label>
            <div id="setFactorWrap">
              <label>SET/SEF factor (average-based)<input type="number" step="0.01" name="setFactor" value="${ind.calculation?.factor ?? 0.36}"/></label>
              <label>Max semester slots<input type="number" min="1" max="6" name="semesterCount" value="${ind.calculation?.semesterCount ?? 6}"/></label>
              <label>Criterion A policy<select name="setSefPolicy">
                <option value="average_available_max_six" ${(ind.calculation?.policy || 'average_available_max_six') === 'average_available_max_six' ? 'selected' : ''}>Average available ratings (max 6 slots)</option>
                <option value="legacy_six_semester_required" ${ind.calculation?.policy === 'legacy_six_semester_required' ? 'selected' : ''}>Legacy: require six ratings (fixed ÷6)</option>
              </select></label>
            </div>
            <fieldset id="patentStageWrap" style="display:none">
              <legend>Patent stages (A / P / G)</legend>
              <p class="muted" style="font-size:0.85rem;margin:0 0 0.5rem">One stage per achievement; stages do not accumulate (workbook B16–B17).</p>
              ${['A', 'P', 'G'].map((s) => {
                const st = ind.calculation?.stages || ind.points || {};
                const val = st[s] ?? '';
                return `<label>Stage ${s}<input type="number" step="0.01" min="0" name="stage${s}" value="${val}"/></label>`;
              }).join('')}
              <label><input type="checkbox" name="notCumulative" ${ind.calculation?.notCumulative !== false ? 'checked' : ''}/> Stages are not cumulative</label>
            </fieldset>
            <fieldset id="tieredOptionWrap" style="display:none">
              <legend>Tier options</legend>
              <p class="muted" style="font-size:0.85rem;margin:0 0 0.5rem">Field name on faculty form (e.g. commercializationScope, softwareVersionType).</p>
              <label>Tier field<input name="tierField" value="${escAttr(ind.calculation?.tierField || '')}"/></label>
              ${tierInputsHtml}
              <label>Local tier cap (optional)<input type="number" step="0.01" min="0" name="tierCapLocal" value="${ind.calculation?.tierCaps?.local ?? ''}"/></label>
              <label>International tier cap (optional)<input type="number" step="0.01" min="0" name="tierCapIntl" value="${ind.calculation?.tierCaps?.international ?? ''}"/></label>
            </fieldset>
            <fieldset id="aggregateWrap" style="display:none">
              <legend>Aggregate cap (workbook combined limits)</legend>
              <label>Aggregate cap<input type="number" step="0.01" min="0" name="aggregateCap" value="${ind.calculation?.aggregateCap ?? ''}"/></label>
              <label>Aggregate group id (shared across indicators)<input name="aggregateGroup" value="${escAttr(ind.calculation?.aggregateGroup || '')}"/></label>
            </fieldset>
            <fieldset id="yearlyRateWrap" style="display:none">
              <legend>Yearly service rates (Criterion D)</legend>
              <label>Role field<input name="roleField" value="${escAttr(ind.calculation?.roleField || 'academicServiceRole')}"/></label>
              <label>Years field<input name="yearsField" value="${escAttr(ind.calculation?.yearsField || 'serviceYears')}"/></label>
              <label><input type="checkbox" name="requiresNewlyAppointed" ${ind.calculation?.requiresNewlyAppointed ? 'checked' : ''}/> Requires newly-appointed attestation</label>
              <label>Fractional-year policy<select name="fractionalYearPolicy">
                <option value="unresolved" ${(ind.calculation?.fractionalYearPolicy || 'unresolved') === 'unresolved' ? 'selected' : ''}>Unresolved (workbook comment only)</option>
                <option value="whole_years_only" ${ind.calculation?.fractionalYearPolicy === 'whole_years_only' ? 'selected' : ''}>Whole years only</option>
              </select></label>
              ${rateInputsHtml}
            </fieldset>
          </section>
          <section class="cfg-form-section"><h4>Required documents</h4>
            <label>List one per line<textarea name="docs" rows="3">${escAttr((ind.documentaryRequirements || []).join('\n'))}</textarea></label>
          </section>
          <section class="cfg-form-section"><h4>Source &amp; conditions</h4>
            <label>Source reference<input name="sourceRef" value="${escAttr(ind.sourceRef || '')}"/></label>
            <label>Conditions (one per line)<textarea name="conditions" rows="3">${escAttr((ind.conditions || []).join('\n'))}</textarea></label>
            <fieldset><legend>Contribution split</legend>
              <label>Mode<select name="contribMode">
                ${['percent', 'lead_contributor', 'none'].map((m) => `<option value="${m}" ${ind.contributionAllocation?.mode === m ? 'selected' : ''}>${m}</option>`).join('')}
              </select></label>
              <label>Default %<input type="number" name="defPct" min="0" max="100" value="${ind.contributionAllocation?.defaultPercent ?? 100}"/></label>
            </fieldset>
          </section>
          <details><summary>Technical details</summary>
            <p class="muted" style="font-size:0.85rem">Indicator ID: ${esc(ind.id)}</p>
          </details>
          <p id="indFormErr" class="cfg-field-error" role="alert"></p>
          <div style="display:flex;gap:0.75rem;margin-top:1rem">
            <button type="button" class="cfg-btn-secondary" id="closeInd">Cancel</button>
            <button type="submit" class="cfg-btn-primary">Save changes</button>
          </div>
        </form>
      </aside>`,
  });
  if (!modal) return;

  const kindSelect = modal.dialog?.querySelector('[name="calcKind"]');
  const syncCalcFields = () => {
    const kind = kindSelect?.value;
    const wrap = modal.dialog?.querySelector('#setFactorWrap');
    if (wrap) wrap.style.display = kind === 'set_sef_average' ? '' : 'none';
    const patentWrap = modal.dialog?.querySelector('#patentStageWrap');
    if (patentWrap) patentWrap.style.display = kind === 'patent_stage' ? '' : 'none';
    const tierWrap = modal.dialog?.querySelector('#tieredOptionWrap');
    if (tierWrap) tierWrap.style.display = kind === 'tiered_option' ? '' : 'none';
    const aggWrap = modal.dialog?.querySelector('#aggregateWrap');
    if (aggWrap) aggWrap.style.display = kind === 'tiered_option' || kind === 'fixed_per_entry' ? '' : 'none';
    const yrWrap = modal.dialog?.querySelector('#yearlyRateWrap');
    if (yrWrap) yrWrap.style.display = kind === 'yearly_rate' ? '' : 'none';
  };
  kindSelect?.addEventListener('change', syncCalcFields);
  syncCalcFields();

  modal.dialog?.querySelector('#closeInd')?.addEventListener('click', () => modal.close());

  modal.dialog?.querySelector('#indForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const err = modal.dialog?.querySelector('#indFormErr');
    if (err) err.textContent = '';
    ind.name = fd.get('name').trim();
    ind.description = fd.get('description').trim();
    const mp = fd.get('maxPoints');
    ind.maxPoints = mp === '' ? null : Number(mp);
    ind.sourceRef = fd.get('sourceRef').trim();
    ind.conditions = fd.get('conditions').toString().split('\n').map((s) => s.trim()).filter(Boolean);
    ind.documentaryRequirements = fd.get('docs').toString().split('\n').map((s) => s.trim()).filter(Boolean);
    const kind = fd.get('calcKind');
    const prevCalc = { ...(ind.calculation || {}) };
    ind.calculation = { ...prevCalc, kind };
    if (kind === 'set_sef_average') {
      ind.calculation.factor = Number(fd.get('setFactor'));
      const slots = Number(fd.get('semesterCount') || 6);
      ind.calculation.semesterCount = Number.isFinite(slots) ? Math.min(6, Math.max(1, slots)) : 6;
      ind.calculation.policy = String(fd.get('setSefPolicy') || 'average_available_max_six');
    }
    if (kind === 'fixed_per_entry') {
      ind.calculation.maxPoints = ind.maxPoints;
      const ac = fd.get('aggregateCap');
      if (ac !== '' && ac != null) ind.calculation.aggregateCap = Number(ac);
      else delete ind.calculation.aggregateCap;
      const ag = fd.get('aggregateGroup')?.toString().trim();
      if (ag) ind.calculation.aggregateGroup = ag;
      else delete ind.calculation.aggregateGroup;
    }
    if (kind === 'patent_stage') {
      ind.calculation.stages = {
        A: Number(fd.get('stageA') || 0),
        P: Number(fd.get('stageP') || 0),
        G: Number(fd.get('stageG') || 0),
      };
      ind.calculation.notCumulative = fd.get('notCumulative') === 'on';
      delete ind.points;
    }
    if (kind === 'tiered_option') {
      const options = {};
      for (const [k, v] of fd.entries()) {
        if (!String(k).startsWith('tierPts_') || v === '' || v == null) continue;
        options[String(k).slice(8)] = Number(v);
      }
      ind.calculation.options = options;
      const tf = fd.get('tierField')?.toString().trim();
      if (tf) ind.calculation.tierField = tf;
      const caps = {};
      const cLocal = fd.get('tierCapLocal');
      const cIntl = fd.get('tierCapIntl');
      if (cLocal !== '' && cLocal != null) caps.local = Number(cLocal);
      if (cIntl !== '' && cIntl != null) caps.international = Number(cIntl);
      if (Object.keys(caps).length) ind.calculation.tierCaps = caps;
      else delete ind.calculation.tierCaps;
      const ac = fd.get('aggregateCap');
      if (ac !== '' && ac != null) ind.calculation.aggregateCap = Number(ac);
      else delete ind.calculation.aggregateCap;
      const ag = fd.get('aggregateGroup')?.toString().trim();
      if (ag) ind.calculation.aggregateGroup = ag;
      else delete ind.calculation.aggregateGroup;
      delete ind.points;
    }
    if (kind === 'yearly_rate') {
      const rates = {};
      for (const [k, v] of fd.entries()) {
        if (!String(k).startsWith('ratePts_') || v === '' || v == null) continue;
        rates[String(k).slice(8)] = Number(v);
      }
      ind.calculation.rates = rates;
      ind.calculation.fractionalYearPolicy = fd.get('fractionalYearPolicy') || 'unresolved';
      ind.calculation.requiresNewlyAppointed = fd.get('requiresNewlyAppointed') === 'on';
      const yf = fd.get('yearsField')?.toString().trim();
      const rf = fd.get('roleField')?.toString().trim();
      if (yf) ind.calculation.yearsField = yf;
      if (rf) ind.calculation.roleField = rf;
    }
    ind.contributionAllocation = { mode: fd.get('contribMode'), defaultPercent: Number(fd.get('defPct')) };
    crit.capMaxPoints = fd.get('critCap') === '' ? null : Number(fd.get('critCap'));

    try {
      const w = readWeightsPct();
      validateCatalog(draft.catalog, w);
      ConfigRepository.saveDraft(store, { catalog: draft.catalog, kraWeights: w, actor: _session.email, summary: `Updated indicator ${ind.id}` });
      MockStore.save(store);
      _savedFingerprint = fingerprintDraft(store);
      modal.close();
      _onRefresh?.();
    } catch (ex) {
      if (err) err.textContent = ex.message;
    }
  });
}

function openSupportingEvidenceEditor(kra, crit, ind) {
  const store = MockStore.load();
  const draft = requireDraft(store);
  const categories = (ind.specialStatusCategories || []).join('\n');
  const modal = openDrawerModal({
    opener: null,
    panelHtml: `
      <aside class="cfg-side-panel" role="dialog" aria-labelledby="indEditTitle">
        <h3 id="indEditTitle">Edit supporting evidence</h3>
        <p class="muted">${esc(kra.name)} → ${esc(crit.name)}</p>
        <p class="muted" style="font-size:0.85rem">This category collects supporting documents only. It does not award points or change SET/SEF scores automatically.</p>
        <form id="indForm" class="cfg-form">
          <section class="cfg-form-section"><h4>Basic information</h4>
            <label>Name<input required name="name" value="${escAttr(ind.name)}"/></label>
            <label>Description<textarea name="description" rows="3">${escAttr(ind.description || '')}</textarea></label>
          </section>
          <section class="cfg-form-section"><h4>Special status categories</h4>
            <p class="muted" style="font-size:0.85rem;margin:0 0 0.5rem">One category per line. Faculty select from this list when uploading evidence.</p>
            <label><span class="sr-only">Categories</span><textarea name="categories" rows="5">${escAttr(categories)}</textarea></label>
          </section>
          <section class="cfg-form-section"><h4>Guidance &amp; requirements</h4>
            <label>Faculty guidance (one per line)<textarea name="conditions" rows="4">${escAttr((ind.conditions || []).join('\n'))}</textarea></label>
            <label>Required supporting documents (one per line)<textarea name="docs" rows="3">${escAttr((ind.documentaryRequirements || []).join('\n'))}</textarea></label>
          </section>
          <section class="cfg-form-section"><h4>Source reference</h4>
            <label>Source reference<input name="sourceRef" value="${escAttr(ind.sourceRef || '')}"/></label>
          </section>
          <details><summary>Technical details</summary>
            <p class="muted" style="font-size:0.85rem">Indicator ID: ${esc(ind.id)} · Role: supporting evidence (not scored)</p>
          </details>
          <p id="indFormErr" class="cfg-field-error" role="alert"></p>
          <div style="display:flex;gap:0.75rem;margin-top:1rem">
            <button type="button" class="cfg-btn-secondary" id="closeInd">Cancel</button>
            <button type="submit" class="cfg-btn-primary">Save changes</button>
          </div>
        </form>
      </aside>`,
  });
  if (!modal) return;
  modal.dialog?.querySelector('#closeInd')?.addEventListener('click', () => modal.close());
  modal.dialog?.querySelector('#indForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const err = modal.dialog?.querySelector('#indFormErr');
    if (err) err.textContent = '';
    ind.name = fd.get('name').trim();
    ind.description = fd.get('description').trim();
    ind.role = 'supporting_evidence';
    ind.maxPoints = null;
    ind.calculation = { kind: 'supporting_evidence' };
    delete ind.pointRule;
    ind.specialStatusCategories = fd
      .get('categories')
      .toString()
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);
    ind.conditions = fd.get('conditions').toString().split('\n').map((s) => s.trim()).filter(Boolean);
    ind.documentaryRequirements = fd.get('docs').toString().split('\n').map((s) => s.trim()).filter(Boolean);
    ind.sourceRef = fd.get('sourceRef').trim();
    try {
      const w = readWeightsPct();
      validateCatalog(draft.catalog, w);
      ConfigRepository.saveDraft(store, {
        catalog: draft.catalog,
        kraWeights: w,
        actor: _session.email,
        summary: `Updated supporting evidence ${ind.id}`,
      });
      MockStore.save(store);
      _savedFingerprint = fingerprintDraft(store);
      modal.close();
      _onRefresh?.();
    } catch (ex) {
      if (err) err.textContent = ex.message;
    }
  });
}

function openKraScoringPolicyEditor(kraId) {
  const store = MockStore.load();
  const draft = requireDraft(store);
  const kra = (draft.catalog.kras || []).find((k) => k.id === kraId);
  if (!kra) return;
  const sp = kra.scoringPolicy || {};
  const modal = openDrawerModal({
    opener: null,
    panelHtml: `
      <aside class="cfg-side-panel" role="dialog" aria-labelledby="kraSpTitle">
        <h3 id="kraSpTitle">KRA scoring policy</h3>
        <p class="muted">${esc(kra.name || kraId)}</p>
        <form id="kraSpForm" class="cfg-form">
          <section class="cfg-form-section">
            <p class="muted" style="font-size:0.85rem">Envelope and subtotal rules from the JC3 workbook. Do not enable envelope cap until institutional policy is confirmed.</p>
            <label><input type="checkbox" name="applyKraEnvelopeCap" ${sp.applyKraEnvelopeCap ? 'checked' : ''}/> Apply KRA envelope cap (${sp.kraListedMax ?? kra.maxPoints ?? '—'} pts)</label>
            <label>Unresolved policy note (shown to faculty/reviewers)<textarea name="unresolvedNote" rows="4">${escAttr(sp.unresolvedNote || '')}</textarea></label>
            <p class="muted" style="font-size:0.85rem">Core criteria: ${esc((sp.coreCriteria || []).join(', ') || '—')}</p>
            <p class="muted" style="font-size:0.85rem">Additional criteria: ${esc((sp.additionalCriteria || []).join(', ') || '—')}</p>
            <p class="muted" style="font-size:0.85rem">Core max sum: ${esc(String(sp.coreMaxSum ?? '—'))} · Additional max: ${esc(String(sp.additionalMax ?? '—'))}</p>
          </section>
          <p id="kraSpFormErr" class="cfg-field-error" role="alert"></p>
          <div style="display:flex;gap:0.75rem;margin-top:1rem">
            <button type="button" class="cfg-btn-secondary" id="closeKraSp">Cancel</button>
            <button type="submit" class="cfg-btn-primary">Save policy</button>
          </div>
        </form>
      </aside>`,
  });
  if (!modal) return;
  modal.dialog?.querySelector('#closeKraSp')?.addEventListener('click', () => modal.close());
  modal.dialog?.querySelector('#kraSpForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const err = modal.dialog?.querySelector('#kraSpFormErr');
    if (err) err.textContent = '';
    kra.scoringPolicy = {
      ...sp,
      applyKraEnvelopeCap: fd.get('applyKraEnvelopeCap') === 'on',
      unresolvedNote: fd.get('unresolvedNote')?.toString().trim() || sp.unresolvedNote || '',
    };
    try {
      const w = readWeightsPct();
      validateCatalog(draft.catalog, w);
      ConfigRepository.saveDraft(store, {
        catalog: draft.catalog,
        kraWeights: w,
        actor: _session.email,
        summary: `Updated scoring policy for ${kraId}`,
      });
      MockStore.save(store);
      _savedFingerprint = fingerprintDraft(store);
      modal.close();
      _onRefresh?.();
    } catch (ex) {
      if (err) err.textContent = ex.message;
    }
  });
}

function labelCalcKind(k) {
  const map = {
    fixed_per_entry: 'Fixed points per output',
    set_sef_average: 'SET/SEF semester average',
    role_matrix: 'Role matrix',
    structured_points: 'Structured tier points',
    patent_stage: 'Patent stage (A / P / G)',
    tiered_option: 'Tiered option (local/intl or new/updated)',
    income_tier: 'Income generation tiers (lead/contributor)',
    hourly_tier: 'Hourly rate by scope',
    designation_matrix: 'Administrative designation matrix',
    yearly_rate: 'Years × workbook rate (service)',
    supporting_evidence: 'Supporting evidence (not scored)',
    pending: 'Needs configuration',
  };
  return map[k] || k;
}

function persistDraftFromEditor(store) {
  const w = readWeightsPct();
  const d = requireDraft(store);
  ConfigRepository.saveDraft(store, { catalog: d.catalog, kraWeights: w, actor: _session.email, summary: 'Criterion updated' });
  MockStore.save(store);
  _savedFingerprint = fingerprintDraft(store);
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
}
function escAttr(s) {
  return String(s).replace(/"/g, '&quot;');
}
