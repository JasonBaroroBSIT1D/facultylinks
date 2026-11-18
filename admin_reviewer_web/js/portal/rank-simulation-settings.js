import { PortalApi } from '../services/portal-api.js';
import { MockStore } from '../repositories/mock-store.js';
import { DEFAULT_INSTITUTION_CONFIG } from '../core/institution-config.js';
import {
  DEFAULT_RANK_SIMULATION,
  DECIMAL_POLICY_OPTIONS,
  KRA_WEIGHT_COLUMN_IDS,
  KRA_WEIGHT_COLUMN_LABELS,
  RANK_CATEGORY_IDS,
  RANK_CATEGORY_LABELS,
  decimalToPercentDisplay,
  findUncoveredScoreRanges,
  formatWeightRowTotal,
  parsePercentField,
  validateRankSimulation,
} from '../core/rank-simulation-config.js';

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function clone(v) {
  return JSON.parse(JSON.stringify(v));
}

function round4(n) {
  const x = Number(n);
  if (!Number.isFinite(x)) return null;
  return Math.round(x * 10000) / 10000;
}

function mergeRankSim(ic) {
  const base = DEFAULT_RANK_SIMULATION();
  const rs = { ...base, ...(ic?.rankSimulation || {}) };
  rs.weightMatrixByCategory = { ...base.weightMatrixByCategory, ...(rs.weightMatrixByCategory || {}) };
  for (const cat of RANK_CATEGORY_IDS) {
    const merged = {
      ...base.weightMatrixByCategory[cat],
      ...(rs.weightMatrixByCategory[cat] || {}),
    };
    rs.weightMatrixByCategory[cat] = Object.fromEntries(
      KRA_WEIGHT_COLUMN_IDS.map((kid) => [kid, round4(merged[kid]) ?? 0])
    );
  }
  if (!Array.isArray(rs.scoreBrackets) || !rs.scoreBrackets.length) {
    rs.scoreBrackets = clone(base.scoreBrackets);
  } else {
    rs.scoreBrackets = rs.scoreBrackets.map((b) => ({
      minInclusive: Number(b.minInclusive),
      maxInclusive: Number(b.maxInclusive),
      subRankIncrements: Number(b.subRankIncrements),
    }));
  }
  return rs;
}

function snapshotState(ic) {
  return {
    rankSimulation: clone(mergeRankSim(ic)),
    rankOptions: clone(ic?.rankOptions || DEFAULT_INSTITUTION_CONFIG().rankOptions || []),
  };
}

function policyMeta(value) {
  return DECIMAL_POLICY_OPTIONS.find((o) => o.value === value) || DECIMAL_POLICY_OPTIONS[0];
}

function totalBadgeHtml(cat, row) {
  const total = formatWeightRowTotal(
    KRA_WEIGHT_COLUMN_IDS.reduce((a, kid) => a + Number(row?.[kid] || 0), 0)
  );
  return `<span class="fl-rs-total-badge ${total.ok ? 'ok' : 'bad'}" data-rs-total="${esc(cat)}" aria-live="polite">${esc(total.text)}</span>`;
}

function weightRowHtml(cat, row, readOnly) {
  const cells = KRA_WEIGHT_COLUMN_IDS.map((kid) => {
    const pct = decimalToPercentDisplay(row?.[kid]);
    const id = `rs-w-${cat}-${kid}`;
    return `<td class="fl-rs-weight-cell">
      <div class="fl-rs-pct-control">
        <label class="fl-rs-sr-only" for="${esc(id)}">${esc(RANK_CATEGORY_LABELS[cat])} · ${esc(KRA_WEIGHT_COLUMN_LABELS[kid])} percent</label>
        <input type="number" inputmode="decimal" min="0" max="100" step="0.1"
          id="${esc(id)}" data-rs-weight="${esc(cat)}:${esc(kid)}"
          value="${esc(pct)}" ${readOnly ? 'disabled' : ''} />
        <span class="fl-rs-pct-suffix" aria-hidden="true">%</span>
      </div>
      <p class="fl-rs-field-error" data-rs-weight-err="${esc(cat)}:${esc(kid)}" hidden></p>
    </td>`;
  }).join('');
  return `<tr class="fl-rs-weight-row" data-rs-cat="${esc(cat)}">
    <th scope="row">${esc(RANK_CATEGORY_LABELS[cat])}</th>
    ${cells}
    <td class="fl-rs-total-cell">${totalBadgeHtml(cat, row)}</td>
  </tr>`;
}

