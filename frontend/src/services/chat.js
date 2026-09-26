/* Для чего нужен этот файл:
 * Содержит правила работы этой части приложения. Сервисный слой связывает API, проверку данных и хранилище.
 */

/** Chat REST + WebSocket stubs */
import { API_BASE, apiRequest } from './api';

export async function getConversations() {
  return apiRequest(API_BASE.messaging, '/api/v1/messages/conversations');
}

export async function getConversation(peerId) {
  return apiRequest(
    API_BASE.messaging,
    `/api/v1/messages/conversation/${peerId}`
  );
}

export async function sendMessage(receiverId, content) {
  return apiRequest(API_BASE.messaging, '/api/v1/messages/send', {
    method: 'POST',
    body: JSON.stringify({ receiver_id: receiverId, content }),
  });
}

/**
 * connectChat(userId, accessToken, handlers)
 * handlers: { onMessage, onAck, onError, onOpen, onClose }
 */
export function connectChat(userId, accessToken, handlers = {}) {
  const url = `ws://localhost:8004/ws/chat/${userId}?token=${encodeURIComponent(accessToken)}`;
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
