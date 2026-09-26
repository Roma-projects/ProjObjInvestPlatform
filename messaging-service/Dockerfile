# Для чего нужен этот файл:
# Объясняет Docker, как собрать образ сервиса messaging-service: выбрать базовый образ, установить библиотеки и запустить приложение.

# Docker временно отключён — используйте Start_test.py
FROM python:3.11-slim
WORKDIR /app
COPY messaging-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY messaging-service/app ./app
COPY messaging-service/alembic ./alembic
COPY messaging-service/alembic.ini .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
