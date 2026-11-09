import { API_TIMEOUT_MS, getApiBase } from '../core/api-config.js';

async function apiJson(path, options = {}) {
  const timeoutMs = options.timeoutMs ?? API_TIMEOUT_MS;
  const { timeoutMs: _drop, ...fetchOpts } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${getApiBase()}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(fetchOpts.headers || {}) },
      ...fetchOpts,
      signal: controller.signal,
    });
  } catch (e) {
    if (e?.name === 'AbortError') {
      const err = new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s. Check that the API is running.`);
      err.name = 'TimeoutError';
      throw err;
    }
    const err = new Error(e.message || 'Failed to fetch');
    err.name = 'NetworkError';
    throw err;
  } finally {
    clearTimeout(timer);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

export const PortalApi = {
  fetchState: ({ full = false } = {}) =>
    apiJson(full ? '/api/portal/state' : '/api/portal/state?lite=1', { timeoutMs: full ? API_TIMEOUT_MS * 2 : API_TIMEOUT_MS }),
  createFaculty: (body) => apiJson('/api/admin/faculty', { method: 'POST', body: JSON.stringify(body) }),
  updateFaculty: (id, body) => apiJson(`/api/admin/faculty/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(body) }),
  createReviewer: (body) => apiJson('/api/admin/reviewers', { method: 'POST', body: JSON.stringify(body) }),
  updateReviewer: (id, body) => apiJson(`/api/admin/reviewers/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(body) }),
  setAssignments: (reviewerId, assignedFacultyIds) =>
    apiJson(`/api/admin/reviewers/${encodeURIComponent(reviewerId)}/assignments`, {
      method: 'PUT',
      body: JSON.stringify({ assignedFacultyIds }),
    }),
  saveInstitution: (institutionConfig) =>
    apiJson('/api/config/institution', { method: 'PUT', body: JSON.stringify(institutionConfig) }),
  saveAssessmentMeta: (meta) => apiJson('/api/config/assessment-meta', { method: 'PUT', body: JSON.stringify(meta) }),
  publishCatalog: (payload) => apiJson('/api/config/catalog/publish', { method: 'POST', body: JSON.stringify(payload) }),
  saveCatalogDraft: (payload) =>
    apiJson('/api/config/catalog/draft', { method: 'PUT', body: JSON.stringify(payload), timeoutMs: API_TIMEOUT_MS * 2 }),
  setFacultyStatus: (portalId, status) =>
    apiJson(`/api/admin/faculty/${encodeURIComponent(portalId)}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  setReviewerStatus: (portalId, status) =>
    apiJson(`/api/admin/reviewers/${encodeURIComponent(portalId)}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  reviewDocument: (publicId, patch) =>
    apiJson(`/api/documents/${encodeURIComponent(publicId)}/review`, { method: 'PATCH', body: JSON.stringify(patch) }),
  resendFacultyCredentials: (portalId) =>
    apiJson(`/api/admin/faculty/${encodeURIComponent(portalId)}/resend-credentials`, { method: 'POST', body: '{}' }),
  reassignFacultyConfigVersion: (portalId, body) =>
    apiJson(`/api/admin/faculty/${encodeURIComponent(portalId)}/assessment/config-version`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  setFacultyScoringWindow: (portalId, body) =>
    apiJson(`/api/admin/faculty/${encodeURIComponent(portalId)}/assessment/scoring-window`, {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
  resendReviewerCredentials: (portalId) =>
    apiJson(`/api/admin/reviewers/${encodeURIComponent(portalId)}/resend-credentials`, { method: 'POST', body: '{}' }),
  fetchSetSefExtraction: (documentId) => apiJson(`/api/documents/${encodeURIComponent(documentId)}/set-sef`),
  fetchDocumentViewUrl: (documentId) => apiJson(`/api/documents/${encodeURIComponent(documentId)}/view-url`),
  fetchFacultyCriterionA: (facultyPortalId) =>
    apiJson(`/api/portal/faculty/${encodeURIComponent(facultyPortalId)}/teaching-effectiveness/criterion-a`),
  fetchFacultyAchievements: (facultyPortalId, { criterionId, submittedOnly } = {}) => {
    const q = new URLSearchParams();
    if (criterionId) q.set('criterionId', criterionId);
    if (submittedOnly) q.set('submitted', '1');
    const qs = q.toString();
    return apiJson(
      `/api/portal/faculty/${encodeURIComponent(facultyPortalId)}/achievements${qs ? `?${qs}` : ''}`,
    );
  },
  reviewAchievement: (achievementId, body) =>
    apiJson(`/api/portal/achievements/${encodeURIComponent(achievementId)}/review`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  patchSetSefSemester: (documentId, recordId, body) =>
    apiJson(`/api/documents/${encodeURIComponent(documentId)}/set-sef/semesters/${recordId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
};
