# Web-агрегатор недвижимости

Микросервисная платформа для размещения, поиска и анализа объектов недвижимости.

## Возможности

- Лоты с фото, характеристиками и координатами на карте
- Поиск с фильтрами и автокомплитом
- Заявки и встроенный мессенджер (REST + WebSocket)
- Оценка аренды и инвестиционный скоринг (ML + эвристики)
- JWT auth (access 15 мин / refresh 7 дней), личные кабинеты

## Архитектура

| Сервис | Порт | БД |
|--------|------|-----|
| auth-service | 8001 | auth_db |
| listing-service | 8002 | listing_db |
| search-service | 8003 | — (Redis + in-memory index) |
| messaging-service | 8004 | messaging_db |
| analytics-service | 8005 | analytics_db |
| notification-service | 8006 | — |

Инфраструктура: PostgreSQL 15, Redis 7, RabbitMQ 3 (management UI :15672).

**Docker Compose временно отключён** (весь `docker-compose.yml` закомментирован). Локальный запуск — через `Start_test.py`.

## Быстрый старт (без Docker)

### 1. Инфраструктура вручную

Поднимите локально PostgreSQL, Redis и RabbitMQ (или раскомментируйте `docker-compose.yml` только для infra).

Создайте БД:

```sql
CREATE DATABASE auth_db;
CREATE DATABASE listing_db;
CREATE DATABASE messaging_db;
CREATE DATABASE analytics_db;
```

Скрипт: `scripts/init-databases.sql`.

### 2. Переменные окружения

```bash
cp .env.example .env
# при необходимости отредактируйте *.service/.env
```

### 3. Зависимости

```bash
python -m pip install -r requirements.txt
```

### 4. Запуск

```bash
# все сервисы
python Start_test.py

# или по одному
python auth-service/Start_test.py
python listing-service/Start_test.py
python search-service/Start_test.py
python messaging-service/Start_test.py
python analytics-service/Start_test.py
python notification-service/Start_test.py
```

Makefile:

```bash
make start-all
make start-auth
make migrate
```

### 5. OpenAPI

- http://localhost:8001/docs — Auth  
- http://localhost:8002/docs — Listings  
- http://localhost:8003/docs — Search  
- http://localhost:8004/docs — Messaging  
- http://localhost:8005/docs — Analytics  
- http://localhost:8006/docs — Notifications  

Frontend-гайд: `frontend/README.md`, примеры API: `frontend/API_DOCS.md`.

## RabbitMQ topology

- Exchange `listings_events` (topic) → `search_index_queue`, `analytics_queue`
- Exchange `messages_events` (topic) → `notifications_queue`
- Exchange `notifications` (fanout) → `email_notifications_queue`

Сервисы сами объявляют exchanges/queues при старте (если брокер доступен). Без RabbitMQ/Redis сервисы стартуют с warning и продолжают работать (graceful degrade).

## Безопасность

- JWT HS256, access 15 мин, refresh 7 дней
- bcrypt 12 rounds
- CORS: `http://localhost:3000`
- Валидация входа через Pydantic v2

## Включение Docker позже

1. Раскомментируйте блоки в `docker-compose.yml`
2. `docker compose up -d --build`
3. Healthchecks и `depends_on: condition: service_healthy` уже прописаны в шаблоне

## Структура

```
real-estate-aggregator/
├── Start_test.py              # запуск всех сервисов
├── docker-compose.yml         # ЗАКОММЕНТИРОВАН
├── shared/                    # общий Python-пакет
├── auth-service/              # + Start_test.py
├── listing-service/
├── search-service/
├── messaging-service/
├── analytics-service/
├── notification-service/
├── frontend/                  # структура + docs (без UI)
└── uploads/                   # MVP хранилище фото
```

## Стек

Python 3.11+, FastAPI, SQLAlchemy 2.0 async, asyncpg, Alembic, aio-pika, Redis, Pydantic v2, scikit-learn (analytics).

## Виртуальное окружение и зависимости

Выполните команды из корневой папки проекта. Создайте окружение, активируйте его и установите все зависимости из общего `requirements.txt`.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Чтобы выйти из виртуального окружения, выполните `deactivate`.

## Git и GitHub

### Первый коммит и отправка проекта на GitHub

1. Установите Git и войдите в свой аккаунт на [GitHub](https://github.com/).
2. Создайте на GitHub новый пустой репозиторий. Если проект уже есть на компьютере, удобнее не добавлять при создании репозитория README, лицензию или `.gitignore`.
3. Откройте терминал в корневой папке проекта. Если Git-репозиторий ещё не создан, выполните:

```bash
git init
git branch -M main
```

4. Добавьте файлы и проверьте, что попадёт в коммит:

```bash
git add .
git status
```

5. Создайте первый коммит и привяжите удалённый репозиторий. Замените адрес на URL своего репозитория на GitHub:

```bash
git commit -m "Initial project commit"
git remote add origin https://github.com/ВАШЕ_ИМЯ/ИМЯ_РЕПОЗИТОРИЯ.git
git push -u origin main
```

`git add .` добавляет все изменения, кроме временного кэша, локальных виртуальных окружений и результатов сборки, указанных в `.gitignore`. Файлы `.env` намеренно включены в Git, чтобы команда могла использовать общие настройки. Добавляйте их только в приватный репозиторий и выдавайте доступ только участникам команды.

Если команда `git remote add origin ...` сообщает, что `origin` уже существует, обновите его адрес командой `git remote set-url origin https://github.com/ВАШЕ_ИМЯ/ИМЯ_РЕПОЗИТОРИЯ.git`.

### Как отправлять следующие изменения

После того как внесли изменения в файлы, выполните из корня проекта:

```bash
git pull
git status
git add .
git commit -m "Коротко описать изменения"
git push
```

`git pull` сначала загружает последние изменения из GitHub. `git status` показывает, какие файлы изменены, `git add .` подготавливает их к сохранению, `git commit` создаёт запись об изменениях, а `git push` отправляет коммиты на GitHub. Вместо `git add .` можно добавить только нужные файлы, например `git add README.md`.

### Перед тем как сделать репозиторий публичным

Сейчас файлы `.env` и другие настройки с секретами специально попадают в Git. Перед открытием репозитория обновите `.gitignore`, чтобы исключить секретные файлы, удалите их из Git и замените опубликованные пароли и ключи. Простого нового коммита с удалением `.env` недостаточно: старые коммиты остаются в истории. Сначала проверьте и очистите историю репозитория от секретов, а затем меняйте видимость на публичную. Файлы `.gitkeep` — пустые маркеры, которые позволяют Git хранить нужные пустые папки; они сами по себе секретов не содержат.
