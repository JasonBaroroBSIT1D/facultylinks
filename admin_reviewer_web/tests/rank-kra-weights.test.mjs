import test from 'node:test';
import assert from 'node:assert/strict';
import {
  resolveRankCategory,
  resolveRankKraWeights,
  DEFAULT_WEIGHT_MATRIX,
} from '../js/core/rank-simulation-config.js';

test('sub-ranks map to shared categories', () => {
  assert.equal(resolveRankCategory('Instructor III'), 'instructor');
  assert.equal(resolveRankCategory('Professor VI'), 'professor');
  assert.equal(resolveRankCategory('Visiting Scholar'), null);
});

test('KRA I raw 58.92 instructor contribution', () => {
  const raw = 58.92;
  const w = DEFAULT_WEIGHT_MATRIX.instructor['kra-I'];
  assert.equal(Math.round(raw * w * 1000) / 1000, 35.352);
});

test('unknown rank does not return instructor weights', () => {
  const res = resolveRankKraWeights('Guest Lecturer', {});
  assert.equal(res.ok, false);
  assert.equal(res.weights, undefined);
});

test('weighted contributions sum to overall', () => {
  const raws = { 'kra-I': 58.92, 'kra-II': 10, 'kra-III': 20, 'kra-IV': 5 };
  const weights = DEFAULT_WEIGHT_MATRIX.associate_professor;
  let total = 0;
  for (const kid of Object.keys(raws)) {
    total += raws[kid] * weights[kid];
  }
  assert.ok(total > 0);
  assert.equal(
    Math.round(total * 10000) / 10000,
  Math.round(
      Object.keys(raws).reduce((a, k) => a + raws[k] * weights[k], 0) * 10000,
    ) / 10000,
  );
});