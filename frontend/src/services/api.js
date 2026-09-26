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
  auth: 'http://localhost:8001',
  listings: 'http://localhost:8002',
  search: 'http://localhost:8003',
  messaging: 'http://localhost:8004',
  analytics: 'http://localhost:8005',
  notifications: 'http://localhost:8006',
};

let accessToken = null;

export function setAccessToken(token) {
  accessToken = token;
}

export async function apiRequest(baseUrl, path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
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
