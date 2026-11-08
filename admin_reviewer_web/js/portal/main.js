import { AuthRepository } from '../services/auth-repository.js';
import { MockStore, MOCK_STORE_STORAGE_KEY, syncEntryPointsFromDocument } from '../repositories/mock-store.js';
import { computeKraSummaries, computeSetSefPoints, computeTeachingEffectiveness } from '../core/scoring.js';
import { ConfigRepository } from '../repositories/config-repository.js';
import { initConfigUi, renderConfig } from './config-ui.js';
import {
  DEFAULT_INSTITUTION_CONFIG,
  evaluateRankEligibility,
} from '../core/institution-config.js';
import {
  computeEvaluationPeriodStatus,
  formatEvaluationDate,
  validateEvaluationPeriodDates,
  reviewerAvailabilityDetail,
  statusBadgeClass,
} from '../core/evaluation-period-service.js';
import { KRA_HELP, SCREEN_INTRO, pageIntro, statusBadgeHtml } from '../core/copy.js';
import { iconForNav, navIcon } from '../core/icons.js';
import { initSidebarLayout, applySidebarLayout, closeMobileDrawer, isMobileViewport } from './sidebar-layout.js';
import {
  openFacultyForm,
  openReviewerForm,
  openReviewerAssignModal,
  countFacultyForReviewer,
} from './account-modals.js';
import { brandCompactHtml } from '../core/brand-markup.js';
import { openCenteredModal } from './modal-access.js';

const session = AuthRepository.requireRole(['admin', 'reviewer']);
if (!session) throw new Error('No session');

const ADMIN_NAV = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'faculty', label: 'Faculty' },
  { id: 'reviewers', label: 'Reviewers' },
  { id: 'evalSettings', label: 'Evaluation Settings' },
  { id: 'reports', label: 'Reports' },
  { id: 'activity', label: 'Activity' },
  { id: 'profile', label: 'Profile' },
];

const REVIEWER_NAV = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'assigned', label: 'Assigned Faculty' },
  { id: 'workspace', label: 'Check Documents' },
  { id: 'evalSettings', label: 'Evaluation Settings' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'profile', label: 'Profile' },
];

const state = { route: 'dashboard', params: {}, workspaceFacultyId: null, reviewDocId: null };

function rulesForFaculty(store, facultyId) {
  const ctx = ConfigRepository.getCalculationCatalog(store, { facultyId });
  return { catalog: ctx.catalog, kraWeights: ctx.kraWeights, versionId: ctx.versionId, pinned: ctx.pinned };
}

function navItems() {
  return session.role === 'admin' ? ADMIN_NAV : REVIEWER_NAV;
}

function openSignOutConfirm(opener) {
  const modal = openCenteredModal({
    title: 'Sign out?',
    lede: 'Are you sure you want to sign out?',
    opener,
    footerHtml: `
      <button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Cancel</button>
      <button type="button" class="cfg-btn-primary" id="confirmSignOut">Sign Out</button>`,
  });
  if (!modal) return;
  modal.dialog.querySelector('#confirmSignOut')?.addEventListener('click', () => {
    if (isMobileViewport()) closeMobileDrawer(false);
    AuthRepository.logout();
    modal.close();
    location.href = '/login.html';
  });
}

function renderShell() {
  const sidebar = document.getElementById('sidebar');
  sidebar.innerHTML = `
    <div class="brand">${brandCompactHtml({ onDark: true })}</div>
    <nav class="sidebar-nav" aria-label="Portal sections">
      ${navItems()
        .map((n) => {
          const active =
            state.route === n.id ||
            (state.route === 'review' && n.id === 'workspace') ||
            (n.id === 'evalSettings' &&
              (state.route === 'rules' || state.route === 'config' || state.route === 'simulationCfg'));
          return `<button type="button" class="nav-item ${active ? 'active' : ''}" data-route="${n.id}" title="${n.label}" aria-label="${n.label}"${active ? ' aria-current="page"' : ''}>${iconForNav(n.id)}<span class="nav-label">${n.label}</span></button>`;
        })
        .join('')}
    </nav>
    <div class="sidebar-footer">
      <button type="button" class="nav-item nav-item-signout" id="signOut" title="Sign out" aria-label="Sign out">${navIcon.signOut}<span class="nav-label">Sign out</span></button>
    </div>
  `;
  sidebar.querySelectorAll('[data-route]').forEach((b) =>
    b.addEventListener('click', () => {
      if (isMobileViewport()) closeMobileDrawer(false);
      navigate(b.dataset.route);
    })
  );
  document.getElementById('signOut').onclick = (e) => openSignOutConfirm(e.currentTarget);
  document.getElementById('topActions').innerHTML = `<span style="color:#5a7089">${session.name} · ${session.role}</span>`;
}

function navigate(route, params = {}) {
  if (route === 'config') {
    route = 'evalSettings';
    params = { ...params, tab: params.tab || 'rules' };
  } else if (route === 'simulationCfg') {
    route = 'evalSettings';
    params = { ...params, tab: 'period' };
  } else if (route === 'rules') {
    route = 'evalSettings';
    params = { ...params, tab: params.tab || 'rules' };
  }
  state.route = route;
  state.params = params;
  renderShell();
  applySidebarLayout();
  renderView();
}

