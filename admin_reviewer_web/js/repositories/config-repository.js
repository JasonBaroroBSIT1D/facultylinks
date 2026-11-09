import {
  ASSESSMENT_CATALOG,
  DEFAULT_SPECIAL_STATUS_CATEGORIES,
  KRA_WEIGHTS,
  SET_SEF_DOCUMENT_INTAKE_ALIASES,
  SOURCE_CIRCULAR,
  isDocumentIntakeIndicator,
  isSupportingEvidenceIndicator,
} from '../core/assessment-definitions.js';

const SOURCE_SEED_TAG = 'dbm-jc3-workbook-seed';

export const OFFICIAL_KRA_IDS = ['kra-I', 'kra-II', 'kra-III', 'kra-IV'];

function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function normalizeIndicator(ind) {
  return {
    documentaryRequirements: [],
    conditions: ind.conditions || (ind.conditions === undefined ? [] : []),
    description: ind.description || '',
    calculation: inferCalculation(ind),
    contributionAllocation: ind.contributionAllocation || {
      mode: ind.contributorPoints != null ? 'lead_contributor' : 'percent',
      defaultPercent: 100,
      leadPoints: ind.maxPoints ?? null,
      contributorPoints: ind.contributorPoints ?? null,
    },
    ...ind,
    conditions: Array.isArray(ind.conditions) ? ind.conditions : ind.conditions ? [String(ind.conditions)] : [],
    documentaryRequirements: ind.documentaryRequirements || [],
  };
}

function inferCalculation(ind) {
  if (isSupportingEvidenceIndicator(ind)) return { kind: 'supporting_evidence' };
  if (ind.calculation?.kind === 'supporting_evidence') return ind.calculation;
  if (ind.id === 'kra-III-D-1' && (!ind.calculation || ind.calculation.kind === 'pending')) {
    return {
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
    };
  }
  if (ind.id === 'kra-III-C-1' && ind.calculation?.kind === 'pending') {
    return {
      kind: 'pending',
      requiresLinkedAchievement: { indicatorId: 'kra-III-B-2-1', linkField: 'linkedIsrProjectId' },
    };
  }
  if (ind.id === 'kra-IV-B-2' && (!ind.calculation || ind.calculation.kind === 'structured_points')) {
    return {
      kind: 'tiered_option',
      tierField: 'attendanceScope',
      options: { local: 1, international: 2 },
      aggregateCap: 10,
    };
  }
  if (ind.id === 'kra-IV-D-1' && (!ind.calculation || ind.calculation.kind === 'structured_points')) {
    return {
      kind: 'yearly_rate',
      roleField: 'academicServiceRole',
      yearsField: 'serviceYears',
      requiresNewlyAppointed: true,
      newlyAppointedField: 'newlyAppointedEligible',
      fractionalYearPolicy: 'unresolved',
      rates: {
        president: 5,
        vp_dean_director: 4,
        dept_program_head: 3,
        faculty_member: 2,
      },
    };
  }
  if (ind.calculation) return ind.calculation;
  if (ind.type === 'set_sef') {
    return {
      kind: 'set_sef_average',
      subType: ind.subType,
      factor: ind.subType === 'SET' ? 0.36 : 0.24,
      semesterCount: 6,
      policy: 'average_available_max_six',
    };
  }
  if (ind.matrix) return { kind: 'role_matrix', matrix: ind.matrix };
  if (ind.points && typeof ind.points === 'object') {
    const keys = Object.keys(ind.points);
    const patentKeys = keys.filter((k) => ['A', 'P', 'G'].includes(String(k).toUpperCase()));
    if (patentKeys.length && patentKeys.length === keys.length) {
      const stages = {};
      for (const k of keys) stages[String(k).toUpperCase()] = ind.points[k];
      return { kind: 'patent_stage', stages, notCumulative: true };
    }
    if (ind.id === 'kra-III-B-1-5' && ind.points?.local === 2 && ind.points?.international === 3) {
      return {
        kind: 'hourly_tier',
        rates: { local: 2, international: 3 },
        tierField: 'serviceScope',
        hoursField: 'hours',
      };
    }
    if (keys.includes('researchAward') || keys.includes('academicCompetition')) {
      return {
        kind: 'tiered_option',
        options: {
          research_award: ind.points.researchAward ?? ind.points.research_award,
          academic_competition: ind.points.academicCompetition ?? ind.points.academic_competition,
        },
        tierField: 'judgeServiceType',
      };
    }
    if (keys.includes('lead') && keys.includes('participant')) {
      return {
        kind: 'tiered_option',
        options: { lead: ind.points.lead, participant: ind.points.participant },
        tierField: 'extensionRole',
        aggregateCap: ind.aggregateCap ?? ind.calculation?.aggregateCap,
      };
    }
    if (keys.some((k) => ['local', 'international'].includes(k))) {
      const tierField =
        ind.id?.endsWith('B-1-1') || ind.id?.endsWith('B-1-3') ? 'serviceScope' : ind.calculation?.tierField;
      return {
        kind: 'tiered_option',
        options: ind.points,
        tierField: tierField || 'serviceScope',
        tierCaps: ind.calculation?.tierCaps,
      };
    }
    if (keys.some((k) => ['local', 'international', 'new', 'updated'].includes(k))) {
      return {
        kind: 'tiered_option',
        options: ind.points,
        tierField: ind.calculation?.tierField,
        tierCaps: ind.calculation?.tierCaps,
      };
    }
    return { kind: 'structured_points', points: ind.points };
  }
  if (ind.pointRule === 'pending' || ind.pointRule === 'pending_external') return { kind: 'pending' };
  if (ind.maxPoints != null) return { kind: 'fixed_per_entry', maxPoints: ind.maxPoints, perService: ind.perService ?? null };
  return { kind: 'pending' };
}

