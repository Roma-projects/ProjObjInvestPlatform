/* Для чего нужен этот файл:
 * Содержит правила работы этой части приложения. Сервисный слой связывает API, проверку данных и хранилище.
 */

/** Auth API stubs — register, login, refresh, logout, me */
import { API_BASE, apiRequest, setAccessToken } from './api';

export async function register(payload) {
  return apiRequest(API_BASE.auth, '/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function login(email, password) {
  const data = await apiRequest(API_BASE.auth, '/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setAccessToken(data.access_token);
  return data;
}

export async function refresh(refreshToken) {
  const data = await apiRequest(API_BASE.auth, '/api/v1/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  setAccessToken(data.access_token);
  return data;
}

export async function logout(refreshToken) {
  return apiRequest(API_BASE.auth, '/api/v1/auth/logout', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function me() {
  return apiRequest(API_BASE.auth, '/api/v1/auth/me');
}