function renderView() {
  const el = document.getElementById('appContent');
  const title = document.getElementById('pageTitle');
  const map = {
    dashboard: () => renderDashboard(el, title),
    faculty: () => renderFacultyList(el, title),
    reviewers: () => renderReviewerList(el, title),
    evalSettings: () => renderEvaluationSettings(el, title),
    config: () => {
      state.params = { ...state.params, tab: 'rules' };
      renderEvaluationSettings(el, title);
    },
    simulationCfg: () => {
      state.params = { ...state.params, tab: 'period' };
      renderEvaluationSettings(el, title);
    },
    reports: () => renderReports(el, title),
    activity: () => renderActivity(el, title),
    profile: () => renderProfile(el, title),
    assigned: () => renderAssigned(el, title),
    workspace: () => renderWorkspace(el, title),
    review: () => renderDocumentReview(el, title),
    rules: () => {
      state.params = { ...state.params, tab: 'rules' };
      renderEvaluationSettings(el, title);
    },
    notifications: () => renderNotifications(el, title),
  };
  (map[state.route] || map.dashboard)();
}

function statusBadge(s) {
  return statusBadgeHtml(s);
}

function renderDashboard(root, title) {
  title.textContent = 'Dashboard';
  const store = MockStore.load();
  const docStats = MockStore.getDocumentStats();
  const facultyCount = store.faculty.filter((f) => f.status === 'active').length;
  const revCount = store.reviewers.filter((r) => r.status === 'active').length;
  const assigned = session.role === 'reviewer' ? store.faculty.filter((f) => session.reviewerId && store.reviewers.find((r) => r.id === session.reviewerId)?.assignedFacultyIds?.includes(f.id)) : [];

  const ic = store.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
  const evalCard =
    session.role === 'reviewer'
      ? evaluationPeriodReviewerDashboardHtml(ic.preparationPeriod)
      : '';

  root.innerHTML = `
    ${pageIntro(session.role === 'admin' ? SCREEN_INTRO.dashboardAdmin : SCREEN_INTRO.dashboardReviewer)}
    <h2 style="margin-top:0">${session.role === 'admin' ? 'Admin' : 'Reviewer'} Dashboard</h2>
    ${evalCard}
    <div class="cards">
      <div class="card"><h3>Active faculty</h3><div class="val">${session.role === 'reviewer' ? assigned.length : facultyCount}</div></div>
      <div class="card"><h3>Active reviewers</h3><div class="val">${session.role === 'admin' ? revCount : '—'}</div></div>
      <div class="card"><h3>Pending documents</h3><div class="val">${docStats.pending || 0}</div></div>
      <div class="card"><h3>Approved</h3><div class="val">${docStats.approved || 0}</div></div>
      <div class="card"><h3>Needs changes</h3><div class="val">${docStats.correction_requested || 0}</div></div>
      <div class="card"><h3>Config version</h3><div class="val" style="font-size:1rem">${store.configPublished}</div></div>
    </div>
    <h3>Recent activity</h3>
    <div class="table-wrap"><table><thead><tr><th>When</th><th>Actor</th><th>Event</th></tr></thead><tbody>
      ${store.activity
        .slice(0, 8)
        .map((a) => `<tr><td>${new Date(a.at).toLocaleString()}</td><td>${a.actor}</td><td>${a.text}</td></tr>`)
        .join('')}
    </tbody></table></div>
  `;
}

