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

# Copy entrypoint startup script
COPY start.sh /app/start.sh
RUN tr -d '\r' < /app/start.sh > /app/start_unix.sh && \
    mv /app/start_unix.sh /app/start.sh && \
    chmod +x /app/start.sh

# Ensure data and uploads directories exist
RUN mkdir -p /app/backend/data/uploads

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

ENTRYPOINT ["/bin/bash", "/app/start.sh"]
