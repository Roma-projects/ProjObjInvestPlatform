# Внешний API платформы

Все HTTP-запросы из браузера направляются в Nginx на `http://localhost:8080`. Nginx удаляет начальный `/api/` и пересылает запрос в API Gateway. Защищённые методы требуют `Authorization: Bearer <access_token>`.

## Auth

Создание пользователя: `POST /api/auth/register`. Тело включает `email`, `phone`, `password`, `password_confirm`, `first_name`, `last_name` и `agree_to_terms: true`. После регистрации Auth отправляет код подтверждения, если SMTP настроен.

Вход: `POST /api/auth/login` с `login` и `password`. Ответ содержит короткоживущий access token; refresh token хранится в защищённой cookie. Другие маршруты профиля, восстановления пароля и сессий описаны в OpenAPI Auth.

## Объявления

- `POST /api/v1/listings` — создать черновик объявления.
- `GET /api/v1/listings` — список собственных объявлений с курсором.
- `GET /api/v1/listings/{id}` — получить своё объявление.
- `PATCH /api/v1/listings/{id}` — изменить черновик.
- `POST /api/v1/listings/{id}/files/{field}` — загрузить один файл как multipart-поле `file`.
- `POST /api/v1/listings/{id}/submit` — отправить объявление на анализ и модерацию.
- `GET /api/v1/listings/moderation/queue` — получить очередь (только модератор).
- `POST /api/v1/listings/{id}/moderation-decision` — принять `approve` или `reject` (только модератор).

Внешний путь для объявлений Gateway преобразует в `/api/v1/listings` сервиса Listing. Содержание черновика проверяется строгой схемой Pydantic; точный перечень полей задаёт `BusinessListingDraft`.

## Каталог

- `GET /api/catalog` — публичный каталог. Поддерживает фильтры `q`, `business_type`, `min_price`, `max_price`, `verification_status`, `sort`, `cursor` и `limit`.
- `GET /api/search/suggest?q=...` — подсказки поиска.

## Сообщения и уведомления

- `POST /api/messages` — отправить сообщение. Тело: `participant_id` (UUID собеседника), `text` и уникальный `client_message_id`. Gateway возвращает `202 Accepted`, так как запись выполняется асинхронно.
- `GET /api/messages/conversations` — список диалогов; необязательные `filter=all|unread`, `cursor` и `limit`.
- `GET /api/messages/conversations/{conversation_id}/messages` — история диалога.
- `ws://localhost:8080/ws/notifications?token=<access_token>` — WebSocket с уведомлениями пользователя.

Публичные изображения доступны через `/public/uploads/`. Частные документы не выдаются через Nginx.
