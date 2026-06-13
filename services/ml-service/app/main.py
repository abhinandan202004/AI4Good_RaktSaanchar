"""
ML Service main — donor ranking and geospatial map data.
Exposes HTTP endpoints called by core-service.
Models (.pkl) are mounted from the host via Docker volume.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine

# ML service only reads from core schema (donors, patients, blood_requests)
# It doesn't create its own tables; Base.metadata.create_all is a no-op here
# because all referenced tables live in the core schema.

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RaktSaanchar ML Service — donor ranking and GeoJSON map data",
    docs_url="/api/v1/ml/docs",
    redoc_url="/api/v1/ml/redoc",
    openapi_url="/api/v1/ml/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

from app.modules.ml.routes import router as ml_router
from app.modules.transfusion.routes import router as transfusion_router

app.include_router(ml_router,         prefix=API_PREFIX)
app.include_router(transfusion_router, prefix=API_PREFIX)


@app.on_event("startup")
async def on_startup():
    """Pre-load the ML model at startup to avoid cold-start latency."""
    from app.modules.ml.service import _load_model
    _load_model()


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok", "service": "ml-service"}


@app.get("/internal/rank-donors")
def internal_rank_donors(
    blood_group: str,
    urgency: str = "medium",
    units_required: int = 1,
    patient_city: str = "",
    patient_lat: float = 0.0,
    patient_lon: float = 0.0,
    limit: int = 10,
):
    """
    Internal endpoint called by core-service to get ranked donor list.
    Not exposed via the Nginx gateway (internal Docker network only).
    """
    from app.core.database import SessionLocal
    from app.modules.ml.service import rank_donors

    db = SessionLocal()
    try:
        donors = rank_donors(
            db=db,
            patient_blood_group=blood_group,
            urgency=urgency,
            units_required=units_required,
            patient_city=patient_city or None,
            patient_latitude=patient_lat or None,
            patient_longitude=patient_lon or None,
            limit=limit,
        )
        return {"donors": donors}
    finally:
        db.close()
