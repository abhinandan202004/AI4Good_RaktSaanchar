FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

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

# ── Step 2: ML deps ────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir numpy pandas scikit-learn
RUN pip install --no-cache-dir xgboost

# ── Step 3: Chatbot & RAG deps ────────────────────────────────────────────────
RUN pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir mistralai sarvamai langchain langchain-community faiss-cpu sentence-transformers

COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads/validation_reports

EXPOSE 8000

# Production: no --reload, use $PORT env var (Render injects this)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]