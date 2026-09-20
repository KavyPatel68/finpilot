# Multi-Stage Dockerfile for FinPilot (React + FastAPI Single Service)

# -------------------------------------------------------------
# Stage 1: Build React Frontend
# -------------------------------------------------------------
FROM node:20-slim AS frontend-builder
WORKDIR /frontend

# Copy package descriptors first for Docker layer caching
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source and build production bundle
COPY frontend/ ./
RUN npm run build

# -------------------------------------------------------------
# Stage 2: Python 3.11 Runtime + Static Server
# -------------------------------------------------------------
FROM python:3.11-slim AS runner

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    DEMO_MODE=true \
    LLM_PROVIDER=none \
    FRONTEND_DIST_DIR=/app/frontend/dist \
    DATABASE_URL=sqlite:///./data/finpilot.db

WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

# Ensure data and uploads directories exist
RUN mkdir -p /app/backend/data/uploads

EXPOSE 8000

# Start command with dynamic Render PORT expansion
CMD ["sh", "-c", "mkdir -p data/uploads && (python -m alembic upgrade head || true) && exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
