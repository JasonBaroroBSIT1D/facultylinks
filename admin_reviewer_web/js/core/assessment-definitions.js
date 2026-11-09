/**
 * FacultyLink assessment catalog — DBM–CHED JC No. 3, s. 2022
 * Source: BONGCAWEL - JC3 Self Assessment.docx.xlsx (worksheet row refs in sourceRef)
 * Stable IDs shared with faculty_mobile.
 */
import { KRA_II_CRITERIA } from './kra-ii-catalog.js';
import { KRA_III_CRITERIA, KRA_III_SCORING_POLICY } from './kra-iii-catalog.js';
import { KRA_IV_CRITERIA, KRA_IV_SCORING_POLICY } from './kra-iv-catalog.js';

export const SOURCE_CIRCULAR =
  'Enhanced Implementing Guidelines of DBM-CHED Joint Circular No. 3, series of 2022';

export const KRA_WEIGHTS = {
  'kra-I': 0.6,
  'kra-II': 0.2,
  'kra-III': 0.1,
  'kra-IV': 0.1,
};

export const CONFIG_VERSION = '2022-jc3-demo-1';

/** PDF upload routes — not shown in the Criterion A scoring editor (intake compatibility only). */
export const SET_SEF_DOCUMENT_INTAKE_IDS = [
  'kra-I-A-setsef-eval',
  'kra-I-A-setsef-combined',
  'kra-I-A-set-pdf',
  'kra-I-A-sef-pdf',
];

export const SET_SEF_DOCUMENT_INTAKE_ALIASES = [
  {
    id: 'kra-I-A-setsef-eval',
    name: 'SET / SEF Evaluation (PDF)',
    maxPoints: 60,
    description:
      'One evaluation PDF. OCR detects SET, SEF, or both from content; reviewers verify extracted semester ratings.',
    type: 'set_sef_unified_pdf',
    fields: ['pdf'],
    conditions: ['PDF only; one or more semesters per file.'],
    pointRule: 'Routes to SET and SEF scoring components (no separate Criterion A line).',
    kraId: 'kra-I',
    criterionId: 'kra-I-A',
    intakeOnly: true,
  },
  {
    id: 'kra-I-A-setsef-combined',
    name: 'Combined SET–SEF PDF',
    maxPoints: 60,
    description: 'Legacy combined PDF upload.',
    type: 'set_sef_combined_pdf',
    fields: ['pdf'],
    conditions: ['PDF only; up to six semester slots.'],
    pointRule: 'Intake alias for existing documents.',
    kraId: 'kra-I',
    criterionId: 'kra-I-A',
    intakeOnly: true,
  },
  {
    id: 'kra-I-A-set-pdf',
    name: 'SET PDF (OCR)',
    maxPoints: 36,
    description: 'Legacy SET-only PDF upload.',
    type: 'set_sef_set_pdf',
    fields: ['pdf'],
    conditions: ['PDF only; one or more semesters per file.'],
    pointRule: 'Intake alias for existing documents.',
    kraId: 'kra-I',
    criterionId: 'kra-I-A',
    intakeOnly: true,
  },
  {
    id: 'kra-I-A-sef-pdf',
    name: 'SEF PDF (OCR)',
    maxPoints: 24,
    description: 'Legacy SEF-only PDF upload.',
    type: 'set_sef_sef_pdf',
    fields: ['pdf'],
    conditions: ['PDF only; one or more semesters per file.'],
    pointRule: 'Intake alias for existing documents.',
    kraId: 'kra-I',
    criterionId: 'kra-I-A',
    intakeOnly: true,
  },
];

const INTAKE_PDF_TYPES = new Set([
  'set_sef_unified_pdf',
  'set_sef_combined_pdf',
  'set_sef_set_pdf',
  'set_sef_sef_pdf',
]);

export const SUPPORTING_EVIDENCE_INDICATOR_ID = 'kra-I-A-special';

export const DEFAULT_SPECIAL_STATUS_CATEGORIES = [
  'Official Study Leave',
  'Maternity Leave',
  'Sabbatical Leave',
  'Newly appointed faculty',
  'SUC laboratory school assignment',
];