function renderFacultyList(root, title, preservedQuery = '') {
  title.textContent = 'Faculty management';
  root.innerHTML = `
    ${pageIntro(SCREEN_INTRO.faculty)}
    <p class="muted" style="font-size:0.85rem;margin:-0.25rem 0 1rem">Demo mode: changes are saved on this browser.</p>
    <div class="fl-page-toolbar">
      <input type="search" id="facSearch" placeholder="Search by name or email…" aria-label="Search faculty" />
      <button type="button" class="btn-primary-sm btn-sm" id="addFac">Add Faculty Member</button>
    </div>
    <div class="fl-page-card">
      <div class="table-wrap"><table><thead><tr>
        <th>Name</th><th>Email</th><th>Current rank</th><th>Department</th><th>Assigned reviewer</th><th>Status</th><th>Actions</th>
      </tr></thead><tbody id="facBody"></tbody></table></div>
      <div class="fl-account-card-list" id="facCards" aria-live="polite"></div>
    </div>`;
  const searchEl = document.getElementById('facSearch');
  if (preservedQuery) searchEl.value = preservedQuery;

  const redraw = (q = '') => {
    const store = MockStore.load();
    const needle = q.trim().toLowerCase();
    const rows = store.faculty.filter((f) => {
      if (!needle) return true;
      const blob = `${f.firstName} ${f.lastName} ${f.email} ${f.department || ''} ${f.rank || ''}`.toLowerCase();
      return blob.includes(needle);
    });
    const body = document.getElementById('facBody');
    const cards = document.getElementById('facCards');
    if (!rows.length) {
      const msg =
        needle && store.faculty.length
          ? 'No faculty match your search.'
          : 'No faculty records yet. Use Add Faculty Member to create one.';
      body.innerHTML = `<tr><td colspan="7"><p class="fl-empty-state">${msg}</p></td></tr>`;
      cards.innerHTML = `<p class="fl-empty-state">${msg}</p>`;
      return;
    }
    body.innerHTML = rows
      .map((f) => {
        const rev = f.reviewerId ? store.reviewers.find((r) => r.id === f.reviewerId) : null;
        const revLabel = rev ? `${rev.firstName} ${rev.lastName}` : '—';
        return `<tr>
          <td>${f.firstName} ${f.lastName}</td>
          <td>${f.email}</td>
          <td>${f.rank || '—'}</td>
          <td>${f.department || '—'}</td>
          <td>${revLabel}</td>
          <td>${statusBadge(f.status)}</td>
          <td class="fl-account-card-actions">
            <button type="button" class="btn-ghost btn-sm" data-edit="${f.id}" title="Edit faculty">Edit</button>
            <button type="button" class="btn-ghost btn-sm" data-toggle="${f.id}" title="${f.status === 'active' ? 'Deactivate faculty' : 'Activate faculty'}">${f.status === 'active' ? 'Deactivate' : 'Activate'}</button>
          </td></tr>`;
      })
      .join('');
    cards.innerHTML = rows
      .map((f) => {
        const rev = f.reviewerId ? store.reviewers.find((r) => r.id === f.reviewerId) : null;
        return `<article class="fl-account-card">
          <h4>${f.firstName} ${f.lastName}</h4>
          <p>${f.email}</p>
          <p>${f.rank || '—'} · ${f.department || '—'}</p>
          <p>Reviewer: ${rev ? `${rev.firstName} ${rev.lastName}` : '—'}</p>
          <p>${statusBadge(f.status)}</p>
          <div class="fl-account-card-actions">
            <button type="button" class="btn-ghost btn-sm" data-edit="${f.id}">Edit</button>
            <button type="button" class="btn-ghost btn-sm" data-toggle="${f.id}">${f.status === 'active' ? 'Deactivate' : 'Activate'}</button>
          </div>
        </article>`;
      })
      .join('');
    root.querySelectorAll('[data-edit]').forEach((b) => {
      b.onclick = () =>
        openFacultyForm(b.dataset.edit, {
          opener: b,
          onSaved: () => renderFacultyList(root, title, searchEl.value),
        });
    });
    root.querySelectorAll('[data-toggle]').forEach((b) => {
      b.onclick = () => {
        const st = MockStore.load();
        const f = st.faculty.find((x) => x.id === b.dataset.toggle);
        if (!f) return;
        const next = f.status === 'active' ? 'inactive' : 'active';
        if (!confirm(`${next === 'inactive' ? 'Deactivate' : 'Activate'} ${f.firstName} ${f.lastName}?`)) return;
        MockStore.upsertFaculty({ ...f, status: next });
        MockStore.logActivity(`Faculty ${next === 'active' ? 'activated' : 'deactivated'}: ${f.firstName} ${f.lastName}`, session.email);
        redraw(searchEl.value);
      };
    });
  };

  redraw(searchEl.value);
  searchEl.oninput = (e) => redraw(e.target.value);
  document.getElementById('addFac').onclick = (e) =>
    openFacultyForm(null, {
      opener: e.currentTarget,
      onSaved: () => renderFacultyList(root, title, searchEl.value),
    });
}

