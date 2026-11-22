# Auth Service

Отвечает за учётные записи, проверку email, пароли, access/refresh-токены и сессии устройств. Запросы приложения проходят через API Gateway.

Auth получает `moderation.user.blacklisted` и `moderation.user.unblocked` из RabbitMQ. Блокировка помечает аккаунт, отзывает refresh-сессии и запрещает новый вход/обновление токенов. В access JWT передаётся стабильный UUID пользователя, чтобы Gateway мог блокировать уже выданные токены.

## Запуск через Docker Compose

Из корня проекта заполните `.env` по `.env.example` и задайте рабочие SMTP-параметры для регистрации с подтверждением email:

```powershell
docker compose up --build -d auth-service
docker compose logs -f auth-service
```

Проверка доступности через внешний маршрут: `http://localhost:8080/api/auth/...`. Прямой порт сервиса наружу не опубликован.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .\shared
python -m pip install -r auth-service\requirements.txt
cd auth-service
python -m uvicorn app.main:app --reload --port 8000
```

Нужны PostgreSQL, Redis и RabbitMQ. Контейнерная конфигурация читает `JWT_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `RABBITMQ_URL`, `GATEWAY_SHARED_SECRET` и SMTP-настройки `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`, `SMTP_START_TLS`. Не вставляйте пароли или токены в README.
