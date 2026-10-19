# Analytic Scripts

Независимо от AI рассчитывает финансовые метрики, динамику выручки, точки графиков и проверки согласованности данных объявления. Получает `listing.creation.started` и возвращает `listing.scripts.analysis.completed`.

## Запуск через Docker Compose

```powershell
docker compose up --build -d analytic-scripts
docker compose logs -f analytic-scripts
```

Сервис работает внутри Compose и не публикует HTTP-порт на хост.

## Зависимости и локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r analytic-scripts\requirements.txt
cd analytic-scripts
python -m uvicorn app.main:app --reload --port 8000
```

Для обработки событий необходимы `MONGODB_URL` (база `analytic_scripts_db`) и `RABBITMQ_URL`.
