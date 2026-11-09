import { DEFAULT_INSTITUTION_CONFIG } from '../core/institution-config.js';
import { ConfigRepository, ensureAssessmentConfig } from './config-repository.js';

function mergeInstitutionConfig(raw) {
  const base = DEFAULT_INSTITUTION_CONFIG();
  if (!raw || typeof raw !== 'object') return base;
  return {
    ...base,
    ...raw,
    preparationPeriod: { ...base.preparationPeriod, ...(raw.preparationPeriod || {}) },
    rankOptions: Array.isArray(raw.rankOptions) && raw.rankOptions.length ? raw.rankOptions : base.rankOptions,
    rankRequirements:
      raw.rankRequirements && typeof raw.rankRequirements === 'object'
        ? raw.rankRequirements
        : base.rankRequirements,
  };
}
import { PortalApi } from '../services/portal-api.js';
import { AuthRepository } from '../services/auth-repository.js';
import {
  documentCountsTowardLegacyPending,
  enrichPortalDocuments,
} from '../portal/achievement-attachment-display.js';

/** @deprecated Remove after clients migrate — legacy demo localStorage key. */
export const MOCK_STORE_STORAGE_KEY = 'facultylink_demo_state_v1';

let _cache = null;
let _loadError = null;
let _bootstrapPromise = null;
let _bootstrapLoadId = 0;
let _portalFullLoaded = false;
let _catalogEnsurePromise = null;
let _cacheScopeKey = null;
let _revalidatePromise = null;
let _revalidateLoadId = 0;

/** Merge submitted achievements into portal cache (reviewer workspace authority). */
export function patchFacultyAchievements(facultyId, achievements) {
  if (!_cache || !facultyId) return;
  const prev = _cache.assessments?.[facultyId] || { setSef: { SET: [], SEF: [] }, entries: {} };
  _cache.assessments = {
    ...(_cache.assessments || {}),
    [facultyId]: { ...prev, achievements: Array.isArray(achievements) ? achievements : [] },
  };
  _cache.documents = enrichPortalDocuments(_cache.documents || [], _cache.assessments);
}

export function portalFullStateLoaded() {
  return _portalFullLoaded;
}

export function clearPortalCache() {
  _cache = null;
  _loadError = null;
  _bootstrapPromise = null;
  _bootstrapLoadId = 0;
  _portalFullLoaded = false;
  _catalogEnsurePromise = null;
  _cacheScopeKey = null;
  _revalidatePromise = null;
  _revalidateLoadId = 0;
}

function portalCacheScopeKey(user) {
  if (!user || typeof user !== 'object') return null;
  const id = user.id || user.portalId || user.email || '';
  const role = user.role || '';
  const cfg = user.activeConfigVersion || user.configVersion || '';
  return `${id}:${role}:${cfg}`;
}

function mergePortalPayload(prev, data) {
  const next = { ...prev };
  if (Array.isArray(data.faculty)) next.faculty = data.faculty;
  if (Array.isArray(data.reviewers)) next.reviewers = data.reviewers;
  if (Array.isArray(data.activity)) next.activity = data.activity;
  if (Array.isArray(data.notifications)) next.notifications = data.notifications;
  if (data.institutionConfig) next.institutionConfig = mergeInstitutionConfig(data.institutionConfig);
  if (data.catalogPublished) next.catalogPublished = data.catalogPublished;
  if (data.configDraft !== undefined) next.configDraft = data.configDraft;
  if (data.configPublished !== undefined) next.configPublished = data.configPublished;
  if (data.assessmentConfig) next.assessmentConfig = data.assessmentConfig;
  if (data.assessments) next.assessments = { ...prev.assessments, ...data.assessments };
  if (data.reviewQueue) next.reviewQueue = data.reviewQueue;
  if (Array.isArray(data.documents)) {
    const byId = new Map((prev.documents || []).map((d) => [d.id, d]));
    for (const d of data.documents) byId.set(d.id, { ...(byId.get(d.id) || {}), ...d });
    next.documents = enrichPortalDocuments([...byId.values()], next.assessments || prev.assessments);
  }
  ensureAssessmentConfig(next);
  hydrateAssessmentConfigFromPortal(next);
  return next;
}

