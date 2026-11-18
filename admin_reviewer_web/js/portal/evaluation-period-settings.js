import { PortalApi } from '../services/portal-api.js';
import { MockStore, bootstrapPortal } from '../repositories/mock-store.js';
import { DEFAULT_INSTITUTION_CONFIG } from '../core/institution-config.js';
import {
  EVALUATION_PERIOD_TIMEZONE,
  computeEvaluationPeriodStatus,
  formatEvaluationDate,
  formatEvaluationDateRange,
  validateEvaluationPeriodDates,
  reviewerAvailabilityDetail,
  reviewerScheduleNote,
  reviewerAccessBadgeClass,
  statusBadgeClass,
} from '../core/evaluation-period-service.js';

const CALENDAR_ICON = `<svg class="fl-ep-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/></svg>`;

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function normalizePeriod(raw) {
  const base = DEFAULT_INSTITUTION_CONFIG().preparationPeriod;
  const p = { ...base, ...(raw || {}) };
  return {
    start: p.start ? String(p.start).slice(0, 10) : '',
    end: p.end ? String(p.end).slice(0, 10) : '',
    reviewerAvailableFrom: p.reviewerAvailableFrom ? String(p.reviewerAvailableFrom).slice(0, 10) : '',
  };
}

function fingerprint(period) {
  const p = normalizePeriod(period);
  return JSON.stringify({
    start: p.start || '',
    end: p.end || '',
    reviewerAvailableFrom: p.reviewerAvailableFrom || '',
  });
}

function summaryHtml(period, { preview = false } = {}) {
  const status = computeEvaluationPeriodStatus(period);
  const rev = reviewerAvailabilityDetail(period);
  const range = formatEvaluationDateRange(period.start, period.end);
  const previewLabel = preview
    ? `<span class="fl-ep-preview-tag">Preview (unsaved)</span>`
    : `<span class="fl-ep-preview-tag fl-ep-preview-tag--saved">Saved schedule</span>`;
  const revMeta = rev.configured
    ? rev.available
      ? `from ${esc(rev.startDateLabel)}`
      : `Opens ${esc(rev.startDateLabel)}`
    : '';

  return `
    <div class="fl-ep-summary" aria-live="polite">
      <div class="fl-ep-summary__head">
        <h4 class="fl-ep-summary__title">Schedule summary</h4>
        ${previewLabel}
      </div>
      <dl class="fl-ep-summary__list">
        <div class="fl-ep-summary__row">
          <dt>Evaluation period</dt>
          <dd>${esc(range)}</dd>
        </div>
        <div class="fl-ep-summary__row">
          <dt>Evaluation status</dt>
          <dd>
            <span class="badge-status ${statusBadgeClass(status)}" aria-label="Evaluation status: ${esc(status)}">${esc(status)}</span>
          </dd>
        </div>
        <div class="fl-ep-summary__row">
          <dt>Reviewer access</dt>
          <dd>
            <span class="badge-status ${reviewerAccessBadgeClass(rev)}" aria-label="Reviewer access: ${esc(rev.statusLabel)}">${esc(rev.statusLabel)}</span>
            ${revMeta ? `<span class="fl-ep-summary__meta">${revMeta}</span>` : ''}
          </dd>
        </div>
      </dl>
      <p class="fl-ep-summary__tz muted">Statuses use the ${esc(EVALUATION_PERIOD_TIMEZONE)} calendar day.</p>
    </div>`;
}

/**
 * Evaluation schedule settings — institution preparationPeriod (active).
 */
