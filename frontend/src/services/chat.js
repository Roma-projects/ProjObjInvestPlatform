/** Messaging HTTP endpoints plus the notifications WebSocket. */
import { API_BASE, apiRequest, getAccessToken } from './api.js';
import { issueNotificationTicket } from './notifications.js';

export function getConversations() {
  return apiRequest(API_BASE.messaging, '/api/messages/conversations');
}

export function createConversation(participantId) {
  return apiRequest(API_BASE.messaging, '/api/messages/conversations', {
    method: 'POST',
    body: JSON.stringify({ participant_id: participantId }),
  });
}

export function getConversation(conversationId) {
  return apiRequest(
    API_BASE.messaging,
    `/api/messages/conversations/${encodeURIComponent(conversationId)}/messages`,
  );
}

export function markMessagesRead(messageIds) {
  return apiRequest(API_BASE.messaging, '/api/messages/read', {
    method: 'POST',
    body: JSON.stringify({ message_ids: messageIds }),
  });
}

export function sendMessage(participantId, text, clientMessageId = crypto.randomUUID()) {
  return apiRequest(API_BASE.messaging, '/api/messages', {
    method: 'POST',
    body: JSON.stringify({
      participant_id: participantId,
      text,
      client_message_id: clientMessageId,
    }),
  });
}

/** The access token stays in the authenticated API request; the WS URL carries no credentials. */
export async function connectNotifications(handlers = {}) {
  if (!getAccessToken()) throw new Error('Для подключения к уведомлениям войдите в аккаунт');
  const { ticket } = await issueNotificationTicket();
  if (!ticket) throw new Error('Не удалось получить ключ подключения к уведомлениям');
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const socket = new WebSocket(`${protocol}//${location.host}/ws/notifications`);
  socket.onopen = () => socket.send(JSON.stringify({ type: 'authenticate', ticket }));
  socket.onclose = (event) => handlers.onClose?.(event);
  socket.onerror = (event) => handlers.onError?.(event);
  socket.onmessage = (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch {
      handlers.onError?.(new Error('Сервер прислал некорректное событие'));
      return;
    }
    if (message?.type === 'ready') {
      handlers.onOpen?.();
      return;
    }
    if (message?.type === 'error') {
      handlers.onError?.(new Error('Не удалось подключить уведомления'));
      return;
    }
    handlers.onEvent?.(message);
  };
  return socket;
}
