/** Auth endpoints are routed by the API Gateway to the Auth microservice. */
import { API_BASE, apiRequest, setAccessToken } from './api.js';

export async function register(payload) {
  return apiRequest(API_BASE.auth, '/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function login(loginName, password) {
  const data = await apiRequest(API_BASE.auth, '/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      login: loginName,
      password,
      device_info: { user_agent: navigator.userAgent, device_name: 'Веб-браузер' },
    }),
  });
  setAccessToken(data.access_token);
  return data;
}

export async function refresh() {
  const data = await apiRequest(API_BASE.auth, '/api/auth/refresh', { method: 'POST' });
  setAccessToken(data.access_token);
  return data;
}

export async function logout(logoutAllDevices = false) {
  try {
    const sendLogout = () => apiRequest(API_BASE.auth, '/api/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ logout_all_devices: logoutAllDevices }),
    });
    try {
      return await sendLogout();
    } catch (error) {
      if (error.status !== 401) throw error;
      await refresh();
      return await sendLogout();
    }
  } finally {
    setAccessToken(null);
  }
}

export function me() {
  return apiRequest(API_BASE.auth, '/api/auth/me');
}

export function updateProfile(payload) {
  return apiRequest(API_BASE.auth, '/api/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function verifyEmail(code) {
  return apiRequest(API_BASE.auth, '/api/auth/verify', {
    method: 'POST',
    body: JSON.stringify({ type: 'email', code }),
  });
}

export function resendVerificationCode() {
  return apiRequest(API_BASE.auth, '/api/auth/resend-code', {
    method: 'POST',
    body: JSON.stringify({ type: 'email' }),
  });
}

export function requestPasswordReset(email) {
  return apiRequest(API_BASE.auth, '/api/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(payload) {
  return apiRequest(API_BASE.auth, '/api/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
