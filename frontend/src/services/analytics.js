/* Для чего нужен этот файл:
 * Содержит правила работы этой части приложения. Сервисный слой связывает API, проверку данных и хранилище.
 */

/** Analytics API stubs */
import { API_BASE, apiRequest } from './api';

export async function rentEstimate(payload) {
  return apiRequest(API_BASE.analytics, '/api/v1/analytics/rent-estimate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function investmentScore(payload) {
  return apiRequest(API_BASE.analytics, '/api/v1/analytics/investment-score', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function priceHistory(listingId) {
  return apiRequest(
    API_BASE.analytics,
    `/api/v1/analytics/history/${listingId}`
  );
}

export async function retrain() {
  return apiRequest(API_BASE.analytics, '/api/v1/analytics/retrain', {
    method: 'POST',
  });
}
