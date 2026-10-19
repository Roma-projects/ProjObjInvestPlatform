# Listing Service

Хранит черновики и опубликованные объявления, проверяет поля формы, сохраняет загруженные файлы и публикует события через RabbitMQ. Частные документы находятся в `private_uploads`, публичные изображения — в `public_uploads`.

## Запуск через Docker Compose

Из корня проекта:

```powershell
docker compose up --build -d listing-service
docker compose logs -f listing-service
```

Для запуска полного набора сервисов используйте `docker compose up --build -d`. В Compose Listing получает отдельную БД `listing_db`, оба файловых volume и соединение с RabbitMQ.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .\shared
python -m pip install -r listing-service\requirements.txt
cd listing-service
python -m uvicorn app.main:app --reload --port 8000
```

Для ручного запуска настройте `DATABASE_URL`, `JWT_SECRET_KEY`, `RABBITMQ_URL`, `PUBLIC_UPLOAD_DIR`, `PRIVATE_UPLOAD_DIR` и `GATEWAY_SHARED_SECRET`. Миграции для контейнера запускает `migration_bootstrap.py`; не удаляйте PostgreSQL volume при обычном обновлении кода.

Модератор получает очередь через `GET /api/v1/listings/moderation/queue`, затем отправляет `POST /api/v1/listings/{listing_id}/moderation-decision` с `approve` или `reject`. Оба endpoint доступны только роли `moderator`, которую Gateway переносит из подписанного access JWT. Роль хранится в пользователе Auth; присваивайте её только доверенным сотрудникам.
