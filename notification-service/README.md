# Notification Service

Сохраняет уведомления в MongoDB и передаёт их только внутри сайта через авторизованный WebSocket. Email/SMS/push в этом сервисе не отправляются.

## Запуск через Docker Compose

```powershell
docker compose up --build -d notification-service
docker compose logs -f notification-service
```

WebSocket доступен снаружи через Nginx по `/ws/notifications`; HTTP-порт контейнера не публикуется. Браузер запрашивает короткоживущий одноразовый ticket через авторизованный API Gateway и передаёт его первым WebSocket-сообщением, поэтому в URL сокета нет ни access JWT, ни ticket. До проверки ticket сервер не отправляет данные и закрывает неавторизованное соединение через 5 секунд. Nginx отключает access log для WebSocket.

Compose публикует сайт по HTTP для локальной разработки. HTTP и `ws://` не шифруют трафик. Для внешнего доступа разместите перед Nginx TLS-терминатор с действительным сертификатом и открывайте сайт только по HTTPS: клиент автоматически выберет `wss://`. Один лишь WebSocket handshake не заменяет TLS.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r notification-service\requirements.txt
cd notification-service
python -m uvicorn app.main:app --reload --port 8000
```

Нужны отдельные MongoDB (`MONGODB_URL`) и RabbitMQ (`RABBITMQ_URL`) credentials, а также `GATEWAY_SHARED_SECRET`, выделенный только Notification. Через Gateway сервис получает проверенный user ID; прямые запросы без внутреннего секрета и идентификатора отклоняются.

Notification хранит активные blacklist UUID в собственной MongoDB, закрывает уже открытые WebSocket-соединения по `moderation.user.blacklisted` и отклоняет новые соединения заблокированного пользователя. Событие `moderation.user.unblocked` снимает ограничение на WebSocket.
