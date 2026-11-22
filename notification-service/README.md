# Notification Service

Сохраняет уведомления в MongoDB и передаёт их только внутри сайта через авторизованный WebSocket. Email/SMS/push в этом сервисе не отправляются.

## Запуск через Docker Compose

```powershell
docker compose up --build -d notification-service
docker compose logs -f notification-service
```

WebSocket доступен снаружи через Nginx по `ws://localhost:8080/ws/notifications`; клиент передаёт access JWT. HTTP-порт контейнера не публикуется.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r notification-service\requirements.txt
cd notification-service
python -m uvicorn app.main:app --reload --port 8000
```

Нужны MongoDB (`MONGODB_URL`), RabbitMQ (`RABBITMQ_URL`) и тот же JWT secret/algorithm, что и у Auth (`JWT_SECRET_KEY`, `JWT_ALGORITHM`).

Notification хранит активные blacklist UUID в собственной MongoDB, закрывает уже открытые WebSocket-соединения по `moderation.user.blacklisted` и отклоняет новые соединения заблокированного пользователя. Событие `moderation.user.unblocked` снимает ограничение на WebSocket.
