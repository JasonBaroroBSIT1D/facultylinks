import { AuthRepository } from '../services/auth-repository.js';
import {
  MockStore,
  bootstrapPortal,
  clearPortalCache,
  ensurePublishedCatalog,
  portalFullStateLoaded,
  portalLoadError,
  prefetchFullPortalState,
  publishedCatalogReady,
  revalidatePortalInBackground,
} from '../repositories/mock-store.js';
import { PortalApi } from '../services/portal-api.js';
import { computeKraSummaries } from '../core/scoring.js';
import { formatCriterionAEstimateHtml } from '../core/criterion-a-display.js';
import {
  buildCriterionADocumentsHtml,
  buildWorkspaceRecoveryHtml,
  formatCriterionAScoresHtml,
  workspaceCriterionHeading,
} from './workspace-kra-i-sections.js';
import {
  WS_FOLDER_CRITERION,
  WS_FOLDER_FACULTY,
  WS_FOLDER_KRA_I,
  WS_FOLDER_KRA_II,
  WS_FOLDER_KRA_III,
  WS_FOLDER_KRA_IV,
  buildCriterionDetailShell,
  buildFacultyRootFolderHtml,
  buildKraICriterionFoldersHtml,
  buildKraIICriterionFoldersHtml,
  buildKraIIICriterionFoldersHtml,
  buildKraIVCriterionFoldersHtml,
  buildWorkspaceBreadcrumb,
  bindWorkspaceBreadcrumbNav,
  kraIInstructionCounts,
  kraIIResearchCounts,
  kraIIIExtensionCounts,
  kraIVProfessionalCounts,
  patchWorkspaceFolderMetas,
  workspaceScrollKey,
} from './workspace-folder-nav.js';
import {
  ACH_LOAD_ERROR,
  ACH_LOAD_LOADED,
  achievementsForCriterion,
  clearWorkspaceAchievementsCache,
  ensureFacultyAchievementsLoaded,
  getFacultyAchievementsEntry,
  invalidateFacultyAchievementsCache,
  patchAchievementInCache,
  resolveAchievementCriterionId,
} from './workspace-achievements-cache.js';
import {
  documentCountsTowardLegacyPending,
  enrichPortalDocuments,
  isKraIAchievementIndicator,
  parentLinkForDocument,
} from './achievement-attachment-display.js';
import { ConfigRepository } from '../repositories/config-repository.js';
import { initConfigUi, renderConfig } from './config-ui.js';
import {
  DEFAULT_INSTITUTION_CONFIG,
  evaluateRankEligibility,
} from '../core/institution-config.js';
import {
  DEFAULT_RANK_SIMULATION,
  RANK_CATEGORY_IDS,
  RANK_CATEGORY_LABELS,
  validateRankSimulation,
} from '../core/rank-simulation-config.js';
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
  showAppToast,
} from './account-modals.js';
import { openFacultyScoringRulesModal } from './scoring-rules-modal.js';
import { brandCompactHtml } from '../core/brand-markup.js';
import { openCenteredModal } from './modal-access.js';
import { mountDocumentPdfViewer } from './document-pdf-viewer.js?v=3';
import {
  buildCriterionAchievementsFolderHtml,
  bindCriterionFolderNavigation,
  renderAchievementReviewPage,
} from './achievement-review-ui.js';

/** Set after server session verification in initPortalApp(). */
let session = null;

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

const state = { route: 'dashboard', params: {}, workspaceFacultyId: null, reviewDocId: null, workspaceUi: {} };

let _viewRenderId = 0;
let _evalSettingsLoadId = 0;
let _evalSettingsLoading = false;

const EVAL_SETTINGS_ROUTES = new Set(['evalSettings', 'config', 'rules', 'simulationCfg']);

function isEvalSettingsRoute(route = state.route) {
  return EVAL_SETTINGS_ROUTES.has(route);
}

function refreshEvaluationSettingsView() {
  if (!isEvalSettingsRoute()) return;
  const el = document.getElementById('appContent');
  const title = document.getElementById('pageTitle');
  if (el && title) renderEvaluationSettings(el, title);
}

