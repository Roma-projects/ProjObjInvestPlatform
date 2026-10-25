/* Для чего нужен этот файл:
 * Содержит правила работы этой части приложения. Сервисный слой связывает API, проверку данных и хранилище.
 */

/** Чтение истории сообщений и WebSocket-уведомления о новых событиях. */
import { API_BASE, apiRequest } from './api';

export async function getConversations() {
  return apiRequest(API_BASE.messaging, '/api/messages/conversations');
}

export async function getConversation(peerId) {
  return apiRequest(
    API_BASE.messaging,
    `/api/messages/conversations/${peerId}/messages`
  );
}

export async function sendMessage(receiverId, content, clientMessageId = crypto.randomUUID()) {
  return apiRequest(API_BASE.messaging, '/api/messages', {
    method: 'POST',
    body: JSON.stringify({ participant_id: receiverId, text: content, client_message_id: clientMessageId }),
  });
}

/**
 * connectChat(userId, accessToken, handlers)
 * handlers: { onMessage, onAck, onError, onOpen, onClose }
 */
export function connectChat(userId, accessToken, handlers = {}) {
  const url = `ws://localhost:8080/ws/notifications?token=${encodeURIComponent(accessToken)}`;
  const ws = new WebSocket(url);
  ws.onopen = () => handlers.onOpen?.();
  ws.onclose = (e) => handlers.onClose?.(e);
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'message') handlers.onMessage?.(data.data);
    else if (data.type === 'message_ack') handlers.onAck?.(data.data);
    else if (data.type === 'error') handlers.onError?.(data.detail);
  };
  return ws;
}
