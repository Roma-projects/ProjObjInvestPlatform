"""Запускает health endpoint, MongoDB индексы и consumer очереди Parsers."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.storage import MongoStorage
from app.worker import ParserQueueConsumer

settings = get_settings()
storage = MongoStorage()
consumer = ParserQueueConsumer(storage)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await storage.connect()
    await consumer.start(settings.rabbitmq_url)
    yield
    await consumer.stop()
    await storage.close()


app = FastAPI(title="Parsers", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "parsers"}
