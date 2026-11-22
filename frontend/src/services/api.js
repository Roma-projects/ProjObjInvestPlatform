/** Same-origin API client. Nginx forwards /api/* directly to the API Gateway. */

export const API_BASE = Object.freeze({
  auth: '',
  listings: '',
  search: '',
  messaging: '',
  analytics: '',
  notifications: '',
  moderation: '',
});

const ACCESS_TOKEN_KEY = 'mieroventure.access_token';
let accessToken = typeof sessionStorage === 'undefined'
  ? null
  : sessionStorage.getItem(ACCESS_TOKEN_KEY);
let refreshPromise = null;

export function setAccessToken(token) {
  accessToken = token || null;
  if (typeof sessionStorage === 'undefined') return;
  if (accessToken) sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  else sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function getAccessToken() {
  return accessToken;
}

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = fetch('/api/auth/refresh', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    })
      .then(async (response) => {
        if (!response.ok) {
          setAccessToken(null);
          return null;
        }
        const data = await response.json();
        setAccessToken(data.access_token);
        return data.access_token;
      })
      .finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}

function errorMessage(body, status) {
  if (body && typeof body === 'object') {
    const detail = body.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object') {
      if (Array.isArray(detail.missing_fields)) {
        return `Заполните обязательные поля: ${detail.missing_fields.join(', ')}`;
      }
      return JSON.stringify(detail);
    }
    if (Array.isArray(body)) return body.map((item) => item.msg || item.message).filter(Boolean).join('; ');
  }
  return `Ошибка API (${status})`;
}

async function parseResponse(response) {
  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return response.json();
  const text = await response.text();
  return text ? { detail: text } : null;
}

export async function apiRequest(_baseUrl, path, options = {}) {
  const headers = new Headers(options.headers || {});
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  if (options.body && !isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  headers.set('Accept', 'application/json');
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);

  const response = await fetch(path, {
    ...options,
    headers,
    credentials: options.credentials || 'same-origin',
  });

  const isAuthEndpoint = path.startsWith('/api/auth/');
  if (response.status === 401 && !isAuthEndpoint && options.retryAuth !== false) {
    const renewed = await refreshAccessToken();
    if (renewed) return apiRequest(_baseUrl, path, { ...options, retryAuth: false });
  }

  const data = await parseResponse(response);
  if (!response.ok) {
    const error = new Error(errorMessage(data, response.status));
    error.status = response.status;
    error.detail = data?.detail;
    throw error;
  }
  return data;
}

export async function restoreSession() {
  if (accessToken) return true;
  return Boolean(await refreshAccessToken());
}

export default { API_BASE, apiRequest, getAccessToken, restoreSession, setAccessToken };
