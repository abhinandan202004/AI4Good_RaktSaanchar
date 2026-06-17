from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
CORE_DB_URL = os.getenv("CORE_DB_URL", "")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if CORE_DB_URL.startswith("postgres://"):
    CORE_DB_URL = CORE_DB_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Read-only connection to core schema (for user/donor lookups)
if CORE_DB_URL:
    core_engine = create_engine(CORE_DB_URL)
    CoreSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=core_engine)
else:
    CoreSessionLocal = SessionLocal
