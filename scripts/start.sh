#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# HELIOS OS + SEVRA AI — Application Start Script
# Usage: ./scripts/start.sh [dev|prod]
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

ENVIRONMENT="${1:-dev}"
cd "$(dirname "$0")/../backend"

echo "Starting HELIOS backend — environment: $ENVIRONMENT"

if [ "$ENVIRONMENT" = "prod" ]; then
    exec uvicorn app:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers "${HELIOS_WORKERS:-4}" \
        --loop uvloop \
        --http httptools \
        --log-config /dev/null \
        --no-access-log
else
    exec uvicorn app:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --loop asyncio \
        --log-config /dev/null
fi
