import test from 'node:test';
import assert from 'node:assert/strict';
import {
  WS_FOLDER_CRITERION,
  WS_FOLDER_FACULTY,
  buildFacultyRootFolderHtml,
  buildKraICriterionFoldersHtml,
  buildWorkspaceBreadcrumb,
  buildAchievementReviewBreadcrumb,
  countCriterionADocs,
  kraIInstructionCounts,
  kraIIResearchCounts,
  workspaceScrollKey,
} from '../js/portal/workspace-folder-nav.js';
import { ACH_LOAD_LOADED, ACH_LOAD_LOADING } from '../js/portal/workspace-achievements-cache.js';
import { ASSESSMENT_CATALOG } from '../js/core/assessment-definitions.js';

const fac = { id: 'fac-1', firstName: 'Jason', lastName: 'Baroro' };

test('workspaceScrollKey distinguishes criterion levels', () => {
  assert.equal(workspaceScrollKey({ folder: WS_FOLDER_FACULTY }), WS_FOLDER_FACULTY);
  assert.equal(workspaceScrollKey({ folder: WS_FOLDER_CRITERION, criterionId: 'kra-I-B' }), 'criterion-kra-I-B');
});

test('kraIInstructionCounts aggregates A docs and B/C achievements', () => {
  const store = {
    documents: [
      {
        id: 'd1',
        facultyId: 'fac-1',
        documentKind: 'set_sef_unified',
        indicatorId: 'kra-I-A-setsef-eval',
        reviewStatus: 'pending',
      },
      { id: 'd2', facultyId: 'fac-1', indicatorId: 'kra-I-A-special', reviewStatus: 'approved' },
    ],
    assessments: {
      'fac-1': {
        achievements: [
          { id: 'a1', indicatorId: 'kra-I-B-textbook', submissionStatus: 'submitted', reviewStatus: 'pending' },
          { id: 'a2', indicatorId: 'kra-I-C-advise', submissionStatus: 'submitted', reviewStatus: 'approved' },
        ],
      },
    },
  };
  const a = countCriterionADocs(store, 'fac-1');
  assert.equal(a.setSef, 1);
  assert.equal(a.special, 1);
  const k = kraIInstructionCounts(store, 'fac-1', {
    state: ACH_LOAD_LOADED,
    achievements: store.assessments['fac-1'].achievements,
  });
  assert.equal(k.items, 4);
  assert.equal(k.pending, 2);
});

test('bc folder meta shows Loading before fetch completes', () => {
  const counts = kraIInstructionCounts({ documents: [] }, 'fac-1', { state: ACH_LOAD_LOADING, achievements: [] });
  const html = buildKraICriterionFoldersHtml(ASSESSMENT_CATALOG, counts);
  assert.match(html, /Loading…/);
  assert.doesNotMatch(html, /No items yet/);
});

test('folder html exposes kra-i and criterion navigation targets', () => {
  const counts = kraIInstructionCounts(
    { documents: [], assessments: {} },
    'fac-1',
    { state: ACH_LOAD_LOADED, achievements: [] }
  );
  const iiCounts = kraIIResearchCounts({ state: ACH_LOAD_LOADED, achievements: [] });
  const iiiCounts = { achLoadState: ACH_LOAD_LOADED, items: 0, pending: 0, byCriterion: {} };
  const ivCounts = { achLoadState: 'loaded', items: 0, pending: 0, byCriterion: {} };
  assert.match(buildFacultyRootFolderHtml(counts, iiCounts, iiiCounts, ivCounts), /data-ws-nav="kra-i"/);
  assert.match(buildFacultyRootFolderHtml(counts, iiCounts, iiiCounts, ivCounts), /KRA II/);
  assert.match(buildFacultyRootFolderHtml(counts, iiCounts, iiiCounts, ivCounts), /KRA IV/);
  const inner = buildKraICriterionFoldersHtml(ASSESSMENT_CATALOG, counts);
  assert.match(inner, /data-ws-criterion="kra-I-A"/);
  assert.match(inner, /Teaching Effectiveness/);
  assert.match(inner, /data-ws-criterion="kra-I-C"/);
});

test('breadcrumbs follow Assigned Faculty → faculty → KRA I → criterion', () => {
  const html = buildWorkspaceBreadcrumb({
    fac,
    folder: WS_FOLDER_CRITERION,
    criterionId: 'kra-I-A',
    catalog: ASSESSMENT_CATALOG,
  });
  assert.match(html, /Assigned Faculty/);
  assert.match(html, /Jason Baroro/);
  assert.match(html, /Teaching Effectiveness/);
  assert.doesNotMatch(html, /wsFolderContent/);
});

test('achievement review breadcrumb ends on achievement title', () => {
  const html = buildAchievementReviewBreadcrumb({
    fac,
    criterionId: 'kra-I-B',
    catalog: ASSESSMENT_CATALOG,
    achievementTitle: 'My textbook',
  });
  assert.match(html, /My textbook/);
  assert.match(html, /aria-current="page"/);
  assert.match(html, /Instructional Materials/);
});
