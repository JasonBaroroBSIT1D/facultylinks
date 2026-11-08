import { MockStore } from '../repositories/mock-store.js';
import { PortalApi } from '../services/portal-api.js';
import { DEFAULT_INSTITUTION_CONFIG } from '../core/institution-config.js';
import { navIcon } from '../core/icons.js';
import { openCenteredModal } from './modal-access.js';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

function escAttr(s) {
  return String(s).replace(/"/g, '&quot;');
}

function showAppToast(text, isErr = false) {
  let el = document.getElementById('appToast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'appToast';
    el.className = 'cfg-toast';
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.classList.toggle('cfg-toast--err', isErr);
  el.hidden = false;
  clearTimeout(el._t);
  el._t = setTimeout(() => {
    el.hidden = true;
  }, 4200);
}

function allEmails(store, exclude = {}) {
  const emails = [];
  store.faculty.forEach((f) => {
    if (f.id !== exclude.facultyId && f.email) emails.push(f.email.toLowerCase());
  });
  store.reviewers.forEach((r) => {
    if (r.id !== exclude.reviewerId && r.email) emails.push(r.email.toLowerCase());
  });
  (store.admins || []).forEach((a) => {
    if (a.email) emails.push(a.email.toLowerCase());
  });
  return emails;
}

function syncReviewerAssignments(state, facultyId, reviewerId) {
  state.reviewers.forEach((r) => {
    const ids = new Set(r.assignedFacultyIds || []);
    if (r.id === reviewerId && facultyId) ids.add(facultyId);
    else ids.delete(facultyId);
    r.assignedFacultyIds = [...ids];
  });
}

export function countFacultyForReviewer(store, reviewerId) {
  return store.faculty.filter((f) => f.reviewerId === reviewerId).length;
}

function activeReviewers(store) {
  return store.reviewers.filter((r) => r.status === 'active');
}

function rankOptions(store) {
  const ic = store.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
  return ic.rankOptions || [];
}

function attachDirtyTracking(dialog, onDirty) {
  let dirty = false;
  const mark = () => {
    if (!dirty) {
      dirty = true;
      onDirty?.(true);
    }
  };
  dialog.querySelectorAll('input, select, textarea').forEach((el) => {
    el.addEventListener('input', mark);
    el.addEventListener('change', mark);
  });
  return {
    isDirty: () => dirty,
    confirmClose: () => !dirty || window.confirm('Discard your changes?'),
  };
}

function setFieldError(form, name, message) {
  const el = form.querySelector(`[data-error-for="${name}"]`);
  if (el) el.textContent = message || '';
  const inp = form.querySelector(`[name="${name}"]`);
  if (inp) inp.setAttribute('aria-invalid', message ? 'true' : 'false');
}

function clearFormErrors(form) {
  form.querySelectorAll('[data-error-for]').forEach((el) => (el.textContent = ''));
}

export function openFacultyForm(facultyId, { opener, onSaved }) {
  const store = MockStore.load();
  const isEdit = !!facultyId;
  const existing = isEdit ? store.faculty.find((f) => f.id === facultyId) : null;
  const f = existing || {
    firstName: '',
    lastName: '',
    email: '',
    rank: rankOptions(store)[0] || '',
    department: '',
    reviewerId: '',
    status: 'active',
  };

  const activeRevs = activeReviewers(store);
  const reviewerOptions = activeRevs.length
    ? activeRevs
        .map(
          (r) =>
            `<option value="${escAttr(r.id)}" ${r.id === f.reviewerId ? 'selected' : ''}>${esc(r.firstName)} ${esc(r.lastName)}</option>`
        )
        .join('')
    : '';

  const reviewerBlock = activeRevs.length
    ? `<select name="reviewerId" id="facReviewerId" aria-describedby="facReviewerHint">
        <option value="" ${!f.reviewerId ? 'selected' : ''}>Select a reviewer</option>
        <option value="__later__" ${f.reviewerId === '__later__' ? 'selected' : ''}>Assign later</option>
        ${reviewerOptions}
      </select>
      <p id="facReviewerHint" class="fl-account-empty-hint">Optional — you can assign a reviewer anytime.</p>`
    : `<p class="fl-account-empty-hint">No active reviewers yet. Add a reviewer first, or save and assign later.</p>
       <input type="hidden" name="reviewerId" value="__later__"/>`;

  const ranks = rankOptions(store);
  const rankOpts = ranks.map((r) => `<option value="${escAttr(r)}" ${r === f.rank ? 'selected' : ''}>${esc(r)}</option>`).join('');

  const bodyHtml = `
    <p class="fl-account-demo-note">Demo mode: changes are saved on this browser.</p>
    <form id="facultyAccountForm" class="fl-account-form" novalidate>
      <section aria-labelledby="facSecPersonal">
        <h3 id="facSecPersonal">Personal details</h3>
        <div class="fl-account-grid">
          <div class="fl-account-field">
            <label for="facFirst">First name</label>
            <input id="facFirst" name="firstName" required value="${escAttr(f.firstName)}" data-autofocus autocomplete="given-name"/>
            <p class="fl-account-field-error" data-error-for="firstName" role="alert"></p>
          </div>
          <div class="fl-account-field">
            <label for="facLast">Last name</label>
            <input id="facLast" name="lastName" required value="${escAttr(f.lastName)}" autocomplete="family-name"/>
            <p class="fl-account-field-error" data-error-for="lastName" role="alert"></p>
          </div>
          <div class="fl-account-field fl-account-field--full">
            <label for="facEmail">Email address</label>
            <input id="facEmail" name="email" type="email" required value="${escAttr(f.email)}" autocomplete="email"/>
            <p class="fl-account-field-error" data-error-for="email" role="alert"></p>
          </div>
        </div>
      </section>
      ${
        isEdit
          ? ''
          : `<section aria-labelledby="facSecAuth">
        <h3 id="facSecAuth">Sign-in</h3>
        <div class="fl-account-grid fl-account-grid--single">
          <div class="fl-account-field fl-account-field--full">
            <label for="facPassword">Initial password</label>
            <input id="facPassword" name="password" type="password" minlength="8" required autocomplete="new-password"/>
            <p class="muted" style="font-size:0.85rem;margin:0.35rem 0 0">At least 8 characters for the mobile app.</p>
          </div>
        </div>
      </section>`
      }
      <section aria-labelledby="facSecAcademic">
        <h3 id="facSecAcademic">Academic details</h3>
        <div class="fl-account-grid">
          <div class="fl-account-field">
            <label for="facRank">Current rank</label>
            <select id="facRank" name="rank" required>${rankOpts}</select>
            <p class="fl-account-field-error" data-error-for="rank" role="alert"></p>
          </div>
          <div class="fl-account-field">
            <label for="facDept">Department</label>
            <input id="facDept" name="department" value="${escAttr(f.department || '')}" autocomplete="organization"/>
            <p class="fl-account-field-error" data-error-for="department" role="alert"></p>
          </div>
        </div>
      </section>
      <section aria-labelledby="facSecRev">
        <h3 id="facSecRev">Reviewer assignment</h3>
        <div class="fl-account-grid fl-account-grid--single">
          <div class="fl-account-field fl-account-field--full">
            <label for="facReviewerId">Assigned reviewer</label>
            ${reviewerBlock}
            <p class="fl-account-field-error" data-error-for="reviewerId" role="alert"></p>
          </div>
        </div>
      </section>
      <p class="fl-account-field-error" data-error-for="_form" role="alert"></p>
    </form>`;

  const modal = openCenteredModal({
    title: isEdit ? 'Edit Faculty' : 'Add Faculty Member',
    lede: isEdit ? 'Update this faculty member’s profile and reviewer assignment.' : 'Create a faculty record for the local demonstration.',
    size: 'account',
    iconHtml: navIcon.faculty,
    bodyHtml,
    footerHtml: `
      <button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Cancel</button>
      <button type="submit" form="facultyAccountForm" class="cfg-btn-primary" id="facultySubmitBtn">${isEdit ? 'Save Changes' : 'Add Faculty Member'}</button>`,
    opener,
    onBeforeClose: () => {
      const track = modal._dirty;
      return track ? track.confirmClose() : true;
    },
  });
  if (!modal) return;

  const track = attachDirtyTracking(modal.dialog, () => {});
  modal._dirty = track;

  const form = modal.dialog.querySelector('#facultyAccountForm');
  const submitBtn = modal.dialog.querySelector('#facultySubmitBtn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormErrors(form);
    const fd = new FormData(form);
    const firstName = fd.get('firstName')?.toString().trim() || '';
    const lastName = fd.get('lastName')?.toString().trim() || '';
    const email = fd.get('email')?.toString().trim().toLowerCase() || '';
    const rank = fd.get('rank')?.toString().trim() || '';
    const department = fd.get('department')?.toString().trim() || '';
    let reviewerId = fd.get('reviewerId')?.toString() || '';
    if (reviewerId === '__later__' || reviewerId === '') reviewerId = '';

    let valid = true;
    if (!firstName) {
      setFieldError(form, 'firstName', 'First name is required.');
      valid = false;
    }
    if (!lastName) {
      setFieldError(form, 'lastName', 'Last name is required.');
      valid = false;
    }
    if (!email || !EMAIL_RE.test(email)) {
      setFieldError(form, 'email', 'Enter a valid email address.');
      valid = false;
    } else if (allEmails(MockStore.load(), { facultyId: existing?.id }).includes(email)) {
      setFieldError(form, 'email', 'This email is already used by another account.');
      valid = false;
    }
    if (!rank) {
      setFieldError(form, 'rank', 'Select a rank.');
      valid = false;
    }
    if (!valid) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving…';

    try {
      const record = {
        id: existing?.id,
        firstName,
        lastName,
        email,
        rank,
        department,
        reviewerId: reviewerId || null,
        status: existing?.status || 'active',
        employeeId: existing?.employeeId || '',
        phone: existing?.phone || '',
        password: fd.get('password')?.toString() || '',
      };
      await MockStore.upsertFaculty(record);
      modal.close();
      showAppToast(`${firstName} ${lastName} saved.`);
      onSaved?.();
    } catch (err) {
      setFieldError(form, '_form', err.message || 'Could not save.');
      submitBtn.disabled = false;
      submitBtn.textContent = isEdit ? 'Save Changes' : 'Add Faculty Member';
    }
  });
}

export function openReviewerForm(reviewerId, { opener, onSaved }) {
  const store = MockStore.load();
  const isEdit = !!reviewerId;
  const existing = isEdit ? store.reviewers.find((r) => r.id === reviewerId) : null;
  const r = existing || {
    firstName: '',
    lastName: '',
    email: '',
    department: '',
    status: 'active',
    assignedFacultyIds: [],
  };

  const bodyHtml = `
    <p class="fl-account-demo-note">Demo mode: changes are saved on this browser.</p>
    <form id="reviewerAccountForm" class="fl-account-form" novalidate>
      <section aria-labelledby="revSecPersonal">
        <h3 id="revSecPersonal">Personal details</h3>
        <div class="fl-account-grid">
          <div class="fl-account-field">
            <label for="revFirst">First name</label>
            <input id="revFirst" name="firstName" required value="${escAttr(r.firstName)}" data-autofocus autocomplete="given-name"/>
            <p class="fl-account-field-error" data-error-for="firstName" role="alert"></p>
          </div>
          <div class="fl-account-field">
            <label for="revLast">Last name</label>
            <input id="revLast" name="lastName" required value="${escAttr(r.lastName)}" autocomplete="family-name"/>
            <p class="fl-account-field-error" data-error-for="lastName" role="alert"></p>
          </div>
          <div class="fl-account-field fl-account-field--full">
            <label for="revEmail">Email address</label>
            <input id="revEmail" name="email" type="email" required value="${escAttr(r.email)}" autocomplete="email"/>
            <p class="fl-account-field-error" data-error-for="email" role="alert"></p>
          </div>
        </div>
      </section>
      <section aria-labelledby="revSecDetails">
        <h3 id="revSecDetails">Reviewer details</h3>
        <div class="fl-account-grid">
          <div class="fl-account-field">
            <label for="revDept">Department / office <span class="muted" style="font-weight:400">(optional)</span></label>
            <input id="revDept" name="department" value="${escAttr(r.department || '')}"/>
          </div>
          <div class="fl-account-field">
            <label for="revStatus">Status</label>
            <select id="revStatus" name="status">
              <option value="active" ${r.status === 'active' ? 'selected' : ''}>Active</option>
              <option value="inactive" ${r.status === 'inactive' ? 'selected' : ''}>Inactive</option>
            </select>
          </div>
        </div>
      </section>
      <p class="fl-account-field-error" data-error-for="_form" role="alert"></p>
    </form>`;

  const modal = openCenteredModal({
    title: isEdit ? 'Edit Reviewer' : 'Add Reviewer',
    lede: isEdit ? 'Update reviewer contact details and status.' : 'Create a reviewer who can check faculty documents in the demo.',
    size: 'account',
    iconHtml: navIcon.reviewers,
    bodyHtml,
    footerHtml: `
      <button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Cancel</button>
      <button type="submit" form="reviewerAccountForm" class="cfg-btn-primary" id="reviewerSubmitBtn">${isEdit ? 'Save Changes' : 'Add Reviewer'}</button>`,
    opener,
    onBeforeClose: () => {
      const track = modal._dirty;
      return track ? track.confirmClose() : true;
    },
  });
  if (!modal) return;

  modal._dirty = attachDirtyTracking(modal.dialog, () => {});

  const form = modal.dialog.querySelector('#reviewerAccountForm');
  const submitBtn = modal.dialog.querySelector('#reviewerSubmitBtn');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormErrors(form);
    const fd = new FormData(form);
    const firstName = fd.get('firstName')?.toString().trim() || '';
    const lastName = fd.get('lastName')?.toString().trim() || '';
    const email = fd.get('email')?.toString().trim().toLowerCase() || '';
    const department = fd.get('department')?.toString().trim() || '';
    const status = fd.get('status')?.toString() || 'active';

    let valid = true;
    if (!firstName) {
      setFieldError(form, 'firstName', 'First name is required.');
      valid = false;
    }
    if (!lastName) {
      setFieldError(form, 'lastName', 'Last name is required.');
      valid = false;
    }
    if (!email || !EMAIL_RE.test(email)) {
      setFieldError(form, 'email', 'Enter a valid email address.');
      valid = false;
    } else if (allEmails(MockStore.load(), { reviewerId: existing?.id }).includes(email)) {
      setFieldError(form, 'email', 'This email is already used by another account.');
      valid = false;
    }
    if (!valid) return;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving…';

    try {
      const record = {
        id: existing?.id,
        firstName,
        lastName,
        email,
        department,
        status,
        employeeId: existing?.employeeId || '',
        password: fd.get('password')?.toString() || '',
      };
      await MockStore.upsertReviewer(record);
      modal.close();
      showAppToast(`${firstName} ${lastName} saved.`);
      onSaved?.();
    } catch (err) {
      setFieldError(form, '_form', err.message || 'Could not save.');
      submitBtn.disabled = false;
      submitBtn.textContent = isEdit ? 'Save Changes' : 'Add Reviewer';
    }
  });
}

