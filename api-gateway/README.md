# API Gateway

Единая точка входа API: проверяет access JWT, ограничивает частоту запросов, направляет HTTP-запросы к Auth/Listing/Search и отправляет новые сообщения в RabbitMQ.

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

Для локального запуска должны быть доступны Redis, RabbitMQ и сервисы Auth, Listing, Search. В контейнере их адреса заданы в Compose. Основные настройки: `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `GATEWAY_SHARED_SECRET`, `REDIS_URL`, `RABBITMQ_URL`, `AUTH_URL`, `LISTING_URL`, `SEARCH_URL`, `NOTIFICATION_URL`.
