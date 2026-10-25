"""Для чего нужен этот файл:
Точка входа микросервиса search-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.rabbitmq.consumer import consumer
from app.routers import search as search_router
from app.services.search_service import search_service

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting %s", settings.service_name)
    await search_service.connect_redis()
    await consumer.start()
    yield
    await consumer.stop()
    await search_service.close()
    logger.info("Stopped %s", settings.service_name)


app = FastAPI(
    title="Search Service",
    description="Full-text search with Redis cache",
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
    return {
        "status": "ok",
        "service": settings.service_name,
        "index_size": len(search_service._index),
    }


app.include_router(search_router.router)
