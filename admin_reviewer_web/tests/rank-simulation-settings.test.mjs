import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEFAULT_RANK_SIMULATION,
  decimalToPercentDisplay,
  formatWeightRowTotal,
  percentInputToDecimal,
  parsePercentField,
  validateRankSimulation,
  findUncoveredScoreRanges,
  bracketSummary,
} from '../js/core/rank-simulation-config.js';

test('stored 0.6 displays as 60 and converts back to 0.6', () => {
  assert.equal(decimalToPercentDisplay(0.6), '60');
  assert.equal(percentInputToDecimal('60'), 0.6);
  assert.equal(percentInputToDecimal('60.0'), 0.6);
});

test('does not double-convert already-decimal storage', () => {
  // UI shows percent; save path divides by 100 once.
  const shown = decimalToPercentDisplay(0.6);
  const saved = percentInputToDecimal(shown);
  assert.equal(saved, 0.6);
});

test('row total messaging', () => {
  assert.equal(formatWeightRowTotal(1).text, '✓ 100%');
  assert.match(formatWeightRowTotal(0.9).text, /90% — Add 10%/);
  assert.match(formatWeightRowTotal(1.1).text, /110% — Reduce by 10%/);
});

test('blank negative non-finite percent fields fail', () => {
  assert.equal(parsePercentField('', 'Instruction').ok, false);
  assert.equal(parsePercentField('-1', 'Instruction').ok, false);
  assert.equal(parsePercentField('abc', 'Instruction').ok, false);
  assert.equal(parsePercentField('101', 'Instruction').ok, false);
  assert.equal(parsePercentField('60', 'Instruction').value, 0.6);
});

test('default matrix validates and invalid totals are blocked', () => {
  const rs = DEFAULT_RANK_SIMULATION();
  assert.deepEqual(validateRankSimulation(rs), []);
  rs.weightMatrixByCategory.instructor['kra-I'] = 0.5;
  const errs = validateRankSimulation(rs);
  assert.ok(errs.some((e) => /Instructor/.test(e) && /100%/.test(e)));
});

test('bracket summary and uncovered ranges', () => {
  assert.equal(bracketSummary({ minInclusive: 41, maxInclusive: 50, subRankIncrements: 1 }), '41–50 points → 1 rank step');
  const gaps = findUncoveredScoreRanges([
    { minInclusive: 41, maxInclusive: 50, subRankIncrements: 1 },
    { minInclusive: 61, maxInclusive: 70, subRankIncrements: 3 },
  ]);
  assert.ok(gaps.some((g) => /51 to 60/.test(g)));
  assert.ok(gaps.some((g) => /below 41/.test(g)));
});
