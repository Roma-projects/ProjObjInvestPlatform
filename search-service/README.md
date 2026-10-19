# Search + Catalog Service

Индексирует только публичные поля опубликованных бизнес-объявлений в MongoDB, обслуживает фильтры и сортировку каталога, использует Redis для кэша.

## Запуск через Docker Compose

Из корня проекта:

```powershell
docker compose up --build -d search-service
docker compose logs -f search-service
```

Публичный маршрут каталога: `http://localhost:8080/api/catalog`. Порт контейнера наружу не публикуется.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r search-service\requirements.txt
cd search-service
python -m uvicorn app.main:app --reload --port 8000
```

Нужны MongoDB, Redis и RabbitMQ. Настройки: `MONGODB_URL`, `REDIS_URL`, `RABBITMQ_URL`, `GATEWAY_SHARED_SECRET`. Для поиска используется собственная база `search_catalog`.
