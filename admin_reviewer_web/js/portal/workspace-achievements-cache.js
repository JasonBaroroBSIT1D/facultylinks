/**
 * Reviewer workspace — one submitted-achievements fetch per faculty (coalesced, cached).
 */
import { PortalApi } from '../services/portal-api.js';
import { AuthRepository } from '../services/auth-repository.js';
import { MockStore, patchFacultyAchievements } from '../repositories/mock-store.js';

export const ACH_LOAD_IDLE = 'idle';
export const ACH_LOAD_LOADING = 'loading';
export const ACH_LOAD_LOADED = 'loaded';
export const ACH_LOAD_ERROR = 'error';

const STALE_MS = 90_000;
const _entries = new Map();
const _inflight = new Map();
let _scopeKey = null;

export function resolveAchievementCriterionId(achievement) {
  const cid = (achievement?.criterionId || '').trim();
  if (cid) return cid;
  const ind = (achievement?.indicatorId || '').trim();
  if (ind.startsWith('kra-I-B')) return 'kra-I-B';
  if (ind.startsWith('kra-I-C')) return 'kra-I-C';
  if (ind.startsWith('kra-II-A')) return 'kra-II-A';
  if (ind.startsWith('kra-II-B')) return 'kra-II-B';
  if (ind.startsWith('kra-II-C')) return 'kra-II-C';
  if (ind.startsWith('kra-III-A')) return 'kra-III-A';
  if (ind.startsWith('kra-III-B')) return 'kra-III-B';
  if (ind.startsWith('kra-III-C')) return 'kra-III-C';
  if (ind.startsWith('kra-III-D')) return 'kra-III-D';
  if (ind.startsWith('kra-IV-A')) return 'kra-IV-A';
  if (ind.startsWith('kra-IV-B')) return 'kra-IV-B';
  if (ind.startsWith('kra-IV-C')) return 'kra-IV-C';
  if (ind.startsWith('kra-IV-D')) return 'kra-IV-D';
  return null;
}

export function filterSubmittedAchievements(list) {
  return (list || []).filter((a) => a.submissionStatus === 'submitted');
}

export function achievementsForCriterion(achievements, criterionId) {
  return filterSubmittedAchievements(achievements).filter((a) => resolveAchievementCriterionId(a) === criterionId);
}

export function countAchievementsList(achievements, criterionId) {
  const list = achievementsForCriterion(achievements, criterionId);
  const pending = list.filter((a) => ['pending', 'correction_requested'].includes(a.reviewStatus || 'pending')).length;
  return { total: list.length, pending };
}

function readScopeKey() {
  const session = AuthRepository.getSession() || null;
  const store = MockStore.load();
  const user = session || {};
  const uid = user.id || user.portalId || user.email || 'anon';
  const role = user.role || '';
  const cfg =
    store?.assessmentConfig?.activePublishedId ||
    store?.configPublished ||
    '';
  return `${uid}:${role}:${cfg}`;
}

function entryKey(facultyId) {
  return `${_scopeKey || readScopeKey()}|${facultyId}`;
}

function syncScope() {
  const next = readScopeKey();
  if (_scopeKey && next !== _scopeKey) {
    clearWorkspaceAchievementsCache();
  }
  _scopeKey = next;
  return _scopeKey;
}

function getEntry(facultyId) {
  syncScope();
  const key = entryKey(facultyId);
  if (!_entries.has(key)) {
    _entries.set(key, { state: ACH_LOAD_IDLE, achievements: [], error: null, updatedAt: 0 });
  }
  return _entries.get(key);
}

function commitEntry(facultyId, achievements, { state = ACH_LOAD_LOADED, error = null } = {}) {
  const key = entryKey(facultyId);
  const entry = {
    state,
    achievements: achievements || [],
    error,
    updatedAt: Date.now(),
  };
  _entries.set(key, entry);
  if (state === ACH_LOAD_LOADED) {
    patchFacultyAchievements(facultyId, achievements);
  }
  return entry;
}

function seedAchievementsFromStore(facultyId) {
  const store = MockStore.load();
  const raw = store?.assessments?.[facultyId]?.achievements;
  if (!Array.isArray(raw)) return [];
  const submitted = filterSubmittedAchievements(raw);
  return submitted.length ? submitted : [];
}

export function clearWorkspaceAchievementsCache() {
  _entries.clear();
  _inflight.clear();
  _scopeKey = null;
}

export function invalidateFacultyAchievementsCache(facultyId) {
  syncScope();
  const key = entryKey(facultyId);
  _entries.delete(key);
  _inflight.delete(key);
}

export function getFacultyAchievementsEntry(facultyId) {
  return { ...getEntry(facultyId) };
}

export function patchAchievementInCache(facultyId, achievement) {
  if (!achievement?.id) return;
  const entry = getEntry(facultyId);
  const list = [...(entry.achievements || [])];
  const idx = list.findIndex((a) => a.id === achievement.id);
  if (idx >= 0) list[idx] = { ...list[idx], ...achievement };
  else list.push(achievement);
  commitEntry(facultyId, filterSubmittedAchievements(list));
}

async function fetchAllSubmitted(facultyId) {
  const data = await PortalApi.fetchFacultyAchievements(facultyId, { submittedOnly: true });
  return filterSubmittedAchievements(data.achievements || []);
}

/**
 * @param {{ force?: boolean, background?: boolean }} options
 */
export function ensureFacultyAchievementsLoaded(facultyId, options = {}) {
  syncScope();
  const key = entryKey(facultyId);
  const entry = getEntry(facultyId);
  const now = Date.now();
  const stale = entry.state === ACH_LOAD_LOADED && now - entry.updatedAt > STALE_MS;

  if (entry.state === ACH_LOAD_LOADED && !options.force && !stale) {
    return Promise.resolve(entry);
  }

  if (entry.state === ACH_LOAD_LOADED && stale && !options.force) {
    if (!_inflight.has(key)) {
      _inflight.set(
        key,
        fetchAllSubmitted(facultyId)
          .then((list) => commitEntry(facultyId, list))
          .catch(() => entry)
          .finally(() => _inflight.delete(key))
      );
    }
    return Promise.resolve(entry);
  }

  if (_inflight.has(key)) {
    return _inflight.get(key);
  }

  const seeded = entry.state === ACH_LOAD_IDLE ? seedAchievementsFromStore(facultyId) : [];
  if (seeded.length && entry.state === ACH_LOAD_IDLE) {
    commitEntry(facultyId, seeded);
  }

  if (!options.background) {
    const cur = getEntry(facultyId);
    if (cur.state !== ACH_LOAD_LOADED) {
      _entries.set(key, { ...cur, state: ACH_LOAD_LOADING, error: null });
    }
  }

  const promise = fetchAllSubmitted(facultyId)
    .then((list) => commitEntry(facultyId, list))
    .catch((e) => {
      const prev = getEntry(facultyId);
      const fallback = prev.achievements?.length ? prev.achievements : [];
      const next = {
        state: ACH_LOAD_ERROR,
        achievements: fallback,
        error: e,
        updatedAt: prev.updatedAt || 0,
      };
      _entries.set(key, next);
      return next;
    })
    .finally(() => _inflight.delete(key));

  _inflight.set(key, promise);
  return promise;
}
