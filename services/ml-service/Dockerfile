FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# Install 'uv' for 10x-100x faster package installation to prevent Hugging Face timeouts
RUN pip install uv && uv pip install --system --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY models/ ./models/

# Expose port 7860 for Hugging Face Spaces
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
