/**
 * KRA IV — Professional Development (workbook rows 5–17).
 * @see docs/KRA_IV_WORKBOOK_MAPPING.md
 */

const FIXED = (id, name, maxPoints, sourceRef, extra = {}) => ({
  id,
  name,
  maxPoints,
  sourceRef,
  selfAssessed: true,
  calculation: { kind: 'fixed_per_entry', maxPoints, ...(extra.calculation || {}) },
  fields: ['title', 'achievementDate', 'description', ...(extra.fields || [])],
  ...extra,
});

const TIERED = (id, name, options, tierField, sourceRef, extra = {}) => ({
  id,
  name,
  sourceRef,
  selfAssessed: true,
  guidelinesRef: extra.guidelinesRef,
  calculation: {
    kind: 'tiered_option',
    options,
    tierField,
    aggregateCap: extra.aggregateCap,
    aggregateGroup: extra.aggregateGroup,
    ...extra.calculation,
  },
  fields: ['title', 'achievementDate', 'description', tierField, ...(extra.fields || [])],
  ...extra,
});

export const KRA_IV_SCORING_POLICY = {
  coreCriteria: ['kra-IV-A', 'kra-IV-B', 'kra-IV-C'],
  additionalCriteria: ['kra-IV-D'],
  coreMaxSum: 100,
  additionalMax: 20,
  kraListedMax: 100,
  applyKraEnvelopeCap: false,
  unresolvedNote:
    'Workbook B5 lists KRA max 100 while F5 sums Criteria A+B+C+D (up to 120 raw) before ×10%. Confirm whether D stacks beyond the 100-point envelope or replaces a portion of it.',
};

export const KRA_IV_CRITERIA = [
  {
    id: 'kra-IV-A',
    name: 'Criterion A – Involvement in Professional Organizations',
    maxPoints: 20,
    capMaxPoints: 20,
    capNote: 'Max = 20',
    indicators: [
      FIXED('kra-IV-A-1', 'Membership and participation in registered professional organizations', 5, 'A7 B7', {
        guidelinesRef: 'Section 38',
        eligibilityUnresolved:
          'Registered professional organization / society membership must be verified per Section 38.',
      }),
    ],
  },
  {
    id: 'kra-IV-B',
    name: 'Criterion B – Continuing Development',
    maxPoints: 60,
    capMaxPoints: 60,
    capNote: 'Max = 60',
    indicators: [
      TIERED(
        'kra-IV-B-1',
        'Educational qualifications',
        {
          post_master_diploma: 10,
          post_doctorate_diploma: 10,
          additional_masters: 20,
          doctorate: 40,
        },
        'qualificationType',
        'A9 B9',
        {
          guidelinesRef: 'Section 40',
          eligibilityUnresolved:
            'Section 40 eligibility for post-master, post-doctorate, additional master’s, and doctorate credentials must be confirmed before points are final.',
        }
      ),
      TIERED(
        'kra-IV-B-2',
        'Conference, seminar, workshop, or industry immersion attendance',
        { local: 1, international: 2 },
        'attendanceScope',
        'A10 B10',
        {
          guidelinesRef: 'Section 41',
          aggregateCap: 10,
          capNote: 'Max = 10 combined (local + international)',
        }
      ),
      {
        id: 'kra-IV-B-3-1',
        name: 'Paper presentation — local',
        sourceRef: 'A11 B11',
        selfAssessed: true,
        guidelinesRef: 'Section 42',
        maxPoints: 3,
        capNote: 'Max = 10 combined presentations',
        calculation: {
          kind: 'fixed_per_entry',
          maxPoints: 3,
          aggregateGroup: 'kra-IV-B-presentations',
          aggregateCap: 10,
        },
        fields: ['title', 'achievementDate', 'presentationScope', 'description'],
      },
      {
        id: 'kra-IV-B-3-2',
        name: 'Paper presentation — international',
        sourceRef: 'A12 B12',
        selfAssessed: true,
        guidelinesRef: 'Section 42',
        maxPoints: 5,
        calculation: {
          kind: 'fixed_per_entry',
          maxPoints: 5,
          aggregateGroup: 'kra-IV-B-presentations',
          aggregateCap: 10,
        },
        fields: ['title', 'achievementDate', 'presentationScope', 'description'],
      },
    ],
  },
  {
    id: 'kra-IV-C',
    name: 'Criterion C – Awards and Recognition',
    maxPoints: 20,
    capMaxPoints: 20,
    capNote: 'Max = 20',
    indicators: [
      TIERED(
        'kra-IV-C-1',
        'Award of distinction',
        { institutional: 2, local_regional: 3, national: 4 },
        'awardLevel',
        'A14 B14',
        { guidelinesRef: 'Section 43' }
      ),
    ],
  },
  {
    id: 'kra-IV-D',
    name: 'Criterion D – Additional Points for Newly Appointed Faculty',
    maxPoints: 20,
    capMaxPoints: 20,
    capNote: 'Max = 20',
    isAdditionalCriterion: true,
    eligibilityUnresolved:
      'Criterion D applies only to newly appointed faculty per workbook row 15. Faculty must attest eligibility; institution confirms.',
    indicators: [
      {
        id: 'kra-IV-D-1',
        name: 'Full-time academic service in higher education',
        sourceRef: 'A16 B16',
        selfAssessed: true,
        guidelinesRef: 'Section 44',
        calculation: {
          kind: 'yearly_rate',
          roleField: 'academicServiceRole',
          yearsField: 'serviceYears',
          requiresNewlyAppointed: true,
          newlyAppointedField: 'newlyAppointedEligible',
          fractionalYearPolicy: 'unresolved',
          fractionalYearNote:
            'Workbook F16 comment allows proportionate months; policy not in column B — admin must publish before fractional years score.',
          rates: {
            president: 5,
            vp_dean_director: 4,
            dept_program_head: 3,
            faculty_member: 2,
          },
        },
        fields: [
          'title',
          'achievementDate',
          'newlyAppointedEligible',
          'academicServiceRole',
          'serviceYears',
          'description',
        ],
      },
      {
        id: 'kra-IV-D-2',
        name: 'Industry experience (non-academic organization)',
        sourceRef: 'A17 B17',
        selfAssessed: true,
        guidelinesRef: 'Section 44',
        calculation: {
          kind: 'yearly_rate',
          roleField: 'industryCategory',
          yearsField: 'serviceYears',
          requiresNewlyAppointed: true,
          newlyAppointedField: 'newlyAppointedEligible',
          fractionalYearPolicy: 'unresolved',
          fractionalYearNote:
            'Fractional-year and multiple simultaneous roles (workbook F17 comment) are not defined in column B.',
          rates: {
            managerial_supervisory: 4,
            technical_skilled: 3,
            support_admin: 2,
          },
        },
        fields: [
          'title',
          'achievementDate',
          'newlyAppointedEligible',
          'industryCategory',
          'serviceYears',
          'description',
        ],
      },
    ],
  },
];
