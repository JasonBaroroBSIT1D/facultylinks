/**
 * FacultyLink assessment catalog — DBM–CHED JC No. 3, s. 2022
 * Source: BONGCAWEL - JC3 Self Assessment.docx.xlsx (worksheet row refs in sourceRef)
 * Stable IDs shared with faculty_mobile.
 */
export const SOURCE_CIRCULAR =
  'Enhanced Implementing Guidelines of DBM-CHED Joint Circular No. 3, series of 2022';

export const KRA_WEIGHTS = {
  'kra-I': 0.6,
  'kra-II': 0.2,
  'kra-III': 0.1,
  'kra-IV': 0.1,
};

export const CONFIG_VERSION = '2022-jc3-demo-1';

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
              description: 'Average of six semester SET ratings across three academic years.',
              type: 'set_sef',
              subType: 'SET',
              fields: ['academicYear', 'semester', 'rating'],
              conditions: ['Six semesters across three selectable academic years.'],
              pointRule: 'raw = (sum of 6 ratings / 6) * 0.36',
            },
            {
              id: 'kra-I-A-sef',
              name: "Supervisor's Evaluation of Faculty (SEF)",
              maxPoints: 24,
              sourceRef: 'KRA I A8 B8; formula J12 = SUM(J10:O10)/6*24%',
              description: 'Average of six semester SEF ratings.',
              type: 'set_sef',
              subType: 'SEF',
              fields: ['academicYear', 'semester', 'rating'],
              pointRule: 'raw = (sum of 6 ratings / 6) * 0.24',
            },
            {
              id: 'kra-I-A-special',
              name: 'For Faculty with Special Status',
              maxPoints: null,
              sourceRef: 'KRA I A9–A13',
              description:
                'Official Study Leave, Maternity Leave, Sabbatical Leave, newly appointed, SUC lab schools — additional evidence per Enhanced Guidelines.',
              fields: ['specialStatus', 'notes'],
              conditions: ['Pending configuration for automatic point substitution.'],
              pointRule: 'pending',
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
      criteria: [
        {
          id: 'kra-II-A',
          name: 'Criterion A – Research Outputs Published',
          maxPoints: 100,
          capNote: 'Max = 100',
          indicators: [
            { id: 'kra-II-A-1', name: 'Sole Author of an Academic Book', maxPoints: 100, sourceRef: 'A7 B7' },
            { id: 'kra-II-A-2', name: 'Sole Author of Edited Academic Book Chapter', maxPoints: 35, sourceRef: 'A8 B8' },
            { id: 'kra-II-A-3', name: 'Sole Author of a Journal Article', maxPoints: 50, sourceRef: 'A9 B9' },
            { id: 'kra-II-A-4', name: 'Sole Author of Academic Monograph', maxPoints: 100, sourceRef: 'A10 B10' },
            { id: 'kra-II-A-5', name: 'Research Translated Into Project, Policy, or Product', maxPoints: 35, capNote: 'Max = 70 per activity tier', sourceRef: 'A11' },
            { id: 'kra-II-A-6', name: 'Research Publication Cited', maxPoints: 10, capNote: 'Max = 60', sourceRef: 'A12' },
          ],
        },
        {
          id: 'kra-II-B',
          name: 'Criterion B – Inventions',
          maxPoints: 100,
          capNote: 'Max = 100',
          indicators: [
            { id: 'kra-II-B-1-1', name: 'Invention Patent (A/P/G stages)', points: { A: 10, P: 20, G: 80 }, sourceRef: 'A15–B17' },
            { id: 'kra-II-B-1-2', name: 'Commercialized Patented Product', points: { local: 5, international: 10 }, capNote: 'Local max 20, Intl max 30', sourceRef: 'A18' },
            { id: 'kra-II-B-2-1', name: 'Copyrighted Software', points: { new: 10, updated: 4 }, sourceRef: 'A19' },
            { id: 'kra-II-B-2-2', name: 'New plant variety / animal breeds / microbial strains', maxPoints: 10, sourceRef: 'A20' },
          ],
        },
        {
          id: 'kra-II-C',
          name: 'Criterion C – Creative Works',
          maxPoints: 100,
          capNote: 'Max = 100',
          indicators: [
            { id: 'kra-II-C-1-1-1', name: 'Musical Composition', maxPoints: 20, sourceRef: 'A22' },
            { id: 'kra-II-C-1-1-2', name: 'Musical Arrangement', maxPoints: 20, sourceRef: 'A23' },
            { id: 'kra-II-C-1-1-3', name: 'Musical Performance', maxPoints: 10, sourceRef: 'A24' },
            { id: 'kra-II-C-1-1-4', name: 'Conducting', maxPoints: 10, sourceRef: 'A25' },
            { id: 'kra-II-C-1-1-5', name: 'Music Production', maxPoints: 20, sourceRef: 'A26' },
            { id: 'kra-II-C-1-2-1', name: 'Original Choreography', maxPoints: 20, sourceRef: 'A27' },
            { id: 'kra-II-C-1-2-2', name: 'Dance Performance', maxPoints: 10, sourceRef: 'A28' },
            { id: 'kra-II-C-1-3-1', name: 'Playwright', maxPoints: 20, sourceRef: 'A29' },
            { id: 'kra-II-C-1-3-2', name: 'Directing (Theatre)', maxPoints: 20, sourceRef: 'A30' },
            { id: 'kra-II-C-1-3-3', name: 'Acting', maxPoints: 20, sourceRef: 'A31' },
            { id: 'kra-II-C-1-3-4', name: 'Production Design', maxPoints: 20, sourceRef: 'A32' },
            { id: 'kra-II-C-1-2-visual', name: 'Visual Arts (Painting, Drawing, etc.)', maxPoints: 20, sourceRef: 'A33' },
            { id: 'kra-II-C-1-3-film', name: 'Film (short/feature/documentary/etc.)', maxPoints: 20, sourceRef: 'A35' },
            { id: 'kra-II-C-1-4-1', name: 'Novel', maxPoints: 20, sourceRef: 'A36' },
            { id: 'kra-II-C-1-4-2', name: 'Short story', maxPoints: 10, sourceRef: 'A37' },
            { id: 'kra-II-C-1-4-3', name: 'Poetry', maxPoints: 2, sourceRef: 'A38' },
            { id: 'kra-II-C-1-4-4', name: 'Literary Essay', maxPoints: 2, sourceRef: 'A39' },
          ],
        },
      ],
    },
    {
      id: 'kra-III',
      name: 'KRA III – Extension Services',
      maxPoints: 100,
      weight: KRA_WEIGHTS['kra-III'],
      scoreFormula: 'SUM(Criteria A+B+C+D) × 10%',
      criteria: [
        {
          id: 'kra-III-A',
          name: 'Criterion A – Service to the Institution',
          capNote: 'Max = 30',
          indicators: [
            { id: 'kra-III-A-1', name: 'Linkages / networking / partnership', maxPoints: 5, sourceRef: 'A7' },
            { id: 'kra-III-A-2', name: 'Income generation (Lead/Contributor tiers)', sourceRef: 'A8 B8 Sec.31', pointRule: 'tiered', fields: ['role', 'amount', 'tier'] },
          ],
        },
        {
          id: 'kra-III-B',
          name: 'Criterion B – Service to the Community',
          capNote: 'Max = 50',
          indicators: [
            { id: 'kra-III-B-1-1', name: 'QA accreditation/evaluation services', points: { local: 8, international: 10 }, sourceRef: 'A10' },
            { id: 'kra-III-B-1-2', name: 'Judge/Examiner awards & competitions', sourceRef: 'A11', points: { researchAward: 2, academicCompetition: 1 } },
            { id: 'kra-III-B-1-3', name: 'Short-term consultant/expert', points: { local: 8, international: 10 }, sourceRef: 'A12' },
            { id: 'kra-III-B-1-4-1', name: 'Occasional newspaper column', maxPoints: 2, capNote: 'max 10', sourceRef: 'A13' },
            { id: 'kra-III-B-1-4-2', name: 'Regular newspaper column', maxPoints: 10, sourceRef: 'A14' },
            { id: 'kra-III-B-1-4-3', name: 'Host TV/Radio Program', maxPoints: 10, sourceRef: 'A15' },
            { id: 'kra-III-B-1-4-4', name: 'Guest technical expert', maxPoints: 1, capNote: 'max 10', sourceRef: 'A16' },
            { id: 'kra-III-B-1-5', name: 'Training/seminar as resource person', points: { local: 2, international: 3 }, sourceRef: 'A17' },
            { id: 'kra-III-B-2-1', name: 'Extension Project (Lead/Participant)', points: { lead: 5, participant: 2 }, capNote: 'Max = 30 ISR', sourceRef: 'A19' },
          ],
        },
        {
          id: 'kra-III-C',
          name: 'Criterion C – Relevance and Quality of Extension Services',
          capNote: 'Max = 20',
          indicators: [
            {
              id: 'kra-III-C-1',
              name: 'Client Satisfaction Rating for Extension Projects',
              maxPoints: 20,
              sourceRef: 'A21 B21 F21',
              conditions: ['Must be declared under ISR in Criterion B.'],
              externalFormulaRef: '[1]Luthie!$P$21',
              pointRule: 'pending_external',
            },
          ],
        },
        {
          id: 'kra-III-D',
          name: 'Criterion D – Bonus Criterion for Administrative Designations',
          capNote: 'Max = 20',
          indicators: [
            { id: 'kra-III-D-1', name: 'Administrative Designation', sourceRef: 'A23 B23 Sec.36', pointRule: 'designation_table', unresolvedNote: 'CCIR Coordinator 1 or 2 points???' },
          ],
        },
      ],
    },
    {
      id: 'kra-IV',
      name: 'KRA IV – Professional Development',
      maxPoints: 100,
      weight: KRA_WEIGHTS['kra-IV'],
      scoreFormula: 'SUM(Criteria A+B+C+D) × 10%',
      criteria: [
        {
          id: 'kra-IV-A',
          name: 'Criterion A – Involvement in Professional Organizations',
          capNote: 'Max = 20',
          indicators: [{ id: 'kra-IV-A-1', name: 'Membership in Registered Professional Organizations', maxPoints: 5, sourceRef: 'A7 B7 Sec.38' }],
        },
        {
          id: 'kra-IV-B',
          name: 'Criterion B – Continuing Development',
          capNote: 'Max = 60',
          indicators: [
            { id: 'kra-IV-B-1', name: 'Educational Qualifications', points: { postMaster: 10, postDoc: 10, addtlMaster: 20, doctorate: 40 }, sourceRef: 'A9' },
            { id: 'kra-IV-B-2', name: 'Conference/seminar attendance', points: { local: 1, international: 2 }, capNote: 'Max = 10', sourceRef: 'A10' },
            { id: 'kra-IV-B-3-1', name: 'Paper presentation — Local', maxPoints: 3, capNote: 'Max = 10', sourceRef: 'A11' },
            { id: 'kra-IV-B-3-2', name: 'Paper presentation — International', maxPoints: 5, sourceRef: 'A12' },
          ],
        },
        {
          id: 'kra-IV-C',
          name: 'Criterion C – Awards and Recognition',
          capNote: 'Max = 20',
          indicators: [{ id: 'kra-IV-C-1', name: 'Award of distinction', points: { institutional: 2, localRegional: 3, national: 4 }, sourceRef: 'A14 Sec.43' }],
        },
        {
          id: 'kra-IV-D',
          name: 'Criterion D – Additional Points for Newly Appointed Faculty',
          capNote: 'Max = 20',
          indicators: [
            { id: 'kra-IV-D-1', name: 'Prior academic service', points: { president: 5, vpDean: 4, deptHead: 3, faculty: 2 }, sourceRef: 'A16', note: 'Proportionate months pending' },
            { id: 'kra-IV-D-2', name: 'Industry experience', points: { managerial: 4, technical: 3, support: 2 }, sourceRef: 'A17' },
          ],
        },
      ],
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
