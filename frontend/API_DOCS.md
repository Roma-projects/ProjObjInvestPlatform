# API Documentation — Real Estate Aggregator

Базовый URL сервисов (локальный `Start_test.py`):

| Сервис | Base URL |
|--------|----------|
| Auth | `http://localhost:8001` |
| Listings | `http://localhost:8002` |
| Search | `http://localhost:8003` |
| Messaging | `http://localhost:8004` |
| Analytics | `http://localhost:8005` |
| Notifications | `http://localhost:8006` |

Все защищённые REST-эндпоинты требуют заголовок:

```
Authorization: Bearer <access_token>
```

---

## Auth Service (`:8001`)

### POST `/api/v1/auth/register`

```bash
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123","first_name":"Иван","last_name":"Иванов","phone":"+79001112233"}'
```

### POST `/api/v1/auth/login`

```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}'
```

Ответ:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

### POST `/api/v1/auth/refresh`

```bash
curl -X POST http://localhost:8001/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh>"}'
```

### POST `/api/v1/auth/logout`

```bash
curl -X POST http://localhost:8001/api/v1/auth/logout \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh>"}'
```

### GET `/api/v1/auth/me`

```bash
curl http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer <access>"
```

---

## Listing Service (`:8002`)

### POST `/api/v1/listings`

```bash
curl -X POST http://localhost:8002/api/v1/listings \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Квартира","description":"Описание","price":10000000,"area":45,"rooms":2,"floor":5,"address":"Москва, Тверская 1","type":"apartment","status":"active"}'
```

### GET `/api/v1/listings?page=1&page_size=20&min_price=1000000&rooms=2`

### GET `/api/v1/listings/{id}`

### PUT `/api/v1/listings/{id}`

### DELETE `/api/v1/listings/{id}`

### POST `/api/v1/listings/{id}/photos`

```bash
curl -X POST http://localhost:8002/api/v1/listings/1/photos \
  -H "Authorization: Bearer <access>" \
  -F "file=@photo.jpg" \
  -F "is_main=true"
```

Фото доступны как статика: `http://localhost:8002/uploads/...`

---

## Search Service (`:8003`)

### GET `/api/v1/search?q=москва&min_price=1000000&max_price=20000000&rooms=2&page=1`

### GET `/api/v1/search/suggest?q=квар&limit=10`

Индекс наполняется событиями RabbitMQ `listing.*` (при создании/обновлении лотов).

---

## Messaging Service (`:8004`)

### GET `/api/v1/messages/conversations`

### GET `/api/v1/messages/conversation/{user_id}`

### POST `/api/v1/messages/send`

```bash
curl -X POST http://localhost:8004/api/v1/messages/send \
  -H "Authorization: Bearer <access>" \
  -H "Content-Type: application/json" \
  -d '{"receiver_id":2,"content":"Здравствуйте!"}'
```

### WebSocket `ws://localhost:8004/ws/chat/{user_id}?token=<access>`

См. протокол в `README.md`.

---

## Analytics Service (`:8005`)

### POST `/api/v1/analytics/rent-estimate`

```bash
curl -X POST http://localhost:8005/api/v1/analytics/rent-estimate \
  -H "Content-Type: application/json" \
  -d '{"area":54,"rooms":2,"floor":7,"price":12500000,"region":"moscow","listing_id":5}'
```

### POST `/api/v1/analytics/investment-score`

```bash
curl -X POST http://localhost:8005/api/v1/analytics/investment-score \
  -H "Content-Type: application/json" \
  -d '{"price":12500000,"area":54,"rooms":2,"region":"moscow"}'
```

### GET `/api/v1/analytics/history/{listing_id}`

### POST `/api/v1/analytics/retrain`

---

## Fetch / axios примеры

```javascript
import api from './services/api';

// axios instance with interceptor
api.defaults.headers.common.Authorization = `Bearer ${accessToken}`;

await api.post('http://localhost:8001/api/v1/auth/login', {
  email: 'a@b.c',
  password: 'secret123',
});

await api.get('http://localhost:8003/api/v1/search', {
  params: { q: 'москва', rooms: 2 },
});
```
