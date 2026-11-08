import { MockStore } from '../repositories/mock-store.js';
import { ConfigRepository, findIndicatorInCatalog, validateCatalog, SOURCE_CIRCULAR } from '../repositories/config-repository.js';
import { KRA_HELP } from '../core/copy.js';
import { computeKraSummaries } from '../core/scoring.js';
import { modalHost, bindModalShell, teardownModal, openCenteredModal, openDrawerModal } from './modal-access.js';

let _session = null;
let _onRefresh = null;

const _ui = {
  kraTab: 0,
  search: '',
  needsOnly: false,
  expanded: new Set(),
  expandedKraId: null,
  dirty: false,
};

const OFFICIAL_KRA_IDS = ['kra-I', 'kra-II', 'kra-III', 'kra-IV'];

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
    <li><strong>Save Draft</strong> stores your work in the browser without affecting published rules.</li>
    <li><strong>Review &amp; Publish</strong> checks weights and catalog validation, then sets an effective date for new work.</li>
    <li><strong>Preview</strong> (inside Review &amp; Publish) runs what-if calculations only — it does not change saved faculty scores.</li>
  </ul>
  <p>${KRA_HELP}</p>
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

function pctToDecimal(p) {
  return Number(p) / 100;
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
  if (document.querySelector('[data-kw-pct]')) {
    _pendingWeights = readWeightsPctFromDomOrEmpty();
    refreshDirtyFlag();
  }
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
  const k = ind.calculation?.kind;
  if (k === 'pending') return true;
  if (k === 'fixed_per_entry' && ind.maxPoints == null && ind.calculation?.maxPoints == null) return true;
  if (ind.pointRule === 'pending' || ind.pointRule === 'pending_external') return true;
  return false;
}

function indicatorPointsLabel(ind) {
  if (indicatorNeedsConfig(ind)) return 'Needs configuration';
  const k = ind.calculation?.kind || 'fixed_per_entry';
  if (k === 'set_sef_average') {
    const f = ind.calculation.factor ?? 0.36;
    return `${f} factor (SET/SEF avg.)`;
  }
  if (k === 'fixed_per_entry') {
    const pts = ind.maxPoints ?? ind.calculation?.maxPoints ?? '—';
    if (ind.perService) return `${pts} pts per service`;
    return `${pts} pts per output`;
  }
  if (k === 'structured_points' || ind.points) return 'Tiered reference points';
  if (k === 'role_matrix' || ind.matrix) return 'Role-based points';
  if (ind.maxPoints != null) return `${ind.maxPoints} pts max`;
  return 'Reference points configured';
}