/** Background lite refresh; coalesced and silent (no full view re-render). */
export function revalidatePortalInBackground() {
  if (_revalidatePromise) return _revalidatePromise;
  const loadId = ++_revalidateLoadId;
  _revalidatePromise = (async () => {
    try {
      const data = await PortalApi.fetchState({ full: false });
      if (loadId !== _revalidateLoadId) return _cache;
      const scope = portalCacheScopeKey(data.user);
      if (_cacheScopeKey && scope && scope !== _cacheScopeKey) {
        return _cache;
      }
      if (data.user) {
        _cacheScopeKey = scope;
        AuthRepository.syncSessionFromApiUser(data.user);
      }
      if (_cache) {
        _cache = mergePortalPayload(_cache, data);
      } else {
        _cache = normalizeFromApi(data);
      }
      _loadError = null;
    } catch {
      /* keep showing cached data */
    } finally {
      _revalidatePromise = null;
    }
    return _cache;
  })();
  return _revalidatePromise;
}

export function prefetchFullPortalState() {
  if (_portalFullLoaded) return Promise.resolve(_cache);
  return bootstrapPortal({ full: true, background: true });
}

/** Published catalog with KRA tree is present in memory (full bootstrap or hydrated). */
export function publishedCatalogReady(store = null) {
  const s = store || _cache;
  if (!s) return false;
  const pub = ConfigRepository.getActivePublished(s);
  return Boolean(pub?.catalog?.kras?.length);
}

/**
 * Load published catalog into portal cache (full portal state). Coalesces concurrent callers.
 * @returns {Promise<{ ok: boolean, reason?: string, error?: Error, store: object }>}
 */
export async function ensurePublishedCatalog(options = {}) {
  const store = MockStore.load();
  if (publishedCatalogReady(store) && !options.force) {
    return { ok: true, store };
  }
  if (_catalogEnsurePromise && !options.force) {
    return _catalogEnsurePromise;
  }
  _catalogEnsurePromise = (async () => {
    try {
      const current = MockStore.load();
      if (!publishedCatalogReady(current) || (options.force && !_portalFullLoaded)) {
        await bootstrapPortal({ full: true, force: Boolean(options.force) });
      }
      const next = MockStore.load();
      if (publishedCatalogReady(next)) {
        return { ok: true, store: next };
      }
      const pub = ConfigRepository.getActivePublished(next);
      if (!pub) {
        return { ok: false, reason: 'no_published', store: next };
      }
      return { ok: false, reason: 'catalog_not_loaded', store: next };
    } catch (error) {
      return { ok: false, reason: 'error', error, store: MockStore.load() };
    } finally {
      _catalogEnsurePromise = null;
    }
  })();
  return _catalogEnsurePromise;
}

function emptyState() {
  return {
    configPublished: null,
    configDraft: null,
    institutionConfig: DEFAULT_INSTITUTION_CONFIG(),
    faculty: [],
    reviewers: [],
    admins: [],
    assessments: {},
    documents: [],
    activity: [],
    notifications: [],
    catalogPublished: null,
    assessmentConfig: { activePublishedId: null, versions: [] },
    reviewQueue: null,
  };
}

function normalizeFromApi(data) {
  const base = emptyState();
  const s = {
    ...base,
    faculty: data.faculty || [],
    reviewers: data.reviewers || [],
    documents: enrichPortalDocuments(data.documents || [], data.assessments || {}),
    assessments: data.assessments || {},
    activity: data.activity || [],
    notifications: data.notifications || [],
    institutionConfig: mergeInstitutionConfig(data.institutionConfig),
    catalogPublished: data.catalogPublished ?? null,
    configDraft: data.configDraft ?? data.catalogDraft ?? null,
    configPublished: data.configPublished ?? null,
    assessmentConfig: data.assessmentConfig || base.assessmentConfig,
    reviewQueue: data.reviewQueue || null,
  };
  ensureAssessmentConfig(s);
  hydrateAssessmentConfigFromPortal(s);
  if (data.user) {
    AuthRepository.syncSessionFromApiUser(data.user);
  }
  return s;
}

