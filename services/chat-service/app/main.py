"""
Chat Service main — WebSocket chat + REST endpoints + RabbitMQ consumer.
"""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.modules.chat.models import ChatRoom, ChatMessage  # noqa

Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RaktSaanchar Chat Service — Real-time WebSocket chat",
    docs_url="/api/v1/chat/docs",
    redoc_url="/api/v1/chat/redoc",
    openapi_url="/api/v1/chat/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

from app.modules.chat.routes import router as chat_router
app.include_router(chat_router, prefix=API_PREFIX)


@app.on_event("startup")
async def on_startup():
    """Start RabbitMQ consumer to auto-create chat rooms on blood_request.accepted."""
    try:
        from app.messaging.consumer import start_consumer
        asyncio.create_task(start_consumer())
        logger.info("✅ Chat service RabbitMQ consumer started")
    except Exception as e:
        logger.warning("⚠️ Could not start RabbitMQ consumer: %s", e)


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok", "service": "chat-service"}
