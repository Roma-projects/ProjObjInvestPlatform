# Listing Service

Хранит черновики и опубликованные объявления, проверяет поля формы, сохраняет загруженные файлы и публикует события через RabbitMQ. Частные документы находятся в `private_uploads`, публичные изображения — в `public_uploads`.

## Запуск через Docker Compose

Из корня проекта:

```powershell
docker compose up --build -d listing-service
docker compose logs -f listing-service
```

Для запуска полного набора сервисов используйте `docker compose up --build -d`. В Compose Listing получает отдельную БД `listing_db`, оба файловых volume и соединение с RabbitMQ. `MODERATION_SERVICE_SHARED_SECRET` должен совпадать с секретом Moderation.

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

После получения обоих аналитических отчётов Listing пишет в outbox `listing.moderation.requested` с ограниченным снимком объявления, отчётами и ссылками на закрытые документы. Публичную запись в Search Listing создаёт после решения о публикации от Moderation: чистый случай с низким рейтингом AI и базовой проверкой проходит автоматически, риск или углублённая проверка требуют ручного решения. Модератор может снять опубликованное объявление событием `moderation.listing.removed`. Очередь и решения находятся на маршрутах `/api/moderation/*` у `moderation-service`; Listing больше не выдаёт модератору свою полную запись через внешний API.

Владелец через Gateway может читать только свои объявления. GET Listing возвращает список имён прикреплённых полей без путей хранения. Посетителям публичный GET к Listing недоступен: каталог читает Search из публичной проекции уже одобренных объявлений.

Для чтения закрытого файла Moderation вызывает `GET /internal/listings/{listing_id}/documents/{field}` внутри сети Compose с `X-Moderation-Token`. Этот маршрут проверяет поле и путь в базе Listing; Nginx и API Gateway его не проксируют. Только Moderation может отдать файл модератору после проверки JWT и роли.
