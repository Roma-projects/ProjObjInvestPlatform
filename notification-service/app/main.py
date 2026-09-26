"""Для чего нужен этот файл:
Точка входа микросервиса notification-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.rabbitmq.consumer import consumer

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting %s", settings.service_name)
    await consumer.start()
    yield
    await consumer.stop()
    logger.info("Stopped %s", settings.service_name)


app = FastAPI(
    title="Notification Service",
    description="Async notifications via RabbitMQ (MVP logs)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


@app.get("/api/v1/notifications/ping")
async def ping() -> dict:
    return {"message": "notification-service ready"}
