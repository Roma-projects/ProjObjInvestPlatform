/** Messaging HTTP endpoints plus the notifications WebSocket. */
import { API_BASE, apiRequest, getAccessToken } from './api.js';

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

/** Browser WebSocket APIs cannot set Authorization headers, so this handshake uses the documented token query. */
export function connectNotifications(handlers = {}) {
  const token = getAccessToken();
  if (!token) throw new Error('Для подключения к уведомлениям войдите в аккаунт');
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${location.host}/ws/notifications?token=${encodeURIComponent(token)}`;
  const socket = new WebSocket(url);
  socket.onopen = () => handlers.onOpen?.();
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
    handlers.onEvent?.(message);
  };
  return socket;
}
