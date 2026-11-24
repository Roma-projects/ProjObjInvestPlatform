"""Для чего нужен этот файл:
Точка входа микросервиса notification-service: создаёт FastAPI-приложение, подключает маршруты и настраивает запуск и остановку.
"""

import asyncio
import json
import logging
import secrets
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import Body, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

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


def authenticated_gateway_user(request: Request) -> str:
    gateway_token = request.headers.get("X-Gateway-Token", "")
    user_id = request.headers.get("X-Authenticated-User-ID", "")
    valid_gateway = gateway_token.isascii() and secrets.compare_digest(gateway_token, settings.gateway_shared_secret)
    if not valid_gateway or not user_id or len(user_id) > 128:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authenticated gateway request required")
    return user_id


@app.get("/notifications")
async def get_notifications(request: Request, limit: int = 50) -> JSONResponse:
    user_id = authenticated_gateway_user(request)
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    return JSONResponse(
        {"items": await notification_service.list_notifications(user_id, limit)},
        headers={"Cache-Control": "no-store"},
    )


@app.post("/notifications/ticket")
async def create_websocket_ticket(request: Request) -> JSONResponse:
    user_id = authenticated_gateway_user(request)
    return JSONResponse(
        {"ticket": await notification_service.issue_websocket_ticket(user_id), "expires_in": 30},
        headers={"Cache-Control": "no-store"},
    )


@app.post("/notifications/read")
async def mark_notifications_read(
    request: Request, event_ids: list[str] = Body(embed=True, max_length=100),
) -> JSONResponse:
    user_id = authenticated_gateway_user(request)
    if len(event_ids) > 100 or any(not event_id or len(event_id) > 128 for event_id in event_ids):
        raise HTTPException(status_code=422, detail="event_ids must contain at most 100 valid IDs")
    if event_ids:
        await notification_service.collection.update_many(
            {"user_id": user_id, "event_id": {"$in": event_ids}},
            {"$set": {"is_read": True}},
        )
    return JSONResponse({"updated": len(event_ids)}, headers={"Cache-Control": "no-store"})


def origin_is_allowed(socket: WebSocket) -> bool:
    origin = socket.headers.get("origin")
    if not origin:
        return False
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc
            or parsed.path or parsed.query or parsed.fragment or parsed.username):
        return False
    normalized_origin = f"{parsed.scheme}://{parsed.netloc}".lower()
    allowed_origins = {value.rstrip("/").lower() for value in settings.cors_origins_list}
    host = socket.headers.get("host", "").lower()
    try:
        request_host = urlsplit(f"{parsed.scheme}://{host}")
        default_port = 443 if parsed.scheme == "https" else 80
        same_origin = (
            parsed.hostname is not None
            and request_host.hostname is not None
            and parsed.hostname.lower() == request_host.hostname.lower()
            and (parsed.port or default_port) == (request_host.port or default_port)
        )
    except ValueError:
        same_origin = False
    return normalized_origin in allowed_origins or same_origin


@app.websocket("/ws/notifications")
async def notification_socket(socket: WebSocket) -> None:
    """Consumes a short-lived, single-use ticket from the first WebSocket message."""
    if not origin_is_allowed(socket):
        await socket.close(code=4403, reason="Origin not allowed")
        return
    await socket.accept()
    user_id = None
    try:
        try:
            auth_message = await asyncio.wait_for(socket.receive_text(), timeout=5)
            auth = json.loads(auth_message) if len(auth_message) <= 512 else None
        except WebSocketDisconnect:
            return
        except (asyncio.TimeoutError, ValueError, RuntimeError):
            await socket.close(code=4401, reason="Unauthorized")
            return
        if not isinstance(auth, dict) or auth.get("type") != "authenticate":
            await socket.close(code=4401, reason="Unauthorized")
            return
        user_id = await notification_service.consume_websocket_ticket(str(auth.get("ticket", "")))
        if not user_id:
            await socket.close(code=4401, reason="Unauthorized")
            return
        if not await notification_service.add_connection(user_id, socket):
            return
        await socket.send_json({"type": "ready"})
        while True:
            message = await socket.receive()
            if message["type"] == "websocket.disconnect":
                break
            await socket.close(code=4400, reason="Client messages are not supported")
            break
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if user_id:
            notification_service.remove_connection(user_id, socket)
