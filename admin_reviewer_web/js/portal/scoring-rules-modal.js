import { MockStore, prefetchFullPortalState } from '../repositories/mock-store.js';
import { PortalApi } from '../services/portal-api.js';
import { openCenteredModal } from './modal-access.js';
import { showAppToast } from './account-modals.js';

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

function escAttr(s) {
  return String(s).replace(/"/g, '&quot;');
}

function versionLabel(v) {
  const cat = v.catalog || {};
  const ver = cat.version || v.id;
  const published = v.publishedAt || v.createdAt || '';
  return `${ver} (${v.id})${published ? ` · ${published}` : ''}`;
}

function policySummary(catalog) {
  if (!catalog?.kras) return '—';
  for (const kra of catalog.kras) {
    if (kra.id !== 'kra-I') continue;
    for (const crit of kra.criteria || []) {
      if (crit.id !== 'kra-I-A') continue;
      for (const ind of crit.indicators || []) {
        if (ind.subType === 'SET' || ind.id === 'kra-I-A-set') {
          const p = (ind.calculation || {}).policy;
          return p === 'average_available_max_six'
            ? 'Flexible: average of available ratings (≤6 semesters)'
            : 'Legacy: six-semester fixed average (per pinned catalog)';
        }
      }
    }
  }
  return 'Legacy (no explicit policy on catalog)';
}

export function openFacultyScoringRulesModal(facultyId, { onApplied } = {}) {
  const store = MockStore.load();
  const faculty = store.faculty.find((f) => f.id === facultyId);
  if (!faculty) return;

  const meta = store.assessmentConfig || { versions: [], activePublishedId: null };
  const published = (meta.versions || []).filter((v) => v.status === 'published');
  const assessment = store.assessments?.[facultyId] || {};
  const currentId = assessment.configVersionId || '';
  const activeId = meta.activePublishedId || '';
  const currentRec = published.find((v) => v.id === currentId);
  const activeRec = published.find((v) => v.id === activeId);

  const history = (assessment.configVersionHistory || [])
    .slice(-5)
    .reverse()
    .map(
      (h) =>
        `<li><span class="muted">${esc(h.at || '')}</span> — ${esc(h.from || '—')} → <strong>${esc(h.to || '')}</strong> by ${esc(h.actor || '')}${h.reason ? `: ${esc(h.reason)}` : ''}</li>`
    )
    .join('');

  const options = published
    .map((v) => {
      const selected = v.id === currentId ? 'selected' : v.id === activeId && !currentId ? 'selected' : '';
      return `<option value="${escAttr(v.id)}" ${selected}>${esc(versionLabel(v))}</option>`;
    })
    .join('');

  const bodyHtml = `
    <form id="facultyRulesForm" class="fl-account-form">
      <p><strong>${esc(faculty.firstName)} ${esc(faculty.lastName)}</strong></p>
      <section>
        <h3>Current scoring rules version</h3>
        <p>${currentId ? `<code>${esc(currentId)}</code>` : '<span class="muted">Not pinned yet — pins on first evidence submission.</span>'}</p>
        <p class="muted">${esc(policySummary(currentRec?.catalog))}</p>
      </section>
      <section>
        <h3>Active published version (new faculty default)</h3>
        <p><code>${esc(activeId || '—')}</code></p>
        <p class="muted">${esc(policySummary(activeRec?.catalog))}</p>
      </section>
      <section>
        <h3>Reassign to published version</h3>
        <p class="muted">This is audited. Pinned assessments are not upgraded when you publish — use this action to move a faculty member to a new rules version (e.g. flexible Criterion A).</p>
        <label for="rulesTargetVersion">Target version</label>
        <select id="rulesTargetVersion" name="configVersionId" required>
          <option value="">Select published version…</option>
          ${options}
        </select>
        <label for="rulesReason">Reason (optional)</label>
        <textarea id="rulesReason" name="reason" rows="2" placeholder="e.g. Enable flexible Criterion A for 2026 cycle"></textarea>
        <label class="fl-checkbox-row">
          <input type="checkbox" id="rulesConfirm" required />
          I confirm this faculty assessment should use the selected rules version for scoring.
        </label>
      </section>
      ${history ? `<section><h3>Recent reassignments</h3><ul class="muted">${history}</ul></section>` : ''}
      <p class="fl-account-field-error" data-error-for="_form" role="alert"></p>
    </form>`;

  const modal = openCenteredModal({
    title: 'Scoring rules version',
    lede: 'View pinned configuration and reassign with confirmation.',
    size: 'account',
    bodyHtml,
    footerHtml: `
      <button type="button" class="cfg-btn-secondary" data-fl-modal-cancel>Cancel</button>
      <button type="submit" form="facultyRulesForm" class="cfg-btn-primary" id="rulesSubmitBtn">Apply reassignment</button>`,
  });

  const form = modal.querySelector('#facultyRulesForm');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = form.querySelector('[data-error-for="_form"]');
    const versionId = form.querySelector('#rulesTargetVersion').value.trim();
    const reason = form.querySelector('#rulesReason').value.trim();
    if (!versionId) {
      errEl.textContent = 'Select a target published version.';
      return;
    }
    if (versionId === currentId) {
      errEl.textContent = 'Faculty is already on this rules version.';
      return;
    }
    const target = published.find((v) => v.id === versionId);
    const targetLabel = target ? versionLabel(target) : versionId;
    if (
      !window.confirm(
        `Reassign ${faculty.firstName} ${faculty.lastName} from ${currentId || '(unpinned)'} to ${targetLabel}? This affects Criterion A calculation policy and is recorded in the audit trail.`
      )
    ) {
      return;
    }
    errEl.textContent = '';
    const btn = modal.querySelector('#rulesSubmitBtn');
    btn.disabled = true;
    try {
      await PortalApi.reassignFacultyConfigVersion(faculty.id, { configVersionId: versionId, reason });
      await prefetchFullPortalState({ force: true });
      showAppToast('Scoring rules version updated.');
      modal.close();
      onApplied?.();
    } catch (ex) {
      errEl.textContent = ex.message || 'Request failed.';
      btn.disabled = false;
    }
  });
}
