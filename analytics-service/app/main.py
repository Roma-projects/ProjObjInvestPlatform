"""Для чего нужен этот файл:
Точка входа микросервиса analytics-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.rabbitmq.consumer import consumer
from app.routers import analytics as analytics_router

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting %s", settings.service_name)
    try:
        await init_db()
    except Exception as exc:
        logger.warning("DB init failed: %s", exc)
    await consumer.start()
    yield
    await consumer.stop()
    logger.info("Stopped %s", settings.service_name)


app = FastAPI(
    title="Analytics Service",
    description="Rent estimates, investment scoring, price history",
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


app.include_router(analytics_router.router)
