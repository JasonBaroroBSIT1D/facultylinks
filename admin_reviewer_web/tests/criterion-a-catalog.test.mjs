import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ASSESSMENT_CATALOG,
  isSupportingEvidenceIndicator,
  scoringIndicatorsForCriterion,
} from '../js/core/assessment-definitions.js';
import {
  buildSeedCatalog,
  mergeWorkbookReferenceIntoCatalog,
  reconcileSupportingEvidenceIndicator,
} from '../js/repositories/config-repository.js';

test('reference Criterion A has exactly 3 scoring indicators', () => {
  const crit = ASSESSMENT_CATALOG.kras
    .find((k) => k.id === 'kra-I')
    .criteria.find((c) => c.id === 'kra-I-A');
  const scoring = scoringIndicatorsForCriterion(crit);
  assert.equal(scoring.length, 3);
  assert.deepEqual(
    scoring.map((i) => i.id),
    ['kra-I-A-set', 'kra-I-A-sef', 'kra-I-A-special']
  );
  const special = scoring.find((i) => i.id === 'kra-I-A-special');
  assert.ok(isSupportingEvidenceIndicator(special));
  assert.equal(special.calculation?.kind, 'supporting_evidence');
  assert.equal(special.pointRule, undefined);
});

test('workbook merge adds intake aliases without re-adding PDF scoring rows', () => {
  const seed = buildSeedCatalog();
  const crit = seed.kras.find((k) => k.id === 'kra-I').criteria.find((c) => c.id === 'kra-I-A');
  assert.equal(scoringIndicatorsForCriterion(crit).length, 3);

  const legacy = {
    version: seed.version,
    kras: [
      {
        id: 'kra-I',
        name: 'KRA I',
        criteria: [
          {
            id: 'kra-I-A',
            name: 'Criterion A',
            indicators: [
              { id: 'kra-I-A-setsef-eval', name: 'PDF', type: 'set_sef_unified_pdf' },
              { id: 'kra-I-A-set', name: 'SET', type: 'set_sef', subType: 'SET', maxPoints: 36 },
              { id: 'kra-I-A-sef', name: 'SEF', type: 'set_sef', subType: 'SEF', maxPoints: 24 },
              { id: 'kra-I-A-special', name: 'Special', maxPoints: null },
            ],
          },
        ],
      },
    ],
  };
  const { catalog } = mergeWorkbookReferenceIntoCatalog(legacy);
  const mergedCrit = catalog.kras[0].criteria[0];
  assert.equal(scoringIndicatorsForCriterion(mergedCrit).length, 3);
  assert.ok(Array.isArray(catalog.documentIntakeAliases));
  assert.ok(catalog.documentIntakeAliases.some((a) => a.id === 'kra-I-A-setsef-eval'));
  const special = mergedCrit.indicators.find((i) => i.id === 'kra-I-A-special');
  assert.ok(isSupportingEvidenceIndicator(special));
  assert.equal(special.calculation?.kind, 'supporting_evidence');
});

test('legacy pending special status reconciles to supporting evidence', () => {
  const legacy = {
    id: 'kra-I-A-special',
    name: 'Special',
    pointRule: 'pending',
    calculation: { kind: 'pending' },
    conditions: ['Pending configuration for automatic point substitution.'],
  };
  assert.ok(reconcileSupportingEvidenceIndicator(legacy));
  assert.equal(legacy.calculation.kind, 'supporting_evidence');
  assert.equal(legacy.pointRule, undefined);
  assert.ok(Array.isArray(legacy.specialStatusCategories));
  assert.ok(!legacy.conditions.some((c) => /pending configuration/i.test(c)));
});
