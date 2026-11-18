/** JC3 Table 2.2 / 3.1 rank simulation defaults (admin-configurable). */

export const RANK_CATEGORY_IDS = [
  'instructor',
  'assistant_professor',
  'associate_professor',
  'professor',
  'college_university_professor',
];

export const RANK_CATEGORY_LABELS = {
  instructor: 'Instructor I–III',
  assistant_professor: 'Assistant Professor I–IV',
  associate_professor: 'Associate Professor I–V',
  professor: 'Professor I–VI',
  college_university_professor: 'College/University Professor',
};

export const KRA_WEIGHT_COLUMN_IDS = ['kra-I', 'kra-II', 'kra-III', 'kra-IV'];

export const KRA_WEIGHT_COLUMN_LABELS = {
  'kra-I': 'Instruction',
  'kra-II': 'Research',
  'kra-III': 'Extension',
  'kra-IV': 'Professional Development',
};

export const DEFAULT_WEIGHT_MATRIX = {
  instructor: { 'kra-I': 0.6, 'kra-II': 0.1, 'kra-III': 0.2, 'kra-IV': 0.1 },
  assistant_professor: { 'kra-I': 0.5, 'kra-II': 0.2, 'kra-III': 0.2, 'kra-IV': 0.1 },
  associate_professor: { 'kra-I': 0.4, 'kra-II': 0.3, 'kra-III': 0.2, 'kra-IV': 0.1 },
  professor: { 'kra-I': 0.3, 'kra-II': 0.4, 'kra-III': 0.2, 'kra-IV': 0.1 },
  college_university_professor: { 'kra-I': 0.2, 'kra-II': 0.5, 'kra-III': 0.2, 'kra-IV': 0.1 },
};

export const DEFAULT_SCORE_BRACKETS = [
  { minInclusive: 41, maxInclusive: 50, subRankIncrements: 1 },
  { minInclusive: 51, maxInclusive: 60, subRankIncrements: 2 },
  { minInclusive: 61, maxInclusive: 70, subRankIncrements: 3 },
  { minInclusive: 71, maxInclusive: 80, subRankIncrements: 4 },
  { minInclusive: 81, maxInclusive: 90, subRankIncrements: 5 },
  { minInclusive: 91, maxInclusive: 100, subRankIncrements: 6 },
];

export const DECIMAL_POLICY_OPTIONS = [
  {
    value: 'unresolved',
    label: 'Not configured',
    example: 'Choose a decimal-score rule to confirm affected rank projections.',
  },
  {
    value: 'floor_to_bracket',
    label: 'Use the lower whole-number score',
    example: 'Example: 70.62 uses 70, which falls in the 61–70 range (3 rank steps).',
  },
  {
    value: 'round_half_up',
    label: 'Round to the nearest whole number (half rounds up)',
    example: 'Example: 70.62 rounds to 71, which falls in the 71–80 range (4 rank steps).',
  },
];

export const DEFAULT_RANK_SIMULATION = () => ({
  status: 'published',
  version: 'jc3-table-2.2-3.1',
  sourceRef: 'DBM–CHED Joint Circular No. 3 (9th Cycle) Tables 2.2 and 3.1',
  weightMatrixByCategory: structuredClone(DEFAULT_WEIGHT_MATRIX),
  scoreBrackets: structuredClone(DEFAULT_SCORE_BRACKETS),
  decimalBracketPolicy: 'unresolved',
  decimalBracketPolicyNote:
    'Table 3.1 lists whole-number brackets only. Publish a decimal rule before fractional scores (e.g. 78.02) yield authoritative increments.',
  belowMinimumNote: 'Table 3.1 does not define sub-rank increments for scores below 41.',
});

export const DEFAULT_RANK_LADDER = () => [
  'Instructor I',
  'Instructor II',
  'Instructor III',
  'Assistant Professor I',
  'Assistant Professor II',
  'Assistant Professor III',
  'Assistant Professor IV',
  'Associate Professor I',
  'Associate Professor II',
  'Associate Professor III',
  'Associate Professor IV',
  'Associate Professor V',
  'Professor I',
  'Professor II',
  'Professor III',
  'Professor IV',
  'Professor V',
  'Professor VI',
  'College/University Professor',
];

const WEIGHT_TOLERANCE = 0.001;

export function decimalToPercentDisplay(d) {
  const n = Number(d);
  if (!Number.isFinite(n)) return '';
  const pct = Math.round(n * 10000) / 100;
  return Number.isInteger(pct) ? String(pct) : String(pct);
}

export function percentInputToDecimal(raw) {
  if (raw == null || String(raw).trim() === '') return NaN;
  const n = Number(String(raw).trim());
  if (!Number.isFinite(n)) return NaN;
  return n / 100;
}

export function formatWeightRowTotal(sumDecimal) {
  if (!Number.isFinite(sumDecimal)) {
    return { ok: false, text: 'Enter valid percentages for every area.', badge: '—', pct: null };
  }
  const pct = Math.round(sumDecimal * 10000) / 100;
  const pctLabel = Number.isInteger(pct) ? `${pct}%` : `${pct}%`;
  if (Math.abs(sumDecimal - 1) <= WEIGHT_TOLERANCE) {
    return { ok: true, text: '✓ 100%', badge: '✓ 100%', pct };
  }
  if (sumDecimal < 1) {
    const need = Math.round((1 - sumDecimal) * 10000) / 100;
    return { ok: false, text: `${pctLabel} — Add ${need}%`, badge: pctLabel, pct };
  }
  const extra = Math.round((sumDecimal - 1) * 10000) / 100;
  return { ok: false, text: `${pctLabel} — Reduce by ${extra}%`, badge: pctLabel, pct };
}

