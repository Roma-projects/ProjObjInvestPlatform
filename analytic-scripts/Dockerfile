# syntax=docker/dockerfile:1.7
# Собирает контейнер расчётов и аналитических скриптов.
FROM python:3.11-slim
WORKDIR /app
COPY analytic-scripts/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY analytic-scripts/app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