function renderReviewerList(root, title, preservedQuery = '') {
  title.textContent = 'Reviewer management';
  root.innerHTML = `
    ${pageIntro(SCREEN_INTRO.reviewers)}
    <p class="muted" style="font-size:0.85rem;margin:-0.25rem 0 1rem">Demo mode: changes are saved on this browser.</p>
    <div class="fl-page-toolbar">
      <input type="search" id="revSearch" placeholder="Search by name or email…" aria-label="Search reviewers" />
      <button type="button" class="btn-primary-sm btn-sm" id="addRev">Add Reviewer</button>
    </div>
    <div class="fl-page-card">
      <div class="table-wrap"><table><thead><tr>
        <th>Name</th><th>Email</th><th>Department / office</th><th>Assigned faculty</th><th>Status</th><th>Actions</th>
      </tr></thead><tbody id="revBody"></tbody></table></div>
      <div class="fl-account-card-list" id="revCards" aria-live="polite"></div>
    </div>`;
  const searchEl = document.getElementById('revSearch');
  if (preservedQuery) searchEl.value = preservedQuery;

  const redraw = (q = '') => {
    const store = MockStore.load();
    const needle = q.trim().toLowerCase();
    const list = store.reviewers.filter((r) => {
      if (!needle) return true;
      const blob = `${r.firstName} ${r.lastName} ${r.email} ${r.department || ''}`.toLowerCase();
      return blob.includes(needle);
    });
    const body = document.getElementById('revBody');
    const cards = document.getElementById('revCards');
    if (!list.length) {
      const msg =
        needle && store.reviewers.length
          ? 'No reviewers match your search.'
          : 'No reviewers yet. Use Add Reviewer to invite someone for the demo.';
      body.innerHTML = `<tr><td colspan="6"><p class="fl-empty-state">${msg}</p></td></tr>`;
      cards.innerHTML = `<p class="fl-empty-state">${msg}</p>`;
      return;
    }
    body.innerHTML = list
      .map((r) => {
        const count = countFacultyForReviewer(store, r.id);
        return `<tr>
          <td>${r.firstName} ${r.lastName}</td>
          <td>${r.email}</td>
          <td>${r.department || '—'}</td>
          <td>${count}</td>
          <td>${statusBadge(r.status)}</td>
          <td class="fl-account-card-actions">
            <button type="button" class="btn-ghost btn-sm" data-edit="${r.id}" title="Edit reviewer">Edit</button>
            <button type="button" class="btn-ghost btn-sm" data-assign="${r.id}" title="Manage faculty assignments">Assignments</button>
            <button type="button" class="btn-ghost btn-sm" data-toggle="${r.id}" title="${r.status === 'active' ? 'Deactivate reviewer' : 'Activate reviewer'}">${r.status === 'active' ? 'Deactivate' : 'Activate'}</button>
          </td></tr>`;
      })
      .join('');
    cards.innerHTML = list
      .map((r) => {
        const count = countFacultyForReviewer(store, r.id);
        return `<article class="fl-account-card">
          <h4>${r.firstName} ${r.lastName}</h4>
          <p>${r.email}</p>
          <p>${r.department || '—'}</p>
          <p>Assigned faculty: ${count}</p>
          <p>${statusBadge(r.status)}</p>
          <div class="fl-account-card-actions">
            <button type="button" class="btn-ghost btn-sm" data-edit="${r.id}">Edit</button>
            <button type="button" class="btn-ghost btn-sm" data-assign="${r.id}">Assignments</button>
            <button type="button" class="btn-ghost btn-sm" data-toggle="${r.id}">${r.status === 'active' ? 'Deactivate' : 'Activate'}</button>
          </div>
        </article>`;
      })
      .join('');
    root.querySelectorAll('[data-edit]').forEach((b) => {
      b.onclick = () =>
        openReviewerForm(b.dataset.edit, {
          opener: b,
          onSaved: () => renderReviewerList(root, title, searchEl.value),
        });
    });
    root.querySelectorAll('[data-assign]').forEach((b) => {
      b.onclick = () =>
        openReviewerAssignModal(b.dataset.assign, {
          opener: b,
          onSaved: () => renderReviewerList(root, title, searchEl.value),
        });
    });
    root.querySelectorAll('[data-toggle]').forEach((b) => {
      b.onclick = () => {
        const st = MockStore.load();
        const r = st.reviewers.find((x) => x.id === b.dataset.toggle);
        if (!r) return;
        const next = r.status === 'active' ? 'inactive' : 'active';
        if (!confirm(`${next === 'inactive' ? 'Deactivate' : 'Activate'} ${r.firstName} ${r.lastName}?`)) return;
        MockStore.upsertReviewer({ ...r, status: next });
        MockStore.logActivity(`Reviewer ${next === 'active' ? 'activated' : 'deactivated'}: ${r.firstName} ${r.lastName}`, session.email);
        redraw(searchEl.value);
      };
    });
  };

  redraw(searchEl.value);
  searchEl.oninput = (e) => redraw(e.target.value);
  document.getElementById('addRev').onclick = (e) =>
    openReviewerForm(null, {
      opener: e.currentTarget,
      onSaved: () => renderReviewerList(root, title, searchEl.value),
    });
}

function evaluationPeriodReviewerDashboardHtml(period) {
  const status = computeEvaluationPeriodStatus(period);
  const rev = reviewerAvailabilityDetail(period);
  return `
    <div class="card fl-eval-period-card fl-eval-period-card--compact" style="margin-bottom:1rem" aria-labelledby="dash-eval-period">
      <div class="fl-eval-period-card__head">
        <h3 id="dash-eval-period" style="margin:0">Evaluation Period</h3>
        <span class="badge-status ${statusBadgeClass(status)}">${status}</span>
      </div>
      <p style="margin:0.35rem 0 0;font-weight:600">${formatEvaluationDate(period.start)} – ${formatEvaluationDate(period.end)}</p>
      <p class="muted" style="margin:0.35rem 0 0;font-size:0.9rem">Reviewer availability: ${rev.shortLabel}</p>
      <p class="muted" style="margin:0.5rem 0 0;font-size:0.85rem">Schedule is read-only for reviewers.</p>
    </div>`;
}

function setEvalSettingsTab(root, tab) {
  root.querySelectorAll('[data-eval-tab]').forEach((btn) => {
    const on = btn.dataset.evalTab === tab;
    btn.classList.toggle('active', on);
    btn.setAttribute('aria-selected', String(on));
  });
  const rulesPanel = root.querySelector('#evalTabRules');
  const periodPanel = root.querySelector('#evalTabPeriod');
  if (rulesPanel) rulesPanel.hidden = tab !== 'rules';
  if (periodPanel) periodPanel.hidden = tab !== 'period';
}

function renderEvaluationSettings(root, title) {
  title.textContent = 'Evaluation Settings';
  const tab = state.params.tab === 'period' ? 'period' : 'rules';
  const periodReadOnly = session.role === 'reviewer';

  root.innerHTML = `
    <div class="fl-eval-settings">
      <div class="fl-settings-tabs" role="tablist" aria-label="Evaluation settings sections">
        <button type="button" class="fl-settings-tab ${tab === 'rules' ? 'active' : ''}" role="tab" id="tab-btn-rules"
          aria-selected="${tab === 'rules'}" aria-controls="evalTabRules" data-eval-tab="rules">Scoring Rules</button>
        <button type="button" class="fl-settings-tab ${tab === 'period' ? 'active' : ''}" role="tab" id="tab-btn-period"
          aria-selected="${tab === 'period'}" aria-controls="evalTabPeriod" data-eval-tab="period">Evaluation Period</button>
      </div>
      <div id="evalTabRules" class="fl-settings-panel" role="tabpanel" aria-labelledby="tab-btn-rules" ${tab !== 'rules' ? 'hidden' : ''}></div>
      <div id="evalTabPeriod" class="fl-settings-panel" role="tabpanel" aria-labelledby="tab-btn-period" ${tab !== 'period' ? 'hidden' : ''}></div>
    </div>`;

  root.querySelectorAll('[data-eval-tab]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const next = btn.dataset.evalTab;
      if (state.params.tab === next) return;
      state.params = { ...state.params, tab: next };
      setEvalSettingsTab(root, next);
    });
  });

  renderConfig(document.getElementById('evalTabRules'), title, { embedded: true });
  renderEvaluationPeriod(document.getElementById('evalTabPeriod'), title, { embedded: true, readOnly: periodReadOnly });
  setEvalSettingsTab(root, tab);
}

