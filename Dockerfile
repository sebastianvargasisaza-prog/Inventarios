# syntax=docker/dockerfile:1
# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Variables de entorno de sistema — no secretos (esos van en .env / Render)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    WEB_CONCURRENCY=3 \
    DB_PATH=/var/data/inventario.db

WORKDIR /app

# Dependencias del sistema (mínimas para SQLite + openpyxl)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python primero (capa cacheada)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY api/ ./api/

# Volumen para datos persistentes
VOLUME ["/var/data"]

# Health check nativo de Docker — Render también lo usa
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/health')" || exit 1

EXPOSE $PORT

# Gunicorn con WAL-safe settings (sync workers = correcto para SQLite WAL)
CMD gunicorn api.index:app \
    --bind 0.0.0.0:$PORT \
    --workers $WEB_CONCURRENCY \
    --worker-class sync \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile -
