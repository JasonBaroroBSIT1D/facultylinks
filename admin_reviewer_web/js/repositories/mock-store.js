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

/** @deprecated Remove after clients migrate — legacy demo localStorage key. */
export const MOCK_STORE_STORAGE_KEY = 'facultylink_demo_state_v1';

let _cache = null;
let _loadError = null;
let _bootstrapPromise = null;

export function clearPortalCache() {
  _cache = null;
  _loadError = null;
  _bootstrapPromise = null;
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
  };
}

function normalizeFromApi(data) {
  const base = emptyState();
  const s = {
    ...base,
    faculty: data.faculty || [],
    reviewers: data.reviewers || [],
    documents: data.documents || [],
    assessments: data.assessments || {},
    activity: data.activity || [],
    notifications: data.notifications || [],
    institutionConfig: mergeInstitutionConfig(data.institutionConfig),
    catalogPublished: data.catalogPublished ?? null,
    configDraft: data.configDraft ?? data.catalogDraft ?? null,
    configPublished: data.configPublished ?? null,
    assessmentConfig: data.assessmentConfig || base.assessmentConfig,
  };
  ensureAssessmentConfig(s);
  hydrateAssessmentConfigFromPortal(s);
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

export async function bootstrapPortal() {
  if (_bootstrapPromise) return _bootstrapPromise;
  _bootstrapPromise = (async () => {
    clearDemoStorageKeys();
    try {
      const data = await PortalApi.fetchState();
      _cache = normalizeFromApi(data);
      _loadError = null;
    } catch (e) {
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

  static async refresh() {
    return bootstrapPortal();
  }

  static save(state, { notify = true } = {}) {
    _cache = state;
    if (notify) window.dispatchEvent(new CustomEvent('fl-state-changed'));
    return state;
  }

  static reset() {
    return bootstrapPortal();
  }

  static getDocumentStats() {
    const state = MockStore.load();
    const stats = { pending: 0, approved: 0, rejected: 0, correction_requested: 0 };
    for (const d of state.documents) {
      const key = d.reviewStatus || 'pending';
      stats[key] = (stats[key] || 0) + 1;
    }
    return stats;
  }

  static async updateDocument(id, patch) {
    const updated = await PortalApi.reviewDocument(id, patch);
    await bootstrapPortal();
    return updated.document;
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
      password: faculty.password,
    };
    if (faculty.id && String(faculty.id).startsWith('u-')) {
      await PortalApi.updateFaculty(faculty.id, body);
    } else {
      await PortalApi.createFaculty(body);
    }
    await bootstrapPortal();
    return faculty;
  }

  static async upsertReviewer(rev) {
    const body = {
      firstName: rev.firstName,
      lastName: rev.lastName,
      email: rev.email,
      employeeId: rev.employeeId,
      department: rev.department,
      status: rev.status,
      password: rev.password,
    };
    if (rev.id && String(rev.id).startsWith('u-')) {
      await PortalApi.updateReviewer(rev.id, body);
    } else {
      await PortalApi.createReviewer(body);
    }
    await bootstrapPortal();
    return rev;
  }

  static logActivity(_text, _actor) {
    /* persisted server-side */
  }
}

export function syncEntryPointsFromDocument(_doc) {
  /* assessment entry sync deferred to dedicated API */
}