export function buildSeedCatalog() {
  const catalog = deepClone(ASSESSMENT_CATALOG);
  catalog.kras = catalog.kras.map((kra) => ({
    ...kra,
    criteria: kra.criteria.map((crit) => ({
      ...crit,
      capMaxPoints: crit.maxPoints ?? parseCapFromNote(crit.capNote),
      indicators: crit.indicators.map(normalizeIndicator),
    })),
  }));
  return catalog;
}

function ensureDocumentIntakeAliases(catalog, report) {
  if (!catalog || typeof catalog !== 'object') return;
  if (!Array.isArray(catalog.documentIntakeAliases)) catalog.documentIntakeAliases = [];
  const existing = new Set(catalog.documentIntakeAliases.map((a) => a.id));
  for (const alias of SET_SEF_DOCUMENT_INTAKE_ALIASES) {
    if (existing.has(alias.id)) continue;
    catalog.documentIntakeAliases.push(deepClone(alias));
    report.push(`intake ${alias.id}`);
  }
}

function shouldUpgradeIndicatorCalculation(existingInd, seedInd) {
  const seed = seedInd.calculation?.kind;
  if (!seed || seed === 'pending') return false;
  const ex = existingInd.calculation?.kind;
  if (!ex) return true;
  if (ex === 'structured_points' && (seed === 'patent_stage' || seed === 'tiered_option' || seed === 'hourly_tier')) return true;
  if (ex === 'structured_points' && seedInd.id?.startsWith('kra-III-B-')) return true;
  if (ex === 'structured_points' && seedInd.id?.startsWith('kra-IV-')) return true;
  if (ex === 'fixed_per_entry' && seedInd.id?.startsWith('kra-IV-B-3-') && seed === 'fixed_per_entry') {
    return !seedInd.calculation?.aggregateGroup;
  }
  if (ex === 'pending' && seedInd.id === 'kra-III-D-1' && seed === 'designation_matrix') return true;
  if (ex === 'pending' && seedInd.id === 'kra-III-C-1' && seed === 'pending' && seedInd.calculation?.requiresLinkedAchievement) {
    return true;
  }
  if (ex === 'pending' && seed !== 'pending') return true;
  return false;
}

function mergeIndicators(existingCrit, seedCrit, report) {
  if (!Array.isArray(existingCrit.indicators)) existingCrit.indicators = [];
  for (const seedInd of seedCrit.indicators || []) {
    if (existingCrit.id === 'kra-I-A' && isDocumentIntakeIndicator(seedInd)) continue;
    const ex = existingCrit.indicators.find((i) => i.id === seedInd.id);
    if (!ex) {
      existingCrit.indicators.push(deepClone(normalizeIndicator(seedInd)));
      report.push(`indicator ${seedInd.id}`);
    } else if (shouldUpgradeIndicatorCalculation(ex, seedInd)) {
      const normalized = normalizeIndicator(seedInd);
      ex.calculation = deepClone(normalized.calculation);
      if (seedInd.sourceRef && !ex.sourceRef) ex.sourceRef = seedInd.sourceRef;
      report.push(`calculation ${seedInd.id}`);
    }
  }
}