/** Merge portal `configDraft` / `catalogPublished` blobs into assessmentConfig.versions. */
function hydrateAssessmentConfigFromPortal(store) {
  const ctx = store.assessmentConfig;
  if (!ctx) return;

  const draftBlob = store.configDraft;
  if (draftBlob && typeof draftBlob === 'object') {
    const catalog = draftBlob.catalog || (draftBlob.kras ? draftBlob : null);
    if (catalog) {
      let draft = ctx.draftId ? ctx.versions.find((v) => v.id === ctx.draftId) : null;
      if (!draft) {
        draft = ctx.versions.find((v) => v.status === 'draft');
      }
      if (!draft) {
        const id = ctx.draftId || `cfg-draft-${catalog.version || 'server'}`;
        draft = {
          id,
          label: `${catalog.version || 'Draft'}`,
          status: 'draft',
          catalog,
          kraWeights: draftBlob.kraWeights || {},
          changeHistory: [],
        };
        ctx.versions.push(draft);
        ctx.draftId = id;
      } else {
        draft.catalog = draft.catalog || catalog;
        draft.kraWeights = draft.kraWeights || draftBlob.kraWeights || {};
      }
    }
  }

  const pubCatalog = store.catalogPublished;
  if (pubCatalog && typeof pubCatalog === 'object' && pubCatalog.kras) {
    let pub =
      (ctx.activePublishedId && ctx.versions.find((v) => v.id === ctx.activePublishedId)) ||
      ctx.versions.find((v) => v.status === 'published');
    if (!pub) {
      const id = ctx.activePublishedId || `cfg-published-${pubCatalog.version || 'server'}`;
      pub = {
        id,
        label: pubCatalog.version || id,
        status: 'published',
        catalog: pubCatalog,
        kraWeights: pubCatalog.kraWeights || {},
        changeHistory: [],
      };
      ctx.versions.push(pub);
      ctx.activePublishedId = id;
    } else if (!pub.catalog) {
      pub.catalog = pubCatalog;
    }
  }
}

export async function persistConfigDraft(store) {
  await PortalApi.saveCatalogDraft({ assessmentConfig: store.assessmentConfig });
  MockStore.save(store, { notify: false });
}

