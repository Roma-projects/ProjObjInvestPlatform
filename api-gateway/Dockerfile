# syntax=docker/dockerfile:1.7
# Собирает контейнер API Gateway и устанавливает только его зависимости.
FROM python:3.12-slim
WORKDIR /app
COPY api-gateway/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY api-gateway/app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