export function renderEvaluationPeriodSettings(root, { readOnly = false } = {}) {
  if (!root) return;

  const store = MockStore.load();
  const ic = store.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
  let baseline = normalizePeriod(ic.preparationPeriod);
  let savedFp = fingerprint(baseline);
  let saving = false;

  const note = reviewerScheduleNote(baseline);

  if (readOnly) {
    root.innerHTML = `
      <section class="fl-ep-page" aria-labelledby="epHeading">
        <header class="fl-ep-header">
          <h2 id="epHeading" class="fl-ep-title">Evaluation schedule</h2>
          <p class="fl-ep-lede">Choose the evaluation dates and when reviewers can begin.</p>
        </header>
        <p class="muted fl-ep-readonly-note">These settings are managed by your administrator.</p>
        <div class="card fl-ep-card">
          <div class="fl-ep-card__head">
            ${CALENDAR_ICON}
            <h3 class="fl-ep-card__title">Schedule dates</h3>
          </div>
          <dl class="fl-ep-readonly-dl">
            <div><dt>Evaluation starts</dt><dd>${esc(formatEvaluationDate(baseline.start))}</dd></div>
            <div><dt>Evaluation ends</dt><dd>${esc(formatEvaluationDate(baseline.end))}</dd></div>
            <div><dt>Reviewers can start</dt><dd>${baseline.reviewerAvailableFrom ? esc(formatEvaluationDate(baseline.reviewerAvailableFrom)) : '—'}</dd></div>
          </dl>
          ${note ? `<p class="fl-ep-note" role="note">${esc(note)}</p>` : ''}
          ${summaryHtml(baseline, { preview: false })}
        </div>
      </section>`;
    return;
  }

  root.innerHTML = `
    <section class="fl-ep-page" aria-labelledby="epHeading">
      <header class="fl-ep-header">
        <h2 id="epHeading" class="fl-ep-title">Evaluation schedule</h2>
        <p class="fl-ep-lede">Choose the evaluation dates and when reviewers can begin.</p>
      </header>

      <div class="card fl-ep-card">
        <div class="fl-ep-card__head">
          ${CALENDAR_ICON}
          <h3 class="fl-ep-card__title">Schedule dates</h3>
        </div>

        <form id="evalPeriodForm" class="fl-ep-fields" novalidate>
          <label class="fl-ep-field" for="ppStart">
            <span class="fl-ep-field__label">Evaluation starts</span>
            <input type="date" id="ppStart" name="start" value="${esc(baseline.start)}" required aria-required="true" />
          </label>
          <label class="fl-ep-field" for="ppEnd">
            <span class="fl-ep-field__label">Evaluation ends</span>
            <input type="date" id="ppEnd" name="end" value="${esc(baseline.end)}" required aria-required="true" />
          </label>
          <label class="fl-ep-field" for="ppRev">
            <span class="fl-ep-field__label">Reviewers can start</span>
            <input type="date" id="ppRev" name="reviewerAvailableFrom" value="${esc(baseline.reviewerAvailableFrom)}" />
            <span class="fl-ep-field__hint">The date reviewers may begin checking submitted evidence.</span>
          </label>
        </form>

        <p id="epFieldError" class="fl-ep-field-error" role="alert" hidden></p>
        <p id="epRevNote" class="fl-ep-note" role="note" ${note ? '' : 'hidden'}>${note ? esc(note) : ''}</p>

        <div id="epSummary">${summaryHtml(baseline, { preview: false })}</div>

        <footer class="fl-ep-actions" role="region" aria-label="Save evaluation schedule">
          <div class="fl-ep-actions__row">
            <span id="epDirty" class="fl-ep-status-chip" data-state="saved">All changes saved</span>
            <div class="fl-ep-actions__buttons">
              <button type="button" class="cfg-btn-secondary btn-sm" id="epCancel" disabled>Cancel changes</button>
              <button type="button" class="btn-primary-sm btn-sm" id="epSave" disabled>Save changes</button>
            </div>
          </div>
          <p id="evalPeriodMsg" class="fl-ep-msg" role="status" aria-live="polite"></p>
        </footer>
      </div>
    </section>`;

  const msg = root.querySelector('#evalPeriodMsg');
  const dirtyChip = root.querySelector('#epDirty');
  const saveBtn = root.querySelector('#epSave');
  const cancelBtn = root.querySelector('#epCancel');
  const fieldError = root.querySelector('#epFieldError');
  const revNoteEl = root.querySelector('#epRevNote');
  const summaryHost = root.querySelector('#epSummary');

  const readDraft = () => ({
    start: root.querySelector('#ppStart')?.value || '',
    end: root.querySelector('#ppEnd')?.value || '',
    reviewerAvailableFrom: root.querySelector('#ppRev')?.value || '',
  });

  const updateUi = () => {
    const draft = readDraft();
    const dirty = fingerprint(draft) !== savedFp;
    const validationError = validateEvaluationPeriodDates(draft);
    const invalid = Boolean(validationError);

    if (fieldError) {
      if (invalid && (draft.start || draft.end)) {
        fieldError.hidden = false;
        fieldError.textContent = validationError;
      } else {
        fieldError.hidden = true;
        fieldError.textContent = '';
      }
    }

    const noteText = reviewerScheduleNote(draft);
    if (revNoteEl) {
      if (noteText) {
        revNoteEl.hidden = false;
        revNoteEl.textContent = noteText;
      } else {
        revNoteEl.hidden = true;
        revNoteEl.textContent = '';
      }
    }

    if (summaryHost) {
      summaryHost.innerHTML = summaryHtml(draft, { preview: dirty });
    }

    if (dirtyChip) {
      dirtyChip.textContent = dirty ? 'Unsaved changes' : 'All changes saved';
      dirtyChip.dataset.state = dirty ? 'dirty' : 'saved';
    }
    if (cancelBtn) cancelBtn.disabled = !dirty || saving;
    if (saveBtn) saveBtn.disabled = !dirty || invalid || saving;
    return { draft, dirty, invalid, validationError };
  };

  const onChange = () => {
    updateUi();
    if (msg?.dataset.kind === 'ok') {
      msg.textContent = '';
      delete msg.dataset.kind;
      msg.classList.remove('fl-ep-msg--err');
    }
  };

  root.querySelectorAll('#ppStart, #ppEnd, #ppRev').forEach((el) => {
    el.addEventListener('input', onChange);
    el.addEventListener('change', onChange);
  });

  cancelBtn?.addEventListener('click', () => {
    if (cancelBtn.disabled) return;
    renderEvaluationPeriodSettings(root, { readOnly: false });
  });

  saveBtn?.addEventListener('click', async () => {
    if (saving || saveBtn.disabled) return;
    const { draft, validationError } = updateUi();
    if (validationError) {
      msg.textContent = validationError;
      msg.dataset.kind = 'err';
      msg.classList.add('fl-ep-msg--err');
      return;
    }

    msg.classList.remove('fl-ep-msg--err');
    saving = true;
    updateUi();
    saveBtn.textContent = 'Saving…';
    msg.textContent = 'Saving changes…';

    try {
      const s = MockStore.load();
      const institutionConfig = {
        ...(s.institutionConfig || DEFAULT_INSTITUTION_CONFIG()),
        preparationPeriod: {
          start: draft.start,
          end: draft.end,
          reviewerAvailableFrom: draft.reviewerAvailableFrom || '',
        },
      };
      await PortalApi.saveInstitution(institutionConfig);
      s.institutionConfig = institutionConfig;
      MockStore.save(s);
      await bootstrapPortal();
      baseline = normalizePeriod(institutionConfig.preparationPeriod);
      savedFp = fingerprint(baseline);
      msg.textContent = `Schedule saved. Evaluation period is ${computeEvaluationPeriodStatus(baseline)} (${formatEvaluationDateRange(baseline.start, baseline.end)}).`;
      msg.dataset.kind = 'ok';
    } catch (ex) {
      // Keep entered dates; do not reset the form.
      msg.textContent = ex.message || 'Could not save evaluation schedule. Your dates were kept — try again.';
      msg.dataset.kind = 'err';
      msg.classList.add('fl-ep-msg--err');
    } finally {
      saving = false;
      saveBtn.textContent = 'Save changes';
      updateUi();
    }
  });

  updateUi();
}