function renderEvaluationPeriod(root, title, { embedded = false, readOnly = false } = {}) {
  if (!embedded) title.textContent = 'Evaluation Period';
  const store = MockStore.load();
  const ic = store.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
  const period = ic.preparationPeriod;
  const status = computeEvaluationPeriodStatus(period);
  const rev = reviewerAvailabilityDetail(period);

  if (readOnly) {
    root.innerHTML = `
      ${pageIntro(SCREEN_INTRO.simulationCfg)}
      <p class="muted" style="margin:-0.5rem 0 1rem;font-size:0.92rem">These settings are managed by your administrator.</p>
      <div class="card fl-eval-period-form">
        <dl class="fl-eval-period-dl">
          <div>
            <dt>Start date</dt>
            <dd>${formatEvaluationDate(period.start)}</dd>
          </div>
          <div>
            <dt>End date</dt>
            <dd>${formatEvaluationDate(period.end)}</dd>
          </div>
          <div>
            <dt>Reviewer available from</dt>
            <dd>${period.reviewerAvailableFrom ? formatEvaluationDate(period.reviewerAvailableFrom) : '—'}</dd>
          </div>
        </dl>
        <div class="fl-eval-period-summary" style="margin-top:0.75rem">
          <p><span class="muted">Current status</span> <span class="badge-status ${statusBadgeClass(status)}">${status}</span></p>
          <p class="muted" style="font-size:0.9rem;margin:0.35rem 0 0">Reviewer availability: ${rev.shortLabel}</p>
        </div>
      </div>`;
    return;
  }

  root.innerHTML = `
    ${pageIntro(SCREEN_INTRO.simulationCfg)}
    <div class="card fl-eval-period-form">
      <form id="evalPeriodForm" class="fl-eval-period-fields" novalidate>
        <label class="fl-field">
          <span class="fl-field__label">Start Date</span>
          <input type="date" id="ppStart" name="start" value="${period.start}" required aria-required="true" />
        </label>
        <label class="fl-field">
          <span class="fl-field__label">End Date</span>
          <input type="date" id="ppEnd" name="end" value="${period.end}" required aria-required="true" />
        </label>
        <label class="fl-field">
          <span class="fl-field__label">Reviewer Available From</span>
          <input type="date" id="ppRev" name="reviewerAvailableFrom" value="${period.reviewerAvailableFrom || ''}" />
        </label>
      </form>
      <div class="fl-eval-period-summary" aria-live="polite">
        <p><span class="muted">Current status</span> <span class="badge-status ${statusBadgeClass(status)}" id="ppStatusBadge">${status}</span></p>
        <p class="muted" style="font-size:0.9rem;margin:0.35rem 0 0" id="ppRevLine">Reviewer availability: ${rev.shortLabel}</p>
      </div>
      <div style="margin-top:1rem;display:flex;flex-wrap:wrap;gap:0.75rem;align-items:center">
        <button type="button" class="btn-primary-sm btn-sm" id="saveEvalPeriod">Save Changes</button>
        <p id="evalPeriodMsg" class="muted" role="status" style="margin:0;flex:1 1 12rem"></p>
      </div>
    </div>`;

  const form = document.getElementById('evalPeriodForm');
  const msg = document.getElementById('evalPeriodMsg');

  const refreshPreview = () => {
    const draft = {
      start: document.getElementById('ppStart').value,
      end: document.getElementById('ppEnd').value,
      reviewerAvailableFrom: document.getElementById('ppRev').value || null,
    };
    const st = computeEvaluationPeriodStatus(draft);
    const badge = document.getElementById('ppStatusBadge');
    badge.textContent = st;
    badge.className = `badge-status ${statusBadgeClass(st)}`;
    document.getElementById('ppRevLine').textContent = `Reviewer availability: ${reviewerAvailabilityDetail(draft).shortLabel}`;
  };

  form.querySelectorAll('input[type="date"]').forEach((inp) => inp.addEventListener('change', refreshPreview));

  document.getElementById('saveEvalPeriod').onclick = () => {
    const start = document.getElementById('ppStart').value;
    const end = document.getElementById('ppEnd').value;
    const reviewerAvailableFrom = document.getElementById('ppRev').value || '';
    const err = validateEvaluationPeriodDates({ start, end });
    if (err) {
      msg.textContent = err;
      msg.style.color = 'var(--fl-danger, #b42318)';
      return;
    }
    const s = MockStore.load();
    s.institutionConfig = s.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
    s.institutionConfig.preparationPeriod = { start, end, reviewerAvailableFrom };
    MockStore.save(s);
    MockStore.logActivity('Updated evaluation period (demo)', session.email);
    msg.style.color = '';
    msg.textContent = `Saved. Evaluation period is ${computeEvaluationPeriodStatus(s.institutionConfig.preparationPeriod)} (${formatEvaluationDate(start)} – ${formatEvaluationDate(end)}).`;
    refreshPreview();
  };
}

function renderReports(root, title) {
  title.textContent = 'Reports';
  const store = MockStore.load();
  root.innerHTML = `
    ${pageIntro(SCREEN_INTRO.reports)}
    <div class="toolbar"><select id="repFac">${store.faculty.map((f) => `<option value="${f.id}">${f.firstName} ${f.lastName}</option>`).join('')}</select>
    <button class="btn-primary-sm btn-sm" id="printRep">Print preview</button></div>
    <div id="repOut" class="card"></div>`;
  const update = () => {
    const fid = document.getElementById('repFac').value;
    const ass = store.assessments[fid] || { entries: {}, setSef: { SET: [], SEF: [] } };
    const rules = rulesForFaculty(store, fid);
    const sum = computeKraSummaries(ass, rules.catalog, rules.kraWeights);
    const pinnedNote = rules.pinned ? ` (config version ${rules.versionId} pinned)` : '';
    document.getElementById('repOut').innerHTML = `<h3>Faculty assessment summary</h3>
      ${Object.values(sum.byKra)
        .map((k) => `<p><strong>${k.name}</strong> raw ${k.rawTotal.toFixed(2)} · weighted ${k.weightedContribution.toFixed(2)}</p>`)
        .join('')}
      <p><strong>Overall weighted total:</strong> ${sum.overallWeighted.toFixed(2)}</p>
      <h4>Documents</h4><ul>${store.documents
        .filter((d) => d.facultyId === fid)
        .map((d) => `<li>${d.fileName} — ${statusBadge(d.reviewStatus)}</li>`)
        .join('')}</ul>`;
  };
  update();
  document.getElementById('repFac').onchange = update;
  document.getElementById('printRep').onclick = () => window.print();
}

function renderActivity(root, title) {
  title.textContent = 'Activity';
  const store = MockStore.load();
  root.innerHTML = `${pageIntro(SCREEN_INTRO.activity)}<div class="table-wrap"><table><thead><tr><th>When</th><th>Actor</th><th>Description</th></tr></thead><tbody>
    ${store.activity.map((a) => `<tr><td>${new Date(a.at).toLocaleString()}</td><td>${a.actor}</td><td>${a.text}</td></tr>`).join('')}
  </tbody></table></div>`;
}

function renderProfile(root, title) {
  title.textContent = 'Profile';
  root.innerHTML = `<div class="card" style="max-width:480px"><h3>${session.name}</h3><p>Email: ${session.email}</p><p>Role: ${session.role}</p>
    <button class="btn-ghost btn-sm" id="resetDemo">Reset demonstration data</button></div>`;
  document.getElementById('resetDemo').onclick = () => {
    if (confirm('Reset all local demonstration data?')) {
      MockStore.reset();
      renderView();
    }
  };
}

function renderAssigned(root, title) {
  title.textContent = 'My assigned faculty';
  const store = MockStore.load();
  const rev = store.reviewers.find((r) => r.id === session.reviewerId);
  const list = store.faculty.filter((f) => rev?.assignedFacultyIds?.includes(f.id));
  root.innerHTML = `
    ${pageIntro(SCREEN_INTRO.assigned)}
    <div class="toolbar"><input type="search" id="asSearch" placeholder="Search by name…"/><select id="asStatus"><option value="">All status</option><option>active</option><option>inactive</option></select></div>
    <div class="cards" id="asCards"></div>`;
  const draw = () => {
    const q = document.getElementById('asSearch').value.toLowerCase();
    const st = document.getElementById('asStatus').value;
    document.getElementById('asCards').innerHTML = list
      .filter((f) => (`${f.firstName} ${f.lastName}`.toLowerCase().includes(q) || f.email.includes(q)) && (!st || f.status === st))
      .map((f) => {
        const docs = store.documents.filter((d) => d.facultyId === f.id);
        const pending = docs.filter((d) => d.reviewStatus === 'pending').length;
        return `<motion class="card"><h3>${f.firstName} ${f.lastName}</h3><p>${f.rank} · ${f.department}</p><p>Documents pending: ${pending}</p>
          <button class="btn-primary-sm btn-sm" data-open="${f.id}">Check documents</button></motion>`;
      })
      .join('');
    document.getElementById('asCards').querySelectorAll('motion').forEach((m) => {
      const div = document.createElement('div');
      div.className = m.className;
      div.innerHTML = m.innerHTML;
      m.replaceWith(div);
    });
    document.querySelectorAll('[data-open]').forEach((b) => (b.onclick = () => {
      state.workspaceFacultyId = b.dataset.open;
      navigate('workspace');
    }));
  };
  draw();
  document.getElementById('asSearch').oninput = draw;
  document.getElementById('asStatus').onchange = draw;
}

