# Для чего нужен этот файл:
# Объясняет Docker, как собрать образ сервиса search-service: выбрать базовый образ, установить библиотеки и запустить приложение.

# Собирает сервис каталога и устанавливает его зависимости.
FROM python:3.11-slim
WORKDIR /app
COPY search-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY search-service/app ./app
COPY search-service/scripts ./scripts
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
