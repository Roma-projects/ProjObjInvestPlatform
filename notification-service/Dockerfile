# syntax=docker/dockerfile:1.7
# Для чего нужен этот файл:
# Объясняет Docker, как собрать образ сервиса notification-service: выбрать базовый образ, установить библиотеки и запустить приложение.

# Собирает сервис уведомлений и устанавливает его зависимости.
FROM python:3.11-slim
WORKDIR /app
COPY notification-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY notification-service/app ./app
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home app \
    && chown -R 10001:10001 /app
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "4096"]
