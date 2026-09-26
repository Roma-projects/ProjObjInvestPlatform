# Frontend — Web-агрегатор недвижимости

## Описание проекта

Клиентская часть **Web-агрегатора недвижимости**: размещение лотов с фото и картой, поиск и фильтры, заявки владельцам, встроенный мессенджер, оценка аренды и инвестиционный скоринг, личные кабинеты.

Backend уже реализован как набор микросервисов (FastAPI). Эта папка — **каркас для фронтенд-команды**: структура каталогов, API-документация и stub-клиенты. Полная UI-реализация здесь не делается.

## Цели фронтенда

1. Каталог и карта объектов
2. Карточка лота + аналитика (аренда / инвестиции / история цен)
3. Auth (регистрация, логин, refresh JWT)
4. Личный кабинет владельца (CRUD лотов, фото)
5. Чат (REST история + WebSocket realtime)

## Рекомендуемый стек

| Слой | Рекомендации |
|------|----------------|
| Framework | **React 18+** или Vue 3 / Angular 17+ |
| Язык | **TypeScript** |
| Сборка | Vite |
| Стили | TailwindCSS или SCSS (+ CSS variables в `src/styles`) |
| Состояние | Zustand / Redux Toolkit / Pinia |
| HTTP | axios или fetch-обёртка (`src/services/api.js`) |
| Карты | Leaflet / Mapbox / Yandex Maps |
| Роутинг | React Router / Vue Router |

## Структура папок

```
frontend/
├── public/                 # статика (favicon и т.п.)
├── src/
│   ├── assets/             # изображения, шрифты, иконки
│   ├── components/
│   │   ├── common/         # кнопки, инпуты, модалки
│   │   ├── listings/       # карточки лотов, формы
│   │   ├── map/            # карта и маркеры
│   │   ├── chat/           # UI чата
│   │   └── auth/           # формы входа/регистрации
│   ├── pages/
│   │   ├── Home/           # главная: карта + список
│   │   ├── Listing/        # страница лота
│   │   ├── Auth/           # вход/регистрация
│   │   ├── Dashboard/      # личный кабинет
│   │   └── Chat/           # мессенджер
│   ├── services/           # API-клиенты (stubs)
│   ├── store/              # глобальное состояние
│   ├── hooks/              # кастомные хуки
│   ├── utils/              # хелперы
│   ├── styles/             # variables / reset / global
│   ├── router/             # маршруты
│   └── App.js              # корневой компонент (stub)
├── index.html
├── package.json
├── vite.config.js
├── API_DOCS.md             # примеры запросов
└── README.md               # этот файл
```

## API документация (Swagger)

Пока Docker отключён, сервисы поднимаются через `Start_test.py`:

| Сервис | Docs |
|--------|------|
| Auth | http://localhost:8001/docs |
| Listings | http://localhost:8002/docs |
| Search | http://localhost:8003/docs |
| Messaging | http://localhost:8004/docs |
| Analytics | http://localhost:8005/docs |
| Notifications | http://localhost:8006/docs |

Подробные примеры curl/fetch: [API_DOCS.md](./API_DOCS.md).

## JWT авторизация (базовый пример)

```javascript
// 1. Логин
const loginRes = await fetch('http://localhost:8001/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'user@example.com', password: 'secret123' }),
});
const { access_token, refresh_token } = await loginRes.json();

// 2. Защищённый запрос
const me = await fetch('http://localhost:8001/api/v1/auth/me', {
  headers: { Authorization: `Bearer ${access_token}` },
});

// 3. Refresh (access живёт 15 минут)
const refreshed = await fetch('http://localhost:8001/api/v1/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh_token }),
});
```

Храните `access_token` в memory / sessionStorage, `refresh_token` — в httpOnly cookie (предпочтительно) или secure storage.

## WebSocket протокол чата

**URL:** `ws://localhost:8004/ws/chat/{user_id}?token={access_token}`

Клиент → сервер:

```json
{ "type": "ping" }
```

```json
{ "type": "send", "receiver_id": 2, "content": "Здравствуйте! Интересует квартира." }
```

Сервер → клиент:

```json
{ "type": "pong" }
```

```json
{
  "type": "message",
  "data": {
    "id": 10,
    "sender_id": 1,
    "receiver_id": 2,
    "content": "Здравствуйте!",
    "status": "sent",
    "created_at": "2026-09-26T12:00:00Z",
    "read_at": null
  }
}
```

```json
{ "type": "message_ack", "data": { "...": "то же сообщение" } }
```

```json
{ "type": "error", "detail": "..." }
```

При невалидном токене соединение закрывается с кодом `4401`.

## Примеры JSON ответов

**User (GET /auth/me):**

```json
{
  "id": 1,
  "email": "owner@example.com",
  "first_name": "Иван",
  "last_name": "Петров",
  "phone": "+79001234567",
  "is_active": true,
  "created_at": "2026-09-26T10:00:00Z",
  "updated_at": "2026-09-26T10:00:00Z"
}
```

**Listing:**

```json
{
  "id": 5,
  "owner_id": 1,
  "title": "2-к квартира у метро",
  "description": "Светлая квартира",
  "price": 12500000,
  "area": 54.5,
  "rooms": 2,
  "floor": 7,
  "address": "Москва, ул. Примерная, 1",
  "lat": 55.75,
  "lng": 37.62,
  "type": "apartment",
  "status": "active",
  "created_at": "2026-09-26T11:00:00Z",
  "updated_at": "2026-09-26T11:00:00Z",
  "photos": [{ "id": 1, "listing_id": 5, "url": "/uploads/5/abc.jpg", "is_main": true }]
}
```

**Rent estimate:**

```json
{
  "rent_estimate": "65000.00",
  "currency": "RUB",
  "model_version": "1.0.0",
  "method": "heuristic_area"
}
```

## CORS

Backend разрешает origin `http://localhost:3000` (см. `CORS_ORIGINS`). Запускайте dev-сервер на порту **3000** или обновите `.env` сервисов.

## Запуск и разработка

```bash
# 1. Backend (из корня real-estate-aggregator)
pip install -r auth-service/requirements.txt  # и остальные сервисы / shared
python Start_test.py

# 2. Frontend (когда команда заполнит package.json)
cd frontend
npm install
npm run dev   # ожидаемо http://localhost:3000
```

Сейчас `package.json` и `vite.config.js` — плейсхолдеры. Фронтенд-команда выбирает стек и заполняет зависимости.

## Контакты / согласование API

При изменении контрактов обновляйте `API_DOCS.md` и OpenAPI (`/docs`) соответствующего сервиса.
