/* Для чего нужен этот файл:
 * Содержит правила работы этой части приложения. Сервисный слой связывает API, проверку данных и хранилище.
 */

/** Listings API stubs */
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
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteListing(id) {
  return apiRequest(API_BASE.listings, `/api/v1/listings/${id}`, {
    method: 'DELETE',
  });
}

/** uploadPhoto — использовать FormData + fetch вручную (multipart) */
export async function uploadPhoto(listingId, file, isMain = false) {
  // TODO: multipart FormData implementation
  console.warn('uploadPhoto stub', listingId, file, isMain);
}
