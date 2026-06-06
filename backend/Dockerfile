FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

# ── Step 1: lightweight core deps ─────────────────────────────────────────────
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    sqlalchemy \
    psycopg2-binary \
    python-dotenv \
    alembic \
    redis \
    "python-jose[cryptography]" \
    "passlib[bcrypt]" \
    "bcrypt<4.1" \
    "pydantic[email]" \
    pydantic-settings \
    httpx \
    python-multipart \
    joblib \
    boto3

# ── Step 2: ML deps (installed separately to avoid OOM during build) ──────────
RUN pip install --no-cache-dir numpy pandas scikit-learn
RUN pip install --no-cache-dir xgboost

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]