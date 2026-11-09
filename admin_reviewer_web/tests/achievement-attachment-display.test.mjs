import test from 'node:test';
import assert from 'node:assert/strict';
import {
  attachmentReviewStatusHtml,
  documentCountsTowardLegacyPending,
  enrichPortalDocuments,
  dedupeDocumentsById,
} from '../js/portal/achievement-attachment-display.js';

test('attachment shows part of approved achievement', () => {
  const html = attachmentReviewStatusHtml(
    { id: 'd1', reviewStatus: 'pending', indicatorId: 'kra-I-B-1-1' },
    { achievement: { submissionStatus: 'submitted', reviewStatus: 'approved' } }
  );
  assert.match(html, /Part of approved achievement/);
  assert.doesNotMatch(html, /Waiting for review/);
});

test('legacy pending excludes B/C indicators', () => {
  assert.equal(
    documentCountsTowardLegacyPending({ reviewStatus: 'pending', indicatorId: 'kra-I-B-1-1' }, []),
    false
  );
  assert.equal(
    documentCountsTowardLegacyPending({ reviewStatus: 'pending', indicatorId: 'kra-I-A-setsef-eval' }, []),
    true
  );
});

test('enrich and dedupe portal documents', () => {
  const assessments = {
    'u-1': {
      achievements: [
        {
          id: 'a1',
          submissionStatus: 'submitted',
          reviewStatus: 'approved',
          documentIds: ['x'],
        },
      ],
    },
  };
  const docs = enrichPortalDocuments(
    [
      { id: 'x', reviewStatus: 'pending' },
      { id: 'x', reviewStatus: 'pending' },
    ],
    assessments
  );
  assert.equal(docs.length, 1);
  assert.equal(docs[0].parentReviewStatus, 'approved');
});

test('dedupe by id not filename', () => {
  const rows = dedupeDocumentsById([
    { id: '1', fileName: 'same.pdf' },
    { id: '2', fileName: 'same.pdf' },
  ]);
  assert.equal(rows.length, 2);
});
