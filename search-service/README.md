# Search + Catalog Service

Индексирует только публичные поля опубликованных бизнес-объявлений в MongoDB, обслуживает фильтры и сортировку каталога, использует Redis для кэша.

## Запуск через Docker Compose

Из корня проекта:

```powershell
docker compose up --build -d search-service
docker compose logs -f search-service
```

Публичные маршруты Search + Catalog идут через API Gateway: `POST http://localhost:8080/api/catalog/query` принимает JSON фильтры, `POST /api/catalog/map` возвращает только координаты и название/цену опубликованных карточек, `GET /api/catalog/{listing_id}` отдаёт одну опубликованную карточку, `POST /api/search/suggest` принимает поисковую строку в JSON. Совместимый `GET /api/catalog` оставлен для старых клиентов. Порт контейнера наружу не публикуется.

Search принимает в каталог только `listing.creation.completed` от Listing. Событие `moderation.user.blacklisted` сохраняет блокировку продавца в MongoDB и удаляет все его карточки; параллельно Search отклоняет запоздавшие события публикации. Снятие блокировки не восстанавливает удалённые карточки автоматически.

## Геокодирование и карта

При событии публикации Search сначала использует переданные координаты, если они валидны. Если координат нет, он геокодирует только публичный адрес бизнеса через Nominatim, сохраняет GeoJSON-точку в MongoDB и не повторяет уже закэшированный запрос. Закрытые документы и данные продавца в Nominatim не отправляются. Ограничитель в Redis выдерживает не менее 1,1 секунды между запросами для всех экземпляров Search; при недоступном Redis включается локальный ограничитель. Геокодирование — необязательное обогащение и не задерживает отказом публикацию каталога.

Настройки задаются в `search-service/.env`: `NOMINATIM_BASE_URL` позволяет переключить провайдера, `NOMINATIM_USER_AGENT` идентифицирует приложение, `NOMINATIM_ENABLED=false` отключает геокодирование. Для уже опубликованных карточек предусмотрен ручной одноразовый backfill. Сначала запускайте просмотр количества, затем при необходимости ограниченную обработку:

```powershell
cd search-service
python -m scripts.geocode_existing_catalog
python -m scripts.geocode_existing_catalog --execute --limit 100
```

Для Compose запуск выглядит так же после сборки нового образа: `docker compose exec search-service python -m scripts.geocode_existing_catalog --execute --limit 100`.

Скрипт работает последовательно, ограничивает частоту, кэширует ответы, по умолчанию ничего не меняет и обрабатывает не более 100 записей за запуск; увеличивать лимит стоит только для небольшого контролируемого каталога. Автоматический массовый опрос Nominatim при старте сервиса не выполняется.

`POST /api/catalog/map` принимает те же основные фильтры JSON, что каталог, и отдаёт только геокодированные публичные точки (до 2000 за ответ), счётчик объявлений без координат и признак усечения. Точки без улицы/дома помечаются как привязка к городу. Карта в браузере использует Leaflet и стандартные тайлы OSM; атрибуция видна внизу карты. URL тайлов переключается через meta `miero-map-tiles` в HTML страниц.

Публичный Nominatim не имеет SLA, ограничивает использование максимумом 1 запроса в секунду и требует уникальный User-Agent, кэширование и явную атрибуцию OSM. Для постоянного большого потока геокодирования следует развернуть собственный Nominatim или переключить провайдера на совместимый endpoint. См. [политику Nominatim](https://operations.osmfoundation.org/policies/nominatim/) и [политику тайлов](https://operations.osmfoundation.org/policies/tiles/).

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r search-service\requirements.txt
cd search-service
python -m uvicorn app.main:app --reload --port 8000
```

Нужны MongoDB, Redis и RabbitMQ. Настройки: `MONGODB_URL`, `REDIS_URL`, `RABBITMQ_URL`, `GATEWAY_SHARED_SECRET`, `NOMINATIM_*`. Для поиска используется собственная база `search_catalog`.
