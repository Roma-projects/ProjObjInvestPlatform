/** Listing API is routed by the API Gateway to the Listing microservice. */
import { API_BASE, apiRequest } from './api.js';

export function createListing(payload) {
  return apiRequest(API_BASE.listings, '/api/listings', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function getListings() {
  return apiRequest(API_BASE.listings, '/api/listings');
}

export function getListing(id) {
  return apiRequest(API_BASE.listings, `/api/listings/${encodeURIComponent(id)}`);
}

export function updateListing(id, payload) {
  return apiRequest(API_BASE.listings, `/api/listings/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function deleteListing(id) {
  return apiRequest(API_BASE.listings, `/api/listings/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
}

export function submitListing(id) {
  return apiRequest(API_BASE.listings, `/api/listings/${encodeURIComponent(id)}/submit`, {
    method: 'POST',
  });
}

/** Uploads one file to the visibility class selected by the Listing service. */
export function uploadListingFile(listingId, field, file) {
  const form = new FormData();
  form.append('file', file);
  return apiRequest(
    API_BASE.listings,
    `/api/listings/${encodeURIComponent(listingId)}/files/${encodeURIComponent(field)}`,
    { method: 'POST', body: form },
  );
}

/** Replaces an uploaded public photo while keeping the original gallery position. */
export function replaceListingPhoto(listingId, index, file) {
  const form = new FormData();
  form.append('file', file);
  return apiRequest(
    API_BASE.listings,
    `/api/listings/${encodeURIComponent(listingId)}/files/photos/${index}`,
    { method: 'PUT', body: form },
  );
}