export function isDocumentIntakeIndicator(ind) {
  if (!ind) return false;
  if (SET_SEF_DOCUMENT_INTAKE_IDS.includes(ind.id)) return true;
  return INTAKE_PDF_TYPES.has(ind.type);
}

/** Supporting documentation only — not independently scored. */
export function isSupportingEvidenceIndicator(ind) {
  if (!ind) return false;
  if (ind.id === SUPPORTING_EVIDENCE_INDICATOR_ID) return true;
  if (ind.role === 'supporting_evidence') return true;
  return ind.calculation?.kind === 'supporting_evidence';
}

/** Indicators shown in the admin scoring editor for a criterion. */
export function scoringIndicatorsForCriterion(crit) {
  if (!crit?.indicators) return [];
  if (crit.id !== 'kra-I-A') return crit.indicators;
  return crit.indicators.filter((ind) => !isDocumentIntakeIndicator(ind));
}

/** @type {import('../models/types.js').AssessmentCatalog} */
export const ASSESSMENT_CATALOG = {
  version: CONFIG_VERSION,
  source: SOURCE_CIRCULAR,
  kras: [
    {
      id: 'kra-I',
      name: 'KRA I – Instruction',
      maxPoints: 100,
      weight: KRA_WEIGHTS['kra-I'],
      sourceRef: "Luthie KRA Score B8; 'KRA I - Instruction' A5",
      scoreFormula: 'SUM(Criterion A+B+C raw) × 60%',
      criteria: [
        {
          id: 'kra-I-A',
          name: 'Criterion A – Teaching Effectiveness',
          maxPoints: 60,
          sourceRef: "'KRA I - Instruction' A6 B6",
          indicators: [
            {
              id: 'kra-I-A-set',
              name: 'Student Evaluation of Teachers (SET)',
              maxPoints: 36,
              sourceRef: 'KRA I A7 B7; formula J11 = SUM(J9:O9)/6*36%',
              description:
                'Average of available eligible SET ratings (up to six shared semester slots) × SET factor.',
              type: 'set_sef',
              subType: 'SET',
              fields: ['academicYear', 'semester', 'rating'],
              conditions: [
                'Up to six distinct semester slots (shared with SEF) in the assessment window.',
                'Average available eligible ratings; missing semesters do not force zero.',
              ],
              pointRule: 'avg(available SET ratings) × 0.36 (max 36 pts)',
            },
            {
              id: 'kra-I-A-sef',
              name: "Supervisor's Evaluation of Faculty (SEF)",
              maxPoints: 24,
              sourceRef: 'KRA I A8 B8; formula J12 = SUM(J10:O10)/6*24%',
              description:
                'Average of available eligible SEF ratings (up to six shared semester slots) × SEF factor.',
              type: 'set_sef',
              subType: 'SEF',
              fields: ['academicYear', 'semester', 'rating'],
              conditions: [
                'Up to six distinct semester slots (shared with SET) in the assessment window.',
                'Average available eligible ratings; missing semesters do not force zero.',
              ],
              pointRule: 'avg(available SEF ratings) × 0.24 (max 24 pts)',
            },
            {
              id: 'kra-I-A-special',
              name: 'For Faculty with Special Status',
              role: 'supporting_evidence',
              maxPoints: null,
              sourceRef: 'KRA I A9–A13',
              description:
                'Upload supporting documents when an official special circumstance applies. Reviewer validates applicability; this does not change SET/SEF calculations automatically.',
              fields: ['specialStatus', 'notes'],
              specialStatusCategories: [
                'Official Study Leave',
                'Maternity Leave',
                'Sabbatical Leave',
                'Newly appointed faculty',
                'SUC laboratory school assignment',
              ],
              conditions: [
                'Select the category that applies and upload supporting documents per Enhanced Guidelines.',
                'Reviewer confirms status and remarks; no automatic points or SET/SEF exemptions.',
              ],
              documentaryRequirements: ['Supporting documentation for the selected special status category.'],
              calculation: { kind: 'supporting_evidence' },
            },
          ],
        },
        {
          id: 'kra-I-B',
          name: 'Criterion B – Instructional Materials Development',
          maxPoints: 30,
          capNote: 'Max = 30 (criterion)',
          sourceRef: "'KRA I - Instruction' A14 B14",
          indicators: [
            { id: 'kra-I-B-1-1', name: 'Sole Author of a Textbook', maxPoints: 30, sourceRef: 'A16 B16', sectionRef: 'Sec. 12–13 Item 1', fields: ['title', 'date', 'role', 'authorship'] },
            { id: 'kra-I-B-1-2', name: 'Sole Author of a Module', maxPoints: 16, sourceRef: 'A17 B17', fields: ['title', 'date'] },
            { id: 'kra-I-B-1-3', name: 'Sole Author of Instructional Manual', maxPoints: 16, sourceRef: 'A18 B18', fields: ['title', 'date'] },
            { id: 'kra-I-B-1-4', name: 'Sole Author of Multimedia Teaching Materials', maxPoints: 16, sourceRef: 'A19 B19', fields: ['title', 'date'] },
            { id: 'kra-I-B-2', name: 'Academic Programs Developed/Revised (Lead / Contributor)', maxPoints: 10, contributorPoints: 5, sourceRef: 'A20 B20 Sec.14', fields: ['title', 'role', 'date'] },
          ],
        },
        {
          id: 'kra-I-C',
          name: 'Criterion C – Research Advising and Mentorship Services',
          maxPoints: 10,
          capNote: 'Max = 10',
          sourceRef: 'A21–A27',
          indicators: [
            {
              id: 'kra-I-C-1',
              name: 'Research-Related Services (Adviser / Panel)',
              maxPoints: 10,
              sourceRef: 'A22 B22–B26',
              matrix: {
                adviser: { SP_CP: 3, UT: 5, MT: 8, DD: 10 },
                panel: { SP_CP: 1, UT: 1, MT: 2, DD: 2 },
              },
              fields: ['thesisType', 'role', 'title', 'quantity', 'date'],
            },
            { id: 'kra-I-C-2', name: 'Mentorship Services', maxPoints: 3, perService: 3, sourceRef: 'A27 B27', fields: ['title', 'duration', 'date'] },
          ],
        },
      ],
    },
    {
      id: 'kra-II',
      name: 'KRA II – Research, Innovation and/or Creative Work',
      maxPoints: 100,
      weight: KRA_WEIGHTS['kra-II'],
      scoreFormula: 'SUM(Criteria A+B+C) × 20%',
      criteria: KRA_II_CRITERIA,
    },
    {
      id: 'kra-III',
      name: 'KRA III – Extension Services',
      maxPoints: 100,
      weight: KRA_WEIGHTS['kra-III'],
      scoreFormula: 'SUM(Criteria A+B+C+D) × 10%',
      scoringPolicy: KRA_III_SCORING_POLICY,
      criteria: KRA_III_CRITERIA,
    },
    {
      id: 'kra-IV',
      name: 'KRA IV – Professional Development',
      maxPoints: 100,
      weight: KRA_WEIGHTS['kra-IV'],
      scoreFormula: 'SUM(Criteria A+B+C+D) × 10%',
      scoringPolicy: KRA_IV_SCORING_POLICY,
      criteria: KRA_IV_CRITERIA,
    },
  ],
};

export function findIndicator(indicatorId) {
  for (const kra of ASSESSMENT_CATALOG.kras) {
    for (const crit of kra.criteria) {
      const ind = crit.indicators.find((i) => i.id === indicatorId);
      if (ind) return { kra, crit, ind };
    }
  }
  return null;
}

export function flattenIndicators() {
  const list = [];
  for (const kra of ASSESSMENT_CATALOG.kras) {
    for (const crit of kra.criteria) {
      for (const ind of crit.indicators) {
        list.push({ kraId: kra.id, criterionId: crit.id, ...ind });
      }
    }
  }
  return list;
}
