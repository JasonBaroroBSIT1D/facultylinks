import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatFileSize,
  fileTypeLabel,
  groupAchievementsByIndicator,
  achievementReviewStatusLabel,
  formatCompactUploadDate,
  criterionBackLabel,
  formatAchievementContextLine,
  rulePermittedPoints,
} from '../js/portal/achievement-review-format.js';
import { resolveSupportingDocuments } from '../js/portal/achievement-attachment-display.js';

test('formatFileSize handles unknown and kb', () => {
  assert.equal(formatFileSize(null), '—');
  assert.equal(formatFileSize(0), '—');
  assert.equal(formatFileSize(2048), '2.0 KB');
});

test('fileTypeLabel uses mime and extension', () => {
  assert.equal(fileTypeLabel({ mimeType: 'application/pdf', fileName: 'x.pdf' }), 'PDF');
  assert.equal(fileTypeLabel({ fileName: 'photo.PNG' }), 'PNG');
});

test('achievementReviewStatusLabel', () => {
  assert.equal(achievementReviewStatusLabel('approved'), 'Approved');
  assert.equal(achievementReviewStatusLabel('correction_requested'), 'Needs changes');
});

test('formatCompactUploadDate', () => {
  const s = formatCompactUploadDate('2026-11-09T12:00:00Z');
  assert.match(s, /2026/);
});

test('criterionBackLabel for KRA III D', () => {
  assert.equal(criterionBackLabel('kra-III-D'), 'Back to Criterion D');
  assert.equal(criterionBackLabel('kra-I-B'), 'Back to Criterion B');
});

test('formatAchievementContextLine designation labels', () => {
  const line = formatAchievementContextLine({
    designationLevel: 'college_department',
    designationRole: 'department_head',
  });
  assert.match(line, /College \/ department level/);
  assert.match(line, /Department head/);
});

test('rulePermittedPoints prefers ruleExpectedPoints', () => {
  assert.equal(rulePermittedPoints({ ruleExpectedPoints: 4, permittedMax: 20 }), 4);
});

test('resolveSupportingDocuments matches by public id', () => {
  const store = {
    documents: [{ id: 'doc-a', facultyId: 'u-2', fileName: 'a.pdf' }],
    assessments: {},
  };
  const { docs, missing } = resolveSupportingDocuments(store, 'u-2', ['doc-a', 'missing']);
  assert.equal(docs.length, 1);
  assert.equal(missing.length, 1);
});

test('groupAchievementsByIndicator', () => {
  const g = groupAchievementsByIndicator([
    { id: 'a1', indicatorId: 'kra-I-B-1-1' },
    { id: 'a2', indicatorId: 'kra-I-B-1-1' },
    { id: 'a3', indicatorId: 'kra-I-B-1-2' },
  ]);
  assert.equal(g.get('kra-I-B-1-1').length, 2);
  assert.equal(g.get('kra-I-B-1-2').length, 1);
});
