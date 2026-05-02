const API_BASE = '';

async function apiFetch(path, options = {}) {
  const res = await fetch(API_BASE + '/api' + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

const api = {
  getPrice: () => apiFetch('/price'),
  getBalance: () => apiFetch('/balance'),
  getBotStatus: () => apiFetch('/bot/status'),
  startBot: () => apiFetch('/bot/start', { method: 'POST' }),
  stopBot: () => apiFetch('/bot/stop', { method: 'POST' }),
  getTrades: (limit = 100, offset = 0) => apiFetch(`/trades?limit=${limit}&offset=${offset}`),
  getAssetHistory: (days = 30) => apiFetch(`/assets/history?days=${days}`),
  getLogs: (limit = 200) => apiFetch(`/logs?limit=${limit}`),
  getSettings: () => apiFetch('/settings'),
  updateSettings: (data) => apiFetch('/settings', { method: 'PUT', body: JSON.stringify(data) }),
  getRules: () => apiFetch('/rules'),
  updateRules: (content) => apiFetch('/rules', { method: 'PUT', body: JSON.stringify({ content }) }),
};