export function parsePercentField(raw, label) {
  if (raw == null || String(raw).trim() === '') {
    return { ok: false, error: `${label} is required.`, value: NaN };
  }
  const n = Number(String(raw).trim());
  if (!Number.isFinite(n)) {
    return { ok: false, error: `${label} must be a number.`, value: NaN };
  }
  if (n < 0 || n > 100) {
    return { ok: false, error: `${label} must be between 0% and 100%.`, value: NaN };
  }
  return { ok: true, error: null, value: n / 100 };
}

export function bracketSummary(b) {
  const lo = b?.minInclusive;
  const hi = b?.maxInclusive;
  const steps = b?.subRankIncrements;
  if (![lo, hi, steps].every((x) => Number.isFinite(Number(x)))) return '';
  return `${lo}–${hi} points → ${steps} rank step${Number(steps) === 1 ? '' : 's'}`;
}

export function findUncoveredScoreRanges(brackets) {
  const notes = [];
  const sorted = [...(brackets || [])]
    .filter((b) => Number.isFinite(Number(b.minInclusive)) && Number.isFinite(Number(b.maxInclusive)))
    .sort((a, c) => Number(a.minInclusive) - Number(c.minInclusive));
  if (!sorted.length) {
    notes.push('No score ranges are configured yet.');
    return notes;
  }
  const first = Number(sorted[0].minInclusive);
  if (first > 0) {
    notes.push(`Scores below ${first} are not covered by a configured range.`);
  }
  for (let i = 1; i < sorted.length; i++) {
    const prevHi = Number(sorted[i - 1].maxInclusive);
    const lo = Number(sorted[i].minInclusive);
    if (lo > prevHi + 1) {
      notes.push(`Scores from ${prevHi + 1} to ${lo - 1} are not covered by a configured range.`);
    }
  }
  return notes;
}

/**
 * Validates rank-simulation config. Weight rows must sum to 1.0 (decimal storage).
 * Does not silently normalize values.
 */
export function validateRankSimulation(rs) {
  const errors = [];
  const wmb = rs?.weightMatrixByCategory || {};
  for (const cat of RANK_CATEGORY_IDS) {
    const row = wmb[cat];
    const label = RANK_CATEGORY_LABELS[cat] || cat;
    if (!row) {
      errors.push(`Missing weights for ${label}.`);
      continue;
    }
    let sum = 0;
    for (const kid of KRA_WEIGHT_COLUMN_IDS) {
      const v = Number(row[kid]);
      if (!Number.isFinite(v) || v < 0 || v > 1) {
        errors.push(`${label}: ${KRA_WEIGHT_COLUMN_LABELS[kid]} must be a valid percentage (0–100%).`);
        sum = NaN;
        break;
      }
      sum += v;
    }
    if (!Number.isFinite(sum)) continue;
    if (Math.abs(sum - 1) > WEIGHT_TOLERANCE) {
      const pct = Math.round(sum * 10000) / 100;
      errors.push(`${label} weights total ${pct}% (must equal 100%).`);
    }
  }

  const brackets = rs?.scoreBrackets || [];
  if (!brackets.length) {
    errors.push('At least one score range is required.');
  }
  const sortedIdx = brackets
    .map((b, i) => ({ b, i }))
    .sort((a, c) => Number(a.b.minInclusive) - Number(c.b.minInclusive));
  let prevHi = null;
  const seen = new Set();
  for (const { b, i } of sortedIdx) {
    const lo = Number(b.minInclusive);
    const hi = Number(b.maxInclusive);
    const inc = Number(b.subRankIncrements);
    const rowLabel = `Score range ${i + 1}`;
    if (!Number.isFinite(lo) || !Number.isFinite(hi) || !Number.isFinite(inc)) {
      errors.push(`${rowLabel}: enter valid numbers for score from, score to, and rank steps.`);
      continue;
    }
    if (lo > hi) errors.push(`${rowLabel}: score from must be less than or equal to score to.`);
    if (inc < 0 || !Number.isInteger(inc)) {
      errors.push(`${rowLabel}: rank steps gained must be a whole number ≥ 0.`);
    }
    const key = `${lo}|${hi}`;
    if (seen.has(key)) errors.push(`${rowLabel}: duplicate range ${lo}–${hi}.`);
    seen.add(key);
    if (prevHi != null && lo <= prevHi) {
      errors.push(`${rowLabel}: overlaps another range ending at ${prevHi}.`);
    }
    prevHi = hi;
  }

  const policy = rs?.decimalBracketPolicy;
  if (policy && !DECIMAL_POLICY_OPTIONS.some((o) => o.value === policy)) {
    errors.push('Choose a supported rule for scores with decimals.');
  }
  return errors;
}

function structuredClone(v) {
  return JSON.parse(JSON.stringify(v));
}
