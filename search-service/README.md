# Search + Catalog Service

Индексирует только публичные поля опубликованных бизнес-объявлений в MongoDB, обслуживает фильтры и сортировку каталога, использует Redis для кэша.

## Запуск через Docker Compose

Из корня проекта:

```powershell
docker compose up --build -d search-service
docker compose logs -f search-service
```

Публичные маршруты Search + Catalog идут через API Gateway: `POST http://localhost:8080/api/catalog/query` принимает JSON фильтры, `GET /api/catalog/{listing_id}` отдаёт одну опубликованную карточку, `POST /api/search/suggest` принимает поисковую строку в JSON. Совместимый `GET /api/catalog` оставлен для старых клиентов. Порт контейнера наружу не публикуется.

Search принимает в каталог только `listing.creation.completed` от Listing. Событие `moderation.user.blacklisted` сохраняет блокировку продавца в MongoDB и удаляет все его карточки; параллельно Search отклоняет запоздавшие события публикации. Снятие блокировки не восстанавливает удалённые карточки автоматически.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r search-service\requirements.txt
cd search-service
python -m uvicorn app.main:app --reload --port 8000
```

Нужны MongoDB, Redis и RabbitMQ. Настройки: `MONGODB_URL`, `REDIS_URL`, `RABBITMQ_URL`, `GATEWAY_SHARED_SECRET`. Для поиска используется собственная база `search_catalog`.
