const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

function getHeaders(token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request(endpoint, options = {}, token = null) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    ...options,
    headers: {
      ...getHeaders(token),
      ...(options.headers || {})
    }
  };

  const res = await fetch(url, config);
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const errorMsg = data?.detail || `HTTP Error ${res.status}`;
    const err = new Error(errorMsg);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

export const api = {
  // Phase 1 Legacy Endpoints
  checkHealth: () => request('/health'),
  runPhase1Review: (draft, channel = 'social') =>
    request('/review', {
      method: 'POST',
      body: JSON.stringify({ draft, channel })
    }),

  // Auth & Profile
  fetchDemoUsers: () => request('/api/auth/demo-users'),
  fetchProfile: (token) => request('/api/auth/me', {}, token),
  fetchTeamMembers: (token) => request('/api/auth/members', {}, token),

  // Guidelines
  fetchGuidelines: (token, activeOnly = false) =>
    request(`/api/guidelines?active_only=${activeOnly}`, {}, token),
  createGuideline: (token, ruleData) =>
    request('/api/guidelines', {
      method: 'POST',
      body: JSON.stringify(ruleData)
    }, token),
  updateGuideline: (token, ruleId, updateData) =>
    request(`/api/guidelines/${ruleId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData)
    }, token),
  deactivateGuideline: (token, ruleId) =>
    request(`/api/guidelines/${ruleId}`, {
      method: 'DELETE'
    }, token),

  // Drafts
  fetchDrafts: (token, myDraftsOnly = false) =>
    request(`/api/drafts?my_drafts_only=${myDraftsOnly}`, {}, token),
  fetchDraft: (token, draftId) =>
    request(`/api/drafts/${draftId}`, {}, token),
  createDraft: (token, draftData) =>
    request('/api/drafts', {
      method: 'POST',
      body: JSON.stringify(draftData)
    }, token),
  updateDraft: (token, draftId, draftData) =>
    request(`/api/drafts/${draftId}`, {
      method: 'PUT',
      body: JSON.stringify(draftData)
    }, token),
  checkDraft: (token, draftId) =>
    request(`/api/drafts/${draftId}/check`, {
      method: 'POST'
    }, token),
  submitDraft: (token, draftId) =>
    request(`/api/drafts/${draftId}/submit`, {
      method: 'POST'
    }, token),
  approveDraft: (token, draftId, comments) =>
    request(`/api/drafts/${draftId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ comments })
    }, token),
  requestChangesDraft: (token, draftId, comments) =>
    request(`/api/drafts/${draftId}/request-changes`, {
      method: 'POST',
      body: JSON.stringify({ comments })
    }, token),

  // Audit Logs
  fetchAuditLogs: (token, entityId = null) => {
    const query = entityId ? `?entity_id=${encodeURIComponent(entityId)}` : '';
    return request(`/api/audit-logs${query}`, {}, token);
  }
};
