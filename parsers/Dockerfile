# Собирает контейнер Parsers; данные реестров сохраняются в отдельном Docker volume.
FROM python:3.11-slim
WORKDIR /app
COPY parsers/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY parsers/app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
