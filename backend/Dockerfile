# ═══════════════════════════════════════════════════════════════
# HELIOS OS + SEVRA AI — Backend Dockerfile
# Multi-stage build: builder → runtime
# Production image: python:3.12-slim, non-root user
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies first (Docker layer cache optimization)
COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir "." --prefix=/install

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: create non-root user
RUN groupadd -r helios && useradd -r -g helios -u 1001 helios

WORKDIR /app

# Install runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=helios:helios . .

# Create data directory for SQLite
RUN mkdir -p /app/data && chown -R helios:helios /app/data

# Switch to non-root user
USER helios

# Expose application port
EXPOSE 8000

# Health check (used by Docker and Docker Compose)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live || exit 1

# Default command
CMD ["uvicorn", "app:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--access-log", \
     "--loop", "uvloop", \
     "--http", "httptools"]