function mergeCriteria(existingKra, seedKra, report) {
  if (!Array.isArray(existingKra.criteria)) existingKra.criteria = [];
  for (const seedCrit of seedKra.criteria || []) {
    const ex = existingKra.criteria.find((c) => c.id === seedCrit.id);
    if (!ex) {
      existingKra.criteria.push(
        deepClone({
          ...seedCrit,
          capMaxPoints: seedCrit.maxPoints ?? parseCapFromNote(seedCrit.capNote),
          indicators: (seedCrit.indicators || []).map(normalizeIndicator),
        })
      );
      report.push(`criterion ${seedCrit.id}`);
    } else {
      if (ex.capMaxPoints == null && seedCrit.maxPoints != null) {
        ex.capMaxPoints = seedCrit.maxPoints ?? parseCapFromNote(seedCrit.capNote);
      }
      mergeIndicators(ex, seedCrit, report);
    }
  }
}

/** Add missing JC3 workbook nodes by stable id; preserve existing edits. Safe to run repeatedly. */
export function mergeWorkbookReferenceIntoCatalog(catalog, report = []) {
  const seed = buildSeedCatalog();
  if (!catalog || typeof catalog !== 'object') {
    return { catalog: seed, report: ['full reference catalog'], changed: true };
  }
  if (!Array.isArray(catalog.kras)) catalog.kras = [];
  for (const seedKra of seed.kras) {
    let ex = catalog.kras.find((k) => k.id === seedKra.id);
    if (!ex) {
      catalog.kras.push(deepClone(seedKra));
      report.push(`kra ${seedKra.id}`);
    } else {
      if (!ex.name) ex.name = seedKra.name;
      if (ex.maxPoints == null && seedKra.maxPoints != null) ex.maxPoints = seedKra.maxPoints;
      if (!ex.scoringPolicy && seedKra.scoringPolicy) {
        ex.scoringPolicy = deepClone(seedKra.scoringPolicy);
        report.push(`scoringPolicy ${seedKra.id}`);
      }
      mergeCriteria(ex, seedKra, report);
    }
  }
  if (!catalog.version) catalog.version = seed.version;
  if (!catalog.source) catalog.source = seed.source;
  ensureDocumentIntakeAliases(catalog, report);
  if (reconcileSupportingEvidenceIndicators(catalog)) {
    report.push('reconcile kra-I-A-special supporting evidence');
  }
  return { catalog, report, changed: report.length > 0 };
}

/** Upgrade legacy “pending” special-status rows without overwriting admin edits. */
export function reconcileSupportingEvidenceIndicator(ind) {
  if (!ind || ind.id !== 'kra-I-A-special') return false;
  let changed = false;
  if (ind.role !== 'supporting_evidence') {
    ind.role = 'supporting_evidence';
    changed = true;
  }
  const kind = ind.calculation?.kind;
  if (kind === 'pending' || ind.pointRule === 'pending' || ind.pointRule === 'pending_external' || !kind) {
    ind.calculation = { kind: 'supporting_evidence' };
    delete ind.pointRule;
    ind.maxPoints = null;
    changed = true;
  }
  if (!Array.isArray(ind.specialStatusCategories) || !ind.specialStatusCategories.length) {
    ind.specialStatusCategories = [...DEFAULT_SPECIAL_STATUS_CATEGORIES];
    changed = true;
  }
  if (Array.isArray(ind.conditions) && ind.conditions.some((c) => /pending configuration/i.test(c))) {
    ind.conditions = ind.conditions.filter((c) => !/pending configuration/i.test(c));
    if (!ind.conditions.length) {
      ind.conditions = [
        'Select the category that applies and upload supporting documents per Enhanced Guidelines.',
        'Reviewer confirms status and remarks; no automatic points or SET/SEF exemptions.',
      ];
    }
    changed = true;
  }
  return changed;
}

