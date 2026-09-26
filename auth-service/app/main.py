"""Для чего нужен этот файл:
Точка входа микросервиса auth-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.exceptions import AppError
from app.routers import auth as auth_router

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
    yield
    logger.info("Shutting down %s", settings.service_name)


app = FastAPI(
    title="Auth Service",
    description="JWT authentication for Real Estate Aggregator",
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


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


app.include_router(auth_router.router)
