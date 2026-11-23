# Auth Service

Отвечает за учётные записи, проверку email, пароли, access/refresh-токены и сессии устройств. Запросы приложения проходят через API Gateway.

Auth получает `moderation.user.blacklisted` и `moderation.user.unblocked` из RabbitMQ. Блокировка помечает аккаунт, отзывает refresh-сессии и запрещает новый вход/обновление токенов. В access JWT передаётся стабильный UUID пользователя, чтобы Gateway мог блокировать уже выданные токены.

Фото профиля загружается владельцем через `POST /api/auth/me/avatar` (JPEG, PNG или WebP, до 5 МБ). Auth проверяет и перекодирует изображение в PNG, хранит его в отдельном volume `auth_avatars`; только Nginx имеет read-only доступ к файлам. Путь аватара нельзя установить через JSON PATCH профиля.

## Запуск через Docker Compose

При запуске через Compose заполните SMTP-переменные в корневом `.env` по корневому `.env.example`. Для локального запуска Auth заполните SMTP-переменные в `auth-service/.env` по этому `.env.example`.

### SMTP для кодов подтверждения

Для личного Gmail включите двухэтапную проверку, создайте [пароль приложения](https://support.google.com/accounts/answer/185833) в Google Account и задайте:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-address@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_ADDRESS=your-address@gmail.com
SMTP_START_TLS=true
```

Пароль приложения — отдельный пароль SMTP, не пароль от Google; вставьте его в `.env` без пробелов. Google отзывает пароли приложений при смене пароля аккаунта и ограничивает объём отправки (обычный лимит Gmail — до 500 писем в сутки; параметры сервера: [справка Gmail SMTP](https://support.google.com/mail/answer/7104828?hl=en)). Для транзакционных писем можно использовать Brevo: `SMTP_HOST=smtp-relay.brevo.com`, порт `587`, `SMTP_USER` из SMTP-настроек Brevo, `SMTP_PASSWORD` — SMTP key (не API key), `SMTP_FROM_ADDRESS` — подтверждённый отправитель, `SMTP_START_TLS=true`. Следуйте [инструкции SMTP Brevo](https://help.brevo.com/hc/en-us/articles/7924908994450-Send-transactional-emails-using-Brevo-SMTP); бесплатный план ограничен [300 письмами в день](https://help.brevo.com/hc/en-us/articles/208580669-FAQs-What-are-the-limits-of-the-Free-plan) и требует подтверждения домена/отправителя.

SMTP-клиент не предоставляет почтовый ящик или квоту отправки. [go-simple-mail](https://github.com/xhit/go-simple-mail) — Go-библиотека SMTP-клиента, поэтому она не заменит провайдера и не подходит как зависимость этого Python-сервиса. [EmailBomber](https://github.com/SagarBiswas-MultiHAT/EmailBomber) — скрипт автоматизированной отправки через Gmail, а не транзакционный почтовый сервис. Auth использует уже подключённую `aiosmtplib`, а Redis ограничивает адрес одним письмом в минуту и пятью письмами в час для защиты от злоупотреблений.

Запуск после заполнения SMTP-переменных:

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
