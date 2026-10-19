# Analytics Service (legacy)

Этот сервис содержит прежние расчёты оценки аренды и инвестиционного скоринга для недвижимости. Он сохранён ради существующего API и отделён от нового по ТЗ сервиса Analytic Scripts.

## Запуск через Docker Compose

Legacy-сервис не запускается вместе с основным контуром, но доступен как Compose-профиль `legacy`. Он нужен только старым сценариям расчёта аренды и недвижимости:

```powershell
docker compose --profile legacy up --build -d analytics-service
docker compose logs -f analytics-service
```

Остановить legacy-контейнер можно командой `docker compose --profile legacy stop analytics-service`.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .\shared
python -m pip install -r analytics-service\requirements.txt
cd analytics-service
python -m uvicorn app.main:app --reload --port 8000
```

Для старого сервиса требуется PostgreSQL с конфигурацией `DATABASE_URL`, RabbitMQ (`RABBITMQ_URL`) и при наличии обученная модель из `ML_MODEL_PATH`.
