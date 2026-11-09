import test from 'node:test';
import assert from 'node:assert/strict';
import {
  workspaceCriterionHeading,
  isSetSefEvaluationDoc,
  isSpecialStatusTeachingDoc,
  coercePortalDocumentsList,
  buildCriterionADocumentsHtml,
} from '../js/portal/workspace-kra-i-sections.js';
import { ASSESSMENT_CATALOG } from '../js/core/assessment-definitions.js';

test('workspaceCriterionHeading uses catalog names', () => {
  assert.equal(workspaceCriterionHeading(ASSESSMENT_CATALOG, 'kra-I-A'), 'A. Teaching Effectiveness');
  assert.equal(workspaceCriterionHeading(ASSESSMENT_CATALOG, 'kra-I-B'), 'B. Instructional Materials Development');
});

test('set/sef vs special status document classification', () => {
  assert.equal(isSetSefEvaluationDoc({ documentKind: 'set_sef_unified', indicatorId: 'kra-I-A-setsef-eval' }), true);
  assert.equal(isSpecialStatusTeachingDoc({ indicatorId: 'kra-I-A-special' }), true);
  assert.equal(isSetSefEvaluationDoc({ indicatorId: 'kra-I-A-special' }), false);
});

test('coercePortalDocumentsList accepts array and { documents: [] } portal payloads', () => {
  const rows = [{ id: 'd1', fileName: 'a.pdf' }];
  assert.deepEqual(coercePortalDocumentsList(rows), rows);
  assert.deepEqual(coercePortalDocumentsList({ documents: rows }), rows);
  assert.deepEqual(coercePortalDocumentsList(null), []);
  assert.throws(() => coercePortalDocumentsList({ items: rows }), /expected documents array/);
});

test('buildCriterionADocumentsHtml lists SET/SEF rows and handles empty faculty docs', () => {
  const store = {
    documents: [
      {
        id: 'pdf1',
        facultyId: 'fac-1',
        fileName: 'eval.pdf',
        documentKind: 'set_sef_unified',
        indicatorId: 'kra-I-A-setsef-eval',
        reviewStatus: 'pending',
        uploadedAt: '2026-01-10T12:00:00Z',
      },
      {
        id: 'sp1',
        facultyId: 'fac-1',
        fileName: 'leave.pdf',
        indicatorId: 'kra-I-A-special',
        reviewStatus: 'approved',
        uploadedAt: '2026-01-11T12:00:00Z',
      },
      {
        id: 'other',
        facultyId: 'fac-2',
        fileName: 'x.pdf',
        documentKind: 'set_sef_unified',
        indicatorId: 'kra-I-A-setsef-eval',
      },
    ],
  };
  const html = buildCriterionADocumentsHtml(store, 'fac-1', ASSESSMENT_CATALOG);
  assert.match(html, /data-doc="pdf1"/);
  assert.match(html, /data-doc="sp1"/);
  assert.doesNotMatch(html, /data-doc="other"/);
  const emptyHtml = buildCriterionADocumentsHtml({ documents: [] }, 'fac-1', ASSESSMENT_CATALOG);
  assert.match(emptyHtml, /No SET\/SEF evaluation uploads yet/);
  assert.match(emptyHtml, /No special-status supporting documents/);
});

test('buildCriterionADocumentsHtml unwraps cached portal blob with documents key', () => {
  const html = buildCriterionADocumentsHtml(
    {
      documents: {
        documents: [
          {
            id: 'nested',
            facultyId: 'f1',
            fileName: 'nested.pdf',
            documentKind: 'set_sef_combined',
            indicatorId: 'kra-I-A-setsef-combined',
            reviewStatus: 'pending',
          },
        ],
      },
    },
    'f1',
    null
  );
  assert.match(html, /data-doc="nested"/);
});
