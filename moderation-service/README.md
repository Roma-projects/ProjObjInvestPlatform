# Moderation Service

Отдельный сервис очереди рассмотрения и чёрного списка. Использует FastAPI, SQLAlchemy async, asyncpg, PostgreSQL и RabbitMQ. Compose создаёт `moderation_db`; `create_database.py` также подготавливает эту БД, если PostgreSQL volume уже существовал до добавления сервиса.

## Поток объявления

1. Listing отправляет исходные данные в Analytic Scripts и Analytic AI. AI при необходимости вызывает Parsers; результаты возвращаются в Listing через RabbitMQ.
2. После получения обоих отчётов Listing сохраняет событие `listing.moderation.requested` в PostgreSQL outbox. В сообщении есть ограниченный снимок полей для проверки, отчёты, UUID продавца и ссылки на приватные документы.
3. Moderation фиксирует обращение в собственной PostgreSQL. Объявление публикуется автоматически, если AI вернул низкий рейтинг риска, `auto_ok` и `verification_level=basic`, не указал подозрений, все фотографии разрешены, проверки аналитических скриптов присутствуют и прошли без предупреждений, закрытых документов нет, а реестровая проверка ИП подтверждена. Любой сигнал риска, требование углублённой проверки или закрытый документ направляет случай в ручную очередь.
4. Одобренное решение публикуется через outbox как `moderation.listing.approved`. Listing меняет статус и передаёт в Search только публичные allow-listed поля. Отклонённые и заблокированные записи в Search не попадают.

Moderation не копирует байты документов и не подключает `private_uploads`. Для просмотра файла авторизованный модератор вызывает маршрут Moderation, а сервис получает его через внутренний Listing endpoint с отдельным `MODERATION_SHARED_SECRET`. Gateway не проксирует внутренний маршрут Listing.

## API через Gateway

Все маршруты ниже требуют access JWT роли `moderator`; фильтры/решения передаются JSON-телом, а не query-параметрами.

- `GET /api/moderation/cases` — очередь ручного рассмотрения.
- `GET /api/moderation/cases/{case_id}` — снимок, аналитические отчёты и перечень закрытых документов.
- `GET /api/moderation/cases/auto-releases` — последние автоматические одобрения для аудита.
- `POST /api/moderation/cases/{case_id}/decision` — JSON `{ "verdict": "approve" | "reject", "reason": "...", "verification_level": "basic" | "deep" }`.
- `POST /api/moderation/catalog/{listing_id}/remove` — JSON `{ "reason": "..." }`; модератор может снять уже опубликованное объявление с карточки каталога или из его списка контроля.
- `GET /api/moderation/cases/{case_id}/documents/{field}` — получить приватный документ для текущего случая.
- `GET /api/moderation/blacklist` — активные блокировки.
- `POST /api/moderation/blacklist` — JSON `{ "user_id": "UUID", "reason": "..." }`.
- `DELETE /api/moderation/blacklist/{user_id}` — снять блокировку.

## События RabbitMQ

Exchange `listings` (topic). Вход: `listing.moderation.requested`. Выход: `moderation.listing.approved`, `moderation.listing.rejected`, `moderation.listing.removed`, `moderation.user.blacklisted`, `moderation.user.unblocked`. Исходящие решения записываются в `moderation_outbox_events` в той же транзакции, что и изменение случая/блокировки, и повторяются с ограниченной задержкой до успешной публикации.

Блокировка сначала разрешает стабильный UUID через закрытый Auth endpoint, затем событие с UUID и legacy integer ID распространяется в Auth, Gateway, Listing, Search и Notification. Так удаляются новые бизнес-объявления и объявления старого каталога; Search запоминает оба ID, чтобы не применить запоздавшую публикацию. После разблокировки аккаунт может войти, но объявления остаются снятыми до повторной проверки.

Доступ к очереди выдаётся JWT с `role=moderator`. Роль назначает доверенный администратор в Auth-хранилище; после изменения пользователь должен войти заново, чтобы получить JWT с новой ролью. Например, в `auth_db` администратор может выполнить `UPDATE users SET role = 'moderator' WHERE email = 'moderator@example.com';`. Модератор также видит действие снятия с каталога на карточке опубликованного объявления.

## Настройки

- `DATABASE_URL` — async PostgreSQL URL для `moderation_db`.
- `RABBITMQ_URL` — брокер событий.
- `JWT_SECRET_KEY`, `JWT_ALGORITHM` — проверка moderator access JWT.
- `GATEWAY_SHARED_SECRET` — проверка запросов от Gateway.
- `MODERATION_SERVICE_SHARED_SECRET` — доступ Moderation к внутреннему Listing endpoint.
- `LISTING_URL` — внутренний URL Listing в Compose.
- `AUTH_URL` — внутренний URL Auth для разрешения UUID в ID прежнего API.

Локальный запуск после PostgreSQL и RabbitMQ: `python create_database.py`, затем `python -m uvicorn app.main:app --reload --port 8000` из каталога сервиса.
