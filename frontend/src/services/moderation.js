/** Moderator-only APIs are routed by API Gateway to moderation-service. */
import { API_BASE, apiRequest, getAccessToken } from './api.js';

const root = '/api/moderation';

export function getModerationCases() {
  return apiRequest(API_BASE.moderation, `${root}/cases`);
}

export function getModerationCase(caseId) {
  return apiRequest(API_BASE.moderation, `${root}/cases/${encodeURIComponent(caseId)}`);
}

export function getAutoReleaseHistory() {
  return apiRequest(API_BASE.moderation, `${root}/cases/auto-releases`);
}

export function decideModerationCase(caseId, verdict, reason, verificationLevel = 'basic') {
  return apiRequest(API_BASE.moderation, `${root}/cases/${encodeURIComponent(caseId)}/decision`, {
    method: 'POST',
    body: JSON.stringify({ verdict, reason: reason || null, verification_level: verificationLevel }),
  });
}

export function removeFromCatalog(listingId, reason) {
  return apiRequest(API_BASE.moderation, `${root}/catalog/${encodeURIComponent(listingId)}/remove`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

export function getBlacklist() {
  return apiRequest(API_BASE.moderation, `${root}/blacklist`);
}

export function addToBlacklist(userId, reason) {
  return apiRequest(API_BASE.moderation, `${root}/blacklist`, {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, reason }),
  });
}

export function removeFromBlacklist(userId) {
  return apiRequest(API_BASE.moderation, `${root}/blacklist/${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
}

export async function openModerationDocument(caseId, field) {
  const viewer = window.open('about:blank', '_blank');
  if (!viewer) throw new Error('Разрешите открытие вкладки для просмотра документа.');
  viewer.opener = null;
  try {
    const headers = new Headers();
    const token = getAccessToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const response = await fetch(
      `${root}/cases/${encodeURIComponent(caseId)}/documents/${encodeURIComponent(field)}`,
      { headers, credentials: 'same-origin' },
    );
    if (!response.ok) {
      viewer.close();
      throw new Error(`Не удалось получить документ (${response.status}).`);
    }
    const url = URL.createObjectURL(await response.blob());
    viewer.location.href = url;
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (error) {
    if (!viewer.closed) viewer.close();
    throw error;
  }
}

