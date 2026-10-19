# Analytic AI

AI-ветвь по ТЗ принимает `listing.creation.started`, анализирует ред-флаги и публичные медиа, формирует отчёты для модератора и продавца. Она работает независимо от Analytic Scripts и ждёт результаты Parsers через `ai.resume`.

## Запуск через Docker Compose

```powershell
docker compose up --build -d analytic-ai
docker compose logs -f analytic-ai
```

Настройте OpenAI-совместимый endpoint Qwen и модель в корневом `.env`. Без endpoint сервис не одобряет объявления автоматически, а возвращает консервативный отчёт для ручной проверки. Контейнер не публикует порт на хост.

Перед отдельным запуском AI-воркера поднимите инфраструктуру и его зависимости: `docker compose up -d postgres redis rabbitmq mongo parsers`. Затем команда Compose выше запустит сам сервис и необходимые зависимые контейнеры.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r analytic-ai\requirements.txt
cd analytic-ai
python -m uvicorn app.main:app --reload --port 8000
```

Для очередей и конфигурации нужны `RABBITMQ_URL`, `DATABASE_URL` (PostgreSQL), `REDIS_URL`; для модели — `QWEN_BASE_URL`, `QWEN_API_KEY` и `QWEN_MODEL`. Не запускайте обучение модели с нуля: это противоречит ТЗ.
