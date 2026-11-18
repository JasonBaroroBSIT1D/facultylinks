import { writeFileSync } from 'fs';
import { KRA_II_CRITERIA } from '../js/core/kra-ii-catalog.js';
import { KRA_III_CRITERIA } from '../js/core/kra-iii-catalog.js';
import { KRA_IV_CRITERIA } from '../js/core/kra-iv-catalog.js';
import { ASSESSMENT_CATALOG } from '../js/core/assessment-definitions.js';

const out = {};

function walk(criteria, kraId) {
  for (const c of criteria || []) {
    for (const i of c.indicators || []) {
      out[i.id] = {
        kraId,
        criterionId: c.id,
        name: i.name || '',
        fields: i.fields || [],
        type: i.type || '',
        role: i.role || '',
        calculationKind: (i.calculation && i.calculation.kind) || '',
        source: 'workbook_catalog_js',
      };
    }
  }
}

walk(KRA_II_CRITERIA, 'kra-II');
walk(KRA_III_CRITERIA, 'kra-III');
walk(KRA_IV_CRITERIA, 'kra-IV');

const kraI = (ASSESSMENT_CATALOG.kras || []).find((k) => k.id === 'kra-I');
if (kraI) walk(kraI.criteria, 'kra-I');

writeFileSync(
  new URL('../../backend/app/services/catalog_indicator_fields.json', import.meta.url),
  JSON.stringify({ version: 'workbook-fields-1.0', generatedFrom: 'admin_reviewer_web/js/core/*-catalog.js', indicators: out }, null, 2)
);
console.log('wrote', Object.keys(out).length, 'indicators');
