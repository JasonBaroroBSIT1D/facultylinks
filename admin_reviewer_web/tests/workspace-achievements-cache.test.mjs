import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ACH_LOAD_IDLE,
  ACH_LOAD_LOADED,
  achievementsForCriterion,
  clearWorkspaceAchievementsCache,
  countAchievementsList,
  filterSubmittedAchievements,
  resolveAchievementCriterionId,
} from '../js/portal/workspace-achievements-cache.js';

test('resolveAchievementCriterionId matches backend rules', () => {
  assert.equal(resolveAchievementCriterionId({ criterionId: 'kra-I-B' }), 'kra-I-B');
  assert.equal(resolveAchievementCriterionId({ indicatorId: 'kra-I-C-2-1' }), 'kra-I-C');
  assert.equal(resolveAchievementCriterionId({ indicatorId: 'kra-I-B-1-2' }), 'kra-I-B');
  assert.equal(resolveAchievementCriterionId({ indicatorId: 'kra-IV-B-2' }), 'kra-IV-B');
  assert.equal(resolveAchievementCriterionId({ indicatorId: 'kra-IV-D-1' }), 'kra-IV-D');
});

test('filterSubmittedAchievements excludes drafts', () => {
  const rows = [
    { id: '1', submissionStatus: 'submitted', reviewStatus: 'approved' },
    { id: '2', submissionStatus: 'draft' },
  ];
  assert.equal(filterSubmittedAchievements(rows).length, 1);
});

test('countAchievementsList counts approved and pending separately', () => {
  const rows = [
    { id: '1', submissionStatus: 'submitted', criterionId: 'kra-I-B', reviewStatus: 'approved' },
    { id: '2', submissionStatus: 'submitted', indicatorId: 'kra-I-B-1-2', reviewStatus: 'pending' },
    { id: '3', submissionStatus: 'submitted', criterionId: 'kra-I-C', reviewStatus: 'approved' },
  ];
  const b = countAchievementsList(rows, 'kra-I-B');
  assert.equal(b.total, 2);
  assert.equal(b.pending, 1);
  const c = countAchievementsList(rows, 'kra-I-C');
  assert.equal(c.total, 1);
  assert.equal(achievementsForCriterion(rows, 'kra-I-B').length, 2);
});

test('clearWorkspaceAchievementsCache resets module state', () => {
  clearWorkspaceAchievementsCache();
  assert.doesNotThrow(() => clearWorkspaceAchievementsCache());
});
