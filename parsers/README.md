# Parsers

Сервис проверок по открытым российским реестрам. По ТЗ получает отдельные задания от Listing по RabbitMQ, хранит файлы и извлечённые данные в собственной MongoDB и отвечает только в очередь `reply_to` сервиса Analytic AI.

## Запуск через Docker Compose

```powershell
docker compose up --build -d parsers
docker compose logs -f parsers
```

Файлы сервиса размещаются в volume `parsers_storage`, доступном только Parsers. Прямой HTTP-порт наружу не публикуется.

Если требуется запустить только Parsers, команда Compose выше автоматически запустит MongoDB и RabbitMQ как его зависимости.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r parsers\requirements.txt
cd parsers
python -m uvicorn app.main:app --reload --port 8000
```

Сервису необходимы `MONGODB_URL`, `RABBITMQ_URL` и `PARSERS_STORAGE_DIR`. Из каталога Parsers ручной direct_mode запуск выполняется командой `python -m tests.test_run`; CLI-поля перекрывают JSON, который перекрывает `TEST_DATA` в файле runner.
