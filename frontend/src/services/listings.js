/* Для чего нужен этот файл:
 * Содержит правила работы этой части приложения. Сервисный слой связывает API, проверку данных и хранилище.
 */

/** Запросы фронтенда для создания, чтения, обновления и загрузки объявлений. */
import { API_BASE, apiRequest } from './api';

export async function createListing(payload) {
  return apiRequest(API_BASE.listings, '/api/v1/listings', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getListings(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return apiRequest(API_BASE.listings, `/api/v1/listings?${qs}`);
}

export async function getListing(id) {
  return apiRequest(API_BASE.listings, `/api/v1/listings/${id}`);
}

export async function updateListing(id, payload) {
  return apiRequest(API_BASE.listings, `/api/v1/listings/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteListing(id) {
  return apiRequest(API_BASE.listings, `/api/v1/listings/${id}`, {
    method: 'DELETE',
  });
}

/** Загружает файл в закрытый API Listing; поле задаёт тип документа или медиа. */
export async function uploadListingFile(listingId, field, file) {
  const form = new FormData();
  form.append('file', file);
  return apiRequest(API_BASE.listings, `/api/v1/listings/${listingId}/files/${encodeURIComponent(field)}`, {
    method: 'POST',
    body: form,
  });
}
