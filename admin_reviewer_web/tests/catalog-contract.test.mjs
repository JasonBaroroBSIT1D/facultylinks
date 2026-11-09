import test from 'node:test';
import assert from 'node:assert/strict';
import { ConfigRepository } from '../js/repositories/config-repository.js';

test('lite portal meta without catalog body → catalog_not_loaded (not undefined)', () => {
  const store = {
    assessmentConfig: {
      activePublishedId: 'cfg-published-1',
      draftId: null,
      previewDraft: false,
      versions: [{ id: 'cfg-published-1', status: 'published', label: 'Published', kraWeights: { 'kra-I': 0.3 } }],
    },
    catalogPublished: null,
    assessments: {},
  };
  const rules = ConfigRepository.getCalculationCatalog(store, { facultyId: 'u-2' });
  assert.equal(rules.state, 'catalog_not_loaded');
  assert.equal(rules.catalog, null);
  assert.ok(rules.versionId);
});

test('hydrated published catalog → state ok', () => {
  const store = {
    assessmentConfig: {
      activePublishedId: 'cfg-published-1',
      versions: [
        {
          id: 'cfg-published-1',
          status: 'published',
          catalog: { kras: [{ id: 'kra-I', name: 'KRA I', criteria: [] }], version: 'v1' },
          kraWeights: { 'kra-I': 0.3 },
        },
      ],
    },
    assessments: {},
  };
  const rules = ConfigRepository.getCalculationCatalog(store);
  assert.equal(rules.state, 'ok');
  assert.equal(rules.catalog.kras.length, 1);
});

test('no published version → no_published', () => {
  const store = {
    assessmentConfig: { activePublishedId: null, versions: [] },
    assessments: {},
  };
  const rules = ConfigRepository.getCalculationCatalog(store);
  assert.equal(rules.state, 'no_published');
  assert.equal(rules.catalog, null);
});