export function openReviewerAssignModal(reviewerId, { opener, onSaved }) {
  const store = MockStore.load();
  const rev = store.reviewers.find((r) => r.id === reviewerId);
  if (!rev) return;

  const rows = store.faculty
    .map(
      (f) => `<label class="fl-publish-preview-toggle" style="width:100%;justify-content:flex-start">
      <input type="checkbox" data-fid="${escAttr(f.id)}" ${f.reviewerId === rev.id ? 'checked' : ''}/>
      ${esc(f.firstName)} ${esc(f.lastName)} <span class="muted">(${esc(f.email)})</span>
    </label>`
    )
    .join('');

  const modal = openCenteredModal({
    title: `Assignments — ${rev.firstName} ${rev.lastName}`,
    lede: 'Choose which faculty members this reviewer supports.',
    size: 'account',
    iconHtml: navIcon.reviewers,
    bodyHtml: `<div class="fl-account-form">${rows || '<p class="fl-empty-state">No faculty records yet.</p>'}</div>`,
    footerHtml: `
      <button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Cancel</button>
      <button type="button" class="cfg-btn-primary" id="saveAssignBtn">Save assignments</button>`,
    opener,
  });
  if (!modal) return;

  modal.dialog.querySelector('#saveAssignBtn')?.addEventListener('click', async () => {
    const ids = [...modal.dialog.querySelectorAll('[data-fid]')].filter((c) => c.checked).map((c) => c.dataset.fid);
    try {
      await PortalApi.setAssignments(reviewerId, ids);
      await MockStore.refresh();
      modal.close();
      showAppToast('Reviewer assignments updated.');
      onSaved?.();
    } catch (err) {
      showAppToast(err.message || 'Could not save assignments.', { error: true });
    }
  });
}

export { showAppToast };