export function reconcileSupportingEvidenceIndicators(catalog) {
  let changed = false;
  for (const kra of catalog?.kras || []) {
    for (const crit of kra.criteria || []) {
      for (const ind of crit.indicators || []) {
        if (reconcileSupportingEvidenceIndicator(ind)) changed = true;
      }
    }
  }
  return changed;
}

export function countOfficialKrasWithContent(catalog) {
  if (!catalog?.kras?.length) return 0;
  return OFFICIAL_KRA_IDS.filter((id) => {
    const kra = catalog.kras.find((k) => k.id === id);
    return kra && (kra.criteria?.length ?? 0) > 0;
  }).length;
}

export function isCatalogWorkbookComplete(catalog) {
  return countOfficialKrasWithContent(catalog) === OFFICIAL_KRA_IDS.length;
}

function parseCapFromNote(note) {
  if (!note) return null;
  const m = /Max\s*=\s*(\d+)/i.exec(note);
  return m ? Number(m[1]) : null;
}

export function ensureAssessmentConfig(store) {
  if (!store.assessmentConfig || typeof store.assessmentConfig !== 'object') {
    store.assessmentConfig = {
      activePublishedId: null,
      draftId: null,
      previewDraft: false,
      versions: [],
    };
  }
  if (!Array.isArray(store.assessmentConfig.versions)) {
    store.assessmentConfig.versions = [];
  }
  return store.assessmentConfig;
}