function renderWorkspace(root, title) {
  title.textContent = 'Check Documents';
  const store = MockStore.load();
  const facId = state.workspaceFacultyId || store.faculty.find((f) => f.reviewerId === session.reviewerId)?.id;
  const fac = store.faculty.find((f) => f.id === facId);
  if (!fac) {
    root.innerHTML = '<p>Select a faculty member from Assigned Faculty.</p>';
    return;
  }
  const ass = store.assessments[facId] || { setSef: { SET: [], SEF: [] }, entries: {} };
  const setPts = computeSetSefPoints(ass.setSef?.SET || [], 'SET');
  const sefPts = computeSetSefPoints(ass.setSef?.SEF || [], 'SEF');
  const te = computeTeachingEffectiveness(setPts.raw, sefPts.raw);
  const rules = rulesForFaculty(store, facId);
  const kraSum = computeKraSummaries(ass, rules.catalog, rules.kraWeights);
  const ic = store.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
  const estWt = kraSum.overallWeighted;
  const verifiedAss = {
    ...ass,
    entries: Object.fromEntries(
      Object.entries(ass.entries || {}).map(([k, list]) => [
        k,
        list.map((e) => ({ ...e, estimatedPoints: e.reviewerVerifiedPoints ?? e.estimatedPoints })),
      ])
    ),
  };
  const verSum = computeKraSummaries(verifiedAss, rules.catalog, rules.kraWeights);

  root.innerHTML = `
    ${pageIntro(SCREEN_INTRO.workspace)}
    <p class="muted" style="font-size:0.9rem">${KRA_HELP}</p>
    <nav aria-label="Breadcrumb" class="muted" style="font-size:0.9rem;margin-bottom:0.75rem">Check Documents → ${fac.firstName} ${fac.lastName}</nav>
    <motion class="toolbar"><label class="visually-hidden" for="wsFac">Faculty</label><select id="wsFac">${store.faculty.map((f) => `<option value="${f.id}" ${f.id === facId ? 'selected' : ''}>${f.firstName} ${f.lastName}</option>`).join('')}</select></motion>
    <details style="margin-bottom:0.75rem"><summary style="cursor:pointer;font-weight:600">How are these points calculated?</summary>
    <p style="font-size:0.9rem;color:#5a7089">Teaching Effectiveness uses your SET and SEF ratings. Each KRA has a weight. Faculty keep the rule version they started with.</p></details>
    <div class="card" style="margin-bottom:1rem"><strong>Teaching Effectiveness (Criterion A)</strong><p>${te.breakdown}</p></div>
    <motion class="card" style="margin-bottom:1rem"><strong>KRA simulation summary</strong>
      <p>Estimated weighted total: <strong>${estWt.toFixed(2)}</strong> · Reviewer-verified weighted: <strong>${verSum.overallWeighted.toFixed(2)}</strong></p>
      <p class="muted" style="font-size:0.85rem">Preparation only — not an official promotion decision. Rules: ${rules.versionId}${rules.pinned ? ' (pinned to assessment)' : ''}.</p>
      ${Object.values(kraSum.byKra)
        .map(
          (k) =>
            `<div style="margin-top:0.35rem">${k.name}: est. ${k.weightedContribution.toFixed(2)} · verified ${(verSum.byKra[k.kraId]?.weightedContribution ?? 0).toFixed(2)}</div>`
        )
        .join('')}
      <p style="margin-top:0.5rem;font-size:0.85rem">Rank mapping: <strong>${ic.rankMappingStatus === 'configured' ? 'Configured' : 'Pending configuration'}</strong></p>
    </motion>
    <div id="wsTree" class="tree"></div>`;

  root.querySelectorAll('motion').forEach((m) => {
    const d = document.createElement(m.tagName === 'motion' ? 'div' : 'div');
    d.className = m.className;
    d.innerHTML = m.innerHTML;
    m.replaceWith(d);
  });

  const tree = document.getElementById('wsTree');
  tree.innerHTML = rules.catalog.kras
    .map(
      (kra) => `
    <details open style="margin-bottom:0.75rem;background:#fff;padding:0.75rem;border-radius:8px;border:1px solid var(--fl-border)">
      <summary><strong>${kra.name}</strong></summary>
      ${kra.criteria
        .map((c) => {
          const indHtml = c.indicators
            .map((ind) => {
              let folder = '';
              if (ind.id === 'kra-I-A-set') folder = 'SET';
              if (ind.id === 'kra-I-A-sef') folder = 'SEF';
              const docs = store.documents.filter((d) => d.facultyId === facId && d.indicatorId === ind.id);
              return `<details style="margin:0.5rem 0 0 1rem"><summary>${ind.name}${folder ? ` · ${folder}` : ''}</summary>
                <ul style="list-style:none;padding:0">${docs.length ? docs.map((d) => `<li style="margin:0.35rem 0"><button class="btn-ghost btn-sm" data-doc="${d.id}">${d.fileName}</button> ${statusBadge(d.reviewStatus)} · ${d.academicYear || ''} ${d.semester || ''}</li>`).join('') : '<li class="muted">No demonstration documents</li>'}</ul>
              </details>`;
            })
            .join('');
          return `<details style="margin-left:0.5rem"><summary>${c.name}</summary>${indHtml}</details>`;
        })
        .join('')}
    </details>`
    )
    .join('');

  tree.querySelectorAll('[data-doc]').forEach((b) => (b.onclick = () => navigate('review', { docId: b.dataset.doc })));
  document.getElementById('wsFac').onchange = (e) => {
    state.workspaceFacultyId = e.target.value;
    renderWorkspace(root, title);
  };
}

