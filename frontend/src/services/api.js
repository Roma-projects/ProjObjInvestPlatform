/* Для чего нужен этот файл:
 * Содержит правила работы этой части приложения. Сервисный слой связывает API, проверку данных и хранилище.
 */

/**
 * Базовый HTTP-клиент (stub).
 * Фронтенд-команда: заменить на axios/fetch wrapper.
 *
 * Порты бэкенда:
 *  auth 8001 | listings 8002 | search 8003
 *  messaging 8004 | analytics 8005 | notifications 8006
 */

export const API_BASE = {
  // Браузер ходит только в Nginx; он пересылает API в Gateway.
  auth: 'http://localhost:8080',
  listings: 'http://localhost:8080',
  search: 'http://localhost:8080',
  messaging: 'http://localhost:8080',
  analytics: 'http://localhost:8080',
  notifications: 'http://localhost:8080',
};

let accessToken = null;

export function setAccessToken(token) {
  accessToken = token;
}

export async function apiRequest(baseUrl, path, options = {}) {
  const headers = { ...(options.headers || {}) };
  // Для JSON указываем формат явно; FormData сам добавит multipart boundary.
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  const res = await fetch(`${baseUrl}${path}`, { ...options, headers });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export default { API_BASE, setAccessToken, apiRequest };
