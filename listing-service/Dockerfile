# syntax=docker/dockerfile:1.7
# Для чего нужен этот файл:
# Объясняет Docker, как собрать образ сервиса listing-service: выбрать базовый образ, установить библиотеки и запустить приложение.

# Собирает Listing API и запускает миграции перед стартом приложения.
FROM python:3.11-slim
WORKDIR /app
COPY shared /shared
RUN --mount=type=cache,target=/root/.cache/pip pip install -e /shared
COPY listing-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY listing-service/app ./app
COPY listing-service/alembic ./alembic
COPY listing-service/alembic.ini .
COPY listing-service/migration_bootstrap.py .
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home app \
    && mkdir -p /app/uploads /public_uploads /private_uploads \
    && chown -R 10001:10001 /app /public_uploads /private_uploads
USER 10001:10001
EXPOSE 8000
CMD ["sh", "-c", "python migration_bootstrap.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
