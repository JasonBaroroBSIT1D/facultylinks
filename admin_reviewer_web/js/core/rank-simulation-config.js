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

export function validateRankSimulation(rs) {
  const errors = [];
  const wmb = rs?.weightMatrixByCategory || {};
  for (const cat of RANK_CATEGORY_IDS) {
    const row = wmb[cat];
    if (!row) {
      errors.push(`Missing weights for ${cat}`);
      continue;
    }
    const sum = Object.values(row).reduce((a, b) => a + Number(b), 0);
    if (Math.abs(sum - 1) > 0.001) errors.push(`${RANK_CATEGORY_LABELS[cat]} weights sum to ${sum.toFixed(4)} (expected 1.0)`);
  }
  const brackets = rs?.scoreBrackets || [];
  let prevHi = null;
  for (const b of [...brackets].sort((a, c) => a.minInclusive - c.minInclusive)) {
    if (b.minInclusive == null || b.maxInclusive == null) errors.push('Bracket missing min/max');
    if (b.minInclusive > b.maxInclusive) errors.push(`Invalid bracket ${b.minInclusive}-${b.maxInclusive}`);
    if (prevHi != null && b.minInclusive <= prevHi) errors.push('Overlapping brackets');
    prevHi = b.maxInclusive;
  }
  return errors;
}

function structuredClone(v) {
  return JSON.parse(JSON.stringify(v));
}
