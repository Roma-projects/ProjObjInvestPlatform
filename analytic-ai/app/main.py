"""Запускает Analytic AI, его отдельную PostgreSQL и очереди RabbitMQ."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.consumer import AIConsumer
from app.database import initialize_database

consumer = AIConsumer()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await initialize_database()
    await consumer.start()
    yield
    await consumer.stop()


app = FastAPI(title="Analytic AI", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "analytic-ai"}
