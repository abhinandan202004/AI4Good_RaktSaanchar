"""
Chatbot Service main
- Runs the chatbot/AI assistant independently
- Queries core-service via REST instead of direct DB access
- Session management via Redis
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RaktSaanchar AI Chatbot Service",
    docs_url="/api/v1/chatbot/docs",
    redoc_url="/api/v1/chatbot/redoc",
    openapi_url="/api/v1/chatbot/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

from app.modules.chatbot.routes import router as chatbot_router
app.include_router(chatbot_router, prefix=API_PREFIX)


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok", "service": "chatbot-service"}