export function renderConfig(root, title) {
  title.textContent = 'Scoring Rules';
  syncWeightsFromDom();

  const store = MockStore.load();
  ConfigRepository.loadContext(store);
  if (_session?.role !== 'reviewer') pruneEmptyPlaceholderKras(store);

  const readOnly = _session?.role === 'reviewer';
  const active = ConfigRepository.getActivePublished(store);
  const draft = ConfigRepository.getDraft(store);

  const catalog = readOnly ? active.catalog : draft?.catalog || active.catalog;
  const weights = effectiveWeights(readOnly ? active.kraWeights : draft?.kraWeights || active.kraWeights);

  if (!_savedFingerprint && draft) _savedFingerprint = fingerprintDraft(store);

  const navigable = getNavigableKras(catalog);
  if (_ui.kraTab >= navigable.length) _ui.kraTab = 0;

  const draftStatus = draft
    ? '<span class="badge-status badge-submitted">Draft in progress</span>'
    : '<span class="muted">No open draft</span>';
  const hiddenPlaceholders = catalog.kras.filter((k) => isRemovablePlaceholder(k)).length;

  root.innerHTML = `
    <section class="cfg-page" id="cfgPage" aria-labelledby="cfgHeading">
      <header class="cfg-page-header cfg-page-header--compact">
        <h2 id="cfgHeading">Scoring Rules</h2>
        <p class="cfg-page-sub">Manage how faculty assessment points are calculated.</p>
      </header>
      <div class="cfg-sticky-stack" id="cfgStickyStack"></div>
      <div id="cfgKraPanel" role="tabpanel" class="cfg-kra-panel"></div>
      <div id="cfgToast" class="cfg-toast" role="status" aria-live="polite" hidden></div>
      <div id="cfgModalRoot"></div>
    </section>
  `;

  const sticky = document.getElementById('cfgStickyStack');
  sticky.innerHTML = `
    <div class="cfg-summary-strip">
      <span><strong>Published:</strong> ${esc(active.label || 'Active')} · ${esc(formatDate(active.effectiveDate))}</span>
      <span class="cfg-summary-sep" aria-hidden="true">|</span>
      <span><strong>Editing:</strong> ${draftStatus}</span>
      <details class="cfg-details-inline">
        <summary>Details</summary>
        <div class="cfg-details-body">
          <section><h4>How this works</h4>${HOW_IT_WORKS}</section>
          <section><h4>Version details</h4>
            <dl class="cfg-dl">
              <dt>Published ID</dt><dd>${esc(active.id)}</dd>
              ${draft ? `<dt>Draft ID</dt><dd>${esc(draft.id)}</dd>` : ''}
              <dt>Catalog</dt><dd>${esc(catalog.version || '—')}</dd>
            </dl>
          </section>
          <section><h4>View source</h4><p class="muted">${esc(SOURCE_CIRCULAR)}</p></section>
        </div>
      </details>
    </div>
    ${readOnly ? '<span class="badge-status badge-approved cfg-readonly-tag">Read-only</span>' : `
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

  renderKraPanel(catalog, weights, readOnly);

  if (!readOnly) bindAdminActions(store);
  updateDirtyChip();
}

function kraTabLabel(kra) {
  if (KRA_TAB_LABELS[kra.id]) return KRA_TAB_LABELS[kra.id];
  return kra.name.replace(/^KRA [IVX]+ –\s*/i, '') || kra.name;
}

function weightStatusLabel(weights) {
  const w = weights || {};
  const total = Object.values(w).reduce((a, b) => a + Number(b), 0);
  const pct = Math.round(total * 10000) / 100;
  const ok = Math.abs(total - 1) <= 0.001;
  return { text: ok ? `Weights total ${pct}%` : `Weights ${pct}% — need 100%`, ok };
}

function readWeightsPctFromDomOrEmpty() {
  const w = {};
  document.querySelectorAll('[data-kw-pct]').forEach((inp) => {
    w[inp.dataset.kwPct] = pctToDecimal(inp.value);
  });
  return w;
}