function weightCardHtml(cat, row, readOnly) {
  const fields = KRA_WEIGHT_COLUMN_IDS.map((kid) => {
    const pct = decimalToPercentDisplay(row?.[kid]);
    const id = `rs-w-m-${cat}-${kid}`;
    return `<label class="fl-rs-pct-field" for="${esc(id)}">
      <span class="fl-rs-pct-field__label">${esc(KRA_WEIGHT_COLUMN_LABELS[kid])}</span>
      <span class="fl-rs-pct-control">
        <input type="number" inputmode="decimal" min="0" max="100" step="0.1"
          id="${esc(id)}" data-rs-weight="${esc(cat)}:${esc(kid)}"
          value="${esc(pct)}" ${readOnly ? 'disabled' : ''} />
        <span class="fl-rs-pct-suffix" aria-hidden="true">%</span>
      </span>
      <p class="fl-rs-field-error" data-rs-weight-err="${esc(cat)}:${esc(kid)}" hidden></p>
    </label>`;
  }).join('');
  return `<article class="fl-rs-weight-card" data-rs-cat="${esc(cat)}">
    <div class="fl-rs-weight-card__head">
      <h4 class="fl-rs-weight-card__title">${esc(RANK_CATEGORY_LABELS[cat])}</h4>
      ${totalBadgeHtml(cat, row)}
    </div>
    <div class="fl-rs-weight-card__fields">${fields}</div>
  </article>`;
}

function bracketRowHtml(b, i, readOnly) {
  return `<tr data-rs-bracket-row="${i}">
    <td>
      <label class="fl-rs-field" for="rs-b-${i}-min">
        <span class="fl-rs-mobile-only">From</span>
        <input type="number" id="rs-b-${i}-min" data-rs-bracket="${i}:min" value="${esc(b.minInclusive)}" aria-label="Score range ${i + 1} from" ${readOnly ? 'disabled' : ''} />
      </label>
      <p class="fl-rs-field-error" data-rs-bracket-err="${i}:min" hidden></p>
    </td>
    <td>
      <label class="fl-rs-field" for="rs-b-${i}-max">
        <span class="fl-rs-mobile-only">To</span>
        <input type="number" id="rs-b-${i}-max" data-rs-bracket="${i}:max" value="${esc(b.maxInclusive)}" aria-label="Score range ${i + 1} to" ${readOnly ? 'disabled' : ''} />
      </label>
      <p class="fl-rs-field-error" data-rs-bracket-err="${i}:max" hidden></p>
    </td>
    <td>
      <label class="fl-rs-field" for="rs-b-${i}-inc">
        <span class="fl-rs-mobile-only">Rank steps gained</span>
        <input type="number" id="rs-b-${i}-inc" data-rs-bracket="${i}:inc" step="1" min="0" value="${esc(b.subRankIncrements)}" aria-label="Score range ${i + 1} rank steps gained" ${readOnly ? 'disabled' : ''} />
      </label>
      <p class="fl-rs-field-error" data-rs-bracket-err="${i}:inc" hidden></p>
    </td>
  </tr>`;
}

function preferredWeightInput(root, cat, kid) {
  const inputs = [...root.querySelectorAll(`[data-rs-weight="${cat}:${kid}"]`)];
  return inputs.find((el) => el.offsetParent !== null) || inputs[0];
}

