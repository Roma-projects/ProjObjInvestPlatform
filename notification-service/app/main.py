"""Для чего нужен этот файл:
Точка входа микросервиса notification-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.config import get_settings
from app.rabbitmq.consumer import consumer
from app.services.notification_service import notification_service

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting %s", settings.service_name)
    await notification_service.connect()
    await consumer.start()
    yield
    await consumer.stop()
    await notification_service.close()
    logger.info("Stopped %s", settings.service_name)


app = FastAPI(
    title="Notification Service",
    description="Доставляет уведомления пользователям в реальном времени через WebSocket.",
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
    return {"message": "notification-service ready", "delivery": "in-app-websocket"}


@app.websocket("/ws/notifications")
async def notification_socket(socket: WebSocket) -> None:
    """Authenticates a WebSocket from its short-lived JWT access token."""
    token = socket.query_params.get("token")
    try:
        claims = jwt.decode(token or "", settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = str(claims.get("user_id") or claims.get("sub"))
        if claims.get("type") != "access" or not user_id:
            raise JWTError("Invalid access token")
    except JWTError:
        await socket.close(code=4401, reason="Unauthorized")
        return
    await notification_service.add_connection(user_id, socket)
    try:
        # Acknowledgements let offline notifications stay unread until the client receives them.
        while True:
            incoming = await socket.receive_json()
            if incoming.get("type") == "ack" and incoming.get("event_id"):
                await notification_service.mark_read(user_id, str(incoming["event_id"]))
    except WebSocketDisconnect:
        notification_service.remove_connection(user_id, socket)
