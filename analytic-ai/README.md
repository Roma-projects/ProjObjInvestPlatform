# Analytic AI

AI-ветвь принимает событие Listing, анализирует фото и финансовые показатели и возвращает `listing.ai.analysis.completed`. По умолчанию использует совместимый с OpenAI API endpoint Polza и `google/gemini-3.8-flash`. Парсеры получают отдельное задание через `parsers.tasks`; ответ Parsers ждёт очередь `ai.reply.<correlation_id>`, после чего AI публикует итог Listing.

## Настройка окружения

Скопируйте `.env.example` в `analytic-ai/.env` и внесите секрет `POLZA_API_KEY`. Файл `.env` игнорируется Git и передаётся контейнеру через Compose `env_file`; он не копируется в Docker image. Для всех примеров в репозитории остаются только `.env.example`.

В корне также нужны локальные `.env` файлы из корневого и сервисных шаблонов. Секреты RabbitMQ, PostgreSQL и JWT должны быть одинаковыми в корневом `.env` и в соответствующих строках сервисных файлов. При развёртывании на отдельных машинах задайте каждому сервису доступные по сети адреса RabbitMQ, Redis, MongoDB и PostgreSQL в переменных окружения. Имена `rabbitmq`, `mongo`, `redis`, `postgres` работают только внутри Compose-сети.

## Запуск Compose

```powershell
docker compose up --build -d postgres redis rabbitmq mongo parsers analytic-ai
docker compose logs -f analytic-ai parsers
```

## Тест полного потока Parsers → Analytic AI

Тестовый JSON `tests/registry_then_ai.json` содержит финансовые поля и предыдущие тестовые значения ИНН/ФИО. Сценарий публикует запрос в RabbitMQ, ожидает результат работающего Parsers и только после этого передаёт отчёт в AI. Требуются запущенные `rabbitmq`, `mongo`, `parsers`, настроенный `analytic-ai/.env` и установленный пакет `analytic-ai/requirements.txt`.

Из корня проекта в PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r analytic-ai\requirements.txt
python analytic-ai\tests\run_registry_then_ai.py
```

Результат создаётся в `analytic-ai/tests/registry_then_ai_result.json`. Документ считается достаточным только если хотя бы один источник его скачал, а извлечённый текст подтверждает ФИО, ИНН и статус ИП. Если совпадения не подтверждены, AI возвращает `requires_moderation`. Тест обращается к сайтам реестров и внешнему API модели.

Для сценариев модерации фотографий используйте `tests/run_rabbit_scenarios.py`; он создаёт JSON-результаты и HTML/Markdown-отчёт в той же директории. API-ключ читается из переменных окружения или локального `analytic-ai/.env` и не печатается.
