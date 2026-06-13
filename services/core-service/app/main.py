"""
Core Service — main FastAPI application
Hosts: donors, patients, blood_requests, blood_bank, coordinator, leaderboard
"""
import asyncio
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine

logger = logging.getLogger(__name__)

# ── Register all ORM models before create_all ─────────────────────────────────
from app.modules.users.models import User                              # noqa
from app.modules.donors.models import Donor                            # noqa
from app.modules.patients.models import Patient                        # noqa
from app.modules.blood_requests.models import BloodRequest             # noqa
from app.modules.leaderboard.models import Badge, DonorBadge           # noqa
from app.modules.blood_bank.models import (                            # noqa
    BloodInventory, BloodUnit, BloodValidationReport, BloodBankProfile
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="RaktSaanchar Core Domain Service",
    docs_url="/api/v1/donors/docs",
    redoc_url="/api/v1/donors/redoc",
    openapi_url="/api/v1/donors/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

from app.modules.donors.routes import router as donors_router
from app.modules.patients.routes import router as patients_router
from app.modules.blood_requests.routes import router as requests_router
from app.modules.blood_bank.routes import router as blood_bank_router
from app.modules.coordinator.routes import router as coordinator_router
from app.modules.leaderboard.routes import router as leaderboard_router

app.include_router(donors_router,      prefix=API_PREFIX)
app.include_router(patients_router,    prefix=API_PREFIX)
app.include_router(requests_router,    prefix=API_PREFIX)
app.include_router(blood_bank_router,  prefix=API_PREFIX)
app.include_router(coordinator_router, prefix=API_PREFIX)
app.include_router(leaderboard_router, prefix=API_PREFIX)


@app.on_event("startup")
async def on_startup():
    """
    1. Run idempotent schema migrations (ADD COLUMN IF NOT EXISTS).
    2. Seed default badges.
    3. Start RabbitMQ consumer to cache user.registered events.
    """
    from sqlalchemy import text
    from app.core.database import SessionLocal
    from app.modules.leaderboard.service import LeaderboardService

    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE donors ADD COLUMN IF NOT EXISTS response_rate FLOAT DEFAULT 1.0;"))
        db.execute(text("ALTER TABLE donors ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE donors ADD COLUMN IF NOT EXISTS no_show_count INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE donors ADD COLUMN IF NOT EXISTS latitude FLOAT;"))
        db.execute(text("ALTER TABLE donors ADD COLUMN IF NOT EXISTS longitude FLOAT;"))
        db.execute(text("ALTER TABLE patients ADD COLUMN IF NOT EXISTS latitude FLOAT;"))
        db.execute(text("ALTER TABLE patients ADD COLUMN IF NOT EXISTS longitude FLOAT;"))
        db.execute(text("ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS assigned_blood_bank_id INTEGER;"))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS blood_validation_reports (
                id SERIAL PRIMARY KEY,
                unit_id INTEGER NOT NULL UNIQUE,
                donor_id INTEGER NOT NULL,
                hemoglobin_g_dl FLOAT NOT NULL,
                systolic_bp INTEGER,
                diastolic_bp INTEGER,
                pulse_bpm INTEGER,
                status VARCHAR NOT NULL,
                issue_category VARCHAR,
                feedback_notes TEXT,
                improvement_recommendations TEXT,
                report_pdf_path VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES blood_units(id) ON DELETE CASCADE,
                FOREIGN KEY (donor_id) REFERENCES donors(id) ON DELETE CASCADE
            );
        """))
        db.execute(text("ALTER TABLE blood_validation_reports ADD COLUMN IF NOT EXISTS report_pdf_path VARCHAR;"))
        db.commit()
        LeaderboardService(db).seed_badges()
        os.makedirs("/app/uploads/validation_reports", exist_ok=True)
    except Exception as e:
        db.rollback()
        logger.warning("Startup migration warning: %s", e)
    finally:
        db.close()

    # Start RabbitMQ consumer (best-effort)
    try:
        from app.messaging.consumer import start_consumer
        asyncio.create_task(start_consumer())
    except Exception as e:
        logger.warning("Could not start RabbitMQ consumer: %s", e)


@app.get("/")
def root():
    return {"service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/health")
def health():
    return {"status": "ok", "service": "core-service"}
