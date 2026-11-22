/** JSON catalog queries are routed by the API Gateway to Search + Catalog. */
import { API_BASE, apiRequest } from './api.js';

export function search(filters = {}) {
  return apiRequest(API_BASE.search, '/api/catalog/query', {
    method: 'POST',
    body: JSON.stringify(filters),
  });
}

export function searchMap(filters = {}) {
  return apiRequest(API_BASE.search, '/api/catalog/map', {
    method: 'POST',
    body: JSON.stringify(filters),
  });
}

export function getPublishedListing(id) {
  return apiRequest(API_BASE.search, `/api/catalog/${encodeURIComponent(id)}`);
}

export function suggest(q, limit = 10) {
  return apiRequest(API_BASE.search, '/api/search/suggest', {
    method: 'POST',
    body: JSON.stringify({ q, limit }),
  });
}
