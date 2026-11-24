# syntax=docker/dockerfile:1.7
# Для чего нужен этот файл:
# Объясняет Docker, как собрать образ сервиса notification-service: выбрать базовый образ, установить библиотеки и запустить приложение.

# Собирает сервис уведомлений и устанавливает его зависимости.
FROM python:3.11-slim
WORKDIR /app
COPY notification-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY notification-service/app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