function syncWeightTwins(root, source) {
  const key = source?.dataset?.rsWeight;
  if (!key) return;
  root.querySelectorAll(`[data-rs-weight="${key}"]`).forEach((el) => {
    if (el !== source) el.value = source.value;
  });
}

function collectForm(root, baseline) {
  const next = clone(baseline.rankSimulation);
  next.weightMatrixByCategory = {};
  const fieldErrors = [];

  for (const cat of RANK_CATEGORY_IDS) {
    next.weightMatrixByCategory[cat] = {};
    for (const kid of KRA_WEIGHT_COLUMN_IDS) {
      const inp = preferredWeightInput(root, cat, kid);
      const label = `${RANK_CATEGORY_LABELS[cat]} · ${KRA_WEIGHT_COLUMN_LABELS[kid]}`;
      const parsed = parsePercentField(inp?.value, label);
      root.querySelectorAll(`[data-rs-weight-err="${cat}:${kid}"]`).forEach((errEl) => {
        if (parsed.ok) {
          errEl.hidden = true;
          errEl.textContent = '';
        } else {
          errEl.hidden = false;
          errEl.textContent = parsed.error;
        }
      });
      if (!parsed.ok) fieldErrors.push(parsed.error);
      next.weightMatrixByCategory[cat][kid] = round4(parsed.value);
    }
  }

  const count = (baseline.rankSimulation.scoreBrackets || []).length;
  next.scoreBrackets = [];
  for (let i = 0; i < count; i++) {
    const minRaw = root.querySelector(`[data-rs-bracket="${i}:min"]`)?.value;
    const maxRaw = root.querySelector(`[data-rs-bracket="${i}:max"]`)?.value;
    const incRaw = root.querySelector(`[data-rs-bracket="${i}:inc"]`)?.value;
    const min = Number(minRaw);
    const max = Number(maxRaw);
    const inc = Number(incRaw);
    for (const [key, raw, num] of [
      ['min', minRaw, min],
      ['max', maxRaw, max],
      ['inc', incRaw, inc],
    ]) {
      const errEl = root.querySelector(`[data-rs-bracket-err="${i}:${key}"]`);
      const blank = raw == null || String(raw).trim() === '';
      const bad = blank || !Number.isFinite(num);
      if (errEl) {
        errEl.hidden = !bad;
        errEl.textContent = bad ? 'Enter a valid number.' : '';
      }
      if (bad) fieldErrors.push(`Score range ${i + 1}: enter a valid number.`);
    }
    next.scoreBrackets.push({
      minInclusive: min,
      maxInclusive: max,
      subRankIncrements: inc,
    });
  }

  next.decimalBracketPolicy = root.querySelector('#rsDecimalPolicy')?.value || 'unresolved';
  next.decimalBracketPolicyNote = baseline.rankSimulation.decimalBracketPolicyNote;
  next.belowMinimumNote = baseline.rankSimulation.belowMinimumNote;
  next.sourceRef = baseline.rankSimulation.sourceRef;
  next.version = baseline.rankSimulation.version;
  next.status = baseline.rankSimulation.status || 'published';

  return { next, fieldErrors: [...new Set(fieldErrors)] };
}