function readWeightsPct() {
  const fromDom = readWeightsPctFromDomOrEmpty();
  if (Object.keys(fromDom).length) return fromDom;
  if (_pendingWeights) return { ..._pendingWeights };
  const store = MockStore.load();
  const d = ConfigRepository.getDraft(store);
  const active = ConfigRepository.getActivePublished(store);
  return { ...(d?.kraWeights || active.kraWeights) };
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
  const cat = d?.catalog || activePub.catalog;
  const weights = effectiveWeights(d?.kraWeights || activePub.kraWeights);
  renderKraPanel(cat, weights, readOnly);
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

function readModalWeightPct() {
  const w = {};
  modalHost()?.querySelectorAll('[data-kw-pct]').forEach((inp) => {
    w[inp.dataset.kwPct] = pctToDecimal(inp.value);
  });
  return w;
}

function validateWeightPercentsFromModal() {
  const host = modalHost();
  const problems = [];
  let total = 0;
  for (const id of OFFICIAL_KRA_IDS) {
    const inp = host?.querySelector(`[data-kw-pct="${id}"]`);
    const num = Number(inp?.value);
    if (!Number.isFinite(num) || num < 0 || num > 100) {
      problems.push(`${KRA_TAB_LABELS[id]} must be between 0 and 100.`);
      continue;
    }
    total += num / 100;
  }
  const pct = Math.round(total * 10000) / 100;
  if (Math.abs(total - 1) > 0.001) problems.push(`Combined weight must equal 100% (currently ${pct}%).`);
  return { ok: problems.length === 0, problems, pct };
}

function openWeightsPanel(store, readOnly) {
  const opener = document.getElementById('cfgEditWeights');
  const weightsAtOpen = { ...readWeightsPct() };

  const fieldsHtml = OFFICIAL_KRA_IDS.map((id) => {
    const v = weightsAtOpen[id] ?? 0;
    return `<label class="fl-weight-field" for="kw-modal-${escAttr(id)}">${esc(KRA_TAB_LABELS[id])}
      <span><input type="number" step="0.1" min="0" max="100" inputmode="decimal" id="kw-modal-${escAttr(id)}"
        data-kw-pct="${escAttr(id)}" value="${escAttr(decimalToPct(v))}" ${readOnly ? 'disabled' : ''} ${id === 'kra-I' ? 'data-autofocus' : ''}/> <span class="fl-weight-suffix">%</span></span>
    </label>`;
  }).join('');

  const footerHtml = readOnly
    ? `<button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Close</button>`
    : `<p id="cfgWeightsErr" class="fl-modal-footer-err" role="alert" aria-live="polite"></p>
       <button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Cancel</button>
       <button type="button" class="cfg-btn-primary" id="cfgWeightsApply" disabled>Apply Changes</button>`;

  const modal = openCenteredModal({
    title: 'Edit KRA Weights',
    lede: 'Set each area’s share of the total score.',
    size: 'md',
    bodyHtml: `
      <div class="fl-weight-fields">${fieldsHtml}</div>
      <p id="cfgWeightCombined" class="fl-weight-combined" aria-live="polite"></p>
    `,
    footerHtml,
    opener,
  });
  if (!modal) return;

  const combinedEl = modal.dialog.querySelector('#cfgWeightCombined');
  const applyBtn = modal.dialog.querySelector('#cfgWeightsApply');
  const errEl = modal.dialog.querySelector('#cfgWeightsErr');

  const refreshState = () => {
    const v = validateWeightPercentsFromModal();
    if (combinedEl) {
      combinedEl.textContent = v.ok
        ? `Combined weight: ${v.pct}% (equals 100%)`
        : `Combined weight: ${v.pct}% — must equal 100%`;
      combinedEl.className = `fl-weight-combined ${v.ok ? 'ok' : 'bad'}`;
    }
    if (errEl) errEl.textContent = v.problems.join(' ');
    if (applyBtn) applyBtn.disabled = !v.ok || readOnly;
  };

  modal.dialog.querySelectorAll('[data-kw-pct]').forEach((inp) => {
    inp.addEventListener('input', refreshState);
  });
  refreshState();

  applyBtn?.addEventListener('click', () => {
    const v = validateWeightPercentsFromModal();
    if (!v.ok) {
      if (errEl) errEl.textContent = v.problems.join(' ');
      return;
    }
    _pendingWeights = readModalWeightPct();
    _ui.dirty = true;
    refreshDirtyFlag();
    updateDirtyChip();
    modal.close();
    const activePub = ConfigRepository.getActivePublished(store);
    const draft2 = ConfigRepository.getDraft(store);
    const catalog2 = draft2?.catalog || activePub.catalog;
    renderKraPanel(catalog2, _pendingWeights, false);
    toast('Weights updated in draft. Use Save Draft to persist.');
  });
}

function renderKraPanel(catalog, weights, readOnly) {
  const navigable = getNavigableKras(catalog);
  const entry = navigable[_ui.kraTab];
  const kra = entry ? catalog.kras[entry.catalogIndex] : null;
  const panel = document.getElementById('cfgKraPanel');
  if (!kra) {
    panel.innerHTML = '<p class="muted">No KRAs configured.</p>';
    return;
  }

  ensureKraExpansion(kra);
  const kraPct = decimalToPct(weights[kra.id] ?? 0);
  const ws = weightStatusLabel(weights);
  const q = _ui.search.trim().toLowerCase();
  const criteriaHtml = kra.criteria
    .map((crit) => {
      const indicators = crit.indicators.filter((ind) => {
        if (_ui.needsOnly && !indicatorNeedsConfig(ind)) return false;
        if (q && !ind.name.toLowerCase().includes(q) && !crit.name.toLowerCase().includes(q)) return false;
        return true;
      });
      if (_ui.needsOnly && !indicators.length) return '';

      const expanded = _ui.expanded.has(crit.id);
      const indCount = crit.indicators.length;
      const countLabel = `${indCount} indicator${indCount === 1 ? '' : 's'}`;

      const indRows = indicators
        .map(
          (ind) => `<div class="cfg-ind-row">
            <span style="flex:1;min-width:10rem">${esc(ind.name)}</span>
            <span class="cfg-ind-points ${indicatorNeedsConfig(ind) ? 'badge-required' : ''}">${esc(indicatorPointsLabel(ind))}</span>
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

  panel.innerHTML = `
    <div class="cfg-kra-workspace">
      <div class="cfg-kra-nav-slot" id="cfgKraNavHost"></div>
      <div class="cfg-kra-heading">
        <h3>${esc(kra.name)}</h3>
        <div class="cfg-kra-heading-actions">
          <span class="cfg-kra-weight" title="Weight for this KRA">Weight <strong>${esc(kraPct)}%</strong></span>
          ${readOnly ? '' : `<button type="button" class="cfg-btn-ghost btn-sm" id="cfgEditWeights">Edit weights</button>`}
          <span class="cfg-weight-total cfg-weight-total--sm ${ws.ok ? 'ok' : 'bad'}">${esc(ws.text)}</span>
        </div>
      </div>
      <div class="cfg-ind-toolbar">
        <input type="search" id="cfgIndSearch" class="cfg-search" placeholder="Search indicators" value="${escAttr(_ui.search)}" aria-label="Search indicators"/>
        <label class="cfg-filter-check"><input type="checkbox" id="cfgNeedsFilter" ${_ui.needsOnly ? 'checked' : ''}/> Needs configuration</label>
        ${readOnly ? '' : `<button type="button" class="cfg-btn-ghost btn-sm" id="addCrit" data-kra="${escAttr(kra.id)}">Add criterion</button>`}
      </div>
      <div class="cfg-criteria-list">${criteriaHtml || '<p class="muted">No criteria match your filters.</p>'}</div>
    </div>
  `;

  renderKraNav(navigable);

  panel.querySelector('#cfgEditWeights')?.addEventListener('click', () => {
    const store = MockStore.load();
    openWeightsPanel(store, readOnly);
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

function bindAdminActions(store) {
  const moreBtn = document.getElementById('cfgMoreBtn');
  const moreMenu = document.getElementById('cfgMoreMenu');
  moreBtn?.addEventListener('click', () => {
    const open = moreMenu.hidden;
    moreMenu.hidden = !open;
    moreBtn.setAttribute('aria-expanded', String(open));
  });
  moreMenu?.addEventListener('click', (e) => e.stopPropagation());

  document.getElementById('cfgSaveDraft')?.addEventListener('click', () => saveDraft(store));
  document.getElementById('cfgReviewPublish')?.addEventListener('click', () => openPublishPanel(store));
  document.getElementById('cfgHistBtn')?.addEventListener('click', () => {
    moreMenu.hidden = true;
    openHistoryModal(store);
  });
  document.getElementById('addKra')?.addEventListener('click', () => {
    moreMenu.hidden = true;
    openAddKraForm(store);
  });
  document.getElementById('cfgPruneKra')?.addEventListener('click', () => {
    moreMenu.hidden = true;
    pruneEmptyPlaceholderKras(store);
    toast('Removed empty draft KRAs.');
    _onRefresh?.();
  });
}

function saveDraft(store) {
  try {
    const w = readWeightsPct();
    const d = requireDraft(store);
    ConfigRepository.saveDraft(store, {
      catalog: d.catalog,
      kraWeights: w,
      actor: _session.email,
      summary: 'Draft saved from configuration UI',
    });
    MockStore.save(store);
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
    MockStore.save(store);
    modal.close();
    toast('KRA saved to draft catalog. Main tabs remain the four JC3 KRAs until you add criteria.');
    _onRefresh?.();
  });
}

function addCriterion(kraId) {
  const store = MockStore.load();
  const d = requireDraft(store);
  const kra = d.catalog.kras.find((k) => k.id === kraId);
  if (!kra) return toast('KRA not found.', true);
  const id = `crit-${Date.now()}`;
  kra.criteria.push({ id, name: 'New criterion', capMaxPoints: null, indicators: [] });
  _ui.expanded.add(id);
  MockStore.save(store);
  const w = readWeightsPct();
  renderKraPanel(d.catalog, w, false);
  toast('Criterion added. Save Draft when ready.');
}

function addIndicator(kraId, critId) {
  const store = MockStore.load();
  const d = requireDraft(store);
  const kra = d.catalog.kras.find((k) => k.id === kraId);
  const crit = kra?.criteria.find((c) => c.id === critId);
  if (!crit) return toast('Criterion not found.', true);
  const indId = `ind-${Date.now()}`;
  crit.indicators.push({
    id: indId,
    name: 'New indicator',
    description: '',
    maxPoints: 0,
    sourceRef: '',
    conditions: [],
    documentaryRequirements: [],
    calculation: { kind: 'fixed_per_entry', maxPoints: 0 },
    contributionAllocation: { mode: 'percent', defaultPercent: 100 },
  });
  _ui.expanded.add(critId);
  MockStore.save(store);
  openIndicatorEditor(kraId, critId, indId);
}

function diffDraftVsActive(active, draft, weights) {
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
  if (sample) {
    const estActive = computeKraSummaries(sample, active.catalog, active.kraWeights).overallWeighted;
    const estDraft = computeKraSummaries(sample, draft.catalog, weights).overallWeighted;
    previewHtml = `<p class="muted">Sample faculty weighted total — published: <strong>${estActive.toFixed(2)}</strong> · draft rules: <strong>${estDraft.toFixed(2)}</strong>. Preview only; pinned assessments stay unchanged.</p>`;
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

  publishBtn?.addEventListener('click', () => {
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
      MockStore.save(store);
      MockStore.logActivity(`Published assessment config effective ${eff}`, _session.email);
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
              ${['fixed_per_entry', 'set_sef_average', 'role_matrix', 'structured_points', 'pending'].map((k) => `<option value="${k}" ${ind.calculation?.kind === k ? 'selected' : ''}>${labelCalcKind(k)}</option>`).join('')}
            </select></label>
            <label id="setFactorWrap">SET/SEF factor (average-based)<input type="number" step="0.01" name="setFactor" value="${ind.calculation?.factor ?? 0.36}"/></label>
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
    ind.calculation = { kind };
    if (kind === 'set_sef_average') ind.calculation.factor = Number(fd.get('setFactor'));
    if (kind === 'fixed_per_entry') ind.calculation.maxPoints = ind.maxPoints;
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

function labelCalcKind(k) {
  const map = {
    fixed_per_entry: 'Fixed points per output',
    set_sef_average: 'SET/SEF semester average',
    role_matrix: 'Role matrix',
    structured_points: 'Structured tier points',
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