export const ConfigRepository = {
  loadContext(store) {
    ensureAssessmentConfig(store);
    return store.assessmentConfig;
  },

  getVersion(store, id) {
    return this.loadContext(store).versions.find((v) => v.id === id);
  },

  getActivePublished(store) {
    const ctx = this.loadContext(store);
    if (ctx.activePublishedId) {
      const v = this.getVersion(store, ctx.activePublishedId);
      if (v?.status === 'published') return v;
    }
    return ctx.versions.find((v) => v.status === 'published') || null;
  },

  /** Create an editable draft from the JC3 workbook reference mapping (not published). */
  initializeDraftFromReference(store, actor) {
    const ctx = this.loadContext(store);
    const existing = this.getDraft(store);
    if (existing) {
      if (isCatalogWorkbookComplete(existing.catalog)) return existing;
      const { report } = mergeWorkbookReferenceIntoCatalog(existing.catalog);
      if (report.length) {
        existing.changeHistory = existing.changeHistory || [];
        existing.changeHistory.push({
          at: new Date().toISOString(),
          actor: actor || 'admin',
          summary: `Merged missing workbook reference items (${report.length}).`,
        });
      }
      if (!existing.kraWeights || !Object.keys(existing.kraWeights).length) {
        existing.kraWeights = { ...KRA_WEIGHTS };
      }
      return existing;
    }
    const seed = buildSeedCatalog();
    const draft = {
      id: `cfg-draft-${Date.now()}`,
      label: `${ASSESSMENT_CATALOG.version} (draft)`,
      status: 'draft',
      effectiveDate: null,
      publishedAt: null,
      publishedBy: null,
      sourceSeed: SOURCE_SEED_TAG,
      catalog: seed,
      kraWeights: { ...KRA_WEIGHTS },
      changeHistory: [
        {
          at: new Date().toISOString(),
          actor: actor || 'admin',
          summary: 'Draft initialized from DBM–CHED JC3 workbook reference mapping.',
        },
      ],
    };
    ctx.versions.push(draft);
    ctx.draftId = draft.id;
    return draft;
  },

  resolveRulesView(store, { readOnly = false } = {}) {
    this.loadContext(store);
    const published = this.getActivePublished(store);
    const draft = this.getDraft(store);
    if (readOnly) {
      if (!published) return { mode: 'no_published' };
      return {
        mode: 'ok',
        catalog: published.catalog,
        weights: published.kraWeights,
        active: published,
        draft: null,
      };
    }
    if (draft?.catalog) {
      return {
        mode: 'ok',
        catalog: draft.catalog,
        weights: draft.kraWeights || published?.kraWeights || { ...KRA_WEIGHTS },
        active: published,
        draft,
      };
    }
    if (published?.catalog) {
      return {
        mode: 'ok',
        catalog: published.catalog,
        weights: published.kraWeights,
        active: published,
        draft: null,
      };
    }
    return { mode: 'uninitialized', active: null, draft: null };
  },

  /** Ensure editable draft contains all four official KRAs from the workbook reference (no publish). */
  ensureDraftCatalogComplete(store, actor) {
    this.loadContext(store);
    let draft = this.getDraft(store);
    if (!draft) {
      const pub = this.getActivePublished(store);
      draft = pub ? this.forkDraftFromActive(store, actor) : this.initializeDraftFromReference(store, actor);
    } else if (!draft.catalog) {
      draft.catalog = buildSeedCatalog();
    }
    const { report, changed } = mergeWorkbookReferenceIntoCatalog(draft.catalog);
    let weightsChanged = false;
    if (!draft.kraWeights || Object.keys(draft.kraWeights).length < OFFICIAL_KRA_IDS.length) {
      draft.kraWeights = { ...KRA_WEIGHTS, ...(draft.kraWeights || {}) };
      weightsChanged = true;
    }
    if (changed || weightsChanged) {
      draft.changeHistory = draft.changeHistory || [];
      draft.changeHistory.push({
        at: new Date().toISOString(),
        actor: actor || 'admin',
        summary: changed
          ? `Restored missing workbook reference (${report.length} items).`
          : 'Restored default KRA weights.',
      });
    }
    return { draft, report, changed: changed || weightsChanged };
  },

  getDraft(store) {
    const ctx = this.loadContext(store);
    if (!ctx.draftId) return null;
    const d = this.getVersion(store, ctx.draftId);
    return d?.status === 'draft' ? d : null;
  },

  /** Catalog used for new calculations in UI (preview draft when enabled). */
  getCalculationCatalog(store, { facultyId = null, preview = null } = {}) {
    const ctx = this.loadContext(store);
    const usePreview = preview ?? ctx.previewDraft;

    if (facultyId) {
      const pinned = store.assessments?.[facultyId]?.configVersionId;
      if (pinned) {
        const v = this.getVersion(store, pinned);
        if (v) {
          if (v.catalog?.kras?.length) {
            return {
              catalog: v.catalog,
              kraWeights: v.kraWeights || {},
              versionId: v.id,
              pinned: true,
              state: 'ok',
            };
          }
          return {
            catalog: null,
            kraWeights: v.kraWeights || {},
            versionId: v.id,
            pinned: true,
            state: 'catalog_not_loaded',
          };
        }
      }
    }

    if (usePreview) {
      const draft = this.getDraft(store);
      if (draft?.catalog?.kras?.length) {
        return {
          catalog: draft.catalog,
          kraWeights: draft.kraWeights || {},
          versionId: draft.id,
          pinned: false,
          preview: true,
          state: 'ok',
        };
      }
      if (draft) {
        return {
          catalog: null,
          kraWeights: draft.kraWeights || {},
          versionId: draft.id,
          pinned: false,
          preview: true,
          state: 'catalog_not_loaded',
        };
      }
    }

    const pub = this.getActivePublished(store);
    if (!pub) {
      return { catalog: null, kraWeights: {}, versionId: null, pinned: false, state: 'no_published' };
    }
    if (!pub.catalog?.kras?.length) {
      return {
        catalog: null,
        kraWeights: pub.kraWeights || {},
        versionId: pub.id,
        pinned: false,
        state: 'catalog_not_loaded',
      };
    }
    return {
      catalog: pub.catalog,
      kraWeights: pub.kraWeights || {},
      versionId: pub.id,
      pinned: false,
      state: 'ok',
    };
  },

  forkDraftFromActive(store, actor) {
    const ctx = this.loadContext(store);
    const existingDraft = ctx.draftId ? this.getDraft(store) : null;
    if (existingDraft) return existingDraft;
    if (ctx.draftId && !existingDraft) {
      ctx.draftId = null;
    }
    const active = this.getActivePublished(store);
    if (!active) return this.initializeDraftFromReference(store, actor);
    const draft = {
      id: `cfg-draft-${Date.now()}`,
      label: `${active.label}-draft`,
      status: 'draft',
      effectiveDate: null,
      publishedAt: null,
      publishedBy: null,
      sourceSeed: active.sourceSeed,
      catalog: deepClone(active.catalog),
      kraWeights: { ...active.kraWeights },
      changeHistory: [
        ...deepClone(active.changeHistory || []),
        { at: new Date().toISOString(), actor, summary: 'Draft created from published configuration (scores are not retroactively recalculated).' },
      ],
    };
    ctx.versions.push(draft);
    ctx.draftId = draft.id;
    return draft;
  },

  saveDraft(store, { catalog, kraWeights, actor, summary }) {
    const draft = this.getDraft(store) || this.forkDraftFromActive(store, actor);
    const validation = validateCatalog(catalog, kraWeights);
    if (!validation.ok) throw new Error(validation.message);

    draft.catalog = deepClone(catalog);
    draft.kraWeights = { ...kraWeights };
    draft.changeHistory.push({ at: new Date().toISOString(), actor, summary: summary || 'Draft saved' });
    return draft;
  },

  publishDraft(store, { effectiveDate, actor, summary }) {
    const ctx = this.loadContext(store);
    const draft = this.getDraft(store);
    if (!draft) throw new Error('No draft to publish.');
    if (!effectiveDate) throw new Error('Effective date is required.');

    const validation = validateCatalog(draft.catalog, draft.kraWeights);
    if (!validation.ok) throw new Error(validation.message);

    const prev = this.getActivePublished(store);
    if (prev) {
      prev.status = 'archived';
      prev.changeHistory = prev.changeHistory || [];
      prev.changeHistory.push({ at: new Date().toISOString(), actor, summary: `Superseded by ${draft.id}` });
    }

    draft.status = 'published';
    draft.effectiveDate = effectiveDate;
    draft.publishedAt = new Date().toISOString();
    draft.publishedBy = actor;
    draft.label = `published-${effectiveDate}`;
    draft.changeHistory.push({ at: new Date().toISOString(), actor, summary: summary || 'Published' });

    ctx.activePublishedId = draft.id;
    ctx.draftId = null;
    ctx.previewDraft = false;
    store.configPublished = draft.label;

    return draft;
  },

  setPreviewDraft(store, on) {
    this.loadContext(store).previewDraft = !!on;
  },

  pinFacultyConfigVersion(store, facultyId, versionId) {
    if (!store.assessments[facultyId]) store.assessments[facultyId] = { setSef: { SET: [], SEF: [] }, entries: {} };
    if (!store.assessments[facultyId].configVersionId && versionId) {
      store.assessments[facultyId].configVersionId = versionId;
    }
  },
};

