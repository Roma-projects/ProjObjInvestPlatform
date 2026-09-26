"""Для чего нужен этот файл:
Точка входа микросервиса messaging-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.rabbitmq.publisher import message_publisher
from app.routers import messages as messages_router
from app.websocket import endpoints as ws_endpoints

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
    await message_publisher.connect()
    yield
    await message_publisher.close()
    logger.info("Stopped %s", settings.service_name)


app = FastAPI(
    title="Messaging Service",
    description="REST + WebSocket chat",
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


app.include_router(messages_router.router)
app.include_router(ws_endpoints.router)
