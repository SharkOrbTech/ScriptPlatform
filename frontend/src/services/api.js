const API_BASE = '/api';

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '请求失败');
  }
  return res.json();
}

export const api = {
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
