"""
ML Service main — donor ranking and geospatial map data.
Exposes HTTP endpoints called by core-service.
Models (.pkl) are mounted from the host via Docker volume.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RaktSaanchar ML Service — Serverless Inference API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.modules.ml.routes import router as ml_router
from app.modules.transfusion.routes import router as transfusion_router
from app.modules.iron_overload.routes import router as iron_overload_router

# Direct routing for serverless endpoints
app.include_router(ml_router)
app.include_router(transfusion_router)
app.include_router(iron_overload_router)


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok", "service": "ml-service"}
