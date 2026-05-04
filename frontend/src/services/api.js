const API_BASE = '/api';

function getToken() {
  return localStorage.getItem('token');
}

async function request(url, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${url}`, {
    headers,
    ...options,
  });

  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('登录已过期');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '请求失败');
  }
  return res.json();
}

export const api = {
  // Auth
  login: (username, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),

  getMe: () => request('/auth/me'),

  createAccount: (username, password) =>
    request('/auth/create-account', { method: 'POST', body: JSON.stringify({ username, password }) }),

  listAccounts: () => request('/auth/accounts'),

  deleteAccount: (username) =>
    request(`/auth/accounts/${username}`, { method: 'DELETE' }),

  changePassword: (oldPassword, newPassword) =>
    request('/auth/change-password', { method: 'POST', body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }) }),

  // Trends
  getTrends: (source = 'all', forceRefresh = false) =>
    request(`/trends?source=${source}&force_refresh=${forceRefresh}`),

  getTrendAnalysis: (forceRefresh = false) =>
    request(`/trends/analysis?force_refresh=${forceRefresh}`),

  searchTrends: (keyword) =>
    request(`/trends/search?keyword=${encodeURIComponent(keyword)}`),

  getTrendsFetchStatus: () =>
    request('/trends/fetch-status'),

  refreshTrends: () =>
    request('/trends/refresh', { method: 'POST' }),

  getRefreshSchedule: () =>
    request('/trends/refresh-schedule'),

  setRefreshSchedule: (data) =>
    request('/trends/refresh-schedule', { method: 'POST', body: JSON.stringify(data) }),

  // Scripts
  generateScript: (data) =>
    request('/scripts/generate', { method: 'POST', body: JSON.stringify(data) }),

  getScriptStatus: (taskId) =>
    request(`/scripts/status/${taskId}`),

  getScript: (scriptId) =>
    request(`/scripts/${scriptId}`),

  listScripts: () =>
    request('/scripts/list'),

  scriptQA: (data) =>
    request('/scripts/qa', { method: 'POST', body: JSON.stringify(data) }),

  rewriteScript: (data) =>
    request('/scripts/rewrite', { method: 'POST', body: JSON.stringify(data) }),

  uploadNovel: async (file, params) => {
    const formData = new FormData();
    formData.append('file', file);
    if (params.episode_count) formData.append('episode_count', params.episode_count);
    if (params.genre) formData.append('genre', params.genre);
    if (params.style) formData.append('style', params.style);

    const res = await fetch(`${API_BASE}/scripts/upload-novel`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || '上传失败');
    }
    return res.json();
  },

  checkCopyright: (scriptId) =>
    request(`/scripts/${scriptId}/copyright-check`, { method: 'POST' }),

  // Config
  getConfig: () => request('/config'),
  getConfigForTopic: (topic) => request(`/config/topic/${encodeURIComponent(topic)}`),

  getRelatedTrends: (trendId) => request(`/trends/related/${trendId}`),

  // Health
  health: () => request('/health'),
};
