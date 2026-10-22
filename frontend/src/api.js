export class ApiError extends Error {
  constructor(message, status = 0, data = null, isNetworkError = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.isNetworkError = isNetworkError;
  }
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'https://brandguard-ai-zvud.onrender.com').replace(/\/$/, '');

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

  let res;
  try {
    res = await fetch(url, config);
  } catch (networkErr) {
    throw new ApiError(
      `Network connection failed: Unable to reach BrandGuard API at ${API_BASE}. The backend service may be offline or starting up.`,
      0,
      null,
      true
    );
  }

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    let errorMsg = data?.detail;
    if (!errorMsg) {
      if (res.status === 401) {
        errorMsg = 'Authentication required: Your session has expired or is invalid. Please sign in again.';
      } else if (res.status === 403) {
        errorMsg = 'Permission denied (403): Your account role does not have authorization for this resource.';
      } else if (res.status === 404) {
        errorMsg = 'Not found (404): No organization membership or guideline record exists for your account.';
      } else if (res.status === 503) {
        errorMsg = 'Backend service unavailable (503): Database or authentication credentials temporarily unreachable.';
      } else {
        errorMsg = `API Error ${res.status}: Unexpected backend response.`;
      }
    }
    const err = new ApiError(errorMsg, res.status, data, false);
    throw err;
  }

  return data;
}

export const api = {
  getBaseUrl: () => API_BASE,

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
