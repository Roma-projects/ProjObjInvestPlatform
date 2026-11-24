# syntax=docker/dockerfile:1.7
# Для чего нужен этот файл:
# Объясняет Docker, как собрать образ сервиса auth-service: выбрать базовый образ, установить библиотеки и запустить приложение.

# Собирает Auth API и применяет миграции перед запуском приложения.
FROM python:3.11-slim
WORKDIR /app
COPY shared /shared
RUN --mount=type=cache,target=/root/.cache/pip pip install -e /shared
COPY auth-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY auth-service/app ./app
COPY auth-service/app/templates ./app/templates
COPY auth-service/alembic ./alembic
COPY auth-service/alembic.ini .
COPY auth-service/migration_bootstrap.py .
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home app \
    && mkdir -p /auth_avatars \
    && chown -R 10001:10001 /app /auth_avatars
USER 10001:10001
EXPOSE 8000
CMD ["sh", "-c", "python migration_bootstrap.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