function portalStateChanged() {
  if (_evalSettingsLoading) return;
  if (state.route === 'review' || state.route === 'workspace' || state.route === 'achievement-review') return;
  renderView();
}

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
  const confirmBtn = modal.dialog.querySelector('#confirmSignOut');
  const errEl = document.createElement('p');
  errEl.className = 'fl-account-field-error';
  errEl.setAttribute('role', 'alert');
  errEl.hidden = true;
  modal.dialog.querySelector('.fl-modal-dialog__footer')?.insertAdjacentElement('beforebegin', errEl);

  confirmBtn?.addEventListener('click', async () => {
    if (confirmBtn.disabled) return;
    errEl.hidden = true;
    errEl.textContent = '';
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Signing out…';
    try {
      await AuthRepository.logout();
      clearPortalCache();
      clearWorkspaceAchievementsCache();
      if (isMobileViewport()) closeMobileDrawer(false);
      modal.close();
      window.location.replace('/login.html');
    } catch (ex) {
      errEl.textContent = ex.message || 'Sign out failed. Try again.';
      errEl.hidden = false;
      confirmBtn.disabled = false;
      confirmBtn.textContent = 'Sign Out';
    }
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
            (state.route === 'achievement-review' && n.id === 'workspace') ||
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
  _viewRenderId += 1;
  _evalSettingsLoadId += 1;
  _evalSettingsLoading = false;
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
  el.classList.toggle('content--doc-review', state.route === 'review' || state.route === 'achievement-review');
  const title = document.getElementById('pageTitle');
  const map = {
    dashboard: () => renderDashboard(el, title),
    faculty: () => renderFacultyList(el, title),
    reviewers: () => renderReviewerList(el, title),
    evalSettings: () => {
      const viewId = ++_viewRenderId;
      const loadId = ++_evalSettingsLoadId;
      const paint = () => {
        if (viewId !== _viewRenderId || !isEvalSettingsRoute()) return;
        _evalSettingsLoading = false;
        renderEvaluationSettings(el, title);
      };
      const fail = (err) => {
        if (viewId !== _viewRenderId || !isEvalSettingsRoute()) {
          _evalSettingsLoading = false;
          return;
        }
        _evalSettingsLoading = false;
        el.innerHTML = `<div class="card" style="padding:1rem"><h2>Could not load evaluation settings</h2>
          <p>${err?.message || 'Request failed.'}</p>
          <button type="button" class="btn-primary-sm" id="evalSettingsRetry">Retry</button></div>`;
        document.getElementById('evalSettingsRetry')?.addEventListener('click', () => renderView());
      };

      if (portalFullStateLoaded()) {
        paint();
        void MockStore.refresh({ full: true, force: true }).catch(() => {});
        return;
      }

      _evalSettingsLoading = true;
      el.innerHTML = '<p class="muted" style="padding:1rem">Loading evaluation settings…</p>';
      void MockStore.refresh({ full: true, force: true }).then(
        () => {
          if (loadId !== _evalSettingsLoadId || viewId !== _viewRenderId || !isEvalSettingsRoute()) {
            _evalSettingsLoading = false;
            return;
          }
          paint();
        },
        fail
      );
    },
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
    workspace: () => {
      void renderWorkspace(el, title).catch((err) => showWorkspaceLoadError(el, title, err));
    },
    review: () => {
      void renderDocumentReview(el, title).catch((err) => showWorkspaceLoadError(el, title, err));
    },
    'achievement-review': () => {
      const renderSeq = ++_workspaceRenderSeq;
      const facId = state.params.facultyId || state.workspaceFacultyId;
      const rules = rulesForFaculty(MockStore.load(), facId);
      void renderAchievementReviewPage(el, title, {
        session,
        navigate,
        isActive: () => state.route === 'achievement-review' && renderSeq === _workspaceRenderSeq,
        getStore: () => MockStore.load(),
        catalog: rules.catalog,
        params: state.params,
        stateRef: state,
      });
    },
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

function countBcOrphanEvidence(store, facId, criterionId) {
  const achievements = store.assessments?.[facId]?.achievements || [];
  const linked = new Set();
  for (const a of achievements) {
    for (const id of a.documentIds || []) linked.add(id);
  }
  return (store.documents || []).filter(
    (d) =>
      d.facultyId === facId &&
      isKraIAchievementIndicator(d.indicatorId) &&
      d.indicatorId.startsWith(criterionId) &&
      !linked.has(d.id),
  ).length;
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
    <p class="muted" style="font-size:0.9rem;margin-bottom:0.75rem">Awaiting review = documents (SET/SEF and legacy) + submitted KRA I B/C achievements. Supporting evidence files alone are not counted until the faculty submits an achievement.</p>
    <div class="cards">
      <div class="card"><h3>Active faculty</h3><div class="val">${session.role === 'reviewer' ? assigned.length : facultyCount}</div></div>
      <div class="card"><h3>Active reviewers</h3><div class="val">${session.role === 'admin' ? revCount : '—'}</div></div>
      <button type="button" class="card card--link" data-dash-nav="assigned" style="text-align:left"><h3>Awaiting review</h3><div class="val">${docStats.pending || 0}</div><p class="muted" style="font-size:0.85rem;margin:0.35rem 0 0">${docStats.documentsPending || 0} document(s) · ${docStats.achievementsPending || 0} achievement(s)</p></button>
      <div class="card"><h3>Evidence files (not queued)</h3><div class="val">${docStats.bcEvidenceUnlinked || 0}</div><p class="muted" style="font-size:0.85rem;margin:0.35rem 0 0">Uploaded B/C files without a submitted achievement</p></div>
      <div class="card"><h3>Files approved</h3><div class="val">${docStats.approved || 0}</div></div>
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
  root.querySelector('[data-dash-nav="assigned"]')?.addEventListener('click', () => navigate('assigned'));
}

function renderFacultyList(root, title, preservedQuery = '') {
  title.textContent = 'Faculty management';
  root.innerHTML = `
    ${pageIntro(SCREEN_INTRO.faculty)}
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
            <button type="button" class="btn-ghost btn-sm" data-rules="${f.id}" title="Pinned scoring rules version">Scoring rules</button>
            <button type="button" class="btn-ghost btn-sm" data-resend="${f.id}" title="Resend sign-in credentials">Resend credentials</button>
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
            <button type="button" class="btn-ghost btn-sm" data-rules="${f.id}">Scoring rules</button>
            <button type="button" class="btn-ghost btn-sm" data-resend="${f.id}">Resend credentials</button>
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
    root.querySelectorAll('[data-rules]').forEach((b) => {
      b.onclick = () =>
        openFacultyScoringRulesModal(b.dataset.rules, {
          onApplied: () => renderFacultyList(root, title, searchEl.value),
        });
    });
    root.querySelectorAll('[data-resend]').forEach((b) => {
      b.onclick = async () => {
        const st = MockStore.load();
        const f = st.faculty.find((x) => x.id === b.dataset.resend);
        if (!f) return;
        if (!confirm(`Resend credentials for ${f.firstName} ${f.lastName}? This replaces their password and signs them out.`)) return;
        b.disabled = true;
        try {
          const res = await PortalApi.resendFacultyCredentials(f.id);
          await bootstrapPortal();
          showAppToast(
            res.emailDelivery?.ok
              ? 'Replacement credentials email was accepted by the mail server.'
              : res.emailDelivery?.message || 'Credential email failed.',
            !res.emailDelivery?.ok
          );
          redraw(searchEl.value);
        } catch (err) {
          showAppToast(err.message || 'Could not resend credentials.', true);
          b.disabled = false;
        }
      };
    });
    root.querySelectorAll('[data-toggle]').forEach((b) => {
      b.onclick = () => {
        const st = MockStore.load();
        const f = st.faculty.find((x) => x.id === b.dataset.toggle);
        if (!f) return;
        const next = f.status === 'active' ? 'inactive' : 'active';
        if (!confirm(`${next === 'inactive' ? 'Deactivate' : 'Activate'} ${f.firstName} ${f.lastName}?`)) return;
        PortalApi.setFacultyStatus(f.id, next).then(() => bootstrapPortal()).then(() => renderView());
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
          : 'No reviewers yet. Use Add Reviewer to create an account.';
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
            <button type="button" class="btn-ghost btn-sm" data-resend-rev="${r.id}" title="Resend sign-in credentials">Resend credentials</button>
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
            <button type="button" class="btn-ghost btn-sm" data-resend-rev="${r.id}">Resend credentials</button>
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
    root.querySelectorAll('[data-resend-rev]').forEach((b) => {
      b.onclick = async () => {
        const st = MockStore.load();
        const r = st.reviewers.find((x) => x.id === b.dataset.resendRev);
        if (!r) return;
        if (!confirm(`Resend credentials for ${r.firstName} ${r.lastName}? This replaces their password and signs them out.`)) return;
        b.disabled = true;
        try {
          const res = await PortalApi.resendReviewerCredentials(r.id);
          await bootstrapPortal();
          showAppToast(
            res.emailDelivery?.ok
              ? 'Replacement credentials email was accepted by the mail server.'
              : res.emailDelivery?.message || 'Credential email failed.',
            !res.emailDelivery?.ok
          );
          redraw(searchEl.value);
        } catch (err) {
          showAppToast(err.message || 'Could not resend credentials.', true);
          b.disabled = false;
        }
      };
    });
    root.querySelectorAll('[data-toggle]').forEach((b) => {
      b.onclick = () => {
        const st = MockStore.load();
        const r = st.reviewers.find((x) => x.id === b.dataset.toggle);
        if (!r) return;
        const next = r.status === 'active' ? 'inactive' : 'active';
        if (!confirm(`${next === 'inactive' ? 'Deactivate' : 'Activate'} ${r.firstName} ${r.lastName}?`)) return;
        PortalApi.setReviewerStatus(r.id, next).then(() => bootstrapPortal()).then(() => renderView());
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
  const rankPanel = root.querySelector('#evalTabRank');
  if (rulesPanel) rulesPanel.hidden = tab !== 'rules';
  if (periodPanel) periodPanel.hidden = tab !== 'period';
  if (rankPanel) rankPanel.hidden = tab !== 'rank';
}

function renderEvaluationSettings(root, title) {
  title.textContent = 'Evaluation Settings';
  const tab = ['rules', 'period', 'rank'].includes(state.params.tab) ? state.params.tab : 'rules';
  const periodReadOnly = session.role === 'reviewer';

  root.innerHTML = `
    <div class="fl-eval-settings">
      <div class="fl-settings-tabs" role="tablist" aria-label="Evaluation settings sections">
        <button type="button" class="fl-settings-tab ${tab === 'rules' ? 'active' : ''}" role="tab" id="tab-btn-rules"
          aria-selected="${tab === 'rules'}" aria-controls="evalTabRules" data-eval-tab="rules">Scoring Rules</button>
        <button type="button" class="fl-settings-tab ${tab === 'period' ? 'active' : ''}" role="tab" id="tab-btn-period"
          aria-selected="${tab === 'period'}" aria-controls="evalTabPeriod" data-eval-tab="period">Evaluation Period</button>
        <button type="button" class="fl-settings-tab ${tab === 'rank' ? 'active' : ''}" role="tab" id="tab-btn-rank"
          aria-selected="${tab === 'rank'}" aria-controls="evalTabRank" data-eval-tab="rank">Rank simulation</button>
      </div>
      <div id="evalTabRules" class="fl-settings-panel" role="tabpanel" aria-labelledby="tab-btn-rules" ${tab !== 'rules' ? 'hidden' : ''}></div>
      <div id="evalTabPeriod" class="fl-settings-panel" role="tabpanel" aria-labelledby="tab-btn-period" ${tab !== 'period' ? 'hidden' : ''}></div>
      <div id="evalTabRank" class="fl-settings-panel" role="tabpanel" aria-labelledby="tab-btn-rank" ${tab !== 'rank' ? 'hidden' : ''}></div>
    </div>`;

  root.querySelectorAll('[data-eval-tab]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const next = btn.dataset.evalTab;
      if (state.params.tab === next) return;
      state.params = { ...state.params, tab: next };
      setEvalSettingsTab(root, next);
    });
  });

  const rulesHost = root.querySelector('#evalTabRules');
  const periodHost = root.querySelector('#evalTabPeriod');
  const rankHost = root.querySelector('#evalTabRank');
  try {
    renderConfig(rulesHost, title, { embedded: true });
  } catch (e) {
    console.error(e);
    if (rulesHost) {
      rulesHost.innerHTML = `<div class="card" style="padding:1rem"><h3>Could not load scoring rules</h3>
        <p>${e.message || 'Unknown error.'}</p>
        <button type="button" class="btn-primary-sm" id="evalRulesRetry">Retry</button></div>`;
      rulesHost.querySelector('#evalRulesRetry')?.addEventListener('click', () => {
        state.params = { ...state.params, tab: 'rules' };
        renderEvaluationSettings(root, title);
      });
    }
  }
  try {
    renderEvaluationPeriod(periodHost, title, { embedded: true, readOnly: periodReadOnly });
  } catch (e) {
    console.error(e);
    if (periodHost) {
      periodHost.innerHTML = `<div class="card" style="padding:1rem"><h3>Could not load evaluation period</h3>
        <p>${e.message || 'Unknown error.'}</p>
        <button type="button" class="btn-primary-sm" id="evalPeriodRetry">Retry</button></div>`;
      periodHost.querySelector('#evalPeriodRetry')?.addEventListener('click', () => {
        state.params = { ...state.params, tab: 'period' };
        renderEvaluationSettings(root, title);
      });
    }
  }
  try {
    renderRankSimulationSettings(rankHost, { readOnly: periodReadOnly });
  } catch (e) {
    console.error(e);
    if (rankHost) rankHost.innerHTML = `<div class="card" style="padding:1rem"><p>${e.message || 'Could not load rank simulation settings.'}</p></div>`;
  }
  setEvalSettingsTab(root, tab);
}

function renderRankSimulationSettings(root, { readOnly = false } = {}) {
  if (!root) return;
  const store = MockStore.load();
  const ic = store.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
  const rs = { ...DEFAULT_RANK_SIMULATION(), ...(ic.rankSimulation || {}) };
  const weightRows = RANK_CATEGORY_IDS.map((cat) => {
    const w = rs.weightMatrixByCategory?.[cat] || {};
    const cells = ['kra-I', 'kra-II', 'kra-III', 'kra-IV']
      .map(
        (kid) =>
          `<label style="display:block;font-size:0.85rem">${kid}<input type="number" step="0.01" min="0" max="1" data-rs-weight="${cat}:${kid}" value="${w[kid] ?? ''}" ${readOnly ? 'disabled' : ''}/></label>`
      )
      .join('');
    return `<details open><summary>${RANK_CATEGORY_LABELS[cat]}</summary><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.5rem;margin:0.5rem 0">${cells}</div></details>`;
  }).join('');
  const bracketRows = (rs.scoreBrackets || [])
    .map(
      (b, i) =>
        `<tr><td><input type="number" data-rs-bracket="${i}:min" value="${b.minInclusive}" ${readOnly ? 'disabled' : ''}/></td>
        <td><input type="number" data-rs-bracket="${i}:max" value="${b.maxInclusive}" ${readOnly ? 'disabled' : ''}/></td>
        <td><input type="number" data-rs-bracket="${i}:inc" value="${b.subRankIncrements}" ${readOnly ? 'disabled' : ''}/></td></tr>`
    )
    .join('');
  root.innerHTML = `
    <p class="muted" style="margin-top:0">Table 2.2 KRA weights by <strong>current</strong> faculty rank category · Table 3.1 sub-rank brackets · rank ladder from institution <code>rankOptions</code> (saved with institution config).</p>
    <details style="margin-top:0.5rem"><summary>Rank ladder order (${(ic.rankOptions || []).length} steps)</summary>
      <ol style="margin:0.5rem 0 0 1.25rem;font-size:0.9rem">${(ic.rankOptions || []).map((r) => `<li>${r}</li>`).join('') || '<li class="muted">No ranks configured</li>'}</ol>
    </details>
    <div class="card" style="padding:1rem;margin-top:0.75rem">
      <p class="muted" style="font-size:0.85rem">Source: ${rs.sourceRef || 'JC3 Tables 2.2 & 3.1'}</p>
      <h4 style="margin:1rem 0 0.5rem">Weight matrix</h4>
      ${weightRows}
      <h4 style="margin:1rem 0 0.5rem">Score brackets</h4>
      <table class="data-table"><thead><tr><th>Min</th><th>Max</th><th>Sub-ranks</th></tr></thead><tbody>${bracketRows}</tbody></table>
      <label style="display:block;margin-top:1rem">Decimal bracket policy
        <select id="rsDecimalPolicy" ${readOnly ? 'disabled' : ''}>
          <option value="unresolved" ${rs.decimalBracketPolicy === 'unresolved' ? 'selected' : ''}>Unresolved (default)</option>
          <option value="floor_to_bracket" ${rs.decimalBracketPolicy === 'floor_to_bracket' ? 'selected' : ''}>Floor to bracket</option>
          <option value="round_half_up" ${rs.decimalBracketPolicy === 'round_half_up' ? 'selected' : ''}>Round half up</option>
        </select>
      </label>
      ${readOnly ? '' : '<button type="button" class="btn-primary-sm btn-sm" id="saveRankSim" style="margin-top:1rem">Save rank simulation settings</button>'}
      <p id="rankSimMsg" class="muted" role="status" style="margin-top:0.5rem"></p>
    </div>`;
  if (readOnly) return;
  root.querySelector('#saveRankSim')?.addEventListener('click', async () => {
    const msg = root.querySelector('#rankSimMsg');
    const next = { ...rs, weightMatrixByCategory: { ...rs.weightMatrixByCategory } };
    root.querySelectorAll('[data-rs-weight]').forEach((inp) => {
      const [cat, kid] = inp.dataset.rsWeight.split(':');
      if (!next.weightMatrixByCategory[cat]) next.weightMatrixByCategory[cat] = {};
      next.weightMatrixByCategory[cat][kid] = Number(inp.value);
    });
    const brackets = (rs.scoreBrackets || []).map((b, i) => ({
      minInclusive: Number(root.querySelector(`[data-rs-bracket="${i}:min"]`)?.value),
      maxInclusive: Number(root.querySelector(`[data-rs-bracket="${i}:max"]`)?.value),
      subRankIncrements: Number(root.querySelector(`[data-rs-bracket="${i}:inc"]`)?.value),
    }));
    next.scoreBrackets = brackets;
    next.decimalBracketPolicy = root.querySelector('#rsDecimalPolicy')?.value || 'unresolved';
    next.status = 'published';
    const errs = validateRankSimulation(next);
    if (errs.length) {
      msg.textContent = errs.join(' ');
      return;
    }
    const s = MockStore.load();
    s.institutionConfig = { ...(s.institutionConfig || DEFAULT_INSTITUTION_CONFIG()), rankSimulation: next };
    try {
      await PortalApi.saveInstitution(s.institutionConfig);
      MockStore.save(s);
      msg.textContent = 'Rank simulation settings saved.';
    } catch (ex) {
      msg.textContent = ex.message || 'Save failed.';
    }
  });
}

function renderEvaluationPeriod(root, title, { embedded = false, readOnly = false } = {}) {
  if (!root) return;
  if (!embedded) title.textContent = 'Evaluation Period';
  const store = MockStore.load();
  const ic = store.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
  const period = { ...DEFAULT_INSTITUTION_CONFIG().preparationPeriod, ...(ic.preparationPeriod || {}) };
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

  document.getElementById('saveEvalPeriod').onclick = async () => {
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
    try {
      await PortalApi.saveInstitution(s.institutionConfig);
      await bootstrapPortal();
      msg.style.color = '';
      msg.textContent = `Saved. Evaluation period is ${computeEvaluationPeriodStatus(s.institutionConfig.preparationPeriod)} (${formatEvaluationDate(start)} – ${formatEvaluationDate(end)}).`;
      refreshPreview();
    } catch (ex) {
      msg.style.color = 'var(--fl-danger, #b42318)';
      msg.textContent = ex.message || 'Could not save evaluation period.';
    }
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
    if (!rules.catalog?.kras?.length) {
      document.getElementById('repOut').innerHTML =
        '<p class="muted">Open any page that loads the full portal state, or refresh after login, to load the published catalog for KRA summaries.</p>';
      return;
    }
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
        const q = MockStore.getReviewQueue().byFaculty?.[f.id] || {
          awaitingReview: 0,
          documentsPending: 0,
          achievementsPending: 0,
          bcEvidenceUnlinked: 0,
        };
        return `<motion class="card"><h3>${f.firstName} ${f.lastName}</h3><p>${f.rank} · ${f.department}</p>
          <p>Awaiting review: <strong>${q.awaitingReview}</strong> (${q.documentsPending} doc · ${q.achievementsPending} achievement)</p>
          ${q.bcEvidenceUnlinked ? `<p class="muted" style="font-size:0.85rem">${q.bcEvidenceUnlinked} B/C evidence file(s) not yet on a submitted achievement</p>` : ''}
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
      state.workspaceUi = { scrollByLevel: {}, folder: WS_FOLDER_FACULTY, facId: b.dataset.open };
      navigate('workspace');
    }));
  };
  draw();
  document.getElementById('asSearch').oninput = draw;
  document.getElementById('asStatus').onchange = draw;
}

const SET_SEF_PDF_KINDS = new Set(['set_sef_unified', 'set_sef_combined', 'set_sef_set_only', 'set_sef_sef_only']);
const SET_SEF_PDF_INDICATORS = new Set([
  'kra-I-A-setsef-eval',
  'kra-I-A-setsef-combined',
  'kra-I-A-set-pdf',
  'kra-I-A-sef-pdf',
]);

function isSetSefTeachingDoc(d) {
  return SET_SEF_PDF_KINDS.has(d.documentKind) || SET_SEF_PDF_INDICATORS.has(d.indicatorId);
}

function primarySetSefIndicatorId(d) {
  if (d.indicatorId && SET_SEF_PDF_INDICATORS.has(d.indicatorId)) return d.indicatorId;
  if (d.documentKind === 'set_sef_unified') return 'kra-I-A-setsef-eval';
  if (d.documentKind === 'set_sef_combined') return 'kra-I-A-setsef-combined';
  if (d.documentKind === 'set_sef_set_only') return 'kra-I-A-set-pdf';
  if (d.documentKind === 'set_sef_sef_only') return 'kra-I-A-sef-pdf';
  return d.indicatorId || '';
}

function docBelongsToIndicator(d, indId, catalogIndicatorIds) {
  if (d.indicatorId === indId) return true;
  if (!isSetSefTeachingDoc(d)) return false;
  const primary = primarySetSefIndicatorId(d);
  if (primary === indId) return true;
  if (indId === 'kra-I-A-setsef-eval' && !catalogIndicatorIds.has(primary)) return true;
  return false;
}

function ocrStatusLabel(s) {
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

const DOC_KIND_LABELS = {
  set_sef_unified: 'SET/SEF combined evaluation PDF',
  set_sef_combined: 'SET/SEF combined evaluation PDF',
  set_sef_set_only: 'SET evaluation PDF',
  set_sef_sef_only: 'SEF evaluation PDF',
};

function reviewDocumentTypeLabel(doc, isSetSef) {
  if (isSetSef) return DOC_KIND_LABELS[doc.documentKind] || 'SET/SEF evaluation PDF';
  const mime = doc.fileType || doc.mimeType || '';
  if (mime && mime !== '—') {
    if (mime === 'application/pdf') return 'PDF document';
    return mime.replace(/^application\//, '').replace(/\//, ' · ');
  }
  if (doc.fileName?.toLowerCase().endsWith('.pdf')) return 'PDF document';
  return 'Uploaded document';
}

function formatManilaDateTime(raw) {
  if (!raw || raw === '—') return '—';
  try {
    const hasTime = String(raw).includes('T');
    const d = new Date(hasTime ? raw : `${String(raw).slice(0, 10)}T12:00:00+08:00`);
    if (Number.isNaN(d.getTime())) return String(raw);
    return new Intl.DateTimeFormat('en-PH', {
      dateStyle: 'medium',
      timeStyle: hasTime ? 'short' : undefined,
      timeZone: 'Asia/Manila',
    }).format(d);
  } catch {
    return String(raw);
  }
}

function formatSemesterRating(v) {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(2) : String(v);
}

function verifyStatusShort(s) {
  if (s === 'verified') return 'Verified';
  if (s === 'needs_review') return 'Needs review';
  if (s === 'rejected') return 'Rejected';
  return s ? String(s).replace(/_/g, ' ') : 'Pending';
}

function identitySummaryFromRecords(records) {
  if (!records?.length) return { summary: '—', primary: null };
  const statuses = records.map((r) => r.facultyIdentityStatus).filter(Boolean);
  const unique = [...new Set(statuses)];
  if (!unique.length) return { summary: '—', primary: null };
  const primary = unique[0];
  if (unique.length === 1) return { summary: primary, primary };
  const exceptions = records.filter((r) => r.facultyIdentityStatus && r.facultyIdentityStatus !== primary).length;
  return { summary: `${primary} (${exceptions} row exception${exceptions === 1 ? '' : 's'})`, primary };
}

function processingStatusLabel(s) {
  const map = {
    completed: 'Complete',
    processing: 'Processing',
    failed: 'Failed',
    pending: 'Pending',
    queued: 'Queued',
  };
  return map[s] || s || '—';
}

function statusChip(label, tone = 'neutral') {
  return `<span class="doc-status-chip doc-status-chip--${tone}">${label}</span>`;
}

function verifyControlButton(kind, recordId, isVerified) {
  if (isVerified) return '';
  const attr = kind === 'set' ? `data-verify-set="${recordId}"` : `data-verify-sef="${recordId}"`;
  const label = kind === 'set' ? 'Verify SET' : 'Verify SEF';
  return `<button type="button" class="btn-verify" ${attr} data-verify-label="${label}">
    <span class="btn-verify__label">${label}</span>
  </button>`;
}

function formatScoringVerifiedHtml(scoringVer) {
  if (!scoringVer) return '—';
  return formatCriterionAEstimateHtml(scoringVer);
}

function formatScoringVerifiedReadonly(scoringVer) {
  if (!scoringVer) return '—';
  return formatCriterionAEstimateHtml(scoringVer).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

function verifyRowKey(recordId, kind) {
  return `${recordId}-${kind}`;
}

function ensureVerifyLiveRegion(pageRoot) {
  let live = pageRoot.querySelector('#docVerifyLive');
  if (!live) {
    live = document.createElement('div');
    live.id = 'docVerifyLive';
    live.className = 'visually-hidden';
    live.setAttribute('aria-live', 'polite');
    live.setAttribute('aria-atomic', 'true');
    pageRoot.prepend(live);
  }
  return live;
}

function announceVerifyStatus(pageRoot, message) {
  const live = ensureVerifyLiveRegion(pageRoot);
  live.textContent = '';
  requestAnimationFrame(() => {
    live.textContent = message;
  });
}

function snapshotVerifyBadge(pageRoot, recordId, kind) {
  const kindKey = kind === 'set' ? 'set' : 'sef';
  const badge = pageRoot.querySelector(`[data-record-badge="${recordId}-${kindKey}"]`);
  if (!badge) return null;
  return { v: badge.dataset.v || '', text: badge.textContent || '', syncing: badge.classList.contains('doc-verify-badge--syncing') };
}

function setVerifyBadgeSyncing(pageRoot, recordId, kind) {
  const kindKey = kind === 'set' ? 'set' : 'sef';
  const badgeLabel = kind === 'set' ? 'SET' : 'SEF';
  pageRoot.querySelectorAll(`[data-record-badge="${recordId}-${kindKey}"]`).forEach((badge) => {
    badge.dataset.v = 'syncing';
    badge.classList.add('doc-verify-badge--syncing');
    badge.textContent = `${badgeLabel} · Verified · syncing`;
  });
}

function restoreVerifyBadge(pageRoot, recordId, kind, snapshot) {
  if (!snapshot) return;
  const kindKey = kind === 'set' ? 'set' : 'sef';
  pageRoot.querySelectorAll(`[data-record-badge="${recordId}-${kindKey}"]`).forEach((badge) => {
    badge.dataset.v = snapshot.v;
    badge.classList.toggle('doc-verify-badge--syncing', snapshot.syncing);
    badge.textContent = snapshot.text;
  });
}

function setVerifyButtonsPending(btn, pending) {
  const pageRoot = btn.closest('.doc-review-page');
  const kind = btn.hasAttribute('data-verify-set') ? 'set' : 'sef';
  const recordId = btn.dataset.verifySet || btn.dataset.verifySef;
  const targets =
    pageRoot && recordId ? pageRoot.querySelectorAll(`[data-verify-${kind}="${recordId}"]`) : [btn];
  targets.forEach((target) => {
    target.disabled = pending;
    target.setAttribute('aria-busy', pending ? 'true' : 'false');
    target.classList.toggle('btn-verify--pending', pending);
  });
  if (!pending && recordId) {
    pageRoot?.querySelectorAll(`.btn-verify__err[data-for="${recordId}"]`).forEach((el) => el.remove());
  }
}

function showVerifyButtonError(btn, message = 'Verification was not saved.') {
  setVerifyButtonsPending(btn, false);
  const recordId = String(btn.dataset.verifySet || btn.dataset.verifySef);
  let err = btn.parentElement?.querySelector(`.btn-verify__err[data-for="${recordId}"]`);
  if (!err) {
    err = document.createElement('div');
    err.className = 'btn-verify__err';
    err.setAttribute('role', 'alert');
    err.dataset.for = recordId;
    btn.insertAdjacentElement('afterend', err);
  }
  err.innerHTML = '';
  err.append(document.createTextNode(message));
  const retry = document.createElement('button');
  retry.type = 'button';
  retry.className = 'btn-verify__retry';
  retry.textContent = 'Retry';
  retry.addEventListener('click', () => {
    err.remove();
    void runSemesterVerification(btn);
  });
  err.append(document.createTextNode(' '));
  err.append(retry);
}

function applyVerifiedBadgeFromServer(pageRoot, record, kind) {
  if (!record) return;
  const recordId = record.id;
  const kindKey = kind === 'set' ? 'set' : 'sef';
  const status = kind === 'set' ? record.setVerificationStatus : record.sefVerificationStatus;
  const badgeLabel = kind === 'set' ? 'SET' : 'SEF';
  pageRoot.querySelectorAll(`[data-record-badge="${recordId}-${kindKey}"]`).forEach((badge) => {
    badge.classList.remove('doc-verify-badge--syncing');
    badge.dataset.v = status || 'pending';
    badge.textContent = `${badgeLabel} · ${verifyStatusShort(status)}`;
  });
  if (status === 'verified') {
    pageRoot.querySelectorAll(`[data-verify-${kindKey}="${recordId}"]`).forEach((b) => {
      b.remove();
    });
    pageRoot.querySelectorAll(`.btn-verify__err[data-for="${recordId}"]`).forEach((el) => el.remove());
  }
}

function applyScoringSummaryFromServer(pageRoot, payload) {
  if (!payload) return;
  const ver = payload.scoring?.verified;
  const verDd = pageRoot.querySelector('#docScoreVerified');
  if (verDd && ver) verDd.innerHTML = formatScoringVerifiedHtml(ver);
  const counts = payload.verifyCounts;
  const countsEl = pageRoot.querySelector('#docVerifyCounts');
  if (countsEl && counts) {
    countsEl.innerHTML = `SET <strong>${counts.setVerified}/${counts.total}</strong> · SEF <strong>${counts.sefVerified}/${counts.total}</strong>`;
  }
  const verDisplay = pageRoot.querySelector('#docVerPtsDisplay');
  if (verDisplay && ver) verDisplay.textContent = formatScoringVerifiedReadonly(ver);
  const verPts = pageRoot.querySelector('#verPts');
  if (verPts && ver && !ver.incomplete) verPts.value = String(Number(ver.criterionAPoints ?? ''));
}

function beginVerifyInflight(pageRoot) {
  pageRoot._verifyInflight = (pageRoot._verifyInflight || 0) + 1;
}

function endVerifyInflight(pageRoot) {
  pageRoot._verifyInflight = Math.max(0, (pageRoot._verifyInflight || 1) - 1);
  reconcileVerifyScoring(pageRoot);
}

function queueVerifyScoring(pageRoot, payload, seq) {
  if (!pageRoot._verifyScoringQueue || seq >= pageRoot._verifyScoringQueue.seq) {
    pageRoot._verifyScoringQueue = { payload, seq };
  }
}

function reconcileVerifyScoring(pageRoot) {
  if ((pageRoot._verifyInflight || 0) > 0) return;
  const queued = pageRoot._verifyScoringQueue;
  if (!queued?.payload) return;
  applyScoringSummaryFromServer(pageRoot, queued.payload);
  pageRoot._verifyScoringAppliedSeq = queued.seq;
}

async function runSemesterVerification(btn) {
  if (!btn || btn.disabled) return;
  const pageRoot = btn.closest('.doc-review-page');
  if (!pageRoot) return;
  const docId = pageRoot.dataset.reviewDocId;
  if (!docId || state.route !== 'review') return;
  if ((state.params.docId || state.reviewDocId) !== docId) return;
  const kind = btn.hasAttribute('data-verify-set') ? 'set' : 'sef';
  const recordId = Number(btn.dataset.verifySet || btn.dataset.verifySef);
  if (!recordId) return;

  const rowKey = verifyRowKey(recordId, kind);
  pageRoot._verifyRowOps = pageRoot._verifyRowOps || {};
  pageRoot._verifyRowOps[rowKey] = (pageRoot._verifyRowOps[rowKey] || 0) + 1;
  const rowOpId = pageRoot._verifyRowOps[rowKey];
  const scoringSeq = (pageRoot._verifyScoringSeq = (pageRoot._verifyScoringSeq || 0) + 1);

  const badgeBefore = snapshotVerifyBadge(pageRoot, recordId, kind);
  setVerifyButtonsPending(btn, true);
  setVerifyBadgeSyncing(pageRoot, recordId, kind);
  announceVerifyStatus(pageRoot, 'Saving verification');

  beginVerifyInflight(pageRoot);
  const body = kind === 'set' ? { setVerificationStatus: 'verified' } : { sefVerificationStatus: 'verified' };
  try {
    const data = await PortalApi.patchSetSefSemester(docId, recordId, body);
    if (pageRoot._verifyRowOps[rowKey] !== rowOpId) return;
    if (state.route !== 'review' || (state.params.docId || state.reviewDocId) !== docId) return;
    applyVerifiedBadgeFromServer(pageRoot, data.record, kind);
    queueVerifyScoring(pageRoot, data, scoringSeq);
    reconcileVerifyScoring(pageRoot);
    announceVerifyStatus(pageRoot, 'Verification saved.');
  } catch (e) {
    if (pageRoot._verifyRowOps[rowKey] !== rowOpId) return;
    restoreVerifyBadge(pageRoot, recordId, kind, badgeBefore);
    setVerifyButtonsPending(btn, false);
    showVerifyButtonError(btn, e.message ? `Verification was not saved. ${e.message}` : 'Verification was not saved.');
    announceVerifyStatus(pageRoot, 'Verification was not saved.');
  } finally {
    endVerifyInflight(pageRoot);
  }
}

const REVIEW_ACTION_LABELS = {
  approved: 'Approve document',
  correction_requested: 'Request changes',
  rejected: 'Reject document',
};

function reviewDecisionPlain(action) {
  if (action === 'approved') return 'Approval';
  if (action === 'correction_requested') return 'Change request';
  if (action === 'rejected') return 'Rejection';
  return 'Decision';
}

function setReviewDecisionSyncing(pageRoot, syncing, action) {
  if (!pageRoot) return;
  const actions = pageRoot.querySelector('.doc-review-actions');
  actions?.classList.toggle('doc-review-actions--syncing', syncing);
  actions?.querySelectorAll('[data-action]').forEach((btn) => {
    const key = btn.dataset.action;
    btn.disabled = syncing;
    if (!syncing) {
      btn.textContent = REVIEW_ACTION_LABELS[key] || btn.textContent;
      btn.removeAttribute('aria-busy');
      return;
    }
    if (key === action) {
      btn.textContent = 'Saving…';
      btn.setAttribute('aria-busy', 'true');
    }
  });
  const badge = pageRoot.querySelector('#docReviewDecisionBadge');
  if (badge) {
    badge.hidden = !syncing;
    badge.textContent = syncing ? `Syncing ${reviewDecisionPlain(action).toLowerCase()}…` : '';
  }
}

function showReviewDecisionSaveError(pageRoot, message, onRetry) {
  const err = pageRoot?.querySelector('#revErr');
  if (!err) return;
  err.innerHTML = '';
  const text = document.createElement('span');
  text.textContent = message || 'Decision was not saved.';
  err.appendChild(text);
  if (onRetry) {
    const retry = document.createElement('button');
    retry.type = 'button';
    retry.className = 'btn-ghost btn-sm doc-review-actions__retry';
    retry.textContent = 'Retry';
    retry.addEventListener('click', onRetry);
    err.appendChild(document.createTextNode(' '));
    err.appendChild(retry);
  }
}

function ensureSetSefVerificationDelegation() {
  const host = document.getElementById('appContent');
  if (!host || host._verifyDelegationBound) return;
  host._verifyDelegationBound = true;
  host.addEventListener('click', (ev) => {
    const btn = ev.target.closest('[data-verify-set], [data-verify-sef]');
    if (!btn || !btn.closest('.doc-review-page') || btn.disabled) return;
    if (ev.target.closest('.btn-verify__retry')) return;
    ev.preventDefault();
    void runSemesterVerification(btn);
  });
}

let _workspaceRenderSeq = 0;

function workspaceRenderActive(seq) {
  return state.route === 'workspace' && seq === _workspaceRenderSeq;
}

function reviewRenderActive(seq) {
  return state.route === 'review' && seq === _workspaceRenderSeq;
}

function showWorkspaceLoadError(root, title, err) {
  title.textContent = 'Check Documents';
  const msg = err?.message || portalLoadError()?.message || 'Could not load workspace.';
  root.innerHTML = `
    <div class="card" style="margin-top:1rem;border-color:#c62828">
      <h3>Error loading workspace</h3>
      <p>${msg}</p>
      <button type="button" class="btn-primary-sm btn-sm" id="wsLoadRetry">Retry</button>
      <button type="button" class="btn-ghost btn-sm" id="wsLoadBack">Back to assigned faculty</button>
    </div>`;
  root.querySelector('#wsLoadRetry')?.addEventListener('click', () => {
    void renderWorkspace(root, title).catch((e) => showWorkspaceLoadError(root, title, e));
  });
  root.querySelector('#wsLoadBack')?.addEventListener('click', () => navigate('assigned'));
}

function workspaceCatalogStatusMessage(rules, catalogLoad) {
  if (catalogLoad?.ok === false && catalogLoad.reason === 'error') {
    return null;
  }
  if (rules.state === 'no_published') {
    return '<p class="muted">No published assessment catalog is configured yet. An administrator must publish evaluation rules before achievement folders use catalog labels.</p>';
  }
  if (rules.state === 'catalog_not_loaded') {
    return '<p class="muted">Published catalog metadata is present but the rule tree is not loaded. Try refresh or contact an administrator.</p>';
  }
  return '';
}

function bindWorkspaceDocButtons(root) {
  root.querySelectorAll('[data-doc]').forEach((b) => {
    b.onclick = () => {
      saveWorkspaceScroll(root);
      navigate('review', {
        docId: b.dataset.doc,
        restore: true,
        wsFolder: state.workspaceUi?.folder || WS_FOLDER_CRITERION,
        criterionId: state.workspaceUi?.criterionId || 'kra-I-A',
      });
    };
  });
}

function bindWorkspaceInteractions(root, title, renderSeq) {
  bindWorkspaceDocButtons(root);
  const facSelect = root.querySelector('#wsFac');
  if (facSelect) {
    facSelect.onchange = (e) => {
      state.workspaceFacultyId = e.target.value;
      state.workspaceUi = { scrollByLevel: {}, folder: WS_FOLDER_FACULTY, facId: e.target.value };
      void renderWorkspace(root, title).catch((err) => showWorkspaceLoadError(root, title, err));
    };
  }
}

function isWorkspaceAchievementCriterion(criterionId) {
  return (
    criterionId === 'kra-I-B' ||
    criterionId === 'kra-I-C' ||
    criterionId === 'kra-II-A' ||
    criterionId === 'kra-II-B' ||
    criterionId === 'kra-II-C' ||
    criterionId === 'kra-III-A' ||
    criterionId === 'kra-III-B' ||
    criterionId === 'kra-III-C' ||
    criterionId === 'kra-III-D' ||
    criterionId === 'kra-IV-A' ||
    criterionId === 'kra-IV-B' ||
    criterionId === 'kra-IV-C' ||
    criterionId === 'kra-IV-D'
  );
}

const KRA_IV_CRITERION_SECTIONS = {
  'kra-IV-A': {
    criterionId: 'kra-IV-A',
    cap: 20,
    empty: 'No professional organization achievements yet.',
    hostId: '#wsFolderContent',
  },
  'kra-IV-B': {
    criterionId: 'kra-IV-B',
    cap: 60,
    empty: 'No continuing development achievements yet.',
    hostId: '#wsFolderContent',
  },
  'kra-IV-C': {
    criterionId: 'kra-IV-C',
    cap: 20,
    empty: 'No awards or recognition achievements yet.',
    hostId: '#wsFolderContent',
  },
  'kra-IV-D': {
    criterionId: 'kra-IV-D',
    cap: 20,
    empty: 'No newly appointed faculty additional points yet.',
    hostId: '#wsFolderContent',
  },
};

const KRA_I_CRITERION_SECTIONS = {
  'kra-I-B': {
    criterionId: 'kra-I-B',
    cap: 30,
    empty: 'No Criterion B submissions yet.',
    hostId: '#wsFolderContent',
  },
  'kra-I-C': {
    criterionId: 'kra-I-C',
    cap: 10,
    empty: 'No Criterion C submissions yet.',
    hostId: '#wsFolderContent',
  },
};

const KRA_III_CRITERION_SECTIONS = {
  'kra-III-A': {
    criterionId: 'kra-III-A',
    cap: 30,
    empty: 'No institution-service achievements yet.',
    hostId: '#wsFolderContent',
  },
  'kra-III-B': {
    criterionId: 'kra-III-B',
    cap: 50,
    empty: 'No community-service achievements yet.',
    hostId: '#wsFolderContent',
  },
  'kra-III-C': {
    criterionId: 'kra-III-C',
    cap: 20,
    empty: 'No extension-quality achievements yet.',
    hostId: '#wsFolderContent',
  },
  'kra-III-D': {
    criterionId: 'kra-III-D',
    cap: 20,
    empty: 'No bonus designation achievements yet.',
    hostId: '#wsFolderContent',
  },
};

const KRA_II_CRITERION_SECTIONS = {
  'kra-II-A': {
    criterionId: 'kra-II-A',
    cap: 100,
    empty: 'No submitted research-output achievements yet.',
    hostId: '#wsFolderContent',
  },
  'kra-II-B': {
    criterionId: 'kra-II-B',
    cap: 100,
    empty: 'No submitted invention achievements yet.',
    hostId: '#wsFolderContent',
  },
  'kra-II-C': {
    criterionId: 'kra-II-C',
    cap: 100,
    empty: 'No submitted creative-work achievements yet.',
    hostId: '#wsFolderContent',
  },
};

function workspaceCriterionMeta(criterionId) {
  return (
    KRA_I_CRITERION_SECTIONS[criterionId] ||
    KRA_II_CRITERION_SECTIONS[criterionId] ||
    KRA_III_CRITERION_SECTIONS[criterionId] ||
    KRA_IV_CRITERION_SECTIONS[criterionId]
  );
}

function capAchievementPoints(sum, cap) {
  return cap != null ? Math.min(sum, cap) : sum;
}

function sumCriterionAchievementPoints(list, { verified }) {
  let sum = 0;
  for (const a of list) {
    if (a.submissionStatus !== 'submitted') continue;
    if (verified) {
      if (a.reviewStatus === 'approved' && a.reviewerVerifiedPoints != null) {
        sum += Number(a.reviewerVerifiedPoints);
      }
    } else {
      sum += Number(a.claimedPoints || 0);
    }
  }
  return sum;
}

function saveWorkspaceScroll(root) {
  const el = root.querySelector('[data-ws-scroll]');
  if (!el) return;
  const key = workspaceScrollKey(state.workspaceUi);
  if (!state.workspaceUi.scrollByLevel) state.workspaceUi.scrollByLevel = {};
  state.workspaceUi.scrollByLevel[key] = el.scrollTop;
  state.workspaceUi.scrollTop = el.scrollTop;
}

function resolveWorkspaceNav(facId) {
  if (state.params.restore) {
    const folder = state.params.wsFolder || state.workspaceUi?.folder || WS_FOLDER_FACULTY;
    const criterionId = state.params.criterionId || state.workspaceUi?.criterionId || null;
    return { folder, criterionId };
  }
  if (state.workspaceUi?.facId && state.workspaceUi.facId !== facId) {
    return { folder: WS_FOLDER_FACULTY, criterionId: null };
  }
  if (state.params.wsFolder) {
    return {
      folder: state.params.wsFolder,
      criterionId: state.params.criterionId || state.workspaceUi?.criterionId || null,
    };
  }
  return {
    folder: state.workspaceUi?.folder || WS_FOLDER_FACULTY,
    criterionId: state.workspaceUi?.criterionId || null,
  };
}

function wsSetFolder(folder, criterionId) {
  state.workspaceUi = {
    ...state.workspaceUi,
    folder,
    criterionId: criterionId || null,
    facId: state.workspaceFacultyId,
  };
  state.params = { ...state.params, wsFolder: folder, criterionId: criterionId || undefined };
}

function bindWorkspaceFolderNav(root, title, renderSeq) {
  root.querySelectorAll('[data-ws-nav]').forEach((btn) => {
    btn.addEventListener('click', () => {
      saveWorkspaceScroll(root);
      const target = btn.dataset.wsNav;
      if (target === WS_FOLDER_KRA_I) wsSetFolder(WS_FOLDER_KRA_I, null);
      else if (target === WS_FOLDER_KRA_II) wsSetFolder(WS_FOLDER_KRA_II, null);
      else if (target === WS_FOLDER_KRA_III) wsSetFolder(WS_FOLDER_KRA_III, null);
      else if (target === WS_FOLDER_KRA_IV) wsSetFolder(WS_FOLDER_KRA_IV, null);
      else if (target === WS_FOLDER_CRITERION) wsSetFolder(WS_FOLDER_CRITERION, btn.dataset.wsCriterion);
      void renderWorkspace(root, title).catch((err) => showWorkspaceLoadError(root, title, err));
    });
    btn.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        btn.click();
      }
    });
  });
  bindWorkspaceBreadcrumbNav(root, {
    onCrumb: (id, crit) => {
      saveWorkspaceScroll(root);
      if (id === 'assigned') {
        navigate('assigned');
        return;
      }
      if (id === WS_FOLDER_FACULTY) wsSetFolder(WS_FOLDER_FACULTY, null);
      else if (id === WS_FOLDER_KRA_I) wsSetFolder(WS_FOLDER_KRA_I, null);
      else if (id === WS_FOLDER_KRA_II) wsSetFolder(WS_FOLDER_KRA_II, null);
      else if (id === WS_FOLDER_KRA_III) wsSetFolder(WS_FOLDER_KRA_III, null);
      else if (id === WS_FOLDER_KRA_IV) wsSetFolder(WS_FOLDER_KRA_IV, null);
      else if (id === 'criterion') wsSetFolder(WS_FOLDER_CRITERION, crit || null);
      void renderWorkspace(root, title).catch((err) => showWorkspaceLoadError(root, title, err));
    },
  });
}

function paintWorkspaceCriterionAchievements(host, root, facId, criterionId, list, storeFresh, catalog) {
  const meta = workspaceCriterionMeta(criterionId);
  if (!host || !meta) return;
  const claimed = capAchievementPoints(sumCriterionAchievementPoints(list, { verified: false }), meta.cap);
  const verified = capAchievementPoints(sumCriterionAchievementPoints(list, { verified: true }), meta.cap);
  const totalsHtml = `<p style="font-size:0.9rem;margin:0.35rem 0 0.5rem">Faculty-claimed total: <strong>${claimed.toFixed(2)}</strong> · Reviewer-verified total: <strong>${verified.toFixed(2)}</strong> · Maximum <strong>${meta.cap}</strong> points.</p>`;
  if (!list.length) {
    const orphan = countBcOrphanEvidence(storeFresh, facId, criterionId);
    const orphanNote =
      orphan > 0
        ? `<p class="muted" style="font-size:0.85rem;margin-top:0.35rem">${orphan} unlinked supporting file(s) — see <strong>Unlinked files (recovery)</strong> below.</p>`
        : '';
    host.innerHTML = `${totalsHtml}<p class="muted">${meta.empty}</p>${orphanNote}`;
    return;
  }
  const expanded = state.workspaceUi?.expandedIndicators?.[criterionId] || {};
  host.innerHTML =
    totalsHtml +
    buildCriterionAchievementsFolderHtml({
      list,
      facId,
      store: storeFresh,
      catalog,
        meta: workspaceCriterionMeta(criterionId),
      expandedIndicators: expanded,
    });
  bindCriterionFolderNavigation(host, {
    facId,
    onExpandChange: (indId, open) => {
      if (!state.workspaceUi.expandedIndicators) state.workspaceUi.expandedIndicators = {};
      if (!state.workspaceUi.expandedIndicators[criterionId]) state.workspaceUi.expandedIndicators[criterionId] = {};
      state.workspaceUi.expandedIndicators[criterionId][indId] = open;
    },
  });
  host.addEventListener('fl-open-achievement-review', (e) => {
    saveWorkspaceScroll(root);
    const { achievementId, facultyId, criterionId: crit } = e.detail;
    state.workspaceFacultyId = facultyId || facId;
    const ach = list.find((a) => a.id === achievementId);
    wsSetFolder(WS_FOLDER_CRITERION, crit || criterionId);
    navigate('achievement-review', {
      facultyId: facultyId || facId,
      criterionId: crit || criterionId,
      achievementId,
      docId: ach?.documentIds?.[0],
      wsFolder: WS_FOLDER_CRITERION,
    });
  });
}

function achievementFetchErrorHtml(criterionId, message) {
  return `<p class="fl-error" role="alert">Could not load achievements: ${message || 'Request failed.'}</p>
    <button type="button" class="btn-ghost btn-sm" data-ach-retry="${criterionId}">Retry</button>`;
}

async function renderWorkspace(root, title) {
  const renderSeq = ++_workspaceRenderSeq;
  const savedScroll = root.querySelector('[data-ws-scroll]')?.scrollTop ?? 0;
  title.textContent = 'Check Documents';
  const store = MockStore.load();
  const facId = state.workspaceFacultyId || store.faculty.find((f) => f.reviewerId === session.reviewerId)?.id;
  const fac = store.faculty.find((f) => f.id === facId);
  if (!fac) {
    root.innerHTML = '<p>Select a faculty member from Assigned Faculty.</p>';
    return;
  }

  const catalogLoad = publishedCatalogReady(store)
    ? { ok: true, store }
    : await ensurePublishedCatalog();
  if (!workspaceRenderActive(renderSeq)) return;

  if (catalogLoad.reason === 'error') {
    const err = catalogLoad.error || new Error('Could not load published catalog.');
    showWorkspaceLoadError(root, title, err);
    return;
  }

  const storeFresh = catalogLoad.store || MockStore.load();
  const ass = storeFresh.assessments[facId] || { setSef: { SET: [], SEF: [] }, entries: {} };
  const rules = rulesForFaculty(storeFresh, facId);
  const catalogOk = rules.state === 'ok' && rules.catalog;
  const catalogForUi = catalogOk ? rules.catalog : null;
  const kraSum = catalogOk ? computeKraSummaries(ass, rules.catalog, rules.kraWeights) : { overallWeighted: 0, byKra: {} };
  const ic = storeFresh.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
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
  const verSum = catalogOk
    ? computeKraSummaries(verifiedAss, rules.catalog, rules.kraWeights)
    : { overallWeighted: 0, byKra: {} };

  const catalogBanner = workspaceCatalogStatusMessage(rules, catalogLoad);
  const nav = resolveWorkspaceNav(facId);
  wsSetFolder(nav.folder, nav.criterionId);
  const folder = state.workspaceUi.folder;
  const criterionId = state.workspaceUi.criterionId;

  const needsAchievementData =
    folder === WS_FOLDER_FACULTY ||
    folder === WS_FOLDER_KRA_I ||
    folder === WS_FOLDER_KRA_II ||
    folder === WS_FOLDER_KRA_III ||
    folder === WS_FOLDER_KRA_IV ||
    (folder === WS_FOLDER_CRITERION && isWorkspaceAchievementCriterion(criterionId));
  const achEntry = getFacultyAchievementsEntry(facId);
  const kraCounts = kraIInstructionCounts(storeFresh, facId, achEntry);
  const kraIICounts = kraIIResearchCounts(achEntry);
  const kraIIICounts = kraIIIExtensionCounts(achEntry);
  const kraIVCounts = kraIVProfessionalCounts(achEntry);
  const breadcrumb = buildWorkspaceBreadcrumb({
    fac,
    folder,
    criterionId,
    catalog: catalogForUi,
  });

  let folderBody = '';
  if (folder === WS_FOLDER_FACULTY) {
    folderBody = buildFacultyRootFolderHtml(kraCounts, kraIICounts, kraIIICounts, kraIVCounts);
  } else if (folder === WS_FOLDER_KRA_I) {
    folderBody = buildKraICriterionFoldersHtml(catalogForUi, kraCounts);
  } else if (folder === WS_FOLDER_KRA_II) {
    folderBody = buildKraIICriterionFoldersHtml(catalogForUi, kraIICounts);
  } else if (folder === WS_FOLDER_KRA_III) {
    folderBody = buildKraIIICriterionFoldersHtml(catalogForUi, kraIIICounts);
  } else if (folder === WS_FOLDER_KRA_IV) {
    folderBody = buildKraIVCriterionFoldersHtml(catalogForUi, kraIVCounts);
  } else if (folder === WS_FOLDER_CRITERION && criterionId) {
    folderBody = buildCriterionDetailShell(criterionId, workspaceCriterionHeading(catalogForUi, criterionId));
  } else {
    folderBody = buildFacultyRootFolderHtml(kraCounts, kraIICounts, kraIIICounts, kraIVCounts);
    wsSetFolder(WS_FOLDER_FACULTY, null);
  }

  root.innerHTML = `
    <div class="workspace-page" data-ws-scroll>
    ${pageIntro(SCREEN_INTRO.workspace)}
    <p class="muted" style="font-size:0.9rem">${KRA_HELP}</p>
    ${breadcrumb}
    <motion class="toolbar ws-faculty-toolbar"><label class="visually-hidden" for="wsFac">Faculty</label><select id="wsFac">${storeFresh.faculty.map((f) => `<option value="${f.id}" ${f.id === facId ? 'selected' : ''}>${f.firstName} ${f.lastName}</option>`).join('')}</select></motion>
    ${catalogBanner || ''}
    <section class="ws-folder-panel" aria-label="KRA workspace folders">${folderBody}</section>
    ${
      folder === WS_FOLDER_KRA_I && (countBcOrphanEvidence(storeFresh, facId, 'kra-I-B') + countBcOrphanEvidence(storeFresh, facId, 'kra-I-C')) > 0
        ? `<div id="wsRecoveryMount" class="ws-recovery-mount--kra"></div>`
        : ''
    }
    ${
      folder === WS_FOLDER_FACULTY
        ? `<details class="ws-kra-reference card">
      <summary class="ws-kra-reference__summary">Weighted KRA simulation (reference)</summary>
      <p>Estimated weighted total: <strong>${estWt.toFixed(2)}</strong> · Reviewer-verified weighted: <strong>${verSum.overallWeighted.toFixed(2)}</strong></p>
      <p class="muted" style="font-size:0.85rem">Preparation only — not an official promotion decision.${catalogOk ? ` Rules: ${rules.versionId}${rules.pinned ? ' (pinned to assessment)' : ''}.` : ' Requires a published catalog.'}</p>
      ${
        catalogOk
          ? Object.values(kraSum.byKra)
              .map(
                (k) =>
                  `<div style="margin-top:0.35rem">${k.name}: est. ${k.weightedContribution.toFixed(2)} · verified ${(verSum.byKra[k.kraId]?.weightedContribution ?? 0).toFixed(2)}</div>`
              )
              .join('')
          : '<p class="muted" style="font-size:0.9rem">Manual KRA weighting is hidden until the published rule tree is loaded.</p>'
      }
      <p style="margin-top:0.5rem;font-size:0.85rem">Rank mapping: <strong>${ic.rankMappingStatus === 'configured' ? 'Configured' : 'Pending configuration'}</strong></p>
    </details>`
        : ''
    }
    </div>`;

  root.querySelectorAll('motion').forEach((m) => {
    const d = document.createElement(m.tagName === 'motion' ? 'div' : 'div');
    d.className = m.className;
    d.innerHTML = m.innerHTML;
    m.replaceWith(d);
  });

  bindWorkspaceInteractions(root, title, renderSeq);
  bindWorkspaceFolderNav(root, title, renderSeq);
  const scrollEl = root.querySelector('[data-ws-scroll]');
  const scrollKey = workspaceScrollKey(state.workspaceUi);
  const levelScroll = state.workspaceUi?.scrollByLevel?.[scrollKey];
  const restoreScroll = state.params.restore ? levelScroll ?? state.workspaceUi?.scrollTop : savedScroll;
  if (scrollEl && restoreScroll) scrollEl.scrollTop = restoreScroll;
  if (state.params.restore) {
    state.params = { ...state.params, restore: false };
  }
  scrollEl?.addEventListener(
    'scroll',
    () => {
      state.workspaceUi.scrollTop = scrollEl.scrollTop;
    },
    { passive: true }
  );

  if (folder === WS_FOLDER_CRITERION && criterionId === 'kra-I-A') {
    const host = root.querySelector('#wsFolderContent');
    if (host) {
      host.innerHTML = `<div id="wsCritAScores" class="ws-criterion-card__body"><p class="muted">Loading SET/SEF totals…</p></div>
        <div id="wsCritADocs" class="ws-criterion-card__body ws-criterion-card__body--docs"></div>`;
      host.querySelector('#wsCritADocs').innerHTML = buildCriterionADocumentsHtml(storeFresh, facId, catalogForUi);
      bindWorkspaceDocButtons(root);
      void (async () => {
        try {
          const critA = await PortalApi.fetchFacultyCriterionA(facId);
          if (!workspaceRenderActive(renderSeq)) return;
          const scoresHost = root.querySelector('#wsCritAScores');
          if (scoresHost) scoresHost.innerHTML = formatCriterionAScoresHtml(critA, null);
        } catch (e) {
          if (!workspaceRenderActive(renderSeq)) return;
          const scoresHost = root.querySelector('#wsCritAScores');
          if (scoresHost) scoresHost.innerHTML = formatCriterionAScoresHtml(null, e.message || 'Could not load Criterion A totals.');
        }
      })();
    }
  } else if (folder === WS_FOLDER_CRITERION && isWorkspaceAchievementCriterion(criterionId)) {
    const host = root.querySelector('#wsFolderContent');
    if (host) {
      const entry = getFacultyAchievementsEntry(facId);
      if (entry.state === ACH_LOAD_LOADED) {
        const list = achievementsForCriterion(entry.achievements, criterionId);
        paintWorkspaceCriterionAchievements(host, root, facId, criterionId, list, storeFresh, catalogForUi);
      } else if (entry.state === ACH_LOAD_ERROR) {
        host.innerHTML = achievementFetchErrorHtml(criterionId, entry.error?.message);
        host.querySelector(`[data-ach-retry="${criterionId}"]`)?.addEventListener('click', () => {
          invalidateFacultyAchievementsCache(facId);
          void ensureFacultyAchievementsLoaded(facId).then((next) => {
            if (!workspaceRenderActive(renderSeq)) return;
            if (next.state === ACH_LOAD_LOADED) {
              paintWorkspaceCriterionAchievements(
                host,
                root,
                facId,
                criterionId,
                achievementsForCriterion(next.achievements, criterionId),
                storeFresh,
                catalogForUi
              );
            } else if (next.state === ACH_LOAD_ERROR) {
              host.innerHTML = achievementFetchErrorHtml(criterionId, next.error?.message);
            }
          });
        });
      } else {
        host.innerHTML = '<p class="muted" aria-busy="true">Loading submitted achievements…</p>';
      }
    }
    if (countBcOrphanEvidence(storeFresh, facId, criterionId) > 0) {
      const rec = document.createElement('div');
      rec.innerHTML = buildWorkspaceRecoveryHtml(storeFresh, facId);
      const recoveryDetails = rec.firstElementChild;
      if (recoveryDetails && host) {
        host.appendChild(recoveryDetails);
        bindWorkspaceDocButtons(root);
      }
    }
  }

  const recoveryMount = root.querySelector('#wsRecoveryMount');
  if (recoveryMount) {
    recoveryMount.innerHTML = buildWorkspaceRecoveryHtml(storeFresh, facId);
    bindWorkspaceDocButtons(root);
  }

  if (needsAchievementData && achEntry.state !== ACH_LOAD_LOADED && achEntry.state !== ACH_LOAD_ERROR) {
    void ensureFacultyAchievementsLoaded(facId).then((entry) => {
      if (!workspaceRenderActive(renderSeq)) return;
      const nextCounts = kraIInstructionCounts(storeFresh, facId, entry);
      const nextIICounts = kraIIResearchCounts(entry);
      const nextIIICounts = kraIIIExtensionCounts(entry);
      const nextIVCounts = kraIVProfessionalCounts(entry);
      patchWorkspaceFolderMetas(root, nextCounts, nextIICounts, nextIIICounts, nextIVCounts, catalogForUi, folder);
      if (entry.state === ACH_LOAD_LOADED && folder === WS_FOLDER_CRITERION && isWorkspaceAchievementCriterion(criterionId)) {
        const host = root.querySelector('#wsFolderContent');
        const list = achievementsForCriterion(entry.achievements, criterionId);
        paintWorkspaceCriterionAchievements(host, root, facId, criterionId, list, storeFresh, catalogForUi);
      }
    });
  } else if (needsAchievementData && achEntry.state === ACH_LOAD_LOADED) {
    void ensureFacultyAchievementsLoaded(facId, { background: true });
  }

  if (folder === WS_FOLDER_FACULTY) void revalidatePortalInBackground();
}

async function renderDocumentReview(root, title) {
  const renderSeq = ++_workspaceRenderSeq;
  title.textContent = 'Check this document';
  const store = MockStore.load();
  const doc = store.documents.find((d) => d.id === (state.params.docId || state.reviewDocId));
  if (!doc) {
    root.innerHTML = '<p>Document not found.</p><button class="btn-ghost btn-sm" onclick="history.back()">Back</button>';
    return;
  }
  const catalogReady = publishedCatalogReady(store);
  if (!catalogReady) {
    await ensurePublishedCatalog();
  }
  if (!reviewRenderActive(renderSeq)) return;

  const storeFresh = MockStore.load();
  const docFresh = storeFresh.documents.find((d) => d.id === doc.id) || doc;
  const bcParentLink = parentLinkForDocument(docFresh, storeFresh.assessments);
  const bcEvidenceDoc = isKraIAchievementIndicator(docFresh.indicatorId);
  const bcReviewViaAchievement = bcEvidenceDoc && bcParentLink?.achievement;
  const rulesCtx = rulesForFaculty(storeFresh, docFresh.facultyId);
  let meta = null;
  if (rulesCtx.catalog?.kras?.length) {
    meta = rulesCtx.catalog.kras
      .flatMap((k) => k.criteria.flatMap((c) => c.indicators.map((i) => ({ kra: k, c, i }))))
      .find((x) => x.i.id === docFresh.indicatorId);
  }
  const isSetSefPdf = isSetSefTeachingDoc(docFresh);
  let setSefPayload = null;
  if (isSetSefPdf) {
    try {
      setSefPayload = await PortalApi.fetchSetSefExtraction(docFresh.id);
    } catch {
      setSefPayload = null;
    }
  }
  if (!reviewRenderActive(renderSeq)) return;

  const formatSourcePages = (r) => {
    const pages = [...new Set([...(r.setSourcePages || []), ...(r.sefSourcePages || [])])].sort((a, b) => a - b);
    if (!pages.length) return '—';
    return pages
      .map((p) => `<button type="button" class="doc-page-ref" data-goto-page="${p}" title="Show page ${p} in PDF">p.${p}</button>`)
      .join(' ');
  };

  const scoringEst = setSefPayload?.scoring?.estimated;
  const scoringVer = setSefPayload?.scoring?.verified;
  const semesterRecords = setSefPayload?.semesterRecords || [];
  const identityInfo = identitySummaryFromRecords(semesterRecords);
  const setVerifiedCount = semesterRecords.filter((r) => r.setVerificationStatus === 'verified').length;
  const sefVerifiedCount = semesterRecords.filter((r) => r.sefVerificationStatus === 'verified').length;
  const semTotal = semesterRecords.length;

  const facultyMember = storeFresh.faculty.find((f) => f.id === docFresh.facultyId);
  const facultyDisplay = facultyMember
    ? `${facultyMember.firstName} ${facultyMember.lastName}`.trim()
    : semesterRecords[0]?.facultyNameExtracted || '—';
  const extractedName = semesterRecords[0]?.facultyNameExtracted;
  const identityNote =
    extractedName && facultyMember && extractedName.toLowerCase() !== facultyDisplay.toLowerCase()
      ? `<p class="doc-review-meta__note">Extracted name in PDF: <strong>${extractedName}</strong></p>`
      : '';

  const semesterRowHtml = (r) => {
    const rowIdentity =
      identityInfo.primary && r.facultyIdentityStatus && r.facultyIdentityStatus !== identityInfo.primary
        ? `<span class="doc-sem-identity-except" title="Identity on this row">${r.facultyIdentityStatus}</span>`
        : '';
    return `<tr data-sid="${r.id}">
      <td>${r.academicYear || '—'}</td>
      <td>${r.semester || '—'}</td>
      <td class="doc-sem-num">${formatSemesterRating(r.setRatingConfirmed ?? r.setRatingExtracted)}</td>
      <td class="doc-sem-num">${formatSemesterRating(r.sefRatingConfirmed ?? r.sefRatingExtracted)}</td>
      <td class="doc-sem-verify-col">${rowIdentity}
        <div class="doc-sem-verify">
          <span class="doc-verify-badge" data-record-badge="${r.id}-set" data-v="${r.setVerificationStatus || 'pending'}">SET · ${verifyStatusShort(r.setVerificationStatus)}</span>
          ${verifyControlButton('set', r.id, r.setVerificationStatus === 'verified')}
        </div>
        <div class="doc-sem-verify">
          <span class="doc-verify-badge" data-record-badge="${r.id}-sef" data-v="${r.sefVerificationStatus || 'pending'}">SEF · ${verifyStatusShort(r.sefVerificationStatus)}</span>
          ${verifyControlButton('sef', r.id, r.sefVerificationStatus === 'verified')}
        </div>
      </td>
      <td class="doc-sem-pages">${formatSourcePages(r)}</td>
    </tr>`;
  };

  const semesterCardHtml = (r) => {
    const rowIdentity =
      identityInfo.primary && r.facultyIdentityStatus && r.facultyIdentityStatus !== identityInfo.primary
        ? `<p class="doc-sem-card__except">Identity: ${r.facultyIdentityStatus}</p>`
        : '';
    return `<article class="doc-sem-card" data-sid="${r.id}">
      <header class="doc-sem-card__head">
        <strong>${r.academicYear || '—'} · ${r.semester || '—'}</strong>
        <span class="doc-sem-card__pages">${formatSourcePages(r)}</span>
      </header>
      <dl class="doc-sem-card__dl">
        <div><dt>SET</dt><dd>${formatSemesterRating(r.setRatingConfirmed ?? r.setRatingExtracted)}</dd></div>
        <div><dt>SEF</dt><dd>${formatSemesterRating(r.sefRatingConfirmed ?? r.sefRatingExtracted)}</dd></div>
      </dl>
      ${rowIdentity}
      <div class="doc-sem-card__actions">
        <span class="doc-verify-badge" data-record-badge="${r.id}-set" data-v="${r.setVerificationStatus || 'pending'}">SET · ${verifyStatusShort(r.setVerificationStatus)}</span>
        ${verifyControlButton('set', r.id, r.setVerificationStatus === 'verified')}
        <span class="doc-verify-badge" data-record-badge="${r.id}-sef" data-v="${r.sefVerificationStatus || 'pending'}">SEF · ${verifyStatusShort(r.sefVerificationStatus)}</span>
        ${verifyControlButton('sef', r.id, r.sefVerificationStatus === 'verified')}
      </div>
    </article>`;
  };

  const extractionBlock = isSetSefPdf
    ? semesterRecords.length
      ? `<div class="doc-semester-table-wrap">
          <table class="doc-semester-table">
            <thead><tr>
              <th>AY</th><th>Sem</th><th>SET</th><th>SEF</th><th>Verification</th><th>Page</th>
            </tr></thead>
            <tbody>${semesterRecords.map(semesterRowHtml).join('')}</tbody>
          </table>
        </div>
        <div class="doc-semester-cards" aria-label="Semester records">${semesterRecords.map(semesterCardHtml).join('')}</div>
        ${
          (setSefPayload.validationFindings || []).length
            ? `<ul class="doc-findings-list">${(setSefPayload.validationFindings || [])
                .map((f) => `<li><strong>${f.ruleId}</strong> (${f.outcome}): ${f.explanation}</li>`)
                .join('')}</ul>`
            : ''
        }`
      : '<p class="muted">No semester records yet. OCR may still be processing.</p>'
    : '';

  const scoringBlock =
    scoringEst || scoringVer
      ? `<section class="doc-review-section doc-review-scoring" aria-labelledby="docScoreHeading">
          <h4 class="doc-review-section__title" id="docScoreHeading">Criterion A scoring</h4>
          <dl class="doc-score-dl">
            <div>
              <dt>Estimated points</dt>
              <dd>${
                scoringEst?.incomplete
                  ? `<span class="doc-score-incomplete">Incomplete</span> <span class="muted">${scoringEst.incompleteReason || ''}</span>`
                  : `${Number(scoringEst?.criterionAPoints ?? 0).toFixed(2)} <span class="muted">/ 60</span>`
              }</dd>
            </div>
            <div>
              <dt>Reviewer-verified points</dt>
              <dd id="docScoreVerified">${
                !scoringVer
                  ? '—'
                  : scoringVer.incomplete
                    ? `<span class="doc-score-incomplete">Incomplete</span> <span class="muted">${scoringVer.incompleteReason || ''}</span>`
                    : `${Number(scoringVer.criterionAPoints ?? 0).toFixed(2)} <span class="muted">/ 60</span>`
              }</dd>
            </div>
            ${
              semTotal
                ? `<div class="doc-score-dl__verify">
                    <dt>Semester verification</dt>
                    <dd id="docVerifyCounts">SET <strong>${setVerifiedCount}/${semTotal}</strong> · SEF <strong>${sefVerifiedCount}/${semTotal}</strong></dd>
                  </div>`
                : ''
            }
          </dl>
        </section>`
      : '';

  const docTypeLabel = reviewDocumentTypeLabel(docFresh, isSetSefPdf);
  const submitted = formatManilaDateTime(docFresh.submittedAt || docFresh.uploadedAt);
  const ocrRaw = docFresh.ocrStatus || setSefPayload?.document?.ocrStatus;
  const procRaw = docFresh.processingStatus || setSefPayload?.document?.processingStatus;
  const ocrSt = ocrStatusLabel(ocrRaw);
  const procSt = processingStatusLabel(procRaw);
  const ocrTone = ocrRaw === 'completed' ? 'ok' : ocrRaw === 'failed' ? 'danger' : 'warn';
  const procTone = procRaw === 'completed' ? 'ok' : procRaw === 'failed' ? 'danger' : 'warn';

  const bcAchievementBanner = bcReviewViaAchievement
    ? `<p class="doc-review-bc-banner" role="status">This file is supporting evidence for achievement <strong>${bcParentLink.achievement.title || 'Untitled'}</strong>. Review and scoring happen on the achievement — not per file.</p>
       <button type="button" class="btn-primary-sm btn-sm" id="openAchFromDoc">Open achievement review</button>`
    : '';

  const verifiedPointsUi = isSetSefPdf
    ? `<div class="doc-review-field">
        <span class="doc-review-field__label" id="verPtsLabel">Reviewer-verified points (Criterion A)</span>
        <p class="doc-review-readonly" id="docVerPtsDisplay" aria-labelledby="verPtsLabel">${
          scoringVer?.incomplete
            ? `Incomplete — ${scoringVer.incompleteReason || 'Verify all required semester ratings.'}`
            : `${Number(scoringVer?.criterionAPoints ?? 0).toFixed(2)} / 60`
        }</p>
        <p class="doc-review-field__hint">Computed from per-semester SET/SEF verification (server authority).</p>
        <input type="hidden" id="verPts" value="${scoringVer?.incomplete ? '' : Number(scoringVer?.criterionAPoints ?? '')}" />
      </div>`
  : bcReviewViaAchievement
    ? ''
    : `<div class="doc-review-field">
        <label class="doc-review-field__label" for="verPts">Reviewer-verified points</label>
        <span class="doc-review-field__hint">Points you confirmed for this indicator.</span>
        <input type="number" class="doc-review-input" id="verPts" step="0.01" value="${docFresh.verifiedPoints ?? docFresh.estimatedPoints ?? ''}" />
      </div>`;

  const history = docFresh.history || [];
  const historyHtml = history.length
    ? `<ul class="doc-review-history-list">${history.map((h) => `<li><time>${h.at}</time> — ${h.action}${h.note ? `: ${h.note}` : ''}</li>`).join('')}</ul>`
    : '<p class="muted">No prior actions on this document.</p>';

  root.innerHTML = `
    <motion class="doc-review-page" data-review-doc-id="${docFresh.id}">
      <div id="docVerifyLive" class="visually-hidden" aria-live="polite" aria-atomic="true"></div>
      ${pageIntro(SCREEN_INTRO.review)}
      <header class="doc-review-header">
        <button type="button" class="btn-ghost btn-sm" id="backWs">← Back to documents</button>
        <h2 class="doc-review-header__title">${docFresh.fileName}</h2>
      </header>
      <motion class="doc-review-workspace" id="docReviewWorkspace" data-panel="pdf">
        <div class="doc-review-mobile-tabs" role="tablist" aria-label="Review panels">
          <button type="button" role="tab" data-review-tab="pdf" aria-selected="true">Document</button>
          <button type="button" role="tab" data-review-tab="review" aria-selected="false">Review details</button>
        </div>
        <section class="doc-review-pdf-panel" aria-label="Original document">
          <div class="doc-review-panel doc-review-panel--pdf">
            <h3 class="doc-review-panel__title">Original document</h3>
            <div id="docReviewPdfMount" class="doc-review-pdf-mount" data-doc-id="${docFresh.id}"></div>
          </div>
        </section>
        <section class="doc-review-detail-panel" aria-label="Review details">
          <motion class="doc-review-detail-scroll">
            <section class="doc-review-section doc-review-summary">
              <h3 class="doc-review-section__title">Summary</h3>
              <dl class="doc-review-meta">
                <div><dt>Faculty</dt><dd>${facultyDisplay}</dd></div>
                <div><dt>Document</dt><dd>${docTypeLabel}</dd></div>
                <div><dt>Submitted</dt><dd>${submitted}</dd></div>
                <div><dt>Status</dt><dd class="doc-review-meta__status">${statusChip(ocrSt, ocrTone)} ${statusChip(procSt, procTone)}</dd></div>
                ${
                  isSetSefPdf
                    ? `<div><dt>Identity check</dt><dd>${identityInfo.summary}</dd></div>`
                    : ''
                }
              </dl>
              ${identityNote}
              ${docFresh.processingError ? `<p class="doc-review-error">${docFresh.processingError}</p>` : ''}
            </section>
            ${
              isSetSefPdf
                ? `<section class="doc-review-section" aria-labelledby="docExtractHeading">
                    <h4 class="doc-review-section__title" id="docExtractHeading">SET/SEF extraction</h4>
                    ${extractionBlock}
                  </section>`
                : ''
            }
            ${scoringBlock}
            <section class="doc-review-section doc-review-form" aria-labelledby="docReviewHeading">
              <h3 class="doc-review-section__title" id="docReviewHeading">Review decision</h3>
              ${bcAchievementBanner}
              <p class="doc-review-indicator"><span class="muted">Indicator</span> ${meta?.i?.name || docFresh.indicatorId}</p>
              <details class="doc-review-ref">
                <summary>Source reference</summary>
                <p>${meta?.i?.sourceRef || '—'}</p>
              </details>
              ${verifiedPointsUi}
              <div class="doc-review-field">
                <label class="doc-review-field__label" for="rem">Remarks</label>
                <textarea class="doc-review-textarea" id="rem" rows="4" placeholder="Optional for approval; required for changes or rejection.">${docFresh.remarks || ''}</textarea>
              </div>
              <p id="docReviewDecisionBadge" class="doc-review-decision-sync" hidden role="status" aria-live="polite"></p>
              <motion class="doc-review-actions"${bcReviewViaAchievement ? ' hidden' : ''}>
                <button class="btn-primary-sm btn-sm doc-review-actions__primary" data-action="approved" type="button">Approve document</button>
                <button class="btn-ghost btn-sm" data-action="correction_requested" type="button">Request changes</button>
                <button class="btn-ghost btn-sm doc-review-actions__reject" data-action="rejected" type="button">Reject document</button>
              </motion>
              <p id="revOk" class="success-banner doc-review-feedback" hidden role="status">Your review was saved.</p>
              <p id="revErr" class="doc-review-feedback doc-review-feedback--error" role="alert"></p>
              <details class="doc-review-history">
                <summary>Review history (${history.length})</summary>
                ${historyHtml}
              </details>
            </section>
          </motion>
        </section>
      </motion>
    </motion>`;

  root.querySelectorAll('motion').forEach((m) => {
    const d = document.createElement('div');
    d.className = m.className;
    d.innerHTML = m.innerHTML;
    m.replaceWith(d);
  });

  if (root._pdfViewerDestroy) {
    root._pdfViewerDestroy();
    root._pdfViewerDestroy = null;
  }

  const pdfMount = document.getElementById('docReviewPdfMount');
  const pdfViewer =
    pdfMount &&
    mountDocumentPdfViewer(pdfMount, {
      documentId: docFresh.id,
      fetchViewUrl: () => PortalApi.fetchDocumentViewUrl(docFresh.id),
    });
  if (pdfViewer) {
    root._pdfViewerDestroy = () => pdfViewer.destroy();
  }

  const workspace = document.getElementById('docReviewWorkspace');
  workspace?.querySelectorAll('[data-review-tab]').forEach((tab) => {
    tab.addEventListener('click', () => {
      const panel = tab.dataset.reviewTab;
      if (workspace) workspace.dataset.panel = panel;
      workspace?.querySelectorAll('[data-review-tab]').forEach((t) => {
        t.setAttribute('aria-selected', t.dataset.reviewTab === panel ? 'true' : 'false');
      });
    });
  });

  const jumpPdfAndGo = (page) => {
    if (workspace) {
      workspace.dataset.panel = 'pdf';
      workspace.querySelectorAll('[data-review-tab]').forEach((t) => {
        t.setAttribute('aria-selected', t.dataset.reviewTab === 'pdf' ? 'true' : 'false');
      });
    }
    if (pdfViewer && page) pdfViewer.goToPage(page);
    document.getElementById('docReviewPdfMount')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  root.querySelectorAll('[data-goto-page]').forEach((btn) => {
    btn.addEventListener('click', () => jumpPdfAndGo(Number(btn.dataset.gotoPage)));
  });

  document.getElementById('backWs').onclick = () => {
    if (root._pdfViewerDestroy) root._pdfViewerDestroy();
    state.workspaceFacultyId = docFresh.facultyId;
    const crit =
      state.workspaceUi?.criterionId ||
      (isSetSefTeachingDoc(docFresh)
        ? 'kra-I-A'
        : bcParentLink?.achievement
          ? resolveAchievementCriterionId(bcParentLink.achievement)
          : null);
    navigate('workspace', {
      restore: true,
      wsFolder: crit ? WS_FOLDER_CRITERION : state.workspaceUi?.folder || WS_FOLDER_FACULTY,
      criterionId: crit || undefined,
    });
  };

  document.getElementById('openAchFromDoc')?.addEventListener('click', () => {
    if (!bcParentLink?.achievement) return;
    const crit = resolveAchievementCriterionId(bcParentLink.achievement) || 'kra-I-B';
    navigate('achievement-review', {
      facultyId: docFresh.facultyId,
      criterionId: crit,
      achievementId: bcParentLink.achievement.id,
      docId: docFresh.id,
      wsFolder: WS_FOLDER_CRITERION,
    });
  });

  const reviewPage = root.querySelector('.doc-review-page');
  if (reviewPage) {
    reviewPage.dataset.reviewDocId = docFresh.id;
    reviewPage._verifyRowOps = {};
    reviewPage._verifyInflight = 0;
    reviewPage._verifyScoringQueue = null;
    reviewPage._verifyScoringSeq = 0;
  }
  ensureSetSefVerificationDelegation();

  let reviewSaveInflight = false;

  const submitReviewDecision = async (action, triggerBtn) => {
    if (reviewSaveInflight) return;
    const note = document.getElementById('rem')?.value.trim() || '';
    const revErr = document.getElementById('revErr');
    const revOk = document.getElementById('revOk');
    if ((action === 'rejected' || action === 'correction_requested') && !note) {
      if (revErr) revErr.textContent = 'Please write a short reason so the faculty member knows what to fix.';
      return;
    }
    const verPtsEl = document.getElementById('verPts');
    const verifiedRaw = verPtsEl?.value ?? '';
    const history = [
      ...(docFresh.history || []),
      { at: new Date().toISOString().slice(0, 10), by: session.email, action, note },
    ];
    const apiPatch = {
      reviewStatus: action,
      remarks: note,
      verifiedPoints: verifiedRaw !== '' && verifiedRaw != null ? Number(verifiedRaw) : null,
    };

    reviewSaveInflight = true;
  if (revErr) revErr.textContent = '';
    if (revOk) revOk.hidden = true;
    setReviewDecisionSyncing(reviewPage, true, action);

    try {
      const saved = await MockStore.updateDocument(docFresh.id, apiPatch, { clientHistory: history });
      docFresh.reviewStatus = saved?.reviewStatus || action;
      docFresh.remarks = saved?.remarks ?? note;
      docFresh.history = history;
      setReviewDecisionSyncing(reviewPage, false);
      if (revOk) {
        revOk.hidden = false;
        revOk.textContent =
          action === 'approved'
            ? 'Document approved. The faculty member can see this update.'
            : action === 'correction_requested'
              ? 'You requested changes. The faculty member can read your note.'
              : 'Document rejected. The faculty member can read your reason.';
      }
      const histDetails = reviewPage?.querySelector('.doc-review-history');
      if (histDetails) {
        histDetails.querySelector('summary').textContent = `Review history (${history.length})`;
        const list = histDetails.querySelector('ul') || document.createElement('ul');
        list.className = 'doc-review-history-list';
        list.innerHTML = history
          .map((h) => `<li><time>${h.at}</time> — ${h.action}${h.note ? `: ${h.note}` : ''}</li>`)
          .join('');
        if (!histDetails.querySelector('ul')) histDetails.appendChild(list);
      }
      void revalidatePortalInBackground();
    } catch (err) {
      setReviewDecisionSyncing(reviewPage, false);
      showReviewDecisionSaveError(reviewPage, err.message || 'Decision was not saved.', () => {
        void submitReviewDecision(action, triggerBtn);
      });
    } finally {
      reviewSaveInflight = false;
    }
  };

  root.querySelectorAll('[data-action]').forEach((btn) => {
    btn.onclick = () => void submitReviewDecision(btn.dataset.action, btn);
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

window.addEventListener('fl-state-changed', () => portalStateChanged());

function showPortalError(err) {
  const el = document.getElementById('appContent');
  el.innerHTML = `<motion class="card"><h2>Could not load data</h2><p>${err?.message || 'Request failed.'}</p>
    <button type="button" class="btn-primary-sm" id="portalRetry">Retry</button></motion>`;
  document.querySelectorAll('motion').forEach((m) => {
    const d = document.createElement('div');
    d.className = m.className;
    d.innerHTML = m.innerHTML;
    m.replaceWith(d);
  });
  document.getElementById('portalRetry')?.addEventListener('click', () => startPortal());
}

async function startPortal({ skipBootstrap = false } = {}) {
  initSidebarLayout();
  initConfigUi(session, refreshEvaluationSettingsView);
  renderShell();
  applySidebarLayout();
  const el = document.getElementById('appContent');
  if (!skipBootstrap) {
    el.innerHTML = '<p class="muted" style="padding:1rem">Loading…</p>';
  }
  try {
    if (!skipBootstrap) await bootstrapPortal();
    if (location.hash.startsWith('#review/')) {
      state.route = 'review';
      state.params.docId = location.hash.replace('#review/', '');
      renderShell();
      applySidebarLayout();
    }
    renderView();
    void prefetchFullPortalState();
  } catch (err) {
    if (err?.name === 'AuthRedirect') {
      window.location.replace('/login.html');
      return;
    }
    showPortalError(err || portalLoadError());
  }
}

async function initPortalApp() {
  const el = document.getElementById('appContent');
  if (el) el.innerHTML = '<p class="muted" style="padding:1rem">Loading…</p>';
  try {
    await bootstrapPortal();
    session = AuthRepository.getSession();
    if (!session) {
      const me = await AuthRepository.ensureWebPortalSession(['admin', 'reviewer']);
      session = me;
    }
  } catch (e) {
    if (e?.name === 'AuthRedirect') {
      AuthRepository.clearClientSession();
      clearPortalCache();
      clearWorkspaceAchievementsCache();
      window.location.replace('/login.html');
      return;
    }
    el.innerHTML = `<div class="card" style="margin:1rem"><h2>Could not load portal</h2><p>${e.message || 'Network error.'}</p>
      <button type="button" class="btn-primary-sm" id="sessionRetry">Retry</button></div>`;
    document.getElementById('sessionRetry')?.addEventListener('click', () => initPortalApp());
    return;
  }
  if (!session || !['admin', 'reviewer'].includes(session.role)) {
    AuthRepository.clearClientSession();
    clearPortalCache();
    clearWorkspaceAchievementsCache();
    window.location.replace('/login.html');
    return;
  }
  if (session.mustChangePassword) {
    window.location.replace('/change-password.html');
    return;
  }
  await startPortal({ skipBootstrap: true });
}

window.addEventListener('pageshow', (ev) => {
  if (!ev.persisted || !session) return;
  void (async () => {
    try {
      const next = await AuthRepository.ensureWebPortalSession(['admin', 'reviewer']);
      if (!next) {
        clearPortalCache();
        clearWorkspaceAchievementsCache();
        try {
          await AuthRepository.logout();
        } catch {
          AuthRepository.clearClientSession();
        }
        window.location.replace('/login.html');
        return;
      }
      session = next;
      renderShell();
    } catch {
      /* keep current view on transient network errors */
    }
  })();
});

void initPortalApp();
