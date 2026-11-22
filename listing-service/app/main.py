"""Для чего нужен этот файл:
Точка входа микросервиса listing-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.rabbitmq.publisher import publisher
from app.rabbitmq.results_consumer import results_consumer
from app.rabbitmq.moderation_consumer import moderation_consumer
from app.routers import listings as listings_router
from app.routers import business_listings as business_listings_router
from app.services.business_listing_service import run_outbox_dispatcher

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting %s", settings.service_name)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.public_upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.private_upload_dir).mkdir(parents=True, exist_ok=True)
    try:
        await init_db()
    except Exception as exc:
        logger.warning("DB init failed: %s", exc)
    await publisher.connect()
    await results_consumer.start()
    await moderation_consumer.start()
    stop_dispatcher = asyncio.Event()
    dispatcher_task = asyncio.create_task(run_outbox_dispatcher(stop_dispatcher))
    yield
    stop_dispatcher.set()
    await dispatcher_task
    await results_consumer.stop()
    await moderation_consumer.stop()
    await publisher.close()
    logger.info("Stopped %s", settings.service_name)


app = FastAPI(
    title="Listing Service",
    description="Listings and photo uploads",
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


app.include_router(listings_router.router)
app.include_router(business_listings_router.router)
app.include_router(business_listings_router.internal_router)
