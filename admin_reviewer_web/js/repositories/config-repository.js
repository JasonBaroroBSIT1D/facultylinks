import { ASSESSMENT_CATALOG, KRA_WEIGHTS, SOURCE_CIRCULAR } from '../core/assessment-definitions.js';

const SOURCE_SEED_TAG = 'dbm-jc3-workbook-seed';

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
  if (ind.calculation) return ind.calculation;
  if (ind.type === 'set_sef') {
    return {
      kind: 'set_sef_average',
      subType: ind.subType,
      factor: ind.subType === 'SET' ? 0.36 : 0.24,
      semesterCount: 6,
    };
  }
  if (ind.matrix) return { kind: 'role_matrix', matrix: ind.matrix };
  if (ind.points && typeof ind.points === 'object') return { kind: 'structured_points', points: ind.points };
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

function parseCapFromNote(note) {
  if (!note) return null;
  const m = /Max\s*=\s*(\d+)/i.exec(note);
  return m ? Number(m[1]) : null;
}

export function ensureAssessmentConfig(store) {
  if (store.assessmentConfig?.versions?.length) return store.assessmentConfig;

  const seed = buildSeedCatalog();
  const v1 = {
    id: 'cfg-published-1',
    label: ASSESSMENT_CATALOG.version,
    status: 'published',
    effectiveDate: '2026-01-01',
    publishedAt: new Date().toISOString(),
    publishedBy: 'system',
    sourceSeed: SOURCE_SEED_TAG,
    catalog: seed,
    kraWeights: { ...KRA_WEIGHTS },
    changeHistory: [{ at: new Date().toISOString(), actor: 'system', summary: 'Seeded from DBM–CHED JC3 workbook source mapping.' }],
  };
  store.assessmentConfig = {
    activePublishedId: v1.id,
    draftId: null,
    previewDraft: false,
    versions: [v1],
  };
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
    return this.getVersion(store, ctx.activePublishedId);
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
        if (v) return { catalog: v.catalog, kraWeights: v.kraWeights, versionId: v.id, pinned: true };
      }
    }

    if (usePreview) {
      const draft = this.getDraft(store);
      if (draft) return { catalog: draft.catalog, kraWeights: draft.kraWeights, versionId: draft.id, pinned: false, preview: true };
    }

    const pub = this.getActivePublished(store);
    return { catalog: pub.catalog, kraWeights: pub.kraWeights, versionId: pub.id, pinned: false };
  },

  forkDraftFromActive(store, actor) {
    const ctx = this.loadContext(store);
    if (ctx.draftId) return this.getDraft(store);
    const active = this.getActivePublished(store);
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

  if (!store.assessments) store.assessments = {};
  Object.keys(store.assessments).forEach((fid) => {
    if (!store.assessments[fid].configVersionId) store.assessments[fid].configVersionId = prev?.id || draft.id;
  });

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