export function findIndicatorInCatalog(catalog, indicatorId) {
  for (const kra of catalog.kras) {
    for (const crit of kra.criteria) {
      const ind = crit.indicators.find((i) => i.id === indicatorId);
      if (ind) return { kra, crit, ind };
    }
  }
  const alias = (catalog.documentIntakeAliases || []).find((a) => a.id === indicatorId);
  if (alias) {
    const kra = catalog.kras.find((k) => k.id === (alias.kraId || 'kra-I'));
    const crit = kra?.criteria?.find((c) => c.id === (alias.criterionId || 'kra-I-A'));
    if (kra && crit) return { kra, crit, ind: alias, intakeOnly: true };
  }
  return null;
}

export function validateCatalog(catalog, kraWeights) {
  if (!catalog?.kras?.length) return { ok: false, message: 'Catalog must contain at least one KRA.' };
  const wSum = Object.values(kraWeights || {}).reduce((a, b) => a + Number(b), 0);
  if (Math.abs(wSum - 1) > 0.001) {
    return { ok: false, message: `KRA weights should sum to 1.0 (current ${wSum.toFixed(3)}).` };
  }
  for (const kra of catalog.kras) {
    if (!kra.id || !kra.name) return { ok: false, message: 'Each KRA requires id and name.' };
    for (const crit of kra.criteria) {
      if (!crit.id || !crit.name) return { ok: false, message: 'Each criterion requires id and name.' };
      if (crit.capMaxPoints != null && Number(crit.capMaxPoints) < 0) return { ok: false, message: 'Criterion caps must be non-negative.' };
      for (const ind of crit.indicators) {
        if (!ind.id || !ind.name) return { ok: false, message: 'Each indicator requires id and name.' };
        if (ind.maxPoints != null && Number(ind.maxPoints) < 0) return { ok: false, message: `Invalid max points on ${ind.id}` };
      }
    }
  }
  return { ok: true };
}

export { SOURCE_CIRCULAR, SOURCE_SEED_TAG };
