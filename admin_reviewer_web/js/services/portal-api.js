import { getApiBase } from '../core/api-config.js';

async function apiJson(path, options = {}) {
  let res;
  try {
    res = await fetch(`${getApiBase()}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
  } catch (e) {
    const err = new Error(e.message || 'Failed to fetch');
    err.name = 'NetworkError';
    throw err;
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
  fetchState: () => apiJson('/api/portal/state'),
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
  saveCatalogDraft: (payload) => apiJson('/api/config/catalog/draft', { method: 'PUT', body: JSON.stringify(payload) }),
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
};