function renderDocumentReview(root, title) {
  title.textContent = 'Check this document';
  const store = MockStore.load();
  const doc = store.documents.find((d) => d.id === (state.params.docId || state.reviewDocId));
  if (!doc) {
    root.innerHTML = '<p>Document not found.</p><button class="btn-ghost btn-sm" onclick="history.back()">Back</button>';
    return;
  }
  const rulesCtx = rulesForFaculty(store, doc.facultyId);
  const meta = rulesCtx.catalog.kras.flatMap((k) => k.criteria.flatMap((c) => c.indicators.map((i) => ({ kra: k, c, i })))).find((x) => x.i.id === doc.indicatorId);

  root.innerHTML = `
    ${pageIntro(SCREEN_INTRO.review)}
    <button class="btn-ghost btn-sm" id="backWs">← Back to documents</button>
    <p class="muted" style="font-size:0.85rem">OCR text is demonstration-only and does not approve the document.</p>
    <h2>${doc.fileName}</h2>
    <div class="review-layout" style="margin-top:1rem">
      <motion class="card"><h3>Preview</h3><p><strong>Type:</strong> ${doc.fileType}</p><p><strong>Submitted:</strong> ${doc.submittedAt}</p>
        <p><strong>OCR status:</strong> ${doc.ocrStatus} (separate from review)</p>
        <motion class="ocr-box">${doc.ocrText || 'No OCR text'}</motion></motion>
      <motion class="card"><h3>Review</h3>
        <p>Indicator: ${meta?.i?.name || doc.indicatorId}</p>
        <details style="margin:0.5rem 0"><summary>View source reference</summary><p style="font-size:0.85rem">${meta?.i?.sourceRef || '—'}</p></details>
        <label>Reviewer-verified points <span class="muted">(points checked by you)</span>
        <input type="number" id="verPts" value="${doc.verifiedPoints ?? doc.estimatedPoints ?? ''}"/></label>
        <label style="display:block;margin-top:0.75rem">Remarks<textarea id="rem" rows="3">${doc.remarks || ''}</textarea></label>
        <div class="toolbar" style="margin-top:1rem;flex-direction:column;align-items:stretch">
          <button class="btn-primary-sm btn-sm" data-action="approved" type="button">Approve document</button>
          <button class="btn-ghost btn-sm" data-action="correction_requested" type="button">Request changes</button>
          <button class="btn-ghost btn-sm review-actions-reject" data-action="rejected" type="button">Reject document</button>
        </div>
        <p id="revOk" class="success-banner" style="display:none" role="status">Your review was saved.</p>
        <p id="revErr" style="color:#c62828"></p>
        <h4>History</h4><ul>${(doc.history || []).map((h) => `<li>${h.at}: ${h.action} — ${h.note || ''}</li>`).join('')}</ul>
      </motion>
    </div>`;

  root.querySelectorAll('motion').forEach((m) => {
    const d = document.createElement('div');
    d.className = m.className;
    d.innerHTML = m.innerHTML;
    m.replaceWith(d);
  });

  document.getElementById('backWs').onclick = () => {
    state.workspaceFacultyId = doc.facultyId;
    navigate('workspace');
  };

  root.querySelectorAll('[data-action]').forEach((btn) => {
    btn.onclick = () => {
      const action = btn.dataset.action;
      const note = document.getElementById('rem').value.trim();
      if ((action === 'rejected' || action === 'correction_requested') && !note) {
        document.getElementById('revErr').textContent = 'Please write a short reason so the faculty member knows what to fix.';
        return;
      }
      const verified = document.getElementById('verPts').value;
      const patch = {
        reviewStatus: action,
        remarks: note,
        verifiedPoints: verified ? Number(verified) : null,
        history: [...(doc.history || []), { at: new Date().toISOString().slice(0, 10), by: session.email, action, note }],
      };
      MockStore.updateDocument(doc.id, patch);
      syncEntryPointsFromDocument({ ...doc, ...patch });
      MockStore.logActivity(`${action} document ${doc.fileName} for faculty ${doc.facultyId}`, session.email);
      const ok = document.getElementById('revOk');
      if (ok) {
        ok.style.display = 'block';
        ok.textContent =
          action === 'approved'
            ? 'Document approved. The faculty member can see this update.'
            : action === 'correction_requested'
              ? 'You requested changes. The faculty member can read your note.'
              : 'Document rejected. The faculty member can read your reason.';
        setTimeout(() => navigate('workspace'), 1200);
      } else navigate('workspace');
    };
  });
}

function renderNotifications(root, title) {
  title.textContent = 'Notifications';
  const store = MockStore.load();
  const rev = store.reviewers.find((r) => r.id === session.reviewerId);
  const facultyIds = rev?.assignedFacultyIds || [];
  root.innerHTML = `${pageIntro(SCREEN_INTRO.notifications)}<ul>${store.notifications
    .filter((n) => facultyIds.includes(n.facultyId))
  .map((n) => `<li class="card" style="margin-bottom:0.5rem"><strong>${n.title}</strong><p>${n.body}</p><small>${new Date(n.at).toLocaleString()}</small></li>`)
    .join('')}</ul>`;
}

window.addEventListener('fl-state-changed', () => renderView());
window.addEventListener('storage', (e) => {
  if (e.key === MOCK_STORE_STORAGE_KEY) renderView();
});

initSidebarLayout();
initConfigUi(session, renderView);
renderShell();
applySidebarLayout();
renderView();

// hash routing for review deep links
if (location.hash.startsWith('#review/')) {
  const docId = location.hash.replace('#review/', '');
  state.route = 'review';
  state.params.docId = docId;
  renderShell();
  applySidebarLayout();
  renderView();
}
