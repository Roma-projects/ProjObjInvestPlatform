# Собирает изолированный контейнер AI-аналитики с её собственными Python-зависимостями.
FROM python:3.11-slim
WORKDIR /app
COPY analytic-ai/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY analytic-ai/app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
