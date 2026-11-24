# Messaging Service

Сервис диалогов и сообщений между пользователями. По ТЗ сообщение от клиента принимает Gateway и отправляет в `messaging.in`; обработчик сохраняет его и публикует событие `message.new` для Notification.

## Запуск через Docker Compose

```powershell
docker compose up --build -d messaging-service
docker compose logs -f messaging-service
```

Контейнер использует MongoDB и RabbitMQ внутри сети Compose. Внешний порт не опубликован.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .\shared
python -m pip install -r messaging-service\requirements.txt
cd messaging-service
python -m uvicorn app.main:app --reload --port 8000
```

Настройки включают собственные `MONGODB_URL`, `RABBITMQ_URL` и `GATEWAY_SHARED_SECRET`. Messaging не получает JWT signing key: Gateway подтверждает пользователя и отправляет только проверенный UUID. Для контейнерного запуска сначала поднимите MongoDB с аутентификацией, RabbitMQ и API Gateway.
