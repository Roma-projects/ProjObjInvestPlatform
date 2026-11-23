# API Gateway

Единая точка входа API: проверяет access JWT, ограничивает частоту запросов, направляет HTTP-запросы к Auth/Listing/Search/Moderation и отправляет новые сообщения в RabbitMQ. События блокировки из Moderation синхронизируют Redis-проверку access JWT, поэтому уже выданный токен перестаёт давать доступ после получения события.

Публичные маршруты каталога и подсказок поиска не требуют JWT: `GET /api/catalog`, `GET /api/catalog/{listing_id}`, `POST /api/catalog/query`, `POST /api/catalog/map` и `POST /api/search/suggest`. Поиск и фильтры передавайте JSON-телом; маршруты `/api/auth/*` используют контракты Auth-сервиса, а приватные маршруты объявлений и сообщений требуют Bearer access token.

## Запуск через Docker Compose

Из корня репозитория сначала заполните корневой `.env` по образцу `.env.example`, затем выполните:

```powershell
docker compose up --build -d api-gateway
docker compose logs -f api-gateway
```

Gateway доступен через Nginx по `http://localhost:8080/api/`. Отдельный порт хоста не публикуется.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r api-gateway\requirements.txt
cd api-gateway
python -m uvicorn app.main:app --reload --port 8000
```

Для локального запуска должны быть доступны Redis, RabbitMQ и сервисы Auth, Listing, Search, Moderation. В контейнере их адреса заданы в Compose. Основные настройки: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `GATEWAY_SHARED_SECRET`, `REDIS_URL`, `RABBITMQ_URL`, `AUTH_URL`, `LISTING_URL`, `SEARCH_URL`, `MODERATION_URL`, `NOTIFICATION_URL`.

Маршруты `/api/moderation/*` доступны только JWT с ролью `moderator` и направляются в `moderation-service`. Gateway не публикует `/internal/listings/*`; этот внутренний маршрут Listing разрешает только сервисный секрет Moderation. Старые `/api/v1/auth/*` и `/api/v1/listings/*` маршруты отключены.
