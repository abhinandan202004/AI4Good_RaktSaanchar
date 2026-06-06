from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine

# ── Import ALL models so SQLAlchemy registers them before create_all ──────────
from app.modules.users.models import User                          # noqa
from app.modules.donors.models import Donor                        # noqa
from app.modules.patients.models import Patient                    # noqa
from app.modules.blood_requests.models import BloodRequest         # noqa
from app.modules.notifications.models import Notification          # noqa
from app.modules.chat.models import ChatRoom, ChatMessage          # noqa
from app.modules.leaderboard.models import Badge, DonorBadge      # noqa
from app.modules.blood_bank.models import BloodInventory, BloodUnit, BloodValidationReport, BloodBankProfile  # noqa
from app.modules.transfusion.models import TransfusionPrediction  # noqa

# ── Create all tables ─────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered blood donation and coordination platform",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

from app.modules.auth.routes import router as auth_router
from app.modules.users.routes import router as users_router
from app.modules.donors.routes import router as donors_router
from app.modules.patients.routes import router as patients_router
from app.modules.blood_requests.routes import router as requests_router
from app.modules.notifications.routes import router as notifications_router
from app.modules.chat.routes import router as chat_router
from app.modules.blood_bank.routes import router as blood_bank_router
from app.modules.coordinator.routes import router as coordinator_router
from app.modules.ml.routes import router as ml_router
from app.modules.leaderboard.routes import router as leaderboard_router
from app.modules.transfusion.routes import router as transfusion_router
from app.modules.chatbot.routes import router as chatbot_router

app.include_router(auth_router,          prefix=API_PREFIX)
app.include_router(users_router,         prefix=API_PREFIX)
app.include_router(donors_router,        prefix=API_PREFIX)
app.include_router(patients_router,      prefix=API_PREFIX)
app.include_router(requests_router,      prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)
app.include_router(chat_router,          prefix=API_PREFIX)
app.include_router(blood_bank_router,    prefix=API_PREFIX)
app.include_router(coordinator_router,   prefix=API_PREFIX)
app.include_router(ml_router,            prefix=API_PREFIX)
app.include_router(leaderboard_router,   prefix=API_PREFIX)
app.include_router(transfusion_router,   prefix=API_PREFIX)
app.include_router(chatbot_router,       prefix=API_PREFIX)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """
    1. Add new columns to existing tables (idempotent ALTER TABLE).
    2. Seed default badges.
    """
    from sqlalchemy import text
    from app.core.database import SessionLocal
    from app.modules.leaderboard.service import LeaderboardService

    db = SessionLocal()
    try:
        # Add new donor columns (Phase 4) — safe to run multiple times
        db.execute(text("""
            ALTER TABLE donors
            ADD COLUMN IF NOT EXISTS response_rate FLOAT DEFAULT 1.0;
        """))
        db.execute(text("""
            ALTER TABLE donors
            ADD COLUMN IF NOT EXISTS points INTEGER DEFAULT 0;
        """))
        db.execute(text("""
            ALTER TABLE donors
            ADD COLUMN IF NOT EXISTS no_show_count INTEGER DEFAULT 0;
        """))
        db.execute(text("ALTER TABLE donors ADD COLUMN IF NOT EXISTS latitude FLOAT;"))
        db.execute(text("ALTER TABLE donors ADD COLUMN IF NOT EXISTS longitude FLOAT;"))
        db.execute(text("ALTER TABLE patients ADD COLUMN IF NOT EXISTS latitude FLOAT;"))
        db.execute(text("ALTER TABLE patients ADD COLUMN IF NOT EXISTS longitude FLOAT;"))
        db.execute(text("ALTER TABLE blood_requests ADD COLUMN IF NOT EXISTS assigned_blood_bank_id INTEGER;"))
        # Create blood_validation_reports table if not exists
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
        # Run ALTER TABLE for existing databases
        db.execute(text("""
            ALTER TABLE blood_validation_reports
            ADD COLUMN IF NOT EXISTS report_pdf_path VARCHAR;
        """))
        db.commit()

        # Seed default badge definitions
        LeaderboardService(db).seed_badges()

        # Create uploads folder dynamically
        import os
        os.makedirs("/app/uploads/validation_reports", exist_ok=True)
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger(__name__).warning("Startup migration warning: %s", e)
    finally:
        db.close()



# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": f"{settings.APP_NAME} v{settings.APP_VERSION} running"}


@app.get("/health")
def health():
    return {"status": "ok"}