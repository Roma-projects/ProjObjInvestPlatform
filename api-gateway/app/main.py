"""Маршрутизация внешнего API, проверка JWT и передача сообщений в RabbitMQ."""

from __future__ import annotations

import hashlib
import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4
from uuid import UUID

import aio_pika
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import Response
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("api-gateway")

_RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], 60) end
return count
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))
    app.state.rabbit_connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await app.state.rabbit_connection.channel()
    app.state.messaging_exchange = await channel.declare_exchange("messaging", aio_pika.ExchangeType.TOPIC, durable=True)
    await channel.declare_queue("messaging.in.dlq", durable=True)
    messaging_queue = await channel.declare_queue(
        "messaging.in",
        durable=True,
        arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": "messaging.in.dlq"},
    )
    await messaging_queue.bind(app.state.messaging_exchange, routing_key="message.send")
    yield
    await app.state.http.aclose()
    await app.state.redis.aclose()
    await app.state.rabbit_connection.close()


app = FastAPI(title="API Gateway", version="1.0.0", lifespan=lifespan)


def _verify_token(request: Request) -> dict:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token required")
    return payload


def _is_public_auth(method: str, path: str) -> bool:
    endpoint = path.removeprefix("/api/v1")
    public = {
        ("POST", "/auth/register"), ("POST", "/auth/login"), ("POST", "/auth/refresh"),
        ("POST", "/auth/forgot-password"), ("POST", "/auth/reset-password"),
        ("POST", "/auth/verify"), ("POST", "/auth/resend-code"),
    }
    return (method, endpoint) in public


def _service_path(path: str, prefix: str, upstream_prefix: str | None = None) -> str:
    tail = path[len(prefix):]
    return (upstream_prefix or prefix) + tail


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api-gateway"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def route_request(path: str, request: Request) -> Response:
    full_path = "/" + path
    client_ip = request.client.host if request.client else "unknown"
    bucket = hashlib.sha256(f"{client_ip}:{request.method}:{full_path}".encode()).hexdigest()
    count = await request.app.state.redis.eval(_RATE_LIMIT_SCRIPT, 1, f"gateway:rate:{bucket}")
    if count > settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "60"})

    claims = None
    if not (full_path.startswith("/auth/") or full_path.startswith("/api/v1/auth/")) or not _is_public_auth(request.method, full_path):
        claims = _verify_token(request)

    if full_path == "/messages" and request.method == "POST":
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=422, detail="Expected a JSON object")
        body.pop("user_id", None)
        body.pop("sender_id", None)
        try:
            participant_id = str(UUID(str(body.get("participant_id", ""))))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="participant_id must be a UUID") from exc
        payload = {
            "event": "message.send",
            "event_id": str(uuid4()),
            "sender_id": str(claims.get("user_id") or ""),
            "participant_id": participant_id,
            "text": body.get("text"),
            "client_message_id": body.get("client_message_id"),
            "correlation_id": request.headers.get("X-Request-ID", str(uuid4())),
        }
        if not payload["sender_id"] or not payload["text"] or not payload["client_message_id"]:
            raise HTTPException(status_code=422, detail="participant_id, text and client_message_id are required")
        if not isinstance(payload["text"], str) or not 1 <= len(payload["text"]) <= 5000:
            raise HTTPException(status_code=422, detail="text must contain 1 to 5000 characters")
        message = aio_pika.Message(
            json.dumps(payload, ensure_ascii=False).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=payload["event_id"],
        )
        await request.app.state.messaging_exchange.publish(message, routing_key="message.send", mandatory=True)
        return Response(
            content=json.dumps({"status": "accepted", "correlation_id": payload["correlation_id"]}),
            status_code=status.HTTP_202_ACCEPTED,
            media_type="application/json",
        )

    if full_path.startswith("/auth/"):
        base_url = settings.auth_url
        upstream_path = full_path
    elif full_path.startswith("/api/v1/auth/"):
        base_url = settings.auth_url
        upstream_path = full_path
    elif full_path.startswith("/v1/listings"):
        base_url = settings.listing_url
        upstream_path = "/api" + full_path
    elif full_path.startswith("/api/v1/listings"):
        base_url = settings.listing_url
        upstream_path = full_path
    elif full_path == "/listings" or full_path.startswith("/listings/"):
        base_url = settings.listing_url
        upstream_path = full_path
    elif full_path.startswith("/search"):
        base_url = settings.search_url
        upstream_path = _service_path(full_path, "/search", "/api/v1/search")
    elif full_path.startswith("/catalog"):
        base_url = settings.search_url
        upstream_path = _service_path(full_path, "/catalog", "/api/v1/search/catalog")
    elif full_path.startswith("/api/v1/search"):
        base_url = settings.search_url
        upstream_path = full_path
    elif full_path.startswith("/notifications"):
        base_url = settings.notification_url
        upstream_path = full_path
    elif full_path.startswith("/messages/"):
        base_url = settings.messaging_url
        upstream_path = full_path
    else:
        raise HTTPException(status_code=404, detail="API route not found")

    headers = {key: value for key, value in request.headers.items() if key.lower() not in {"host", "content-length", "connection"}}
    headers["X-Gateway-Token"] = settings.gateway_shared_secret
    if claims:
        headers["X-Authenticated-User-ID"] = str(claims.get("user_id") or claims.get("sub"))
        headers["X-Authenticated-User-Role"] = str(claims.get("role", "user"))
    upstream = f"{base_url}{upstream_path}"
    if request.url.query:
        upstream += "?" + request.url.query
    result = await request.app.state.http.request(
        request.method,
        upstream,
        content=await request.body(),
        headers=headers,
        cookies=request.cookies,
    )
    response_headers = {
        key: value for key, value in result.headers.items()
        if key.lower() in {"content-type", "set-cookie", "www-authenticate", "retry-after"}
    }
    return Response(content=result.content, status_code=result.status_code, headers=response_headers)
