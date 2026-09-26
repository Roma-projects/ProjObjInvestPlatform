/* Для чего нужен этот файл:
 * Содержит правила работы этой части приложения. Сервисный слой связывает API, проверку данных и хранилище.
 */

/** Search API stubs */
import { API_BASE, apiRequest } from './api';

export async function search(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return apiRequest(API_BASE.search, `/api/v1/search?${qs}`);
}

export async function suggest(q, limit = 10) {
  const qs = new URLSearchParams({ q, limit }).toString();
  return apiRequest(API_BASE.search, `/api/v1/search/suggest?${qs}`);
}
