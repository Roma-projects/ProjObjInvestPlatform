# Для чего нужен этот файл:
# Объясняет Docker, как собрать образ сервиса auth-service: выбрать базовый образ, установить библиотеки и запустить приложение.

# FROM python:3.11-slim
# WORKDIR /app
# COPY shared /shared
# RUN pip install --no-cache-dir -e /shared
# COPY auth-service/requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY auth-service/app ./app
# COPY auth-service/alembic ./alembic
# COPY auth-service/alembic.ini .
# EXPOSE 8000
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Docker временно отключён. Локальный запуск: python Start_test.py
FROM python:3.11-slim
WORKDIR /app
# Валидный Dockerfile оставлен для будущего включения Docker.
# Сейчас compose закомментирован — используйте Start_test.py
COPY shared /shared
RUN pip install --no-cache-dir -e /shared
COPY auth-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY auth-service/app ./app
COPY auth-service/alembic ./alembic
COPY auth-service/alembic.ini .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
