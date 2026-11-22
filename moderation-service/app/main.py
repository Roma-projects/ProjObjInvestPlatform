import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.config import get_settings
from app.database import engine, init_db
from app.rabbitmq.consumer import consumer
from app.rabbitmq.publisher import publisher
from app.routers import moderation as moderation_router
from app.services.outbox import run_outbox_dispatcher

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(settings.service_name)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await publisher.connect()
    await consumer.start()
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(90, connect=5))
    stop = asyncio.Event()
    dispatcher = asyncio.create_task(run_outbox_dispatcher(stop))
    yield
    stop.set()
    await dispatcher
    await consumer.stop()
    await publisher.close()
    await app.state.http.aclose()
    await engine.dispose()


app = FastAPI(title="Moderation Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


app.include_router(moderation_router.router)

