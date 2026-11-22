FROM python:3.11-slim
WORKDIR /app
COPY moderation-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY moderation-service/app ./app
COPY moderation-service/create_database.py ./create_database.py
EXPOSE 8000
CMD ["sh", "-c", "python create_database.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

