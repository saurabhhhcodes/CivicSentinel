# ==============================================================================
# CivicSentinel — Production Dockerfile
# OpenCV AI Competition 2026 Powered by AWS
# Compatible with AWS App Runner, ECS Graviton/x86, Render, Railway, and Cloud Run
# ==============================================================================

FROM python:3.12-slim

WORKDIR /app

# Install system runtime dependencies for OpenCV 5 headless & multimedia
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libgl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pinned Python dependencies
COPY CivicSentinel_Complete_Project/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files (with pre-compiled React 18 frontend)
COPY CivicSentinel_Complete_Project /app/CivicSentinel_Complete_Project

WORKDIR /app/CivicSentinel_Complete_Project

# Create persistent data directories
RUN mkdir -p /app/CivicSentinel_Complete_Project/data/evidence \
             /app/CivicSentinel_Complete_Project/data/uploads

ENV PYTHONPATH=/app/CivicSentinel_Complete_Project \
    PROCESSING_MODE=LOCAL \
    PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Start unified FastAPI server on dynamically assigned cloud port
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
