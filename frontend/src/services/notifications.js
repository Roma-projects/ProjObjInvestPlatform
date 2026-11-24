/** User-scoped notification history and read-state operations. */
import { API_BASE, apiRequest } from './api.js';

export function getNotifications() {
  return apiRequest(API_BASE.notifications, '/api/notifications?limit=50', { cache: 'no-store' });
}

export function issueNotificationTicket() {
  return apiRequest(API_BASE.notifications, '/api/notifications/ticket', { method: 'POST', cache: 'no-store' });
}

export function markNotificationsRead(eventIds) {
  return apiRequest(API_BASE.notifications, '/api/notifications/read', {
    method: 'POST',
    cache: 'no-store',
    body: JSON.stringify({ event_ids: eventIds }),
  });
}
