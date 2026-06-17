"""
Notification Service main — consumes RabbitMQ events, sends email + push.
"""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.modules.notifications.models import Notification  # noqa
from app.modules.users.models import User  # noqa

Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RaktSaanchar Notification Service",
    docs_url="/api/v1/notifications/docs",
    redoc_url="/api/v1/notifications/redoc",
    openapi_url="/api/v1/notifications/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

from app.modules.notifications.routes import router as notifications_router
app.include_router(notifications_router, prefix=API_PREFIX)


@app.on_event("startup")
async def on_startup():
    """Start RabbitMQ consumer to handle notification events."""
    try:
        from app.messaging.consumer import start_consumer
        asyncio.create_task(start_consumer())
        logger.info("✅ Notification service RabbitMQ consumer started")
    except Exception as e:
        logger.warning("⚠️ Could not start RabbitMQ consumer: %s", e)


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}
