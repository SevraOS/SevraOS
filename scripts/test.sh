#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# HELIOS OS + SEVRA AI — Test Runner Script
# ═══════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")/../backend"
export HELIOS_ENVIRONMENT=testing
exec python -m pytest tests/ \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-fail-under=80 \
    -v "$@"