function refreshLiveUi(root) {
  let allWeightsOk = true;
  for (const cat of RANK_CATEGORY_IDS) {
    let sum = 0;
    let valid = true;
    for (const kid of KRA_WEIGHT_COLUMN_IDS) {
      const inp = preferredWeightInput(root, cat, kid);
      const n = Number(inp?.value);
      if (!Number.isFinite(n)) valid = false;
      else sum += n / 100;
    }
    const total = formatWeightRowTotal(valid ? sum : NaN);
    if (!total.ok) allWeightsOk = false;
    root.querySelectorAll(`[data-rs-total="${cat}"]`).forEach((el) => {
      el.textContent = total.text;
      el.classList.toggle('ok', total.ok);
      el.classList.toggle('bad', !total.ok);
    });
  }

  const count = root.querySelectorAll('[data-rs-bracket-row]').length;
  const brackets = [];
  for (let i = 0; i < count; i++) {
    brackets.push({
      minInclusive: Number(root.querySelector(`[data-rs-bracket="${i}:min"]`)?.value),
      maxInclusive: Number(root.querySelector(`[data-rs-bracket="${i}:max"]`)?.value),
      subRankIncrements: Number(root.querySelector(`[data-rs-bracket="${i}:inc"]`)?.value),
    });
  }
  const gapEl = root.querySelector('#rsBracketGaps');
  if (gapEl) {
    const gaps = findUncoveredScoreRanges(brackets);
    gapEl.textContent = gaps.length
      ? gaps.join(' ')
      : 'Configured ranges are contiguous from the first score listed.';
  }

  const policy = root.querySelector('#rsDecimalPolicy')?.value || 'unresolved';
  const ex = root.querySelector('#rsDecimalExample');
  if (ex) {
    ex.textContent = policyMeta(policy).example;
    ex.classList.toggle('fl-rs-policy-example--warn', policy === 'unresolved');
  }
  return { allWeightsOk };
}

/** Normalized fingerprint so load formatting does not mark the page dirty. */
function fingerprint(rs) {
  const w = {};
  for (const cat of RANK_CATEGORY_IDS) {
    w[cat] = {};
    for (const kid of KRA_WEIGHT_COLUMN_IDS) {
      w[cat][kid] = round4(rs?.weightMatrixByCategory?.[cat]?.[kid]);
    }
  }
  const b = (rs?.scoreBrackets || []).map((row) => ({
    minInclusive: Number(row.minInclusive),
    maxInclusive: Number(row.maxInclusive),
    subRankIncrements: Number(row.subRankIncrements),
  }));
  return JSON.stringify({
    w,
    b,
    p: rs?.decimalBracketPolicy || 'unresolved',
  });
}

/**
 * Rank simulation settings — institution config (active), not scoring-catalog draft/publish.
 */
