# Для чего нужен этот файл:
# Объясняет Docker, как собрать образ сервиса listing-service: выбрать базовый образ, установить библиотеки и запустить приложение.

# Docker временно отключён — используйте Start_test.py
FROM python:3.11-slim
WORKDIR /app
COPY shared /shared
RUN pip install --no-cache-dir -e /shared
COPY listing-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY listing-service/app ./app
COPY listing-service/alembic ./alembic
COPY listing-service/alembic.ini .
RUN mkdir -p /app/uploads
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