export function clearDemoStorageKeys() {
  try {
    localStorage.removeItem(MOCK_STORE_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export async function bootstrapPortal(options = {}) {
  const wantFull = Boolean(options.full);
  const background = Boolean(options.background);
  const useLite = wantFull ? false : options.lite !== false;
  const fullFetch = !useLite;
  if (_bootstrapPromise && !options.force) {
    if (wantFull && !_portalFullLoaded) {
      await _bootstrapPromise;
      if (!_portalFullLoaded) {
        return bootstrapPortal({ ...options, full: true, force: true });
      }
    }
    return _bootstrapPromise;
  }
  const loadId = ++_bootstrapLoadId;
  _bootstrapPromise = (async () => {
    clearDemoStorageKeys();
    try {
      const data = await PortalApi.fetchState({ full: fullFetch });
      if (loadId !== _bootstrapLoadId) {
        return _cache;
      }
      const scope = portalCacheScopeKey(data.user);
      if (_cacheScopeKey && scope && scope !== _cacheScopeKey) {
        _cache = null;
      }
      if (data.user) {
        _cacheScopeKey = scope;
      }
      _portalFullLoaded = fullFetch || _portalFullLoaded;
      if (_cache && !options.replace) {
        _cache = mergePortalPayload(_cache, data);
      } else {
        _cache = normalizeFromApi(data);
      }
      _loadError = null;
    } catch (e) {
      if (loadId !== _bootstrapLoadId) {
        return _cache;
      }
      if (e?.name === 'NetworkError' || e?.name === 'TypeError') {
        _loadError = e;
        throw e;
      }
      if (e?.status === 401 || e?.status === 403) {
        let me = null;
        try {
          me = await AuthRepository.fetchMe();
        } catch (checkErr) {
          _loadError = checkErr;
          throw checkErr;
        }
        if (!me) {
          AuthRepository.clearClientSession();
          clearPortalCache();
          try {
            await AuthRepository.logout();
          } catch {
            /* cookie may already be gone */
          }
          const redir = new Error('Sign in required.');
          redir.name = 'AuthRedirect';
          throw redir;
        }
        _loadError = e;
        throw e;
      }
      _loadError = e;
      throw e;
    } finally {
      _bootstrapPromise = null;
    }
    return _cache;
  })();
  if (background) {
    void _bootstrapPromise;
    return _cache;
  }
  return _bootstrapPromise;
}

export function portalLoadError() {
  return _loadError;
}

export class MockStore {
  static load() {
    if (_cache) return _cache;
    const s = emptyState();
    ensureAssessmentConfig(s);
    return s;
  }

  static async refresh(options = {}) {
    return bootstrapPortal({ ...options, force: true });
  }

  static save(state, { notify = true } = {}) {
    _cache = state;
    if (notify) window.dispatchEvent(new CustomEvent('fl-state-changed'));
    return state;
  }

  static applyReviewMutationResponse(res, { clientHistory } = {}) {
    const store = MockStore.load();
    const doc = res?.document;
    let saved = doc;
    if (doc?.id) {
      const idx = store.documents.findIndex((d) => d.id === doc.id);
      const prevHist = idx >= 0 ? store.documents[idx].history : [];
      const merged = {
        ...(idx >= 0 ? store.documents[idx] : {}),
        ...doc,
        history: clientHistory || prevHist || doc.history || [],
      };
      if (idx >= 0) store.documents[idx] = merged;
      else store.documents.push(merged);
      saved = merged;
    }
    MockStore.save(store, { notify: false });
    return saved;
  }

  static reset() {
    return bootstrapPortal();
  }

  static getReviewQueue() {
    const state = MockStore.load();
    if (state.reviewQueue) return state.reviewQueue;
    return MockStore._computeReviewQueueFallback(state);
  }

  static _computeReviewQueueFallback(state) {
    let documentsPending = 0;
    let achievementsPending = 0;
    let bcEvidenceUnlinked = 0;
    const byFaculty = {};
    const achByFac = {};
    for (const [facId, ass] of Object.entries(state.assessments || {})) {
      const list = ass.achievements || [];
      achByFac[facId] = list;
      for (const a of list) {
        if (a.submissionStatus === 'submitted' && ['pending', 'correction_requested'].includes(a.reviewStatus || 'pending')) {
          achievementsPending += 1;
          const slot = (byFaculty[facId] ||= { documentsPending: 0, achievementsPending: 0, awaitingReview: 0, bcEvidenceUnlinked: 0 });
          slot.achievementsPending += 1;
        }
      }
    }
    for (const d of state.documents || []) {
      const facId = d.facultyId;
      const slot = (byFaculty[facId] ||= { documentsPending: 0, achievementsPending: 0, awaitingReview: 0, bcEvidenceUnlinked: 0 });
      const achievements = achByFac[facId] || [];
      if (documentCountsTowardLegacyPending(d, achievements)) {
        documentsPending += 1;
        slot.documentsPending += 1;
      }
      const linked = achievements.find((a) => (a.documentIds || []).includes(d.id));
      if (d.indicatorId && (d.indicatorId.startsWith('kra-I-B') || d.indicatorId.startsWith('kra-I-C')) && !linked) {
        bcEvidenceUnlinked += 1;
        slot.bcEvidenceUnlinked += 1;
      }
    }
    for (const slot of Object.values(byFaculty)) {
      slot.awaitingReview = slot.documentsPending + slot.achievementsPending;
    }
    return {
      documentsPending,
      achievementsPending,
      awaitingReview: documentsPending + achievementsPending,
      bcEvidenceUnlinked,
      byFaculty,
    };
  }

  static getDocumentStats() {
    const q = MockStore.getReviewQueue();
    const state = MockStore.load();
    const stats = {
      pending: q.awaitingReview || 0,
      approved: 0,
      rejected: 0,
      correction_requested: 0,
      evidence: 0,
      documentsPending: q.documentsPending || 0,
      achievementsPending: q.achievementsPending || 0,
      bcEvidenceUnlinked: q.bcEvidenceUnlinked || 0,
    };
    for (const d of state.documents) {
      const key = d.reviewStatus || 'pending';
      if (key === 'approved') stats.approved += 1;
      else if (key === 'rejected') stats.rejected += 1;
      else if (key === 'correction_requested') stats.correction_requested += 1;
      else if (key === 'evidence') stats.evidence += 1;
    }
    return stats;
  }

  static async updateDocument(id, patch, opts = {}) {
    const updated = await PortalApi.reviewDocument(id, patch);
    return MockStore.applyReviewMutationResponse(updated, opts);
  }

  static async upsertFaculty(faculty) {
    const body = {
      firstName: faculty.firstName,
      lastName: faculty.lastName,
      email: faculty.email,
      employeeId: faculty.employeeId,
      department: faculty.department,
      rank: faculty.rank,
      phone: faculty.phone,
      status: faculty.status,
      reviewerId: faculty.reviewerId,
    };
    let res;
    if (faculty.id && String(faculty.id).startsWith('u-')) {
      res = await PortalApi.updateFaculty(faculty.id, body);
    } else {
      res = await PortalApi.createFaculty(body);
    }
    await bootstrapPortal();
    return res;
  }

  static async upsertReviewer(rev) {
    const body = {
      firstName: rev.firstName,
      lastName: rev.lastName,
      email: rev.email,
      employeeId: rev.employeeId,
      department: rev.department,
      status: rev.status,
      phone: rev.phone,
    };
    let res;
    if (rev.id && String(rev.id).startsWith('u-')) {
      res = await PortalApi.updateReviewer(rev.id, body);
    } else {
      res = await PortalApi.createReviewer(body);
    }
    await bootstrapPortal();
    return res;
  }

  static logActivity(_text, _actor) {
    /* persisted server-side */
  }
}

export function syncEntryPointsFromDocument(_doc) {
  /* assessment entry sync deferred to dedicated API */
}