export function renderRankSimulationSettings(root, { readOnly = false } = {}) {
  if (!root) return;

  const store = MockStore.load();
  const ic = store.institutionConfig || DEFAULT_INSTITUTION_CONFIG();
  let baseline = snapshotState(ic);
  let savedFp = fingerprint(baseline.rankSimulation);
  let saving = false;

  const rs = baseline.rankSimulation;
  const weightTableRows = RANK_CATEGORY_IDS.map((cat) =>
    weightRowHtml(cat, rs.weightMatrixByCategory[cat], readOnly)
  ).join('');
  const weightCards = RANK_CATEGORY_IDS.map((cat) =>
    weightCardHtml(cat, rs.weightMatrixByCategory[cat], readOnly)
  ).join('');
  const bracketRows = (rs.scoreBrackets || []).map((b, i) => bracketRowHtml(b, i, readOnly)).join('');
  const policy = policyMeta(rs.decimalBracketPolicy);
  const ladder = baseline.rankOptions || [];
  const gaps = findUncoveredScoreRanges(rs.scoreBrackets || []);

  root.innerHTML = `
    <section class="fl-rs-page" aria-labelledby="rsHeading">
      <header class="fl-rs-header">
        <h2 id="rsHeading" class="fl-rs-title">Rank simulation settings</h2>
        <p class="fl-rs-lede">Set how assessment scores contribute to possible faculty rank advancement.</p>
      </header>

      <section class="card fl-rs-card" aria-labelledby="rsWeightsHeading">
        <h3 id="rsWeightsHeading" class="fl-rs-section-title">Assessment weights by current faculty rank</h3>
        <p class="fl-rs-section-lede">Each rank category must total 100%.</p>

        <div class="fl-rs-weights-desktop table-wrap">
          <table class="fl-rs-weights-table">
            <thead>
              <tr>
                <th scope="col">Current rank</th>
                ${KRA_WEIGHT_COLUMN_IDS.map((kid) => `<th scope="col">${esc(KRA_WEIGHT_COLUMN_LABELS[kid])}</th>`).join('')}
                <th scope="col">Total</th>
              </tr>
            </thead>
            <tbody>${weightTableRows}</tbody>
          </table>
        </div>
        <div class="fl-rs-weights-mobile" aria-label="Assessment weights by rank">${weightCards}</div>
      </section>

      <section class="card fl-rs-card" aria-labelledby="rsBracketsHeading">
        <h3 id="rsBracketsHeading" class="fl-rs-section-title">Score ranges and rank advancement</h3>
        <p class="fl-rs-section-lede">One rank step is the next position in the faculty rank order, not an entire rank category.</p>
        <div class="table-wrap">
          <table class="fl-rs-brackets-table">
            <thead>
              <tr>
                <th scope="col">From</th>
                <th scope="col">To</th>
                <th scope="col">Rank steps gained</th>
              </tr>
            </thead>
            <tbody>${bracketRows}</tbody>
          </table>
        </div>
        <p id="rsBracketGaps" class="fl-rs-gaps" aria-live="polite">${esc(
          gaps.length ? gaps.join(' ') : 'Configured ranges are contiguous from the first score listed.'
        )}</p>
      </section>

      <section class="card fl-rs-card fl-rs-additional" aria-labelledby="rsMoreHeading">
        <h3 id="rsMoreHeading" class="fl-rs-section-title">Additional settings</h3>

        <div class="fl-rs-additional__block">
          <h4 class="fl-rs-subheading">Scores with decimals</h4>
          <label class="fl-field fl-rs-policy-field" for="rsDecimalPolicy">
            <span class="fl-rs-sr-only">Scores with decimals</span>
            <select id="rsDecimalPolicy" ${readOnly ? 'disabled' : ''}>
              ${DECIMAL_POLICY_OPTIONS.map(
                (o) =>
                  `<option value="${esc(o.value)}" ${rs.decimalBracketPolicy === o.value ? 'selected' : ''}>${esc(o.label)}</option>`
              ).join('')}
            </select>
          </label>
          <p id="rsDecimalExample" class="fl-rs-policy-example${rs.decimalBracketPolicy === 'unresolved' ? ' fl-rs-policy-example--warn' : ''}" aria-live="polite">${esc(policy.example)}</p>
          ${
            rs.decimalBracketPolicyNote
              ? `<details class="fl-rs-inline-details"><summary>Source details</summary><p class="muted">${esc(rs.decimalBracketPolicyNote)}</p></details>`
              : ''
          }
        </div>

        <details class="fl-rs-inline-details fl-rs-ladder">
          <summary>Faculty rank order <span class="muted">(${ladder.length})</span></summary>
          <p class="muted fl-rs-compact-note">One rank step moves to the next position in this list.</p>
          <ol class="fl-rs-ladder-list">
            ${
              ladder.length
                ? ladder.map((r, i) => `<li><span class="fl-rs-ladder-num">${i + 1}.</span> ${esc(r)}</li>`).join('')
                : '<li class="muted">No ranks configured</li>'
            }
          </ol>
        </details>

        <details class="fl-rs-inline-details">
          <summary>Guideline references</summary>
          <p class="muted">${esc(rs.sourceRef || 'DBM–CHED Joint Circular No. 3 (9th Cycle) Tables 2.2 and 3.1')}</p>
          ${rs.belowMinimumNote ? `<p class="muted">${esc(rs.belowMinimumNote)}</p>` : ''}
        </details>

        <details class="fl-rs-inline-details">
          <summary>Technical details</summary>
          <p class="muted">Updates institution simulation settings used for preparation. Does not publish scoring-rule versions or change faculty assessment pins. Version: ${esc(rs.version || '—')}</p>
        </details>
      </section>

      ${
        readOnly
          ? '<p class="muted">These settings are managed by your administrator.</p>'
          : `<footer class="fl-rs-actions" role="region" aria-label="Save rank simulation settings">
              <div class="fl-rs-actions__row">
                <span id="rsDirty" class="fl-rs-status-chip" data-state="saved">All changes saved</span>
                <div class="fl-rs-actions__buttons">
                  <button type="button" class="cfg-btn-secondary btn-sm" id="rsCancel" disabled>Cancel changes</button>
                  <button type="button" class="btn-primary-sm btn-sm" id="rsSave" disabled>Save changes</button>
                </div>
              </div>
              <p class="fl-rs-action-help">Saving updates the active simulation settings.</p>
              <p id="rsMsg" class="fl-rs-msg" role="status" aria-live="polite"></p>
            </footer>`
      }

      <p class="fl-rs-footer-note" role="note">Simulation supports preparation. Official rank decisions remain with authorized committees.</p>
    </section>
  `;

  if (readOnly) return;

  const msg = root.querySelector('#rsMsg');
  const dirtyChip = root.querySelector('#rsDirty');
  const saveBtn = root.querySelector('#rsSave');
  const cancelBtn = root.querySelector('#rsCancel');

  const updateActionState = () => {
    const { next, fieldErrors } = collectForm(root, baseline);
    const live = refreshLiveUi(root);
    const dirty = fingerprint(next) !== savedFp;
    const invalid = fieldErrors.length > 0 || !live.allWeightsOk || validateRankSimulation(next).length > 0;
    if (dirtyChip) {
      dirtyChip.textContent = dirty ? 'Unsaved changes' : 'All changes saved';
      dirtyChip.dataset.state = dirty ? 'dirty' : 'saved';
    }
    if (cancelBtn) cancelBtn.disabled = !dirty || saving;
    if (saveBtn) saveBtn.disabled = !dirty || invalid || saving;
    return { next, fieldErrors, dirty, invalid };
  };

  const onChange = (e) => {
    if (e?.target?.dataset?.rsWeight) syncWeightTwins(root, e.target);
    updateActionState();
    if (msg && msg.dataset.kind === 'ok') {
      msg.textContent = '';
      delete msg.dataset.kind;
      msg.classList.remove('fl-rs-msg--err');
    }
  };

  root.querySelectorAll('[data-rs-weight], [data-rs-bracket], #rsDecimalPolicy').forEach((el) => {
    el.addEventListener('input', onChange);
    el.addEventListener('change', onChange);
  });

  cancelBtn?.addEventListener('click', () => {
    if (cancelBtn.disabled) return;
    renderRankSimulationSettings(root, { readOnly: false });
  });

  saveBtn?.addEventListener('click', async () => {
    if (saving || saveBtn.disabled) return;
    const { next, fieldErrors } = collectForm(root, baseline);
    const errs = [...fieldErrors, ...validateRankSimulation(next)];
    if (errs.length) {
      msg.textContent = errs[0];
      msg.dataset.kind = 'err';
      msg.classList.add('fl-rs-msg--err');
      updateActionState();
      return;
    }
    msg.classList.remove('fl-rs-msg--err');
    saving = true;
    updateActionState();
    saveBtn.textContent = 'Saving…';
    msg.textContent = 'Saving changes…';
    try {
      const s = MockStore.load();
      const institutionConfig = {
        ...(s.institutionConfig || DEFAULT_INSTITUTION_CONFIG()),
        rankSimulation: next,
        rankOptions: baseline.rankOptions,
      };
      await PortalApi.saveInstitution(institutionConfig);
      s.institutionConfig = institutionConfig;
      MockStore.save(s);
      baseline = snapshotState(institutionConfig);
      savedFp = fingerprint(baseline.rankSimulation);
      msg.textContent = 'Rank simulation settings saved.';
      msg.dataset.kind = 'ok';
    } catch (ex) {
      msg.textContent = ex.message || 'Save failed. Your entries were kept — fix the issue and try again.';
      msg.dataset.kind = 'err';
      msg.classList.add('fl-rs-msg--err');
    } finally {
      saving = false;
      saveBtn.textContent = 'Save changes';
      updateActionState();
    }
  });

  updateActionState();
}
