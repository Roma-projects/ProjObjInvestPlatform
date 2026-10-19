# Для чего нужен этот файл:
# Объясняет Docker, как собрать образ сервиса analytics-service: выбрать базовый образ, установить библиотеки и запустить приложение.

# Собирает legacy analytics-service; новый Compose-контур использует Analytic Scripts и Analytic AI.
FROM python:3.11-slim
WORKDIR /app
COPY analytics-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY analytics-service/app ./app
COPY analytics-service/alembic ./alembic
COPY analytics-service/alembic.ini .
COPY analytics-service/ml ./ml
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
