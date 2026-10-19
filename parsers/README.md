# Parsers

Сервис проверок по открытым российским реестрам. По ТЗ получает отдельные задания от Listing по RabbitMQ, хранит файлы и извлечённые данные в собственной MongoDB и отвечает только в очередь `reply_to` сервиса Analytic AI.

## Запуск через Docker Compose

```powershell
docker compose up --build -d parsers
docker compose logs -f parsers
```

Файлы сервиса размещаются в volume `parsers_storage`, доступном только Parsers. Прямой HTTP-порт наружу не публикуется. MongoDB доступна тестовому runner на `localhost:27017` и привязана только к loopback-интерфейсу.

Для скачивания PDF-выписок из ЕГРЮЛ/ЕГРИП и «Прозрачного бизнеса» контейнер устанавливает Chromium для Playwright. Браузер запускается внутри контейнера от отдельного непривилегированного пользователя. HTML страницы поиска не сохраняются как документы; сохраняются только PDF/XML/ZIP-файлы.

При запросе обоих источников сначала проверяется ЕГРЮЛ. «Прозрачный бизнес» запускается как резервный источник только при ошибке ЕГРЮЛ. Для изолированной проверки PB укажите только `--sources pb`.

Если требуется запустить только Parsers, команда Compose выше автоматически запустит MongoDB и RabbitMQ как его зависимости.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r parsers\requirements.txt
python -m playwright install chromium
cd parsers
python -m uvicorn app.main:app --reload --port 8000
```

Сервису необходимы `MONGODB_URL`, `RABBITMQ_URL` и `PARSERS_STORAGE_DIR`. Для локального runner сначала поднимите MongoDB из Compose, затем запустите тест из корня проекта:

```powershell
docker compose up -d mongo
$env:PYTHONPATH = "$PWD\parsers"
python -m parsers.tests.test_run
```

Можно проверить отдельный источник, например только выписки ФНС:

```powershell
python -m parsers.tests.test_run --sources egrul pb
```

CLI-поля перекрывают JSON, который перекрывает `TEST_DATA` в файле runner.
