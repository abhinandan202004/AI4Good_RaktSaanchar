from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chat import router as chat_router

app = FastAPI(
    title="RaktaSanchaar Chatbot",
    version="1.0.0",
    description="Multilingual AI Chatbot for RaktaSanchaar"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routes
app.include_router(chat_router)


@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "RaktaSanchaar Chatbot"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }