/**
 * KRA II criteria/indicators — traced to workbook sheet "KRA II - Research & Innovation".
 * @see docs/KRA_II_WORKBOOK_MAPPING.md
 */

const FIXED = (id, name, maxPoints, sourceRef, extra = {}) => ({
  id,
  name,
  maxPoints,
  sourceRef,
  selfAssessed: true,
  calculation: { kind: 'fixed_per_entry', maxPoints },
  fields: ['title', 'achievementDate', 'description', 'authorRole', 'publicationIdentifier'],
  ...extra,
});

export const KRA_II_CRITERIA = [
  {
    id: 'kra-II-A',
    name: 'Criterion A – Research Outputs Published',
    maxPoints: 100,
    capMaxPoints: 100,
    capNote: 'Max = 100',
    indicators: [
      FIXED('kra-II-A-1', 'Sole Author of an Academic Book', 100, 'A7 B7', {
        guidelinesRef: 'Section 18; Item 1 Section 19',
      }),
      FIXED('kra-II-A-2', 'Sole Author of Edited Academic Book Chapter', 35, 'A8 B8', {
        guidelinesRef: 'Section 18; Item 2 Section 19',
      }),
      FIXED('kra-II-A-3', 'Sole Author of a Journal Article', 50, 'A9 B9', {
        guidelinesRef: 'Section 18; Item 3 Section 19',
      }),
      FIXED('kra-II-A-4', 'Sole Author of Academic Monograph', 100, 'A10 B10', {
        guidelinesRef: 'Section 18; Item 4 Section 19',
      }),
      {
        id: 'kra-II-A-5',
        name: 'Research Outputs Translated Into Project, Policy, or Product',
        maxPoints: 35,
        aggregateCap: 70,
        capNote: 'Max = 70',
        sourceRef: 'A11',
        selfAssessed: true,
        guidelinesRef: 'Section 20; item 4(d) examples',
        eligibilityUnresolved:
          'Workbook lists 35 pts with max 70; Section 20 conditions are not automated — reviewer confirms eligibility.',
        calculation: { kind: 'fixed_per_entry', maxPoints: 35, aggregateCap: 70 },
        fields: ['title', 'achievementDate', 'description', 'translationOutcome'],
      },
      {
        id: 'kra-II-A-6',
        name: 'Research Publication Cited',
        maxPoints: 10,
        aggregateCap: 60,
        capNote: 'Max = 60',
        sourceRef: 'A12',
        selfAssessed: true,
        guidelinesRef: 'Section 21',
        eligibilityUnresolved: 'Citation qualification per Section 21 is not automated.',
        calculation: { kind: 'fixed_per_entry', maxPoints: 10, aggregateCap: 60 },
        fields: ['title', 'achievementDate', 'citingWork', 'citationContext'],
      },
    ],
  },
  {
    id: 'kra-II-B',
    name: 'Criterion B – Inventions',
    maxPoints: 100,
    capMaxPoints: 100,
    capNote: 'Max = 100',
    indicators: [
      {
        id: 'kra-II-B-1-1',
        name: 'Invention Patent (per highest patenting stage claimed)',
        sourceRef: 'A15–B17',
        selfAssessed: true,
        guidelinesRef: 'Item 1, Section 23',
        calculation: {
          kind: 'patent_stage',
          stages: { A: 10, P: 20, G: 80 },
          notCumulative: true,
        },
        fields: ['title', 'patentStage', 'patentNumber', 'achievementDate'],
      },
      {
        id: 'kra-II-B-1-2',
        name: 'Commercialized Patented Product',
        sourceRef: 'A18',
        selfAssessed: true,
        guidelinesRef: 'Item 2, Section 23',
        calculation: {
          kind: 'tiered_option',
          options: { local: 5, international: 10 },
          tierCaps: { local: 20, international: 30 },
          tierField: 'commercializationScope',
        },
        fields: ['title', 'commercializationScope', 'achievementDate', 'productName'],
      },
      {
        id: 'kra-II-B-2-1',
        name: 'Copyrighted and Utilized Software',
        sourceRef: 'A19',
        selfAssessed: true,
        guidelinesRef: 'Item 1, Section 24',
        calculation: {
          kind: 'tiered_option',
          options: { new: 10, updated: 4 },
          tierField: 'softwareVersionType',
        },
        fields: ['title', 'softwareVersionType', 'achievementDate', 'softwareTitle'],
      },
      FIXED('kra-II-B-2-2', 'New plant variety / animal breed / microbial strain', 10, 'A20', {
        guidelinesRef: 'Item 2, Section 24',
      }),
    ],
  },
  {
    id: 'kra-II-C',
    name: 'Criterion C – Creative Works',
    maxPoints: 100,
    capMaxPoints: 100,
    capNote: 'Max = 100',
    indicators: [
      FIXED('kra-II-C-1-1-1', 'Musical Composition', 20, 'A22'),
      FIXED('kra-II-C-1-1-2', 'Musical Arrangement', 20, 'A23'),
      FIXED('kra-II-C-1-1-3', 'Musical Performance', 10, 'A24'),
      FIXED('kra-II-C-1-1-4', 'Conducting', 10, 'A25'),
      FIXED('kra-II-C-1-1-5', 'Music Production', 20, 'A26'),
      FIXED('kra-II-C-1-2-1', 'Original Choreography', 20, 'A27'),
      FIXED('kra-II-C-1-2-2', 'Dance Performance', 10, 'A28'),
      FIXED('kra-II-C-1-3-1', 'Playwright', 20, 'A29'),
      FIXED('kra-II-C-1-3-2', 'Directing (Theatre)', 20, 'A30'),
      FIXED('kra-II-C-1-3-3', 'Acting', 20, 'A31'),
      FIXED('kra-II-C-1-3-4', 'Production Design', 20, 'A32'),
      FIXED('kra-II-C-1-2-visual', 'Visual Arts (painting, drawing, mixed media, sculpture, photography, digital art)', 20, 'A33'),
      {
        id: 'kra-II-C-1-2-design',
        name: 'Architectural / Engineering / Interior Design',
        sourceRef: 'A34',
        selfAssessed: true,
        pointRule: 'unresolved_workbook',
        calculation: { kind: 'pending' },
        unresolved:
          'Workbook row A34 lists categories but no points in column B — do not infer rate from neighbours.',
        fields: ['title', 'achievementDate', 'designType', 'description'],
      },
      FIXED('kra-II-C-1-3-film', 'Film (short, feature, documentary, experimental video, animation)', 20, 'A35'),
      FIXED('kra-II-C-1-4-1', 'Novel', 20, 'A36'),
      FIXED('kra-II-C-1-4-2', 'Short story', 10, 'A37'),
      FIXED('kra-II-C-1-4-3', 'Poetry', 2, 'A38'),
      FIXED('kra-II-C-1-4-4', 'Literary Essay', 2, 'A39'),
    ],
  },
];
