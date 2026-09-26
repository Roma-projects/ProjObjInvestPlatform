"""Для чего нужен этот файл:
Точка входа микросервиса listing-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.rabbitmq.publisher import publisher
from app.routers import listings as listings_router

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
    try:
        await init_db()
    except Exception as exc:
        logger.warning("DB init failed: %s", exc)
    await publisher.connect()
    yield
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

uploads_path = Path(settings.upload_dir)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


app.include_router(listings_router.router)
