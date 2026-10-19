"""Запускает health endpoint и RabbitMQ consumer для расчётного сервиса."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.consumer import consumer


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await consumer.start()
    yield
    await consumer.stop()


app = FastAPI(title="Analytic Scripts", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "analytic-scripts"}
