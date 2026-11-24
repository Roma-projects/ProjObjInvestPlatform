# Внешний API платформы

Браузер обращается к тому же origin: Nginx на `http://localhost:8080` раздаёт клиент и пересылает `/api/*` в API Gateway. Gateway маршрутизирует запросы к соответствующему микросервису. Фронтенд не обращается напрямую к контейнерным портам и не дублирует бизнес-логику.

Для защищённых HTTP-методов клиент передаёт `Authorization: Bearer <access_token>`. Access JWT хранится в `sessionStorage`, refresh JWT — в HttpOnly cookie. Cookie отправляется автоматически с same-origin запросом.

## Auth

- `POST /api/auth/register` — JSON: `email`, `phone`, `password`, `password_confirm`, `first_name`, `last_name`, необязательный `patronymic`, `agree_to_terms: true`. После регистрации Auth устанавливает cookie подтверждения почты.
- `POST /api/auth/login` — JSON: `login`, `password`, `device_info`; ответ содержит `access_token`, refresh token устанавливается в HttpOnly cookie.
- `POST /api/auth/refresh` — обновить access token по refresh cookie.
- `POST /api/auth/logout` — JSON: `{ "logout_all_devices": false }`.
- `GET /api/auth/me` и `PATCH /api/auth/me` — текущий профиль; patch принимает поля профиля и `notification_preferences`.
- `POST /api/auth/me/avatar` — multipart-поле `file`; JPEG/PNG/WebP, максимум 5 МБ. Изображение проверяется и повторно кодируется Auth-сервисом.
- `POST /api/auth/verify` — JSON: `{ "type": "email", "code": "12345678" }`; requires the short-lived verification challenge cookie and allows at most five invalid codes per challenge.
- `POST /api/auth/resend-code` — JSON: `{ "type": "email" }`; требуется cookie подтверждения.
- `POST /api/auth/forgot-password` — JSON: `{ "email": "user@example.com" }`.
- `POST /api/auth/reset-password` — JSON: `token_from_email`, `new_password`, `new_password_confirm`.
- `POST /api/auth/change-password` — JSON: `current_password`, `new_password`, `new_password_confirm`.

Пароль должен содержать не менее 12 символов. В подтверждении и сбросе пароля используется проверочный код/токен, присланный Auth.

Главная проверяет состояние сессии через `POST /api/auth/refresh` (если access token отсутствует) и `GET /api/auth/me`. Выход удаляет refresh-cookie ответом Auth; сам access token очищается из `sessionStorage`.

## Listing — объявления

- `POST /api/listings` — создать черновик; JSON-схема `BusinessListingDraft` находится в `listing-service/app/schemas/business_listing.py`.
- `GET /api/listings` — список собственных объявлений.
- `GET /api/listings/{id}` — получить своё объявление. Listing проверяет владельца и не отдаёт другим пользователям исходную запись.
- `PATCH /api/listings/{id}` — сохранить изменения черновика JSON-телом.
- `DELETE /api/listings/{id}` — удалить свой черновик.
- `POST /api/listings/{id}/files/{field}` — загрузить файл multipart-полем `file`; ответы и GET Listing возвращают только имена полей закрытых документов, без путей хранения.
- `PUT /api/listings/{id}/files/photos/{index}` — заменить фотографию.
- `POST /api/listings/{id}/submit` — отправить черновик на обработку.
- Очередь и решения модерации находятся в Moderation API, Listing не отдаёт модераторам полную запись.

Эти маршруты идут в бизнес-часть Listing. Для обновления и удаления ресурса используются соответствующие HTTP-методы; безопасность обеспечивается JWT на Gateway и проверкой владельца/состояния в Listing. Устаревший `/api/v1/listings` отключён на Gateway и не включён в приложение Listing. Публичный GET разрешён только к одобренной карточке через Search (`/api/catalog/{id}`): это публичная проекция, а не исходная запись Listing и не закрытые файлы.

## Moderation — очередь и чёрный список

Все маршруты требуют access JWT пользователя с ролью `moderator`. Решения и фильтры отправляются JSON-телом; API Gateway проксирует запросы в отдельный `moderation-service`.

