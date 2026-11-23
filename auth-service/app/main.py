"""Для чего нужен этот файл:
Точка входа микросервиса auth-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.exceptions import AppError
from app.routers import identity as identity_router
from app.routers import internal as internal_router
from app.rabbitmq.moderation_consumer import moderation_consumer
from app.rabbitmq.publisher import publisher as auth_publisher

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
        logger.info("Database schema ready")
    except Exception as exc:
        logger.warning("DB init skipped/failed (start PostgreSQL): %s", exc)
    try:
        await auth_publisher.connect()
    except Exception as exc:
        logger.warning("RabbitMQ unavailable during startup: %s", exc)
    try:
        await moderation_consumer.start()
    except Exception as exc:
        logger.warning("Moderation blacklist consumer unavailable during startup: %s", exc)
    yield
    await auth_publisher.close()
    await moderation_consumer.stop()
    logger.info("Shutting down %s", settings.service_name)


app = FastAPI(
    title="Auth Service",
    description="JWT authentication for Real Estate Aggregator",
    version="0.1.0",
    lifespan=lifespan,
)

@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


app.include_router(identity_router.router)
app.include_router(internal_router.router)
