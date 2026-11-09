/**
 * KRA III — Extension Services (workbook rows 5–23).
 * @see docs/KRA_III_WORKBOOK_MAPPING.md
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

const SCOPE_TIER = (id, name, options, sourceRef, extra = {}) => ({
  id,
  name,
  sourceRef,
  selfAssessed: true,
  guidelinesRef: extra.guidelinesRef,
  calculation: {
    kind: 'tiered_option',
    options,
    tierField: 'serviceScope',
    ...extra.calculation,
  },
  fields: ['title', 'achievementDate', 'description', 'serviceScope', ...(extra.fields || [])],
  ...extra,
});

export const KRA_III_SCORING_POLICY = {
  coreCriteria: ['kra-III-A', 'kra-III-B', 'kra-III-C'],
  bonusCriterion: 'kra-III-D',
  coreMaxSum: 100,
  bonusMax: 20,
  applyKraEnvelopeCap: false,
  unresolvedNote:
    'Workbook B5 lists KRA max 100 while Criterion D allows bonus max 20 (B22). Confirm from Section 36 / implementing guidelines whether bonus stacks beyond the 100-point envelope.',
};

export const KRA_III_CRITERIA = [
  {
    id: 'kra-III-A',
    name: 'Criterion A – Service to the Institution',
    maxPoints: 30,
    capMaxPoints: 30,
    capNote: 'Max = 30',
    indicators: [
      FIXED('kra-III-A-1', 'Linkages / networking / partnership activity', 5, 'A7 B7', {
        guidelinesRef: 'Section 30',
      }),
      {
        id: 'kra-III-A-2',
        name: 'Income generation (Lead / Contributor tiers)',
        sourceRef: 'A8 B8 Sec.31',
        selfAssessed: true,
        guidelinesRef: 'Section 31',
        calculation: {
          kind: 'income_tier',
          tierField: 'incomeTier',
          amountField: 'incomeAmount',
          roleField: 'incomeRole',
          tiers: [
            { id: 't1', label: '100,000 and below', lead: 2, contributor: 1, resolved: true, maxAmount: 100000 },
            {
              id: 't2',
              label: '100,001 to 500,000',
              lead: 4,
              contributor: 2,
              resolved: true,
              minAmount: 100001,
              maxAmount: 500000,
            },
            {
              id: 't3',
              label: '500,000 to 6,000,0000 (workbook boundary ambiguous)',
              lead: 6,
              contributor: 3,
              resolved: false,
              workbookNote:
                'Workbook band text is malformed/overlapping — confirm amount boundaries in Section 31 before enabling this tier.',
            },
            {
              id: 't4',
              label: '6,000,001 to 12,000,000',
              lead: 12,
              contributor: 6,
              resolved: true,
              minAmount: 6000001,
              maxAmount: 12000000,
            },
            { id: 't5', label: 'Above 12,000,000', lead: 18, contributor: 9, resolved: true, minAmount: 12000001 },
          ],
        },
        fields: ['title', 'achievementDate', 'incomeRole', 'incomeAmount', 'incomeTier', 'description'],
      },
    ],
  },
  {
    id: 'kra-III-B',
    name: 'Criterion B – Service to the Community',
    maxPoints: 50,
    capMaxPoints: 50,
    capNote: 'Max = 50',
    indicators: [
      SCOPE_TIER('kra-III-B-1-1', 'Accreditation / evaluation / educational QA services', { local: 8, international: 10 }, 'A10', {
        guidelinesRef: 'Item 1.1, Section 33',
      }),
      {
        id: 'kra-III-B-1-2',
        name: 'Judge / examiner for research awards and academic competitions',
        sourceRef: 'A11',
        selfAssessed: true,
        guidelinesRef: 'Item 1.2, Section 33',
        calculation: {
          kind: 'tiered_option',
          options: { research_award: 2, academic_competition: 1 },
          tierField: 'judgeServiceType',
        },
        fields: ['title', 'achievementDate', 'judgeServiceType', 'description'],
      },
      SCOPE_TIER('kra-III-B-1-3', 'Short-term consultant / expert', { local: 8, international: 10 }, 'A12', {
        guidelinesRef: 'Item 1.3, Section 33',
      }),
      FIXED('kra-III-B-1-4-1', 'Occasional newspaper column', 2, 'A13', {
        aggregateCap: 10,
        capNote: 'max 10',
        calculation: { kind: 'fixed_per_entry', maxPoints: 2, aggregateCap: 10 },
        guidelinesRef: 'Item 1.4.1, Section 33',
      }),
      FIXED('kra-III-B-1-4-2', 'Regular newspaper column', 10, 'A14', { guidelinesRef: 'Item 1.4.2, Section 33' }),
      FIXED('kra-III-B-1-4-3', 'Host of TV/Radio program', 10, 'A15', { guidelinesRef: 'Item 1.4.3, Section 33' }),
      FIXED('kra-III-B-1-4-4', 'Guest technical expert (media)', 1, 'A16', {
        aggregateCap: 10,
        capNote: 'max 10',
        calculation: { kind: 'fixed_per_entry', maxPoints: 1, aggregateCap: 10 },
        guidelinesRef: 'Item 1.4.4, Section 33',
      }),
      {
        id: 'kra-III-B-1-5',
        name: 'Training / seminar / workshop conducted (resource person)',
        sourceRef: 'A17',
        selfAssessed: true,
        guidelinesRef: 'Item 1.5, Section 33',
        calculation: {
          kind: 'hourly_tier',
          tierField: 'serviceScope',
          hoursField: 'hours',
          rates: { local: 2, international: 3 },
        },
        fields: ['title', 'achievementDate', 'serviceScope', 'hours', 'description'],
      },
      {
        id: 'kra-III-B-2-1',
        name: 'Institutional Social Responsibility — extension project activity',
        sourceRef: 'A18–B19',
        selfAssessed: true,
        aggregateCap: 30,
        capNote: 'Max = 30 ISR',
        guidelinesRef: 'Section 34',
        calculation: {
          kind: 'tiered_option',
          options: { lead: 5, participant: 2 },
          tierField: 'extensionRole',
          aggregateCap: 30,
        },
        fields: ['title', 'achievementDate', 'extensionRole', 'description', 'projectPeriod'],
      },
    ],
  },
  {
    id: 'kra-III-C',
    name: 'Criterion C – Relevance and Quality of Extension Services',
    maxPoints: 20,
    capMaxPoints: 20,
    capNote: 'Max = 20',
    indicators: [
      {
        id: 'kra-III-C-1',
        name: 'Client Satisfaction Rating for Extension Projects',
        maxPoints: 20,
        sourceRef: 'A21 B21 F21',
        selfAssessed: true,
        guidelinesRef: 'Section 35',
        externalFormulaRef: '[1]Luthie!$P$21',
        calculation: {
          kind: 'pending',
          requiresLinkedAchievement: {
            indicatorId: 'kra-III-B-2-1',
            linkField: 'linkedIsrProjectId',
          },
        },
        eligibilityUnresolved:
          'Satisfaction-to-points conversion is not defined in workbook rows 5–23. Project must be declared under ISR (kra-III-B-2-1) via linked achievement id.',
        fields: ['title', 'achievementDate', 'linkedIsrProjectId', 'clientSatisfactionRating', 'description'],
      },
    ],
  },
  {
    id: 'kra-III-D',
    name: 'Criterion D – Bonus Criterion for Administrative Designations',
    maxPoints: 20,
    capMaxPoints: 20,
    capNote: 'Max = 20',
    isBonusCriterion: true,
    indicators: [
      {
        id: 'kra-III-D-1',
        name: 'Administrative designation',
        sourceRef: 'A23 B23 Sec.36',
        selfAssessed: true,
        guidelinesRef: 'Section 36',
        eligibilityUnresolved:
          'Workbook note G23: “CCIR Coordinator 1 or 2 points???” — confirm coordinator rate before scoring that role.',
        calculation: {
          kind: 'designation_matrix',
          levelField: 'designationLevel',
          roleField: 'designationRole',
          matrix: {
            institutional: {
              president: 20,
              vice_president: 15,
              chancellor: 10,
              vice_chancellor: 8,
              campus_director: 8,
              faculty_trustee: 8,
              office_director: 6,
              university_secretary: 6,
              project_head: 4,
              inst_committee_chair: 3,
              inst_committee_member: 2,
              inst_coordinator: 2,
            },
            college_department: {
              dean: 6,
              associate_dean: 5,
              college_secretary: 3,
              department_head: 4,
              program_chair: 3,
              dept_committee_chair: 2,
              dept_committee_member: 1,
              dept_coordinator: 1,
            },
          },
        },
        fields: ['title', 'achievementDate', 'designationLevel', 'designationRole', 'description'],
      },
    ],
  },
];