Низкий рейтинг AI, отсутствие сигналов риска, базовый уровень проверки и отсутствие закрытых документов позволяют опубликовать объявление автоматически. Случаи с подозрениями или углублённой проверкой остаются в ручной очереди. Модератор может снять опубликованную карточку с самой страницы объявления в каталоге.

- `GET /api/moderation/cases` — очередь ручной проверки.
- `GET /api/moderation/cases/{case_id}` — данные объявления, оба аналитических отчёта и доступные названия документов.
- `GET /api/moderation/cases/auto-releases` — последние автоматически одобренные случаи.
- `POST /api/moderation/cases/{case_id}/decision` — JSON `{ "verdict": "approve" | "reject", "reason": "...", "verification_level": "basic" | "deep" }`.
- `POST /api/moderation/catalog/{listing_id}/remove` — JSON `{ "reason": "..." }`; снимает опубликованное объявление с каталога и фиксирует причину в случае модерации.
- `GET /api/moderation/cases/{case_id}/documents/{field}` — получить закрытый файл текущего случая; файл проходит через Moderation, Listing volume не доступен браузеру.
- `GET /api/moderation/blacklist` — список активных блокировок.
- `POST /api/moderation/blacklist` — JSON `{ "user_id": "UUID", "reason": "..." }`; бан отзывает сессии и снимает все объявления с каталога.
- `DELETE /api/moderation/blacklist/{user_id}` — снять бан. Это не возвращает объявления в каталог автоматически.

## Search — каталог и поиск

Для браузерного каталога используйте POST: фильтры находятся в JSON-теле, не в query string.

- `POST /api/catalog/query` — `q`, `business_type`, `deal_composition`, `property_type`, `property_condition`, `transfer_method`, `min_price`, `max_price`, `verification_status`, `revenue_trend`, `city`, `sort`, `cursor`, `limit`. Поля категорий принимают строку или массив строк.
- `POST /api/catalog/map` — JSON-фильтры каталога; возвращает только ID, название, цену, город и координаты публичных объявлений.
- `GET /api/catalog/{listing_id}` — получить публичную карточку опубликованного объявления.
- `POST /api/search/suggest` — JSON: `{ "q": "кофейня", "limit": 10 }`.
- `GET /api/catalog` — совместимый маршрут со значениями по умолчанию; новые клиенты должны использовать POST `/query`.

Пример JSON-фильтров:

```json
{
  "q": "кофейня",
  "business_type": ["food", "hospitality"],
  "min_price": 1000000,
  "max_price": 15000000,
  "city": "Екатеринбург",
  "sort": "price_asc",
  "limit": 20
}
```

Публичный Search-индекс не содержит телефон, email, паспортные данные и закрытые документы продавца. Начать диалог можно по `seller_id` из карточки объявления.

Пример карты без фильтрации: `POST /api/catalog/map` с телом `{}`. Ответ содержит `items` (маркеры), `total` (количество точек), `unlocated` (объявления без координат) и `truncated` (если превышен лимит карты).

Карта использует координаты из публичного индекса Search. При публикации Search геокодирует адрес объекта на сервере и кэширует координату; закрытые документы и адреса, не предназначенные для каталога, не отправляются в Nominatim. Для ранее опубликованных карточек предусмотрен одноразовый backfill, описанный в [документации Search](../search-service/README.md).

## Messaging — сообщения

- `POST /api/messages` — JSON: `participant_id` (UUID собеседника), `text`, уникальный `client_message_id`. Gateway принимает сообщение асинхронно и отвечает `202 Accepted`.
- `POST /api/messages/conversations` — JSON: `{ "participant_id": "<UUID>" }`; создать или получить диалог.
- `GET /api/messages/conversations` — список диалогов.
- `GET /api/messages/conversations/{conversation_id}/messages` — история диалога.
- `POST /api/messages/read` — JSON: `{ "message_ids": ["..."] }`.
- `GET /api/notifications` — последние уведомления текущего пользователя; `POST /api/notifications/read` помечает переданные `event_ids` прочитанными.
- `POST /api/notifications/ticket` выдаёт одноразовый ticket на 30 секунд. Клиент отправляет его первым сообщением после подключения к `/ws/notifications`; в URL WebSocket нет учётных данных.

## Что пока не маршрутизируется

У Gateway пока нет отдельного HTTP API аналитики. Результаты скриптов и AI проходят через внутренние события RabbitMQ и доступны модераторам в карточке случая.
