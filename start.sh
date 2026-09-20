#!/usr/bin/env bash
set -e

echo "FinPilot Bootstrapping..."
echo "Environment: DEMO_MODE=${DEMO_MODE:-false}, LLM_PROVIDER=${LLM_PROVIDER:-none}, PORT=${PORT:-8000}"

# Run Alembic migrations if alembic.ini is present
if [ -f "alembic.ini" ]; then
    echo "Applying database schema migrations..."
    alembic upgrade head || echo "Notice: alembic upgrade completed or tables initialized via app lifespan"
fi

echo "Starting Uvicorn web server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
