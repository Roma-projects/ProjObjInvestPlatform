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

## Тестовый JSON и Markdown-отчёт

`tests/rabbit_listing_started.json` — пример события `listing.creation.started`, похожего на сообщение Listing в RabbitMQ. Поля сверены с `_data_for_analytics()` и моделью `BusinessListing` сервиса Listing. Служебные поля объявления, адрес, контакты и документы в расчёты не передаются. Расчёты используют финансовые показатели, состав расходов, персонал, оборудование и сезонность.

`validate_input()` оставляет только поддерживаемые аналитические поля. Если тип поля или вложенного значения неверный, оно заменяется на `null` (Python `None`); неизвестные поля игнорируются. Для проверки логики и генерации отчёта из примера RabbitMQ подключение к брокеру и MongoDB не требуется:

```powershell
python analytic-scripts\tests\render_report.py
```

Скрипт создаст `analytic-scripts/tests/analytic_report.md` со сводкой и `analytic-scripts/tests/analytic_report.html` с интерактивными графиками Plotly (линии, круговая диаграмма расходов, сезонность, шкала окупаемости и таблица проверок). HTML автономный: графическая библиотека встроена в него, интернет для просмотра не требуется. Чтобы оформить фактический JSON-ответ сервиса, сохраните его в файл и передайте:

```powershell
python analytic-scripts\tests\render_report.py --result analytic-scripts\tests\response.json
```

## Запуск тестового расчёта

### Через venv (без RabbitMQ)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r analytic-scripts\requirements.txt
python analytic-scripts\tests\render_report.py
```

### Через Docker

```powershell
docker compose build analytic-scripts
docker compose run --rm -v "${PWD}/analytic-scripts/tests:/tests" analytic-scripts sh -c "PYTHONPATH=/app python /tests/render_report.py --input /tests/rabbit_listing_started.json --output /tests/analytic_report.md"
```

Для самого мини-скрипта подключение RabbitMQ и MongoDB не требуется; Compose при `run` может запустить зависимости сервиса. Для обработки реальных событий запустите `docker compose up --build -d analytic-scripts`. Для сборки тестового отчёта через Docker в образе нужна Plotly (установится из обновлённого `requirements.txt`); команда `docker compose build analytic-scripts` пересоберёт образ.
