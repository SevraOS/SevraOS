#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# HELIOS OS + SEVRA AI — Database Migration Script
# Usage: ./scripts/migrate.sh [upgrade|downgrade|history|current]
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")/../backend"

ACTION="${1:-upgrade}"

case "$ACTION" in
    upgrade)
        echo "Running database migrations (upgrade head)..."
        python -m alembic upgrade head
        ;;
    downgrade)
        echo "Rolling back last migration..."
        python -m alembic downgrade -1
        ;;
    history)
        python -m alembic history
        ;;
    current)
        python -m alembic current
        ;;
    *)
        echo "Usage: $0 [upgrade|downgrade|history|current]"
        exit 1
        ;;
esac
